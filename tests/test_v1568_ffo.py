"""v1.5.68: en los REIT, el FFO que informa la empresa (data/ffo_reit.json) en lugar del de Stock Analysis (decisión de Guille del 11/11/2026)."""
import datetime as dt
import json
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

anios = ["2026 (TTM)", 2025, 2024, 2023]
HOY = dt.date(2026, 11, 11)
HIST = {"anios_sin_recorte": 20, "anios_pagando": 20, "aumentos_12": 10, "crisis_0809": "sin_recorte", "crisis_2020": "sin_recorte"}


def estados():
    return {"moneda": "USD",
            "resultados": {"anios": anios, "filas": [["Resultado operativo", [500.0] * 4, "t"], ["Gasto por intereses", [100.0] * 4, "m"],
                                                     ["EBITDA", [900.0] * 4, "m"], ["Ganancia por acción (diluida)", [1.4, 1.3, 1.2, 1.1], "eps"],
                                                     ["Resultado neto", [300.0] * 4, "m"]]},
            "balance": {"anios": anios, "filas": [["Deuda total", [4000.0] * 4, "m"], ["Deuda neta", [3800.0] * 4, "m"],
                                                  ["Patrimonio neto", [9000.0] * 4, "t"]]},
            "flujo": {"anios": anios, "filas": [["Flujo de efectivo libre", [700.0] * 4, "t"], ["Dividendos pagados", [-400.0] * 4, "m"]]}}


def entrada(ffo_empresa=None, p_ffo=64.62, grupo="REITs", dpa=3.40):
    return {"ticker": "XREIT", "grupo": grupo, "pais": "United States", "dividendo_anual": dpa, "precio": 245.07, "p_ffo": p_ffo,
            "dy": 0.014, "dy_mediana": 0.03, "market_cap": 1.6e11, "estados": estados(), "historial": HIST, "estimacion": None,
            "ffo_empresa": ffo_empresa, "hoy": HOY}


def ffo_var(r):
    return next((v for v in r["variables"] if v["clave"] == "ffo"), None)


FE = {"ffo_12m": 6.19, "ffo_anual": 5.29, "hasta": "2026-09-30", "medida": "Normalized FFO por acción diluida"}

# 1) con el FFO de la empresa: payout = 3,40 / 6,19 (el mejor de 12 meses y último año)
r = SD.calcular(entrada(FE))
v = ffo_var(r)
chk(v and abs(v["valor"] - 54.93) < 0.05, f"payout con FFO de la empresa: {v}")
chk(v and v.get("fuente") == "empresa", "fuente = empresa")
chk(v and v["pts"] == 35, "55% de payout = puntaje completo del pilar 1")
chk(any("FFO informado por la empresa" in n for n in r["notas"]), "nota del FFO de la empresa")

# 2) sin el dato de la empresa: vuelve el de Stock Analysis (precio / P/FFO = 3,79 → 89,7%)
r0 = SD.calcular(entrada(None))
v0 = ffo_var(r0)
chk(v0 and abs(v0["valor"] - 89.65) < 0.1 and v0.get("fuente") == "stockanalysis", f"sin dato de la empresa: {v0}")
chk(r["score"] > r0["score"], "el FFO de la empresa sube el score de un REIT con gastos extraordinarios")

# 3) vencido (más de 200 días desde el cierre del trimestre): vuelve Stock Analysis con una nota
viejo = dict(FE, hasta="2026-03-31")
rv = SD.calcular(entrada(viejo))
chk(ffo_var(rv).get("fuente") == "stockanalysis", "vencido: Stock Analysis")
chk(any("vencido" in n for n in rv["notas"]), "vencido: nota")
chk(SD.ffo_vigente({"ffo_empresa": FE, "hoy": dt.date(2027, 4, 18)}) is FE, "a 200 días todavía vale")
chk(SD.ffo_vigente({"ffo_empresa": FE, "hoy": dt.date(2027, 4, 19)}) is None, "a 201 días ya no")

# 4) el mejor de los dos: si el año fiscal es más alto que los 12 meses, manda el año
r2 = SD.calcular(entrada(dict(FE, ffo_12m=4.0, ffo_anual=5.0)))
chk(abs(ffo_var(r2)["valor"] - 68.0) < 0.05, "toma el FFO más alto (menor payout)")

# 5) FFO negativo en ambos: pérdida, 0 puntos
r3 = SD.calcular(entrada(dict(FE, ffo_12m=-0.5, ffo_anual=-0.2)))
v3 = ffo_var(r3)
chk(v3 and v3.get("perdida") and v3["pts"] == 0, f"FFO negativo: {v3}")

# 6) una empresa que no es REIT no lo usa aunque tenga el dato
r4 = SD.calcular(entrada(FE, grupo="Consumo Básico"))
chk(ffo_var(r4) is None, "no REIT: sin variable de FFO")

# 7) el archivo: los tres REIT de la calibración, con medida, fuentes y fecha, y la suma de los trimestres cerrando
datos = json.load(open(SD.RUTA_FFO, encoding="utf-8"))["datos"]
for tk in ("WELL", "O", "PLD"):
    d = datos.get(tk) or {}
    chk(d.get("ffo_12m") and d.get("ffo_anual") and d.get("hasta") and d.get("medida") and d.get("fuentes"), f"{tk}: campos completos")
    chk("AFFO" not in d.get("medida", ""), f"{tk}: FFO sin extraordinarios, no AFFO")
    partes = [float(x.replace(",", ".")) for x in __import__("re").findall(r"\d+,\d+", d.get("detalle_12m", ""))]
    chk(partes and abs(sum(partes) - d["ffo_12m"]) < 0.005, f"{tk}: la suma del detalle da ffo_12m ({partes})")
chk(SD.ffo_empresa("WELL")["ffo_12m"] == 6.19, "ffo_empresa lee el archivo")
chk(SD.ffo_empresa("KO") is None, "sin dato para quien no está")
chk(SD.entrada({"ticker": "PLD"}, {}, grupo="REITs")["ffo_empresa"]["medida"].startswith("Core"), "entrada trae el FFO de la empresa")

print(f"OK {ok} MAL {mal}")
