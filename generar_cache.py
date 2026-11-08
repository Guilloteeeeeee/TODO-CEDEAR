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

from data.fetcher import fetch_all_tickers_seguro
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
print("Esto tarda 15-30 minutos. Vas a ver el avance empresa por empresa.")
print(f"Python {sys.version.split()[0]}")
print()

# v1.5.43: el dato anterior de cada empresa sirve de respaldo si Yahoo no responde (la corrida del 07/11 se colgó 4 horas)
_respaldo = {}
try:
    with open("data/cache_datos.json", encoding="utf-8") as f:
        _c = json.load(f)
    _f_ant = str(_c.get("timestamp") or "")[:10]
    for _r in _c.get("data") or []:
        if _r.get("ticker"):
            _r.setdefault("fecha_dato", _f_ant)
            _respaldo[_r["ticker"]] = _r
except Exception:
    _respaldo = {}

df, _info = fetch_all_tickers_seguro(tickers, respaldo=_respaldo, parcial="data/cache_parcial.json")
print()
if _info["respaldo"]:
    print(f"  {len(_info['respaldo'])} empresas quedaron con su dato anterior (no respondieron hoy): {', '.join(_info['respaldo'][:30])}{' ...' if len(_info['respaldo']) > 30 else ''}")
if _info["cortado"]:
    print("  Yahoo dejó de responder a mitad de camino. Lo bajado quedó guardado: volvé a correr generar_cache.bat más tarde y sigue desde ahí.")
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
# v1.5.48: archivo histórico propio: foto del mes (precio, múltiplos, score, categoría y la calidad del Análisis Fundamental)
try:
    from data import historico as _hist
    from data import analisis_fundamental as _AFh
    _af = _AFh.cargar()[0] or {}
    _n_foto = _hist.foto_mensual("empresas", {r["ticker"]: r for r in cache.get("data", [])}, _hist.CAMPOS_FOTO_EMPRESA,
                                 extra={t: {"calidad_af": a.get("calidad"), "fecha_af": a.get("fecha")} for t, a in _af.items() if isinstance(a, dict) and a.get("calidad")})
    print(f"  Archivo histórico: foto del mes guardada ({_n_foto} empresas) en data/historico/fotos/")
except Exception as _e:  # noqa: BLE001
    print(f"  (No se pudo guardar la foto del mes en el archivo histórico: {_e})")
try:
    os.remove("data/cache_parcial.json")   # v1.5.43: la corrida terminó bien, el avance parcial ya no hace falta
except OSError:
    pass

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
