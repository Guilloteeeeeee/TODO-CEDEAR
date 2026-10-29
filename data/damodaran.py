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


@lru_cache(maxsize=1)
def _regiones():
    import json
    with open(os.path.join(_DIR, "regiones.json"), encoding="utf-8") as f:
        return json.load(f)["regiones"]


def region_de(ticker):
    """'us' | 'emergentes' | 'europa' | 'aus_nz_canada' | 'japon' (Japón se compara con EE.UU.)."""
    from data.damodaran_mapa import REGION
    return REGION.get(str(ticker).upper(), "us")


def valores(ticker):
    """Dict de planillas de la industria de Damodaran de esa empresa, en la región que le toca (o None). Si la región no tiene una planilla, esa clave no está (no se completa con EE.UU.).
    Incluye 'industria', 'region' y 'region_txt'. Los porcentajes están en puntos (12,3 = 12,3 %)."""
    from data.damodaran_mapa import REGION_TXT
    ind = industria_de(ticker)
    if not ind or ind not in cargar():
        return None
    rg = region_de(ticker)
    out = {"industria": ind, "region": rg, "region_txt": REGION_TXT[rg]}
    if rg in ("us", "japon"):
        out.update(cargar()[ind])
    else:
        for ds, filas in _regiones().get(rg, {}).items():
            if ind in filas:
                out[ds] = filas[ind]
    return out


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


@lru_cache(maxsize=1)
def _rating_tabla():
    import json
    with open(os.path.join(_DIR, "rating_sintetico.json"), encoding="utf-8") as f:
        return json.load(f)


def rating_sintetico(cobertura, tipo="grande"):
    """Rating y spread de default estimados a partir de la cobertura de intereses (resultado operativo / intereses), con la planilla de Damodaran.
    tipo: 'grande' (no financiera grande), 'chica' (más chica o riesgosa) o 'financiera'. -> (rating, spread) o (None, None). Para el DCF; no se muestra todavía."""
    if cobertura is None:
        return None, None
    t = _rating_tabla()[{"grande": "grandes_no_financieras", "chica": "chicas_o_riesgosas", "financiera": "financieras"}[tipo]]
    for desde, hasta, rating, spread in t:
        if desde < float(cobertura) <= hasta or (float(cobertura) == desde == t[0][0]):
            return rating, spread
    return None, None


@lru_cache(maxsize=1)
def tasas_paises():
    """Tasa marginal de impuesto a las ganancias por país: {'fuente', 'paises': {país: {'tasa', 'tasa_minimo_global'}}}. Para el DCF; no se muestra todavía."""
    import json
    with open(os.path.join(_DIR, "tasas_paises.json"), encoding="utf-8") as f:
        return json.load(f)
