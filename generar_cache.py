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
from data.resumen import resumen_fuentes
from data.cache_seguro import validar_cache, guardar_seguro, marcar_fecha_dato
try:
    from config.ajustes import STOCK_ANALYSIS_MODO
except Exception:
    STOCK_ANALYSIS_MODO = "respaldo"

print("=" * 40)
print("  CEDEAR Screener - Generar Cache")
print("=" * 40)
print()

tickers = [t for ts in TICKER_UNIVERSE.values() for t in ts]
print(f"Descargando {len(tickers)} tickers...")
print(f"Fuente principal de los ratios: {'Stock Analysis (Yahoo de respaldo)' if STOCK_ANALYSIS_MODO == 'principal' else 'Yahoo Finance'}")
print("Esto tarda 10-15 minutos, esperá...")
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
ahora = datetime.now()
cache = {
    "timestamp": ahora.isoformat(),
    "data": marcar_fecha_dato(_limpiar(scored.replace({float("nan"): None}).to_dict(orient="records")), ahora.date().isoformat()),
}

# v1.2.50 - Antes de reemplazar el cache bueno se controla que la descarga no haya salido rota (Yahoo o Stock Analysis caidos, cortes de
# internet): empresas con precio, cantidad de filas y de puntajes contra el cache anterior. Si no pasa, el cache bueno NO se toca.
CACHE_PATH = "data/cache_datos.json"
anterior = None
if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            anterior = json.load(f).get("data")
    except Exception:
        anterior = None          # el cache actual esta roto: no hay con que comparar, pero igual se exige lo minimo
ok, problemas = validar_cache(cache["data"], anterior, tickers)
if not ok and "--forzar" not in sys.argv:
    rechazado = "data/cache_rechazado.json"
    try:
        guardar_seguro(cache, rechazado)
    except Exception:
        rechazado = None
    print()
    print("=" * 40)
    print("  ATENCION: la descarga salio incompleta, NO se reemplazo el cache")
    for pr in problemas:
        print(f"   - {pr}")
    print("  El cache anterior sigue intacto (data/cache_datos.json).")
    if rechazado:
        print(f"  Lo descargado se guardo aparte en {rechazado} por si queres revisarlo.")
    print("  Proba de nuevo en un rato. Si queres guardarlo igual: python generar_cache.py --forzar")
    print("=" * 40)
    input("\nPresioná Enter para cerrar...")
    sys.exit(1)

guardar_seguro(cache, CACHE_PATH)      # escribe a un temporal, lo relee y recien ahi reemplaza el archivo bueno

# v1.2.11 - Historial: copia con fecha para poder comparar como cambian los datos entre actualizaciones (solo si el cache paso los controles)
copia = None
try:
    os.makedirs("data/historial", exist_ok=True)
    copia = f"data/historial/cache_{datetime.now():%Y-%m-%d}.json"
    guardar_seguro(cache, copia)
except Exception as e:
    print(f"  (No se pudo guardar la copia del historial: {e})")
    copia = None

# v1.2.13 - Resumen de que fuente aporto cada dato (se guarda tambien en resultados_cache.txt)
resumen = resumen_fuentes(scored, STOCK_ANALYSIS_MODO)
try:
    with open("resultados_cache.txt", "w", encoding="utf-8") as f:
        f.write(resumen)
except Exception:
    pass
print()
print(resumen)

print()
print("=" * 40)
print(f"  LISTO! {len(scored)} tickers descargados")
print("  Archivo: data/cache_datos.json")
if copia:
    print(f"  Copia para el historial: {copia}")
print("  Subilo a GitHub en la carpeta data/ (incluida la carpeta historial/)")
try:
    from config.ajustes import proxima_actualizacion
    _prox = proxima_actualizacion()
    if _prox:
        print(f"  Proxima actualizacion completa sugerida: {_prox:%d/%m/%Y} (despues de la temporada de resultados)")
except Exception:
    pass
print("  Mandame resultados_cache.txt (el resumen de fuentes)")
print("=" * 40)
input("\nPresioná Enter para cerrar...")
