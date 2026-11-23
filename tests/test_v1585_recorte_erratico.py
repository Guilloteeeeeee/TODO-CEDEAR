"""v1.5.85 (Guille 23/11/2026: «el recorte no debería restar aparte en los dividendos erráticos, sino castiga doble. A partir de ahora si
hay divi errático y recorte castiga el que reste más puntos de los 2»): con dividendo errático (o variable) y recorte, cuenta solo el
castigo que resta más; el puntaje es el mismo que dejar el recorte y después el techo de 80, y una nota dice cuál contó."""
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


def entrada(tasa, recortes=(), fcf=4e9, deuda=1.5e10, racha=0, sin_suba=0, tk=None):
    fila = lambda n, v: [n, [v] * len(AN), "m"]  # noqa: E731
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8),
                                                  fila("Ingresos", 3e10), fila("Resultado neto", 4e9), fila("Ganancia por acción (diluida)", 4.0)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", deuda), fila("Caja e inversiones de corto plazo", 9e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", fcf), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 5e9)]}}
    hist = {"racha_subas": racha, "anios_sin_suba": sin_suba, "recortes": list(recortes), "ultimo_completo": 2025, "tasa": tasa,
            "anios_sin_recorte": 10}
    return {"grupo": "Industrial", "estados": est, "dividendo_anual": 2.4, "historial": hist, "fuente_historial": "dolares", "ticker": tk}


def aj(r):
    return dict(r["ajustes"])


def nota(r):
    return next((n for n in r["notas"] if "cuenta el que resta más" in n), "")


plano = lambda desde, hasta, v=1.0: {a: v for a in range(desde, hasta + 1)}  # noqa: E731
congelado = {2019: 0.9, **plano(2020, 2023), 2024: 1.1, 2025: 1.2}        # congelado de 2020 a 2023: errático

# --- 1) base alta y recorte chico: pesa más el techo ---------------------------------------------------------------------------------
r = V1.calcular(entrada(congelado, recortes=[2018], racha=2))
base = r["base"]
chk(r["erratico"] and base > 90, f"empresa sana con dividendo errático (base {base})")
chk("recorte_5_10" not in aj(r) and r["score"] == 80, f"recorte de hace 7 años (−10) contra techo (−{base - 80:.0f}): solo el techo, 80 ({r['score']}, {r['ajustes']})")
chk("el techo de 80" in nota(r) and "restaría" not in nota(r), f"la nota dice que contó el techo ({nota(r)})")

# --- 2) recorte grande: pesa más el recorte y el techo no actúa ------------------------------------------------------------------------
r = V1.calcular(entrada(congelado, recortes=[2024], racha=1))
chk(r["erratico"] and aj(r).get("recorte_menos_5") == -25, f"recorte de hace 1 año (−25) queda ({r['ajustes']})")
chk(r["score"] == round(min(r["base"] - 25, V1.TOPE_SCORE)), f"puntaje = base − 25, sin el techo encima ({r['base']} → {r['score']})")
chk("el recorte" in nota(r), f"la nota dice que contó el recorte ({nota(r)})")

# --- 3) nunca se suman: el puntaje es base menos el mayor de los dos -----------------------------------------------------------------
for rec, castigo in (([2018], 10), ([2024], 25)):
    for fcf in (4e9, 2e9, 1.3e9):
        r = V1.calcular(entrada(congelado, recortes=rec, fcf=fcf, racha=1))
        b = r["base"]
        esperado = round(b - max(castigo, max(0, b - 80)))
        chk(r["score"] == esperado, f"base {b}, recorte −{castigo}: {esperado} ({r['score']})")
        chk(r["score"] >= round(min(b, 80)) - castigo, f"no castiga doble (base {b}, recorte −{castigo}: {r['score']})")

# --- 4) sin errático, el recorte resta como siempre ----------------------------------------------------------------------------------
sube = {a: 1.0 + 0.1 * (a - 2015) for a in range(2015, 2026)}
r = V1.calcular(entrada(sube, recortes=[2018], racha=7))
chk(not r["erratico"] and aj(r).get("recorte_5_10") == -10 and not nota(r), f"sin errático: −10 como siempre ({r['ajustes']})")

# --- 5) dividendo variable declarado: misma regla ----------------------------------------------------------------------------------
tk = next(iter(V1.VARIABLE_DECLARADA))
r = V1.calcular(entrada(sube, recortes=[2018], racha=7, tk=tk))
chk(r["variable"] and not r["erratico"] and r["score"] == 80 and "recorte_5_10" not in aj(r), f"{tk} (variable declarado): solo el techo ({r['ajustes']}, {r['score']})")
chk("dividendo variable" in nota(r), f"la nota dice variable ({nota(r)})")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
