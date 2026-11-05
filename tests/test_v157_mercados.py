"""v1.5.7: barra de mercados (formato, orden, casilleros que faltan, lectura de yfinance) y pantalla de inicio."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pandas as pd
from ui import mercados as M, inicio as I
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1
    else: bad += 1; print("FALLA:", m)

chk(M.num_es(7580.07, 2) == "7.580,07" and M.num_es(-140.32, 2) == "-140,32" and M.num_es(1234567.891, 2) == "1.234.567,89", "formato argentino")
chk(M.num_es(-0.001, 2) == "0,00", "cero negativo sin signo")
ind = {"^GSPC": (7580.07, 7720.39), "^VIX": (19.42, 17.2), "BZ=F": (65.1, 65.1)}
it = M.armar(ind, {"oficial": 1475.0, "bolsa": 1567.23, "contadoconliqui": 1580.5})
nom = [i["nombre"] for i in it]
chk(nom[:3] == ["Dólar oficial", "Dólar MEP", "Dólar CCL"], "primero los tres dólares")
chk("S&P 500" in nom and "VIX" in nom and "Petróleo Brent (US$)" in nom, "casilleros presentes")
chk("Nasdaq" not in nom and "Merval" not in nom, "lo que no llegó se oculta")
sp = next(i for i in it if i["nombre"] == "S&P 500")
chk(sp["signo"] == -1 and sp["var"] == "-140,32" and sp["pct"] == "-1,82 %", f"S&P bajó: {sp}")
vx = next(i for i in it if i["nombre"] == "VIX")
chk(vx["signo"] == 1 and vx["var"].startswith("+") and vx["pct"].startswith("+"), "VIX sube con +")
chk(next(i for i in it if i["nombre"] == "Petróleo Brent (US$)")["signo"] == 0, "sin variación")
chk(M.armar({}, {}) == [], "sin datos -> lista vacía")
h = M.barra_html(it)
chk("<svg" not in h and "<a " not in h and "href" not in h, "sin gráficos chicos ni links")
chk("venta" not in h and "mk-fl" in h and "WTI" not in h, "sin la palabra venta, con puntita de flecha y un solo petróleo")
chk(M.barra_html([]) == "", "sin datos no se dibuja nada")
# dólares desde DolarApi (con una respuesta simulada)
d = M.descargar_dolares(get=lambda: [{"casa": "oficial", "venta": 1475}, {"casa": "bolsa", "venta": "1567.23"}, {"casa": "tarjeta", "venta": None}, {"casa": "x"}])
chk(d == {"oficial": 1475.0, "bolsa": 1567.23}, f"dolarapi {d}")
chk(M.descargar_dolares(get=lambda: 1 / 0) == {}, "dolarapi roto -> vacío")
# yfinance con varias columnas
idx = pd.date_range("2026-10-29", periods=3)
cols = pd.MultiIndex.from_product([["^GSPC", "^IXIC"], ["Close"]])
df = pd.DataFrame([[7700.0, 26000.0], [7720.39, 26184.7], [7580.07, float("nan")]], index=idx, columns=cols)
r = M._ultimos_dos(df, ["^GSPC", "^IXIC", "^NOEXISTE"])
chk(abs(r["^GSPC"][0] - 7580.07) < 1e-6 and abs(r["^GSPC"][1] - 7720.39) < 1e-6, "último y anterior")
chk(abs(r["^IXIC"][0] - 26184.7) < 1e-6 and "^NOEXISTE" not in r, "salta NaN y lo que falta")
# obtener: primera vez espera; después usa lo guardado y no vuelve a pedir
llamadas = []
M._EST.update(t=0.0, items=None, hilo=None)
r1 = M.obtener(esperar=5, indices_fn=lambda: (llamadas.append(1), ind)[1], dolares_fn=lambda: {"oficial": 1475.0})
chk(len(r1) == 4 and len(llamadas) == 1, "primera vez: espera y trae datos")
r2 = M.obtener(esperar=5, indices_fn=lambda: (llamadas.append(1), ind)[1], dolares_fn=lambda: {})
chk(len(llamadas) == 1 and r2 == r1, "dentro de los 5 minutos no vuelve a pedir")
M._EST["t"] = time.time() - 400
r3 = M.obtener(esperar=5, indices_fn=lambda: {}, dolares_fn=lambda: {})
chk(r3 == r1, "vencido y sin respuesta nueva: se sigue mostrando lo último")
time.sleep(0.3)
M._EST.update(t=0.0, items=None, hilo=None)
chk(M.obtener(esperar=3, indices_fn=lambda: {}, dolares_fn=lambda: {}) == [], "sin datos desde el principio: barra vacía")
# inicio
hh = I.hero_html()
chk(hh.count("<a ") == 1 and 'href="?inicio=0"' in hh and ">Comenzar<" in hh, "un solo botón de acceso")
chk("Pantalla ilustrativa" not in hh, "sin leyenda")
# v1.5.10: foto fija con empresas reales (sin leer el caché), desenfocada y oculta para lectores de pantalla; texto nuevo justificado, «Todo Gratuito!» en negrita, sin aviso bajo el botón
chk([f["nombre"] for f in I.FOTO] == ["Microsoft Corporation", "Alphabet Inc.", "The Coca-Cola Company"], "foto: empresas reales")
chk("Microsoft Corporation" in hh and "Empresa de ejemplo" not in hh and "filter:blur(" in hh and 'aria-hidden="true"' in hh, "vista previa real, desenfocada")
chk(all(0 < f["pos"] < 100 and f["txt"].startswith("Podría estar") and f["sc"] > 0 for f in I.FOTO), "valoración y barra de la foto")
chk(not hasattr(I, "filas_reales") and not hasattr(I, "_leer_cache"), "no lee el caché al entrar: es una foto")
chk("Todos los CEDEARs de Acciones y ETFs en un solo lugar. Análisis de empresas y filtros para saber cuáles están baratas. <b>Todo Gratuito!</b>" in hh, "texto de Guille, con negrita")
chk("text-align:justify" in hh and "Información educativa" not in hh and "<small" not in hh.split("</style>")[1].split('class="hr-der"')[0], "justificado y sin nada debajo de Comenzar")
chk("justify-content:center" not in M.CSS_BARRA and "mk-d" not in M.CSS_BARRA, "los dólares van a la misma altura que el resto")
# v1.5.14: franja negra con Noticias, Calendario, Ideas y Evalúa tu Portfolio (en ese orden, sin buscador), panel del filtro desplegable
from ui import marca as MA
_b = MA.encabezado_html("TodoCedears", links=True, home=True)
_orden = [_b.index(x) for x in ("Mapa de Calor</a>", "Noticias del Día</label>", "Calendario Financiero</label>", ">Ideas de Inversión</a>", "Evalúa tu Portfolio</a>")]
chk(_orden == sorted(_orden), "franja: Mapa de Calor, Noticias del Día, Calendario Financiero, Ideas de Inversión y Evalúa tu Portfolio en ese orden")
chk('for="bn-noticias"' in _b and 'for="bn-cal"' in _b and 'id="bn-filtro"' in _b and "buscador" not in _b, "franja: paneles sin recargar y sin buscador")
_f = MA.encabezado_html("TodoCedears", links=True, home=False)
chk("abrir=noticias" in _f and "abrir=cal" in _f, "fuera del inicio, Noticias y Calendario llevan al inicio con el panel abierto")
chk("links" not in MA.encabezado_html("TodoCedears").split("mc-band")[0] and "mc-links" not in MA.encabezado_html("TodoCedears"), "sin links en el inicio con «Comenzar»")
chk("bn-filtro:checked) .st-key-fly_filtro" in MA.CSS and "left:40px;right:40px" in MA.CSS, "el filtro se despliega casi a todo el ancho")
chk("mc-links" in MA.CSS and "st-key-buscador" in MA.CSS and "padding-left:28px" in MA.CSS, "tabla más ancha y buscador fuera de la franja")
chk("Filtro de Empresas" not in MA.menu_lista_html(True, filtro="Filtro de Empresas"), "el menú ya no repite el Filtro")
_m = MA.menu_lista_html(True, version="1.5.33", enlaces={"quienes_somos": "", "youtube": "https://y.com", "mail": "a@b.com"})
chk(all(x not in _m for x in ("Noticias", "Calendario", "Ideas", "Portfolio", "Mapa", "Sobre Nosotros", "mn-det")) and "Quiénes Somos" in _m and "Nuestras Redes" in _m and "Contactanos" in _m, "v1.5.33: el menú deja solo Quiénes Somos, Redes, Contacto y Comentarios, desplegados")
# v1.5.15: tickers gemelos (ADR + acción local de Brasil): una sola ficha, el ticker local en otra línea
from data import gemelos as GM
from ui import ficha as FI
import json as _j
_by = _j.load(open("data/byma_cedears.json", encoding="utf-8"))["cedears"]
chk(len(GM.GEMELOS) == 9 and all(l in _by and a in _by for a, (l, _m) in GM.GEMELOS.items()), "los 9 pares están en la lista oficial de BYMA")
chk(GM.gemelo("PBR") == ("PETR3", "B3") and GM.principal("PETR3") == "PBR" and GM.gemelo("AAPL") is None, "gemelo / principal")
_h = FI._encabezado({"ticker": "PBR", "nombre": "Petrobras"}, "NYSE", None, None, None)
chk(">NYSE: PBR<" in _h and ">B3: PETR3<" in _h and _h.index("NYSE: PBR") < _h.index("B3: PETR3"), "ficha: debajo de «NYSE: PBR» va «B3: PETR3»")
chk("B3:" not in FI._encabezado({"ticker": "AAPL", "nombre": "Apple"}, "Nasdaq", None, None, None), "ficha sin gemelo: igual que antes")
print(f"OK {ok} MAL {bad}")
