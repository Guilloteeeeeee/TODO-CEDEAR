"""Multiplos de cada anio fiscal (v1.2.57), de Stock Analysis: P/E, P/Book, P/S, EV/Ventas, EV/EBITDA, P/FCF, PEG y Dividend Yield.
Los baja `bajar_multiplos_anuales.py` (script aparte, no toca el cache ni los puntajes) y se guardan en data/multiplos_anuales.json:
{"fecha": "dd/mm/aaaa", "datos": {TICKER: {metrica: {"2025": valor, "2024": valor, ...}}}}. Si el archivo no esta, la pantalla muestra la tabla sin esas columnas."""
import json
import os

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "multiplos_anuales.json")
METRICAS = ("per", "p_b", "ps", "ev_ventas", "ev_ebitda", "p_fcf", "peg", "dividend_yield")


def cargar(ruta=None):
    """({TICKER: {metrica: {anio(int): valor}}}, fecha|None). ({}, None) si el archivo no esta o no se puede leer."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        datos = {}
        for t, ms in (d.get("datos") or {}).items():
            datos[str(t).upper()] = {m: {int(a): float(v) for a, v in (xs or {}).items()} for m, xs in ms.items() if isinstance(xs, dict)}
        return datos, d.get("fecha")
    except Exception:  # noqa: BLE001
        return {}, None


def desde_metricas(metricas, max_anios=10):
    """De la salida de stockanalysis.fetch_ratios_completos()['metricas'] -> {metrica: {anio: valor}} (solo las que se muestran y con valores > 0)."""
    out = {}
    for m in METRICAS:
        xs = (metricas.get(m) or {}).get("anios") or {}
        xs = {int(a): float(v) for a, v in sorted(xs.items(), reverse=True)[:max_anios] if v is not None and v > 0}
        if xs:
            out[m] = xs
    return out
