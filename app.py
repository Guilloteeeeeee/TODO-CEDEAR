"""
CEDEAR Screener — App principal Streamlit
Detecta CEDEARs potencialmente infravalorados usando métricas fundamentales
y técnicas descargadas automáticamente desde Yahoo Finance.

Ejecutar: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime

# Importaciones del proyecto
from data.fetcher import fetch_all_tickers
from scoring.engine import score_dataframe, leyenda_categorias
from config.sectors import TICKER_UNIVERSE, TICKER_TO_SECTOR, SECTOR_CONFIG

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CEDEAR Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
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


def load_cache() -> tuple[pd.DataFrame | None, datetime | None]:
    """Carga datos del cache si existen y no están vencidos."""
    if not os.path.exists(CACHE_FILE):
        return None, None
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        ts = datetime.fromisoformat(cache["timestamp"])
        horas_pasadas = (datetime.now() - ts).total_seconds() / 3600
        if horas_pasadas > CACHE_TTL_HORAS:
            return None, ts
        df = pd.DataFrame(cache["data"])
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
def get_scored_data(universe_key: str) -> pd.DataFrame:
    """
    Descarga datos y calcula scores. Cachea en sesión de Streamlit.
    universe_key fuerza recargar cuando cambia el universo.
    """
    universe = load_custom_tickers()
    all_tickers = [t for tickers in universe.values() for t in tickers]

    # Mapeo ticker -> sector actualizado con tickers custom
    ticker_to_sector = {
        ticker: sector
        for sector, tickers in universe.items()
        for ticker in tickers
    }

    progress_bar = st.progress(0, text="Descargando datos...")

    def progress_cb(i, total, ticker):
        pct = int((i / total) * 100)
        progress_bar.progress(pct, text=f"Descargando {ticker} ({i+1}/{total})...")

    raw_df = fetch_all_tickers(all_tickers, progress_callback=progress_cb)
    progress_bar.progress(100, text="Calculando scores...")

    scored_df = score_dataframe(raw_df, ticker_to_sector)
    save_cache(scored_df)
    progress_bar.empty()
    return scored_df


# ---------------------------------------------------------------------------
# HELPERS DE VISUALIZACIÓN
# ---------------------------------------------------------------------------

def render_52w_bar(posicion: float | None) -> str:
    """
    Genera una barra HTML del rango 52 semanas.
    posicion: 0.0 (mínimo del año) a 1.0 (máximo del año)
    """
    if posicion is None:
        return "—"
    pct = int(posicion * 100)
    if pct <= 30:
        color = "#2da44e"   # verde
    elif pct <= 70:
        color = "#d4a017"   # amarillo
    else:
        color = "#cf222e"   # rojo

    return (
        f'<div style="display:flex;align-items:center;gap:6px;min-width:120px">'
        f'<div style="background:#e1e4e8;border-radius:4px;height:10px;width:80px;position:relative;">'
        f'<div style="background:{color};width:{pct}%;height:100%;border-radius:4px;"></div>'
        f'</div>'
        f'<span style="font-size:12px;color:#57606a">{pct}%</span>'
        f'</div>'
    )


def render_categoria_badge(emoji: str, categoria: str, color_hex: str) -> str:
    """Badge HTML para mostrar la categoría con color."""
    return (
        f'<span style="background:{color_hex}22;color:{color_hex};'
        f'border:1px solid {color_hex}66;border-radius:12px;'
        f'padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap">'
        f'{emoji} {categoria}</span>'
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
    if val is None:
        return "—"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:.0f}"


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

def render_sidebar(universe: dict) -> tuple[list, list, int, bool]:
    """
    Renderiza el sidebar y retorna:
      - sectores_seleccionados
      - categorias_seleccionadas
      - min_metricas
      - forzar_refresh
    """
    st.sidebar.title("📊 CEDEAR Screener")
    st.sidebar.markdown("---")

    # Filtro por sector
    st.sidebar.subheader("Sectores")
    todos_sectores = list(universe.keys())
    seleccionar_todos = st.sidebar.checkbox("Todos los sectores", value=True)
    if seleccionar_todos:
        sectores_sel = todos_sectores
    else:
        sectores_sel = st.sidebar.multiselect(
            "Elegir sectores",
            todos_sectores,
            default=todos_sectores,
        )

    # Filtro por categoría
    st.sidebar.markdown("---")
    st.sidebar.subheader("Categorías")
    leyenda = leyenda_categorias()
    cats_disponibles = [f"{l['emoji']} {l['nombre']}" for l in leyenda]
    cats_sel = st.sidebar.multiselect(
        "Mostrar categorías",
        cats_disponibles,
        default=cats_disponibles,
    )
    cats_nombres = [c.split(" ", 1)[1] for c in cats_sel]

    # Filtro por cobertura de métricas
    st.sidebar.markdown("---")
    st.sidebar.subheader("Calidad de datos")
    min_metricas = st.sidebar.slider(
        "Mínimo de métricas disponibles",
        min_value=1,
        max_value=4,
        value=2,
        help="Empresas con menos métricas disponibles se muestran en gris",
    )

    # Refresh
    st.sidebar.markdown("---")
    forzar_refresh = st.sidebar.button(
        "🔄 Actualizar datos",
        help=f"Los datos se refrescan automáticamente cada {CACHE_TTL_HORAS} horas",
        use_container_width=True,
    )

    # Leyenda de colores
    st.sidebar.markdown("---")
    st.sidebar.subheader("Leyenda")
    for item in leyenda:
        st.sidebar.markdown(
            f'<span style="color:{item["color"]};font-size:16px">{item["emoji"]}</span> '
            f'**{item["nombre"]}**  \n'
            f'<span style="font-size:11px;color:#57606a">{item["rango"]}</span>',
            unsafe_allow_html=True,
        )

    # Aviso trampa de valor
    st.sidebar.markdown("---")
    st.sidebar.info(
        "⚠️ **Aviso importante**\n\n"
        "Este screener es una herramienta de filtrado inicial. "
        "Una empresa 'potencialmente infravalorada' puede ser una **trampa de valor**. "
        "Siempre investigá más antes de invertir."
    )

    return sectores_sel, cats_nombres, min_metricas, forzar_refresh


# ---------------------------------------------------------------------------
# PANEL DE GESTIÓN DE TICKERS
# ---------------------------------------------------------------------------

def render_ticker_manager(universe: dict) -> dict | None:
    """
    Panel para agregar/quitar tickers. Retorna universo actualizado o None si no cambió.
    """
    with st.expander("⚙️ Gestionar tickers del universo", expanded=False):
        st.markdown("Agregá o quitá tickers por sector. Los cambios actualizan el universo local.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Agregar ticker")
            new_sector = st.selectbox("Sector", list(universe.keys()), key="add_sector")
            new_ticker = st.text_input("Ticker (ej: AAPL, MSFT)", key="add_ticker").upper().strip()
            if st.button("Agregar", key="btn_add"):
                if new_ticker and new_ticker not in universe[new_sector]:
                    universe[new_sector].append(new_ticker)
                    save_custom_tickers(universe)
                    st.success(f"{new_ticker} agregado a {new_sector}")
                    st.rerun()
                elif new_ticker in universe[new_sector]:
                    st.warning(f"{new_ticker} ya está en {new_sector}")

        with col2:
            st.subheader("Quitar ticker")
            del_sector = st.selectbox("Sector", list(universe.keys()), key="del_sector")
            del_ticker = st.selectbox(
                "Ticker a quitar",
                universe[del_sector],
                key="del_ticker",
            )
            if st.button("Quitar", key="btn_del", type="secondary"):
                universe[del_sector].remove(del_ticker)
                save_custom_tickers(universe)
                st.success(f"{del_ticker} quitado de {del_sector}")
                st.rerun()

    return universe


# ---------------------------------------------------------------------------
# TABLA PRINCIPAL
# ---------------------------------------------------------------------------

def render_main_table(df: pd.DataFrame, sectores_sel: list,
                      cats_nombres: list, min_metricas: int):
    """Renderiza la tabla principal con colores y filtros aplicados."""

    # Filtrar por sector
    df_show = df[df["sector"].isin(sectores_sel)].copy()

    # Filtrar por mínimo de métricas
    df_show = df_show[
        (df_show["metricas_usadas"] >= min_metricas) |
        (df_show["categoria"] == "DATOS INSUFICIENTES")
    ]

    # Filtrar por categoría seleccionada
    df_show = df_show[df_show["categoria"].isin(cats_nombres)]

    # Ordenar: mejor score primero, gris al final
    df_show["_sort_score"] = df_show["score_total"].fillna(-1)
    df_show = df_show.sort_values("_sort_score", ascending=False).drop(columns=["_sort_score"])

    if df_show.empty:
        st.warning("No hay empresas que coincidan con los filtros seleccionados.")
        return

    st.markdown(f"**{len(df_show)} empresas** | Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.markdown("---")

    # Encabezados de tabla
    header_cols = st.columns([2.5, 1, 1.5, 1, 1, 1, 1, 1.5, 2, 3])
    headers = ["Empresa", "Ticker", "Sector", "Market Cap", "Precio", "Score\nFund.", "Score\nTotal", "Métricas", "Rango 52s", "Categoría"]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    st.markdown("---")

    # Filas
    for _, row in df_show.iterrows():
        cols = st.columns([2.5, 1, 1.5, 1, 1, 1, 1, 1.5, 2, 3])

        nombre = row.get("nombre") or row.get("ticker", "—")
        cols[0].markdown(f"**{nombre}**")
        cols[1].markdown(row.get("ticker", "—"))
        cols[2].markdown(row.get("sector", "—"))
        cols[3].markdown(format_market_cap(row.get("market_cap")))
        cols[4].markdown(f"${format_metric(row.get('precio_actual'), 2)}")

        # Score fundamental
        sf = row.get("score_fundamental")
        cols[5].markdown(f"**{sf:.0f}**" if sf is not None else "—")

        # Score total (con color)
        st_val = row.get("score_total")
        color = row.get("color_hex", "#6e7781")
        if st_val is not None:
            cols[6].markdown(
                f'<span style="color:{color};font-weight:700;font-size:16px">{st_val:.0f}</span>',
                unsafe_allow_html=True,
            )
        else:
            cols[6].markdown("—")

        # Métricas disponibles
        usadas = row.get("metricas_usadas", 0)
        total = row.get("metricas_total", 4)
        cols[7].markdown(f"{usadas}/{total}")

        # Barra 52 semanas
        cols[8].markdown(render_52w_bar(row.get("posicion_52s")), unsafe_allow_html=True)

        # Categoría badge
        cols[9].markdown(
            render_categoria_badge(
                row.get("emoji", "⚫"),
                row.get("categoria", "—"),
                row.get("color_hex", "#6e7781"),
            ),
            unsafe_allow_html=True,
        )


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
    st.markdown(f"**Sector:** {sector} | **País:** {row.get('pais', '—')} | **Market Cap:** {format_market_cap(row.get('market_cap'))}")

    # Score y categoría
    st.markdown(
        render_categoria_badge(
            row.get("emoji", "⚫"),
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
                    color_m = "#2da44e" if score_m >= 60 else "#d4a017" if score_m >= 40 else "#cf222e"
                    st.markdown(
                        f'Score: <span style="color:{color_m};font-weight:700">{score_m:.0f}/100</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("Score: —")

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

def main():
    # Cargar universo de tickers
    universe = load_custom_tickers()

    # Sidebar
    sectores_sel, cats_nombres, min_metricas, forzar_refresh = render_sidebar(universe)

    # Gestión de tickers
    universe = render_ticker_manager(universe)

    # Título principal
    st.title("📊 CEDEAR Screener")
    st.markdown("Detector de empresas potencialmente infravaloradas — datos automáticos vía Yahoo Finance")

    # Calcular universe_key para invalidar cache cuando cambian los tickers
    universe_key = str(sorted([t for ts in universe.values() for t in ts]))

    # Forzar refresh limpia el cache de Streamlit
    if forzar_refresh:
        st.cache_data.clear()
        st.rerun()

    # Cargar datos
    with st.spinner("Cargando datos..."):
        try:
            df = get_scored_data(universe_key)
        except Exception as e:
            st.error(f"Error al cargar datos: {e}")
            st.stop()

    if df is None or df.empty:
        st.error("No se pudieron cargar datos. Intentá de nuevo en unos minutos.")
        st.stop()

    # Tabla principal
    render_main_table(df, sectores_sel, cats_nombres, min_metricas)

    # Panel de detalle
    render_detalle(df)


if __name__ == "__main__":
    main()
