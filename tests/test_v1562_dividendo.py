"""v1.5.62/65: excepción del payout con la ganancia que esperan los analistas (decisión de Guille del 10/11/2026) y bajada trimestral de estimaciones."""
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


from scoring import dividendo as SD  # noqa: E402
import bajar_estimaciones as BE  # noqa: E402

anios = ["2026 (TTM)", 2025, 2024, 2023]


def estados(eps=(4.0, 3.9, 3.8, 3.7), fcf=400.0, divp=-150.0):
    return {"moneda": "USD",
            "resultados": {"anios": anios, "filas": [["Resultado operativo", [500.0] * 4, "t"], ["Gasto por intereses", [100.0] * 4, "m"],
                                                     ["EBITDA", [700.0] * 4, "m"], ["Ganancia por acción (diluida)", list(eps), "eps"]]},
            "balance": {"anios": anios, "filas": [["Deuda total", [1000.0] * 4, "m"], ["Deuda neta", [800.0] * 4, "m"],
                                                  ["Patrimonio neto", [3000.0] * 4, "t"]]},
            "flujo": {"anios": anios, "filas": [["Flujo de efectivo libre", [fcf] * 4, "t"], ["Dividendos pagados", [divp] * 4, "m"]]}}


HIST = {"anios_sin_recorte": 20, "anios_pagando": 20, "aumentos_12": 10, "crisis_0809": "sin_recorte", "crisis_2020": "sin_recorte"}
HOY = dt.date(2026, 11, 10)


def est(actual, proximo=None, n=20, fecha="2026-11-10"):
    return {"actual": actual, "proximo": proximo or actual * 1.05, "analistas": n, "fecha": fecha}


BASE = {"ticker": "AJ", "grupo": "Salud", "pais": "United States", "dividendo_anual": 4.4, "precio": 100.0, "dy": 0.044, "dy_mediana": 0.04,
        "estados": estados(), "historial": HIST, "estimacion": est(6.5), "hoy": HOY}


def var(r, clave):
    return next((v for v in r["variables"] if v["clave"] == clave), None)


r = SD.calcular(BASE)
v = var(r, "eps")
chk(v.get("ajustada") and v["peso_estimada"] == 0.75 and v["valor"] == 74.89 and v["pts"] == 9 and v["estimada"] == 6.5 and v["contable"] == 4.0,
    f"salto de 1,625 veces: pesa 75% la estimada (4,0 + 0,75 × 2,5 = 5,875 → payout 74,89%): {v}")
v = var(SD.calcular({**BASE, "estimacion": est(7.0)}), "eps")
chk(v["peso_estimada"] == 1.0 and v["valor"] == 62.86, f"desde 1,7 veces, toda la estimada (4,4 ÷ 7,0 = 62,86%): {v}")
chk("la ganancia que esperan los analistas para este año" in r["conclusion"] or any("estimada" in n for n in r["notas"]),
    f"la conclusión o la nota lo dicen: {r['conclusion']} {r['notas']}")
v = var(SD.calcular({**BASE, "estimacion": est(5.0)}), "eps")
chk(not v.get("ajustada") and v["pts"] == 0, "salto de 1,25 veces: sigue la contable (110% = 0 puntos)")
# v1.5.67: estados en otra moneda: payout con montos de la misma moneda y salto homologado (se prueba en su moneda y en dólares)
def estados_m(eps, ni, divp=-150.0, fcf=400.0):
    e = estados(eps=eps, fcf=fcf, divp=divp)
    e["resultados"]["filas"].append(["Resultado neto", list(ni), "m"])
    return e


tsm = {**BASE, "moneda_estados": "TWD", "fx": 0.03027, "dividendo_anual": 3.77, "estados": estados_m((489.6, 450.0, 300.0, 280.0), (1500.0,) * 4),
       "estimacion": est(17.5)}
v = var(SD.calcular(tsm), "eps")
chk(v["valor"] == 10.0 and not v.get("ajustada") and v.get("con") == "montos",
    f"TSMC: payout = dividendos pagados ÷ resultado neto (150 ÷ 1.500 = 10%), no 3,77 dólares ÷ 489,6 dólares taiwaneses: {v}")
chk(SD.salto_homologado(17.5, 489.6, 0.03027) == (1.1808, 489.6 * 0.03027), "TSMC: la estimación en dólares por ADR se compara con la contable en dólares (1,18)")
kb = SD.salto_homologado(18660.7, 14000.0, 0.00074)
chk(kb[0] == 1.3329 and kb[1] == 14000.0, f"KB: la estimación viene en wones y se compara en wones (1,33): {kb}")
brl = {**BASE, "moneda_estados": "BRL", "fx": 0.18195, "estados": estados_m((4.0, 3.9, 3.8, 3.7), (500.0,) * 4), "estimacion": est(6.5)}
v = var(SD.calcular(brl), "eps")
chk(v.get("ajustada") and v["salto"] == 1.625 and v["peso_estimada"] == 0.75 and v["valor"] == 20.43,
    f"en reales: el salto de 1,625 se aplica al payout de montos (30% ÷ (1 + 0,75 × 0,625) = 20,43%): {v}")
chk(SD.salto_homologado(6.5, 4.0, None, 0.5) == (0.8125, 8.0), "con factor de ADR también se prueba por ADR y se queda la base más cercana (0,81: sin excepción)")
v = var(SD.calcular({**brl, "estados": estados_m((-1.0, -0.5, 3.8, 3.7), (-100.0, -50.0, 400.0, 380.0))}), "eps")
chk(v and not v.get("ajustada") and v.get("perdida"), f"con pérdida y otra moneda: sin excepción (no se sabe en qué moneda viene la estimación): {v}")
r = SD.calcular({**tsm, "estados": estados_m((489.6, 450.0, 300.0, 280.0), (100.0,) * 4, divp=-150.0, fcf=100.0)})
chk(("dividendo_supera", 40) in r["topes"], "tope en otra moneda: dividendos pagados (150) > resultado neto (100) y > flujo libre")
chk(SD.entrada({"ticker": "X", "moneda_estados": "CNY", "moneda_nota": "Estados en CNY convertidos a USD (fx spot 0.14998). Acciones ajustadas a equivalentes del ADR (x0.2, ~5.0 ordinarias por ADR)."},
               {}, None, None) | {} and SD.entrada({"ticker": "X", "moneda_nota": "Estados en CNY convertidos a USD (fx spot 0.14998). Acciones ajustadas a equivalentes del ADR (x0.2, ~5.0)"}, {}, None, None)["fx"] == 0.14998,
    "entrada() lee el tipo de cambio de la nota de moneda")
chk(SD.entrada({"ticker": "X", "moneda_nota": "Acciones ajustadas a equivalentes del ADR (x1.575, ~0.6 ordinarias por ADR)."}, {}, None, None)["n_inv"] == 1.575,
    "entrada() lee el factor de acciones por ADR")
v = var(SD.calcular({**BASE, "estimacion": est(6.5, n=4)}), "eps")
chk(not v.get("ajustada"), "con 4 analistas no entra (mínimo 5)")
v = var(SD.calcular({**BASE, "estados": estados(divp=-450.0)}), "eps")
chk(not v.get("ajustada"), "si el dividendo supera el flujo de caja libre no entra")
r = SD.calcular({**BASE, "estimacion": est(6.5, fecha="2026-06-01")})
chk(not var(r, "eps").get("ajustada") and var(r, "tendencia")["fuente"] == "3 años",
    "estimación de más de 130 días: no se usa (ni para el payout ni para la tendencia)")
chk(var(SD.calcular({**BASE, "estimacion": est(6.5, fecha="2026-07-05")}), "eps").get("ajustada"), "128 días: todavía vale")
r = SD.calcular({**BASE, "estados": estados(eps=(-1.0, -0.5, 3.8, 3.7)), "dividendo_anual": 1.5})
v = var(r, "eps")
chk(v.get("ajustada") and v.get("perdida_contable") and v["valor"] == 23.08, f"con pérdida contable entra (Guille: «entrarían también»): {v}")
chk(SD._frase(v, True) == "paga el 23% de la ganancia que esperan los analistas para este año (el último año tuvo pérdida)",
    f"frase con pérdida: {SD._frase(v, True)}")
r = SD.calcular({**BASE, "estados": estados(divp=-450.0, fcf=400.0)})
chk(("dividendo_supera", 40) in r["topes"], "tope 1 con la ganancia contable (4,4 > 4,0 y dividendos > flujo)")
for g in ("Bancos y seguros", "REITs", "Utilities"):
    v = var(SD.calcular({**BASE, "grupo": g}), "eps") or var(SD.calcular({**BASE, "grupo": g}), "ffo")
    chk(v is None or not v.get("ajustada"), f"{g}: sin excepción")
chk(SD.estimacion_vigente({"estimacion": None}) is None and SD.estimacion_vigente({"estimacion": {"actual": 1.0}}) == {"actual": 1.0},
    "estimación sin fecha: se usa (compatibilidad)")

# bajar_estimaciones: el histórico solo agrega
hist = {"KO": {"2026-08-15": {"actual": 3.3, "proximo": 3.5, "analistas": 25}}}
n = BE.archivar({"KO": {"actual": 3.34, "proximo": 3.53, "analistas": 25, "fecha": "2026-11-10"},
                 "PG": {"actual": 6.9, "proximo": 7.4, "analistas": 20, "fecha": "2026-11-10"}}, hist)
chk(n == 2 and sorted(hist["KO"]) == ["2026-08-15", "2026-11-10"] and hist["KO"]["2026-08-15"]["actual"] == 3.3, "histórico de estimaciones: solo agrega")
chk(BE.archivar({"KO": {"actual": 9.9, "fecha": "2026-11-10"}}, hist) == 0 and hist["KO"]["2026-11-10"]["actual"] == 3.34,
    "la misma fecha no se pisa")

print(f"OK {ok} MAL {mal}")
