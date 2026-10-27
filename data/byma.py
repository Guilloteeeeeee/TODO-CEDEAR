"""Lista oficial de CEDEARs de BYMA (v1.2.66): simbolo, nombre, mercado de origen y ratio de los 445 CEDEARs negociables.
Fuente: PDF "CEDEARs Negociables en BYMA" actualizado el 16/09/2026 + planilla de nuevos CEDEARs del 19/08 (ISIN, monto maximo). Se guarda en
data/byma_cedears.json para sumar de a poco los instrumentos que faltan en la app. Los ratios de cedears.csv y etfs.csv se controlan contra este archivo
(ver `controlar`)."""
import json
import os

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "byma_cedears.json")


def cargar(ruta=None):
    """({SIMBOLO: {...}}, fecha_del_pdf). ({}, None) si el archivo no esta."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        return {str(k).upper(): v for k, v in (d.get("cedears") or {}).items()}, d.get("fecha_pdf")
    except Exception:  # noqa: BLE001
        return {}, None


def ratio_oficial(simbolo, datos=None):
    """Ratio de BYMA como texto ('20:1') o None si el simbolo no figura."""
    datos = datos if datos is not None else cargar()[0]
    r = datos.get(str(simbolo or "").upper())
    return r.get("ratio") if r else None


def controlar(ratios, datos=None):
    """ratios: {simbolo: ratio_texto} -> lista de (simbolo, ratio_propio, ratio_BYMA) que no coinciden. Los que no figuran en BYMA no se marcan."""
    from data import cedears as _c
    datos = datos if datos is not None else cargar()[0]
    out = []
    for s, r in ratios.items():
        of = ratio_oficial(s, datos)
        if of is None or not str(r or "").strip():
            continue
        if _c.leer_ratio(r) != _c.leer_ratio(of):
            out.append((s, r, of))
    return out
