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
_CARGO = re.compile(r"chief executive|\bceo\b|chairman|chairwoman|president", re.I)


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
    return re.sub(r"\s+", " ", _HONOR.sub("", str(nombre or "").strip())).strip()


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
        if primero in tit and ultimo in tit and emp in ext.split() and _CARGO.search(str(p.get("extract") or "")) and thumb.startswith("https://upload.wikimedia.org/"):
            return thumb
    return None


def _pedir(nombre, empresa):
    q = f"{nombre_limpio(nombre)} {palabra_empresa(empresa)}"
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrlimit": "5", "prop": "pageimages|extracts",
              "piprop": "thumbnail", "pithumbsize": "240", "exintro": "1", "explaintext": "1", "exlimit": "5", "redirects": "1"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "TodoCedears/1.2 (educativo; finanzas.medicos@gmail.com)"})
    with urllib.request.urlopen(req, timeout=8) as r:  # noqa: S310 (url fija, https)
        datos = json.loads(r.read(400_000).decode("utf-8", "replace"))
    pags = (datos.get("query") or {}).get("pages") or {}
    lista = sorted(pags.values(), key=lambda p: p.get("index", 99))
    return [{"title": p.get("title"), "extract": p.get("extract"), "thumb": (p.get("thumbnail") or {}).get("source")} for p in lista]


def buscar_foto(nombre, empresa, obtener=None):
    """URL de la foto (Wikipedia) o None. Nunca levanta excepciones."""
    try:
        if not nombre_limpio(nombre):
            return None
        return elegir((obtener or _pedir)(nombre, empresa), nombre, empresa)
    except Exception:  # noqa: BLE001
        return None
