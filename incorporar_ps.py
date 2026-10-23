"""
Carga en el cache los datos de P/S bajados con probar_ps.py (resultados_ps.json), SIN volver a bajar nada, y
vuelve a puntuar todo el cache (v1.2.43). Mantiene la fecha original del cache.

Uso (desde la carpeta del proyecto):
    python incorporar_ps.py                          (usa resultados_ps.json)
    python incorporar_ps.py otro_archivo.json

Regla (la misma que usa generar_cache con Stock Analysis): una empresa toma el P/S solo si la pagina trae el valor
actual y al menos SA_MIN_PUNTOS (3) anios fiscales de historia; la mediana es la de hasta 5 anios fiscales.
Con el generador normal (generar_cache.bat) esto ya no hace falta: el P/S se baja junto con las demas metricas.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import stockanalysis as sa
from scoring.engine import score_dataframe

CACHE_PATH = "data/cache_datos.json"


def _limpiar(o):
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _limpiar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_limpiar(v) for v in o]
    return o


def ps_de(entrada: dict):
    """(actual, mediana, anios) del P/S de una empresa del archivo de resultados, o None si no se puede usar."""
    f = ((entrada or {}).get("filas") or {}).get("ps")
    if not f or f.get("actual") is None or f["actual"] <= 0:
        return None
    por_anio = {int(a): v for a, v in (f.get("anios") or {}).items()}
    serie = [por_anio[a] for a in sorted(por_anio, reverse=True)[:sa.MAX_YEARS]
             if por_anio[a] is not None and por_anio[a] > 0]
    if len(serie) < sa.SA_MIN_PUNTOS:
        return None
    return round(float(f["actual"]), 2), round(float(np.median(serie)), 2), len(serie)


def main(ruta_ps="resultados_ps.json"):
    with open(ruta_ps, encoding="utf-8") as f:
        datos_ps = json.load(f)
    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)
    filas = cache["data"]
    tomadas, sin = 0, []
    for r in filas:
        p = ps_de(datos_ps.get(r["ticker"]))
        fuentes = dict(r.get("fuentes") or {})
        anios = dict(r.get("anios_historia") or {})
        if p is None:
            r["ps_actual"], r["ps_mediana"] = None, None
            fuentes.pop("ps", None); anios.pop("ps", None)
            sin.append(r["ticker"])
        else:
            r["ps_actual"], r["ps_mediana"] = p[0], p[1]
            fuentes["ps"] = "Stock Analysis"; anios["ps"] = p[2]
            tomadas += 1
        r["fuentes"], r["anios_historia"] = fuentes, anios
    print(f"P/S cargado en {tomadas} de {len(filas)} empresas" + (f" (sin P/S: {', '.join(sin)})" if sin else ""))

    antes = {r["ticker"]: (r.get("score_total"), r.get("categoria")) for r in filas}
    nuevas = _limpiar(score_dataframe(pd.DataFrame(filas)).replace({float("nan"): None}).to_dict(orient="records"))
    cambian = [(r["ticker"], antes[r["ticker"]], (r.get("score_total"), r.get("categoria")))
               for r in nuevas if antes[r["ticker"]] != (r.get("score_total"), r.get("categoria"))]
    print(f"Empresas cuyo puntaje o categoria cambia: {len(cambian)}")
    for t, a, b in cambian:
        print(f"   {t}: {a[0]} ({a[1]}) -> {b[0]} ({b[1]})")
    cache["data"] = nuevas
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    print(f"Cache guardado en {CACHE_PATH} con {len(nuevas)} empresas (fecha original sin cambios).")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or []))
