"""
Score de Seguridad de Dividendos — versión 1 (diseño de Guille, documento «Score de Seguridad de Dividendos (Escala 0 - 100)», 16/11/2026).

Se programa aparte del score v0.2 (scoring/dividendo.py) para compararlos contra Simply Safe Dividends antes de reemplazar nada.
Regla de Guille: «respetar lo más posible el archivo». Lo que el documento no dice y Guille definió el 16/11/2026:
  - Bordes: cada zona va hasta el punto inmediato anterior de la siguiente (la gris cubre todo lo que no es segura ni crítica).
  - Zona gris con puntaje fijo (como en el documento).
  - Freno por pérdida: resultado neto negativo en el último año fiscal completo → máximo 20, sin excepciones (también REITs).
  - Ganancias retenidas ajustadas = ganancias retenidas + |acciones en tesorería| (así no castiga las recompras).
  - Trampa de rendimiento: rendimiento > 8% y payout sobre flujo libre > 100% → −30 y máximo 40.
  - Payout futuro: siempre el plan B (no hay consenso gratis de flujo libre futuro); ganancia de los próximos 12 meses = mezcla de la
    estimación de este año fiscal y la del próximo según los meses que faltan.
  - Crecimiento de ventas: anual compuesto de 3 años fiscales.
  - Utilities: FFO/Deuda de S&P ≈ flujo operativo ÷ deuda total. REITs: cobertura de cargos fijos ≈ EBITDA ÷ intereses.
Definiciones mías, pendientes de su OK (marcadas PROPUESTA): pesos de las métricas de reemplazo por sector, «pagos erráticos».
v1.5.72 (Guille 17/11/2026): cobertura con resultado e intereses del mismo período (12 meses o último año, nada más viejo; SEC y carga manual
con fuente de respaldo) y obligatoria; REITs solo con AFFO (sin FFO provisorio); CET1 con el requisito regulatorio de cada banco.
"""
import datetime as _dt
import json
import os

from scoring import dividendo as V0

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATEGORIAS = [(20, "Muy inseguro"), (40, "Inseguro"), (60, "Límite"), (80, "Seguro"), (100, "Muy seguro")]

ASSET_LIGHT = {"Hardware y servicios TI", "Semiconductores", "Software y nube", "Salud", "Pagos y datos"}
STAPLES = {"Consumo Básico"}
BANCOS = {"Bancos y seguros"}
REITS = {"REITs"}
UTILITIES = {"Utilities"}

# Política de dividendo variable declarada (techo 80, sin bono). Cada una con su fuente.
VARIABLE_DECLARADA = {
    "GFI": "paga 35% del flujo libre antes de inversiones discrecionales (resultados 1S2026)",
}
VIGENCIA_FINANCIERA = 200  # v1.5.77: días desde el cierre del trimestre de las cifras de una financiera propia antes de avisar «renovar»
RECOMPRAS_ANIOS = 10        # v1.5.74: recompras que se suman a las ganancias retenidas (Guille: aprobado)
SOLVENCIA_SEGURA = 150.0    # v1.5.74, aprobado por Guille el 17/11/2026: índice de solvencia de las aseguradoras (segura más de 150 %; crítica debajo del requisito, 100 %)
# PROPUESTA: «historial de pagos erráticos» = 3 o más años con recorte en los últimos 10 (en la moneda del dividendo)
ERRATICO_RECORTES, ERRATICO_ANIOS = 3, 10


def _zona(x, segura, critica, pts, menor_es_mejor):
    """Puntos por zona: segura / gris / crítica. segura y crítica son (umbral, incluido)."""
    if x is None:
        return None
    s, s_inc = segura
    c, c_inc = critica
    if menor_es_mejor:
        if x < s or (s_inc and x == s):
            return pts[0]
        if x > c or (c_inc and x == c):
            return pts[2]
    else:
        if x > s or (s_inc and x == s):
            return pts[0]
        if x < c or (c_inc and x == c):
            return pts[2]
    return pts[1]


def categoria(p):
    for tope, nombre in CATEGORIAS:
        if p <= tope:
            return nombre
    return CATEGORIAS[-1][1]


def _ultimo(serie, n=2):
    """Primer valor no nulo empezando por los últimos 12 meses (si falta, el último año fiscal); n = cuántos períodos mirar."""
    for k in list(serie)[: max(1, n)]:
        if serie[k] is not None:
            return serie[k]
    return None


def _anuales(serie):
    return {k: v for k, v in serie.items() if isinstance(k, int) and v is not None}


def ntm(est, mes_cierre=None, hoy=None):
    """Ganancia por acción de los próximos 12 meses: mezcla de la estimación del año fiscal en curso y la del próximo."""
    if not est or est.get("actual") is None:
        return None
    hoy = hoy or _dt.date.today()
    mes = int(mes_cierre or 12)
    cierre = _dt.date(hoy.year, mes, 28)
    if cierre < hoy:
        cierre = _dt.date(hoy.year + 1, mes, 28)
    faltan = max(0.0, min(12.0, (cierre - hoy).days / 30.44))
    w = faltan / 12
    prox = est.get("proximo")
    if prox is None:
        return est["actual"]
    return w * est["actual"] + (1 - w) * prox


def calcular(e):
    """e: la entrada del score v0.2 (scoring.dividendo.entrada) más: "hist" ya en la moneda del dividendo, "mes_cierre", "cet1",
    "affo" (por acción), "rend" (rendimiento del dividendo, 0,05 = 5%). Devuelve {"score", "categoria", "variables", "ajustes", "topes"}."""
    grupo = e.get("grupo")
    banco, reit, util = grupo in BANCOS, grupo in REITS, grupo in UTILITIES
    est = e.get("estados") or {}
    S = lambda parte, fila: V0.serie(est, fila)  # noqa: E731
    neto, ebit, inte = S("r", "Resultado neto"), S("r", "Resultado operativo"), S("r", "Gasto por intereses")
    ebitda, ingresos, eps = S("r", "EBITDA"), S("r", "Ingresos"), S("r", "Ganancia por acción (diluida)")
    fcf, divp, cfo = S("f", "Flujo de efectivo libre"), S("f", "Dividendos pagados"), S("f", "Flujo de efectivo operativo")
    int_pag = S("f", "Intereses pagados")
    deuda, dneta, caja = S("b", "Deuda total"), S("b", "Deuda neta"), S("b", "Caja e inversiones de corto plazo")
    ac, inv, pc, at = S("b", "Activo corriente"), S("b", "Inventarios"), S("b", "Pasivo corriente"), S("b", "Activo total")
    rr, tes = S("b", "Ganancias retenidas"), S("b", "Acciones en tesorería")
    recomp, arrend = S("f", "Recompra de acciones"), S("b", "Deuda por arrendamientos")
    dpa = V0._n(e.get("dividendo_anual"))
    vs, ajustes, topes, notas = [], [], [], []

    def var(clave, pts, mx, valor, **extra):
        vs.append(dict(clave=clave, pts=pts, max=mx, valor=valor, **extra))

    # --- cobertura de intereses (25) / cobertura de cargos fijos en REITs (EBITDA ÷ intereses) / CET1 en bancos ---------
    # v1.5.72 (Guille 17/11/2026: usar un dato de años atrás «es una atrocidad»): resultado e intereses del MISMO período, los últimos 12 meses
    # o el último año fiscal; nada más viejo. Intereses: el gasto (Yahoo; si falta, la SEC, data/sec.huecos) → los pagados (flujo de efectivo)
    # → cargado a mano con fuente (data/intereses_manuales.json, empresas que no lo informan). Sin cobertura no hay score.
    cob = None
    finp = e.get("financiera_propia") or {}
    if not banco:
        base_s = ebitda if reit else ebit
        antes_imp = S("r", "Resultado antes de impuestos")
        fy_base = [a for a in _anuales(base_s)] or [a for a in _anuales(antes_imp)]
        periodos = (["TTM"] if "TTM" in base_s or "TTM" in antes_imp else []) + ([max(fy_base)] if fy_base else [])
        man = e.get("intereses_manual")
        if man and man.get("solo_pagados"):
            # v1.5.76 (Guille 17/11/2026, NextEra: «hagamos como hacés vos»): su línea de intereses mezcla ganancias y pérdidas de coberturas
            # de tasa; se usan los intereses PAGADOS (flujo de efectivo) del mismo período, o los cargados a mano
            inte = {}
            notas.append("intereses: los pagados (su gasto por intereses incluye coberturas de tasa)")

        def _base(p, i):
            b = base_s.get(p)
            if b is None and not reit and antes_imp.get(p) is not None:
                b = antes_imp[p] + abs(i)            # sin resultado operativo: antes de impuestos + intereses
            return b

        # v1.5.77: las cifras pueden ser de un año fiscal («anio») o del último trimestre («hasta»: balance a esa fecha e intereses de los
        # 12 meses que terminan ahí); las renueva la tarea trimestral (Guille 17/11/2026)
        trim = bool(finp.get("hasta"))
        if trim:
            try:
                ref = e.get("hoy") or _dt.date.today()
                ref = _dt.date.fromisoformat(str(ref)[:10]) if not isinstance(ref, _dt.date) else ref
                if (ref - _dt.date.fromisoformat(str(finp["hasta"])[:10])).days > VIGENCIA_FINANCIERA:
                    notas.append(f"financiera propia: las cifras del negocio industrial son al {finp['hasta']} (renovar)")
            except ValueError:
                pass
        elif finp.get("anio") and fy_base and max(fy_base) > int(finp["anio"]):
            notas.append(f"financiera propia: las cifras del negocio industrial son de {finp['anio']} y ya hay un año fiscal más nuevo (renovar)")
        if V0._n(finp.get("intereses")) is not None:
            # v1.5.76 (Guille 17/11/2026: «sí, hagámoslo como hace SSD»): empresa con financiera propia → cobertura del negocio industrial
            # (data/financieras_propias.json): resultado operativo ÷ intereses del negocio sin la financiera, del mismo período
            p, i = ("TTM" if trim else int(finp.get("anio") or 0)), V0._n(finp["intereses"])
            b = V0._n(finp.get("ebit")) if V0._n(finp.get("ebit")) is not None else base_s.get(p)
            if b is not None:
                cob = 99.0 if i == 0 else b / abs(i)
                notas.append(f"cobertura del negocio sin su financiera ({finp.get('hasta') or p})")
            periodos = []
        for p in periodos:
            i, de = inte.get(p), "gasto"
            if i is None and int_pag.get(p) is not None:
                i, de = int_pag[p], "pagados"
            if i is None:
                continue
            b = _base(p, i)
            if b is None:
                continue
            cob = 99.0 if abs(i) == 0 else b / abs(i)
            if de == "pagados":
                notas.append(f"intereses: los pagados (flujo de efectivo, {p})")
            break
        if cob is None and man and V0._n(man.get("monto")) is not None:
            p = int(man.get("anio") or 0)
            b = _base(p, man["monto"]) if p in base_s or p in antes_imp else None
            if b is not None:
                cob = 99.0 if V0._n(man["monto"]) == 0 else b / abs(V0._n(man["monto"]))
                notas.append(f"intereses cargados a mano ({p}): {man.get('medida', '')[:80]}")
        d = _ultimo(deuda)
        if cob is None and d is not None and d <= 0:
            cob = 99.0
            notas.append("sin deuda: cobertura segura")
        # v1.5.74 (Guille: «si no hay interés a pagar la cobertura es máxima»): sin intereses informados y sin deuda financiera (la deuda total de
        # Yahoo incluye los alquileres) → cobertura máxima
        a = _ultimo(arrend)
        if cob is None and d is not None and a is not None and d - abs(a) <= 0.01 * d:
            cob = 99.0
            notas.append("sin deuda financiera (su deuda son alquileres) ni intereses: cobertura máxima")
        if reit:
            var("cobertura", _zona(cob, (3.0, False), (1.5, False), (25, 10, 0), False), 25, cob, nombre="EBITDA ÷ intereses (cargos fijos)")
        else:
            var("cobertura", _zona(cob, (5.0, False), (2.0, False), (25, 10, 0), False), 25, cob)
        if cob is None:
            return {"score": None, "categoria": None, "variables": vs, "ajustes": ajustes, "topes": topes,
                    "notas": notas + ["falta el gasto por intereses de los últimos 12 meses o del último año fiscal"]}
    elif V0._n(e.get("solvencia")) is not None:
        # v1.5.74 (Guille 17/11/2026: «hagamos con índice de solvencia» en las aseguradoras; cortes aprobados: «OK, de acuerdo»), igual que el CET1: segura más de
        # 150 %, gris desde el requisito (100 % = el mínimo regulatorio) hasta 150 %, crítica por debajo del requisito.
        sv, rq = V0._n(e.get("solvencia")), V0._n(e.get("solvencia_requisito")) or 100.0
        var("solvencia", 25 if sv > SOLVENCIA_SEGURA else 10 if sv >= rq else 0, 25, sv, requisito=rq)
    else:
        # CET1 (documento): segura > 11 %, gris 9,5 % a 11 %, crítica = por debajo del requisito regulatorio de ESE banco. Con la regla de
        # bordes de Guille la gris llega hasta el requisito. Si el requisito no está cargado se usa 9,5 % (piso de la gris del documento).
        c1, req = V0._n(e.get("cet1")), V0._n(e.get("cet1_requisito"))
        piso = req if req is not None else 9.5
        pts = None if c1 is None else (25 if c1 > 11 else 10 if c1 >= piso else 0)
        if c1 is not None and c1 <= 11 and req is None:
            notas.append("CET1: sin el requisito regulatorio cargado, se usó 9,5 %")
        var("cet1", pts, 25, c1, requisito=req)

    # --- payout sobre flujo libre (20) / AFFO en REITs / ganancias en utilities y bancos ---------------------------------------
    fcf_pay = None
    d12, f12 = _ultimo(divp), _ultimo(fcf)
    if d12 is not None and f12 is not None:
        fcf_pay = abs(d12) / f12 * 100 if f12 > 0 else 999.0
    if reit:
        # v1.5.72: dividendos pagados ÷ AFFO de los mismos 12 meses, con las cifras de la empresa (data/ffo_reit.json, affo_payout_12m);
        # si solo hay AFFO por acción, dividendo anual ÷ AFFO. Sin AFFO de la empresa, la métrica no cuenta (nada de FFO provisorio).
        affo, pay = V0._n(e.get("affo")), V0._n(e.get("affo_payout"))
        if pay is None:
            pay = (dpa / affo * 100 if affo and affo > 0 else 999.0) if (dpa and affo is not None) else None
        var("affo", _zona(pay, (80, False), (90, False), (20, 10, 0), True), 20, pay, nombre=e.get("affo_nombre") or "AFFO")
    elif util or banco:
        e12 = _ultimo(eps)
        pay = (dpa / e12 * 100 if e12 and e12 > 0 else 999.0) if (dpa and e12 is not None) else None
        if util:
            var("eps_payout", _zona(pay, (70, False), (80, False), (20, 10, 0), True), 20, pay)
        else:
            var("eps_payout", _zona(pay, (50, False), (75, True), (20, 10, 0), True), 20, pay)
    else:
        var("fcf_payout", _zona(fcf_pay, (60, False), (85, False), (20, 10, 0), True), 20, fcf_pay)

    # --- payout futuro (15): plan B, ganancia de los próximos 12 meses (no en REITs) ------------------------------------------
    if not reit:
        g = ntm(e.get("estimacion"), e.get("mes_cierre"), e.get("hoy"))
        fp = (dpa / g * 100 if g > 0 else 999.0) if (dpa and g is not None) else None
        var("payout_futuro", _zona(fp, (55, False), (80, True), (15, 7, 0), True), 15, fp)

    # --- crecimiento de ventas, 3 años (10) -------------------------------------------------------------------------------
    an = _anuales(ingresos)
    sgr = None
    if an:
        u = max(an)
        if u - 3 in an and an[u - 3] > 0 and an[u] > 0:
            sgr = ((an[u] / an[u - 3]) ** (1 / 3) - 1) * 100
    var("ventas", _zona(sgr, (3, False), (0, False), (10, 5, 0), False), 10, sgr)

    # --- deuda neta ÷ EBITDA (15) -------------------------------------------------------------------------------------------
    if not banco:
        dn = _ultimo(dneta)
        if dn is None and _ultimo(deuda) is not None and _ultimo(caja) is not None:
            dn = _ultimo(deuda) - _ultimo(caja)
        eb = _ultimo(ebitda)
        # v1.5.76: con financiera propia, deuda neta y EBITDA del negocio industrial (data/financieras_propias.json); sin la cifra de deuda
        # cargada (pendiente) sigue la consolidada
        dn_fp = V0._n(finp.get("deuda_neta"))
        if dn_fp is None and V0._n(finp.get("deuda")) is not None and V0._n(finp.get("caja")) is not None:
            dn_fp = V0._n(finp["deuda"]) - V0._n(finp["caja"])
        if dn_fp is not None:
            dn = dn_fp
            eb = V0._n(finp.get("ebitda")) or (ebitda.get("TTM") if finp.get("hasta") else ebitda.get(int(finp.get("anio") or 0))) or eb
            notas.append(f"deuda del negocio sin su financiera ({finp.get('hasta') or finp.get('anio')})")
        nd = None
        if dn is not None and eb:
            nd = -1.0 if dn <= 0 else (dn / eb if eb > 0 else 99.0)
        if reit:
            var("deuda", _zona(nd, (5.5, False), (6.5, False), (15, 7, 0), True), 15, nd)
        elif util:
            var("deuda", _zona(nd, (5.0, False), (6.0, False), (15, 7, 0), True), 15, nd)
        else:
            var("deuda", _zona(nd, (2.5, False), (4.5, False), (15, 7, 0), True), 15, nd)

    # --- FFO/Deuda en utilities (≈ flujo operativo ÷ deuda total): PROPUESTA 10 puntos más, el total se lleva a 100 ---------
    if util:
        o, d = _ultimo(cfo), _ultimo(deuda)
        fd = o / d * 100 if (o is not None and d) else None
        var("ffo_deuda", _zona(fd, (15, False), (10, False), (10, 5, 0), False), 10, fd)

    # --- ganancias retenidas ajustadas ÷ activos (10) (no en REITs) ---------------------------------------------------------
    # v1.5.74 (Guille 17/11/2026: «me gusta la solución»): ganancias retenidas + lo mayor entre las acciones en tesorería y las recompras de los
    # últimos 10 años fiscales. Así no se castiga a las que cancelan las acciones que recompran (Apple) y no se cuenta dos veces una recompra.
    if not reit:
        r, t, a = _ultimo(rr), _ultimo(tes), _ultimo(at)
        an_r = _anuales(recomp)
        rec10 = sum(abs(v) for k, v in an_r.items() if k > max(an_r) - RECOMPRAS_ANIOS) if an_r else 0.0
        suma = max(abs(t or 0), rec10)
        re_ta = (r + suma) / a * 100 if (r is not None and a) else None
        var("re_ta", _zona(re_ta, (35, False), (15, False), (10, 5, 0), False), 10, re_ta,
            recompras=rec10, anios_recompras=len([k for k in an_r if k > max(an_r) - RECOMPRAS_ANIOS]) if an_r else 0)

    # --- prueba ácida (5) (no en bancos) ------------------------------------------------------------------------------------
    if not banco:
        a_c, p_c = _ultimo(ac), _ultimo(pc)
        q = (a_c - (_ultimo(inv) or 0)) / p_c if (a_c is not None and p_c) else None
        if util:
            pts = None if q is None else (0 if q < 0.4 else 5)
        elif grupo in ASSET_LIGHT:
            pts = _zona(q, (1.5, False), (1.0, False), (5, 2, 0), False)
        elif grupo in STAPLES:
            pts = _zona(q, (0.6, False), (0.4, False), (5, 2, 0), False)
        else:
            pts = _zona(q, (1.1, False), (0.7, False), (5, 2, 0), False)
        var("acida", pts, 5, q)

    # --- base: puntos sobre el máximo posible, llevados a 100 ----------------------------------------------------------------
    con = [v for v in vs if v["pts"] is not None]
    mx = sum(v["max"] for v in con)
    if not con or mx < 40:
        return {"score": None, "categoria": None, "variables": vs, "ajustes": ajustes, "topes": topes, "notas": notas + ["faltan datos"]}
    base = sum(v["pts"] for v in con) / mx * 100
    if mx != 100:
        notas.append(f"base sobre {mx} puntos posibles, llevada a 100")

    # --- historial (moneda del dividendo) -------------------------------------------------------------------------------------
    h = e.get("historial") or {}
    tk = e.get("ticker")
    ult = h.get("ultimo_completo")
    medible = e.get("fuente_historial") != "variable"     # sin el dividendo en su moneda no se puede medir: ni castigo ni bono
    rec = [a for a in (h.get("recortes") or []) if ult is None or a <= ult] if medible else []
    # un recorte a mitad de año aparece también en el año siguiente (y una suspensión, en cada año sin pagos): se cuenta desde
    # el primer año de cada tramo seguido de recortes
    eventos = [a for a in rec if a - 1 not in rec]
    hace = 0 if (h.get("recorte_en_curso") and medible) else (ult - max(eventos) if eventos and ult else None)
    erratico = sum(1 for a in eventos if ult and a > ult - ERRATICO_ANIOS) >= ERRATICO_RECORTES
    variable = tk in VARIABLE_DECLARADA or erratico
    racha, sin_suba = (h.get("racha_subas") or 0, h.get("anios_sin_suba") or 0) if medible else (0, 0)
    if hace is not None:
        if hace < 5:
            ajustes.append(("recorte_menos_5", -25))
        elif hace <= 10:
            ajustes.append(("recorte_5_10", -10))
    # el bono se anula si la cobertura (o su reemplazo) o el payout principal están en zona crítica
    critica = any(v["pts"] == 0 for v in vs if v["clave"] in ("cobertura", "cet1", "solvencia", "fcf_payout", "affo", "eps_payout"))
    if sin_suba >= 3:
        ajustes.append(("congelamiento", -5))           # congelamiento crónico: −5 y pierde el bono
    elif not variable and not critica:
        if racha >= 25:
            ajustes.append(("aristocrata", 10))
        elif racha >= 10:
            ajustes.append(("aspirante", 5))

    # --- trampa de rendimiento -------------------------------------------------------------------------------------------------
    rend = V0._n(e.get("rend"))
    trampa = rend is not None and rend > 0.08 and fcf_pay is not None and fcf_pay > 100
    if trampa:
        ajustes.append(("trampa_rendimiento", -30))

    total = base + sum(x for _, x in ajustes)
    # --- frenos -------------------------------------------------------------------------------------------------------------------
    an_n = _anuales(neto)
    if an_n and an_n[max(an_n)] < 0:
        topes.append(("perdida", 20))
    if cob is not None and not banco and cob < 1.5:
        topes.append(("cobertura_letal", 20))
    if trampa:
        topes.append(("trampa_rendimiento", 40))
    if variable:
        topes.append(("dividendo_variable", 80))
    for _, t in topes:
        total = min(total, t)
    total = max(0, min(100, int(round(round(total, 6)))))
    return {"score": total, "categoria": categoria(total), "variables": vs, "ajustes": ajustes, "topes": topes, "notas": notas,
            "base": round(base, 1), "variable": variable, "erratico": erratico}


def cargar_json(nombre):
    try:
        return json.load(open(os.path.join(AQUI, "data", nombre), encoding="utf-8")).get("datos", {})
    except (OSError, ValueError):
        return {}


_MANUALES = {}


def intereses_manual(ticker, ruta=None):
    """v1.5.72: gasto por intereses cargado a mano con fuente (data/intereses_manuales.json) para las empresas que no lo informan, o None."""
    ruta = ruta or os.path.join(AQUI, "data", "intereses_manuales.json")
    if ruta not in _MANUALES:
        try:
            _MANUALES[ruta] = json.load(open(ruta, encoding="utf-8")).get("datos", {})
        except (OSError, ValueError):
            _MANUALES[ruta] = {}
    return _MANUALES[ruta].get(ticker)


_FINANCIERAS = {}


def financiera_propia(ticker, ruta=None):
    """v1.5.76: cifras del negocio industrial de las empresas con financiera propia (data/financieras_propias.json), o None."""
    ruta = ruta or os.path.join(AQUI, "data", "financieras_propias.json")
    if ruta not in _FINANCIERAS:
        try:
            _FINANCIERAS[ruta] = json.load(open(ruta, encoding="utf-8")).get("datos", {})
        except (OSError, ValueError):
            _FINANCIERAS[ruta] = {}
    return _FINANCIERAS[ruta].get(ticker)
