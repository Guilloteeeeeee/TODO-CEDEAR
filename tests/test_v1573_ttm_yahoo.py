"""v1.5.73: gasto por intereses de Eli Lilly (captura de Yahoo de Guille, 17/11/2026): el dato de 12 meses que publica Yahoo completa la suma de
trimestres, y en las filas de intereses cada columna toma la primera clave de Yahoo que tenga dato."""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import yahoo_extra as Y  # noqa: E402

ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


T = pd.Timestamp
NAN = float("nan")
# anual como en Yahoo para LLY: «Interest Expense» con 2025 vacío («--»)
anual = pd.DataFrame({T("2025-12-31"): [65.0e9, 29.7e9, NAN, 20.6e9], T("2024-12-31"): [45.0e9, 17.0e9, 780.6e6, 10.6e9],
                      T("2023-12-31"): [34.1e9, 9.0e9, 485.9e6, 5.2e9]},
                     index=["Total Revenue", "Operating Income", "Interest Expense", "Net Income"])
# trimestres: a «Interest Expense» le falta un trimestre; «Interest Expense Non Operating» tiene los 4
q = pd.DataFrame({T("2026-09-30"): [20e9, 12e9, NAN, 230e6, 7e9], T("2026-06-30"): [19e9, 11e9, 225e6, 225e6, 6.5e9],
                  T("2026-03-31"): [17e9, 10e9, 220e6, 220e6, 5.5e9], T("2025-12-31"): [18e9, 11.3e9, 222.1e6, 222.1e6, 6e9]},
                 index=["Total Revenue", "Operating Income", "Interest Expense", "Interest Expense Non Operating", "Net Income"])
ttm = pd.DataFrame({T("2026-09-30"): [74e9, 44.3e9, 897.1e6, 897.1e6, 25e9]},
                   index=["Total Revenue", "Operating Income", "Interest Expense", "Interest Expense Non Operating", "Net Income"])

est = Y.analizar_estados({"income_stmt": anual, "q_income_stmt": q, "t_income_stmt": ttm}, "USD")
r = est["resultados"]
fila = dict(zip(r["anios"], next(f[1] for f in r["filas"] if f[0] == "Gasto por intereses")))
chk(r["anios"][0] == "2026 (TTM)", "columna de 12 meses")
chk(abs(fila["2026 (TTM)"] - 897.1e6) < 1, "12 meses: la suma de trimestres no se puede (falta uno) → el dato de 12 meses de Yahoo (897,1 millones)")
chk(fila[2025] is None and abs(fila[2024] - 780.6e6) < 1, "2025 sigue vacío como en Yahoo; 2024 = 780,6 millones")
ope = dict(zip(r["anios"], next(f[1] for f in r["filas"] if f[0] == "Resultado operativo")))
chk(abs(ope["2026 (TTM)"] - 44.3e9) < 1, "el resultado operativo de 12 meses sigue siendo la suma de los 4 trimestres")

# sin el dato de Yahoo: cada celda toma la primera clave con dato («Interest Expense Non Operating» suma los 4 trimestres)
est2 = Y.analizar_estados({"income_stmt": anual, "q_income_stmt": q}, "USD")
r2 = est2["resultados"]
f2 = dict(zip(r2["anios"], next(f[1] for f in r2["filas"] if f[0] == "Gasto por intereses")))
chk(abs(f2["2026 (TTM)"] - (230e6 + 225e6 + 220e6 + 222.1e6)) < 1, "sin el de Yahoo: la otra clave de intereses tiene los 4 trimestres")

# las demás filas no mezclan claves entre años
anual2 = anual.copy()
anual2.loc["Operating Revenue"] = [NAN, NAN, 1.0]
anual2.loc["Total Revenue", T("2023-12-31")] = NAN
est3 = Y.analizar_estados({"income_stmt": anual2}, "USD")
ing = next(f[1] for f in est3["resultados"]["filas"] if f[0] == "Ingresos")
chk(ing[-1] is None, "Ingresos: no se completa 2023 con otra clave (una sola clave por fila)")

# el de Yahoo de otro trimestre no se mezcla
ttm_viejo = ttm.copy()
ttm_viejo.columns = [T("2026-06-30")]
est4 = Y.analizar_estados({"income_stmt": anual, "q_income_stmt": q.drop(index="Interest Expense Non Operating"), "t_income_stmt": ttm_viejo}, "USD")
f4 = dict(zip(est4["resultados"]["anios"], next(f[1] for f in est4["resultados"]["filas"] if f[0] == "Gasto por intereses")))
chk(f4.get("2026 (TTM)") is None, "un dato de 12 meses de Yahoo de otro trimestre no se usa")

# solo el de Yahoo, sin trimestres
est5 = Y.analizar_estados({"income_stmt": anual, "t_income_stmt": ttm}, "USD")
chk(est5["resultados"]["anios"][0] == "2026 (TTM)", "sin trimestres: la columna de 12 meses sale del dato de Yahoo")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
