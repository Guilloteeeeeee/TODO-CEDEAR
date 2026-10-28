"""
Baja de Yahoo Finance el historial de precios (14 meses de cierres y volumen) de cada empresa y cada ETF y calcula los parametros tecnicos del filtro
(RSI, precio contra sus promedios de 50 y 200 ruedas, distancia al maximo de 52 semanas, rendimientos y volumen relativo). Todo se guarda en
data/tecnicos.json. NO cambia nada mas. Conviene correrlo una vez por semana (o cuando quieras datos frescos) y subir data/tecnicos.json a GitHub.

Uso (desde la carpeta del proyecto):
    python bajar_tecnicos.py            (todo: unos 2 a 4 minutos)
    python bajar_tecnicos.py AAPL SPY   (solo esos; el resto queda como estaba)
Pide de a 20 con pausa; si un grupo falla se reintenta uno por uno.
"""
import datetime
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import etfs as et  # noqa: E402
from data import tecnicos as tec  # noqa: E402

LOTE = 20
PAUSA_S = 2.0


def _tickers_empresas():
    try:
        with open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8") as f:
            return [r["ticker"] for r in json.load(f)["data"] if r.get("ticker")]
    except Exception:  # noqa: BLE001
        return []


def _series(df):
    """([(fecha, cierre)], [(fecha, volumen)]) de un DataFrame de Yahoo con columnas Close y Volume."""
    from data import historial_precios as hp
    if df is None or len(df) == 0 or "Close" not in df.columns:
        return [], []
    fechas = [i.date() if hasattr(i, "date") else i for i in df.index]
    pares = hp.limpiar(fechas, list(df["Close"]))
    vol = []
    if "Volume" in df.columns:
        vol = [(f, float(v)) for f, v in zip(fechas, df["Volume"]) if v == v]
    return pares, vol


def _lote(yf, simbolos):
    """{simbolo: DataFrame} de un pedido grupal; {} si falla."""
    try:
        d = yf.download(simbolos, period="14mo", interval="1d", auto_adjust=False, group_by="ticker", progress=False, threads=True)
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for s in simbolos:
        try:
            sub = d[s] if len(simbolos) > 1 else d
            out[s] = sub.dropna(how="all")
        except Exception:  # noqa: BLE001
            pass
    return out


def main(elegidos=None):
    import yfinance as yf
    mapa = {t: t for t in _tickers_empresas()}                                  # ticker de la app -> simbolo de Yahoo
    for e in et.cargar():
        mapa.setdefault(e["ticker"], et.simbolo_yahoo(e))
    if elegidos:
        pedidos = {t.upper() for t in elegidos}
        mapa = {t: s for t, s in mapa.items() if t.upper() in pedidos}
    datos, _ = tec.cargar()
    fecha = datetime.datetime.now().strftime("%d/%m/%Y")
    items = list(mapa.items())
    avisos = []
    print(f"Bajando el historial de {len(items)} empresas y ETFs (de a {LOTE}, con pausa; no cierres la ventana)...")
    for i in range(0, len(items), LOTE):
        grupo = items[i:i + LOTE]
        dfs = _lote(yf, [s for _, s in grupo])
        for t, s in grupo:
            df = dfs.get(s)
            if df is None or len(df) < 30:                                       # reintento uno por uno
                try:
                    df = yf.Ticker(s).history(period="14mo", interval="1d", auto_adjust=False)
                except Exception:  # noqa: BLE001
                    df = None
            pares, vol = _series(df)
            r = tec.calcular(pares, vol)
            if r:
                datos[t.upper()] = r
            else:
                avisos.append(f"{t}: sin historial suficiente")
        print(f"  {min(i + LOTE, len(items))}/{len(items)}")
        time.sleep(PAUSA_S)
    with open(tec.RUTA, "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha, "datos": datos}, f, ensure_ascii=False)
    print(f"\nListo: {len(datos)} con parametros tecnicos. Subi data/tecnicos.json a GitHub.")
    if avisos:
        print("Avisos:\n  " + "\n  ".join(avisos))
        with open(os.path.join(AQUI, "resultados_tecnicos.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(avisos))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
