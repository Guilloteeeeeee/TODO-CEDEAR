"""
Industria de Damodaran (EE.UU., enero 2026) que le corresponde a cada empresa de TodoCedears (v1.2.88, PROPUESTA a aprobar por Guille).
Damodaran tiene ~94 industrias y TodoCedears 15 sectores: la comparación se hace contra la industria de Damodaran, no contra el sector propio.
Los nombres tienen que ser EXACTAMENTE los de sus planillas (el test lo controla). Para corregir una empresa, cambiar su línea.
"""

_G = {
    "Bank (Money Center)": "BAC C JPM BBVA HSBC ING MUFG SAN",
    "Banks (Regional)": "HDB IBN ITUB NU USB",
    "Brokerage & Investment Banking": "GS MS IBKR SCHW",
    "Investments & Asset Management": "BNY BX",
    "Insurance (General)": "AIG MRSH",
    "Insurance (Prop/Cas.)": "BRK-B",
    "Financial Svcs. (Non-bank & Insurance)": "AXP COIN FISV MA PYPL V",
    "Information Services": "SPGI",
    "Retail (REITs)": "O",
    "R.E.I.T.": "PLD WELL",
    "Entertainment": "DIS NFLX SPOT",
    "Software (Internet)": "GOOGL META",
    "Software (Entertainment)": "NTES",
    "Household Products": "CL PG UL",
    "Retail (General)": "COST TGT WMT AMZN BABA PDD MELI",
    "Beverage (Alcoholic)": "DEO",
    "Beverage (Soft)": "KO PEP",
    "Food Processing": "MDLZ",
    "Tobacco": "MO PM",
    "Hotel/Gaming": "ABNB BKNG",
    "Auto & Truck": "GM TM TSLA RACE",
    "Retail (Building Supply)": "HD",
    "Restaurant/Dining": "MCD SBUX",
    "Shoe": "NKE",
    "Retail (Automotive)": "ORLY",
    "Retail (Special Lines)": "ROST TJX",
    "Electronics (Consumer & Office)": "SONY",
    "Oil/Gas (Integrated)": "BP CVX EQNR PBR SHEL TTE XOM",
    "Oil/Gas (Production and Exploration)": "COP",
    "Oil/Gas Distribution": "PSX",
    "Oilfield Svcs/Equip.": "SLB",
    "Computers/Peripherals": "AAPL DELL WDC",
    "Computer Services": "ACN ADP IBM INFY",
    "Telecom. Equipment": "ANET CSCO MSI",
    "Aerospace/Defense": "BA GE HWM LMT RTX",
    "Machinery": "CAT DE PCAR",
    "Transportation": "FDX UBER",
    "Transportation (Railroads)": "UNP",
    "Electrical Equipment": "GEV",
    "Diversified": "HON MMM SIEGY",
    "Precious Metals": "AEM NEM",
    "Metals & Mining": "BHP RIO FCX SCCO VALE",
    "Chemical (Specialty)": "ECL LIN SHW",
    "Drugs (Pharmaceutical)": "ABBV AZN BMY GSK JNJ LLY MRK NVO NVS PFE",
    "Drugs (Biotechnology)": "AMGN GILD VRTX",
    "Healthcare Products": "ABT ISRG MDT DHR TMO",
    "Healthcare Support Services": "CVS UNH",
    "Semiconductor": "ADI AMD ARM AVGO INTC MRVL MU NVDA QCOM TSM TXN",
    "Semiconductor Equip": "AMAT ASML KLAC LRCX",
    "Software (System & Application)": "ADBE CRM NOW SAP SHOP SNOW CRWD MSFT ORCL PANW PLTR",
    "Telecom. Services": "T VZ",
    "Telecom (Wireless)": "TMUS",
    "Power": "CEG TLN VST",
    "Utility (General)": "NEE",
}

MAPA = {t: ind for ind, tks in _G.items() for t in tks.split()}

# Industrias donde los márgenes/EV de Damodaran NO se pueden comparar con una empresa común (financieras): en la ficha se muestran solo PER, P/B, ROE y margen neto.
FINANCIERAS = {"Bank (Money Center)", "Banks (Regional)", "Brokerage & Investment Banking", "Investments & Asset Management", "Insurance (General)", "Insurance (Prop/Cas.)",
               "Financial Svcs. (Non-bank & Insurance)"}


# Región de Damodaran con la que se compara cada empresa (v1.2.88). Todo lo que no figura acá se compara con EE.UU. Cuenta el lugar donde la empresa hace su negocio y cotiza, no sólo donde está registrada
# (ACN, MDT y LIN, registradas en Irlanda/Reino Unido pero con negocio y cotización en EE.UU., quedan con EE.UU.; PDD, registrada en Irlanda pero china, va con emergentes).
_R = {
    "emergentes": "VALE ITUB NU PBR HDB IBN INFY BABA NTES PDD MELI TSM",
    "europa": "HSBC ARM SHEL BP UL DEO GSK AZN RIO SAN BBVA ING ASML SIEGY SAP RACE SPOT TTE EQNR NVS NVO",
    "aus_nz_canada": "AEM SHOP BHP",
    "japon": "MUFG TM SONY",          # sin planilla regional: se compara con EE.UU. y la nota lo aclara
}
REGION = {t: r for r, tks in _R.items() for t in tks.split()}
REGION_TXT = {"us": "empresas de EE.UU.", "emergentes": "empresas de mercados emergentes", "europa": "empresas de Europa", "aus_nz_canada": "empresas de Australia, Nueva Zelanda y Canadá",
              "japon": "empresas de EE.UU. (no hay planilla de Japón)"}
