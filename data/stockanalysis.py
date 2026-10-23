"""
Scraper de Stock Analysis (stockanalysis.com) para obtener ratios históricos.

Se usa como fuente secundaria cuando yfinance no devuelve estados financieros
completos para calcular las medianas históricas.

Estrategia de extracción (en orden):
  1. __NEXT_DATA__ JSON embebido en el HTML → más robusto, no depende del DOM
  2. <table> HTML via BeautifulSoup → fallback si Next.js no embebe datos

Endpoints usados:
  - /stocks/{ticker}/financials/ratios/?p=annual  → PE Ratio, PB Ratio, Dividend Yield, EV/EBITDA, P/FCF
  - /stocks/{ticker}/financials/?p=annual         → EPS, FCF, Revenue
  - /stocks/{ticker}/financials/balance-sheet/?p=annual → Book Value Per Share, Shares

Para ADRs y tickers extranjeros: igual URL base /stocks/{ticker}/
"""

import re
import json
import time
import logging
import numpy as np
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

# Headers para no ser bloqueado
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",   # sin "br": sin la libreria brotli, requests no sabe abrirlo (v1.2.14)
    "Cache-Control": "no-cache",
}

# Pausa entre requests
REQUEST_DELAY = 1.0

# Años a buscar
MAX_YEARS = 5


# ---------------------------------------------------------------------------
# FETCH HTML
# ---------------------------------------------------------------------------

# v1.2.13 - Trato correcto con el sitio: respeta robots.txt, una pagina a la vez con pausa,
# espera y reintenta una vez si pide frenar (429), y se detiene si lo bloquean.
_ROBOTS = {}
_FALLOS_SEGUIDOS = 0         # bloqueos / paginas ilegibles seguidos
_FALLOS_LECTURA = 0          # paginas bajadas bien pero cuya tabla no se pudo leer, seguidas
MAX_FALLOS_SEGUIDOS = 5      # tras esta cantidad de bloqueos seguidos se deja de consultar en esta corrida
ESPERA_429 = 15              # segundos antes de reintentar si el sitio pide frenar


def _robots_permite(url: str, session=None) -> bool:
    """True si el robots.txt del sitio permite pedir `url` (si no se puede leer, se permite)."""
    from urllib import robotparser
    from urllib.parse import urlparse
    partes = urlparse(url)
    base = f"{partes.scheme}://{partes.netloc}"
    if base not in _ROBOTS:
        rp = robotparser.RobotFileParser()
        try:
            import requests
            r = (session or requests).get(base + "/robots.txt", headers=HEADERS, timeout=15)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            else:
                rp = None
        except Exception:
            rp = None
        _ROBOTS[base] = rp
    rp = _ROBOTS[base]
    return True if rp is None else rp.can_fetch("*", url)


def sa_disponible() -> bool:
    """False cuando el sitio nos bloqueo varias veces seguidas en esta corrida."""
    return _FALLOS_SEGUIDOS < MAX_FALLOS_SEGUIDOS and _FALLOS_LECTURA < MAX_FALLOS_SEGUIDOS


def _legible(texto: str) -> bool:
    """True si `texto` parece HTML de verdad (y no bytes comprimidos mal abiertos)."""
    if not texto:
        return False
    cabeza = texto[:3000].lower()
    return "<html" in cabeza or "<!doctype" in cabeza or "<head" in cabeza or "<body" in cabeza


ULTIMO_ERROR = ""   # motivo del ultimo fallo de descarga (para el diagnostico)


def _fetch_html(url: str, session=None) -> Optional[str]:
    """Descarga HTML de una URL (respetando robots.txt)."""
    global _FALLOS_SEGUIDOS, ULTIMO_ERROR
    ULTIMO_ERROR = ""
    if not sa_disponible():
        ULTIMO_ERROR = "Stock Analysis se dejo de consultar en esta corrida (bloqueos, paginas ilegibles o sin tabla, varias seguidas)"
        return None
    try:
        import requests
        s = session or requests.Session()
        if not _robots_permite(url, s):
            logger.warning(f"robots.txt no permite {url}")
            ULTIMO_ERROR = "robots.txt no permite esta pagina"
            return None
        headers = dict(HEADERS)
        for intento in range(3):
            resp = s.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                if _legible(resp.text):
                    _FALLOS_SEGUIDOS = 0
                    return resp.text
                # Pagina que no parece HTML (compresion mal abierta): se reintenta sin compresion
                if headers.get("Accept-Encoding") != "identity":
                    headers["Accept-Encoding"] = "identity"
                    continue
                ULTIMO_ERROR = "la pagina llego ilegible (no parece HTML)"
                _FALLOS_SEGUIDOS += 1
                return None
            if resp.status_code == 429 and intento == 0:
                time.sleep(ESPERA_429)
                continue
            break
        logger.debug(f"HTTP {resp.status_code} para {url}")
        ULTIMO_ERROR = f"HTTP {resp.status_code}"
        if resp.status_code in (403, 429):
            _FALLOS_SEGUIDOS += 1
    except Exception as e:
        logger.debug(f"Error fetching {url}: {e}")
        ULTIMO_ERROR = f"{type(e).__name__}: {e}"
    return None


# ---------------------------------------------------------------------------
# ESTRATEGIA 1: __NEXT_DATA__ JSON (Next.js)
# ---------------------------------------------------------------------------

def _extract_next_data(html: str) -> Optional[dict]:
    """
    Extrae el JSON embebido en <script id="__NEXT_DATA__">.
    Stock Analysis (Next.js) incluye todos los datos de la tabla en este JSON.
    """
    if not html:
        return None
    try:
        m = re.search(
            r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if m:
            return json.loads(m.group(1))
    except Exception as e:
        logger.debug(f"Error parseando __NEXT_DATA__: {e}")
    return None


def _parse_next_data_table(next_data: dict) -> dict:
    """
    Extrae datos de tabla desde el __NEXT_DATA__ de Stock Analysis.
    Retorna dict {row_label: {column_header: value}}.

    La estructura de pageProps varía por página pero generalmente:
    props.pageProps.data.financialData o similar.
    """
    result = {}
    try:
        page_props = next_data.get("props", {}).get("pageProps", {})

        # Intentar varias rutas donde SA puede guardar los datos
        data_candidates = [
            page_props.get("data"),
            page_props.get("financialData"),
            page_props.get("ratioData"),
            page_props.get("tableData"),
        ]

        # También buscar en cualquier dict que tenga estructura de tabla
        def _find_tables(obj, depth=0):
            if depth > 6 or not isinstance(obj, dict):
                return []
            tables = []
            # Una tabla de SA suele tener "headers" y "rows" o "data"
            if "headers" in obj and ("rows" in obj or "data" in obj):
                tables.append(obj)
            for v in obj.values():
                if isinstance(v, dict):
                    tables.extend(_find_tables(v, depth + 1))
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            tables.extend(_find_tables(item, depth + 1))
            return tables

        tables = _find_tables(page_props)

        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", table.get("data", []))
            if not headers or not rows:
                continue

            # Extraer texto de headers (pueden ser dicts o strings)
            def _get_text(cell):
                if isinstance(cell, str):
                    return cell
                if isinstance(cell, dict):
                    return cell.get("text") or cell.get("value") or cell.get("title") or str(cell)
                return str(cell)

            header_texts = [_get_text(h) for h in headers]

            for row in rows:
                cells = row if isinstance(row, list) else row.get("cells", row.get("values", []))
                if not cells:
                    continue
                label = _get_text(cells[0]) if cells else ""
                if not label:
                    continue
                row_data = {}
                for i, cell in enumerate(cells[1:], 1):
                    if i < len(header_texts):
                        val = _parse_number(_get_text(cell))
                        if val is not None:
                            row_data[header_texts[i]] = val
                if row_data:
                    result[label] = row_data

    except Exception as e:
        logger.debug(f"Error parseando __NEXT_DATA__ table: {e}")

    return result


# ---------------------------------------------------------------------------
# ESTRATEGIA 2: Parseo HTML de tablas (BeautifulSoup)
# ---------------------------------------------------------------------------

_PATRON_ENCABEZADO = re.compile(r"^(current|ttm)$|fy\s*20\d{2}|^20\d{2}$|^(q[1-4]\s*)?20\d{2}", re.I)


def _texto_celda(celda) -> str:
    """Texto de una celda con espacios normalizados (separa los trozos de texto con un espacio)."""
    t = celda.get_text(" ", strip=True).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def _parse_html_table(html: str, section_keywords: list) -> dict:
    """
    Parsea tablas HTML de Stock Analysis via BeautifulSoup.
    Retorna dict {row_label: {column_header: value}}.
    v1.2.14: la fila de encabezados se busca entre las primeras 4 filas (la que tiene mas
    columnas tipo "Current" / "FY 2025"), por si la tabla trae una fila extra arriba.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup no instalado — pip install beautifulsoup4")
        return {}

    result = {}
    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue

            # Fila de encabezados: la que mas columnas tipo "Current"/"FY 20xx" tenga
            mejor_idx, mejor_n = 0, 0
            for idx, row in enumerate(rows[:4]):
                textos = [_texto_celda(c) for c in row.find_all(["th", "td"])]
                n = sum(1 for t in textos[1:] if _PATRON_ENCABEZADO.search(t))
                if n > mejor_n:
                    mejor_idx, mejor_n = idx, n
            headers = [_texto_celda(c) for c in rows[mejor_idx].find_all(["th", "td"])]

            if len(headers) < 2:
                continue

            # Leer filas de datos
            table_data = {}
            for row in rows[mejor_idx + 1:]:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                label = _texto_celda(cells[0])
                if not label:
                    continue
                row_data = {}
                for i, cell in enumerate(cells[1:], 1):
                    if i < len(headers):
                        val = _parse_number(_texto_celda(cell))
                        if val is not None:
                            row_data[headers[i]] = val
                if row_data:
                    table_data[label] = row_data

            # ¿Esta tabla tiene alguna de las keywords?
            found = any(
                any(_sin_espacios(kw) in _sin_espacios(label) for kw in section_keywords)
                for label in table_data.keys()
            )
            if found:
                result.update(table_data)

    except Exception as e:
        logger.debug(f"Error parseando tabla HTML: {e}")

    return result


def _sin_espacios(texto: str) -> str:
    return re.sub(r"\s+", "", str(texto)).lower()


def _parse_page(html: str, section_keywords: list) -> dict:
    """
    Intenta extraer datos de una página SA:
    1. Primero __NEXT_DATA__ (más confiable)
    2. Si no encuentra datos relevantes, cae a BeautifulSoup
    """
    if not html:
        return {}

    # Intento 1: __NEXT_DATA__
    next_data = _extract_next_data(html)
    if next_data:
        table = _parse_next_data_table(next_data)
        if table and any(
            any(kw.lower() in label.lower() for kw in section_keywords)
            for label in table.keys()
        ):
            return table

    # Intento 2: BeautifulSoup HTML
    return _parse_html_table(html, section_keywords)


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

def _parse_number(text: str) -> Optional[float]:
    """Convierte texto de Stock Analysis a float."""
    if not text or text in ("-", "—", "N/A", "", "∞", "--"):
        return None
    try:
        clean = text.replace("%", "").replace("$", "").replace(",", "").strip()
        multiplier = 1.0
        if clean.endswith("B"):
            multiplier = 1e9
            clean = clean[:-1]
        elif clean.endswith("M"):
            multiplier = 1e6
            clean = clean[:-1]
        elif clean.endswith("K"):
            multiplier = 1e3
            clean = clean[:-1]
        val = float(clean) * multiplier
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        return None


def _find_label(data: dict, *keywords, exclude: list = None) -> Optional[str]:
    """Busca la primera clave del dict que contenga todos los keywords (sin importar espacios)."""
    exclude = exclude or []
    kws = [_sin_espacios(k) for k in keywords]
    exs = [_sin_espacios(e) for e in exclude]
    for label in data.keys():
        label_lower = _sin_espacios(label)
        if all(kw in label_lower for kw in kws):
            if not any(ex in label_lower for ex in exs):
                return label
    return None


def _extract_annual_series(row_data: dict, max_years: int = MAX_YEARS) -> list:
    """
    Extrae valores anuales de un dict {header: value}.
    Filtra solo columnas que parecen años (FY20xx, 20xx, TTM).
    Retorna lista de floats, máximo max_years valores.
    """
    year_cols = []
    for col in row_data.keys():
        match = re.search(r'(20\d{2})', str(col))
        if match:
            year_cols.append((int(match.group(1)), col))

    year_cols.sort(reverse=True)

    values = []
    for _, col in year_cols[:max_years]:
        val = row_data.get(col)
        if val is not None and val > 0:
            values.append(val)

    return values


# ---------------------------------------------------------------------------
# FETCH PRINCIPAL
# ---------------------------------------------------------------------------

def fetch_ratios_stockanalysis(ticker: str, session=None) -> dict:
    """
    Obtiene ratios históricos de Stock Analysis para un ticker.

    Retorna dict con listas de valores históricos:
      - per_historia: [float, ...]
      - p_b_historia: [float, ...]
      - ev_ebitda_historia: [float, ...]
      - p_fcf_historia: [float, ...]
      - dividend_yield_historia: [float, ...]
    """
    result = {
        "per_historia": [],
        "p_b_historia": [],
        "ev_ebitda_historia": [],
        "p_fcf_historia": [],
        "dividend_yield_historia": [],
    }

    # Normalizar ticker para URL (BRK-B → brk-b)
    ticker_url = ticker.lower().replace(".", "-")
    base = f"https://stockanalysis.com/stocks/{ticker_url}"

    try:
        import requests
        session = session or requests.Session()

        # --- 1. Ratios page: PE, PB, EV/EBITDA, P/FCF, Dividend Yield ---
        time.sleep(REQUEST_DELAY)
        ratios_html = _fetch_html(f"{base}/financials/ratios/?p=annual", session)
        ratios_data = _parse_page(
            ratios_html,
            ["PE Ratio", "PB Ratio", "Dividend Yield", "EV/EBITDA", "P/FCF", "Price to"]
        )

        if ratios_data:
            pe_label = _find_label(ratios_data, "pe ratio") or _find_label(ratios_data, "price to earnings")
            if pe_label:
                result["per_historia"] = _extract_annual_series(ratios_data[pe_label])

            pb_label = _find_label(ratios_data, "pb ratio") or _find_label(ratios_data, "price to book")
            if pb_label:
                result["p_b_historia"] = _extract_annual_series(ratios_data[pb_label])

            ev_label = (_find_label(ratios_data, "ev/ebitda") or
                        _find_label(ratios_data, "ev to ebitda") or
                        _find_label(ratios_data, "enterprise value"))
            if ev_label:
                result["ev_ebitda_historia"] = _extract_annual_series(ratios_data[ev_label])

            pfcf_label = (_find_label(ratios_data, "p/fcf") or
                          _find_label(ratios_data, "price to free cash flow") or
                          _find_label(ratios_data, "price/fcf"))
            if pfcf_label:
                result["p_fcf_historia"] = _extract_annual_series(ratios_data[pfcf_label])

            dy_label = _find_label(ratios_data, "dividend yield")
            if dy_label:
                vals = _extract_annual_series(ratios_data[dy_label])
                # En SA el DY viene como porcentaje (ej: 2.5 = 2.5%)
                result["dividend_yield_historia"] = [v / 100.0 for v in vals if 0 < v < 50]

        # --- 2. Income statement: EPS, FCF ---
        time.sleep(REQUEST_DELAY)
        income_html = _fetch_html(f"{base}/financials/?p=annual", session)
        income_data = _parse_page(income_html, ["EPS", "Free Cash Flow", "Revenue", "Net Income"])

        if income_data:
            fcf_label = (_find_label(income_data, "free cash flow") or
                         _find_label(income_data, "fcf"))
            if fcf_label:
                result["_fcf_historia_raw"] = income_data[fcf_label]

        # --- 3. Balance sheet: Book Value Per Share, Shares ---
        time.sleep(REQUEST_DELAY)
        balance_html = _fetch_html(f"{base}/financials/balance-sheet/?p=annual", session)
        balance_data = _parse_page(balance_html, ["Book Value", "Shares Outstanding", "Equity"])

        if balance_data:
            bvps_label = (_find_label(balance_data, "book value per share", exclude=["tangible"]) or
                          _find_label(balance_data, "bvps"))
            if bvps_label and not result["p_b_historia"]:
                result["_bvps_historia_raw"] = balance_data[bvps_label]

            shares_label = (_find_label(balance_data, "shares outstanding", exclude=["filing"]) or
                            _find_label(balance_data, "common shares outstanding") or
                            _find_label(balance_data, "weighted average shares"))
            if shares_label:
                result["_shares_historia_raw"] = balance_data[shares_label]

    except Exception as e:
        logger.warning(f"Error en Stock Analysis para {ticker}: {e}")

    return result


# ---------------------------------------------------------------------------
# ENRIQUECIMIENTO DEL RESULT
# ---------------------------------------------------------------------------

def enrich_with_stockanalysis(ticker: str, result: dict, precio_hist: dict) -> None:
    """
    Enriquece el result dict con medianas de Stock Analysis cuando yfinance no tiene histórico.

    precio_hist: dict {year: precio_cierre} para calcular ratios de precio.
    Modifica result in-place, solo llena campos que siguen siendo None.
    """
    needs = [
        ("per_mediana", "per_actual"),
        ("p_b_mediana", "p_b_actual"),
        ("ev_ebitda_mediana", "ev_ebitda_actual"),
        ("p_fcf_mediana", "p_fcf_actual"),
        ("dividend_yield_mediana", "dividend_yield_actual"),
    ]
    if not any(result.get(med) is None and result.get(act) is not None
               for med, act in needs):
        return  # Ya tiene todas las medianas

    logger.info(f"Usando Stock Analysis como fallback para {ticker}")

    try:
        sa = fetch_ratios_stockanalysis(ticker)

        # PER mediana
        if result.get("per_mediana") is None and sa["per_historia"]:
            result["per_mediana"] = round(float(np.median(sa["per_historia"])), 2)
            logger.debug(f"{ticker} SA PER mediana: {result['per_mediana']}")

        # P/B mediana
        if result.get("p_b_mediana") is None and sa["p_b_historia"]:
            result["p_b_mediana"] = round(float(np.median(sa["p_b_historia"])), 2)
            logger.debug(f"{ticker} SA P/B mediana: {result['p_b_mediana']}")

        # EV/EBITDA mediana (SA también tiene este dato en ratios)
        if result.get("ev_ebitda_mediana") is None and sa["ev_ebitda_historia"]:
            result["ev_ebitda_mediana"] = round(float(np.median(sa["ev_ebitda_historia"])), 2)
            logger.debug(f"{ticker} SA EV/EBITDA mediana: {result['ev_ebitda_mediana']}")

        # P/FCF mediana directa (si SA lo tiene en ratios)
        if result.get("p_fcf_mediana") is None and sa["p_fcf_historia"]:
            result["p_fcf_mediana"] = round(float(np.median(sa["p_fcf_historia"])), 2)
            logger.debug(f"{ticker} SA P/FCF mediana: {result['p_fcf_mediana']}")

        # Dividend Yield mediana
        if result.get("dividend_yield_mediana") is None and sa["dividend_yield_historia"]:
            result["dividend_yield_mediana"] = round(
                float(np.median(sa["dividend_yield_historia"])), 4
            )
            logger.debug(f"{ticker} SA DY mediana: {result['dividend_yield_mediana']}")

        # P/B desde BVPS + precio histórico (fallback si P/B de ratios no disponible)
        if result.get("p_b_mediana") is None and "_bvps_historia_raw" in sa and precio_hist:
            pb_vals = []
            for col, bvps in sa["_bvps_historia_raw"].items():
                match = re.search(r'(20\d{2})', str(col))
                if match and bvps and bvps > 0:
                    year = int(match.group(1))
                    precio = precio_hist.get(year)
                    if precio and precio > 0:
                        val = precio / bvps
                        if 0 < val < 100:
                            pb_vals.append(val)
            if pb_vals:
                result["p_b_mediana"] = round(float(np.median(pb_vals)), 2)

        # P/FCF desde FCF + shares + precio histórico (fallback)
        if result.get("p_fcf_mediana") is None and "_fcf_historia_raw" in sa and precio_hist:
            pfcf_vals = []
            shares_raw = sa.get("_shares_historia_raw", {})
            for col, fcf in sa["_fcf_historia_raw"].items():
                match = re.search(r'(20\d{2})', str(col))
                if not match or fcf is None or fcf <= 0:
                    continue
                year = int(match.group(1))
                precio = precio_hist.get(year)
                if not precio or precio <= 0:
                    continue
                # Buscar shares del mismo año
                shares = None
                for scol, sv in shares_raw.items():
                    smatch = re.search(r'(20\d{2})', str(scol))
                    if smatch and int(smatch.group(1)) == year and sv and sv > 0:
                        shares = sv
                        break
                if shares is None:
                    # Fallback: calcular shares desde market_cap / precio_actual
                    mktcap = result.get("market_cap")
                    p_act = result.get("precio_actual")
                    if mktcap and p_act and p_act > 0:
                        shares = mktcap / p_act
                if shares and shares > 0:
                    fcf_per_share = fcf / shares
                    if fcf_per_share > 0:
                        val = precio / fcf_per_share
                        if 0 < val < 1000:
                            pfcf_vals.append(val)
            if pfcf_vals:
                result["p_fcf_mediana"] = round(float(np.median(pfcf_vals)), 2)

    except Exception as e:
        logger.warning(f"Error enriqueciendo con Stock Analysis para {ticker}: {e}")


# ---------------------------------------------------------------------------
# v1.2.12 - PAGINA DE RATIOS COMPLETA (valor actual + historia en la MISMA fuente)
# ---------------------------------------------------------------------------
# Una sola pagina (/financials/ratios/) trae, para cada ratio, la columna "Current" y las
# columnas de los ultimos 5 anios fiscales ("FY 2025", ...). Con eso se arma tanto el valor
# actual como la mediana historica sin mezclar fuentes.

SA_ETIQUETAS = {
    # metrica: (palabras que debe tener la etiqueta, palabras que NO debe tener)
    "per":            (["pe ratio"], ["forward"]),
    "p_b":            (["pb ratio"], []),
    "ev_ebitda":      (["ev/ebitda"], []),
    "p_fcf":          (["p/fcf"], []),
    "peg":            (["peg ratio"], []),
    "ps":             (["ps ratio"], []),        # v1.2.43: precio / ventas
    "p_ffo":          (["price/ffo"], []),
    "p_affo":         (["price/affo"], []),
    "dividend_yield": (["dividend yield"], []),
}

SA_MIN_PUNTOS = 3   # anios fiscales utiles minimos para usar la mediana de Stock Analysis


def _es_columna_actual(header) -> bool:
    h = str(header).strip().lower()
    return h.startswith("current") or h == "ttm"


def _anio_columna(header) -> Optional[int]:
    m = re.search(r"fy\s*(20\d{2})", str(header).lower())
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"\s*(20\d{2})\s*", str(header))
    if m:
        return int(m.group(1))
    return None


def extraer_metricas_ratios(tabla: dict) -> dict:
    """
    tabla: {etiqueta_de_fila: {encabezado_de_columna: valor}} (salida de _parse_page).
    Devuelve {metrica: {"actual": float|None, "historia": [floats > 0, mas reciente primero]}}.
    Dividend yield se devuelve como decimal (0.0095 = 0,95 %).
    """
    salida = {}
    for metrica, (claves, excluir) in SA_ETIQUETAS.items():
        etiqueta = _find_label(tabla, *claves, exclude=excluir)
        if not etiqueta:
            continue
        actual, por_anio = None, {}
        for columna, valor in tabla[etiqueta].items():
            if _es_columna_actual(columna):
                actual = valor
            else:
                anio = _anio_columna(columna)
                if anio is not None:
                    por_anio[anio] = valor
        anios = sorted(por_anio, reverse=True)[:MAX_YEARS]
        serie = [por_anio[a] for a in anios if por_anio[a] is not None and por_anio[a] > 0]
        if actual is not None and actual <= 0:
            actual = None                      # negativo o cero = sin dato (empresa con perdidas, sin dividendo)
        if metrica == "dividend_yield":        # SA lo muestra en porcentaje
            actual = actual / 100.0 if actual is not None and actual < 50 else None
            serie = [v / 100.0 for v in serie if v < 50]
        salida[metrica] = {"actual": actual, "historia": serie}
    return salida


def fetch_ratios_completos(ticker: str, session=None) -> dict:
    """
    Baja la pagina de ratios anuales de un ticker.
    Devuelve {"ok": bool, "metricas": {...}, "etiquetas": [...], "columnas": [...], "url": str}.
    """
    global _FALLOS_LECTURA
    ticker_url = ticker.lower().replace(".", "-")
    url = f"https://stockanalysis.com/stocks/{ticker_url}/financials/ratios/?p=annual"
    resultado = {"ok": False, "metricas": {}, "etiquetas": [], "columnas": [], "url": url}
    try:
        import requests
        session = session or requests.Session()
        time.sleep(REQUEST_DELAY)
        html = _fetch_html(url, session)
        if not html:
            resultado["error"] = "no se pudo bajar la pagina" + (f" ({ULTIMO_ERROR})" if ULTIMO_ERROR else "")
            return resultado
        tabla = _parse_page(
            html, ["PE Ratio", "PB Ratio", "Dividend Yield", "EV/EBITDA", "P/FCF", "PEG Ratio", "PS Ratio", "FFO"])
        if not tabla:
            # Se bajo bien pero no se entiende: si pasa varias veces seguidas se deja de insistir
            _FALLOS_LECTURA += 1
            resultado["error"] = "la pagina se bajo pero no se pudo leer la tabla"
            return resultado
        resultado["etiquetas"] = list(tabla)[:80]
        resultado["columnas"] = sorted({c for fila in tabla.values() for c in fila})
        resultado["metricas"] = extraer_metricas_ratios(tabla)
        resultado["ok"] = bool(resultado["metricas"])
        _FALLOS_LECTURA = 0 if resultado["ok"] else _FALLOS_LECTURA + 1
    except Exception as e:
        logger.warning(f"Error en Stock Analysis (ratios completos) para {ticker}: {e}")
        resultado["error"] = str(e)
    return resultado


def diagnosticar_pagina(ticker: str, session=None):
    """
    Para el script de prueba: baja la pagina SIN interpretarla y describe que llego.
    Devuelve (lineas_de_texto, bytes_crudos). Sirve para ver por que no se pudo leer la tabla.
    """
    import requests
    ticker_url = ticker.lower().replace(".", "-")
    url = f"https://stockanalysis.com/stocks/{ticker_url}/financials/ratios/?p=annual"
    s = session or requests.Session()
    lineas = []
    crudo = b""
    for etiqueta, enc in (("con los encabezados normales", HEADERS.get("Accept-Encoding")), ("sin compresion", "identity")):
        h = dict(HEADERS)
        h["Accept-Encoding"] = enc
        try:
            r = s.get(url, headers=h, timeout=20)
        except Exception as e:  # noqa: BLE001
            lineas.append(f"[{etiqueta}] FALLO la conexion: {type(e).__name__}: {e}")
            continue
        txt = r.text or ""
        crudo = r.content or crudo
        soup_tablas = txt.lower().count("<table")
        titulo = ""
        i = txt.lower().find("<title>")
        if i >= 0:
            titulo = txt[i + 7: i + 120].split("</")[0].strip()
        marcas = {k: (k.lower() in txt.lower()) for k in
                  ("PE Ratio", "PB Ratio", "Fiscal Year", "Current", "Just a moment", "captcha", "cloudflare", "Upgrade")}
        lineas.append(
            f"[{etiqueta}] HTTP {r.status_code} | {len(txt):,} caracteres | Content-Encoding={r.headers.get('Content-Encoding')} "
            f"| Content-Type={r.headers.get('Content-Type')} | parece HTML={_legible(txt)} | <table>={soup_tablas}")
        lineas.append(f"    Titulo: {titulo!r}")
        lineas.append("    Aparece en la pagina: " + ", ".join(f"{k}={'si' if v else 'no'}" for k, v in marcas.items()))
        lineas.append(f"    Primeros 200 caracteres: {txt[:200]!r}")
        if _legible(txt):
            try:
                tabla = _parse_page(txt, ["PE Ratio", "PB Ratio", "Dividend Yield", "EV/EBITDA", "P/FCF", "PEG Ratio", "PS Ratio", "FFO"])
                lineas.append(f"    El lector entiende {len(tabla)} filas; columnas: "
                              f"{sorted({c for f in tabla.values() for c in f})[:10]}")
            except Exception as e:  # noqa: BLE001
                lineas.append(f"    El lector fallo: {type(e).__name__}: {e}")
            break      # con la primera descarga legible alcanza
    return lineas, crudo


def aplicar_stockanalysis(result: dict, datos_sa: Optional[dict] = None, session=None) -> list:
    """
    Pisa los valores de Yahoo por los de Stock Analysis, metrica por metrica, cuando SA trae el
    valor actual Y al menos SA_MIN_PUNTOS anios de historia (asi actual y mediana salen de la
    misma fuente). Lo que SA no trae se deja como estaba (Yahoo = respaldo).
    Devuelve la lista de metricas tomadas de Stock Analysis. Modifica `result`.
    """
    if datos_sa is None:
        datos_sa = fetch_ratios_completos(result["ticker"], session)
    tomadas = []
    fuentes = dict(result.get("fuentes") or {})
    anios_hist = dict(result.get("anios_historia") or {})
    for metrica, d in (datos_sa.get("metricas") or {}).items():
        actual, serie = d.get("actual"), d.get("historia") or []
        if actual is None or len(serie) < SA_MIN_PUNTOS:
            continue
        dec = 4 if metrica == "dividend_yield" else 2
        result[f"{metrica}_actual"] = round(float(actual), dec)
        result[f"{metrica}_mediana"] = round(float(np.median(serie)), dec)
        fuentes[metrica] = "Stock Analysis"
        anios_hist[metrica] = len(serie)
        if metrica == "dividend_yield":
            # v1.2.28: serie anual (de la mas vieja a la mas nueva) para el minigrafico de la tabla
            result["dividend_yield_serie"] = [round(float(x), 4) for x in reversed(serie)]
        tomadas.append(metrica)
    result["anios_historia"] = anios_hist
    # El dividendo anual (para el Fair Value por DY) sale de Yahoo; si falta, se deduce del DY de SA
    if result.get("annual_dividend") is None and "dividend_yield" in tomadas and result.get("precio_actual"):
        result["annual_dividend"] = round(result["dividend_yield_actual"] * result["precio_actual"], 4)
    result["fuentes"] = fuentes
    return tomadas
