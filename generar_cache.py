"""
Script para generar el cache de datos del CEDEAR Screener.
Correr desde la carpeta raiz del proyecto:
    python generar_cache.py
"""
import sys
import os
import json
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
print("Calculando scores...")
scored = score_dataframe(df)

os.makedirs("data", exist_ok=True)
cache = {
    "timestamp": datetime.now().isoformat(),
    "data": scored.replace({float("nan"): None}).to_dict(orient="records"),
}
with open("data/cache_datos.json", "w") as f:
    json.dump(cache, f)

print()
print("=" * 40)
print(f"  LISTO! {len(scored)} tickers descargados")
print("  Archivo: data/cache_datos.json")
print("  Subilo a GitHub en la carpeta data/")
print("=" * 40)
input("\nPresioná Enter para cerrar...")
