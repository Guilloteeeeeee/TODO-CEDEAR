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

# Tanda 1 (v1.5.24): las 49 empresas cargadas en la v1.5.16 (propuesta, igual que el resto; para corregir una empresa, cambiar su línea).
_G_TANDA1 = {
    "Steel": "NUE",
    "Chemical (Basic)": "MOS DOW",
    "Chemical (Specialty)": "DD IFF",
    "Packaging & Container": "IP AVY",
    "Bank (Money Center)": "WFC BCS",
    "Banks (Regional)": "LYG",
    "Auto & Truck": "F",
    "Retail (General)": "EBAY JD",
    "Recreation": "CCL",
    "Hotel/Gaming": "LVS",
    "Shoe": "DECK",
    "Software (Internet)": "PINS SNAP ROKU BIDU VRSN",
    "Telecom (Wireless)": "AMX VOD",
    "Building Materials": "JCI",
    "Machinery": "SNA",
    "Air Transport": "DAL UAL AAL",
    "Semiconductor": "SWKS ALAB",
    "Software (System & Application)": "DOCU TWLO TEAM",
    "Computers/Peripherals": "HPQ SNDK",
    "Electronics (General)": "GLW GRMN",
    "Oil/Gas (Production and Exploration)": "OXY",
    "Oilfield Svcs/Equip.": "BKR HAL",
    "Metals & Mining": "CCJ",
    "Food Processing": "HSY",
    "Household Products": "KMB",
    "Food Wholesalers": "SYY",
    "Farming/Agriculture": "BG",
    "Drugs (Biotechnology)": "BIIB MRNA",
    "Healthcare Support Services": "CAH",
    "Healthcare Products": "NTRA",
}
for _ind, _tks in _G_TANDA1.items():
    _G[_ind] = (_G.get(_ind, "") + " " + _tks).strip()

# Tanda 2 (v1.5.26): 50 empresas nuevas (PROPUESTA, igual que el resto: Guille la puede corregir cambiando la línea).
_G_TANDA2 = {
    "Aerospace/Defense": "SPCX RKLB",
    "Brokerage & Investment Banking": "HOOD XP",
    "Software (System & Application)": "MSTR CRWV ZM PATH AI",
    "Software (Entertainment)": "RBLX",
    "Power": "OKLO",
    "Software (Internet)": "NBIS YELP",
    "Green & Renewable Energy": "FSLR",
    "Auto & Truck": "XPEV NIO STLA HMC HOG",
    "Retail (General)": "SE ETSY",
    "Hotel/Gaming": "TCOM TRIP",
    "Financial Svcs. (Non-bank & Insurance)": "STNE PAGS XYZ UPST",
    "Information Services": "EFX",
    "Healthcare Support Services": "HIMS",
    "Heathcare Information and Technology": "TEM",
    "Telecom. Equipment": "ASTS ERIC",
    "Computers/Peripherals": "RGTI",
    "Precious Metals": "B KGC HMY GFI PAAS CDE HL",
    "Metals & Mining": "MP NXE LAC",
    "Retail (Grocery and Food)": "FMX",
    "Healthcare Products": "PHG",
    "Utility (General)": "NGG",
    "Rubber& Tires": "GT",
    "Retail (Special Lines)": "ANF URBN",
    "Banks (Regional)": "KB",
}
for _ind, _tks in _G_TANDA2.items():
    _G[_ind] = (_G.get(_ind, "") + " " + _tks).strip()

# Tanda 3 (v1.5.37): PROPUESTA, igual que el resto: Guille la puede corregir cambiando la línea.
_G_TANDA3 = {
    "Retail (Automotive)": "AAP SDA",
    "Beverage (Alcoholic)": "ABEV",
    "Farming/Agriculture": "AGRO BIOX LND",
    "Insurance (Life)": "AEG",
    "Beverage (Soft)": "AKO-B KOF",
    "Restaurant/Dining": "ARCO",
    "Transportation": "ASR CAAP CAR PAC",
    "Chemical (Basic)": "BAK",
    "Software (System & Application)": "BB",
    "Banks (Regional)": "BBD BSBR",
    "Financial Svcs. (Non-bank & Insurance)": "BMNR HUT IREN RIOT",
    "Electronics (General)": "CLS",
    "Building Materials": "CX",
    "Oil/Gas (Integrated)": "E",
    "Utility (General)": "ELPC KEP",
    "Aerospace/Defense": "EMBJ SATL SPCE",
    "Steel": "GGB PKX SID TX",
    "Oil/Gas Distribution": "GLNG UGP",
    "Computer Services": "GLOB KEEL",
    "Oil/Gas (Production and Exploration)": "GPRK VIST",
    "Retail (General)": "JMIA",
    "Software (Internet)": "JOYY WB",
    "Metals & Mining": "LAR",
    "Bank (Money Center)": "MFG",
    "Precious Metals": "MUX NG",
    "Brokerage & Investment Banking": "NMR",
    "Telecom. Equipment": "NOK ONDS",
    "Office Equipment & Services": "PBI XRX",
    "Utility (Water)": "SBS",
    "Paper/Forest Products": "SUZ",
    "Oilfield Svcs/Equip.": "TS",
    "Telecom (Wireless)": "TIMB",
    "Broadcasting": "TV",
    "Telecom. Services": "VIV",
    "Insurance (Prop/Cas.)": "TRV",
    "Power": "AXIAY",
}
for _ind, _tks in _G_TANDA3.items():
    _G[_ind] = (_G.get(_ind, "") + " " + _tks).strip()

MAPA = {t: ind for ind, tks in _G.items() for t in tks.split()}

# Industrias donde los márgenes/EV de Damodaran NO se pueden comparar con una empresa común (financieras): en la ficha se muestran solo PER, P/B, ROE y margen neto.
FINANCIERAS = {"Bank (Money Center)", "Banks (Regional)", "Brokerage & Investment Banking", "Investments & Asset Management", "Insurance (General)", "Insurance (Prop/Cas.)",
               "Financial Svcs. (Non-bank & Insurance)"}


# Región de Damodaran con la que se compara cada empresa (v1.2.88). Todo lo que no figura acá se compara con EE.UU. Cuenta el lugar donde la empresa hace su negocio y cotiza, no sólo donde está registrada
# (ACN, MDT y LIN, registradas en Irlanda/Reino Unido pero con negocio y cotización en EE.UU., quedan con EE.UU.; PDD, registrada en Irlanda pero china, va con emergentes).
_R = {
    "emergentes": "VALE ITUB NU PBR HDB IBN INFY BABA NTES PDD MELI TSM AMX BIDU JD XPEV NIO SE TCOM STNE XP PAGS FMX HMY GFI KB",
    "europa": "HSBC ARM SHEL BP UL DEO GSK AZN RIO SAN BBVA ING ASML SIEGY SAP RACE SPOT TTE EQNR NVS NVO BCS LYG VOD NBIS STLA ERIC PHG NGG",
    "aus_nz_canada": "AEM SHOP BHP CCJ B KGC PAAS NXE",
    "japon": "MUFG TM SONY HMC",          # sin planilla regional: se compara con EE.UU. y la nota lo aclara
}
for _r3, _t3 in {"emergentes": "ABEV AGRO AKO-B ARCO ASR BAK BBD BIOX BSBR CAAP CX ELPC EMBJ GGB GLOB GPRK JMIA JOYY KEP KOF LAR LND PAC PKX SBS SDA SID SUZ TS TIMB TV TX UGP VIST VIV WB AXIAY", "europa": "AEG E NOK", "aus_nz_canada": "BB CLS NG", "japon": "MFG NMR"}.items():   # Tanda 3 (v1.5.37)
    _R[_r3] = _R[_r3] + " " + _t3
REGION = {t: r for r, tks in _R.items() for t in tks.split()}
REGION_TXT = {"us": "empresas de EE.UU.", "emergentes": "empresas de mercados emergentes", "europa": "empresas de Europa", "aus_nz_canada": "empresas de Australia, Nueva Zelanda y Canadá",
              "japon": "empresas de EE.UU. (no hay planilla de Japón)"}
