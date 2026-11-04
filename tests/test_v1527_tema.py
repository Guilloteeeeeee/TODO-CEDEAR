"""v1.5.27: el tema del día (la victoria demócrata) abre cada bloque aunque los titulares compartan una sola palabra. Correr: python tests/test_v1527_tema.py"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import noticias as N

ahora = dt.datetime(2026, 11, 4, 23, tzinfo=dt.timezone.utc)
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
def nota(t, medio, h=1, idioma="en"):
    return {"titulo": t, "link": "https://x/" + (medio + t).replace(" ", "_"), "clave": medio + "/" + t, "fecha": ahora - dt.timedelta(hours=h), "medio": medio, "idioma": idioma}
def bloque(notas):
    return {"notas": notas, "portada": set(), "feeds_ok": 1, "feeds_total": 3}
TK = ["QCOM", "AAPL", "MSFT", "AMZN", "AZN", "CVS", "GOOGL", "ABNB", "TSLA", "WFC"]

# Titulares de la pantalla de Guille del 04/11 (los de inglés están reconstruidos: en la app se ven ya traducidos)
loc = [nota("Finanzas al día: novedades de bancos, inversiones y mercado de capitales", "Ámbito", 0.2, "es"),
       nota("Dólar blue hoy: a cuánto cerró este miércoles 4 de noviembre", "Ámbito", 3, "es"),
       nota("Los bonos en dólares extendieron pérdidas y el riesgo país saltó por encima de los 850 puntos tras las elecciones en EEUU", "Ámbito", 0.9, "es")]
usa = [nota("Qualcomm shares fall 6% on weak guidance as memory shortage weighs on smartphone sales", "CNBC", 0.8),
       nota("Hyperscalers and Apple rise after election results remove uncertainty for investors", "CNBC", 3),
       nota("Microsoft and Amazon combine to see a $424 billion market-cap jump, and here is why", "MarketWatch", 1),
       nota("Rhythm Pharmaceuticals acciones suben 28% tras oferta de AstraZeneca", "Investing.com", 1, "es"),
       nota("The worst-performing S&P 500 stocks of this year are finally seeing big relief", "MarketWatch", 0.1)]
mun = [nota("UK interest rates expected to rise after they accelerate", "The Guardian", 8),
       nota("CVS Health plans a split. Here's why a breakup could make sense now", "CNBC", 2),
       nota("Google responds to political backlash over removing search from schools that ban AI", "CNBC", 4),
       nota("Airbnb may be positive for the community | Letters", "The Guardian", 5),
       nota("Democrats' midterm triumph sends US stocks soaring, but Tesla and SpaceX fall", "South China Morning Post", 7)]
crudo = {"bloques": {"locales": bloque(loc), "usa": bloque(usa), "mundo": bloque(mun)}}

pares = [(n["titulo"], n["medio"]) for b in crudo["bloques"].values() for n in b["notas"]]
chk(N.tema_del_dia(pares) == "elecciones", f"el tema del día tendría que ser elecciones: {N.tema_del_dia(pares)}")
chk(N.tema_del_dia([("Qualcomm cae 6%", "CNBC"), ("Dólar blue hoy", "Ámbito")]) is None, "sin tema común no hay tema")
chk(N.tema_del_dia([("Elecciones en EEUU: qué pasa", "Ámbito"), ("Elecciones y mercados", "Ámbito")]) is None, "un solo medio no hace tema")
bl = N.ordenar_bloques(crudo, TK, ahora=ahora)
B = {b["clave"]: b for b in bl}
chk("elecciones" in B["locales"]["notas"][0]["titulo"], f"Locales abre con las elecciones: {B['locales']['notas'][0]['titulo']}")
chk("election" in B["usa"]["notas"][0]["titulo"], f"Estados Unidos abre con las elecciones: {B['usa']['notas'][0]['titulo']}")
chk("Democrats" in B["mundo"]["notas"][0]["titulo"], f"Resto del mundo abre con las elecciones: {B['mundo']['notas'][0]['titulo']}")
for k in B:
    chk(sum(1 for n in B[k]["notas"] if n.get("tendencia")) == 1, f"{k}: una sola tendencia")
chk([len(B[k]["notas"]) for k in ("locales", "usa", "mundo")] == [3, 5, 5], "cantidades 3/5/5")
tks = [t for b in bl for n in b["notas"] for t in (n.get("menciona") or [])]
chk(len(tks) == len(set(tks)), f"tickers repetidos {tks}")
# otro día: si el tema es la Fed, abre con la Fed
loc2 = [nota("Dólar hoy", "Ámbito", 1, "es"), nota("La Fed baja las tasas y el mercado reacciona", "Ámbito", 2, "es")]
usa2 = [nota("Qualcomm shares fall 6%", "CNBC", 1), nota("Fed cuts rates by a quarter point, Powell signals pause", "CNBC", 3), nota("Stocks rally after Fed decision", "MarketWatch", 2)]
bl2 = {b["clave"]: b for b in N.ordenar_bloques({"bloques": {"locales": bloque(loc2), "usa": bloque(usa2), "mundo": bloque([])}}, TK, ahora=ahora)}
chk("Fed" in bl2["usa"]["notas"][0]["titulo"] and "Fed" in bl2["locales"]["notas"][0]["titulo"], "con la Fed como tema, abre con la Fed")
# el estado de cada feed queda guardado para el panel de diagnóstico
crudo2 = N._bajar_todo(descargar=lambda u: None)
chk(crudo2.get("estado_feeds") is not None and len(crudo2["estado_feeds"]) == crudo2["feeds_total"], "estado_feeds")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
