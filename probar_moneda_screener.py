"""
Control de moneda del Screener (v1.2.11): para empresas de afuera de EEUU compara lo que informa
Yahoo con lo que calcula el Screener despues del ajuste de moneda / acciones por ADR.

Uso (desde la carpeta del proyecto):
    python probar_moneda_screener.py
    python probar_moneda_screener.py SONY TSM SAP        (otros tickers)

Guarda resultados_moneda_screener.txt: mandalo para revisarlo.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf

from data import moneda
from data.fetcher import fetch_ticker_data

TICKERS_DEFECTO = ["VALE", "PBR", "ITUB", "TSM", "ASML", "SAP", "TM", "SONY", "BABA", "HDB", "MUFG", "DEO", "NVO", "BP", "BRK-B"]


def _fmt(x, d=2):
    try:
        return f"{float(x):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def main(tickers):
    out = []
    for sym in tickers:
        out.append(f"\n===== {sym} =====")
        try:
            info = yf.Ticker(sym).info or {}
            precio = info.get("currentPrice") or info.get("regularMarketPrice")
            mc = info.get("marketCap")
            out.append(
                f"Yahoo: pais={info.get('country')} | moneda cotizacion={info.get('currency')} | "
                f"moneda estados={info.get('financialCurrency')} | precio={_fmt(precio)} | marketCap={_fmt(mc, 0)}"
            )
            out.append(
                f"Yahoo (multiplos actuales): PER={_fmt(info.get('trailingPE'))} | P/B={_fmt(info.get('priceToBook'))} | "
                f"EV/EBITDA={_fmt(info.get('enterpriseToEbitda'))} | P/S={_fmt(info.get('priceToSalesTrailing12Months'))}"
            )
            sh = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
            n_inv = moneda.factor_acciones_adr(mc, precio, sh)
            out.append(f"Acciones: sharesOutstanding={_fmt(sh, 0)} | factor por ADR={_fmt(n_inv, 3)} "
                       f"(~{_fmt(1 / n_inv, 1) if n_inv else '—'} ordinarias por ADR)")

            r = fetch_ticker_data(sym)
            out.append(f"Screener: moneda_cotizacion={r.get('moneda_cotizacion')} | estados={r.get('moneda_estados')}")
            out.append(f"  Nota: {r.get('moneda_nota') or '(sin ajuste)'}")
            for m in ("per", "p_b", "ev_ebitda", "p_fcf"):
                out.append(f"  {m:10s} actual={_fmt(r.get(m + '_actual')):>10s}   mediana historica={_fmt(r.get(m + '_mediana')):>10s}")
        except Exception as e:  # noqa: BLE001
            out.append(f"  FALLO: {type(e).__name__}: {e}")
            out.append(traceback.format_exc(limit=3))
    txt = "\n".join(out)
    with open("resultados_moneda_screener.txt", "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print("\nListo. Se guardo resultados_moneda_screener.txt: mandalo.")


if __name__ == "__main__":
    main([a.upper() for a in sys.argv[1:]] or TICKERS_DEFECTO)
    try:
        input("\nPresiona Enter para cerrar...")
    except EOFError:
        pass
