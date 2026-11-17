"""v1.5.78 (decisiones de Guille del 17/11/2026): medio premio con aumentos simbólicos (menos de 1,5 % por año en 3 años), tope 99,
pago futuro de las utilities con su propio corte (70 / 80) y FFO ÷ Deuda publicado por la empresa."""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


from scoring import dividendo_v1 as V1  # noqa: E402

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def entrada(grupo="Industrial", racha=30, tasas=None, eps=4.0, est_g=None, ffo_sp=None, cfo=3e9, deuda=15.6e9):
    fila = lambda n, v: [n, list(v) if isinstance(v, (list, tuple)) else [v] * len(AN), "m"]  # noqa: E731
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8),
                                                  fila("Ingresos", (3.3e10, 3.2e10, 3.1e10, 3.0e10, 2.8e10)), fila("Resultado neto", 4e9),
                                                  fila("Ganancia por acción (diluida)", eps)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", deuda), fila("Caja e inversiones de corto plazo", 9.3e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 4e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", cfo)]}}
    tasas = tasas or {2022: 6.60, 2023: 6.64, 2024: 6.68, 2025: 6.72}
    hist = {"racha_subas": racha, "anios_sin_suba": 0, "recortes": [], "ultimo_completo": 2025, "tasa": tasas, "anios_sin_recorte": racha}
    e = {"grupo": grupo, "estados": est, "dividendo_anual": 2.4, "historial": hist, "fuente_historial": "dolares"}
    if est_g is not None:
        e["estimacion"] = est_g
    if ffo_sp is not None:
        e["ffo_deuda_sp"] = ffo_sp
    return e


def var(r, clave):
    return next((v for v in r["variables"] if v["clave"] == clave), None)


# --- 1) aumentos simbólicos: medio premio --------------------------------------------------------------------------------------
r = V1.calcular(entrada())                                               # 6,60 → 6,72 en 3 años = 0,6 % por año (IBM)
chk(("aristocrata", 5) in r["ajustes"], f"aristócrata con aumentos de un centavo: +5 ({r['ajustes']})")
chk(any("aumentos simbólicos" in n for n in r["notas"]), "lo anota")
r = V1.calcular(entrada(tasas={2022: 2.00, 2023: 2.10, 2024: 2.20, 2025: 2.31}))   # 4,9 % por año
chk(("aristocrata", 10) in r["ajustes"] and not any("simbólicos" in n for n in r["notas"]), "aumentos normales: premio entero")
r = V1.calcular(entrada(racha=15))
chk(("aspirante", 2.5) in r["ajustes"], f"aspirante con aumentos simbólicos: +2,5 ({r['ajustes']})")
r = V1.calcular(entrada(racha=15, tasas={2022: 2.00, 2023: 2.03, 2024: 2.06, 2025: 2.0918}))   # 1,5 % justo: no es simbólico
chk(("aspirante", 5) in r["ajustes"], f"1,5 % justo: premio entero ({r['ajustes']})")
r = V1.calcular(entrada(tasas={2024: 6.68, 2025: 6.72}))                 # sin 3 años de historia: no se puede medir, premio entero
chk(("aristocrata", 10) in r["ajustes"], "sin la serie de 3 años no se castiga")
chk(V1.CRECIMIENTO_SIMBOLICO == 1.5 and V1.CRECIMIENTO_ANIOS == 3, "constantes 1,5 % y 3 años")

# --- 2) tope 99 -----------------------------------------------------------------------------------------------------------------
r = V1.calcular(entrada(tasas={2022: 2.00, 2023: 2.10, 2024: 2.20, 2025: 2.31}))
chk(r["score"] <= 99 and V1.TOPE_SCORE == 99, f"tope 99 ({r['score']})")

# --- 3) utilities: pago futuro con corte 70 / 80 ----------------------------------------------------------------------------------
g = {"actual": 3.6, "proximo": 3.6}                                       # 2,40 ÷ 3,60 = 66,7 %
for gr, esperado in (("Utilities", 15), ("Industrial", 7)):
    r = V1.calcular(entrada(grupo=gr, est_g=g))
    pf = var(r, "payout_futuro")
    chk(pf is not None and abs(pf["valor"] - 66.67) < 0.1 and pf["pts"] == esperado, f"{gr}: pago futuro de 66,7 % → {esperado} ({pf})")
g = {"actual": 2.9, "proximo": 2.9}                                       # 82,8 %: crítica en los dos
r = V1.calcular(entrada(grupo="Utilities", est_g=g))
chk(var(r, "payout_futuro")["pts"] == 0, "utilities: más de 80 % → crítica")
src = open(os.path.join(RAIZ, "scoring", "dividendo_v1.py"), encoding="utf-8").read()
chk('var("payout_futuro", _zona(fp, (70, False), (80, False), (15, 7, 0), True), 15, fp)' in src, "corte 70 / 80 para utilities en el código")

# --- 4) FFO ÷ Deuda publicado por la empresa -------------------------------------------------------------------------------------
r = V1.calcular(entrada(grupo="Utilities", ffo_sp={"ffo_deuda": 19.4, "anio": 2025}))
f = var(r, "ffo_deuda")
chk(f["valor"] == 19.4 and f["pts"] == 10 and f.get("fuente") == "empresa", f"usa el de la empresa ({f})")
r = V1.calcular(entrada(grupo="Utilities"))
f = var(r, "ffo_deuda")
chk(abs(f["valor"] - 3e9 / 15.6e9 * 100) < 0.01 and f.get("fuente") == "app", f"sin dato de la empresa, la cuenta de la app ({f})")
fd = json.load(open(os.path.join(RAIZ, "data", "ffo_deuda_utilities.json"), encoding="utf-8"))["datos"]
chk(fd["NEE"]["ffo_deuda"] == 19.4 and fd["NEE"]["fuentes"], "NEE 19,4 % con fuente")
chk(fd["NGG"]["ffo_deuda"] == 13.0 and "No es la cifra de S&P" in fd["NGG"]["medida"], "NGG 13,0 % y aclara que no es la de S&P")
chk(V1.ffo_deuda_sp("NEE")["ffo_deuda"] == 19.4 and V1.ffo_deuda_sp("CEG") is None and V1.ffo_deuda_sp("KEP") is None, "lector")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
