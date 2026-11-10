"""v1.5.58: Score de Seguridad del Dividendo (método v0.2 de Guille), historial de dividendos, regla de bordes y años viejos de la SEC."""
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


from data import damodaran as D  # noqa: E402
from data import historico as H  # noqa: E402
from data import sec as S  # noqa: E402
from scoring import dividendo as SD  # noqa: E402
import bajar_sec as BS  # noqa: E402

HOY = dt.date(2026, 11, 10)

# --- regla de bordes (Guille: «los puntos de corte no se pueden pisar») ---
chk(D.rating_sintetico(3.0)[0] == "A3/A-", "cobertura justo 3x = A- (antes devolvía None)")
chk(D.rating_sintetico(2.5)[0] == "Baa2/BBB" and D.rating_sintetico(2.4999)[0] == "Ba1/BB+", "borde de BBB")
chk(D.rating_sintetico(8.5)[0] == "Aaa/AAA" and D.rating_sintetico(6.5)[0] == "Aa2/AA", "bordes de AA y AAA")
chk(D.rating_sintetico(-2)[0] == "D2/D", "cobertura negativa = D")
chk(SD.menos_es_mejor(60, SD.ESC_FCF) == 17, "payout de 60% = 17 (no 14)")
chk(SD.menos_es_mejor(60.004, SD.ESC_FCF) == 17 and SD.menos_es_mejor(60.006, SD.ESC_FCF) == 14, "dos decimales antes de ubicar la franja")
chk(SD.menos_es_mejor(100.5, SD.ESC_FCF) == 0 and SD.menos_es_mejor(50, SD.ESC_EPS) == 15, "extremos de las escalas")
chk(SD.categoria(80)[0] == "Seguro" and SD.categoria(81)[0] == "Muy seguro" and SD.categoria(20)[0] == "Muy inseguro" and SD.categoria(41)[0] == "Al límite",
    "categorías 0-20 / 21-40 / 41-60 / 61-80 / 81-100")


# --- historial de dividendos ---
def trimestral(desde, hasta, monto, suba=0.0, meses=(3, 6, 9, 12)):
    out, m = [], monto
    for a in range(desde, hasta + 1):
        for mes in meses:
            out.append([f"{a}-{mes:02d}-15", round(m, 4)])
        m *= 1 + suba
    return out


h = SD.analizar_dividendos(trimestral(1990, 2026, 0.20, 0.05)[:-1], hoy=HOY)       # 2026 con 3 pagos hasta setiembre
chk(h["anios_sin_recorte"] == 36 and h["aumentos_12"] == 12 and h["frecuencia"] == 4, f"subas todos los años: {h['anios_sin_recorte']} años, {h['aumentos_12']} aumentos")
chk(h["crisis_0809"] == "sin_recorte" and h["crisis_2020"] == "sin_recorte", "sin recortes en las crisis")

jpm = trimestral(2000, 2008, 0.38) + [["2009-03-15", 0.38], ["2009-06-15", 0.05], ["2009-09-15", 0.05], ["2009-12-15", 0.05]] + \
    trimestral(2010, 2010, 0.05) + trimestral(2011, 2026, 0.25, 0.08)[:-1]
h = SD.analizar_dividendos(jpm, hoy=HOY)
chk(h["crisis_0809"] == "recorto" and h["anios_sin_recorte"] == 16, f"recorte de 2009 (JPMorgan): {h['crisis_0809']}, {h['anios_sin_recorte']} años")

ford = trimestral(2012, 2019, 0.15) + [["2020-03-01", 0.15], ["2021-12-01", 0.10], ["2022-03-01", 0.10], ["2022-06-01", 0.10],
                                        ["2022-09-01", 0.15], ["2022-12-01", 0.15]] + trimestral(2023, 2026, 0.15, meses=(3, 6, 9))
h = SD.analizar_dividendos(ford, hoy=HOY)
chk(h["crisis_2020"] == "recorto" and h["crisis_0809"] == "no_pagaba", f"suspensión de 2020 (Ford): {h['crisis_2020']}, 2008-09 {h['crisis_0809']}")
chk(h["anios_sin_recorte"] == 4, f"Ford: años sin recortar desde 2022 = 4 ({h['anios_sin_recorte']})")

corrido = trimestral(2010, 2018, 0.50) + [["2019-03-15", 0.5], ["2019-06-15", 0.5], ["2019-09-15", 0.5], ["2020-01-03", 0.5]] + \
    [["2020-03-15", 0.5], ["2020-06-15", 0.5], ["2020-09-15", 0.5], ["2020-12-15", 0.5]] + trimestral(2021, 2026, 0.5, meses=(3, 6, 9))
h = SD.analizar_dividendos(corrido, hoy=HOY)
chk(h["anios_sin_recorte"] == 16 and h["crisis_2020"] == "sin_recorte", f"un pago corrido de diciembre a enero no es recorte ({h['anios_sin_recorte']})")

especial = trimestral(2015, 2026, 1.0, 0.03, meses=(3, 6, 9))
especial.append(["2024-12-20", 15.0])
h = SD.analizar_dividendos(sorted(especial), hoy=HOY)
chk(h["anios_sin_recorte"] == 11 and h["aumentos_12"] == 10, f"un dividendo extraordinario no cuenta ({h['anios_sin_recorte']}, {h['aumentos_12']})")

mmm = trimestral(1990, 2023, 1.0, 0.04) + [["2024-03-15", 6.0], ["2024-06-15", 0.70], ["2024-09-15", 0.70], ["2024-12-15", 0.70]] + \
    trimestral(2025, 2026, 0.73, meses=(3, 6, 9, 12))[:-1]
h = SD.analizar_dividendos(mmm, hoy=HOY)
chk(h["anios_sin_recorte"] == 1, f"recorte de 2024 (3M): 1 año sin recortar ({h['anios_sin_recorte']})")

h = SD.analizar_dividendos(trimestral(2000, 2025, 1.0, 0.03) + [["2026-03-15", 0.5], ["2026-06-15", 0.5], ["2026-09-15", 0.5]], hoy=HOY)
chk(h["recorte_en_curso"] and h["anios_sin_recorte"] == 0, "recorte en el año en curso: 0 años sin recortar")
h = SD.analizar_dividendos(trimestral(2000, 2025, 1.0, meses=(3, 6)), hoy=HOY)
chk(h["anios_pagando"] == 0 and h["anios_sin_recorte"] == 0, "dejó de pagar hace más de un período y medio")
chk(SD.analizar_dividendos([], hoy=HOY) is None, "sin pagos: sin historial")


# --- el ejemplo del documento (empresa inventada): tiene que dar 86, Muy seguro ---
def estados_ejemplo(dpa_ttm_pagado=-700.0, eps_ttm=4.0, patrimonio=5500.0, ebit=5000.0, interes=1000.0):
    fy = list(range(2025, 2012, -1))                                    # 13 años fiscales
    eps = [3.9, 3.8, 3.7, 3.75, 3.6, 3.5, 3.55, 3.4, 3.3, 3.35, 3.2, 3.25, 3.1]   # 8 subas en 12 comparaciones
    anios = ["2026 (TTM)"] + fy
    fcf = [1000.0, 1000.0, 1000.0, 1000.0] + [900.0] * 10
    divp = [dpa_ttm_pagado, -700.0, -700.0, -700.0] + [-600.0] * 10
    return {"moneda": "USD",
            "resultados": {"anios": anios, "filas": [["Resultado operativo", [ebit] * 14, "t"], ["EBITDA", [6000.0] * 14, "m"],
                                                     ["Gasto por intereses", [interes] * 14, "m"], ["Ganancia por acción (diluida)", [eps_ttm] + eps, "eps"]]},
            "balance": {"anios": anios, "filas": [["Deuda total", [6000.0] * 14, "m"], ["Deuda neta", [4500.0] * 14, "m"],
                                                  ["Patrimonio neto", [patrimonio] * 14, "t"]]},
            "flujo": {"anios": anios, "filas": [["Flujo de efectivo libre", fcf, "t"], ["Dividendos pagados", divp, "m"]]},
            "ratios": {"anios": anios, "filas": [["Deuda neta / EBITDA", [2.5] * 14, "x"]]}}


HIST = {"anios_sin_recorte": 30, "anios_pagando": 30, "aumentos_12": 11, "crisis_0809": "sin_recorte", "crisis_2020": "sin_recorte"}
BASE = {"ticker": "EJ", "grupo": "Consumo Básico", "pais": "United States", "dividendo_anual": 2.0, "precio": 50.0, "dy": 0.04, "dy_mediana": 0.035,
        "estados": estados_ejemplo(), "historial": HIST, "estimacion": {"actual": 4.0, "proximo": 4.16}}
r = SD.calcular(BASE)
pts = {v["clave"]: v["pts"] for v in r["variables"]}
chk(r["score"] == 86 and r["categoria"] == "Muy seguro", f"ejemplo del documento = 86 ({r['score']})")
chk(pts == {"fcf": 14, "eps": 15, "cobertura": 10, "deuda": 5, "ndc": 4, "anios": 10, "aumentos": 5, "crisis": 5, "eps_suba": 4, "sector": 5,
            "fcf_pos": 4, "tendencia": 5}, f"puntos por variable del ejemplo: {pts}")
chk(r["conclusion"] == "Paga el 50% de lo que gana y lleva 30 años sin recortar el dividendo. Pierde puntos porque el dividendo ya usa el 70% de su "
    "flujo de caja libre y la deuda equivale a 2,5 veces su EBITDA.",
    f"conclusión del ejemplo: {r['conclusion']}")

r = SD.calcular({**BASE, "dividendo_anual": 4.4, "estados": estados_ejemplo(dpa_ttm_pagado=-1100.0, eps_ttm=4.0)})
chk(r["score"] <= 40 and ("dividendo_supera", 40) in r["topes"] and r["conclusion"].startswith("El dividendo supera lo que gana"),
    f"tope 1: dividendo mayor que ganancia y flujo ({r['score']}, {r['topes']})")
r = SD.calcular({**BASE, "estados": estados_ejemplo(ebit=1200.0)})
chk(r["score"] <= 40 and ("cobertura_baja", 40) in r["topes"], f"tope 2: cobertura menor a 1,5x ({r['score']})")
r = SD.calcular({**BASE, "dy": 0.08, "dy_mediana": 0.035})
chk(r["score"] == 76 and ("alarma_rendimiento", -10) in r["topes"], f"alarma: rendimiento doble de su mediana resta 10 ({r['score']})")
r = SD.calcular({**BASE, "estados": estados_ejemplo(patrimonio=-800.0)})
chk("posible caníbal" in r["notas"] and r["pilares"][2][1] == 25 and not any(v["clave"] == "ndc" for v in r["variables"]),
    "posible caníbal: no se usa deuda neta / capital y el pilar se lleva a 25")
r = SD.calcular({**BASE, "grupo": "Bancos y seguros"})
chk(2 not in r["pilares"] and r["score"] is not None and not any(v["clave"] == "fcf" for v in r["variables"]), "bancos: sin pilar 2 ni flujo libre")
r = SD.calcular({**BASE, "grupo": "Utilities"})
cob = next(v for v in r["variables"] if v["clave"] == "cobertura")
chk(cob["con"] == "EBITDA" and cob["valor"] == 6.0 and next(v for v in r["variables"] if v["clave"] == "eps")["max"] == 35,
    "utilities: cobertura con EBITDA y payout sobre ganancias vale 35")
r = SD.calcular({**BASE, "historial": None})
chk(r["score"] is None and any("bajar_historico" in n for n in r["notas"]), "sin historial de dividendos no se calcula")
r = SD.calcular({**BASE, "dividendo_anual": 0})
chk(r["score"] is None and "no paga dividendo" in r["notas"], "empresa sin dividendo")
r = SD.calcular({**BASE, "pais": "Brazil", "historial": {**HIST, "anios_sin_recorte": 2, "anios_pagando": 30}})
chk(next(v for v in r["variables"] if v["clave"] == "anios")["valor"] == 30, "dividendo variable (extranjera): cuenta los años pagando")
r = SD.calcular({**BASE, "estimacion": None})
chk(next(v for v in r["variables"] if v["clave"] == "tendencia")["fuente"] == "3 años", "sin analistas: tendencia contra 3 años atrás")

# --- con los datos reales guardados en la app: las 21 empresas comparadas con SSD calculan sin error ---
try:
    from config.sectors import TICKER_TO_SECTOR
    paq = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "paquetes_yahoo.json"), encoding="utf-8"))["datos"]
    cache = {x["ticker"]: x for x in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache_datos.json"),
                                                       encoding="utf-8"))["data"]}
    buenos = 0
    for t in ("KO", "PG", "JNJ", "PEP", "MCD", "ADP", "TXN", "ABBV", "MO", "VZ", "T", "PFE", "MMM", "CVX", "XOM", "F", "NEE", "O", "PLD", "WELL", "JPM"):
        if t in paq and t in cache:
            rr = SD.calcular(SD.entrada(cache[t], paq[t]["estados"], HIST))
            buenos += rr["score"] is not None and 0 <= rr["score"] <= 100 and bool(rr["conclusion"])
    chk(buenos == 21, f"las 21 empresas calculan con datos reales ({buenos})")
except FileNotFoundError:
    pass

# --- SEC: años viejos al archivo histórico ---
def hecho(val, ini, fin, form, filed):
    return {"val": val, "start": ini, "end": fin, "form": form, "filed": filed}


facts = {"facts": {"us-gaap": {
    "Revenues": {"units": {"USD": [hecho(100.0, "2014-01-01", "2014-12-31", "10-K", "2015-02-01"), hecho(110.0, "2015-01-01", "2015-12-31", "10-K", "2016-02-01"),
                                   hecho(112.0, "2015-01-01", "2015-12-31", "10-K", "2017-02-01"),       # corregido después: gana el más nuevo
                                   hecho(30.0, "2016-01-01", "2016-03-31", "10-Q", "2016-05-01"),        # trimestre: no cuenta
                                   hecho(120.0, "2016-01-01", "2016-12-31", "10-K", "2017-02-01")]}},
    "EarningsPerShareDiluted": {"units": {"USD/shares": [hecho(4.0, "2014-01-01", "2014-12-31", "10-K", "2015-02-01"),
                                                         hecho(4.4, "2015-01-01", "2015-12-31", "10-K", "2016-02-01"),
                                                         hecho(5.0, "2016-01-01", "2016-12-31", "10-K", "2017-02-01")]}},
    "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [hecho(50.0, "2014-01-01", "2014-12-31", "10-K", "2015-02-01")]}},
    "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [hecho(20.0, "2014-01-01", "2014-12-31", "10-K", "2015-02-01")]}},
    "PaymentsOfDividendsCommonStock": {"units": {"USD": [hecho(10.0, "2014-01-01", "2014-12-31", "10-K", "2015-02-01")]}},
}}}
a = S.a_anios(facts)
chk(sorted(a) == ["2014", "2015", "2016"] and a["2015"]["resultados"]["Ingresos"] == 112.0, "SEC: años completos y gana el informe más nuevo")
chk(a["2014"]["flujo"]["Inversión en activos fijos (CAPEX)"] == -20.0 and a["2014"]["flujo"]["Dividendos pagados"] == -10.0
    and a["2014"]["flujo"]["Flujo de efectivo libre"] == 30.0, "SEC: CAPEX y dividendos en negativo, flujo libre = operativo − CAPEX")
chk(a["2014"]["presentado"] == "2015-02-01", "SEC: fecha de presentación de la ganancia por acción")

reg = H.fusionar_estados(None, {"moneda": "USD", "resultados": {"anios": ["2017 (TTM)", 2016], "filas": [["Ingresos", [130.0, 121.0], "t"],
                                                                                                            ["Ganancia por acción (diluida)", [5.2, 5.0], "eps"]]}},
                         "X", [], "2017-06-01")
chk(S.coincide(a, reg)[0] is True, "SEC y Yahoo coinciden en 2016 (120 vs 121)")
nuevo, sumados = H.sumar_anios_viejos(reg, a, "X", [], hoy="2026-11-10")
chk(sumados == ["2014", "2015"] and nuevo["anios"]["2016"] == reg["anios"]["2016"], "solo suma años más viejos; el de Yahoo no se toca")
chk(nuevo["anios"]["2014"]["fuente"] == "SEC" and nuevo["anios"]["2014"]["captura_acc"] == "2015-02-01", "fuente y fecha para ajustar splits")
full = H.estados_completos("X", archivo={"X": nuevo}, splits=[["2020-06-01", 2.0]], max_anios=13)
eps = SD.serie(full, "Ganancia por acción (diluida)")
chk(eps.get(2014) == 2.0 and eps.get(2016) == 2.5, f"la ganancia por acción vieja se ajusta por el split posterior: {eps}")
_, sum2 = H.sumar_anios_viejos(reg, {"2014": {**a["2014"], "moneda": "EUR"}}, "X", [])
chk(sum2 == [], "otra moneda: no se suma")
mal_reg = H.fusionar_estados(None, {"moneda": "USD", "resultados": {"anios": [2016], "filas": [["Ingresos", [200.0], "t"]]}}, "Y", [], "2017-06-01")
archivo = {"Y": mal_reg}
estado, det, _ = BS.procesar("Y", facts, archivo, [])
chk(estado == "no_coincide" and archivo["Y"] == mal_reg, f"si no coinciden se saltea: {estado} ({det})")
archivo = {"X": reg}
estado, _, sumados = BS.procesar("X", facts, archivo, [])
chk(estado == "ok" and sumados == ["2014", "2015"] and "2014" in archivo["X"]["anios"], "bajar_sec.procesar suma los años")

print(f"OK {ok} MAL {mal}")
