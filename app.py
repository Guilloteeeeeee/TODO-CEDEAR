"""
CEDEAR Screener — App principal Streamlit
Detecta CEDEARs potencialmente infravalorados usando métricas fundamentales
y técnicas de Stock Analysis y Yahoo Finance (caché que se actualiza una vez por trimestre).

Ejecutar: streamlit run app.py
"""

APP_VERSION = "1.2.31"

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
from scoring.engine import score_dataframe, leyenda_categorias, COLOR_POR_CATEGORIA
from scoring.seguimiento import (cargar_copias, evaluar_copias, proxima_medicion, CATEGORIAS_ORDEN,
                                 MIN_DIAS_ENTRE_COPIAS)
from config.sectors import TICKER_UNIVERSE, TICKER_TO_SECTOR, SECTOR_CONFIG, etiqueta_sector, PAIS_MANUAL
from ui.banderas import css_banderas, bandera_html
from ui.tabla_visual import (CSS as CSS_VISUAL, celda_valoracion, sector_html, escala_valoracion_html,
                             texto_categoria, ANCHOS_VISUAL, css_encabezado, html_tabla_visual)

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CEDEAR Screener",
    page_icon="📊",
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
        ts_str = ts_cache.strftime("%d/%m %H:%M") if ts_cache else "?"
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
            ts_str = ts_viejo.strftime("%d/%m %H:%M") if ts_viejo else "?"
            return df_viejo, f"cache_vencido|{e}|{ts_str}"
        raise


# ---------------------------------------------------------------------------
# HELPERS DE VISUALIZACIÓN
# ---------------------------------------------------------------------------

def render_52w_bar(posicion: float | None) -> str:
    """
    Genera una barra HTML del rango 52 semanas.
    posicion: 0.0 (mínimo del año) a 1.0 (máximo del año)
    """
    if posicion is None or (isinstance(posicion, float) and (posicion != posicion)):
        return "—"
    try:
        pct = int(float(posicion) * 100)
    except (TypeError, ValueError):
        return "—"
    color = "#64748b"   # v1.2.22: un solo color (gris azulado), sin semaforo

    return (
        f'<div style="display:flex;align-items:center;gap:6px;min-width:120px">'
        f'<div style="background:#e1e4e8;border-radius:4px;height:10px;width:80px;position:relative;">'
        f'<div style="background:{color};width:{pct}%;height:100%;border-radius:4px;"></div>'
        f'</div>'
        f'<span style="font-size:12px;color:#57606a">{pct}%</span>'
        f'</div>'
    )


def render_categoria_badge(categoria: str, color_hex: str) -> str:
    """Badge HTML para mostrar la categoría con color (sin circulitos ni cuadraditos)."""
    return (
        f'<span style="background:{color_hex}22;color:{texto_categoria(color_hex)};'
        f'border:1px solid {color_hex}88;border-radius:12px;'
        f'padding:2px 10px;font-size:12px;font-weight:700;white-space:nowrap">'
        f'{categoria}</span>'
    )


def format_metric(val: float | None, decimals: int = 1, suffix: str = "") -> str:
    """Formatea una métrica para mostrar en tabla."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if suffix == "%":
        return f"{val * 100:.1f}%"
    return f"{val:.{decimals}f}{suffix}"


def format_market_cap(val: float | None) -> str:
    """Formatea market cap en billones/millones."""
    if val is None or pd.isna(val):
        return "—"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:.0f}"


# Países (Yahoo los entrega en inglés) → castellano. Si aparece uno que no está, se muestra tal cual.
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


# --- Vista de diagnóstico: métodos del Fair Value (se activa con el casillero de los filtros) ---
FV_LABELS = {
    "ev_ebitda": "EV/EBITDA", "per": "PER", "p_fcf": "P/FCF", "p_b": "P/B",
    "dividend_yield": "DY", "peg": "PEG", "p_ffo": "P/FFO", "p_affo": "P/AFFO",
}


def _num_valido(x) -> bool:
    return x is not None and not pd.isna(x)


def _motivo_metodo_faltante(row, metrica: str) -> str:
    """Por qué un método del sector no aportó precio al Fair Value."""
    descartados = row.get("fair_value_descartados")
    if isinstance(descartados, dict) and descartados.get(metrica):
        return str(descartados[metrica])
    mediana = row.get(f"{metrica}_mediana")
    actual = row.get(f"{metrica}_actual")
    if metrica == "dividend_yield":
        div = row.get("annual_dividend")
        if not (_num_valido(div) and div > 0) and not (_num_valido(actual) and actual > 0):
            return "no paga dividendo"
    if not _num_valido(mediana) or mediana <= 0:
        return "sin mediana histórica"
    if metrica != "dividend_yield" and (not _num_valido(actual) or actual <= 0):
        return "sin dato actual"
    return "sin precio implícito válido"


def _metodos_fv_html(row) -> str:
    """Una línea por método esperado del sector: ✓ con su precio implícito, o ✗ con el motivo."""
    esperados = SECTOR_CONFIG.get(row.get("sector"), {}).get("metrics", {})
    if not esperados:
        return "—"
    detalle = row.get("fair_value_detalle")
    detalle = detalle if isinstance(detalle, dict) else {}
    precio = row.get("precio_actual")
    lineas = []
    for metrica, peso in esperados.items():
        label = FV_LABELS.get(metrica, metrica)
        d = detalle.get(metrica)
        if d and _num_valido(d.get("precio")):
            pm = d["precio"]
            extra, color = "", "#57606a"
            if _num_valido(precio) and precio > 0:
                up = (pm - precio) / precio
                color = "#15803d" if up > 0.05 else "#b91c1c" if up < -0.05 else "#a16207"
                extra = f" ({up * 100:+.0f}%)"
            lineas.append(
                f'<span style="color:{color};font-weight:600" title="peso {peso * 100:.0f}%">'
                f'✓ {label} ${pm:,.2f}{extra}</span>'
            )
        else:
            motivo = _motivo_metodo_faltante(row, metrica)
            lineas.append(
                f'<span style="color:#8c959f" title="peso {peso * 100:.0f}%">'
                f'✗ {label} — <i>{motivo}</i></span>'
            )
    n_ok = sum(1 for m in esperados if detalle.get(m) and _num_valido(detalle[m].get("precio")))
    color_n = "#57606a" if n_ok >= len(esperados) else "#bf8700" if n_ok >= 3 else "#b91c1c"
    cabecera = f'<span style="color:{color_n};font-weight:700">{n_ok}/{len(esperados)} métodos</span>'
    return (
        '<div style="font-size:11px;line-height:1.35">' + cabecera + "<br>" + "<br>".join(lineas) + "</div>"
    )


def _resumen_cobertura_fv(df_show: pd.DataFrame) -> str:
    """Resumen de cuántas empresas pudieron usar cada método (sobre las empresas visibles)."""
    usados, esperados_n, por_cant = {}, {}, {}
    for _, r in df_show.iterrows():
        esperados = list(SECTOR_CONFIG.get(r.get("sector"), {}).get("metrics", {}))
        det = r.get("fair_value_detalle")
        det = det if isinstance(det, dict) else {}
        ok = 0
        for m in esperados:
            esperados_n[m] = esperados_n.get(m, 0) + 1
            if m in det:
                usados[m] = usados.get(m, 0) + 1
                ok += 1
        clave = (ok, len(esperados))
        por_cant[clave] = por_cant.get(clave, 0) + 1
    por_metodo = " · ".join(
        f"<b>{FV_LABELS.get(m, m)}</b> {usados.get(m, 0)}/{n}"
        for m, n in sorted(esperados_n.items(), key=lambda x: -x[1])
    )
    por_empresa = " · ".join(
        f"{ok}/{tot} métodos: <b>{n}</b>"
        for (ok, tot), n in sorted(por_cant.items(), key=lambda x: (-x[0][0], x[0][1]))
    )
    return (
        '<div style="font-size:12px;color:#57606a;background:#f6f8fa;border:1px solid #d0d7de;'
        'border-radius:6px;padding:8px 12px;margin-bottom:6px">'
        '🔬 <b>Cobertura de métodos del Fair Value</b> (empresas visibles)<br>'
        f'Por método (empresas que lo pudieron usar / donde aplica): {por_metodo}<br>'
        f'Por empresa: {por_empresa}'
        '</div>'
    )


def get_logo_url(ticker: str) -> str:
    """URL (o data URI) del logo de un ticker; vacio si solo hay iniciales. Ver ui/logos.py."""
    from ui.logos import logo_url
    return logo_url(ticker) or ""


def format_fair_value(fv: float | None, precio: float | None) -> tuple[str, str]:
    """
    Retorna (texto, color) para el Fair Value.
    Muestra el precio y el upside/downside vs precio actual.
    """
    if fv is None or precio is None or pd.isna(fv) or pd.isna(precio) or precio <= 0:
        return "—", "#6e7781"
    upside = (fv - precio) / precio
    color = "#374151"   # v1.2.22: sin semaforo; el color queda solo para la categoria
    upside_str = f"+{upside*100:.0f}%" if upside >= 0 else f"{upside*100:.0f}%"
    return f"${fv:.2f} ({upside_str})", color


# ---------------------------------------------------------------------------
# FILTROS INLINE (reemplaza sidebar)
# ---------------------------------------------------------------------------

def _pastillas(etiqueta, opciones, formato, key):
    """Filtro en pastillas (st.pills, Streamlit 1.40+). Sin seleccion = todas. Si la version es vieja, usa un selector multiple."""
    if hasattr(st, "pills"):
        sel = st.pills(etiqueta, opciones, selection_mode="multi", format_func=formato, key=key,
                       label_visibility="collapsed")
        return list(sel or [])
    return st.multiselect(etiqueta, opciones, format_func=formato, key=key, label_visibility="collapsed",
                          placeholder="Todas")


def render_filtros_inline(universe: dict, df: pd.DataFrame = None) -> dict:
    """
    Renderiza los filtros encima de la tabla (sin sidebar) y retorna dict con filtros activos.
    """
    leyenda = leyenda_categorias()

    # --- Sector / Industria y Valoración: pastillas (sin selección = todas) ---
    todos_sectores = sorted(universe.keys(), key=etiqueta_sector)
    st.markdown('<div class="flt-t">Sector / Industria</div>', unsafe_allow_html=True)
    sectores_sel = _pastillas("Sector / Industria", todos_sectores, etiqueta_sector, "flt_sector")
    if not sectores_sel:
        sectores_sel = todos_sectores

    hay_gris = df is not None and not df.empty and "categoria" in df.columns and bool((df["categoria"] == "DATOS INSUFICIENTES").any())
    cats_disponibles = [l["nombre"] for l in leyenda if hay_gris or l["nombre"] != "DATOS INSUFICIENTES"]
    st.markdown('<div class="flt-t">Valoración</div>', unsafe_allow_html=True)
    cats_sel = _pastillas("Valoración", cats_disponibles, lambda c: c.capitalize(), "flt_valoracion")
    if not cats_sel:
        cats_sel = cats_disponibles
    cats_nombres = list(cats_sel)

    # --- Fila 3: País + Market Cap + Div. Yield + Métricas ---
    col_pais, col_mkt, col_dy, col_met = st.columns([2, 2, 2, 2])

    paises_disponibles = []
    if df is not None and not df.empty and "pais" in df.columns:
        paises_disponibles = sorted(
            [p for p in df["pais"].dropna().unique().tolist() if p],
            key=lambda x: x.lower()
        )
    with col_pais:
        paises_sel = st.multiselect(
            "País",
            paises_disponibles,
            default=[],
            placeholder="Todos los países",
        )

    mktcap_opciones = {
        "Sin mínimo": 0,
        "≥ $1B": 1e9,
        "≥ $10B": 10e9,
        "≥ $50B": 50e9,
        "≥ $100B": 100e9,
        "≥ $500B": 500e9,
    }
    with col_mkt:
        mktcap_label = st.selectbox(
            "Market Cap mínimo",
            list(mktcap_opciones.keys()),
            index=0,
        )
    mktcap_minimo = mktcap_opciones[mktcap_label]

    with col_dy:
        dy_minimo = st.slider(
            "Div. Yield mínimo (%)",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            format="%.1f%%",
        )

    with col_met:
        min_metricas = st.slider(
            "Métricas mínimas",
            min_value=1,
            max_value=4,
            value=1,
            help="Si subís este número, las empresas con menos métricas se muestran en gris. "
                 "Con 1 se ve todo (mejor algo que nada).",
        )

    # --- Fila 4: vista de revisión + actualizar ---
    col_diag, col_ref, _vacio = st.columns([3, 2, 3])
    with col_diag:
        ver_metodos_fv = st.checkbox(
            "🔬 Vista de revisión: métodos del Fair Value",
            key="ver_metodos_fv",
            help="Muestra la tabla de revisión, con una columna con los métodos usados en cada Fair Value "
                 "(✓ con su precio implícito, ✗ con el motivo por el que no se pudo usar).",
        )

    with col_ref:
        forzar_refresh = st.button(
            "Actualizar datos",
            help="Vuelve a leer el caché guardado (el caché se actualiza una vez por trimestre desde la PC)",
        )

    st.markdown("---")

    return {
        "sectores": sectores_sel,
        "categorias": cats_nombres,
        "paises": paises_sel,
        "dy_minimo": dy_minimo / 100.0,
        "mktcap_minimo": mktcap_minimo,
        "min_metricas": min_metricas,
        "sort_col": st.session_state.get("sort_col", "fv_upside"),
        "sort_asc": st.session_state.get("sort_asc", False),
        "ver_metodos_fv": ver_metodos_fv,
        "forzar_refresh": forzar_refresh,
    }


# ---------------------------------------------------------------------------
# TABLA PRINCIPAL
# ---------------------------------------------------------------------------

# Anchos de las columnas de la tabla clasica (encabezados y filas deben coincidir)
ANCHOS_TABLA = [3, 0.9, 1.6, 1, 3.6, 1.1, 1.8, 2.8, 1.2]


def render_tabla_visual(df_show: pd.DataFrame):
    """Tabla visual: titulos ordenables (botones) y filas en una sola pieza de HTML con la misma grilla."""
    sort_col = st.session_state.get("sort_col", "fv_upside")
    sort_asc = st.session_state.get("sort_asc", False)
    st.markdown(f"<style>{css_encabezado(sort_col)}</style>", unsafe_allow_html=True)

    cols = st.columns(ANCHOS_VISUAL, gap="small")
    sub = cols[0].columns([2.4, 1.2], gap="small")
    titulos = [
        (sub[0], "Empresa", "nombre"),
        (sub[1], "Mkt Cap", "market_cap"),
        (cols[1], "Valoración: Precio vs Fair Value", "fv_upside"),
        (cols[2], "Puntaje", "score_total"),
        (cols[3], "Div. Yield", "dividend_yield_actual"),
    ]
    for contenedor, etiqueta, clave in titulos:
        activo = sort_col == clave
        flecha = (" ▲" if sort_asc else " ▼") if activo else ""
        if contenedor.button(etiqueta + flecha, key=f"tvh_{clave}", use_container_width=True):
            if activo:
                st.session_state["sort_asc"] = not sort_asc
            else:
                st.session_state["sort_col"] = clave
                st.session_state["sort_asc"] = (clave == "nombre")
            st.rerun()
    st.markdown(html_tabla_visual(df_show), unsafe_allow_html=True)


def render_main_table(df: pd.DataFrame, filtros: dict):
    """Renderiza la tabla principal con colores y filtros aplicados."""

    df_show = df.copy()

    # --- Aplicar filtros ---
    df_show = df_show[df_show["sector"].isin(filtros["sectores"])]

    df_show = df_show[
        (df_show["metricas_usadas"] >= filtros["min_metricas"]) |
        (df_show["categoria"] == "DATOS INSUFICIENTES")
    ]

    df_show = df_show[df_show["categoria"].isin(filtros["categorias"])]

    # Filtro por país (solo si hay países seleccionados)
    if filtros["paises"]:
        df_show = df_show[df_show["pais"].isin(filtros["paises"])]

    # Filtro por DY mínimo
    if filtros["dy_minimo"] > 0:
        mask_dy = (
            df_show["dividend_yield_actual"].notna() &
            (df_show["dividend_yield_actual"] >= filtros["dy_minimo"])
        )
        df_show = df_show[mask_dy]

    # Filtro por Market Cap mínimo
    if filtros["mktcap_minimo"] > 0:
        df_show = df_show[
            df_show["market_cap"].notna() &
            (df_show["market_cap"] >= filtros["mktcap_minimo"])
        ]

    # --- Calcular columna de upside para ordenamiento ---
    def _fv_upside(row):
        fv = row.get("fair_value")
        p = row.get("precio_actual")
        if fv and p and p > 0:
            return (fv - p) / p
        return None

    df_show["fv_upside"] = df_show.apply(_fv_upside, axis=1)

    # --- Ordenamiento ---
    sort_col = st.session_state.get("sort_col", "fv_upside")
    sort_asc = st.session_state.get("sort_asc", False)

    df_show["sector_txt"] = df_show["sector"].map(etiqueta_sector)
    STR_COLS = {"nombre", "pais", "sector_txt"}
    if sort_col == "sector":
        sort_col = "sector_txt"
    if sort_col in STR_COLS:
        df_show = df_show.sort_values(sort_col, ascending=sort_asc, na_position="last",
                                      key=lambda s: s.astype(str).str.lower())
    elif sort_col == "score_total":
        df_show["_sort_v"] = df_show["score_total"].fillna(-1)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "fv_upside":
        df_show["_sort_v"] = df_show["fv_upside"].fillna(-999 if not sort_asc else 999)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "market_cap":
        df_show["_sort_v"] = df_show["market_cap"].fillna(0 if sort_asc else -1)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "dividend_yield_actual":
        df_show["_sort_v"] = df_show["dividend_yield_actual"].fillna(-1 if not sort_asc else 999)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "posicion_52s":
        df_show["_sort_v"] = df_show["posicion_52s"].fillna(-1 if not sort_asc else 999)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "precio_actual":
        df_show["_sort_v"] = df_show["precio_actual"].fillna(-1 if not sort_asc else 999)
        df_show = df_show.sort_values("_sort_v", ascending=sort_asc).drop(columns=["_sort_v"])
    elif sort_col == "metricas_usadas":
        # desempate por nombre para que el orden sea estable entre empresas con la misma cantidad
        df_show["_sort_v"] = pd.to_numeric(df_show["metricas_usadas"], errors="coerce").fillna(-1)
        df_show = df_show.sort_values(["_sort_v", "nombre"], ascending=[sort_asc, True]).drop(columns=["_sort_v"])
    else:
        df_show["_sort_v"] = df_show["score_total"].fillna(-1)
        df_show = df_show.sort_values("_sort_v", ascending=False).drop(columns=["_sort_v"])

    if df_show.empty:
        st.warning("No hay empresas que coincidan con los filtros seleccionados.")
        return

    # --- v1.2.28: la tabla visual es la definitiva (encabezados ordenables). La tabla clasica queda como
    # vista de revision: se muestra cuando se marca "Ver métodos del Fair Value".
    ver_metodos = bool(filtros.get("ver_metodos_fv"))
    st.markdown(f"**{len(df_show)} empresas**" + ("  ·  vista de revisión (tabla clásica)" if ver_metodos else ""))
    if not ver_metodos:
        render_tabla_visual(df_show)
        return

    if ver_metodos:
        st.markdown(_resumen_cobertura_fv(df_show), unsafe_allow_html=True)
    st.markdown("---")

    # --- Encabezados con sort clickable ---
    # Mapeo: nombre visible → columna interna para sort
    SORT_MAP = {
        "Empresa": "nombre",
        "País": "pais",
        "Sector": "sector",
        "Mkt Cap": "market_cap",
        "Valoración": "fv_upside",
        "Div. Yield": "dividend_yield_actual",
        "Rango 52s": "posicion_52s",
        "Categoría": "score_total",
        "Métricas": "metricas_usadas",
    }
    headers = ["Empresa", "País", "Sector", "Mkt Cap", "Valoración", "Div. Yield", "Rango 52s", "Categoría", "Métricas"]
    anchos = ANCHOS_TABLA
    if ver_metodos:
        headers = headers + ["Métodos del Fair Value"]
        anchos = anchos + [3.6]
    header_cols = st.columns(anchos)

    current_sort = st.session_state.get("sort_col", "fv_upside")
    current_asc = st.session_state.get("sort_asc", False)

    for col_ui, h in zip(header_cols, headers):
        if h not in SORT_MAP:  # columna de revisión: no se ordena
            col_ui.markdown(f"<div style='padding-top:6px'><b>🔬 {h}</b></div>", unsafe_allow_html=True)
            continue
        sort_key = SORT_MAP[h]
        if sort_key == current_sort:
            arrow = "↑" if current_asc else "↓"
            label = f"**{h} {arrow}**"
        else:
            label = f"**{h}**"
        if col_ui.button(label, key=f"sort_btn_{h}", use_container_width=True):
            if current_sort == sort_key:
                st.session_state["sort_asc"] = not current_asc
            else:
                st.session_state["sort_col"] = sort_key
                # Métricas: el primer clic ordena de menos a más (para ver primero a las que fallan)
                st.session_state["sort_asc"] = (sort_key == "metricas_usadas")
            st.rerun()

    st.markdown("---")

    # --- Filas ---
    for _, row in df_show.iterrows():
        cols = st.columns(ANCHOS_TABLA + ([3.6] if ver_metodos else []))

        ticker = row.get("ticker", "—")
        nombre = row.get("nombre") or ticker

        # Columna 0: Logo + Empresa (logo local o favicon; si no hay, iniciales: ver ui/logos.py)
        from ui.logos import logo_html
        cols[0].markdown(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'{logo_html(ticker, 22)}'
            f'<div><span style="font-weight:600;font-size:14px">{nombre}</span>'
            f'<br><span style="font-size:11px;color:#57606a">{ticker}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # País
        cols[1].markdown(bandera_html(row.get("pais")), unsafe_allow_html=True)

        # Sector
        cols[2].markdown(sector_html(row.get("sector")), unsafe_allow_html=True)

        # Market Cap
        cols[3].markdown(f'<b>{format_market_cap(row.get("market_cap")).replace("$", "&#36;")}</b>', unsafe_allow_html=True)

        # Valoración: precio de hoy (punto) contra el rango de los métodos del Fair Value y su promedio
        cols[4].markdown(celda_valoracion(row.to_dict()), unsafe_allow_html=True)

        # Dividend Yield
        # dividend_yield_actual viene como decimal desde yfinance (ej: 0.0128 = 1.28%)
        # None o NaN → no tiene datos; 0 → no paga dividendo → ambos muestran "—"
        dy = row.get("dividend_yield_actual")
        dy_valido = (
            dy is not None
            and not (isinstance(dy, float) and np.isnan(dy))
            and dy > 0  # 0.0 = no paga dividendo → "—"
        )
        if dy_valido:
            # Si el valor es > 1, ya viene como porcentaje (cache viejo); si < 1, es decimal
            if dy > 1:
                dy_pct = dy  # ya es porcentaje (ej: 1.28 → "1.3%")
            else:
                dy_pct = dy * 100  # decimal → porcentaje (ej: 0.0128 → "1.3%")
            dy_str = f"{dy_pct:.1f}%"
            dy_color = "#57606a"
            cols[5].markdown(
                f'<span style="color:{dy_color};font-weight:500">{dy_str}</span>',
                unsafe_allow_html=True,
            )
        else:
            cols[5].markdown("—")

        # Barra 52 semanas
        cols[6].markdown(render_52w_bar(row.get("posicion_52s")), unsafe_allow_html=True)

        # Categoría badge
        cols[7].markdown(
            render_categoria_badge(
                row.get("categoria", "—"),
                row.get("color_hex", "#6e7781"),
            ),
            unsafe_allow_html=True,
        )

        # Métricas usadas en el score (ej: 4/4) — columna propia y ordenable
        usadas, total = row.get("metricas_usadas"), row.get("metricas_total")
        if _num_valido(usadas) and _num_valido(total) and total > 0:
            color_n = "#57606a"
            cols[8].markdown(
                f'<span style="font-size:14px;font-weight:700;color:{color_n}" '
                f'title="Métricas del sector que tuvieron dato actual e histórico para calcular el score">'
                f'{int(usadas)}/{int(total)}</span>',
                unsafe_allow_html=True,
            )
        else:
            cols[8].markdown("—")

        # Vista de revisión: métodos usados en el Fair Value
        if ver_metodos:
            cols[9].markdown(_metodos_fv_html(row), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PANEL DE DETALLE POR EMPRESA
# ---------------------------------------------------------------------------

def render_detalle(df: pd.DataFrame):
    """Panel expandible con desglose de métricas para una empresa seleccionada."""
    st.markdown("---")
    st.subheader("🔍 Detalle de empresa")

    tickers_disp = sorted(df["ticker"].dropna().unique().tolist())
    ticker_sel = st.selectbox("Seleccioná una empresa para ver el detalle", tickers_disp)

    if not ticker_sel:
        return

    row = df[df["ticker"] == ticker_sel]
    if row.empty:
        st.warning("No hay datos para ese ticker.")
        return

    row = row.iloc[0]
    sector = row.get("sector", "")

    st.markdown(f"### {row.get('nombre', ticker_sel)} ({ticker_sel})")
    st.markdown(f"**Sector:** {sector_html(sector, en_linea=True)} | **País:** {bandera_html(row.get('pais'), con_nombre=True)} | **Market Cap:** <b>{format_market_cap(row.get('market_cap')).replace('$', '&#36;')}</b>", unsafe_allow_html=True)

    # Score y categoría
    st.markdown(
        render_categoria_badge(
            row.get("categoria", "—"),
            row.get("color_hex", "#6e7781"),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(f"**Score fundamental:** {row.get('score_fundamental', '—')} | **Score total:** {row.get('score_total', '—')}")

    # Rango 52 semanas
    st.markdown("**Posición en rango 52 semanas:**")
    pos = row.get("posicion_52s")
    if pos is not None:
        st.progress(float(pos), text=f"{pos*100:.0f}% del rango | Min: ${format_metric(row.get('precio_min_52s'), 2)} — Max: ${format_metric(row.get('precio_max_52s'), 2)}")
    else:
        st.markdown("Sin datos de rango 52s")

    # Desglose de métricas
    if sector in SECTOR_CONFIG and row.get("detalle"):
        st.markdown("---")
        st.subheader("📊 Desglose de métricas")

        detalle = row.get("detalle", {})
        if isinstance(detalle, str):
            import ast
            detalle = ast.literal_eval(detalle)

        metricas_cols = st.columns(len(SECTOR_CONFIG[sector]["metrics"]))

        METRIC_LABELS = {
            "ev_ebitda": "EV/EBITDA",
            "per": "P/E Ratio",
            "p_fcf": "P/FCF",
            "p_b": "P/Book",
            "dividend_yield": "Div. Yield",
            "peg": "PEG",
            "p_ffo": "P/FFO",
            "p_affo": "P/AFFO",
        }

        for i, (metrica, peso) in enumerate(SECTOR_CONFIG[sector]["metrics"].items()):
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

    # --- Fair Value desglose ---
    fv = row.get("fair_value")
    precio_actual = row.get("precio_actual")
    fv_detalle = row.get("fair_value_detalle")

    if fv_detalle:
        if isinstance(fv_detalle, str):
            import ast
            try:
                fv_detalle = ast.literal_eval(fv_detalle)
            except Exception:
                fv_detalle = {}

    if fv is not None and fv_detalle:
        st.markdown("---")
        st.subheader("🎯 Fair Value por método")

        fv_text, fv_color = format_fair_value(fv, precio_actual)
        st.markdown(
            f'**Fair Value estimado:** <span style="color:{fv_color};font-size:20px;font-weight:700">{fv_text}</span>',
            unsafe_allow_html=True,
        )
        st.caption("Promedio ponderado de los métodos disponibles, usando los mismos pesos del sector.")
        descartados_fv = row.get("fair_value_descartados")
        if isinstance(descartados_fv, dict) and descartados_fv:
            etiquetas = {"ev_ebitda": "EV/EBITDA", "per": "P/E Ratio", "p_fcf": "P/FCF", "p_b": "P/Book",
                         "dividend_yield": "Div. Yield", "peg": "PEG", "p_ffo": "P/FFO", "p_affo": "P/AFFO"}
            st.caption(
                "Métodos que no entran al promedio: "
                + " · ".join(f"{etiquetas.get(m, m)} ({mot})" for m, mot in descartados_fv.items())
            )
        nota_moneda = row.get("moneda_nota")
        if isinstance(nota_moneda, str) and nota_moneda.strip():
            st.caption(f"💱 Moneda: {nota_moneda}")

        METRIC_LABELS_FV = {
            "ev_ebitda": "EV/EBITDA", "per": "P/E Ratio", "p_fcf": "P/FCF",
            "p_b": "P/Book", "dividend_yield": "Div. Yield",
            "peg": "PEG", "p_ffo": "P/FFO", "p_affo": "P/AFFO",
        }

        fv_cols = st.columns(len(fv_detalle))
        for i, (metrica, datos) in enumerate(fv_detalle.items()):
            precio_m = datos.get("precio")
            peso_m = datos.get("peso", 0)
            label = METRIC_LABELS_FV.get(metrica, metrica.upper())

            with fv_cols[i]:
                if pd.notna(precio_actual) and precio_actual and precio_m:
                    upside = (precio_m - precio_actual) / precio_actual
                    up_str = f"+{upside*100:.0f}%" if upside >= 0 else f"{upside*100:.0f}%"
                    color_m = "#15803d" if upside > 0.05 else "#b91c1c" if upside < -0.05 else "#a16207"
                else:
                    up_str = "—"
                    color_m = "#6e7781"

                st.markdown(f"**{label}**")
                st.markdown(f"<small>Peso: {peso_m*100:.0f}%</small>", unsafe_allow_html=True)
                st.markdown(
                    f'<span style="font-size:18px;font-weight:700;color:{color_m}">'
                    f'${precio_m:.2f}</span><br>'
                    f'<span style="font-size:12px;color:{color_m}">{up_str} vs precio actual</span>',
                    unsafe_allow_html=True,
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

def render_aviso_legal():
    """Barra fija al pie de la pantalla con el aviso (texto en config/ajustes.py: AVISO_LEGAL)."""
    try:
        from config.ajustes import AVISO_LEGAL
    except Exception:  # noqa: BLE001
        AVISO_LEGAL = ("Herramienta de filtrado inicial, con fines informativos y educativos. No es una recomendación "
                       "de inversión ni una oferta de compra o venta.")
    texto = (AVISO_LEGAL or "").strip()
    if not texto:
        return
    st.markdown(
        '<style>'
        '.aviso-fijo{position:fixed;left:0;right:0;bottom:0;z-index:999;background:#f3f5f8;border-top:1px solid #d5dde6;'
        'color:#4b5563;font-size:12px;line-height:1.35;padding:7px 18px;text-align:center}'
        '.aviso-fijo b{color:#374151}'
        '[data-testid="stMainBlockContainer"]{padding-bottom:5rem}'
        '</style>'
        f'<div class="aviso-fijo"><b>Aviso:</b> {html.escape(texto)}</div>',
        unsafe_allow_html=True)


def main():
    # Cargar universo de tickers
    universe = load_custom_tickers()
    universe_key = str(sorted([t for ts in universe.values() for t in ts]))

    # Título principal
    col_title, col_ver = st.columns([8, 1])
    with col_title:
        st.title("📊 CEDEAR Screener")
        st.markdown("Detector de empresas potencialmente infravaloradas — datos de Stock Analysis y Yahoo Finance")
    with col_ver:
        st.markdown(f"<br><span style='color:#888;font-size:0.85em'>v{APP_VERSION}</span>", unsafe_allow_html=True)

    # Aviso fijo al pie (se muestra siempre, aunque despues falle algo)
    render_aviso_legal()

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
                ts_str = fuente.split("|")[1] if "|" in fuente else "?"
                st.info(f"📦 Datos del caché ({ts_str}) — se actualiza una vez por trimestre")
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

    # Filtros inline (encima de la tabla)
    filtros = render_filtros_inline(universe, df)

    # Forzar refresh limpia el cache de Streamlit
    if filtros["forzar_refresh"]:
        st.cache_data.clear()
        st.rerun()

    if df is None or df.empty:
        st.error("No se pudieron cargar datos. Intentá de nuevo en unos minutos.")
        st.stop()

    # Estilos de la tabla (una sola vez por pagina; los usan la escala, la tabla y el detalle)
    st.markdown(f"<style>{CSS_VISUAL}</style>", unsafe_allow_html=True)

    # Escala de valoracion (titulo + tramos de color)
    hay_gris = "categoria" in df.columns and bool((df["categoria"] == "DATOS INSUFICIENTES").any())
    st.markdown(escala_valoracion_html(hay_gris), unsafe_allow_html=True)

    # Estilos de las banderas (una sola vez por pagina; los usan la tabla y el detalle)
    st.markdown(css_banderas(), unsafe_allow_html=True)

    # Tabla principal
    render_main_table(df, filtros)

    # Panel de detalle
    render_detalle(df)

    # Seguimiento (historial del caché)
    render_seguimiento()

    # Panel de diagnóstico (solo visible si ?debug=1 en la URL)
    render_debug_panel()


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
            "Baratas − caras, ajustado (pts)": None if p.get("spread_ajustado") is None else round(p["spread_ajustado"], 1),
        } for p in res["pares"]]
        st.markdown("**Por período** (baratas − caras: cuánto más subieron las empresas marcadas como infravaloradas que las sobrevaloradas; positivo = el screener acertó)")
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
        # Una sola tabla: por categoria, cuantas empresas habia y cuanto cambio el precio medio segun cada puntaje
        etiquetas = (("oficial", "Oficial"), ("sector", "En sombra: vs sector"), ("ajustado", "En sombra: ajustado"))
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
