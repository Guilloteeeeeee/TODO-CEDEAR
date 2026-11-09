"""v1.5.52: explicación de cada solapa al pasar el mouse (hacia arriba), definiciones por subsolapa de Estados, «Ideal: más de X», score centrado,
solapa Análisis Fundamental solo en los ETFs con informe, ROIC con el capital invertido arreglado y carga sin esperas a Yahoo."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from ui import tabla_visual as TV, ficha as F, etfs as UE
css = TV.css_ayuda_solapas("sol_x", ["Uno \"dos\"", "", "Tres"])
chk("@media (hover:hover)" in css and 'nth-child(1):hover::after{content:"Uno \\"dos\\""' in css and "nth-child(2)" not in css and "nth-child(3)" in css,
    "un globito por solapa con texto, solo con mouse")
chk("bottom:calc(100% + 8px)" in css, "el globito sale hacia arriba")
chk('[role="tablist"]{overflow:visible!important}' in css and '[role="tablist"]:hover{z-index:60!important}' in css, "no lo recorta la barra ni lo tapa el encabezado")
chk(".st-key-sol_x .fch-intro{display:none}" in css, "con mouse se esconde el texto fijo de arriba (en el celular sigue)")
chk(set(F.INTROS_ESTADOS) == {k for k, _t, _c in F.PARTES_ESTADOS} and all("Pasá el mouse" in v for v in F.INTROS_ESTADOS.values()), "cada subsolapa de Estados tiene su definición")
chk("Pasá el mouse" not in F.INTROS["estados"], "la explicación general de Estados ya no repite lo de cada parte")
chk('class="fch-intro"' in F.con_intro_estados("balance", "<p>x</p>"), "en el celular, la definición va arriba de cada subsolapa")
app = open("app.py", encoding="utf-8").read()
chk('css_ayuda_solapas("sol_emp"' in app and 'st.container(key="sol_emp")' in app and 'css_ayuda_solapas("sol_est"' in app and 'css_ayuda_solapas("sol_etf"' in app,
    "empresa, subsolapas de Estados y ETF con sus globitos")
chk(app.index('css_ayuda_solapas("sol_emp"') < app.index('css_ayuda_solapas("sol_est"'), "el CSS de las subsolapas va después (gana a igual especificidad)")
chk('"analisis": "Análisis Fundamental"' in app and '(["analisis"] if _con_af else [])' in app, "ETF: solapa Análisis Fundamental solo si tiene informe")
src_f = open("ui/ficha.py", encoding="utf-8").read()
chk(".af-rs>.af-rt{flex:0 1 760px" in src_f and ".af-rs>.af-sc{flex:1 1 190px;align-self:center" in src_f, "score de calidad centrado entre el texto y el borde")
# ROIC con capital invertido roto (ASML, 12 meses: Yahoo trae solo la deuda)
from data import yahoo_extra as YX, paquetes_yahoo as PY, af_tablas as T
chk(YX.capital_invertido(1963e6, 1963e6, 22064e6) == 1963e6 + 22064e6 and YX.capital_invertido(24e9, 4.4e9, 19.6e9) == 24e9, "capital invertido: arregla solo el roto")
chk(YX.capital_invertido(5e9, 10e9, -2e9) == 5e9, "con patrimonio negativo no se toca")
P = PY.cargar()[0]
r = T._serie(YX.reparar_roic(P["ASML"]["estados"]), "ratios", "Retorno sobre el capital invertido (ROIC)")
chk(r.get("2026 (TTM)") is not None and r["2026 (TTM)"] < 1, f"ASML: ROIC de 12 meses razonable ({r.get('2026 (TTM)')})")
chk(T._serie(YX.reparar_roic(P["AAPL"]["estados"]), "ratios", "Retorno sobre el capital invertido (ROIC)") == T._serie(P["AAPL"]["estados"], "ratios", "Retorno sobre el capital invertido (ROIC)"),
    "AAPL: sin cambios")
chk("res[\"estados\"] = _yx.reparar_roic(res[\"estados\"])" in app and "_yx.reparar_roic(estados)" in src_f, "se aplica en la ficha y en Competidores")
# rapidez
chk("def _precios_ars(items: tuple, esperar: float = 4.0)" in app and '_swr.obtener(("ars", items)' in app, "precios en pesos: sin esperar la bajada (segundo plano)")
chk("esperar=(1.0 if hay_guardado else 40.0)" in app and '_swr.obtener(k_hist, lambda: _hp.bajar(ticker), 1800, esperar=8.0' in app, "empresa: no espera a Yahoo si tiene su paquete guardado")
chk('memo[("falla",) + k] = time.time()' in app, "foto del CEO: un fallo no se reintenta en cada visita")
nt = open("ui/noticias.py", encoding="utf-8").read()
chk("timeout=0.3 if viejo is not None else espera_s" in nt, "noticias: salen las guardadas mientras se renuevan")
from data import swr
import time as _t
swr.olvidar()
lento = lambda: (_t.sleep(1.0), {"a": 1})[1]
t0 = _t.time(); swr.obtener("x", lento, 60, esperar=0, vacio=None); chk(_t.time() - t0 < 0.3, "esperar=0 no frena")
_t.sleep(1.2); chk(swr.obtener("x", lento, 60, esperar=0, vacio=None) == {"a": 1}, "lo bajado en segundo plano queda para la visita siguiente")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
