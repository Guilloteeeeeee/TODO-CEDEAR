"""Datos de Yahoo guardados en un archivo (v1.2.59): dividendos, directivos, accionistas, calendario y estados financieros de cada empresa, mas la foto
del CEO. Los baja `bajar_paquetes_yahoo.py` (desde la PC de Guille, donde Yahoo si responde) y quedan en data/paquetes_yahoo.json:
{"fecha": "dd/mm/aaaa", "datos": {TICKER: {"dividendos": {...}, "gobierno": {...}, "agenda": {...}, "estados": {...}, "foto_ceo": url|null}}}.
La app pide primero a Yahoo en vivo; lo que no responde se completa con este archivo (y avisa la fecha). Las fechas se guardan como "d:AAAA-MM-DD"."""
import datetime
import json
import os
import re

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paquetes_yahoo.json")
CLAVES = ("dividendos", "gobierno", "agenda", "estados")
_FECHA = re.compile(r"^d:(\d{4})-(\d{2})-(\d{2})$")


def a_json(o):
    """Convierte fechas a texto "d:AAAA-MM-DD" (y tuplas a listas) para poder guardar en JSON."""
    if isinstance(o, dict):
        return {str(k): a_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [a_json(v) for v in o]
    if isinstance(o, datetime.datetime):
        return "d:" + o.date().isoformat()
    if isinstance(o, datetime.date):
        return "d:" + o.isoformat()
    return o


def de_json(o):
    """Al reves: los textos "d:AAAA-MM-DD" vuelven a ser fechas."""
    if isinstance(o, dict):
        # JSON solo admite claves de texto: los diccionarios con anios como clave ({1: .., 3: ..}) vuelven a tener numeros
        enteras = bool(o) and all(isinstance(k, str) and k.isdigit() for k in o)
        return {(int(k) if enteras else k): de_json(v) for k, v in o.items()}
    if isinstance(o, list):
        return [de_json(v) for v in o]
    if isinstance(o, str):
        m = _FECHA.match(o)
        if m:
            try:
                return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return o
    return o


def cargar(ruta=None):
    """({TICKER: {...}}, fecha|None). ({}, None) si el archivo no esta o no se puede leer."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        return {str(t).upper(): de_json(v) for t, v in (d.get("datos") or {}).items() if isinstance(v, dict)}, d.get("fecha")
    except Exception:  # noqa: BLE001
        return {}, None


def _vacio(v):
    return v is None or (isinstance(v, (str, list, tuple, dict, set)) and len(v) == 0)


def completar(vivo, guardado):
    """Mezcla lo que respondio Yahoo en vivo con lo guardado: para cada dato que vino vacio se usa el del archivo.
    v1.2.62: el "gobierno" (directivos y accionistas) tambien por dentro. Yahoo desde la nube a veces contesta a medias (por ejemplo los accionistas pero no la lista de directivos: CAT, PM...):
    el diccionario "gobierno" de la nube no estaba vacio y el archivo no se usaba; ahora cada campo vacio se completa con el del archivo.
    Devuelve (resultado, [claves tomadas del archivo])."""
    res = dict(vivo)
    usadas = []
    for k in CLAVES:
        g = (guardado or {}).get(k)
        if not g:
            continue
        v = res.get(k)
        if not v:
            res[k] = g
            usadas.append(k)
        elif k == "gobierno" and isinstance(v, dict) and isinstance(g, dict):       # solo este: es el que Yahoo contesta a medias
            nuevo = dict(v)
            tomo = False
            for sub, sv in g.items():
                if _vacio(nuevo.get(sub)) and not _vacio(sv):
                    nuevo[sub] = sv
                    tomo = True
            if tomo:
                res[k] = nuevo
                usadas.append(k)
    return res, usadas
