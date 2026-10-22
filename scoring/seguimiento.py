"""
Seguimiento del screener (v1.2.13): compara, entre una copia y la siguiente, cuanto subieron o bajaron las empresas
segun la categoria que tenian en una copia anterior del cache (data/historial/cache_AAAA-MM-DD.json).

Se calcula para dos formas de puntuar:
  - "oficial":   contra la historia propia de cada empresa (columna `categoria`)
  - "vs sector": contra sus pares del sector, puntaje en sombra (columna `categoria_sector`)

Solo mide variacion de PRECIO (no incluye dividendos). Con pocos meses no es concluyente.
"""
import glob
import json
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

HISTORIAL_DIR = os.path.join("data", "historial")
MIN_DIAS_ENTRE_COPIAS = 20

CATEGORIAS_ORDEN = [
    "PODRÍA ESTAR INFRAVALORADA",
    "TENDENCIA A INFRAVALORADA",
    "PARECE BIEN VALUADA",
    "TENDENCIA A SOBREVALORADA",
    "PODRÍA ESTAR SOBREVALORADA",
]
GRUPO_BARATAS = {"PODRÍA ESTAR INFRAVALORADA", "TENDENCIA A INFRAVALORADA"}
GRUPO_CARAS = {"PODRÍA ESTAR SOBREVALORADA", "TENDENCIA A SOBREVALORADA"}


def cargar_copias(directorio: str = HISTORIAL_DIR) -> list:
    """[(fecha, DataFrame)] ordenado por fecha, a partir de data/historial/cache_*.json."""
    copias = []
    for ruta in sorted(glob.glob(os.path.join(directorio, "cache_*.json"))):
        try:
            with open(ruta, encoding="utf-8") as f:
                c = json.load(f)
            copias.append((datetime.fromisoformat(c["timestamp"]), pd.DataFrame(c["data"])))
        except Exception:
            continue
    copias.sort(key=lambda x: x[0])
    return copias


def _retornos_par(ini: pd.DataFrame, fin: pd.DataFrame) -> pd.DataFrame:
    m = ini.merge(fin[["ticker", "precio_actual"]], on="ticker", suffixes=("", "_fin"))
    m = m[(m["precio_actual"] > 0) & (m["precio_actual_fin"] > 0)].copy()
    m["ret"] = (m["precio_actual_fin"] / m["precio_actual"] - 1.0) * 100.0
    return m


def _spread(m: pd.DataFrame, col: str) -> Optional[float]:
    if col not in m.columns:
        return None
    baratas = m.loc[m[col].isin(GRUPO_BARATAS), "ret"]
    caras = m.loc[m[col].isin(GRUPO_CARAS), "ret"]
    if baratas.empty or caras.empty:
        return None
    return float(baratas.mean() - caras.mean())


def proxima_medicion(copias: list, min_dias: int = MIN_DIAS_ENTRE_COPIAS):
    """Fecha desde la cual otra copia permitiría medir (última copia + min_dias), o None si no hay copias."""
    if not copias:
        return None
    return (copias[-1][0] + timedelta(days=min_dias)).date()


def evaluar_copias(copias: list, min_dias: int = MIN_DIAS_ENTRE_COPIAS) -> dict:
    """
    Usa pares de copias consecutivas separadas por al menos `min_dias` dias.
    Devuelve {"pares": [...], "tablas": {"oficial": DataFrame, "sector": DataFrame}, "todas": float}.
    """
    pares, acumulado = [], []
    for (f1, d1), (f2, d2) in zip(copias, copias[1:]):
        dias = (f2 - f1).days
        if dias < min_dias:
            continue
        m = _retornos_par(d1, d2)
        if m.empty:
            continue
        pares.append({
            "desde": f1.date(), "hasta": f2.date(), "dias": dias, "empresas": len(m),
            "todas": float(m["ret"].mean()),
            "spread_oficial": _spread(m, "categoria"),
            "spread_sector": _spread(m, "categoria_sector"),
        })
        acumulado.append(m)
    salida = {"pares": pares, "tablas": {}, "todas": None}
    if not acumulado:
        return salida
    todo = pd.concat(acumulado, ignore_index=True)
    salida["todas"] = float(todo["ret"].mean())
    for clave, col in (("oficial", "categoria"), ("sector", "categoria_sector")):
        if col not in todo.columns:
            continue
        g = todo[todo[col].isin(CATEGORIAS_ORDEN)].groupby(col)["ret"].agg(["count", "mean"])
        g = g.reindex(CATEGORIAS_ORDEN).dropna(how="all")
        g.columns = ["Empresas", "Variación media del precio (%)"]
        salida["tablas"][clave] = g
    return salida
