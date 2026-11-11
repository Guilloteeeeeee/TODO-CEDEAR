"""v1.5.61: arreglos después de la segunda calibración contra SSD (10/11/2026).
- cambio de pago anual a trimestral (McDonald's 2008) no es recorte;
- tabla de Damodaran de empresas chicas por debajo de US$1.000 millones (Guille: «APLIQUEMOS DESDE 1 B»);
- conclusión: con el tope «el dividendo supera…» no se repiten los payouts y no se dice dos veces «el dividendo»;
- SEC: resultado neto primero al comparar, ganancia por acción en la base de Yahoo (ADR), años ya sumados que se rehacen, diagnóstico."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


from data import historico as H  # noqa: E402
from data import sec as S  # noqa: E402
from scoring import dividendo as SD  # noqa: E402
import bajar_sec as BS  # noqa: E402

HOY = dt.date(2026, 11, 10)


def trimestral(desde, hasta, monto, suba=0.0):
    out = []
    for a in range(desde, hasta + 1):
        for m in (3, 6, 9, 12):
            if dt.date(a, m, 15) <= HOY:
                out.append([f"{a}-{m:02d}-15", round(monto + suba * (a - desde), 4)])
    return out


# --- frecuencia por año ---
chk(SD._habitual(3) == 4 and SD._habitual(5) == 4 and SD._habitual(1) == 1 and SD._habitual(11) == 12, "frecuencia habitual (3 pagos = trimestral)")
mcd = [[f"{a}-11-15", 0.2 + 0.05 * (a - 1990)] for a in range(1990, 2008)] + trimestral(2008, 2026, 0.375, 0.05)
h = SD.analizar_dividendos(mcd, hoy=HOY)
chk(h["crisis_0809"] == "sin_recorte" and h["anios_sin_recorte"] == 36, f"de anual a trimestral (McDonald's 2008) no es recorte: {h['crisis_0809']}, {h['anios_sin_recorte']}")
semi = [[f"{a}-{m:02d}-10", 0.5] for a in range(2005, 2015) for m in (5, 11)] + trimestral(2015, 2026, 0.25)
h = SD.analizar_dividendos(semi, hoy=HOY)
chk(h["anios_sin_recorte"] == 21, f"de semestral a trimestral sin bajar el monto anual no es recorte ({h['anios_sin_recorte']})")
corte = [[f"{a}-11-15", 2.0] for a in range(2000, 2010)] + trimestral(2010, 2026, 0.30)
h = SD.analizar_dividendos(corte, hoy=HOY)
chk(h["anios_sin_recorte"] == 15, f"de anual 2,00 a trimestral 0,30 (1,20 por año) sí es recorte ({h['anios_sin_recorte']})")

faltan = trimestral(2010, 2025, 0.5)[:-2]                       # el historial termina en junio de 2025 (pasa con algunos ADR en Yahoo)
h1, h2 = SD.analizar_dividendos(faltan, hoy=HOY), SD.analizar_dividendos(faltan, hoy=HOY, sigue_pagando=True)
chk(h1["anios_pagando"] == 0 and h2["anios_pagando"] == 16 and h2["historial_incompleto"] and not h1["historial_incompleto"],
    f"si el cache dice que sigue pagando, los pagos que faltan no son suspensión ({h1['anios_pagando']}, {h2['anios_pagando']})")
ngg = [[f"{a}-05-30", 2.0] for a in range(2012, 2027)] + [[f"{a}-11-20", 1.0] for a in range(2012, 2026)] + [["2024-06-07", 2.5]]
h = SD.analizar_dividendos(sorted(ngg), hoy=HOY)
chk(h["frecuencia"] == 2 and h["anios_pagando"] == 14 and not h["recorte_en_curso"],
    f"semestral con un extraordinario en el año anterior: sigue siendo semestral ({h['frecuencia']}, {h['anios_pagando']})")
txn = [[f"{a}-{m:02d}-28", v] for a, vals in ((2002, (0.022, 0.023, 0.021, 0.021)), (2003, (0.021, 0.023, 0.021, 0.021)))
       for m, v in zip((1, 4, 7, 10), vals)] + trimestral(2004, 2026, 0.025, 0.02)
h = SD.analizar_dividendos(txn, hoy=HOY)
chk(h["anios_sin_recorte"] == 24, f"0,0215 → 0,021 por pago es redondeo de Yahoo, no recorte ({h['anios_sin_recorte']})")
acn = [[f"{a}-{m:02d}-15", v] for a, vals in ((2017, (1.21, 1.33)), (2018, (1.33, 1.46)), (2019, (1.46, 0.80))) for m, v in zip((5, 11), vals)] + \
    trimestral(2020, 2026, 0.80, 0.08)
h = SD.analizar_dividendos(acn, hoy=HOY)
chk(h["anios_sin_recorte"] == 9 and h["crisis_2020"] == "sin_recorte",
    f"de semestral a trimestral a mitad de año (Accenture 2019) no es recorte ({h['anios_sin_recorte']})")
cop = trimestral(2015, 2020, 0.3) + [[f"2021-{m:02d}-05", 0.2] for m in (2, 5, 8, 11)] + trimestral(2021, 2023, 0.45) + trimestral(2024, 2026, 0.78)
h = SD.analizar_dividendos(sorted(cop), hoy=HOY)
chk(h["anios_sin_recorte"] == 11 and h["frecuencia"] == 4, f"trimestral con pagos variables extra (ConocoPhillips) sigue trimestral ({h['anios_sin_recorte']})")
ford = trimestral(2012, 2019, 0.15) + [["2020-03-01", 0.15], ["2021-12-01", 0.10]] + trimestral(2022, 2026, 0.15)
h = SD.analizar_dividendos(ford, hoy=HOY)
chk(h["crisis_2020"] == "recorto" and h["anios_sin_recorte"] == 4, f"suspensión de Ford: un pago suelto por año no es «pago anual» ({h['anios_sin_recorte']})")

# --- empresas chicas: tabla de Damodaran de chicas o riesgosas por debajo de US$1.000 millones ---
anios = ["2026 (TTM)", 2025, 2024, 2023]
est = {"moneda": "USD",
       "resultados": {"anios": anios, "filas": [["Resultado operativo", [500.0] * 4, "t"], ["Gasto por intereses", [100.0] * 4, "m"],
                                                ["EBITDA", [700.0] * 4, "m"], ["Ganancia por acción (diluida)", [4.0, 3.9, 3.8, 3.7], "eps"]]},
       "balance": {"anios": anios, "filas": [["Deuda total", [1000.0] * 4, "m"], ["Deuda neta", [800.0] * 4, "m"], ["Patrimonio neto", [3000.0] * 4, "t"]]},
       "flujo": {"anios": anios, "filas": [["Flujo de efectivo libre", [400.0] * 4, "t"], ["Dividendos pagados", [-150.0] * 4, "m"]]}}
HIST = {"anios_sin_recorte": 20, "anios_pagando": 20, "aumentos_12": 10, "crisis_0809": "sin_recorte", "crisis_2020": "sin_recorte"}
base = {"ticker": "CH", "grupo": "Consumo Básico", "pais": "United States", "dividendo_anual": 1.5, "precio": 40.0, "dy": 0.0375, "dy_mediana": 0.035,
        "estados": est, "historial": HIST, "estimacion": None}
grande = next(v for v in SD.calcular({**base, "market_cap": 5e10})["variables"] if v["clave"] == "cobertura")
chica = next(v for v in SD.calcular({**base, "market_cap": 6e8})["variables"] if v["clave"] == "cobertura")
sin = next(v for v in SD.calcular(base)["variables"] if v["clave"] == "cobertura")
chk(grande["rating"] == "A2/A" and grande["pts"] == 10 and grande["tabla"] == "grande", f"cobertura 5x en una grande = A ({grande['rating']})")
chk(chica["rating"] == "A3/A-" and chica["pts"] == 8 and chica["tabla"] == "chica", f"cobertura 5x en una chica = A- ({chica['rating']})")
chk(sin["tabla"] == "grande", "sin capitalización: tabla de grandes")
chk(next(v for v in SD.calcular({**base, "market_cap": 1e9})["variables"] if v["clave"] == "cobertura")["tabla"] == "grande",
    "justo US$1.000 millones: tabla de grandes (chica es por debajo)")
chk(SD.entrada({"ticker": "CH", "market_cap": 6e8, "annual_dividend": 1.5}, est, HIST, None, "Consumo Básico")["market_cap"] == 6e8,
    "entrada() pasa la capitalización del cache")

# --- conclusión ---
chk(SD._unir(["el dividendo supera lo que gana y lo que genera de caja", "el dividendo ya usa el 100% de su flujo de caja libre"])
    == "el dividendo supera lo que gana y lo que genera de caja y pagarlo ya usa el 100% de su flujo de caja libre",
    "no se pega «el 100%…» a la frase del tope")
chk(SD._unir(["el dividendo se lleva el 95% de lo que gana", "el dividendo ya usa el 120% de su flujo de caja libre"])
    == "el dividendo se lleva el 95% de lo que gana y el 120% de su flujo de caja libre", "dos payouts seguidos se juntan")
chk(SD._unir(["lleva solo 1 año sin recortar el dividendo", "el dividendo ya usa el 60% de su flujo de caja libre"])
    == "lleva solo 1 año sin recortar el dividendo y pagarlo ya usa el 60% de su flujo de caja libre", "sin decir dos veces «el dividendo»")
res = {"score": 38, "topes": [("dividendo_supera", 40)],
       "variables": [{"clave": "fcf", "pilar": 1, "pts": 0.0, "max": 20, "valor": 140.0}, {"clave": "eps", "pilar": 1, "pts": 0.0, "max": 15, "valor": 130.0},
                     {"clave": "eps_suba", "pilar": 4, "pts": 0.0, "max": 6, "valor": 0, "de": 3},
                     {"clave": "tendencia", "pilar": 5, "pts": 5.0, "max": 5, "valor": 0.1, "fuente": "analistas"}]}
c = SD.conclusion(res)
chk(c == "El dividendo supera lo que gana y lo que genera de caja y sus ganancias no subieron en ninguno de los últimos 3 años. "
    "A favor: se espera que su ganancia crezca el próximo año.", f"con el tope no se repiten los payouts: {c}")


# --- SEC ---
def hecho(val, ini, fin, form, filed):
    return {"val": val, "start": ini, "end": fin, "form": form, "filed": filed}


def anual(a, v, filed=None):
    return hecho(v, f"{a}-01-01", f"{a}-12-31", "20-F", filed or f"{a + 1}-04-01")


def en_informes(valor, desde=2014, hasta=2023, base=lambda f: 1.0):
    """Como los informes reales: cada 20-F presentado en abril del año F trae los años F-3, F-2 y F-1 (en la base de ese informe)."""
    return [anual(a, valor(a) * base(f), f"{f}-04-01") for f in range(desde + 1, hasta + 2) for a in (f - 3, f - 2, f - 1) if desde <= a <= hasta]


facts = {"facts": {"ifrs-full": {
    "Revenue": {"units": {"TWD": [anual(a, 1000.0 + 100 * (a - 2014)) for a in range(2014, 2024)]}},
    "ProfitLossAttributableToOwnersOfParent": {"units": {"TWD": en_informes(lambda a: 400.0 + 40 * (a - 2014))}},
    "DilutedEarningsLossPerShare": {"units": {"TWD/shares": en_informes(lambda a: 10.0 + (a - 2014))}}}}}
sec = S.a_anios(facts)
# Yahoo: mismo resultado neto, ingresos armados de otra forma (+20%) y ganancia por ADR (1 ADR = 5 acciones)
yahoo = {"moneda": "TWD", "resultados": {"anios": ["2024 (TTM)", 2023, 2022, 2021],
                                         "filas": [["Ingresos", [2200.0, 1900 * 1.2, 1800 * 1.2, 1700 * 1.2], "t"],
                                                   ["Resultado neto", [800.0, 760.0, 720.0, 680.0], "t"],
                                                   ["Ganancia por acción (diluida)", [100.0, 95.0, 90.0, 85.0], "eps"]]}}
reg = H.fusionar_estados(None, yahoo, "TSMX", [], "2026-11-01")
ok_c, det = S.coincide(sec, reg)
chk(ok_c is True and "Resultado neto" in det, f"coincide con el resultado neto aunque los ingresos difieran 20% ({det})")
f, det_f = S.factor_por_accion(sec, reg)
chk(f == 5.0, f"factor por acción del ADR = 5 ({f}, {det_f})")
nuevo, sumados = H.sumar_anios_viejos(reg, sec, "TSMX", [], hoy="2026-11-10", factor_accion=f)
chk(sumados == [str(a) for a in range(2014, 2021)] and nuevo["anios"]["2014"]["resultados"]["Ganancia por acción (diluida)"] == 50.0
    and nuevo["anios"]["2014"]["factor_accion"] == 5.0, "la ganancia por acción de la SEC pasa a la base de Yahoo (10 × 5 = 50)")
chk(nuevo["anios"]["2014"]["resultados"]["Resultado neto"] == 400.0, "los montos no se tocan")
# con split posterior al informe de la SEC: el factor se mide con las dos cifras llevadas a hoy
sec_sp = {a: {**r, "resultados": {**r["resultados"], "Ganancia por acción (diluida)": r["resultados"]["Ganancia por acción (diluida)"] * 2}}
          for a, r in sec.items()}                               # SEC presentada antes de un split 1:2 (el doble por acción)
chk(S.factor_por_accion(sec_sp, reg, splits=[["2025-01-15", 2.0]])[0] == 5.0, "el split posterior no se confunde con la base del ADR")
chk(S.factor_por_accion(sec, H.fusionar_estados(None, {"moneda": "TWD", "resultados": {"anios": [2023], "filas": [
    ["Resultado neto", [760.0], "t"], ["Ganancia por acción (diluida)", [19.0], "eps"]]}}, "Z", [], "2026-11-01"))[0] == 1.0,
    "misma base: factor 1")
# bajar_sec: años ya sumados sin el factor (como quedaron en la v1.5.58) se rehacen
viejo, _ = H.sumar_anios_viejos(reg, sec, "TSMX", [], hoy="2026-11-09")
archivo, cambios = {"TSMX": viejo}, []
estado, det, corr = BS.procesar("TSMX", facts, archivo, cambios, hoy="2026-11-10")
chk(estado == "corregido" and len(corr) == 7 and archivo["TSMX"]["anios"]["2016"]["resultados"]["Ganancia por acción (diluida)"] == 60.0
    and any(c["tipo"] == "sec_corregido" for c in cambios), f"bajar_sec rehace los años ya sumados: {estado} ({det})")
antes = archivo["TSMX"]["anios"]["2016"]
estado, _, _ = BS.procesar("TSMX", facts, archivo, cambios, hoy="2026-12-01")
chk(estado == "nada_nuevo" and archivo["TSMX"]["anios"]["2016"] is antes, "segunda corrida: nada nuevo y no se reescribe")
chk(all(archivo["TSMX"]["anios"][a].get("fuente") is None for a in ("2021", "2022", "2023")), "los años de Yahoo no se tocan")
# EPS «básica y diluida» y diagnóstico de «sin datos»
f2 = {"facts": {"us-gaap": {"EarningsPerShareBasicAndDiluted": {"units": {"USD/shares": [hecho(2.5, "2015-01-01", "2015-12-31", "10-K", "2016-02-20")]}},
                            "NetIncomeLoss": {"units": {"USD": [hecho(90.0, "2015-01-01", "2015-12-31", "10-K", "2016-02-20")]}}}}}
chk(S.a_anios(f2)["2015"]["resultados"]["Ganancia por acción (diluida)"] == 2.5, "ganancia por acción «básica y diluida»")
estado, det, _ = BS.procesar("Q", {"entityName": "Ejemplo SA", "facts": {"dei": {"EntityCommonStockSharesOutstanding": {}}}}, {}, [])
chk(estado == "sin_datos" and "Ejemplo SA" in det and "ninguno de nuestros conceptos" in det, f"diagnóstico de «sin datos»: {det}")

print(f"OK {ok} MAL {mal}")
