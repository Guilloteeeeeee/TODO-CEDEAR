"""v1.5.91 — Versión 2 del score de dividendos (el Word puro con lo definido el 16/11) como modo de scoring/dividendo_v1.calcular.
python tests/test_v1591_version2.py  →  "OK n MAL 0"."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring import dividendo_v1 as V1  # noqa: E402

ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


# reusar la empresa de ejemplo de la prueba del v1 sin correr sus controles
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_v1571_score_v1.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_v1571_score_v1.py")}
exec(src.split("# 1) empresa sana")[0], ns)
e, est, v = ns["e"], ns["est"], ns["v"]

# 1) empresa sana: la versión 3 topa en 99, la 2 llega a 100 (base 100 + aspirante 5)
r3, r2 = V1.calcular(e()), V1.calcular(e(), version=2)
chk(r3["score"] == 99 and r2["score"] == 100, f"tope 99 solo en la versión 3: {r3['score']} {r2['score']}")

# 2) congelamiento vigente (3 años sin subir): v3 = errático (techo 80, sin premio); v2 = −5 y sin premio
h = {"recortes": [], "racha_subas": 0, "anios_sin_suba": 3, "ultimo_completo": 2025, "recorte_en_curso": False,
     "tasa": {2021: 1.0, 2022: 1.5, 2023: 1.5, 2024: 1.5, 2025: 1.5}}
r3, r2 = V1.calcular(e(historial=h)), V1.calcular(e(historial=h), version=2)
chk(("dividendo_variable", 80) in r3["topes"] and r3["score"] == 80, f"v3: congelado = techo 80 ({r3['score']}, {r3['topes']})")
chk(("congelamiento", -5) in r2["ajustes"] and not r2["topes"] and r2["score"] == 95, f"v2: congelado = −5 ({r2['score']}, {r2['ajustes']})")

# 3) recompras: v3 suma las de 10 años a las ganancias retenidas; v2 solo las acciones en tesorería
es = est(rr=500.0, tes=0.0)
es["flujo"]["filas"].append(["Recompra de acciones", [-300.0] * 5, "m"])
r3, r2 = V1.calcular(e(estados=es)), V1.calcular(e(estados=es), version=2)
chk(v(r3, "re_ta")["valor"] > v(r2, "re_ta")["valor"] and abs(v(r2, "re_ta")["valor"] - 10.0) < 0.01, f"re_ta v3 {v(r3, 're_ta')['valor']} v2 {v(r2, 're_ta')['valor']}")

# 4) bancos: v3 sin ganancias retenidas ÷ activos (con CET1); v2 con; pago futuro: v3 50/75, v2 el general 55/80
rb3 = V1.calcular(e(grupo="Bancos y seguros", cet1=12.0, dividendo_anual=2.1))
rb2 = V1.calcular(e(grupo="Bancos y seguros", cet1=12.0, dividendo_anual=2.1), version=2)
chk(v(rb3, "re_ta") is None and v(rb2, "re_ta") is not None, "bancos: ganancias retenidas solo en la versión 2")
chk(v(rb3, "payout_futuro")["pts"] == 7 and v(rb2, "payout_futuro")["pts"] == 15, f"banco con pago futuro 52 %: v3 gris, v2 segura")

# 5) utilities: v3 deuda 7,5 + FFO ÷ Deuda 7,5; v2 deuda 15 + FFO ÷ Deuda 10
ru3, ru2 = V1.calcular(e(grupo="Utilities")), V1.calcular(e(grupo="Utilities"), version=2)
chk(v(ru3, "deuda")["max"] == 7.5 and v(ru3, "ffo_deuda")["max"] == 7.5, "utilities v3: 7,5 + 7,5")
chk(v(ru2, "deuda")["max"] == 15 and v(ru2, "ffo_deuda")["max"] == 10, "utilities v2: 15 + 10")

# 6) aseguradoras: la solvencia solo en la versión 3
ra3 = V1.calcular(e(grupo="Bancos y seguros", solvencia=200.0))
ra2 = V1.calcular(e(grupo="Bancos y seguros", solvencia=200.0), version=2)
chk(v(ra3, "solvencia") is not None and v(ra2, "solvencia") is None and v(ra2, "cet1")["pts"] is None, "aseguradora: solvencia solo en v3")

# 7) errático + recorte: v3 «cuenta el que resta más», v2 aplica los dos. Da siempre el mismo número (si el techo resta más que el
#    recorte, el puntaje menos el recorte igual queda arriba de 80): la regla de la v1.5.85 solo cambia la explicación
for recs, base_esp in (([2016, 2019, 2023], 75), ([2016, 2018, 2020], 80)):
    h = {"recortes": recs, "racha_subas": 2, "anios_sin_suba": 0, "ultimo_completo": 2025, "recorte_en_curso": False}
    r3, r2 = V1.calcular(e(historial=h)), V1.calcular(e(historial=h), version=2)
    chk(r3["score"] == r2["score"] == base_esp and any("cuenta el que resta más" in n for n in r3["notas"]),
        f"errático + recorte {recs}: v3 {r3['score']} v2 {r2['score']}")

# 8) pérdida por operaciones discontinuadas: v3 sin freno, v2 con freno
es = est(neto=-10.0)
es["resultados"]["filas"].append(["Resultado de operaciones continuas", [50.0] * 5, "t"])
r3, r2 = V1.calcular(e(estados=es)), V1.calcular(e(estados=es), version=2)
chk(not r3["topes"] and ("perdida", 20) in r2["topes"], f"Sony: freno solo en v2 ({r3['topes']} / {r2['topes']})")

# 9) financiera propia y ventas comparables solo en v3; Welltower: el FFO como AFFO solo en v3
fp = {"anio": 2025, "ebit": 100.0, "intereses": 50.0}
chk(v(V1.calcular(e(financiera_propia=fp)), "cobertura")["valor"] == 2.0 and v(V1.calcular(e(financiera_propia=fp), version=2), "cobertura")["valor"] == 10.0,
    "financiera propia solo en v3")
rw3 = V1.calcular(e(grupo="REITs", affo=3.0, affo_es_ffo=True))
rw2 = V1.calcular(e(grupo="REITs", affo=3.0, affo_es_ffo=True), version=2)
chk(v(rw3, "affo")["pts"] is not None and v(rw2, "affo")["pts"] is None, "Welltower: FFO como AFFO solo en v3")

# 10) sin argumento = versión 3 (la app y la calibración de antes no cambian)
chk(V1.calcular(e()) == V1.calcular(e(), version=3), "por defecto, versión 3")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
