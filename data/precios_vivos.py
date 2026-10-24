"""
Precios en vivo (v1.2.46).

Hasta la v1.2.45 la tabla mostraba el precio del cache (se baja una vez por mes o trimestre desde la PC), por eso no se movia. Ahora, al abrir
la app, se baja de Yahoo Finance el ultimo precio de cada empresa (un solo pedido para todas) y se guarda unos minutos en memoria
(PRECIOS_MINUTOS_CACHE en config/ajustes.py). Esos precios reemplazan al del cache en la tabla y en la pagina de la empresa; el Fair Value
(en dolares) no cambia, asi que lo que se mueve es el porcentaje contra el precio de hoy, la capitalizacion, el Dividend Yield actual y la
posicion en el rango de 52 semanas. El PUNTAJE y la CATEGORIA no se recalculan: salen de los multiplos del ultimo cache (cambiarlo seria
un cambio de metodo, y lo decide Guille).

Tambien baja el precio en pesos de cada CEDEAR (simbolo de BYMA + ".BA" en Yahoo). Antes de mostrarlo se controla que tenga sentido: del
precio en pesos, el ratio y el precio en dolares sale el dolar que implica cada CEDEAR (dolar CCL implicito); si el de uno se aleja mucho de
la mediana de todos, se descarta (puede ser un ratio desactualizado o un simbolo que no es el CEDEAR). Si Yahoo no responde, nada se rompe:
la tabla sigue con el precio del cache y la pagina muestra "—" en pesos.

No se pudo probar contra Yahoo desde el entorno de desarrollo (esta bloqueado): las pruebas usan un descargador falso.
"""
from datetime import datetime
from statistics import median

try:
    from zoneinfo import ZoneInfo
    _ZONA = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:  # noqa: BLE001
    _ZONA = None

RATIO_MIN, RATIO_MAX = 0.4, 2.5        # un precio nuevo que se aleje mas que esto del del cache se ignora (split, dato roto)
BANDA_CCL = 0.25                       # el dolar implicito de un CEDEAR puede apartarse hasta 25% de la mediana
MINIMO_PARA_MEDIANA = 5                # con menos CEDEARs que esto no hay mediana confiable y no se muestra ningun precio en pesos


def ahora_ba():
    return datetime.now(_ZONA) if _ZONA else datetime.now()


def hora_texto(dt=None):
    return (dt or ahora_ba()).strftime("%H:%M")


def _num(x):
    try:
        v = float(x)
        return v if v == v and v > 0 else None
    except (TypeError, ValueError):
        return None


def descargar_yahoo(simbolos, timeout=10):
    """{simbolo: (precio, fecha_del_dato)} para los simbolos que Yahoo devuelve. Un solo pedido. Nunca levanta excepciones (error -> {})."""
    simbolos = [s for s in dict.fromkeys(simbolos) if s]
    if not simbolos:
        return {}
    try:
        import yfinance as yf
        datos = yf.download(simbolos, period="5d", interval="1d", auto_adjust=False, progress=False, threads=True,
                            group_by="ticker", timeout=timeout)
    except Exception:  # noqa: BLE001
        return {}
    return _leer_descarga(datos, simbolos)


def _leer_descarga(datos, simbolos):
    """Saca el ultimo cierre valido de cada simbolo de lo que devuelve yf.download (con una o varias columnas por simbolo)."""
    out = {}
    try:
        if datos is None or len(datos) == 0:
            return out
        multi = hasattr(datos.columns, "nlevels") and datos.columns.nlevels > 1
        for s in simbolos:
            try:
                if multi:
                    nivel0 = set(datos.columns.get_level_values(0))
                    serie = datos[s]["Close"] if s in nivel0 else datos["Close"][s]
                else:
                    serie = datos["Close"] if len(simbolos) == 1 else None
                if serie is None:
                    continue
                serie = serie.dropna()
                if len(serie) == 0:
                    continue
                p = _num(serie.iloc[-1])
                if p is None:
                    continue
                f = serie.index[-1]
                f = f.date() if hasattr(f, "date") else None
                out[s] = (p, f)
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        return {}
    return out


def fecha_mas_comun(precios):
    """La fecha del dato que mas se repite entre los precios bajados (para decir "precios al dd/mm")."""
    cuenta = {}
    for _, f in precios.values():
        if f is not None:
            cuenta[f] = cuenta.get(f, 0) + 1
    return max(cuenta, key=cuenta.get) if cuenta else None


def aplicar_precios(df, precios, fecha=None, hora=None):
    """Copia de `df` con el precio de hoy de cada empresa (precios: {ticker: precio}). Devuelve (df_nuevo, cantidad_actualizada).
    Se guarda el precio viejo en `precio_cache`, y la fecha y la hora del dato en `precio_fecha` y `precio_hora`. Se ignora un precio que se aleje
    demasiado del del cache."""
    import pandas as pd
    if df is None or len(df) == 0 or not precios:
        return df, 0
    df = df.copy()
    if "precio_cache" not in df.columns:
        df["precio_cache"] = df["precio_actual"]
    df["precio_en_vivo"] = False
    df["precio_fecha"] = None
    df["precio_hora"] = None
    f_txt = fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else None
    n = 0
    for i in df.index:
        t = df.at[i, "ticker"]
        p0, p1 = _num(df.at[i, "precio_cache"]), _num(precios.get(t))
        if p0 is None or p1 is None or not (RATIO_MIN <= p1 / p0 <= RATIO_MAX):
            continue
        k = p1 / p0
        df.at[i, "precio_actual"] = round(p1, 4)
        df.at[i, "precio_en_vivo"] = True
        df.at[i, "precio_fecha"], df.at[i, "precio_hora"] = f_txt, hora
        mc = _num(df.at[i, "market_cap"]) if "market_cap" in df.columns else None
        if mc is not None:
            df.at[i, "market_cap"] = mc * k
        if "dividend_yield_actual" in df.columns:
            dy = _num(df.at[i, "dividend_yield_actual"])
            if dy is not None:
                df.at[i, "dividend_yield_actual"] = dy / k      # el dividendo anual no cambia: el rendimiento baja si el precio sube
        lo, hi = _num(df.at[i, "precio_min_52s"]), _num(df.at[i, "precio_max_52s"])
        if lo is not None and hi is not None and hi > lo:
            lo, hi = min(lo, p1), max(hi, p1)
            df.at[i, "precio_min_52s"], df.at[i, "precio_max_52s"] = lo, hi
            df.at[i, "posicion_52s"] = round((p1 - lo) / (hi - lo), 4)
        n += 1
    return df, n


def validar_ars(precios_ars, ratios, precios_usd):
    """Controla los precios en pesos. precios_ars: {ticker: pesos}; ratios: {ticker: ratio}; precios_usd: {ticker: dolares}.
    Devuelve ({ticker: {'ars': pesos, 'ccl': dolar_implicito}}, ccl_mediana). Descarta los que se alejan mas de BANDA_CCL de la mediana."""
    ccl = {}
    for t, ars in (precios_ars or {}).items():
        r, u, a = _num((ratios or {}).get(t)), _num((precios_usd or {}).get(t)), _num(ars)
        if r and u and a:
            ccl[t] = a * r / u
    if len(ccl) < MINIMO_PARA_MEDIANA:
        return {}, None
    med = median(ccl.values())
    buenos = {t: {"ars": float(precios_ars[t]), "ccl": c} for t, c in ccl.items() if abs(c / med - 1) <= BANDA_CCL}
    return buenos, med


def bajar_usd(tickers, descargador=None):
    """Precios en dolares de todas las empresas con un solo pedido. `descargador(lista_de_simbolos) -> {simbolo: (precio, fecha)}`
    (por defecto Yahoo). Devuelve {'usd': {ticker: precio}, 'fecha': date|None, 'hora': 'HH:MM'}; sin respuesta, 'usd' queda vacio."""
    d = descargador or descargar_yahoo
    ahora = ahora_ba()
    tickers = list(tickers)
    crudo = d(tickers) or {}
    usd = {t: crudo[t][0] for t in tickers if t in crudo}
    return {"usd": usd, "fecha": fecha_mas_comun({t: crudo[t] for t in usd}), "hora": hora_texto(ahora)}


def bajar_ars(simbolos_por_ticker, descargador=None):
    """Precios en pesos de los CEDEARs. simbolos_por_ticker: {ticker: [simbolos de Yahoo a probar en orden]}.
    Devuelve {ticker: pesos} con el primer simbolo que Yahoo conoce (todavia sin controlar: ver validar_ars)."""
    d = descargador or descargar_yahoo
    todos = [s for ss in (simbolos_por_ticker or {}).values() for s in ss]
    bruto = d(todos) or {}
    out = {}
    for t, ss in (simbolos_por_ticker or {}).items():
        for s in ss:
            if s in bruto:
                out[t] = bruto[s][0]
                break
    return out
