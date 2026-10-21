"""
Control de moneda y ADR del CEDEAR Screener (v1.2.11).

Problema que resuelve
---------------------
Muchas empresas de afuera cotizan en dolares (ADR) pero presentan sus estados
contables en otra moneda (yenes, yuanes, rupias, reales, euros...). Ademas, un ADR
puede representar varias acciones ordinarias (TSM = 5, HDB = 3, TM = 10...).
Si se mezclan precio en dolares con ganancias en yenes, o precio de ADR con cantidad
de acciones ordinarias, los multiplos historicos salen absurdos (ej.: SONY, PER 0,13).

Solucion (misma idea que el control de moneda del DCF del usuario, v2.47.2)
---------------------------------------------------------------------------
1. Todos los montos de los estados se pasan a la moneda de COTIZACION con el tipo de
   cambio de cada anio (si no se consigue, con el spot).
2. Las acciones se expresan en "acciones equivalentes al ADR": capitalizacion / precio.
   Eso resuelve el ratio de ADR y las clases multiples sin tablas manuales.
3. Yahoo a veces ROTULA mal la moneda (VALE: dice BRL pero ya esta en dolares). Por eso
   se hace una votacion: precio/ventas, precio/valor libro y precio/ganancia no dependen
   de la moneda y Yahoo los informa. Si al menos DOS votan "ya estaba en dolares" y
   NINGUNA vota "convertir", no se convierte.

Las funciones de este modulo son puras (sin red) salvo `descargar_serie_fx`, que se
puede reemplazar en las pruebas.
"""
import math
import re
import logging
from typing import Optional, Callable, Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FX_CHECK_TOL = 1.5        # tolerancia (x) al comparar nuestros multiplos con los de Yahoo
FX_CHECK_MIN_GAP = 0.20   # solo se controla si la conversion mueve los montos al menos 20 %
N_INV_MIN_GAP = 0.15      # el factor de acciones por ADR solo se aplica si se aleja de 1 en mas de 15 %
N_INV_MIN, N_INV_MAX = 0.02, 5.0   # factores fuera de este rango se consideran un dato roto

_RE_ACCIONES = re.compile(r"(shares?\b|shares number|share issued)", re.I)
_RE_EPS = re.compile(r"\beps\b", re.I)
_RE_SIN_CONVERTIR = re.compile(r"(rate|ratio|percent|%)", re.I)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


# ---------------------------------------------------------------------------
# Votacion: ¿los estados ya estan en la moneda de cotizacion aunque Yahoo diga otra?
# ---------------------------------------------------------------------------
def votacion_moneda(fin_cur: str, qcur: str, fxr: Optional[float], mc: Optional[float],
                    rev: Optional[float], equity: Optional[float], ni: Optional[float],
                    ps_y: Optional[float], pb_y: Optional[float], pe_y: Optional[float]) -> Optional[str]:
    """
    Devuelve el texto de la evidencia si los estados YA estan en la moneda de cotizacion
    (no hay que convertirlos), o None si no hay motivo para dudar de la etiqueta de Yahoo.
    Se corrige solo si al menos DOS senales votan "no convertir" y NINGUNA vota "convertir".
    """
    if fxr is None or fxr <= 0 or fin_cur == qcur or not mc or mc <= 0:
        return None
    if abs(fxr - 1.0) < FX_CHECK_MIN_GAP:
        return None
    pairs = []
    if ps_y and ps_y > 0 and rev and rev > 0:
        pairs.append(("precio/ventas", mc / (rev * fxr), ps_y))
    if pb_y and pb_y > 0 and equity and equity > 0:
        pairs.append(("precio/valor libro", mc / (equity * fxr), pb_y))
    if pe_y and pe_y > 0 and ni and ni > 0:
        pairs.append(("precio/ganancia", mc / (ni * fxr), pe_y))
    if not pairs:
        return None
    lim = math.log(FX_CHECK_TOL)
    votos_no = votos_si = 0
    for _, o, y in pairs:
        sin_conv = abs(math.log(o / y * fxr)) <= lim   # si los montos ya estaban en la moneda de cotizacion
        con_conv = abs(math.log(o / y)) <= lim         # si la conversion era correcta
        if sin_conv and not con_conv:
            votos_no += 1
        elif con_conv and not sin_conv:
            votos_si += 1
    if votos_no >= 2 and votos_si == 0:
        return "; ".join(f"{n}: con conversion {o:.1f}x, Yahoo informa {y:.1f}x, sin convertir {o * fxr:.1f}x"
                         for n, o, y in pairs)
    return None


# ---------------------------------------------------------------------------
# Tipo de cambio
# ---------------------------------------------------------------------------
def descargar_serie_fx(fin: str, quote: str, period: str = "6y") -> Optional[pd.Series]:
    """
    Serie mensual de cierres: cuantas unidades de `quote` vale 1 unidad de `fin`.
    Prueba "FINQUOTE=X" y, si no existe, la inversa. Devuelve None si no se consigue.
    """
    try:
        import yfinance as yf
    except Exception:
        return None
    for pair, inv in ((f"{fin}{quote}=X", False), (f"{quote}{fin}=X", True)):
        try:
            h = yf.Ticker(pair).history(period=period, interval="1mo")
            if h is None or h.empty or "Close" not in h.columns:
                continue
            s = h["Close"].dropna()
            s = s[s > 0]
            if len(s) < 3:
                continue
            return (1.0 / s) if inv else s
        except Exception as e:  # noqa: BLE001
            logger.debug(f"FX {pair}: {e}")
    return None


def fx_spot_y_anual(fin: str, quote: str,
                    descargar: Optional[Callable[[str, str], Optional[pd.Series]]] = None
                    ) -> Tuple[Optional[float], Dict[int, float]]:
    """(fx spot, {anio: fx promedio del anio}). (None, {}) si no hay datos."""
    if fin == quote:
        return 1.0, {}
    serie = (descargar or descargar_serie_fx)(fin, quote)
    if serie is None or len(serie) == 0:
        return None, {}
    spot = _f(serie.iloc[-1])
    anual = {}
    try:
        idx = serie.index
        for y in sorted(set(int(i.year) for i in idx)):
            vals = serie[[int(i.year) == y for i in idx]]
            m = _f(vals.mean())
            if m and m > 0:
                anual[y] = m
    except Exception:  # noqa: BLE001
        anual = {}
    return spot, anual


# ---------------------------------------------------------------------------
# Factor de acciones por ADR
# ---------------------------------------------------------------------------
def factor_acciones_adr(mc: Optional[float], precio: Optional[float],
                        acciones_ordinarias: Optional[float]) -> Optional[float]:
    """
    n_inv = (capitalizacion / precio) / acciones ordinarias = "acciones equivalentes al ADR"
    por cada accion ordinaria. Para TSM (1 ADR = 5 ordinarias) da ~0,2.
    Devuelve None si no hay datos o el valor es absurdo; 1.0 si es practicamente 1.
    """
    mc, precio, sh = _f(mc), _f(precio), _f(acciones_ordinarias)
    if not mc or not precio or not sh or mc <= 0 or precio <= 0 or sh <= 0:
        return None
    n = (mc / precio) / sh
    if not (N_INV_MIN <= n <= N_INV_MAX):
        return None
    if abs(n - 1.0) < N_INV_MIN_GAP:
        return 1.0
    return n


# ---------------------------------------------------------------------------
# Conversion de un estado contable (income / balance / cashflow)
# ---------------------------------------------------------------------------
def convertir_estado(df: Optional[pd.DataFrame], fx_anio: Dict[int, float], fx_spot: float,
                     n_inv: float = 1.0) -> Optional[pd.DataFrame]:
    """
    Devuelve una copia del estado con los montos en la moneda de cotizacion y las acciones
    expresadas en equivalentes al ADR:
      - filas de acciones (Shares, Share Issued...)  x n_inv
      - filas de EPS (por accion ordinaria)           x fx / n_inv
      - filas de tasas/ratios                         sin cambios
      - resto (montos)                                x fx del anio de la columna
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        try:
            y = int(col.year) if hasattr(col, "year") else int(pd.Timestamp(col).year)
        except Exception:  # noqa: BLE001
            y = None
        fx = fx_anio.get(y, fx_spot) if y is not None else fx_spot
        for idx in out.index:
            lbl = str(idx)
            v = out.at[idx, col]
            v = _f(v)
            if v is None:
                continue
            if _RE_EPS.search(lbl):
                out.at[idx, col] = v * fx / (n_inv or 1.0)
            elif _RE_ACCIONES.search(lbl):
                out.at[idx, col] = v * n_inv
            elif _RE_SIN_CONVERTIR.search(lbl):
                continue
            else:
                out.at[idx, col] = v * fx
    return out


# ---------------------------------------------------------------------------
# Decision completa para un ticker
# ---------------------------------------------------------------------------
def es_contexto_extranjero(pais: Optional[str], fin_cur: Optional[str], qcur: Optional[str]) -> bool:
    """True si hay que mirar moneda/ADR: reporta en otra moneda o la empresa no es de EE.UU."""
    if fin_cur and qcur and fin_cur != qcur:
        return True
    if pais and str(pais).strip() and str(pais).strip() not in ("United States", "USA", "US"):
        return True
    return False


def decidir_contexto(info: dict, precio: Optional[float], mc: Optional[float], equity_local: Optional[float],
                     descargar: Optional[Callable[[str, str], Optional[pd.Series]]] = None) -> dict:
    """
    Arma el contexto de moneda de un ticker. Claves:
      activo        bool   -> si hay que convertir/ajustar este ticker
      qcur, fin_cur str
      fxr           float  -> fx spot fin->cotizacion que se usa (1.0 si no se convierte)
      fx_anio       dict   -> fx promedio por anio
      n_inv         float  -> factor de acciones por ADR
      nota          str    -> texto para auditar
    """
    ctx = {"activo": False, "qcur": None, "fin_cur": None, "fxr": 1.0, "fx_anio": {}, "n_inv": 1.0, "nota": ""}
    qcur = str(info.get("currency") or "USD")
    fin_cur = str(info.get("financialCurrency") or qcur)
    ctx["qcur"], ctx["fin_cur"] = qcur, fin_cur
    pais = info.get("country")
    if not es_contexto_extranjero(pais, fin_cur, qcur):
        return ctx

    notas = []
    fxr, fx_anio = 1.0, {}
    if fin_cur != qcur:
        spot, anual = fx_spot_y_anual(fin_cur, qcur, descargar)
        if spot is None or spot <= 0:
            ctx["nota"] = f"No se pudo obtener el tipo de cambio {fin_cur}->{qcur}: sin ajuste (las metricas absurdas se descartan por rango)."
            return ctx
        fxr, fx_anio = spot, anual
        # Votacion: ¿Yahoo rotulo mal la moneda?
        ev = votacion_moneda(
            fin_cur, qcur, fxr, mc,
            _f(info.get("totalRevenue")), equity_local, _f(info.get("netIncomeToCommon")),
            _f(info.get("priceToSalesTrailing12Months")), _f(info.get("priceToBook")),
            _f(info.get("trailingPE")),
        )
        if ev:
            notas.append(f"Yahoo rotula los estados como {fin_cur} pero ya estan en {qcur} ({ev}): no se convierten.")
            fxr, fx_anio, fin_cur = 1.0, {}, qcur
            ctx["fin_cur"] = qcur
        else:
            notas.append(f"Estados en {fin_cur} convertidos a {qcur} (fx spot {fxr:.5f}).")

    n_inv = factor_acciones_adr(mc, precio, _f(info.get("sharesOutstanding")) or _f(info.get("impliedSharesOutstanding")))
    if n_inv is None:
        n_inv = 1.0
    elif n_inv != 1.0:
        notas.append(f"Acciones ajustadas a equivalentes del ADR (x{n_inv:.3f}, ~{1 / n_inv:.1f} ordinarias por ADR).")

    ctx.update(activo=True, fxr=fxr, fx_anio=fx_anio, n_inv=n_inv, nota=" ".join(notas))
    return ctx
