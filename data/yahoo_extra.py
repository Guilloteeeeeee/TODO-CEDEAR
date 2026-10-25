"""
Datos extra de Yahoo Finance para las solapas de la pagina de una empresa (v1.2.52): grafico intradia (1D y 5D), dividendos, directivos, accionistas y
noticias. Todo se pide en el momento (la app lo guarda en memoria un rato), con tope de tiempo, y si Yahoo no responde devuelve None / {} / []: la pagina
dice "no disponible" y nunca se inventa un dato. Los analizadores (`analizar_*`) no tocan la red y se prueban con datos simulados.
"""
import datetime as _dt
import threading


def _con_tope(fn, timeout):
    res = {}

    def _run():
        try:
            res["v"] = fn()
        except Exception:  # noqa: BLE001
            res["v"] = None

    h = threading.Thread(target=_run, daemon=True)
    h.start()
    h.join(timeout)
    return res.get("v")


def _num(x):
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _fecha(x):
    """Fecha desde un numero de Unix (segundos), un datetime o una fecha; None si no se puede."""
    try:
        if x is None:
            return None
        if isinstance(x, _dt.datetime):
            return x.date()
        if isinstance(x, _dt.date):
            return x
        v = float(x)
        return _dt.datetime.fromtimestamp(v, _dt.timezone.utc).date() if v > 0 else None
    except (TypeError, ValueError, OSError, OverflowError):
        return None


# --- grafico intradia -------------------------------------------------------------------------------------------------
def bajar_intradia(ticker, marco, timeout=12.0, obtener=None):
    """[(datetime, cierre)] del ultimo dia (1D, cada 5 minutos) o de los ultimos 5 dias (5D, cada 30 minutos); None si Yahoo no responde."""
    per, inter = ("1d", "5m") if marco == "1D" else ("5d", "30m")

    def _pedir():
        if obtener is not None:
            return obtener(ticker, per, inter)
        import yfinance as yf
        h = yf.Ticker(str(ticker)).history(period=per, interval=inter, auto_adjust=False)
        if h is None or h.empty or "Close" not in h:
            return None
        return [(i.to_pydatetime() if hasattr(i, "to_pydatetime") else i, c) for i, c in zip(h.index, h["Close"])]

    v = _con_tope(_pedir, timeout)
    if not v:
        return None
    pts = [(f, _num(c)) for f, c in v]
    pts = [(f, c) for f, c in pts if c and c > 0]
    return pts if len(pts) >= 2 else None


# --- dividendos -------------------------------------------------------------------------------------------------------
def trayectoria_dividendos(serie, hoy=None):
    """De los pagos historicos [(fecha, monto)] saca, por anio calendario: cuantos anios hace que paga, cuantos anios seguidos viene aumentando el total anual
    y el crecimiento anual compuesto (CAGR) a 1, 3, 5 y 10 anios, segun la historia que haya. El anio en curso y el primero (suelen estar incompletos) no entran
    en las cuentas de crecimiento. Devuelve {} si no hay datos."""
    from datetime import date
    hoy = hoy or date.today()
    tot = {}
    for f, m in (serie or []):
        f, m = _fecha(f), _num(m)
        if f and m and m > 0:
            tot[f.year] = tot.get(f.year, 0.0) + m
    if not tot:
        return {}
    primero = min(tot)
    completos = sorted(y for y in tot if primero < y < hoy.year)       # anios enteros (sin el primero ni el actual)
    # anios seguidos pagando, contando para atras desde el ultimo anio con pagos
    ultimo = max(tot)
    seguidos = 0
    y = ultimo
    while y in tot:
        seguidos += 1
        y -= 1
    d = {"primer_anio": primero, "anios_pagando": seguidos if ultimo >= hoy.year - 1 else 0, "anios_crece": 0, "cagr": {}}
    if not completos:
        return d
    fin = completos[-1]
    racha, y = 0, fin
    while y in tot and (y - 1) in tot and (y - 1) > primero and tot[y] > tot[y - 1] * 1.0005:
        racha += 1
        y -= 1
    # el primer anio con pagos no se compara (puede estar incompleto), asi que la racha cuenta aumentos entre anios completos
    d["anios_crece"] = racha
    for n in (1, 3, 5, 10):
        ini = fin - n
        if ini in tot and ini > primero and tot[ini] > 0 and tot[fin] > 0:
            d["cagr"][n] = (tot[fin] / tot[ini]) ** (1.0 / n) - 1
    d["anio_base"] = fin
    return d


def analizar_dividendos(info, serie):
    """info: dict `info` de Yahoo; serie: [(fecha, monto)] de pagos pasados. Devuelve {'ex_fecha', 'pago_fecha', 'monto', 'tasa_anual', 'ultimos',
    'trayectoria'}. La fecha de pago y la ex-fecha son las ultimas que informa Yahoo: puede ser ya pasada si la empresa todavia no anuncio la siguiente."""
    info = info or {}
    ultimos = sorted(((_fecha(f), _num(m)) for f, m in (serie or [])), key=lambda x: (x[0] is None, x[0]), reverse=True)
    ultimos = [(f, m) for f, m in ultimos if f and m and m > 0]
    tray = trayectoria_dividendos(serie)
    ultimos = ultimos[:8]
    monto = _num(info.get("lastDividendValue")) or (ultimos[0][1] if ultimos else None)
    d = {"ex_fecha": _fecha(info.get("exDividendDate")), "pago_fecha": _fecha(info.get("dividendDate")), "monto": monto,
         "tasa_anual": _num(info.get("dividendRate")), "ultimos": ultimos, "trayectoria": tray}
    return d if (d["monto"] or d["ex_fecha"] or d["tasa_anual"] or ultimos) else {}


def bajar_dividendos(ticker, timeout=12.0, obtener=None):
    def _pedir():
        if obtener is not None:
            return obtener(ticker)
        import yfinance as yf
        tk = yf.Ticker(str(ticker))
        info = tk.info or {}
        try:
            serie = [(i.date(), v) for i, v in tk.dividends.items()]
        except Exception:  # noqa: BLE001
            serie = []
        return info, serie

    v = _con_tope(_pedir, timeout)
    return analizar_dividendos(*v) if v else {}


# --- directivos y accionistas -----------------------------------------------------------------------------------------
def analizar_gobierno(info, tenedores=None, mayores=None):
    """{'directivos': [{nombre, cargo, edad, pago}], 'insiders': %, 'instituciones': %, 'principales': [{nombre, pct}]} (los que Yahoo informe)."""
    info = info or {}
    dirs = []
    for o in (info.get("companyOfficers") or [])[:10]:
        nom = str(o.get("name") or "").strip()
        if nom:
            dirs.append({"nombre": nom, "cargo": str(o.get("title") or "").strip(), "edad": _num(o.get("age")), "pago": _num(o.get("totalPay"))})
    ins, inst = _num(info.get("heldPercentInsiders")), _num(info.get("heldPercentInstitutions"))
    princ = []
    for t in (tenedores or [])[:10]:
        nom = str(t.get("nombre") or "").strip()
        if nom:
            princ.append({"nombre": nom, "pct": _num(t.get("pct"))})
    d = {"directivos": dirs, "insiders": ins, "instituciones": inst, "principales": princ}
    return d if (dirs or ins is not None or inst is not None or princ) else {}


def bajar_gobierno(ticker, timeout=15.0, obtener=None):
    def _pedir():
        if obtener is not None:
            return obtener(ticker)
        import yfinance as yf
        tk = yf.Ticker(str(ticker))
        info = tk.info or {}
        ten = []
        try:
            h = tk.institutional_holders
            for _, r in h.iterrows():
                p = r.get("pctHeld", r.get("% Out"))
                ten.append({"nombre": r.get("Holder"), "pct": p})
        except Exception:  # noqa: BLE001
            pass
        return info, ten

    v = _con_tope(_pedir, timeout)
    return analizar_gobierno(*v) if v else {}


# --- noticias ---------------------------------------------------------------------------------------------------------
def analizar_noticias(crudo, maximo=8):
    """[{titulo, fuente, link, fecha}] desde lo que devuelve yfinance (formato viejo o nuevo); solo links http(s)."""
    out = []
    for n in crudo or []:
        c = n.get("content") if isinstance(n.get("content"), dict) else n
        tit = str(c.get("title") or "").strip()
        url = ""
        for k in ("canonicalUrl", "clickThroughUrl"):
            u = c.get(k)
            if isinstance(u, dict) and u.get("url"):
                url = str(u["url"])
                break
        url = url or str(c.get("link") or c.get("url") or "")
        if not tit or not url.startswith(("http://", "https://")):
            continue
        prov = c.get("provider")
        fuente = str(prov.get("displayName") if isinstance(prov, dict) else (c.get("publisher") or "")).strip()
        f = _fecha(c.get("providerPublishTime"))
        if f is None and c.get("pubDate"):
            try:
                f = _dt.date.fromisoformat(str(c["pubDate"])[:10])
            except ValueError:
                f = None
        out.append({"titulo": tit, "fuente": fuente, "link": url, "fecha": f})
    return out[:maximo]


def bajar_noticias(ticker, timeout=10.0, obtener=None):
    def _pedir():
        if obtener is not None:
            return obtener(ticker)
        import yfinance as yf
        return yf.Ticker(str(ticker)).news

    v = _con_tope(_pedir, timeout)
    return analizar_noticias(v) if v else []
