"""v1.5.24: noticias con varios medios, tendencia del día al principio, 3/5/5 notas, una nota por ticker y por historia. Correr: python tests/test_v1524_noticias.py"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import noticias as N

ahora = dt.datetime(2026, 11, 4, 15, tzinfo=dt.timezone.utc)
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
def nota(t, medio, h=1, idioma="en", k=None):
    k = k or (medio + "/" + t)
    return {"titulo": t, "link": "https://x/" + k.replace(" ", "_"), "clave": k, "fecha": ahora - dt.timedelta(hours=h), "medio": medio, "idioma": idioma}
def bloque(notas, portada=(), ok_=1):
    return {"notas": notas, "portada": set(portada), "feeds_ok": ok_, "feeds_total": 3}
TK = ["TSLA", "NVDA", "WFC", "MRNA", "AAPL", "MSFT", "INTC", "F"]

# --- historias
T = N.tokens_historia
chk(N.misma_historia(T("US midterms live: Stocks climb as Democrats take control of Congress"), T("Democrats’ midterm triumph sends US stocks soaring, but Tesla, SpaceX fall")), "misma historia (demócratas)")
chk(not N.misma_historia(T("Intel surges on AI chip deal"), T("Toyota shares slide in Tokyo")), "historias distintas")
chk(not N.misma_historia(T("Stocks rally as markets rise"), T("Stocks fall as markets drop")), "palabras comunes no cuentan")

# --- bloques de hoy (titulares reales del 04/11 de la prueba de fuentes)
loc = [nota("Dólar hoy: a cuánto cotiza el blue este miércoles", "Ámbito", 1, "es"), nota("Merval y bonos: las acciones argentinas suben tras Wall Street", "Ámbito", 2, "es"),
       nota("Las 8 señales de alarma para Caputo tras la derrota de Trump y la suba del dólar en Brasil", "iProfesional", 3, "es"),
       nota("Caputo y la derrota de Trump: qué pasa con el dólar y el riesgo país en Argentina", "La Nación", 2, "es"),
       nota("Patricia Bullrich reconoció los reclamos del campo por las retenciones", "La Nación", 4, "es"),
       nota("Un parque industrial espera generar 25.000 puestos de trabajo", "Ámbito", 5, "es"), nota("Wells Fargo sube y el dólar baja", "Ámbito", 6, "es")]
usa = [nota("Stocks making the biggest moves premarket: Trump Media, Tesla, CoreWeave, Novo Nordisk and more", "CNBC", 3),
       nota("Wall Street rallies as Democrats take control of Congress, stocks climb", "CNBC", 1),
       nota("Stock market rallies after Democrats win control of Congress in midterms", "MarketWatch", 2),
       nota("La acción de Alarm.com alcanza su máximo de 52 semanas en 67,43 dólares", "Investing.com", 1, "es"),
       nota("¿Por qué cae hoy la acción de Intel?", "Investing.com", 2, "es"),
       nota("Why is Nvidia stock sliding today?", "Investing.com", 3, "en"),
       nota("Qualcomm sat out the semiconductor rally. Can a SpaceX partnership change that?", "MarketWatch", 4),
       nota("Apple supplier cuts forecast, Apple shares dip", "CNBC", 5), nota("Fed's Powell says rates on hold as inflation cools", "CNBC", 6),
       nota("Microsoft unveils new AI chip, Microsoft stock jumps", "MarketWatch", 7)]
mun = [nota("US midterms live: Stocks climb as Democrats take control of Congress", "South China Morning Post", 1),
       nota("Democrats’ midterm triumph sends US stocks soaring, but Tesla, SpaceX fall", "South China Morning Post", 2),
       nota("What the Democrats' midterms win means for the US economy and Trump", "DW", 1),
       nota("ECB wage tracker suggests slightly higher wage growth in 2027", "DW", 3),
       nota("Elon Musk's millions fail to deliver Texas for the Republicans in fierce midterms", "BBC", 2),
       nota("Bank of England holds rates as inflation stays high", "BBC", 4), nota("UK retailers warn of weaker Christmas sales", "BBC", 5),
       nota("Key Central Asian highway expands on trade route from China towards Europe", "The Guardian", 3),
       nota("Japan's Nikkei hits record as Toyota shares slide in Tokyo", "CNBC", 4), nota("European stocks close higher, STOXX 600 up 1%", "CNBC", 2),
       nota("Oil prices fall as OPEC weighs output", "The Guardian", 6),
       nota("Bank of England keeps interest rates unchanged as inflation stays high", "The Guardian", 2), nota("Bank of England interest rates decision: what it means", "CNBC", 3)]
crudo = {"bloques": {"locales": bloque(loc), "usa": bloque(usa, portada=[]), "mundo": bloque(mun)}}
bl = N.ordenar_bloques(crudo, TK, ahora=ahora)
B = {b["clave"]: b for b in bl}
chk([len(B[k]["notas"]) for k in ("locales", "usa", "mundo")] == [3, 5, 5], f"cantidades {[len(B[k]['notas']) for k in ('locales','usa','mundo')]} (deben ser 3, 5 y 5)")
for k in B:
    n0 = B[k]["notas"][0] if B[k]["notas"] else {}
    chk(n0.get("tendencia"), f"la primera nota de {k} tiene que ser la tendencia del día: {n0.get('titulo')}")
    chk(sum(1 for n in B[k]["notas"] if n.get("tendencia")) <= 1, f"más de una tendencia en {k}")
chk("Democrats" in B["usa"]["notas"][0]["titulo"], f"la tendencia de EEUU es la victoria demócrata: {B['usa']['notas'][0]['titulo']}")
chk("Caputo" in B["locales"]["notas"][0]["titulo"], f"la tendencia local es Caputo/Trump (la cubren iProfesional y La Nación): {B['locales']['notas'][0]['titulo']}")
todos = [n for b in bl for n in b["notas"]]
tks = [t for n in todos for t in (n.get("menciona") or [])]
chk(len(tks) == len(set(tks)), f"tickers repetidos: {tks}")
dem = [n["titulo"] for n in todos if "Democrat" in n["titulo"]]
chk(len(dem) <= 1, f"la historia demócrata salió {len(dem)} veces: {dem}")
chk(sum("Democrats" in n["titulo"] for n in B["mundo"]["notas"]) == 0, "la historia que ya abrió EEUU no se repite en Resto del mundo")
for k in ("usa", "mundo"):
    por_medio = {}
    for n in B[k]["notas"]:
        por_medio[n["fuente"]] = por_medio.get(n["fuente"], 0) + 1
    chk(max(por_medio.values()) <= 2, f"{k}: un medio pasa de 2 notas {por_medio}")
    chk(len(por_medio) >= 3, f"{k}: pocos medios distintos {por_medio}")
chk(any("Merval" in n["titulo"] for n in B["locales"]["notas"]) or any("Dólar" in n["titulo"] for n in B["locales"]["notas"]), "Locales sin dólar ni mercado")
chk(any(N.es_macro(n["titulo"]) for k in ("usa", "mundo") for n in B[k]["notas"]), "falta una nota macro entre EEUU y el mundo")

# --- si un medio no responde, lo llenan los otros (CNBC solo con 5 notas llena el bloque)
solo = [nota(x, "CNBC", i + 1) for i, x in enumerate(["Toyota unveils battery plant in Japan", "Oil prices fall as OPEC weighs output", "Airline strike grounds flights across Europe",
        "Copper hits record on Chinese demand", "Bitcoin slides below key level", "Hotel chains report weaker bookings", "Chip equipment makers warn on exports", "Gold steadies near highs"])]
b2 = N.ordenar_bloques({"bloques": {"locales": bloque(loc), "usa": bloque(solo), "mundo": bloque([])}}, TK, ahora=ahora)
chk(len(b2[1]["notas"]) == 5, f"con un solo medio vivo el bloque tiene que llenarse con lo que haya (titulares distintos): {len(b2[1]['notas'])}")
chk(len(b2[2]["notas"]) == 0 and not b2[2]["respondio"] is None, "un bloque sin notas no rompe")
# ningún medio responde en Locales: el bloque queda vacío pero los otros siguen
b3 = N.ordenar_bloques({"bloques": {"locales": bloque([], ok_=0), "usa": bloque(usa), "mundo": bloque(mun)}}, TK, ahora=ahora)
chk(b3[0]["notas"] == [] and not b3[0]["respondio"], "Locales sin respuesta")
chk(len(b3[1]["notas"]) == 5 and len(b3[2]["notas"]) == 5, "los otros bloques siguen completos")

# --- traducción: solo lo que está en inglés
llamadas = []
def falso(titulos, mail):
    llamadas.extend(titulos); return {t: "ES:" + t for t in titulos}
N.TRADUCIR = True
tr = N.traducir_bloques(bl, traducir_lista=falso)
esp = [n for n in tr[1]["notas"] if n.get("idioma") == "es"]
chk(all(not n.get("titulo_es") for n in esp), "los titulares de Investing en español no se traducen")
chk(all(n.get("titulo_es") for n in tr[1]["notas"] if n.get("idioma") == "en"), "los titulares en inglés sí se traducen")
chk(not any(t.startswith("La acción") or t.startswith("¿Por qué") for t in llamadas), "se mandó a traducir un titular en español")

# --- dibujo
h = N.noticias_bloques_html(tr, ahora=ahora)
chk("nt-t" not in h and "Tendencia del día</span>" not in h, "no tiene que haber etiqueta naranja de tendencia (Guille: dejar el dibujo como estaba)")
for medio in {n["fuente"] for b in tr for n in b["notas"]}:
    chk(medio in h, f"el HTML no nombra a {medio} (cada nota nombra su medio)")
chk("Fuentes:" not in h and "nt-pie" not in h and "Es información" not in h, "Guille: sin pie de fuentes en el recuadro de noticias")
chk("<small>" not in h.split("nt-ul")[0], "Guille: sin la lista de medios en el título de cada bloque")

# --- los feeds por defecto
cl = {b["clave"]: b for b in N.BLOQUES}
chk(cl["locales"]["cantidad"] == 3 and cl["usa"]["cantidad"] == 5 and cl["mundo"]["cantidad"] == 5, "cantidades 3/5/5 en la configuración")
med = lambda k: {f[3] for f in cl[k]["feeds"]}
chk(med("locales") == {"Ámbito", "iProfesional", "La Nación"}, f"medios de Locales {med('locales')}")
chk(cl["usa"]["fuente"].startswith("Investing.com"), "Investing.com va primero en el rótulo de Estados Unidos")
chk(med("usa") == {"CNBC", "MarketWatch", "Investing.com"}, f"medios de EEUU {med('usa')}")
chk(med("mundo") == {"CNBC", "BBC", "The Guardian", "DW", "South China Morning Post"}, f"medios del mundo {med('mundo')}")
chk(not any("yahoo" in f[1] or "economista" in f[1] for b in N.BLOQUES for f in b["feeds"]), "Yahoo y elEconomista quedaron afuera")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
