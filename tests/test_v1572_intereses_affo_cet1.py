"""v1.5.72: gasto por intereses sin datos viejos (mismo período, SEC, carga manual), AFFO sin FFO provisorio, CET1 con requisito de cada banco."""
import copy
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


from scoring import dividendo_v1 as V1  # noqa: E402
from data import sec as S, historico as H  # noqa: E402
import bajar_sec as B  # noqa: E402

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def est(ebit=(500.0,) * 5, inte=(50.0,) * 5, pag=None, deuda=1500.0, ebitda=700.0):
    f = lambda v: [v] * 5  # noqa: E731
    res = [["Ingresos", [1200, 1150, 1100, 1050, 1000], "t"], ["Resultado operativo", list(ebit), "t"], ["EBITDA", f(ebitda), "m"],
           ["Gasto por intereses", list(inte), "m"], ["Resultado neto", f(300.0), "t"], ["Ganancia por acción (diluida)", f(4.0), "eps"]]
    flu = [["Flujo de efectivo libre", f(400.0), "t"], ["Dividendos pagados", f(-150.0), "m"], ["Flujo de efectivo operativo", f(600.0), "t"]]
    if pag:
        flu.append(["Intereses pagados", list(pag), "m"])
    return {"resultados": {"anios": AN, "filas": res},
            "balance": {"anios": AN, "filas": [["Deuda total", f(deuda), "m"], ["Deuda neta", f(1000.0), "m"], ["Activo corriente", f(800.0), "t"],
                                               ["Inventarios", f(100.0), "m"], ["Pasivo corriente", f(500.0), "t"], ["Activo total", f(5000.0), "t"],
                                               ["Ganancias retenidas", f(2500.0), "m"], ["Acciones en tesorería", f(0.0), "m"]]},
            "flujo": {"anios": AN, "filas": flu}}


def e(**k):
    base = {"ticker": "X", "grupo": "Industrial", "dividendo_anual": 1.5, "estados": est(),
            "historial": {"recortes": [], "racha_subas": 12, "anios_sin_suba": 0, "ultimo_completo": 2025, "recorte_en_curso": False},
            "estimacion": {"actual": 4.0, "proximo": 4.0}, "mes_cierre": 12, "hoy": dt.date(2026, 11, 17), "rend": 0.03, "fuente_historial": "dolares"}
    base.update(k)
    return base


def v(r, clave):
    return next((x for x in r["variables"] if x["clave"] == clave), None)


# --- 1. intereses: nada de años viejos ------------------------------------------------------------------------------------
r = V1.calcular(e(estados=est(inte=(None, None, 80.0, 80.0, 80.0))))
chk(r["score"] is None and any("gasto por intereses" in n for n in r["notas"]), "sin intereses en 12 meses ni último año: no usa 2024, no hay score")
r = V1.calcular(e(estados=est(ebit=(900.0, 500.0, 400.0, 400.0, 400.0), inte=(None, 50.0, 300.0, 300.0, 300.0))))
chk(abs(v(r, "cobertura")["valor"] - 10.0) < 1e-9, "sin intereses de 12 meses: resultado e intereses del último año (mismo período, 500/50)")
r = V1.calcular(e(estados=est(ebit=(900.0, 500.0, 400.0, 400.0, 400.0), inte=(90.0, 50.0, 50.0, 50.0, 50.0))))
chk(abs(v(r, "cobertura")["valor"] - 10.0) < 1e-9, "con los dos de 12 meses: 900/90")
r = V1.calcular(e(estados=est(inte=(None,) * 5, pag=(None, 125.0, 10.0, 10.0, 10.0))))
chk(abs(v(r, "cobertura")["valor"] - 4.0) < 1e-9 and any("pagados" in n for n in r["notas"]), "respaldo: intereses pagados del mismo período")
man = {"anio": 2025, "monto": 25.0, "medida": "intereses de sus bonos a pagar", "fuentes": ["x"]}
r = V1.calcular(e(estados=est(inte=(None,) * 5), intereses_manual=man))
chk(abs(v(r, "cobertura")["valor"] - 20.0) < 1e-9 and v(r, "cobertura")["pts"] == 25 and any("a mano" in n for n in r["notas"]),
    "carga manual con fuente: resultado de su año ÷ monto")
r = V1.calcular(e(estados=est(inte=(None,) * 5), intereses_manual=dict(man, monto=0)))
chk(v(r, "cobertura")["valor"] == 99.0, "carga manual 0 (sin deuda financiera): cobertura segura")
r = V1.calcular(e(estados=est(inte=(None,) * 5), intereses_manual=dict(man, anio=2019)))
chk(r["score"] is None, "carga manual de un año que no está en los estados: no se usa")
r = V1.calcular(e(estados=est(inte=(None,) * 5, deuda=0.0)))
chk(v(r, "cobertura")["valor"] == 99.0 and r["score"] is not None, "sin deuda: cobertura segura")
chk(V1.intereses_manual("AAPL")["monto"] > 0 and V1.intereses_manual("GRMN")["monto"] == 0 and V1.intereses_manual("KO") is None,
    "archivo data/intereses_manuales.json")
for tk, d in V1._MANUALES[next(iter(V1._MANUALES))].items():
    chk(d.get("fuentes") and d.get("medida") and d.get("anio") and d.get("cargado"), f"{tk}: carga manual con fuente, medida, año y fecha")
rb = V1.calcular(e(grupo="Bancos y seguros", estados=est(inte=(None,) * 5), cet1=12.0))
chk(rb["score"] is not None and v(rb, "cobertura") is None, "bancos: sin cobertura de intereses, el score sigue")

# --- 2. SEC: completar los huecos de Yahoo ----------------------------------------------------------------------------------


def fact(val, ini, fin, form="10-K", filed="2026-02-01"):
    return {"val": val, "start": ini, "end": fin, "form": form, "filed": filed}


facts = {"facts": {"us-gaap": {
    "NetIncomeLoss": {"units": {"USD": [fact(300.0, "2024-01-01", "2024-12-31"), fact(310.0, "2025-01-01", "2025-12-31")]}},
    "Revenues": {"units": {"USD": [fact(1100.0, "2024-01-01", "2024-12-31"), fact(1150.0, "2025-01-01", "2025-12-31")]}},
    "InterestExpense": {"units": {"USD": [fact(40.0, "2024-01-01", "2024-12-31"), fact(45.0, "2025-01-01", "2025-12-31"),
                                          fact(11.0, "2025-07-01", "2025-09-30", form="10-Q")]}},
    "InterestPaidNet": {"units": {"USD": [fact(-42.0, "2025-01-01", "2025-12-31")]}}}}}
sa = S.a_anios(facts)
chk(sa["2025"]["resultados"]["Gasto por intereses"] == 45.0 and sa["2025"]["flujo"]["Intereses pagados"] == -42.0,
    "SEC: gasto por intereses e intereses pagados del año completo (no el trimestre)")
reg = {"anios": {"2025": {"moneda": "USD", "resultados": {"Resultado neto": 312.0, "Ingresos": 1150.0, "Gasto por intereses": None}, "flujo": {}},
                 "2024": {"moneda": "USD", "resultados": {"Resultado neto": 300.0, "Gasto por intereses": 39.0}}}}
hz, no = S.huecos(sa, reg)
chk(set(hz) == {"2025"} and hz["2025"]["resultados"]["Gasto por intereses"] == 45.0 and hz["2025"]["flujo"]["Intereses pagados"] == 42.0,
    "huecos: solo la celda vacía de 2025 (2024 ya lo tenía Yahoo), en positivo")
reg_mal = copy.deepcopy(reg)
reg_mal["anios"]["2025"]["resultados"]["Resultado neto"] = 500.0
reg_mal["anios"]["2025"]["resultados"]["Ingresos"] = 2000.0
hz2, no2 = S.huecos(sa, reg_mal)
chk(not hz2 and no2 and "2025" in no2[0], "huecos: si el año no coincide (neto e ingresos), no se completa")
reg_eur = copy.deepcopy(reg)
reg_eur["anios"]["2025"]["moneda"] = "EUR"
# v1.5.90: la etiqueta sola ya no decide (Yahoo rotula BRL lo que está en dólares: Vale, Embraer, Petrobras): con cifras iguales se completa
# con la etiqueta de lo guardado; con cifras de verdad en otra moneda (acá 10 % distintas, como un tipo de cambio), no
chk(S.huecos(sa, reg_eur)[0].get("2025", {}).get("moneda") == "EUR", "huecos: etiqueta distinta con cifras iguales, se completa con la etiqueta guardada")
for g in ("resultados",):
    for rot in ("Resultado neto", "Ingresos"):
        if reg_eur["anios"]["2025"][g].get(rot) is not None:
            reg_eur["anios"]["2025"][g][rot] *= 0.9
chk(not S.huecos(sa, reg_eur)[0], "huecos: otra moneda de verdad (cifras distintas), no se completa")
reg_sec = copy.deepcopy(reg)
reg_sec["anios"]["2025"]["fuente"] = "SEC"
chk(not S.huecos(sa, reg_sec)[0], "huecos: solo en los años de Yahoo")
cambios = []
reg2, camb = H.completar_huecos(reg, hz, "X", cambios, hoy="2026-12-01")
chk(camb == ["2025"] and reg2["huecos"]["2025"]["fuente"] == "SEC" and cambios and cambios[-1]["tipo"] == "huecos_sec", "huecos guardados aparte")
reg3, camb3 = H.completar_huecos(reg2, hz, "X", cambios, hoy="2026-12-15")
chk(not camb3 and reg3["huecos"]["2025"]["captura"] == "2026-12-01", "segunda corrida igual: no cambia nada")
yahoo = {"moneda": "USD", "resultados": {"anios": ["2026 (TTM)", 2025, 2024], "filas": [["Resultado neto", [320.0, 312.0, 300.0], "t"],
                                                                                       ["Gasto por intereses", [None, None, 39.0], "m"]]},
         "flujo": {"anios": ["2026 (TTM)", 2025, 2024], "filas": [["Flujo de efectivo libre", [1.0, 1.0, 1.0], "t"]]}}
antes = copy.deepcopy(yahoo)
ec = H.estados_completos("X", yahoo, archivo={"X": reg2}, splits=[])
fila = next(f for f in ec["resultados"]["filas"] if f[0] == "Gasto por intereses")
filap = next((f for f in ec["flujo"]["filas"] if f[0] == "Intereses pagados"), None)
chk(fila[1] == [None, 45.0, 39.0], "estados_completos: completa la celda vacía de 2025, no toca la de Yahoo ni el TTM")
chk(filap and filap[1] == [None, 42.0, None], "estados_completos: suma la fila de intereses pagados que Yahoo no trajo")
chk(yahoo == antes, "no modifica los estados de Yahoo recibidos")
yahoo_lleno = copy.deepcopy(yahoo)
yahoo_lleno["resultados"]["filas"][1][1][1] = 47.0
ec2 = H.estados_completos("X", yahoo_lleno, archivo={"X": reg2}, splits=[])
chk(next(f for f in ec2["resultados"]["filas"] if f[0] == "Gasto por intereses")[1][1] == 47.0, "si Yahoo tiene el dato, manda Yahoo")
arch = {"KO": {"anios": {"2025": {"moneda": "USD", "resultados": {"Resultado neto": 1.0}, "flujo": {}}}},
        "PEP": {"anios": {"2025": {"moneda": "USD", "resultados": {"Gasto por intereses": 5.0}}}}}
falt = B.sin_intereses(arch, ["KO", "PEP"])
chk(any(x.startswith("KO") for x in falt) and not any(x.startswith("PEP") for x in falt), "resultados_sec: lista las que siguen sin intereses")

# --- 3. CET1 con el requisito de cada banco ---------------------------------------------------------------------------------
B_ = dict(grupo="Bancos y seguros", dividendo_anual=1.0)
chk(v(V1.calcular(e(**B_, cet1=11.5)), "cet1")["pts"] == 25, "CET1 > 11 %: seguro")
chk(v(V1.calcular(e(**B_, cet1=10.0, cet1_requisito=8.0)), "cet1")["pts"] == 10, "CET1 10 % con requisito 8 %: gris")
chk(v(V1.calcular(e(**B_, cet1=9.0, cet1_requisito=8.0)), "cet1")["pts"] == 10, "CET1 9 % con requisito 8 %: gris (llega hasta el requisito)")
chk(v(V1.calcular(e(**B_, cet1=10.0, cet1_requisito=10.5)), "cet1")["pts"] == 0, "CET1 por debajo de su requisito: crítico")
rq = V1.calcular(e(**B_, cet1=9.0))
chk(v(rq, "cet1")["pts"] == 0 and any("requisito" in n for n in rq["notas"]), "sin requisito cargado: 9,5 % y nota")
chk(v(V1.calcular(e(**B_)), "cet1")["pts"] is None, "sin CET1: no cuenta")

# --- 4. REITs: solo AFFO --------------------------------------------------------------------------------------------------
rr = V1.calcular(e(grupo="REITs"))
chk(v(rr, "affo")["pts"] is None, "REIT sin AFFO cargado: la métrica no cuenta (nada de FFO provisorio)")
import json  # noqa: E402
ffo = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ffo_reit.json"), encoding="utf-8"))["datos"]
for tk in ("O", "PLD"):
    d = ffo.get(tk) or {}
    chk(d.get("affo_payout_12m") and d.get("affo_medida") and d.get("affo_detalle") and d.get("affo_fuentes"), f"{tk}: AFFO de 12 meses cargado con medida, detalle y fuente")
chk(ffo["WELL"].get("affo_no_informa") and not ffo["WELL"].get("affo_payout_12m"), "WELL: no informa AFFO, queda anotado y sin número")
rp = V1.calcular(e(grupo="REITs", affo_payout=78.9))
chk(v(rp, "affo")["pts"] == 20 and abs(v(rp, "affo")["valor"] - 78.9) < 1e-9, "REIT: payout de AFFO de la empresa (dividendos ÷ AFFO, 12 meses) 78,9 %: seguro")
rp = V1.calcular(e(grupo="REITs", affo_payout=85.0, affo=1.0))
chk(v(rp, "affo")["pts"] == 10, "REIT: el payout informado manda sobre dividendo anual ÷ AFFO por acción")
import calibrar_dividendo as C  # noqa: E402
src = open(C.__file__, encoding="utf-8").read()
chk("FFO (provisorio)" not in src.split("def calcular_todo")[1].split("def main")[0], "calibrar: sin FFO provisorio")

c1 = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cet1_bancos.json"), encoding="utf-8"))["datos"]
chk(len([x for x in c1.values() if x.get("cet1")]) >= 20, "CET1 cargado para 20 bancos o más")
for tk, x in c1.items():
    if x.get("no_aplica") or x.get("pendiente"):
        chk(x.get("motivo") or x.get("pendiente"), f"{tk}: sin CET1 con motivo")
        continue
    chk(x.get("cet1") and x.get("hasta") and x.get("fuentes") and x.get("medida"), f"{tk}: CET1 con fecha, medida y fuente")
    if x["cet1"] <= 11:
        chk(x.get("requisito") or x.get("nota"), f"{tk}: CET1 de 11 % o menos con su requisito (o la nota de por qué falta)")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
