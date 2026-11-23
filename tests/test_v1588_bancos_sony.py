"""v1.5.88 (Guille 23/11/2026): «bancos, opción B»: donde hay CET1, ganancias retenidas ÷ activos no se usa (el CET1 ya mide el capital);
«Sony, vamos con la B»: si la pérdida del último año fiscal viene de operaciones discontinuadas y las que siguen ganaron, no hay freno por
pérdida (fila «Resultado de operaciones continuas» de Yahoo)."""
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
from data import yahoo_extra as YE  # noqa: E402

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def entrada(grupo="Industrial", neto=4e9, continuas=None, cet1=None):
    fila = lambda n, v: [n, [v] * len(AN), "m"]  # noqa: E731
    res = [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8), fila("Ingresos", 3e10),
           fila("Resultado neto", neto), fila("Ganancia por acción (diluida)", 4.0 if neto > 0 else -1.0)]
    if continuas is not None:
        res.append(fila("Resultado de operaciones continuas", continuas))
    est = {"resultados": {"anios": AN, "filas": res},
           "balance": {"anios": AN, "filas": [fila("Deuda total", 1.5e10), fila("Caja e inversiones de corto plazo", 9e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9),
                                               fila("Ganancias retenidas", 4e9)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 4e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 5e9)]}}
    hist = {"racha_subas": 3, "anios_sin_suba": 0, "recortes": [], "ultimo_completo": 2025, "tasa": {a: 1 + 0.05 * (a - 2020) for a in range(2020, 2026)},
            "anios_sin_recorte": 10}
    return {"grupo": grupo, "estados": est, "dividendo_anual": 2.4, "historial": hist, "fuente_historial": "dolares", "cet1": cet1}


claves = lambda r: {v["clave"] for v in r["variables"]}  # noqa: E731

# --- bancos -------------------------------------------------------------------------------------------------------------------------
r = V1.calcular(entrada("Bancos y seguros", cet1=13.5))
chk("re_ta" not in claves(r) and any("CET1 ya mide su capital" in n for n in r["notas"]), f"banco con CET1: sin ganancias retenidas ÷ activos ({claves(r)})")
chk(any(v["clave"] == "cet1" and v["pts"] == 25 for v in r["variables"]), "el CET1 sigue contando")
r = V1.calcular(entrada("Bancos y seguros", cet1=None))
chk("re_ta" in claves(r), "financiera sin CET1 (administradora, broker, aseguradora sin índice): sigue la medida")
r = V1.calcular(entrada("Industrial"))
chk("re_ta" in claves(r), "una industrial sigue con la medida")

# --- pérdida por operaciones discontinuadas -----------------------------------------------------------------------------------------
r = V1.calcular(entrada(neto=-3e9, continuas=1e10))
chk(("perdida", 20) not in r["topes"] and any("operaciones discontinuadas" in n for n in r["notas"]), f"pérdida por discontinuadas y las que siguen ganan: sin freno ({r['topes']})")
r = V1.calcular(entrada(neto=-3e9, continuas=-1e9))
chk(("perdida", 20) in r["topes"], "las que siguen también pierden: freno")
r = V1.calcular(entrada(neto=-3e9))
chk(("perdida", 20) in r["topes"], "sin la fila de operaciones continuas: freno como siempre")
r = V1.calcular(entrada(neto=4e9, continuas=4e9))
chk(("perdida", 20) not in r["topes"], "sin pérdida: nada cambia")

# --- la fila se baja de Yahoo y no se muestra en la ficha ----------------------------------------------------------------------------
filas = [f[0] for f in YE.ESTADOS["resultados"][1]]
chk("Resultado de operaciones continuas" in filas, "Yahoo baja la fila de operaciones continuas")
from ui import ficha as F  # noqa: E402
chk("Resultado de operaciones continuas" in F.SOLO_SCORE, "la fila no se muestra en la ficha")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
