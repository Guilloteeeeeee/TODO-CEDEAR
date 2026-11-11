"""
v1.5.69 — Moneda en que cada empresa de afuera fija su dividendo (Score de Seguridad del Dividendo, pilar 3).

Decisión de Guille (11/11/2026): «el recorte no debería aplicar si hay un cambio por devaluación o apreciación, sino que debería
buscarse en la moneda en que paga el dividendo la empresa». Hasta la v1.5.68, a toda empresa no estadounidense se le contaban los años
pagando (no los años sin recortar), porque su dividendo en dólares se mueve con la moneda. Eso dejaba pasar recortes reales (Shell y BP
en 2020, Diageo en 2026, GSK en 2022). Ahora el recorte se busca en la moneda del dividendo:

  1. Dividendo fijado en dólares (Shell, BP, BHP, Rio Tinto, AstraZeneca, Diageo, Alibaba…) → la misma regla que en EE.UU.
  2. En otra moneda, con el dividendo original bajado de la bolsa de origen (bajar_dividendos_locales.py → data/historico/
     dividendos_locales.json) → la misma regla que en EE.UU., sobre los montos en su moneda (sin pasar por el dólar).
  3. Sin el original, pero con la historia de la moneda (data/historico/monedas.json, o los fondos de monedas FXB, FXE, FXF, FXY,
     FXA y FXC del archivo de precios mensuales) → los pagos del ADR se pasan a su moneda y se busca el recorte con un margen de
     TOLERANCIA_CONVERTIDO (la conversión es aproximada: Yahoo da la fecha de corte y el banco del ADR convierte el día de pago,
     semanas después, y cobra una comisión).
  4. Sin nada de eso → la regla de antes (años pagando).

Los años que no se pueden medir en su moneda (antes de que empiece la serie) se cuentan como antes, con el beneficio de la duda.
"""
import datetime as _dt
from statistics import mean

TOLERANCIA_CONVERTIDO = 0.05   # con pagos reconstruidos desde los dólares: recorte = baja de más de 5%
VENTANA_PAGO = 42             # días después de la fecha de corte en que se promedia el tipo de cambio (fecha de pago aproximada)
COINCIDENCIA_MIN = 0.6        # bolsa de origen: parte de los pagos del ADR que tiene que tener un pago local cerca para darla por buena

# Por defecto, la moneda del dividendo es la de sus balances (moneda_estados del cache). Estas son las excepciones, verificadas.
EXCEPCIONES = {
    "NVS": ("CHF", "informa en dólares; el dividendo lo fija en francos suizos"),
    "TTE": ("EUR", "informa en dólares; el dividendo lo fija en euros"),
    "GFI": ("ZAR", "informa en dólares; dividendo en centavos sudafricanos (interino 1S2026: 1.625 centavos)"),
    "INFY": ("INR", "informa a la SEC en dólares; dividendo en rupias (final del año fiscal 2026: ₹25)"),
    "VALE": ("BRL", "informa a la SEC en dólares; remuneración en reales (julio 2026: R$ 2,03 por acción)"),
    "XP": ("USD", "informa en reales; dividendo en dólares (mayo 2026: US$0,20 por acción)"),
    "PAGS": ("USD", "informa en reales; dividendo en dólares (marzo 2026: US$0,26 por acción)"),
    "BABA": ("USD", "informa en yuanes; dividendo en dólares por ADS (año fiscal 2026: US$1,05)"),
    "NTES": ("USD", "informa en yuanes; dividendo en dólares por ADS"),
    "JD": ("USD", "informa en yuanes; dividendo en dólares por ADS"),
    "DEO": ("USD", "desde el año fiscal 2024 informa y fija el dividendo en centavos de dólar"),
}

# Cotización en la bolsa de origen (Yahoo), para bajar el dividendo original en su moneda. Solo empresas que no lo fijan en dólares.
# Unilever: Ámsterdam (euros; la de Londres paga en libras convertidas). Vodafone fija en euros y cotiza en Londres en libras: sin bolsa
# en su moneda, se convierte el ADR.
LOCAL = {
    # libras
    "BCS": "BARC.L", "GSK": "GSK.L", "LYG": "LLOY.L", "NGG": "NG.L",
    # euros
    "AEG": "AGN.AS", "ASML": "ASML.AS", "BBVA": "BBVA.MC", "E": "ENI.MI", "ING": "INGA.AS", "NOK": "NOKIA.HE", "PHG": "PHIA.AS",
    "RACE": "RACE.MI", "SAN": "SAN.MC", "SAP": "SAP.DE", "SIEGY": "SIE.DE", "UL": "UNA.AS", "TTE": "TTE.PA",
    # francos suizos, yenes
    "NVS": "NOVN.SW",
    "HMC": "7267.T", "MFG": "8411.T", "MUFG": "8306.T", "NMR": "8604.T", "SONY": "6758.T", "TM": "7203.T",
    # reales
    "ABEV": "ABEV3.SA", "BBD": "BBDC4.SA", "BSBR": "SANB11.SA", "EMBJ": "EMBJ3.SA", "GGB": "GGBR4.SA", "ITUB": "ITUB4.SA",
    "LND": "AGRO3.SA", "PBR": "PETR3.SA", "SBS": "SBSP3.SA", "SUZ": "SUZB3.SA", "TIMB": "TIMS3.SA", "UGP": "UGPA3.SA",
    "VIV": "VIVT3.SA", "VALE": "VALE3.SA",
    # pesos mexicanos
    "AMX": "AMXB.MX", "ASR": "ASURB.MX", "FMX": "FEMSAUBD.MX", "KOF": "KOFUBL.MX", "PAC": "GAPB.MX", "TV": "TLEVISACPO.MX",
    # wones, rupias, rands, dólar taiwanés, coronas, dólar canadiense, peso chileno
    "KB": "105560.KS", "KEP": "015760.KS", "PKX": "005490.KS",
    "HDB": "HDFCBANK.NS", "IBN": "ICICIBANK.NS", "INFY": "INFY.NS",
    "HMY": "HAR.JO", "GFI": "GFI.JO", "TSM": "2330.TW", "ERIC": "ERIC-B.ST", "NVO": "NOVO-B.CO", "CCJ": "CCO.TO",
    "AKO-B": "ANDINA-B.SN",
}

# Fondos de monedas del archivo de precios mensuales (respaldo mientras no esté data/historico/monedas.json): dólares por unidad × 100
PROXY = {"GBP": "FXB", "EUR": "FXE", "CHF": "FXF", "JPY": "FXY", "AUD": "FXA", "CAD": "FXC"}


def moneda(ticker, moneda_estados=None, pais=None):
    """Moneda en que la empresa fija su dividendo: la excepción verificada o la de sus balances. Las de EE.UU., dólares."""
    if ticker in EXCEPCIONES:
        return EXCEPCIONES[ticker][0]
    if (pais or "United States") == "United States":
        return "USD"
    return (moneda_estados or "USD").upper()


def _fecha(f):
    return _dt.date.fromisoformat(str(f)[:10])


def _tc_semanal(serie, d):
    """Dólares por unidad: promedio de la serie entre la fecha de corte y VENTANA_PAGO días después (fecha de pago aproximada)."""
    hasta = d + _dt.timedelta(days=VENTANA_PAGO)
    vals = [v for f, v in serie if d < f <= hasta]
    if vals:
        return mean(vals)
    antes = [v for f, v in serie if d - _dt.timedelta(days=10) <= f <= d]
    return antes[-1] if antes else None


def convertir(pagos, mon, monedas=None, precios=None):
    """Pagos del ADR (dólares) pasados a la moneda del dividendo. -> (pagos convertidos, fuente) o (None, None).
    Usa data/historico/monedas.json ({"monedas": {"GBP": {"usd_por_unidad": {fecha: valor}}}}) y, si no está esa moneda, el fondo de
    monedas del archivo de precios mensuales (FXB, FXE…: mes de la fecha de corte y el siguiente). Los pagos sin tipo de cambio se dejan
    afuera (la serie arranca donde arranca la historia de la moneda)."""
    if not pagos or not mon or mon == "USD":
        return None, None
    sem = (((monedas or {}).get("monedas") or {}).get(mon) or {}).get("usd_por_unidad")
    if sem:
        serie = sorted((_fecha(f), float(v)) for f, v in sem.items() if v)
        out = []
        for f, m in pagos:
            tc = _tc_semanal(serie, _fecha(f))
            if tc and m:
                out.append([str(f)[:10], m / tc])
        return (out, "monedas") if out else (None, None)
    px = ((precios or {}).get(PROXY.get(mon, "")) or {}).get("m")
    if px:
        out = []
        for f, m in pagos:
            d = _fecha(f)
            sig = (d.replace(day=1) + _dt.timedelta(days=32)).strftime("%Y-%m")
            vals = [px[k] for k in (d.strftime("%Y-%m"), sig) if px.get(k)]
            if vals and m:
                out.append([str(f)[:10], m / mean(vals) * 100])
        return (out, "fondo de monedas") if out else (None, None)
    return None, None


def _completar(h, base):
    """Los años que no se pueden medir en su moneda (antes de que empiece la serie) se cuentan como antes, con el beneficio de la duda:
    si en todo lo medido no hubo recorte, los años sin recortar se extienden a los años pagando de la serie del ADR. Las crisis que la
    serie no alcanza a cubrir se leen como antes (serie del ADR)."""
    if not h or not base:
        return h
    medidos = sum(1 for a in (h.get("tasa") or {}) if a <= h["ultimo_completo"])
    if not h.get("recorte_en_curso") and h["anios_sin_recorte"] >= medidos and base["anios_pagando"] > h["anios_sin_recorte"]:
        h = dict(h, anios_sin_recorte=base["anios_pagando"], extendido=True)
    h = dict(h, anios_pagando=max(h["anios_pagando"], base["anios_pagando"]))
    primero = min(h.get("tasa") or {9999: 0})
    for clave, previo in (("crisis_0809", 2007), ("crisis_2020", 2019)):
        if primero > previo and base.get(clave):
            h[clave] = base[clave]
    return h


def historial(ticker, moneda_estados, pagos, pais=None, hoy=None, sigue_pagando=False, locales=None, monedas=None, precios=None):
    """-> (historial de analizar_dividendos, fuente). fuente: "dolares" | "local" | "convertido" | "variable" (la regla de antes).
    El score usa la regla de EE.UU. (años sin recortar) salvo con fuente "variable"."""
    from scoring import dividendo as SD
    mon = moneda(ticker, moneda_estados, pais)
    base = SD.analizar_dividendos(pagos, hoy=hoy, sigue_pagando=sigue_pagando) if pagos else None
    if mon == "USD":
        return base, "dolares"
    loc = (locales or {}).get(ticker) or {}
    if loc.get("ok") and loc.get("pagos"):
        h = SD.analizar_dividendos(loc["pagos"], hoy=hoy, sigue_pagando=sigue_pagando)
        if h:
            return _completar(h, base), "local"
    conv, _ = convertir(pagos, mon, monedas, precios)
    if conv:
        h = SD.analizar_dividendos(conv, hoy=hoy, sigue_pagando=sigue_pagando, tolerancia=TOLERANCIA_CONVERTIDO)
        if h:
            return _completar(h, base), "convertido"
    return base, "variable"


def coincidencia(pagos_adr, pagos_local, dias=25, desde=None):
    """Parte de los pagos del ADR (desde que empieza la serie local, o `desde`) que tienen un pago local a `dias` días o menos.
    Sirve para confirmar que el símbolo de la bolsa de origen es la misma empresa."""
    if not pagos_adr or not pagos_local:
        return 0.0
    loc = sorted(_fecha(f) for f, _ in pagos_local)
    ini = _fecha(desde) if desde else loc[0]
    adr = [_fecha(f) for f, _ in pagos_adr if _fecha(f) >= ini]
    if not adr:
        return 0.0
    ok = sum(1 for d in adr if any(abs((d - x).days) <= dias for x in loc))
    return round(ok / len(adr), 3)


def saltos_de_unidad(pagos, factor=40):
    """Fechas donde un pago es `factor` veces mayor o menor que el anterior (Yahoo a veces mezcla peniques y libras)."""
    out = []
    for (f0, m0), (f1, m1) in zip(pagos, pagos[1:]):
        if m0 and m1 and (m1 / m0 > factor or m0 / m1 > factor):
            out.append(str(f1)[:10])
    return out
