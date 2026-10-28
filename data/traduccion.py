"""Traducción de inglés a castellano SIN instalar nada (v1.2.71): usa solo la librería estándar de Python.
Orden: (1) el traductor gratuito de Google (el mismo que usaba deep-translator), (2) MyMemory (ui/traducir.py), (3) deep-translator si por casualidad está instalado.
Devuelve el texto en castellano o None; el motivo del último fallo queda en ULTIMO_ERROR para mostrarlo en el resumen de la corrida."""
import json
import re
import urllib.parse
import urllib.request

ULTIMO_ERROR = [""]
URL_GOOGLE = "https://translate.googleapis.com/translate_a/single"
TOPE = 1800          # letras por pedido (con POST no hay problema de largo de URL)


def _partes(texto, tope=TOPE):
    partes, actual = [], ""
    for frase in re.split(r"(?<=[.!?])\s+", str(texto or "").strip()):
        while len(frase) > tope:          # frase gigante: se corta en una coma o espacio
            c = max(frase.rfind(", ", 0, tope), frase.rfind(" ", 0, tope), tope // 2)
            if actual:
                partes.append(actual)
                actual = ""
            partes.append(frase[:c + 1].strip())
            frase = frase[c + 1:].strip()
        if actual and len(actual) + len(frase) + 1 > tope:
            partes.append(actual)
            actual = ""
        actual = (actual + " " + frase).strip()
    if actual:
        partes.append(actual)
    return [p for p in partes if p]


def _google(parte, origen="en", destino="es", timeout=15):
    q = urllib.parse.urlencode({"client": "gtx", "sl": origen, "tl": destino, "dt": "t"})
    req = urllib.request.Request(URL_GOOGLE + "?" + q, data=urllib.parse.urlencode({"q": parte}).encode("utf-8"),
                                 headers={"User-Agent": "Mozilla/5.0 (compatible; TodoCedears/1.2)", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (url fija, https)
        j = json.loads(r.read(500_000).decode("utf-8", "replace"))
    return "".join(seg[0] for seg in (j[0] or []) if seg and isinstance(seg[0], str)).strip()


def traducir(texto, origen="en", destino="es"):
    """Texto traducido o None. Nunca mezcla idiomas a medias: si una parte falla con Google, prueba el siguiente servicio con todo el texto."""
    texto = str(texto or "").strip()
    if not texto:
        return None
    partes = _partes(texto)
    try:
        res = [_google(p, origen, destino) for p in partes]
        es = " ".join(x for x in res if x).strip()
        if es and es.lower() != texto.lower():
            return es
        ULTIMO_ERROR[0] = "Google devolvio el mismo texto o vacio"
    except Exception as e:  # noqa: BLE001
        ULTIMO_ERROR[0] = f"Google: {type(e).__name__}: {e}"[:160]
    try:
        from ui.traducir import traducir_texto_largo
        es = traducir_texto_largo(texto, max_trozos=40)
        if es:
            return es
        ULTIMO_ERROR[0] += " | MyMemory no pudo"
    except Exception as e:  # noqa: BLE001
        ULTIMO_ERROR[0] += f" | MyMemory: {type(e).__name__}"
    try:
        from deep_translator import GoogleTranslator
        tr = GoogleTranslator(source=origen, target=destino)
        es = " ".join(x for x in (tr.translate(p) for p in partes) if x).strip()
        if es:
            return es
    except Exception:  # noqa: BLE001
        pass
    return None
