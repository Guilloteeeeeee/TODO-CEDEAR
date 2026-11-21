"""v1.5.80: consolidaciones de acciones que mantienen comparable el dividendo por acción después de una escisión (Unilever 2025, The Magnum
Ice Cream Company) o de un dividendo extraordinario (National Grid 2017). Yahoo las anota como split y el dividendo de después parecía un
recorte."""
import datetime as dt
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


from data import historico as H, moneda_dividendo as MD  # noqa: E402

# --- 1) cada consolidación de la tabla tiene el mismo factor que el archivo de splits, motivo y fuente ---------------------------------
splits = H.leer("splits.json", {})
for tk, lista in MD.CONSOLIDACIONES_COMPARABLES.items():
    for fecha, factor, motivo, fuente in lista:
        guardado = [f for d, f in splits.get(tk, []) if d == fecha]
        chk(guardado == [factor], f"{tk} {fecha}: factor {factor} igual al del archivo de splits ({guardado})")
        chk(motivo and fuente, f"{tk}: motivo y fuente")

# --- 2) se deshace el ajuste solo antes de la fecha ----------------------------------------------------------------------------------
p = MD.sin_consolidacion("UL", [["2025-11-07", 0.5625], ["2026-02-27", 0.555]])
chk(abs(p[0][1] - 0.5625 * 0.888) < 1e-9 and p[1][1] == 0.555, f"antes × factor, después igual ({p})")
chk(MD.sin_consolidacion("KO", [["2020-01-01", 1.0]]) == [["2020-01-01", 1.0]], "las demás no cambian")

# --- 3) Unilever: el dividendo trimestral sube 3 % (0,4528 → 0,4664 euros), no baja ----------------------------------------------------
# pagos en dólares con el ajuste que hizo el archivo (÷ 0,888 antes del 9/12/2025) y tipo de cambio fijo para no mezclar efectos
ajustado = lambda m: m / 0.888  # noqa: E731
pagos = [[f"{a}-{m:02d}-15", ajustado(0.4396 if a == 2024 else 0.4528) * 1.15] for a in (2024, 2025) for m in (2, 5, 8, 11)]
pagos += [[f"2026-{m:02d}-15", 0.4664 * 1.15] for m in (2, 5, 8)]
h, fuente = MD.historial("UL", "USD", pagos, hoy=dt.date(2026, 11, 21), sigue_pagando=True)
chk(not h.get("recorte_en_curso") and 2026 not in h["recortes"], f"Unilever sin recorte en 2026 ({h['recortes']}, en curso {h.get('recorte_en_curso')})")
h, _ = MD.historial("XX", "USD", pagos, hoy=dt.date(2026, 11, 21), sigue_pagando=True)
chk(h.get("recorte_en_curso"), "con el ajuste de Yahoo sin deshacer, parecía un recorte (control de la prueba)")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
