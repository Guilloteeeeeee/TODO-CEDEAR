"""
Actualiza el cache solo para algunos tickers, SIN volver a descargar los 166.
Correr desde la carpeta raiz del proyecto:

    python actualizar_ticker.py BNY

- Descarga y puntua solo los tickers indicados (segundos, no minutos).
- Reemplaza (o agrega) esas filas en data/cache_datos.json.
- Quita del cache los tickers que ya no estan en el universo (ej: BK, ahora BNY).
- Mantiene la fecha original del cache (el resto de los datos no cambia).
"""
import sys
import os
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import fetch_all_tickers
from scoring.engine import score_dataframe
from config.sectors import TICKER_TO_SECTOR

CACHE_PATH = "data/cache_datos.json"


def _limpiar(o):
    """NaN -> None (tambien dentro de diccionarios anidados) para guardar JSON valido."""
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _limpiar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_limpiar(v) for v in o]
    return o


def main(tickers):
    if not os.path.exists(CACHE_PATH):
        print(f"No encuentro {CACHE_PATH}. Corre primero generar_cache.bat")
        return 1

    with open(CACHE_PATH) as f:
        cache = json.load(f)
    filas = cache["data"]

    print(f"Descargando: {', '.join(tickers)} ...")
    df = fetch_all_tickers(tickers)
    ok = df[df["precio_actual"].notna()]
    fallidos = [t for t in tickers if t not in set(ok["ticker"])]
    for t in fallidos:
        err = df.loc[df["ticker"] == t, "error"].iloc[0] if (df["ticker"] == t).any() else "?"
        print(f"  ! {t}: no se pudo descargar ({err}). Se deja como estaba.")
    if ok.empty:
        print("No se descargo ningun ticker, no se modifica el cache.")
        return 1

    nuevas = _limpiar(score_dataframe(ok).replace({float("nan"): None}).to_dict(orient="records"))
    tickers_ok = {r["ticker"] for r in nuevas}

    # Quitar filas reemplazadas y las que ya no pertenecen al universo (ej: BK)
    obsoletos = {r["ticker"] for r in filas if r["ticker"] not in TICKER_TO_SECTOR}
    if obsoletos:
        print(f"Se quitan del cache (ya no estan en el universo): {', '.join(sorted(obsoletos))}")
    filas = [r for r in filas if r["ticker"] not in tickers_ok and r["ticker"] not in obsoletos]
    filas.extend(nuevas)

    cache["data"] = filas
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)

    # Releer el archivo para confirmar que quedo guardado
    with open(CACHE_PATH) as f:
        guardados = {r["ticker"] for r in json.load(f)["data"]}
    print()
    for r in nuevas:
        print(f"  OK {r['ticker']}: {r['categoria']} (score {r['score_total']}, "
              f"DY {r['dividend_yield_actual']}, precio {r['precio_actual']})")
    print(f"\nVerificacion: {', '.join(sorted(tickers_ok))} "
          f"{'ESTA' if tickers_ok <= guardados else 'NO ESTA'} en el archivo guardado.")
    print(f"\nListo. Cache con {len(filas)} tickers.")
    print("ARCHIVO MODIFICADO (este es el que hay que subir a GitHub, a la carpeta data/):")
    print("  " + os.path.abspath(CACHE_PATH))
    return 0


if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]] or ["BNY"]
    code = main(args)
    input("\nPresiona Enter para cerrar...")
    sys.exit(code)
