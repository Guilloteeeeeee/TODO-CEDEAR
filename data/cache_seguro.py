"""
Guardado seguro del cache (v1.2.50, auditoria del 25/10/2026).

Problemas que resuelve:
  - Antes generar_cache.py escribia directo sobre data/cache_datos.json: si el programa se cortaba a la mitad (o Yahoo / Stock Analysis fallaban
    y devolvian filas vacias), el cache bueno se pisaba y la app quedaba sin datos. Tambien guardaba en data/historial una copia de lo que
    hubiera salido, aunque estuviera roto.
  - Cada fila no decia de que dia eran sus datos: al actualizar solo algunos tickers, el cache mezclaba fechas sin dejar registro.

Que hay aca:
  validar_cache(filas, anterior)    -> (ok, problemas): controles minimos antes de reemplazar el cache bueno.
  guardar_seguro(cache, ruta)       -> escribe a un archivo temporal, lo relee y recien ahi reemplaza el original (os.replace es atomico).
  marcar_fecha_dato(filas, fecha)   -> pone `fecha_dato` (YYYY-MM-DD) en las filas que todavia no la tienen.
  ultimo_historial_valido(carpeta)  -> el archivo mas nuevo de data/historial que se puede leer (la app lo usa si el cache principal esta roto).
"""
import json
import os
import glob

# Controles de validar_cache. Son pisos bajos a proposito: apuntan a una descarga ROTA, no a un cambio normal de datos.
MIN_PRECIO_PCT = 0.95        # al menos el 95 % de las empresas con precio
MIN_PUNTAJE_VS_ANTERIOR = 0.95   # empresas con puntaje: al menos el 95 % de las que tenia el cache anterior
MIN_FILAS_VS_ANTERIOR = 0.95     # cantidad de filas: al menos el 95 % de las del cache anterior


def _tiene(v):
    return v is not None and v == v


def validar_cache(filas, anterior=None, universo=None):
    """
    filas: lista de dicts (el cache nuevo). anterior: lista de dicts del cache bueno actual (o None). universo: tickers esperados (o None).
    Devuelve (ok, problemas). Si `problemas` no esta vacio, el cache NO deberia reemplazar al anterior.
    """
    problemas = []
    if not filas:
        return False, ["el cache nuevo no tiene ninguna fila"]
    n = len(filas)
    con_precio = sum(1 for r in filas if _tiene(r.get("precio_actual")))
    if con_precio < MIN_PRECIO_PCT * n:
        problemas.append(f"solo {con_precio} de {n} empresas tienen precio (se pide al menos el {MIN_PRECIO_PCT:.0%})")
    if universo:
        faltan = sorted(set(universo) - {r.get("ticker") for r in filas})
        if len(faltan) > (1 - MIN_PRECIO_PCT) * len(universo):
            problemas.append(f"faltan {len(faltan)} empresas del universo ({', '.join(faltan[:8])}{'...' if len(faltan) > 8 else ''})")
    if anterior:
        if n < MIN_FILAS_VS_ANTERIOR * len(anterior):
            problemas.append(f"tiene {n} filas y el cache anterior tenia {len(anterior)}")
        pun_ant = sum(1 for r in anterior if _tiene(r.get("score_total")))
        pun_nue = sum(1 for r in filas if _tiene(r.get("score_total")))
        if pun_nue < MIN_PUNTAJE_VS_ANTERIOR * pun_ant:
            problemas.append(f"{pun_nue} empresas con puntaje contra {pun_ant} del cache anterior")
    return (not problemas), problemas


def guardar_seguro(cache, ruta):
    """
    Guarda `cache` (dict con "timestamp" y "data") en `ruta` sin riesgo de dejarlo a medias: escribe a ruta.tmp, relee el temporal para
    confirmar que es JSON valido con las mismas filas, y lo mueve sobre el original. Si algo falla, el original queda intacto y se
    levanta la excepcion.
    """
    carpeta = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(carpeta, exist_ok=True)
    tmp = ruta + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
            f.flush()
            os.fsync(f.fileno())
        with open(tmp, encoding="utf-8") as f:
            leido = json.load(f)
        if len(leido.get("data", [])) != len(cache.get("data", [])):
            raise ValueError("el archivo temporal no quedo con todas las filas")
        os.replace(tmp, ruta)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def marcar_fecha_dato(filas, fecha):
    """Pone `fecha_dato` (texto YYYY-MM-DD) en las filas que no la tienen. Devuelve la misma lista."""
    for r in filas:
        if not r.get("fecha_dato"):
            r["fecha_dato"] = str(fecha)[:10]
    return filas


def ultimo_historial_valido(carpeta):
    """(ruta, contenido) del archivo cache_AAAA-MM-DD.json mas nuevo de `carpeta` que se pueda leer, o (None, None)."""
    for ruta in sorted(glob.glob(os.path.join(carpeta, "cache_*.json")), reverse=True):
        try:
            with open(ruta, encoding="utf-8") as f:
                c = json.load(f)
            if c.get("data") and c.get("timestamp"):
                return ruta, c
        except Exception:
            continue
    return None, None
