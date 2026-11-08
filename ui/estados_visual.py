"""v1.5.47 (Guille aprobó la maqueta de KO, 08/11/2026): Estados Financieros visuales.

La solapa «Estados Financieros» de la ficha se divide en subsolapas (Estado de Resultados · Balance · Estado de Flujo de Efectivo · Ratios Financieros).
En cada una, arriba van tarjetas con gráficos de barras (los últimos 4 años fiscales y, en oscuro, los últimos 12 meses) con una explicación corta y,
cuando tiene sentido, una línea punteada de referencia; debajo, la tabla de siempre. Todo sale de los estados guardados (Yahoo), sin datos nuevos.
"""
import html

from data import af_tablas as _T

try:
    from data.af_v4 import NOMBRES_MONEDA
except Exception:  # noqa: BLE001
    NOMBRES_MONEDA = {}


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def series(est):
    """(años con el TTM al final, clave del TTM, {clave: {año: valor}}) con todo lo que dibujan los gráficos."""
    fy, ttm = _T._anios(est)
    anios = fy + ([ttm] if ttm else [])
    S = lambda g, r: _T._serie(est, g, r)      # noqa: E731
    ing = S("resultados", "Ingresos")
    acc = S("resultados", "Acciones promedio (diluidas)")
    fcf = S("flujo", "Flujo de efectivo libre")
    div = S("flujo", "Dividendos pagados")
    capex = S("flujo", "Inversión en activos fijos (CAPEX)")
    crec = {}
    for i, a in enumerate(fy):
        if i and ing.get(a) and ing.get(fy[i - 1]) and ing[fy[i - 1]] > 0:
            crec[a] = ing[a] / ing[fy[i - 1]] - 1
    # sin barra de 12 meses: comparar los últimos 12 meses con el último año fiscal mezclaría trimestres repetidos
    R = lambda r: S("ratios", r)      # noqa: E731
    return anios, ttm, {
        "ing": ing, "crec": crec, "mbr": R("Margen bruto"), "mop": R("Margen operativo"), "mne": R("Margen neto"),
        "eps": S("resultados", "Ganancia por acción (diluida)"), "acc": acc,
        "caja": S("balance", "Caja e inversiones de corto plazo"), "deuda": S("balance", "Deuda total"), "pat": S("balance", "Patrimonio neto"),
        "dne": R("Deuda neta / EBITDA"), "liq": R("Liquidez corriente (activo / pasivo corriente)"),
        "roe": R("Retorno sobre el patrimonio (ROE)"), "roic": R("Retorno sobre el capital invertido (ROIC)"),
        "cob": R("Cobertura de intereses (resultado operativo / intereses)"),
        "fco": S("flujo", "Flujo de efectivo operativo"), "fcf": fcf,
        "capex": {a: abs(v) for a, v in capex.items() if v is not None},
        "mfcf": R("Margen de flujo de efectivo libre"),
        "fps": {a: fcf[a] / acc[a] for a in anios if fcf.get(a) is not None and acc.get(a)},
        "div": {a: abs(v) for a, v in div.items() if v is not None},
        "pay": {a: abs(div[a]) / fcf[a] for a in anios if div.get(a) is not None and fcf.get(a) and fcf[a] > 0},
    }


# (clave, título, explicación, referencia (valor, texto) o None, tipo: "$" monto · "pct" · "x" veces · "ps" por acción · "acc" acciones)
TARJETAS = {
    "resultados": [
        ("ing", "Ingresos", "Lo que vende la empresa en el año. Un negocio sano los hace crecer con el tiempo, sin saltos bruscos.", None, "$"),
        ("crec", "Crecimiento de los ingresos", "Cuánto crecieron las ventas contra el año anterior. Subas parejas indican un negocio estable; saltos grandes, uno cíclico.", None, "pct"),
        ("mbr", "Margen bruto", "De cada 100 que vende, cuánto le queda después del costo de lo vendido. Un margen alto suele indicar marca o poder de precio.", None, "pct"),
        ("mop", "Margen operativo", "De cada 100 que vende, cuánto le queda después de pagar todos los costos del negocio. Altos y estables suelen indicar una ventaja competitiva.", (0.15, "Referencia: más de 15%"), "pct"),
        ("eps", "Ganancia por acción", "Lo que gana la empresa por cada acción. Si crece año tras año, sostiene la suba del precio y del dividendo.", None, "ps"),
        ("acc", "Acciones en circulación", "Si baja, la empresa recompra acciones y cada accionista es dueño de una porción mayor. Si sube, hay dilución.", None, "acc"),
    ],
    "balance": [
        ("caja", "Caja e inversiones de corto plazo", "El dinero disponible: efectivo e inversiones que se pueden vender rápido.", None, "$"),
        ("deuda", "Deuda total", "Todo lo que debe a bancos y tenedores de bonos, de corto y largo plazo.", None, "$"),
        ("dne", "Deuda neta / EBITDA", "Cuántos años de EBITDA haría falta para pagar la deuda neta (deuda menos caja). Si es negativo, tiene más caja que deuda.", (2.0, "Referencia: menos de 2 veces"), "x"),
        ("liq", "Liquidez corriente", "Lo que tiene para el corto plazo dividido por lo que vence en el año. Por encima de 1, puede cubrir lo que vence.", (1.0, "Referencia: más de 1 vez"), "x"),
        ("roe", "Retorno sobre el patrimonio (ROE)", "Cuánto gana por cada dólar que pusieron los accionistas. La deuda lo puede inflar: conviene mirarlo junto al ROIC.", (0.15, "Referencia: más de 15%"), "pct"),
        ("roic", "Retorno sobre el capital invertido (ROIC)", "Cuánto rinde cada dólar que pusieron accionistas y acreedores. Mide qué tan bien invierte la gerencia.", (0.12, "Referencia: más de 12%"), "pct"),
    ],
    "flujo": [
        ("fco", "Flujo de efectivo operativo", "El efectivo que genera el negocio con su actividad habitual. Es más difícil de maquillar que la ganancia contable.", None, "$"),
        ("capex", "Inversión en activos fijos (CAPEX)", "Lo que gasta en fábricas, equipos y tecnología para mantener y hacer crecer el negocio.", None, "$"),
        ("fcf", "Flujo de efectivo libre", "Flujo operativo menos CAPEX: lo que queda para dividendos, recompras o pagar deuda.", None, "$"),
        ("mfcf", "Margen de flujo libre", "Qué parte de las ventas se convierte en caja libre. Las mejores empresas lo mantienen alto y estable.", (0.10, "Referencia: más de 10%"), "pct"),
        ("fps", "Flujo libre por acción", "La caja libre que le corresponde a cada acción. Si crece, crece lo que la empresa puede devolver al accionista.", None, "ps"),
        ("pay", "Dividendos / flujo libre", "Qué parte de la caja libre se va en dividendos. Si se acerca al 100%, el dividendo queda con poco margen.", (0.60, "Referencia: menos de 60%"), "pct"),
    ],
    "ratios": [
        ("mne", "Margen neto", "De cada 100 que vende, cuánto termina como ganancia final, después de intereses e impuestos.", None, "pct"),
        ("cob", "Cobertura de intereses", "Cuántas veces la ganancia operativa paga los intereses. Cuanto más alta, más tranquila está frente a la deuda.", (5.0, "Referencia: más de 5 veces"), "x"),
    ],
}


def _escala(vals):
    """(divisor, texto) para montos: miles de millones si algún valor pasa los mil millones; si no, millones."""
    m = max((abs(v) for v in vals if v is not None), default=0)
    return (1e9, "miles de millones") if m >= 1e9 else (1e6, "millones")


def _fmt(v, tipo, div=1.0):
    if v is None:
        return "—"
    if tipo == "pct":
        return f"{v * 100:.0f}%".replace("-0%", "0%")
    if tipo == "x":
        return f"{v:.1f}x"
    if tipo == "ps":
        return f"{v:.2f}"
    x = v / div
    if tipo == "acc" and abs(x) < 10:
        return f"{x:.2f}"
    return f"{x:,.1f}" if abs(x) < 100 else f"{x:,.0f}"


def tarjeta(clave, tit, txt, ref, tipo, anios, ttm, s, moneda=None):
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
        txt_ref = f"{ref[0] * 100:.0f}%" if tipo == "pct" else f"{ref[0]:g}x"
        linea = f'<div class="ev-ref" style="bottom:{y(ref[0]) + 34:.0f}px"><span>{txt_ref}</span></div>'
    cero = f'<div class="ev-cero" style="bottom:{y(0) + 34:.0f}px"></div>' if lo < 0 else ""
    pie = f" <b>{html.escape(ref[1])}</b>." if ref else ""
    return (f'<div class="ev-t"><h4>{html.escape(tit)}<small>{html.escape(unidad)}</small></h4><p>{html.escape(txt)}{pie}</p>'
            f'<div class="ev-g">{linea}{cero}{"".join(barras)}</div></div>')


def graficos_html(est, clave):
    """La grilla de tarjetas de una subsolapa ('' si no hay datos)."""
    if not est or clave not in TARJETAS:
        return ""
    anios, ttm, s = series(est)
    if not anios:
        return ""
    t = "".join(tarjeta(*x, anios, ttm, s, est.get("moneda")) for x in TARJETAS[clave])
    return f'<div class="ev-grid">{t}</div>' if t else ""


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
.ev-ref span{position:absolute;left:0;top:-16px;font-size:11px;color:#64748b;background:#fff;padding:0 3px}
.ev-cero{position:absolute;left:0;right:0;border-top:1px solid #cbd5e1}
.mc-oscuro .ev-t{background:#111827;border-color:#1f2937}.mc-oscuro .ev-t h4{color:#e5e7eb}.mc-oscuro .ev-t p{color:#9ca3af}.mc-oscuro .ev-ref span{background:#111827}
@media (max-width:1100px){.ev-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){.ev-grid{grid-template-columns:1fr}}
"""
