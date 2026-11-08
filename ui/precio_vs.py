"""v1.5.49 (Guille aprobó la maqueta de Netflix, 08/11/2026): «Precio vs fundamentales del negocio», en la solapa Valuación de la ficha.

Compara cuánto cambió el precio de la acción con cuánto cambió el negocio, desde el cierre del primer año fiscal que tenemos hasta hoy.
- Todo en % de cambio desde el inicio (arranca en 0%): es lo mismo que «base 100», pero se lee directo («+120%»).
- Por defecto, contra la ganancia por acción (lo que miraba Peter Lynch). Se puede cambiar a ventas por acción o flujo libre por acción, o ver las tres.
  Van «por acción» para que sean comparables con el precio (si la empresa recompra acciones, cada acción tiene una parte mayor del negocio).
- Precio: cierre del mes en que termina cada año fiscal (archivo histórico propio, ajustado por splits) y el precio de hoy. Negocio: años fiscales y,
  en «Hoy», los últimos 12 meses informados (estados_completos, también ajustados por splits).
- Un solo eje (nunca dos escalas). El cambio de vista es solo con CSS (no recarga la página).
"""
import html

from data import af_tablas as _T

METRICAS = [("eps", "Ganancia por acción"), ("vps", "Ventas por acción"), ("fps", "Flujo libre por acción")]
COLORES = {"precio": "#2a78d6", "eps": "#1baf7a", "vps": "#eb6834", "fps": "#eda100"}


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _precio_en(cierres, anio, mes):
    """Cierre del mes del fin del año fiscal; si falta ese mes, el último cierre anterior dentro de los 2 meses previos."""
    for k in range(3):
        m, a = mes - k, anio
        while m < 1:
            m += 12
            a -= 1
        v = _n(cierres.get(f"{a:04d}-{m:02d}"))
        if v:
            return v
    return None


def puntos(estados, cierres, precio_hoy, mes_cierre=12):
    """[(etiqueta, precio, {eps, vps, fps})] de los años fiscales con precio, más «Hoy» (últimos 12 meses y precio de hoy)."""
    if not estados or not cierres:
        return []
    fy, ttm = _T._anios(estados)
    S = lambda g, r: _T._serie(estados, g, r)      # noqa: E731
    eps, ing, acc, fcf = S("resultados", "Ganancia por acción (diluida)"), S("resultados", "Ingresos"), S("resultados", "Acciones promedio (diluidas)"), S("flujo", "Flujo de efectivo libre")

    def neg(a):
        return {"eps": _n(eps.get(a)), "vps": (ing[a] / acc[a]) if ing.get(a) is not None and acc.get(a) else None,
                "fps": (fcf[a] / acc[a]) if fcf.get(a) is not None and acc.get(a) else None}
    out = []
    for a in fy:
        p = _precio_en(cierres, int(a), int(mes_cierre or 12))
        if p:
            out.append((f"{_MES[int(mes_cierre or 12)]} {a}", p, neg(a)))
    if ttm and _n(precio_hoy):
        out.append(("Hoy", float(precio_hoy), neg(ttm)))
    return out


_MES = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}


def cambios(pts, clave):
    """[% de cambio desde el primer punto] del precio (clave 'precio') o de una métrica; None si la base no es positiva (no se puede medir el cambio)."""
    vals = [p[1] if clave == "precio" else p[2].get(clave) for p in pts]
    base = vals[0] if vals else None
    if not base or base <= 0:
        return None
    return [(v / base - 1) if v is not None else None for v in vals]


def _fmt_pct(x):
    return f"{x * 100:+.0f}%".replace("+-", "-")


def _grafico(pts, series, ancho=880, alto=300):
    """SVG de líneas (un eje: % de cambio). series: [(nombre, [cambios], color, grosor)]."""
    L, R, T, B = 52, 170, 18, 34
    todos = [v for _, vs, _, _ in series for v in vs if v is not None] + [0.0]
    lo, hi = min(todos), max(todos)
    pad = (hi - lo) * 0.08 or 0.1
    lo, hi = lo - pad, hi + pad
    X = lambda i: L + (i * (ancho - L - R) / max(1, len(pts) - 1))      # noqa: E731
    Y = lambda v: T + (alto - T - B) * (1 - (v - lo) / (hi - lo))       # noqa: E731
    g = []
    paso = _paso(hi - lo)
    v = (int(lo / paso) - 1) * paso
    while v <= hi:
        if v >= lo:
            g.append(f'<line x1="{L}" x2="{ancho - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{"#94a3b8" if abs(v) < 1e-9 else "#e5e7eb"}" stroke-width="1"/>'
                     f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="12" fill="#64748b">{_fmt_pct(v) if abs(v) > 1e-9 else "0%"}</text>')
        v += paso
    for i, p in enumerate(pts):
        g.append(f'<text x="{X(i):.1f}" y="{alto - 10}" text-anchor="middle" font-size="12.5" fill="#475569">{html.escape(p[0])}</text>')
    finales = []
    for nombre, vs, color, w in series:
        tramo = [(i, x) for i, x in enumerate(vs) if x is not None]
        if len(tramo) < 2:
            continue
        g.append(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(x):.1f}" for i, x in tramo)}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, x in tramo:
            g.append(f'<circle cx="{X(i):.1f}" cy="{Y(x):.1f}" r="4.5" fill="{color}" stroke="#fff" stroke-width="2"><title>{html.escape(nombre)} · {html.escape(pts[i][0])}: {_fmt_pct(x)}</title></circle>')
        finales.append([Y(tramo[-1][1]), nombre, tramo[-1][1]])
    finales.sort()
    for k in range(1, len(finales)):
        if finales[k][0] - finales[k - 1][0] < 36:
            finales[k][0] = finales[k - 1][0] + 36
    for y, nombre, x in finales:
        g.append(f'<text x="{ancho - R + 12}" y="{y - 2:.1f}" font-size="13" font-weight="700" fill="#0f172a">{html.escape(nombre)}</text>'
                 f'<text x="{ancho - R + 12}" y="{y + 14:.1f}" font-size="12.5" fill="#475569">{_fmt_pct(x)}</text>')
    return f'<svg viewBox="0 0 {ancho} {alto}" width="100%" role="img" font-family="inherit">{"".join(g)}</svg>'


def _paso(rango):
    for p in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10):
        if rango / p <= 7:
            return p
    return 20


def _lectura(pts, cp, cm, nombre_m):
    """Una frase que lee el gráfico, con números (sin opinar)."""
    if not cp or not cm or cp[-1] is None or cm[-1] is None:
        return ""
    desde = pts[0][0].lower()
    txt = f"Desde {desde}, el precio cambió {_fmt_pct(cp[-1])} y la {nombre_m.lower()}, {_fmt_pct(cm[-1])}."
    if nombre_m == "Ganancia por acción":
        e0, e1 = pts[0][2].get("eps"), pts[-1][2].get("eps")
        if e0 and e1 and e0 > 0 and e1 > 0:
            txt += (f" Por eso el PER (cuántos años de ganancia pagás) pasó de {pts[0][1] / e0:.0f} a {pts[-1][1] / e1:.0f}: "
                    + ("la acción se abarató respecto de lo que gana." if pts[-1][1] / e1 < pts[0][1] / e0 else "la acción se encareció respecto de lo que gana."))
    elif cp[-1] < cm[-1]:
        txt += " El negocio creció más que el precio: la acción se abarató respecto de ese número."
    elif cp[-1] > cm[-1]:
        txt += " El precio creció más que el negocio: la acción se encareció respecto de ese número."
    return txt


def precio_vs_html(ticker, estados, cierres, precio_hoy, mes_cierre=None):
    """Tarjeta completa (con el selector de qué comparar). '' si no hay al menos dos puntos con datos."""
    mes = int(mes_cierre) if mes_cierre else 12
    pts = puntos(estados, cierres, precio_hoy, mes)
    if len(pts) < 2:
        return ""
    cp = cambios(pts, "precio")
    if not cp:
        return ""
    disponibles = [(k, nm, cambios(pts, k)) for k, nm in METRICAS]
    disponibles = [(k, nm, c) for k, nm, c in disponibles if c and sum(x is not None for x in c) >= 2]
    if not disponibles:
        return ""
    uid = "pv" + "".join(ch for ch in str(ticker) if ch.isalnum())
    radios, vistas = [], []
    opciones = disponibles + ([("todos", "Las tres", None)] if len(disponibles) > 1 else [])
    for i, (k, nm, c) in enumerate(opciones):
        radios.append(f'<input type="radio" name="{uid}" id="{uid}-{k}" class="pv-r pv-r-{k}"{" checked" if i == 0 else ""}><label for="{uid}-{k}">{html.escape(nm)}</label>')
        if k == "todos":
            series = [("Precio de la acción", cp, COLORES["precio"], 3.2)] + [(n2, c2, COLORES[k2], 2) for k2, n2, c2 in disponibles]
            lectura = ""
        else:
            series = [("Precio de la acción", cp, COLORES["precio"], 3.2), (nm, c, COLORES[k], 2.2)]
            lectura = _lectura(pts, cp, c, nm)
        vistas.append(f'<div class="pv-v pv-v-{k}">{_grafico(pts, series)}' + (f'<p class="pv-l">{html.escape(lectura)}</p>' if lectura else "") + "</div>")
    css_sel = "".join(f".pv-w:has(.pv-r-{k}:checked) .pv-v-{k}{{display:block}}" for k, _, _ in opciones)
    nota = ("Todas las líneas arrancan en 0% al cierre del primer año fiscal y muestran cuánto cambió cada una desde ahí. Si el precio sube más que el negocio, "
            "la acción se encarece; si sube menos, se abarata. Precio: cierre del mes en que termina cada año fiscal y el de hoy (ajustados por splits). "
            "Negocio: cada año fiscal y, en «Hoy», los últimos 12 meses informados; van por acción para que se puedan comparar con el precio. "
            "El punto de partida importa: con otra fecha de inicio, la foto puede cambiar.")
    if not mes_cierre:
        nota += " Se toma diciembre como cierre del año fiscal."
    return (f'<style>{CSS}{css_sel}</style><div class="pv-w"><h3>Precio vs fundamentales del negocio</h3>'
            f'<div class="pv-sel"><span>Comparar el precio con:</span>{"".join(radios)}</div>{"".join(vistas)}'
            f'<div class="pv-n">{html.escape(nota)}</div></div>')


CSS = """
.pv-w{background:#fff;border:1px solid #e3e8ee;border-left:5px solid #2a78d6;border-radius:14px;padding:16px 20px 14px;margin:14px 0;box-shadow:0 1px 2px rgba(15,23,42,.05),0 8px 22px rgba(15,23,42,.07)}
.pv-w h3{margin:0 0 10px;font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:#0f172a;padding:0!important}
.pv-sel{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 6px;font-size:14px;color:#475569}
.pv-sel input{position:absolute;opacity:0;pointer-events:none}
.pv-sel label{cursor:pointer;border:1px solid #cbd5e1;border-radius:999px;padding:4px 12px;font-weight:600;color:#334155;background:#fff;margin:0}
.pv-sel input:checked+label{background:#1e3a5f;border-color:#1e3a5f;color:#fff}
.pv-v{display:none}
.pv-l{margin:6px 0 0;font-size:14.5px;line-height:1.45;color:#334155;text-align:justify}
.pv-n{margin-top:10px;font-size:12.5px;line-height:1.45;color:#64748b;text-align:justify}
.mc-oscuro .pv-w{background:#111827;border-color:#1f2937}.mc-oscuro .pv-w h3{color:#e5e7eb}.mc-oscuro .pv-l{color:#cbd5e1}
"""
