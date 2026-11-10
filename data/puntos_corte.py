"""v1.5.56: puntos de corte por industria (vara «OK») para los gráficos de Estados Financieros.

Los armó Guille en otra charla (09/11/2026): Excel y método en data/referencias/puntos_corte_<fecha>.xlsx / _metodo_<fecha>.txt;
los valores, en data/referencias/puntos_corte_<fecha>.json (se usa el más nuevo). Un corte por variable: si la empresa lo cumple, PASA.
Cómo se elige la fila: la industria de Damodaran de la empresa (data/damodaran_mapa.py) si está entre las 72 de Guille; si no, su
subgrupo o su sector (hoja Damodaran del Excel). "n/a" en el Excel = esa variable no se evalúa en ese tipo de empresa (None acá).
"""
import glob
import json
import os

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "referencias")

# Cómo se nombra cada grupo en la frase «… es nuestra preferencia para …»
NOMBRES = {
    "Aerospace/Defense": "las empresas aeroespaciales y de defensa", "Air Transport": "las aerolíneas", "Auto & Truck": "las automotrices",
    "Bank (Money Center)": "los grandes bancos", "Banks (Regional)": "los bancos regionales", "Beverage (Alcoholic)": "las bebidas alcohólicas",
    "Beverage (Soft)": "las bebidas sin alcohol", "Broadcasting": "los medios de radio y televisión",
    "Brokerage & Investment Banking": "los brokers y bancos de inversión", "Building Materials": "los materiales de construcción",
    "Chemical (Basic)": "la química básica", "Chemical (Specialty)": "la química especializada", "Computer Services": "los servicios informáticos",
    "Computers/Peripherals": "los fabricantes de computadoras y equipos", "Diversified": "los conglomerados",
    "Drugs (Biotechnology)": "las biotecnológicas", "Drugs (Pharmaceutical)": "los laboratorios farmacéuticos",
    "Electrical Equipment": "los fabricantes de equipos eléctricos", "Electronics (Consumer & Office)": "la electrónica de consumo",
    "Electronics (General)": "los fabricantes de componentes electrónicos", "Entertainment": "las empresas de entretenimiento",
    "Farming/Agriculture": "las empresas agrícolas", "Financial Svcs. (Non-bank & Insurance)": "los servicios financieros no bancarios",
    "Food Processing": "las alimenticias", "Food Wholesalers": "los mayoristas de alimentos", "Green & Renewable Energy": "las energías renovables",
    "Healthcare Information and Technology": "la tecnología para la salud", "Healthcare Products": "los productos médicos",
    "Healthcare Support Services": "los servicios de salud", "Hotel/Gaming": "la hotelería, el turismo y el juego",
    "Household Products": "los productos para el hogar", "Information Services": "los servicios de información financiera",
    "Insurance (General)": "las aseguradoras", "Insurance (Life)": "las aseguradoras de vida", "Insurance (Prop/Cas.)": "las aseguradoras patrimoniales",
    "Investments & Asset Management": "las administradoras de inversiones", "Machinery": "los fabricantes de maquinaria",
    "Metals & Mining": "la minería", "Office Equipment & Services": "los equipos y servicios de oficina",
    "Oil/Gas (Integrated)": "las petroleras integradas", "Oil/Gas (Production and Exploration)": "las petroleras de exploración y producción",
    "Oil/Gas Distribution": "el transporte y la distribución de petróleo y gas", "Oilfield Svcs/Equip.": "los servicios petroleros",
    "Packaging & Container": "los envases", "Paper/Forest Products": "el papel y los productos forestales", "Power": "las eléctricas",
    "Precious Metals": "la minería de metales preciosos", "R.E.I.T.": "los REITs", "Recreation": "las empresas de recreación",
    "Restaurant/Dining": "los restaurantes", "Retail (Automotive)": "las tiendas de repuestos para autos",
    "Retail (Building Supply)": "las tiendas de construcción y mejoras del hogar", "Retail (General)": "las cadenas de comercio minorista",
    "Retail (Grocery and Food)": "los supermercados", "Retail (REITs)": "los REITs comerciales", "Retail (Special Lines)": "las tiendas especializadas",
    "Rubber & Tires": "los fabricantes de neumáticos", "Semiconductor": "los fabricantes de semiconductores",
    "Semiconductor Equip": "los fabricantes de equipos para semiconductores", "Shoe": "el calzado y la indumentaria deportiva",
    "Software (Entertainment)": "los videojuegos", "Software (Internet)": "las empresas de internet",
    "Software (System & Application)": "las empresas de software", "Steel": "las siderúrgicas", "Telecom (Wireless)": "las telefónicas móviles",
    "Telecom. Equipment": "los equipos de telecomunicaciones", "Telecom. Services": "las telefónicas", "Tobacco": "las tabacaleras",
    "Transportation": "el transporte", "Transportation (Railroads)": "los ferrocarriles", "Utility (General)": "las empresas de servicios públicos",
    "Utility (Water)": "las empresas de agua",
}
NOMBRES_GRUPO = {
    "Tecnología": "las tecnológicas", "Semiconductores": "los fabricantes de semiconductores", "Software y nube": "las empresas de software y nube",
    "Hardware y servicios TI": "el hardware y los servicios informáticos", "Financiero": "las financieras", "Bancos y seguros": "los bancos y aseguradoras",
    "Pagos y datos": "las empresas de pagos y datos", "Comunicación": "las empresas de comunicación", "Internet y medios": "internet y los medios",
    "Telecomunicaciones": "las telefónicas", "Consumo Discrecional": "el consumo discrecional", "Consumo Básico": "el consumo básico",
    "Materiales Básicos": "los materiales básicos", "Industrial": "las industriales", "Salud": "las empresas de salud", "Energía": "las energéticas",
    "Utilities": "las empresas de servicios públicos", "REITs": "los REITs", "Mercado (no financieras)": "las empresas en general",
}

_MEMO = {}


def tabla(carpeta=None):
    k = carpeta or CARPETA
    if k not in _MEMO:
        rutas = sorted(glob.glob(os.path.join(k, "puntos_corte_*.json")))
        try:
            with open(rutas[-1], encoding="utf-8") as f:
                _MEMO[k] = json.load(f)
        except Exception:  # noqa: BLE001
            _MEMO[k] = {}
    return _MEMO[k]


def _industria(ticker):
    try:
        from data import damodaran as _D
        return _D.industria_de(ticker)
    except Exception:  # noqa: BLE001
        return None


def cortes(ticker, industria=None, carpeta=None):
    """{"grupo": nombre para la frase, "fila": de dónde salió, "cortes": {variable: valor o None}, "sentido": {variable: "min"/"max"}} o None."""
    t = tabla(carpeta)
    if not t:
        return None
    ind = industria or _industria(ticker)
    if not ind:
        return None
    fila = (t.get("industrias") or {}).get(ind)
    if fila:
        return {"grupo": NOMBRES.get(ind, ind), "fila": ind, "cortes": fila["cortes"], "sentido": t["sentido"]}
    d = (t.get("damodaran_a_sector") or {}).get(ind)
    if not d:
        return None
    filas = t.get("sectores") or []
    f = next((x for x in filas if d.get("subgrupo") and x.get("subgrupo") == d["subgrupo"]), None) or \
        next((x for x in filas if x.get("sector") == d.get("sector") and not x.get("subgrupo")), None)
    if not f:
        return None
    nombre = f.get("subgrupo") or f.get("sector")
    return {"grupo": NOMBRES_GRUPO.get(nombre, nombre), "fila": nombre, "cortes": f["cortes"], "sentido": t["sentido"]}


def olvidar():
    _MEMO.clear()
