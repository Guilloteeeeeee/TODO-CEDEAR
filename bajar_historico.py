"""
v1.5.48: baja de Yahoo Finance TODA la historia de precios de cada empresa y cada ETF de la app y la guarda en el archivo histórico propio
(data/historico/): el cierre de cada mes (ajustado por splits, no por dividendos), cada dividendo pagado y cada split.

- La primera vez trae toda la historia (en muchas empresas, décadas). Después, cada vez que lo corras, suma los meses nuevos.
- Lo ya guardado nunca se borra. Si aparece un split nuevo, los precios y dividendos guardados de antes de esa fecha se ajustan solos
  (queda anotado en data/historico/cambios.json).
- No cambia el cache ni los puntajes.

Uso (desde la carpeta del proyecto):
    python bajar_historico.py              (todas las empresas y ETFs, unos 10 a 20 minutos)
    python bajar_historico.py KO NFLX SPY  (solo esos)
Conviene correrlo una vez por mes (por ejemplo, junto con generar_cache.bat).
"""
import datetime
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import historico as H  # noqa: E402
from data.fetcher import _con_tope  # noqa: E402

PAUSA_S = 0.8
TOPE_S = 60
MAX_FALLOS_SEGUIDOS = 8


def _universo():
    import json
    from data import etfs as et
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    emp = [(r["ticker"], r["ticker"]) for r in cache]
    etf = [(e["ticker"], et.simbolo_yahoo(e)) for e in et.cargar()]
    vistos, out = set(), []
    for t, s in emp + etf:
        if t not in vistos:
            vistos.add(t)
            out.append((t, s))
    return out


def bajar_uno(simbolo):
    """(pares diarios [(date, cierre)], dividendos [[fecha, monto]], splits [[fecha, factor]]) de toda la historia, o None."""
    import yfinance as yf
    h = yf.Ticker(str(simbolo)).history(period="max", interval="1d", auto_adjust=False, actions=True)
    if h is None or h.empty or "Close" not in h:
        return None
    fechas = [i.date() for i in h.index]
    pares = [(f, float(c)) for f, c in zip(fechas, h["Close"]) if c == c and c > 0]
    divs = [[f.isoformat(), float(v)] for f, v in zip(fechas, h["Dividends"]) if v == v and v > 0] if "Dividends" in h else []
    sps = [[f.isoformat(), float(v)] for f, v in zip(fechas, h["Stock Splits"]) if v == v and v > 0 and v != 1.0] if "Stock Splits" in h else []
    return pares, divs, sps


def main(tickers=None):
    todos = _universo()
    if tickers:
        pedidos = {t.upper() for t in tickers}
        todos = [(t, s) for t, s in todos if t in pedidos] + [(t, t) for t in pedidos if t not in {x for x, _ in todos}]
    archivos = {"precios": H.leer("precios_mensuales.json", {}), "dividendos": H.leer("dividendos.json", {}), "splits": H.leer("splits.json", {})}
    cambios = H.leer("cambios.json", [])
    avisos, ok, seguidos, splits_ajustados = [], 0, 0, []
    print(f"Bajando la historia de precios, dividendos y splits de {len(todos)} empresas y ETFs (uno por uno; no cierres la ventana)...")
    for i, (t, sim) in enumerate(todos, 1):
        t0 = time.time()
        try:
            termino, res = _con_tope(bajar_uno, (sim,), TOPE_S)
        except Exception as ex:  # noqa: BLE001
            termino, res = True, None
            avisos.append(f"{t}: error ({type(ex).__name__}: {str(ex)[:80]})")
        if not termino or not res:
            seguidos += 1
            print(f"  {i:3d}/{len(todos)} {t:6} SIN DATOS" + (" (no respondió a tiempo)" if not termino else ""))
            if termino and res is None:
                avisos.append(f"{t}: Yahoo no trajo historia ({sim})")
            if seguidos >= MAX_FALLOS_SEGUIDOS:
                avisos.append(f"Yahoo dejó de responder ({seguidos} seguidos sin datos): se corta acá. Lo ya bajado quedó guardado; probá de nuevo en un rato.")
                break
            continue
        seguidos = 0
        pares, divs, sps = res
        nuevos = H.archivar_mercado(t, pares, divs, sps, archivos=archivos, cambios=cambios)
        if nuevos:
            splits_ajustados.append(f"{t}: split nuevo {', '.join(f'{f} ({x:g} por 1)' for f, x in nuevos)} → se ajustaron los precios y dividendos guardados")
        ok += 1
        meses = len((archivos["precios"].get(t) or {}).get("m") or {})
        print(f"  {i:3d}/{len(todos)} {t:6} ok  {meses} meses desde {min((archivos['precios'][t]['m']) or ['?'])}, {len(divs)} dividendos, {len(sps)} splits")
        if i % 25 == 0:
            H.guardar_mercado(archivos, cambios)
        time.sleep(max(0.0, PAUSA_S - (time.time() - t0)))
    H.guardar_mercado(archivos, cambios)
    r = H.resumen()
    texto = [f"Historia bajada: {ok} de {len(todos)} ({datetime.datetime.now():%d/%m/%Y %H:%M})",
             f"Archivo: {r['tickers_con_precios']} con precios mensuales ({r['cierres_mensuales']} cierres; el más viejo, {r['mes_mas_viejo']}), "
             f"{r['con_dividendos']} con dividendos, {r['con_splits']} con splits", ""] + splits_ajustados + [f"- {a}" for a in avisos]
    with open(os.path.join(AQUI, "resultados_historico.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Se actualizó la carpeta data/historico (subila a GitHub) y resultados_historico.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
