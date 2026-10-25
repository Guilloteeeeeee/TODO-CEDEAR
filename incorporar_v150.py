"""
v1.2.50 - Pone al dia el cache con los datos nuevos de la auditoria, SIN volver a bajar nada, y vuelve a puntuar todo.
Mantiene la fecha original del cache.

Usa los dos archivos que ya bajaste con probar_ps.bat y probar_roe_recompras.bat:
    resultados_ps.json              (P/S, EV/Ventas y demas multiplos con 5 anios fiscales)
    resultados_roe_recompras.json   (Dividend Yield y recompras netas con 5 anios fiscales)

Uso (desde la carpeta del proyecto):
    python incorporar_v150.py
    python incorporar_v150.py ruta/resultados_ps.json ruta/resultados_roe_recompras.json

Que hace:
  1. Quita del cache el P/FFO y el P/AFFO que eran el P/E disfrazado ("Yahoo (aprox. con PER)").
  2. Guarda cuantos anios de historia hay detras de cada mediana de Stock Analysis (el cache solo traia los del P/S).
  3. Carga EV/Ventas (ev_ventas) y el Rendimiento total = dividendo + recompras netas (rend_total), con la misma regla de siempre:
     valor actual + al menos 3 anios fiscales (SA_MIN_PUNTOS); mediana de hasta 5 anios.
  4. Calcula ev_sobre_cap = (EV/Ventas) / (P/S): valor de la empresa sobre valor de mercado, para el puente de deuda del Fair Value.
  5. Vuelve a puntuar todo el cache (puntaje, categoria y Fair Value) y lo guarda de forma segura (archivo temporal + reemplazo).
Con el generador normal (generar_cache.bat) esto ya no hace falta: todo se baja junto.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import stockanalysis as sa
from data.cache_seguro import guardar_seguro, marcar_fecha_dato
from scoring.engine import score_dataframe

CACHE_PATH = "data/cache_datos.json"
METRICAS_CON_ANIOS = ("per", "p_b", "ev_ebitda", "p_fcf", "peg", "ps")


def _limpiar(o):
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _limpiar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_limpiar(v) for v in o]
    return o


def _anios(fila):
    return {int(a): v for a, v in ((fila or {}).get("anios") or {}).items()}


def serie_de(fila):
    """Valores positivos de los ultimos MAX_YEARS anios fiscales, del mas nuevo al mas viejo (igual que Stock Analysis en el generador)."""
    por_anio = _anios(fila)
    return [por_anio[a] for a in sorted(por_anio, reverse=True)[:sa.MAX_YEARS] if por_anio[a] is not None and por_anio[a] > 0]


def multiplo_de(fila):
    """(actual, mediana, anios) de un multiplo, o None si no se puede usar."""
    if not fila or fila.get("actual") is None or fila["actual"] <= 0:
        return None
    serie = serie_de(fila)
    if len(serie) < sa.SA_MIN_PUNTOS:
        return None
    return round(float(fila["actual"]), 2), round(float(np.median(serie)), 2), len(serie)


def rend_total_de(fila_dy, fila_bb):
    """(actual, mediana, anios) del rendimiento total (fraccion), o None."""
    if not fila_bb:
        return None
    actual, historia = sa.calcular_rend_total((fila_dy or {}).get("actual"), _anios(fila_dy), fila_bb.get("actual"), _anios(fila_bb))
    if actual is None or len(historia) < sa.SA_MIN_PUNTOS:
        return None
    return round(float(actual), 4), round(float(np.median(historia)), 4), len(historia)


def main(ruta_ps="resultados_ps.json", ruta_roe="resultados_roe_recompras.json"):
    with open(ruta_ps, encoding="utf-8") as f:
        datos_ps = json.load(f)
    with open(ruta_roe, encoding="utf-8") as f:
        datos_roe = json.load(f)
    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)
    filas = cache["data"]
    antes = {r["ticker"]: (r.get("score_total"), r.get("categoria"), r.get("fair_value")) for r in filas}

    sin_proxy, con_ev, con_rt = 0, 0, 0
    for r in filas:
        t = r["ticker"]
        fuentes = dict(r.get("fuentes") or {})
        anios = dict(r.get("anios_historia") or {})
        # 1) P/FFO y P/AFFO que eran el P/E
        for m in ("p_ffo", "p_affo"):
            # solo vale el dato de Stock Analysis; cualquier otro (la aproximacion con el P/E, con o sin etiqueta) se quita
            if fuentes.get(m) != "Stock Analysis" and (r.get(f"{m}_actual") is not None or r.get(f"{m}_mediana") is not None):
                r[f"{m}_actual"], r[f"{m}_mediana"] = None, None
                fuentes.pop(m, None)
                anios.pop(m, None)
                sin_proxy += 1
        # 2) anios de historia detras de cada mediana de Stock Analysis
        filas_ps = ((datos_ps.get(t) or {}).get("filas")) or {}
        for m in METRICAS_CON_ANIOS:
            if fuentes.get(m) == "Stock Analysis" and filas_ps.get(m):
                anios[m] = len(serie_de(filas_ps[m]))
        filas_roe = ((datos_roe.get(t) or {}).get("filas")) or {}
        if fuentes.get("dividend_yield") == "Stock Analysis" and filas_roe.get("dividend_yield"):
            fila = filas_roe["dividend_yield"]
            anios["dividend_yield"] = len([v for v in serie_de(fila) if v < 50])
        # 3) EV/Ventas y Rendimiento total
        ev = multiplo_de(filas_ps.get("ev_sales"))
        if ev:
            r["ev_ventas_actual"], r["ev_ventas_mediana"] = ev[0], ev[1]
            fuentes["ev_ventas"], anios["ev_ventas"] = "Stock Analysis", ev[2]
            con_ev += 1
        else:
            r["ev_ventas_actual"], r["ev_ventas_mediana"] = None, None
            fuentes.pop("ev_ventas", None); anios.pop("ev_ventas", None)
        rt = rend_total_de(filas_roe.get("dividend_yield"), filas_roe.get("recompras"))
        if rt:
            r["rend_total_actual"], r["rend_total_mediana"] = rt[0], rt[1]
            fuentes["rend_total"], anios["rend_total"] = "Stock Analysis", rt[2]
            con_rt += 1
        else:
            r["rend_total_actual"], r["rend_total_mediana"] = None, None
            fuentes.pop("rend_total", None); anios.pop("rend_total", None)
        # 4) valor de la empresa / valor de mercado
        ps_a = r.get("ps_actual")
        pa = filas_ps.get("ps") or {}
        ev_a = (filas_ps.get("ev_sales") or {}).get("actual")
        if ev_a and pa.get("actual"):
            r["ev_sobre_cap"] = round(float(ev_a) / float(pa["actual"]), 4)
        else:
            r["ev_sobre_cap"] = None
        r["fuentes"], r["anios_historia"] = fuentes, anios
    print(f"P/FFO o P/AFFO aproximados con el P/E quitados: {sin_proxy}")
    print(f"EV/Ventas cargado en {con_ev} de {len(filas)} empresas; Rendimiento total en {con_rt}")

    nuevas = _limpiar(score_dataframe(pd.DataFrame(filas)).replace({float("nan"): None}).to_dict(orient="records"))
    cambian_cat = [(r["ticker"], antes[r["ticker"]][1], r.get("categoria")) for r in nuevas if antes[r["ticker"]][1] != r.get("categoria")]
    cambian_fv = [(r["ticker"], antes[r["ticker"]][2], r.get("fair_value")) for r in nuevas if antes[r["ticker"]][2] != r.get("fair_value")]
    print(f"Empresas cuya categoria cambia: {len(cambian_cat)}")
    for t, a, b in cambian_cat:
        print(f"   {t}: {a} -> {b}")
    print(f"Empresas cuyo Fair Value cambia: {len(cambian_fv)}")
    marcar_fecha_dato(nuevas, str(cache.get("timestamp", ""))[:10])   # cada fila dice de que dia son sus datos
    cache["data"] = nuevas
    guardar_seguro(cache, CACHE_PATH)
    print(f"Cache guardado en {CACHE_PATH} con {len(nuevas)} empresas (fecha original sin cambios).")


if __name__ == "__main__":
    main(*(sys.argv[1:3] or []))
