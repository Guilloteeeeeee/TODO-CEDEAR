"""
Industria de cada empresa (v1.2.47). Es solo INFORMACION: se muestra en la tabla y en la pagina de la empresa, y sirve para buscar y filtrar.
NO se usa para calcular el puntaje, el Fair Value ni la categoria (eso sigue dependiendo del grupo del screener, config/sectors.py).

Son los nombres de industria que usan Yahoo Finance y las clasificaciones de mercado (tipo GICS), escritos en castellano a mano para las
166 empresas. Si una empresa nueva no esta en la lista, la tabla muestra solo su sector. Para sumar o corregir una: cambiar su linea.
bajar_fichas.py guarda ademas la industria que informa Yahoo (campo "industria_yahoo" de data/fichas.json) por si se quiere comparar.
"""

INDUSTRIA = {
    # --- Materiales básicos ---
    "AEM": "Minería de oro", "BHP": "Minería diversificada", "ECL": "Químicos especiales", "FCX": "Minería de cobre",
    "LIN": "Gases industriales", "NEM": "Minería de oro", "RIO": "Minería diversificada", "SCCO": "Minería de cobre",
    "SHW": "Pinturas y recubrimientos", "VALE": "Minería de hierro",
    # --- REITs ---
    "O": "REIT de locales comerciales", "PLD": "REIT industrial y logístico", "WELL": "REIT de salud",
    # --- Bancos y seguros ---
    "AIG": "Seguros diversificados", "AXP": "Tarjetas y crédito", "BAC": "Bancos diversificados", "BBVA": "Bancos diversificados",
    "BNY": "Custodia y gestión de activos", "BRK-B": "Seguros diversificados", "BX": "Gestión de activos alternativos",
    "C": "Bancos diversificados", "GS": "Banca de inversión", "HDB": "Bancos regionales", "HSBC": "Bancos diversificados",
    "IBKR": "Corredoras de bolsa", "IBN": "Bancos regionales", "ING": "Bancos diversificados", "ITUB": "Bancos regionales",
    "JPM": "Bancos diversificados", "MS": "Banca de inversión", "MUFG": "Bancos diversificados", "NU": "Bancos regionales",
    "SAN": "Bancos diversificados", "SCHW": "Corredoras de bolsa", "USB": "Bancos regionales",
    # --- Pagos y datos ---
    "COIN": "Plataformas de criptomonedas", "FISV": "Tecnología de pagos", "MA": "Procesamiento de pagos",
    "MRSH": "Corretaje de seguros", "PYPL": "Procesamiento de pagos", "SPGI": "Datos e índices financieros", "V": "Procesamiento de pagos",
    # --- Consumo discrecional ---
    "ABNB": "Alojamiento y viajes", "AMZN": "Comercio electrónico", "BABA": "Comercio electrónico", "BKNG": "Servicios de viajes",
    "GM": "Fabricantes de autos", "HD": "Mejoras del hogar", "MCD": "Restaurantes", "MELI": "Comercio electrónico",
    "NKE": "Calzado y ropa deportiva", "ORLY": "Repuestos para automotores", "PDD": "Comercio electrónico", "RACE": "Fabricantes de autos",
    "ROST": "Tiendas de ropa con descuento", "SBUX": "Restaurantes", "SONY": "Electrónica de consumo",
    "TJX": "Tiendas de ropa con descuento", "TM": "Fabricantes de autos", "TSLA": "Fabricantes de autos",
    # --- Comunicación ---
    "DIS": "Entretenimiento", "GOOGL": "Internet y publicidad", "META": "Redes sociales y publicidad", "NFLX": "Entretenimiento (streaming)",
    "NTES": "Videojuegos", "SPOT": "Streaming de música",
    # --- Telecomunicaciones ---
    "T": "Servicios de telecomunicaciones", "TMUS": "Servicios de telecomunicaciones", "VZ": "Servicios de telecomunicaciones",
    # --- Industrial ---
    "BA": "Aeroespacial y defensa", "CAT": "Maquinaria de construcción y minería", "DE": "Maquinaria agrícola",
    "FDX": "Logística y paquetería", "GE": "Aeroespacial y defensa", "GEV": "Equipos eléctricos y energía", "HON": "Conglomerados industriales",
    "HWM": "Aeroespacial y defensa", "LMT": "Aeroespacial y defensa", "MMM": "Conglomerados industriales", "PCAR": "Camiones pesados",
    "RTX": "Aeroespacial y defensa", "SIEGY": "Conglomerados industriales", "UBER": "Movilidad y reparto", "UNP": "Ferrocarriles",
    # --- Semiconductores ---
    "ADI": "Semiconductores", "AMAT": "Equipos para semiconductores", "AMD": "Semiconductores", "ARM": "Semiconductores",
    "ASML": "Equipos para semiconductores", "AVGO": "Semiconductores", "INTC": "Semiconductores", "KLAC": "Equipos para semiconductores",
    "LRCX": "Equipos para semiconductores", "MRVL": "Semiconductores", "MU": "Semiconductores", "NVDA": "Semiconductores",
    "QCOM": "Semiconductores", "TSM": "Semiconductores", "TXN": "Semiconductores",
    # --- Software y nube ---
    "ADBE": "Software de aplicaciones", "CRM": "Software de aplicaciones", "CRWD": "Software de infraestructura", "MSFT": "Software de infraestructura",
    "NOW": "Software de aplicaciones", "ORCL": "Software de infraestructura", "PANW": "Software de infraestructura",
    "PLTR": "Software de infraestructura", "SAP": "Software de aplicaciones", "SHOP": "Software de aplicaciones", "SNOW": "Software de aplicaciones",
    # --- Hardware y servicios TI ---
    "AAPL": "Electrónica de consumo", "ACN": "Servicios de TI y consultoría", "ADP": "Nómina y recursos humanos", "ANET": "Equipos de redes",
    "CSCO": "Equipos de redes", "DELL": "Computadoras y equipos", "IBM": "Servicios de TI y software", "INFY": "Servicios de TI y consultoría",
    "MSI": "Equipos de comunicaciones", "WDC": "Almacenamiento de datos",
    # --- Energía ---
    "BP": "Petróleo y gas integrado", "COP": "Exploración y producción de petróleo", "CVX": "Petróleo y gas integrado",
    "EQNR": "Petróleo y gas integrado", "PBR": "Petróleo y gas integrado", "PSX": "Refinación y comercialización", "SHEL": "Petróleo y gas integrado",
    "SLB": "Servicios petroleros", "TTE": "Petróleo y gas integrado", "XOM": "Petróleo y gas integrado",
    # --- Consumo básico ---
    "CL": "Cuidado personal y del hogar", "COST": "Hipermercados y tiendas de descuento", "DEO": "Bebidas alcohólicas", "KO": "Bebidas sin alcohol",
    "MDLZ": "Alimentos envasados", "MO": "Tabaco", "PEP": "Bebidas sin alcohol", "PG": "Cuidado personal y del hogar", "PM": "Tabaco",
    "TGT": "Hipermercados y tiendas de descuento", "UL": "Cuidado personal y del hogar", "WMT": "Hipermercados y tiendas de descuento",
    # --- Salud ---
    "ABBV": "Farmacéuticas", "ABT": "Dispositivos médicos", "AMGN": "Biotecnología", "AZN": "Farmacéuticas", "BMY": "Farmacéuticas",
    "CVS": "Seguros de salud y farmacias", "DHR": "Diagnósticos e investigación", "GILD": "Biotecnología", "GSK": "Farmacéuticas",
    "ISRG": "Dispositivos médicos", "JNJ": "Farmacéuticas", "LLY": "Farmacéuticas", "MDT": "Dispositivos médicos", "MRK": "Farmacéuticas",
    "NVO": "Farmacéuticas", "NVS": "Farmacéuticas", "PFE": "Farmacéuticas", "TMO": "Diagnósticos e investigación",
    "UNH": "Seguros de salud", "VRTX": "Biotecnología",
    # --- Utilities ---
    "CEG": "Generación de energía", "NEE": "Servicios eléctricos", "TLN": "Generación de energía", "VST": "Generación de energía",
}


def industria_de(ticker):
    """Industria de una empresa (texto) o None si no esta en la lista."""
    return INDUSTRIA.get(str(ticker or "").upper())
