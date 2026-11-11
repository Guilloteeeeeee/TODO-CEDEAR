"""v1.5.69: el recorte del dividendo se busca en la moneda en que la empresa lo fija (decisión de Guille del 11/11/2026)."""
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


from data import moneda_dividendo as MD  # noqa: E402
from data import historico as H  # noqa: E402
from scoring import dividendo as SD  # noqa: E402

HOY = dt.date(2026, 11, 11)


def semestral(desde, hasta, monto_de, mes=(5, 11)):
    """Pagos semestrales: monto_de(año) -> monto de cada pago."""
    return [[f"{a}-{m:02d}-15", monto_de(a)] for a in range(desde, hasta + 1) for m in mes if dt.date(a, m, 15) <= HOY]


def trimestral(desde, hasta, monto_de, meses=(3, 6, 9, 12)):
    return [[f"{a}-{m:02d}-15", monto_de(a)] for a in range(desde, hasta + 1) for m in meses if dt.date(a, m, 15) <= HOY]


# tipo de cambio semanal inventado: la libra pasa de 1,60 a 1,20 dólares entre 2014 y 2016 y vuelve a 1,35
def gbp(d):
    if d.year < 2014:
        return 1.60
    if d.year < 2016:
        return 1.60 - 0.20 * (d.year - 2014 + d.month / 12)
    return 1.20 if d.year < 2020 else 1.35


semanas = {}
d = dt.date(2008, 1, 4)
while d <= HOY:
    semanas[d.isoformat()] = round(gbp(d), 6)
    d += dt.timedelta(days=7)
MONEDAS = {"monedas": {"GBP": {"usd_por_unidad": semanas}}}

# 1) moneda del dividendo: excepciones verificadas, balances, EE.UU.
chk(MD.moneda("NVS", "USD", "Switzerland") == "CHF", "Novartis: francos")
chk(MD.moneda("TTE", "USD", "France") == "EUR", "TotalEnergies: euros")
chk(MD.moneda("BABA", "CNY", "China") == "USD", "Alibaba: dólares por ADS")
chk(MD.moneda("GSK", "GBP", "United Kingdom") == "GBP", "GSK: la moneda de sus balances")
chk(MD.moneda("SHEL", "USD", "United Kingdom") == "USD", "Shell: dólares")
chk(MD.moneda("KO", None, "United States") == "USD", "EE.UU.: dólares")
chk(not [t for t in MD.LOCAL if MD.EXCEPCIONES.get(t, ("x",))[0] == "USD"], "ningún símbolo local es de una empresa que paga en dólares")

# 2) dividendo fijo en libras (0,50 por semestre) que en dólares baja por la libra: no es recorte en su moneda
pagos_gbp = semestral(2008, 2026, lambda a: 0.50)
pagos_usd = [[f, round(m * gbp(dt.date.fromisoformat(f) + dt.timedelta(days=21)), 4)] for f, m in pagos_gbp]
h_usd = SD.analizar_dividendos(pagos_usd, hoy=HOY, sigue_pagando=True)
chk(h_usd["anios_sin_recorte"] < 12, f"en dólares la caída de la libra parece recorte ({h_usd['anios_sin_recorte']})")
conv, fuente = MD.convertir(pagos_usd, "GBP", MONEDAS)
chk(fuente == "monedas" and conv and abs(conv[-1][1] - 0.50) < 0.02, f"convertido a libras vuelve a 0,50 ({conv and conv[-1]})")
h, f = MD.historial("GSK", "GBP", pagos_usd, pais="United Kingdom", hoy=HOY, sigue_pagando=True, monedas=MONEDAS)
chk(f == "convertido" and h["anios_sin_recorte"] >= 17, f"en su moneda no hay recorte ({f}, {h and h['anios_sin_recorte']})")

# 3) recorte real en libras (0,50 -> 0,35 en 2022): aparece aunque el dólar ayude
pagos_gbp2 = semestral(2008, 2026, lambda a: 0.50 if a < 2022 else 0.35)
pagos_usd2 = [[f, round(m * gbp(dt.date.fromisoformat(f) + dt.timedelta(days=21)), 4)] for f, m in pagos_gbp2]
h2, f2 = MD.historial("GSK", "GBP", pagos_usd2, pais="United Kingdom", hoy=HOY, sigue_pagando=True, monedas=MONEDAS)
chk(f2 == "convertido" and h2["anios_sin_recorte"] == 3, f"recorte de 2022 en libras: 2023-2025 sin recortar ({h2['anios_sin_recorte']})")

# 4) bolsa de origen: manda sobre la conversión; sin margen (baja de 3% = recorte)
locales = {"GSK": {"ok": True, "pagos": semestral(2008, 2026, lambda a: 50.0 if a < 2024 else 48.5)}}
h3, f3 = MD.historial("GSK", "GBP", pagos_usd, pais="United Kingdom", hoy=HOY, sigue_pagando=True, locales=locales, monedas=MONEDAS)
chk(f3 == "local" and h3["anios_sin_recorte"] == 1, f"en la bolsa de origen se ve una baja de 3% ({f3}, {h3['anios_sin_recorte']})")
locales_no = {"GSK": dict(locales["GSK"], ok=False)}
_, f4 = MD.historial("GSK", "GBP", pagos_usd, pais="United Kingdom", hoy=HOY, sigue_pagando=True, locales=locales_no, monedas=MONEDAS)
chk(f4 == "convertido", "bolsa de origen no confirmada: se usa el ADR convertido")

# 5) dividendo fijado en dólares: misma regla que EE.UU. (Shell 2020: de 0,94 a 0,32 por trimestre)
shel = trimestral(2005, 2026, lambda a: 0.94 if a < 2020 else 0.32 + 0.03 * (a - 2020))
h5, f5 = MD.historial("SHEL", "USD", shel, pais="United Kingdom", hoy=HOY, sigue_pagando=True)
chk(f5 == "dolares" and h5["anios_sin_recorte"] <= 6 and h5["crisis_2020"] == "recorto", f"Shell: recorte de 2020 ({h5['anios_sin_recorte']})")

# 6) sin bolsa de origen ni moneda: la regla de antes
h6, f6 = MD.historial("TSM", "TWD", pagos_usd, pais="Taiwan", hoy=HOY, sigue_pagando=True)
chk(f6 == "variable" and h6["anios_pagando"] >= 17, "dólar taiwanés sin historia: años pagando (regla de antes)")

# 7) respaldo con el fondo de monedas (FXB del archivo de precios mensuales)
fxb = {"m": {f"{a}-{m:02d}": gbp(dt.date(a, m, 15)) * 100 for a in range(2008, 2027) for m in range(1, 13)}}
conv7, f7 = MD.convertir(pagos_usd, "GBP", None, {"FXB": fxb})
chk(f7 == "fondo de monedas" and conv7 and abs(conv7[-1][1] - 0.50) < 0.025, f"FXB: vuelve a 0,50 libras ({conv7 and conv7[-1]})")
h7, f7b = MD.historial("NGG", "GBP", pagos_usd, pais="United Kingdom", hoy=HOY, sigue_pagando=True, precios={"FXB": fxb})
chk(f7b == "convertido" and h7["anios_sin_recorte"] >= 17, f"con FXB tampoco hay recorte ({h7['anios_sin_recorte']})")

# 8) la serie en su moneda arranca tarde y no tiene recortes: los años de antes se cuentan como antes (beneficio de la duda)
largo = semestral(1995, 2026, lambda a: 1.0)
corto = {"GSK": {"ok": True, "pagos": semestral(2015, 2026, lambda a: 50.0 + a - 2015)}}
h8, f8 = MD.historial("GSK", "GBP", largo, pais="United Kingdom", hoy=HOY, sigue_pagando=True, locales=corto)
chk(f8 == "local" and h8["anios_sin_recorte"] >= 30 and h8.get("extendido"), f"serie corta sin recortes: se extiende ({h8['anios_sin_recorte']})")
chk(h8["crisis_0809"] == "sin_recorte", "la crisis de 2008-09 que la serie local no cubre se lee como antes")

# 9) pagos que faltan en Yahoo (Johnson Controls 2025: 2 de 4) no son recorte; una suspensión de verdad sí
jci = [p for p in trimestral(2015, 2026, lambda a: 0.37 if a < 2026 else 0.40) if not ("2025-09" <= p[0] <= "2025-12-31")]
hj = SD.analizar_dividendos(jci, hoy=HOY, sigue_pagando=True)
chk(hj["anios_sin_recorte"] >= 10 and 2025 in hj["datos_faltantes"], f"pagos faltantes: no es recorte ({hj['anios_sin_recorte']}, {hj['datos_faltantes']})")
susp = [p for p in trimestral(2015, 2026, lambda a: 0.37 if a < 2026 else 0.20) if not ("2025-09" <= p[0] <= "2025-12-31")]
hs = SD.analizar_dividendos(susp, hoy=HOY, sigue_pagando=True)
chk(hs["anios_sin_recorte"] == 0, f"si vuelve a pagar menos, sí es recorte ({hs['anios_sin_recorte']})")
semi = trimestral(2015, 2024, lambda a: 0.37) + [["2025-03-15", 0.37], ["2025-09-15", 0.37], ["2026-03-15", 0.37], ["2026-09-15", 0.37]]
hm = SD.analizar_dividendos(semi, hoy=HOY, sigue_pagando=True)
chk(hm["anios_sin_recorte"] <= 1, f"pasar de 4 a 2 pagos iguales por año es recorte ({hm['anios_sin_recorte']})")

# 10) el score: con dividendo_variable=False se cuentan los años sin recortar; con True, los años pagando
anios = ["2026 (TTM)", 2025, 2024, 2023]
est = {"moneda": "USD",
       "resultados": {"anios": anios, "filas": [["Resultado operativo", [500.0] * 4, "t"], ["Gasto por intereses", [100.0] * 4, "m"],
                                                ["EBITDA", [700.0] * 4, "m"], ["Ganancia por acción (diluida)", [4.0, 3.9, 3.8, 3.7], "eps"]]},
       "balance": {"anios": anios, "filas": [["Deuda total", [1000.0] * 4, "m"], ["Deuda neta", [800.0] * 4, "m"], ["Patrimonio neto", [3000.0] * 4, "t"]]},
       "flujo": {"anios": anios, "filas": [["Flujo de efectivo libre", [400.0] * 4, "t"], ["Dividendos pagados", [-150.0] * 4, "m"]]}}
hist = {"anios_sin_recorte": 4, "anios_pagando": 30, "aumentos_12": 6, "crisis_0809": "sin_recorte", "crisis_2020": "recorto"}
base = {"ticker": "X", "grupo": "Consumo Básico", "pais": "United Kingdom", "dividendo_anual": 1.5, "precio": 50, "estados": est, "historial": hist}
va = next(v for v in SD.calcular(dict(base, dividendo_variable=False))["variables"] if v["clave"] == "anios")
vb = next(v for v in SD.calcular(dict(base, dividendo_variable=True))["variables"] if v["clave"] == "anios")
vc = next(v for v in SD.calcular(dict(base))["variables"] if v["clave"] == "anios")
chk(va["valor"] == 4 and vb["valor"] == 30 and vc["valor"] == 30, f"años: medido {va['valor']}, variable {vb['valor']}, sin dato {vc['valor']}")

# 11) control de la bolsa de origen
chk(MD.coincidencia(pagos_usd, pagos_gbp) == 1.0, "mismas fechas: coinciden 100%")
chk(MD.coincidencia(pagos_usd, semestral(2008, 2026, lambda a: 1, mes=(2, 8))) < 0.6, "otras fechas: no coinciden")
chk(MD.saltos_de_unidad([["2020-01-01", 16.0], ["2020-07-01", 0.16], ["2021-01-01", 16.0]]) == ["2020-07-01", "2021-01-01"], "peniques y libras mezclados")

# 12) bajar_dividendos_locales.py sin red: guarda, controla y no pisa con menos pagos
import bajar_dividendos_locales as BL  # noqa: E402
tmp = tempfile.mkdtemp()
viejo_c, viejo_aqui = H.CARPETA, BL.AQUI
H.CARPETA, BL.AQUI = tmp, tmp
try:
    H.escribir("dividendos.json", {"GSK": pagos_usd, "TM": pagos_usd})
    BL._empresas = lambda: [("GSK", "GBP", "GSK.L"), ("TM", "JPY", "7203.T"), ("VOD", "EUR", None)]
    BL.bajar_dividendos = lambda s: pagos_gbp if s == "GSK.L" else semestral(2008, 2026, lambda a: 1, mes=(2, 8))
    BL.bajar_moneda = lambda m: (f"{m}USD=X", {"2020-01-03": 1.3, "2020-01-10": 1.31}) if m != "JPY" else (None, None)
    BL.PAUSA_S = 0
    BL.main()
    dl = H.leer("dividendos_locales.json", {})["datos"]
    chk(dl["GSK"]["ok"] and dl["GSK"]["coinciden"] == 1.0, "GSK.L confirmada")
    chk(not dl["TM"]["ok"] and "coinciden" in dl["TM"]["motivo"], "fechas que no coinciden: no se usa")
    mo = H.leer("monedas.json", {})["monedas"]
    chk(set(mo) == {"GBP", "EUR"} and mo["GBP"]["usd_por_unidad"]["2020-01-03"] == 1.3, f"monedas guardadas ({sorted(mo)})")
    chk(os.path.exists(os.path.join(tmp, "resultados_dividendos_locales.txt")), "deja resultados_dividendos_locales.txt")
    BL.bajar_dividendos = lambda s: pagos_gbp[:5]
    BL.main(["GSK"])
    chk(len(H.leer("dividendos_locales.json", {})["datos"]["GSK"]["pagos"]) == len(pagos_gbp), "con menos pagos que antes queda lo anterior")
finally:
    H.CARPETA, BL.AQUI = viejo_c, viejo_aqui

print(f"OK {ok} MAL {mal}")
