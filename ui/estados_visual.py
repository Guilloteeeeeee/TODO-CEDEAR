"""Estados Financieros visuales (v1.5.47; v1.5.49 rehecho con Guille, 08/11/2026).

La solapa «Estados Financieros» de la ficha tiene subsolapas: Estado de Resultados · Balance · Estado de Flujo de Efectivo · Ratios Financieros.
Cada una muestra lo que dice ESE estado (montos); los cruces entre estados (márgenes, retornos, deuda sobre EBITDA…) van en Ratios. Arriba van
tarjetas con gráficos de barras (años fiscales y, en oscuro, los últimos 12 meses) y debajo la tabla de siempre.

Tipo de empresa (familia), porque no todo sirve para todas (pedido de Guille: «rigurosos y precisos»):
- general: la mayoría.
- financiera (bancos, aseguradoras, bancos de inversión): no tienen costo de ventas, resultado operativo ni EBITDA comparables, y su flujo
  operativo mueve préstamos y depósitos, así que el flujo libre no dice nada útil. Se miran el resultado neto, el patrimonio, el ROE y el ROA.
- reit (inmobiliarias que reparten casi todo): la amortización de los inmuebles achica mucho la ganancia contable; se miran el EBITDA, el flujo
  operativo por acción (lo más cercano al FFO que tenemos) y cuánto de ese flujo se va en dividendos.

Línea punteada = valor de SU industria según Damodaran (ene-2026), y solo cuando el número se calcula igual que el nuestro
(Damodaran suma las cifras de todas las empresas de la industria: no es un promedio simple). Sin texto de leyenda (Guille): el número va sobre
la línea y el detalle aparece al pasar el mouse. Si la industria no tiene ese dato, o se calcula distinto, no hay línea.
"""
import html

from data import af_tablas as _T

try:
    from data.af_v4 import NOMBRES_MONEDA
except Exception:  # noqa: BLE001
    NOMBRES_MONEDA = {}

INDUSTRIAS_FIN = ("Bank (Money Center)", "Banks (Regional)", "Insurance (General)", "Insurance (Life)", "Insurance (Prop/Cas.)", "Reinsurance",
                  "Brokerage & Investment Banking")


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def familia(ticker, est=None):
    """'reit', 'financiera' o 'general', según la industria de Damodaran y, si no está, según los datos (sin resultado operativo = financiera)."""
    ind = ""
    try:
        from data import damodaran as _D
        ind = _D.industria_de(ticker) or ""
    except Exception:  # noqa: BLE001
        pass
    if "REIT" in ind or "R.E.I.T" in ind:      # Damodaran usa «Retail (REITs)» y «R.E.I.T.»
        return "reit"
    if ind in INDUSTRIAS_FIN:
        return "financiera"
    if est:      # sin resultado operativo informado (como los bancos): se trata como financiera aunque Damodaran la ponga en otra industria
        op = _T._serie(est, "resultados", "Resultado operativo")
        if not any(v is not None for v in op.values()):
            return "financiera"
    return "general"


def series(est):
    """(años con el TTM al final, clave del TTM, {clave: {año: valor}}) con todo lo que dibujan los gráficos."""
    fy, ttm = _T._anios(est)
    anios = fy + ([ttm] if ttm else [])
    S = lambda g, r: _T._serie(est, g, r)      # noqa: E731
    R = lambda r: S("ratios", r)               # noqa: E731
    ing, acc = S("resultados", "Ingresos"), S("resultados", "Acciones promedio (diluidas)")
    op, neto, ebitda = S("resultados", "Resultado operativo"), S("resultados", "Resultado neto"), S("resultados", "EBITDA")
    tasa, intereses = S("resultados", "Tasa de impuesto"), S("resultados", "Gasto por intereses")
    caja, deuda, pat, activo = (S("balance", "Caja e inversiones de corto plazo"), S("balance", "Deuda total"), S("balance", "Patrimonio neto"),
                                S("balance", "Activo total"))
    fco, fcf = S("flujo", "Flujo de efectivo operativo"), S("flujo", "Flujo de efectivo libre")
    div, capex, recompra = S("flujo", "Dividendos pagados"), S("flujo", "Inversión en activos fijos (CAPEX)"), S("flujo", "Recompra de acciones")
    crec = {}
    for i, a in enumerate(fy):
        if i and ing.get(a) and ing.get(fy[i - 1]) and ing[fy[i - 1]] > 0:
            crec[a] = ing[a] / ing[fy[i - 1]] - 1
    # (sin barra de 12 meses en el crecimiento: comparar 12 meses con el último año fiscal mezclaría trimestres repetidos)

    sin_intereses = [a for a in fy if op.get(a) is not None and intereses.get(a) is None]
    return anios, ttm, {
        "ing": ing, "crec": crec, "op": op, "neto": neto, "ebitda": ebitda,
        "eps": S("resultados", "Ganancia por acción (diluida)"), "acc": acc,
        "caja": caja, "deuda": deuda, "dneta": S("balance", "Deuda neta"), "pat": pat, "activo": activo,
        "good": S("balance", "Plusvalía (goodwill)"), "liq": R("Liquidez corriente (activo / pasivo corriente)"),
        "fco": fco, "capex": {a: abs(v) for a, v in capex.items() if v is not None}, "fcf": fcf,
        "fps": {a: fcf[a] / acc[a] for a in anios if fcf.get(a) is not None and acc.get(a)},
        "fcops": {a: fco[a] / acc[a] for a in anios if fco.get(a) is not None and acc.get(a)},
        "div": {a: abs(v) for a, v in div.items() if v is not None},
        "rec": {a: abs(v) for a, v in recompra.items() if v is not None},
        "mbr": R("Margen bruto"), "mop": R("Margen operativo"), "mne": R("Margen neto"), "mfcf": R("Margen de flujo de efectivo libre"),
        "mebitda": {a: ebitda[a] / ing[a] for a in anios if ebitda.get(a) is not None and ing.get(a)},
        "roe": R("Retorno sobre el patrimonio (ROE)"),
        "roic": R("Retorno sobre el capital invertido (ROIC)"),      # el mismo de la tabla (capital invertido según Yahoo)
        "roa": {a: neto[a] / activo[a] for a in anios if neto.get(a) is not None and activo.get(a)},
        "solv": {a: pat[a] / activo[a] for a in anios if pat.get(a) is not None and activo.get(a)},
        "dne": R("Deuda neta / EBITDA"), "cob": R("Cobertura de intereses (resultado operativo / intereses)"),
        "pay": {a: abs(div[a]) / fcf[a] for a in anios if div.get(a) is not None and fcf.get(a) and fcf[a] > 0},
        "payn": {a: abs(div[a]) / neto[a] for a in anios if div.get(a) is not None and neto.get(a) and neto[a] > 0},
        "payfco": {a: abs(div[a]) / fco[a] for a in anios if div.get(a) is not None and fco.get(a) and fco[a] > 0},
        "_sin_intereses": sin_intereses,
    }


# Tarjeta: (clave, título, explicación, tipo)   tipo: "$" monto · "pct" · "x" veces · "ps" por acción · "acc" acciones
_T_ING = ("ing", "Ingresos", "Lo que vende la empresa en el año. Un negocio sano los hace crecer con el tiempo, sin saltos bruscos.", "$")
_T_CREC = ("crec", "Crecimiento de los ingresos", "Cuánto crecieron las ventas contra el año anterior. Subas parejas indican un negocio estable; saltos grandes, uno cíclico.", "pct")
_T_OP = ("op", "Resultado operativo", "Lo que gana el negocio en sí: ventas menos todos los costos de producir, vender y administrar, antes de intereses e impuestos.", "$")
_T_NETO = ("neto", "Resultado neto", "La ganancia final, después de intereses e impuestos. Es la que corresponde a los accionistas.", "$")
_T_EPS = ("eps", "Ganancia por acción", "El resultado neto dividido por la cantidad de acciones. Si crece año tras año, sostiene la suba del precio y del dividendo.", "ps")
_T_ACC = ("acc", "Acciones en circulación", "Si baja, la empresa recompra acciones y cada accionista es dueño de una porción mayor. Si sube, hay dilución.", "acc")
_T_EBITDA = ("ebitda", "EBITDA", "El resultado operativo antes de amortizaciones. En las inmobiliarias se mira mucho porque la amortización de los edificios achica la ganancia contable aunque los inmuebles no pierdan valor.", "$")
_T_CAJA = ("caja", "Caja e inversiones de corto plazo", "El dinero disponible: efectivo e inversiones que se pueden vender rápido.", "$")
_T_DEUDA = ("deuda", "Deuda total", "Todo lo que debe a bancos y tenedores de bonos, de corto y largo plazo.", "$")
_T_DNETA = ("dneta", "Deuda neta", "La deuda menos la caja. Si es negativa, la empresa tiene más caja que deuda.", "$")
_T_PAT = ("pat", "Patrimonio neto", "Lo que les pertenece a los accionistas: todo lo que tiene la empresa menos todo lo que debe. Las recompras de acciones lo achican.", "$")
_T_GOOD = ("good", "Plusvalía (goodwill)", "Lo que pagó de más, por encima del valor contable, al comprar otras empresas. Si es grande, buena parte del crecimiento vino de compras.", "$")
_T_LIQ = ("liq", "Liquidez corriente", "Lo que tiene para el corto plazo dividido por lo que vence en el año. Más de 1 indica que puede cubrir lo que vence.", "x")
_T_ACT = ("activo", "Activo total", "Todo lo que tiene la empresa. En un banco son, sobre todo, los préstamos que dio y los bonos que compró.", "$")
_T_SOLV = ("solv", "Patrimonio sobre activo", "Qué parte de lo que tiene está financiada con plata de los accionistas y no con depósitos o deuda. Cuanto más alto, más colchón frente a pérdidas.", "pct")
_T_FCO = ("fco", "Flujo de efectivo operativo", "El efectivo que genera el negocio con su actividad habitual. Es más difícil de maquillar que la ganancia contable.", "$")
_T_CAPEX = ("capex", "Inversión en activos fijos (CAPEX)", "Lo que gasta en fábricas, equipos y tecnología para mantener y hacer crecer el negocio.", "$")
_T_FCF = ("fcf", "Flujo de efectivo libre", "Flujo operativo menos CAPEX: lo que queda para dividendos, recompras o pagar deuda.", "$")
_T_FPS = ("fps", "Flujo libre por acción", "La caja libre que le corresponde a cada acción. Si crece, crece lo que la empresa puede devolver al accionista.", "ps")
_T_FCOPS = ("fcops", "Flujo operativo por acción", "El efectivo que genera el negocio por cada acción. En las inmobiliarias es lo más parecido al FFO (la medida que usa el sector) que tenemos.", "ps")
_T_DIV = ("div", "Dividendos pagados", "Lo que repartió en efectivo a los accionistas en el año.", "$")
_T_REC = ("rec", "Recompra de acciones", "Lo que usó para comprar sus propias acciones. Es otra forma de devolver dinero al accionista.", "$")
_T_MBR = ("mbr", "Margen bruto", "De cada 100 que vende, cuánto le queda después del costo de lo vendido. Un margen alto suele indicar marca o poder de precio.", "pct")
_T_MOP = ("mop", "Margen operativo", "De cada 100 que vende, cuánto le queda después de pagar todos los costos del negocio.", "pct")
_T_MNE = ("mne", "Margen neto", "De cada 100 que vende, cuánto termina como ganancia final, después de intereses e impuestos.", "pct")
_T_MEBITDA = ("mebitda", "Margen EBITDA", "De cada 100 que factura, cuánto le queda antes de intereses, impuestos y amortizaciones.", "pct")
_T_MFCF = ("mfcf", "Margen de flujo libre", "Qué parte de las ventas se convierte en caja libre. Las mejores empresas lo mantienen alto y estable.", "pct")
_T_ROE = ("roe", "Retorno sobre el patrimonio (ROE)", "Cuánto gana por cada dólar que pusieron los accionistas. La deuda lo puede inflar: conviene mirarlo junto al ROIC.", "pct")
_T_ROIC = ("roic", "Retorno sobre el capital invertido (ROIC)", "Cuánto rinde cada dólar que pusieron accionistas y acreedores. Mide qué tan bien invierte la gerencia.", "pct")
_T_ROA = ("roa", "Retorno sobre el activo (ROA)", "Resultado neto ÷ activo total. En un banco, ganar un poco más de 1% sobre todo lo que tiene ya es un buen número.", "pct")
_T_DNE = ("dne", "Deuda neta / EBITDA", "Cuántos años de EBITDA haría falta para pagar la deuda neta. Si es negativo, tiene más caja que deuda.", "x")
_T_COB = ("cob", "Cobertura de intereses", "Cuántas veces el resultado operativo paga los intereses del año. Cuanto más alta, más tranquila está frente a la deuda.", "x")
_T_PAY = ("pay", "Dividendos / flujo libre", "Qué parte de la caja libre se va en dividendos. Si se acerca al 100%, el dividendo queda con poco margen.", "pct")
_T_PAYN = ("payn", "Dividendos / resultado neto", "Qué parte de la ganancia reparte como dividendo (payout).", "pct")
_T_PAYFCO = ("payfco", "Dividendos / flujo operativo", "Qué parte del efectivo que genera el negocio se va en dividendos. En las inmobiliarias suele ser alto por ley, pero cerca del 100% deja poco margen.", "pct")

TARJETAS = {
    "general": {
        "resultados": [_T_ING, _T_CREC, _T_OP, _T_NETO, _T_EPS, _T_ACC],
        "balance": [_T_CAJA, _T_DEUDA, _T_DNETA, _T_PAT, _T_GOOD, _T_LIQ],
        "flujo": [_T_FCO, _T_CAPEX, _T_FCF, _T_FPS, _T_DIV, _T_REC],
        "ratios": [_T_MBR, _T_MOP, _T_MNE, _T_MFCF, _T_ROE, _T_ROIC, _T_DNE, _T_COB, _T_PAY],
    },
    "financiera": {
        "resultados": [_T_ING, _T_CREC, _T_NETO, _T_EPS, _T_ACC],
        "balance": [_T_ACT, _T_PAT, _T_SOLV, _T_DEUDA, _T_GOOD],
        "flujo": [_T_DIV, _T_REC],
        "ratios": [_T_MNE, _T_ROE, _T_ROA, _T_PAYN],
    },
    "reit": {
        "resultados": [_T_ING, _T_CREC, _T_OP, _T_EBITDA, _T_NETO, _T_ACC],
        "balance": [_T_ACT, _T_DEUDA, _T_DNETA, _T_PAT],
        "flujo": [_T_FCO, _T_FCOPS, _T_DIV, _T_PAYFCO],
        "ratios": [_T_MOP, _T_MEBITDA, _T_MNE, _T_ROE, _T_DNE, _T_COB],
    },
}
AVISO_FAMILIA = {
    "financiera": ("En bancos y aseguradoras no se muestran el costo de ventas, el resultado operativo, el EBITDA ni el flujo libre: por cómo funciona "
                   "el negocio (su «mercadería» es el dinero), esos números no significan lo mismo que en otras empresas."),
    "reit": ("En las inmobiliarias (REITs) la amortización de los edificios achica mucho la ganancia contable; por eso pesan más el EBITDA, el flujo "
             "operativo por acción y cuánto de ese flujo se va en dividendos."),
}

# Dato de la industria de Damodaran comparable con cada gráfico: (planilla, columna). Solo los que se calculan igual que el nuestro.
_DAMODARAN = {"mbr": ("margin", "Gross Margin"), "mop": ("margin", "Pre-tax Unadjusted Operating Margin"), "mne": ("margin", "Net Margin"),
              "mebitda": ("margin", "EBITDA/Sales"), "roe": ("pbvdata", "ROE")}
# No se toman de Damodaran: ROIC (él resta la caja del capital y el nuestro no), cobertura de intereses (él usa el resultado operativo DESPUÉS de
# impuestos), deuda neta / EBITDA, liquidez corriente, margen de flujo libre y payouts (no están en sus planillas cargadas). Para esos, la línea es la
# mediana del grupo dentro de la app (ver CLAVES_GRUPO).


# Ratios sin dato comparable en Damodaran: la línea es la MEDIANA de las demás empresas de la app del mismo sector (o del mismo tipo, en
# financieras y REITs), calculada con la misma fórmula que la de la empresa. Solo si hay al menos MIN_GRUPO empresas con dato.
CLAVES_GRUPO = ("roic", "dne", "cob", "liq", "mfcf", "pay", "roa", "solv", "payn", "payfco")
MIN_GRUPO = 5
_CACHE_GRUPOS = {}


def _sector_de(ticker):
    try:
        import json, os
        from config.sectors import partes_sector
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache_datos.json")
        clave = ("sectores", os.path.getmtime(ruta))
        if clave not in _CACHE_GRUPOS:
            filas = json.load(open(ruta, encoding="utf-8")).get("data", [])
            _CACHE_GRUPOS.clear()
            _CACHE_GRUPOS[clave] = {str(r["ticker"]).upper(): (partes_sector(r.get("sector"))[0] or "") for r in filas}
        return _CACHE_GRUPOS[clave].get(str(ticker).upper(), "")
    except Exception:  # noqa: BLE001
        return ""


def _ultimo_fy(serie, fy):
    for a in reversed(fy):
        if serie.get(a) is not None:
            return serie[a]
    return None


def valores_grupo():
    """{ticker: (familia, sector, {clave: último valor de año fiscal})} de todas las empresas con estados guardados (se calcula una vez)."""
    try:
        import os
        from data import paquetes_yahoo as _PY
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "paquetes_yahoo.json")
        clave = ("grupo", os.path.getmtime(ruta))
    except Exception:  # noqa: BLE001
        return {}
    if clave in _CACHE_GRUPOS:
        return _CACHE_GRUPOS[clave]
    out = {}
    for tk, paq in (_PY.cargar()[0] or {}).items():
        est = (paq or {}).get("estados")
        if not est:
            continue
        try:
            fy, _ttm = _T._anios(est)
            _a, _t, s = series(est)
        except Exception:  # noqa: BLE001
            continue
        out[str(tk).upper()] = (familia(tk, est), _sector_de(tk), {k: _ultimo_fy(s.get(k) or {}, fy) for k in CLAVES_GRUPO})
    _CACHE_GRUPOS[clave] = out
    return out


def mediana_grupo(ticker, clave, fam):
    """(mediana, n, texto del grupo) de las demás empresas de la app del mismo sector (general) o del mismo tipo (financiera, reit); None si < MIN_GRUPO."""
    vg = valores_grupo()
    t = str(ticker).upper()
    sector = vg.get(t, (None, _sector_de(t)))[1] if t in vg else _sector_de(t)
    vals = []
    for otro, (f, sec, v) in vg.items():
        if otro == t or f != fam or v.get(clave) is None:
            continue
        if fam == "general" and (not sector or sec != sector):
            continue
        vals.append(v[clave])
    if len(vals) < MIN_GRUPO:
        return None
    vals.sort()
    n = len(vals)
    med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    grupo = {"financiera": "bancos, aseguradoras y financieras", "reit": "inmobiliarias (REITs)"}.get(fam, f"del sector {sector}")
    return med, n, grupo


def referencias(ticker, fam="general"):
    """{clave: (valor en fracción, texto del mouse)}.
    - Márgenes y ROE: valor de la industria de la empresa según Damodaran (se calcula igual que el nuestro). En financieras, solo margen neto y ROE.
    - El resto (ROIC, deuda neta/EBITDA, cobertura, liquidez, margen de flujo libre, payout, ROA…): mediana de las demás empresas de la app del mismo
      sector (o tipo), con la misma fórmula."""
    out = {}
    try:
        from data import damodaran as _D
        v = _D.valores(ticker)
    except Exception:  # noqa: BLE001
        v = None
    if v:
        for k, (ds, col) in _DAMODARAN.items():
            if fam == "financiera" and k not in ("mne", "roe"):
                continue
            x = _n((v.get(ds) or {}).get(col))
            # un margen bruto/operativo/EBITDA ≤ 0 o un ROE ≤ 0 de toda una industria no sirve como referencia (suele ser un dato raro de la
            # planilla, como el ROE de −0,2% de «Computers/Peripherals»): mejor sin línea que con una engañosa
            if x is None or (k in ("mbr", "mop", "mebitda", "roe") and x <= 0):
                continue
            out[k] = (x / 100, f"Industria: {v['industria']} ({v.get('region_txt', '')}; Damodaran, enero 2026). Suma las cifras de todas las empresas de la industria.")
    for k in CLAVES_GRUPO:
        if k in out:
            continue
        m = mediana_grupo(ticker, k, fam)
        if m:
            out[k] = (m[0], f"Mediana de {m[1]} empresas {m[2]} que sigue TodoCedears (último año fiscal; misma fórmula que la de esta empresa).")
    return out


def _escala(vals):
    """(divisor, texto) para montos: miles de millones si algún valor pasa los mil millones; si no, millones."""
    m = max((abs(v) for v in vals if v is not None), default=0)
    return (1e9, "miles de millones") if m >= 1e9 else (1e6, "millones")


def _fmt(v, tipo, div=1.0):
    if v is None:
        return "—"
    if tipo == "pct":
        x = v * 100
        return (f"{x:.1f}%" if abs(x) < 10 else f"{x:.0f}%").replace("-0%", "0%").replace("-0.0%", "0.0%")
    if tipo == "x":
        return f"{v:.1f}x"
    if tipo == "ps":
        return f"{v:.2f}"
    x = v / div
    if tipo == "acc" and abs(x) < 10:
        return f"{x:.2f}"
    return f"{x:,.1f}" if abs(x) < 100 else f"{x:,.0f}"


def tarjeta(clave, tit, txt, tipo, anios, ttm, s, moneda=None, ref=None, extra_txt=""):
    serie = s.get(clave) or {}
    vals = [(a, serie.get(a)) for a in anios]
    vals = [(a, v) for a, v in vals if not (a == ttm and v is None)]
    if not any(v is not None for _, v in vals):
        return ""
    nm = NOMBRES_MONEDA.get(moneda, moneda) if moneda and moneda != "USD" else "dólares"
    div, unidad = 1.0, ""
    if tipo == "$":
        div, esc = _escala([v for _, v in vals])
        unidad = f" ({esc} de {nm})"
    elif tipo == "acc":
        div, esc = _escala([v for _, v in vals])
        unidad = f" ({esc})"
    elif tipo == "ps":
        unidad = f" ({nm})"
    nums = [v / div for _, v in vals if v is not None] + ([ref[0]] if ref else [])
    lo, hi = min(0.0, min(nums)), max(0.0, max(nums))
    if hi == lo:
        hi = lo + 1
    rango = hi - lo
    H = 124

    def y(v):
        return H * (v - lo) / rango

    ult = vals[-1][0]
    barras = []
    for a, v in vals:
        etq = "Últimos<br>12 meses" if a == ttm else html.escape(_T._etq(a))
        if v is None:
            barras.append(f'<div class="ev-b"><div class="ev-v">—</div><div class="ev-c"></div><div class="ev-a">{etq}</div></div>')
            continue
        x = v / div
        h, z = abs(y(x) - y(0)), y(0)
        oscuro = a == ult and a == ttm
        color = "#f59e0b" if x < 0 else ("#0e7490" if oscuro else "#a5e3f3")
        barras.append(f'<div class="ev-b"><div class="ev-v{" ev-vu" if oscuro else ""}">{_fmt(v, tipo, div)}</div>'
                      f'<div class="ev-c"><div class="ev-bb" style="height:{max(h, 1.5):.0f}px;bottom:{(z - h) if x < 0 else z:.0f}px;background:{color}"></div></div>'
                      f'<div class="ev-a">{etq}</div></div>')
    linea = ""
    if ref:
        linea = (f'<div class="ev-ref" style="bottom:{y(ref[0]) + 34:.0f}px"><span title="{html.escape(ref[1], quote=True)}">'
                 f'{_fmt(ref[0], tipo)}</span></div>')
    cero = f'<div class="ev-cero" style="bottom:{y(0) + 34:.0f}px"></div>' if lo < 0 else ""
    return (f'<div class="ev-t"><h4>{html.escape(tit)}<small>{html.escape(unidad)}</small></h4><p>{html.escape(txt)}{html.escape(extra_txt)}</p>'
            f'<div class="ev-g">{linea}{cero}{"".join(barras)}</div></div>')


def graficos_html(est, clave, ticker=None):
    """La grilla de tarjetas de una subsolapa ('' si no hay datos), según el tipo de empresa."""
    if not est:
        return ""
    fam = familia(ticker, est) if ticker else "general"
    lista = TARJETAS[fam].get(clave)
    if not lista:
        return ""
    anios, ttm, s = series(est)
    if not anios:
        return ""
    refs = referencias(ticker, fam) if ticker else {}
    piezas = []
    for k, tit, txt, tipo in lista:
        extra = ""
        if k == "cob" and s.get("_sin_intereses"):
            ys = [str(a) for a in s["_sin_intereses"]]
            ys = ys[0] if len(ys) == 1 else ", ".join(ys[:-1]) + " y " + ys[-1]
            extra = f" En {ys} la fuente no trae el gasto por intereses por separado, así que no se puede calcular."
        piezas.append(tarjeta(k, tit, txt, tipo, anios, ttm, s, est.get("moneda"), refs.get(k), extra))
    t = "".join(piezas)
    aviso = f'<div class="fch-nota" style="margin:0 0 10px">{html.escape(AVISO_FAMILIA[fam])}</div>' if fam in AVISO_FAMILIA else ""
    return f'{aviso}<div class="ev-grid">{t}</div>' if t else aviso


CSS = """
.ev-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:0 0 14px}
.ev-t{background:#fff;border:1px solid #e3e8ee;border-radius:14px;padding:14px 14px 10px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.ev-t h4{margin:0 0 4px;font-size:16.5px;font-weight:700;text-align:center;color:#0f172a;padding:0!important}
.ev-t h4 small{display:block;font-size:12px;font-weight:400;color:#64748b}
.ev-t p{margin:0 0 8px;font-size:13.5px;line-height:1.38;color:#475569;text-align:justify;min-height:56px}
.ev-g{position:relative;display:flex;align-items:flex-end;gap:6px;height:192px;border-bottom:1px solid #cbd5e1}
.ev-b{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%}
.ev-v{font-size:12.5px;color:#475569;margin-bottom:3px;white-space:nowrap}
.ev-vu{font-weight:800;color:#0f172a}
.ev-c{position:relative;width:100%;height:124px}
.ev-bb{position:absolute;left:12%;right:12%;border-radius:4px 4px 0 0}
.ev-a{font-size:11.5px;color:#64748b;margin-top:4px;text-align:center;line-height:1.15;height:28px}
.ev-ref{position:absolute;left:0;right:0;border-top:2px dashed #94a3b8;z-index:1;pointer-events:none}
.ev-ref span{position:absolute;left:0;top:-16px;font-size:11px;color:#64748b;background:#fff;padding:0 3px;pointer-events:auto;cursor:help}
.ev-cero{position:absolute;left:0;right:0;border-top:1px solid #cbd5e1}
.mc-oscuro .ev-t{background:#111827;border-color:#1f2937}.mc-oscuro .ev-t h4{color:#e5e7eb}.mc-oscuro .ev-t p{color:#9ca3af}.mc-oscuro .ev-ref span{background:#111827}
@media (max-width:1100px){.ev-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){.ev-grid{grid-template-columns:1fr}}
"""
