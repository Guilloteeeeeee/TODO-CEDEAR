"""
Motor de scoring del CEDEAR Screener.

Lógica central:
  1. Para cada métrica del sector, calcula qué tan barata está la empresa
     comparando el valor ACTUAL vs la MEDIANA HISTÓRICA.
  2. Normaliza cada métrica a un score de 0-100:
       - 100 = muy barata (actual << mediana histórica)
       - 50  = bien valuada (actual ≈ mediana histórica)
       - 0   = muy cara (actual >> mediana histórica)
  3. Pondera los scores según los pesos del sector.
  4. Agrega el componente técnico (rango 52 semanas, 15%).
  5. Asigna categoría de color según el score final.

v1.2.11 — reglas de datos:
  - Una métrica con un valor imposible (ej.: PER histórico 0,13 por mezclar yenes con dólares)
    se DESCARTA y el score se arma con las métricas que sí funcionan (se reparte su peso).
  - Alcanza con 1 métrica fundamental; si no hay ninguna, la categoría sale del rango de 52 semanas.
  - El PEG se compara contra la mediana de su sector (antes se comparaba contra sí mismo).

v1.2.12 — respaldo de sector:
  - Si a una empresa le falta (o tiene imposible) la mediana histórica propia de una métrica,
    se usa la mediana de su sector (mediana de las medianas propias de sus pares, mínimo 5).
  - El PEG usa su propia historia cuando viene de Stock Analysis; si no, la mediana del sector.
  - Las extranjeras viejas del caché (sin 'fuentes') no usan respaldo, salvo el PEG, porque su
    valor actual también puede estar roto hasta que se actualicen.

Categorías de color:
  🟢 VERDE OSCURO  — Podría estar infravalorada       (score >= 70)
  🟩 VERDE CLARO   — Tendencia a infravalorada        (score >= 58)
  🟡 AMARILLO      — Parece bien valuada              (score >= 42)
  🟠 NARANJA       — Tendencia a sobrevalorada        (score >= 30)
  🔴 ROJO          — Podría estar sobrevalorada       (score < 30)
  ⚫ GRIS          — Sin datos                        (ni métricas ni rango de 52 semanas)
"""

import numpy as np
import pandas as pd
from typing import Optional
from config.sectors import (
    SECTOR_CONFIG, FUNDAMENTAL_WEIGHT, TECHNICAL_WEIGHT, TICKER_TO_SECTOR,
    motivo_descarte, SECTOR_MIN_EMPRESAS,
)


# ---------------------------------------------------------------------------
# UMBRALES DE CATEGORÍAS
# ---------------------------------------------------------------------------

CATEGORIAS = [
    (70, "PODRÍA ESTAR INFRAVALORADA",   "#1a7f37", "🟢"),  # verde oscuro
    (58, "TENDENCIA A INFRAVALORADA",    "#2da44e", "🟩"),  # verde claro
    (42, "PARECE BIEN VALUADA",          "#d4a017", "🟡"),  # amarillo
    (30, "TENDENCIA A SOBREVALORADA",    "#e16a1a", "🟠"),  # naranja
    (0,  "PODRÍA ESTAR SOBREVALORADA",   "#cf222e", "🔴"),  # rojo
]
CATEGORIA_GRIS = ("DATOS INSUFICIENTES", "#6e7781", "⚫")

# Mínimo de métricas fundamentales para armar el score fundamental.
# v1.2.11: con 1 alcanza ("mejor algo que nada"): las métricas descartadas por datos rotos
# no hacen caer a la empresa a "datos insuficientes"; el score se arma con las que sí funcionan.
# La columna "Métricas" (n/N) muestra cuán sólido es el resultado.
MIN_METRICAS = 1

# Cuántas métricas del sector debe tener disponibles (de 4) para armar el score fundamental
MIN_METRICAS_DEL_SECTOR = 1


# ---------------------------------------------------------------------------
# NORMALIZACIÓN DE MÉTRICAS
# ---------------------------------------------------------------------------

def _score_metrica(actual: Optional[float], mediana: Optional[float],
                   metrica: str) -> Optional[float]:
    """
    Convierte la comparación actual/mediana en score 0-100.

    Para métricas de precio (EV/EBITDA, PER, P/FCF, P/B, PEG, P/FFO, P/AFFO):
      - Menor actual que mediana = barata = score alto
      - ratio = actual / mediana
      - Usamos función sigmoide invertida centrada en 1.0

    Para dividend_yield:
      - Mayor actual que mediana = más rendimiento = score alto (lógica inversa)
    """
    # None o NaN = métrica faltante (pandas convierte None en NaN dentro de un DataFrame;
    # un NaN que se cuela contamina toda la suma ponderada y deja la empresa en gris)
    if actual is None or mediana is None:
        return None
    if pd.isna(actual) or pd.isna(mediana):
        return None
    if mediana <= 0 or actual < 0:
        return None
    # v1.2.11: dato imposible (moneda mezclada, ADR, etc.) -> la métrica se descarta
    if motivo_descarte(metrica, actual, mediana):
        return None

    YIELD_METRICS = {"dividend_yield"}

    if metrica in YIELD_METRICS:
        # Mayor yield = mejor = score alto
        ratio = actual / mediana
    else:
        # Menor múltiplo = más barato = score alto → invertimos el ratio
        ratio = mediana / actual  # > 1 si actual < mediana (barata)

    # Sigmoide suavizada: score = 100 / (1 + e^(-k*(ratio-1)))
    # k=4 da una curva que va de ~18 en ratio=0.5 a ~82 en ratio=1.5
    k = 4.0
    score = 100.0 / (1.0 + np.exp(-k * (ratio - 1.0)))
    return round(float(score), 1)


def _estado_metrica(metrica: str, actual, mediana) -> tuple[str, Optional[str]]:
    """('ok' | 'descartada' | 'sin dato', motivo) para mostrar por qué una métrica no cuenta."""
    def falta(v):
        return v is None or pd.isna(v)
    if falta(actual) and falta(mediana):
        return "sin dato", "sin valor actual ni mediana"
    if falta(actual):
        return "sin dato", "sin valor actual"
    if falta(mediana):
        return "sin dato", "sin mediana histórica"
    if mediana <= 0 or actual < 0:
        return "descartada", "valor no positivo"
    motivo = motivo_descarte(metrica, actual, mediana)
    if motivo:
        return "descartada", motivo
    return "ok", None


# ---------------------------------------------------------------------------
# SCORE TÉCNICO (RANGO 52 SEMANAS)
# ---------------------------------------------------------------------------

def _score_tecnico(posicion_52s: Optional[float]) -> Optional[float]:
    """
    Convierte la posición en el rango 52 semanas a score 0-100.

    posicion_52s = (precio - mínimo) / (máximo - mínimo), de 0 a 1.
      - 0.0 = precio en el mínimo del año → muy barata por precio → score 100
      - 1.0 = precio en el máximo del año → muy cara por precio  → score 0
      - 0.5 = mitad del rango → neutro → score 50
    """
    if posicion_52s is None or pd.isna(posicion_52s):
        return None
    # Inversión lineal simple: score = (1 - posicion) * 100
    return round((1.0 - posicion_52s) * 100.0, 1)


# ---------------------------------------------------------------------------
# SCORE FUNDAMENTAL POR EMPRESA
# ---------------------------------------------------------------------------

def _score_fundamental(row: dict, sector: str) -> tuple[Optional[float], int, int]:
    """
    Calcula el score fundamental ponderado para una empresa en su sector.

    Retorna:
      - score_fundamental (0-100) o None si no hay suficientes métricas
      - metricas_usadas: cantidad de métricas que aportaron al score
      - metricas_total: cantidad de métricas del sector
    """
    if sector not in SECTOR_CONFIG:
        return None, 0, 0

    config = SECTOR_CONFIG[sector]["metrics"]
    metricas_total = len(config)

    scores_ponderados = []
    peso_acumulado = 0.0
    metricas_usadas = 0

    for metrica, peso in config.items():
        actual_key = f"{metrica}_actual"
        mediana_key = f"{metrica}_mediana"

        actual = row.get(actual_key)
        mediana = row.get(mediana_key)

        score = _score_metrica(actual, mediana, metrica)

        if score is not None:
            scores_ponderados.append(score * peso)
            peso_acumulado += peso
            metricas_usadas += 1

    if metricas_usadas < MIN_METRICAS_DEL_SECTOR or peso_acumulado == 0:
        return None, metricas_usadas, metricas_total

    # Renormalizar por el peso acumulado (por si faltan métricas)
    score_fund = sum(scores_ponderados) / peso_acumulado
    return round(score_fund, 1), metricas_usadas, metricas_total


# ---------------------------------------------------------------------------
# SCORE TOTAL Y CATEGORÍA
# ---------------------------------------------------------------------------

def calcular_score(row: dict, sector: str) -> dict:
    """
    Calcula el score total y asigna categoría de color para una empresa.

    Retorna dict con:
      - score_fundamental, score_tecnico, score_total
      - metricas_usadas, metricas_total
      - categoria, color_hex, emoji
      - detalle: dict con score individual por métrica
    """
    resultado = {
        "score_fundamental": None,
        "score_tecnico": None,
        "score_total": None,
        "metricas_usadas": 0,
        "metricas_total": 0,
        "categoria": CATEGORIA_GRIS[0],
        "color_hex": CATEGORIA_GRIS[1],
        "emoji": CATEGORIA_GRIS[2],
        "detalle": {},
    }

    # Score fundamental
    score_fund, usadas, total = _score_fundamental(row, sector)
    resultado["metricas_usadas"] = usadas
    resultado["metricas_total"] = total

    # Score técnico
    score_tec = _score_tecnico(row.get("posicion_52s"))
    resultado["score_tecnico"] = score_tec

    if score_fund is None:
        # Ninguna métrica fundamental usable. Sin etiquetas de "datos insuficientes" (pedido del
        # usuario): si hay rango de 52 semanas, la categoría sale solo de él. La columna
        # "Métricas" muestra 0/N para que se vea que es una lectura débil.
        if score_tec is None or sector not in SECTOR_CONFIG:
            return resultado
        score_total = score_tec
    else:
        resultado["score_fundamental"] = score_fund
        # Score total
        if score_tec is not None:
            score_total = (score_fund * FUNDAMENTAL_WEIGHT) + (score_tec * TECHNICAL_WEIGHT)
        else:
            # Si no hay dato técnico, el fundamental es el 100%
            score_total = score_fund

    resultado["score_total"] = round(score_total, 1)

    # Categoría de color
    for umbral, nombre, color, emoji in CATEGORIAS:
        if score_total >= umbral:
            resultado["categoria"] = nombre
            resultado["color_hex"] = color
            resultado["emoji"] = emoji
            break

    # Detalle por métrica (para el panel de desglose)
    if sector in SECTOR_CONFIG:
        for metrica, peso in SECTOR_CONFIG[sector]["metrics"].items():
            actual = row.get(f"{metrica}_actual")
            mediana = row.get(f"{metrica}_mediana")
            score_m = _score_metrica(actual, mediana, metrica)
            estado, motivo = _estado_metrica(metrica, actual, mediana)
            resultado["detalle"][metrica] = {
                "actual": actual,
                "mediana": mediana,
                "score": score_m,
                "peso": peso,
                "estado": estado,
                "motivo": motivo,
            }

    return resultado


# ---------------------------------------------------------------------------
# PROCESAR DATAFRAME COMPLETO
# ---------------------------------------------------------------------------

def _num_ok(v) -> bool:
    return v is not None and not pd.isna(v)


def _fuentes_de(row) -> dict:
    f = row.get("fuentes") if hasattr(row, "get") else None
    return f if isinstance(f, dict) else {}


def _mediana_propia_valida(row, metrica: str) -> Optional[float]:
    """
    Mediana historica PROPIA de la empresa si es utilizable; None si falta o es imposible.
    El PEG solo cuenta como propio si viene con historia real (Stock Analysis): en versiones
    anteriores se guardaba el PEG actual (o la mediana del sector) en ese campo.
    """
    med = row.get(f"{metrica}_mediana")
    if not _num_ok(med) or med <= 0:
        return None
    if motivo_descarte(metrica, None, med):
        return None
    if metrica == "peg" and _fuentes_de(row).get("peg") != "Stock Analysis":
        return None
    return float(med)


def _actual_valido(row, metrica: str) -> bool:
    a = row.get(f"{metrica}_actual")
    return _num_ok(a) and a > 0 and not motivo_descarte(metrica, a, None)


def _apto_respaldo_sector(row) -> bool:
    """
    El respaldo de sector se aplica cuando el valor ACTUAL tambien es confiable:
    filas bajadas con la version nueva (traen 'fuentes') o empresas de EEUU. Las extranjeras
    viejas del cache pueden tener el valor actual roto (moneda / ADR) hasta que se actualicen.
    """
    if _fuentes_de(row):
        return True
    pais = row.get("pais")
    if not _num_ok(pais):
        return True
    return str(pais) in ("United States", "USA", "US")


def referencias_sector(df: pd.DataFrame, ticker_to_sector: dict = None,
                       referencia: Optional[pd.DataFrame] = None) -> dict:
    """
    {sector: {metrica: valor}}: lo que cuestan "normalmente" las empresas del sector, calculado
    como la mediana de las medianas historicas PROPIAS validas de sus pares (minimo
    SECTOR_MIN_EMPRESAS pares). Para el PEG, si no hay suficientes medianas propias se usa la
    mediana de los PEG actuales de los pares.
    `referencia` suma empresas que no estan en `df` (ej.: al actualizar un solo ticker).
    """
    if ticker_to_sector is None:
        ticker_to_sector = TICKER_TO_SECTOR
    base = df if referencia is None else pd.concat(
        [df, referencia[~referencia["ticker"].isin(df["ticker"])]], ignore_index=True)
    propias: dict = {}
    actuales_peg: dict = {}
    for _, r in base.iterrows():
        sector = ticker_to_sector.get(r.get("ticker", ""), "")
        cfg = SECTOR_CONFIG.get(sector, {}).get("metrics", {})
        for m in cfg:
            v = _mediana_propia_valida(r, m)
            if v is not None:
                propias.setdefault((sector, m), []).append(v)
            if m == "peg" and _num_ok(r.get("peg_actual")) and r["peg_actual"] > 0:
                actuales_peg.setdefault(sector, []).append(float(r["peg_actual"]))
    refs: dict = {}
    for (sector, m), vals in propias.items():
        if len(vals) >= SECTOR_MIN_EMPRESAS:
            refs.setdefault(sector, {})[m] = round(float(np.median(vals)), 4)
    for sector, vals in actuales_peg.items():
        if "peg" not in refs.get(sector, {}) and len(vals) >= SECTOR_MIN_EMPRESAS:
            refs.setdefault(sector, {})["peg"] = round(float(np.median(vals)), 4)
    return refs


def peg_mediana_por_sector(df: pd.DataFrame, ticker_to_sector: dict = None,
                           referencia: Optional[pd.DataFrame] = None) -> dict:
    """Mediana de referencia del PEG por sector (compatibilidad con v1.2.11)."""
    return {sec: m["peg"] for sec, m in referencias_sector(df, ticker_to_sector, referencia).items()
            if "peg" in m}


def aplicar_respaldo_sector(datos: dict, sector: str, refs: dict) -> dict:
    """
    Si a una empresa le falta (o tiene imposible) la mediana historica propia de una metrica
    de su sector, y su valor actual es creible, usa la mediana del sector.
    Modifica `datos` (una copia de trabajo) y devuelve {metrica: valor_usado}.
    """
    usados: dict = {}
    if sector not in SECTOR_CONFIG:
        return usados
    apto = _apto_respaldo_sector(datos)
    for m in SECTOR_CONFIG[sector]["metrics"]:
        # El PEG lo calcula Yahoo/Stock Analysis como cociente de ratios y no se vio roto por moneda
        # o ADR: se permite siempre. Las demas metricas, solo si el valor actual tambien es confiable.
        if not apto and m != "peg":
            continue
        if _mediana_propia_valida(datos, m) is not None or not _actual_valido(datos, m):
            continue
        ref = refs.get(sector, {}).get(m)
        if ref is None:
            continue
        datos[f"{m}_mediana"] = ref
        usados[m] = ref
    return usados


def score_dataframe(df: pd.DataFrame, ticker_to_sector: dict = None,
                    referencia: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Aplica el scoring a todo el DataFrame de tickers.
    Agrega columnas: score_fundamental, score_tecnico, score_total,
                     categoria, color_hex, emoji, metricas_usadas, metricas_total,
                     fair_value, fair_value_detalle, fair_value_metodos,
                     respaldo_sector.

    v1.2.12: si la mediana propia de una metrica falta o es imposible, se compara contra la
    mediana de su sector (ver referencias_sector). Los datos originales de la fila no se pisan:
    el valor usado queda en `detalle[metrica]` y en `respaldo_sector`.
    """
    from data.fetcher import calc_fair_value

    if ticker_to_sector is None:
        ticker_to_sector = TICKER_TO_SECTOR

    refs = referencias_sector(df, ticker_to_sector, referencia)

    rows = []
    for _, row in df.iterrows():
        ticker = row.get("ticker", "")
        sector = ticker_to_sector.get(ticker, "")
        datos = row.to_dict()
        calc = dict(datos)
        usados = aplicar_respaldo_sector(calc, sector, refs)
        resultado = calcular_score(calc, sector)
        fv_resultado = calc_fair_value(calc, sector)
        fuentes = _fuentes_de(row)
        for m, d in resultado["detalle"].items():
            d["fuente"] = fuentes.get(m)
            d["referencia"] = "sector" if m in usados else "propia"
        rows.append({**datos, **resultado, **fv_resultado, "sector": sector,
                     "respaldo_sector": usados})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# UTILIDADES DE VISUALIZACIÓN
# ---------------------------------------------------------------------------

def get_categoria_label(score: Optional[float]) -> tuple[str, str, str]:
    """
    Dado un score, retorna (categoria, color_hex, emoji).
    Útil para tests y generación de leyendas.
    """
    if score is None:
        return CATEGORIA_GRIS

    for umbral, nombre, color, emoji in CATEGORIAS:
        if score >= umbral:
            return nombre, color, emoji

    return CATEGORIA_GRIS


def leyenda_categorias() -> list[dict]:
    """Retorna la leyenda completa para mostrar en la app."""
    leyenda = []
    thresholds = [
        ("🟢", "PODRÍA ESTAR INFRAVALORADA",   "#1a7f37", "Score ≥ 70"),
        ("🟩", "TENDENCIA A INFRAVALORADA",    "#2da44e", "Score 58–69"),
        ("🟡", "PARECE BIEN VALUADA",          "#d4a017", "Score 42–57"),
        ("🟠", "TENDENCIA A SOBREVALORADA",    "#e16a1a", "Score 30–41"),
        ("🔴", "PODRÍA ESTAR SOBREVALORADA",   "#cf222e", "Score < 30"),
        ("⚫", "DATOS INSUFICIENTES",          "#6e7781", "Sin métricas ni rango de 52 semanas"),
    ]
    for emoji, nombre, color, rango in thresholds:
        leyenda.append({
            "emoji": emoji,
            "nombre": nombre,
            "color": color,
            "rango": rango,
        })
    return leyenda
