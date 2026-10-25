"""
v1.2.51 - Vuelve a puntuar el cache actual con las reglas vigentes (puntaje, categoria y Fair Value), SIN bajar nada y sin tocar la fecha.
Uso: python rescorar_cache.py
"""
import json, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.cache_seguro import guardar_seguro
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


def main():
    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)
    antes = {r["ticker"]: (r.get("score_total"), r.get("categoria")) for r in cache["data"]}
    nuevas = _limpiar(score_dataframe(pd.DataFrame(cache["data"])).replace({float("nan"): None}).to_dict(orient="records"))
    fecha = {r["ticker"]: r.get("fecha_dato") for r in cache["data"]}
    for r in nuevas:
        if not r.get("fecha_dato"):
            r["fecha_dato"] = fecha.get(r["ticker"])
    cambian = [(r["ticker"], antes[r["ticker"]][1], r.get("categoria")) for r in nuevas if antes[r["ticker"]][1] != r.get("categoria")]
    print(f"Empresas cuya categoria cambia: {len(cambian)}")
    cache["data"] = nuevas
    guardar_seguro(cache, CACHE_PATH)
    print(f"Cache guardado con {len(nuevas)} empresas.")


if __name__ == "__main__":
    main()
