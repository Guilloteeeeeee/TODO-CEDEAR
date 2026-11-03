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
# v1.5.9: empresas reales del caché, vista previa desenfocada y oculta para lectores de pantalla; sin caché vuelve a las filas de ejemplo
fr = I.filas_reales()
chk(fr is not None and [f["nombre"] for f in fr] == ["Microsoft Corporation", "Alphabet Inc.", "The Coca-Cola Company"], f"filas reales: {fr and [f['nombre'] for f in fr]}")
chk("Microsoft Corporation" in hh and "Empresa de ejemplo" not in hh and "filter:blur(" in hh and 'aria-hidden="true"' in hh, "vista previa real, desenfocada")
chk(all(0 < f["pos"] < 100 and f["txt"].startswith("Podría estar") and f["sc"] > 0 for f in fr), "valoración y barra con datos de la tabla")
_raiz = I._RAIZ
I._RAIZ = I.Path("/no/existe")
I._CACHE.update(mtime=None, datos=None)
chk(I.filas_reales() is None and "Empresa de ejemplo A" in I.hero_html(), "sin caché: filas de ejemplo")
I._RAIZ = _raiz
I._CACHE.update(mtime=None, datos=None)
chk("Filtrá Acciones y ETFs que cotizan como CEDEARs en Argentina, leé el análisis de cada empresa y enterate cuáles están baratas. Evalúa tu Portfolio. Todo Gratuito!" in hh, "texto de Guille")
print(f"OK {ok} MAL {bad}")
