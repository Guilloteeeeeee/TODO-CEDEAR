"""Foto del CEO desde Wikipedia (v1.2.55). Yahoo no da fotos. Se busca la pagina de la persona en Wikipedia y SOLO se usa su foto si la pagina
coincide con el nombre del CEO y el texto de presentacion nombra a la empresa y su cargo: asi no se muestra la foto de un homonimo. Si no se
encuentra nada seguro, la pantalla muestra sus iniciales. No se inventa nada."""
import json
import re
import unicodedata
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
_STOP = {"the", "inc", "corp", "corporation", "company", "co", "ltd", "plc", "holdings", "holding", "group", "and", "sa", "nv", "ag", "de", "new", "class"}
_HONOR = re.compile(r"^(mr|mrs|ms|miss|dr|prof|sir|dame)\.?\s+", re.I)
# v1.2.61: sin "president" solo (aceptaba a un prócer del siglo XVIII como CEO de AIG); los CEO con ese cargo dicen "president and chief executive"
_CARGO = re.compile(r"chief executive|\bceo\b|chairman|chairwoman", re.I)
# Titulos que Yahoo pega detras del nombre ("Ph.D.", "CPA", "M.B.A., P.Eng."): se sacan. Los ambiguos (MD, BA, MA...) solo si traen puntos.
_TITULOS = {"cpa", "cebs", "phd", "mba", "dvm", "esq", "cfa", "peng", "bsc", "msc", "llb", "llm", "mph", "fca", "cma", "dds"}
_TITULOS_PUNTOS = {"jd", "md", "ba", "bs", "ms", "ma", "ca", "pe", "eng", "dr"}
# Palabras tan comunes en nombres de empresas que no prueban nada ("American", "Bank", "Group"): si el nombre tiene otras, se usan esas
_GENERICAS = {"american", "international", "general", "united", "first", "national", "global", "bank", "banco", "group", "financial", "technologies",
              "technology", "systems", "energy", "industries", "capital", "services", "resources", "communications", "motors", "laboratories", "labs",
              "pharmaceuticals", "therapeutics", "partners", "brands", "stores", "electric", "power", "oil", "gas", "mining", "mines", "services"}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s)


def palabra_empresa(empresa):
    """Primera palabra significativa del nombre de la empresa (para comprobar que la pagina habla de ella)."""
    for w in _norm(empresa).split():
        if len(w) >= 3 and w not in _STOP:
            return w
    return ""


def nombre_limpio(nombre):
    """'Mr. Robert A. Michael CPA' -> 'Robert A. Michael'; 'Ms. Julie T. Spellman Sweet J.D.' -> 'Julie T. Spellman Sweet'."""
    s = re.sub(r"\s+", " ", _HONOR.sub("", str(nombre or "").strip())).strip().split(",")[0].strip()
    toks = s.split(" ")
    while len(toks) > 2:
        crudo = toks[-1]
        letras = re.sub(r"[^a-z]", "", crudo.lower())
        if letras in _TITULOS or (letras in _TITULOS_PUNTOS and "." in crudo):
            toks.pop()
        else:
            break
    return " ".join(toks)


def _foto_url(u):
    """URL https de una imagen de Wikipedia/Wikimedia (la API la devuelve por TLS); acepta '//host/...'. None si no es de ahi."""
    u = str(u or "").strip()
    if u.startswith("//"):
        u = "https:" + u
    m = re.match(r"https://([^/]+)/", u)
    if m and (m.group(1).endswith("wikimedia.org") or m.group(1).endswith("wikipedia.org")):
        return u
    return None


def _nombre_pila_ok(toks, tit):
    """El nombre de pila de Wikipedia coincide con el de Yahoo: comparten el comienzo (Tim / Timothy) o la inicial del segundo nombre (Robert K. / Kelly)."""
    if _prefijo(toks[0], tit[0]) >= min(2, len(toks[0])):
        return True
    iniciales = {t for t in toks[1:-1] if len(t) == 1}
    return bool(iniciales) and len(tit) >= 2 and tit[0][:1] in iniciales


def elegir(paginas, nombre, empresa):
    """paginas: [{'title','extract','thumb'}]. URL de la foto de la pagina que coincide con el CEO y la empresa, o None."""
    toks = _norm(nombre_limpio(nombre)).split()
    emp = palabra_empresa(empresa)
    if len(toks) < 2 or not emp:
        return None
    primero, ultimo = toks[0], toks[-1]
    for p in paginas or []:
        tit = _norm(p.get("title")).split()
        ext = _norm(p.get("extract"))
        thumb = p.get("thumb") or ""
        if not tit or ultimo not in tit:
            continue
        # Yahoo y Wikipedia escriben distinto el nombre de pila (Jen-Hsun / Jensen, Tim / Timothy): alcanza con que compartan el comienzo
        if not _nombre_pila_ok(toks, tit):
            continue
        url = _foto_url(thumb)
        if _nombra_empresa(ext, empresa) and _CARGO.search(str(p.get("extract") or "")) and url:
            return url
    return None


def _nombra_empresa(ext_norm, empresa):
    """El texto de presentacion nombra a la empresa: alcanza con una de sus dos primeras palabras significativas (v1.2.58; antes solo la primera:
    'Taiwan Semiconductor Manufacturing' no aparecia en la presentacion de su CEO, que habla de TSMC)."""
    palabras = set(ext_norm.split())
    todas = [w for w in _norm(empresa).split() if len(w) >= 3 and w not in _STOP]
    claves = [w for w in todas if w not in _GENERICAS][:2]
    if claves:
        return any(w in palabras for w in claves)
    return bool(todas) and all(w in palabras for w in todas[:3])      # solo palabras comunes ("General Motors"): hacen falta todas


def _prefijo(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _consultas(nombre, empresa):
    toks = nombre_limpio(nombre).split()
    emp = palabra_empresa(empresa)
    qs = []
    if len(toks) >= 2:
        qs.append(f"{toks[0]} {toks[-1]} {emp}".strip())
        qs.append(f"{toks[0]} {toks[-1]}")
        if len(toks) > 2:
            qs.append(" ".join(toks))
    elif toks:
        qs.append(toks[0])
    return list(dict.fromkeys(qs))


ULTIMO_ERROR = None     # v1.2.60: ultimo error de red (para saber por que no hay foto: antes se tragaba en silencio)
_UA = {"User-Agent": "TodoCedears/1.2 (educativo; finanzas.medicos@gmail.com)", "Accept": "application/json"}


def _descargar(url):
    """Texto de la respuesta. Primero con requests (usa los certificados de certifi: en algunas PC con Windows urllib falla por el antivirus o por
    certificados viejos); si requests no esta o falla, con urllib."""
    global ULTIMO_ERROR
    try:
        import requests
        r = requests.get(url, headers=_UA, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:  # noqa: BLE001
        ULTIMO_ERROR = f"requests: {type(e).__name__}: {str(e)[:160]}"
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 (url fija, https)
        return r.read(600_000).decode("utf-8", "replace")


def _pedir_una(q):
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrlimit": "6", "prop": "pageimages|extracts",
              "piprop": "thumbnail", "pithumbsize": "240", "exintro": "1", "explaintext": "1", "exlimit": "6", "redirects": "1"}
    datos = json.loads(_descargar(API + "?" + urllib.parse.urlencode(params)))
    pags = (datos.get("query") or {}).get("pages") or {}
    lista = sorted(pags.values(), key=lambda p: p.get("index", 99))
    return [{"title": p.get("title"), "extract": p.get("extract"), "thumb": (p.get("thumbnail") or {}).get("source")} for p in lista]


def _pedir(nombre, empresa):
    """Paginas de Wikipedia para el nombre (se prueban hasta tres busquedas: nombre + empresa, solo el nombre, nombre completo). Junta todas."""
    todas, vistos = [], set()
    for q in _consultas(nombre, empresa):
        try:
            for p in _pedir_una(q):
                if p["title"] not in vistos:
                    vistos.add(p["title"])
                    todas.append(p)
        except Exception as e:  # noqa: BLE001
            global ULTIMO_ERROR
            ULTIMO_ERROR = f"{type(e).__name__}: {str(e)[:160]}"
            continue
        if elegir(todas, nombre, empresa):
            break
    return todas


def diagnostico(nombre, empresa, obtener=None):
    """Texto para entender por que no sale una foto (se ve con ?debug=1 y con probar_foto_ceo.bat). No cambia nada."""
    try:
        pags = (obtener or _pedir)(nombre, empresa)
    except Exception as e:  # noqa: BLE001
        return f"fallo la consulta a Wikipedia: {type(e).__name__}: {e}"
    if not pags:
        return "Wikipedia no devolvio paginas (sin conexion, bloqueo o busqueda vacia)" + (f"; ultimo error de red: {ULTIMO_ERROR}" if ULTIMO_ERROR else "")
    toks = _norm(nombre_limpio(nombre)).split()
    out = []
    for p in pags:
        tit = _norm(p.get("title")).split()
        out.append(f'"{p.get("title")}": apellido={"si" if toks and toks[-1] in tit else "no"}, nombre={"si" if toks and tit and _nombre_pila_ok(toks, tit) else "no"}, '
                   f'empresa={"si" if _nombra_empresa(_norm(p.get("extract")), empresa) else "no"}, cargo={"si" if _CARGO.search(str(p.get("extract") or "")) else "no"}, '
                   f'foto={"si" if p.get("thumb") else "no"}{" (" + str(p.get("thumb"))[:70] + ")" if p.get("thumb") and not _foto_url(p.get("thumb")) else ""}')
    return f"elegida: {elegir(pags, nombre, empresa)}; paginas: " + " | ".join(out)


def buscar_foto(nombre, empresa, obtener=None):
    """URL de la foto (Wikipedia) o None. Nunca levanta excepciones."""
    try:
        if not nombre_limpio(nombre):
            return None
        return elegir((obtener or _pedir)(nombre, empresa), nombre, empresa)
    except Exception:  # noqa: BLE001
        return None
