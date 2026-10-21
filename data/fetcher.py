"""
Módulo de descarga de datos desde Yahoo Finance (yfinance).
Obtiene métricas actuales e históricas para calcular medianas.

Métricas que descarga por ticker:
  - EV/EBITDA actual e histórico (últimos 5 años anuales)
  - P/E Ratio (PER) actual e histórico
  - P/FCF actual e histórico
  - P/B actual e histórico
  - Dividend Yield actual e histórico
  - PEG actual
  - P/FFO y P/AFFO (solo REITs — aproximado via P/E ajustado)
  - Precio actual, máximo y mínimo 52 semanas
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)

# Años de histórico para calcular medianas
HISTORY_YEARS = 5

# Pausa entre requests para no saturar la API
REQUEST_DELAY = 0.3  # segundos


def _safe_get(obj, *keys, default=None):
    """Navega un dict anidado de forma segura."""
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return default
    return obj if obj is not None else default


def fetch_ticker_data(ticker: str) -> dict:
    """
    Descarga todos los datos necesarios para un ticker.
    Retorna un dict con métricas actuales e históricas.
    En caso de error, retorna dict con valores None.
    """
    result = {
        "ticker": ticker,
        "nombre": None,
        "pais": None,
        "sector_yf": None,
        "market_cap": None,
        "precio_actual": None,
        "precio_max_52s": None,
        "precio_min_52s": None,
        "posicion_52s": None,           # (precio - min) / (max - min), de 0 a 1
        # Valores actuales
        "ev_ebitda_actual": None,
        "per_actual": None,
        "p_fcf_actual": None,
        "p_b_actual": None,
        "dividend_yield_actual": None,
        "peg_actual": None,
        "p_ffo_actual": None,           # REITs
        "p_affo_actual": None,          # REITs
        # Medianas históricas (últimos HISTORY_YEARS años)
        "ev_ebitda_mediana": None,
        "per_mediana": None,
        "p_fcf_mediana": None,
        "p_b_mediana": None,
        "dividend_yield_mediana": None,
        "peg_mediana": None,
        "p_ffo_mediana": None,
        "p_affo_mediana": None,
        # Metadatos
        "error": None,
        "metricas_disponibles": 0,
    }

    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        if not info or info.get("regularMarketPrice") is None:
            result["error"] = "Sin datos en Yahoo Finance"
            return result

        # --- Datos básicos ---
        result["nombre"] = info.get("shortName") or info.get("longName") or ticker
        result["pais"] = info.get("country")
        result["sector_yf"] = info.get("sector")
        result["market_cap"] = info.get("marketCap")
        result["precio_actual"] = info.get("currentPrice") or info.get("regularMarketPrice")
        result["precio_max_52s"] = info.get("fiftyTwoWeekHigh")
        result["precio_min_52s"] = info.get("fiftyTwoWeekLow")

        # --- Posición en rango 52 semanas (0 = mínimo, 1 = máximo) ---
        p = result["precio_actual"]
        hi = result["precio_max_52s"]
        lo = result["precio_min_52s"]
        if p and hi and lo and hi != lo:
            result["posicion_52s"] = round((p - lo) / (hi - lo), 4)

        # --- Métricas actuales desde info ---
        result["ev_ebitda_actual"] = info.get("enterpriseToEbitda")
        result["per_actual"] = info.get("trailingPE") or info.get("forwardPE")
        result["p_b_actual"] = info.get("priceToBook")
        result["dividend_yield_actual"] = info.get("dividendYield")
        result["peg_actual"] = info.get("pegRatio")

        # P/FCF: market cap / free cash flow
        fcf = info.get("freeCashflow")
        mktcap = result["market_cap"]
        if fcf and mktcap and fcf > 0:
            result["p_fcf_actual"] = round(mktcap / fcf, 2)

        # P/FFO y P/AFFO para REITs (aproximación):
        # yfinance no expone FFO directamente.
        # Usamos P/E como proxy del P/FFO (suficientemente bueno para screening).
        result["p_ffo_actual"] = result["per_actual"]
        result["p_affo_actual"] = result["per_actual"]

        # --- Histórico anual para medianas ---
        time.sleep(REQUEST_DELAY)
        _enrich_with_history(tk, result)

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"Error fetching {ticker}: {e}")

    # Contar métricas disponibles
    metric_keys = [
        "ev_ebitda_actual", "per_actual", "p_fcf_actual", "p_b_actual",
        "dividend_yield_actual", "peg_actual", "p_ffo_actual", "p_affo_actual"
    ]
    result["metricas_disponibles"] = sum(
        1 for k in metric_keys if result[k] is not None
    )

    return result


def _enrich_with_history(tk: yf.Ticker, result: dict) -> None:
    """
    Agrega medianas históricas al resultado usando los estados financieros anuales.
    Modifica result in-place.
    """
    try:
        # Financials anuales
        income = tk.financials          # income statement anual
        balance = tk.balance_sheet      # balance sheet anual
        cashflow = tk.cashflow          # cash flow anual

        # Precio histórico anual para calcular múltiplos históricos
        hist = tk.history(period=f"{HISTORY_YEARS}y", interval="1mo")
        if hist.empty:
            return

        # EV/EBITDA histórico: necesita EBITDA y EV (deuda + market cap - caja)
        ev_ebitda_list = _calc_ev_ebitda_history(tk, income, balance, hist)
        if ev_ebitda_list:
            result["ev_ebitda_mediana"] = round(float(np.median(ev_ebitda_list)), 2)

        # PER histórico: EPS anual vs precio fin de año
        per_list = _calc_per_history(income, hist)
        if per_list:
            result["per_mediana"] = round(float(np.median(per_list)), 2)

        # P/FCF histórico
        pfcf_list = _calc_pfcf_history(cashflow, balance, hist)
        if pfcf_list:
            result["p_fcf_mediana"] = round(float(np.median(pfcf_list)), 2)

        # P/B histórico
        pb_list = _calc_pb_history(balance, hist)
        if pb_list:
            result["p_b_mediana"] = round(float(np.median(pb_list)), 2)

        # Dividend Yield histórico
        dy_list = _calc_divy_history(tk, hist)
        if dy_list:
            result["dividend_yield_mediana"] = round(float(np.median(dy_list)), 4)

        # PEG: no calculamos histórico, usamos el actual como mediana
        result["peg_mediana"] = result["peg_actual"]

        # FFO/AFFO: usamos PER como proxy
        result["p_ffo_mediana"] = result["per_mediana"]
        result["p_affo_mediana"] = result["per_mediana"]

    except Exception as e:
        logger.debug(f"Error en histórico para {result['ticker']}: {e}")


def _get_annual_price(hist: pd.DataFrame, year: int) -> Optional[float]:
    """Precio de cierre al final de un año dado."""
    try:
        year_data = hist[hist.index.year == year]
        if not year_data.empty:
            return float(year_data["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _calc_ev_ebitda_history(tk, income, balance, hist) -> list:
    """Calcula EV/EBITDA para cada año disponible."""
    values = []
    try:
        shares = tk.info.get("sharesOutstanding", 0)
        for col in income.columns[:HISTORY_YEARS]:
            year = col.year
            price = _get_annual_price(hist, year)
            if not price or not shares:
                continue

            ebitda = _safe_get(income, "EBITDA", col) if "EBITDA" in income.index else None
            if ebitda is None:
                # Reconstruir: EBIT + D&A
                ebit_row = next((r for r in income.index if "EBIT" in str(r) and "DA" not in str(r)), None)
                da_row = next((r for r in income.index if "Depreciation" in str(r)), None)
                if ebit_row and da_row:
                    ebitda = income.loc[ebit_row, col] + abs(income.loc[da_row, col])

            debt_row = next((r for r in balance.index if "Total Debt" in str(r) or "LongTermDebt" in str(r)), None)
            cash_row = next((r for r in balance.index if "Cash" in str(r) and "Equivalents" in str(r)), None)

            if ebitda and debt_row:
                debt = balance.loc[debt_row, col] if col in balance.columns else 0
                cash = balance.loc[cash_row, col] if cash_row and col in balance.columns else 0
                market_cap = price * shares
                ev = market_cap + (debt or 0) - (cash or 0)
                if ebitda > 0:
                    val = ev / ebitda
                    if 0 < val < 200:  # filtrar outliers
                        values.append(val)
    except Exception as e:
        logger.debug(f"EV/EBITDA history error: {e}")
    return values


def _calc_per_history(income, hist) -> list:
    """Calcula PER para cada año disponible."""
    values = []
    try:
        eps_row = next((r for r in income.index if "EPS" in str(r) or "Earnings Per Share" in str(r)), None)
        ni_row = next((r for r in income.index if "Net Income" in str(r)), None)

        for col in income.columns[:HISTORY_YEARS]:
            year = col.year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            eps = None
            if eps_row:
                eps = income.loc[eps_row, col]
            elif ni_row:
                # EPS aproximado si tenemos shares
                pass  # lo dejamos para cuando tengamos shares del histórico

            if eps and eps > 0:
                val = price / eps
                if 0 < val < 500:
                    values.append(val)
    except Exception as e:
        logger.debug(f"PER history error: {e}")
    return values


def _calc_pfcf_history(cashflow, balance, hist) -> list:
    """Calcula P/FCF para cada año disponible."""
    values = []
    try:
        fcf_row = next((r for r in cashflow.index if "Free Cash Flow" in str(r)), None)
        shares_row = next((r for r in balance.index if "Ordinary Shares Number" in str(r)
                           or "Share Issued" in str(r)), None)

        if not fcf_row:
            return values

        for col in cashflow.columns[:HISTORY_YEARS]:
            year = col.year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            fcf = cashflow.loc[fcf_row, col]
            shares = balance.loc[shares_row, col] if shares_row and col in balance.columns else None

            if fcf and shares and fcf > 0 and shares > 0:
                fcf_per_share = fcf / shares
                val = price / fcf_per_share
                if 0 < val < 500:
                    values.append(val)
    except Exception as e:
        logger.debug(f"P/FCF history error: {e}")
    return values


def _calc_pb_history(balance, hist) -> list:
    """Calcula P/B para cada año disponible."""
    values = []
    try:
        equity_row = next((r for r in balance.index
                           if "Stockholders Equity" in str(r) or "Total Equity" in str(r)), None)
        shares_row = next((r for r in balance.index
                           if "Ordinary Shares Number" in str(r) or "Share Issued" in str(r)), None)

        if not equity_row or not shares_row:
            return values

        for col in balance.columns[:HISTORY_YEARS]:
            year = col.year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            equity = balance.loc[equity_row, col]
            shares = balance.loc[shares_row, col]

            if equity and shares and shares > 0:
                bvps = equity / shares
                if bvps > 0:
                    val = price / bvps
                    if 0 < val < 100:
                        values.append(val)
    except Exception as e:
        logger.debug(f"P/B history error: {e}")
    return values


def _calc_divy_history(tk, hist) -> list:
    """Calcula Dividend Yield histórico usando dividendos pagados."""
    values = []
    try:
        divs = tk.dividends
        if divs.empty:
            return values

        for year in range(hist.index[-1].year - HISTORY_YEARS + 1, hist.index[-1].year + 1):
            annual_div = divs[divs.index.year == year].sum()
            price = _get_annual_price(hist, year)
            if annual_div > 0 and price and price > 0:
                val = annual_div / price
                if 0 < val < 0.5:  # máximo 50% yield, filtrar outliers
                    values.append(val)
    except Exception as e:
        logger.debug(f"DivY history error: {e}")
    return values


def fetch_all_tickers(tickers: list, progress_callback=None) -> pd.DataFrame:
    """
    Descarga datos para una lista de tickers.
    progress_callback(i, total, ticker): función opcional para mostrar progreso.
    Retorna DataFrame con una fila por ticker.
    """
    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i, total, ticker)
        logger.info(f"Fetching {ticker} ({i+1}/{total})")
        data = fetch_ticker_data(ticker)
        results.append(data)
        time.sleep(REQUEST_DELAY)

    return pd.DataFrame(results)
