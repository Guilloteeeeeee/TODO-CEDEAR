"""v1.5.54: referencias de industria de afuera para el respaldo del score (empresas sin historia propia suficiente).

Decisión de Guille (09/11/2026), para cada múltiplo que necesita respaldo:
- PER, P/FCF, P/B y P/S: mediana de GuruFocus. Primero su industria; si falta o es un disparate, su sector de GuruFocus;
  si tampoco, la referencia de siempre (mediana de los pares de la app, ver scoring.engine.referencias_sector).
- PEG: Finviz (GuruFocus no lo da), con la misma cascada (industria → sector → app).
- EV/EBITDA y el resto: la referencia de la app. El EV/EBITDA de GuruFocus está roto (mete empresas con EBITDA negativo en la mediana).
"Disparate" = fuera de la franja FRANJAS (valores que ninguna industria normal tiene: los da una gigante que pesa más que el resto,
pérdidas o recompras que dejan el patrimonio chiquito).

Las tablas viven en data/referencias/<fuente>_<aaaa-mm-dd>.json (se usa la más nueva de cada fuente; las viejas quedan de archivo).
Se renuevan una vez por año (noviembre): Guille copia la tabla de cada página y se arma el archivo nuevo con la fecha.
Sin archivos, o para una empresa sin industria conocida, todo sigue como antes (referencia de la app).
"""
import glob
import json
import os

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "referencias")
FRANJAS = {"per": (5.0, 50.0), "p_fcf": (5.0, 50.0), "peg": (0.3, 5.0), "p_b": (0.5, 20.0), "ps": (0.1, 20.0)}
DE_GURUFOCUS = ("per", "p_fcf", "p_b", "ps")
DE_FINVIZ = ("peg",)

# Sector de Yahoo -> nombre del sector en cada fuente (los que no figuran se llaman igual)
SECTOR_FINVIZ = {"Financial Services": "Financial"}
SECTOR_GURUFOCUS = {}

# Industria de Yahoo -> grupo de industrias de GuruFocus (55 grupos, clasificación de Morningstar).
# Finviz usa los mismos nombres de industria que Yahoo: no necesita tabla.
INDUSTRIA_GURUFOCUS = {
    "Agricultural Inputs": "Agriculture", "Building Materials": "Building Materials", "Chemicals": "Chemicals", "Specialty Chemicals": "Chemicals",
    "Copper": "Metals & Mining", "Gold": "Metals & Mining", "Silver": "Metals & Mining", "Aluminum": "Metals & Mining",
    "Other Industrial Metals & Mining": "Metals & Mining", "Other Precious Metals & Mining": "Metals & Mining", "Coking Coal": "Steel",
    "Paper & Paper Products": "Forest Products", "Lumber & Wood Production": "Forest Products", "Steel": "Steel",
    "Electronic Gaming & Multimedia": "Interactive Media", "Internet Content & Information": "Interactive Media",
    "Entertainment": "Media - Diversified", "Broadcasting": "Media - Diversified", "Publishing": "Media - Diversified",
    "Advertising Agencies": "Media - Diversified", "Telecom Services": "Telecommunication Services",
    "Apparel Retail": "Retail - Cyclical", "Home Improvement Retail": "Retail - Cyclical", "Internet Retail": "Retail - Cyclical",
    "Specialty Retail": "Retail - Cyclical", "Department Stores": "Retail - Cyclical", "Luxury Goods": "Retail - Cyclical",
    "Auto & Truck Dealerships": "Vehicles & Parts", "Auto Manufacturers": "Vehicles & Parts", "Auto Parts": "Vehicles & Parts",
    "Recreational Vehicles": "Vehicles & Parts", "Footwear & Accessories": "Manufacturing - Apparel & Accessories",
    "Apparel Manufacturing": "Manufacturing - Apparel & Accessories", "Textile Manufacturing": "Manufacturing - Apparel & Accessories",
    "Packaging & Containers": "Packaging & Containers", "Resorts & Casinos": "Travel & Leisure", "Travel Services": "Travel & Leisure",
    "Lodging": "Travel & Leisure", "Gambling": "Travel & Leisure", "Leisure": "Travel & Leisure", "Restaurants": "Restaurants",
    "Residential Construction": "Homebuilding & Construction", "Furnishings, Fixtures & Appliances": "Furnishings, Fixtures & Appliances",
    "Personal Services": "Personal Services",
    "Beverages - Brewers": "Beverages - Alcoholic", "Beverages - Wineries & Distilleries": "Beverages - Alcoholic",
    "Beverages - Non-Alcoholic": "Beverages - Non-Alcoholic", "Confectioners": "Consumer Packaged Goods", "Farm Products": "Consumer Packaged Goods",
    "Household & Personal Products": "Consumer Packaged Goods", "Packaged Foods": "Consumer Packaged Goods",
    "Discount Stores": "Retail - Defensive", "Food Distribution": "Retail - Defensive", "Grocery Stores": "Retail - Defensive",
    "Tobacco": "Tobacco Products", "Education & Training Services": "Education",
    "Oil & Gas E&P": "Oil & Gas", "Oil & Gas Equipment & Services": "Oil & Gas", "Oil & Gas Integrated": "Oil & Gas", "Oil & Gas Midstream": "Oil & Gas",
    "Oil & Gas Refining & Marketing": "Oil & Gas", "Oil & Gas Drilling": "Oil & Gas", "Thermal Coal": "Oil & Gas", "Uranium": "Other Energy Sources",
    "Asset Management": "Asset Management", "Banks - Diversified": "Banks", "Banks - Regional": "Banks", "Capital Markets": "Capital Markets",
    "Financial Data & Stock Exchanges": "Capital Markets", "Credit Services": "Credit Services", "Mortgage Finance": "Credit Services",
    "Insurance - Diversified": "Insurance", "Insurance - Property & Casualty": "Insurance", "Insurance - Life": "Insurance",
    "Insurance - Specialty": "Insurance", "Insurance - Reinsurance": "Insurance", "Insurance Brokers": "Insurance",
    "Financial Conglomerates": "Diversified Financial Services",
    "Biotechnology": "Biotechnology", "Diagnostics & Research": "Medical Diagnostics & Research",
    "Drug Manufacturers - General": "Drug Manufacturers", "Drug Manufacturers - Specialty & Generic": "Drug Manufacturers",
    "Health Information Services": "Healthcare Providers & Services", "Medical Care Facilities": "Healthcare Providers & Services",
    "Pharmaceutical Retailers": "Healthcare Providers & Services", "Healthcare Plans": "Healthcare Plans",
    "Medical Devices": "Medical Devices & Instruments", "Medical Instruments & Supplies": "Medical Devices & Instruments",
    "Medical Distribution": "Medical Distribution",
    "Aerospace & Defense": "Aerospace & Defense", "Airlines": "Transportation", "Airports & Air Services": "Transportation",
    "Integrated Freight & Logistics": "Transportation", "Railroads": "Transportation", "Trucking": "Transportation", "Marine Shipping": "Transportation",
    "Building Products & Equipment": "Construction", "Engineering & Construction": "Construction", "Infrastructure Operations": "Construction",
    "Business Equipment & Supplies": "Industrial Distribution", "Industrial Distribution": "Industrial Distribution",
    "Conglomerates": "Conglomerates", "Consulting Services": "Business Services", "Rental & Leasing Services": "Business Services",
    "Staffing & Employment Services": "Business Services", "Security & Protection Services": "Business Services",
    "Specialty Business Services": "Business Services", "Farm & Heavy Construction Machinery": "Farm & Heavy Construction Machinery",
    "Specialty Industrial Machinery": "Industrial Products", "Tools & Accessories": "Industrial Products",
    "Electrical Equipment & Parts": "Industrial Products", "Metal Fabrication": "Industrial Products", "Pollution & Treatment Controls": "Industrial Products",
    "Waste Management": "Waste Management",
    "REIT - Healthcare Facilities": "REITs", "REIT - Industrial": "REITs", "REIT - Retail": "REITs", "REIT - Residential": "REITs",
    "REIT - Office": "REITs", "REIT - Specialty": "REITs", "REIT - Diversified": "REITs", "REIT - Hotel & Motel": "REITs", "REIT - Mortgage": "REITs",
    "Real Estate Services": "Real Estate", "Real Estate - Development": "Real Estate", "Real Estate - Diversified": "Real Estate",
    "Communication Equipment": "Hardware", "Computer Hardware": "Hardware", "Consumer Electronics": "Hardware", "Electronic Components": "Hardware",
    "Scientific & Technical Instruments": "Hardware", "Electronics & Computer Distribution": "Hardware",
    "Information Technology Services": "Software", "Software - Application": "Software", "Software - Infrastructure": "Software",
    "Semiconductor Equipment & Materials": "Semiconductors", "Semiconductors": "Semiconductors", "Solar": "Semiconductors",
    "Utilities - Independent Power Producers": "Utilities - Independent Power Producers", "Utilities - Renewable": "Utilities - Independent Power Producers",
    "Utilities - Regulated Electric": "Utilities - Regulated", "Utilities - Regulated Gas": "Utilities - Regulated",
    "Utilities - Regulated Water": "Utilities - Regulated", "Utilities - Diversified": "Utilities - Regulated",
}

_MEMO = {}


def _mas_nuevo(fuente, carpeta=None):
    rutas = sorted(glob.glob(os.path.join(carpeta or CARPETA, f"{fuente}_*.json")))
    if not rutas:
        return {}
    try:
        with open(rutas[-1], encoding="utf-8") as f:
            j = json.load(f)
        return j if isinstance(j, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def tablas(carpeta=None):
    """{"gurufocus": {...}, "finviz": {...}} con la tabla más nueva de cada fuente ({} si falta)."""
    k = carpeta or CARPETA
    if k not in _MEMO:
        _MEMO[k] = {"gurufocus": _mas_nuevo("gurufocus", carpeta), "finviz": _mas_nuevo("finviz", carpeta)}
    return _MEMO[k]


def _clasificacion():
    if "fichas" not in _MEMO:
        try:
            from data import fichas as _f
            d, _ = _f.cargar()
        except Exception:  # noqa: BLE001
            d = {}
        _MEMO["fichas"] = {t: (v.get("sector_yahoo"), v.get("industria_yahoo")) for t, v in d.items()}
    return _MEMO["fichas"]


def en_franja(metrica, valor):
    lo, hi = FRANJAS[metrica]
    try:
        return valor is not None and valor == valor and lo <= float(valor) <= hi
    except (TypeError, ValueError):
        return False


def referencias(ticker, refs_app, clasificacion=None, carpeta=None):
    """({metrica: valor}, {metrica: origen}) para el respaldo de una empresa. Parte de `refs_app` (la referencia de siempre de su
    sector en la app) y reemplaza PER, P/FCF, P/B, P/S (GuruFocus) y PEG (Finviz) cuando hay un valor dentro de la franja.
    origen: "industria GuruFocus", "sector GuruFocus", "industria Finviz", "sector Finviz" o "app"."""
    refs = {m: v for m, v in (refs_app or {}).items() if v is not None}
    origen = {m: "app" for m in refs}
    sec, ind = (clasificacion if clasificacion is not None else _clasificacion()).get(str(ticker).upper(), (None, None))
    if not sec and not ind:
        return refs, origen
    t = tablas(carpeta)
    g, f = t.get("gurufocus") or {}, t.get("finviz") or {}
    cascadas = {}
    for m in DE_GURUFOCUS:
        cascadas[m] = [((g.get("industrias") or {}).get(INDUSTRIA_GURUFOCUS.get(ind)), "industria GuruFocus"),
                       ((g.get("sectores") or {}).get(SECTOR_GURUFOCUS.get(sec, sec)), "sector GuruFocus")]
    for m in DE_FINVIZ:
        cascadas[m] = [((f.get("industrias") or {}).get(ind), "industria Finviz"),
                       ((f.get("sectores") or {}).get(SECTOR_FINVIZ.get(sec, sec)), "sector Finviz")]
    for m, pasos in cascadas.items():
        for d, nombre in pasos:
            v = d.get(m) if isinstance(d, dict) else None
            if en_franja(m, v):
                refs[m], origen[m] = float(v), nombre
                break
    return refs, origen


def olvidar():
    _MEMO.clear()
