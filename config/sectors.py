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
    # v1.2.17: "Financieros" se separo en dos (el P/B pesa mucho para bancos y aseguradoras, pero casi no
    # dice nada de empresas de pagos y datos, que casi no tienen activos y recompran acciones):
    "Bancos y seguros": {          # bancos, aseguradoras, brokers y administradoras de activos
        "metrics": {
            "p_b":             0.40,
            "per":             0.35,
            "dividend_yield":  0.25,
        },
    },
    "Pagos y datos": {             # redes de pago, datos financieros, cripto, corredores de seguros
        "metrics": {
            "per":             0.35,
            "p_fcf":           0.35,
            "ev_ebitda":       0.20,
            "dividend_yield":  0.10,
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
    # v1.2.18: telecomunicaciones aparte de Comunicación. Son negocios lentos, con mucha deuda y que
    # pagan dividendo: el PEG (crecimiento) no las describe; se miden por dividendo, EV/EBITDA y flujo.
    "Telecomunicaciones": {
        "metrics": {
            "dividend_yield":  0.30,
            "ev_ebitda":       0.30,
            "p_fcf":           0.25,
            "per":             0.15,
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
    # v1.2.19: Tecnología en tres grupos de negocios parecidos. Los pesos son los mismos de antes
    # (PEG 40 / P-FCF 20 / EV-EBITDA 20 / PER 20): lo que cambia es contra quien se compara el
    # sector cuando falta la historia propia (sobre todo el PEG).
    "Semiconductores": {
        "metrics": {
            "peg":             0.40,
            "p_fcf":           0.20,
            "ev_ebitda":       0.20,
            "per":             0.20,
        },
    },
    "Software y nube": {
        "metrics": {
            "peg":             0.40,
            "p_fcf":           0.20,
            "ev_ebitda":       0.20,
            "per":             0.20,
        },
    },
    "Hardware y servicios TI": {
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
    "Bancos y seguros":   [
        "BRK-B", "JPM", "MUFG", "BAC", "MS", "GS", "HSBC", "C", "AXP", "SCHW", "BX", "HDB", "SAN",
        "IBN", "USB", "BBVA", "ITUB", "AIG", "BNY", "ING", "NU", "IBKR",
    ],
    "Pagos y datos":      ["V", "MA", "SPGI", "PYPL", "COIN", "FISV", "MRSH"],   # MRSH = Marsh McLennan (antes MMC)
    "Consumo Discrecional": [
        "AMZN", "TSLA", "HD", "BABA", "TM", "BKNG", "PDD", "MELI",
        "SONY", "RACE", "NKE", "MCD", "SBUX", "TJX", "ABNB", "ORLY", "GM", "ROST",
    ],
    "Comunicación":       ["GOOGL", "META", "NFLX", "DIS", "SPOT", "NTES"],   # internet y medios
    "Telecomunicaciones": ["T", "VZ", "TMUS"],
    "Industrial":         [
        "CAT", "GE", "RTX", "SIEGY", "DE", "UNP", "UBER", "LMT",
        "HON", "BA", "MMM", "FDX", "GEV", "HWM", "PCAR",
    ],
    "Semiconductores":    [
        "NVDA", "TSM", "AVGO", "MU", "AMD", "ASML", "INTC", "AMAT", "ARM", "TXN",
        "MRVL", "ADI", "QCOM", "LRCX", "KLAC",
    ],
    "Software y nube":    [
        "MSFT", "ORCL", "PLTR", "PANW", "CRWD", "SAP", "SHOP", "CRM", "NOW", "ADBE", "SNOW",
    ],
    "Hardware y servicios TI": [
        "AAPL", "CSCO", "ANET", "IBM", "ACN", "ADP", "INFY", "DELL", "MSI", "WDC",
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
# Pais de respaldo: solo se usa cuando Yahoo Finance no informa el pais de la empresa (ej.: FISV, que
# cambio de ticker, o MRSH). Los nombres van como los entrega Yahoo (en ingles).
PAIS_MANUAL = {
    "FISV": "United States",   # Fiserv (Milwaukee, EEUU)
    "MRSH": "United States",   # Marsh McLennan (Nueva York, EEUU)
}


TICKER_TO_SECTOR = {
    ticker: sector
    for sector, tickers in TICKER_UNIVERSE.items()
    for ticker in tickers
}


# ---------------------------------------------------------------------------
# SECTOR / INDUSTRIA (v1.2.20) - solo para mostrar en pantalla
# Los grupos de arriba (SECTOR_CONFIG / TICKER_UNIVERSE) son los que se usan para puntuar. Algunos son
# una industria dentro de un sector mas grande; en las tablas se muestran como "Sector / Industria".
# Los grupos que no figuran aca (Salud, Industrial, Energia, etc.) se muestran solo con su nombre.
# ---------------------------------------------------------------------------
SECTOR_E_INDUSTRIA = {
    "Bancos y seguros":        ("Financiero", "Bancos y seguros"),
    "Pagos y datos":           ("Financiero", "Pagos y datos"),
    "Semiconductores":         ("Tecnología", "Semiconductores"),
    "Software y nube":         ("Tecnología", "Software y nube"),
    "Hardware y servicios TI": ("Tecnología", "Hardware y servicios TI"),
    "Comunicación":            ("Comunicación", "Internet y medios"),
    "Telecomunicaciones":      ("Comunicación", "Telecomunicaciones"),
}


def etiqueta_sector(grupo) -> str:
    """Texto para mostrar: 'Financiero / Pagos y datos', o solo 'Salud' si el grupo no tiene industria."""
    if not isinstance(grupo, str) or not grupo:
        return "—"
    sector, industria = SECTOR_E_INDUSTRIA.get(grupo, (grupo, None))
    return f"{sector} / {industria}" if industria else sector


# ---------------------------------------------------------------------------
# REGLAS DE DATOS (v1.2.11)
# ---------------------------------------------------------------------------
# Rango en el que un multiplo (actual o mediana historica) es creible. Fuera de este rango
# el dato casi seguro esta roto (moneda mezclada, ADR, ganancia casi cero) y la metrica
# se DESCARTA: el score y el Fair Value se calculan con las metricas que si funcionan,
# repartiendo su peso. Solo se cortan los valores IMPOSIBLES (ej.: PER 0,13 o EV/EBITDA 0,01);
# los multiplos muy altos pero posibles (PER 350, P/FCF 800) se mantienen: son empresas caras de verdad.
# El PEG no tiene limites (sus valores extremos son reales).
RANGOS_PLAUSIBLES = {
    "ev_ebitda":      (1.0, 500.0),
    "per":            (3.0, 2000.0),
    "p_fcf":          (3.0, 2000.0),
    "p_b":            (0.3, 200.0),
    "dividend_yield": (0.0005, 0.5),
    "p_ffo":          (3.0, 2000.0),
    "p_affo":         (3.0, 2000.0),
}

# Un metodo de Fair Value que dice que la empresa vale mas de 3 veces (o menos de 1/3) su precio
# no se promedia: es mas probable un dato roto que una oportunidad. No se toca el score.
FV_RATIO_MIN = 1.0 / 3.0
FV_RATIO_MAX = 3.0

# Cantidad minima de empresas de un sector con dato propio valido para usar la mediana del sector
# como respaldo cuando a una empresa le falta (o tiene imposible) su mediana historica.
SECTOR_MIN_EMPRESAS = 5
PEG_MIN_EMPRESAS_SECTOR = SECTOR_MIN_EMPRESAS   # nombre anterior (v1.2.11)


def motivo_descarte(metrica, actual, mediana):
    """
    Si el par (actual, mediana) de una metrica no es creible devuelve un texto con el motivo;
    si es utilizable (o falta algun dato, que es otro caso) devuelve None.
    """
    rango = RANGOS_PLAUSIBLES.get(metrica)
    if rango is None:
        return None
    lo, hi = rango
    for etiqueta, v in (("valor actual", actual), ("mediana histórica", mediana)):
        try:
            if v is None or v != v:      # None o NaN: no es un descarte, es un dato faltante
                continue
            if v < lo or v > hi:
                return f"{etiqueta} fuera de rango ({v:g})"
        except TypeError:
            continue
    return None
