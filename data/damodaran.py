"""
Medias de industria de Aswath Damodaran (EE.UU., enero 2026), cargadas de las planillas que Guille copió de su página (data/damodaran/*.txt).
v1.2.88: sólo CARGA y CONSULTA (todavía no se muestra en pantalla: falta que Guille apruebe la tabla empresa -> industria de data/damodaran_mapa.py).
Fuente a citar: "Damodaran, ene-2026, empresas de EE.UU.". Se actualiza una vez por año (en enero).
"""
import os
import re
from functools import lru_cache

FUENTE = "Damodaran, ene-2026 (empresas de EE.UU.)"
_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "damodaran")
ARCHIVOS = ("margin", "pbvdata", "pedata", "vebitda", "psdata", "wacc", "betas", "capex", "fundgrEB")


def _num(x):
    x = (x or "").strip()
    if not x or x.upper() == "NA":
        return None
    pct = x.endswith("%")
    x = x.replace("%", "").replace("$", "").replace(",", "")
    try:
        return float(x)          # los porcentajes quedan en puntos (12,3 % -> 12.3)
    except ValueError:
        return None


def _leer(nombre):
    """-> (columnas, {industria: [valores]}) con los nombres tal cual figuran en la planilla."""
    with open(os.path.join(_DIR, nombre + ".txt"), encoding="utf-8") as f:
        lineas = f.read().splitlines()
    i = next(k for k, l in enumerate(lineas) if l.lstrip().startswith("Industry Name"))
    cols = [c.strip() for c in lineas[i].split("\t")]
    filas = {}
    for l in lineas[i + 1:]:
        p = l.split("\t")
        if len(p) < 3 or not p[0].strip() or not re.match(r"^\d+$", p[1].strip()):
            continue
        filas[p[0].strip()] = [_num(x) for x in p[1:len(cols)]]
    return cols[1:], filas


@lru_cache(maxsize=1)
def cargar():
    """{industria canónica: {archivo: {columna: valor}}}. Las industrias con nombre cortado en alguna planilla se igualan por prefijo con las de 'margin'."""
    cols0, base = _leer("margin")
    canon = list(base)
    out = {c: {} for c in canon}
    for a in ARCHIVOS:
        cols, filas = _leer(a)
        for nombre, vals in filas.items():
            c = nombre if nombre in out else next((k for k in canon if k.startswith(nombre)), None)
            if c is None:
                continue
            d = {}
            for col, v in zip(cols, vals):
                d[col if col not in d else col + " (2)"] = v
            out[c][a] = d
    return out


def industria_de(ticker):
    from data.damodaran_mapa import MAPA
    return MAPA.get(str(ticker).upper())


def valores(ticker):
    """Dict de planillas de la industria de Damodaran de esa empresa (o None)."""
    ind = industria_de(ticker)
    return ({"industria": ind, **cargar()[ind]} if ind and ind in cargar() else None)


@lru_cache(maxsize=1)
def primas_pais():
    """Primas de riesgo por país (Damodaran, actualización de julio 2026): {'fuente','erp_maduro','erp_eeuu','paises':{país: {region, rating_moodys, spread_default, erp_total, crp}}}. Para el DCF; no se muestra todavía."""
    import json
    with open(os.path.join(_DIR, "erp_paises.json"), encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def historico():
    """PER y EV/EBITDA de todas las industrias a fin de 2015 y de 2020 (planillas de archivo de Damodaran): {'años': {'2015': {'fecha_actualizacion', 'pedata': {industria: {...}}, 'vebitda': {...}}}}.
    Para comparar el múltiplo actual de una industria con el de hace 5 y 10 años. No se muestra todavía."""
    import json
    with open(os.path.join(_DIR, "historico.json"), encoding="utf-8") as f:
        return json.load(f)
