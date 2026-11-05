"""v1.5.34: calendario de cuadraditos, globitos de columnas hacia abajo, índices solo con %, menú que se cierra con un segundo toque, mapa más prolijo. Correr: python tests/test_v1534_calendario_menu.py"""
import sys, os, re, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import calendario as C
from ui import tabla_visual as T
from ui import mercados as MK
from ui import marca as MA
from ui import mapa_calor as M

ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)

# --- calendario de cuadraditos
hoy = datetime.date(2026, 11, 5)
g = [(datetime.date(2026, 11, 5), [("AAPL", None, False), ("MSFT", "antes", True)]), (datetime.date(2026, 12, 2), [("NVDA", None, False)])]
h = C.calendario_grilla_html(g, hoy=hoy, nombres={"AAPL": "Apple Inc."})
chk(h.count('class="cg-tab"') == 3, "una solapa por mes (nov, dic, ene)")
chk(h.count("cg-wd") == 7 * 3 and "Lun" in h and "Dom" in h, "cabecera de días en cada mes")
chk('href="?empresa=AAPL"' in h and 'title="Apple Inc."' in h and ">NVDA</a>" in h, "cada empresa lleva a su ficha")
chk('cg-t est' in h and "fecha estimada" in h, "fecha estimada con borde punteado")
chk('class="cg-c hoy"' in h and "cg-hoy" in h, "hoy marcado")
chk("checked" in h.split("cg-tabs")[0] and h.count(" checked") == 1, "arranca en el mes actual")
e = C.economico_grilla_html([(datetime.date(2026, 11, 6), [("Empleo de EE.UU.", "EE.UU."), ("IPC", "Argentina")])], "Fed", hoy=hoy)
chk("Empleo de EE.UU." in e and "cg-e ar" in e and "Fed" in e, "eventos económicos en cuadraditos")
vacio = C.calendario_grilla_html([], hoy=hoy)
chk("No hay resultados cargados" in vacio, "sin datos: aviso")
chk("@media (max-width:900px)" in C.CSS_GRILLA and ".cg-g{display:block}" in C.CSS_GRILLA, "en el celular vuelve a lista")
d1 = C.calendario_grilla_html([], hoy=datetime.date(2026, 11, 18))
chk("<b>2</b>" not in d1.split("cg-mes-0")[-1].split("cg-mes-1")[0] and "<b>16</b>" in d1 and "<b>17</b>" in d1, "el primer mes arranca en el lunes de la semana de hoy")

# --- globitos hacia abajo
css = T.css_ayudas([("nombre", "Presioná"), ("precio_actual", "Lo que **cuesta** \"x\""), ("score_total", "Puntaje")])
chk("top:calc(100% + 6px)" in css and "bottom" not in css.split("tvtip")[1], "el globito se abre hacia abajo")
chk('\\"x\\"' in css and "**" not in css, "comillas escapadas y sin asteriscos")
chk(".st-key-tvh_nombre:hover::after" in css and "left:0" in css and "right:0" in css, "primero a la izquierda, últimos a la derecha")
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"), encoding="utf-8").read()
chk("help=ayuda_texto(clave, fecha)" not in src and "help=_ui_etfs.TIPS.get(titulo)" not in src, "los títulos ya no usan el globito de Streamlit")

# --- índices solo con porcentaje
barra = MK.barra_html([{"nombre": "S&P 500", "valor": "7.580,07", "var": "-140,32", "pct": "-1,82 %", "signo": -1}])
chk("-1,82 %" in barra and "-140,32" not in barra, "la barra muestra solo el porcentaje")

# --- menú que se cierra con el segundo toque
m = MA.menu_lista_html(True, version="1.5.34", enlaces={"quienes_somos": "", "youtube": "https://y.com", "mail": "a@b.com"})
chk('for="sec-redes" class="mn-it mn-ab mn-ab-redes"' in m and 'for="sec-none" class="mn-it mn-ce mn-ce-redes"' in m, "cada ítem tiene etiqueta de abrir y de cerrar")
chk("label.mn-ab-redes{display:none!important}" in MA.CSS and "label.mn-ce-redes{display:flex!important}" in MA.CSS, "abierto: se ve la de cerrar")
chk(".mn-it.mn-ce{display:none}" in MA.CSS, "cerrado: la de cerrar está escondida")

# --- paneles desde arriba y mapa
chk("body:has(#bn-cal:checked) .st-key-fly_cal{top:84px" in MA.CSS and "left:32px;right:32px" in MA.CSS.split("st-key-fly_cal{top:84px")[1][:200], "el calendario se despliega desde arriba, a todo el ancho")
chk("height:calc(100dvh - 84px - 16px)" in MA.CSS, "los paneles llegan casi al pie de la pantalla")
chk("margin:-62px auto 0" in M.CSS and "font-weight:400;opacity:.9" in M.CSS, "mapa: más aire con el buscador y letra más fina")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
