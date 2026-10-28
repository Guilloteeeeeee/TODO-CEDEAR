"""Perfiles del Análisis Fundamental (v1.2.70): el formato del informe es SIEMPRE el mismo, pero según el tipo de empresa el programa elige solo (1) qué filas lleva la tabla
"Los números de un vistazo", (2) cómo se llama la sección de deuda y (3) la guía de análisis que se le pasa a quien redacta (qué mirar y qué NO mirar en ese tipo de negocio,
tomada de las listas de verificación por industria de Pat Dorsey, "Las cinco reglas para invertir en acciones con éxito").

El perfil sale de datos que ya están: sector e industria de Yahoo (data/fichas.json), la etapa del foso (data/foso.json) y los estados financieros. Nada se carga a mano.
Además hay dos "capas" que se suman a cualquier perfil: 'compounder' (foso amplio, retorno alto y sostenido) y 'ciclica'. Las funciones no tocan la red."""
from data import af_tablas as T

PERFILES = ("banco", "seguros", "mercados", "pagos", "reit", "utility", "energia", "materiales", "joven", "software", "hardware", "salud", "consumo", "general")

TIT_BALANCE = {
    "banco": "Capital y calidad del crédito",
    "seguros": "Solvencia y disciplina al asegurar",
    "mercados": "Solidez financiera y dependencia del mercado",
    "reit": "Deuda y vencimientos",
    "utility": "Deuda y regulación",
}
NOMBRE_PERFIL = {
    "banco": "Banco o financiera de crédito", "seguros": "Aseguradora", "mercados": "Mercados de capital, gestoras y bolsas", "pagos": "Pagos, datos y servicios financieros sin crédito",
    "reit": "Inmobiliaria cotizada (REIT)",
    "utility": "Servicios públicos", "energia": "Energía", "materiales": "Materiales y minería", "joven": "Empresa joven o con pérdidas", "software": "Software y plataformas",
    "hardware": "Hardware y semiconductores", "salud": "Salud", "consumo": "Consumo y comercio", "general": "Empresa general",
}

GUIAS = {
    "general": ("Empresa no financiera común. Mirá: ¿crece de forma pareja?, ¿el margen operativo sube o baja?, ¿la ganancia se convierte en caja (flujo libre)?, ¿el retorno sobre "
                "el capital (ROIC) es alto y sostenido?, ¿la deuda es cómoda?, ¿las acciones en circulación bajan (recompras) o suben (dilución)? Regla práctica de Dorsey: flujo libre "
                "mayor al 5 % de las ventas y acciones que no crecen más de 2 % por año son buenas señales."),
    "banco": ("BANCO o FINANCIERA DE CRÉDITO. No uses EBIT, EBITDA, flujo de caja ni cobertura de intereses: en un banco la deuda (los depósitos) es la materia prima. Un banco "
              "gana prestando más caro de lo que paga por el dinero (el margen de intermediación) más comisiones, y su negocio es gestionar tres riesgos: de crédito (que no te "
              "paguen), de liquidez y de tasa de interés. Mirá: resultado neto y ganancia por acción a lo largo de los años (¿estable en distintos ciclos?), ROE (referencia: por "
              "encima de 12 %), cuánto capital propio hay frente a los activos (activo/patrimonio: cuanto más bajo, más colchón), y si crece mucho más rápido que el sector (mala "
              "señal: suele significar que baja la calidad de los préstamos). Dorsey: preferí bancos conservadores, con buen capital y provisiones prudentes; comparar precio/valor "
              "contable entre bancos parecidos evita pagar de más. Los datos de calidad de cartera (morosidad, provisiones) NO están en el bloque: si los mencionás, decí que no "
              "los tenés."),
    "seguros": ("ASEGURADORA. No uses EBIT, EBITDA ni cobertura de intereses. Una aseguradora cobra primas hoy y paga siniestros después, e invierte ese dinero mientras tanto "
                "(el 'float'). La clave es la disciplina: que las primas cobradas superen los siniestros más los gastos. Mirá resultado neto estable en distintos años, ROE, "
                "patrimonio creciente y que no crezca mucho más rápido que el sector (Dorsey: ojo con el que crece muy por encima del promedio, salvo que sea por compras). "
                "Las cifras técnicas (ratio combinado, reservas) NO están en el bloque: no las inventes."),
    "mercados": ("MERCADOS DE CAPITAL, GESTORAS, BROKERS Y BOLSAS. No uses EBITDA ni cobertura de intereses como en una industrial. Su negocio vive de comisiones sobre activos "
                 "gestionados o volumen operado, y por eso sus resultados siguen al mercado. Mirá si los ingresos son estables o dependen de años buenos de mercado, ROE, margen "
                 "operativo, y cuán 'pegajosa' es su base de clientes (activos que no se van fácil dan estabilidad, según Dorsey). Las bolsas y plataformas de datos pueden tener "
                 "efecto de red y fosos anchos."),
    "pagos": ("PAGOS, DATOS Y SERVICIOS FINANCIEROS SIN CRÉDITO (redes de pago, calificadoras, datos financieros, corredores de seguros, procesadores). No son bancos: no prestan "
              "con su propio balance, así que podés usar márgenes, flujo libre y ROIC como en una empresa común. Su ventaja suele ser el efecto de red (más comercios y clientes "
              "hacen la red más valiosa para todos) o los costos de cambio, y por eso muchas tienen márgenes muy altos. Mirá si el volumen crece de forma pareja, si el margen "
              "operativo se sostiene, y el riesgo regulatorio (comisiones, competencia de nuevas plataformas). Si el negocio depende del precio de cripto o del humor del mercado, "
              "decilo: los resultados serán muy irregulares."),
    "reit": ("INMOBILIARIA COTIZADA (REIT). Reparte casi toda su ganancia como dividendo, así que no puede reinvertir mucho: crece comprando propiedades con deuda y capital "
             "nuevo. La ganancia neta contable subestima su caja real (por las depreciaciones), y el indicador que se usa en el sector, FFO, NO está en el bloque: usá el flujo "
             "operativo como aproximación y decilo. Mirá: estabilidad de ingresos y alquileres, flujo operativo contra dividendos pagados (¿alcanza?), deuda sobre EBITDA y "
             "vencimientos, y si emite acciones nuevas (dilución). La deuda alta es normal en el sector; lo importante es que sea manejable."),
    "utility": ("SERVICIOS PÚBLICOS. Los regulados son casi monopolios y por eso suelen tener foso, pero el regulador limita lo que pueden ganar y puede cambiar las reglas. "
                "Tienen mucha deuda e inversiones constantes (CAPEX alto): es normal, no la juzgues como una industrial. Mirá: que la deuda no suba más rápido que el negocio, que "
                "el flujo operativo cubra el dividendo y las inversiones, y el riesgo regulatorio y ambiental. Los generadores sin regulación (productores independientes) son más "
                "cíclicos y riesgosos."),
    "energia": ("ENERGÍA (petróleo y gas). Sus ganancias dependen del precio de las materias primas: son cíclicas, así que juzgá el ciclo completo y no un solo año. Dorsey: "
                "conviene mirar cuando los precios están bajos y no cuando son titular; la escala es casi la única ventaja competitiva real; los balances sólidos (poca deuda) "
                "son lo que permite pasar las malas épocas. Mirá márgenes y flujo libre en años buenos y malos, deuda y si paga dividendos y recompra sin endeudarse."),
    "materiales": ("MATERIALES Y MINERÍA. Es un negocio de materias primas: precio fijado por el mercado, ganancias cíclicas. Ganan las empresas de menor costo y mayor escala. "
                   "Juzgá el ciclo completo; un mal año con balance sólido no es lo mismo que un mal año con deuda. Mirá márgenes y flujo libre a lo largo de los años, deuda y CAPEX."),
    "joven": ("EMPRESA JOVEN O CON PÉRDIDAS. No la juzgues por la ganancia (no hay o es chica). Mirá: ritmo de crecimiento de ingresos, si el margen bruto es alto y estable, "
              "si las pérdidas se achican, cuánta caja tiene frente a lo que quema por año (¿cuántos años aguanta?) y si emite acciones nuevas (dilución). Dorsey advierte que "
              "invertir en empresas que nunca ganaron plata se parece más a una lotería que a un análisis: sé exigente y decí con claridad si todavía no demostró que su "
              "modelo funciona."),
    "software": ("SOFTWARE Y PLATAFORMAS. La economía del software es de las mejores (márgenes altos, poco capital), pero la tecnología por sí sola es una de las ventajas menos "
                 "duraderas: los fosos sostenibles son los costos de cambio (al cliente le cuesta irse) y los efectos de red. Mirá crecimiento de ingresos, margen operativo en "
                 "expansión, caja y cuánta compensación en acciones diluye al accionista."),
    "hardware": ("HARDWARE Y SEMICONDUCTORES. Crecen rápido pero compiten duro y la demanda es cíclica. Dorsey: la tecnología sola no es una ventaja sostenible; buscá empresas con foso "
                 "(costos bajos, activos intangibles, costos de cambio o efecto de red). Mirá márgenes en el ciclo completo, inversión en investigación y capital, y cuánto "
                 "depende de pocos clientes."),
    "salud": ("SALUD. En farmacéuticas y biotecnológicas el motor son las patentes y los productos en desarrollo: mirá cuánto de las ventas depende de pocos productos y cuándo "
              "vencen sus patentes, y si tiene caja o flujo para financiar el próximo ciclo de desarrollo. Los dispositivos médicos y las herramientas para laboratorios suelen "
              "tener fosos más estables (costos de cambio). Dorsey: con biotecnológicas jóvenes es más fácil perder que ganar si no se entiende la tecnología."),
    "consumo": ("CONSUMO Y COMERCIO. Las marcas fuertes dan poder de fijar precios y fidelidad; en el comercio minorista los costos de cambio son bajos y los conceptos suelen "
                "fracasar a largo plazo, salvo que la tienda tenga una ventaja clara (costos, escala, lealtad). Mirá márgenes estables, rotación de inventario, y cuidado con los "
                "alquileres y otras obligaciones que no aparecen como deuda."),
}
CAPA_COMPOUNDER = ("CAPA 'COMPOUNDER' (empresa de calidad que compone valor): tiene foso amplio y un retorno sobre el capital alto y sostenido. Lo que importa es cuántos años más "
                   "puede reinvertir a esos retornos, si el flujo libre por acción crece más rápido que los ingresos y si recompra acciones con criterio. El riesgo típico: que el "
                   "mercado ya pague un precio muy alto por esa calidad (eso se mira en la solapa Valuación).")
CAPA_CICLICA = ("CAPA CÍCLICA: sus resultados suben y bajan con la economía o con el precio de una materia prima. No te alarmes por un mal año si el balance es sólido, ni te "
                "entusiasmes con un año récord: preguntate cuánto gana en un año normal.")


# Puntos del detalle (data/af_tablas.PUNTOS) que ve quien redacta según el perfil: un banco no se juzga con EBIT, flujo de caja ni cobertura de intereses.
CLAVES_DETALLE = {"banco": ("ingresos", "eps", "acciones", "roic"), "seguros": ("ingresos", "eps", "acciones", "roic"), "mercados": ("ingresos", "ebit", "eps", "acciones", "roic")}


# Casos que el sector/industria de Yahoo no resuelve bien (el criterio sigue siendo el tipo de negocio real).
OVERRIDE = {"COIN": "mercados", "FISV": "pagos", "FI": "pagos"}


def perfil(sector, industria, etapa=None, estados=None, ticker=None, sector_app=None):
    """Perfil de análisis ('banco', 'reit', ... 'general') a partir del sector e industria de Yahoo, la etapa y los estados.
    `sector_app` es el sector de la app (por ejemplo 'Pagos y datos'): las redes de pago no se analizan como bancos aunque Yahoo las llame 'Credit Services'."""
    s, i = str(sector or ""), str(industria or "")
    if ticker and str(ticker).upper() in OVERRIDE:
        return OVERRIDE[str(ticker).upper()]
    if s == "Financial Services":
        if sector_app == "Pagos y datos":
            return "pagos"
        if "Bank" in i or "Credit" in i:
            return "banco"
        if "Insurance" in i:
            return "seguros"
        return "mercados"
    if s == "Real Estate":
        return "reit"
    if s == "Utilities":
        return "utility"
    if s == "Energy":
        return "energia"
    if s == "Basic Materials":
        return "materiales"
    if etapa == "Con pérdidas y creciendo":
        return "joven"
    ebit = T._serie(estados, "resultados", "Resultado operativo") if estados else {}
    fy, ttm = T._anios(estados) if estados else ([], None)
    ult = ebit.get(ttm) if ttm and ebit.get(ttm) is not None else (ebit.get(fy[-1]) if fy else None)
    if ult is not None and ult < 0:
        return "joven"
    if s == "Technology":
        if "Software" in i or "Internet" in i or "Information" in i:
            return "software"
        return "hardware"
    if s == "Healthcare":
        return "salud"
    if s in ("Consumer Cyclical", "Consumer Defensive"):
        return "consumo"
    return "general"


def capas(perfil_, etapa=None, foso=None, estados=None):
    """Capas extra: 'compounder' (foso amplio y ROIC promedio de 15 % o más, no financieras) y 'ciclica' (etapa cíclica o perfil de materias primas)."""
    out = []
    if perfil_ not in ("banco", "seguros", "mercados", "reit", "utility", "joven") and foso == "Amplio" and estados:
        roic = T._serie(estados, "ratios", "Retorno sobre el capital invertido (ROIC)")
        vals = [v for v in roic.values() if v is not None]
        if len(vals) >= 3 and sum(vals) / len(vals) >= 0.15:
            out.append("compounder")
    if etapa == "Cíclica o de materias primas" or perfil_ in ("energia", "materiales"):
        out.append("ciclica")
    return out


def titulo_balance(perfil_):
    return TIT_BALANCE.get(perfil_, "Deuda y solidez financiera")


def guia(perfil_, capas_=()):
    """Texto de guía de análisis (perfil + capas) que se agrega al bloque de datos."""
    g = [GUIAS.get(perfil_, GUIAS["general"])]
    if "compounder" in capas_:
        g.append(CAPA_COMPOUNDER)
    if "ciclica" in capas_:
        g.append(CAPA_CICLICA)
    return "\n".join(g)


# --- tabla "Los números de un vistazo" -------------------------------------------------------------------------------------------

def _filas(perfil_):
    """[(rótulo, clave)] de la tabla según el perfil. Las claves las resuelve _serie_de()."""
    base = {
        "banco": ["ingresos", "neto", "eps", "roe", "patrimonio", "act_pat"],
        "seguros": ["ingresos", "neto", "eps", "roe", "patrimonio", "act_pat"],
        "mercados": ["ingresos", "crec", "m_op", "neto", "roe", "act_pat"],
        "pagos": ["ingresos", "crec", "m_op", "eps", "fcf", "roic", "acciones"],
        "reit": ["ingresos", "fco", "neto", "divs", "dn_ebitda", "deuda_pat"],
        "utility": ["ingresos", "m_op", "fco", "capex", "dn_ebitda", "divs"],
        "energia": ["ingresos", "m_op", "fcf", "roic", "dn_ebitda"],
        "materiales": ["ingresos", "m_op", "fcf", "roic", "dn_ebitda"],
        "joven": ["ingresos", "crec", "m_bruto", "m_op", "fcf", "caja", "acciones"],
        "software": ["ingresos", "crec", "m_op", "eps", "fcf", "roic", "acciones"],
        "hardware": ["ingresos", "crec", "m_op", "eps", "fcf", "roic", "dn_ebitda"],
        "salud": ["ingresos", "crec", "m_op", "eps", "fcf", "roic", "dn_ebitda"],
        "consumo": ["ingresos", "crec", "m_op", "eps", "fcf", "roic", "dn_ebitda"],
        "general": ["ingresos", "crec", "m_op", "eps", "fcf", "roic", "dn_ebitda"],
    }
    return base.get(perfil_, base["general"])


_ROT = {
    "ingresos": ("Ingresos (M)", "m"), "crec": ("Crecimiento de ingresos", "var"), "m_bruto": ("Margen bruto", "pct"), "m_op": ("Margen operativo", "pct"),
    "neto": ("Resultado neto (M)", "m"), "eps": ("Ganancia por acción", "eps"), "fcf": ("Flujo libre de caja (M)", "m"), "fco": ("Flujo operativo (M)", "m"),
    "capex": ("CAPEX (M)", "m"), "divs": ("Dividendos pagados (M)", "m"), "roic": ("ROIC", "pct"), "roe": ("ROE", "pct"), "patrimonio": ("Patrimonio neto (M)", "m"),
    "act_pat": ("Activo total / Patrimonio", "x"), "dn_ebitda": ("Deuda neta / EBITDA", "x"), "deuda_pat": ("Deuda total / Patrimonio", "x"), "caja": ("Caja (M)", "m"),
    "acciones": ("Acciones diluidas (M)", "m"),
}


def _serie_de(estados, clave, fy):
    S = lambda g, r: T._serie(estados, g, r)  # noqa: E731
    ab = lambda d: {k: (abs(v) if v is not None else None) for k, v in d.items()}  # noqa: E731
    if clave == "ingresos":
        return S("resultados", "Ingresos")
    if clave == "crec":
        s = S("resultados", "Ingresos")
        return {a: T._var(s, fy, a) for a in fy}
    if clave == "m_bruto":
        return S("ratios", "Margen bruto")
    if clave == "m_op":
        return S("ratios", "Margen operativo")
    if clave == "neto":
        return S("resultados", "Resultado neto")
    if clave == "eps":
        return S("resultados", "Ganancia por acción (diluida)")
    if clave == "fcf":
        return S("flujo", "Flujo de efectivo libre")
    if clave == "fco":
        return S("flujo", "Flujo de efectivo operativo")
    if clave == "capex":
        return ab(S("flujo", "Inversión en activos fijos (CAPEX)"))
    if clave == "divs":
        return ab(S("flujo", "Dividendos pagados"))
    if clave == "roic":
        return S("ratios", "Retorno sobre el capital invertido (ROIC)")
    if clave == "roe":
        return S("ratios", "Retorno sobre el patrimonio (ROE)")
    if clave == "patrimonio":
        return S("balance", "Patrimonio neto")
    if clave == "caja":
        return S("balance", "Caja e inversiones de corto plazo")
    if clave == "acciones":
        return S("resultados", "Acciones promedio (diluidas)")
    if clave == "act_pat":
        a, p = S("balance", "Activo total"), S("balance", "Patrimonio neto")
        return {k: (a[k] / p[k] if a.get(k) is not None and p.get(k) not in (None, 0) else None) for k in a}
    if clave == "deuda_pat":
        return S("ratios", "Deuda total / Patrimonio")
    if clave == "dn_ebitda":
        d, c, e = S("balance", "Deuda total"), S("balance", "Caja e inversiones de corto plazo"), S("resultados", "EBITDA")
        dn = S("balance", "Deuda neta") or {k: (d[k] - c[k] if d.get(k) is not None and c.get(k) is not None else None) for k in d}
        return {k: (dn[k] / e[k] if dn.get(k) is not None and e.get(k) not in (None, 0) and e[k] > 0 else None) for k in dn}
    return {}


def vistazo(estados, perfil_):
    """{'cols': ['Año', ...años...], 'filas': [[rótulo, celdas...]]} con las filas del perfil que tienen algún dato, o None. Años de menor a mayor y TTM al final."""
    fy, ttm = T._anios(estados)
    años = fy + ([ttm] if ttm else [])
    if not años:
        return None
    filas = []
    for clave in _filas(perfil_):
        rot, tipo = _ROT[clave]
        s = _serie_de(estados, clave, fy)
        cel = [T._f(s.get(a), tipo) for a in años]
        if any(c != "–" for c in cel):
            filas.append([rot] + cel)
    if not filas:
        return None
    return {"cols": ["Año"] + [T._etq(a) for a in años], "filas": filas}


def vistazo_texto(estados, perfil_):
    v = vistazo(estados, perfil_)
    if not v:
        return "(sin datos)"
    mon = T.moneda(estados)
    return f"(Montos en millones{' de ' + mon if mon else ''}; TTM = últimos 12 meses; \"–\" = no disponible)\n" + " | ".join(v["cols"]) + "\n" + "\n".join(" | ".join(f) for f in v["filas"])


def vistazo_html(v):
    import html
    cab = "".join(f"<th>{html.escape(c)}</th>" for c in v["cols"])
    cuerpo = "".join("<tr><th scope='row'>" + html.escape(f[0]) + "</th>" + "".join(f"<td>{html.escape(x)}</td>" for x in f[1:]) + "</tr>" for f in v["filas"])
    return f'<div class="af-tw"><table class="af-tb af-vz"><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table></div>'
