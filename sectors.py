"""
Configuración de sectores: métricas, pesos fundamentales y mapping de tickers.
Distribución: 85% fundamental (4 métricas ponderadas) + 15% técnico (rango 52 semanas).
"""

# ---------------------------------------------------------------------------
# PESOS POR SECTOR
# Cada sector define sus 4 métricas con peso fundamental.
# La suma de pesos fundamentales debe ser 1.0.
# El rango 52 semanas siempre pesa 0.15 sobre el score total.
#
# Métricas disponibles:
#   ev_ebitda, per, p_fcf, p_b, dividend_yield, p_ffo, p_affo, peg
# ---------------------------------------------------------------------------

SECTOR_CONFIG = {
    "Materiales Básicos": {
        "metrics": {
            "ev_ebitda":       0.35,
            "p_fcf":           0.30,
            "dividend_yield":  0.25,
            "p_b":             0.10,
        },
    },
    "REITs": {
        "metrics": {
            "p_ffo":           0.30,
            "p_affo":          0.30,
            "dividend_yield":  0.30,
            "ev_ebitda":       0.10,
        },
    },
    "Financieros": {
        "metrics": {
            "p_b":             0.40,
            "per":             0.30,
            "dividend_yield":  0.20,
            "p_fcf":           0.10,
        },
    },
    "Consumo Discrecional": {
        "metrics": {
            "p_fcf":           0.30,
            "ev_ebitda":       0.30,
            "per":             0.25,
            "dividend_yield":  0.15,
        },
    },
    "Consumo Básico": {
        "metrics": {
            "dividend_yield":  0.35,
            "ev_ebitda":       0.25,
            "per":             0.25,
            "p_fcf":           0.15,
        },
    },
    "Comunicación": {
        "metrics": {
            "peg":             0.30,
            "ev_ebitda":       0.30,
            "dividend_yield":  0.20,
            "per":             0.20,
        },
    },
    "Industrial": {
        "metrics": {
            "ev_ebitda":       0.30,
            "per":             0.30,
            "p_fcf":           0.25,
            "dividend_yield":  0.15,
        },
    },
    "Tecnología": {
        "metrics": {
            "peg":             0.40,
            "p_fcf":           0.20,
            "ev_ebitda":       0.20,
            "per":             0.20,
        },
    },
    "Energía": {
        "metrics": {
            "p_fcf":           0.35,
            "ev_ebitda":       0.30,
            "dividend_yield":  0.25,
            "p_b":             0.10,
        },
    },
    "Salud": {
        "metrics": {
            "p_fcf":           0.30,
            "ev_ebitda":       0.25,
            "per":             0.25,
            "dividend_yield":  0.20,
        },
    },
    "Utilities": {
        "metrics": {
            "dividend_yield":  0.45,
            "p_fcf":           0.20,
            "ev_ebitda":       0.20,
            "per":             0.15,
        },
    },
}

# Peso del componente técnico (rango 52 semanas) sobre el score total
TECHNICAL_WEIGHT = 0.15
FUNDAMENTAL_WEIGHT = 1.0 - TECHNICAL_WEIGHT  # 0.85

# ---------------------------------------------------------------------------
# UNIVERSO DE TICKERS
# Sector -> lista de tickers.
# El usuario puede agregar/quitar desde la app; este dict es la base inicial.
# ---------------------------------------------------------------------------

TICKER_UNIVERSE = {
    "Materiales Básicos": ["LIN", "BHP", "RIO", "SCCO", "FCX", "SHW", "NEM", "VALE", "AEM", "ECL"],
    "REITs":              ["O", "PLD", "WELL"],
    "Financieros":        [
        "BRK-B", "JPM", "V", "MA", "MUFG", "BAC", "MS", "GS", "HSBC", "C",
        "AXP", "SCHW", "BX", "SPGI", "MMS", "HDB", "SAN", "IBN", "PYPL",
        "USB", "COIN", "BBVA", "ITUB", "AIG", "BK", "FISV", "ING", "NU", "IBKR",
    ],
    "Consumo Discrecional": [
        "AMZN", "TSLA", "HD", "BABA", "TM", "BKNG", "PDD", "MELI",
        "SONY", "RACE", "NKE", "MCD", "SBUX", "TJX", "ABNB", "ORLY", "GM", "ROST",
    ],
    "Comunicación":       ["GOOGL", "META", "NFLX", "TMUS", "VZ", "T", "DIS", "SPOT", "NTES"],
    "Industrial":         [
        "CAT", "GE", "RTX", "SIEGY", "DE", "UNP", "UBER", "LMT",
        "HON", "BA", "MMM", "FDX", "GEV", "HWM", "PCAR",
    ],
    "Tecnología":         [
        "NVDA", "AAPL", "MSFT", "TSM", "AVGO", "MU", "AMD", "ASML", "INTC",
        "PLTR", "CSCO", "ORCL", "AMAT", "PANW", "ARM", "CRWD", "TXN", "ANET",
        "SAP", "MRVL", "IBM", "SHOP", "ADI", "QCOM", "CRM", "NOW", "ACN",
        "ADP", "ADBE", "LRCX", "INFY", "SNOW", "DELL", "KLAC", "MSI", "WDC",
    ],
    "Energía":            ["XOM", "CVX", "SHEL", "TTE", "COP", "PBR", "SLB", "BP", "EQNR", "PSX"],
    "Consumo Básico":     ["WMT", "COST", "KO", "PG", "PM", "PEP", "UL", "TGT", "MDLZ", "MO", "CL", "DEO"],
    "Salud":              [
        "LLY", "JNJ", "ABBV", "MRK", "UNH", "NVS", "TMO", "AMGN",
        "GILD", "ABT", "PFE", "DHR", "ISRG", "VRTX", "NVO", "BMY", "MDT", "GSK", "AZN", "CVS",
    ],
    "Utilities":          ["NEE", "CEG", "VST", "TLN"],
}

# Mapeo inverso: ticker -> sector (se genera automáticamente)
TICKER_TO_SECTOR = {
    ticker: sector
    for sector, tickers in TICKER_UNIVERSE.items()
    for ticker in tickers
}
