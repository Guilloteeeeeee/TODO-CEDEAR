"""
CEDEAR Screener — App principal Streamlit
Detecta CEDEARs potencialmente infravalorados usando métricas fundamentales
y técnicas descargadas automáticamente desde Yahoo Finance.

Ejecutar: streamlit run app.py
"""

APP_VERSION = "1.2.5"

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import sys
import time
from datetime import datetime

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    1. Cache vigente (< 6hs) → mostrar directo sin llamar a yfinance
    2. yfinance → descargar frescos y guardar cache
    3. Cache vencido → mejor que nada
    Retorna (df, fuente).
    """
    universe = load_custom_tickers()
    all_tickers = [t for tickers in universe.values() for t in tickers]
    ticker_to_sector = {
        ticker: sector
        for sector, tickers in universe.items()
        for ticker in tickers
    }

    # 1. Cache vigente → usar directo
    df_cache, ts_cache = load_cache(ignorar_ttl=False)
    if df_cache is not None and not df_cache.empty:
        ts_str = ts_cache.strftime("%d/%m %H:%M") if ts_cache else "?"
        return df_cache, f"cache_vigente|{ts_str}"

    # 2. Intentar yfinance
    progress_bar = st.progress(0, text="Descargando datos de Yahoo Finance...")
    try:
        def progress_cb(i, total, ticker):
            pct = int((i / total) * 100)
            progress_bar.progress(pct, text=f"Descargando {ticker} ({i+1}/{total})...")

        raw_df = fetch_all_tickers(all_tickers, progress_callback=progress_cb)
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


def get_logo_url(ticker: str) -> str:
    """
    Retorna URL del logo para un ticker dado.
    Usa Logo.dev (logo.dev) como fuente principal.
    """
    # Mapeo de tickers a dominio de empresa para logos
    TICKER_DOMAIN = {
        "AAPL": "apple.com", "MSFT": "microsoft.com", "GOOGL": "google.com",
        "AMZN": "amazon.com", "NVDA": "nvidia.com", "META": "meta.com",
        "TSLA": "tesla.com", "JPM": "jpmorganchase.com", "V": "visa.com",
        "MA": "mastercard.com", "AVGO": "broadcom.com", "UNH": "unitedhealthgroup.com",
        "JNJ": "jnj.com", "XOM": "exxonmobil.com", "WMT": "walmart.com",
        "LLY": "lilly.com", "HD": "homedepot.com", "PG": "pg.com",
        "COST": "costco.com", "MRK": "merck.com", "ABBV": "abbvie.com",
        "CVX": "chevron.com", "KO": "coca-cola.com", "PEP": "pepsico.com",
        "BAC": "bankofamerica.com", "NFLX": "netflix.com", "CRM": "salesforce.com",
        "ORCL": "oracle.com", "ACN": "accenture.com", "MCD": "mcdonalds.com",
        "CSCO": "cisco.com", "IBM": "ibm.com", "ADBE": "adobe.com",
        "NOW": "servicenow.com", "QCOM": "qualcomm.com", "TXN": "ti.com",
        "INTC": "intel.com", "AMD": "amd.com", "GE": "ge.com",
        "CAT": "caterpillar.com", "DE": "deere.com", "BA": "boeing.com",
        "LMT": "lockheedmartin.com", "RTX": "rtx.com", "HON": "honeywell.com",
        "UNP": "up.com", "NEE": "nexteraenergy.com", "DIS": "disney.com",
        "SBUX": "starbucks.com", "NKE": "nike.com", "SPOT": "spotify.com",
        "SHOP": "shopify.com", "SLB": "slb.com", "PFE": "pfizer.com",
        "TMO": "thermofisher.com", "ABT": "abbott.com", "GS": "goldmansachs.com",
        "MS": "morganstanley.com", "AXP": "americanexpress.com", "BRK-B": "berkshirehathaway.com",
        "BKNG": "booking.com", "UBER": "uber.com", "ABNB": "airbnb.com",
        "PYPL": "paypal.com", "COIN": "coinbase.com", "MELI": "mercadolibre.com",
        "PLTR": "palantir.com", "PANW": "paloaltonetworks.com", "CRWD": "crowdstrike.com",
        "ANET": "arista.com", "SNOW": "snowflake.com", "MU": "micron.com",
        "ASML": "asml.com", "TSM": "tsmc.com", "SAP": "sap.com",
        "NVO": "novonordisk.com", "NVS": "novartis.com", "AZN": "astrazeneca.com",
        "GILD": "gilead.com", "AMGN": "amgen.com", "VRTX": "vrtx.com",
        "ISRG": "intuitivesurgical.com", "DHR": "danaher.com", "MDT": "medtronic.com",
        "BHP": "bhp.com", "RIO": "riotinto.com", "VALE": "vale.com",
        "FCX": "fcx.com", "NEM": "newmont.com", "LIN": "linde.com",
        "SHW": "sherwin-williams.com", "SCCO": "southerncopper.com",
        "XOM": "exxonmobil.com", "CVX": "chevron.com", "SHEL": "shell.com",
        "TTE": "totalenergies.com", "COP": "conocophillips.com", "BP": "bp.com",
        "PBR": "petrobras.com.br", "EQNR": "equinor.com",
        "O": "realtyincome.com", "PLD": "prologis.com", "WELL": "welltower.com",
        "VZ": "verizon.com", "T": "att.com", "TMUS": "t-mobile.com",
        "PM": "pmi.com", "MO": "altria.com", "UL": "unilever.com",
        "DEO": "diageo.com", "CL": "colgate.com", "MDLZ": "mondelezinternational.com",
        "TGT": "target.com", "TM": "toyota.com", "SONY": "sony.com",
        "BABA": "alibaba.com", "PDD": "pinduoduo.com", "HSBC": "hsbc.com",
        "SAN": "santander.com", "BBVA": "bbva.com", "ITUB": "itau.com.br",
        "IBN": "icicibank.com", "HDB": "hdfcbank.com", "MUFG": "mufg.jp",
        "ING": "ing.com", "NU": "nu.com.br", "IBKR": "interactivebrokers.com",
        "BX": "blackstone.com", "SPGI": "spglobal.com", "SCHW": "schwab.com",
        "USB": "usbank.com", "BK": "bny.com", "FISV": "fiserv.com",
        "C": "citigroup.com", "AIG": "aig.com", "TJX": "tjx.com",
        "ROST": "rossstores.com", "GM": "gm.com", "RACE": "ferrari.com",
        "ORLY": "oreillyauto.com", "FDX": "fedex.com", "MMM": "3m.com",
        "PSX": "phillips66.com", "GEV": "gevernova.com", "HWM": "howmet.com",
        "PCAR": "paccar.com", "SIEGY": "siemens.com", "ARM": "arm.com",
        "AMAT": "appliedmaterials.com", "LRCX": "lamresearch.com",
        "KLAC": "kla.com", "ADI": "analog.com", "MRVL": "marvell.com",
        "INFY": "infosys.com", "DELL": "dell.com", "WDC": "westerndigital.com",
        "MSI": "motorolasolutions.com", "ADP": "adp.com", "CEG": "constellationenergy.com",
        "VST": "vistratenergy.com", "TLN": "talenenergy.com", "CVS": "cvshealth.com",
        "BMY": "bms.com", "GSK": "gsk.com", "NTES": "netease.com",
    }
    domain = TICKER_DOMAIN.get(ticker)
    if domain:
        return f"https://logo.clearbit.com/{domain}"
    # Fallback: URL genérica de logo.dev
    return f"https://logo.clearbit.com/{ticker.lower()}.com"


def format_fair_value(fv: float | None, precio: float | None) -> tuple[str, str]:
    """
    Retorna (texto, color) para el Fair Value.
    Muestra el precio y el upside/downside vs precio actual.
    """
    if fv is None or precio is None or precio <= 0:
        return "—", "#6e7781"
    upside = (fv - precio) / precio
    color = "#2da44e" if upside > 0.05 else "#cf222e" if upside < -0.05 else "#d4a017"
    upside_str = f"+{upside*100:.0f}%" if upside >= 0 else f"{upside*100:.0f}%"
    return f"${fv:.2f} ({upside_str})", color


# ---------------------------------------------------------------------------
# FILTROS INLINE (reemplaza sidebar)
# ---------------------------------------------------------------------------

def render_filtros_inline(universe: dict, df: pd.DataFrame = None) -> dict:
    """
    Renderiza los filtros encima de la tabla (sin sidebar) y retorna dict con filtros activos.
    """
    leyenda = leyenda_categorias()

    # --- Fila 1: Sectores + Categorías + País ---
    col_sec, col_cat, col_pais, col_mkt = st.columns([2, 2, 2, 2])

    todos_sectores = list(universe.keys())
    with col_sec:
        sectores_sel = st.multiselect(
            "🏭 Sectores",
            todos_sectores,
            default=todos_sectores,
            placeholder="Todos los sectores",
        )
        if not sectores_sel:
            sectores_sel = todos_sectores

    cats_disponibles = [f"{l['emoji']} {l['nombre']}" for l in leyenda]
    with col_cat:
        cats_sel = st.multiselect(
            "🎯 Categorías",
            cats_disponibles,
            default=cats_disponibles,
            placeholder="Todas las categorías",
        )
        if not cats_sel:
            cats_sel = cats_disponibles
    cats_nombres = [c.split(" ", 1)[1] for c in cats_sel]

    paises_disponibles = []
    if df is not None and not df.empty and "pais" in df.columns:
        paises_disponibles = sorted(
            [p for p in df["pais"].dropna().unique().tolist() if p],
            key=lambda x: x.lower()
        )
    with col_pais:
        paises_sel = st.multiselect(
            "🌎 País",
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
            "📏 Market Cap mínimo",
            list(mktcap_opciones.keys()),
            index=0,
        )
    mktcap_minimo = mktcap_opciones[mktcap_label]

    # --- Fila 2: DY + Métricas + Refresh ---
    col_dy, col_met, col_ref = st.columns([2, 2, 4])

    with col_dy:
        dy_minimo = st.slider(
            "💰 Div. Yield mínimo (%)",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            format="%.1f%%",
        )

    with col_met:
        min_metricas = st.slider(
            "📐 Métricas mínimas",
            min_value=1,
            max_value=4,
            value=2,
            help="Empresas con menos métricas se muestran en gris",
        )

    with col_ref:
        st.markdown("<br>", unsafe_allow_html=True)
        forzar_refresh = st.button(
            "🔄 Actualizar datos",
            help=f"Los datos se refrescan automáticamente cada {CACHE_TTL_HORAS} horas",
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
        "forzar_refresh": forzar_refresh,
    }


# ---------------------------------------------------------------------------
# TABLA PRINCIPAL
# ---------------------------------------------------------------------------

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

    STR_COLS = {"nombre", "pais", "sector"}
    if sort_col in STR_COLS:
        df_show = df_show.sort_values(sort_col, ascending=sort_asc, na_position="last")
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
    else:
        df_show["_sort_v"] = df_show["score_total"].fillna(-1)
        df_show = df_show.sort_values("_sort_v", ascending=False).drop(columns=["_sort_v"])

    if df_show.empty:
        st.warning("No hay empresas que coincidan con los filtros seleccionados.")
        return

    st.markdown(f"**{len(df_show)} empresas**")
    st.markdown("---")

    # --- Encabezados con sort clickable ---
    # Mapeo: nombre visible → columna interna para sort
    SORT_MAP = {
        "Empresa": "nombre",
        "País": "pais",
        "Sector": "sector",
        "Mkt Cap": "market_cap",
        "Precio": "precio_actual",
        "Fair Value": "fv_upside",
        "Div. Yield": "dividend_yield_actual",
        "Rango 52s": "posicion_52s",
        "Categoría": "score_total",
    }
    headers = ["Empresa", "País", "Sector", "Mkt Cap", "Precio", "Fair Value", "Div. Yield", "Rango 52s", "Categoría"]
    header_cols = st.columns([3, 1, 1.5, 1, 1, 1.8, 1.2, 1.8, 2.8])

    current_sort = st.session_state.get("sort_col", "fv_upside")
    current_asc = st.session_state.get("sort_asc", False)

    for col_ui, h in zip(header_cols, headers):
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
                st.session_state["sort_asc"] = False
            st.rerun()

    st.markdown("---")

    # --- Filas ---
    for _, row in df_show.iterrows():
        cols = st.columns([3, 1, 1.5, 1, 1, 1.8, 0.9, 1.8, 2.8])

        ticker = row.get("ticker", "—")
        nombre = row.get("nombre") or ticker

        # Columna 0: Logo + Empresa (con fallback a iniciales si el logo no carga)
        logo_url = get_logo_url(ticker)
        inicial = ticker[0] if ticker else "?"
        cols[0].markdown(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span id="logo-wrap-{ticker}" style="display:inline-block;width:22px;height:22px;flex-shrink:0;">'
            f'<img src="{logo_url}" width="22" height="22" '
            f'style="border-radius:4px;object-fit:contain;" '
            f'onerror="this.parentNode.innerHTML=\'<span style=&quot;display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:4px;background:#e1e4e8;font-size:10px;font-weight:700;color:#57606a;&quot;>{inicial}</span>\'">'
            f'</span>'
            f'<div><span style="font-weight:600;font-size:14px">{nombre}</span>'
            f'<br><span style="font-size:11px;color:#57606a">{ticker}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # País
        cols[1].markdown(row.get("pais") or "—")

        # Sector
        cols[2].markdown(row.get("sector", "—"))

        # Market Cap
        cols[3].markdown(format_market_cap(row.get("market_cap")))

        # Precio actual
        precio = row.get("precio_actual")
        cols[4].markdown(f"${format_metric(precio, 2)}" if precio else "—")

        # Fair Value con color
        fv = row.get("fair_value")
        fv_text, fv_color = format_fair_value(fv, precio)
        cols[5].markdown(
            f'<span style="color:{fv_color};font-weight:600;font-size:13px">{fv_text}</span>',
            unsafe_allow_html=True,
        )

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
            dy_color = "#2da44e" if dy_pct >= 3.0 else "#57606a"
            cols[6].markdown(
                f'<span style="color:{dy_color};font-weight:500">{dy_str}</span>',
                unsafe_allow_html=True,
            )
        else:
            cols[6].markdown("—")

        # Barra 52 semanas
        cols[7].markdown(render_52w_bar(row.get("posicion_52s")), unsafe_allow_html=True)

        # Categoría badge
        cols[8].markdown(
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
                if precio_actual and precio_m:
                    upside = (precio_m - precio_actual) / precio_actual
                    up_str = f"+{upside*100:.0f}%" if upside >= 0 else f"{upside*100:.0f}%"
                    color_m = "#2da44e" if upside > 0.05 else "#cf222e" if upside < -0.05 else "#d4a017"
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

def main():
    # Cargar universo de tickers
    universe = load_custom_tickers()
    universe_key = str(sorted([t for ts in universe.values() for t in ts]))

    # Título principal
    col_title, col_ver = st.columns([8, 1])
    with col_title:
        st.title("📊 CEDEAR Screener")
        st.markdown("Detector de empresas potencialmente infravaloradas — datos automáticos vía Yahoo Finance")
    with col_ver:
        st.markdown(f"<br><span style='color:#888;font-size:0.85em'>v{APP_VERSION}</span>", unsafe_allow_html=True)

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
                st.info(f"📦 Datos del caché ({ts_str}) — se actualizan cada {CACHE_TTL_HORAS}hs")
        except Exception as e:
            st.error(f"❌ Error al cargar datos y sin caché disponible: {e}")
            df = None
            fuente = "error"

    # Filtros inline (encima de la tabla)
    filtros = render_filtros_inline(universe, df)

    # Forzar refresh limpia el cache de Streamlit
    if filtros["forzar_refresh"]:
        st.cache_data.clear()
        st.rerun()

    if df is None or df.empty:
        st.error("No se pudieron cargar datos. Intentá de nuevo en unos minutos.")
        st.stop()

    # Leyenda compacta
    leyenda = leyenda_categorias()
    legend_parts = [
        f'<span style="color:{item["color"]}">{item["emoji"]}</span> {item["nombre"]}'
        for item in leyenda
    ]
    st.markdown(
        '<div style="font-size:12px;color:#57606a;margin-bottom:4px">'
        + "  &nbsp;|&nbsp;  ".join(legend_parts)
        + '</div>',
        unsafe_allow_html=True,
    )

    # Tabla principal
    render_main_table(df, filtros)

    # Panel de detalle
    render_detalle(df)

    # Panel de diagnóstico (solo visible si ?debug=1 en la URL)
    render_debug_panel()


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
