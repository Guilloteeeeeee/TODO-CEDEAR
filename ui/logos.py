"""
Logos de las empresas (v1.2.16).

Por que cambio: la app usaba logo.clearbit.com, un servicio que dejo de funcionar, y el truco de
mostrar iniciales cuando falla la imagen (atributo onerror) no corre dentro de st.markdown, asi que
quedaban cuadros vacios.

Ahora, para cada ticker, en este orden:
  1. Archivo local assets/logos/<TICKER>.png (o .webp/.jpg/.svg): se incrusta en la pagina, no depende
     de ningun servicio. Se generan con descargar_logos.bat (una vez, en la PC).
  2. Si no hay archivo y LOGOS_EN_LINEA == "google": favicon del dominio de la empresa servido por
     Google (lo carga el navegador de quien mira la app).
  3. Si no hay nada: circulo con las iniciales (siempre se ve algo).
"""
import base64
import functools
import hashlib
from pathlib import Path

try:
    from config.ajustes import LOGOS_EN_LINEA
except Exception:  # noqa: BLE001
    LOGOS_EN_LINEA = "google"

CARPETA_LOGOS = Path(__file__).resolve().parent.parent / "assets" / "logos"
EXTENSIONES = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg",
               ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}

# Dominio de cada empresa (para el favicon y para el script de descarga)
DOMINIOS = {
    "AEM": "agnicoeagle.com", "ECL": "ecolab.com", "MRSH": "marshmclennan.com",
    "AAPL": "apple.com", "MSFT": "microsoft.com", "GOOGL": "google.com",
    "AMZN": "amazon.com", "NVDA": "nvidia.com", "META": "meta.com",
    "TSLA": "tesla.com", "JPM": "jpmorganchase.com", "V": "visa.com",
    "MA": "mastercard.com", "AVGO": "broadcom.com", "UNH": "unitedhealthgroup.com",
    "JNJ": "jnj.com", "XOM": "exxonmobil.com", "WMT": "walmart.com",
    "LLY": "lilly.com", "HD": "homedepot.com", "PG": "pg.com",
    "COST": "costco.com", "MRK": "merck.com", "ABBV": "abbvie.com",
    "CVX": "chevron.com", "KO": "coca-cola.com", "PEP": "pepsico.com",
    "BAC": "bankofamerica.com", "NFLX": "netflix.com", "CRM": "salesforce.com",
    "ORCL": "oracle.com", "ACN": "accenture.com", "MCD": "mcdonalds.com",
    "CSCO": "cisco.com", "IBM": "ibm.com", "ADBE": "adobe.com",
    "NOW": "servicenow.com", "QCOM": "qualcomm.com", "TXN": "ti.com",
    "INTC": "intel.com", "AMD": "amd.com", "GE": "ge.com",
    "CAT": "caterpillar.com", "DE": "deere.com", "BA": "boeing.com",
    "LMT": "lockheedmartin.com", "RTX": "rtx.com", "HON": "honeywell.com",
    "UNP": "up.com", "NEE": "nexteraenergy.com", "DIS": "disney.com",
    "SBUX": "starbucks.com", "NKE": "nike.com", "SPOT": "spotify.com",
    "SHOP": "shopify.com", "SLB": "slb.com", "PFE": "pfizer.com",
    "TMO": "thermofisher.com", "ABT": "abbott.com", "GS": "goldmansachs.com",
    "MS": "morganstanley.com", "AXP": "americanexpress.com", "BRK-B": "berkshirehathaway.com",
    "BKNG": "booking.com", "UBER": "uber.com", "ABNB": "airbnb.com",
    "PYPL": "paypal.com", "COIN": "coinbase.com", "MELI": "mercadolibre.com",
    "PLTR": "palantir.com", "PANW": "paloaltonetworks.com", "CRWD": "crowdstrike.com",
    "ANET": "arista.com", "SNOW": "snowflake.com", "MU": "micron.com",
    "ASML": "asml.com", "TSM": "tsmc.com", "SAP": "sap.com",
    "NVO": "novonordisk.com", "NVS": "novartis.com", "AZN": "astrazeneca.com",
    "GILD": "gilead.com", "AMGN": "amgen.com", "VRTX": "vrtx.com",
    "ISRG": "intuitivesurgical.com", "DHR": "danaher.com", "MDT": "medtronic.com",
    "BHP": "bhp.com", "RIO": "riotinto.com", "VALE": "vale.com",
    "FCX": "fcx.com", "NEM": "newmont.com", "LIN": "linde.com",
    "SHW": "sherwin-williams.com", "SCCO": "southerncopper.com",
    "XOM": "exxonmobil.com", "CVX": "chevron.com", "SHEL": "shell.com",
    "TTE": "totalenergies.com", "COP": "conocophillips.com", "BP": "bp.com",
    "PBR": "petrobras.com.br", "EQNR": "equinor.com",
    "O": "realtyincome.com", "PLD": "prologis.com", "WELL": "welltower.com",
    "VZ": "verizon.com", "T": "att.com", "TMUS": "t-mobile.com",
    "PM": "pmi.com", "MO": "altria.com", "UL": "unilever.com",
    "DEO": "diageo.com", "CL": "colgate.com", "MDLZ": "mondelezinternational.com",
    "TGT": "target.com", "TM": "toyota.com", "SONY": "sony.com",
    "BABA": "alibaba.com", "PDD": "pinduoduo.com", "HSBC": "hsbc.com",
    "SAN": "santander.com", "BBVA": "bbva.com", "ITUB": "itau.com.br",
    "IBN": "icicibank.com", "HDB": "hdfcbank.com", "MUFG": "mufg.jp",
    "ING": "ing.com", "NU": "nu.com.br", "IBKR": "interactivebrokers.com",
    "BX": "blackstone.com", "SPGI": "spglobal.com", "SCHW": "schwab.com",
    "USB": "usbank.com", "BNY": "bny.com", "FISV": "fiserv.com",
    "C": "citigroup.com", "AIG": "aig.com", "TJX": "tjx.com",
    "ROST": "rossstores.com", "GM": "gm.com", "RACE": "ferrari.com",
    "ORLY": "oreillyauto.com", "FDX": "fedex.com", "MMM": "3m.com",
    "PSX": "phillips66.com", "GEV": "gevernova.com", "HWM": "howmet.com",
    "PCAR": "paccar.com", "SIEGY": "siemens.com", "ARM": "arm.com",
    "AMAT": "appliedmaterials.com", "LRCX": "lamresearch.com",
    "KLAC": "kla.com", "ADI": "analog.com", "MRVL": "marvell.com",
    "INFY": "infosys.com", "DELL": "dell.com", "WDC": "westerndigital.com",
    "MSI": "motorolasolutions.com", "ADP": "adp.com", "CEG": "constellationenergy.com",
    "VST": "vistratenergy.com", "TLN": "talenenergy.com", "CVS": "cvshealth.com",
    "BMY": "bms.com", "GSK": "gsk.com", "NTES": "netease.com",
}


_COLORES_INICIALES = ["#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3", "#ede9fe", "#e0f2fe", "#ffedd5", "#f1f5f9"]


def _archivo_local(ticker: str):
    for ext in EXTENSIONES:
        p = CARPETA_LOGOS / f"{ticker}{ext}"
        if p.is_file():
            return p
    return None


@functools.lru_cache(maxsize=512)
def _data_uri(ticker: str):
    p = _archivo_local(ticker)
    if p is None:
        return None
    try:
        return f"data:{EXTENSIONES[p.suffix.lower()]};base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    except OSError:
        return None


def url_favicon(ticker: str, tam: int = 64):
    dom = DOMINIOS.get(ticker)
    if not dom or LOGOS_EN_LINEA != "google":
        return None
    return f"https://www.google.com/s2/favicons?domain={dom}&sz={tam}"


def logo_url(ticker: str):
    """Fuente de la imagen (data URI local o favicon), o None si solo hay iniciales."""
    return _data_uri(ticker) or url_favicon(ticker)


def logo_html(ticker: str, tam: int = 28) -> str:
    """HTML del logo (sin JavaScript): imagen si hay, si no un circulo con iniciales."""
    src = logo_url(ticker)
    if src:
        return (f'<img class="tv-logo" src="{src}" width="{tam}" height="{tam}" alt="" loading="lazy" '
                f'style="width:{tam}px;height:{tam}px;border-radius:6px;object-fit:contain;flex-shrink:0;background:#fff">')
    ini = "".join(ch for ch in str(ticker) if ch.isalnum())[:2].upper() or "?"
    color = _COLORES_INICIALES[int(hashlib.md5(str(ticker).encode()).hexdigest(), 16) % len(_COLORES_INICIALES)]
    return (f'<span class="tv-ini" style="display:inline-block;flex-shrink:0;text-align:center;border-radius:50%;'
            f'font-weight:700;color:#475569;width:{tam}px;height:{tam}px;background:{color};'
            f'line-height:{tam}px;font-size:{max(tam // 2 - 1, 9)}px">{ini}</span>')
