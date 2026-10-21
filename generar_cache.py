"""
Script para generar el cache de datos del CEDEAR Screener.
Correr desde la carpeta raiz del proyecto:
    python generar_cache.py
"""
import sys
import os
import json
import shutil
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import fetch_all_tickers
from scoring.engine import score_dataframe
from config.sectors import TICKER_UNIVERSE

print("=" * 40)
print("  CEDEAR Screener - Generar Cache")
print("=" * 40)
print()

tickers = [t for ts in TICKER_UNIVERSE.values() for t in ts]
print(f"Descargando {len(tickers)} tickers...")
print("Esto tarda 5-10 minutos, esperá...")
print()

df = fetch_all_tickers(tickers)
def _limpiar(o):
    """NaN -> None (tambien dentro de diccionarios anidados) para guardar JSON valido."""
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _limpiar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_limpiar(v) for v in o]
    return o


print("Calculando scores...")
scored = score_dataframe(df)

os.makedirs("data", exist_ok=True)
cache = {
    "timestamp": datetime.now().isoformat(),
    "data": _limpiar(scored.replace({float("nan"): None}).to_dict(orient="records")),
}
with open("data/cache_datos.json", "w") as f:
    json.dump(cache, f)

# v1.2.11 - Historial: copia con fecha para poder comparar como cambian los datos mes a mes
copia = None
try:
    os.makedirs("data/historial", exist_ok=True)
    copia = f"data/historial/cache_{datetime.now():%Y-%m-%d}.json"
    shutil.copyfile("data/cache_datos.json", copia)
except Exception as e:
    print(f"  (No se pudo guardar la copia del historial: {e})")

print()
print("=" * 40)
print(f"  LISTO! {len(scored)} tickers descargados")
print("  Archivo: data/cache_datos.json")
if copia:
    print(f"  Copia para el historial: {copia}")
print("  Subilo a GitHub en la carpeta data/ (incluida la carpeta historial/)")
print("=" * 40)
input("\nPresioná Enter para cerrar...")
