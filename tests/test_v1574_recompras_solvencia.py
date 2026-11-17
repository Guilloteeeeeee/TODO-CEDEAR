"""v1.5.74: ganancias retenidas + recompras de 10 años (aprobado por Guille), sin deuda financiera = cobertura máxima, índice de solvencia de las
aseguradoras (cortes PROPUESTOS), intereses de PACCAR cargados con fuente."""
import datetime as dt
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


from scoring import dividendo_v1 as V1  # noqa: E402
from data import sec as S  # noqa: E402

AN = ["2026 (TTM)"] + list(range(2025, 2013, -1))      # TTM + 12 años fiscales (2025 … 2014)


def est(rr=13.7e9, tes=None, at=404.5e9, recompras=None, deuda=100e9, arrend=None, inte=3e9):
    n = len(AN)
    f = lambda v: [v] * n  # noqa: E731
    bal = [["Deuda total", f(deuda), "m"], ["Deuda neta", f(deuda), "m"], ["Activo corriente", f(150e9), "t"], ["Inventarios", f(5e9), "m"],
           ["Pasivo corriente", f(100e9), "t"], ["Activo total", f(at), "t"], ["Ganancias retenidas", f(rr), "m"]]
    if tes is not None:
        bal.append(["Acciones en tesorería", f(tes), "m"])
    if arrend is not None:
        bal.append(["Deuda por arrendamientos", f(arrend), "m"])
    flu = [["Flujo de efectivo libre", f(100e9), "t"], ["Dividendos pagados", f(-15e9), "m"], ["Flujo de efectivo operativo", f(110e9), "t"]]
    if recompras is not None:
        flu.append(["Recompra de acciones", [None] + list(recompras), "m"])
    return {"resultados": {"anios": AN, "filas": [["Ingresos", [400e9 * (1.05 ** -i) for i in range(n)], "t"], ["Resultado operativo", f(130e9), "t"],
                                                  ["EBITDA", f(140e9), "m"], ["Gasto por intereses", f(inte), "m"], ["Resultado neto", f(110e9), "t"],
                                                  ["Ganancia por acción (diluida)", f(7.0), "eps"]]},
            "balance": {"anios": AN, "filas": bal}, "flujo": {"anios": AN, "filas": flu}}


def e(**k):
    base = {"ticker": "X", "grupo": "Hardware y servicios TI", "dividendo_anual": 1.0, "estados": est(),
            "historial": {"recortes": [], "racha_subas": 12, "anios_sin_suba": 0, "ultimo_completo": 2025, "recorte_en_curso": False},
            "estimacion": {"actual": 7.5, "proximo": 8.0}, "mes_cierre": 9, "hoy": dt.date(2026, 11, 17), "rend": 0.004, "fuente_historial": "dolares"}
    base.update(k)
    return base


def v(r, clave):
    return next((x for x in r["variables"] if x["clave"] == clave), None)


# --- 1. ganancias retenidas + recompras -----------------------------------------------------------------------------------
r = V1.calcular(e())
chk(v(r, "re_ta")["pts"] == 0 and abs(v(r, "re_ta")["valor"] - 13.7 / 404.5 * 100) < 1e-6, "sin recompras ni tesorería: 3,4 % → crítica (como Apple antes)")
rec = [-80e9] * 12                                        # 2025 … 2014: 12 años de recompras
r = V1.calcular(e(estados=est(recompras=rec)))
x = v(r, "re_ta")
chk(abs(x["recompras"] - 800e9) < 1 and x["anios_recompras"] == 10, "se suman solo los últimos 10 años fiscales (2016–2025), no los 12")
chk(x["pts"] == 10 and abs(x["valor"] - (13.7e9 + 800e9) / 404.5e9 * 100) < 1e-6, "caníbal: (ganancias retenidas + recompras) ÷ activos → segura")
r = V1.calcular(e(estados=est(rr=50e9, tes=-300e9, recompras=[-10e9] * 12)))
chk(abs(v(r, "re_ta")["valor"] - (50e9 + 300e9) / 404.5e9 * 100) < 1e-6, "tesorería mayor que las recompras: se usa la tesorería (no se suman las dos)")
r = V1.calcular(e(estados=est(rr=50e9, tes=-20e9, recompras=[-10e9] * 12)))
chk(abs(v(r, "re_ta")["valor"] - (50e9 + 100e9) / 404.5e9 * 100) < 1e-6, "recompras mayores que la tesorería: se usan las recompras")
rec_huecos = [-80e9, None, -80e9] + [None] * 9
r = V1.calcular(e(estados=est(recompras=rec_huecos)))
chk(abs(v(r, "re_ta")["recompras"] - 160e9) < 1, "años sin dato de recompras no suman")

# --- 2. sin deuda financiera = cobertura máxima ---------------------------------------------------------------------------
r = V1.calcular(e(estados=est(deuda=0.17e9, arrend=0.17e9, inte=None)))
chk(v(r, "cobertura")["valor"] == 99.0 and any("alquileres" in n for n in r["notas"]), "deuda = alquileres y sin intereses: cobertura máxima")
r = V1.calcular(e(estados=est(deuda=1.0e9, arrend=0.17e9, inte=None)))
chk(r["score"] is None, "con deuda financiera y sin intereses: no hay score (falta el dato)")
r = V1.calcular(e(estados=est(deuda=0.17e9, inte=None)))
chk(r["score"] is None, "sin el dato de alquileres no se supone nada")

# --- 3. índice de solvencia de las aseguradoras --------------------------------------------------------------------------
A = dict(grupo="Bancos y seguros", dividendo_anual=1.0)
chk(v(V1.calcular(e(**A, solvencia=169, solvencia_requisito=100)), "solvencia")["pts"] == 25, "169 %: segura (más de 150 %)")
chk(v(V1.calcular(e(**A, solvencia=150, solvencia_requisito=100)), "solvencia")["pts"] == 10, "150 % justo: gris")
chk(v(V1.calcular(e(**A, solvencia=105)), "solvencia")["pts"] == 10, "105 % (requisito 100 % por defecto): gris")
rs = V1.calcular(e(**A, solvencia=95, solvencia_requisito=100))
chk(v(rs, "solvencia")["pts"] == 0 and not any(a in ("aristocrata", "aspirante") for a, _ in rs["ajustes"]), "debajo del requisito: crítica y sin bono")
chk(v(V1.calcular(e(**A, solvencia=169)), "cet1") is None, "aseguradora con solvencia: no usa CET1")
chk(v(V1.calcular(e(**A, cet1=13.0)), "cet1")["pts"] == 25, "banco: sigue con CET1")
sol = json.load(open(os.path.join(RAIZ, "data", "solvencia_aseguradoras.json"), encoding="utf-8"))["datos"]
for tk, d in sol.items():
    chk((d.get("solvencia") and d.get("requisito") and d.get("hasta") and d.get("fuentes") and d.get("medida")) or d.get("no_publica"),
        f"{tk}: solvencia con requisito, fecha, medida y fuente (o el motivo de por qué no hay)")
chk(sol["AEG"]["solvencia"] == 169, "Aegon 169 % (30/06/2026)")

# --- 4. datos ----------------------------------------------------------------------------------------------------------
pc = V1.intereses_manual("PCAR")
chk(pc and pc["monto"] == 783e6 and pc["anio"] == 2025 and pc["fuentes"], "PACCAR: intereses de su financiera 2025 con fuente")
facts = {"facts": {"us-gaap": {
    "NetIncomeLoss": {"units": {"USD": [{"val": 10.0, "start": "2014-01-01", "end": "2014-12-31", "form": "10-K", "filed": "2015-02-01"}]}},
    "PaymentsForRepurchaseOfCommonStock": {"units": {"USD": [{"val": 45.0, "start": "2014-01-01", "end": "2014-12-31", "form": "10-K", "filed": "2015-02-01"}]}}}}}
chk(S.a_anios(facts)["2014"]["flujo"]["Recompra de acciones"] == -45.0, "SEC: recompras del año (en negativo, como Yahoo)")
from ui import ficha as F  # noqa: E402
chk("Deuda por arrendamientos" in F.SOLO_SCORE, "la fila de alquileres no se muestra en la ficha")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
