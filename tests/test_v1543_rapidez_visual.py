"""v1.5.43: generar_cache con tope por empresa y reanudación, barra de mercados que no frena, buscador del mapa en la fila del título,
noticias prolijas, casita «Volver al inicio», sin raya verde en Evalúa tu Portfolio, buscador del calendario chico."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
import data.fetcher as F
orig = F.fetch_ticker_data
def falso(t, m=None):
    if t.startswith("C"): time.sleep(3)
    return {"ticker": t, "precio": 1.0}
F.fetch_ticker_data, F.REQUEST_DELAY = falso, 0
df, info = F.fetch_all_tickers_seguro(["A", "C1", "B"], tope_seg=1, respaldo={"C1": {"ticker": "C1", "precio": 9.0}}, avisar=lambda *_: None)
chk(list(df["precio"]) == [1.0, 9.0, 1.0] and info["respaldo"] == ["C1"], "una empresa colgada usa su dato anterior y el resto sigue")
df, info = F.fetch_all_tickers_seguro(["A", "C1", "C2", "C3"], tope_seg=1, max_colgados=2, avisar=lambda *_: None)
chk(info["cortado"], "varias colgadas seguidas: deja de pedir")
F.fetch_ticker_data = orig
src = open("generar_cache.py", encoding="utf-8").read()
chk("fetch_all_tickers_seguro" in src and "cache_parcial.json" in src, "generar_cache usa la bajada segura y guarda el avance")
app = open("app.py", encoding="utf-8").read()
chk("_mk.obtener(esperar=0)" in app and "_arrancar_precios(universe_key)" in app, "barra y precios en paralelo, sin frenar la página")
chk('with st.container(key="fila_mapa")' in app and "nav_html(" in app, "buscador del mapa en la fila del título y «Atrás · Inicio» (v1.5.47)")
chk('render_nav_tablas("ambos")' not in app, "ya no van Empresas · ETFs en Evalúa tu Portfolio")
from ui import marca as MA, noticias as N, mapa_calor as MC
chk(".mc-lk.mc-eval.mc-on{box-shadow:none}" in MA.CSS and "#00e05a" not in MA.css_nav("cartera"), "sin raya verde en Evalúa tu Portfolio")
chk("st-key-cal_tk" in MA.CSS, "buscador del calendario chico")
h = N._fila({"titulo": "Hola", "link": "#", "fuente": "CNBC", "menciona": ["MSFT"]}, "CNBC")
chk('<div class="nt-pi">' in h and h.index("</a>") < h.index("nt-pi"), "noticias: medio y etiqueta debajo del título")
izq, der = MC.cabecera_html("Mapa de Calor de empresas", "empresas")
chk("mpc-sw" in izq and "mpc-leyenda" in der, "cabecera del mapa partida")
chk("mpc-w2" in MC.mapa_html([], "x", "empresas", sin_cabecera=True), "mapa sin cabecera propia")
lg = open("descargar_logos.py", encoding="utf-8").read()
chk("t not in SOLO_POR_DOMINIO" in lg, "ASML y SPCX se rehacen siempre")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
