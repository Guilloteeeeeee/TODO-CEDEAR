"""Análisis Fundamental v4 (v1.2.91): un ARTÍCULO con tesis, al estilo de los mejores analistas de dividendos y crecimiento (pedido de Guille, 29/10/2026).

Estructura (la misma para todas las empresas; los títulos de las secciones los escribe el redactor):
  titulo · fecha · resumen (3 puntos, el último es la conclusión) · introduccion · secciones (3 a 5, con gráficos) · valuacion (con datos del día)
  · conclusion (con la calidad) · pros / contras · fuentes (los datos del informe oficial, con su link).

Lo que cambia todos los días NO queda escrito: el texto de la valuación lleva MARCADORES ({precio}, {per_ref}, {vs:per}...) que la app completa
con el precio del día. Así, quien lo lee dentro de un mes ve los números de ese día, no los del día en que se escribió. Si un marcador no se puede
calcular (falta el dato), la oración que lo contiene no se muestra: nunca se inventa un número.

Los GRÁFICOS los dibuja el programa con los datos reales (estados de Yahoo, promedios de la industria, historial de precios); el redactor solo elige
cuáles y dónde, con una línea [[grafico:clave]] dentro del texto. Ninguna función de este módulo toca la red salvo `bono10_vivo` (Yahoo, con tope de tiempo)."""
import html
import json
import os
import re
import threading

from data import af_tablas as T

FORMATO = "v4"
AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_PROMPT = os.path.join(AQUI, "prompt_analisis_fundamental_v4.txt")
RUTA_MACRO_NUM = os.path.join(AQUI, "macro_numeros.json")

CALIDADES = ("Excelente", "Muy buena", "Buena", "Regular", "Pobre")
RIESGOS_IA = ("muy alto", "alto", "moderado", "bajo", "muy bajo")

# Gráficos que puede pedir el redactor: clave -> título que ve el lector
GRAFICOS = {
    "ingresos": "Ingresos por año (millones de dólares)",
    "margen_bruto": "Margen bruto contra el promedio de su industria",
    "margen_operativo": "Margen operativo contra el promedio de su industria",
    "margen_neto": "Margen neto contra el promedio de su industria",
    "roe": "Retorno sobre el patrimonio (ROE) contra el promedio de su industria",
    "roic": "Retorno sobre el capital invertido (ROIC) contra el promedio de su industria",
    "flujo_libre": "Flujo libre de caja (millones de dólares)",
    "flujo_vs_inversion": "Lo que genera la operación contra lo que invierte (millones de dólares)",
    "deuda_neta": "Deuda neta (millones de dólares) y cuántos años de EBITDA representa",
    "cobertura_intereses": "Cuántas veces la ganancia operativa paga los intereses",
    "acciones": "Acciones en circulación (millones)",
    "eps": "Ganancia por acción (dólares, contable)",
    "dividendo": "Dividendo anual por acción (dólares)",
    "per_historico": "PER al cierre de cada año contra su mediana histórica",
}

# Múltiplos que entienden los marcadores {v:X}, {med:X}, {vs:X}, {ind:X}, {vsind:X}
MULTIPLOS = ("per", "ev_ebitda", "p_b", "ps", "p_fcf", "p_ffo", "p_affo", "dy")
_IND = {"per": ("pedata", "Aggregate Mkt Cap/ Trailing Net Income (only money making firms)"), "ev_ebitda": ("vebitda", "EV/EBITDA"),
        "ps": ("psdata", "Price/Sales"), "p_b": ("pbvdata", "PBV")}
MARCADORES_SIMPLES = ("precio", "fecha_precio", "per_ref", "vs_ref_med", "vs_ref_ind", "dy", "bono10", "vs_bono", "fv", "dist_fv", "retorno")
RE_MARCADOR = re.compile(r"\{([a-z_0-9]+)(?::([a-z_0-9]+))?\}")
RE_GRAFICO = re.compile(r"^\s*\[\[grafico:([a-z_]+)\]\]\s*$")
BANDA = 0.07                      # ±7 %: "en línea con"

PROHIBIDAS = ("damodaran", "nelissen", "seeking alpha", "morningstar", "dividend collection", "te recomendamos", "recomendamos comprar", "precio objetivo",
              "potencial de suba", "potencial alcista", "comprá", "vendé", "en el dinámico mundo", "cabe destacar", "es importante señalar", "sin lugar a dudas",
              "en resumen,", "navegar los desafíos", "jugador clave", "bloque de datos", "según el modelo")


# --- formatos -----------------------------------------------------------------------------------------------------------------

def _n(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _es(txt):
    return txt.replace(",", "§").replace(".", ",").replace("§", ".")


def num(v, dec=1):
    v = _n(v)
    return None if v is None else _es(f"{v:,.{dec}f}")


def pct(v, dec=1):
    """v en puntos (3.05 -> '3,1 %')."""
    v = _n(v)
    return None if v is None else _es(f"{v:.{dec}f}") + " %"


def comparar(a, b, banda=BANDA):
    a, b = _n(a), _n(b)
    if a is None or b is None or b <= 0 or a <= 0:
        return None
    r = a / b - 1
    return "en línea con" if abs(r) <= banda else ("por debajo de" if r < 0 else "por encima de")


# --- datos del día ------------------------------------------------------------------------------------------------------------

def macro_numeros(ruta=None):
    """{'fecha', 'bono10', ...} de data/macro_numeros.json (lo actualiza quien renueva la foto macro). {} si no está."""
    try:
        with open(ruta or RUTA_MACRO_NUM, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def bono10_vivo(timeout=6.0):
    """Rendimiento del bono del Tesoro de EE.UU. a 10 años en puntos (4.98), de Yahoo (^TNX), o None. Nunca levanta excepciones."""
    res = {}

    def _pedir():
        try:
            import yfinance as yf
            h = yf.Ticker("^TNX").history(period="5d", interval="1d")
            v = _n(h["Close"].dropna().iloc[-1]) if h is not None and not h.empty else None
            res["v"] = v if v and 0.1 < v < 20 else None
        except Exception:  # noqa: BLE001
            res["v"] = None
    hilo = threading.Thread(target=_pedir, daemon=True)
    hilo.start()
    hilo.join(timeout)
    return res.get("v")


def _vivo(row, clave):
    """Múltiplo de hoy: el del cache ajustado por cuánto se movió el precio desde el cache (los múltiplos de precio se mueven igual que el precio)."""
    row = row or {}
    p, p0 = _n(row.get("precio_actual")), _n(row.get("precio_cache")) or _n(row.get("precio_actual"))
    r = (p / p0) if (p and p0) else 1.0
    if clave == "dy":
        ad = _n(row.get("annual_dividend"))
        if ad and p:
            return ad / p * 100
        dy = _n(row.get("dividend_yield_actual"))
        return dy * 100 / r if dy else None
    v = _n(row.get(f"{clave}_actual"))
    if v is None or v <= 0:
        return None
    if clave == "ev_ebitda":
        evc = _n(row.get("ev_sobre_cap"))
        return v * (1 + (r - 1) / evc) if evc and evc > 0 else v * r
    return v * r


def _mediana(row, clave):
    v = _n((row or {}).get(f"{clave}_mediana" if clave != "dy" else "dividend_yield_mediana"))
    if v is None or v <= 0:
        return None
    return v * 100 if clave == "dy" else v


def _industria(dam, clave):
    if not dam or clave not in _IND:
        return None
    ds, k = _IND[clave]
    v = _n((dam.get(ds) or {}).get(k))
    return v if v and v > 0 else None


def contexto(row, af=None, dam=None, bono10=None):
    """{marcador: texto} con todo lo que se puede calcular hoy. Lo que no se puede, no está (y la oración que lo use no se muestra)."""
    row, af = row or {}, af or {}
    val = af.get("valuacion") if isinstance(af.get("valuacion"), dict) else {}
    c = {}
    p = _n(row.get("precio_actual"))
    if p:
        c["precio"] = num(p, 2)
    f = str(row.get("precio_fecha") or row.get("fecha_dato") or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}", f):
        f = f"{f[8:10]}/{f[5:7]}/{f[:4]}"
    if f:
        c["fecha_precio"] = f
    for m in MULTIPLOS:
        v, md, ind = _vivo(row, m), _mediana(row, m), _industria(dam, m)
        if v is not None:
            c[f"v:{m}"] = pct(v) if m == "dy" else num(v)
        if md is not None:
            c[f"med:{m}"] = pct(md) if m == "dy" else num(md)
        if ind is not None:
            c[f"ind:{m}"] = num(ind)
        if comparar(v, md):
            c[f"vs:{m}"] = comparar(v, md)
        if comparar(v, ind):
            c[f"vsind:{m}"] = comparar(v, ind)
    g = _n(val.get("ganancia_ref"))
    per_ref = (p / g) if (p and g and g > 0) else _vivo(row, "per")
    if per_ref:
        c["per_ref"] = num(per_ref)
        if comparar(per_ref, _mediana(row, "per")):
            c["vs_ref_med"] = comparar(per_ref, _mediana(row, "per"))
        if comparar(per_ref, _industria(dam, "per")):
            c["vs_ref_ind"] = comparar(per_ref, _industria(dam, "per"))
    dy = _vivo(row, "dy")
    if dy is not None:
        c["dy"] = pct(dy)
    b = _n(bono10) or _n(macro_numeros().get("bono10"))
    if b:
        c["bono10"] = pct(b, 2)
        if dy is not None:
            c["vs_bono"] = "casi lo mismo que" if abs(dy - b) <= 0.25 else ("menos que" if dy < b else "más que")
    fv = _n(row.get("fair_value"))
    if fv and p:
        c["fv"] = num(fv, 2)
        d = fv / p - 1
        c["dist_fv"] = ("prácticamente en el precio de hoy" if abs(d) < 0.03 else
                        f"un {num(abs(d) * 100, 0)} % {'por encima' if d > 0 else 'por debajo'} del precio de hoy")
    if _n(af.get("mes_cierre_fiscal")):
        c["_mes_cierre"] = str(int(_n(af.get("mes_cierre_fiscal"))))
    cr = _n(val.get("crecimiento_ref"))
    if cr is not None and dy is not None:
        c["retorno"] = pct(cr + dy, 0)
    return c


def _oraciones(parrafo):
    return re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\"«(])", parrafo.strip())


def rellenar(texto, ctx, marca=True):
    """Reemplaza los marcadores por los datos de hoy. Una oración con un marcador que no se puede completar se saca entera.
    Con `marca`, el dato del día va en <span class="af-vv"> (subrayado punteado, "dato del día") y el texto queda listo para _negrita (sin escapar)."""
    out = []
    for par in str(texto or "").split("\n\n"):
        oks = []
        for o in _oraciones(par):
            faltan = [m.group(0) for m in RE_MARCADOR.finditer(o) if (m.group(1) + (f":{m.group(2)}" if m.group(2) else "")) not in ctx]
            if faltan:
                continue
            oks.append(RE_MARCADOR.sub(lambda m: ("\x01" + ctx[m.group(1) + (f":{m.group(2)}" if m.group(2) else "")] + "\x02") if marca
                                       else ctx[m.group(1) + (f":{m.group(2)}" if m.group(2) else "")], o))
        if oks:
            out.append(" ".join(oks))
    return "\n\n".join(out)


# --- gráficos -----------------------------------------------------------------------------------------------------------------

def _ser(estados, grupo, rot, esc=1.0):
    s = T._serie(estados, grupo, rot)
    fy, ttm = T._anios(estados)
    lab, val = [], []
    for a in fy + ([ttm] if ttm else []):
        v = _n(s.get(a))
        if v is not None:
            lab.append("Últ. 12 m" if isinstance(a, str) else str(a))
            val.append(v * esc)
    return lab, val


def _fmt_eje(v, tipo):
    if tipo == "pct":
        return _es(f"{v:.0f}") + " %"
    if tipo == "x":
        return _es(f"{v:.1f}") + "x"
    if tipo == "usd":
        return _es(f"{v:.2f}")
    return _es(f"{v:,.0f}")


def _paso_lindo(rango):
    """Paso 'redondo' para el eje (1, 2, 2,5 o 5 por una potencia de 10) que deja unas 4 marcas."""
    import math
    if rango <= 0:
        return 1.0
    crudo = rango / 4
    pot = 10 ** math.floor(math.log10(crudo))
    for m in (1, 2, 2.5, 5, 10):
        if crudo <= m * pot:
            return m * pot
    return 10 * pot


def _svg_barras(lab, val, tipo="m", refs=(), etiquetas=None, serie2=None, nombres=None):
    """Barras (con negativos en rojo), líneas de referencia horizontales [(valor, texto, color)] y, opcional, una segunda serie de barras.
    Ancho 480 y letra 13: en el celular se lee (se achica a ~330 px) y en la computadora no pasa de 600 px (CSS)."""
    import math
    if len(val) < 2:
        return ""
    W, H, ml, mr, mt, mb = 480, 240, 62, 8, 26, 32
    todos = list(val) + list(serie2 or []) + [r[0] for r in refs]
    lo, hi = min(0.0, min(todos)), max(0.0, max(todos))
    paso_e = _paso_lindo((hi - lo) * 1.1 or 1)
    lo = math.floor(lo / paso_e) * paso_e
    hi = math.ceil(hi * 1.12 / paso_e) * paso_e
    if hi == lo:
        hi = lo + paso_e
    Y = lambda v: mt + (hi - v) / (hi - lo) * (H - mt - mb)
    n = len(val)
    paso = (W - ml - mr) / n
    ancho = paso * (0.36 if serie2 else 0.58)
    s = ""
    k = lo
    while k <= hi + 1e-9:
        s += (f'<line x1="{ml}" y1="{Y(k):.1f}" x2="{W - mr}" y2="{Y(k):.1f}" stroke="#e5e7eb" stroke-dasharray="2 3"/>'
              f'<text x="{ml - 6}" y="{Y(k) + 4:.1f}" font-size="14" text-anchor="end" fill="#6b7280">{_fmt_eje(k, tipo)}</text>')
        k += paso_e
    for i, (l, v) in enumerate(zip(lab, val)):
        x = ml + paso * i + (paso - ancho * (2 if serie2 else 1)) / 2
        y0, y1 = Y(max(v, 0)), Y(min(v, 0))
        col = "#dc2626" if v < 0 else ("#94a3b8" if l.startswith(("Últ", "Hoy")) else "#1d4ed8")
        s += f'<rect x="{x:.1f}" y="{y0:.1f}" width="{ancho:.1f}" height="{max(1, y1 - y0):.1f}" rx="3" fill="{col}"><title>{html.escape(l)}: {_fmt_eje(v, tipo)}</title></rect>'
        txt = (etiquetas[i] if etiquetas else _fmt_eje(v, tipo))
        if txt:
            s += f'<text x="{x + ancho / 2:.1f}" y="{(y0 - 5) if v >= 0 else (y1 + 14):.1f}" font-size="15" font-weight="700" text-anchor="middle" fill="#111827">{html.escape(txt)}</text>'
        if serie2:
            v2 = serie2[i]
            y0b, y1b = Y(max(v2, 0)), Y(min(v2, 0))
            s += f'<rect x="{x + ancho:.1f}" y="{y0b:.1f}" width="{ancho:.1f}" height="{max(1, y1b - y0b):.1f}" rx="3" fill="#f59e0b"><title>{html.escape(l)}: {_fmt_eje(v2, tipo)}</title></rect>'
        s += f'<text x="{ml + paso * i + paso / 2:.1f}" y="{H - 9}" font-size="14" text-anchor="middle" fill="#4b5563">{html.escape(l)}</text>'
    s += f'<line x1="{ml}" y1="{Y(0):.1f}" x2="{W - mr}" y2="{Y(0):.1f}" stroke="#9ca3af"/>'
    ley = ""
    for v, t, col in refs:
        s += f'<line x1="{ml}" y1="{Y(v):.1f}" x2="{W - mr}" y2="{Y(v):.1f}" stroke="{col}" stroke-width="2" stroke-dasharray="6 4"/>'
        ley += f'<span><i style="border-top:2px dashed {col}"></i>{html.escape(t)}: {_fmt_eje(v, tipo) if tipo != "pct" else pct(v)}</span>'
    if serie2 and nombres:
        ley = f'<span><i class="b" style="background:#1d4ed8"></i>{html.escape(nombres[0])}</span><span><i class="b" style="background:#f59e0b"></i>{html.escape(nombres[1])}</span>' + ley
    return (f'<svg class="af-g" viewBox="0 0 {W} {H}" role="img">{s}</svg>' + (f'<div class="af-gl">{ley}</div>' if ley else ""))


def _per_historico(estados, historial, row, ctx):
    eps = T._serie(estados, "resultados", "Ganancia por acción (diluida)")
    fy, _ = T._anios(estados)
    if not historial:
        return "", ""
    lab, val = [], []
    mes = int(_n(ctx.get("_mes_cierre")) or 12)            # mes en que cierra el año fiscal (NVDA: enero; AAPL: septiembre...)
    for a in fy:
        e = _n(eps.get(a))
        cierres = [c for d, c in historial if hasattr(d, "year") and (d.year, d.month) <= (a, mes) and (d.year, d.month) > (a - 1, mes)]
        if e and e > 0 and cierres and historial and (historial[-1][0].year, historial[-1][0].month) > (a, mes):
            lab.append(str(a))
            val.append(cierres[-1] / e)
    if ctx.get("per_ref"):
        lab.append("Hoy")
        val.append(_n(ctx["per_ref"].replace(".", "").replace(",", ".")))
    md = _mediana(row, "per")
    return lab, (val, md)


def grafico(clave, estados, row=None, dam=None, ctx=None, historial=None, dps=None):
    """HTML del gráfico pedido (título + SVG), o "" si no hay datos suficientes. Nunca levanta excepciones."""
    try:
        return _grafico(clave, estados, row or {}, dam or {}, ctx or {}, historial, dps)
    except Exception:  # noqa: BLE001
        return ""


def _ind_pct(dam, ds, k):
    v = _n((dam.get(ds) or {}).get(k))
    return v


def _grafico(clave, estados, row, dam, ctx, historial, dps):
    tit = GRAFICOS.get(clave)
    if not tit:
        return ""
    svg = ""
    ref_ind = lambda v: [(v, "Promedio de su industria", "#f59e0b")] if v is not None else []
    if clave == "ingresos":
        lab, val = _ser(estados, "resultados", "Ingresos", 1e-6)
        svg = _svg_barras(lab, val, "m")
    elif clave in ("margen_bruto", "margen_operativo", "margen_neto"):
        rot = {"margen_bruto": "Margen bruto", "margen_operativo": "Margen operativo", "margen_neto": "Margen neto"}[clave]
        k = {"margen_bruto": "Gross Margin", "margen_operativo": "Pre-tax Unadjusted Operating Margin", "margen_neto": "Net Margin"}[clave]
        lab, val = _ser(estados, "ratios", rot, 100)
        svg = _svg_barras(lab, val, "pct", ref_ind(_ind_pct(dam, "margin", k)), etiquetas=[pct(v) for v in val])
    elif clave in ("roe", "roic"):
        rot = "Retorno sobre el patrimonio (ROE)" if clave == "roe" else "Retorno sobre el capital invertido (ROIC)"
        lab, val = _ser(estados, "ratios", rot, 100)
        svg = _svg_barras(lab, val, "pct", ref_ind(_ind_pct(dam, "pbvdata", "ROE" if clave == "roe" else "ROIC")), etiquetas=[pct(v) for v in val])
    elif clave == "flujo_libre":
        lab, val = _ser(estados, "flujo", "Flujo de efectivo libre", 1e-6)
        svg = _svg_barras(lab, val, "m")
    elif clave == "flujo_vs_inversion":
        la, a = _ser(estados, "flujo", "Flujo de efectivo operativo", 1e-6)
        lb, b = _ser(estados, "flujo", "Inversión en activos fijos (CAPEX)", 1e-6)
        comunes = [l for l in la if l in lb]
        a2 = [a[la.index(l)] for l in comunes]
        b2 = [abs(b[lb.index(l)]) for l in comunes]
        svg = _svg_barras(comunes, a2, "m", serie2=b2, nombres=("Genera la operación", "Invierte (CAPEX)"), etiquetas=[""] * len(comunes))
    elif clave == "deuda_neta":
        lab, val = _ser(estados, "balance", "Deuda neta", 1e-6)
        lr, rv = _ser(estados, "ratios", "Deuda neta / EBITDA")
        et = [(num(rv[lr.index(l)]) + "x") if l in lr else _fmt_eje(v, "m") for l, v in zip(lab, val)]
        svg = _svg_barras(lab, val, "m", etiquetas=et)
    elif clave == "cobertura_intereses":
        lab, val = _ser(estados, "ratios", "Cobertura de intereses (resultado operativo / intereses)")
        svg = _svg_barras(lab, val, "x", [(3.0, "Nivel sano (más de 3 veces)", "#16a34a"), (1.5, "Zona de alarma (menos de 1,5)", "#dc2626")])
    elif clave == "acciones":
        lab, val = _ser(estados, "resultados", "Acciones promedio (diluidas)", 1e-6)
        svg = _svg_barras(lab, val, "m")
    elif clave == "eps":
        lab, val = _ser(estados, "resultados", "Ganancia por acción (diluida)")
        svg = _svg_barras(lab, val, "usd")
    elif clave == "dividendo":
        xs = [(int(a), _n(v)) for a, v in (dps or []) if _n(v)][-10:]
        svg = _svg_barras([str(a) for a, _ in xs], [v for _, v in xs], "usd")
    elif clave == "per_historico":
        if str(T.moneda(estados) or "USD").upper() != "USD":          # ganancia en otra moneda y precio en dólares: el PER saldría mal
            return ""
        lab, x = _per_historico(estados, historial, row, ctx)
        if lab:
            val, md = x
            svg = _svg_barras(lab, val, "x", [(md, "Mediana histórica", "#f59e0b")] if md else [], etiquetas=[num(v) + "x" for v in val])
    if not svg:
        return ""
    return f'<figure class="af-fig"><figcaption>{html.escape(tit)}</figcaption>{svg}</figure>'


CSS = ('<style>.af4{max-width:760px}.af4 .af4-t{font-size:1.65rem;line-height:1.2;font-weight:800;color:#0f172a;margin:0 0 .3em;text-wrap:balance}'
       '.af4 .af4-f{font-size:.82rem;color:#64748b;margin:0 0 1em}.af4 h3{font-size:1.18rem;line-height:1.3;font-weight:800;color:#0f172a;margin:1.6em 0 .55em;text-wrap:balance}'
       '.af4 p{margin:0 0 .85em;font-size:15.5px;line-height:1.65;color:#1f2937;text-align:left}.af4 ul{margin:0 0 .6em 1.1em;padding:0}'
       '.af4 li{margin:0 0 .5em;font-size:15.5px;line-height:1.6;color:#1f2937}.af4 b{color:#0f172a}.af4-rs li:last-child{font-weight:700}'
       '.af-vv{border-bottom:1px dotted #64748b;cursor:help;white-space:nowrap}.af-fig{max-width:600px;margin:.6em 0 1.2em;padding:10px 12px;border:1px solid #e5e7eb;border-radius:12px;background:#fafbfc}'
       '.af-fig figcaption{font-size:.84rem;font-weight:700;color:#334155;margin:0 0 4px}.af-g{width:100%;height:auto;display:block}'
       '.af-gl{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:.8rem;color:#475569;margin-top:2px}.af-gl i{display:inline-block;width:18px;margin-right:6px;vertical-align:middle}'
       '.af-gl i.b{height:10px;border-radius:2px}.af4-vf{font-size:.8rem;color:#64748b;margin:-.3em 0 .9em}'
       '.af4-cal{display:inline-block;padding:2px 12px;border-radius:999px;font-weight:700;font-size:.9rem;margin-left:6px;vertical-align:middle}'
       '.af4-pc{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:700px){.af4-pc{grid-template-columns:1fr}}.af4-pc>div{min-width:0}'
       '.af4-pc h4{margin:0 0 .5em;font-size:.95rem;font-weight:800;letter-spacing:.4px;text-transform:uppercase}.af4-pc .p h4{color:#15803d}.af4-pc .c h4{color:#b91c1c}'
       '.af4-fu{font-size:.85rem;color:#475569}.af4-fu li{font-size:.85rem;line-height:1.5;margin:0 0 .35em}</style>')


def texto_html(txt, ctx=None, graficos=None):
    """Párrafos -> HTML. **negrita**, marcadores del día (si hay ctx) y líneas [[grafico:clave]] (si `graficos` es una función clave -> html)."""
    if ctx is not None:
        txt = rellenar(txt, ctx)
    out = []
    for par in str(txt or "").replace("\r", "").split("\n\n"):
        par = par.strip()
        if not par:
            continue
        m = RE_GRAFICO.match(par)
        if m:
            if graficos:
                out.append(graficos(m.group(1)))
            continue
        h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(par))
        h = h.replace("\x01", '<span class="af-vv" title="Dato del día: lo actualiza la app">').replace("\x02", "</span>")
        out.append(f"<p>{h}</p>")
    return "".join(out)


# --- validación ---------------------------------------------------------------------------------------------------------------

def _t(x):
    return str(x or "").strip()


def _l(x):
    return [_t(i) for i in (x if isinstance(x, list) else []) if _t(i)]


def _palabras(t):
    return len(re.findall(r"\w+", t))


def validar(d):
    """(análisis limpio | None, [problemas]) del formato v4."""
    pr = []
    if not isinstance(d, dict):
        return None, ["no es un objeto JSON"]
    o = {"formato": FORMATO}
    o["titulo"] = _t(d.get("titulo"))
    if not 20 <= len(o["titulo"]) <= 100:
        pr.append("'titulo': la tesis en una línea (20 a 100 caracteres)")
    o["resumen"] = _l(d.get("resumen"))
    if len(o["resumen"]) != 3:
        pr.append("'resumen' tiene que tener exactamente 3 puntos (el último, la conclusión sobre la calidad)")
    o["introduccion"] = _t(d.get("introduccion"))
    if not 60 <= _palabras(o["introduccion"]) <= 260:
        pr.append("'introduccion' de 100 a 220 palabras")
    secs = d.get("secciones") if isinstance(d.get("secciones"), list) else []
    o["secciones"] = [{"titulo": _t(s.get("titulo")), "texto": _t(s.get("texto"))} for s in secs if isinstance(s, dict) and _t(s.get("titulo")) and _t(s.get("texto"))]
    if not 3 <= len(o["secciones"]) <= 5:
        pr.append("'secciones': de 3 a 5, cada una con 'titulo' (una afirmación) y 'texto'")
    for s in o["secciones"]:
        if s["titulo"].lower().strip(" .") in ("el negocio", "los números", "los numeros", "deuda", "balance", "foso", "gerencia", "riesgos", "valuación", "conclusión"):
            pr.append(f"el título de sección «{s['titulo']}» es una etiqueta: tiene que ser una afirmación sobre la empresa")
    val = d.get("valuacion") if isinstance(d.get("valuacion"), dict) else {}
    o["valuacion"] = {"texto": _t(val.get("texto"))}
    for k in ("ganancia_ref", "crecimiento_ref"):
        if _n(val.get(k)) is not None:
            o["valuacion"][k] = _n(val.get(k))
    if _t(val.get("ganancia_ref_txt")):
        o["valuacion"]["ganancia_ref_txt"] = _t(val.get("ganancia_ref_txt"))
    if _palabras(o["valuacion"]["texto"]) < 60:
        pr.append("'valuacion.texto' falta o es muy corto (100 a 220 palabras, con marcadores del día)")
    if not RE_MARCADOR.search(o["valuacion"]["texto"]):
        pr.append("'valuacion.texto' tiene que usar marcadores del día ({precio}, {per_ref}, {vs:per}...): los números del día no se escriben a mano")
    o["conclusion"] = _t(d.get("conclusion"))
    if _palabras(o["conclusion"]) < 60:
        pr.append("'conclusion' falta o es muy corta")
    if "para que la tesis se mantenga" not in o["conclusion"].lower():
        pr.append("la 'conclusion' tiene que cerrar con \"Para que la tesis se mantenga, lo más importante es …\"")
    o["pros"], o["contras"] = _l(d.get("pros")), _l(d.get("contras"))
    if not 2 <= len(o["pros"]) <= 4 or not 2 <= len(o["contras"]) <= 4:
        pr.append("'pros' y 'contras': de 2 a 4 cada uno, con la forma \"Idea corta: frase con evidencia\"")
    for x in o["pros"] + o["contras"]:
        if not re.match(r"^[^:]{3,50}:\s+\S", x):
            pr.append("cada pro/contra con la forma \"Idea corta: frase con evidencia\"")
            break
    cal = _t(d.get("calidad")).capitalize()
    o["calidad"] = cal if cal in CALIDADES else ""
    if not o["calidad"]:
        pr.append("'calidad': " + " | ".join(CALIDADES))
    r = _t(d.get("riesgo_ia")).lower()
    o["riesgo_ia"] = r if r in RIESGOS_IA else ""
    if not o["riesgo_ia"]:
        pr.append("'riesgo_ia': " + " | ".join(RIESGOS_IA))
    o["clientes"] = _l(d.get("clientes"))[:8]
    hs = d.get("hechos") if isinstance(d.get("hechos"), list) else []
    o["hechos"] = [{"dato": _t(h.get("dato")), "fuente": _t(h.get("fuente")), "url": _t(h.get("url"))} for h in hs
                   if isinstance(h, dict) and _t(h.get("dato")) and _t(h.get("url")).startswith("https://")]
    if len(o["hechos"]) != len(hs):
        pr.append("cada 'hecho' necesita 'dato', 'fuente' y 'url' (https://, documento oficial)")
    mc = _n(d.get("mes_cierre_fiscal"))
    if mc is not None:
        if 1 <= mc <= 12:
            o["mes_cierre_fiscal"] = int(mc)
        else:
            pr.append("'mes_cierre_fiscal' tiene que ser un mes (1 a 12)")
    if _t(d.get("desde_el_ultimo")):
        o["desde_el_ultimo"] = _t(d.get("desde_el_ultimo"))
    # marcadores y gráficos válidos
    textos = [o["introduccion"], o["conclusion"], o["valuacion"]["texto"]] + [s["texto"] for s in o["secciones"]]
    for tx in textos:
        for m in RE_MARCADOR.finditer(tx):
            k, a = m.group(1), m.group(2)
            ok = (k in MARCADORES_SIMPLES and not a) or (k in ("v", "med", "vs") and a in MULTIPLOS) or (k in ("ind", "vsind") and a in _IND)
            if not ok:
                pr.append(f"marcador desconocido: {m.group(0)}")
        for par in tx.split("\n\n"):
            if "[[" in par:
                g = RE_GRAFICO.match(par)
                if not g or g.group(1) not in GRAFICOS:
                    pr.append(f"gráfico mal escrito o desconocido: {par.strip()[:60]} (va solo, en su propio párrafo: [[grafico:clave]])")
    for tx in textos[:2] + textos[3:]:
        if RE_MARCADOR.search(tx):
            pr.append("los marcadores del día solo van en 'valuacion.texto'")
            break
    todo = json.dumps(d, ensure_ascii=False).lower()
    mal = [w for w in PROHIBIDAS if w in todo]
    if mal:
        pr.append("frases o nombres prohibidos: " + ", ".join(mal))
    tot = sum(_palabras(t) for t in textos + o["resumen"])
    if not 1100 <= tot <= 2300:
        pr.append(f"extensión total {tot} palabras (orientativo: 1.300 a 1.900)")
    if _t(d.get("ticker")):
        o["ticker"] = _t(d.get("ticker")).upper()
    for k in ("perfil",):
        if _t(d.get(k)):
            o[k] = _t(d.get(k))
    return (None if pr else o), pr


# --- prompt -------------------------------------------------------------------------------------------------------------------

def industria_texto(ticker):
    """Promedios de la industria de la empresa (Damodaran, su región) para el prompt. '' si no hay."""
    try:
        from data import damodaran as D
        v = D.valores(ticker)
    except Exception:  # noqa: BLE001
        v = None
    if not v:
        return "(sin datos de industria)"
    m, pb, pe, ve, ps = (v.get(k) or {} for k in ("margin", "pbvdata", "pedata", "vebitda", "psdata"))
    filas = [("Margen bruto", m.get("Gross Margin"), "%"), ("Margen operativo", m.get("Pre-tax Unadjusted Operating Margin"), "%"),
             ("Margen neto", m.get("Net Margin"), "%"), ("ROE", pb.get("ROE"), "%"), ("ROIC", pb.get("ROIC"), "%"),
             ("PER (empresas con ganancias)", pe.get("Aggregate Mkt Cap/ Trailing Net Income (only money making firms)"), "x"),
             ("EV/EBITDA", ve.get("EV/EBITDA"), "x"), ("Precio / ventas", ps.get("Price/Sales"), "x"), ("Precio / valor libros", pb.get("PBV"), "x")]
    lin = [f"Industria: {v['industria']} ({v.get('region_txt')}; {int(_n(m.get('Number of firms')) or 0)} empresas; datos a enero de 2026). En el texto decí \"el promedio de su industria\", sin nombrar la fuente."]
    for nom, val, u in filas:
        if _n(val) is not None:
            lin.append(f"- {nom}: {num(val)}{' %' if u == '%' else 'x'}")
    return "\n".join(lin)


def valuacion_hoy_texto(row, af=None, dam=None):
    ctx = contexto(row, af, dam)
    if not ctx:
        return "(sin datos)"
    return "\n".join(f"- {{{k}}} = {v}" for k, v in sorted(ctx.items()) if not k.startswith("_"))


def armar_prompt(ticker, bloque, row=None, anterior=None, ruta=None):
    from data import analisis_fundamental as AF
    try:
        from data import damodaran as D
        dam = D.valores(ticker)
    except Exception:  # noqa: BLE001
        dam = None
    with open(ruta or RUTA_PROMPT, encoding="utf-8") as f:
        p = f.read()
    ant = "(no hay análisis anterior en este formato)"
    if anterior:
        ant = f"Fecha: {anterior.get('fecha')}\nTítulo: {anterior.get('titulo') or ''}\nResumen: " + " ".join(anterior.get("resumen") if isinstance(anterior.get("resumen"), list) else [str(anterior.get("resumen") or "")])
    return (p.replace("{MACRO_ACTUAL}", AF.macro_actual() or "(sin foto macro)").replace("{INDUSTRIA}", industria_texto(ticker))
            .replace("{VALUACION_HOY}", valuacion_hoy_texto(row, None, dam)).replace("{ANALISIS_ANTERIOR}", ant).replace("{BLOQUE_DATOS}", bloque))
