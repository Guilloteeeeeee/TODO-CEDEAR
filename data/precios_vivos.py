"""
Precios en vivo (v1.2.46; fuentes de respaldo en la v1.2.47).

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

v1.2.47 - Respaldos (Guille: "Yahoo los tiene mal"):
  * Pesos: ademas de Yahoo (SIMBOLO.BA) se lee la tabla de CEDEARs de Rava (https://www.rava.com/invertir/cedears, una sola pagina). Para cada
    empresa se juntan todos los precios en pesos disponibles y se usa el primero cuyo dolar implicito cierra (dentro de 3 % de la mediana);
    si ninguno cierra tan bien, el que mas se acerque mientras no pase de 25 %. Asi un precio viejo o de otro instrumento de Yahoo (DIS, UL,
    SNOW...) se reemplaza por el de Rava, y los CEDEARs que Yahoo no trae (BNY, MRSH) salen de Rava. En la pagina se dice de que fuente salio.
  * Dolares: Yahoo primero; las empresas que Yahoo no devuelva se piden a Stock Analysis (plan B; respeta robots.txt, de a una pagina, con un
    tope de empresas y de tiempo por consulta).
Ninguna de las dos fuentes de respaldo se pudo probar desde el entorno de desarrollo (esta bloqueado): las pruebas usan paginas simuladas con
el formato que se vio en cada sitio. Si el formato cambiara, no se rompe nada: la fuente se ignora y se sigue con las otras.
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
BANDA_PREFERIDA = 0.03                 # v1.2.47: si hay varios precios, se usa el primero que cae a menos de 3 % de la mediana
FUENTE_YAHOO, FUENTE_RAVA, FUENTE_SA = "Yahoo Finance", "Rava", "Stock Analysis"
RAVA_URL = "https://www.rava.com/invertir/cedears"
SA_URL = "https://stockanalysis.com/stocks/{t}/"
SA_MAX_EMPRESAS = 30                   # tope de paginas que se piden a Stock Analysis en una consulta
SA_PRESUPUESTO_SEG = 25.0              # y tiempo maximo total
SA_PAUSA_SEG = 0.4                     # pausa entre paginas (una a la vez)
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
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


def aplicar_precios(df, precios, fecha=None, hora=None, fuentes=None):
    """Copia de `df` con el precio de hoy de cada empresa (precios: {ticker: precio}). Devuelve (df_nuevo, cantidad_actualizada).
    Se guarda el precio viejo en `precio_cache`, y la fecha, la hora y la fuente del dato en `precio_fecha`, `precio_hora` y `precio_fuente`
    (fuentes: {ticker: "Yahoo Finance" | "Stock Analysis"}). Se ignora un precio que se aleje demasiado del del cache."""
    import pandas as pd
    if df is None or len(df) == 0 or not precios:
        return df, 0
    df = df.copy()
    if "precio_cache" not in df.columns:
        df["precio_cache"] = df["precio_actual"]
    df["precio_en_vivo"] = False
    df["precio_fecha"] = None
    df["precio_hora"] = None
    df["precio_fuente"] = None
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
        df.at[i, "precio_fuente"] = (fuentes or {}).get(t) or FUENTE_YAHOO
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


def bajar_usd(tickers, descargador=None, respaldo=None):
    """Precios en dolares de todas las empresas con un solo pedido. `descargador(lista_de_simbolos) -> {simbolo: (precio, fecha)}`
    (por defecto Yahoo). Las empresas que Yahoo no devuelva se piden al plan B (`respaldo(lista) -> {ticker: (precio, fecha)}`; por defecto
    Stock Analysis; `False` lo apaga). Devuelve {'usd': {ticker: precio}, 'fecha': date|None, 'hora': 'HH:MM', 'fuente': {ticker: nombre}};
    sin respuesta de nadie, 'usd' queda vacio."""
    d = descargador or descargar_yahoo
    ahora = ahora_ba()
    tickers = list(tickers)
    crudo = dict(d(tickers) or {})
    fuente = {t: FUENTE_YAHOO for t in tickers if t in crudo}
    faltan = [t for t in tickers if t not in crudo]
    if faltan and respaldo is not False:
        try:
            extra = (respaldo or descargar_stockanalysis)(faltan) or {}
        except Exception:  # noqa: BLE001
            extra = {}
        for t, v in extra.items():
            if t in faltan and _num(v[0]):
                crudo[t] = (float(v[0]), v[1] if len(v) > 1 else None)
                fuente[t] = FUENTE_SA
    usd = {t: crudo[t][0] for t in tickers if t in crudo}
    return {"usd": usd, "fecha": fecha_mas_comun({t: crudo[t] for t in usd}), "hora": hora_texto(ahora), "fuente": fuente}


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


# ---------------------------------------------------------------------------
# v1.2.47 - FUENTES DE RESPALDO
# ---------------------------------------------------------------------------

def _http_get(url, timeout=10):
    """Texto de la pagina `url` o None (cualquier error, o un codigo que no sea 200, da None; nunca levanta excepciones)."""
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                                       "Accept-Language": "es-AR,es;q=0.9,en;q=0.7"}, timeout=timeout)
        return r.text if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


def _num_ar(txt):
    """'15.480,00' -> 15480.0 ; '8,34' -> 8.34 ; '-' o vacio -> None (formato argentino: punto de miles y coma decimal)."""
    t = str(txt or "").strip().replace("\xa0", "").replace(" ", "")
    if not t or t in ("-", "—"):
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1 or (t.count(".") == 1 and len(t.rsplit(".", 1)[1]) == 3):
        t = t.replace(".", "")          # '15.480' = quince mil cuatrocientos ochenta
    return _num(t)


_RE_FILA = None


def parsear_rava(texto):
    """{simbolo_de_BYMA: precio_en_pesos} a partir de la pagina de CEDEARs de Rava.
    La pagina es una tabla (Especie, Nombre, Ultimo, Var %) cuyas filas empiezan con 'AAPL-0002-C-CT-ARS' (simbolo, plazo de 48 hs,
    pesos) y el precio ultimo en formato argentino ('28.660,00'). Se leen las filas <tr>; si la pagina no trae esa estructura, se busca el
    mismo patron en el texto plano. Solo se toman las especies en pesos (terminan en -ARS: las que terminan en -USD se ignoran).
    Devuelve {} si no encuentra nada (pagina distinta, bloqueo...)."""
    import html as _html
    import re
    global _RE_FILA
    if _RE_FILA is None:
        _RE_FILA = re.compile(r"^([A-Z0-9][A-Z0-9.]*?)-\d{4}-[A-Z]-[A-Z]{2}-ARS$")
    out = {}
    if not texto:
        return out

    def sin_tags(x):
        return _html.unescape(re.sub(r"<[^>]*>", " ", x)).replace("\xa0", " ").strip()

    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", texto, flags=re.S | re.I):
        celdas = [sin_tags(c) for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
        if not celdas:
            continue
        m = _RE_FILA.match(celdas[0].replace(" ", ""))
        if not m:
            continue
        for c in celdas[1:]:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?", c.replace(" ", "")):
                v = _num_ar(c)
                if v:
                    out[m.group(1)] = v
                break
    if out:
        return out
    # Respaldo: texto plano (celdas separadas por | o por saltos de linea)
    plano = re.sub(r"<[^>]*>", "|", texto)
    plano = _html.unescape(plano)
    for m in re.finditer(r"([A-Z0-9][A-Z0-9.]*?)-\d{4}-[A-Z]-[A-Z]{2}-ARS[\s|]+(?:[^|\n]*?[\s|]+)?(\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+)", plano):
        v = _num_ar(m.group(2))
        if v and m.group(1) not in out:
            out[m.group(1)] = v
    return out


def descargar_rava(timeout=10, get=None):
    """{simbolo_de_BYMA: (precio_en_pesos, None)} de la tabla de CEDEARs de Rava (una sola pagina). Error o pagina rara -> {}."""
    try:
        texto = (get or _http_get)(RAVA_URL, timeout)
        return {s: (p, None) for s, p in parsear_rava(texto).items()}
    except Exception:  # noqa: BLE001
        return {}


def parsear_precio_sa(texto):
    """(precio, fecha) de la pagina de una accion en Stock Analysis, o None. El precio es el numero grande de arriba; a su lado dice
    'At close: Oct 23, 2026, 4:00 PM EDT' (si el mercado esta abierto no hay fecha y se devuelve None en su lugar)."""
    import html as _html
    import re
    from datetime import datetime as _dt
    if not texto:
        return None
    precio = None
    m = re.search(r'<div[^>]*class="[^"]*\btext-4xl\b[^"]*"[^>]*>\s*\$?\s*([\d,]+(?:\.\d+)?)\s*</div>', texto, flags=re.S)
    if m:
        precio = _num(m.group(1).replace(",", ""))
    plano = _html.unescape(re.sub(r"<[^>]*>", " ", texto))
    plano = re.sub(r"\s+", " ", plano)
    m2 = re.search(r"([\d,]+\.\d{2,4})\s+[+\-−]?\s*[\d,.]+\s*\(\s*[+\-−]?\s*[\d.,]+%\s*\)\s*(?:At close|Real-Time|After|Pre)", plano)
    if precio is None and m2:
        precio = _num(m2.group(1).replace(",", ""))
    if precio is None:
        return None
    fecha = None
    m3 = re.search(r"At close:\s*([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", plano)
    if m3:
        try:
            fecha = _dt.strptime(f"{m3.group(1)} {m3.group(2)} {m3.group(3)}", "%b %d %Y").date()
        except ValueError:
            fecha = None
    return precio, fecha


def descargar_stockanalysis(tickers, get=None, robots=None, max_empresas=None, presupuesto=None, pausa=None, reloj=None, dormir=None):
    """Plan B de los precios en dolares: {ticker: (precio, fecha)} leidos de stockanalysis.com/stocks/<ticker>/, de a una pagina, con
    pausa, hasta `max_empresas` empresas y `presupuesto` segundos en total (lo que no alcance queda con el precio del cache). Respeta
    robots.txt. Cualquier error en una empresa la salta; tres bloqueos seguidos cortan la consulta. Nunca levanta excepciones."""
    import time
    max_empresas = SA_MAX_EMPRESAS if max_empresas is None else max_empresas
    presupuesto = SA_PRESUPUESTO_SEG if presupuesto is None else presupuesto
    pausa = SA_PAUSA_SEG if pausa is None else pausa
    reloj = reloj or time.monotonic
    dormir = dormir or time.sleep
    out = {}
    try:
        if robots is None:
            from data import stockanalysis as _sa
            robots = lambda u: _sa._robots_permite(u)      # noqa: E731
        t0, fallos = reloj(), 0
        for t in list(tickers)[:max_empresas]:
            if reloj() - t0 > presupuesto or fallos >= 3:
                break
            url = SA_URL.format(t=str(t).lower().replace("-", "."))
            try:
                if not robots(url):
                    fallos += 1
                    continue
                r = parsear_precio_sa((get or _http_get)(url, 10))
            except Exception:  # noqa: BLE001
                r = None
            if r:
                out[t] = r
                fallos = 0
            else:
                fallos += 1
            if pausa:
                dormir(pausa)
    except Exception:  # noqa: BLE001
        pass
    return out


def bajar_ars_fuentes(simbolos_yahoo, simbolos_byma, yahoo=None, rava=None):
    """Todos los precios en pesos disponibles, sin controlar: {ticker: [(fuente, pesos), ...]} con primero los de Yahoo (cada simbolo
    que Yahoo conozca, no solo el primero: BA.C.BA puede ser otra cosa y BAC.BA el correcto) y despues el de Rava.
    simbolos_yahoo: {ticker: [simbolos de Yahoo]}; simbolos_byma: {ticker: simbolo de BYMA}. `yahoo` y `rava` son funciones
    descargadoras (para pruebas); `rava=False` la apaga."""
    d = yahoo or descargar_yahoo
    todos = [s for ss in (simbolos_yahoo or {}).values() for s in ss]
    bruto = d(todos) or {}
    cand = {}
    for t, ss in (simbolos_yahoo or {}).items():
        for s in ss:
            if s in bruto:
                cand.setdefault(t, []).append((FUENTE_YAHOO, bruto[s][0]))
    if rava is not False:
        try:
            r = (rava or descargar_rava)() or {}
        except Exception:  # noqa: BLE001
            r = {}
        for t, sim in (simbolos_byma or {}).items():
            if sim in r:
                cand.setdefault(t, []).append((FUENTE_RAVA, r[sim][0]))
    return cand


def elegir_ars(candidatos, ratios, precios_usd):
    """Elige, para cada empresa, el precio en pesos que mejor cierra. candidatos: {ticker: [(fuente, pesos), ...]} en orden de preferencia;
    ratios: {ticker: ratio}; precios_usd: {ticker: dolares}. El dolar implicito de cada precio es pesos x ratio / dolares; la mediana de todos
    es la referencia. Se usa el primero que cae a menos de BANDA_PREFERIDA (3 %) de la mediana; si ninguno, el mas cercano mientras este a menos
    de BANDA_CCL (25 %); si no, la empresa queda sin precio en pesos.
    Devuelve ({ticker: {'ars', 'ccl', 'fuente'}}, mediana)."""
    ccl = {}
    for t, lista in (candidatos or {}).items():
        r, u = _num((ratios or {}).get(t)), _num((precios_usd or {}).get(t))
        if not (r and u):
            continue
        for fuente, ars in lista:
            a = _num(ars)
            if a:
                ccl.setdefault(t, []).append((fuente, a, a * r / u))
    todos = [c for l in ccl.values() for _, _, c in l]
    if len(todos) < MINIMO_PARA_MEDIANA:
        return {}, None
    med = median(todos)
    out = {}
    for t, l in ccl.items():
        ok = [x for x in l if abs(x[2] / med - 1) <= BANDA_CCL]
        if not ok:
            continue
        cerca = [x for x in ok if abs(x[2] / med - 1) <= BANDA_PREFERIDA]
        f, a, c = cerca[0] if cerca else min(ok, key=lambda x: abs(x[2] / med - 1))
        out[t] = {"ars": float(a), "ccl": c, "fuente": f}
    return out, med
