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

Categorías de color:
  🟢 VERDE OSCURO  — Podría estar infravalorada       (score >= 70)
  🟩 VERDE CLARO   — Tendencia a infravalorada        (score >= 58)
  🟡 AMARILLO      — Parece bien valuada              (score >= 42)
  🟠 NARANJA       — Tendencia a sobrevalorada        (score >= 30)
  🔴 ROJO          — Podría estar sobrevalorada       (score < 30)
  ⚫ GRIS          — Datos insuficientes              (< 2 métricas disponibles)
"""

import numpy as np
import pandas as pd
from typing import Optional
from config.sectors import SECTOR_CONFIG, FUNDAMENTAL_WEIGHT, TECHNICAL_WEIGHT, TICKER_TO_SECTOR


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

# Mínimo de métricas fundamentales para asignar categoría (no gris)
MIN_METRICAS = 2

# Cuántas métricas del sector debe tener disponibles (de 4) para no ser gris
MIN_METRICAS_DEL_SECTOR = 2


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
    if actual is None or mediana is None:
        return None
    if mediana <= 0 or actual < 0:
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
    if posicion_52s is None:
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

    if score_fund is None:
        return resultado

    resultado["score_fundamental"] = score_fund

    # Score técnico
    score_tec = _score_tecnico(row.get("posicion_52s"))
    resultado["score_tecnico"] = score_tec

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
            resultado["detalle"][metrica] = {
                "actual": actual,
                "mediana": mediana,
                "score": score_m,
                "peso": peso,
            }

    return resultado


# ---------------------------------------------------------------------------
# PROCESAR DATAFRAME COMPLETO
# ---------------------------------------------------------------------------

def score_dataframe(df: pd.DataFrame, ticker_to_sector: dict = None) -> pd.DataFrame:
    """
    Aplica el scoring a todo el DataFrame de tickers.
    Agrega columnas: score_fundamental, score_tecnico, score_total,
                     categoria, color_hex, emoji, metricas_usadas, metricas_total.
    """
    if ticker_to_sector is None:
        ticker_to_sector = TICKER_TO_SECTOR

    rows = []
    for _, row in df.iterrows():
        ticker = row.get("ticker", "")
        sector = ticker_to_sector.get(ticker, "")
        resultado = calcular_score(row.to_dict(), sector)
        rows.append({**row.to_dict(), **resultado, "sector": sector})

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
        ("⚫", "DATOS INSUFICIENTES",          "#6e7781", "< 2 métricas disponibles"),
    ]
    for emoji, nombre, color, rango in thresholds:
        leyenda.append({
            "emoji": emoji,
            "nombre": nombre,
            "color": color,
            "rango": rango,
        })
    return leyenda
