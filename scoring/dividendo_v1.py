"""
Score de Seguridad de Dividendos — versión 1 (diseño de Guille, documento «Score de Seguridad de Dividendos (Escala 0 - 100)», 16/11/2026).

Se programa aparte del score v0.2 (scoring/dividendo.py) para compararlos contra Simply Safe Dividends antes de reemplazar nada.
Regla de Guille: «respetar lo más posible el archivo». Lo que el documento no dice y Guille definió el 16/11/2026:
  - Bordes: cada zona va hasta el punto inmediato anterior de la siguiente (la gris cubre todo lo que no es segura ni crítica).
  - Zona gris con puntaje fijo (como en el documento).
  - Freno por pérdida: resultado neto negativo en el último año fiscal completo → máximo 20, sin excepciones (también REITs).
    v1.5.88 (Guille 23/11/2026, opción B): salvo que la pérdida venga de operaciones discontinuadas (escisión o venta) y lo que sigue haya ganado.
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
import math
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
CRECIMIENTO_SIMBOLICO = 1.5  # v1.5.78: % anual del dividendo regular por debajo del cual el premio de aristócrata/aspirante queda en la mitad
CRECIMIENTO_ANIOS = 3        # v1.5.78: años completos para medirlo (a 5 años, Yahoo deforma los pagos viejos cuando la empresa separa un negocio)
TOPE_SCORE = 99              # v1.5.78: el score no muestra 100 (Guille, por estética)
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


def congelamientos(h, minimo=3):
    """Último año de cada tramo de `minimo` o más años completos seguidos sin subir el dividendo regular (sin recorte), en la serie `tasa`
    del historial. v1.5.81; desde la v1.5.83 hace errático al dividendo."""
    tasa = {int(k): v for k, v in (h.get("tasa") or {}).items()}
    ult, rec = h.get("ultimo_completo"), set(h.get("recortes") or [])
    planos = [a for a in sorted(tasa) if ult and a <= ult and a - 1 in tasa and tasa[a] and tasa[a - 1] and a not in rec
              and tasa[a] <= tasa[a - 1] * 1.001]
    fin, tramo = [], []
    for a in planos + [None]:
        if a is not None and tramo and a == tramo[-1] + 1:
            tramo.append(a)
            continue
        if len(tramo) >= minimo:
            fin.append(tramo[-1])
        tramo = [a] if a is not None else []
    return fin


def _periodo(serie, n=2):
    """Como _ultimo, pero devuelve el período («TTM» o el año)."""
    for k in list(serie)[: max(1, n)]:
        if serie[k] is not None:
            return k
    return None


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


def calcular(e, version=3):
    """e: la entrada del score v0.2 (scoring.dividendo.entrada) más: "hist" ya en la moneda del dividendo, "mes_cierre", "cet1",
    "affo" (por acción), "rend" (rendimiento del dividendo, 0,05 = 5%). Devuelve {"score", "categoria", "variables", "ajustes", "topes"}.
    v1.5.91 (Guille 24/11/2026, numeración para la auditoría): version=3 = el Word del 16/11 con las decisiones posteriores de Guille (lo de
    siempre); version=2 = el Word puro con lo definido el 16/11 (como se programó en la v1.5.71), con los mismos arreglos de datos. En la
    versión 2 se apagan: recompras en ganancias retenidas, solvencia de aseguradoras, FFO de Welltower como AFFO, financieras propias,
    medio premio simbólico, tope 99, pago futuro propio de utilities y bancos, utilities 7,5 + 7,5 (vuelve a deuda 15 + FFO ÷ Deuda 10 sobre
    110), congelamiento = errático (vuelve a −5 y sin premio, solo si sigue congelado), ventas comparables, «cuenta el castigo que resta más»,
    bancos sin ganancias retenidas y el freno por pérdida de operaciones discontinuadas."""
    v2 = version == 2
    if v2:
        e = dict(e, solvencia=None, financiera_propia=None, ventas_comparables=None)
        if e.get("affo_es_ffo"):
            e["affo"] = None
    grupo = e.get("grupo")
    banco, reit, util = grupo in BANCOS, grupo in REITS, grupo in UTILITIES
    # v1.5.81: sin dividendo no hay score de seguridad del dividendo (Roku, Snap y Fiserv salían con puntaje en la comparación con SSD)
    if not V0._n(e.get("dividendo_anual")):
        return {"score": None, "categoria": None, "variables": [], "ajustes": [], "topes": [], "notas": ["no paga dividendo"]}
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
    # v1.5.79: deuda del último trimestre que no cierra con el balance (KEPCO: Yahoo anota 3,1 billones de wones contra 132,9 del cierre del
    # año, con el pasivo total subiendo): se descarta y se usa la del último año fiscal. Si el pasivo baja junto con la deuda (Spotify, Hecla,
    # Honeywell), es un pago de verdad y queda.
    fy_d = [a for a in deuda if isinstance(a, int) and deuda[a]]
    if deuda.get("TTM") is not None and fy_d:
        u_d, pt = max(fy_d), S("b", "Pasivo total")
        caida = deuda[u_d] - deuda["TTM"]
        if (deuda["TTM"] < 0.5 * deuda[u_d] and pt.get(u_d) and pt.get("TTM") and caida > 0.1 * pt[u_d]
                and pt[u_d] - pt["TTM"] < 0.25 * caida):
            deuda = {k: x for k, x in deuda.items() if k != "TTM"}
            dneta = {k: x for k, x in dneta.items() if k != "TTM"}
            notas.append(f"deuda del último trimestre descartada (no cierra con el pasivo): se usa la de {u_d}")

    def var(clave, pts, mx, valor, **extra):
        vs.append(dict(clave=clave, pts=pts, max=mx, valor=valor, **extra))

    # v1.5.79: estados en otra moneda (o acciones llevadas a ADR). El dividendo por acción de Yahoo viene en dólares por ADR y la ganancia por
    # acción del balance en la moneda de la empresa: National Grid daba 99 % de pago (dólares ÷ libras), KB y KEPCO 0 % (dólares ÷ wones). La
    # ganancia se pasa a dólares por ADR con el tipo de cambio del cache. Dos controles con lo que dice Yahoo del precio:
    # - si las acciones del balance no son las del ADR (Santander Brasil: 2 acciones por ADR; Coca-Cola FEMSA: 10), se llevan a las del ADR
    #   (resultado neto ÷ ganancia por acción contra capitalización ÷ precio; sin capitalización, contra precio ÷ PER);
    # - si Yahoo marca los estados en otra moneda pero vienen en dólares (Petrobras y Embraer presentan en dólares), no se convierten: se ve
    #   porque precio ÷ PER coincide con la ganancia sin convertir y no con la convertida (solo con monedas lejos del dólar).
    mon = e.get("moneda_estados") or "USD"
    otra_moneda = mon != "USD" or bool(e.get("ajuste_adr"))
    fx_e = 1.0 if mon == "USD" else V0._n(e.get("fx"))
    pr_e, per_e, mc_e = V0._n(e.get("precio")), V0._n(e.get("per")), V0._n(e.get("market_cap"))
    ancla = pr_e / per_e if (pr_e and per_e and per_e > 0) else None      # ganancia por ADR en dólares según Yahoo (precio ÷ PER)

    def _k(r):
        return r if (r and r > 0 and not (1 / 1.5 <= r <= 1.5)) else 1.0

    def k_cap(per):
        n_, g_ = neto.get(per), eps.get(per)
        return _k((n_ / g_) / (mc_e / pr_e)) if (n_ and g_ and mc_e and pr_e) else None

    if otra_moneda and fx_e and ancla and abs(math.log(fx_e)) > math.log(3):
        p0 = _periodo(eps)
        g0 = eps.get(p0) if p0 is not None else None
        if g0 and g0 > 0:
            k0 = k_cap(p0) or 1.0
            if abs(math.log(g0 * k0 / ancla)) < math.log(1.5) and abs(math.log(g0 * fx_e * k0 / ancla)) > math.log(3):
                fx_e = 1.0
                notas.append(f"estados en dólares (Yahoo los marca en {mon})")

    def acciones_por_adr(per):
        k = k_cap(per)
        if k is not None:
            return k
        g_ = eps.get(per)
        return _k(ancla / (g_ * fx_e)) if (ancla and g_ and g_ > 0 and fx_e) else 1.0

    def a_dolares_adr(valor, per):
        """Ganancia por acción del balance (en su moneda) → dólares por ADR (None sin tipo de cambio)."""
        if valor is None or not otra_moneda:
            return valor
        if fx_e is None:
            return None
        return valor * fx_e * acciones_por_adr(per)

    def estimacion_en_dolares(g):
        """Yahoo no dice en qué moneda ni por qué acción viene la estimación de los analistas (TSMC: dólares por ADR; KB: wones por acción):
        se compara con la ganancia contable en cada base posible (como v0.2, salto_homologado: la más cercana) y se pasa a dólares por ADR.
        La ganancia contable sirve solo para reconocer la base: si los dos últimos períodos dieron pérdida, se usa uno anterior."""
        if g <= 0:
            return g
        pos = [(p, eps[p]) for p in list(eps)[:4] if eps.get(p) is not None and eps[p] > 0]
        pos = pos[:2] if len([x for x in pos if x[0] in list(eps)[:2]]) else pos[:1]
        if not pos or fx_e is None:
            return None
        per_c, c = max(pos, key=lambda x: x[1])
        c_usd = a_dolares_adr(c, per_c)
        bases = {c, c * fx_e, c_usd, c_usd / fx_e}
        n_inv = V0._n(e.get("n_inv"))
        if n_inv and n_inv > 0:
            bases |= {b / n_inv for b in list(bases)}
        c_base = min(bases, key=lambda b: abs(math.log(g / b)))
        return g * c_usd / c_base

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
        per = _periodo(eps)
        e12 = a_dolares_adr(eps.get(per), per) if per is not None else None
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
        if g is not None and otra_moneda:
            g = estimacion_en_dolares(g)
        fp = (dpa / g * 100 if g > 0 else 999.0) if (dpa and g is not None) else None
        if util and not v2:
            # v1.5.78 (Guille 17/11/2026: «sí, obvio, deberías haberlo hecho así de arranque»): las utilities usan para el pago futuro el
            # mismo corte que para el pago actual sobre ganancias (segura < 70 %, crítica > 80 %)
            var("payout_futuro", _zona(fp, (70, False), (80, False), (15, 7, 0), True), 15, fp)
        elif banco and not v2:
            # v1.5.79 (Guille 17/11/2026: «bancos, misma lógica»): mismo corte que el pago actual de los bancos (segura < 50 %, crítica > 75 %)
            var("payout_futuro", _zona(fp, (50, False), (75, True), (15, 7, 0), True), 15, fp)
        else:
            var("payout_futuro", _zona(fp, (55, False), (80, True), (15, 7, 0), True), 15, fp)

    # --- crecimiento de ventas, 3 años (10) -------------------------------------------------------------------------------
    an = _anuales(ingresos)
    sgr = None
    if an:
        u = max(an)
        # v1.5.84 (Guille 23/11/2026: «ok ventas»): si la empresa separó un negocio y volvió a presentar solo los años recientes sin él
        # (data/ventas_comparables.json), el crecimiento se mide desde el primer año presentado de la misma forma (2 años como mínimo)
        desde = V0._n((e.get("ventas_comparables") or {}).get("desde"))
        b = max(u - 3, int(desde)) if desde else u - 3
        if desde and b > u - 3:
            notas.append(f"ventas desde {b}: la empresa volvió a presentar esos años sin el negocio que separó")
        if u - b >= 2 and b in an and an[b] > 0 and an[u] > 0:
            sgr = ((an[u] / an[b]) ** (1 / (u - b)) - 1) * 100
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
        elif util and v2:
            var("deuda", _zona(nd, (5.0, False), (6.0, False), (15, 7, 0), True), 15, nd)      # v1.5.71: deuda 15 y FFO ÷ Deuda 10 aparte
        elif util:
            # v1.5.79 (Guille 17/11/2026: «mitad y mitad, 15 puntos de 100 la deuda»): en las utilities los 15 puntos de deuda se reparten
            # entre deuda neta ÷ EBITDA (7,5) y FFO ÷ Deuda (7,5, abajo); el total queda sobre 100 como en el resto
            var("deuda", _zona(nd, (5.0, False), (6.0, False), (7.5, 3.5, 0), True), 7.5, nd)
        else:
            var("deuda", _zona(nd, (2.5, False), (4.5, False), (15, 7, 0), True), 15, nd)

    # --- FFO ÷ Deuda en utilities (7,5): la otra mitad de los 15 puntos de deuda (v1.5.79) -----------------------------------
    if util:
        # v1.5.78 (Guille 17/11/2026: «con esa fórmula estamos más acorde con el score que diseñé»): el documento pide el FFO ÷ Deuda de
        # S&P; si la empresa lo publica (data/ffo_deuda_utilities.json) se usa ese; si no, la cuenta de la app (flujo operativo ÷ deuda total)
        sp = e.get("ffo_deuda_sp") or {}
        fd = V0._n(sp.get("ffo_deuda"))
        if fd is not None:
            notas.append(f"FFO ÷ Deuda publicado por la empresa ({sp.get('anio')})")
        else:
            o, d = _ultimo(cfo), _ultimo(deuda)
            fd = o / d * 100 if (o is not None and d) else None
        if v2:     # v1.5.71: PROPUESTA de Claude, 10 puntos más y el total sobre 110 llevado a 100
            var("ffo_deuda", _zona(fd, (15, False), (10, False), (10, 5, 0), False), 10, fd, fuente="empresa" if sp.get("ffo_deuda") is not None else "app")
        else:
            var("ffo_deuda", _zona(fd, (15, False), (10, False), (7.5, 3.5, 0), False), 7.5, fd, fuente="empresa" if sp.get("ffo_deuda") is not None else "app")

    # --- ganancias retenidas ajustadas ÷ activos (10) (no en REITs) ---------------------------------------------------------
    # v1.5.74 (Guille 17/11/2026: «me gusta la solución»): ganancias retenidas + lo mayor entre las acciones en tesorería y las recompras de los
    # últimos 10 años fiscales. Así no se castiga a las que cancelan las acciones que recompran (Apple) y no se cuenta dos veces una recompra.
    # v1.5.88 (Guille 23/11/2026: «bancos, opción B»): en los bancos no se usa. Sus activos son unas 10 veces su patrimonio por cómo es el
    # negocio, así que el cociente da bajo aunque sean sólidos, y su capital ya lo mide el CET1 (cuyo numerador es sobre todo ganancias
    # retenidas). Solo donde hay CET1 cargado; aseguradoras, administradoras y brokers sin CET1 siguen con la medida.
    sin_reta_banco = banco and V0._n(e.get("cet1")) is not None and not v2
    if sin_reta_banco:
        notas.append("ganancias retenidas ÷ activos no se usa en bancos: el CET1 ya mide su capital")
    if not reit and not sin_reta_banco:
        r, t, a = _ultimo(rr), _ultimo(tes), _ultimo(at)
        an_r = _anuales(recomp)
        rec10 = sum(abs(v) for k, v in an_r.items() if k > max(an_r) - RECOMPRAS_ANIOS) if an_r else 0.0
        suma = abs(t or 0) if v2 else max(abs(t or 0), rec10)      # v2 (16/11): ganancias retenidas + |acciones en tesorería|
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
    racha, sin_suba = (h.get("racha_subas") or 0, h.get("anios_sin_suba") or 0) if medible else (0, 0)
    # v1.5.83 (Guille 21/11/2026: «no lo consideres como recorte sino como dividendo errático»): 3 o más años seguidos sin subir el
    # dividendo, si terminaron en los últimos ERRATICO_ANIOS años (o siguen), hacen al dividendo errático: techo 80 y sin premio, como 3
    # recortes en 10 años. Se mide en la moneda en que la empresa emite el dividendo: en dólares o con los pagos de su bolsa de origen.
    # Con la serie convertida desde los pagos del ADR el tipo de cambio no deja ver una suba del 3 %: queda sin medir hasta tener los
    # pagos de la bolsa de origen (bajar_dividendos_locales.bat).
    congel = []
    if v2:
        pass                                   # v2: el congelamiento crónico resta 5 y saca el premio (abajo), no hace errático
    elif medible and e.get("fuente_historial") != "convertido":
        congel = congelamientos(h)
        if sin_suba >= 3 and ult and ult not in congel:
            congel.append(ult)
    elif e.get("fuente_historial") == "convertido":
        notas.append("congelamiento sin medir: falta el dividendo de la bolsa de origen")
    congelado = [a for a in congel if ult and a > ult - ERRATICO_ANIOS]
    if congelado:
        notas.append(f"dividendo congelado 3 años o más hasta {max(congelado)}: se trata como errático")
    erratico = sum(1 for a in eventos if ult and a > ult - ERRATICO_ANIOS) >= ERRATICO_RECORTES or bool(congelado)
    variable = tk in VARIABLE_DECLARADA or erratico
    if hace is not None:
        if hace < 5:
            ajustes.append(("recorte_menos_5", -25))
        elif hace <= 10:
            ajustes.append(("recorte_5_10", -10))
    # el bono se anula si la cobertura (o su reemplazo) o el payout principal están en zona crítica
    critica = any(v["pts"] == 0 for v in vs if v["clave"] in ("cobertura", "cet1", "solvencia", "fcf_payout", "affo", "eps_payout"))
    if v2 and sin_suba >= 3:
        ajustes.append(("congelamiento", -5))           # v2 (Word): congelamiento crónico (3 o más años sin subas, vigente): −5 y pierde el bono
    elif v2 and not variable and not critica and racha >= 10:
        ajustes.append(("aristocrata", 10) if racha >= 25 else ("aspirante", 5))
    elif not v2 and not variable and not critica and racha >= 10:
        # v1.5.78 (Guille 17/11/2026: «de acuerdo, vamos con eso»): si el dividendo regular creció menos de CRECIMIENTO_SIMBOLICO % por año en
        # los últimos CRECIMIENTO_ANIOS años completos (aumentos de un centavo para no perder la racha), el premio queda en la mitad.
        # Se mide en la moneda del dividendo, con la misma serie que la racha.
        tasa = {int(k): x for k, x in (h.get("tasa") or {}).items()}
        u0 = h.get("ultimo_completo")
        crec = None
        if u0 and tasa.get(u0) and tasa.get(u0 - CRECIMIENTO_ANIOS):
            crec = ((tasa[u0] / tasa[u0 - CRECIMIENTO_ANIOS]) ** (1 / CRECIMIENTO_ANIOS) - 1) * 100
        simbolico = crec is not None and crec < CRECIMIENTO_SIMBOLICO
        if simbolico:
            notas.append(f"aumentos simbólicos: el dividendo creció {crec:.1f} % por año en {CRECIMIENTO_ANIOS} años (medio premio)")
        if racha >= 25:
            ajustes.append(("aristocrata", 5 if simbolico else 10))
        else:
            ajustes.append(("aspirante", 2.5 if simbolico else 5))

    # --- trampa de rendimiento -------------------------------------------------------------------------------------------------
    rend = V0._n(e.get("rend"))
    trampa = rend is not None and rend > 0.08 and fcf_pay is not None and fcf_pay > 100
    if trampa:
        ajustes.append(("trampa_rendimiento", -30))

    # v1.5.85 (Guille 23/11/2026: «si hay divi errático y recorte castiga el que reste más puntos de los 2»): con dividendo errático (o
    # variable) y recorte no se castiga doble. El techo de 80 resta lo que el puntaje tenga por encima de 80; el recorte, 25 o 10. Cuenta
    # solo el que resta más: si es el techo, el recorte no se suma; si es el recorte, el puntaje queda debajo de 80 y el techo no actúa.
    rec_aj = next(((k, x) for k, x in ajustes if k in ("recorte_menos_5", "recorte_5_10")), None)
    if variable and rec_aj and not v2:
        sin_recorte = base + sum(x for k, x in ajustes if k != rec_aj[0])
        resta_techo = max(0.0, sin_recorte - 80)
        cual = "errático" if erratico else "variable"
        rt = round(resta_techo, 1)
        rt_txt = f"-{rt:g}" if rt else "0"
        if resta_techo >= -rec_aj[1]:
            ajustes.remove(rec_aj)
            notas.append(f"recorte ({rec_aj[1]:g}) y dividendo {cual}: cuenta el que resta más, el techo de 80 ({rt_txt})")
        else:
            notas.append(f"recorte ({rec_aj[1]:g}) y dividendo {cual}: cuenta el que resta más, el recorte (el techo de 80 restaría {rt_txt})")

    total = base + sum(x for _, x in ajustes)
    # --- frenos -------------------------------------------------------------------------------------------------------------------
    an_n = _anuales(neto)
    if an_n and an_n[max(an_n)] < 0:
        # v1.5.88 (Guille 23/11/2026, Sony: «vamos con la B»): si la pérdida viene de operaciones discontinuadas (una escisión o una venta,
        # muchas veces un ajuste contable sin salida de caja) y el resultado de las operaciones que siguen fue positivo ese mismo año, el freno
        # mira lo que sigue: el dividendo lo paga el negocio que queda
        u_n = max(an_n)
        cont = _anuales(S("r", "Resultado de operaciones continuas")).get(u_n)
        if cont is not None and cont > 0 and not v2:
            notas.append(f"pérdida de {u_n} por operaciones discontinuadas: las que siguen ganaron, sin freno por pérdida")
        else:
            topes.append(("perdida", 20))
    if cob is not None and not banco and cob < 1.5:
        topes.append(("cobertura_letal", 20))
    if trampa:
        topes.append(("trampa_rendimiento", 40))
    if variable:
        topes.append(("dividendo_variable", 80))
    for _, t in topes:
        total = min(total, t)
    total = max(0, min(100 if v2 else TOPE_SCORE, int(round(round(total, 6)))))     # v1.5.78: tope 99 (Guille 17/11/2026, por estética)
    return {"score": total, "categoria": categoria(total), "variables": vs, "ajustes": ajustes, "topes": topes, "notas": notas,
            "base": round(base, 1), "variable": variable, "erratico": erratico, "congelado_hasta": max(congelado) if congelado else None}


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


def ventas_comparables(ticker, ruta=None):
    """Entrada de data/ventas_comparables.json para el ticker ({"desde", "motivo", "fuente", "revisado"}) o None. v1.5.84."""
    ruta = ruta or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ventas_comparables.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            return (json.load(f).get("empresas") or {}).get(ticker)
    except (OSError, ValueError):
        return None


def financiera_propia(ticker, ruta=None):
    """v1.5.76: cifras del negocio industrial de las empresas con financiera propia (data/financieras_propias.json), o None."""
    ruta = ruta or os.path.join(AQUI, "data", "financieras_propias.json")
    if ruta not in _FINANCIERAS:
        try:
            _FINANCIERAS[ruta] = json.load(open(ruta, encoding="utf-8")).get("datos", {})
        except (OSError, ValueError):
            _FINANCIERAS[ruta] = {}
    return _FINANCIERAS[ruta].get(ticker)


_FFO_DEUDA = {}


def ffo_deuda_sp(ticker, ruta=None):
    """v1.5.78: FFO ÷ Deuda publicado por la utility (data/ffo_deuda_utilities.json) o None si no lo publica o no se cargó."""
    ruta = ruta or os.path.join(AQUI, "data", "ffo_deuda_utilities.json")
    if ruta not in _FFO_DEUDA:
        try:
            _FFO_DEUDA[ruta] = json.load(open(ruta, encoding="utf-8")).get("datos", {})
        except (OSError, ValueError):
            _FFO_DEUDA[ruta] = {}
    d = _FFO_DEUDA[ruta].get(ticker)
    return d if d and d.get("ffo_deuda") is not None else None
