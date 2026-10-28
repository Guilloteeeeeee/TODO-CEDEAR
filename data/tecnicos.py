"""Parametros tecnicos para filtrar (v1.2.72): RSI, precio contra sus promedios, distancia al maximo de 52 semanas, rendimientos y volumen relativo.
Se calculan con los cierres diarios de Yahoo (y el volumen) que baja `bajar_tecnicos.py` desde la PC de Guille y quedan en data/tecnicos.json:
{"fecha": "dd/mm/aaaa", "datos": {TICKER: {"rsi": 55.2, "vs50": 0.03, "vs200": -0.04, "dist_max": -0.12, "r1m": ..., "r3m": ..., "rytd": ..., "r1a": ..., "volrel": 1.1}}}
Las distancias y rendimientos se guardan como fraccion (0,03 = 3 %). Es informacion: no entra al puntaje ni es una senal de compra o venta.
Los calculos reusan los de la solapa "Analisis Tecnico y Rendimiento" (ui/tecnico.py), asi dan lo mismo que ahi."""
import datetime as _dt
import json
import os

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tecnicos.json")

# clave guardada -> (nombre, unidad)
CLAVES = ("rsi", "vs50", "vs200", "dist_max", "r1m", "r3m", "rytd", "r1a", "volrel")


def _ret(pares, desde):
    """Rendimiento del ultimo cierre contra el ultimo cierre en `desde` o antes; None si la historia no llega."""
    if not pares or pares[0][0] > desde:
        return None
    base = None
    for f, c in pares:
        if f <= desde:
            base = c
        else:
            break
    return pares[-1][1] / base - 1.0 if base else None


def calcular(pares, volumenes=None):
    """`pares`: [(fecha, cierre)] ordenados; `volumenes`: [(fecha, volumen)] opcional. Devuelve {clave: numero}; lo que no se puede calcular no esta."""
    from ui import tecnico as T
    if not pares or len(pares) < 30:
        return {}
    c = [x for _, x in pares]
    ult_f, ult = pares[-1]
    out = {}

    def poner(k, v):
        if v is not None and v == v and abs(v) != float("inf"):
            out[k] = round(float(v), 4)
    poner("rsi", T.rsi(c))
    for k, n in (("vs50", 50), ("vs200", 200)):
        m = T.sma(c, n)
        poner(k, ult / m - 1.0 if m else None)
    r = T.rango_52s(pares)
    poner("dist_max", ult / r[1] - 1.0 if r and r[1] else None)
    poner("r1m", _ret(pares, ult_f - _dt.timedelta(days=30)))
    poner("r3m", _ret(pares, ult_f - _dt.timedelta(days=91)))
    poner("rytd", _ret(pares, _dt.date(ult_f.year - 1, 12, 31)))
    poner("r1a", _ret(pares, ult_f - _dt.timedelta(days=365)))
    v = [x for _, x in (volumenes or []) if x is not None and x == x and x >= 0]
    if len(v) >= 63:
        base = sum(v[-63:]) / 63.0
        poner("volrel", (sum(v[-5:]) / 5.0) / base if base > 0 else None)
    return out


def cargar(ruta=None):
    """({TICKER: {...}}, fecha|None); ({}, None) si el archivo no esta o no se puede leer."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        return {str(t).upper(): v for t, v in (d.get("datos") or {}).items() if isinstance(v, dict)}, d.get("fecha")
    except Exception:  # noqa: BLE001
        return {}, None


def agregar_columnas(df, datos):
    """Copia de `df` con una columna `tec_<clave>` por parametro (NaN si la empresa no tiene el dato)."""
    import pandas as pd
    df = df.copy()
    tk = [str(t).upper() for t in df["ticker"]]
    for k in CLAVES:
        df["tec_" + k] = pd.to_numeric(pd.Series([(datos.get(t) or {}).get(k) for t in tk], index=df.index), errors="coerce")
    return df
