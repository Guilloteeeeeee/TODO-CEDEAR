"""
CEDEAR Screener — App principal Streamlit
Detecta CEDEARs potencialmente infravalorados usando métricas fundamentales
y técnicas de Stock Analysis y Yahoo Finance (caché que se actualiza una vez por trimestre).

Ejecutar: streamlit run app.py
"""

APP_VERSION = "1.2.47"

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
from config.sectors import TICKER_UNIVERSE, TICKER_TO_SECTOR, SECTOR_CONFIG, etiqueta_sector, PAIS_MANUAL, metricas_de, partes_sector
from config.industrias import industria_de
from ui.banderas import css_banderas, bandera_html
from ui.fuentes import css_fuente
from ui.marca import CSS as CSS_MARCA, icono_pagina, encabezado_html, pie_html
from ui import noticias as _noticias
from ui.cajas import CSS as CSS_CAJAS
from ui.exportar import excel_bytes
from ui import estado as estado_url
from ui.logos import logo_html
try:
    from config.ajustes import NOMBRE_APP
except ImportError:      # ajustes.py viejo
    NOMBRE_APP = "TodoCedears"
from ui.tabla_visual import (CSS as CSS_VISUAL, escala_valoracion_html, COLUMNAS_BASE, css_encabezado, html_tabla_visual,
                             como_leer_html, ayuda_texto, anchos as anchos_tabla, _mayusculas)
from ui import criterios as _criterios
from ui.ficha import ficha_html, CSS as CSS_FICHA
from data import cedears as _cedears, precios_vivos as _pv, fichas as _fichas

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
CACHE_TTL_HORAS = 6  # Refresca datos cada 6 horas


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
    if not os.path.exists(CACHE_FILE):
        return None, None
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
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


def _reiniciar_criterios():
    """Boton "Reiniciar criterios": saca todos los criterios agregados (y sus minimos y maximos)."""
    st.session_state["flt_criterios"] = []
    for c in _criterios.CRITERIOS:
        st.session_state.pop(f"crit_{c['clave']}_min", None)
        st.session_state.pop(f"crit_{c['clave']}_max", None)


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
    v1.2.47: todas las selecciones son menus desplegables; el Dividend Yield y el Fair Value ya no son filtros fijos: se suman desde
    "Agregar criterios" (cada criterio agrega una columna a la tabla y, si se escribe un minimo y/o un maximo, filtra).
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
                                      list(MKTCAP_OPCIONES), ORDENES_VALIDOS, todas_industrias, {c["clave"]: c["nombre"] for c in _criterios.CRITERIOS})
            for k, v in vals.items():
                st.session_state[k] = v

    # --- Sector, Industria, Valoracion y Pais: menus desplegables (sin seleccion = todos) ---
    col_sec, col_ind = st.columns(2)
    with col_sec:
        sectores_sel = st.multiselect("Sector", todos_sectores, placeholder="Todos los sectores", key="flt_sector")
    with col_ind:
        industrias_sel = st.multiselect("Industria", todas_industrias, placeholder="Todas las industrias", key="flt_industria")
    col_val, col_pais = st.columns(2)
    with col_val:
        cats_sel = st.multiselect("Valoración", cats_disponibles, format_func=lambda c: _mayusculas(nombre_corto(c)),
                                  placeholder="Todas las valoraciones", key="flt_valoracion")
    cats_nombres = list(cats_sel) or list(cats_disponibles)
    with col_pais:
        paises_sel = st.multiselect("País", paises_disponibles, placeholder="Todos los países", key="flt_pais")

    # --- Capitalizacion minima y metricas minimas ---
    col_mkt, col_met = st.columns(2)
    with col_mkt:
        mktcap_label = st.selectbox("Capitalización bursátil mínima", list(MKTCAP_OPCIONES.keys()), key="flt_mkt")
    mktcap_minimo = MKTCAP_OPCIONES[mktcap_label]
    with col_met:
        min_metricas = st.slider(
            "Métricas mínimas",
            min_value=1,
            max_value=4,
            key="flt_met",
            help="Si subís este número, las empresas con menos métricas se muestran en gris. "
                 "Con 1 se ve todo (mejor algo que nada).",
        )

    # --- Agregar criterios (v1.2.47): suman una columna a la tabla y, con minimo y/o maximo, filtran ---
    nombres_sel = st.multiselect(
        "Agregar criterios", _criterios.NOMBRES, key="flt_criterios",
        placeholder="Buscá y elegí datos para sumar a la tabla (Dividend Yield, Fair Value, P/E…)",
        help="Cada criterio que elijas suma una columna a la tabla. Si además escribís un mínimo y/o un máximo, quedan solo las empresas dentro de ese rango.")
    extras = [c for c in _criterios.CRITERIOS if c["nombre"] in nombres_sel]
    criterios = {}
    for c in extras:
        k = c["clave"]
        with st.container(border=True, key=f"crit_{k}"):
            st.markdown(f'<div class="crit-t">{html.escape(c["nombre"])} <span>({c["unidad"] if c["unidad"] == "%" else "veces"})</span></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            mn = c1.number_input("Mínimo", value=None, step=float(c["paso"]), format="%g", key=f"crit_{k}_min", placeholder="Mínimo", label_visibility="collapsed")
            mx = c2.number_input("Máximo", value=None, step=float(c["paso"]), format="%g", key=f"crit_{k}_max", placeholder="Máximo", label_visibility="collapsed")
        criterios[k] = (mn, mx)
    if extras:
        st.button("Reiniciar criterios", key="crit_reiniciar", type="tertiary", on_click=_reiniciar_criterios)

    # --- Actualizar ---
    forzar_refresh = st.button(
        "Actualizar datos",
        help="Vuelve a leer el caché guardado (el caché se actualiza una vez por trimestre desde la PC)",
    )

    # Texto con los filtros y el orden: viaja en el link de cada empresa para poder volver a la tabla tal cual estaba
    busqueda = st.session_state.get("flt_busqueda", "") or ""
    estado = estado_url.codificar(sectores_sel, todos_sectores, cats_nombres, cats_disponibles, paises_sel, mktcap_label,
                                  min_metricas, st.session_state.get("sort_col", ORDEN_INICIAL[0]), st.session_state.get("sort_asc", ORDEN_INICIAL[1]),
                                  busqueda, industrias_sel, todas_industrias, criterios)
    return {
        "estado_url": estado,
        "sectores": list(sectores_sel) or todos_sectores,
        "industrias": list(industrias_sel) or todas_industrias,
        "categorias": cats_nombres,
        "paises": paises_sel,
        "mktcap_minimo": mktcap_minimo,
        "min_metricas": min_metricas,
        "criterios": criterios,
        "extras": extras,
        "sort_col": st.session_state.get("sort_col", ORDEN_INICIAL[0]),
        "sort_asc": st.session_state.get("sort_asc", ORDEN_INICIAL[1]),
        "forzar_refresh": forzar_refresh,
    }


def render_buscador() -> str:
    """Buscador de arriba de la tabla (v1.2.47): una lupa y "Buscar empresas por nombre o ticker". Busca de las dos formas, sin importar
    mayusculas, tildes ni signos (Enter para buscar). Devuelve el texto escrito."""
    with st.container(key="buscador"):
        return (st.text_input("Buscar empresas por nombre o ticker", key="flt_busqueda", placeholder="Buscar empresas por nombre o ticker",
                              label_visibility="collapsed", max_chars=40) or "").strip()


# ---------------------------------------------------------------------------
# TABLA PRINCIPAL
# ---------------------------------------------------------------------------

def ordenes_movil(extras=()):
    """Opciones del selector "Ordenar por" (solo se ve en el celular, donde los titulos de la tabla no entran): (texto, columna, ascendente).
    Es el mismo orden que dan los titulos de la tabla en la computadora."""
    o = [
        ("Capitalización bursátil: de mayor a menor", "market_cap", False), ("Capitalización bursátil: de menor a mayor", "market_cap", True),
        ("Valoración: de más barata a más cara", "fv_upside", False), ("Valoración: de más cara a más barata", "fv_upside", True),
        ("Puntaje de calidad: de mayor a menor", "score_total", False), ("Puntaje de calidad: de menor a mayor", "score_total", True),
        ("Empresa: de la A a la Z", "nombre", True), ("Empresa: de la Z a la A", "nombre", False),
        ("Sector e industria: de la A a la Z", "sector_txt", True), ("Sector e industria: de la Z a la A", "sector_txt", False),
        ("Precio: de mayor a menor", "precio_actual", False), ("Precio: de menor a mayor", "precio_actual", True),
    ]
    for c in extras:
        o += [(f"{c['nombre']}: de mayor a menor", c["clave"], False), (f"{c['nombre']}: de menor a mayor", c["clave"], True)]
    return o


def _cambiar_orden_movil():
    """Al elegir un orden en el selector del celular se guarda como si se hubiera tocado el titulo de la tabla."""
    eleg = st.session_state.get("orden_movil")
    extras = [c for c in _criterios.CRITERIOS if c["nombre"] in (st.session_state.get("flt_criterios") or [])]
    for texto, col, asc in ordenes_movil(extras):
        if texto == eleg:
            st.session_state["sort_col"], st.session_state["sort_asc"] = col, asc
            return


def render_tabla_visual(df_show: pd.DataFrame, estado=None, fecha=None, extras=()):
    """Tabla visual: titulos ordenables (botones, con la explicacion al pasar el mouse) y filas en una sola pieza de HTML con la misma grilla."""
    sort_col = st.session_state.get("sort_col", ORDEN_INICIAL[0])
    sort_asc = st.session_state.get("sort_asc", ORDEN_INICIAL[1])
    st.markdown(f"<style>{css_encabezado(sort_col, len(extras))}</style>", unsafe_allow_html=True)

    # Celular: el selector reemplaza a los titulos (la hoja de estilos esconde uno u otro segun el ancho de la pantalla)
    opciones = ordenes_movil(extras)
    for texto, col, asc in opciones:
        if col == sort_col and asc == bool(sort_asc):
            st.session_state["orden_movil"] = texto
            break
    with st.container(key="orden_movil_caja"):
        st.selectbox("Ordenar por", [t for t, _, _ in opciones], key="orden_movil", on_change=_cambiar_orden_movil)

    cols = st.columns(anchos_tabla(len(extras)), gap="small")
    titulos = [(clave, etiqueta) for clave, etiqueta, _ in COLUMNAS_BASE] + [(c["clave"], c["nombre"].split(" (")[0]) for c in extras]
    for contenedor, (clave, etiqueta) in zip(cols, titulos):
        activo = sort_col == clave
        flecha = (" ▲" if sort_asc else " ▼") if activo else ""
        if contenedor.button(etiqueta + flecha, key=f"tvh_{clave}", use_container_width=True, help=ayuda_texto(clave, fecha) or None):
            if activo:
                st.session_state["sort_asc"] = not sort_asc
            else:
                st.session_state["sort_col"] = clave
                st.session_state["sort_asc"] = (clave in ("nombre", "ticker", "sector_txt"))
            st.rerun()
    st.markdown(html_tabla_visual(df_show, estado, extras), unsafe_allow_html=True)


def _boton_excel(df_show, fecha, aviso, extras=()):
    """Boton de descarga en Excel (v1.2.46: chico y sin relleno, dentro del Filtro de empresas): las empresas que se ven, con los
    filtros y el orden elegidos. Si algo falla, no se muestra."""
    try:
        datos = excel_bytes(df_show, fecha, aviso, APP_VERSION, extras)
    except Exception:  # noqa: BLE001
        return
    dia = (fecha or datetime.now().strftime("%d/%m/%Y")).replace("/", "-")
    args = dict(data=datos, file_name=f"todocedears_{dia}.xlsx", key="descarga_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore",
                help="Baja un archivo .xlsx con las empresas que ves ahora (con los filtros y el orden elegidos). Es información, no una recomendación.")
    try:
        st.download_button("⬇ Descargar lo que ves en Excel", type="tertiary", **args)
    except TypeError:       # Streamlit viejo, sin type="tertiary"
        st.download_button("⬇ Descargar lo que ves en Excel", **args)


def filtrar_ordenar(df: pd.DataFrame, filtros: dict, busqueda: str = "") -> pd.DataFrame:
    """Aplica el buscador, los filtros y los criterios agregados, y ordena. Devuelve las empresas que se ven, en el orden de la tabla."""
    df_show = _criterios.agregar_columnas(df)

    # --- Aplicar filtros ---
    df_show = df_show[df_show["sector_macro"].isin(filtros["sectores"])]
    df_show = df_show[df_show["industria"].isin(filtros["industrias"]) | (df_show["industria"] == "")]
    df_show = df_show[
        (df_show["metricas_usadas"] >= filtros["min_metricas"]) |
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
    # Criterios agregados (minimo / maximo)
    df_show = _criterios.filtrar(df_show, filtros.get("criterios"))

    # Buscador (v1.2.47): por nombre o ticker, sin importar mayusculas, tildes ni signos
    q = _normalizar(busqueda)
    if q:
        nombres = df_show["nombre"].map(_normalizar)
        tickers = df_show["ticker"].map(_normalizar)
        df_show = df_show[nombres.str.contains(q, regex=False) | tickers.str.contains(q, regex=False)]

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
    # El boton de Excel esta dentro del Filtro de empresas (v1.2.46)
    if lugar_excel is not None:
        with lugar_excel:
            _boton_excel(df_show, fecha, aviso, extras)
    render_tabla_visual(df_show, filtros.get("estado_url"), fecha, extras)


# ---------------------------------------------------------------------------
# PANEL DE DETALLE POR EMPRESA
# ---------------------------------------------------------------------------

def render_pagina_empresa(df: pd.DataFrame, ticker_sel: str):
    """Pagina de una empresa (se abre al tocar su nombre en la tabla: ?empresa=TICKER): resumen, barra del Fair Value y el desglose completo."""
    f = st.query_params.get("f")
    volver = "?" + (f"f={html.escape(str(f), quote=True)}" if f else "")
    st.markdown(f'<a class="emp-vol" href="{volver}" target="_self">← Volver a la tabla</a>', unsafe_allow_html=True)

    row = df[df["ticker"] == str(ticker_sel).upper()] if ticker_sel else df.iloc[0:0]
    if row.empty:
        st.warning("No encontré esa empresa. Volvé a la tabla y elegí otra.")
        return
    row = row.iloc[0]
    ticker_sel = row.get("ticker", ticker_sel)
    sector = row.get("sector", "")

    # v1.2.47: encabezado (logo, nombre, mercado, ticker, ADR, precio) y todos los datos en mosaicos (ui/ficha.py)
    ficha = (_fichas_datos() or {}).get(str(ticker_sel).upper()) or {}
    cod = None if (ficha.get("mercado_cod") or ficha.get("mercado_nombre")) else _mercado_vivo(str(ticker_sel))
    st.markdown(ficha_html(row.to_dict(), _datos_cedear(df, ticker_sel), ficha, cod), unsafe_allow_html=True)

    # Desglose de métricas
    if sector in SECTOR_CONFIG and row.get("detalle"):
        st.markdown("---")
        st.subheader("📊 Desglose de métricas")

        detalle = row.get("detalle", {})
        if isinstance(detalle, str):
            import ast
            detalle = ast.literal_eval(detalle)

        pesos_empresa = metricas_de(row, sector)   # v1.2.44: el PEG aparece solo si es creible para esta empresa
        metricas_cols = st.columns(len(pesos_empresa))

        METRIC_LABELS = {
            "ev_ebitda": "EV/EBITDA",
            "per": "P/E Ratio",
            "p_fcf": "P/FCF",
            "p_b": "P/Book",
            "dividend_yield": "Dividend Yield",
            "peg": "PEG",
            "p_ffo": "P/FFO",
            "p_affo": "P/AFFO",
            "ps": "P/S",
        }

        for i, (metrica, peso) in enumerate(pesos_empresa.items()):
            datos = detalle.get(metrica, {})
            if isinstance(datos, str):
                import ast
                datos = ast.literal_eval(datos)

            actual = datos.get("actual")
            mediana = datos.get("mediana")
            score_m = datos.get("score")
            estado_m = datos.get("estado")
            motivo_m = datos.get("motivo")
            fuente_m = datos.get("fuente")
            referencia_m = datos.get("referencia")

            label = METRIC_LABELS.get(metrica, metrica.upper())
            suffix = "%" if metrica == "dividend_yield" else ""

            with metricas_cols[i]:
                st.markdown(f"**{label}**")
                st.markdown(f"Peso: {peso*100:.0f}%")
                if metrica == "dividend_yield":
                    st.metric(
                        label="Actual",
                        value=format_metric(actual, suffix="%"),
                        delta=f"Mediana hist.: {format_metric(mediana, suffix='%')}",
                        delta_color="normal",
                    )
                else:
                    st.metric(
                        label="Actual",
                        value=format_metric(actual),
                        delta=f"Mediana hist.: {format_metric(mediana)}",
                        delta_color="inverse",
                    )
                if score_m is not None:
                    color_m = "#15803d" if score_m >= 60 else "#a16207" if score_m >= 40 else "#b91c1c"
                    st.markdown(
                        f'Score: <span style="color:{color_m};font-weight:700">{score_m:.0f}/100</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("Score: —")
                if estado_m == "ok" and (fuente_m or referencia_m == "sector"):
                    partes = []
                    if fuente_m:
                        partes.append(f"Fuente: {fuente_m}")
                    if referencia_m == "sector":
                        partes.append("comparada con la mediana de su sector (falta su historia propia)")
                    st.caption(" · ".join(partes))
                if estado_m == "descartada" and motivo_m:
                    st.caption(f"🚫 No se usa: {motivo_m}. Su peso se reparte entre las otras métricas.")
                elif estado_m == "sin dato":
                    st.caption("Sin dato para esta métrica. Su peso se reparte entre las otras.")

        usadas_d, total_d = row.get("metricas_usadas"), row.get("metricas_total")
        if _num_valido(usadas_d) and int(usadas_d) == 0:
            st.info(
                "Ninguna métrica fundamental pudo usarse para esta empresa. "
                "La categoría se calculó solo con la posición en el rango de 52 semanas."
            )

    # Aviso trampa de valor si el score es alto
    if row.get("score_total") and row.get("score_total") >= 65:
        st.warning(
            "⚠️ **Posible trampa de valor:** Una empresa con score alto no garantiza que esté infravalorada. "
            "El precio bajo puede reflejar deterioro real del negocio no capturado por los múltiplos históricos. "
            "Investigá los fundamentales antes de tomar una decisión."
        )


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
        notas, horas = _noticias.ordenar(crudo, list(df["ticker"]))
        notas = _noticias.traducir_notas(notas)
        hubo = bool(crudo and crudo.get("feeds_ok"))
        cuerpo = f"<style>{_noticias.CSS}</style>" + _noticias.noticias_html(notas, horas, hubo_respuesta=hubo)
        (lugar if lugar is not None else st).markdown(cuerpo, unsafe_allow_html=True)
    except Exception:  # noqa: BLE001
        pass


def main():
    # Cargar universo de tickers
    universe = load_custom_tickers()
    universe_key = str(sorted([t for ts in universe.values() for t in ts]))

    # Franja negra de arriba con el nombre (y los iconos y el menu si estan cargados sus links). El aviso y "Datos al ..." van
    # al final de la pagina (pie_html).
    st.markdown(f"<style>{CSS_MARCA}</style>" + encabezado_html(NOMBRE_APP), unsafe_allow_html=True)
    aviso = texto_aviso_legal()
    fecha = None

    # Noticias: la descarga arranca ya, en segundo plano, mientras se cargan los datos de las empresas
    descarga_noticias = _noticias.iniciar_descarga()

    # Cargar datos
    with st.spinner("Cargando datos..."):
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
            with st.spinner("Actualizando precios..."):
                info_p = _precios_usd(_orden_tickers(df))
            df_p, n_p = _pv.aplicar_precios(df, info_p.get("usd") or {}, info_p.get("fecha"), info_p.get("hora"), info_p.get("fuente"))
            if n_p:
                df = df_p
                f_p = info_p.get("fecha")
                n_sa = sum(1 for v in (info_p.get("fuente") or {}).values() if v == _pv.FUENTE_SA)
                extra_sa = f"; {n_sa} desde {_pv.FUENTE_SA}, de respaldo" if n_sa else ""
                texto_precios = (f"Precios en dólares de Yahoo Finance al <b>{f_p.strftime('%d/%m/%Y')}</b> (consultados {info_p.get('hora')}{extra_sa})" if f_p
                                 else f"Precios en dólares de Yahoo Finance (consultados {info_p.get('hora')}{extra_sa})")
        except Exception:  # noqa: BLE001
            pass

    if df is None or df.empty:
        st.error("No se pudieron cargar datos. Intentá de nuevo en unos minutos.")
        st.markdown(pie_html(APP_VERSION, aviso=aviso, datos_al=fecha, precios=texto_precios), unsafe_allow_html=True)
        st.stop()

    # Estilos de la tabla, de la escala, de la pagina de empresa y de las banderas (una sola vez por pagina)
    st.markdown(f"<style>{css_fuente()}{CSS_VISUAL}{CSS_FICHA}</style>", unsafe_allow_html=True)
    st.markdown(css_banderas(), unsafe_allow_html=True)

    # Pagina de una empresa (se abre al tocar su nombre en la tabla): ?empresa=TICKER
    empresa = st.query_params.get("empresa")
    if empresa:
        render_pagina_empresa(df, empresa)
        st.markdown(pie_html(APP_VERSION, aviso=aviso, datos_al=fecha, precios=texto_precios), unsafe_allow_html=True)
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
        # "Cómo leer la tabla". Cerrado, los filtros siguen valiendo: solo se esconden.
        with col_filtro:
            with st.container(key="caja_screener"):
                with st.expander("Filtro de empresas", expanded=False):
                    filtros = render_filtros_inline(universe, df)
                    lugar_excel = st.container()
                    st.markdown(escala_valoracion_html(hay_gris), unsafe_allow_html=True)

    # Forzar refresh limpia el cache de Streamlit
    if filtros["forzar_refresh"]:
        st.cache_data.clear()
        st.rerun()

    # v1.2.47: buscador (por nombre o ticker) y "Cómo leer la tabla" arriba de la tabla; despues, la tabla
    busqueda = render_buscador()
    st.markdown(como_leer_html(filtros.get("extras") or []), unsafe_allow_html=True)
    render_main_table(df, filtros, fecha, aviso, lugar_excel, busqueda)

    if noticias_pendientes:
        render_noticias(df, descarga_noticias, lugar_noticias)

    # Seguimiento (historial del caché)
    render_seguimiento()

    # Panel de diagnóstico (solo visible si ?debug=1 en la URL)
    render_debug_panel()

    st.markdown(pie_html(APP_VERSION, aviso=aviso, datos_al=fecha, precios=texto_precios), unsafe_allow_html=True)


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
