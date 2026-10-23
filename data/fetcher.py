"""
Módulo de descarga de datos desde Yahoo Finance (yfinance).
Obtiene métricas actuales e históricas para calcular medianas.

Estrategia de obtención de medianas (depende de config.ajustes.STOCK_ANALYSIS_MODO):
  "respaldo"  (por defecto):
     1. Calcular desde estados financieros históricos de yfinance (tk.financials, etc.)
     2. Si yfinance no tiene el dato → Stock Analysis (stockanalysis.com)
  "principal" (v1.2.12):
     1. Stock Analysis: valor actual y mediana de 5 años fiscales de la MISMA página
     2. Lo que Stock Analysis no trae → yfinance (con el control de moneda de data/moneda.py)
  "apagado": solo yfinance.
  Lo que no tenga mediana propia válida lo cubre el motor con la mediana del sector.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional
import logging
import time
import json
import os

from data import moneda   # v1.2.11: control de moneda / ADR

try:
    from config.ajustes import STOCK_ANALYSIS_MODO
except Exception:             # archivo de ajustes ausente: comportamiento de siempre
    STOCK_ANALYSIS_MODO = "respaldo"

_METRICAS = ("ev_ebitda", "per", "p_fcf", "p_b", "dividend_yield", "peg", "p_ffo", "p_affo", "ps")

logger = logging.getLogger(__name__)

# Años de histórico para calcular medianas
HISTORY_YEARS = 5

# Pausa entre requests para no saturar la API
REQUEST_DELAY = 0.3  # segundos

# Archivo de diagnóstico — se actualiza con cada fetch completo
# Útil para debuggear qué devuelve yfinance en producción (Streamlit Cloud)
_DEBUG_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "yf_debug_log.json")


def _pais_manual(ticker):
    """Pais de respaldo (config/sectors.py) para cuando Yahoo no lo informa."""
    try:
        from config.sectors import PAIS_MANUAL
        return PAIS_MANUAL.get(ticker)
    except Exception:  # noqa: BLE001
        return None


def _log_yf_debug(ticker: str, income, balance, cashflow, result: dict) -> None:
    """
    Guarda diagnóstico de lo que devolvió yfinance para este ticker.
    El archivo yf_debug_log.json se acumula con cada fetch (máx. 50 tickers).
    Para ver el diagnóstico: agregar ?debug=1 a la URL de Streamlit o usar el panel Debug.
    """
    try:
        def _df_info(df, name: str) -> dict:
            if df is None:
                return {"status": "None"}
            if df.empty:
                return {"status": "empty"}
            return {
                "status": "ok",
                "shape": list(df.shape),
                "columns": [str(c) for c in df.columns[:6]],
                "index": list(df.index[:30]),  # primeras 30 filas
            }

        entry = {
            "ticker": ticker,
            "income": _df_info(income, "income"),
            "balance": _df_info(balance, "balance"),
            "cashflow": _df_info(cashflow, "cashflow"),
            "medianas_calculadas": {
                k: result.get(k)
                for k in [
                    "ev_ebitda_mediana", "per_mediana", "p_fcf_mediana",
                    "p_b_mediana", "dividend_yield_mediana",
                ]
            },
        }

        # Leer log existente
        log = {}
        try:
            if os.path.exists(_DEBUG_LOG_PATH):
                with open(_DEBUG_LOG_PATH, "r", encoding="utf-8") as f:
                    log = json.load(f)
        except Exception:
            log = {}

        log[ticker] = entry

        # Mantener solo los últimos 50 tickers para no crecer indefinidamente
        if len(log) > 50:
            oldest_keys = list(log.keys())[:-50]
            for k in oldest_keys:
                del log[k]

        with open(_DEBUG_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2, default=str)

    except Exception as e:
        logger.debug(f"Error escribiendo debug log para {ticker}: {e}")


def _safe_float(val, min_val=None, max_val=None) -> Optional[float]:
    """Convierte a float de forma segura, con filtros de rango opcionales."""
    try:
        if val is None:
            return None
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        if min_val is not None and f < min_val:
            return None
        if max_val is not None and f > max_val:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _find_row(df: pd.DataFrame, *keywords, exclude=None) -> Optional[str]:
    """
    Busca la primera fila del DataFrame cuyo índice contenga TODOS los keywords.
    Si exclude es una lista, descarta filas que contengan alguna de esas palabras.
    """
    if df is None or df.empty:
        return None
    exclude = exclude or []
    for idx in df.index:
        idx_str = str(idx).lower()
        if all(kw.lower() in idx_str for kw in keywords):
            if not any(ex.lower() in idx_str for ex in exclude):
                return idx
    return None


def _get_col_value(df: pd.DataFrame, row_key: str, col) -> Optional[float]:
    """Obtiene un valor del DataFrame de forma segura."""
    try:
        if row_key is None or df is None or df.empty:
            return None
        if row_key not in df.index:
            return None
        if col not in df.columns:
            return None
        return _safe_float(df.loc[row_key, col])
    except Exception:
        return None


def _get_annual_price(hist: pd.DataFrame, year: int) -> Optional[float]:
    """Precio de cierre al final de un año dado."""
    try:
        year_data = hist[hist.index.year == year]
        if not year_data.empty:
            return _safe_float(year_data["Close"].iloc[-1])
    except Exception:
        pass
    return None


def fetch_ticker_data(ticker: str, modo_sa: Optional[str] = None) -> dict:
    """
    Descarga todos los datos necesarios para un ticker.
    Retorna un dict con métricas actuales e históricas.

    modo_sa: "apagado" | "respaldo" | "principal" (si es None se usa config.ajustes).
    La app publicada usa "apagado": Stock Analysis solo se consulta cuando se genera el caché en la PC.
    """
    modo = modo_sa or STOCK_ANALYSIS_MODO
    result = {
        "ticker": ticker,
        "nombre": None,
        "pais": None,
        "sector_yf": None,
        "market_cap": None,
        "precio_actual": None,
        "precio_max_52s": None,
        "precio_min_52s": None,
        "posicion_52s": None,
        # Valores actuales
        "ev_ebitda_actual": None,
        "per_actual": None,
        "p_fcf_actual": None,
        "p_b_actual": None,
        "dividend_yield_actual": None,
        "peg_actual": None,
        "p_ffo_actual": None,
        "p_affo_actual": None,
        "ps_actual": None,
        "annual_dividend": None,
        # Medianas históricas
        "ev_ebitda_mediana": None,
        "per_mediana": None,
        "p_fcf_mediana": None,
        "p_b_mediana": None,
        "dividend_yield_mediana": None,
        "peg_mediana": None,
        "p_ffo_mediana": None,
        "p_affo_mediana": None,
        "ps_mediana": None,
        # Metadatos
        "error": None,
        "metricas_disponibles": 0,
        # Control de moneda / ADR (v1.2.11)
        "moneda_estados": None,
        "moneda_cotizacion": None,
        "moneda_nota": None,
        # v1.2.12: de donde salio cada metrica ("Yahoo" / "Stock Analysis" / ...)
        "fuentes": {},
        # v1.2.28: cuantos anios de historia hay detras de cada mediana y la serie anual del Div. Yield
        "anios_historia": {},
        "dividend_yield_serie": None,
    }

    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}

        precio = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        if precio is None:
            result["error"] = "Sin datos en Yahoo Finance"
            return result

        # --- Datos básicos ---
        # longName trae el nombre completo; shortName lo corta a ~30 letras ("Mellon Cor", "Inc. New")
        result["nombre"] = info.get("longName") or info.get("shortName") or ticker
        result["pais"] = info.get("country") or _pais_manual(ticker)
        result["sector_yf"] = info.get("sector")
        result["market_cap"] = _safe_float(info.get("marketCap"))
        result["precio_actual"] = precio
        result["precio_max_52s"] = _safe_float(info.get("fiftyTwoWeekHigh"))
        result["precio_min_52s"] = _safe_float(info.get("fiftyTwoWeekLow"))

        # --- Posición en rango 52 semanas ---
        p = result["precio_actual"]
        hi = result["precio_max_52s"]
        lo = result["precio_min_52s"]
        if p and hi and lo and hi != lo:
            result["posicion_52s"] = round((p - lo) / (hi - lo), 4)

        # --- Métricas actuales desde info (múltiples campos alternativos) ---

        # EV/EBITDA
        result["ev_ebitda_actual"] = _safe_float(info.get("enterpriseToEbitda"), min_val=0, max_val=500)

        # PER: trailing primero, luego forward
        result["per_actual"] = (
            _safe_float(info.get("trailingPE"), min_val=0, max_val=2000) or
            _safe_float(info.get("forwardPE"), min_val=0, max_val=2000)
        )

        # P/B
        result["p_b_actual"] = _safe_float(info.get("priceToBook"), min_val=0, max_val=200)

        # Dividendo anual (para Fair Value por DY) — base para calcular el DY
        annual_div = (
            _safe_float(info.get("dividendRate"), min_val=0, max_val=100)
            or _safe_float(info.get("trailingAnnualDividendRate"), min_val=0, max_val=100)
        )
        result["annual_dividend"] = annual_div

        # Dividend Yield = dividendo anual / precio (decimal: 0.0128 = 1.28%).
        # NO se usa info["dividendYield"]: Yahoo cambió sus unidades a porcentaje
        # (1.4 en vez de 0.014) y el filtro viejo descartaba a casi todos los que pagan.
        if annual_div and annual_div > 0 and precio and precio > 0:
            dy_calc = annual_div / precio
            if 0 < dy_calc <= 0.5:
                result["dividend_yield_actual"] = round(dy_calc, 4)
            else:
                result["dividend_yield_actual"] = None  # valor absurdo → descartado
        else:
            result["dividend_yield_actual"] = None  # no paga dividendo

        # PEG
        result["peg_actual"] = _safe_float(info.get("pegRatio"), min_val=0, max_val=100)

        # P/FCF desde info
        fcf = _safe_float(info.get("freeCashflow"))
        mktcap = result["market_cap"]
        if fcf and fcf > 0 and mktcap and mktcap > 0:
            result["p_fcf_actual"] = round(mktcap / fcf, 2)

        # Si P/FCF no está en info, intentar calcularlo de otra forma
        if result["p_fcf_actual"] is None:
            pfcf_info = _safe_float(info.get("priceToFreeCashflows"), min_val=0, max_val=2000)
            result["p_fcf_actual"] = pfcf_info

        # P/FFO y P/AFFO para REITs (proxy via P/E)
        result["p_ffo_actual"] = result["per_actual"]
        result["p_affo_actual"] = result["per_actual"]

        # --- Histórico anual para medianas ---
        time.sleep(REQUEST_DELAY)
        _enrich_with_history(tk, result, info, modo)

        # --- v1.2.12: Stock Analysis como fuente principal (si esta activado) ---
        if modo == "principal":
            _aplicar_stockanalysis_principal(result)
        _etiquetar_fuentes(result)

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"Error fetching {ticker}: {e}")

    # Contar métricas disponibles (con valor actual Y mediana)
    metric_keys = [
        "ev_ebitda_actual", "per_actual", "p_fcf_actual", "p_b_actual",
        "dividend_yield_actual", "peg_actual", "p_ffo_actual", "p_affo_actual"
    ]
    result["metricas_disponibles"] = sum(
        1 for k in metric_keys if result[k] is not None
    )

    return result


def _equity_local(balance) -> Optional[float]:
    """Patrimonio neto del ultimo balance, en la moneda en que Yahoo lo informa (sin convertir)."""
    try:
        if balance is None or balance.empty:
            return None
        row = (
            _find_row(balance, "stockholders equity") or
            _find_row(balance, "total equity gross minority interest") or
            _find_row(balance, "common stock equity")
        )
        return _get_col_value(balance, row, balance.columns[0]) if row else None
    except Exception:
        return None


def _corregir_actuales_extranjeras(result: dict, info: dict, balance_conv, ctx: dict) -> None:
    """
    Para empresas de afuera, Yahoo mezcla monedas en algunos multiplos actuales
    (ej.: SONY EV/EBITDA = 0,12; BP = 14; SAP = 316). Se recalculan con totales en la
    moneda de cotizacion: capitalizacion (Yahoo, en dolares) contra montos convertidos.
    Solo reemplaza lo que se puede calcular; lo demas queda como estaba.
    """
    mc = result.get("market_cap")
    fxr = ctx.get("fxr") or 1.0
    if not mc or mc <= 0:
        return
    cambios = []

    fcf = _safe_float(info.get("freeCashflow"))
    if fcf and fcf > 0:
        v = mc / (fcf * fxr)
        if 0 < v < 5000:
            result["p_fcf_actual"] = round(v, 2)
            cambios.append("P/FCF")

    ebitda = _safe_float(info.get("ebitda"))
    if ebitda and ebitda > 0:
        deuda = _safe_float(info.get("totalDebt")) or 0.0
        caja = _safe_float(info.get("totalCash")) or 0.0
        ev = mc + (deuda - caja) * fxr
        if ev > 0:
            v = ev / (ebitda * fxr)
            if 0 < v < 500:
                result["ev_ebitda_actual"] = round(v, 3)
                cambios.append("EV/EBITDA")

    try:
        row = (
            _find_row(balance_conv, "stockholders equity") or
            _find_row(balance_conv, "total equity gross minority interest") or
            _find_row(balance_conv, "common stock equity")
        )
        eq = _get_col_value(balance_conv, row, balance_conv.columns[0]) if row else None
        if eq and eq > 0:
            v = mc / eq
            if 0 < v < 200:
                result["p_b_actual"] = round(v, 3)
                cambios.append("P/B")
    except Exception:
        pass

    if cambios:
        nota = result.get("moneda_nota") or ""
        result["moneda_nota"] = (nota + " Actuales recalculados: " + ", ".join(cambios) + ".").strip()


def _enrich_with_history(tk: yf.Ticker, result: dict, info: dict, modo: str = "respaldo") -> None:
    """
    Agrega medianas históricas al resultado.

    Estrategia:
    1. Intenta calcular medianas desde estados financieros históricos de yfinance.
    2. Para métricas que siguen sin mediana → intenta Stock Analysis scraping.
    3. Si tampoco hay → queda None (la métrica no aporta al score).
    """
    # Precio histórico anual (necesario para algunos cálculos de SA también)
    precio_hist = {}
    try:
        hist = tk.history(period=f"{HISTORY_YEARS}y", interval="1mo")
        if not hist.empty:
            for year in range(hist.index[-1].year - HISTORY_YEARS + 1, hist.index[-1].year + 1):
                p = _get_annual_price(hist, year)
                if p:
                    precio_hist[year] = p
    except Exception:
        hist = pd.DataFrame()

    income = balance = cashflow = None
    try:
        income = tk.financials
        balance = tk.balance_sheet
        cashflow = tk.cashflow
        shares = (
            _safe_float(info.get("sharesOutstanding")) or
            _safe_float(info.get("impliedSharesOutstanding"))
        )

        # --- v1.2.11: control de moneda / ADR (empresas de afuera) ---
        # Si los estados estan en otra moneda o el ADR representa varias acciones, se
        # llevan los montos a dolares y las acciones a "equivalentes del ADR" ANTES de
        # calcular los multiplos historicos. Si algo falla, se sigue como antes.
        try:
            ctx = moneda.decidir_contexto(
                info, result.get("precio_actual"), result.get("market_cap"), _equity_local(balance))
            result["moneda_estados"] = ctx.get("fin_cur")
            result["moneda_cotizacion"] = ctx.get("qcur")
            result["moneda_nota"] = ctx.get("nota") or None
            if ctx.get("activo"):
                income = moneda.convertir_estado(income, ctx["fx_anio"], ctx["fxr"], ctx["n_inv"])
                balance = moneda.convertir_estado(balance, ctx["fx_anio"], ctx["fxr"], ctx["n_inv"])
                cashflow = moneda.convertir_estado(cashflow, ctx["fx_anio"], ctx["fxr"], ctx["n_inv"])
                if shares:
                    shares = shares * ctx["n_inv"]
                _corregir_actuales_extranjeras(result, info, balance, ctx)
        except Exception as e:
            logger.debug(f"Control de moneda fallo para {result['ticker']}: {e}")

        # --- EV/EBITDA histórico ---
        if not (income is None or income.empty) and shares and not hist.empty:
            vals = _calc_ev_ebitda_history(income, balance, hist, shares)
            if vals:
                result["ev_ebitda_mediana"] = round(float(np.median(vals)), 2)
                result.setdefault("anios_historia", {})["ev_ebitda"] = len(vals)

        # --- PER histórico ---
        if not (income is None or income.empty) and not hist.empty:
            vals = _calc_per_history(income, balance, hist, shares, info)
            if vals:
                result["per_mediana"] = round(float(np.median(vals)), 2)
                result.setdefault("anios_historia", {})["per"] = len(vals)

        # --- P/FCF histórico ---
        if (not (cashflow is None or cashflow.empty) and
                not (balance is None or balance.empty) and not hist.empty):
            vals = _calc_pfcf_history(cashflow, balance, hist, shares, info)
            if vals:
                result["p_fcf_mediana"] = round(float(np.median(vals)), 2)
                result.setdefault("anios_historia", {})["p_fcf"] = len(vals)

        # --- P/B histórico ---
        if not (balance is None or balance.empty) and not hist.empty:
            vals = _calc_pb_history(balance, hist, shares, info)
            if vals:
                result["p_b_mediana"] = round(float(np.median(vals)), 2)
                result.setdefault("anios_historia", {})["p_b"] = len(vals)

        # --- Dividend Yield histórico ---
        if not hist.empty:
            vals = _calc_divy_history(tk, hist)
            if vals:
                result["dividend_yield_mediana"] = round(float(np.median(vals)), 4)
                result.setdefault("anios_historia", {})["dividend_yield"] = len(vals)

        # PEG: Yahoo solo da el valor actual. v1.2.12: NO se guarda el actual como "mediana"
        # (se comparaba contra si mismo y daba siempre 50 puntos); la historia real viene de
        # Stock Analysis y, si no esta, el motor usa la mediana del sector.
        result["peg_mediana"] = None
        # FFO/AFFO: aproximados con el PER mientras no haya fuente real (Stock Analysis si la tiene)
        result["p_ffo_mediana"] = result["per_mediana"]
        result["p_affo_mediana"] = result["per_mediana"]

    except Exception as e:
        logger.debug(f"Error en histórico yfinance para {result['ticker']}: {e}")

    # Guardar diagnóstico (qué devolvió yfinance exactamente)
    _log_yf_debug(result["ticker"], income, balance, cashflow, result)

    # --- Fallback 2: Stock Analysis para métricas que siguen sin mediana (modo "respaldo") ---
    if modo == "respaldo":
        antes = {m: result.get(f"{m}_mediana") for m in _METRICAS}
        _enrich_with_stockanalysis_fallback(result, precio_hist)
        completadas = [m for m in _METRICAS if antes[m] is None and result.get(f"{m}_mediana") is not None]
        if completadas:
            fuentes = dict(result.get("fuentes") or {})
            for m in completadas:
                fuentes[m] = "Yahoo + Stock Analysis (mediana)"
            result["fuentes"] = fuentes


def _aplicar_stockanalysis_principal(result: dict) -> None:
    """Modo "principal": pisa las metricas con las de Stock Analysis (actual + historia, misma fuente)."""
    try:
        from data.stockanalysis import aplicar_stockanalysis
        tomadas = aplicar_stockanalysis(result)
        if not tomadas:
            logger.info(f"{result['ticker']}: Stock Analysis no aporto metricas, se queda con Yahoo")
    except ImportError:
        logger.debug("stockanalysis.py no disponible")
    except Exception as e:
        logger.debug(f"Error en Stock Analysis (principal) para {result['ticker']}: {e}")


def _etiquetar_fuentes(result: dict) -> None:
    """Marca de donde sale cada metrica que tiene valor actual y mediana y todavia no tiene etiqueta."""
    fuentes = dict(result.get("fuentes") or {})
    for m in _METRICAS:
        if m in fuentes:
            continue
        if result.get(f"{m}_actual") is None or result.get(f"{m}_mediana") is None:
            continue
        fuentes[m] = "Yahoo (aprox. con PER)" if m in ("p_ffo", "p_affo") else "Yahoo"
    result["fuentes"] = fuentes


def _enrich_with_stockanalysis_fallback(result: dict, precio_hist: dict) -> None:
    """
    Intenta completar medianas faltantes usando Stock Analysis.
    Solo actúa si hay métricas con valor actual pero sin mediana.
    """
    # Verificar si hay algo que necesite fallback
    needs_fallback = (
        (result.get("per_mediana") is None and result.get("per_actual") is not None) or
        (result.get("p_b_mediana") is None and result.get("p_b_actual") is not None) or
        (result.get("p_fcf_mediana") is None and result.get("p_fcf_actual") is not None) or
        (result.get("dividend_yield_mediana") is None and result.get("dividend_yield_actual") is not None)
    )
    if not needs_fallback:
        return

    try:
        from data.stockanalysis import enrich_with_stockanalysis
        enrich_with_stockanalysis(result["ticker"], result, precio_hist)
    except ImportError:
        logger.debug("stockanalysis.py no disponible")
    except Exception as e:
        logger.debug(f"Error en Stock Analysis fallback para {result['ticker']}: {e}")


def _calc_ev_ebitda_history(income, balance, hist, shares: float) -> list:
    """Calcula EV/EBITDA para cada año disponible."""
    values = []
    try:
        # Buscar EBITDA directo o calcular desde EBIT + D&A
        ebitda_row = _find_row(income, "ebitda")
        ebit_row = _find_row(income, "ebit", exclude=["ebitda"])
        da_row = _find_row(income, "depreciation") or _find_row(income, "amortization")

        # Buscar deuda y caja en balance
        debt_row = (
            _find_row(balance, "total debt") or
            _find_row(balance, "long term debt") or
            _find_row(balance, "totaldebt")
        )
        cash_row = (
            _find_row(balance, "cash and cash equivalents") or
            _find_row(balance, "cash equivalents") or
            _find_row(balance, "cash", exclude=["restricted"])
        )

        for col in income.columns[:HISTORY_YEARS]:
            year = col.year if hasattr(col, 'year') else pd.Timestamp(col).year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            ebitda = _get_col_value(income, ebitda_row, col)
            if ebitda is None and ebit_row and da_row:
                ebit = _get_col_value(income, ebit_row, col)
                da = _get_col_value(income, da_row, col)
                if ebit is not None and da is not None:
                    ebitda = ebit + abs(da)

            if ebitda is None or ebitda <= 0:
                continue

            debt = _get_col_value(balance, debt_row, col) or 0
            cash = _get_col_value(balance, cash_row, col) or 0

            market_cap = price * shares
            ev = market_cap + debt - cash
            if ev <= 0:
                continue

            val = ev / ebitda
            if 0 < val < 200:
                values.append(val)

    except Exception as e:
        logger.debug(f"EV/EBITDA history error: {e}")
    return values


def _calc_per_history(income, balance, hist, shares: Optional[float], info: dict) -> list:
    """Calcula PER para cada año disponible."""
    values = []
    try:
        # Buscar EPS directo o Net Income para calcularlo
        eps_row = (
            _find_row(income, "diluted eps") or
            _find_row(income, "basic eps") or
            _find_row(income, "eps")
        )
        ni_row = (
            _find_row(income, "net income common stockholders") or
            _find_row(income, "net income") or
            _find_row(income, "netincome")
        )
        # Shares del balance (para calcular EPS desde NI)
        shares_row = (
            _find_row(balance, "diluted average shares") or
            _find_row(balance, "ordinary shares number") or
            _find_row(balance, "share issued") or
            _find_row(balance, "shares outstanding")
        )

        for col in income.columns[:HISTORY_YEARS]:
            year = col.year if hasattr(col, 'year') else pd.Timestamp(col).year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            eps = _get_col_value(income, eps_row, col)

            # Si no hay EPS directo, calcularlo desde NI / shares
            if eps is None and ni_row:
                ni = _get_col_value(income, ni_row, col)
                sh = _get_col_value(balance, shares_row, col) if shares_row else None
                if sh is None:
                    sh = shares  # usar shares actuales como proxy
                if ni is not None and sh and sh > 0:
                    eps = ni / sh

            if eps is not None and eps > 0:
                val = price / eps
                if 0 < val < 1000:
                    values.append(val)

    except Exception as e:
        logger.debug(f"PER history error: {e}")
    return values


def _calc_pfcf_history(cashflow, balance, hist, shares: Optional[float], info: dict) -> list:
    """Calcula P/FCF para cada año disponible."""
    values = []
    try:
        fcf_row = (
            _find_row(cashflow, "free cash flow") or
            _find_row(cashflow, "freecashflow")
        )
        # Alternativamente: Operating CF - CapEx
        opcf_row = (
            _find_row(cashflow, "operating cash flow") or
            _find_row(cashflow, "cash from operations") or
            _find_row(cashflow, "operating activities")
        )
        capex_row = (
            _find_row(cashflow, "capital expenditure") or
            _find_row(cashflow, "capex") or
            _find_row(cashflow, "purchase of property")
        )
        shares_row = (
            _find_row(balance, "diluted average shares") or
            _find_row(balance, "ordinary shares number") or
            _find_row(balance, "share issued")
        )

        for col in cashflow.columns[:HISTORY_YEARS]:
            if col not in (balance.columns if balance is not None else []):
                continue
            year = col.year if hasattr(col, 'year') else pd.Timestamp(col).year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            fcf = _get_col_value(cashflow, fcf_row, col)

            # Si no hay FCF directo, calcular desde OpCF - CapEx
            if fcf is None and opcf_row:
                opcf = _get_col_value(cashflow, opcf_row, col)
                capex = _get_col_value(cashflow, capex_row, col) or 0
                if opcf is not None:
                    fcf = opcf - abs(capex)  # capex suele ser negativo

            if fcf is None or fcf <= 0:
                continue

            sh = _get_col_value(balance, shares_row, col) if shares_row else None
            if sh is None:
                sh = shares
            if sh is None or sh <= 0:
                continue

            fcf_per_share = fcf / sh
            if fcf_per_share <= 0:
                continue
            val = price / fcf_per_share
            if 0 < val < 1000:
                values.append(val)

    except Exception as e:
        logger.debug(f"P/FCF history error: {e}")
    return values


def _calc_pb_history(balance, hist, shares: Optional[float], info: dict) -> list:
    """Calcula P/B para cada año disponible."""
    values = []
    try:
        equity_row = (
            _find_row(balance, "stockholders equity") or
            _find_row(balance, "total equity gross minority interest") or
            _find_row(balance, "total equity") or
            _find_row(balance, "common stock equity")
        )
        shares_row = (
            _find_row(balance, "diluted average shares") or
            _find_row(balance, "ordinary shares number") or
            _find_row(balance, "share issued") or
            _find_row(balance, "shares outstanding")
        )

        if equity_row is None:
            return values

        for col in balance.columns[:HISTORY_YEARS]:
            year = col.year if hasattr(col, 'year') else pd.Timestamp(col).year
            price = _get_annual_price(hist, year)
            if not price:
                continue

            equity = _get_col_value(balance, equity_row, col)
            sh = _get_col_value(balance, shares_row, col) if shares_row else None
            if sh is None:
                sh = shares

            if equity is None or sh is None or sh <= 0:
                continue

            bvps = equity / sh
            if bvps <= 0:
                continue

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
        if divs is None or divs.empty:
            return values

        # Normalizar timezone de dividendos
        if hasattr(divs.index, 'tz') and divs.index.tz is not None:
            divs.index = divs.index.tz_localize(None)

        min_year = hist.index[-1].year - HISTORY_YEARS + 1
        max_year = hist.index[-1].year

        for year in range(min_year, max_year + 1):
            annual_div = divs[divs.index.year == year].sum()
            price = _get_annual_price(hist, year)
            if annual_div > 0 and price and price > 0:
                val = annual_div / price
                if 0 < val < 0.5:
                    values.append(float(val))

    except Exception as e:
        logger.debug(f"DivY history error: {e}")
    return values


def calc_fair_value(result: dict, sector: str) -> dict:
    """
    Calcula el Fair Value (precio objetivo) usando múltiples métodos ponderados por sector.

    Retorna un dict con:
      - fair_value: precio objetivo ponderado en USD (o None si no hay suficientes datos)
      - fair_value_detalle: dict con precio implícito por método y su peso
      - fair_value_metodos: cantidad de métodos con precio calculado
    """
    from config.sectors import SECTOR_CONFIG, motivo_descarte, FV_RATIO_MIN, FV_RATIO_MAX, metricas_de

    fv_result = {
        "fair_value": None,
        "fair_value_detalle": {},
        "fair_value_metodos": 0,
        "fair_value_descartados": {},   # v1.2.11: {metodo: motivo} de lo que NO entra al promedio
    }

    if sector not in SECTOR_CONFIG:
        return fv_result

    config = metricas_de(result, sector)   # v1.2.44: puede traer el PEG si es creible para esta empresa
    precio_actual = result.get("precio_actual")
    shares = None  # no disponible en result; usar proxy cuando sea necesario

    precios_metodos = {}

    descartados = fv_result["fair_value_descartados"]

    for metrica, peso in config.items():
        mediana = result.get(f"{metrica}_mediana")
        actual = result.get(f"{metrica}_actual")

        if mediana is None or mediana != mediana or mediana <= 0:
            continue

        # v1.2.11: dato imposible (moneda mezclada, etc.) -> el método no se usa
        motivo = motivo_descarte(metrica, actual, mediana)
        if motivo:
            descartados[metrica] = motivo
            continue

        precio_implicito = None

        if metrica == "per":
            # PER_mediana × EPS_actual
            # EPS = precio / PER_actual (si PER_actual existe); sino intentamos reconstruir
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                eps = precio_actual / actual
                precio_implicito = mediana * eps

        elif metrica == "ev_ebitda":
            # Para EV/EBITDA no podemos reconstruir el precio limpiamente sin deuda/caja/shares
            # Usamos el ratio: precio_implicito = precio_actual * (mediana / actual)
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                precio_implicito = precio_actual * (mediana / actual)

        elif metrica == "p_fcf":
            # P/FCF_mediana × FCF_per_share
            # FCF/share = precio / P/FCF_actual
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                fcf_per_share = precio_actual / actual
                precio_implicito = mediana * fcf_per_share

        elif metrica == "p_b":
            # P/B_mediana × Book Value per share
            # BVPS = precio / P/B_actual
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                bvps = precio_actual / actual
                precio_implicito = mediana * bvps

        elif metrica == "dividend_yield":
            # precio = dividendo_anual / DY_mediana
            annual_div = result.get("annual_dividend")
            if annual_div and annual_div > 0 and mediana > 0:
                precio_implicito = annual_div / mediana
            elif actual and actual > 0 and precio_actual and precio_actual > 0:
                # Fallback: precio_actual × (actual / mediana)
                precio_implicito = precio_actual * (actual / mediana)

        elif metrica in ("peg",):
            # PEG: usamos ratio directo como EV/EBITDA
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                precio_implicito = precio_actual * (mediana / actual)

        elif metrica == "ps":
            # v1.2.43: P/S = precio / ventas por accion, asi que el precio implicito es proporcional (igual que EV/EBITDA)
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                precio_implicito = precio_actual * (mediana / actual)

        elif metrica in ("p_ffo", "p_affo"):
            # Similar a P/E para REITs
            if actual and actual > 0 and precio_actual and precio_actual > 0:
                ffo_per_share = precio_actual / actual
                precio_implicito = mediana * ffo_per_share

        # v1.2.11: si un método dice que la empresa vale más de 3 veces (o menos de 1/3) su precio,
        # no se promedia: es más probable un dato roto que una oportunidad. Se reparte su peso entre
        # los demás métodos. (El score no se toca: ahí las métricas extremas siguen contando.)
        if precio_implicito and precio_actual and precio_implicito > 0:
            ratio_check = precio_implicito / precio_actual
            if FV_RATIO_MIN <= ratio_check <= FV_RATIO_MAX:
                precios_metodos[metrica] = {
                    "precio": round(precio_implicito, 2),
                    "peso": peso,
                }
            else:
                descartados[metrica] = (
                    f"precio implícito {ratio_check:.1f}x el precio (fuera de 1/3x–3x)"
                    if ratio_check > 1 else
                    f"precio implícito {ratio_check:.2f}x el precio (fuera de 1/3x–3x)"
                )

    if not precios_metodos:
        return fv_result

    # Promedio ponderado solo con los métodos disponibles
    peso_total = sum(v["peso"] for v in precios_metodos.values())
    fv = sum(v["precio"] * v["peso"] for v in precios_metodos.values()) / peso_total

    fv_result["fair_value"] = round(fv, 2)
    fv_result["fair_value_detalle"] = precios_metodos
    fv_result["fair_value_metodos"] = len(precios_metodos)

    return fv_result


def fetch_all_tickers(tickers: list, progress_callback=None, modo_sa: Optional[str] = None) -> pd.DataFrame:
    """
    Descarga datos para una lista de tickers.
    progress_callback(i, total, ticker): función opcional para mostrar progreso.
    modo_sa: ver fetch_ticker_data.
    Retorna DataFrame con una fila por ticker.
    """
    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i, total, ticker)
        logger.info(f"Fetching {ticker} ({i+1}/{total})")
        data = fetch_ticker_data(ticker, modo_sa)
        results.append(data)
        time.sleep(REQUEST_DELAY)

    return pd.DataFrame(results)
