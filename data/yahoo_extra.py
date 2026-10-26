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
    d = {"primer_anio": primero, "anios_pagando": seguidos if ultimo >= hoy.year - 1 else 0, "anios_crece": 0, "cagr": {},
         "anuales": [(y, round(tot[y], 4)) for y in sorted(tot) if y < hoy.year][-20:]}
    ref = max((y for y in tot if y < hoy.year), default=None)          # ultimo anio completo: de ahi salen la frecuencia y los meses de pago
    if ref is not None:
        meses = sorted({_fecha(f).month for f, m in (serie or []) if _fecha(f) and _fecha(f).year == ref and _num(m) and _num(m) > 0})
        npag = sum(1 for f, m in (serie or []) if _fecha(f) and _fecha(f).year == ref and _num(m) and _num(m) > 0)
        d["pagos_anio"] = npag
        d["meses_pago"] = meses
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


def metricas_dividendo(info):
    """Del `info` de Yahoo: payout de ganancias (dividendos / ganancias), payout de flujo de caja libre (dividendos / FCF) y deuda neta / EBITDA.
    Cada una es None si Yahoo no trae lo necesario. Los payout son fracciones (0.47 = 47 %)."""
    info = info or {}
    tasa, acc = _num(info.get("dividendRate")), _num(info.get("sharesOutstanding"))
    eps = _num(info.get("trailingEps"))
    payout = _num(info.get("payoutRatio"))
    if payout is None and tasa and eps and eps > 0:
        payout = tasa / eps
    fcf = _num(info.get("freeCashflow"))
    payout_fcf = (tasa * acc) / fcf if (tasa and acc and fcf and fcf > 0) else None
    deuda, caja, ebitda = _num(info.get("totalDebt")), _num(info.get("totalCash")), _num(info.get("ebitda"))
    dn_ebitda = (deuda - (caja or 0.0)) / ebitda if (deuda is not None and ebitda and ebitda > 0) else None
    if payout is not None and payout < 0:
        payout = None
    return {"payout_eps": payout, "payout_fcf": payout_fcf, "deuda_neta_ebitda": dn_ebitda}


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
         "tasa_anual": _num(info.get("dividendRate")), "ultimos": ultimos, "trayectoria": tray, "metricas": metricas_dividendo(info)}
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


# --- beta y fecha de resultados ---------------------------------------------------------------------------------------
def analizar_agenda(info, calendario=None):
    """{'beta': float, 'resultados': (fecha, fecha_hasta o None)} con lo que Yahoo informe (info['beta'], calendario['Earnings Date'] o info['earningsTimestamp...']).
    Si Yahoo da un rango de fechas (aun no confirmada) se devuelven las dos. {} si no hay nada."""
    info = info or {}
    fechas = []
    cal = calendario if isinstance(calendario, dict) else {}
    ed = cal.get("Earnings Date")
    for f in (ed if isinstance(ed, (list, tuple)) else [ed]):
        f = _fecha(f)
        if f:
            fechas.append(f)
    if not fechas:
        for k in ("earningsTimestampStart", "earningsTimestamp", "earningsTimestampEnd"):
            f = _fecha(info.get(k))
            if f and f not in fechas:
                fechas.append(f)
    fechas = sorted(set(fechas))
    d = {}
    beta = _num(info.get("beta"))
    if beta is not None:
        d["beta"] = beta
    if fechas:
        d["resultados"] = (fechas[0], fechas[-1] if fechas[-1] != fechas[0] else None)
    return d


def bajar_agenda(ticker, timeout=12.0, obtener=None):
    def _pedir():
        if obtener is not None:
            return obtener(ticker)
        import yfinance as yf
        tk = yf.Ticker(str(ticker))
        info = tk.info or {}
        try:
            cal = tk.calendar
        except Exception:  # noqa: BLE001
            cal = None
        return info, cal

    v = _con_tope(_pedir, timeout)
    return analizar_agenda(*v) if v else {}


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


# --- estados financieros ----------------------------------------------------------------------------------------------
# (rotulo en castellano, [claves de Yahoo en orden de preferencia], tipo) ; tipo: "m" = monto en moneda, "eps" = por accion, "n" = cantidad, "t" = total (negrita)
ESTADOS = {
    "resultados": ("income_stmt", [
        ("Ingresos", ["Total Revenue", "Operating Revenue"], "t"),
        ("Costo de ventas", ["Cost Of Revenue"], "m"),
        ("Utilidad bruta", ["Gross Profit"], "t"),
        ("Gastos operativos", ["Operating Expense", "Total Expenses"], "m"),
        ("Resultado operativo", ["Operating Income", "Total Operating Income As Reported"], "t"),
        ("EBITDA", ["EBITDA", "Normalized EBITDA"], "m"),
        ("Resultado antes de impuestos", ["Pretax Income"], "m"),
        ("Impuesto a las ganancias", ["Tax Provision"], "m"),
        ("Tasa de impuesto", ["Tax Rate For Calcs"], "pct"),
        ("Resultado neto", ["Net Income", "Net Income Common Stockholders"], "t"),
        ("Ganancia por acción (diluida)", ["Diluted EPS"], "eps"),
        ("Acciones promedio (diluidas)", ["Diluted Average Shares"], "n")]),
    "balance": ("balance_sheet", [
        ("Caja e inversiones de corto plazo", ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"], "m"),
        ("Cuentas por cobrar", ["Accounts Receivable", "Receivables"], "m"),
        ("Inventarios", ["Inventory"], "m"),
        ("Activo corriente", ["Current Assets"], "t"),
        ("Propiedad, planta y equipo (neto)", ["Net PPE"], "m"),
        ("Plusvalía (goodwill)", ["Goodwill"], "m"),
        ("Activo total", ["Total Assets"], "t"),
        ("Pasivo corriente", ["Current Liabilities"], "t"),
        ("Deuda total", ["Total Debt"], "m"),
        ("Pasivo total", ["Total Liabilities Net Minority Interest"], "t"),
        ("Patrimonio neto", ["Stockholders Equity", "Common Stock Equity"], "t"),
        ("Capital invertido (según Yahoo)", ["Invested Capital"], "m")]),
    "flujo": ("cashflow", [
        ("Flujo de efectivo operativo", ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"], "t"),
        ("Inversión en activos fijos (CAPEX)", ["Capital Expenditure"], "m"),
        ("Flujo de efectivo libre", ["Free Cash Flow"], "t"),
        ("Flujo de efectivo de inversión", ["Investing Cash Flow"], "m"),
        ("Flujo de efectivo de financiamiento", ["Financing Cash Flow"], "m"),
        ("Recompra de acciones", ["Repurchase Of Capital Stock"], "m"),
        ("Dividendos pagados", ["Cash Dividends Paid", "Common Stock Dividend Paid"], "m")]),
}


_MARCA_TTM = "TTM|"


def _col_ttm(q, flujo):
    """Serie con la columna "ultimos 12 meses" armada con los trimestres de Yahoo (df `q`, columnas = fechas, la mas nueva primero).
    flujo=True (resultados y flujo de efectivo): suma de los 4 ultimos trimestres (promedio para acciones y tasas); flujo=False (balance): el ultimo trimestre.
    Devuelve (serie, fecha) o (None, None) si no hay trimestres suficientes (4 seguidos: entre 240 y 300 dias de punta a punta)."""
    try:
        cols = list(q.columns)
        if not cols or not hasattr(cols[0], "year"):
            return None, None
        if not flujo:
            return q.iloc[:, 0], cols[0]
        if len(cols) < 4 or not (240 <= (cols[0] - cols[3]).days <= 300):
            return None, None
        c4 = q.iloc[:, :4]
        res = c4.sum(axis=1, min_count=4)
        prom = [r for r in c4.index if str(r) in ("Diluted Average Shares", "Basic Average Shares", "Tax Rate For Calcs")]
        for r in prom:
            res[r] = c4.loc[r].astype(float).mean(skipna=False)
        return res, cols[0]
    except Exception:  # noqa: BLE001
        return None, None


def _con_ttm(anual, trimestral, flujo):
    """Copia del df anual con una columna "TTM|<fecha del ultimo trimestre>" al comienzo (si hay trimestres y son mas nuevos que el ultimo anio fiscal)."""
    try:
        if anual is None or trimestral is None:
            return anual
        serie, fecha = _col_ttm(trimestral, flujo)
        if serie is None or (fecha - list(anual.columns)[0]).days < 30:
            return anual
        df = anual.copy()
        df.insert(0, _MARCA_TTM + fecha.strftime("%Y-%m-%d"), serie.reindex(df.index))
        return df
    except Exception:  # noqa: BLE001
        return anual


def _tabla_estado(df, filas, max_anios=4):
    """df de yfinance (filas = conceptos, columnas = fechas) -> {'anios': ['2026 (TTM)', 2025, 2024, ...], 'filas': [(rotulo, [valores], tipo)]}.
    Desde la v1.2.58 el mas nuevo va primero (a la izquierda); la columna TTM (ultimos 12 meses), si existe, va al comienzo."""
    try:
        todas = list(df.columns)
        ttm = [c for c in todas if isinstance(c, str) and c.startswith(_MARCA_TTM)]
        anuales = [c for c in todas if not (isinstance(c, str) and c.startswith(_MARCA_TTM))]
        anuales = sorted(anuales, key=lambda c: c, reverse=True)[:max_anios]
        cols = ttm[:1] + anuales
        etiquetas = [(f"{c[len(_MARCA_TTM):len(_MARCA_TTM) + 4]} (TTM)" if c in ttm else (c.year if hasattr(c, "year") else int(str(c)[:4]))) for c in cols]
    except Exception:  # noqa: BLE001
        return {}
    out = []
    for rot, claves, tipo in filas:
        for k in claves:
            if k in df.index:
                vals = [_num(df.loc[k][c]) for c in cols]
                if any(v is not None for v in vals):
                    out.append((rot, vals, tipo))
                    break
    return {"anios": etiquetas, "filas": out} if out else {}


def _ratio(a, b):
    return (a / b) if (a is not None and b not in (None, 0)) else None


def analizar_estados(dfs, moneda=None):
    """dfs: {'income_stmt', 'balance_sheet', 'cashflow'} anuales y, si hay, 'q_income_stmt', 'q_balance_sheet', 'q_cashflow' (trimestrales, para la columna TTM).
    Devuelve {'moneda', 'resultados', 'balance', 'flujo', 'ratios'}: la columna TTM y los ultimos 4 anios fiscales (el mas nuevo primero); los ratios se
    calculan con esas cifras. {} si no hay nada."""
    d = {"moneda": moneda}
    dfs = dfs or {}
    for clave, (fuente, filas) in ESTADOS.items():
        df = dfs.get(fuente)
        if df is not None:
            df = _con_ttm(df, dfs.get("q_" + fuente), flujo=(fuente != "balance_sheet"))
        t = _tabla_estado(df, filas) if df is not None else {}
        if t:
            d[clave] = t

    def serie(clave, rot):
        t = d.get(clave) or {}
        for r, vals, _ in t.get("filas", []):
            if r == rot:
                return dict(zip(t["anios"], vals))
        return {}
    ing, bru, ope, net = (serie("resultados", x) for x in ("Ingresos", "Utilidad bruta", "Resultado operativo", "Resultado neto"))
    imp, ebt, tasa = serie("resultados", "Impuesto a las ganancias"), serie("resultados", "Resultado antes de impuestos"), serie("resultados", "Tasa de impuesto")
    fcf, pat, deu, ac, pc, cap = (serie("flujo", "Flujo de efectivo libre"), serie("balance", "Patrimonio neto"), serie("balance", "Deuda total"),
                                  serie("balance", "Activo corriente"), serie("balance", "Pasivo corriente"), serie("balance", "Capital invertido (según Yahoo)"))
    etiquetas = []
    for t in (d.get("resultados"), d.get("balance"), d.get("flujo")):
        for a in (t or {}).get("anios", []):
            if a not in etiquetas:
                etiquetas.append(a)
    # mas nuevo primero: la columna TTM (texto) adelante y despues los anios de mayor a menor
    anios = sorted([a for a in etiquetas if isinstance(a, str)]) + sorted([a for a in etiquetas if not isinstance(a, str)], reverse=True)

    def roic(a):
        o, c = ope.get(a), cap.get(a)
        t = tasa.get(a)
        if t is None:
            t = _ratio(imp.get(a), ebt.get(a))
        if o is None or c in (None, 0) or t is None or not (0 <= t <= 0.6):
            return None
        return o * (1 - t) / c
    rat = []
    for rot, num, den in (("Margen bruto", bru, ing), ("Margen operativo", ope, ing), ("Margen neto", net, ing), ("Margen de flujo de efectivo libre", fcf, ing),
                          ("Retorno sobre el patrimonio (ROE)", net, pat)):
        vals = [_ratio(num.get(a), den.get(a)) for a in anios]
        if any(v is not None for v in vals):
            rat.append((rot, vals, "pct"))
    vals = [roic(a) for a in anios]
    if any(v is not None for v in vals):
        rat.append(("Retorno sobre el capital invertido (ROIC)", vals, "pct"))
    for rot, num, den in (("Deuda total / Patrimonio", deu, pat), ("Liquidez corriente (activo / pasivo corriente)", ac, pc)):
        vals = [_ratio(num.get(a), den.get(a)) for a in anios]
        if any(v is not None for v in vals):
            rat.append((rot, vals, "x"))
    if rat:
        d["ratios"] = {"anios": anios, "filas": rat}
    return d if len(d) > 1 else {}


# --- un solo pedido a Yahoo por empresa ---------------------------------------------------------------------------------
def bajar_paquete(ticker, timeout=25.0, ticker_obj=None):
    """Todo lo de Yahoo que usan las solapas, con UN solo objeto Ticker y UN solo pedido de `info` (antes cada solapa pedia el suyo en paralelo y Yahoo
    cortaba algunos con 'demasiados pedidos'). Devuelve {'info_ok', 'dividendos', 'gobierno', 'agenda', 'noticias', 'estados'}; lo que no responde queda vacio."""
    vacio = {"info_ok": False, "dividendos": {}, "gobierno": {}, "agenda": {}, "noticias": [], "estados": {}}
    try:
        if ticker_obj is None:
            import yfinance as yf
            ticker_obj = yf.Ticker(str(ticker))
    except Exception:  # noqa: BLE001
        return vacio
    tk = ticker_obj
    info = _con_tope(lambda: tk.info or {}, timeout)
    if not info:
        info = _con_tope(lambda: tk.info or {}, timeout)       # un reintento
    info = info or {}
    out = dict(vacio)
    out["info_ok"] = bool(info)
    res = {}

    def tarea(nombre, fn):
        def _r():
            res[nombre] = _con_tope(fn, timeout)
        h = threading.Thread(target=_r, daemon=True)
        h.start()
        return h
    hilos = [
        tarea("serie", lambda: [(i.date(), v) for i, v in tk.dividends.items()]),
        tarea("tenedores", lambda: [{"nombre": r.get("Holder"), "pct": r.get("pctHeld", r.get("% Out"))} for _, r in tk.institutional_holders.iterrows()]),
        tarea("calendario", lambda: tk.calendar),
        tarea("noticias", lambda: tk.news),
        tarea("inc", lambda: tk.income_stmt),
        tarea("bal", lambda: tk.balance_sheet),
        tarea("cf", lambda: tk.cashflow),
        tarea("qinc", lambda: tk.quarterly_income_stmt),
        tarea("qbal", lambda: tk.quarterly_balance_sheet),
        tarea("qcf", lambda: tk.quarterly_cashflow),
    ]
    for h in hilos:
        h.join(timeout)
    try:
        out["dividendos"] = analizar_dividendos(info, res.get("serie") or [])
    except Exception:  # noqa: BLE001
        pass
    try:
        out["gobierno"] = analizar_gobierno(info, res.get("tenedores") or [])
    except Exception:  # noqa: BLE001
        pass
    try:
        out["agenda"] = analizar_agenda(info, res.get("calendario"))
    except Exception:  # noqa: BLE001
        pass
    try:
        out["noticias"] = analizar_noticias(res.get("noticias") or [])
    except Exception:  # noqa: BLE001
        pass
    try:
        out["estados"] = analizar_estados({"income_stmt": res.get("inc"), "balance_sheet": res.get("bal"), "cashflow": res.get("cf"),
                                          "q_income_stmt": res.get("qinc"), "q_balance_sheet": res.get("qbal"), "q_cashflow": res.get("qcf")}, info.get("financialCurrency"))
    except Exception:  # noqa: BLE001
        pass
    return out
