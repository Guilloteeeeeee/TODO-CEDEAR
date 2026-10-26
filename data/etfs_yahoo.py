"""Datos de Yahoo de cada ETF (v1.2.64): NAV, patrimonio (AUM), comision, dividendo, principales tenencias, sectores, noticias... Los baja
`bajar_etfs_yahoo.py` (desde la PC de Guille, donde Yahoo si responde) y quedan en data/etfs_yahoo.json:
{"fecha": "dd/mm/aaaa", "datos": {TICKER: {...}}}. La pagina del ETF pide primero a Yahoo en vivo; lo que no responde (pasa seguido desde la nube) se
completa con este archivo y avisa la fecha. Nada se inventa: lo que Yahoo no trae queda vacio y la pantalla muestra "—"."""
import datetime as _dt
import json
import os

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etfs_yahoo.json")

SECTORES_ES = {
    "technology": "Tecnología", "financial_services": "Servicios financieros", "healthcare": "Salud", "consumer_cyclical": "Consumo discrecional",
    "communication_services": "Comunicaciones", "industrials": "Industriales", "consumer_defensive": "Consumo defensivo", "energy": "Energía",
    "utilities": "Servicios públicos", "realestate": "Inmobiliario", "basic_materials": "Materiales básicos",
}
ACTIVOS_ES = {"stockPosition": "Acciones", "bondPosition": "Bonos", "cashPosition": "Efectivo", "preferredPosition": "Preferidas",
               "convertiblePosition": "Convertibles", "otherPosition": "Otros"}


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _fecha(x):
    """Fecha desde un timestamp de Yahoo (segundos) o un texto AAAA-MM-DD."""
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    v = _num(x)
    if v and v > 1e8:
        try:
            return _dt.datetime.utcfromtimestamp(v).date()
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def frecuencia(cantidad_12m):
    """Cuantos pagos hubo en los ultimos 12 meses -> 'Mensual', 'Trimestral'... (None si no hay pagos)."""
    n = int(cantidad_12m or 0)
    if n <= 0:
        return None
    if n >= 10:
        return "Mensual"
    if n >= 3:
        return "Trimestral"
    if n == 2:
        return "Semestral"
    return "Anual"


def analizar_dividendos(serie, hoy=None):
    """serie: [(fecha, monto)] -> {'pagos_12m', 'frecuencia', 'ultimo': {'fecha','monto'}, 'total_12m'} ({} si no hay pagos en el ultimo anio)."""
    hoy = hoy or _dt.date.today()
    pagos = sorted(((_fecha(f), _num(m)) for f, m in (serie or [])), key=lambda x: (x[0] is None, x[0]))
    pagos = [(f, m) for f, m in pagos if f and m and m > 0]
    if not pagos:
        return {}
    ult = pagos[-1]
    desde = hoy - _dt.timedelta(days=365)
    ult12 = [(f, m) for f, m in pagos if f > desde]
    if not ult12:
        return {"pagos_12m": 0, "frecuencia": None, "ultimo": {"fecha": ult[0], "monto": ult[1]}, "total_12m": 0.0}
    return {"pagos_12m": len(ult12), "frecuencia": frecuencia(len(ult12)), "ultimo": {"fecha": ult[0], "monto": ult[1]}, "total_12m": sum(m for _, m in ult12)}


def analizar(info, dividendos=None, fondo=None, hoy=None):
    """Arma el diccionario del ETF con lo que trae Yahoo (`info`), la serie de dividendos [(fecha, monto)] y `fondo` ({'holdings': [(simbolo, nombre, porcentaje)],
    'sectores': {clave: fraccion}, 'activos': {clave: fraccion}}). Los porcentajes se guardan en % (0.0945 = 0,0945 %). Lo que falta, no se incluye."""
    info = info or {}
    fondo = fondo or {}
    out = {}

    def poner(k, v):
        if v not in (None, "", [], {}):
            out[k] = v
    poner("nombre", str(info.get("longName") or info.get("shortName") or "").strip())
    poner("gestor", str(info.get("fundFamily") or "").strip())
    poner("mercado", str(info.get("fullExchangeName") or info.get("exchange") or "").strip())
    poner("moneda", str(info.get("currency") or "").strip())
    poner("categoria_yahoo", str(info.get("category") or "").strip())
    poner("tipo_legal", str(info.get("legalType") or "").strip())
    poner("precio", _num(info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")))
    poner("nav", _num(info.get("navPrice")))
    poner("aum", _num(info.get("totalAssets")))
    com = _num(info.get("netExpenseRatio"))                    # Yahoo lo da en % (0.0945 = 0,0945 %)
    if com is None:
        c2 = _num(info.get("annualReportExpenseRatio"))        # este viene como fraccion (0.000945)
        com = c2 * 100 if c2 is not None else None
    poner("comision", com)
    rend = _num(info.get("yield"))
    if rend is None:
        rend = _num(info.get("trailingAnnualDividendYield"))
    poner("rendimiento", rend * 100 if rend is not None else None)       # en %
    poner("dividendo_anual", _num(info.get("trailingAnnualDividendRate")))
    ini = _fecha(info.get("fundInceptionDate"))
    poner("inicio", ini)
    poner("max_52s", _num(info.get("fiftyTwoWeekHigh")))
    poner("min_52s", _num(info.get("fiftyTwoWeekLow")))
    poner("beta", _num(info.get("beta3Year") or info.get("beta")))
    poner("volumen_prom", _num(info.get("averageVolume") or info.get("averageDailyVolume3Month")))
    poner("resumen_en", str(info.get("longBusinessSummary") or "").strip())
    div = analizar_dividendos(dividendos, hoy)
    poner("dividendos", div)
    hold = []
    for h in fondo.get("holdings") or []:
        try:
            simbolo, nombre, pct = h
        except (TypeError, ValueError):
            continue
        p = _num(pct)
        if p is not None and (simbolo or nombre):
            hold.append({"simbolo": str(simbolo or ""), "nombre": str(nombre or ""), "pct": p * 100})
    poner("holdings", hold[:10])
    sec = [{"nombre": SECTORES_ES.get(k, str(k).replace("_", " ").title()), "pct": _num(v) * 100} for k, v in (fondo.get("sectores") or {}).items() if _num(v)]
    poner("sectores", sorted(sec, key=lambda x: -x["pct"]))
    act = [{"nombre": ACTIVOS_ES.get(k, str(k)), "pct": _num(v) * 100} for k, v in (fondo.get("activos") or {}).items() if _num(v)]
    poner("activos", sorted(act, key=lambda x: -x["pct"]))
    return out


def bajar(simbolo, timeout=20.0, ticker_obj=None):
    """Datos del ETF pedidos a Yahoo en este momento ({} si no responde). Un solo objeto Ticker; cada dato con su propio tope de tiempo."""
    from data import yahoo_extra as yx
    try:
        if ticker_obj is None:
            import yfinance as yf
            ticker_obj = yf.Ticker(str(simbolo))
    except Exception:  # noqa: BLE001
        return {}
    tk = ticker_obj
    info = yx._con_tope(lambda: tk.info or {}, timeout) or yx._con_tope(lambda: tk.info or {}, timeout) or {}

    def _fondo():
        fd = tk.funds_data
        hold = []
        try:
            for sym, r in fd.top_holdings.iterrows():
                hold.append((sym, r.get("Name"), r.get("Holding Percent")))
        except Exception:  # noqa: BLE001
            pass
        try:
            sec = dict(fd.sector_weightings or {})
        except Exception:  # noqa: BLE001
            sec = {}
        try:
            act = dict(fd.asset_classes or {})
        except Exception:  # noqa: BLE001
            act = {}
        return {"holdings": hold, "sectores": sec, "activos": act}
    fondo = yx._con_tope(_fondo, timeout) or {}
    serie = yx._con_tope(lambda: [(i.date(), v) for i, v in tk.dividends.items()], timeout) or []
    out = analizar(info, serie, fondo)
    noticias = yx._con_tope(lambda: tk.news, timeout)
    if noticias:
        try:
            out["noticias"] = yx.analizar_noticias(noticias)
        except Exception:  # noqa: BLE001
            pass
    return out


# --- archivo ------------------------------------------------------------------------------------------------------------

def a_json(o):
    if isinstance(o, dict):
        return {str(k): a_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [a_json(v) for v in o]
    if isinstance(o, _dt.datetime):
        return "d:" + o.date().isoformat()
    if isinstance(o, _dt.date):
        return "d:" + o.isoformat()
    return o


def de_json(o):
    if isinstance(o, dict):
        return {k: de_json(v) for k, v in o.items()}
    if isinstance(o, list):
        return [de_json(v) for v in o]
    if isinstance(o, str) and o.startswith("d:"):
        try:
            return _dt.date.fromisoformat(o[2:])
        except ValueError:
            return o
    return o


def cargar(ruta=None):
    """({TICKER: {...}}, fecha|None). ({}, None) si el archivo no esta o no se puede leer."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        return {str(t).upper(): de_json(v) for t, v in (d.get("datos") or {}).items() if isinstance(v, dict)}, d.get("fecha")
    except Exception:  # noqa: BLE001
        return {}, None


def _vacio(v):
    return v is None or (isinstance(v, (str, list, tuple, dict, set)) and len(v) == 0)


def completar(vivo, guardado):
    """(datos, claves_del_archivo): lo que Yahoo contesto en vivo manda; lo que falta se toma del archivo guardado."""
    out = dict(vivo or {})
    usadas = []
    for k, v in (guardado or {}).items():
        if _vacio(out.get(k)) and not _vacio(v):
            out[k] = v
            usadas.append(k)
    return out, usadas
