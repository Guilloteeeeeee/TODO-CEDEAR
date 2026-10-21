"""
Actualiza el cache solo para algunos tickers, SIN volver a descargar los 166.
Correr desde la carpeta raiz del proyecto:

    python actualizar_ticker.py BNY
    python actualizar_ticker.py --extranjeras      (todas las empresas de fuera de EEUU)

- Descarga y puntua solo los tickers indicados (segundos, no minutos).
- Reemplaza (o agrega) esas filas en data/cache_datos.json.
- Quita del cache los tickers que ya no estan en el universo (ej: BK, ahora BNY).
- Mantiene la fecha original del cache (el resto de los datos no cambia).
- v1.2.11: al final vuelve a puntuar TODAS las filas con los datos que ya estan guardados
  (sin descargar nada) para que el PEG se compare con la mediana actual de su sector.
- v1.2.11: --extranjeras usa el control de moneda nuevo (data/moneda.py) en las empresas de
  fuera de EEUU, que son las que tenian medianas rotas por mezclar monedas / acciones de ADR.
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
from data.resumen import resumen_fuentes
try:
    from config.ajustes import STOCK_ANALYSIS_MODO
except Exception:
    STOCK_ANALYSIS_MODO = "respaldo"

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


def extranjeras_del_cache():
    """Tickers del cache cuyo pais no es Estados Unidos (incluye los que no tienen pais cargado)."""
    if not os.path.exists(CACHE_PATH):
        return []
    with open(CACHE_PATH) as f:
        filas = json.load(f)["data"]
    return [r["ticker"] for r in filas
            if r.get("pais") != "United States" and r["ticker"] in TICKER_TO_SECTOR]


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

    # Referencia para el PEG del sector: las filas que ya estan guardadas
    referencia = pd.DataFrame(filas) if filas else None
    nuevas = _limpiar(score_dataframe(ok, referencia=referencia).replace({float("nan"): None}).to_dict(orient="records"))
    tickers_ok = {r["ticker"] for r in nuevas}

    # Quitar filas reemplazadas y las que ya no pertenecen al universo (ej: BK)
    obsoletos = {r["ticker"] for r in filas if r["ticker"] not in TICKER_TO_SECTOR}
    if obsoletos:
        print(f"Se quitan del cache (ya no estan en el universo): {', '.join(sorted(obsoletos))}")
    filas = [r for r in filas if r["ticker"] not in tickers_ok and r["ticker"] not in obsoletos]
    filas.extend(nuevas)

    # Volver a puntuar todo con lo ya guardado (sin descargar): deja el PEG de todas las
    # empresas comparado con la mediana de sector actualizada.
    try:
        filas = _limpiar(score_dataframe(pd.DataFrame(filas)).replace({float("nan"): None}).to_dict(orient="records"))
    except Exception as e:  # nunca perder lo descargado por un error de re-puntuacion
        print(f"  ! No se pudo re-puntuar todo el cache ({e}). Se guardan igual las filas nuevas.")

    cache["data"] = filas
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)

    # Releer el archivo para confirmar que quedo guardado
    with open(CACHE_PATH) as f:
        guardados = {r["ticker"] for r in json.load(f)["data"]}
    print()
    for r in nuevas:
        extra = f" | moneda: {r['moneda_nota']}" if r.get("moneda_nota") else ""
        print(f"  OK {r['ticker']}: {r['categoria']} (score {r['score_total']}, "
              f"metricas {r.get('metricas_usadas')}/{r.get('metricas_total')}, "
              f"DY {r['dividend_yield_actual']}, precio {r['precio_actual']}){extra}")
    try:
        resumen = resumen_fuentes(pd.DataFrame(nuevas), STOCK_ANALYSIS_MODO)
        print("\n" + resumen)
        with open("resultados_cache.txt", "w", encoding="utf-8") as f:
            f.write(resumen)
    except Exception as e:
        print(f"  (No se pudo armar el resumen de fuentes: {e})")
    print(f"\nVerificacion: {', '.join(sorted(tickers_ok))} "
          f"{'ESTA' if tickers_ok <= guardados else 'NO ESTA'} en el archivo guardado.")
    print(f"\nListo. Cache con {len(filas)} tickers.")
    print("ARCHIVO MODIFICADO (este es el que hay que subir a GitHub, a la carpeta data/):")
    print("  " + os.path.abspath(CACHE_PATH))
    return 0


if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:] if not a.startswith("--")] or []
    if any(a.lower() == "--extranjeras" for a in sys.argv[1:]):
        args = extranjeras_del_cache() + [a for a in args if a not in extranjeras_del_cache()]
    args = args or ["BNY"]
    code = main(args)
    input("\nPresiona Enter para cerrar...")
    sys.exit(code)
