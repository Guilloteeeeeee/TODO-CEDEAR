"""
v1.5.58 (Guille, 10/11/2026: «SÍ, DE ACUERDO» con sumar años desde la SEC): años fiscales viejos de la SEC (data.sec.gov, «companyfacts», gratis)
para el archivo histórico propio. Lo usa bajar_sec.py (en la PC de Guille: data.sec.gov está bloqueado desde la nube).

Reglas (las mismas que probó piloto_sec.py el 08/11/2026):
- Solo informes anuales (10-K, 20-F, 40-F y sus correcciones) y, en los flujos, solo períodos de un año completo (350 a 380 días).
- Si un año aparece en varios informes (cada informe repite los años anteriores, a veces corregidos), gana el presentado más nuevo.
- Las empresas cambian de concepto con los años (por ejemplo, ventas de SalesRevenueNet a RevenueFromContractWithCustomer… en 2018):
  se usa el primero de la lista que tenga ese año.
- Los signos se dejan como los muestra Yahoo: CAPEX y dividendos pagados en negativo. El flujo de efectivo libre = operativo − CAPEX.
- La ganancia por acción de la SEC está ajustada por los splits ocurridos hasta la fecha en que se presentó el informe. Esa fecha se guarda como
  «captura_acc» del año: al leerlo, data/historico.estados_completos la ajusta por los splits posteriores (mismo mecanismo que para Yahoo).
"""
import datetime as _dt

CONCEPTOS = {
    "Ingresos": [("us-gaap", "Revenues"), ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
                 ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"), ("us-gaap", "SalesRevenueNet"),
                 ("us-gaap", "RevenuesNetOfInterestExpense"), ("ifrs-full", "Revenue")],
    "Resultado operativo": [("us-gaap", "OperatingIncomeLoss"), ("ifrs-full", "ProfitLossFromOperatingActivities")],
    "Resultado neto": [("us-gaap", "NetIncomeLoss"), ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"), ("ifrs-full", "ProfitLoss")],
    "Ganancia por acción (diluida)": [("us-gaap", "EarningsPerShareDiluted"), ("us-gaap", "EarningsPerShareBasicAndDiluted"),
                                      ("ifrs-full", "DilutedEarningsLossPerShare"), ("ifrs-full", "BasicAndDilutedEarningsLossPerShare")],
    "Activo total": [("us-gaap", "Assets"), ("ifrs-full", "Assets")],
    "Patrimonio neto": [("us-gaap", "StockholdersEquity"), ("ifrs-full", "EquityAttributableToOwnersOfParent"), ("ifrs-full", "Equity")],
    "Flujo de efectivo operativo": [("us-gaap", "NetCashProvidedByUsedInOperatingActivities"), ("ifrs-full", "CashFlowsFromUsedInOperatingActivities")],
    "Inversión en activos fijos (CAPEX)": [("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
                                           ("ifrs-full", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities")],
    "Dividendos pagados": [("us-gaap", "PaymentsOfDividendsCommonStock"), ("us-gaap", "PaymentsOfDividends"),
                           ("ifrs-full", "DividendsPaidClassifiedAsFinancingActivities")],
}
GRUPO = {"Ingresos": "resultados", "Resultado operativo": "resultados", "Resultado neto": "resultados", "Ganancia por acción (diluida)": "resultados",
         "Activo total": "balance", "Patrimonio neto": "balance",
         "Flujo de efectivo operativo": "flujo", "Inversión en activos fijos (CAPEX)": "flujo", "Dividendos pagados": "flujo"}
TIPO = {"Ganancia por acción (diluida)": "eps"}          # el resto, montos ("m"), como en paquetes_yahoo
NEGATIVOS = ("Inversión en activos fijos (CAPEX)", "Dividendos pagados")   # Yahoo los muestra en negativo
INSTANTANEOS = {"Activo total", "Patrimonio neto"}      # se miden a una fecha (balance), no durante un año
FORMULARIOS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")
TOLERANCIA_SOLAPE = 0.05                                 # en el año que tienen los dos, SEC y Yahoo tienen que coincidir dentro de 5 %
EPS_ROT, NETO_ROT = "Ganancia por acción (diluida)", "Resultado neto"
EPS_MINIMA = 0.10                                        # para medir la base por acción no se usan ganancias casi nulas (el redondeo pesa)
BASE_MIN, BASE_MAX = 0.8, 1.25                           # v1.5.63: un factor entre 0,8 y 1,25 no es otra base (los ADR van de 0,25 a 80): se toma 1
SALTO_UNION = (0.6, 1.6)                                 # v1.5.63: control de la unión SEC → Yahoo (acciones implícitas = resultado neto ÷ ganancia por acción)


def anuales(facts, rotulo):
    """{año: (valor, moneda, concepto, fecha fin, formulario, presentado)} de los informes anuales."""
    out = {}
    for tax, concepto in CONCEPTOS[rotulo]:
        c = ((facts.get("facts") or {}).get(tax) or {}).get(concepto)
        if not c:
            continue
        este = {}
        for unidad, filas in (c.get("units") or {}).items():
            for f in filas:
                if f.get("form") not in FORMULARIOS or f.get("val") is None or not f.get("end"):
                    continue
                fin = f["end"]
                if rotulo not in INSTANTANEOS:
                    ini = f.get("start")
                    if not ini:
                        continue
                    dias = (_dt.date.fromisoformat(fin) - _dt.date.fromisoformat(ini)).days
                    if not 350 <= dias <= 380:      # solo años completos (no trimestres)
                        continue
                anio = int(fin[:4])
                prev = este.get(anio)
                if not prev or f.get("filed", "") > prev[5]:
                    este[anio] = (float(f["val"]), unidad.split("/")[0], f"{tax}:{concepto}", fin, f.get("form"), f.get("filed", ""))
        for anio, v in este.items():
            out.setdefault(anio, v)
    return out


def a_anios(facts):
    """companyfacts -> {"2015": {"moneda", "presentado", "resultados": {rot: v}, "balance": {…}, "flujo": {…}}} con los rótulos de la app.
    La moneda de cada año es la de sus ingresos (o la más repetida); los datos en otra moneda ese año se descartan."""
    por_rot = {r: anuales(facts, r) for r in CONCEPTOS}
    anios = sorted({a for v in por_rot.values() for a in v})
    out = {}
    for a in anios:
        vals = {r: por_rot[r][a] for r in CONCEPTOS if a in por_rot[r]}
        monedas = [v[1] for v in vals.values()]
        moneda = vals["Ingresos"][1] if "Ingresos" in vals else max(set(monedas), key=monedas.count)
        rec = {"moneda": moneda}
        for r, v in vals.items():
            if v[1] != moneda:
                continue
            x = -abs(v[0]) if r in NEGATIVOS else v[0]
            rec.setdefault(GRUPO[r], {})[r] = x
        fl = rec.get("flujo") or {}
        if fl.get("Flujo de efectivo operativo") is not None and fl.get("Inversión en activos fijos (CAPEX)") is not None:
            fl["Flujo de efectivo libre"] = fl["Flujo de efectivo operativo"] + fl["Inversión en activos fijos (CAPEX)"]
        eps = vals.get("Ganancia por acción (diluida)")
        rec["presentado"] = (eps[5] if eps else max((v[5] for v in vals.values()), default="")) or ""
        if any(rec.get(g) for g in ("resultados", "balance", "flujo")):
            out[str(a)] = rec
    return out


def coincide(sec_anios, reg):
    """¿La SEC y lo guardado (Yahoo) dicen lo mismo en los años que tienen los dos? -> (True/False/None si no hay año en común, detalle).
    Se mira el año en común más nuevo, en la misma moneda: alcanza con que coincida el resultado neto o los ingresos (dentro de 5 %).
    v1.5.61: primero el resultado neto. Los ingresos solos dejaban afuera a bancos, financieras y empresas con impuestos especiales
    (Altria, Diageo, Morgan Stanley, American Express, Berkshire…), donde cada fuente arma la cifra de ventas a su manera."""
    guard = (reg or {}).get("anios") or {}
    comunes = sorted((a for a in set(sec_anios) & set(guard) if guard[a].get("fuente") != "SEC"), reverse=True)
    for a in comunes:
        s, g = sec_anios[a], guard[a]
        if s.get("moneda") != g.get("moneda", "USD"):
            return False, f"{a}: la SEC informa en {s.get('moneda')} y lo guardado está en {g.get('moneda', 'USD')}"
        dets, alguno = [], False
        for rot in (NETO_ROT, "Ingresos"):
            vs, vg = (s.get("resultados") or {}).get(rot), (g.get("resultados") or {}).get(rot)
            if vs is None or vg in (None, 0):
                continue
            dif = abs(vs - vg) / abs(vg)
            dets.append(f"{rot}: SEC {vs:,.0f} vs guardado {vg:,.0f} ({dif:.1%})")
            alguno = alguno or dif <= TOLERANCIA_SOLAPE
        if dets:
            return alguno, f"{a} " + "; ".join(dets)
    return None, "sin año en común para comparar"


def factor_por_accion(sec_anios, reg, splits=None):
    """v1.5.61: ¿la ganancia por acción de la SEC está en la misma base que la de lo guardado (Yahoo)? En los ADR muchas veces no: la SEC informa
    por acción ordinaria y Yahoo por ADR (TSMC: 1 ADR = 5 acciones; Coca-Cola FEMSA: 1 ADR = 80 acciones). También pasa cuando Yahoo rehízo
    sus cifras por un cambio en la cantidad de acciones que no figura como split.
    Se mide en el año más nuevo que tienen los dos, con el resultado neto coincidiendo (dentro de 5 %) y las dos ganancias por acción llevadas a
    hoy por los splits posteriores a su fecha: factor = Yahoo / SEC. Dentro de 5 % se toma 1 (misma base).
    -> (factor, detalle); factor None = no hay con qué comparar (se deja como viene)."""
    from data.historico import factor_despues
    guard = (reg or {}).get("anios") or {}
    for a in sorted((a for a in set(sec_anios) & set(guard) if guard[a].get("fuente") != "SEC"), reverse=True):
        s, g = sec_anios[a], guard[a]
        rs, rg = s.get("resultados") or {}, g.get("resultados") or {}
        es, ey, ns, ny = rs.get(EPS_ROT), rg.get(EPS_ROT), rs.get(NETO_ROT), rg.get(NETO_ROT)
        if None in (es, ey, ns, ny) or not ny or min(abs(es), abs(ey)) < EPS_MINIMA:
            continue
        if abs(ns - ny) / abs(ny) > TOLERANCIA_SOLAPE:
            continue
        es_hoy = es / factor_despues(splits, s.get("presentado") or "")
        ey_hoy = ey / factor_despues(splits, g.get("captura_acc", g.get("captura", "")))
        f = ey_hoy / es_hoy
        if f <= 0:
            continue
        if BASE_MIN <= f <= BASE_MAX:
            return 1.0, f"{a}: misma base por acción" + (f" (diferencia de {abs(f - 1):.0%}, no es otra base)" if abs(f - 1) > TOLERANCIA_SOLAPE else "")
        return round(f, 4), f"{a}: por acción, Yahoo {ey:,.4g} y SEC {es:,.4g} (factor {f:,.3g})"
    return None, "sin año en común con ganancia por acción para comparar"


def diagnostico(facts):
    """Para «sin datos»: qué trae el archivo de la SEC (nombre, cantidad de conceptos y cuáles de los nuestros tiene, con sus formularios)."""
    f = facts.get("facts") or {}
    partes = [f"entidad «{facts.get('entityName', '?')}»"] + [f"{tax}: {len(v)} conceptos" for tax, v in f.items()]
    vistos = []
    for rot, lista in CONCEPTOS.items():
        for tax, concepto in lista:
            c = (f.get(tax) or {}).get(concepto)
            if c:
                formas = sorted({x.get("form") for filas in (c.get("units") or {}).values() for x in filas if x.get("form")})
                vistos.append(f"{concepto} ({', '.join(formas[:4])})")
                break
    return "; ".join(partes) + ("; nuestros conceptos: " + ", ".join(vistos[:5]) if vistos else "; ninguno de nuestros conceptos")


def union_por_accion(reg, splits=None):
    """v1.5.63: control final de la unión entre el último año de la SEC y el primero de Yahoo. Compara las acciones implícitas
    (resultado neto ÷ ganancia por acción, ya ajustadas por splits) de los dos años: si cambian más de lo normal (menos de 0,6 o más de 1,6
    veces), la ganancia por acción de la SEC quedó en otra base. -> (True/False/None si no hay con qué comparar, relación)."""
    from data.historico import factor_despues
    an = (reg or {}).get("anios") or {}

    def acciones(a):
        r = an[a].get("resultados") or {}
        e, n = r.get(EPS_ROT), r.get(NETO_ROT)
        if not e or not n or e <= 0 or n <= 0:
            return None
        return n / (e / factor_despues(splits, an[a].get("captura_acc", an[a].get("captura", ""))))

    sec = [a for a in sorted(an, reverse=True) if an[a].get("fuente") == "SEC" and acciones(a)]
    yah = [a for a in sorted(an) if an[a].get("fuente") != "SEC" and acciones(a)]
    if not sec or not yah:
        return None, None
    rel = acciones(sec[0]) / acciones(yah[0])
    return SALTO_UNION[0] <= rel <= SALTO_UNION[1], round(rel, 2)


def quitar_por_accion(reg):
    """Saca la ganancia por acción de los años de la SEC (cuando no se pudo poner en la base de Yahoo). -> años tocados."""
    tocados = []
    for a, r in ((reg or {}).get("anios") or {}).items():
        if r.get("fuente") == "SEC" and EPS_ROT in (r.get("resultados") or {}):
            r["resultados"] = {k: v for k, v in r["resultados"].items() if k != EPS_ROT}
            r["sin_por_accion"] = True
            tocados.append(a)
    return sorted(tocados)


def por_informe(facts, rotulo=None):
    """v1.5.66/67: {presentado: {año: valor}} de un rótulo (por defecto la ganancia por acción) tal como vino en CADA informe anual (cada
    10-K/20-F trae 2 o 3 años). Sirve para saber en qué base está cada informe: entre dos informes la base cambia si hubo un split o un cambio
    de acciones por ADR."""
    rotulo = rotulo or EPS_ROT
    out = {}
    for tax, concepto in CONCEPTOS[rotulo]:
        c = ((facts.get("facts") or {}).get(tax) or {}).get(concepto)
        if not c:
            continue
        for unidad, filas in (c.get("units") or {}).items():
            for f in filas:
                if f.get("form") not in FORMULARIOS or f.get("val") is None or not f.get("end") or not f.get("start") or not f.get("filed"):
                    continue
                dias = (_dt.date.fromisoformat(f["end"]) - _dt.date.fromisoformat(f["start"])).days
                if not 350 <= dias <= 380:
                    continue
                out.setdefault(f["filed"], {}).setdefault(int(f["end"][:4]), float(f["val"]))
    return out


def eps_por_informe(facts):
    return por_informe(facts, EPS_ROT)


def _parecidos(a, b, tol=TOLERANCIA_SOLAPE):
    return a is not None and b is not None and b != 0 and abs(a - b) / abs(b) <= tol


def factores_por_informe(facts, reg, splits=None):
    """v1.5.66: factor de cada informe de la SEC para llevar su ganancia por acción a la base de HOY de Yahoo.
    - directo: el informe comparte años con Yahoo -> mediana de (Yahoo llevado a hoy ÷ SEC) en esos años;
    - encadenado: el informe no comparte años con Yahoo -> se encadena con el informe más nuevo que ya tiene factor y comparte un año.
    v1.5.67: solo cuentan los años en que el RESULTADO NETO también coincide (dentro de 5 %) entre los dos lados: si un informe cuenta la
    ganancia de otra forma (por ejemplo, con o sin un negocio vendido o escindido, como Johnson & Johnson con Kenvue), ese año no sirve para
    medir la base. Y los años que se usan tienen que dar el mismo factor (dentro de 10 %); si no, el informe no se puede verificar.
    Un factor entre 0,8 y 1,25 se toma como 1; uno fuera de 1/250 a 250 se descarta. -> {presentado: (factor, "directo"/"encadenado")}"""
    from statistics import median

    from data.historico import factor_despues
    yh, yn = {}, {}
    for a, g in ((reg or {}).get("anios") or {}).items():
        if g.get("fuente") == "SEC":
            continue
        r = g.get("resultados") or {}
        e = r.get(EPS_ROT)
        if e is not None and abs(e) >= EPS_MINIMA:
            yh[int(a)] = e / factor_despues(splits, g.get("captura_acc", g.get("captura", "")))
            yn[int(a)] = r.get(NETO_ROT)
    inf, net = por_informe(facts, EPS_ROT), por_informe(facts, NETO_ROT)

    def coherente(rs):
        return rs and max(rs) / min(rs) <= 1.10 if all(x > 0 for x in rs) else False

    fac = {}
    for p in inf:
        rs = [yh[y] / v for y, v in inf[p].items() if y in yh and abs(v) >= EPS_MINIMA and yh[y] * v > 0
              and _parecidos((net.get(p) or {}).get(y), yn.get(y))]
        if coherente(rs):
            fac[p] = (median(rs), "directo")
    for p in sorted(inf, reverse=True):
        if p in fac:
            continue
        for q in sorted(q for q in fac if q > p):          # el informe más nuevo y más cercano primero
            rs = [inf[q][y] / v for y, v in inf[p].items() if y in inf[q] and abs(v) >= EPS_MINIMA and abs(inf[q][y]) >= EPS_MINIMA
                  and inf[q][y] * v > 0 and _parecidos((net.get(p) or {}).get(y), (net.get(q) or {}).get(y))]
            if coherente(rs):
                fac[p] = (fac[q][0] * median(rs), "encadenado")
                break
    out = {}
    for p, (f, modo) in fac.items():
        if not 1 / 250 <= f <= 250:
            continue
        out[p] = (1.0 if BASE_MIN <= f <= BASE_MAX else round(f, 4), modo)
    return out


def llevar_a_base(sec_anios, facts, reg, splits=None, hoy=None):
    """v1.5.66: pasa la ganancia por acción de cada año de la SEC a la base de hoy de Yahoo con el factor de SU informe. El año queda con
    "base_acc" = hoy (ya no se le aplican los splits anteriores a hoy), "factor_accion" si no es 1 y "modo_accion". Un año cuyo informe no se
    pudo llevar a la base de Yahoo queda sin ganancia por acción ("sin_por_accion"). -> (años, factores, años sin base)"""
    hoy = hoy or _dt.date.today().isoformat()
    fac = factores_por_informe(facts, reg, splits)
    out, sin = {}, []
    for a, rec in sec_anios.items():
        rec = {k: (dict(v) if isinstance(v, dict) else v) for k, v in rec.items()}
        r = rec.get("resultados") or {}
        if EPS_ROT in r:
            p = rec.get("presentado")
            if p in fac:
                f, modo = fac[p]
                r[EPS_ROT] = r[EPS_ROT] * f
                rec["base_acc"], rec["modo_accion"] = hoy, modo
                if f != 1.0:
                    rec["factor_accion"] = f
            else:
                r.pop(EPS_ROT)
                rec["sin_por_accion"] = True
                sin.append(a)
        out[a] = rec
    return out, fac, sorted(sin)
