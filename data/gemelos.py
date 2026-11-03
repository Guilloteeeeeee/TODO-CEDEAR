"""Tickers gemelos (v1.5.15): empresas brasileñas que tienen DOS CEDEARs en BYMA, uno por el ADR que cotiza en EE.UU. y otro por la acción local que cotiza en B3 (San Pablo).
La app tiene UNA sola ficha por empresa (la del ADR, con el mismo informe y el mismo score); el ticker local se muestra en la ficha (debajo de «Nasdaq: AAPL», en otra línea)
y en el buscador (al escribirlo se abre la ficha de la empresa). Pares tomados de la lista oficial de BYMA (data/byma_cedears.json, PDF del 16/09/2026)."""

# ticker del ADR (el que tiene la ficha) -> (ticker local, mercado donde cotiza)
GEMELOS = {
    "ABEV": ("ABEV3", "B3"), "BBD": ("BBDC3", "B3"), "ITUB": ("ITUB3", "B3"), "PBR": ("PETR3", "B3"), "SID": ("CSNA3", "B3"),
    "SUZ": ("SUZB3", "B3"), "TIMB": ("TIMS3", "B3"), "VALE": ("VALE3", "B3"), "VIV": ("VIVT3", "B3"),
}


def gemelo(ticker):
    """(ticker local, mercado) de una empresa con ADR, o None."""
    return GEMELOS.get(str(ticker or "").strip().upper())


def principal(simbolo):
    """Ticker del ADR (el de la ficha) a partir del ticker local, o None."""
    s = str(simbolo or "").strip().upper()
    for adr, (loc, _) in GEMELOS.items():
        if loc == s:
            return adr
    return None
