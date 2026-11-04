"""v1.5.22: la app tiene que seguir siendo rapida al crecer. Correr: python tests/test_v1522_rapidez.py
Controla (1) que los precios se renueven en segundo plano y nadie espere cada 5 minutos, (2) que los logos y las fotos NO vayan incrustados en la pagina,
(3) que Streamlit sirva la carpeta static/, (4) un tope de peso de la pagina de empresas."""
import os, re, sys, time
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ); os.chdir(RAIZ)
from data import swr

ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)

# ---- 1. swr: datos de la heladera
swr.olvidar()
n = {"v": 0}
def lento(seg=0.4):
    def f():
        time.sleep(seg); n["v"] += 1; return {"usd": {"A": n["v"]}}
    return f
OK = lambda r: bool(r.get("usd"))
t = time.time(); r = swr.obtener("k1", lento(0.3), ttl=1, esperar=5, valido=OK, vacio={})
chk(r == {"usd": {"A": 1}} and time.time() - t >= 0.25, "la primera vez tiene que esperar el dato")
t = time.time(); r = swr.obtener("k1", lento(0.3), ttl=1, esperar=5, valido=OK, vacio={})
chk(r["usd"]["A"] == 1 and time.time() - t < 0.1 and n["v"] == 1, "dentro del plazo se devuelve lo guardado sin bajar de nuevo")
time.sleep(1.1)
t = time.time(); r = swr.obtener("k1", lento(0.5), ttl=1, esperar=5, valido=OK, vacio={})
chk(r["usd"]["A"] == 1 and time.time() - t < 0.2, "vencido: se devuelve YA lo anterior (nadie espera la bajada)")
time.sleep(0.8)
r = swr.obtener("k1", lento(0.5), ttl=1, esperar=5, valido=OK, vacio={})
chk(r["usd"]["A"] == 2, "la renovacion en segundo plano quedo guardada para la visita siguiente")
# una bajada que falla o viene vacia no pisa a la buena
swr.olvidar("k2"); swr.obtener("k2", lambda: {"usd": {"A": 9}}, ttl=0.05, esperar=2, valido=OK, vacio={})
time.sleep(0.1); swr.obtener("k2", lambda: {"usd": {}}, ttl=0.05, esperar=2, valido=OK, vacio={}); time.sleep(0.2)
chk(swr.obtener("k2", lambda: {"usd": {}}, ttl=0.05, esperar=2, valido=OK, vacio={})["usd"] == {"A": 9}, "una bajada vacia no tiene que pisar los ultimos precios buenos")
def rota(): raise RuntimeError("Yahoo caido")
swr.olvidar("k3"); chk(swr.obtener("k3", rota, ttl=1, esperar=2, valido=OK, vacio={"x": 1}) == {"x": 1}, "si la primera bajada falla, devuelve el valor vacio sin romper")
# primera vez con bajada lenta: no se queda trabada
swr.olvidar("k4"); t = time.time(); r = swr.obtener("k4", lento(1.0), ttl=60, esperar=0.2, valido=OK, vacio={"vacio": 1})
chk(r == {"vacio": 1} and time.time() - t < 0.6, "la primera vez no espera mas que `esperar` segundos")
time.sleep(1.0); chk(swr.obtener("k4", lento(1.0), ttl=60, esperar=0.2, valido=OK, vacio={"vacio": 1}).get("usd"), "...y la visita siguiente ya tiene el dato")

# ---- 2. logos y fotos fuera de la pagina
from ui import logos
from config.sectors import TICKER_UNIVERSE
tickers = sorted({t for v in TICKER_UNIVERSE.values() for t in v})
con_archivo = [t for t in tickers if logos._archivo_local(t)]
chk(len(con_archivo) >= 200, f"pocos logos en static/logos: {len(con_archivo)}")
for t in con_archivo:
    h = logos.logo_html(t, 26)
    if "data:image" in h or f"app/static/logos/{t}.png" not in h:
        chk(False, f"el logo de {t} no sale como archivo servido: {h[:120]}"); break
else:
    chk(True, "")
chk(str(logos.CARPETA_LOGOS).replace("\\", "/").endswith("static/logos"), "los logos tienen que estar en static/logos")
chk(os.path.isfile("static/marca/foto-guillermo.png") and os.path.isfile("static/marca/foto-maria-laura.png"), "faltan las fotos en static/marca")
from ui import quienes
q = quienes.quienes_html()
chk("data:image/png;base64" not in q.split("qs-pers")[-1][:400] and "app/static/marca/foto-guillermo.png" in q, "Quienes somos tiene que traer las fotos como archivo")

# ---- 3. Streamlit sirve static/
cfg = open(".streamlit/config.toml", encoding="utf-8").read()
chk(re.search(r"(?m)^\s*enableStaticServing\s*=\s*true", cfg) is not None, ".streamlit/config.toml: falta enableStaticServing = true")

# ---- 4. peso de la pagina de empresas (HTML que viaja en cada recarga)
try:
    import config.ajustes as A; A.PRECIOS_VIVOS = False
    from ui import mercados as mk      # barra de mercados con datos de mentira (sin red)
    mk._EST["items"] = mk.armar({"^GSPC": (7580.0, 7720.0)}, {"oficial": 1475.0}); mk._EST["t"] = time.time()
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_string("import sys,os\nsys.path.insert(0,%r);os.chdir(%r)\nexec(compile(open('app.py',encoding='utf-8').read(),'app.py','exec'),{'__name__':'__main__','__file__':os.path.abspath('app.py')})" % (RAIZ, RAIZ), default_timeout=300)
    at.query_params["inicio"] = "0"; at.run()
    total = sum(len(m.value) for m in at.markdown)
    mayor = max(len(m.value) for m in at.markdown)
    chk(not at.exception, f"la app dio error: {[e.value for e in at.exception][:1]}")
    chk(total < 1_500_000, f"la pagina pesa {total/1e6:.2f} MB de HTML (tope 1,5 MB)")
    chk(mayor < 700_000, f"un bloque pesa {mayor/1e3:.0f} KB (tope 700 KB)")
    chk("data:image/png;base64" not in "".join(m.value for m in at.markdown if 'class="tv2"' in m.value), "la tabla no debe llevar logos incrustados")
    print(f"   (pagina de empresas: {total/1e6:.2f} MB de HTML, bloque mayor {mayor/1e3:.0f} KB)")
except Exception as e:  # noqa: BLE001
    chk(False, f"no se pudo medir la pagina: {e!r}")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
