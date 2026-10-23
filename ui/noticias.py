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
  * Los titulares salen en el idioma de la fuente elegida (español con Ambito, ingles con CNBC).

No usa JavaScript ni cuentas ni claves. Las fuentes y sus feeds se cambian en config/ajustes.py (NOTICIAS_FUENTES).
"""
import html
import re
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
TIMEOUT_S = 5
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


def buscar_menciones(titulo, tickers):
    """Tickers de las empresas del screener que se nombran en el titular (sin repetir, en orden de aparicion)."""
    pat, formas = _patron(tickers)
    if pat is None or not titulo:
        return []
    out = []
    tset = set(tickers or [])
    for m in pat.finditer(titulo):
        if IDIOMA == "es" and m.group(1) in _NO_AL_INICIO and m.start() == 0:
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


def _bajar_todo(descargar=None):
    descargar = descargar or _descargar
    feeds = list(FEEDS)
    with ThreadPoolExecutor(max_workers=max(1, len(feeds))) as ex:
        bytes_ = list(ex.map(lambda f: descargar(f[1]), feeds))
    notas, portada, ok = {}, set(), 0
    for (nombre, _url, es_portada), contenido in zip(feeds, bytes_):
        lista = leer_feed(contenido)
        if lista:
            ok += 1
        for n in lista:
            k = _clave_link(n["link"])
            if es_portada:
                portada.add(k)
                continue
            if k not in notas:
                notas[k] = {**n, "seccion": nombre, "clave": k}
    return {"notas": list(notas.values()), "portada": portada, "feeds_ok": ok, "feeds_total": len(feeds)}


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
def ordenar(crudo, tickers, ahora=None, cantidad=None, horas=None, horas_max=None):
    """Aplica la regla: ventana de 24 h (se amplia a 48 y 72 h si hay menos de `cantidad`), y orden por
    (menciona empresas del screener, esta en portada, mas reciente). Devuelve (lista, horas_usadas)."""
    cantidad = CANTIDAD if cantidad is None else cantidad
    horas = HORAS if horas is None else horas
    horas_max = HORAS_MAX if horas_max is None else horas_max
    ahora = ahora or datetime.now(timezone.utc)
    if not crudo or not crudo.get("notas"):
        return [], horas
    ventanas = [horas] + [h for h in (48, 72) if horas < h <= horas_max]
    usadas = horas
    elegibles = []
    for h in ventanas:
        usadas = h
        lim = ahora - timedelta(hours=h)
        elegibles = [n for n in crudo["notas"] if n["fecha"] is None or lim <= n["fecha"] <= ahora + timedelta(minutes=10)]
        if len(elegibles) >= cantidad:
            break
    portada = crudo.get("portada") or set()
    tickers = list(tickers or [])
    salida = []
    for n in elegibles:
        m = buscar_menciones(n["titulo"], tickers)
        salida.append({**n, "menciona": m, "en_portada": n["clave"] in portada, "fuente": FUENTE})
    minimo = datetime.min.replace(tzinfo=timezone.utc)
    salida.sort(key=lambda n: (bool(n["menciona"]), n["en_portada"], n["fecha"] or minimo), reverse=True)
    return salida[:cantidad], usadas


# ---------------------------------------------------------------------------------------------------------------
# Dibujo
# ---------------------------------------------------------------------------------------------------------------
CSS = """
.nt{margin:10px 0 14px;border:1px solid #d3e2f2;border-radius:14px;background:#f1f6fc;padding:2px 16px}
.nt>summary{cursor:pointer;list-style:none;padding:11px 0;font-weight:700;font-size:1.02rem;color:#0f2a43;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.nt>summary::-webkit-details-marker{display:none}
.nt>summary::before{content:"▸";color:#5b7a99;font-size:.85rem}
.nt[open]>summary::before{content:"▾"}
.nt>summary small{font-weight:500;color:#5b7a99;font-size:.78rem}
.nt ul{list-style:none;margin:0 0 6px;padding:0}
.nt li{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;padding:8px 0;border-top:1px solid #dde8f4;font-size:.9rem;line-height:1.35}
.nt li a{color:#111827!important;font-weight:600;text-decoration:none!important;flex:1 1 420px;min-width:0}
.nt li a:hover{text-decoration:underline!important}
.nt-m{font-size:.76rem;color:#5b7a99;white-space:nowrap}
.nt-e{font-size:.72rem;font-weight:700;color:#065f46;background:#d1fae5;border-radius:999px;padding:1px 8px;white-space:nowrap}
.nt-pie{font-size:.74rem;color:#5b7a99;padding:2px 0 10px}
.nt-vacio{font-size:.86rem;color:#41566b;padding:2px 0 12px}
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
    """Recuadro desplegable "Noticias Calientes" con los titulares. Sin notas, adentro va un renglon que lo explica."""
    abierto = ABIERTO if abierto is None else abierto
    atr = " open" if abierto else ""
    if not notas:
        motivo = (f"{FUENTE} no respondió en este momento" if not hubo_respuesta
                  else f"no hay notas de {FUENTE} de las últimas {horas} h")
        return (f'<details class="nt"{atr}><summary>Noticias Calientes <small>{FUENTE}</small></summary>'
                f'<div class="nt-vacio">{html.escape(motivo)}. Probá recargar en unos minutos.</div></details>')
    filas = []
    for n in notas:
        link = html.escape(n["link"], quote=True)
        meta = " · ".join(x for x in (FUENTE, n.get("seccion", ""), hace(n.get("fecha"), ahora)) if x)
        etiq = ""
        if n.get("menciona"):
            etiq = f'<span class="nt-e" title="Empresas del screener nombradas en el titular">{html.escape(", ".join(n["menciona"][:3]))}</span>'
        filas.append(f'<li><a href="{link}" target="_blank" rel="noopener noreferrer">{html.escape(n["titulo"])}</a>'
                     f'{etiq}<span class="nt-m">{html.escape(meta)}</span></li>')
    idioma = " · titulares en inglés" if IDIOMA == "en" else ""
    return (f'<details class="nt"{atr}><summary>Noticias Calientes <small>{FUENTE} · últimas {horas} h{idioma}</small></summary>'
            f'<ul>{"".join(filas)}</ul>'
            f'<div class="nt-pie">Orden: primero las que nombran empresas del screener (etiqueta verde), después las de portada, '
            f'después las más recientes. Cada título abre la nota en {FUENTE}. Es información, no una recomendación.</div></details>')
