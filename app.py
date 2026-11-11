"""
CEDEAR Screener — App principal Streamlit
Detecta CEDEARs potencialmente infravalorados usando métricas fundamentales
y técnicas de Stock Analysis y Yahoo Finance (caché que se actualiza una vez por trimestre).

Ejecutar: streamlit run app.py
"""

APP_VERSION = "1.5.69"

import re
import contextlib
import streamlit as st
import pandas as pd
import numpy as np
import html
import json
import os
import sys
import time
from datetime import datetime

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importaciones del proyecto
from data.fetcher import fetch_all_tickers
from scoring.engine import score_dataframe, leyenda_categorias, COLOR_POR_CATEGORIA, nombre_visible, nombre_corto
from scoring.seguimiento import (cargar_copias, evaluar_copias, proxima_medicion, CATEGORIAS_ORDEN,
                                 MIN_DIAS_ENTRE_COPIAS)
from config.sectors import TICKER_UNIVERSE, TICKER_TO_SECTOR, SECTOR_CONFIG, etiqueta_sector, PAIS_MANUAL, partes_sector
from config.industrias import industria_de
from ui.banderas import css_banderas, bandera_html
from ui.fuentes import css_condensada, css_fuente
from ui.marca import CSS as CSS_MARCA, icono_pagina, encabezado_html, pie_html, css_nav, menu_cabecera_html, menu_lista_html, menu_flyouts_html, fly_cabecera_html, SCRIPT_ESC, nav_html, CSS_NAV, SCRIPT_ATRAS
from ui import noticias as _noticias, calendario as _calendario
from data import tecnicos as _tecnicos
from data import historico as _hist
from ui import cartera_visual as _cartera_visual
from ui.cajas import CSS as CSS_CAJAS
from ui.exportar import excel_bytes
from ui import estado as estado_url
from ui.logos import logo_html
try:
    from config.ajustes import NOMBRE_APP
except ImportError:      # ajustes.py viejo
    NOMBRE_APP = "TodoCedears"
from ui.tabla_visual import (CSS as CSS_VISUAL, escala_valoracion_html, COLUMNAS_BASE, columnas_base, css_encabezado, html_tabla_visual,
                             ayuda_texto, css_ayudas, anchos as anchos_tabla, _mayusculas)
from ui import criterios as _criterios
from ui import variables as _variables
from ui.ficha import ficha_html, texto_fuente, CSS as CSS_FICHA
from ui.flecha import poner_flecha, CSS_OCULTAR as CSS_FLECHA
from ui.quienes import quienes_html, quienes_panel_html, CSS as CSS_QUIENES
from ui import ficha as _ficha
from ui import tabla_visual as _tv
from ui import tecnico as _tecnico
from data import swr as _swr
from data import cedears as _cedears, precios_vivos as _pv, fichas as _fichas, historial_precios as _hp, yahoo_extra as _yx, paquetes_yahoo as _py

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=NOMBRE_APP,
    page_icon=icono_pagina("📊"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CACHE Y PERSISTENCIA
# ---------------------------------------------------------------------------

CACHE_FILE = "data/cache_datos.json"
TICKERS_FILE = "data/tickers_custom.json"
CACHE_TTL_HORAS = 6  # v1.2.50: solo vale para la memoria de la app (st.cache_data); el cache en disco se usa SIEMPRE, de cualquier edad (ignorar_ttl=True)


def load_custom_tickers() -> dict:
    """Carga el universo de tickers personalizado (o usa el default)."""
    if os.path.exists(TICKERS_FILE):
        try:
            with open(TICKERS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {k: list(v) for k, v in TICKER_UNIVERSE.items()}


def save_custom_tickers(universe: dict):
    """Persiste el universo de tickers personalizado."""
    os.makedirs("data", exist_ok=True)
    with open(TICKERS_FILE, "w") as f:
        json.dump(universe, f, indent=2)


def load_cache(ignorar_ttl: bool = False) -> tuple[pd.DataFrame | None, datetime | None]:
    """
    Carga datos del cache.
    Si ignorar_ttl=True, devuelve el cache aunque esté vencido (fallback cuando yfinance falla).
    """
    cache = None
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
        except Exception:
            cache = None
    if cache is None:
        # v1.2.50: cache principal ausente o ilegible -> la copia mas nueva y valida de data/historial (antes la app bajaba todo de Yahoo,
        # que bloquea a los servidores en la nube, y con otro metodo)
        from data.cache_seguro import ultimo_historial_valido
        _, cache = ultimo_historial_valido(os.path.join("data", "historial"))
        if cache is None:
            return None, None
    try:
        ts = datetime.fromisoformat(cache["timestamp"])
        horas_pasadas = (datetime.now() - ts).total_seconds() / 3600
        if horas_pasadas > CACHE_TTL_HORAS and not ignorar_ttl:
            return None, ts
        df = pd.DataFrame(cache["data"])
        if "categoria" in df.columns:
            df["color_hex"] = df["categoria"].map(COLOR_POR_CATEGORIA).fillna(df.get("color_hex"))
        return df, ts
    except Exception:
        return None, None


def save_cache(df: pd.DataFrame):
    """Guarda datos en cache."""
    os.makedirs("data", exist_ok=True)
    cache = {
        "timestamp": datetime.now().isoformat(),
        "data": df.replace({np.nan: None}).to_dict(orient="records"),
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---------------------------------------------------------------------------
# CARGA / ACTUALIZACIÓN DE DATOS
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL_HORAS * 3600, show_spinner=False)
def get_scored_data(universe_key: str) -> tuple[pd.DataFrame, str]:
    """
    Carga datos con esta prioridad:
    1. Cache guardado (de cualquier edad) → mostrar directo. v1.2.13: el cache se genera en la PC
       (generar_cache.bat, con Stock Analysis como fuente principal) y es la fuente oficial; la app
       NO lo reemplaza con datos de Yahoo.
    2. Sin cache (primera instalación) → yfinance, solo Yahoo
    Retorna (df, fuente).
    """
    universe = load_custom_tickers()
    all_tickers = [t for tickers in universe.values() for t in tickers]
    ticker_to_sector = {
        ticker: sector
        for sector, tickers in universe.items()
        for ticker in tickers
    }

    # 1. Cache guardado → usar directo
    df_cache, ts_cache = load_cache(ignorar_ttl=True)
    if df_cache is not None and not df_cache.empty:
        ts_str = ts_cache.strftime("%d/%m/%Y %H:%M") if ts_cache else "?"
        return df_cache, f"cache_vigente|{ts_str}"

    # 2. Intentar yfinance
    progress_bar = st.progress(0, text="Descargando datos de Yahoo Finance...")
    try:
        def progress_cb(i, total, ticker):
            pct = int((i / total) * 100)
            progress_bar.progress(pct, text=f"Descargando {ticker} ({i+1}/{total})...")

        raw_df = fetch_all_tickers(all_tickers, progress_callback=progress_cb, modo_sa="apagado")
        progress_bar.progress(100, text="Calculando scores...")

        datos_ok = raw_df["precio_actual"].notna().sum() > len(all_tickers) * 0.1
        if not datos_ok:
            raise ValueError("yfinance devolvió menos del 10% de datos")

        scored_df = score_dataframe(raw_df, ticker_to_sector)
        save_cache(scored_df)
        progress_bar.empty()
        return scored_df, "live"

    except Exception as e:
        progress_bar.empty()
        # 3. Cache vencido como último recurso
        df_viejo, ts_viejo = load_cache(ignorar_ttl=True)
        if df_viejo is not None and not df_viejo.empty:
            ts_str = ts_viejo.strftime("%d/%m/%Y %H:%M") if ts_viejo else "?"
            return df_viejo, f"cache_vencido|{e}|{ts_str}"
        raise


# ---------------------------------------------------------------------------
# PRECIOS EN VIVO (v1.2.46): ver data/precios_vivos.py
# ---------------------------------------------------------------------------
try:
    from config.ajustes import PRECIOS_VIVOS, PRECIOS_MINUTOS_CACHE
except ImportError:      # ajustes.py viejo
    PRECIOS_VIVOS, PRECIOS_MINUTOS_CACHE = True, 5


def _orden_tickers(df: pd.DataFrame) -> tuple:
    """Los tickers de la tabla, de mayor a menor capitalizacion (si Yahoo falla y hay que pedir el precio uno por uno a Stock Analysis,
    se piden primero las empresas mas grandes)."""
    try:
        d = df[["ticker", "market_cap"]].copy()
        d["_mc"] = pd.to_numeric(d["market_cap"], errors="coerce").fillna(-1)
        return tuple(d.sort_values(["_mc", "ticker"], ascending=[False, True])["ticker"])
    except Exception:  # noqa: BLE001
        return tuple(sorted(df["ticker"]))


def _precios_usd(tickers: tuple, esperar: float = 15.0) -> dict:
    """Precios en dolares de todas las empresas (un solo pedido a Yahoo; las que falten, a Stock Analysis). Si falla, {'usd': {}} y la app
    sigue con el precio del cache. v1.5.22: se guardan PRECIOS_MINUTOS_CACHE minutos y, al vencer, se renuevan EN SEGUNDO PLANO (data/swr.py): antes la
    primera visita después del vencimiento esperaba toda la bajada."""
    vacio = {"usd": {}, "fecha": None, "hora": _pv.hora_texto(), "fuente": {}, "var": {}}
    return _swr.obtener(("usd", tickers), lambda: _pv.bajar_usd(tickers), max(1, int(PRECIOS_MINUTOS_CACHE)) * 60,
                        valido=lambda r: bool(r.get("usd")), vacio=vacio, esperar=esperar)


def _precios_ars(items: tuple, esperar: float = 4.0) -> dict:
    """Precios en pesos de los CEDEARs: items = ((ticker, (simbolos de Yahoo...), simbolo de BYMA), ...). Devuelve
    {ticker: [(fuente, pesos), ...]} con los de Yahoo y el de Rava (sin controlar: ver _pv.elegir_ars). Si falla, {}.
    v1.5.52 (Guille: «tarda mucho en cargar»): igual que los precios en dólares, se devuelve al instante lo último bajado y se renueva EN SEGUNDO PLANO
    (data/swr.py). Antes, cada 5 minutos, la primera visita esperaba la bajada de los precios en pesos de todos los CEDEARs."""
    def _bajar():
        return _pv.bajar_ars_fuentes({t: list(ss) for t, ss, _ in items}, {t: b for t, _, b in items})
    try:
        return _swr.obtener(("ars", items), _bajar, max(1, int(PRECIOS_MINUTOS_CACHE)) * 60, valido=lambda r: bool(r), vacio={}, esperar=esperar) or {}
    except Exception:  # noqa: BLE001
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _fichas_datos() -> dict:
    """Datos de Yahoo de cada empresa (data/fichas.json: descripcion, CEO, web, mercado, EV, crecimiento...). {} si el archivo no esta."""
    try:
        return _fichas.cargar()[0]
    except Exception:  # noqa: BLE001
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _mercado_vivo(ticker: str):
    """Codigo del mercado segun Yahoo, pedido en el momento (solo si data/fichas.json no trae el de esa empresa). None si no responde."""
    try:
        return _fichas.mercado_en_vivo(ticker)
    except Exception:  # noqa: BLE001
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _ficha_viva(ticker: str) -> dict:
    """v1.2.52: ficha de Yahoo pedida en el momento, solo para las empresas que no estan en data/fichas.json (o sin descripcion). {} si no responde."""
    try:
        return _fichas.ficha_en_vivo(ticker) or {}
    except Exception:  # noqa: BLE001
        return {}


@st.cache_resource
def _memo_extras() -> dict:
    return {}


def _sp500(m):
    """Historial del S&P 500 (para la recesion 2007-09); se guarda un dia. None si Yahoo no responde."""
    hit = m.get("^GSPC")
    if hit and time.time() - hit[0] < 86400:
        return hit[1]
    v = _hp.bajar("^GSPC", timeout=25.0)
    if v:
        m["^GSPC"] = (time.time(), v)
    return v


def _extras_empresa(ticker: str) -> dict:
    """v1.2.57: lo que piden las solapas de la empresa a Yahoo. Un solo pedido de datos (`yahoo_extra.bajar_paquete`: antes eran cuatro en paralelo y Yahoo
    cortaba algunos) mas el historial de precios, en paralelo. Se guarda 30 minutos SOLO si Yahoo respondio algo: un fallo no se guarda, asi que al
    recargar se vuelve a intentar. Lo que no responde queda vacio y la solapa dice "no disponible"."""
    m = _memo_extras()
    hit = m.get(("emp", ticker))
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    vacio = {"historial": None, "dividendos": {}, "gobierno": {}, "noticias": [], "agenda": {}, "estados": {}, "sp": None}
    guardado, fecha_g = _paquetes_guardados()
    # v1.5.52 (Guille: «tarda mucho en cargar»): las dos bajadas de Yahoo arrancan juntas en segundo plano (data/swr.py). Si la empresa ya tiene su
    # paquete guardado (data/paquetes_yahoo.json), la página NO espera al de Yahoo (que desde la nube tardaba de 5 a 20 segundos): sale con el guardado
    # y lo nuevo queda listo para la visita siguiente. El historial de precios (gráfico y análisis técnico) sí se espera, pero con tope.
    hay_guardado = bool(guardado.get(ticker.upper()))
    k_paq, k_hist = ("paq", ticker), ("hist", ticker)
    paq_ok = lambda r: bool(r and (r.get("info_ok") or r.get("estados") or r.get("dividendos") or r.get("gobierno")))  # noqa: E731
    try:
        _swr.obtener(k_paq, lambda: _yx.bajar_paquete(ticker), 1800, esperar=0, valido=paq_ok, vacio=None)      # solo la arranca
        hist = _swr.obtener(k_hist, lambda: _hp.bajar(ticker), 1800, esperar=8.0, valido=bool, vacio=None)
        paq = _swr.obtener(k_paq, lambda: _yx.bajar_paquete(ticker), 1800, esperar=(1.0 if hay_guardado else 40.0), valido=paq_ok, vacio=None) or {}
        res = {"historial": hist, "sp": None}
        res.update({k: paq.get(k) or vacio[k] for k in ("dividendos", "gobierno", "noticias", "agenda", "estados")})
    except Exception:  # noqa: BLE001
        res = dict(vacio)
        paq = {}
    # v1.2.59: lo que Yahoo no contesto desde la nube se completa con el archivo data/paquetes_yahoo.json (lo baja bajar_paquetes_yahoo.bat)
    res, usadas = _py.completar(res, guardado.get(ticker.upper()))
    # v1.5.48: archivo histórico propio: se suman los años fiscales guardados que Yahoo ya no trae (ajustados por splits); si Yahoo no trajo nada, salen de ahí
    try:
        _arch_est, _arch_sp = _historico_estados()
        res["estados"] = _hist.estados_completos(ticker, res.get("estados"), archivo=_arch_est, splits=_arch_sp.get(ticker.upper(), []))
    except Exception:  # noqa: BLE001
        pass
    if isinstance(res.get("estados"), dict) and res["estados"]:       # v1.5.52: ROIC con el capital invertido arreglado (ASML 12 meses daba 642%)
        res["estados"] = _yx.reparar_roic(res["estados"])
    if isinstance(res.get("estados"), dict) and res["estados"]:       # v1.4.2: Yahoo rotula mal la moneda de algunas (VALE: dice reales y está en dólares)
        from data import moneda as _mon
        res["estados"] = {**res["estados"], "moneda": _mon.moneda_estados(ticker, res["estados"].get("moneda"))}
    res["archivo"] = {"fecha": fecha_g, "claves": usadas, "foto": (guardado.get(ticker.upper()) or {}).get("foto_ceo")} if usadas or guardado.get(ticker.upper()) else None
    if res["historial"] and paq_ok(paq):      # v1.5.52: se guarda el resultado armado solo cuando llegó lo de Yahoo (si no, la próxima vez se usa lo nuevo)
        if len(m) > 300:
            m.clear()
        m[("emp", ticker)] = (time.time(), res)
    return res


@st.cache_data(ttl=3600, show_spinner=False)
def _bono10_hoy():
    """v1.2.91: rendimiento del bono del Tesoro a 10 años (Yahoo ^TNX), para la valuación del Análisis Fundamental. None si Yahoo no responde
    (entonces se usa el de la foto macro, data/macro_numeros.json)."""
    if not PRECIOS_VIVOS:
        return None
    from data import af_v4 as _v4
    return _v4.bono10_vivo()


@st.cache_data(ttl=3600, show_spinner=False)
def _paquetes_guardados():
    """({TICKER: datos}, fecha) del archivo data/paquetes_yahoo.json; ({}, None) si no esta."""
    try:
        return _py.cargar()
    except Exception:  # noqa: BLE001
        return {}, None


@st.cache_data(ttl=3600, show_spinner=False)
def _historico_precios():
    """v1.5.49: {ticker: {"AAAA-MM": cierre}} del archivo histórico propio (bajar_historico.bat); {} si todavía no está."""
    try:
        return {t: (r or {}).get("m") or {} for t, r in _hist.leer("precios_mensuales.json", {}).items()}
    except Exception:  # noqa: BLE001
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _historico_estados():
    """v1.5.48: (estados.json, splits.json) del archivo histórico propio (data/historico/); ({}, {}) si no están."""
    try:
        return _hist.leer("estados.json", {}), _hist.leer("splits.json", {})
    except Exception:  # noqa: BLE001
        return {}, {}


@st.cache_data(ttl=3600, show_spinner=False)
def _tecnicos_guardados():
    """({TICKER: {rsi, vs50, ...}}, fecha) de data/tecnicos.json (lo baja bajar_tecnicos.bat); ({}, None) si no esta."""
    try:
        return _tecnicos.cargar()
    except Exception:  # noqa: BLE001
        return {}, None


@st.cache_data(ttl=3600, show_spinner=False)
def _multiplos_anuales_datos() -> dict:
    """Multiplos de cada anio fiscal (data/multiplos_anuales.json, lo baja bajar_multiplos_anuales.bat). {} si el archivo no esta."""
    try:
        from data import multiplos_anuales as _ma
        return _ma.cargar()[0]
    except Exception:  # noqa: BLE001
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _af_para_ficha(ticker: str):
    """Análisis Fundamental automático de la empresa (data/analisis_fundamental.json, lo arma generar_analisis_fundamental.py). None si no tiene."""
    try:
        from data import analisis_fundamental as _af
        return _af.para_ficha(ticker)
    except Exception:  # noqa: BLE001
        return None


def _boton_pdf_analisis(tk, af, rd, extra, pares):
    """v1.4.1: botón para bajar el Análisis Fundamental (formato v4) en PDF, con los números del día. Se arma en memoria y se guarda un rato por empresa y por precio.
    v1.4.2: va en la misma fila que la fecha ("Escrito el ..."), con el ícono de PDF y el texto "Descargar en PDF". Devuelve True si mostró la fila (entonces la fecha
    ya no va dentro del mosaico del título). Si algo falla (por ejemplo, no está reportlab), no muestra nada y devuelve False: el resto de la página sigue igual."""
    if not (af and af.get("formato") == "v4" and af.get("titulo")):
        return False
    try:
        m = _memo_extras()
        clave = ("afpdf", tk, str(af.get("fecha")), str(rd.get("precio_actual")), str(rd.get("fair_value")), bool(extra.get("estados")))
        hit = m.get(clave)
        if hit and time.time() - hit[0] < 1800:
            datos = hit[1]
        else:
            from ui import af_pdf as _afpdf
            datos = _afpdf.pdf_analisis(af, extra.get("estados"), rd, pares, extra.get("dividendos"), _bono10_hoy(), str(rd.get("nombre") or ""))
            if len(m) > 300:
                m.clear()
            m[clave] = (time.time(), datos)
    except Exception:  # noqa: BLE001
        return False
    args = dict(data=datos, file_name=f"analisis_fundamental_{tk}_{(str(af.get('fecha') or '')).replace('/', '-')}.pdf", mime="application/pdf", key=f"pdf_af_{tk}", on_click="ignore",
                help="Baja este análisis en PDF, con los números de hoy. Es información con fines educativos, no una recomendación.")
    try:
        fila = st.container(horizontal=True, vertical_alignment="center", gap="small")
    except TypeError:       # Streamlit viejo, sin filas horizontales: la fecha y el botón quedan uno debajo del otro
        fila = st.container()
    with fila:
        st.markdown(f'<span style="font-size:.85rem;color:#64748b;white-space:nowrap">Escrito el {html.escape(str(af.get("fecha") or ""))}</span>', unsafe_allow_html=True)
        try:
            st.download_button("Descargar en PDF", icon=":material/picture_as_pdf:", type="tertiary", **args)
        except TypeError:       # Streamlit viejo, sin icon, type="tertiary" u on_click="ignore"
            for k in ("on_click",):
                args.pop(k, None)
            st.download_button("Descargar en PDF", **args)
    return True


@st.cache_data(ttl=900, show_spinner=False)
def _intradia(ticker: str, marco: str):
    """Cierres cada 5 minutos (1D) o cada 30 minutos (5D). None si Yahoo no responde."""
    try:
        return _yx.bajar_intradia(ticker, marco)
    except Exception:  # noqa: BLE001
        return None


@st.cache_resource(show_spinner=False)
def _fotos_memo():
    return {}


def _foto_ceo(nombre: str, empresa: str):
    """URL de la foto del CEO en Wikipedia (solo si la pagina coincide con el nombre, la empresa y el cargo) o None.
    v1.2.58: solo se guarda en memoria cuando se encontro la foto; si falla (Wikipedia no respondio, un corte) se vuelve a intentar la proxima vez
    (antes un fallo quedaba guardado un dia entero y la foto no salia)."""
    memo = _fotos_memo()
    k = (nombre, empresa)
    if memo.get(k):
        return memo[k]
    # v1.5.52: un fallo se recuerda 30 minutos (antes se reintentaba en cada visita y sumaba más de un segundo a cada página sin foto)
    falla = memo.get(("falla",) + k)
    if falla and time.time() - falla < 1800:
        return None
    from data import foto_ceo as _fc
    url = _fc.buscar_foto(nombre, empresa)
    if url:
        memo[k] = url
    else:
        memo[("falla",) + k] = time.time()
    return url


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _descripcion_es(texto_en: str):
    """Traduccion al castellano de la descripcion de Yahoo (cuando data/fichas.json solo la trae en ingles). Primero deep-translator (Google); si no esta
    instalado o falla, MyMemory por oraciones. None si ninguno anda (entonces se muestra el original). v1.2.53."""
    try:
        from bajar_fichas import _traducir
        es = _traducir(texto_en)
        if es:
            return es
    except Exception:  # noqa: BLE001
        pass
    try:
        from ui.traducir import traducir_texto_largo
        return traducir_texto_largo(texto_en)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# ETFs (v1.2.64)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _etfs_lista() -> list:
    """Los ETFs de data/etfs.csv ([] si el archivo no esta)."""
    try:
        from data import etfs as _etfs
        return _etfs.cargar()
    except Exception:  # noqa: BLE001
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def _etfs_guardados():
    """({TICKER: datos}, fecha) del archivo data/etfs_yahoo.json (lo baja bajar_etfs_yahoo.bat); ({}, None) si no esta."""
    try:
        from data import etfs_yahoo as _ey
        return _ey.cargar()
    except Exception:  # noqa: BLE001
        return {}, None


@st.cache_data(ttl=max(1, int(PRECIOS_MINUTOS_CACHE)) * 60, show_spinner=False)
def _info_etfs(items: tuple) -> dict:
    """Precios en dolares y variacion del dia de los ETFs: items = ((ticker, simbolo de Yahoo), ...). Un solo pedido a Yahoo.
    {'precio': {ticker: usd}, 'var': {ticker: %}} (vacios si no responde)."""
    try:
        info = _pv.bajar_usd([s for _, s in items], respaldo=False)
        usd, var = info.get("usd") or {}, info.get("var") or {}
        return {"precio": {t: usd[s] for t, s in items if s in usd}, "var": {t: var[s] for t, s in items if s in var}}
    except Exception:  # noqa: BLE001
        return {"precio": {}, "var": {}}


def _precios_etfs(items: tuple) -> dict:
    """Precios en dolares de los ETFs (ver _info_etfs). {} si Yahoo no responde."""
    return _info_etfs(items)["precio"]


def _var_etfs(items: tuple) -> dict:
    """Variacion del dia (%) de los ETFs (ver _info_etfs). {} si Yahoo no responde."""
    return _info_etfs(items)["var"]


def _extras_etf(e: dict) -> dict:
    """Lo que la pagina de un ETF pide a Yahoo: historial de precios y sus datos (NAV, AUM, comision, dividendos, tenencias, noticias), en paralelo.
    Lo que Yahoo no contesta desde la nube se completa con data/etfs_yahoo.json. Se guarda 30 minutos solo si Yahoo respondio algo."""
    from concurrent.futures import ThreadPoolExecutor
    from data import etfs as _etfs, etfs_yahoo as _ey
    tk = e["ticker"]
    sim = _etfs.simbolo_yahoo(e)
    m = _memo_extras()
    hit = m.get(("etf", tk))
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    vivo, hist = {}, None
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_h, f_d = ex.submit(_hp.bajar, sim), ex.submit(_ey.bajar, sim)
            vivo = f_d.result(timeout=90) or {}
            hist = f_h.result(timeout=60)
    except Exception:  # noqa: BLE001
        pass
    guardado, fecha_g = _etfs_guardados()
    datos, usadas = _ey.completar(vivo, guardado.get(tk))
    res = {"historial": hist, "datos": datos, "simbolo": sim, "archivo": {"fecha": fecha_g, "claves": usadas} if usadas else None}
    if hist or vivo:
        if len(m) > 300:
            m.clear()
        m[("etf", tk)] = (time.time(), res)
    return res


def _cedear_etf(df: pd.DataFrame, e: dict, precio_usd) -> dict:
    """{'ratio', 'simbolo', 'precio_ars'...} del CEDEAR de un ETF. El ratio sale de data/etfs.csv (columna ratio): si esta vacio no se inventa nada.
    El precio en pesos solo se muestra si paso el control de coherencia con el dolar implicito de las demas empresas (ver _pv.elegir_ars)."""
    ratio = _cedears.leer_ratio(e.get("ratio"))
    t = e["ticker"]
    d = {"ratio": ratio, "simbolo": (e.get("simbolo") or t).upper()}
    if not (ratio and precio_usd and PRECIOS_VIVOS):
        return d
    try:
        datos = _cedears.cargar()
        info = _precios_usd(_orden_tickers(df))
        usd = dict(info.get("usd") or {})
        if not usd:
            return d
        simbolos = _cedears.simbolos_yahoo(datos)
        items = tuple((k, tuple(ss), datos[k].get("simbolo") or k) for k, ss in sorted(simbolos.items()))
        cand = dict(_precios_ars(items))
        propios = _cedears.simbolos_yahoo({t: {"simbolo": d["simbolo"]}}).get(t) or [d["simbolo"] + ".BA"]
        cand.update(_precios_ars(((t, tuple(propios), d["simbolo"]),)))
        ratios = {k: v.get("ratio") for k, v in datos.items()}
        ratios[t] = ratio
        usd[t] = precio_usd
        buenos, ccl = _pv.elegir_ars(cand, ratios, usd)
        b = buenos.get(t)
        if b:
            d.update({"precio_ars": b["ars"], "ccl": b["ccl"], "fuente_ars": b["fuente"]})
    except Exception:  # noqa: BLE001
        pass
    return d


def _datos_cedear(df: pd.DataFrame, ticker: str) -> dict:
    """{TICKER: {'ratio', 'simbolo', 'precio_ars', 'ccl', 'fuente_ars', 'hora'}} para la pagina de la empresa. El precio en pesos solo se
    muestra si paso el control de coherencia (ver _pv.elegir_ars). Nunca levanta excepciones."""
    try:
        datos = _cedears.cargar()
        d = dict(datos.get(str(ticker).upper()) or {})
        if not d or not PRECIOS_VIVOS:
            return {str(ticker).upper(): d}
        info = _precios_usd(_orden_tickers(df))
        usd = info.get("usd") or {}
        if not usd:
            return {str(ticker).upper(): d}
        simbolos = _cedears.simbolos_yahoo(datos)
        items = tuple((t, tuple(ss), datos[t].get("simbolo") or t) for t, ss in sorted(simbolos.items()))
        cand = _precios_ars(items)
        ratios = {t: v.get("ratio") for t, v in datos.items()}
        buenos, ccl = _pv.elegir_ars(cand, ratios, usd)
        b = buenos.get(str(ticker).upper())
        if b:
            d.update({"precio_ars": b["ars"], "ccl": b["ccl"], "ccl_mediana": ccl, "fuente_ars": b["fuente"], "hora": info.get("hora")})
        return {str(ticker).upper(): d}
    except Exception:  # noqa: BLE001
        return {str(ticker).upper(): {}}


# ---------------------------------------------------------------------------
# HELPERS DE VISUALIZACIÓN
# ---------------------------------------------------------------------------

def format_metric(val: float | None, decimals: int = 1, suffix: str = "") -> str:
    """Formatea una métrica para mostrar en tabla."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if suffix == "%":
        return f"{val * 100:.1f}%"
    return f"{val:.{decimals}f}{suffix}"


PAISES_ES = {
    "United States": "Estados Unidos", "United Kingdom": "Reino Unido", "Brazil": "Brasil",
    "Japan": "Japón", "India": "India", "Ireland": "Irlanda", "Canada": "Canadá",
    "Spain": "España", "Netherlands": "Países Bajos", "China": "China", "Germany": "Alemania",
    "Australia": "Australia", "Uruguay": "Uruguay", "Italy": "Italia", "Sweden": "Suecia",
    "Taiwan": "Taiwán", "France": "Francia", "Norway": "Noruega", "Switzerland": "Suiza",
    "Denmark": "Dinamarca", "Argentina": "Argentina", "Mexico": "México", "Chile": "Chile",
    "Colombia": "Colombia", "Peru": "Perú", "Israel": "Israel", "South Korea": "Corea del Sur",
    "Hong Kong": "Hong Kong", "Singapore": "Singapur", "Belgium": "Bélgica",
    "Finland": "Finlandia", "Luxembourg": "Luxemburgo", "South Africa": "Sudáfrica",
    "Bermuda": "Bermudas", "Cayman Islands": "Islas Caimán", "Panama": "Panamá",
    "Portugal": "Portugal", "Austria": "Austria", "Greece": "Grecia", "Turkey": "Turquía",
    "Russia": "Rusia", "Jersey": "Jersey", "Guernsey": "Guernsey", "Poland": "Polonia",
    "New Zealand": "Nueva Zelanda", "Indonesia": "Indonesia", "Malaysia": "Malasia",
    "Thailand": "Tailandia", "Vietnam": "Vietnam", "Philippines": "Filipinas",
}


def traducir_pais(pais):
    """Nombre del país en castellano (None/NaN se respetan para que se muestre '—')."""
    if not isinstance(pais, str) or not pais:
        return None
    return PAISES_ES.get(pais, pais)


def _num_valido(x) -> bool:
    """True si x es un numero (no None ni NaN)."""
    try:
        return x is not None and not pd.isna(x)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# FILTROS INLINE (reemplaza sidebar)
# ---------------------------------------------------------------------------

# v1.2.45: al abrir la pagina la tabla va ordenada por capitalizacion bursatil, de mayor a menor (antes: por Valoracion)
ORDEN_INICIAL = ("market_cap", False)
MIN_METRICAS = 1       # v1.2.49: ya no hay slider "Métricas mínimas"; queda fijo en 1 (como venia por defecto)
ORDENES_VALIDOS = ("nombre", "ticker", "sector_txt", "market_cap", "precio_actual", "fv_upside", "categoria", "score_total") + tuple(c["clave"] for c in _criterios.CRITERIOS)
MKTCAP_OPCIONES = {
    "Sin mínimo": 0,
    "≥ US$ 1B": 1e9,
    "≥ US$ 10B": 10e9,
    "≥ US$ 50B": 50e9,
    "≥ US$ 100B": 100e9,
    "≥ US$ 500B": 500e9,
}


def _normalizar(texto) -> str:
    """Minusculas, sin tildes ni signos: 'Nestlé S.A.' -> 'nestlesa'; 'BRK-B' -> 'brkb'. Para buscar sin que importe como se escriba."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii").casefold()
    return "".join(ch for ch in t if ch.isalnum())


def _alternar_variable(clave):
    """Pastilla de "Variables a ver en la tabla": la prende o la apaga (Empresa se ve siempre). Al apagarla, sus filtros dejan de aparecer y de valer."""
    v = _variables.POR_CLAVE.get(clave)
    if not v or v["fija"]:
        return
    sel = _variables.seleccion_valida(st.session_state.get("flt_vars"))
    sel = [c for c in sel if c != clave] if clave in sel else sel + [clave]
    st.session_state["flt_vars"] = _variables.seleccion_valida(sel)


def _reiniciar_variables():
    """Boton "Volver a las variables de siempre": deja las variables de siempre y borra los minimos y maximos escritos."""
    st.session_state["flt_vars"] = list(_variables.DEFECTO)
    for k in [k for k in list(st.session_state) if str(k).startswith(("crit_", "flt_precio_", "flt_score_"))]:
        st.session_state.pop(k, None)


def agregar_columnas_info(df: pd.DataFrame) -> pd.DataFrame:
    """Copia de `df` con el sector (el de siempre), la industria de cada empresa y el texto "Sector · Industria" para ordenar y buscar. Es solo
    informacion para mostrar y filtrar: no interviene en el puntaje ni en el Fair Value (que siguen usando la columna `sector`, el grupo del screener)."""
    df = df.copy()
    sec, ind = [], []
    for g, t in zip(df["sector"], df["ticker"]):
        s0, i0 = partes_sector(g)
        sec.append(s0 or "")
        ind.append(industria_de(t) or i0 or "")
    df["sector_macro"], df["industria"] = sec, ind
    df["sector_txt"] = [f"{a} · {b}" if b else a for a, b in zip(sec, ind)]
    return df


def render_filtros_inline(universe: dict, df: pd.DataFrame = None) -> dict:
    """
    Renderiza los filtros (dentro del recuadro "Filtro de empresas") y retorna dict con filtros activos.
    v1.2.49: arriba de todo va "Variables a ver en la tabla": una pastilla por cada variable (ui/variables.py). Las de siempre vienen elegidas
    (con tilde y en negrita); al elegir una aparecen abajo sus filtros (Sector e Industria, un minimo y un maximo de precio, etc.); una variable que no
    se elige no se ve en la tabla ni filtra. Ya no estan "Métricas mínimas", "Columnas de la tabla", "Agregar criterios" ni "Actualizar datos"
    (este ultimo paso al panel ?debug=1).
    """
    leyenda = leyenda_categorias()
    hay_gris = df is not None and not df.empty and "categoria" in df.columns and bool((df["categoria"] == "DATOS INSUFICIENTES").any())
    cats_disponibles = [l["nombre"] for l in leyenda if hay_gris or l["nombre"] != "DATOS INSUFICIENTES"]
    todos_sectores = sorted([x for x in df["sector_macro"].dropna().unique().tolist() if x], key=lambda x: x.lower()) if df is not None and not df.empty else []
    todas_industrias = sorted([x for x in df["industria"].dropna().unique().tolist() if x], key=lambda x: x.lower()) if df is not None and not df.empty else []
    paises_disponibles = []
    if df is not None and not df.empty and "pais" in df.columns:
        paises_disponibles = sorted(
            [p for p in df["pais"].dropna().unique().tolist() if p],
            key=lambda x: x.lower()
        )

    # v1.2.36: al volver desde la pagina de una empresa, los filtros y el orden vienen en la URL (?f=...)
    if not st.session_state.get("_estado_restaurado"):
        st.session_state["_estado_restaurado"] = True
        f = st.query_params.get("f")
        if f:
            vals = estado_url.valores(estado_url.decodificar(f), todos_sectores, cats_disponibles, paises_disponibles,
                                      list(MKTCAP_OPCIONES), ORDENES_VALIDOS, todas_industrias, {c["clave"]: c["nombre"] for c in _criterios.CRITERIOS},
                                      _variables.CLAVES)
            for k, v in vals.items():
                st.session_state[k] = v

    # --- Variables a ver en la tabla (v1.2.49): arriba de todo ---
    seleccion = _variables.seleccion_valida(st.session_state.get("flt_vars"))
    st.session_state["flt_vars"] = seleccion
    elegidas = set(seleccion)
    st.markdown('<div class="vars-t">Variables a ver en la tabla</div>', unsafe_allow_html=True)
    consulta = st.text_input("Buscar variables", key="flt_vars_q", placeholder="Buscá y elegí qué ver", label_visibility="collapsed")
    for i_g, (titulo_g, vars_g) in enumerate(_variables.agrupar(_variables.buscar(consulta))):
        st.markdown(f'<div class="vars-g">{html.escape(titulo_g)}</div>', unsafe_allow_html=True)
        with st.container(key="vars_chips" if i_g == 0 else ("vars_chips_mult" if i_g == 1 else "vars_chips_tec")):
            for v in vars_g:
                on = v["clave"] in elegidas
                st.button(("✓ " if on else "") + v["nombre"], key=f"{'varon' if on else 'varoff'}_{v['clave']}", help=f"**{v['nombre']}.** {v['ayuda']}",
                          on_click=_alternar_variable, args=(v["clave"],))
    if set(seleccion) != set(_variables.DEFECTO):
        st.button("Volver a las variables de siempre", key="vars_reiniciar", type="tertiary", on_click=_reiniciar_variables)

    # --- Filtros de cada variable elegida (aparecen al elegirla; en dos columnas) ---
    sectores_sel, industrias_sel, paises_sel, cats_sel = [], [], [], []
    mktcap_label = "Sin mínimo"
    precio_lim, puntaje_lim = (None, None), (None, None)
    criterios = {}
    extras = _variables.extras_de(seleccion)
    pares = st.columns(4)      # v1.5.14: el filtro se despliega casi a todo el ancho: 4 columnas de recuadros (en pantallas más angostas se acomodan solas)
    turno = [0]

    def caja(clave, titulo, unidad=""):
        """Recuadro de los filtros de una variable, en la columna que toca (de izquierda a derecha)."""
        col = pares[turno[0] % 4]
        turno[0] += 1
        with col:
            c = st.container(border=True, key=f"fb_{clave}")
        with c:
            u = f" <span>({html.escape(unidad)})</span>" if unidad else ""
            st.markdown(f'<div class="crit-t">{html.escape(titulo)}{u}</div>', unsafe_allow_html=True)
        return c

    def minmax(clave, paso, ph=("Mínimo", "Máximo")):
        c1, c2 = st.columns(2)
        mn = c1.number_input(ph[0], value=None, step=float(paso), format="%g", key=f"{clave}_min", placeholder=ph[0], label_visibility="collapsed")
        mx = c2.number_input(ph[1], value=None, step=float(paso), format="%g", key=f"{clave}_max", placeholder=ph[1], label_visibility="collapsed")
        return mn, mx

    if "nombre" in elegidas:
        with caja("nombre", "País"):
            paises_sel = st.multiselect("País", paises_disponibles, placeholder="Todos los países", key="flt_pais", label_visibility="collapsed")
    if "sector_txt" in elegidas:
        with caja("sector_txt", "Sector e Industria"):
            sectores_sel = st.multiselect("Sector", todos_sectores, placeholder="Todos los sectores", key="flt_sector", label_visibility="collapsed")
            industrias_sel = st.multiselect("Industria", todas_industrias, placeholder="Todas las industrias", key="flt_industria", label_visibility="collapsed")
    if "precio_actual" in elegidas:
        with caja("precio_actual", "Precio", "US$"):
            precio_lim = minmax("flt_precio", 10)
    if "market_cap" in elegidas:
        with caja("market_cap", "Capitalización bursátil mínima"):
            mktcap_label = st.selectbox("Capitalización bursátil mínima", list(MKTCAP_OPCIONES.keys()), key="flt_mkt", label_visibility="collapsed")
    if "fv_upside" in elegidas:
        with caja("fv_upside", "Valoración"):
            cats_sel = st.multiselect("Valoración", cats_disponibles, format_func=lambda c: _mayusculas(nombre_corto(c)),
                                      placeholder="Todas las valoraciones", key="flt_valoracion", label_visibility="collapsed")
    if "score_total" in elegidas:
        with caja("score_total", "Puntaje de calidad", "0 a 100"):
            puntaje_lim = minmax("flt_score", 5)
    for c in extras:
        k = c["clave"]
        with caja(f"crit_{k}", c["nombre"], c["unidad"] if c["unidad"] == "%" else ("0 a 100" if c["unidad"] == "pts" else "veces")):
            criterios[k] = minmax(f"crit_{k}", c["paso"])
    cats_nombres = list(cats_sel) or list(cats_disponibles)

    visibles = _variables.visibles_de(seleccion)

    # Texto con los filtros y el orden: viaja en el link de cada empresa para poder volver a la tabla tal cual estaba
    busqueda = st.session_state.get("flt_busqueda", "") or ""
    estado = estado_url.codificar(sectores_sel, todos_sectores, cats_nombres, cats_disponibles, paises_sel, mktcap_label,
                                  st.session_state.get("sort_col", ORDEN_INICIAL[0]), st.session_state.get("sort_asc", ORDEN_INICIAL[1]),
                                  busqueda, industrias_sel, todas_industrias, criterios, seleccion, precio_lim, puntaje_lim)
    return {
        "estado_url": estado,
        "sectores": list(sectores_sel) or todos_sectores,
        "industrias": list(industrias_sel) or todas_industrias,
        "categorias": cats_nombres,
        "paises": paises_sel,
        "mktcap_minimo": MKTCAP_OPCIONES[mktcap_label],
        "min_metricas": MIN_METRICAS,
        "precio": precio_lim,
        "puntaje": puntaje_lim,
        "criterios": criterios,
        "extras": extras,
        "columnas": visibles,
        "sort_col": st.session_state.get("sort_col", ORDEN_INICIAL[0]),
        "sort_asc": st.session_state.get("sort_asc", ORDEN_INICIAL[1]),
    }


# v1.2.60: el buscador tambien se dibuja en paginas que no cargan la hoja de estilos de la tabla (ETFs, Quienes somos): se toman sus reglas de ahi
CSS_BUSQUEDA = "\n".join(l for l in CSS_VISUAL.splitlines() if l.startswith(".st-key-buscador"))

CSS_PILLS = "\n".join(l for l in CSS_VISUAL.splitlines() if l.startswith('[data-testid="stButtonGroup"]'))


def render_filtro_etfs(etfs) -> list:
    """Adentro de "Filtro de ETFs" (v1.2.64): las categorias, para quedarse con las que interesan (ninguna elegida = todas). Devuelve las elegidas."""
    from data import etfs as _etfs
    st.markdown(f"<style>{CSS_PILLS}</style>" + '<div class="flt-t">Categoría</div>', unsafe_allow_html=True)
    try:
        cats = st.pills("Categoría", _etfs.categorias(etfs), selection_mode="multi", key="etf_cats", label_visibility="collapsed") or []
    except Exception:  # noqa: BLE001
        cats = []
    # v1.2.72: parametros tecnicos (minimo y/o maximo). Los valores quedan en session_state (etf_tec_<clave>_min / _max) y los usa render_tabla_etfs.
    datos, fecha_t = _tecnicos_guardados()
    st.markdown('<div class="flt-t" style="margin-top:.8rem">Parámetros técnicos <span style="font-weight:400;color:#64748b">(informativos; no son señales de compra ni de venta)</span></div>', unsafe_allow_html=True)
    if not datos:
        st.caption("Todavía no hay datos técnicos cargados: se completan al correr bajar_tecnicos.bat.")
        return cats
    cols = st.columns(2)
    for i, c in enumerate(_criterios.TECNICOS):
        with cols[i % 2]:
            u = "0 a 100" if c["unidad"] == "pts" else ("%" if c["unidad"] == "%" else "veces")
            st.markdown(f'<div class="crit-t">{html.escape(c["nombre"])} <span>({u})</span></div>', unsafe_allow_html=True)
            a, b = st.columns(2)
            a.number_input("Mínimo", value=None, step=float(c["paso"]), format="%g", key=f"etf_tec_{c['clave']}_min", placeholder="Mínimo", label_visibility="collapsed", help=c["ayuda"])
            b.number_input("Máximo", value=None, step=float(c["paso"]), format="%g", key=f"etf_tec_{c['clave']}_max", placeholder="Máximo", label_visibility="collapsed", help=c["ayuda"])
    if fecha_t:
        st.caption(f"Datos técnicos al {fecha_t}.")
    return cats


def _filtrar_etfs_tecnicos(etfs):
    """Deja los ETFs que cumplen los minimos y maximos de los parametros tecnicos elegidos (los que no tienen el dato quedan afuera si hay un limite)."""
    datos, _ = _tecnicos_guardados()
    activos = {}
    for c in _criterios.TECNICOS:
        mn, mx = st.session_state.get(f"etf_tec_{c['clave']}_min"), st.session_state.get(f"etf_tec_{c['clave']}_max")
        if mn is not None or mx is not None:
            activos[c["clave"]] = (c, mn, mx)
    if not activos:
        return etfs
    out = []
    for e in etfs:
        d = datos.get(str(e["ticker"]).upper()) or {}
        ok = True
        for _, (c, mn, mx) in activos.items():
            v = d.get(c["clave"][4:])
            v = None if v is None else v * c["escala"]
            if v is None or (mn is not None and v < mn) or (mx is not None and v > mx):
                ok = False
                break
        if ok:
            out.append(e)
    return out


def _cambiar_orden_etfs():
    """Al elegir un orden en el selector del celular se guarda como si se hubiera tocado el título de la tabla."""
    from ui import etfs as _ui_etfs
    eleg = st.session_state.get("etf_orden_movil")
    for texto, col, asc in _ui_etfs.opciones_orden():
        if texto == eleg:
            st.session_state["etf_sort_col"], st.session_state["etf_sort_asc"] = col, asc
            return


def _boton_excel_etfs(mostrados, guardados, precios, fecha):
    """Botón "Descargar tabla en Excel" de la tabla de ETFs (v1.2.67): los ETFs que se ven, en el orden elegido. Si algo falla, no se muestra."""
    from ui.exportar import excel_etfs_bytes
    try:
        datos = excel_etfs_bytes(mostrados, guardados, precios, fecha, texto_aviso_legal(), APP_VERSION)
    except Exception:  # noqa: BLE001
        return
    dia = (fecha or datetime.now().strftime("%d/%m/%Y")).replace("/", "-")
    args = dict(data=datos, file_name=f"todocedears_etfs_{dia}.xlsx", key="descarga_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore",
                help="Baja un archivo .xlsx con la tabla tal como la ves ahora: los ETFs que quedaron con tu filtro y en el orden elegido. Es información, no una recomendación.")
    st.download_button("Descargar tabla en Excel", **args)     # v1.5.8: se ve solo el ícono (flecha + logo de Excel); el texto queda para lectores de pantalla


def render_tabla_etfs(etfs, sel):
    """Tabla de ETFs (v1.2.64; v1.2.67 igual a la de Empresas): títulos centrados y ordenables, leyenda y botón de Excel arriba. Columnas: ETF (nombre y
    ticker, con link a su página), Precio, Descripción, Categoría, Gestor, AUM y Comisión."""
    from data import etfs as _etfs
    from ui import etfs as _ui_etfs
    if not etfs:
        st.markdown(f"<style>{css_fuente()}{css_condensada()}{CSS_QUIENES}</style>"
                    '<div class="qs" style="text-align:center"><h1 style="margin-bottom:10px">ETFs</h1>'
                    '<p>Estamos preparando la tabla de ETFs. Muy pronto la vas a poder ver acá, igual que la de empresas.</p></div>', unsafe_allow_html=True)
        return
    guardados, fecha_g = _etfs_guardados()
    _items_e = tuple((e["ticker"], _etfs.simbolo_yahoo(e)) for e in etfs)
    precios = _precios_etfs(_items_e) if PRECIOS_VIVOS else {}
    variaciones = _var_etfs(_items_e) if PRECIOS_VIVOS else {}
    sort_col = st.session_state.get("etf_sort_col")
    sort_asc = bool(st.session_state.get("etf_sort_asc", True))
    mostrados = _ui_etfs.ordenar(_filtrar_etfs_tecnicos(_etfs.filtrar(etfs, "", sel)), guardados, precios, sort_col, sort_asc)
    _css_ay = css_ayudas([(f"e_{c}", _ui_etfs.TIPS.get(t) or "") for c, t, _w in _ui_etfs.COLUMNAS])
    st.markdown(f"<style>{_ui_etfs.CSS}{_ui_etfs.css_cabecera(sort_col, sort_asc)}{_css_ay}</style>" + _ui_etfs.encabezado_html(len(etfs), len(mostrados)), unsafe_allow_html=True)
    with st.container(key="fila_excel"):
        _fila_tabla("etfs")
        _boton_excel_etfs(mostrados, guardados, precios, fecha_g)
    # Celular: el selector reemplaza a los títulos
    opciones = _ui_etfs.opciones_orden()
    actual = next((t for t, c, a in opciones if c == sort_col and a == sort_asc), None)
    if actual:
        st.session_state["etf_orden_movil"] = actual
    else:
        st.session_state.pop("etf_orden_movil", None)
    with st.container(key="orden_movil_caja"):
        st.selectbox("Ordenar por", [t for t, _, _ in opciones], index=None, placeholder="Ordenar por…", key="etf_orden_movil", on_change=_cambiar_orden_etfs)
    cols = st.columns([w for _, _, w in _ui_etfs.COLUMNAS], gap="small")
    for contenedor, (clave, titulo, _) in zip(cols, _ui_etfs.COLUMNAS):
        if contenedor.button(titulo, key=f"tvh_e_{clave}", use_container_width=True):
            if sort_col == clave:
                st.session_state["etf_sort_asc"] = not sort_asc
            else:
                st.session_state["etf_sort_col"] = clave
                st.session_state["etf_sort_asc"] = clave in _ui_etfs.TEXTO or clave == "comision"
            st.rerun()
    st.markdown(_ui_etfs.tabla_html(mostrados, guardados, precios, variaciones), unsafe_allow_html=True)


def render_mapa(df: pd.DataFrame, texto_precios=None):
    """Mapa de calor (?pagina=mapa, v1.5.29): empresas (tamaño = capitalización, grupo = sector) o ETFs (tamaño = AUM, grupo = categoría), coloreados por la variación de hoy."""
    from ui import mapa_calor as _mc
    tipo = "etfs" if st.query_params.get("tipo") == "etfs" else "empresas"
    st.markdown(f"<style>{_mc.CSS}</style>", unsafe_allow_html=True)
    if tipo == "etfs":
        from data import etfs as _etfs
        etfs = _etfs_lista()
        guardados, _f = _etfs_guardados() if etfs else ({}, None)
        items_e = tuple((e["ticker"], _etfs.simbolo_yahoo(e)) for e in etfs)
        precios = _precios_etfs(items_e) if (PRECIOS_VIVOS and items_e) else {}
        var = _var_etfs(items_e) if (PRECIOS_VIVOS and items_e) else {}
        items = _mc.items_etfs(etfs, guardados, precios, var)
        titulo = "Mapa de Calor de ETFs"
        html_m = _mc.mapa_html(items, titulo, "etfs", hay_var=any(v is not None for v in var.values()), texto_precios=_sin_html(texto_precios),
                               nota_tam="El tamaño es el patrimonio que administra cada ETF (AUM), suavizado para que se vean también los más chicos.", sin_cabecera=True)
    else:
        items = _mc.items_empresas(df)
        titulo = "Mapa de Calor de empresas"
        html_m = _mc.mapa_html(items, titulo, "empresas", hay_var=any(i["var"] is not None for i in items), texto_precios=_sin_html(texto_precios),
                               nota_tam="El tamaño es la capitalización bursátil, suavizada para que se vean también las más chicas.", sin_cabecera=True)
    izq, der = _mc.cabecera_html(titulo, tipo)
    with st.container(key="fila_mapa"):      # v1.5.43: título + interruptor · buscador · leyenda en una sola fila
        st.markdown(izq, unsafe_allow_html=True)
        render_buscador()
        st.markdown(der, unsafe_allow_html=True)
    st.markdown(html_m, unsafe_allow_html=True)


def _sin_html(t):
    """'Datos al <b>05/11/2026</b> (17:58)' -> '05/11/2026 (17:58)' para la nota del mapa."""
    if not t:
        return None
    import re as _re
    return _re.sub(r"<[^>]+>", "", str(t)).replace("Datos al", "").replace("Datos de hoy", "").strip() or None


def render_pagina_etf(df: pd.DataFrame, ticker_sel: str, fecha_datos=None):
    """Pagina de un ETF (?etf=TICKER, v1.2.64): lo mismo que la de una empresa pero con las solapas Resumen, Grafico y Rendimiento y Noticias."""
    from data import etfs as _etfs
    from ui import etfs as _ui_etfs
    e = _etfs.por_ticker(_etfs_lista(), ticker_sel)
    if not e:
        st.warning("No encontré ese ETF. Volvé a la tabla y elegí otro.")
        return
    cargando = st.empty()
    cargando.markdown('<div class="fch-carga"><span class="fch-giro"></span>Aguarde mientras se cargan los datos del ETF…</div>', unsafe_allow_html=True)
    tk = e["ticker"]
    extra = _extras_etf(e)
    d = extra.get("datos") or {}
    precio = (_precios_etfs(((tk, extra["simbolo"]),)) if PRECIOS_VIVOS else {}).get(tk) or d.get("precio")
    var = (_var_etfs(((tk, extra["simbolo"]),)) if PRECIOS_VIVOS else {}).get(tk)
    cedear = _cedear_etf(df, e, precio)
    st.markdown(f"<style>{_ui_etfs.CSS}</style>" + _ui_etfs.encabezado_etf(e, d, precio, cedear, var), unsafe_allow_html=True)
    # v1.5.52 (Guille): la solapa se llama «Análisis Fundamental», como en las empresas, y está solo en los ETFs que tienen su informe
    from ui import etf_informe as _ei
    _con_af = _ei.informe(tk) is not None
    _claves = ["resumen"] + (["analisis"] if _con_af else []) + ["composicion", "grafico", "noticias"]
    _nombres = {"resumen": "Resumen", "analisis": "Análisis Fundamental", "composicion": "Composición", "grafico": "Análisis Técnico y Rendimiento", "noticias": "Noticias"}
    st.markdown("<style>" + _tv.css_ayuda_solapas("sol_etf", [_ui_etfs.INTROS.get(k) for k in _claves]) + "</style>", unsafe_allow_html=True)
    with st.container(key="sol_etf"):
        _solapas = dict(zip(_claves, st.tabs([_nombres[k] for k in _claves])))
    t_res, t_com, t_gra, t_not = _solapas["resumen"], _solapas["composicion"], _solapas["grafico"], _solapas["noticias"]
    t_ana = _solapas.get("analisis")
    with t_res:
        st.markdown(_ui_etfs.con_intro("resumen", _ui_etfs.tab_resumen(e, d, precio, cedear)), unsafe_allow_html=True)
        arch = extra.get("archivo")
        if arch:
            st.caption(f"Algunos datos son de Yahoo guardados el {arch.get('fecha') or 's/d'} (Yahoo no respondió en este momento).")
    if t_ana is not None:
        with t_ana:
            _render_analisis_etf(tk)
    with t_com:
        st.markdown(_ui_etfs.con_intro("composicion", _ui_etfs.tab_composicion(e, d, universo={str(t).upper() for t in df["ticker"]})), unsafe_allow_html=True)
    with t_gra:
        st.markdown(_ui_etfs.con_intro("grafico", _ui_etfs.tab_grafico_etf(extra.get("historial"))), unsafe_allow_html=True)
        _render_grafico(extra["simbolo"], extra.get("historial"), {})
        st.markdown(_tecnico.tab_tecnico_html(extra.get("historial")), unsafe_allow_html=True)
    with t_not:
        st.markdown(_ui_etfs.con_intro("noticias", _ui_etfs.tab_noticias_etf(extra["simbolo"], d.get("noticias"))), unsafe_allow_html=True)
    cargando.empty()


def _render_analisis_etf(tk):
    """v1.5.50: solapa «Análisis del ETF» (data/analisis_etf.json, ui/etf_informe.py): fecha y botón del PDF ya armado arriba, el informe abajo."""
    from ui import etf_informe as _ei
    inf = _ei.informe(tk)
    if not inf:
        st.markdown(_ui_etfs_intro("analisis", '<p style="text-align:justify">El análisis de este ETF todavía no está escrito: lo estamos preparando. '
                                   'Mientras tanto, en las otras solapas está qué tiene adentro, cuánto cuesta y cómo le fue.</p>'), unsafe_allow_html=True)
        return
    ruta = _ei.ruta_pdf(tk, inf)
    try:
        fila = st.container(horizontal=True, vertical_alignment="center", gap="small")
    except TypeError:
        fila = st.container()
    with fila:
        st.markdown(f'<span style="font-size:.85rem;color:#64748b;white-space:nowrap">Escrito el {html.escape(str(inf.get("fecha") or ""))}</span>', unsafe_allow_html=True)
        if ruta:
            args = dict(data=open(ruta, "rb").read(), file_name=f"analisis_etf_{tk}_{_ei.fecha_iso(inf.get('fecha'))}.pdf", mime="application/pdf",
                        key=f"pdf_etf_{tk}", help="Baja este análisis en PDF. Es información con fines educativos, no una recomendación.")
            try:
                st.download_button("Descargar en PDF", icon=":material/picture_as_pdf:", type="tertiary", on_click="ignore", **args)
            except TypeError:
                st.download_button("Descargar en PDF", **args)
    st.markdown(_ui_etfs_intro("analisis", _ei.app_html(tk, inf)), unsafe_allow_html=True)


def _ui_etfs_intro(clave, cuerpo):
    from ui import etfs as _ui_etfs
    return _ui_etfs.con_intro(clave, cuerpo)


def _ir_a_tabla(tabla):
    """Botones "Empresas" / "Exchange Traded Funds (ETFs)" de la franja (v1.2.60): cambian de tabla dentro de la misma sesion (cambian la URL, pero la pagina no se recarga)."""
    st.query_params.clear()
    st.session_state["entro"] = True       # v1.5.7: ya pasó la pantalla de inicio
    if tabla == "etfs":
        st.query_params["tabla"] = "etfs"
    elif tabla == "cartera":
        st.query_params["pagina"] = "cartera"


def render_nav_tablas(contexto="empresas"):
    """v1.2.83: al lado del nombre va el boton de la OTRA tabla: en Empresas, "Exchange Traded Funds (ETFs)"; en ETFs, "Empresas". En las demas pantallas (cartera, Quiénes somos...) van los dos."""
    botones = (("emp", "Empresas"), ("etfs", "Exchange Traded Funds (ETFs)"))
    if contexto == "empresas":
        botones = botones[1:]
    elif contexto == "etfs":
        botones = botones[:1]
    with st.container(key="nav_tablas"):
        for clave, texto in botones:
            args = dict(key=f"nav_{clave}", on_click=_ir_a_tabla, args=({"etfs": "etfs"}.get(clave, "empresas"),))
            try:
                st.button(texto, type="tertiary", **args)
            except TypeError:       # Streamlit viejo, sin type="tertiary"
                st.button(texto, **args)


def _switch_tablas(activa):
    """v1.5.10 (opción B de Guille): interruptor «Empresas | ETFs» arriba a la izquierda de la tabla, en la franja libre entre la barra de mercados y los títulos (el Excel va a la
    derecha, en la misma franja). La tabla en la que estás va en verde. Mismos botones y misma función que antes (`_ir_a_tabla`): no recarga la página."""
    with st.container(key="sw_tablas"):
        for clave, texto in (("emp", "Empresas"), ("etfs", "ETFs")):
            esta = (clave == "etfs") == (activa == "etfs")
            args = dict(key=f"sw_{clave}", on_click=_ir_a_tabla, args=({"etfs": "etfs"}.get(clave, "empresas"),), type="primary" if esta else "secondary")
            try:
                st.button(texto, **args)
            except TypeError:       # Streamlit viejo, sin type=
                args.pop("type")
                st.button(texto, **args)


_ICONO_FILTRO = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1e3a5f" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 5h18l-7 8v6l-4 2v-8z"/></svg>')
_ICONO_CHEV = ('<svg class="fl-c" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#1e3a5f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>')


def _fila_tabla(activa):
    """v1.5.14 (maqueta aprobada por Guille): la fila de arriba de la tabla, de izquierda a derecha: interruptor Empresas | ETFs, buscador (lupita) y botón «Filtro de Empresas / ETFs»,
    que despliega el filtro (radio escondido bn-filtro, el panel es fly_filtro); el Excel va a la derecha (lo agrega quien llama)."""
    _switch_tablas(activa)
    render_buscador()
    with st.container(key="btn_filtro"):
        st.markdown(f'<label for="bn-filtro" class="fl-btn" role="button" tabindex="0">{_ICONO_FILTRO}<span>{"Filtro de ETFs" if activa == "etfs" else "Filtro de Empresas"}</span>{_ICONO_CHEV}</label>',
                    unsafe_allow_html=True)


def render_menu_estatico(caja, home=False, filtro="Filtro de Empresas"):
    """Menu lateral (v1.2.84): la cabecera y la lista de títulos (siempre la misma, se arma al toque) y, aparte, los paneles que se abren hacia el centro y son solo HTML
    (Nuestras Redes, Contactános, Abrí una cuenta, Comentarios). Los paneles con widgets (Filtro, Noticias, Calendario Financiero) se arman en main() cuando hay datos."""
    with caja:
        st.markdown(menu_cabecera_html() + menu_lista_html(home, filtro=filtro, version=APP_VERSION), unsafe_allow_html=True)
    st.markdown(menu_flyouts_html() + quienes_panel_html(), unsafe_allow_html=True)


def poner_esc():
    """La tecla ESC cierra el menú y sus paneles (v1.2.84). Usa st.html con JavaScript (Streamlit nuevo) o, si no existe, un componente de 0 px de alto."""
    try:
        from ui.tema import SCRIPT_TEMA
        st.html(f"<script>{SCRIPT_ESC}{SCRIPT_TEMA}{SCRIPT_ATRAS}</script>", unsafe_allow_javascript=True)
    except Exception:  # noqa: BLE001
        try:
            import streamlit.components.v1 as _cmp
            _cmp.html("<script>(function(){var d=window.parent.document;" + SCRIPT_ESC.replace("document.", "d.").replace("window.__mcEsc", "window.parent.__mcEsc") + "})();"
                      + "(function(){var w=window.parent;" + SCRIPT_ATRAS.replace("window.__mcAtras", "w.__mcAtras").replace("document.", "w.document.").replace("location.", "w.location.").replace("history.", "w.history.") + "})();</script>", height=0)      # (sin modo oscuro en este camino)
        except Exception:  # noqa: BLE001
            pass


@st.cache_data(ttl=3600, show_spinner=False)
def _opciones_busqueda(etfs_firma: tuple) -> list:
    """[(texto, tipo, ticker)] de todas las empresas y ETFs para el buscador con sugerencias (v1.2.64). v1.2.85: el buscador filtra "por el comienzo": cada empresa figura
    dos veces, "TICKER · Nombre" (primero, ordenadas por largo de ticker) y "Nombre · TICKER" (después, de la A a la Z), así al escribir una letra quedan solo las que
    EMPIEZAN con esa letra (ya sea por el ticker o por el nombre) y cada letra nueva achica la lista."""
    items = []
    try:
        df_c, _ = load_cache(ignorar_ttl=True)
        if df_c is not None and not df_c.empty:
            for t, n in zip(df_c["ticker"], df_c["nombre"] if "nombre" in df_c.columns else df_c["ticker"]):
                n = str(n or "").strip()
                items.append((str(t), n if n and n != t else "", "empresa"))
    except Exception:  # noqa: BLE001
        pass
    for t, n in etfs_firma:
        n = str(n or "").strip()
        items.append((str(t), n if n and n != t else "", "etf"))
    por_ticker, por_nombre, vistos = [], [], set()
    sufijo = {"empresa": "", "etf": " · ETF"}
    for t, n, tipo in sorted(items, key=lambda x: (len(x[0]), x[0], x[2])):
        txt = (f"{t} · {n}" if n else t) + sufijo[tipo]
        if txt not in vistos:
            vistos.add(txt)
            por_ticker.append((txt, tipo, t))
    for t, n, tipo in sorted(items, key=lambda x: (x[1].lower() or x[0].lower(), x[0])):
        if not n:
            continue
        txt = f"{n} · {t}" + sufijo[tipo]
        if txt not in vistos:
            vistos.add(txt)
            por_nombre.append((txt, tipo, t))
    # v1.5.15: el ticker local de las brasileñas con ADR (PETR3, VALE3…) también encuentra la ficha de la empresa (una sola ficha por empresa)
    from data import gemelos as _gem
    presentes = {t for t, _, _ in items}
    nombres = {t: n for t, n, _ in items}
    for adr, (loc, _m) in _gem.GEMELOS.items():
        if adr in presentes:
            n = nombres.get(adr, "")
            por_ticker.append((f"{loc} · {n}" if n else loc, "empresa", adr))
    return por_ticker + por_nombre


def _ir_a_seleccion():
    """Al elegir una sugerencia del buscador se abre la pagina de esa empresa o de ese ETF, desde cualquier pantalla (v1.2.64)."""
    destino = (st.session_state.get("_destinos_busqueda") or {}).get(st.session_state.get("flt_busqueda"))
    st.session_state["flt_busqueda"] = None
    if not destino:
        return
    tipo, t = destino
    st.session_state["entro"] = True
    st.query_params.clear()
    st.query_params["etf" if tipo == "etf" else "empresa"] = t


def render_fila_volver(es_etf: bool) -> None:
    """v1.5.32: en las fichas de empresa y de ETF, «← Volver…» y el buscador van en UNA fila (antes el buscador flotaba a una altura fija y, según la pantalla,
    quedaba encimado). Mismo lugar que antes: a la izquierda el «Volver» y el buscador a su derecha; en el celular, uno debajo del otro."""
    with st.container(key="fila_volver"):
        # v1.5.47 (Guille): «← Atrás · ⌂ Inicio» (antes «← Volver a Empresas / ETFs»); «Atrás» sin página anterior va a la tabla correspondiente
        st.markdown(f'<div class="emp-vol">{nav_html("?tabla=etfs" if es_etf else "?inicio=0")}</div>', unsafe_allow_html=True)
        render_buscador()


def render_buscador() -> str:
    """Buscador con sugerencias (v1.2.64): al escribir un ticker o parte del nombre (de una empresa o de un ETF) aparecen las coincidencias; al elegir una se
    abre su pagina. Funciona igual en todas las pantallas. Devuelve siempre '' (ya no filtra la tabla)."""
    etfs = _etfs_lista()
    opciones = _opciones_busqueda(tuple((e["ticker"], e.get("nombre") or e["ticker"]) for e in etfs))
    st.session_state["_destinos_busqueda"] = {o[0]: (o[1], o[2]) for o in opciones}
    with st.container(key="buscador"):
        try:
            args = dict(index=None, key="flt_busqueda", placeholder="Empresa o ETF", label_visibility="collapsed", on_change=_ir_a_seleccion)
            try:
                # v1.2.85: "prefix" = solo quedan las opciones que EMPIEZAN con lo escrito (el ticker o el nombre); cada letra nueva achica la lista
                st.selectbox("Buscar empresa, ETF o ticker", [o[0] for o in opciones], filter_mode="prefix", **args)
            except TypeError:       # Streamlit viejo, sin filter_mode
                st.selectbox("Buscar empresa, ETF o ticker", [o[0] for o in opciones], **args)
        except Exception:  # noqa: BLE001
            pass
    return ""


# ---------------------------------------------------------------------------
# TABLA PRINCIPAL
# ---------------------------------------------------------------------------

def ordenes_movil(extras=(), visibles=None):
    """Opciones del selector "Ordenar por" (solo se ve en el celular, donde los titulos de la tabla no entran): (texto, columna, ascendente).
    Es el mismo orden que dan los titulos de la tabla en la computadora. `visibles` (v1.2.48): solo las columnas que se ven (None = todas)."""
    o = [
        ("Capitalización bursátil: de mayor a menor", "market_cap", False), ("Capitalización bursátil: de menor a mayor", "market_cap", True),
        ("Valoración: de más barata a más cara", "fv_upside", False), ("Valoración: de más cara a más barata", "fv_upside", True),
        ("Puntaje de calidad: de mayor a menor", "score_total", False), ("Puntaje de calidad: de menor a mayor", "score_total", True),
        ("Empresa: de la A a la Z", "nombre", True), ("Empresa: de la Z a la A", "nombre", False),
        ("Sector e Industria: de la A a la Z", "sector_txt", True), ("Sector e Industria: de la Z a la A", "sector_txt", False),
        ("Precio: de mayor a menor", "precio_actual", False), ("Precio: de menor a mayor", "precio_actual", True),
    ]
    o = [x for x in o if x[1] == "nombre" or visibles is None or x[1] in visibles]
    for c in extras:
        o += [(f"{c['nombre']}: de mayor a menor", c["clave"], False), (f"{c['nombre']}: de menor a mayor", c["clave"], True)]
    return o


def _cambiar_orden_movil():
    """Al elegir un orden en el selector del celular se guarda como si se hubiera tocado el titulo de la tabla."""
    eleg = st.session_state.get("orden_movil")
    seleccion = st.session_state.get("flt_vars")
    extras = _variables.extras_de(seleccion)
    visibles = _variables.visibles_de(seleccion)
    for texto, col, asc in ordenes_movil(extras, visibles):
        if texto == eleg:
            st.session_state["sort_col"], st.session_state["sort_asc"] = col, asc
            return


def render_tabla_visual(df_show: pd.DataFrame, estado=None, fecha=None, extras=(), visibles=None):
    """Tabla visual: titulos ordenables (botones, con la explicacion al pasar el mouse) y filas en una sola pieza de HTML con la misma grilla."""
    sort_col = st.session_state.get("sort_col", ORDEN_INICIAL[0])
    sort_asc = st.session_state.get("sort_asc", ORDEN_INICIAL[1])
    _tit = [(clave, etiqueta) for clave, etiqueta, _ in columnas_base(visibles)] + [(c["clave"], c["nombre"]) for c in extras]
    _css_ay = css_ayudas([(clave, ayuda_texto(clave, fecha)) for clave, _e in _tit])
    st.markdown(f"<style>{css_encabezado(sort_col, len(extras), visibles, bool(sort_asc))}{_css_ay}</style>", unsafe_allow_html=True)

    # Celular: el selector reemplaza a los titulos (la hoja de estilos esconde uno u otro segun el ancho de la pantalla)
    opciones = ordenes_movil(extras, visibles)
    sort_col = _orden_efectivo(sort_col, extras, visibles)
    for texto, col, asc in opciones:
        if col == sort_col and asc == bool(sort_asc):
            st.session_state["orden_movil"] = texto
            break
    else:
        st.session_state.pop("orden_movil", None)
    with st.container(key="orden_movil_caja"):
        st.selectbox("Ordenar por", [t for t, _, _ in opciones], key="orden_movil", on_change=_cambiar_orden_movil)

    cols = st.columns(anchos_tabla(len(extras), visibles), gap="small")
    titulos = [(clave, "Cap. Bursátil" if clave == "market_cap" else etiqueta) for clave, etiqueta, _ in columnas_base(visibles)] + [(c["clave"], c["nombre"].split(" (")[0]) for c in extras]
    for contenedor, (clave, etiqueta) in zip(cols, titulos):
        activo = sort_col == clave
        if contenedor.button(etiqueta, key=f"tvh_{clave}", use_container_width=True):
            if activo:
                st.session_state["sort_asc"] = not sort_asc
            else:
                st.session_state["sort_col"] = clave
                st.session_state["sort_asc"] = (clave in ("nombre", "ticker", "sector_txt"))
            st.rerun()
    st.markdown(html_tabla_visual(df_show, estado, extras, visibles), unsafe_allow_html=True)


def _boton_excel(df_show, fecha, aviso, extras=(), visibles=None):
    """Boton "Descargar tabla en Excel" (v1.2.49; arriba de la tabla, a la derecha): las empresas y columnas que se ven, con los filtros y el
    orden elegidos. Si algo falla, no se muestra."""
    if "callable" in (st.download_button.__doc__ or ""):
        # v1.5.22: Streamlit nuevo: el Excel se arma RECIEN cuando se toca el botón (antes se armaba en cada recarga de la página: ~0,15 s de servidor
        # que nadie usaba casi nunca). Con un Streamlit viejo se sigue armando antes, como siempre.
        datos = lambda: excel_bytes(df_show, fecha, aviso, APP_VERSION, extras, visibles)      # noqa: E731
    else:
        try:
            datos = excel_bytes(df_show, fecha, aviso, APP_VERSION, extras, visibles)
        except Exception:  # noqa: BLE001
            return
    dia = (fecha or datetime.now().strftime("%d/%m/%Y")).replace("/", "-")
    args = dict(data=datos, file_name=f"todocedears_{dia}.xlsx", key="descarga_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore",
                help="Baja un archivo .xlsx con la tabla tal como la ves ahora: las empresas que quedaron con tus filtros, en el orden elegido y con las variables que tenés a la vista. Es información, no una recomendación.")
    st.download_button("Descargar tabla en Excel", **args)     # v1.5.8: se ve solo el ícono (flecha + logo de Excel); el texto queda para lectores de pantalla


def _orden_efectivo(sort_col, extras=(), visibles=None):
    """Columna por la que se ordena de verdad (v1.2.48): si se sacó de la tabla la columna elegida, vuelve al orden de arranque (capitalización)."""
    if sort_col in ("nombre", "ticker", "categoria", "sector") or visibles is None:
        return sort_col
    base = {k for k, _, _ in COLUMNAS_BASE}
    if sort_col in base and sort_col not in visibles:
        return ORDEN_INICIAL[0]
    return sort_col


def filtrar_ordenar(df: pd.DataFrame, filtros: dict, busqueda: str = "") -> pd.DataFrame:
    """Aplica el buscador, los filtros y los criterios agregados, y ordena. Devuelve las empresas que se ven, en el orden de la tabla."""
    df_show = _criterios.agregar_columnas(df)

    # v1.2.51: si hay algo escrito en el buscador se busca en TODAS las empresas, aunque algun filtro (sector, categoria, metricas minimas...)
    # las deje afuera; antes una empresa filtrada "no aparecia" aunque existiera. Sin texto, se aplican los filtros de siempre.
    q = _normalizar(busqueda)
    if q:
        nombres = df_show["nombre"].map(_normalizar)
        tickers = df_show["ticker"].map(_normalizar)
        exacto = tickers == q
        if exacto.any():        # v1.2.51: si lo escrito es justo un ticker ("O", "T", "V"), se muestra esa empresa y no todas las que lo contienen
            df_show = df_show[exacto]
        else:
            df_show = df_show[nombres.str.contains(q, regex=False) | tickers.str.contains(q, regex=False)]
    else:
        # --- Aplicar filtros ---
        df_show = df_show[df_show["sector_macro"].isin(filtros["sectores"])]
        df_show = df_show[df_show["industria"].isin(filtros["industrias"]) | (df_show["industria"] == "")]
        df_show = df_show[
            (df_show["metricas_usadas"] >= filtros.get("min_metricas", MIN_METRICAS)) |
            (df_show["categoria"] == "DATOS INSUFICIENTES")
        ]
        df_show = df_show[df_show["categoria"].isin(filtros["categorias"])]
        if filtros["paises"]:
            df_show = df_show[df_show["pais"].isin(filtros["paises"])]
        if filtros["mktcap_minimo"] > 0:
            df_show = df_show[
                df_show["market_cap"].notna() &
                (df_show["market_cap"] >= filtros["mktcap_minimo"])
            ]
        # Precio y Puntaje de calidad (v1.2.49): minimo y/o maximo; una empresa sin dato queda afuera si hay algun limite
        for col, (mn, mx) in (("precio_actual", filtros.get("precio") or (None, None)), ("score_total", filtros.get("puntaje") or (None, None))):
            if mn is not None or mx is not None:
                v = pd.to_numeric(df_show[col], errors="coerce")
                m = v.notna()
                if mn is not None:
                    m &= v >= mn
                if mx is not None:
                    m &= v <= mx
                df_show = df_show[m]
        # Criterios agregados (minimo / maximo)
        df_show = _criterios.filtrar(df_show, filtros.get("criterios"))



    # --- Calcular columna de upside para ordenamiento ---
    def _fv_upside(row):
        fv = row.get("fair_value")
        p = row.get("precio_actual")
        if fv and p and p > 0:
            return (fv - p) / p
        return None

    df_show["fv_upside"] = df_show.apply(_fv_upside, axis=1) if len(df_show) else pd.Series(dtype=float)

    # --- Ordenamiento ---
    sort_col = st.session_state.get("sort_col", ORDEN_INICIAL[0])
    sort_asc = st.session_state.get("sort_asc", ORDEN_INICIAL[1])
    if sort_col not in ("nombre", "ticker", "categoria", "sector") and sort_col in {k for k, _, _ in COLUMNAS_BASE} and sort_col not in filtros.get("columnas", [k for k, _, _ in COLUMNAS_BASE]):
        sort_col, sort_asc = ORDEN_INICIAL      # la columna elegida se sacó de la tabla: orden de arranque
    if len(df_show) == 0:
        return df_show
    STR_COLS = {"nombre", "ticker", "pais", "sector_txt"}
    if sort_col == "sector":
        sort_col = "sector_txt"
    if sort_col in STR_COLS:
        df_show = df_show.sort_values(sort_col, ascending=sort_asc, na_position="last",
                                      key=lambda s: s.astype(str).str.lower())
    elif sort_col in ("score_total", "categoria"):
        df_show["_sort_v"] = df_show["score_total"].fillna(-1)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "fv_upside":
        # v1.2.41: la columna Valoracion ordena primero por categoria (de la mas barata a la mas cara, o al reves) y, adentro
        # de cada categoria, por cuanto mas (o menos) vale el Fair Value que el precio. Asi las categorias no se mezclan.
        # Sin tocar el orden (flecha ▼): primero las mas baratas y, adentro de cada categoria, la de mas diferencia. Con la flecha
        # ▲ se invierte todo. "Datos insuficientes" (sin categoria) va siempre al final.
        rango = {c: i for i, c in enumerate(CATEGORIAS_ORDEN)}
        df_show["_cat"] = df_show["categoria"].map(rango)
        df_show["_up"] = df_show["fv_upside"]
        df_show = df_show.sort_values(["_cat", "_up"], ascending=[not sort_asc, sort_asc], na_position="last",
                                      kind="mergesort").drop(columns=["_cat", "_up"])
    elif sort_col in _criterios.POR_CLAVE or sort_col in ("market_cap", "precio_actual", "posicion_52s", "dividend_yield_actual"):
        # Numericos: las empresas sin dato van siempre al final, sin importar el sentido del orden
        col = _criterios.POR_CLAVE[sort_col]["col"] if sort_col in _criterios.POR_CLAVE else sort_col
        df_show["_sort_v"] = pd.to_numeric(df_show[col], errors="coerce")
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc, na_position="last", kind="mergesort").drop(columns=["_sort_v"])
    elif sort_col == "metricas_usadas":
        # desempate por nombre para que el orden sea estable entre empresas con la misma cantidad
        df_show["_sort_v"] = pd.to_numeric(df_show["metricas_usadas"], errors="coerce").fillna(-1)
        df_show = df_show.sort_values(["_sort_v", "nombre"], ascending=[sort_asc, True]).drop(columns=["_sort_v"])
    else:
        df_show["_sort_v"] = df_show["score_total"].fillna(-1)
        df_show = df_show.sort_values("_sort_v", ascending=False).drop(columns=["_sort_v"])
    return df_show


def render_main_table(df: pd.DataFrame, filtros: dict, fecha=None, aviso="", lugar_excel=None, busqueda=""):
    """Renderiza la tabla principal (v1.2.47: columnas por defecto + los criterios agregados; el buscador va arriba, fuera del filtro)."""
    df_show = filtrar_ordenar(df, filtros, busqueda)
    if df_show.empty:
        st.warning("No hay empresas que coincidan con la búsqueda y los filtros seleccionados.")
        return
    extras = filtros.get("extras") or []
    visibles = filtros.get("columnas")
    # El boton de Excel esta arriba de la tabla, a la derecha (v1.2.49)
    if lugar_excel is not None:
        with lugar_excel:
            _boton_excel(df_show, fecha, aviso, extras, visibles)
    render_tabla_visual(df_show, filtros.get("estado_url"), fecha, extras, visibles)


# ---------------------------------------------------------------------------
# PANEL DE DETALLE POR EMPRESA
# ---------------------------------------------------------------------------

def _render_grafico(tk, pares, rd):
    """Solapa "Análisis Técnico y Rendimiento" (parte del gráfico): selector 1D, 5D, 1M, 3M, YTD, 1A, 5A y MAX y grafico interactivo (zoom con la rueda, arrastrar y ver el valor al pasar el
    mouse). 1D y 5D usan datos de cada 5 y 30 minutos; el resto, cierres diarios. Si Yahoo no responde, lo dice."""
    import altair as alt
    marcos = list(_hp.MARCOS)
    try:
        marco = st.segmented_control("Período", marcos, default="1A", key=f"marco_{tk}", label_visibility="collapsed")
    except Exception:  # noqa: BLE001
        marco = st.radio("Período", marcos, index=marcos.index("1A"), horizontal=True, key=f"marco_{tk}", label_visibility="collapsed")
    marco = marco or "1A"
    if marco in ("1D", "5D"):
        pts = _intradia(tk, marco)
        sufijo = "Cada 5 minutos" if marco == "1D" else "Cada 30 minutos"
    else:
        pts = _hp.recortar(pares, marco) if pares else None
        sufijo = "Cierre diario"
    if not pts or len(pts) < 2:
        st.markdown('<div class="fch"><div class="fch-t s12" style="--ac:#94a3b8"><div class="fch-sub" style="margin:0">Gráfico no disponible por ahora para este período (Yahoo no respondió o no hay datos).</div></div></div>', unsafe_allow_html=True)
        return
    d = pd.DataFrame(pts, columns=["Fecha", "Precio"])
    d["Fecha"] = pd.to_datetime(d["Fecha"])
    sube = d["Precio"].iloc[-1] >= d["Precio"].iloc[0]
    color = "#15803d" if sube else "#b91c1c"
    tit = "Fecha y hora" if marco in ("1D", "5D") else "Fecha"
    ch = (alt.Chart(d).mark_area(clip=True, line={"color": color, "strokeWidth": 2}, color=alt.Gradient(gradient="linear", stops=[alt.GradientStop(color=color, offset=0), alt.GradientStop(color="white", offset=1)], x1=1, x2=1, y1=0, y2=1), opacity=0.18)
          .encode(x=alt.X("Fecha:T", title=None), y=alt.Y("Precio:Q", scale=alt.Scale(domain=[float(d["Precio"].min()) * 0.99, float(d["Precio"].max()) * 1.01], zero=False, nice=False), title=None),
                  tooltip=[alt.Tooltip("Fecha:T", title=tit, format="%d/%m/%Y %H:%M" if marco in ("1D", "5D") else "%d/%m/%Y"), alt.Tooltip("Precio:Q", title="Precio (US$)", format=",.1f")])
          .properties(height=340).interactive())
    try:
        st.altair_chart(ch, width="stretch")
    except TypeError:
        st.altair_chart(ch, use_container_width=True)
    st.caption(f"{sufijo} · No es en tiempo real. Podés acercar con la rueda del mouse y arrastrar el gráfico.")


def _nota_archivo(extra, clave):
    """Si el dato no vino de Yahoo en vivo sino del archivo guardado (data/paquetes_yahoo.json), lo dice con la fecha."""
    arch = (extra or {}).get("archivo") or {}
    if clave in (arch.get("claves") or []):
        st.caption(f"Datos de Yahoo guardados el {arch.get('fecha') or 's/d'} (Yahoo no respondió en este momento).")


def render_pagina_empresa(df: pd.DataFrame, ticker_sel: str, fecha_datos=None):
    """Pagina de una empresa (se abre al tocar su nombre en la tabla: ?empresa=TICKER): resumen, barra del Fair Value y el desglose completo."""
    # v1.2.51: "Volver" lleva siempre al inicio (tabla sin filtros), igual que tocar el titulo. v1.5.32: el «Volver» y el buscador van juntos en una fila (ver render_fila_volver)
    # v1.2.54: aviso bien visible mientras se prepara la informacion de la empresa (se borra al terminar)
    cargando = st.empty()
    cargando.markdown('<div class="fch-carga"><span class="fch-giro"></span>Aguarde mientras se cargan los datos de la empresa…</div>', unsafe_allow_html=True)

    row = df[df["ticker"] == str(ticker_sel).upper()] if ticker_sel else df.iloc[0:0]
    if row.empty:
        cargando.empty()
        st.warning("No encontré esa empresa. Volvé a la tabla y elegí otra.")
        return None
    row = row.iloc[0]
    ticker_sel = row.get("ticker", ticker_sel)
    sector = row.get("sector", "")

    # v1.2.47: encabezado (logo, nombre, mercado, ticker, ADR, precio) y todos los datos en mosaicos (ui/ficha.py)
    ficha = (_fichas_datos() or {}).get(str(ticker_sel).upper()) or {}
    if not (ficha.get("descripcion_es") or ficha.get("descripcion_en")):
        with st.spinner("Aguarde mientras se cargan los datos..."):
            viva = _ficha_viva(str(ticker_sel).upper())
        if viva:
            ficha = {**viva, **ficha}      # lo que ya estaba en data/fichas.json manda; Yahoo en vivo completa lo que falta
    if ficha.get("descripcion_en") and not ficha.get("descripcion_es"):
        es = _descripcion_es(ficha["descripcion_en"])
        if es:
            ficha = {**ficha, "descripcion_es": es}
    cod = None if (ficha.get("mercado_cod") or ficha.get("mercado_nombre")) else _mercado_vivo(str(ticker_sel))
    tk = str(ticker_sel).upper()
    rd = row.to_dict()
    mercado, _adr = _fichas.mercado_y_adr(tk, ficha, cod)
    st.markdown(_ficha.encabezado_html(rd, _datos_cedear(df, ticker_sel), ficha, cod, fecha_datos), unsafe_allow_html=True)
    with st.spinner("Aguarde mientras se cargan los datos..."):
        extra = _extras_empresa(tk)
    pares = extra.get("historial")
    nombres = ["Resumen", "Análisis Fundamental", "Análisis Técnico y Rendimiento", "Valuación", "Estados Financieros", "Dividendos", "Competidores", "Directivos", "Accionariado", "Noticias"]
    # v1.5.52 (Guille): la explicación de cada solapa sale HACIA ARRIBA al pasar el mouse por el título (en el celular sigue arriba de cada solapa)
    st.markdown("<style>" + _tv.css_ayuda_solapas("sol_emp", [_ficha.INTROS.get(k) for k in ("resumen", "analisis", "grafico", "valuacion", "estados", "dividendos",
                                                                                              "competidores", "directivos", "accionariado", "noticias")]) + "</style>",
                unsafe_allow_html=True)
    with st.container(key="sol_emp"):
        t_res, t_ana, t_gra, t_val, t_est, t_div, t_com, t_dir, t_acc, t_not = st.tabs(nombres)
    with t_res:
        st.markdown(_ficha.con_intro("resumen", _ficha.tab_resumen(rd, ficha, mercado, agenda=extra.get("agenda"))), unsafe_allow_html=True)
    with t_ana:
        _af_ficha = _af_para_ficha(tk)
        _fecha_arriba = _boton_pdf_analisis(tk, _af_ficha, rd, extra, pares)      # v1.4.1: el análisis (formato v4) se puede bajar en PDF; v1.4.2: junto a la fecha
        st.markdown(_ficha.con_intro("analisis", _ficha.tab_analisis(rd, af=_af_ficha, estados=extra.get("estados"), universo={str(x).upper() for x in df["ticker"]}, historial=pares, dividendos=extra.get("dividendos"), bono10=_bono10_hoy(), fecha_en_tile=not _fecha_arriba)), unsafe_allow_html=True)
    with t_gra:
        st.markdown(_ficha.con_intro("grafico", _ficha.tab_grafico_tabla(pares)), unsafe_allow_html=True)      # v1.2.53: los rendimientos van arriba del grafico
        _render_grafico(tk, pares, rd)
        st.markdown(_tecnico.tab_tecnico_html(pares), unsafe_allow_html=True)
    with t_val:
        st.markdown(_ficha.con_intro("valuacion", _ficha.tab_valuacion(rd, ficha, anuales=(_multiplos_anuales_datos() or {}).get(tk))), unsafe_allow_html=True)
        try:      # v1.5.49: precio vs fundamentales del negocio (cierres mensuales del archivo histórico propio)
            from ui import precio_vs as _pvs
            _mes_fy = (ficha or {}).get("mes_cierre_fiscal") or (_af_ficha or {}).get("mes_cierre_fiscal")
            _pv_html = _pvs.precio_vs_html(tk, extra.get("estados"), _historico_precios().get(tk.upper()) or {}, rd.get("precio_actual"), _mes_fy)
            if _pv_html:
                st.markdown(_pv_html, unsafe_allow_html=True)
        except Exception:  # noqa: BLE001
            pass
    with t_est:      # v1.5.47 (Guille): subsolapas por parte, con gráficos arriba y la tabla debajo
        _est = extra.get("estados")
        if _est:      # v1.5.52 (Guille): la definición de cada parte va en su subsolapa (al pasar el mouse por el título; en el celular, arriba de cada una)
            st.markdown("<style>" + _tv.css_ayuda_solapas("sol_est", [_ficha.INTROS_ESTADOS.get(k) for k, _t, _c in _ficha.PARTES_ESTADOS]) + "</style>",
                        unsafe_allow_html=True)
            with st.container(key="sol_est"):
                for _sub, (_k, _t, _c) in zip(st.tabs([t for _, t, _ in _ficha.PARTES_ESTADOS]), _ficha.PARTES_ESTADOS):
                    with _sub:
                        st.markdown(_ficha.con_intro_estados(_k, _ficha.tab_estados_parte(_est, _k, ticker=tk)), unsafe_allow_html=True)
        else:
            st.markdown(_ficha.con_intro("estados", _ficha.tab_estados(_est, ticker=tk)), unsafe_allow_html=True)
        _nota_archivo(extra, "estados")
    with t_div:
        div = extra.get("dividendos") or {}
        rec = {"dividendo": _hp.dividendo_recesion((div.get("trayectoria") or {}).get("anuales"))}
        st.markdown(_ficha.con_intro("dividendos", _ficha.tab_dividendos(rd, div, rec)), unsafe_allow_html=True)
        _nota_archivo(extra, "dividendos")
    with t_com:
        st.markdown(_ficha.con_intro("competidores", _ficha.tab_competidores(rd, df, _paquetes_guardados()[0])), unsafe_allow_html=True)
    with t_dir:
        gob = extra.get("gobierno")
        nom_ceo = _ficha.nombre_ceo(gob) or str(ficha.get("ceo") or "")
        arch = extra.get("archivo") or {}
        foto = arch.get("foto") or (_foto_ceo(nom_ceo, str(rd.get("nombre") or tk)) if nom_ceo else None)
        if st.query_params.get("debug") == "1" and nom_ceo:
            from data import foto_ceo as _fc
            st.caption(f"Foto del CEO ({nom_ceo}): " + _fc.diagnostico(nom_ceo, str(rd.get("nombre") or tk)))
        st.markdown(_ficha.con_intro("directivos", _ficha.tab_directivos(gob, foto)), unsafe_allow_html=True)
        _nota_archivo(extra, "gobierno")
    with t_acc:
        st.markdown(_ficha.con_intro("accionariado", _ficha.tab_accionariado(extra.get("gobierno"))), unsafe_allow_html=True)
        _nota_archivo(extra, "gobierno")
    with t_not:
        st.markdown(_ficha.con_intro("noticias", _ficha.tab_noticias(tk, extra.get("noticias"))), unsafe_allow_html=True)
    cargando.empty()

    # v1.2.49: el desglose de metricas pasó a "Estadisticas de la empresa" (ui/ficha.py): valor de hoy, mediana, dibujito, Fair Value y peso de cada una.
    usadas_d = row.get("metricas_usadas")
    if sector in SECTOR_CONFIG and row.get("detalle") and _num_valido(usadas_d) and int(usadas_d) == 0:
        st.info(
            "Ninguna métrica fundamental pudo usarse para esta empresa. "
            "Por eso esta empresa no tiene categoría."
        )

    # v1.2.52: se saco el aviso "Posible trampa de valor" hasta que exista el Score de calidad final (ver README, "Pendientes"): ahi vuelve,
    # para empresas con score de calidad bajo y valoracion infravalorada.
    return texto_fuente(ficha)


# ---------------------------------------------------------------------------
# APP PRINCIPAL
# ---------------------------------------------------------------------------

def texto_aviso_legal():
    """Texto del aviso (config/ajustes.py: AVISO_LEGAL). Desde la v1.2.41 va al final de la pagina, en el pie, y no en una barra fija."""
    try:
        from config.ajustes import AVISO_LEGAL
    except Exception:  # noqa: BLE001
        AVISO_LEGAL = ("Herramienta de filtrado inicial, con fines informativos y educativos. No es una recomendación "
                       "de inversión ni una oferta de compra o venta.")
    return (AVISO_LEGAL or "").strip()


def render_noticias(df, descarga, lugar=None, directo=False):
    """Recuadro "Noticias Calientes": titulares ordenados con la regla de ui/noticias.py. Nunca rompe la pagina."""
    if not _noticias.ACTIVAS:
        return
    try:
        crudo = _noticias.esperar(descarga)
        bloques = _noticias.traducir_bloques(_noticias.ordenar_bloques(crudo, list(df["ticker"])))
        cuerpo = f"<style>{_noticias.CSS}</style>" + _noticias.noticias_bloques_html(bloques)
        if directo:         # v1.2.84: dentro del panel del menú la lista va abierta (el título ya está en la cabecera del panel)
            cuerpo = re.sub(r'<details class="nt"( open)?>', '<details class="nt" open>', cuerpo)
        (lugar if lugar is not None else st).markdown(cuerpo, unsafe_allow_html=True)
    except Exception:  # noqa: BLE001
        pass


def render_calendario(df, lugar=None, directo=False):
    """Recuadro "Calendario" (v1.2.79: solapas Resultados de empresas y Economía): proximos 60 dias agrupados por dia (ui/calendario.py). Va entre Noticias y el Filtro, en la misma fila. Nunca rompe la pagina."""
    try:
        paquetes, _ = _paquetes_guardados()
        tickers = list(df["ticker"])
        grupos = _calendario.proximos(paquetes, tickers=tickers)
        nombres = dict(zip(df["ticker"], df["nombre"])) if "nombre" in df.columns else {}
        n = sum(len(v) for _, v in grupos)
        with (lugar if lugar is not None else st.container()):
            t_res, t_eco = st.tabs(["Próximos Resultados Empresariales", "Próximos Eventos Financieros"])
            with t_res:
                tk = st.text_input("Buscá una empresa por ticker y mirá cuándo presenta resultados", key="cal_tk", placeholder="Ej.: AAPL", max_chars=12)
                if (tk or "").strip():
                    st.markdown(f"<style>{_calendario.CSS}</style><div class=\"cal\"><div class=\"cal-h\"><b>{html.escape(_calendario.buscar_ticker(paquetes, tk))}</b></div></div>", unsafe_allow_html=True)
                st.markdown(f"<style>{_calendario.CSS_GRILLA}</style>" + _calendario.calendario_grilla_html(grupos, nombres=nombres, cantidad=n), unsafe_allow_html=True)
            with t_eco:
                eventos, fuentes_eco = _calendario.cargar_economico()
                st.markdown(f"<style>{_calendario.CSS_GRILLA}</style>" + _calendario.economico_grilla_html(_calendario.economicos(eventos), fuentes_eco), unsafe_allow_html=True)
    except Exception:  # noqa: BLE001
        pass


def _ccl_hoy(df):
    """Dólar CCL implícito de los CEDEARs (mediana de pesos × ratio / dólares, con el control de coherencia de _pv.elegir_ars), o None si no hay precios. Nunca levanta excepciones."""
    try:
        if not PRECIOS_VIVOS:
            return None
        datos = _cedears.cargar()
        info = _precios_usd(_orden_tickers(df))
        usd = info.get("usd") or {}
        if not usd:
            return None
        simbolos = _cedears.simbolos_yahoo(datos)
        items = tuple((t, tuple(ss), datos[t].get("simbolo") or t) for t, ss in sorted(simbolos.items()))
        cand = _precios_ars(items)
        _b, ccl = _pv.elegir_ars(cand, {t: v.get("ratio") for t, v in datos.items()}, usd)
        return float(ccl) if ccl else None
    except Exception:  # noqa: BLE001
        return None


def render_cartera(df, pagina=True):
    """"Evaluá tu Portfolio" (?pagina=cartera): edad + perfil + archivo (Excel, .csv o PDF del broker) o texto -> evaluación en 4 bloques (pesos, geografía, sectores, conclusiones y ajustes).
    v1.2.79: pantalla exclusiva y carga mínima. v1.2.83: sin selector de moneda (se detecta sola), acepta PDF y suma la solapa "Conocé tu rentabilidad anual"."""
    from ui import cartera as C
    from ui import cartera_visual as CV
    st.markdown(f"<style>{C.CSS}{CV.CSS}{CV.CSS_ENTRADA}</style>", unsafe_allow_html=True)
    st.markdown('<div class="cr cr-top"><h1>Evaluá tu Portfolio</h1></div>', unsafe_allow_html=True)
    modo = st.session_state.get("cr_modo")
    _mosaicos = (("eval", "Evaluá tu Cartera de Inversiones", "Subí tus posiciones y recibí una evaluación gratuita."),
                 ("rent", "Conocé tu Rentabilidad", "Decinos cuánto dinero aportaste y retiraste y te contamos cuánto rindió tu portfolio."))

    def _abrir(k):
        st.session_state["cr_modo"] = None if st.session_state.get("cr_modo") == k else k
    st.markdown("""<style>
[class*="st-key-mos_"] button{min-height:132px;height:100%;width:100%;border-radius:16px;border:1px solid #fbd5e1;background:linear-gradient(180deg,#fff7fa 0%,#fff 75%);
 box-shadow:0 1px 2px rgba(15,23,42,.05);padding:16px 18px;text-align:left;justify-content:flex-start;align-items:flex-start;transition:box-shadow .15s,border-color .15s}
[class*="st-key-mos_"] button:hover{border-color:#f4909f;box-shadow:0 4px 14px rgba(232,102,143,.18)}
[class*="st-key-mos_"] button p{text-align:left;margin:0 0 .35em;color:#475569;font-size:.93rem;line-height:1.5;font-weight:400}
[class*="st-key-mos_"] button p:first-child{color:#be185d;font-size:1.12rem;font-weight:800}
[class*="st-key-mos_"] button > div{justify-content:flex-start;width:100%}
[class*="st-key-mos_"] [data-testid="stMarkdownContainer"],[class*="st-key-mos_"] button p{display:block!important;white-space:normal!important;overflow:visible!important;text-overflow:clip!important;width:100%}
.st-key-cr_go button{background:linear-gradient(90deg,#e8668f 0%,#f4909f 100%)!important;color:#fff!important;border:0!important;font-weight:800;border-radius:12px;padding:.55em 1.6em;box-shadow:0 2px 8px rgba(232,102,143,.3)}
[class*="st-key-mos_on_"] button{border:2px solid #e8668f;background:linear-gradient(180deg,#ffeaf1 0%,#fff 85%)}
</style>""", unsafe_allow_html=True)
    cols = st.columns(2, gap="medium")
    for col, (k, tit, sub) in zip(cols, _mosaicos):
        with col:
            st.button(f"{tit}\n\n{sub}", key=f"mos_{'on' if modo == k else 'off'}_{k}", on_click=_abrir, args=(k,), use_container_width=True)
    # las dos secciones quedan armadas (así no se pierde lo cargado al cambiar de mosaico); se muestra sólo la elegida
    ocultar = [f".st-key-cr_sec_{k}{{display:none!important}}" for k in ("eval", "rent") if modo != k]
    if ocultar:
        st.markdown("<style>" + "".join(ocultar) + "</style>", unsafe_allow_html=True)
    with st.container(key="cr_sec_eval"):
        _evaluar_cartera(df, C, CV)
    with st.container(key="cr_sec_rent"):
        _rentabilidad_anual(C)


_INTRO_EVAL = (
    "Una evaluación gratuita basada en reglas de inversión que nos fueron útiles en los más de 10 años que tenemos de experiencia bursátil. "
    "Recordá que no es una recomendación de compra o venta ni un consejo personalizado sino una orientación de índole educativa."
)
_INTRO_RENT = ("Conocer tu rentabilidad como inversor es clave para saber si las decisiones que estás tomando son útiles o no. "
               "Te permite conocerte y encontrar formas de mejorar el proceso de inversión.")
_OPC_RENT = ("Sé las fechas exactas de mis aportes y retiros", "No sé las fechas exactas de mis aportes y retiros")
_CSS_COMENZAR = """<style>
[class*="st-key-cr_comenzar"] button{background:linear-gradient(90deg,#e8668f 0%,#f4909f 100%)!important;color:#fff!important;border:0!important;border-radius:14px;padding:.8em 2.6em;
 box-shadow:0 4px 14px rgba(232,102,143,.35);min-height:3.2rem}
[class*="st-key-cr_comenzar"] button p{font-size:1.2rem!important;font-weight:800!important;color:#fff!important}
[class*="st-key-cr_comenzar"] button:hover{filter:brightness(1.05);box-shadow:0 6px 18px rgba(232,102,143,.45)}
[class*="st-key-cr_comenzar"] button:disabled{background:#cbd5e1!important;box-shadow:none!important;cursor:not-allowed;filter:none}
</style>"""


def _presentacion(intro, key_btn, key_estado):
    """Texto de presentación + botón «Comencemos» bien visible. True si ya se tocó."""
    if st.session_state.get(key_estado):
        return True
    st.markdown(_CSS_COMENZAR + f'<div class="cv-intro">{intro.replace(chr(10) * 2, "<br><br>")}</div>', unsafe_allow_html=True)
    st.button("Comencemos", key=key_btn, on_click=lambda: st.session_state.update({key_estado: True}))
    return False


def _leer_archivos(archivos, C):
    """Lee todos los archivos subidos (Excel, csv, txt, PDF, imagen). Devuelve (posiciones, notas, tc_resumen, hubo_imagen, error)."""
    pos, notas, tc_res, hay_img = [], [], None, False
    for a in archivos:
        n = a.name.lower()
        try:
            if n.endswith(".pdf"):
                p, nt, tc = C.leer_pdf_info(a.getvalue())
                tc_res = tc_res or tc
                nt = [" ".join(nt)] if nt else []
            elif n.endswith((".png", ".jpg", ".jpeg", ".webp")):
                from ui import cartera_ocr as OCR
                p, nt = OCR.posiciones_de_imagen(a.getvalue(), C)
                hay_img = True
                for q in p:
                    q["_img"] = True
            else:
                p, nt = C.leer_archivo_info(a.name, a.getvalue())
                nt = [nt] if nt else []
        except (ValueError, RuntimeError) as e:
            return [], [], None, False, f"{a.name}: {e}"
        pos += p
        notas += [f"{a.name}: {x}" if len(archivos) > 1 else x for x in nt if x]
    return pos, notas, tc_res, hay_img, ""


_CLASES_TABLA = {"rv": "Renta Variable", "rf": "Renta Fija", "oro": "Oro", "cripto": "Criptomonedas", "efectivo": "Liquidez", "otros": "Otras materias primas"}
_TIPO_DE_CLASE = {"Renta Variable": "Renta variable", "Renta Fija": "Renta fija", "Oro": "Oro", "Criptomonedas": "Cripto", "Liquidez": "Efectivo", "Otras materias primas": "", "Sin clasificar": ""}
_PAIS_ES = {"United States": "Estados Unidos", "Brazil": "Brasil", "Canada": "Canadá", "Denmark": "Dinamarca", "France": "Francia", "Germany": "Alemania", "India": "India", "Ireland": "Irlanda",
            "Italy": "Italia", "Japan": "Japón", "Netherlands": "Países Bajos", "Norway": "Noruega", "Spain": "España", "Sweden": "Suecia", "Switzerland": "Suiza", "Taiwan": "Taiwán",
            "United Kingdom": "Reino Unido", "Australia": "Australia", "China": "China", "Uruguay": "Uruguay"}


def _pais_sugerido(c, C, etfs=None):
    """País que la app ya conoce de una posición (para mostrarlo en la tabla); '' si no lo sabe."""
    if c.get("fuente") == "empresa":
        p = str((c.get("info") or {}).get("pais") or "")
        return _PAIS_ES.get(p, p)
    if c.get("clase") == "rf" and c.get("fuente") in ("tipo", "regla"):
        g = C._geo_rf(c)
        return {"emergentes": "Argentina", "usa": "Estados Unidos", "desarrollados": "Europa"}.get(g, "") if g else ""
    if c.get("fuente") == "etf":      # v1.5.62: también los ETFs muestran su país o región en la tabla
        e = (etfs or {}).get(C.clave_tk(c["ticker"])) or {}
        if e.get("pais"):
            return _PAIS_ES.get(str(e["pais"]), str(e["pais"]))
        g = C._geo_de(c, etfs or {})
        return {"usa": "Estados Unidos", "emergentes": "Mercados emergentes", "desarrollados": "Países desarrollados", "global": "Global"}.get(g, "")
    return ""


_TXT_CONFIRMAR = ("<div class='cv-intro'><b>Esto es lo que leímos.</b> Antes de analizar, revisá esta tabla: <b>ticker, país, monto invertido y moneda</b> (pesos o dólares). "
                  "Si algo está mal, corregilo acá mismo: podés editar, borrar o agregar filas. Si está todo bien, seguí con el paso 4.<br>"
                  "Perdoná lo engorroso: es un paso más, pero es necesario para que el análisis sea preciso. Cada broker arma su resumen de manera distinta "
                  "y un solo dato mal leído cambiaría toda la evaluación.</div>")


def _confirmar_lectura(pos, firma, empresas, etfs, C):
    """v1.5.5: «Esto es lo que leímos». Muestra SIEMPRE (Excel, PDF o captura) una tabla corta y editable (activo, país, monto, moneda y clase).
    v1.5.58 (paso 3 de 4): ya no tiene botón; devuelve (posiciones, faltan, huella) y el botón final está en el paso 4. posiciones es None si la tabla quedó vacía."""
    pre = {}
    filas = []
    for p in pos:
        c = C.clasificar(p, empresas, etfs)
        etq = _CLASES_TABLA.get(c["clase"], "Sin clasificar")
        pre[str(p["ticker"]).strip().upper()] = (etq, p.get("tipo") or "")
        filas.append({"Activo": str(p["ticker"]).strip(), "País": str(p.get("pais") or "") or _pais_sugerido(c, C, etfs), "Monto": round(float(p["monto"]), 2),
                      "Moneda": {"usd": "Dólares", "ars": "Pesos"}.get(p.get("moneda") or "", "Sin dato"), "Clase": etq})
    st.markdown(_TXT_CONFIRMAR, unsafe_allow_html=True)
    ed = st.data_editor(
        pd.DataFrame(filas, columns=["Activo", "País", "Monto", "Moneda", "Clase"]), num_rows="dynamic", use_container_width=True, hide_index=True,
        key="cr_conf_tabla_" + str(abs(hash(firma)) % 10**8), height=min(80 + 36 * len(filas), 900),
        column_config={"Activo": st.column_config.TextColumn("Ticker o nombre"),
                       "País": st.column_config.TextColumn("País"),
                       "Monto": st.column_config.NumberColumn("Monto invertido", min_value=0.0, format="%.2f"),
                       "Moneda": st.column_config.SelectboxColumn("Moneda", options=["Dólares", "Pesos", "Sin dato"]),
                       "Clase": st.column_config.SelectboxColumn("Clase", options=list(_CLASES_TABLA.values()) + ["Sin clasificar"])})
    out, sin_moneda, sin_clase = [], [], []
    for _, r in ed.iterrows():
        tk, mt = str(r.get("Activo") or "").strip(), r.get("Monto")
        if not tk or tk.lower() == "nan" or mt is None or pd.isna(mt) or float(mt) <= 0:
            continue
        etq = str(r.get("Clase") or "Sin clasificar")
        mon = {"Dólares": "usd", "Pesos": "ars"}.get(r.get("Moneda"))
        pa = str(r.get("País") or "").strip()
        pa = "" if pa.lower() in ("nan", "none") else pa
        antes = pre.get(tk.upper())
        tipo = antes[1] if antes and antes[0] == etq and antes[1] else _TIPO_DE_CLASE.get(etq, "")      # si la clase no cambió se conserva el tipo original (ON, bono, Money Market…)
        q = {"ticker": tk, "monto": float(mt), "tipo": tipo, "moneda": mon}
        if pa:
            q["pais"] = pa
        out.append(q)
        if not mon:
            sin_moneda.append(tk)
        if etq == "Sin clasificar":
            sin_clase.append(tk)
    if not out:
        st.warning("No hay posiciones en la tabla. Agregá al menos una fila con el ticker y el monto.")
        return None, ["al menos una posición en la tabla"], None
    tot = {"usd": sum(q["monto"] for q in out if q["moneda"] == "usd"), "ars": sum(q["monto"] for q in out if q["moneda"] == "ars")}
    partes = ([f"US\\$ {_fmt_num(tot['usd'])}"] if tot["usd"] else []) + ([f"\\$ {_fmt_num(tot['ars'])}"] if tot["ars"] else [])      # \\$ para que no lo tome como fórmula
    if partes:
        st.caption("Suma de lo que leímos: " + " y ".join(partes) + ". Fijate que coincida con el total de tu resumen.")
    faltan = []
    if sin_moneda:
        faltan.append("Elegí la **moneda** (pesos o dólares) de: " + ", ".join(sin_moneda[:12]) + ("…" if len(sin_moneda) > 12 else "") + ".")
    if sin_clase:
        faltan.append("Elegí la **clase** de: " + ", ".join(sin_clase[:12]) + ("…" if len(sin_clase) > 12 else "") + ".")
    sin_pais = []
    for q in out:
        if q["moneda"] and not q.get("pais"):
            c = C.clasificar(q, empresas, etfs)
            if c["fuente"] in ("tipo", "regla") and (c["clase"] == "rv" or (c["clase"] == "rf" and not C._geo_rf(c))):
                sin_pais.append(q["ticker"])
    if sin_pais:
        st.caption("Para ubicar por país estas posiciones, completá la columna **País**: " + ", ".join(sin_pais[:12]) + ("…" if len(sin_pais) > 12 else "") + ". Si no, quedan como «sin ubicar».")
    for t in faltan:
        st.warning(t)
    huella = str(abs(hash(str([(q["ticker"], round(q["monto"], 2), q["moneda"], q["tipo"], q.get("pais")) for q in out])) % 10**10))
    return out, faltan, huella


_OPC_MONEDA = ("Pesos", "Dólares", "Mixta (cada fila tiene su moneda; la reviso en la tabla)")
_CSS_PASOS = """<style>
.cr-paso{display:flex;align-items:center;gap:12px;margin:2px 0 10px}
.cr-num{flex:0 0 auto;width:34px;height:34px;border-radius:50%;background:#be185d;color:#fff;font-weight:800;font-size:1.1rem;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(190,24,93,.35)}
.cr-tit{font-size:1.2rem;font-weight:700;color:#9d174d}
.st-key-cr_p2,.st-key-cr_p3,.st-key-cr_p4{background:linear-gradient(180deg,#fff7fa 0%,#fff 60%);border:1px solid #fbd5e1;border-radius:16px;padding:14px 18px 12px;margin-top:12px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.st-key-cr_p2 [data-testid="stFileUploaderDropzone"]{border:2px dashed #f4909f;background:#fff7fa;border-radius:14px}
</style>"""


def _paso_html(n, titulo):
    return f'<div class="cr-paso"><span class="cr-num">{n}</span><span class="cr-tit">{titulo}</span></div>'


def _evaluar_cartera(df, C, CV):
    import datetime as _dt
    import json as _json
    if not _presentacion(_INTRO_EVAL, "cr_comenzar_eval", "cr_empezo"):
        return
    perfiles = ["Conservador", "Moderado", "Agresivo"]
    st.markdown(_CSS_PASOS, unsafe_allow_html=True)
    with st.container(key="cr_p1"):
        st.markdown(_paso_html(1, "Completá tus datos"), unsafe_allow_html=True)
        n1, n2, n3 = st.columns([1.3, 1.1, 2.2], gap="medium")
        with n1:
            nombre = st.text_input("Nombre (opcional)", key="cr_nombre", placeholder="Ej.: Guille")
        with n2:
            edad = st.number_input("Edad (obligatorio)", min_value=18, max_value=100, value=None, step=1, placeholder="Ej.: 45", key="cr_edad")
        with n3:
            try:
                perfil = st.segmented_control("Perfil de Inversor (obligatorio)", perfiles, default=None, key="cr_perfil")
            except Exception:  # noqa: BLE001
                perfil = st.radio("Perfil de Inversor (obligatorio)", perfiles, index=None, horizontal=True, key="cr_perfil")
    with st.container(key="cr_p2"):
        st.markdown(_paso_html(2, "Subí tus posiciones"), unsafe_allow_html=True)
        st.markdown('<div class="cv-ayuda">Subí el Excel o el PDF que descargaste de tu broker. Si tenés instrumentos que no son CEDEARs, indicá la categoría a la que pertenecen en una columna «Tipo» '
                    '(Renta fija, Oro, Cripto, Efectivo…) y el país en una columna «País» (Argentina, Estados Unidos, Europa…). Si no tenés un Excel o PDF y querés cargarlo a mano, usá el Excel de ejemplo. '
                    '<b>No intentes subir capturas de pantalla</b>, dado que el análisis se vuelve dificultoso e inexacto.</div>', unsafe_allow_html=True)
        try:
            from ui import cartera_ocr as OCR
            hay_ocr = OCR.disponible()
        except Exception:  # noqa: BLE001
            hay_ocr = False
        tipos = ["xlsx", "xlsm", "xls", "csv", "tsv", "txt", "pdf"] + (["png", "jpg", "jpeg", "webp"] if hay_ocr else [])
        u1, u2 = st.columns([3, 1], gap="medium")
        with u1:
            archivos = st.file_uploader("Tu cartera (Excel o PDF; podés subir más de un archivo)", type=tipos, accept_multiple_files=True, key="cr_archivo", label_visibility="collapsed")
        with u2:
            try:
                st.download_button("⬇ Excel de ejemplo", C.plantilla_excel(), file_name="cartera_ejemplo.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="cr_plantilla", use_container_width=True)
            except Exception:  # noqa: BLE001
                pass
        moneda_sel = st.radio("¿En qué moneda están los montos de tu archivo? (obligatorio)", _OPC_MONEDA, index=None, horizontal=True, key="cr_moneda",
                              help="Algunos brokers (por ejemplo IOL) marcan «Dólares» en un bono pero informan el valor en pesos. Por eso necesitamos que nos digas en qué moneda está el importe.")
        with st.expander("¿Ya te evaluaste antes? Subí tu evaluación anterior para compararla", expanded=False):
            previa_arch = st.file_uploader("Evaluación anterior (el PDF que descargaste la última vez)", type=["pdf"], key="cr_previa")
    _firma_arch = tuple((a.name, a.size) for a in archivos or ()) + (moneda_sel,)
    _firma = (nombre or "", edad, perfil, _firma_arch)
    # --- paso 3: lo que leímos del archivo (tabla para chequear y corregir)
    pos_ok, faltan_tabla, huella, pos, tc_resumen, hay_img, err = None, [], None, [], None, False, ""
    empresas, etfs = {}, {}
    with st.container(key="cr_p3"):
        st.markdown(_paso_html(3, "Chequeá tus posiciones"), unsafe_allow_html=True)
        if not archivos:
            st.markdown('<div class="cv-ayuda">Cuando subas tu archivo, acá te mostramos lo que leímos para que lo revises y, si hace falta, lo corrijas.</div>', unsafe_allow_html=True)
        else:
            pos, notas, tc_resumen, hay_img, err = _leer_archivos(archivos, C)
            _m = {"Pesos": "ars", "Dólares": "usd"}.get(moneda_sel)
            if _m and pos:
                pos = [dict(p, moneda=_m) for p in pos]         # v1.5.61: manda la moneda que declaró la persona en el paso 2
            if not moneda_sel:
                st.markdown('<div class="cv-ayuda">Elegí primero, en el paso 2, la moneda de los montos de tu archivo; después te mostramos lo que leímos.</div>', unsafe_allow_html=True)
            elif err:
                st.error(err)
            elif not pos:
                st.warning("No encontré posiciones. Necesito una columna con el ticker (o el nombre) y otra con el monto, o con cantidad y precio. Mirá el Excel de ejemplo.")
            else:
                for n in notas:
                    st.caption(n)
                if hay_img:
                    st.info("Leí tu captura: el sistema puede confundir números y letras, así que revisá bien la tabla.")
                for _, r in df.iterrows():
                    empresas[C.clave_tk(r.get("ticker"))] = {"nombre": r.get("nombre"), "sector": r.get("sector"), "pais": r.get("pais"), "categoria": r.get("categoria"), "beta": r.get("beta")}
                try:
                    etfs = {C.clave_tk(e["ticker"]): e for e in __import__("data.etfs", fromlist=["cargar"]).cargar()}
                except Exception:  # noqa: BLE001
                    etfs = {}
                pos_ok, faltan_tabla, huella = _confirmar_lectura(pos, _firma_arch, empresas, etfs, C)
        lugar_tc = st.container()
    # --- paso 4: descargo + botón
    with st.container(key="cr_p4"):
        st.markdown(_paso_html(4, "Descargo de responsabilidad"), unsafe_allow_html=True)
        acepto = st.checkbox("Acepto que esta evaluación es una orientación educativa, automática y puede cometer errores. No constituye una recomendación ni asesoría personalizada de inversión. "
                             "Finanzas para Médicos se deslinda de cualquier responsabilidad y acciones que puedan derivar de la mala interpretación del análisis, siendo el inversor el único responsable de sus propias decisiones financieras.", key="cr_acepto")
        falta = []
        if edad is None:
            falta.append("tu edad")
        if not perfil:
            falta.append("tu perfil de inversor")
        if not archivos:
            falta.append("subir tu cartera (Excel o PDF)")
        elif not moneda_sel:
            falta.append("elegir la moneda de tu archivo (paso 2)")
        elif err or not pos or pos_ok is None:
            falta.append("posiciones válidas en la tabla del paso 3")
        falta += [f for f in faltan_tabla if pos_ok is not None]
        if not acepto:
            falta.append("aceptar las condiciones")
        listo = not falta
        st.markdown("<style>.st-key-cr_go button:disabled{background:#cbd5e1!important;color:#fff!important;box-shadow:none!important;cursor:not-allowed}</style>", unsafe_allow_html=True)
        if st.button("Análisis de Cartera de Inversión", key="cr_go", type="primary", disabled=not listo):
            st.session_state["cr_ok"] = (_firma, huella)
        if not listo:
            st.warning("Para habilitar el análisis te falta: " + ", ".join(falta) + ".")
            return
    if st.session_state.get("cr_ok") != (_firma, huella):
        st.caption("Tocá «Análisis de Cartera de Inversión» para ver la devolución.")
        return
    pos = pos_ok
    base_k = "usd"          # desde v1.5.5 cada fila ya trae su moneda (la persona la confirma en la tabla)
    hay_pesos = any((p.get("moneda") or base_k) == "ars" for p in pos)
    tc = None
    if hay_pesos:
        auto = tc_resumen or _ccl_hoy(df)
        with lugar_tc:
            tc = st.number_input("Dólar para convertir (pesos por dólar)", min_value=1.0, value=round(auto, 2) if auto else None, step=1.0, key="cr_tc",
                                 help=("Por defecto, el dólar MEP que figura en tu resumen. Podés cambiarlo." if tc_resumen else "Por defecto, el dólar CCL implícito de los CEDEARs de hoy. Podés cambiarlo.") if auto
                                 else "No pudimos calcular el CCL ahora: escribilo vos.")
        if not tc:
            st.info("Hay montos en pesos: poné el dólar con el que querés convertirlos (por ejemplo, el CCL de hoy).")
            return
    pos, n_conv, _falta = C.convertir(pos, base_k, tc)
    pos, n_fus = C.fusionar(pos)
    res = C.analizar(pos, edad, perfil, empresas, etfs)
    if not res or not res.get("total"):
        st.warning("No pude clasificar ninguna posición. Completá la columna Tipo (Renta fija, Oro, Cripto, Efectivo…) o revisá los tickers.")
        return
    if n_conv:
        tc_txt = f"{tc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        st.caption(f"Pasamos a dólares {n_conv} posición(es) en pesos, a $ {tc_txt} por dólar" + (" (el dólar MEP de tu resumen)." if tc_resumen and abs(tc - tc_resumen) < 0.01 else "."))
    if n_fus:
        st.caption(f"Sumamos {n_fus} posición(es) repetida(s) (el mismo activo en más de un archivo o broker).")
    previa = None
    if previa_arch is not None:
        previa = C.resumen_de_pdf(previa_arch.getvalue())
        if not previa:
            st.caption("No pude leer ese PDF como una evaluación anterior: tiene que ser el PDF que descargaste de esta evaluación.")
    hoy = _dt.date.today()
    fecha_txt = hoy.strftime("%d/%m/%Y")
    st.markdown(CV.visual_html(res, edad, perfil, nombre or "", fecha_txt, previa), unsafe_allow_html=True)
    # informe descargable (PDF con membrete) y resumen para comparar la próxima vez: se arman en memoria y se bajan al dispositivo
    try:
        from ui import cartera_informe as CI
        av = ""
        _nom = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", str(nombre or "")).strip()[:40].strip()
        _arch = "Evaluación de Portfolio" + (" " + _nom if _nom else "")       # v1.5.5: el PDF se llama «Evaluación de Portfolio Laura»
        try:
            datos_inf, nombre_inf, mime_inf, etq_inf = CI.pdf_informe(res, edad, perfil, aviso=av, nombre=nombre or "", previa=previa), _arch + ".pdf", "application/pdf", "Descargar informe en PDF"
        except ImportError:
            datos_inf, nombre_inf, mime_inf, etq_inf = CI.html_informe(res, edad, perfil, aviso=av, nombre=nombre or "", previa=previa), _arch + ".html", "text/html", "Descargar informe (se puede imprimir como PDF)"
        st.markdown(_CSS_COMENZAR.replace("cr_comenzar", "cr_informe") + '<div class="cv-intro"><b>Te recomendamos descargar tu evaluación en PDF.</b> La próxima vez que te evalúes, subila en «¿Ya te evaluaste antes?» '
                    'y vemos juntos cómo fue cambiando tu cartera.</div>', unsafe_allow_html=True)
        st.download_button(etq_inf, datos_inf, file_name=nombre_inf, mime=mime_inf, key="cr_informe", use_container_width=True)
    except Exception:  # noqa: BLE001
        pass


def _fmt_num(x, dec=0):
    t = f"{x:,.{dec}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def _rentabilidad_anual(C):
    """"Conocé tu Rentabilidad" (v1.2.83; rehecha en v1.4.4 y v1.4.8). Primero se elige si se saben o no las fechas exactas (eso decide la página) y se toca «Comencemos».
    (1) ESTIMADA: fecha de inicio + aportado (+ retirado) + capital final -> rango entre un mínimo y un máximo. (2) EXACTA: la fecha y el monto de cada aporte y cada retiro.
    Todo en dólares. Con menos de un año NO se pasa a "por año": se muestra lo que rindió en ese tiempo, diciendo cuánto tiempo fue."""
    import datetime as _dt
    st.markdown(_CSS_COMENZAR + """<style>
.rt-card{border:1px solid #fbd5e1;background:linear-gradient(180deg,#fff7fa 0%,#fff 70%);border-radius:16px;padding:20px 22px;margin:12px 0 6px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.rt-tit{font-size:1.15rem;font-weight:700;color:#334155;margin-bottom:6px}
.rt-big{font-size:2.5rem;font-weight:800;color:#be185d;line-height:1.1}
.rt-big small{font-size:1.1rem;font-weight:700;color:#64748b;margin-left:6px}
.rt-fila{display:flex;flex-direction:column;gap:7px;margin-top:16px;color:#334155;font-size:1.18rem;line-height:1.45}
.rt-fila b{color:#0f172a}
.rt-nota{font-size:.84rem;color:#64748b;line-height:1.5;margin-top:14px;text-align:justify}
.rt-nota-g{font-size:1rem;color:#475569;line-height:1.55;margin-top:14px;text-align:justify}
.rt-aviso{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:10px;padding:9px 12px;font-size:.95rem;line-height:1.5;margin-top:12px}
.rt-ayuda{color:#475569;font-size:.95rem;line-height:1.55;text-align:justify;margin:4px 0 10px}
</style>""", unsafe_allow_html=True)
    hoy = _dt.date.today()
    # ---- paso 1: presentación + elegir si se saben las fechas + «Comencemos»
    if not st.session_state.get("cr_empezo_rent"):
        st.markdown(f'<div class="cv-intro">{_INTRO_RENT}</div>', unsafe_allow_html=True)
        sel = st.radio("¿Sabés las fechas exactas de tus aportes y retiros?", list(_OPC_RENT), index=None, key="rt_modo_sel")
        st.button("Comencemos", key="cr_comenzar_rent", disabled=sel is None,
                  on_click=lambda: st.session_state.update(cr_empezo_rent=True, rt_modo=st.session_state.get("rt_modo_sel")))
        return
    exacto = st.session_state.get("rt_modo") == _OPC_RENT[0]
    st.button("← Cambiar la forma de cálculo", key="rt_volver", on_click=lambda: st.session_state.update(cr_empezo_rent=False))

    def usd(x):
        return "US$ " + _fmt_num(x)

    def tarjeta(titulo, grande, chico, filas, notas, aviso="", nota_g=""):
        f = "".join(f"<span>{x}</span>" for x in filas)
        n = "".join(f'<div class="rt-nota">{x}</div>' for x in notas)
        g = f'<div class="rt-nota-g">{nota_g}</div>' if nota_g else ""
        av = f'<div class="rt-aviso">{aviso}</div>' if aviso else ""
        st.markdown(f'<div class="rt-card"><div class="rt-tit">{titulo}</div><div class="rt-big">{grande}<small>{chico}</small></div>{g}<div class="rt-fila">{f}</div>{av}{n}</div>', unsafe_allow_html=True)

    def filas_res(aportado, retirado, gan, tot, dias):
        signo = "+" if gan >= 0 else "−"
        return [f"Aportes: <b>{usd(aportado)}</b>", f"Retiros: <b>{usd(retirado)}</b>",
                f"Rendimiento sobre el capital invertido: <b>{signo}US$ {_fmt_num(abs(gan))}</b> ({signo}{_fmt_num(abs(tot), 1)} %)", f"Período analizado: <b>{C.duracion_txt(dias)}</b>"]
    nominal = "Los números son nominales (no descuentan inflación ni cambios en el tipo de cambio) y no garantizan resultados futuros."
    aviso_corto = "Pasó menos de un año, así que no te lo pasamos a «por año»: con tan poco tiempo ese número exagera. Te mostramos lo que rindió en ese período."

    # ---- página: fechas exactas
    if exacto:
        st.markdown('<div class="rt-ayuda">Cargá cada vez que pusiste plata (<b>Aporte</b>) y cada vez que sacaste (<b>Retiro</b>), con su fecha. '
                    'Si ya tenías plata invertida cuando empezaste, cargala como un aporte en esa fecha. <b>Todo en dólares</b> (si algún movimiento fue en pesos, pasalo a dólares al valor de ese día).</div>', unsafe_allow_html=True)
        n = st.session_state.setdefault("rt_filas", 4)
        h1, h2, h3 = st.columns([1.1, 1, 1], gap="small")
        h1.markdown("**Fecha**")
        h2.markdown("**Aporte o Retiro**")
        h3.markdown("**Monto en dólares**")
        movs, incompletas = [], 0
        for i in range(n):
            c1, c2, c3 = st.columns([1.1, 1, 1], gap="small")
            f = c1.date_input("Fecha", value=None, min_value=_dt.date(1990, 1, 1), max_value=hoy, format="DD/MM/YYYY", key=f"rt_f{i}", label_visibility="collapsed")
            t = c2.selectbox("Tipo", ["Aporte", "Retiro"], index=None, placeholder="Aporte o Retiro", key=f"rt_t{i}", label_visibility="collapsed")
            m = c3.number_input("Monto", min_value=0.0, value=None, step=100.0, placeholder="Ej.: 5000", key=f"rt_m{i}", label_visibility="collapsed")
            llenos = [f is not None, t is not None, bool(m)]
            if all(llenos):
                movs.append((f, float(m) if t == "Aporte" else -float(m)))
            elif any(llenos):
                incompletas += 1
        b1, b2 = st.columns([1, 1], gap="small")
        b1.button("＋ Agregar otra fila", key="rt_mas", on_click=lambda: st.session_state.update(rt_filas=st.session_state.get("rt_filas", 4) + 1))
        if n > 1:
            b2.button("− Quitar la última fila", key="rt_menos", on_click=lambda: st.session_state.update(rt_filas=max(1, st.session_state.get("rt_filas", 4) - 1)))
        final = st.number_input("Capital final: lo que vale hoy toda tu cartera, en dólares", min_value=0.0, value=None, step=1000.0, placeholder="Ej.: 13000", key="rt_final_ex")
        if incompletas:
            st.caption(f"Hay {incompletas} fila(s) incompleta(s): para que cuenten necesitan fecha, tipo y monto.")
        if not movs or final is None:
            st.caption("Cargá al menos un aporte y el capital final para ver el resultado.")
            return
        r = C.rentabilidad_con_fechas(movs, final, hoy)
        if r.get("error"):
            st.warning(r["error"])
            return
        filas = filas_res(r["aportado"], r["retirado"], r["ganancia"], r["total_pct"], r["dias"])
        if r["anual"] is not None:
            tarjeta("Tu Rentabilidad Anualizada en Dólares fue:", f"{_fmt_num(r['anual'], 1)} %", "", filas,
                    ["Calculado con la fecha de cada aporte y retiro: es la tasa anual con la que creció el dinero mientras estuvo invertido. " + nominal])
        else:
            sg = "+" if r["periodo_pct"] >= 0 else "−"
            tarjeta(f"Tu Rentabilidad en Dólares en {C.duracion_txt(r['dias'])} fue:", f"{sg}{_fmt_num(abs(r['periodo_pct']), 1)} %", "", filas,
                    ["Es lo que rindió el dinero que tuviste invertido durante ese tiempo (cada aporte y retiro pesa según los días que estuvo en la cartera). " + nominal], aviso=aviso_corto)
        return

    # ---- página: sin fechas exactas (rango estimado)
    st.markdown('<div class="rt-ayuda">Si no sabés las fechas exactas de tus aportes y retiros, lo calculamos igual: te damos un <b>rango estimado</b> (un número mínimo y uno máximo) justamente porque falta ese dato. '
                'Si las sabés, volvé y elegí la otra opción: el resultado sale exacto. <b>Todo en dólares.</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        inicio = st.date_input("¿Cuándo empezaste a invertir?", value=None, min_value=_dt.date(1990, 1, 1), max_value=hoy, format="DD/MM/YYYY", key="rt_inicio")
        aportado = st.number_input("Dinero que pusiste en total (en dólares)", min_value=0.0, value=None, step=1000.0, placeholder="Ej.: 10000", key="rt_aportado",
                                   help="La suma de todos tus aportes, en dólares.")
    with c2:
        retirado = st.number_input("Dinero que retiraste en total, en dólares (opcional)", min_value=0.0, value=None, step=1000.0, placeholder="Ej.: 2000", key="rt_retirado",
                                   help="La suma de todo lo que sacaste de la cartera. Si no retiraste nada, dejalo vacío. Se cuenta como si lo hubieras sacado hoy.")
        final = st.number_input("Capital final: lo que vale hoy, en dólares", min_value=0.0, value=None, step=1000.0, placeholder="Ej.: 13000", key="rt_final",
                                help="El valor de toda tu cartera hoy, en dólares.")
    if inicio is None or not aportado or final is None:
        st.caption("Completá la fecha de inicio, lo que pusiste y el capital final para ver la estimación.")
        return
    ret = retirado or 0.0
    dias = (hoy - inicio).days
    if dias < 1:
        st.warning("La fecha de inicio tiene que ser de ayer o antes.")
        return
    anios = dias / 365.25
    gan = final + ret - aportado
    tot = gan / aportado * 100
    filas = filas_res(aportado, ret, gan, tot, dias)
    nota_ret = "Los retiros se contaron como si los hubieras hecho hoy: si los hiciste antes, el resultado real cambia un poco. " if ret else ""
    if anios < 1:
        sg = "+" if tot >= 0 else "−"
        tarjeta(f"Tu Rentabilidad en Dólares en {C.duracion_txt(dias)} fue:", f"{sg}{_fmt_num(abs(tot), 1)} %", "", filas,
                ["Es lo que ganó tu plata sobre lo que pusiste en total. Si fuiste aportando de a poco, sobre el dinero que estuvo invertido el rendimiento fue algo mayor. "
                 "Si querés afinarlo, volvé y elegí la opción de las fechas exactas. " + nota_ret + nominal], aviso=aviso_corto)
        return
    if final <= 0:
        st.warning("Con capital final en cero no se puede estimar la tasa por año. Si perdiste todo, la ganancia total es −100 %.")
        return
    r = C.rentabilidad_anual(aportado, final, anios, ret)
    if r is None:
        st.warning("Con esos datos no puedo estimar. Revisá que los montos sean mayores a cero.")
        return
    pares = [x for x in (r["anual_inicio"], r["anual_parejo"]) if x is not None]
    lo, hi = min(pares), max(pares)
    if hi - lo > 0.05:
        porque = (f"<b>Por qué es una estimación:</b> no sabemos cuándo pusiste cada aporte, y eso cambia el resultado. Si pusiste toda la plata el primer día, tu rendimiento por año fue de <b>{_fmt_num(lo, 1)} %</b>. "
                  f"Si fuiste aportando un poquito cada mes, el dinero estuvo menos tiempo invertido y el rendimiento por año fue de <b>{_fmt_num(hi, 1)} %</b>. Lo real está entre esos dos números. "
                  "Para el número exacto, volvé y elegí la opción de las fechas exactas.")
        tarjeta("Tu Rentabilidad Anualizada en Dólares se encuentra en el rango entre:", f"{_fmt_num(lo, 1)} % y {_fmt_num(hi, 1)} %", "", filas, [nota_ret + nominal], nota_g=porque)
    else:
        tarjeta("Tu Rentabilidad Anualizada en Dólares fue:", f"{_fmt_num(lo, 1)} %", "", filas, [nota_ret + nominal])


def render_barra_cartera(df):
    """Barra naranja "Evaluá tu Cartera de Inversiones" de punta a punta (v1.2.77), en el inicio de Empresas y de ETFs. v1.2.79: un click lleva a su pantalla exclusiva (?pagina=cartera)."""
    with st.container(key="caja_cart"):
        st.markdown('<a class="cr-barra" href="?pagina=cartera" target="_self"><span>Evaluá tu Cartera de Inversiones: subí tu Excel y recibí una evaluación gratuita.</span><b>→</b></a>', unsafe_allow_html=True)


def main():
    """v1.5.43 (rapidez): la barra de mercados ya no frena la página. Se reserva su lugar arriba y se dibuja al final; mientras tanto se ve todo lo demás.
    Además, los precios de hoy empiezan a bajarse al mismo tiempo que la barra (antes iban uno detrás del otro)."""
    ctx = {}
    try:
        _main(ctx)
    finally:
        ph = ctx.get("barra")
        if ph is not None:
            try:
                from ui import mercados as _mk
                ph.markdown(_mk.barra_html(_mk.obtener()), unsafe_allow_html=True)
            except Exception:  # noqa: BLE001
                pass


def render_ideas(universe_key):
    """v1.5.44: «Ideas de Inversión»: cinco mosaicos (Aristócratas, Reyes, Aspirantes, Dividendos Altos, Fundamentales Fuertes) y, al tocar uno, su lista."""
    from ui import ideas as _ideas, tabla_visual as _tv, etfs as _ui_etfs
    from data import etfs as _etfs, analisis_fundamental as _AF
    try:
        df, _ = get_scored_data(universe_key)
    except Exception:  # noqa: BLE001
        df = None
    try:
        calidades = {t: (a or {}).get("calidad") for t, a in (_AF.cargar()[0] or {}).items()}
    except Exception:  # noqa: BLE001
        calidades = {}
    try:
        etfs = _etfs.cargar()
        guardados, _f = _etfs_guardados()
    except Exception:  # noqa: BLE001
        etfs, guardados = [], {}
    listas = _ideas.cargar_listas()
    clave = st.query_params.get("lista")
    # v1.5.45: rendimientos de hoy (el dividendo anual sobre el precio actual), para que «Dividendos Altos» cambie con el precio
    precios_e = {}
    if PRECIOS_VIVOS and df is not None and not df.empty:
        try:
            info_p = _precios_usd(_orden_tickers(df))
            df_p, n_p = _pv.aplicar_precios(df, info_p.get("usd") or {}, info_p.get("fecha"), info_p.get("hora"), info_p.get("fuente"), info_p.get("var"))
            if n_p:
                df = df_p
        except Exception:  # noqa: BLE001
            pass
    if PRECIOS_VIVOS and etfs and clave in (None, "altos"):
        try:
            precios_e = _precios_etfs(tuple((e["ticker"], _etfs.simbolo_yahoo(e)) for e in etfs))
        except Exception:  # noqa: BLE001
            precios_e = {}
    css = f"<style>{css_fuente()}{_tv.CSS}{_ideas.CSS}{css_condensada()}</style>"      # v1.5.47: misma tipografía que la tabla principal
    if clave in {x["clave"] for x in _ideas.LISTAS}:
        filas = _ideas.miembros(clave, df, calidades, etfs, guardados, listas, precios_e)
        _dir = st.query_params.get("dir")
        st.markdown(css + _ideas.lista_html(clave, filas, listas, celda_empresa=_tv._celda_empresa, celda_sector=_tv._celda_sector,
                                            celda_categoria=_tv._celda_valoracion_tabla, celda_puntaje=_tv._celda_puntaje,
                                            logo_etf=lambda e: _ui_etfs.logo_chico_html(e, guardados.get(e.get("ticker"))),
                                            orden=st.query_params.get("orden"), asc=(None if _dir not in ("asc", "desc") else _dir == "asc")),
                    unsafe_allow_html=True)
        return
    conteos = {x["clave"]: len(_ideas.miembros(x["clave"], df, calidades, etfs, guardados, listas, precios_e)) for x in _ideas.LISTAS}
    st.markdown(css + _ideas.mosaicos_html(conteos), unsafe_allow_html=True)


def _arrancar_precios(universe_key):
    """v1.5.43: dispara la bajada de los precios de hoy en segundo plano, sin esperar (la usa la tabla un poco después)."""
    if not PRECIOS_VIVOS:
        return
    try:
        df0, _ = get_scored_data(universe_key)
        _precios_usd(_orden_tickers(df0), esperar=0)
    except Exception:  # noqa: BLE001
        pass


def _main(ctx):
    # Cargar universo de tickers
    universe = load_custom_tickers()
    universe_key = str(sorted([t for ts in universe.values() for t in ts]))

    # Franja negra de arriba con el nombre (y los iconos y el menu si estan cargados sus links). El aviso y "Datos al ..." van
    # al final de la pagina (pie_html).
    etf_sel = st.query_params.get("etf")
    en_etfs = st.query_params.get("tabla") == "etfs" or bool(etf_sel)
    home_etfs = en_etfs and not etf_sel
    en_quienes = st.query_params.get("pagina") == "quienes"
    en_cartera = st.query_params.get("pagina") == "cartera"
    en_ideas = st.query_params.get("pagina") == "ideas"
    en_mapa = st.query_params.get("pagina") == "mapa"      # v1.5.29: mapa de calor de empresas y ETFs
    en_inicio = not (en_quienes or en_cartera or en_ideas or en_mapa or etf_sel or st.query_params.get("empresa"))
    en_landing = en_inicio and not dict(st.query_params) and not st.session_state.get("entro")      # v1.5.7: pantalla de inicio (solo con la URL pelada y antes de tocar «Comenzar»)
    activa = "cartera" if en_cartera else ("etfs" if en_etfs else ("" if (en_quienes or en_ideas or en_mapa) else "empresas"))
    st.markdown(f"<style>{CSS_MARCA}{css_nav(activa)}{CSS_BUSQUEDA}{CSS_FLECHA}{CSS_NAV}</style>"
                + encabezado_html(NOMBRE_APP, activa=activa, menu_abierto=st.query_params.get("menu") == "1", links=not en_landing, home=en_inicio and not en_landing), unsafe_allow_html=True)
    # v1.5.36: en el celu no se veia el «Aguarde»: la barra de mercados espera hasta 8 s la primera vez y hasta ahi no habia nada en pantalla. Ahora el aviso sale ANTES y se borra cuando la barra esta lista.
    # v1.5.43: la barra de mercados (dólares, Merval, bolsas…) se dibuja YA si está guardada; si no (primera visita), se reserva su lugar y se completa al final (main)
    try:
        from ui import mercados as _mk
        _items_mk = _mk.obtener(esperar=0)
        if not (en_quienes or en_cartera or en_ideas):
            _arrancar_precios(universe_key)       # los precios bajan en paralelo con la barra
        if _items_mk:
            st.markdown(_mk.barra_html(_items_mk), unsafe_allow_html=True)
        else:
            ctx["barra"] = st.empty()
    except Exception:  # noqa: BLE001
        pass
    from ui.tema import css_oscuro
    st.markdown(css_oscuro(), unsafe_allow_html=True)      # v1.4.3: modo oscuro (botón sol / luna en la franja negra)
    poner_flecha()      # v1.2.71: flecha "hay más abajo" en todas las páginas
    # v1.2.83: menu lateral (las 3 rayitas). Fuera del inicio se llena ya; en el inicio se llena mas abajo, cuando estan los datos (Filtro, Noticias, Calendario)
    menu_box = st.container(key="menu_lateral")
    render_menu_estatico(menu_box, home=en_inicio and not en_landing, filtro="Filtro de ETFs" if home_etfs else "Filtro de Empresas")
    poner_esc()
    if en_inicio and not en_landing:
        fly_filtro, fly_noticias, fly_cal = st.container(key="fly_filtro"), st.container(key="fly_noticias"), st.container(key="fly_cal")
    # v1.2.60/83: al lado del nombre va el boton de la otra tabla ("Empresas" <-> "Exchange Traded Funds (ETFs)"); el buscador esta en todas las paginas (el de las tablas se dibuja mas abajo, con la tabla)
    if en_quienes or en_cartera or en_ideas or en_mapa:      # v1.5.47 (Guille): «← Atrás · ⌂ Inicio» en azul en todas las páginas (antes «Volver al inicio»)
        _atras = "?pagina=ideas" if (en_ideas and st.query_params.get("lista")) else "?inicio=0"
        st.markdown(f'<div class="vol-fila nav-fila">{nav_html(_atras)}</div>', unsafe_allow_html=True)
    if etf_sel or st.query_params.get("empresa"):
        render_fila_volver(bool(etf_sel))      # v1.5.32: «Volver» + buscador en la misma fila (antes el buscador flotaba a una altura fija y a veces quedaba encimado)
    elif en_quienes:
        render_buscador()      # v1.5.44: en Ideas no va (se superponía con el título; cada lista lleva a la ficha de la empresa)      # v1.5.43: en el mapa el buscador va en la fila del título (render_mapa)
    aviso = texto_aviso_legal()
    fecha = None
    if en_landing:
        from ui import inicio as _inicio
        st.markdown(_inicio.hero_html(), unsafe_allow_html=True)
        st.markdown(pie_html(APP_VERSION, aviso=aviso), unsafe_allow_html=True)
        return

    # v1.2.83: "Ideas de inversión" (?pagina=ideas): por ahora un aviso; la sección se arma más adelante
    if en_ideas:      # v1.5.44: Ideas de Inversión con mosaicos (ui/ideas.py); ?lista=clave abre la lista
        render_ideas(universe_key)
        st.markdown(pie_html(APP_VERSION, aviso=aviso), unsafe_allow_html=True)
        return

    # v1.2.49: pagina "Quiénes somos" (?pagina=quienes): no necesita los datos de las empresas, asi que se muestra al toque
    if st.query_params.get("pagina") == "quienes":
        st.markdown(f"<style>{css_fuente()}{css_condensada()}{CSS_QUIENES}</style>" + quienes_html(), unsafe_allow_html=True)
        st.markdown(pie_html(APP_VERSION, aviso=aviso), unsafe_allow_html=True)
        return

    # Noticias: la descarga arranca ya, en segundo plano, mientras se cargan los datos de las empresas
    descarga_noticias = _noticias.iniciar_descarga()

    # v1.2.59: mismo aviso que la pagina de la empresa ("Aguarde mientras se cargan los datos...") mientras se cargan los datos y los precios
    cargando_inicio = st.empty()
    cargando_inicio.markdown(f"<style>{_ficha.CSS_CARGA}</style>" + '<div class="fch-carga"><span class="fch-giro"></span>Aguarde mientras se cargan los datos…</div>', unsafe_allow_html=True)

    # Cargar datos
    with contextlib.nullcontext():
        try:
            df, fuente = get_scored_data(universe_key)
            if fuente.startswith("cache_vencido"):
                partes = fuente.split("|")
                error_msg = partes[1] if len(partes) > 1 else "error desconocido"
                ts_str = partes[2] if len(partes) > 2 else "?"
                st.warning(
                    f"⚠️ **Yahoo Finance no disponible** — mostrando datos del caché ({ts_str}). "
                    f"Motivo: {error_msg}",
                    icon="⚠️",
                )
            elif fuente.startswith("cache_vigente"):
                # Antes habia un cuadro azul grande con esto; ahora es un renglon chico en el pie de la pagina
                ts_str = fuente.split("|")[1] if "|" in fuente else ""
                fecha = ts_str.split(" ")[0] if ts_str and ts_str != "?" else None
        except Exception as e:
            st.error(f"❌ Error al cargar datos y sin caché disponible: {e}")
            df = None
            fuente = "error"

    # Aviso si el caché es viejo (más de un trimestre)
    try:
        _, ts_cache = load_cache(ignorar_ttl=True)
        if ts_cache is not None and (datetime.now() - ts_cache).days >= CACHE_VIEJO_DIAS:
            st.warning(
                f"⏰ **El caché tiene {(datetime.now() - ts_cache).days} días.** Es hora de actualizarlo: "
                "corré generar_cache.bat en tu PC y subí data/cache_datos.json y la carpeta data/historial a GitHub.",
                icon="⏰",
            )
    except Exception:
        pass

    # Países en castellano (antes de los filtros, así el filtro, el orden y la tabla los usan)
    if df is not None and not df.empty and "pais" in df.columns:
        df = df.copy()
        # Si Yahoo no informo el pais de una empresa, se usa el de respaldo (config/sectors.py)
        df["pais"] = [p if isinstance(p, str) and p else PAIS_MANUAL.get(t) for p, t in zip(df["pais"], df["ticker"])]
        df["pais"] = df["pais"].map(traducir_pais)
    if df is not None and not df.empty and "sector" in df.columns:
        df = agregar_columnas_info(df)       # v1.2.47: sector, industria y "sector · industria" (solo informacion)

    # v1.2.46: precios de hoy (Yahoo) en lugar de los del cache. Si Yahoo no responde, queda el precio del cache y el pie lo dice.
    texto_precios = None
    if PRECIOS_VIVOS and df is not None and not df.empty:
        try:
            with contextlib.nullcontext():
                info_p = _precios_usd(_orden_tickers(df))
            df_p, n_p = _pv.aplicar_precios(df, info_p.get("usd") or {}, info_p.get("fecha"), info_p.get("hora"), info_p.get("fuente"), info_p.get("var"))
            if n_p:
                df = df_p
                f_p = info_p.get("fecha")
                # v1.2.48: el pie no dice de que fuente vino cada precio (dato interno nuestro): solo la fecha y la hora
                # v1.4.9 (pedido de Guille): no se muestra la fecha del cache (puede quedar vieja); solo la de los precios de hoy, como "Datos al dd/mm/aaaa (hh:mm)"
                texto_precios = (f"Datos al <b>{f_p.strftime('%d/%m/%Y')}</b> ({info_p.get('hora')})" if f_p else f"Datos de hoy ({info_p.get('hora')})")
        except Exception:  # noqa: BLE001
            pass

    # v1.2.72: parametros tecnicos (RSI, promedios, rendimientos...) de data/tecnicos.json; sin el archivo las columnas quedan vacias
    if df is not None and not df.empty:
        try:
            df = _tecnicos.agregar_columnas(df, _tecnicos_guardados()[0])
        except Exception:  # noqa: BLE001
            pass

    cargando_inicio.empty()
    if df is None or df.empty:
        st.error("No se pudieron cargar datos. Intentá de nuevo en unos minutos.")
        st.markdown(pie_html(APP_VERSION, aviso=aviso, precios=texto_precios), unsafe_allow_html=True)
        st.stop()

    # Estilos de la tabla, de la escala, de la pagina de empresa y de las banderas (una sola vez por pagina)
    st.markdown(f"<style>{css_fuente()}{CSS_VISUAL}{CSS_FICHA}{css_condensada()}</style>", unsafe_allow_html=True)
    st.markdown(css_banderas(), unsafe_allow_html=True)

    # v1.5.29: mapa de calor (?pagina=mapa&tipo=empresas|etfs)
    if en_mapa:
        render_mapa(df, texto_precios)
        st.markdown(pie_html(APP_VERSION, aviso=aviso, precios=texto_precios, fuente=texto_fuente()), unsafe_allow_html=True)
        return

    # v1.2.73: "Tu Cartera" (?pagina=cartera)
    if en_cartera:
        render_cartera(df)      # v1.5.2: en esta página no va ningún pie (ni "Powered by", ni versión, ni "Developed by")
        return

    # v1.2.64: pagina de un ETF (?etf=TICKER)
    if etf_sel:
        render_pagina_etf(df, etf_sel, fecha)
        st.markdown(pie_html(APP_VERSION, aviso=aviso, precios=texto_precios, fuente=texto_fuente()), unsafe_allow_html=True)
        return

    # Pagina de una empresa (se abre al tocar su nombre en la tabla): ?empresa=TICKER
    empresa = st.query_params.get("empresa")
    if empresa:
        fuente_emp = render_pagina_empresa(df, empresa, fecha)
        st.markdown(pie_html(APP_VERSION, aviso=aviso, precios=texto_precios, fuente=fuente_emp or texto_fuente()), unsafe_allow_html=True)
        return

    # v1.2.83: Filtro, Noticias Calientes y Calendario ya no van arriba de la tabla: viven en el menu lateral (las 3 rayitas), junto con Evaluá tu Portfolio,
    # Ideas de inversión, Quiénes somos, las redes y Comentarios. Asi la tabla sube. Todo se dibuja siempre (aunque el menu este cerrado): los filtros siguen valiendo.
    # Las noticias: si ya estaban bajadas (se guardan 15 minutos) se dibujan al toque; si hay que esperar a la fuente, el lugar queda reservado y se completa al final.
    st.markdown(f"<style>{CSS_CAJAS}</style>", unsafe_allow_html=True)
    hay_gris = "categoria" in df.columns and bool((df["categoria"] == "DATOS INSUFICIENTES").any())
    noticias_pendientes = descarga_noticias is not None
    with fly_filtro:
        st.markdown(fly_cabecera_html("Filtro de ETFs" if home_etfs else "Filtro de Empresas"), unsafe_allow_html=True)
        if home_etfs:
            sel_etfs = render_filtro_etfs(_etfs_lista())
        else:
            filtros = render_filtros_inline(universe, df)
            st.markdown(escala_valoracion_html(hay_gris), unsafe_allow_html=True)
    with fly_noticias:
        st.markdown(fly_cabecera_html("Noticias Calientes del día"), unsafe_allow_html=True)
        lugar_noticias = st.empty()
        if not noticias_pendientes:
            render_noticias(df, None, lugar_noticias, directo=True)
    with fly_cal:
        st.markdown(fly_cabecera_html("Calendario Financiero"), unsafe_allow_html=True)
        render_calendario(df, st.container(), directo=True)

    # v1.2.47: buscador (por nombre o ticker; desde la v1.2.49 sube a la franja negra en pantallas anchas) y, despues, la tabla
    busqueda = ""      # v1.5.14: el buscador va dentro de la fila de la tabla (render_fila_tabla)
    if home_etfs:
        render_tabla_etfs(_etfs_lista(), sel_etfs)
        if noticias_pendientes:
            render_noticias(df, descarga_noticias, lugar_noticias, directo=True)
        st.markdown(pie_html(APP_VERSION, aviso=aviso, precios=texto_precios, fuente=texto_fuente()), unsafe_allow_html=True)
        return
    # v1.2.49: ya no hay "Cómo leer la tabla" (cada título explica su columna al pasar el mouse); el Excel va arriba de la tabla, a la derecha
    lugar_excel = st.container(key="fila_excel")
    with lugar_excel:
        _fila_tabla("empresas")
    render_main_table(df, filtros, fecha, aviso, lugar_excel, busqueda)

    if noticias_pendientes:
        render_noticias(df, descarga_noticias, lugar_noticias, directo=True)

    # Seguimiento (historial del caché)
    render_seguimiento()

    # Panel de diagnóstico (solo visible si ?debug=1 en la URL)
    render_debug_panel()

    st.markdown(pie_html(APP_VERSION, aviso=aviso, precios=texto_precios, fuente=texto_fuente()), unsafe_allow_html=True)


try:
    from config.ajustes import DIAS_AVISO_CACHE_VIEJO as CACHE_VIEJO_DIAS
except Exception:  # noqa: BLE001
    CACHE_VIEJO_DIAS = 100


@st.cache_data(ttl=3600, show_spinner=False)
def _evaluar_historial(clave: str) -> dict:
    copias = cargar_copias()
    res = evaluar_copias(copias)
    res["fechas"] = [f.strftime("%d/%m/%Y") for f, _ in copias]
    prox = proxima_medicion(copias)
    res["proxima"] = prox.strftime("%d/%m/%Y") if prox else None
    return res


def render_seguimiento():
    """Panel: ¿las categorías del screener acertaron lo que pasó con el precio el mes siguiente?"""
    st.markdown("---")
    carpeta = os.path.join("data", "historial")
    clave = "|".join(sorted(os.listdir(carpeta))) if os.path.isdir(carpeta) else "sin_historial"
    try:
        res = _evaluar_historial(clave)
    except Exception as e:
        st.caption(f"Seguimiento no disponible: {e}")
        return
    n = len(res["fechas"])
    with st.expander(f"📈 Seguimiento: ¿el screener acierta? ({n} copia{'s' if n != 1 else ''} del caché)"):
        st.caption(
            "Cada vez que corrés generar_cache.bat se guarda una copia con fecha en data/historial. "
            "Acá se mira cuánto cambió el precio hasta la copia siguiente, según la categoría que tenía cada empresa. "
            "Solo precio (no incluye dividendos). Con pocos meses no es concluyente."
        )
        if n:
            st.markdown("**Copias guardadas:** " + ", ".join(res["fechas"]))
        if not res["pares"]:
            st.info(
                f"Todavía no se puede medir: hacen falta dos copias separadas por al menos {MIN_DIAS_ENTRE_COPIAS} días. "
                + (f"Con la última copia que hay, otra copia hecha el {res['proxima']} o después ya permite medir "
                   "(se crea al correr generar_cache.bat)." if res.get("proxima") else
                   "La próxima actualización del caché la completa.")
            )
            return
        filas = [{
            "Desde": str(p["desde"]), "Hasta": str(p["hasta"]), "Empresas": p["empresas"],
            "Todas (%)": f"{p['todas']:+.1f}",
            "Baratas − caras, oficial (pts)": None if p["spread_oficial"] is None else round(p["spread_oficial"], 1),
            "Baratas − caras, vs sector (pts)": None if p["spread_sector"] is None else round(p["spread_sector"], 1),
        } for p in res["pares"]]
        st.markdown("**Por período** (baratas − caras: cuánto más subieron las empresas marcadas como infravaloradas que las sobrevaloradas; positivo = el screener acertó)")
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
        # Una sola tabla: por categoria, cuantas empresas habia y cuanto cambio el precio medio segun cada puntaje
        etiquetas = (("oficial", "Oficial"), ("sector", "En sombra: vs sector"))
        comp = pd.DataFrame(index=[c for c in CATEGORIAS_ORDEN])
        faltan = []
        for clave, rotulo in etiquetas:
            t = res["tablas"].get(clave)
            if t is None:
                faltan.append(rotulo)
                continue
            comp[(rotulo, "Empresas")] = t["Empresas"].reindex(comp.index)
            comp[(rotulo, "Precio medio (%)")] = t["Variación media del precio (%)"].reindex(comp.index).round(1)
        if comp.shape[1]:
            comp.columns = pd.MultiIndex.from_tuples(comp.columns)
            comp.index = [nombre_corto(c) for c in comp.index]
            comp.index.name = "Categoría"
            st.markdown("**Por categoría** (variación media del precio de las empresas que tenían esa categoría al inicio de cada período)")
            fmt = {c: ("{:.0f}" if c[1] == "Empresas" else "{:+.1f}") for c in comp.columns}
            st.dataframe(comp.dropna(how="all").style.format(fmt, na_rep="—"), use_container_width=True)
        if faltan:
            st.caption("Las copias anteriores no tienen estos puntajes: " + ", ".join(faltan) + ".")
        if res["todas"] is not None:
            st.caption(f"Variación media de todas las empresas en esos períodos: {res['todas']:+.1f}%")


def render_debug_panel():
    """
    Panel de diagnóstico oculto. Muestra qué devolvió yfinance para cada ticker.
    Para activarlo: agregar ?debug=1 a la URL de Streamlit.
    Útil para entender por qué ciertos tickers muestran DATOS INSUFICIENTES.
    """
    # Verificar si debug mode está activo (via query param o session state)
    query_params = st.query_params
    debug_mode = query_params.get("debug", "0") == "1"

    if not debug_mode:
        return

    st.divider()
    # v1.2.49: "Actualizar datos" ya no esta en el Filtro (los datos se refrescan solos: el cache cada 6 horas y los precios cada 5 minutos); queda aca
    if st.button("Actualizar datos", key="debug_actualizar",
                 help="Borra la memoria de Streamlit y vuelve a leer el caché guardado (data/cache_datos.json) y los precios. Sirve justo después de subir un caché nuevo."):
        st.cache_data.clear()
        st.rerun()
    # v1.5.27: qué fuentes de noticias respondieron desde el servidor (algunas webs bloquean los servidores y no la PC de uno)
    try:
        _cr = _noticias._ESTADO.get("crudo") or {}
        _ef = _cr.get("estado_feeds") or {}
        with st.expander(f"📰 Noticias: {sum(1 for v in _ef.values() if v)} de {len(_ef)} fuentes respondieron", expanded=False):
            for _b in _noticias.BLOQUES:
                for _f in _b["feeds"]:
                    _n = _ef.get(_f[1])
                    st.write(f"{'✅' if _n else '❌'} {_b['titulo']} · {(_f[3] if len(_f) > 3 else _b['fuente'])} · {_f[0]}: " + (f"{_n} titulares" if _n else "no respondió"))
    except Exception:  # noqa: BLE001
        pass
    st.subheader("🔧 Panel de Diagnóstico — yfinance Debug")
    st.caption(
        "Este panel muestra exactamente qué devolvió yfinance para cada ticker. "
        "Útil para entender por qué algunas empresas no tienen medianas calculadas."
    )

    debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yf_debug_log.json")

    if not os.path.exists(debug_path):
        st.info("Archivo de diagnóstico no encontrado. Actualizá los datos primero.")
        return

    try:
        with open(debug_path, "r", encoding="utf-8") as f:
            debug_log = json.load(f)
    except Exception as e:
        st.error(f"Error leyendo diagnóstico: {e}")
        return

    st.markdown(f"**{len(debug_log)} tickers registrados** en el último fetch.")

    # Filtro por ticker
    tickers_disponibles = sorted(debug_log.keys())
    ticker_sel = st.selectbox("Seleccionar ticker para ver diagnóstico:", tickers_disponibles)

    if ticker_sel and ticker_sel in debug_log:
        entry = debug_log[ticker_sel]

        col1, col2, col3 = st.columns(3)
        for col_ui, df_name in zip([col1, col2, col3], ["income", "balance", "cashflow"]):
            info = entry.get(df_name, {})
            with col_ui:
                st.markdown(f"**{df_name}**")
                status = info.get("status", "unknown")
                if status == "ok":
                    st.success(f"✅ OK — {info['shape'][0]} filas × {info['shape'][1]} cols")
                    st.caption("Columnas: " + ", ".join(str(c) for c in info.get("columns", [])))
                    with st.expander("Ver filas del índice"):
                        for row in info.get("index", []):
                            st.text(row)
                elif status == "empty":
                    st.warning("⚠️ DataFrame vacío")
                else:
                    st.error("❌ None (no devuelto)")

        st.markdown("**Medianas calculadas:**")
        medianas = entry.get("medianas_calculadas", {})
        meds_display = []
        for k, v in medianas.items():
            metrica = k.replace("_mediana", "").upper()
            valor = f"{v:.2f}" if v is not None else "❌ None"
            meds_display.append({"Métrica": metrica, "Mediana": valor})
        st.dataframe(pd.DataFrame(meds_display), use_container_width=False, hide_index=True)

        # Mostrar JSON completo
        with st.expander("Ver JSON completo"):
            st.json(entry)

    # Resumen de problemas detectados
    st.markdown("---")
    st.markdown("**Resumen de tickers con problemas:**")
    problemas = []
    for tk, entry in debug_log.items():
        meds = entry.get("medianas_calculadas", {})
        faltantes = [k.replace("_mediana", "").upper() for k, v in meds.items() if v is None]
        inc_status = entry.get("income", {}).get("status", "unknown")
        bal_status = entry.get("balance", {}).get("status", "unknown")
        cf_status = entry.get("cashflow", {}).get("status", "unknown")
        if faltantes:
            problemas.append({
                "Ticker": tk,
                "Income": "✅" if inc_status == "ok" else "❌",
                "Balance": "✅" if bal_status == "ok" else "❌",
                "Cashflow": "✅" if cf_status == "ok" else "❌",
                "Medianas faltantes": ", ".join(faltantes),
            })
    if problemas:
        st.dataframe(pd.DataFrame(problemas), use_container_width=True, hide_index=True)
    else:
        st.success("✅ No se detectaron problemas en los tickers analizados.")


if __name__ == "__main__":
    main()
