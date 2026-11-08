"""v1.5.47: «Atrás · Inicio», tablas de Ideas como la principal, estados financieros visuales con subsolapas, barra de mercados centrada, datos del 08/11."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
import pandas as pd
from ui import marca as M, ideas as I, ficha as F, estados_visual as EV, mercados as MK
from data import paquetes_yahoo as PY
n = M.nav_html("?pagina=ideas")
chk("Atrás" in n and "Inicio" in n and 'href="?pagina=ideas"' in n and 'href="?inicio=0"' in n and "<svg" in n, "Atrás (con su página madre) e Inicio, con flechita y casita")
chk("#1d4ed8" in M.CSS_NAV and "history.back()" in M.SCRIPT_ATRAS and "location.origin" in M.SCRIPT_ATRAS, "en azul; Atrás usa el historial solo dentro del sitio")
app = open("app.py", encoding="utf-8").read()
chk("{SCRIPT_ATRAS}" in app and "if en_quienes or en_cartera or en_ideas or en_mapa:" in app and 'class="emp-vol">{nav_html(' in app, "Atrás · Inicio en todas las páginas")
chk("Volver al inicio</a>" not in app and ">← Volver a" not in app, "sin los «Volver» viejos")
df = pd.DataFrame(json.load(open("data/cache_datos.json", encoding="utf-8"))["data"])
L = I.cargar_listas()
al = I.miembros("altos", df, listas=L)
h = I.lista_html("altos", al, L, orden="dy", asc=True)
chk("id-c-tipo" in h and "Empresa" in h and "data-tip=" in h and "&orden=nombre&dir=asc" in h, "altos: columna Tipo, ayudas y orden por título")
o = I.ordenar(al, "dy", True)
chk([x["dy"] for x in o] == sorted(x["dy"] for x in o), "ordenar de menor a mayor")
chk("id-c-tipo" not in I.lista_html("reyes", I.miembros("reyes", df, listas=L), L), "Tipo solo donde hay ETFs")
chk("#d3e6fa" in I.CSS and "text-align:center" in I.CSS, "títulos celestes y centrados como la tabla principal")
P = PY.cargar()[0]
chk(len(P) == 323 and all(v.get("estados") for v in P.values()), "estados de las 323 empresas")
chk(len(json.load(open("data/fichas.json", encoding="utf-8"))["datos"]) == 323, "fichas de las 323")
chk([k for k, _, _ in F.PARTES_ESTADOS] == ["resultados", "balance", "flujo", "ratios"], "subsolapas en orden")
for k in ("resultados", "balance", "flujo"):
    g = EV.graficos_html(P["KO"]["estados"], k)
    chk(g.count('class="ev-t"') == 6, f"KO {k}: 6 gráficos")
chk("coronas danesas" in EV.graficos_html(P["NVO"]["estados"], "flujo"), "moneda de origen en el título del gráfico")
chk(EV.series(P["KO"]["estados"])[2]["crec"].get(EV.series(P["KO"]["estados"])[1]) is None, "sin barra de 12 meses en el crecimiento")
chk("ev-grid" in F.tab_estados_parte(P["KO"]["estados"], "balance") and "Balance" in F.tab_estados_parte(P["KO"]["estados"], "balance"), "subsolapa con gráficos y tabla")
chk("{_ficha.tab_estados_parte(" not in app and "_ficha.tab_estados_parte(_est, _k, ticker=tk)" in app, "la ficha arma las subsolapas")
chk("align-items:center;text-align:center" in open("ui/mercados.py", encoding="utf-8").read(), "barra de mercados centrada")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
