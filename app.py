"""
CEDEAR Screener — App principal Streamlit
Detecta CEDEARs potencialmente infravalorados usando métricas fundamentales
y técnicas de Stock Analysis y Yahoo Finance (caché que se actualiza una vez por trimestre).

Ejecutar: streamlit run app.py
"""

APP_VERSION = "1.2.63"

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
from ui.marca import CSS as CSS_MARCA, icono_pagina, encabezado_html, pie_html, css_nav
from ui import noticias as _noticias
from ui.cajas import CSS as CSS_CAJAS
from ui.exportar import excel_bytes
from ui import estado as estado_url
from ui.logos import logo_html
try:
    from config.ajustes import NOMBRE_APP
except ImportError:      # ajustes.py viejo
    NOMBRE_APP = "TodoCedears"
from ui.tabla_visual import (CSS as CSS_VISUAL, escala_valoracion_html, COLUMNAS_BASE, columnas_base, css_encabezado, html_tabla_visual,
                             ayuda_texto, anchos as anchos_tabla, _mayusculas)
from ui import criterios as _criterios
from ui import variables as _variables
from ui.ficha import ficha_html, texto_fuente, CSS as CSS_FICHA
from ui.quienes import quienes_html, CSS as CSS_QUIENES
from ui import ficha as _ficha
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


@st.cache_data(ttl=max(1, int(PRECIOS_MINUTOS_CACHE)) * 60, show_spinner=False)
def _precios_usd(tickers: tuple) -> dict:
    """Precios en dolares de todas las empresas (un solo pedido a Yahoo; las que falten, a Stock Analysis). Si falla, {'usd': {}} y la app
    sigue con el precio del cache."""
    try:
        return _pv.bajar_usd(tickers)
    except Exception:  # noqa: BLE001
        return {"usd": {}, "fecha": None, "hora": _pv.hora_texto(), "fuente": {}}


@st.cache_data(ttl=max(1, int(PRECIOS_MINUTOS_CACHE)) * 60, show_spinner=False)
def _precios_ars(items: tuple) -> dict:
    """Precios en pesos de los CEDEARs: items = ((ticker, (simbolos de Yahoo...), simbolo de BYMA), ...). Devuelve
    {ticker: [(fuente, pesos), ...]} con los de Yahoo y el de Rava (sin controlar: ver _pv.elegir_ars). Si falla, {}."""
    try:
        return _pv.bajar_ars_fuentes({t: list(ss) for t, ss, _ in items}, {t: b for t, _, b in items})
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
    from concurrent.futures import ThreadPoolExecutor
    m = _memo_extras()
    hit = m.get(("emp", ticker))
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    vacio = {"historial": None, "dividendos": {}, "gobierno": {}, "noticias": [], "agenda": {}, "estados": {}, "sp": None}
    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_hist, f_paq = ex.submit(_hp.bajar, ticker), ex.submit(_yx.bajar_paquete, ticker)
            paq = f_paq.result(timeout=90) or {}
            res = {"historial": f_hist.result(timeout=60), "sp": None}
        res.update({k: paq.get(k) or vacio[k] for k in ("dividendos", "gobierno", "noticias", "agenda", "estados")})
    except Exception:  # noqa: BLE001
        res = dict(vacio)
        paq = {}
    # v1.2.59: lo que Yahoo no contesto desde la nube se completa con el archivo data/paquetes_yahoo.json (lo baja bajar_paquetes_yahoo.bat)
    guardado, fecha_g = _paquetes_guardados()
    res, usadas = _py.completar(res, guardado.get(ticker.upper()))
    res["archivo"] = {"fecha": fecha_g, "claves": usadas, "foto": (guardado.get(ticker.upper()) or {}).get("foto_ceo")} if usadas or guardado.get(ticker.upper()) else None
    if res["historial"] or paq.get("info_ok") or res["gobierno"] or res["dividendos"]:
        if len(m) > 300:
            m.clear()
        m[("emp", ticker)] = (time.time(), res)
    return res


@st.cache_data(ttl=3600, show_spinner=False)
def _paquetes_guardados():
    """({TICKER: datos}, fecha) del archivo data/paquetes_yahoo.json; ({}, None) si no esta."""
    try:
        return _py.cargar()
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
    from data import foto_ceo as _fc
    url = _fc.buscar_foto(nombre, empresa)
    if url:
        memo[k] = url
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
        with st.container(key="vars_chips" if i_g == 0 else "vars_chips_mult"):
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
    pares = st.columns(2)
    turno = [0]

    def caja(clave, titulo, unidad=""):
        """Recuadro de los filtros de una variable, en la columna que toca (de izquierda a derecha)."""
        col = pares[turno[0] % 2]
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
        with caja(f"crit_{k}", c["nombre"], c["unidad"] if c["unidad"] == "%" else "veces"):
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


def render_pagina_etfs(busqueda=""):
    """Tabla de ETFs (v1.2.63): categorias para filtrar (botones), la busqueda de la barra y la tabla. Sin archivo, un cartel."""
    from data import etfs as _etfs
    from ui import etfs as _ui_etfs
    from ui.banderas import css_banderas as _css_b
    todos = _etfs.cargar()
    if not todos:
        st.markdown(f"<style>{css_fuente()}{css_condensada()}{CSS_QUIENES}</style>"
                    '<div class="qs" style="text-align:center"><h1 style="margin-bottom:10px">ETFs</h1>'
                    '<p>Estamos preparando la tabla de ETFs. Muy pronto la vas a poder ver acá, igual que la de empresas.</p></div>', unsafe_allow_html=True)
        return
    cats = _etfs.categorias(todos)
    sel = []
    try:
        st.markdown(f"<style>{css_fuente()}{css_condensada()}{_ui_etfs.CSS}{CSS_PILLS}</style>" + _css_b()
                    + _ui_etfs.encabezado_html(len(todos), len(_etfs.filtrar(todos, busqueda, st.session_state.get("etf_cats") or ()))), unsafe_allow_html=True)
        sel = st.pills("Categoría", cats, selection_mode="multi", key="etf_cats", label_visibility="collapsed") or []
    except Exception:  # noqa: BLE001
        sel = []
    st.markdown(_ui_etfs.tabla_html(_etfs.filtrar(todos, busqueda, sel)), unsafe_allow_html=True)


def _ir_a_tabla(tabla):
    """Botones "Empresas" / "ETFs" de la franja (v1.2.60): cambian de tabla dentro de la misma sesion (cambian la URL, pero la pagina no se recarga)."""
    st.query_params.clear()
    if tabla == "etfs":
        st.query_params["tabla"] = "etfs"


def render_nav_tablas():
    with st.container(key="nav_tablas"):
        for clave, texto in (("emp", "Empresas"), ("etfs", "ETFs")):
            args = dict(key=f"nav_{clave}", on_click=_ir_a_tabla, args=("etfs" if clave == "etfs" else "empresas",))
            try:
                st.button(texto, type="tertiary", **args)
            except TypeError:       # Streamlit viejo, sin type="tertiary"
                st.button(texto, **args)


def _enviar_busqueda():
    """Al buscar desde la pagina de una empresa (o Quienes somos) se vuelve a la tabla de empresas con la busqueda aplicada (v1.2.60)."""
    if st.query_params.get("tabla") != "etfs" and ("empresa" in st.query_params or "pagina" in st.query_params):
        st.query_params.clear()


def render_buscador(tabla="empresas") -> str:
    """Buscador de arriba de la tabla (v1.2.47): una lupa y "Buscar empresas por nombre o ticker". Busca de las dos formas, sin importar
    mayusculas, tildes ni signos (Enter para buscar). Devuelve el texto escrito."""
    # v1.2.51: sin el contador "0/40"; la lupa es el boton que envia la busqueda (Enter tambien)
    with st.container(key="buscador"):
        with st.form("form_busqueda", border=False, clear_on_submit=False):
            texto = st.text_input("Buscar empresas por nombre o ticker", key="flt_busqueda",
                                  placeholder="Buscar ETF o ticker" if tabla == "etfs" else "Buscar empresa o ticker", label_visibility="collapsed")
            st.form_submit_button("Buscar", icon=":material/search:", on_click=_enviar_busqueda)
        return (texto or "").strip()


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
    st.markdown(f"<style>{css_encabezado(sort_col, len(extras), visibles, bool(sort_asc))}</style>", unsafe_allow_html=True)

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
    titulos = [(clave, etiqueta) for clave, etiqueta, _ in columnas_base(visibles)] + [(c["clave"], c["nombre"].split(" (")[0]) for c in extras]
    for contenedor, (clave, etiqueta) in zip(cols, titulos):
        activo = sort_col == clave
        if contenedor.button(etiqueta, key=f"tvh_{clave}", use_container_width=True, help=ayuda_texto(clave, fecha) or None):
            if activo:
                st.session_state["sort_asc"] = not sort_asc
            else:
                st.session_state["sort_col"] = clave
                st.session_state["sort_asc"] = (clave in ("nombre", "ticker", "sector_txt"))
            st.rerun()
    st.markdown(html_tabla_visual(df_show, estado, extras, visibles), unsafe_allow_html=True)


def _boton_excel(df_show, fecha, aviso, extras=(), visibles=None):
    """Boton "Descargar la tabla en Excel" (v1.2.49; arriba de la tabla, a la derecha): las empresas y columnas que se ven, con los filtros y el
    orden elegidos. Si algo falla, no se muestra."""
    try:
        datos = excel_bytes(df_show, fecha, aviso, APP_VERSION, extras, visibles)
    except Exception:  # noqa: BLE001
        return
    dia = (fecha or datetime.now().strftime("%d/%m/%Y")).replace("/", "-")
    args = dict(data=datos, file_name=f"todocedears_{dia}.xlsx", key="descarga_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore",
                help="Baja un archivo .xlsx con la tabla tal como la ves ahora: las empresas que quedaron con tus filtros, en el orden elegido y con las variables que tenés a la vista. Es información, no una recomendación.")
    try:
        st.download_button("⬇ Descargar la tabla en Excel", type="tertiary", **args)
    except TypeError:       # Streamlit viejo, sin type="tertiary"
        st.download_button("⬇ Descargar la tabla en Excel", **args)


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
            st.markdown('<div class="tv-ley">Presioná en la empresa para información detallada.</div>', unsafe_allow_html=True)
            _boton_excel(df_show, fecha, aviso, extras, visibles)
    render_tabla_visual(df_show, filtros.get("estado_url"), fecha, extras, visibles)


# ---------------------------------------------------------------------------
# PANEL DE DETALLE POR EMPRESA
# ---------------------------------------------------------------------------

def _render_grafico(tk, pares, rd):
    """Solapa "Grafico y rendimiento": selector 1D, 5D, 1M, 3M, YTD, 1A, 5A y MAX y grafico interactivo (zoom con la rueda, arrastrar y ver el valor al pasar el
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
    # v1.2.51: "Volver" lleva siempre al inicio (tabla sin filtros), igual que tocar el titulo
    st.markdown('<a class="emp-vol" href="?" target="_self">← Volver al Inicio</a>', unsafe_allow_html=True)
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
    nombres = ["Resumen", "Análisis fundamental", "Gráfico y rendimiento", "Valuación", "Estados Financieros", "Dividendos", "Competidores", "Directivos", "Accionariado", "Noticias"]
    t_res, t_ana, t_gra, t_val, t_est, t_div, t_com, t_dir, t_acc, t_not = st.tabs(nombres)
    with t_res:
        st.markdown(_ficha.con_intro("resumen", _ficha.tab_resumen(rd, ficha, mercado, agenda=extra.get("agenda"))), unsafe_allow_html=True)
    with t_ana:
        st.markdown(_ficha.con_intro("analisis", _ficha.tab_analisis(rd)), unsafe_allow_html=True)
    with t_gra:
        st.markdown(_ficha.con_intro("grafico", _ficha.tab_grafico_tabla(pares)), unsafe_allow_html=True)      # v1.2.53: los rendimientos van arriba del grafico
        _render_grafico(tk, pares, rd)
    with t_val:
        st.markdown(_ficha.con_intro("valuacion", _ficha.tab_valuacion(rd, ficha, anuales=(_multiplos_anuales_datos() or {}).get(tk))), unsafe_allow_html=True)
    with t_est:
        st.markdown(_ficha.con_intro("estados", _ficha.tab_estados(extra.get("estados"))), unsafe_allow_html=True)
        _nota_archivo(extra, "estados")
    with t_div:
        div = extra.get("dividendos") or {}
        rec = {"dividendo": _hp.dividendo_recesion((div.get("trayectoria") or {}).get("anuales"))}
        st.markdown(_ficha.con_intro("dividendos", _ficha.tab_dividendos(rd, div, rec)), unsafe_allow_html=True)
        _nota_archivo(extra, "dividendos")
    with t_com:
        st.markdown(_ficha.con_intro("competidores", _ficha.tab_competidores(rd, df)), unsafe_allow_html=True)
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


def render_noticias(df, descarga, lugar=None):
    """Recuadro "Noticias Calientes": titulares ordenados con la regla de ui/noticias.py. Nunca rompe la pagina."""
    if not _noticias.ACTIVAS:
        return
    try:
        crudo = _noticias.esperar(descarga)
        bloques = _noticias.traducir_bloques(_noticias.ordenar_bloques(crudo, list(df["ticker"])))
        cuerpo = f"<style>{_noticias.CSS}</style>" + _noticias.noticias_bloques_html(bloques)
        (lugar if lugar is not None else st).markdown(cuerpo, unsafe_allow_html=True)
    except Exception:  # noqa: BLE001
        pass


def main():
    # Cargar universo de tickers
    universe = load_custom_tickers()
    universe_key = str(sorted([t for ts in universe.values() for t in ts]))

    # Franja negra de arriba con el nombre (y los iconos y el menu si estan cargados sus links). El aviso y "Datos al ..." van
    # al final de la pagina (pie_html).
    en_etfs = st.query_params.get("tabla") == "etfs"
    en_quienes = st.query_params.get("pagina") == "quienes"
    activa = "etfs" if en_etfs else ("" if en_quienes else "empresas")
    st.markdown(f"<style>{CSS_MARCA}{css_nav(activa)}{CSS_BUSQUEDA}</style>" + encabezado_html(NOMBRE_APP), unsafe_allow_html=True)
    # v1.2.60: "Empresas" y "ETFs" (botones) y el buscador estan en todas las paginas (el de la home se dibuja mas abajo, con la tabla)
    render_nav_tablas()
    busqueda_top = ""
    if en_etfs or en_quienes or st.query_params.get("empresa"):
        busqueda_top = render_buscador("etfs" if en_etfs else "empresas")
    aviso = texto_aviso_legal()
    fecha = None

    # v1.2.49: pagina "Quiénes somos" (?pagina=quienes): no necesita los datos de las empresas, asi que se muestra al toque
    if st.query_params.get("pagina") == "quienes":
        st.markdown(f"<style>{css_fuente()}{css_condensada()}{CSS_QUIENES}</style>" + quienes_html(), unsafe_allow_html=True)
        st.markdown(pie_html(APP_VERSION, aviso=aviso), unsafe_allow_html=True)
        return

    # v1.2.63: tabla de ETFs (data/etfs.csv, la arma Guille de a poco); el buscador de la barra filtra por ticker, descripcion y categoria
    if en_etfs:
        render_pagina_etfs(busqueda_top)
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
            df_p, n_p = _pv.aplicar_precios(df, info_p.get("usd") or {}, info_p.get("fecha"), info_p.get("hora"), info_p.get("fuente"))
            if n_p:
                df = df_p
                f_p = info_p.get("fecha")
                # v1.2.48: el pie no dice de que fuente vino cada precio (dato interno nuestro): solo la fecha y la hora
                texto_precios = (f"Precios en dólares al <b>{f_p.strftime('%d/%m/%Y')}</b> (consultados {info_p.get('hora')})" if f_p
                                 else f"Precios en dólares (consultados {info_p.get('hora')})")
        except Exception:  # noqa: BLE001
            pass

    cargando_inicio.empty()
    if df is None or df.empty:
        st.error("No se pudieron cargar datos. Intentá de nuevo en unos minutos.")
        st.markdown(pie_html(APP_VERSION, aviso=aviso, datos_al=fecha, precios=texto_precios), unsafe_allow_html=True)
        st.stop()

    # Estilos de la tabla, de la escala, de la pagina de empresa y de las banderas (una sola vez por pagina)
    st.markdown(f"<style>{css_fuente()}{CSS_VISUAL}{CSS_FICHA}{css_condensada()}</style>", unsafe_allow_html=True)
    st.markdown(css_banderas(), unsafe_allow_html=True)

    # Pagina de una empresa (se abre al tocar su nombre en la tabla): ?empresa=TICKER
    empresa = st.query_params.get("empresa")
    if empresa:
        fuente_emp = render_pagina_empresa(df, empresa, fecha)
        st.markdown(pie_html(APP_VERSION, aviso=aviso, datos_al=fecha, precios=texto_precios, fuente=fuente_emp or texto_fuente()), unsafe_allow_html=True)
        return

    # v1.2.45: "Noticias Calientes" y "Filtro de empresas" (antes "Screener") van uno al lado del otro, para ocupar menos pantalla.
    # Cada uno se despliega hacia abajo, en su mitad; la mitad que se abre se ensancha un poco (ui/cajas.py). En el celular quedan
    # uno abajo del otro. Si ya estaban bajadas (se guardan 15 minutos) las noticias se dibujan al toque; si hay que esperar a la
    # fuente, el lugar queda reservado y se completa al final, sin hacer esperar a la tabla.
    st.markdown(f"<style>{CSS_CAJAS}</style>", unsafe_allow_html=True)
    hay_gris = "categoria" in df.columns and bool((df["categoria"] == "DATOS INSUFICIENTES").any())
    noticias_pendientes = descarga_noticias is not None
    with st.container(key="fila_cajas"):
        if _noticias.ACTIVAS:
            col_noticias, col_filtro = st.columns(2, gap="medium")
            lugar_noticias = col_noticias.empty()
        else:
            col_filtro, lugar_noticias = st.container(), st.empty()
        if not noticias_pendientes:
            render_noticias(df, None, lugar_noticias)
        # Filtro de empresas: recuadro desplegable, cerrado al abrir la pagina. Adentro: los filtros, la escala de valoracion y
        # las variables a ver en la tabla. Cerrado, los filtros siguen valiendo: solo se esconden.
        with col_filtro:
            with st.container(key="caja_screener"):
                with st.expander("Filtro de empresas", expanded=False):
                    filtros = render_filtros_inline(universe, df)
                    st.markdown(escala_valoracion_html(hay_gris), unsafe_allow_html=True)

    # v1.2.47: buscador (por nombre o ticker; desde la v1.2.49 sube a la franja negra en pantallas anchas) y, despues, la tabla
    busqueda = render_buscador()
    # v1.2.49: ya no hay "Cómo leer la tabla" (cada título explica su columna al pasar el mouse); el Excel va arriba de la tabla, a la derecha
    lugar_excel = st.container(key="fila_excel")
    render_main_table(df, filtros, fecha, aviso, lugar_excel, busqueda)

    if noticias_pendientes:
        render_noticias(df, descarga_noticias, lugar_noticias)

    # Seguimiento (historial del caché)
    render_seguimiento()

    # Panel de diagnóstico (solo visible si ?debug=1 en la URL)
    render_debug_panel()

    st.markdown(pie_html(APP_VERSION, aviso=aviso, datos_al=fecha, precios=texto_precios, fuente=texto_fuente()), unsafe_allow_html=True)


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
