"""v1.5.2: noticias — sin tickers repetidos en todo el cuadro, una nota macro entre USA y Resto del mundo, mercado argentino en Locales."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import noticias as N

ahora = dt.datetime(2026, 11, 2, 15, tzinfo=dt.timezone.utc)
def nota(t, h=1, k=None):
    return {"titulo": t, "link": "https://x/" + (k or t), "clave": k or t, "fecha": ahora - dt.timedelta(hours=h)}
def bloque(notas, portada=()):
    return {"notas": notas, "portada": set(portada), "feeds_ok": 1, "feeds_total": 1}
TK = ["INTC", "AMZN", "NVDA", "MRVL", "MELI", "JPM"]
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)

loc = [nota("Dólar hoy minuto a minuto: a cuánto opera"), nota("Colectivos: ARBA reglamentó la exención"), nota("Merval: el índice sube y los bonos en dólares avanzan"),
       nota("Mercado Libre abre una nueva sede en Córdoba"), nota("El RENATRE aumentó 5% la prestación")]
usa = [nota("Intel surges on AI chip deal", 1), nota("Intel stock jumps again after report", 2), nota("Amazon unveils new AWS chip", 3),
       nota("Nvidia leads chip rally", 4), nota("Fed's Barkin says AI investment is adding to inflation pressure", 5), nota("Marvell to buy Lumentum", 6)]
mundo = [nota("Intel supplier in Taiwan raises forecast", 1), nota("Europe's central bank signals rates on hold", 2), nota("Toyota shares slide in Tokyo", 3)]
crudo = {"bloques": {"locales": bloque(loc), "usa": bloque(usa), "mundo": bloque(mundo)}}
bl = N.ordenar_bloques(crudo, TK, ahora=ahora)
todos = [n for b in bl for n in b["notas"]]
tks = [t for n in todos for t in (n.get("menciona") or [])]
chk(len(tks) == len(set(tks)), f"tickers repetidos {tks}")
chk(sum("Intel" in n["titulo"] for n in todos) <= 1, "Intel más de una vez")
loc_t = [n["titulo"] for n in bl[0]["notas"]]
chk(any("Merval" in t for t in loc_t), f"falta nota de mercado en Locales {loc_t}")
chk(any("Dólar hoy" in t for t in loc_t), "falta el dólar")
ext = [n["titulo"] for b in bl[1:] for n in b["notas"]]
chk(any(N.es_macro(t) for t in ext), f"falta nota macro {ext}")

# sin ninguna macro disponible: quedan notas de empresas
usa2 = [nota("Intel surges", 1), nota("Amazon unveils chip", 2), nota("Nvidia leads rally", 3)]
mundo2 = [nota("Toyota shares slide", 1), nota("Samsung raises forecast", 2)]
bl2 = N.ordenar_bloques({"bloques": {"locales": bloque(loc), "usa": bloque(usa2), "mundo": bloque(mundo2)}}, TK, ahora=ahora)
chk(all(len(b["notas"]) > 0 for b in bl2), "sin macro quedó un bloque vacío")

# macro solo en Resto del mundo: se fuerza ahí
usa3 = [nota("Intel surges", 1), nota("Amazon unveils chip", 2), nota("Nvidia leads rally", 3), nota("Marvell buys Lumentum", 4), nota("JPMorgan hires", 5)]
mundo3 = [nota("Toyota shares slide", 1), nota("Bank of Japan holds interest rates steady", 9)]
bl3 = N.ordenar_bloques({"bloques": {"locales": bloque(loc), "usa": bloque(usa3), "mundo": bloque(mundo3)}}, TK, ahora=ahora)
chk(any(N.es_macro(n["titulo"]) for b in bl3[1:] for n in b["notas"]), "no se forzó la macro de Resto del mundo")
print(f"OK {ok} MAL {mal}")
