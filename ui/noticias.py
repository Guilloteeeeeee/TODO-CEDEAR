"""
Noticias Calientes (v1.2.39; fuente CNBC en la v1.2.40; titulares en español -Ambito- desde la v1.2.41): titulares de las
secciones de la fuente con link a la nota.

Regla de orden (la aprobo Guille el 23/10): primero las que nombran empresas del screener, despues las que estan en la
portada de la fuente, y a igualdad, la mas reciente. Se muestran las 5 primeras de las ultimas 24 horas, solo con titulo,
fuente y link (no se copia el texto de las notas).

Como funciona:
  * Baja los feeds RSS publicos de la fuente elegida (NOTICIAS_IDIOMA en config/ajustes.py: "es" = Ambito, "en" = CNBC) al
    mismo tiempo. La portada se usa solo para saber cuales notas estan ahi; las notas que se muestran salen de las secciones.
  * Si hay menos de 5 notas en 24 h, amplia la ventana a 48 y a 72 h.
  * Guarda el resultado 15 minutos en memoria (todos los que abren la app comparten la misma descarga).
  * Si la fuente no responde, la app sigue normal y muestra un renglon chico avisandolo. Nunca rompe la pagina.
  * Los titulares salen en el idioma de la fuente elegida (español con Ambito, ingles con CNBC). Con CNBC se pueden traducir
    automaticamente al español (NOTICIAS_TRADUCIR = True; ver ui/traducir.py); si la traduccion falla, el titular queda en ingles.

No usa JavaScript ni cuentas ni claves. Las fuentes y sus feeds se cambian en config/ajustes.py (NOTICIAS_FUENTES).
"""
import functools
import html
import re
import unicodedata
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

try:
    from config import ajustes as _aj
except Exception:  # noqa: BLE001
    _aj = None


def _cfg(nombre, defecto):
    return getattr(_aj, nombre, defecto) if _aj is not None else defecto


# Por idioma: nombre de la fuente y sus feeds. Cada feed: (nombre que se muestra, url, es_portada)
_FUENTES_DEFECTO = {
    "es": {"fuente": "Ámbito", "feeds": (
        ("Finanzas", "https://www.ambito.com/rss/pages/finanzas.xml", False),
        ("Economía", "https://www.ambito.com/rss/pages/economia.xml", False),
        ("Portada", "https://www.ambito.com/rss/home.xml", True),
    )},
    "en": {"fuente": "CNBC", "feeds": (
        ("Mercados", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20409666", False),
        ("Tecnología", "https://www.cnbc.com/id/19854910/device/rss/rss.html", False),
        ("Economía", "https://www.cnbc.com/id/20910258/device/rss/rss.html", False),
        ("Portada", "https://www.cnbc.com/id/100003114/device/rss/rss.html", True),
    )},
}
# v1.5.24 (pedido de Guille): cada bloque junta VARIOS medios. Cada feed: (nombre de la seccion, url, es_portada, medio, idioma).
#   * Locales (3 notas): Ámbito, iProfesional y La Nación. Estados Unidos (5): CNBC, MarketWatch e Investing.com en español.
#     Resto del mundo (5): CNBC (Mundo, Europa, Asia), BBC, The Guardian, DW y South China Morning Post.
#   * Si un medio no responde lo llenan los otros; Ámbito (Locales) y CNBC (Estados Unidos y Resto del mundo) son el respaldo conocido.
#   * La primera nota de cada bloque es la «tendencia del día» (la historia que cubren más medios); después, la regla de siempre.
_LOC = (
    ("Finanzas", "https://www.ambito.com/rss/pages/finanzas.xml", False, "Ámbito", "es"),
    ("Economía", "https://www.ambito.com/rss/pages/economia.xml", False, "Ámbito", "es"),
    ("Portada", "https://www.ambito.com/rss/home.xml", True, "Ámbito", "es"),
    ("Finanzas", "https://www.iprofesional.com/rss/finanzas", False, "iProfesional", "es"),
    ("Economía", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/", False, "La Nación", "es"),
)
_USA = (
    ("Mercados", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20409666", False, "CNBC", "en"),
    ("Tecnología", "https://www.cnbc.com/id/19854910/device/rss/rss.html", False, "CNBC", "en"),
    ("Economía", "https://www.cnbc.com/id/20910258/device/rss/rss.html", False, "CNBC", "en"),
    ("Portada", "https://www.cnbc.com/id/100003114/device/rss/rss.html", True, "CNBC", "en"),
    ("Titulares", "https://feeds.content.dowjones.io/public/rss/mw_topstories", False, "MarketWatch", "en"),
    ("Empresas", "https://es.investing.com/rss/news.rss", False, "Investing.com", "es"),
    ("Bolsas", "https://es.investing.com/rss/news_25.rss", False, "Investing.com", "es"),
)
_MUN = (
    ("Mundo", "https://www.cnbc.com/id/100727362/device/rss/rss.html", False, "CNBC", "en"),
    ("Europa", "https://www.cnbc.com/id/19794221/device/rss/rss.html", False, "CNBC", "en"),
    ("Asia", "https://www.cnbc.com/id/19832390/device/rss/rss.html", False, "CNBC", "en"),
    ("Negocios", "https://feeds.bbci.co.uk/news/business/rss.xml", False, "BBC", "en"),
    ("Negocios", "https://www.theguardian.com/uk/business/rss", False, "The Guardian", "en"),
    ("Negocios", "https://rss.dw.com/rdf/rss-en-bus", False, "DW", "en"),
    ("Negocios", "https://www.scmp.com/rss/92/feed", False, "South China Morning Post", "en"),
)
_BLOQUES_DEFECTO = (
    {"clave": "locales", "titulo": "Locales", "fuente": "Ámbito, iProfesional y La Nación", "idioma": "es", "traducir": False, "cantidad": 3, "dolar": True, "mercado": True, "feeds": _LOC},
    {"clave": "usa", "titulo": "Estados Unidos", "fuente": "CNBC, MarketWatch e Investing.com", "idioma": "en", "traducir": True, "cantidad": 5, "feeds": _USA},
    {"clave": "mundo", "titulo": "Resto del mundo", "fuente": "CNBC, BBC, The Guardian, DW y SCMP", "idioma": "en", "traducir": True, "cantidad": 5, "feeds": _MUN},
)
ACTIVAS = bool(_cfg("NOTICIAS_ACTIVAS", True))
IDIOMA = str(_cfg("NOTICIAS_IDIOMA", "es")).strip().lower()
_FUENTES = _cfg("NOTICIAS_FUENTES", _FUENTES_DEFECTO)
_SEL = _FUENTES.get(IDIOMA) or _FUENTES.get("es") or _FUENTES_DEFECTO["es"]
if IDIOMA not in _FUENTES:
    IDIOMA = "es"
FUENTE = str(_SEL.get("fuente", "Ámbito"))
FEEDS = tuple(_SEL.get("feeds") or _FUENTES_DEFECTO["es"]["feeds"])
CANTIDAD = int(_cfg("NOTICIAS_CANTIDAD", 5))
HORAS = int(_cfg("NOTICIAS_HORAS", 24))
HORAS_MAX = int(_cfg("NOTICIAS_HORAS_MAX", 72))
MINUTOS_CACHE = int(_cfg("NOTICIAS_MINUTOS_CACHE", 15))
ABIERTO = bool(_cfg("NOTICIAS_ABIERTO", False))
# Traduccion automatica al español: solo tiene sentido con la fuente en ingles (IDIOMA = "en"). Ver ui/traducir.py.
TRADUCIR = bool(_cfg("NOTICIAS_TRADUCIR", False))   # v1.2.58: se traducen los bloques que lo pidan (los de fuente en ingles)
BLOQUES = tuple(_cfg("NOTICIAS_BLOQUES", _BLOQUES_DEFECTO) or _BLOQUES_DEFECTO)
TRADUCIR_MAIL = str(_cfg("NOTICIAS_TRADUCIR_MAIL", "") or _cfg("COMENTARIOS_MAIL", "") or "")
TIMEOUT_S = 8       # v1.5.24: antes 5; Ámbito tardó 7 s desde una PC común y ahora son más medios
USER_AGENT = "Mozilla/5.0 (compatible; TodoCedears/1.2; lector de titulares RSS; contacto: finanzas.medicos@gmail.com)"

# Como se nombra cada empresa en los titulares (el nombre de Yahoo, "Walt Disney Company (The)", no sirve para buscar).
# Se busca respetando mayusculas (Apple si, "apple" no) y como palabra entera. Los nombres que tambien son palabras
# comunes llevan un texto mas largo para no confundirse ("Target Corp", no "Target"; "Visa Inc", no "Visa").
ALIAS = {
    "LIN": ["Linde"], "BHP": ["BHP"], "RIO": ["Rio Tinto"], "SCCO": ["Southern Copper"],
    "FCX": ["Freeport-McMoRan", "Freeport"], "SHW": ["Sherwin-Williams"], "NEM": ["Newmont"], "VALE": ["Vale"],
    "AEM": ["Agnico Eagle"], "ECL": ["Ecolab"], "O": ["Realty Income"], "PLD": ["Prologis"], "WELL": ["Welltower"],
    "BRK-B": ["Berkshire Hathaway", "Berkshire"], "JPM": ["JPMorgan", "JP Morgan"], "MUFG": ["Mitsubishi UFJ", "MUFG"],
    "BAC": ["Bank of America"], "MS": ["Morgan Stanley"], "GS": ["Goldman Sachs", "Goldman"], "HSBC": ["HSBC"],
    "C": ["Citigroup", "Citi"], "AXP": ["American Express", "Amex"], "SCHW": ["Charles Schwab", "Schwab"],
    "BX": ["Blackstone"], "HDB": ["HDFC Bank"], "SAN": ["Banco Santander", "Santander"], "IBN": ["ICICI Bank"],
    "USB": ["U.S. Bancorp", "US Bancorp"], "BBVA": ["BBVA"], "ITUB": ["Itau Unibanco", "Itaú Unibanco", "Itaú"],
    "AIG": ["AIG", "American International Group"], "BNY": ["BNY Mellon", "Bank of New York Mellon", "BNY"],
    "ING": ["ING Groep", "ING Group", "ING"], "NU": ["Nu Holdings", "Nubank"], "IBKR": ["Interactive Brokers"],
    "V": ["Visa Inc", "Visa and Mastercard", "Mastercard and Visa", "Visa y Mastercard", "Mastercard y Visa"], "MA": ["Mastercard"], "SPGI": ["S&P Global"],
    "PYPL": ["PayPal"], "COIN": ["Coinbase"], "FISV": ["Fiserv"], "MRSH": ["Marsh McLennan"],
    "AMZN": ["Amazon"], "TSLA": ["Tesla"], "HD": ["Home Depot"], "BABA": ["Alibaba"], "TM": ["Toyota"],
    "BKNG": ["Booking Holdings", "Booking.com"], "PDD": ["PDD Holdings", "PDD", "Temu", "Pinduoduo"],
    "MELI": ["MercadoLibre", "Mercado Libre"], "SONY": ["Sony"], "RACE": ["Ferrari"], "NKE": ["Nike"],
    "MCD": ["McDonald's", "McDonald’s"], "SBUX": ["Starbucks"], "TJX": ["TJX"], "ABNB": ["Airbnb"],
    "ORLY": ["O'Reilly Automotive", "O’Reilly Automotive"], "GM": ["General Motors"], "ROST": ["Ross Stores"],
    "GOOGL": ["Alphabet", "Google"], "META": ["Meta Platforms", "Meta"], "NFLX": ["Netflix"], "DIS": ["Disney"],
    "SPOT": ["Spotify"], "NTES": ["NetEase"], "T": ["AT&T"], "VZ": ["Verizon"], "TMUS": ["T-Mobile"],
    "CAT": ["Caterpillar"], "GE": ["GE Aerospace"], "RTX": ["RTX"], "SIEGY": ["Siemens"], "DE": ["Deere"],
    "UNP": ["Union Pacific"], "UBER": ["Uber"], "LMT": ["Lockheed Martin", "Lockheed"], "HON": ["Honeywell"],
    "BA": ["Boeing"], "MMM": ["3M"], "FDX": ["FedEx"], "GEV": ["GE Vernova"], "HWM": ["Howmet"],
    "PCAR": ["Paccar", "PACCAR"], "NVDA": ["Nvidia", "NVIDIA"], "TSM": ["TSMC", "Taiwan Semiconductor"],
    "AVGO": ["Broadcom"], "MU": ["Micron"], "AMD": ["AMD", "Advanced Micro Devices"], "ASML": ["ASML"],
    "INTC": ["Intel"], "AMAT": ["Applied Materials"], "ARM": ["Arm Holdings"], "TXN": ["Texas Instruments"],
    "MRVL": ["Marvell"], "ADI": ["Analog Devices"], "QCOM": ["Qualcomm", "QUALCOMM"], "LRCX": ["Lam Research"],
    "KLAC": ["KLA"], "MSFT": ["Microsoft"], "ORCL": ["Oracle"], "PLTR": ["Palantir"], "PANW": ["Palo Alto Networks"],
    "CRWD": ["CrowdStrike"], "SAP": ["SAP"], "SHOP": ["Shopify"], "CRM": ["Salesforce"], "NOW": ["ServiceNow"],
    "ADBE": ["Adobe"], "SNOW": ["Snowflake"], "AAPL": ["Apple"], "CSCO": ["Cisco"], "ANET": ["Arista"],
    "IBM": ["IBM"], "ACN": ["Accenture"], "ADP": ["Automatic Data Processing"], "INFY": ["Infosys"], "DELL": ["Dell"],
    "MSI": ["Motorola Solutions"], "WDC": ["Western Digital"], "XOM": ["Exxon", "ExxonMobil", "Exxon Mobil"],
    "CVX": ["Chevron"], "SHEL": ["Shell Plc", "Shell PLC", "Shell"], "TTE": ["TotalEnergies"], "COP": ["ConocoPhillips"],
    "PBR": ["Petrobras"], "SLB": ["SLB", "Schlumberger"], "BP": ["BP"], "EQNR": ["Equinor"], "PSX": ["Phillips 66"],
    "WMT": ["Walmart"], "COST": ["Costco"], "KO": ["Coca-Cola", "Coca Cola"], "PG": ["Procter & Gamble"], "PM": ["Philip Morris"],
    "PEP": ["PepsiCo", "Pepsi"], "UL": ["Unilever"], "TGT": ["Target Corp"], "MDLZ": ["Mondelez"], "MO": ["Altria"],
    "CL": ["Colgate-Palmolive", "Colgate"], "DEO": ["Diageo"], "LLY": ["Eli Lilly", "Lilly"],
    "JNJ": ["Johnson & Johnson"], "ABBV": ["AbbVie"], "MRK": ["Merck"], "UNH": ["UnitedHealth"], "NVS": ["Novartis"],
    "TMO": ["Thermo Fisher"], "AMGN": ["Amgen"], "GILD": ["Gilead"], "ABT": ["Abbott"], "PFE": ["Pfizer"],
    "DHR": ["Danaher"], "ISRG": ["Intuitive Surgical"], "VRTX": ["Vertex Pharmaceuticals"], "NVO": ["Novo Nordisk"],
    "BMY": ["Bristol-Myers Squibb", "Bristol Myers"], "MDT": ["Medtronic"], "GSK": ["GSK"], "AZN": ["AstraZeneca"],
    "CVS": ["CVS"], "NEE": ["NextEra"], "CEG": ["Constellation Energy"], "VST": ["Vistra"], "TLN": ["Talen Energy"],
    # v1.5.24: las 49 empresas de la tanda 1 (para que sus noticias cuenten como "del screener"; los nombres que son palabras comunes llevan el texto largo)
    "NUE": ["Nucor"], "MOS": ["Mosaic Co", "Mosaic Company"], "DD": ["DuPont"], "DOW": ["Dow Inc"], "IP": ["International Paper"],
    "IFF": ["International Flavors", "International Flavors & Fragrances"], "WFC": ["Wells Fargo"], "BCS": ["Barclays"], "LYG": ["Lloyds Banking", "Lloyds"],
    "F": ["Ford Motor", "Ford"], "EBAY": ["eBay"], "CCL": ["Carnival"], "LVS": ["Las Vegas Sands"], "DECK": ["Deckers"], "JD": ["JD.com"],
    "AVY": ["Avery Dennison"], "PINS": ["Pinterest"], "SNAP": ["Snap Inc", "Snapchat"], "ROKU": ["Roku"], "BIDU": ["Baidu"],
    "AMX": ["America Movil", "América Móvil"], "VOD": ["Vodafone"], "JCI": ["Johnson Controls"], "SNA": ["Snap-on"], "DAL": ["Delta Air Lines", "Delta Airlines"],
    "UAL": ["United Airlines"], "AAL": ["American Airlines"], "SWKS": ["Skyworks"], "ALAB": ["Astera Labs"], "DOCU": ["DocuSign"], "TWLO": ["Twilio"],
    "TEAM": ["Atlassian"], "VRSN": ["VeriSign", "Verisign"], "HPQ": ["HP Inc"], "GLW": ["Corning"], "GRMN": ["Garmin"], "SNDK": ["SanDisk", "Sandisk"],
    "OXY": ["Occidental Petroleum", "Occidental"], "BKR": ["Baker Hughes"], "HAL": ["Halliburton"], "CCJ": ["Cameco"], "HSY": ["Hershey"],
    "KMB": ["Kimberly-Clark"], "SYY": ["Sysco"], "BG": ["Bunge"], "BIIB": ["Biogen"], "MRNA": ["Moderna"], "CAH": ["Cardinal Health"], "NTRA": ["Natera"],
}
# Tickers que tambien son palabras o siglas comunes: no se buscan como ticker (si por nombre).
_TICKER_NO_BUSCAR = {"NOW", "ARM", "CAT", "WELL", "COST", "DELL", "SNOW", "LIN", "ALL"}
# Nombres que en español tambien son palabras comunes ("Meta de inflación", "Vale la pena", "Arista"): como los titulares
# llevan mayuscula solo al empezar, estas formas cuentan unicamente si NO estan al comienzo del titular (solo con titulares en español).
_NO_AL_INICIO = {"Meta", "Vale", "Arista", "Target"}

# Frases que nombran a dos empresas juntas: se marcan las dos ("Visa y Mastercard")
_CONJUNTAS = {f: ("V", "MA") for f in ("Visa and Mastercard", "Mastercard and Visa", "Visa y Mastercard", "Mastercard y Visa")}

_PAT_CACHE = {}


def _patron(tickers):
    """Regex unica con todas las formas de nombrar a las empresas del screener -> {texto_encontrado: ticker}."""
    clave = tuple(sorted(tickers))
    if clave in _PAT_CACHE:
        return _PAT_CACHE[clave]
    formas = {}
    for t in clave:
        for a in ALIAS.get(t, []):
            formas.setdefault(a, t)
        if len(t) >= 3 and t not in _TICKER_NO_BUSCAR and re.fullmatch(r"[A-Z]+", t):
            formas.setdefault(t, t)
    if not formas:
        pat = None
    else:
        orden = sorted(formas, key=len, reverse=True)  # primero las formas largas ("Meta Platforms" antes que "Meta")
        pat = re.compile(r"(?<![\w&])(" + "|".join(re.escape(f) for f in orden) + r")(?!\w)(?!\.\w)")
    _PAT_CACHE[clave] = (pat, formas)
    return _PAT_CACHE[clave]


def buscar_menciones(titulo, tickers, idioma=None):
    """Tickers de las empresas del screener que se nombran en el titular (sin repetir, en orden de aparicion)."""
    pat, formas = _patron(tickers)
    if pat is None or not titulo:
        return []
    out = []
    tset = set(tickers or [])
    for m in pat.finditer(titulo):
        if (idioma or IDIOMA) == "es" and m.group(1) in _NO_AL_INICIO and m.start() == 0:
            continue
        for t in _CONJUNTAS.get(m.group(1)) or (formas.get(m.group(1)),):
            if t and t in tset and t not in out:
                out.append(t)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Descarga y lectura de los feeds
# ---------------------------------------------------------------------------------------------------------------
def _descargar(url, timeout=TIMEOUT_S):
    """Bytes del feed, o None si no se pudo (sin conexion, bloqueo, error del sitio)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.5"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (url fija de ajustes, https)
            return r.read(3_000_000)
    except Exception:  # noqa: BLE001
        return None


def _texto(el):
    return (el.text or "").strip() if el is not None else ""


_DE_PAGO = re.compile(r"(?i)\bCNBC Pro\b|/pro/")


def es_de_pago(titulo, link):
    """Notas marcadas como "CNBC Pro" (de pago): no se muestran, porque se quiere que todo link se pueda leer gratis."""
    return bool(_DE_PAGO.search(titulo or "") or _DE_PAGO.search(link or ""))


def _link_seguro(url):
    u = (url or "").strip()
    return u if re.match(r"(?i)^https?://", u) else ""


def _clave_link(url):
    """Misma nota con o sin parametros de seguimiento -> misma clave."""
    try:
        p = urlsplit(url)
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:  # noqa: BLE001
        return url


def _fecha(txt):
    if not txt:
        return None
    try:
        d = parsedate_to_datetime(txt.strip())
    except Exception:  # noqa: BLE001
        try:
            d = datetime.fromisoformat(txt.strip().replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            return None
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def leer_feed(contenido):
    """Notas de un feed RSS 2.0 o Atom -> lista de {titulo, link, fecha}. Si el XML viene roto devuelve []."""
    if not contenido:
        return []
    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError:
        return []
    notas = []
    for el in raiz.iter():
        etiqueta = el.tag.rsplit("}", 1)[-1]
        if etiqueta not in ("item", "entry"):
            continue
        titulo = link = fecha = ""
        for h in el:
            e = h.tag.rsplit("}", 1)[-1]
            if e == "title":
                titulo = _texto(h)
            elif e == "link":
                link = _texto(h) or (h.get("href") or "")
            elif e in ("pubDate", "published", "updated", "date") and not fecha:
                fecha = _texto(h)
            elif e in ("guid", "id") and not link and _texto(h).lower().startswith("http"):
                link = _texto(h)
        titulo = re.sub(r"\s+", " ", html.unescape(titulo)).strip()
        link = _link_seguro(link)
        if titulo and link and not es_de_pago(titulo, link):
            notas.append({"titulo": titulo, "link": link, "fecha": _fecha(fecha)})
    return notas


_LOCK = threading.Lock()
_ESTADO = {"ts": 0.0, "crudo": None}   # crudo = {"notas": [...], "portada": set(claves), "feeds_ok": n}
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="noticias")
_FUTURO = {"f": None}


def _armar_bloque(feeds, leidos):
    """Notas de un bloque a partir de los feeds ya leidos ({url: [notas]}). Cada feed puede traer (nombre, url, es_portada, medio, idioma);
    con los tres primeros solamente (formato viejo) la nota hereda el medio y el idioma del bloque."""
    notas, portada, ok = {}, set(), 0
    for f in feeds:
        nombre, url, es_portada = f[0], f[1], f[2]
        medio = f[3] if len(f) > 3 else None
        idioma = f[4] if len(f) > 4 else None
        lista = leidos.get(url) or []
        if lista:
            ok += 1
        for n in lista:
            k = _clave_link(n["link"])
            if es_portada:
                portada.add(k)
                continue
            if k not in notas:
                extra = {}
                if medio:
                    extra["medio"] = medio
                if idioma:
                    extra["idioma"] = idioma
                notas[k] = {**n, "seccion": nombre, "clave": k, **extra}
    return {"notas": list(notas.values()), "portada": portada, "feeds_ok": ok, "feeds_total": len(feeds)}


def _bajar_todo(descargar=None):
    """Baja (en paralelo) los feeds de todos los bloques. -> {"bloques": {clave: crudo del bloque}, "feeds_ok": n, "feeds_total": n}."""
    descargar = descargar or _descargar
    urls = []
    for b in BLOQUES:
        for f in b["feeds"]:
            if f[1] not in urls:
                urls.append(f[1])
    with ThreadPoolExecutor(max_workers=max(1, min(20, len(urls)))) as ex:
        contenidos = list(ex.map(descargar, urls))
    leidos = {u: leer_feed(c) for u, c in zip(urls, contenidos)}
    bloques = {b["clave"]: _armar_bloque(b["feeds"], leidos) for b in BLOQUES}
    return {"bloques": bloques, "feeds_ok": sum(1 for v in leidos.values() if v), "feeds_total": len(urls)}


def _crudo(descargar=None, ahora_ts=None, forzar=False):
    """Descarga (o reutiliza lo bajado hace menos de MINUTOS_CACHE). Si todo falla, conserva lo ultimo bueno."""
    ahora_ts = time.time() if ahora_ts is None else ahora_ts
    with _LOCK:
        vigente = _ESTADO["crudo"] is not None and (ahora_ts - _ESTADO["ts"]) < MINUTOS_CACHE * 60
        if vigente and not forzar:
            return _ESTADO["crudo"]
    nuevo = _bajar_todo(descargar)
    with _LOCK:
        if nuevo["feeds_ok"] > 0:
            _ESTADO["crudo"], _ESTADO["ts"] = nuevo, ahora_ts
        elif _ESTADO["crudo"] is None:
            # primera vez y no respondio nadie: se guarda el vacio pero se vuelve a probar en 3 minutos
            _ESTADO["crudo"], _ESTADO["ts"] = nuevo, ahora_ts - (MINUTOS_CACHE - 3) * 60
        else:
            # no respondio ninguno: se reintenta pronto, pero se muestra lo ultimo que se pudo bajar
            _ESTADO["ts"] = ahora_ts - (MINUTOS_CACHE - 2) * 60
        return _ESTADO["crudo"]


def iniciar_descarga():
    """Arranca la descarga en segundo plano (mientras la app carga los datos de las empresas). Devuelve un futuro o None."""
    if not ACTIVAS:
        return None
    with _LOCK:
        if _ESTADO["crudo"] is not None and (time.time() - _ESTADO["ts"]) < MINUTOS_CACHE * 60:
            return None
    try:
        return _POOL.submit(_crudo)
    except Exception:  # noqa: BLE001
        return None


def esperar(futuro, espera_s=TIMEOUT_S + 2):
    """Resultado crudo de la descarga en segundo plano (o lo guardado); None si no se pudo."""
    try:
        if futuro is not None:
            return futuro.result(timeout=espera_s)
        with _LOCK:
            return _ESTADO["crudo"]
    except Exception:  # noqa: BLE001
        with _LOCK:
            return _ESTADO["crudo"]


# ---------------------------------------------------------------------------------------------------------------
# Orden de las notas
# ---------------------------------------------------------------------------------------------------------------
# v1.2.85 (pedido de Guille): sin relleno. Las notas que no tienen que ver con el mercado (Halloween, horóscopo, farándula, deportes...) no entran, y las cotizaciones
# del dólar del día ("Dólar hoy", "Dólar blue hoy", "minuto a minuto") cuentan como una sola: sale la más reciente. Si quedan menos de 5 notas, se muestran menos.
_RELLENO = re.compile(r"halloween|disfraz|hor[oó]scopo|\bsigno\b|receta|far[aá]ndula|chimento|quiniela|loter[ií]a|pron[oó]stico del tiempo|\bclima\b|gran hermano|\bmessi\b|"
                      r"\bboca\b|\briver\b|selecci[oó]n argentina|\bcostume|horoscope|\brecipe|celebrity", re.I)
_DOLAR_DIA = re.compile(r"d[oó]lar\b.*\b(hoy|cotiza|opera|minuto a minuto|a cu[aá]nto)|\b(hoy|a cu[aá]nto)\b.*d[oó]lar\b|cotizaci[oó]n del d[oó]lar|minuto a minuto", re.I)


# v1.5.2: notas "macro" (Fed, inflación, tasas, empleo, aranceles, petróleo...) y notas del mercado argentino (Merval, bonos, riesgo país...)
_MACRO = re.compile(r"\bfed\b|federal reserve|reserva federal|powell|inflaci[oó]n|inflation|\bcpi\b|\bpce\b|tasas? de inter[eé]s|interest rates?|rate (cut|hike)|rates?\b|"
                    r"jobs report|payrolls?|nonfarm|empleo|desempleo|unemployment|jobless|\bgdp\b|\bpbi\b|econom[ií]a|economy|economic|tariffs?|aranceles?|treasury|"
                    r"bonos? del tesoro|yields?|recession|recesi[oó]n|central bank|banco central|\bbce\b|\becb\b|bank of (japan|england)|\bboj\b|\bboe\b|"
                    r"oil prices?|precio del petr[oó]leo|\bopec\b|retail sales|consumer (confidence|spending|sentiment)|shutdown|trade (deal|war|talks)|"
                    r"d[eé]ficit|deficit|debt ceiling|stimulus|estímulo", re.I)
_MERCADO_AR = re.compile(r"merval|\bbonos?\b|riesgo pa[ií]s|\badrs?\b|\bcedears?\b|\bbolsa\b|acciones|t[ií]tulos p[uú]blicos|renta fija|\blecaps?\b|\bletras?\b|"
                         r"licitaci[oó]n|\bon\b|obligaciones negociables|mercado de capitales|\bcaucion", re.I)


def es_macro(titulo):
    return bool(_MACRO.search(titulo or ""))


def es_relleno(titulo):
    """True si el titular no tiene que ver con el mercado (Halloween, horóscopo, deportes, farándula...)."""
    return bool(_RELLENO.search(titulo or ""))


def _quitar_relleno(ordenadas):
    """Saca las notas de relleno y deja una sola cotización del dólar del día (la primera, que es la mejor ubicada)."""
    salida, hubo_dolar = [], False
    for n in ordenadas:
        t = n.get("titulo") or ""
        if es_relleno(t):
            continue
        if _DOLAR_DIA.search(t):
            if hubo_dolar:
                continue
            hubo_dolar = True
        salida.append(n)
    return salida


# ---------------------------------------------------------------------------------------------------------------
# Historias y tendencia del dia (v1.5.24)
# ---------------------------------------------------------------------------------------------------------------
# Dos titulares cuentan la MISMA historia si comparten al menos 2 palabras importantes (sin las palabras comunes: «mercado», «acciones», «Wall Street»...).
# La tendencia del dia de un bloque es la historia que cubren mas medios distintos. Un par de palabras en castellano se pasan al ingles para que
# «victoria demócrata» y «Democrats win» se reconozcan. No es perfecto (es una comparacion de palabras, no de significado): si no hay una
# historia cubierta por al menos 2 medios, no se marca ninguna tendencia y el bloque sigue con la regla de siempre.
_PARES_ES_EN = {"democrata": "democrat", "democratas": "democrat", "republicano": "republican", "republicanos": "republican", "elecciones": "election",
                "eleccion": "election", "legislativas": "midterm", "congreso": "congress", "senado": "senate", "arancel": "tariff", "aranceles": "tariff",
                "inflacion": "inflation", "petroleo": "oil", "dolar": "dollar", "dolares": "dollar", "tasas": "rate", "tasa": "rate", "reserva": "reserve",
                "banco": "bank", "bancos": "bank", "ganancias": "earnings", "resultados": "earnings", "empleo": "job", "despidos": "layoff",
                "recorte": "cut", "recortes": "cut", "guerra": "war", "gobierno": "government", "presidente": "president", "victoria": "victory", "triunfo": "victory"}
_CORTAS_OK = {"fed", "oil", "gdp", "cpi", "ecb", "imf", "opec", "ai", "ipo", "pbi", "bce", "fmi"}
_STOP = set("""the and for with from that this after over into amid says said will what how why new more than have has are was its about could would week today year years
first live business news update updates their they them his her you your not but out off all one two three can may might also still now just much many most some
stock stocks share shares market markets rally trade trading price prices investor investors wall street analyst analysts company companies report reports
para como esta este estos estas hoy tras entre sobre desde hasta cuando donde porque mas menos anos semana mercado mercados bolsa bolsas acciones accion
inversores noticias empresa empresas segun sera tiene hacen hace dice fue son ser una uno unos unas los las del por con sin que cual ante bajo
estados unidos united states eeuu norteamericana nueva nuevo""".split())


@functools.lru_cache(maxsize=4096)
def tokens_historia(titulo):
    """Palabras importantes de un titular (en minuscula, sin acentos, en singular, castellano -> ingles en las pocas palabras de arriba)."""
    t = unicodedata.normalize("NFKD", (titulo or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    out = set()
    for w in re.findall(r"[a-z0-9]+", t):
        w = _PARES_ES_EN.get(w, w)
        if len(w) > 4 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if w in _STOP or (len(w) < 4 and w not in _CORTAS_OK) or w.isdigit():
            continue
        out.add(w)
    return frozenset(out)


def misma_historia(a, b):
    """a y b: conjuntos de palabras (tokens_historia). True si comparten al menos 2 y esas 2 son por lo menos el 25 % del titular mas corto."""
    if not a or not b:
        return False
    c = len(a & b)
    return c >= 2 and c >= 0.25 * min(len(a), len(b))


def _repite_historia(n, historias):
    tk = tokens_historia(n.get("titulo"))
    return any(misma_historia(tk, h) for h in historias)


def _elegir_tendencia(base, vistos_tickers, historias):
    """La nota de `base` (ya sin relleno) que cuenta la historia cubierta por mas medios distintos (minimo 2), a igualdad la mas reciente. None si no hay."""
    minimo = datetime.min.replace(tzinfo=timezone.utc)
    mejor, mejor_k = None, None
    for n in base:
        m = n.get("menciona") or []
        if m and any(t in vistos_tickers for t in m):
            continue
        tk = tokens_historia(n["titulo"])
        if not tk or any(misma_historia(tk, h) for h in historias):
            continue
        medios = {n.get("fuente")}
        for o in base:
            if o is not n and misma_historia(tk, tokens_historia(o["titulo"])):
                medios.add(o.get("fuente"))
        if len(medios) < 2:
            continue
        k = (len(medios), n["en_portada"], n["fecha"] or minimo)
        if mejor_k is None or k > mejor_k:
            mejor, mejor_k = n, k
    return mejor



def _sin_repetir_ticker(ordenadas, cantidad, vistos_ini=None, historias=None, max_por_medio=None, medios_ini=None):
    """Recorre las notas ya ordenadas por importancia y se queda con una sola por empresa: si una nota nombra un ticker que ya
    salio en una nota mas importante, se saltea y se sigue con la proxima. Las que no nombran empresas no se tocan.
    v1.5.24: tampoco repite una historia que ya salio (la misma noticia de dos medios), y con `max_por_medio` ningun medio pasa de ese numero de notas;
    si con ese tope no se llega a `cantidad` (porque otros medios no respondieron), se completa con los que quedaron."""
    vistos, salida, hist = set(vistos_ini or ()), [], list(historias or [])
    cuenta, salteadas = {}, []
    for m_ in (medios_ini or ()):
        cuenta[m_] = cuenta.get(m_, 0) + 1

    def _ok(n):
        m = n.get("menciona") or []
        if m and any(t in vistos for t in m):
            return False
        return not (hist and _repite_historia(n, hist))

    def _tomar(n):
        salida.append(n)
        vistos.update(n.get("menciona") or [])
        hist.append(tokens_historia(n.get("titulo")))
        cuenta[n.get("fuente")] = cuenta.get(n.get("fuente"), 0) + 1

    for n in ordenadas:
        if len(salida) >= cantidad:
            break
        if not _ok(n):
            continue
        if max_por_medio and cuenta.get(n.get("fuente"), 0) >= max_por_medio:
            salteadas.append(n)
            continue
        _tomar(n)
    for n in salteadas:
        if len(salida) >= cantidad:
            break
        if _ok(n):
            _tomar(n)
    return salida


def ordenar(crudo, tickers, ahora=None, cantidad=None, horas=None, horas_max=None, fuente=None, idioma=None, excluir=None, con_dolar=False,
            vistos_tickers=None, con_mercado=False, con_macro=False, historias=None, con_tendencia=True, max_por_medio=2):
    """Aplica la regla: ventana de 24 h (se amplia a 48 y 72 h si no alcanzan `cantidad` notas), orden por
    (menciona empresas del screener, esta en portada, mas reciente) y una sola nota por ticker (v1.2.46: se saltea la repetida y se
    sigue con la que viene). Devuelve (lista, horas_usadas).
    v1.5.24: (1) la PRIMERA nota es la tendencia del dia (la historia que cubren mas medios distintos, haya o no empresas del screener; `tendencia`=True);
    (2) la misma historia no sale dos veces (ni en otro bloque: `historias`); (3) con varios medios en el bloque, ninguno pasa de `max_por_medio`
    notas, salvo que los otros no alcancen a llenar el bloque."""
    cantidad = CANTIDAD if cantidad is None else cantidad
    horas = HORAS if horas is None else horas
    horas_max = HORAS_MAX if horas_max is None else horas_max
    ahora = ahora or datetime.now(timezone.utc)
    if not crudo or not crudo.get("notas"):
        return [], horas
    ventanas = [horas] + [h for h in (48, 72) if horas < h <= horas_max]
    portada = crudo.get("portada") or set()
    tickers = list(tickers or [])
    minimo = datetime.min.replace(tzinfo=timezone.utc)
    usadas, salida = horas, []
    for h in ventanas:
        usadas = h
        lim = ahora - timedelta(hours=h)
        elegibles = [n for n in crudo["notas"] if (n["fecha"] is None or lim <= n["fecha"] <= ahora + timedelta(minutes=10))
                     and n["clave"] not in (excluir or ())]
        todas = [{**n, "menciona": buscar_menciones(n["titulo"], tickers, n.get("idioma") or idioma), "en_portada": n["clave"] in portada,
                  "fuente": n.get("medio") or fuente or FUENTE} for n in elegibles]
        todas.sort(key=lambda n: (bool(n["menciona"]), n["en_portada"], n["fecha"] or minimo), reverse=True)
        hist = list(historias or [])
        base = [n for n in _quitar_relleno(todas) if not (hist and _repite_historia(n, hist))]
        vt = set(vistos_tickers or ())
        tend = _elegir_tendencia(base, vt, hist) if (con_tendencia and cantidad >= 2) else None
        if tend is not None:
            tend["tendencia"] = True
            tk_t = tokens_historia(tend["titulo"])
            parecidas = [n for n in base if n is not tend and misma_historia(tokens_historia(n["titulo"]), tk_t)]
            huella = frozenset(tk_t.union(*[tokens_historia(n["titulo"]) for n in parecidas]))      # todas las palabras con que los medios cuentan la historia
            tend["historia"] = huella
            base = [n for n in base if n is not tend and not any(n is q for q in parecidas)]
            vt.update(tend.get("menciona") or [])
            hist.append(huella)
        falta = cantidad - (1 if tend is not None else 0)
        # v1.2.87: se reserva un lugar para la nota de "cómo está el dólar hoy" (la mejor ubicada). v1.5.2: también uno para el mercado argentino
        # (Merval, bonos, riesgo país) en Locales y uno para una nota macro (Fed, inflación, tasas...) cuando hace falta; el resto se completa en el mismo orden.
        reservas = []
        def _reservar(pred):
            for n in base:
                if any(n is r for r in reservas) or not pred(n.get("titulo") or ""):
                    continue
                m = n.get("menciona") or []
                if m and any(t in vt or any(t in (r.get("menciona") or []) for r in reservas) for t in m):
                    continue
                reservas.append(n)
                return
        if con_dolar:
            _reservar(lambda t: bool(_DOLAR_DIA.search(t)))
        if con_mercado:
            _reservar(lambda t: bool(_MERCADO_AR.search(t)) and not _DOLAR_DIA.search(t))
        if con_macro:
            _reservar(es_macro)
        vr = set(vt)
        for r in reservas:
            vr.update(r.get("menciona") or [])
        hr = hist + [tokens_historia(r["titulo"]) for r in reservas]
        multi = len({n["fuente"] for n in base}) > 1
        medios_ini = ([tend["fuente"]] if tend is not None else []) + [r["fuente"] for r in reservas]
        otras = _sin_repetir_ticker([n for n in base if not any(n is r for r in reservas)], max(falta - len(reservas), 0), vr,
                                    historias=hr, max_por_medio=(max_por_medio if multi else None), medios_ini=medios_ini)
        elegidas = otras + reservas
        resto = [n for n in base if any(n is e for e in elegidas)]
        salida = ([tend] if tend is not None else []) + resto
        if len(salida) >= cantidad:
            break
    return salida, usadas


def traducir_notas(notas, traducir_lista=None):
    """Agrega `titulo_es` a las notas que se pudieron traducir (solo si TRADUCIR esta activo; si no, devuelve las notas tal cual).
    Las menciones de empresas ya se buscaron en el titulo original: esto solo cambia lo que se lee."""
    if not TRADUCIR or not notas:
        return notas
    try:
        if traducir_lista is None:
            from ui.traducir import traducir_lista
        mapa = traducir_lista([n["titulo"] for n in notas], TRADUCIR_MAIL)
        return [{**n, "titulo_es": mapa[n["titulo"]]} if n["titulo"] in mapa else n for n in notas]
    except Exception:  # noqa: BLE001
        return notas


def ordenar_bloques(crudo, tickers, ahora=None):
    """Aplica la regla de `ordenar` a cada bloque (Locales, Estados Unidos, Resto del mundo). Una nota no sale en dos bloques.
    v1.5.2: una empresa no se repite en todo el cuadro (antes era por bloque: Intel salía una vez en cada uno), Locales reserva una nota del mercado
    argentino y entre Estados Unidos y Resto del mundo tiene que haber al menos una nota macro (si no hay ninguna buena, quedan las de empresas).
    v1.5.24: tampoco se repite una misma historia en todo el cuadro, y cada bloque abre con su tendencia del día.
    -> lista de {clave, titulo, fuente, idioma, traducir, notas, horas, respondio}."""
    vistos, vt, hist = set(), set(), []
    res = {}

    def _uno(b, con_macro=False, vistos_ext=None, tk_ext=None):
        cb = ((crudo or {}).get("bloques") or {}).get(b["clave"])
        notas, horas = ordenar(cb, tickers, ahora=ahora, fuente=b["fuente"], idioma=b["idioma"], excluir=(vistos_ext if vistos_ext is not None else vistos),
                               cantidad=b.get("cantidad"), con_dolar=bool(b.get("dolar")), vistos_tickers=(tk_ext if tk_ext is not None else vt),
                               con_mercado=bool(b.get("mercado")), con_macro=con_macro, historias=hist)
        return cb, notas, horas

    def _marcar(notas):
        vistos.update(n["clave"] for n in notas)
        for n in notas:
            vt.update(n.get("menciona") or [])
            hist.append(n.get("historia") or tokens_historia(n.get("titulo")))

    orden = list(BLOQUES)
    for b in orden:
        if b["clave"] in ("usa", "mundo"):
            continue
        res[b["clave"]] = _uno(b)
        _marcar(res[b["clave"]][1])
    ext = [b for b in orden if b["clave"] in ("usa", "mundo")]
    # primero se arman sin forzar; si ninguna es macro se rearma el primer bloque que tenga una nota macro disponible
    base_v, base_t, base_h = set(vistos), set(vt), list(hist)
    tmp = {}
    for b in ext:
        tmp[b["clave"]] = _uno(b, False, vistos, vt)
        _marcar(tmp[b["clave"]][1])
    if ext and not any(es_macro(n.get("titulo")) for k in tmp for n in tmp[k][1]):
        for forzar in reversed(ext):          # se intenta primero en Resto del mundo y después en Estados Unidos
            vistos.clear(); vistos.update(base_v); vt.clear(); vt.update(base_t); hist[:] = base_h
            tmp2 = {}
            for b in ext:
                tmp2[b["clave"]] = _uno(b, b is forzar, vistos, vt)
                _marcar(tmp2[b["clave"]][1])
            if any(es_macro(n.get("titulo")) for k in tmp2 for n in tmp2[k][1]):
                tmp = tmp2
                break
    res.update(tmp)
    salida = []
    for b in orden:
        cb, notas, horas = res[b["clave"]]
        salida.append({"clave": b["clave"], "titulo": b["titulo"], "fuente": b["fuente"], "idioma": b["idioma"],
                       "traducir": bool(b.get("traducir")), "notas": notas, "horas": horas,
                       "respondio": bool(cb and cb.get("feeds_ok"))})
    return salida


def _a_traducir(n, b):
    """v1.5.24: en un bloque con varios medios solo se traducen los titulares en inglés (los de Investing.com en español no)."""
    return (n.get("idioma") or b.get("idioma") or "en") == "en"


def traducir_bloques(bloques, traducir_lista=None):
    """Agrega `titulo_es` a las notas de los bloques que piden traduccion (una sola consulta para todos). Si falla, quedan en su idioma."""
    if not TRADUCIR or not bloques:
        return bloques
    titulos = [n["titulo"] for b in bloques if b.get("traducir") for n in b["notas"] if _a_traducir(n, b)]
    if not titulos:
        return bloques
    try:
        if traducir_lista is None:
            from ui.traducir import traducir_lista
        mapa = traducir_lista(titulos, TRADUCIR_MAIL) or {}
    except Exception:  # noqa: BLE001
        return bloques
    out = []
    for b in bloques:
        if b.get("traducir"):
            b = {**b, "notas": [{**n, "titulo_es": mapa[n["titulo"]]} if (_a_traducir(n, b) and n["titulo"] in mapa) else n for n in b["notas"]]}
        out.append(b)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Dibujo
# ---------------------------------------------------------------------------------------------------------------
CSS = """
.nt{margin:0;border:0;border-radius:14px;background:#fff;padding:0 16px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07)}
.nt>summary{cursor:pointer;list-style:none;padding:0;min-height:48px;box-sizing:border-box;align-items:center!important;font-weight:700;font-size:1.02rem;color:#1d4ed8;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.nt>summary::-webkit-details-marker{display:none}
.nt>summary::before{content:"▸";color:#6b7280;font-size:.85rem}
.nt[open]>summary::before{content:"▾"}
.nt>summary small{font-weight:500;color:#6b7280;font-size:.78rem}
.nt ul{list-style:none;margin:0 0 6px;padding:0}
.nt li{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;padding:8px 0;border-top:1px solid #eef1f4;font-size:.9rem;line-height:1.35}
.nt li a{color:#111827!important;font-weight:600;text-decoration:none!important;flex:1 1 220px;min-width:0}
.nt li a:hover{text-decoration:underline!important}
.nt-m{font-size:.76rem;color:#6b7280;white-space:nowrap}
.nt-t{font-size:.72rem;font-weight:700;color:#9a3412;background:#ffedd5;border-radius:999px;padding:1px 8px;white-space:nowrap}
.nt-e{font-size:.72rem;font-weight:700;color:#065f46;background:#d1fae5;border-radius:999px;padding:1px 8px;white-space:nowrap}
.nt-b{font-size:.74rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#111827;margin:10px 0 2px;padding:6px 0 0;border-top:2px solid #111827;display:flex;gap:8px;align-items:baseline}
.nt-b small{font-weight:500;letter-spacing:0;text-transform:none;color:#6b7280;font-size:.74rem}
.nt-b:first-of-type{margin-top:2px;border-top:0;padding-top:0}
.nt-b{border-top:0!important;margin:12px 0 4px!important;padding:6px 10px!important;border-radius:8px;color:var(--ntc,#111827)!important;background:var(--ntf,#f3f4f6);border-left:5px solid var(--ntc,#111827)}
.nt-b:first-of-type{margin-top:6px!important}
.nt-locales{--ntc:#0b3a5c;--ntf:#cfe8fa}.nt-usa{--ntc:#fff;--ntf:#1e3a8a}.nt-usa small{color:#c7d2fe!important}.nt-mundo{--ntc:#6d28d9;--ntf:#ede9fe}
.nt-ul-locales li{border-left:3px solid #9fd0f2;padding-left:10px}.nt-ul-usa li{border-left:3px solid #1e3a8a;padding-left:10px}.nt-ul-mundo li{border-left:3px solid #c4b5fd;padding-left:10px}
.nt-pie{font-size:.74rem;color:#6b7280;padding:2px 0 10px}
.nt-vacio{font-size:.86rem;color:#4b5563;padding:2px 0 12px}
@media (max-width:820px){.nt{padding:2px 12px}.nt li a{flex-basis:100%}}
"""


def hace(fecha, ahora=None):
    if not fecha:
        return ""
    s = ((ahora or datetime.now(timezone.utc)) - fecha).total_seconds()
    if s < 90:
        return "recién"
    if s < 3600:
        return f"hace {int(s // 60)} min"
    if s < 86400:
        return f"hace {int(s // 3600)} h"
    d = int(s // 86400)
    return f"hace {d} día" + ("s" if d > 1 else "")


def noticias_html(notas, horas=24, ahora=None, hubo_respuesta=True, abierto=None):
    """Recuadro desplegable "Noticias calientes del día" con los titulares. Sin notas, adentro va un renglon que lo explica.
    (v1.2.46: el titulo ya no lleva la fuente ni las horas; la fuente se nombra en cada nota y en el pie.)"""
    abierto = ABIERTO if abierto is None else abierto
    atr = " open" if abierto else ""
    if not notas:
        motivo = (f"{FUENTE} no respondió en este momento" if not hubo_respuesta
                  else f"no hay notas recientes de {FUENTE}")
        return (f'<details class="nt"{atr}><summary>Noticias Calientes del día</summary>'
                f'<div class="nt-vacio">{html.escape(motivo)}. Probá recargar en unos minutos.</div></details>')
    filas = []
    for n in notas:
        link = html.escape(n["link"], quote=True)
        meta = " · ".join(x for x in (FUENTE, hace(n.get("fecha"), ahora)) if x)
        etiq = ""
        if n.get("menciona"):
            etiq = f'<span class="nt-e" title="Empresas del screener nombradas en el titular">{html.escape(", ".join(n["menciona"][:3]))}</span>'
        es = n.get("titulo_es")
        texto = es or n["titulo"]
        tip = f' title="Titular original: {html.escape(n["titulo"], quote=True)}"' if es else ""
        filas.append(f'<li><a href="{link}" target="_blank" rel="noopener noreferrer"{tip}>{html.escape(texto)}</a>'
                     f'{etiq}<span class="nt-m">{html.escape(meta)}</span></li>')
    hay_es = any(n.get("titulo_es") for n in notas)
    aviso_trad = (" Los titulares están traducidos automáticamente del inglés: pueden tener errores (al pasar el mouse se ve el original)."
                  if hay_es else (" Los titulares salen en inglés porque la traducción no estuvo disponible." if IDIOMA == "en" else ""))
    return (f'<details class="nt"{atr}><summary>Noticias Calientes del día</summary>'
            f'<ul>{"".join(filas)}</ul>'
            f'<div class="nt-pie">Fuente: {FUENTE}. Primero las que nombran empresas del screener (etiqueta verde), una sola nota por empresa; '
            f'después las de portada y las más recientes. Cada título abre la nota en {FUENTE}.{aviso_trad} Es información, no una recomendación.</div></details>')


def _fila(n, fuente, ahora=None):
    link = html.escape(n["link"], quote=True)
    meta = " · ".join(x for x in (n.get("fuente") or fuente, hace(n.get("fecha"), ahora)) if x)      # v1.5.24: cada nota nombra su medio
    etiq = ""
    if n.get("tendencia"):
        etiq += '<span class="nt-t" title="La historia que más medios están cubriendo hoy">Tendencia del día</span>'
    if n.get("menciona"):
        etiq += f'<span class="nt-e" title="Empresas del screener nombradas en el titular">{html.escape(", ".join(n["menciona"][:3]))}</span>'
    es = n.get("titulo_es")
    tip = f' title="Titular original: {html.escape(n["titulo"], quote=True)}"' if es else ""
    return (f'<li><a href="{link}" target="_blank" rel="noopener noreferrer"{tip}>{html.escape(es or n["titulo"])}</a>'
            f'{etiq}<span class="nt-m">{html.escape(meta)}</span></li>')


def noticias_bloques_html(bloques, ahora=None, abierto=None):
    """v1.2.58: recuadro desplegable "Noticias calientes del día" dividido en bloques (Locales, Estados Unidos, Resto del mundo), 5 notas cada uno."""
    abierto = ABIERTO if abierto is None else abierto
    atr = " open" if abierto else ""
    partes = []
    for b in bloques or []:
        k = re.sub(r"[^a-z]", "", str(b.get("clave") or "").lower())
        cab = f'<div class="nt-b nt-{k}">{html.escape(b["titulo"])}<small>{html.escape(b["fuente"])}</small></div>'
        if b["notas"]:
            partes.append(cab + f'<ul class="nt-ul-{k}">{"".join(_fila(n, b["fuente"], ahora) for n in b["notas"])}</ul>')
        else:
            motivo = (f'{b["fuente"]} no respondió en este momento' if not b.get("respondio") else f'no hay notas recientes de {b["fuente"]}')
            partes.append(cab + f'<div class="nt-vacio">{html.escape(motivo)}. Probá recargar en unos minutos.</div>')
    fuentes = []
    for b in bloques or []:
        for n in b["notas"]:
            if n.get("fuente") and n["fuente"] not in fuentes:
                fuentes.append(n["fuente"])
    if not fuentes:
        fuentes = [b["fuente"] for b in bloques or []]
    hay_es = any(n.get("titulo_es") for b in bloques or [] for n in b["notas"])
    aviso_trad = (" Los titulares en inglés están traducidos automáticamente: pueden tener errores (al pasar el mouse se ve el original)." if hay_es else "")
    pie = (f'<div class="nt-pie">Fuentes: {html.escape(", ".join(fuentes))}. Cada bloque abre con la tendencia del día (la historia que más medios cubren); '
           f'después, las que nombran empresas del screener (etiqueta verde), una sola nota por empresa, y las más recientes. Cada título abre la nota en su medio.{aviso_trad} Es información, no una recomendación.</div>')
    return f'<details class="nt"{atr}><summary>Noticias Calientes del día</summary>{"".join(partes)}{pie}</details>'
