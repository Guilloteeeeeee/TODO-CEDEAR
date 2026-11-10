"""
v1.5.58: SCORE DE SEGURIDAD DEL DIVIDENDO (0 a 100). Método de Guille, versión 0.2:
- método aprobado el 10/11/2026 (documento «Score de Seguridad del Dividendo — Metodología», Geraldine Weiss + Simply Safe Dividends);
- más los 3 ajustes aprobados el 10/11/2026 después de la primera calibración contra SSD:
  1) utilities y REITs: cobertura de intereses con EBITDA en lugar de EBIT;
  2) payout sobre flujo de caja libre: el mejor entre 3 años y últimos 12 meses;
  3) payout sobre ganancias: el mejor entre últimos 12 meses y último año fiscal.
- regla de datos: si falta el dato de los últimos 12 meses se usa el último año fiscal; si falta una variable, se saca y su pilar se
  reparte entre las que quedan (preferencia de Guille: «descartarla y ponderar con las que sí funcionan»).
- regla de bordes: los valores se redondean a 2 decimales; donde menos es mejor, el borde va con la franja de más puntos (payout de 60% = 17);
  donde más es mejor, con la franja que arranca en él (cobertura de 3x = A-).

NO se muestra en pantalla el método ni los pesos (regla de Guille): la app solo muestra el score, la categoría y la conclusión.

Pilares (máximos): 1 Cobertura del dividendo 35 · 2 Solidez del balance 25 · 3 Historial del dividendo 20 · 4 Estabilidad del negocio 15 ·
5 Tendencia 5. Topes: dividendo > ganancia y > flujo libre (12 meses) → máx. 40 · cobertura < 1,5x → máx. 40 · pérdida y flujo libre de 3 años
≤ 0 → máx. 20 · rendimiento ≥ 2 × su mediana de 5 años → −10.
"""
import datetime as _dt
from statistics import median

from data import damodaran as D

CATEGORIAS = ((20, "Muy inseguro", "Alto riesgo de recorte"), (40, "Inseguro", "Riesgo elevado de recorte"),
              (60, "Al límite", "Riesgo moderado de recorte"), (80, "Seguro", "Poco probable que se recorte"),
              (100, "Muy seguro", "Muy poco probable que se recorte"))
COLORES = {"Muy inseguro": "#c62828", "Inseguro": "#e8a317", "Al límite": "#b5d35a", "Seguro": "#4e8a17", "Muy seguro": "#2d5a12"}

MAX = {1: 35, 2: 25, 3: 20, 4: 15, 5: 5}
# franjas "menos es mejor": [(tope incluido, puntos)]; lo que pasa el último tope da 0
ESC_FCF = ((50, 20), (60, 17), (70, 14), (80, 10), (90, 6), (100, 3))
ESC_EPS = ((50, 15), (60, 12), (75, 9), (90, 5), (100, 2))
ESC_UR_PAYOUT = ((75, 35), (85, 27), (95, 18), (100, 8))          # utilities (ganancias) y REITs (FFO): todo el pilar 1
ESC_DEUDA = ((1, 9), (2, 7), (3, 5), (4, 2))
ESC_DEUDA_UR = ((4.5, 9), (5.5, 7), (6.5, 5), (7.5, 2))            # utilities y REITs: la general corrida 3,5x
ESC_NDC = ((50, 4), (75, 2))
PTS_RATING = {"Aaa/AAA": 12, "Aa2/AA": 12, "A1/A+": 10, "A2/A": 10, "A3/A-": 8, "Baa2/BBB": 6, "Ba1/BB+": 3, "Ba2/BB": 3}
CASI_NULO_NDC = 90.0          # patrimonio «casi nulo»: la deuda neta es 90% o más de deuda neta + patrimonio
# v1.5.62 (Guille, 10/11/2026: «SÍ, DE ACUERDO CON TODO»; con pérdida «entrarían también»): excepción del payout sobre ganancias. Si los
# analistas esperan para el año en curso una ganancia de 1,5 veces o más la contable (o la contable es pérdida), el payout se mide contra la
# estimada. Resguardos: al menos 5 analistas, estimación de hace 130 días o menos, y el dividendo cubierto por el flujo de caja libre (payout
# de flujo de 100% o menos). Solo empresas generales: bancos, REITs y utilities quedan afuera (en ellos no se mide el flujo libre; en Yahoo
# los analistas de los REIT no estiman FFO). Los topes siguen mirando la ganancia contable.
SALTO_ANALISTAS = 1.5
MIN_ANALISTAS = 5
VIGENCIA_ESTIMACION = 130     # días: las estimaciones se bajan una vez por trimestre, después de los balances
REDONDEO = 0.001             # v1.5.61: una baja por pago menor a esto es redondeo de Yahoo (montos viejos ajustados por splits, a 3 decimales)
CHICA_MCAP = 1_000_000_000    # v1.5.61 (Guille, 10/11/2026: «APLIQUEMOS DESDE 1 B»): por debajo de US$1.000 millones de capitalización la
                              # cobertura de intereses se lee con la tabla de Damodaran para empresas chicas o riesgosas

UTILITIES, REITS, BANCOS = {"Utilities"}, {"REITs"}, {"Bancos y seguros"}
# supersectores de Morningstar (decisión de Guille, 10/11/2026: «así, sencillo y sin controversias»), por grupo de la app
SUPERSECTOR = {"Consumo Básico": "Defensivo", "Utilities": "Defensivo", "Salud": "Defensivo",
               "Semiconductores": "Sensible", "Software y nube": "Sensible", "Hardware y servicios TI": "Sensible", "Comunicación": "Sensible",
               "Telecomunicaciones": "Sensible", "Industrial": "Sensible", "Energía": "Sensible",
               "Materiales Básicos": "Cíclico", "REITs": "Cíclico", "Bancos y seguros": "Cíclico", "Pagos y datos": "Cíclico",
               "Consumo Discrecional": "Cíclico"}
PTS_SUPER = {"Defensivo": 5, "Sensible": 3, "Cíclico": 0}

EPS, OPI, EBITDA, INT = "Ganancia por acción (diluida)", "Resultado operativo", "EBITDA", "Gasto por intereses"
FCF, DIVP, ND, PAT, DT = "Flujo de efectivo libre", "Dividendos pagados", "Deuda neta", "Patrimonio neto", "Deuda total"


# ---------------------------------------------------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------------------------------------------------
def r2(x):
    return None if x is None else round(float(x) + 0.0, 2)


def menos_es_mejor(x, bandas):
    x = r2(x)
    for tope, pts in bandas:
        if x <= tope:
            return pts
    return 0


def categoria(score):
    if score is None:
        return None, None
    for tope, nombre, frase in CATEGORIAS:
        if score <= tope:
            return nombre, frase
    return CATEGORIAS[-1][1], CATEGORIAS[-1][2]


def _n(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def serie(estados, rot):
    """{año: valor} de una fila de los estados (formato paquetes_yahoo / estados_completos); el TTM queda con la clave "TTM"."""
    for g in ("resultados", "balance", "flujo", "ratios"):
        t = (estados or {}).get(g) or {}
        for fila in t.get("filas", []):
            if fila and fila[0] == rot:
                return {("TTM" if isinstance(a, str) else int(a)): _n(v) for a, v in zip(t.get("anios", []), fila[1])}
    return {}


def _fy(s):
    return sorted((a for a in s if a != "TTM" and s[a] is not None), reverse=True)


def ultimo(s):
    """Dato de los últimos 12 meses; si falta, el del último año fiscal (regla de datos). -> (valor, "TTM"|año|None)."""
    if s.get("TTM") is not None:
        return s["TTM"], "TTM"
    fy = _fy(s)
    return (s[fy[0]], fy[0]) if fy else (None, None)


def _pct(x):
    return f"{x:.0f}%".replace(".", ",")


def _veces(x):
    """2,5 · 13 (de 10 para arriba, entero: misma regla que los puntos de corte de la app)."""
    return f"{x:.0f}" if abs(x) >= 10 else f"{x:.1f}".replace(".", ",")


def _anios_txt(n):
    return "1 año" if n == 1 else f"{n} años"


# ---------------------------------------------------------------------------------------------------------------------
# historial de dividendos (data/historico/dividendos.json: [[fecha ISO, monto por acción ajustado por splits]])
# ---------------------------------------------------------------------------------------------------------------------
def _habitual(c):
    """Cantidad de pagos en un año -> frecuencia habitual (1, 2, 4 o 12). Mensual solo con 10 pagos o más; si no, la más cercana entre 1, 2 y 4
    (en empate la mayor: 3 pagos = trimestral con uno corrido; 5 a 9 = trimestral con pagos variables o extraordinarios, como ConocoPhillips)."""
    if c >= 10:
        return 12
    return min((1, 2, 4), key=lambda x: (abs(x - c), -x))


def analizar_dividendos(pagos, hoy=None, sigue_pagando=False):
    """Lee la historia de pagos y devuelve años sin recortar, años pagando, aumentos en los últimos 12 años y qué hizo en 2008-09 y 2020.
    - «Dividendo anual regular» de cada año = mediana de sus pagos × pagos habituales por año (la mediana no se mueve por un dividendo
      extraordinario suelto, que según el método no cuenta).
    - Recorte: el dividendo regular baja más de 1%, o la empresa deja de pagar (suspensión: pagó menos veces de lo habitual y lo cobrado en
      ese año y el siguiente es menos del 90% de los dos anteriores; así un pago corrido de diciembre a enero no cuenta como recorte).
    - El año en curso no cuenta como año completo, pero si en él el dividendo bajó o se suspendió, los años sin recortar quedan en 0.
    - v1.5.61: sigue_pagando=True (el cache dice que hoy paga dividendo): si en el historial faltan los últimos pagos (pasa con algunos ADR en
      Yahoo), no se toma como suspensión; queda "historial_incompleto"."""
    hoy = hoy or _dt.date.today()
    por_anio = {}
    for f, m in pagos or []:
        m = _n(m)
        if m is None or m <= 0:
            continue
        por_anio.setdefault(int(str(f)[:4]), []).append((str(f)[:10], m))
    if not por_anio:
        return None
    actual = hoy.year
    completos = sorted(a for a in por_anio if a < actual)
    if not completos:
        return None
    ultimos = [len(por_anio[a]) for a in completos[-10:]]
    frec = max(set(ultimos), key=lambda c: (ultimos.count(c), c))
    frec = _habitual(frec)
    primero, ultimo_c = completos[0], completos[-1]
    anios = list(range(primero, ultimo_c + 1))
    n = {a: len(por_anio.get(a, [])) for a in anios}
    suma = {a: sum(m for _, m in por_anio.get(a, [])) for a in anios}

    def frec_de(a):
        # v1.5.61: frecuencia habitual DE ESE AÑO (la más repetida entre el año anterior, ese y el siguiente, solo años con pagos; en empate,
        # la del propio año: un extraordinario en el año vecino no cambia la lectura de National Grid, que paga 2 veces por año). Así un
        # cambio de pago anual a trimestral (McDonald's en 2008: 1 pago de 1,50 → 4 de 0,375) no se lee como recorte.
        cs = [n[x] for x in (a - 1, a, a + 1) if n.get(x)]
        if not cs:
            return frec
        c = max(set(cs), key=lambda k: (cs.count(k), k == n[a], k))     # en empate, la cantidad del propio año
        f = _habitual(c)
        if f < frec:
            # menos pagos que lo habitual: es cambio de frecuencia solo si lo cobrado en el año no cae más de 25% contra los dos anteriores;
            # si cae, es una suspensión (Ford 2020-21: un pago suelto por año) y se sigue leyendo con la frecuencia habitual
            prev = [suma[x] for x in (a - 1, a - 2) if x in suma]
            if n[a] == 0 or (prev and suma[a] < max(prev) * 0.75):
                return frec
        return f

    f_anio = {a: frec_de(a) for a in anios}
    tasa = {a: (median(m for _, m in por_anio[a]) * f_anio[a] if n[a] else 0.0) for a in anios}

    todos = sorted(p for a in por_anio for p in por_anio[a])
    fechas = [_dt.date.fromisoformat(f) for f, _ in todos]

    def recorte(a):
        if a - 1 not in tasa or n.get(a - 1, 0) == 0:
            return False               # antes no pagaba: no hay recorte posible
        if n[a] == 0:
            return True                # no pagó en todo el año: suspensión
        if tasa[a] < tasa[a - 1] * 0.99 and (tasa[a - 1] - tasa[a]) / f_anio[a] > REDONDEO:
            # bajó el dividendo regular (más que el redondeo de Yahoo en los montos viejos ajustados por splits: Texas Instruments 2003,
            # 0,0215 → 0,021 por pago, no es recorte). v1.5.61: si el año siguiente vuelve a estar a la altura del anterior, fue el año del cambio de
            # frecuencia (Accenture 2019: último pago semestral de 1,46 y primero trimestral de 0,80) y no un recorte
            sig = tasa.get(a + 1) if a + 1 in tasa and n.get(a + 1) else None
            cambio = len({f_anio.get(a - 1), f_anio[a], f_anio.get(a + 1, f_anio[a])}) > 1     # solo si cambia la frecuencia alrededor
            return not cambio or sig is None or sig < tasa[a - 1] * 0.99
        if n[a] < f_anio[a]:
            # pagó menos veces de lo habitual: si el pago que falta se corrió a pocos días del año (diciembre -> enero), no es recorte
            desde, hasta = _dt.date(a, 1, 1) - _dt.timedelta(days=45), _dt.date(a, 12, 31) + _dt.timedelta(days=45)
            if sum(1 for f in fechas if desde <= f <= hasta) >= f_anio[a]:
                return False
            return suma[a] < suma[a - 1] * 0.75
        return False

    rec = {a: recorte(a) for a in anios}
    # año en curso: si el dividendo bajó o dejó de pagarse, los años sin recortar quedan en 0
    en_curso = False
    f_ult = f_anio[ultimo_c]           # v1.5.61: el año en curso se lee con la frecuencia del último año completo
    if por_anio.get(actual):
        if median(m for _, m in todos[-f_ult:]) * f_ult < tasa[ultimo_c] * 0.99:
            en_curso = True
    dejo = (hoy - fechas[-1]).days > 365 / f_ult * 1.6 + 15
    incompleto = bool(dejo and sigue_pagando)
    if incompleto:
        dejo = False
    en_curso = en_curso or dejo
    sin_recorte = 0
    if not en_curso:
        for a in reversed(anios):
            if n[a] == 0 or rec[a]:
                break                  # el año del recorte (o sin pagos) no cuenta
            sin_recorte += 1
    pagando = 0
    if not dejo:
        for a in reversed(anios):
            if n[a] == 0:
                break
            pagando += 1
    ventana = [a for a in range(ultimo_c - 11, ultimo_c + 1) if a in tasa and a - 1 in tasa]
    aumentos = sum(1 for a in ventana if n[a] and tasa[a] > tasa[a - 1] * 1.001)

    def crisis(anios_c, previo):
        if n.get(previo, 0) == 0 and all(n.get(a, 0) == 0 for a in anios_c):
            return "no_pagaba"
        if previo not in tasa or n.get(previo, 0) == 0:
            return "no_pagaba"
        return "recorto" if any(rec.get(a) for a in anios_c) else "sin_recorte"

    return {"anios_sin_recorte": sin_recorte, "anios_pagando": pagando, "aumentos_12": aumentos, "frecuencia": frec,
            "crisis_0809": crisis((2008, 2009), 2007), "crisis_2020": crisis((2020, 2021), 2019), "recorte_en_curso": en_curso,
            "ultimo_completo": ultimo_c, "historial_incompleto": incompleto, "ultimo_pago": todos[-1][0],
            "tasa": {a: round(t, 4) for a, t in tasa.items()}}


def estimacion_vigente(e):
    """La estimación de analistas de la entrada, si no tiene más de VIGENCIA_ESTIMACION días (contra e["hoy"] o hoy). Si no, None."""
    est = e.get("estimacion") or None
    if not est:
        return None
    f = est.get("fecha")
    if f:
        try:
            ref = e.get("hoy") or _dt.date.today()
            ref = _dt.date.fromisoformat(str(ref)[:10]) if not isinstance(ref, _dt.date) else ref
            if (ref - _dt.date.fromisoformat(str(f)[:10])).days > VIGENCIA_ESTIMACION:
                return None
        except ValueError:
            return None
    return est


def entrada(row, estados, historial=None, estimacion=None, grupo=None):
    """Arma la entrada de calcular() con una fila del cache (data/cache_datos.json) y los estados de la empresa."""
    if grupo is None:
        from config.sectors import TICKER_TO_SECTOR
        grupo = TICKER_TO_SECTOR.get(row.get("ticker"))
    return {"ticker": row.get("ticker"), "grupo": grupo, "pais": row.get("pais"), "dividendo_anual": row.get("annual_dividend"),
            "precio": row.get("precio_actual"), "p_ffo": row.get("p_ffo_actual"), "dy": row.get("dividend_yield_actual"),
            "dy_mediana": row.get("dividend_yield_mediana"), "market_cap": row.get("market_cap"), "estados": estados, "historial": historial,
            "estimacion": estimacion}


# ---------------------------------------------------------------------------------------------------------------------
# el score
# ---------------------------------------------------------------------------------------------------------------------
def calcular(e):
    """e = {"ticker", "grupo" (grupo de la app: config.sectors.TICKER_TO_SECTOR), "pais", "dividendo_anual", "precio", "p_ffo",
            "dy", "dy_mediana", "market_cap" (US$; < 1.000 millones = tabla de empresas chicas), "estados" (con hasta 13 años: historico.estados_completos), "historial" (analizar_dividendos o None),
            "estimacion" ({"actual": EPS estimado año en curso, "proximo": EPS estimado año próximo, "analistas", "fecha"} o None),
            "hoy" (fecha del cálculo, para la vigencia de la estimación; por defecto hoy)}
    -> {"score", "categoria", "frase", "color", "pilares": {n: [pts, máx]}, "variables": [...], "topes": [...], "notas": [...], "conclusion"}"""
    tk, grupo = e.get("ticker", ""), e.get("grupo") or ""
    dpa = _n(e.get("dividendo_anual"))
    res = {"ticker": tk, "score": None, "categoria": None, "frase": None, "color": None, "pilares": {}, "variables": [], "topes": [],
           "notas": [], "conclusion": None}
    if not dpa or dpa <= 0:
        res["notas"].append("no paga dividendo")
        return res
    est = e.get("estados") or {}
    util, reit, banco = grupo in UTILITIES, grupo in REITS, grupo in BANCOS
    variable_ext = (e.get("pais") or "United States") != "United States"
    s = {k: serie(est, k) for k in (EPS, OPI, EBITDA, INT, FCF, DIVP, ND, PAT, DT)}
    ratio_nd = serie(est, "Deuda neta / EBITDA")
    V = []          # variables: dict(clave, pilar, pts, max, valor, texto_valor)

    def var(clave, pilar, pts, mx, valor=None, **extra):
        V.append({"clave": clave, "pilar": pilar, "pts": None if pts is None else float(pts), "max": mx, "valor": valor, **extra})

    eps_u, _ = ultimo(s[EPS])
    fy_eps = _fy(s[EPS])
    eps_fy = s[EPS][fy_eps[0]] if fy_eps else None
    # -------- pilar 1: cobertura del dividendo
    ffo = None
    if reit and _n(e.get("p_ffo")) and _n(e.get("precio")):
        ffo = _n(e["precio"]) / _n(e["p_ffo"])
    if util or (reit and ffo):
        base = ffo if reit else None
        cands = [base] if reit else [x for x in (s[EPS].get("TTM"), eps_fy) if x is not None]
        pos = [x for x in cands if x and x > 0]
        if pos:
            pay = r2(dpa / max(pos) * 100)         # ajuste 3: el mejor (menor payout)
            var("ffo" if reit else "eps", 1, menos_es_mejor(pay, ESC_UR_PAYOUT), 35, pay)
        elif cands:
            var("ffo" if reit else "eps", 1, 0, 35, None, perdida=True)
    else:
        if reit:
            res["notas"].append("REIT sin dato de FFO: se usa la escala general")
        pay_fcf = None
        if not banco:
            fy_f = [a for a in _fy(s[FCF]) if s[DIVP].get(a) is not None][:3]
            p3 = p12 = None
            if len(fy_f) >= 2:
                f3 = sum(s[FCF][a] for a in fy_f)
                d3 = sum(-s[DIVP][a] for a in fy_f)
                p3 = r2(d3 / f3 * 100) if f3 > 0 else 9999
            if s[FCF].get("TTM") is not None and s[DIVP].get("TTM") is not None:
                p12 = r2(-s[DIVP]["TTM"] / s[FCF]["TTM"] * 100) if s[FCF]["TTM"] > 0 else 9999
            opciones = [p for p in (p3, p12) if p is not None]
            if opciones:
                pay = min(opciones)                 # ajuste 2: el mejor entre 3 años y 12 meses
                pay_fcf = pay
                var("fcf", 1, menos_es_mejor(pay, ESC_FCF), 20, None if pay == 9999 else pay, p3=p3, p12=p12)
        cands = [x for x in (s[EPS].get("TTM"), eps_fy) if x is not None]
        pos = [x for x in cands if x > 0]
        mx = 35 if banco else 15
        est_v = estimacion_vigente(e) if not (banco or reit) else None
        eps_est = _n((est_v or {}).get("actual"))
        n_an = (est_v or {}).get("analistas") or 0
        usa_est = bool(eps_est and eps_est > 0 and n_an >= MIN_ANALISTAS and pay_fcf is not None and pay_fcf <= 100
                       and (not pos or eps_est >= SALTO_ANALISTAS * max(pos)))
        if usa_est:
            pay = r2(dpa / eps_est * 100)          # v1.5.62: excepción, contra la ganancia que esperan los analistas
            var("eps", 1, menos_es_mejor(pay, ESC_EPS), mx, pay, ajustada=True, perdida_contable=not pos,
                contable=r2(max(pos)) if pos else None, estimada=r2(eps_est), analistas=n_an)
            res["notas"].append("payout contra la ganancia estimada por los analistas" + (" (la contable fue pérdida)" if not pos else
                                f" ({eps_est / max(pos):.1f} veces la contable)"))
        elif pos:
            pay = r2(dpa / max(pos) * 100)         # ajuste 3
            pts = menos_es_mejor(pay, ESC_EPS) * (35 / 15 if banco else 1)
            var("eps", 1, pts, mx, pay)
        elif cands:
            var("eps", 1, 0, mx, None, perdida=True)
    # -------- pilar 2: solidez del balance (no se usa en bancos y seguros)
    cob = rating = None
    if not banco:
        num = ultimo(s[EBITDA])[0] if (util or reit) else ultimo(s[OPI])[0]
        inte = ultimo(s[INT])[0]
        deuda = ultimo(s[DT])[0]
        if inte is not None and abs(inte) > 0 and num is not None:
            cob = r2(num / abs(inte))
            mcap = _n(e.get("market_cap"))
            tabla = "chica" if mcap and mcap < CHICA_MCAP else "grande"
            rating = D.rating_sintetico(cob, tabla)[0]
            var("cobertura", 2, PTS_RATING.get(rating, 0), 12, cob, rating=rating, con="EBITDA" if (util or reit) else "EBIT", tabla=tabla)
        elif (inte in (None, 0)) and (deuda is None or deuda <= 0):
            var("cobertura", 2, 12, 12, None, sin_deuda=True)
        else:
            res["notas"].append("sin dato de intereses: la cobertura no se usa")
        nd_u = ultimo(s[ND])[0]
        nde = ultimo(ratio_nd)[0]
        if nde is None and nd_u is not None:
            eb = ultimo(s[EBITDA])[0]
            nde = nd_u / eb if eb and eb > 0 else (None if eb is None else 999)
        esc = ESC_DEUDA_UR if (util or reit) else ESC_DEUDA
        if nd_u is not None and nd_u <= 0:
            var("deuda", 2, 9, 9, r2(nd_u), caja_neta=True)
        elif nde is not None:
            var("deuda", 2, menos_es_mejor(nde, esc) if nde >= 0 else 0, 9, r2(nde))
        pat = ultimo(s[PAT])[0]
        if nd_u is not None and pat is not None:
            ndp = max(nd_u, 0.0)
            ndc = 100.0 if (ndp + pat) <= 0 else r2(ndp / (ndp + pat) * 100)
            cob_pts = next((v["pts"] for v in V if v["clave"] == "cobertura"), 0)
            if (pat <= 0 or ndc >= CASI_NULO_NDC) and cob_pts >= 10:
                res["notas"].append("posible caníbal")
            else:
                var("ndc", 2, menos_es_mejor(ndc, ESC_NDC), 4, ndc)
    # -------- pilar 3: historial del dividendo
    h = e.get("historial")
    if h:
        if h.get("historial_incompleto"):
            res["notas"].append(f"faltan pagos recientes en el historial (el último guardado es del {h.get('ultimo_pago')})")
        n = h["anios_pagando"] if variable_ext else h["anios_sin_recorte"]
        pts = 10 if n >= 25 else 8 if n >= 20 else 6 if n >= 15 else 4 if n >= 10 else 2 if n >= 5 else 0
        var("anios", 3, pts, 10, n, variable=variable_ext)
        a = h["aumentos_12"]
        var("aumentos", 3, 5 if a >= 10 else 4 if a >= 7 else 3 if a >= 5 else 1 if a >= 3 else 0, 5, a)
        pc = {"sin_recorte": 2.5, "no_pagaba": 1.0, "recorto": 0.0}
        var("crisis", 3, pc[h["crisis_0809"]] + pc[h["crisis_2020"]], 5, None, c0809=h["crisis_0809"], c2020=h["crisis_2020"])
    else:
        res["notas"].append("falta el historial de dividendos (correr bajar_historico.bat)")
    # -------- pilar 4: estabilidad del negocio
    fy13 = fy_eps[:13]
    comps = [s[EPS][fy13[i]] > s[EPS][fy13[i + 1]] for i in range(len(fy13) - 1)]
    if len(comps) >= 3:
        q = sum(comps) / len(comps)
        var("eps_suba", 4, 6 if q >= 0.75 else 4 if q >= 7 / 12 else 2 if q >= 5 / 12 else 0, 6, sum(comps), de=len(comps))
    sup = SUPERSECTOR.get(grupo)
    if sup:
        var("sector", 4, PTS_SUPER[sup], 5, sup)
    if not (util or banco):
        fy_fcf = _fy(s[FCF])[:12]
        if fy_fcf:
            negs = sum(1 for a in fy_fcf if s[FCF][a] < 0)
            var("fcf_pos", 4, 4 if negs == 0 else 2 if negs == 1 else 0, 4, negs, de=len(fy_fcf))
    # -------- pilar 5: tendencia
    est_a = estimacion_vigente(e) or {}
    g = None
    if _n(est_a.get("actual")) and _n(est_a.get("proximo")) and _n(est_a["actual"]) > 0:
        g = r2((_n(est_a["proximo"]) / _n(est_a["actual"]) - 1) * 100)
        fuente_g = "analistas"
    else:
        base3 = None
        if eps_u is not None and fy_eps:
            # 3 años antes del dato usado: con TTM (que cae en el año siguiente al último fiscal) es el último fiscal − 2; sin TTM, − 3
            ref = fy_eps[0] - (2 if s[EPS].get("TTM") is not None else 3)
            base3 = s[EPS].get(ref)
        if base3 and base3 > 0 and eps_u is not None:
            g = r2((eps_u / base3 - 1) * 100)
        fuente_g = "3 años"
    if g is not None:
        var("tendencia", 5, 5 if g >= 0 else 3 if g >= -10 else 0, 5, g, fuente=fuente_g)
    # -------- total (cada pilar se reparte entre sus variables con dato; lo que falta entero se reparte entre pilares)
    pil = {}
    for p in (1, 2, 3, 4, 5):
        vs = [v for v in V if v["pilar"] == p and v["pts"] is not None]
        mx = sum(v["max"] for v in vs)
        if vs and mx:
            pil[p] = [sum(v["pts"] for v in vs) / mx * MAX[p], MAX[p]]
    res["variables"], res["pilares"] = V, {k: [round(a, 1), b] for k, (a, b) in pil.items()}
    if 3 not in pil or 1 not in pil:
        res["notas"].append("faltan datos clave: no se calcula")
        return res
    total = sum(a for a, _ in pil.values()) / sum(b for _, b in pil.values()) * 100
    # -------- topes y alarma
    topes = []
    d_u = ultimo(s[DIVP])[0]
    div12 = -d_u if d_u is not None else 0.0
    fcf12 = ultimo(s[FCF])[0]
    gan = ffo if (reit and ffo) else eps_u
    supera_gan = gan is not None and (gan <= 0 or dpa > gan)
    if banco:
        if supera_gan:
            topes.append(("dividendo_supera", 40))
    elif supera_gan and fcf12 is not None and div12 > fcf12:
        topes.append(("dividendo_supera", 40))
    if cob is not None and cob < 1.5:
        topes.append(("cobertura_baja", 40))
    fy_f = _fy(s[FCF])[:3]
    if gan is not None and gan <= 0 and fy_f and sum(s[FCF][a] for a in fy_f) <= 0:
        topes.append(("sin_caja", 20))
    for _, t in topes:
        total = min(total, t)
    dy, dym = _n(e.get("dy")), _n(e.get("dy_mediana"))
    if dy and dym and dy >= 2 * dym:
        total -= 10
        topes.append(("alarma_rendimiento", -10))
    score = max(0, min(100, int(round(total))))
    res["topes"] = topes
    res["score"] = score
    res["categoria"], res["frase"] = categoria(score)
    res["color"] = COLORES.get(res["categoria"])
    res["conclusion"] = conclusion(res, e, variable_ext)
    return res


# ---------------------------------------------------------------------------------------------------------------------
# conclusión debajo del score (documento, sección «Lo que ve el usuario»)
# ---------------------------------------------------------------------------------------------------------------------
def _frase(v, a_favor, variable_ext=False):
    k, x = v["clave"], v.get("valor")
    if k == "fcf":
        if x is None:
            return "no genera flujo de caja libre para cubrir el dividendo" if not a_favor else None
        return f"usa solo el {_pct(x)} de su flujo de caja libre para el dividendo" if a_favor else f"el dividendo ya usa el {_pct(x)} de su flujo de caja libre"
    if k == "eps" and v.get("ajustada"):
        de = "de la ganancia que esperan los analistas para este año"
        if a_favor:
            return f"paga el {_pct(x)} {de}" + (" (el último año tuvo pérdida)" if v.get("perdida_contable") else "")
        return f"el dividendo se lleva el {_pct(x)} {de}"
    if k in ("eps", "ffo"):
        de = "de su flujo de fondos (FFO)" if k == "ffo" else "de lo que gana"
        if v.get("perdida"):
            return None if a_favor else "tuvo pérdida en el último año"
        return f"paga el {_pct(x)} {de}" if a_favor else f"el dividendo se lleva el {_pct(x)} {de}"
    if k == "cobertura":
        if v.get("sin_deuda"):
            return "no tiene deuda que pague intereses" if a_favor else None
        quien = "su EBITDA" if v.get("con") == "EBITDA" else "su ganancia operativa"
        if x is not None and x <= 0:
            return None if a_favor else (f"{quien} es negativa (no cubre los intereses)" if quien.endswith("operativa") else f"{quien} es negativo (no cubre los intereses)")
        return f"{quien} cubre {_veces(x)} veces los intereses" if a_favor else f"{quien} cubre apenas {_veces(x)} veces los intereses"
    if k == "deuda":
        if v.get("caja_neta"):
            return "tiene más caja que deuda" if a_favor else None
        return f"tiene poca deuda ({_veces(x)} veces su EBITDA)" if a_favor else f"la deuda equivale a {_veces(x)} veces su EBITDA"
    if k == "ndc":
        return "se financia sobre todo con capital propio" if a_favor else f"la deuda es el {_pct(x)} de su financiamiento"
    if k == "anios":
        if v.get("variable"):
            return f"lleva {_anios_txt(x)} pagando dividendo sin interrupción" if a_favor else f"lleva solo {_anios_txt(x)} pagando dividendo sin interrupción"
        return f"lleva {_anios_txt(x)} sin recortar el dividendo" if a_favor else (f"lleva solo {_anios_txt(x)} sin recortar el dividendo" if x else "recortó el dividendo hace poco")
    if k == "aumentos":
        if not a_favor and x == 0:
            return "no aumentó el dividendo en los últimos 12 años"
        if a_favor and x == 12:
            return "aumentó el dividendo en cada uno de los últimos 12 años"
        return f"aumentó el dividendo en {x} de los últimos 12 años" if a_favor else f"aumentó el dividendo solo en {x} de los últimos 12 años"
    if k == "crisis":
        c1, c2 = v.get("c0809"), v.get("c2020")
        if a_favor:
            if c1 == "sin_recorte" and c2 == "sin_recorte":
                return "no recortó el dividendo en 2008-09 ni en 2020"
            if c2 == "sin_recorte":
                return "no recortó el dividendo en 2020"
            return None
        r = [t for t, c in (("2008-09", c1), ("2020", c2)) if c == "recorto"]
        return f"recortó el dividendo en {' y en '.join(r)}" if r else None
    if k == "eps_suba":
        if not a_favor and x == 0:
            return f"sus ganancias no subieron en ninguno de los últimos {v['de']} años"
        if a_favor and x == v["de"]:
            return f"sus ganancias subieron en cada uno de los últimos {v['de']} años"
        return f"sus ganancias subieron en {x} de los últimos {v['de']} años" if a_favor else f"sus ganancias subieron solo en {x} de los últimos {v['de']} años"
    if k == "sector":
        return ("pertenece a un sector defensivo" if x == "Defensivo" else None) if a_favor else \
            ("pertenece a un sector cíclico" if x == "Cíclico" else "pertenece a un sector sensible al ciclo económico")
    if k == "fcf_pos":
        return "generó flujo de caja libre todos los años" if a_favor else f"tuvo {_anios_txt(x)} con flujo de caja libre negativo"
    if k == "tendencia":
        if v.get("fuente") == "analistas":
            return "se espera que su ganancia crezca el próximo año" if a_favor else f"se espera que su ganancia caiga {_pct(abs(x))} el próximo año"
        return "su ganancia creció en los últimos 3 años" if a_favor else f"su ganancia cayó {_pct(abs(x))} en los últimos 3 años"
    return None


FRASE_TOPE = {"dividendo_supera": "el dividendo supera lo que gana y lo que genera de caja",
              "sin_caja": "tuvo pérdida y no generó flujo de caja libre en 3 años: no tiene de dónde pagar el dividendo",
              "alarma_rendimiento": "su rendimiento duplica su promedio de 5 años, una señal de alarma del mercado"}


def _unir(fr):
    fr = [f for f in fr if f]
    if not fr:
        return ""
    if len(fr) == 1:
        return fr[0]
    a, b = fr[0], fr[1]
    pres = ("el dividendo ya usa ", "el dividendo se lleva ")
    if any(a.startswith(p) for p in pres):       # dos payouts seguidos: «se lleva el 95% de lo que gana y el 120% de su flujo…»
        for pre in pres:
            if b.startswith(pre):
                b = b[len(pre):]
                break
    if "dividendo" in a:      # sin repetir «el dividendo» en la misma oración
        for pre in pres:
            if b.startswith(pre):
                b = "pagarlo " + b[len("el dividendo "):]       # «…sin recortar el dividendo y pagarlo ya usa el 60% de su flujo…»
        b = (b.replace("no recortó el dividendo", "no lo recortó").replace("recortó el dividendo", "lo recortó")
             .replace("aumentó el dividendo", "lo aumentó").replace("sin recortar el dividendo", "sin recortarlo")
             .replace("pagando dividendo", "pagándolo").replace(" para el dividendo", ""))
    return f"{a} y {b}"


def _may(t):
    return t[:1].upper() + t[1:] if t else t


def conclusion(res, e=None, variable_ext=False):
    """1 o 2 oraciones con los números reales: a favor (las 2 variables con puntaje completo que más pesan) y en contra (las 1 o 2 que más
    perdieron, si perdieron 3 puntos o más; un tope o la alarma va primero). Score alto: primero lo que lo sostiene; score bajo: al revés."""
    vs = [v for v in res["variables"] if v["pts"] is not None]
    llenas = sorted((v for v in vs if v["pts"] >= v["max"]), key=lambda v: -v["max"])
    if not llenas:
        llenas = sorted(vs, key=lambda v: -(v["pts"] / v["max"]) if v["max"] else 0)
    favor = [f for f in (_frase(v, True, variable_ext) for v in llenas) if f][:2]
    contra = []
    for clave, _ in res.get("topes") or []:
        if clave == "cobertura_baja":
            c = next((v for v in vs if v["clave"] == "cobertura"), None)
            contra.append(_frase(c, False) if c else None)
        else:
            contra.append(FRASE_TOPE.get(clave))
    perdidas = sorted((v for v in vs if v["max"] - v["pts"] >= 3), key=lambda v: -(v["max"] - v["pts"]))
    if any(c == "dividendo_supera" for c, _ in res.get("topes") or []):
        perdidas = [v for v in perdidas if v["clave"] not in ("fcf", "eps", "ffo")]   # la frase del tope ya lo dice
    for v in perdidas:
        f = _frase(v, False, variable_ext)
        if f and f not in contra:
            contra.append(f)
    contra = [c for c in contra if c][:2]
    alto = (res.get("score") or 0) > 40
    if alto:
        txt = _may(_unir(favor)) + "." if favor else ""
        if contra:
            txt += (" " if txt else "") + "Pierde puntos porque " + _unir(contra) + "."
    else:
        txt = _may(_unir(contra)) + "." if contra else ""
        if favor:
            txt += (" " if txt else "") + "A favor: " + favor[0] + "."
    return txt.strip()
