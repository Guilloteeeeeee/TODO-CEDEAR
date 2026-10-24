"""
Mercado donde cotiza cada empresa y si lo hace como ADR (v1.2.47).

MERCADO: lo informa Yahoo Finance (bajar_fichas.py lo guarda en data/fichas.json; si falta, la app lo pide en el momento). Aca solo se
traducen los codigos de Yahoo a un nombre corto.

ADR: American Depositary Receipt, el certificado que representa acciones de una empresa extranjera y cotiza en Estados Unidos. Yahoo no lo
informa, asi que la lista de abajo esta armada a mano (empresas extranjeras que cotizan en Estados Unidos con certificados ADR/ADS). Revisada
el 24/10/2026. Casos que NO son ADR aunque sean extranjeras: acciones ordinarias que cotizan directo en Estados Unidos (SHOP, SPOT, NU, AEM, ACN,
MDT, LIN, RACE, MELI) y AZN, que dejo el programa de ADS y cotiza directo en la bolsa de Nueva York desde febrero de 2026. ASML cotiza con
"New York Registry Shares" (acciones de registro de Nueva York, no ADR). Si una empresa cambia de esquema, editar este conjunto.
"""

ADR = frozenset({
    "BHP", "ITUB", "PBR", "VALE", "BABA", "NTES", "NVO", "TTE", "SAP", "SIEGY", "HDB", "IBN", "INFY", "PDD", "SONY", "TM", "ING", "EQNR",
    "BBVA", "SAN", "NVS", "TSM", "ARM", "BP", "DEO", "GSK", "HSBC", "RIO", "SHEL", "UL", "MUFG",
})

_MERCADOS = {
    "NMS": "Nasdaq", "NGM": "Nasdaq", "NCM": "Nasdaq", "NASDAQ": "Nasdaq", "NASDAQGS": "Nasdaq", "NASDAQGM": "Nasdaq", "NASDAQCM": "Nasdaq",
    "NYQ": "NYSE", "NYSE": "NYSE", "NYS": "NYSE",
    "ASE": "NYSE American", "NYSEAMERICAN": "NYSE American", "AMEX": "NYSE American",
    "PCX": "NYSE Arca", "NYSEARCA": "NYSE Arca", "BATS": "Cboe BZX", "BTS": "Cboe BZX",
    "PNK": "OTC", "OQB": "OTC", "OQX": "OTC", "OTC": "OTC", "OTCPK": "OTC", "OTCMARKETSOTCPK": "OTC",
}


def es_adr(ticker):
    return str(ticker or "").upper() in ADR


def mercado_texto(codigo):
    """Nombre corto del mercado a partir del codigo o nombre que da Yahoo ('NMS', 'NYQ', 'NasdaqGS', 'NYSE'...). None si no se reconoce."""
    if not isinstance(codigo, str) or not codigo.strip():
        return None
    k = "".join(ch for ch in codigo.upper() if ch.isalnum())
    return _MERCADOS.get(k)
