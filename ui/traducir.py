"""
Traduccion automatica de titulares al español (v1.2.42). Solo se usa si NOTICIAS_IDIOMA = "en" y NOTICIAS_TRADUCIR = True
(config/ajustes.py): los titulares de CNBC salen en ingles y se traducen con el servicio gratuito MyMemory
(https://mymemory.translated.net, API publica). Es traduccion automatica: puede tener errores o sonar rara.

Reglas de seguridad:
  * Nunca rompe la pagina ni la demora: si el servicio no responde, esta lleno o devuelve algo raro, el titular queda en ingles.
  * Cada titulo se traduce una sola vez (queda guardado en memoria): la cuota gratuita (5.000 caracteres por dia sin mail y
    50.000 con un mail) alcanza de sobra para 5 titulares cada 15 minutos.
  * Se descartan las respuestas que no parecen una traduccion (vacias, avisos de cuota, muy cortas o muy largas, iguales al original).
"""
import html
import json
import re
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "https://api.mymemory.translated.net/get"
TIMEOUT_S = 4
MAX_GUARDADOS = 600
_CACHE = {}          # titulo original -> titulo en español, o None si no se pudo (para no insistir en la misma sesion)
_LOCK = threading.Lock()
_RUIDO = re.compile(r"(?i)MYMEMORY|QUERY LENGTH|INVALID|LIMIT|QUOTA|PLEASE SELECT")


def _pedir(texto, mail=""):
    """Respuesta JSON del servicio (dict) o None si no se pudo."""
    params = {"q": texto[:480], "langpair": "en|es"}
    if mail:
        params["de"] = mail
    try:
        req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": "Mozilla/5.0 (compatible; TodoCedears/1.2)", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 (url fija, https)
            return json.loads(r.read(200_000).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


def _limpiar(original, resp):
    """Titulo en español sacado de la respuesta, o None si no parece una traduccion buena."""
    try:
        if not isinstance(resp, dict) or int(resp.get("responseStatus", 0)) != 200:
            return None
        t = resp["responseData"]["translatedText"]
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(t, str):
        return None
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    if not t or _RUIDO.search(t) and not _RUIDO.search(original):
        return None
    if t.lower() == original.strip().lower():
        return None
    if not (0.35 <= len(t) / max(1, len(original)) <= 3.0):
        return None
    return t


def traducir_uno(texto, mail="", pedir=None):
    """Traduccion de un titular (guardada en memoria). `pedir` permite probar sin internet."""
    pedir = pedir or _pedir
    with _LOCK:
        if texto in _CACHE:
            return _CACHE[texto]
    es = _limpiar(texto, pedir(texto, mail))
    with _LOCK:
        if len(_CACHE) >= MAX_GUARDADOS:
            _CACHE.clear()
        _CACHE[texto] = es
    return es


def traducir_lista(textos, mail="", pedir=None):
    """{titulo original: titulo en español} solo para los que se pudieron traducir. Todos a la vez, con tope de tiempo."""
    textos = [t for t in dict.fromkeys(textos) if isinstance(t, str) and t.strip()]
    if not textos:
        return {}
    out = {}
    try:
        with ThreadPoolExecutor(max_workers=min(5, len(textos))) as ex:
            for t, es in zip(textos, ex.map(lambda x: traducir_uno(x, mail, pedir), textos, timeout=TIMEOUT_S * 2 + 2)):
                if es:
                    out[t] = es
    except Exception:  # noqa: BLE001
        pass
    return out
