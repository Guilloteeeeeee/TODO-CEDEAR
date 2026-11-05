"""v1.5.29: variación del día junto al precio, mapa de calor, noticias en 3 columnas desde arriba, buscador en su lugar, LAC sin ADR. Correr: python tests/test_v1529_variacion_mapa.py"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from data import precios_vivos as pv
from ui import mapa_calor as M
from ui import tabla_visual as T
from ui import etfs as E
from ui import marca as MA
from config import mercados as CM

ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)

# --- variacion junto al precio
chk(T.var_html(None) == "" and T.var_html(float("nan")) == "", "sin dato no se muestra nada")
chk("+1,2%" in T.var_html(1.234) and "#0a7a3a" in T.var_html(1.234), "suba en verde con coma")
chk("-0,8%" in T.var_html(-0.84) and "#c62828" in T.var_html(-0.84), "baja en rojo")
chk("0,0%" in T.var_html(0.01) and "#64748b" in T.var_html(0.01), "sin cambios en gris")
chk("+1,2%" in T._celda_precio({"precio_actual": 100.0, "var_dia": 1.2}), "la celda de precio de la tabla trae la variación")
chk("vd" not in T._celda_precio({"precio_actual": 100.0}), "la celda sin variación queda como antes")
chk("-2,0%" in E._fila({"ticker": "SPY", "nombre": "SPDR"}, {}, 500.0, -2.0), "fila de ETF con variación")
chk("vd" not in E._fila({"ticker": "SPY", "nombre": "SPDR"}, {}, 500.0), "fila de ETF sin variación")
chk("+0,5%" in E.encabezado_etf({"ticker": "SPY", "nombre": "SPDR"}, {}, 500.0, None, 0.5), "encabezado de ETF con variación")

# --- datos: variacion = ultimo cierre contra el anterior
idx = pd.to_datetime(["2026-11-02", "2026-11-03", "2026-11-04"])
df_y = pd.DataFrame({"Close": [100.0, 102.0, 99.96]}, index=idx)
r = pv._leer_descarga(df_y, ["AAA"])
chk(r["AAA"][0] == 99.96 and r["AAA"][2] == -2.0, f"variación de Yahoo -2,0% ({r})")
chk(pv.fecha_mas_comun(r) is not None, "fecha más común con tuplas de 3")
one = pd.DataFrame({"Close": [50.0]}, index=idx[:1])
chk(pv._leer_descarga(one, ["AAA"])["AAA"][2] is None, "con una sola barra no hay variación (no se inventa)")
html_sa = '<div class="text-4xl font-bold">$205.20</div><div>205.20 +3.10 (1.53%) At close: Nov 4, 2026, 4:00 PM EDT</div>'
r_sa = pv.parsear_precio_sa(html_sa)
chk(r_sa and r_sa[0] == 205.2 and r_sa[2] == 1.53, f"Stock Analysis trae la variación ({r_sa})")
html_sa2 = '<div class="text-4xl font-bold">$205.20</div><div>205.20 -3.10 (-1.49%) At close: Nov 4, 2026, 4:00 PM EDT</div>'
chk(pv.parsear_precio_sa(html_sa2)[2] == -1.49, "Stock Analysis con baja")
base = pd.DataFrame({"ticker": ["AAA", "BBB"], "precio_actual": [100.0, 50.0], "market_cap": [1e9, 2e9], "dividend_yield_actual": [1.0, 2.0],
                     "precio_min_52s": [80.0, 40.0], "precio_max_52s": [120.0, 60.0]})
d2, n2 = pv.aplicar_precios(base, {"AAA": 101.0, "BBB": 49.0}, None, "10:00", None, {"AAA": 1.0})
chk(n2 == 2 and d2.loc[0, "var_dia"] == 1.0 and pd.isna(d2.loc[1, "var_dia"]), "var_dia por empresa; sin dato queda vacía")
d3, _ = pv.aplicar_precios(base, {"AAA": 101.0}, None, "10:00")
chk("var_dia" in d3.columns and pd.isna(d3.loc[0, "var_dia"]), "sin var la columna existe y está vacía")

# --- mapa de calor
rects = M.squarify([6, 6, 4, 3, 2, 2, 1], 0, 0, 100, 56)
chk(len(rects) == 7, "un rectángulo por valor")
area = sum(w * h for _, _, w, h in rects)
chk(abs(area - 100 * 56) < 1e-6, f"las áreas llenan el mapa ({area})")
chk(all(x >= -1e-9 and y >= -1e-9 and x + w <= 100 + 1e-9 and y + h <= 56 + 1e-9 for x, y, w, h in rects), "nada se sale del mapa")
sup = False
for i, a in enumerate(rects):
    for b in rects[i + 1:]:
        if min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]) > 1e-6 and min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]) > 1e-6:
            sup = True
chk(not sup, "ningún recuadro se superpone")
chk(M.squarify([], 0, 0, 10, 10) == [], "lista vacía")
chk(M.color_var(None) == M.SIN_DATO and M.color_var(float("nan")) == M.SIN_DATO, "sin dato: gris")
chk(M.color_var(-5) == M.color_var(-3) == "#f63538" and M.color_var(9) == M.color_var(3) == "#30cc5a", "tope de color en ±3%")
chk(M.color_var(0) == "#414554", "0% gris oscuro")
items = [{"tk": "AAA", "nombre": "Aaa Inc", "grupo": "Tecnología", "tam": 1e12, "var": -3.1, "precio": 100.0, "href": "?empresa=AAA"},
         {"tk": "BBB", "nombre": "Bbb", "grupo": "Tecnología", "tam": 2e11, "var": 1.0, "precio": 20.0, "href": "?empresa=BBB"},
         {"tk": "CCC", "nombre": "Ccc", "grupo": "Salud", "tam": 5e11, "var": None, "precio": 5.0, "href": "?empresa=CCC"},
         {"tk": "ZZZ", "nombre": "Sin tamaño", "grupo": "Salud", "tam": None, "var": 1.0, "precio": 5.0, "href": "?empresa=ZZZ"}]
h = M.mapa_html(items, "Mapa de Calor de empresas", "empresas", texto_precios="05/11/2026 (17:58)")
chk(h.count('class="mpc-t"') == 6, f"3 empresas con tamaño × 2 versiones (compu y celular) = 6 ({h.count('class=\"mpc-t\"')})")
chk("ZZZ" not in h, "sin tamaño no se dibuja (no se inventa)")
chk('href="?empresa=AAA"' in h and "Tecnología" in h and "Salud" in h, "links y sectores")
chk("-3,1%" in h and "s/d" in h, "variación escrita; sin dato dice s/d")
chk(M.SIN_DATO in h, "gris para el que no tiene variación")
chk("no es una recomendación" in h or "no una recomendación" in h, "aviso de información")
chk("05/11/2026 (17:58)" in h, "fecha de los datos")
chk("no pudimos traer la variación" in M.mapa_html(items, "x", "empresas", hay_var=False), "aviso cuando Yahoo no trae variación")
chk("Todavía no hay datos" in M.mapa_html([], "x", "etfs"), "mapa vacío no rompe")
dfm = pd.DataFrame({"ticker": ["AAA", "BBB"], "nombre": ["A", "B"], "sector": ["Tecnología", "Salud"], "market_cap": [5e9, 3e9], "precio_actual": [10.0, 20.0], "var_dia": [1.5, float("nan")]})
ie = M.items_empresas(dfm)
chk(ie[0]["var"] == 1.5 and ie[1]["var"] is None and ie[0]["href"] == "?empresa=AAA", "items de empresas")
ietf = M.items_etfs([{"ticker": "SPY", "nombre": "SPDR", "categoria": "USA"}], {"SPY": {"aum": 5e11, "precio": 500.0}}, {}, {"SPY": -0.5})
chk(ietf[0]["tam"] == 5e11 and ietf[0]["var"] == -0.5 and ietf[0]["href"] == "?etf=SPY" and ietf[0]["precio"] == 500.0, "items de ETFs")
chk("Mapa de Calor" in MA.menu_lista_html(home=True) and "?pagina=mapa" in MA.menu_lista_html(home=False), "el menú lleva al mapa")

# --- buscador en su lugar y noticias desde arriba en 3 columnas
chk("__BTOP__" not in MA.CSS and "__NTOP__" not in MA.CSS and "__FTOP__" not in MA.CSS, "no quedan marcas sin reemplazar")
chk(re.search(r"\.st-key-buscador\{position:absolute;top:148px;left:196px", MA.CSS) is not None, "buscador: arriba a la izquierda, no al extremo")
chk("nt-baja" in MA.CSS and "repeat(3,minmax(0,1fr))" in MA.CSS, "panel de noticias desde arriba en 3 columnas")
chk("CSS" in dir(MA) and "left:32px;right:32px" in MA.CSS, "el panel de noticias cubre casi todo el ancho")

import datetime as dt
from ui import noticias as N
_ah = dt.datetime(2026, 11, 5, 20, tzinfo=dt.timezone.utc)
def _nt(t, medio):
    return {"titulo": t, "link": "https://x/" + t.replace(" ", "_"), "clave": medio + t, "fecha": _ah - dt.timedelta(hours=1), "medio": medio, "idioma": "es"}
_bl = [{"clave": k, "titulo": k.title(), "fuente": "x", "respondio": True,
        "notas": [{"titulo": f"Nota de prueba {k}", "link": "https://x/" + k, "fecha": _ah, "fuente": "Ámbito"}]} for k in ("locales", "usa", "mundo")]
_h = N.noticias_bloques_html(_bl, ahora=_ah)
chk(_h.count('class="nt-col"') == 3 and 'class="nt-g"' in _h, f"noticias: 3 columnas ({_h.count('class=\"nt-col\"')})")

# --- LAC
chk("Mapa de Calor</a>" in MA.links_html("empresas", home=True) and MA.links_html("empresas", home=True).index("Mapa de Calor") < MA.links_html("empresas", home=True).index("Noticias"), "franja negra: Mapa de Calor a la izquierda de Noticias")
chk("LAC" in CM.NO_ADR, "LAC es acción ordinaria")

# --- v1.5.32: resumen de FISV a mano (Yahoo no lo trae) y «Volver» + buscador en una fila
from data import fichas as FI
_d, _f = FI.cargar()
chk(len(_d["FISV"].get("descripcion_es", "")) > 200 and "Clover" in _d["FISV"]["descripcion_es"], "FISV tiene resumen")
chk(_d["FISV"].get("mercado_nombre") == "NasdaqGS", "lo manual completa, no pisa lo de Yahoo")
_t = {"AAA": {"descripcion_es": "de Yahoo"}}
FI._con_manuales(_t, archivo=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "fichas_manuales.json"))
chk(_t["AAA"]["descripcion_es"] == "de Yahoo" and "FISV" in _t, "un dato de Yahoo no se pisa")
chk(all(len(v.get("descripcion_es", "")) > 50 for v in _d.values()), "todas las empresas tienen resumen")
chk("st-key-fila_volver" in MA.CSS and "flex:0 0 auto!important" in MA.CSS, "estilo de la fila Volver + buscador")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app.py"), encoding="utf-8").read()
chk("def render_fila_volver" in _src and _src.count('class="emp-vol"') == 2, "el Volver se dibuja solo en render_fila_volver (empresa y ETF)")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
