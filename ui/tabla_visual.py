"""
Tabla visual (definitiva desde v1.2.28; antes "en prueba"): una pieza de HTML (sin JavaScript) con una fila por empresa.
Los titulos son botones de Streamlit (los dibuja app.py, con los mismos anchos) y ordenan al tocarlos.
  Empresa        logo, "nombre • TICKER" (mismo tono y tamano) con el Market Cap en negrita al lado;
                 abajo, sector (industria) y bandera del pais
  Valoracion     categoria con color + barra: franja = zona alrededor del Fair Value, raya = Fair Value promedio,
                 punto = precio actual; columna con un tono azul clarito
  Puntaje        caja con el puntaje (0-100) y, abajo, cuantas metricas se pudieron usar
  Div. Yield     rendimiento actual en grande y minigrafico anual contra su mediana historica
El rango de 52 semanas ya no va en la tabla: esta en el detalle de cada empresa.

Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import base64
import html
import math

import pandas as pd

from config.sectors import etiqueta_sector, partes_sector
from ui.banderas import bandera_html
from ui.logos import logo_html

# Color de texto (para leer sobre blanco) de cada color de categoria, y color del texto sobre el relleno de la escala
_TEXTO_OSCURO = {"#eab308": "#854d0e", "#82b93f": "#4d7a12", "#f97316": "#c2410c", "#dc2626": "#b91c1c"}
_TEXTO_EN_RELLENO = {"#15803d": "#ffffff", "#82b93f": "#1f2937", "#eab308": "#1f2937", "#f97316": "#1f2937", "#dc2626": "#ffffff"}


def texto_categoria(color):
    """Color de texto legible sobre blanco para una categoria con ese color de relleno."""
    return _TEXTO_OSCURO.get(str(color).lower(), color)


def sector_html(grupo, en_linea=False):
    """Sector en negrita y la industria entre parentesis. Dos lineas en la tabla; en una sola en la vista visual."""
    sector, industria = partes_sector(grupo)
    if not sector:
        return "—"
    s = f"<b>{html.escape(sector)}</b>"
    if not industria:
        return s if en_linea else f'<div class="tv-sec">{s}</div>'
    ind = html.escape(industria)
    return f'{s} <span class="tv-ind">({ind})</span>' if en_linea else f'<div class="tv-sec">{s}<span class="tv-ind">({ind})</span></div>'


def escala_valoracion_html(mostrar_gris=False):
    """Escala de valoracion (titulo + 5 tramos de color con su rango de puntaje), sin circulos ni cuadraditos."""
    from scoring.engine import CATEGORIAS, CATEGORIA_GRIS
    rangos = ["70 o más", "58 a 69", "42 a 57", "30 a 41", "menos de 30"]
    tramos = []
    for (umbral, nombre, color, _), rango in zip(CATEGORIAS, rangos):
        txt = _TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")
        tramos.append(f'<div class="esc-s" style="background:{color};color:{txt}"><b>{html.escape(nombre.capitalize())}</b>'
                      f'<small>Puntaje {rango}</small></div>')
    gris = (f'<div class="esc-gp"><span class="esc-gc" style="background:{CATEGORIA_GRIS[1]}">{html.escape(CATEGORIA_GRIS[0].capitalize())}</span>'
            f'<span class="esc-gt">sin métricas ni rango de 52 semanas</span></div>') if mostrar_gris else ""
    return ('<div class="esc"><div class="esc-t"><b>Escala de valoración</b>'
            '<span>según el puntaje final de 0 (caro) a 100 (barato)</span></div>'
            f'<div class="esc-b">{"".join(tramos)}</div>{gris}</div>')

# Anchos relativos de las 4 columnas (Empresa, Valoracion, Puntaje, Div. Yield): los usan los
# encabezados (botones de Streamlit) y las filas (grilla CSS), asi quedan alineados.
ANCHOS_VISUAL = [3.6, 3.7, 1.2, 2.3]

CSS = """
.tv2{border:1px solid #d5dde6;border-top:0;border-radius:0 0 10px 10px;background:#fff;color:#1f2328;overflow:hidden;font-family:inherit}
.tv2-r{display:grid;grid-template-columns:__COLS__;align-items:stretch;border-top:1px solid #e8ecf1}
.tv2-r:first-child{border-top:0}
.tv2-r>div{padding:14px 16px;min-width:0;display:flex;flex-direction:column;justify-content:center}
.tv2-r>.tv2-v{background:#f2f6fa}
.tv2-r:hover>div{background:#f8fafc}
.tv2-r:hover>.tv2-v{background:#e9f0f7}
.tv2-c{align-items:center;text-align:center}
.tv2-emp{display:flex;align-items:center;gap:12px;min-width:0}
.tv2-ec{min-width:0;flex:1}
.tv2-l1{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.tv2-nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:15px;font-weight:700;color:#111827}
.tv2-mc{font-size:15px;font-weight:700;color:#111827;white-space:nowrap}
.tv2-l2{margin-top:4px;font-size:12.5px;color:#6b7280;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tv2-l2 b{color:#374151;font-weight:700}
.tv2-l2 .tv-ind{display:inline;margin:0;color:#6b7280}
.tv2-dyn{font-size:22px;font-weight:600;color:#111827;line-height:1.15}
.tv2-dy img{display:block;margin:3px auto 0}
.tv2-dym{font-size:12px;color:#6b7280;margin-top:4px}
.tv2-dym b{color:#374151}
.tv-cat{font-weight:700;font-size:13.5px;display:flex;justify-content:center;align-items:baseline;gap:8px;margin-bottom:2px}
.tv-up{font-weight:700;color:#374151;margin-left:3px}
.tv-v2{position:relative;padding-top:19px;margin:0 4px}
.tv-pl{position:absolute;top:0;transform:translateX(-50%);font-size:12px;font-weight:700;color:#111827;white-space:nowrap}
.tv-leg{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:11.5px;color:#4b5563;white-space:nowrap;margin-top:6px}
.tv-leg>span{display:inline-flex;align-items:center;gap:5px}
.tv-ld{display:inline-block;width:10px;height:10px;border-radius:50%;box-shadow:0 0 0 1px #94a3b8}
.tv-lf{display:inline-block;width:2px;height:12px;background:#2f7fb8;border-radius:1px}
.tv-line{position:relative;height:3px;border-radius:2px;background:#cfe3f3;margin:8px 0}
.tv-band{position:absolute;top:-4px;height:11px;border-radius:5px;background:#a9d3f2;opacity:.9}
.tv-fv{position:absolute;top:-5px;width:2px;height:13px;background:#2f7fb8;border-radius:1px;transform:translateX(-50%)}
.tv-dot{position:absolute;top:-6px;width:15px;height:15px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #94a3b8;transform:translateX(-50%);box-sizing:border-box}
.tv-lbls{display:flex;justify-content:space-between;font-size:11.5px;color:#6b7280;margin-top:5px}
.tv-sub{font-size:12px;color:#6b7280;margin-top:4px}
.tv-score{margin:0 auto;width:62px;border-radius:8px;overflow:hidden;border:2px solid #d1d5db;text-align:center;background:#fff}
.tv-num{font-size:21px;font-weight:700;line-height:36px;color:#111827}
.tv-met{font-size:11px;font-weight:600;color:#fff;line-height:19px}
.tv-t2{position:relative;height:8px;border-radius:4px;background:#e5e7eb;margin-top:12px}
.tv-d2{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #94a3b8;transform:translateX(-50%);box-sizing:border-box}
.tv-dy{font-weight:700;font-size:15px}
.tv-dy small{font-weight:600;font-size:12px;display:block;margin-top:2px}
.tv-mc{font-size:14px;font-weight:700;color:#111827}
.tv-sec{line-height:1.25}
.tv-sec b{display:block;font-size:14px;color:#111827}
.tv-ind{display:block;margin-top:1px;font-size:12px;color:#6b7280}
.tv-meta .tv-ind{display:inline;margin:0}
.tv-emp .tv-meta b{color:#374151;font-weight:700}
.esc{margin:2px 0 14px}
.esc-t{display:flex;align-items:baseline;gap:10px;margin-bottom:6px;font-size:14px;color:#111827}
.esc-t span{font-size:12px;color:#6b7280}
.esc-b{display:flex;flex-wrap:wrap;gap:2px}
.esc-s{flex:1 1 150px;padding:7px 10px;text-align:center;line-height:1.25}
.esc-s:first-child{border-radius:8px 0 0 8px}
.esc-s:last-child{border-radius:0 8px 8px 0}
.esc-s b{display:block;font-size:12.5px;font-weight:700}
.esc-s small{display:block;font-size:11px;opacity:.92}
.esc-gp{margin-top:6px}
.esc-gc{display:inline-block;color:#fff;font-size:11.5px;font-weight:700;padding:2px 10px;border-radius:10px;margin-right:8px}
.esc-gt{font-size:12px;color:#6b7280}
.tv-nota{font-size:12px;color:#6b7280;padding:10px 16px;border-top:1px solid #eef0f2}
.tv-ini{font-family:inherit}
.flt-t{font-size:13px;font-weight:700;color:#374151;margin:12px 0 2px}
[data-testid="stButtonGroup"] button{border:1px solid #cfd8e3;border-radius:18px;background-color:#fff;color:#374151;padding:3px 13px;font-size:13.5px;transition:background .12s,border-color .12s}
[data-testid="stButtonGroup"] button:hover{background:#eef3f8;border-color:#9fb3c8;color:#1e3a52}
[data-testid="stButtonGroup"] button[aria-pressed="true"],[data-testid="stButtonGroup"] button[data-testid="stBaseButton-pillsActive"]{background:#1e3a52!important;border-color:#1e3a52!important;color:#fff!important;font-weight:600}
[data-testid="stButtonGroup"] button[aria-pressed="true"] p,[data-testid="stButtonGroup"] button[data-testid="stBaseButton-pillsActive"] p{color:#fff}
[data-testid="stButtonGroup"] button[aria-pressed="true"]:hover{background:#2a4d6b!important;border-color:#2a4d6b!important;color:#fff!important}
span[data-baseweb="tag"]{background:#e8eef5!important;border-radius:14px!important}
span[data-baseweb="tag"],span[data-baseweb="tag"] span{color:#1f2937!important}
span[data-baseweb="tag"] svg{fill:#475569!important}
"""
CSS = CSS.replace("__COLS__", " ".join(f"minmax(0,{w}fr)" for w in ANCHOS_VISUAL))

# Colores del encabezado (barra oscura, titulos blancos centrados; la columna Valoracion un poco mas oscura)
_BARRA = "#1e3a52"
_BARRA_VAL = "#122a3e"


def css_encabezado(sort_col):
    """CSS de la fila de titulos (botones de Streamlit con la clave 'tvh_<columna>'). La columna ordenada se oscurece."""
    base = 'div[data-testid="stHorizontalBlock"]:has(.st-key-tvh_nombre)'
    return (
        f'{base}{{gap:0!important;background:{_BARRA};border:1px solid {_BARRA};border-radius:10px 10px 0 0;align-items:stretch!important}}'
        f'{base} [data-testid="stColumn"]{{min-width:0!important;padding:0!important}}'
        f'{base} [data-testid="stElementContainer"]{{width:100%}}'
        '[class*="st-key-tvh_"] button{width:100%;min-height:54px;background:transparent;border:0;border-radius:0;box-shadow:none;color:#fff}'
        '[class*="st-key-tvh_"] button p{font-size:15.5px;font-weight:700;color:#fff;margin:0;letter-spacing:.2px}'
        '[class*="st-key-tvh_"] button:hover{background:rgba(255,255,255,.12);color:#fff}'
        '[class*="st-key-tvh_"] button:focus,[class*="st-key-tvh_"] button:active{color:#fff;box-shadow:none;background:rgba(255,255,255,.12)}'
        f'.st-key-tvh_fv_upside button{{background:{_BARRA_VAL}}}'
        f'.st-key-tvh_{sort_col} button{{background:rgba(0,0,0,.28)}}'
        'div[data-testid="stElementContainer"]:has(.tv2){margin-top:-1rem}'
    )


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def _txt(x, defecto=""):
    """Texto no vacio o `defecto` (los vacios de pandas llegan como NaN y no deben verse como 'nan')."""
    return x if isinstance(x, str) and x.strip() else defecto


def _money(x):
    v = _n(x)
    if v is None:
        return "—"
    return f"&#36;{v:,.0f}" if abs(v) >= 100 else f"&#36;{v:,.2f}"


def _mcap(x):
    v = _n(x)
    if not v or v <= 0:
        return "—"
    for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= lim:
            return f"&#36;{v / lim:.1f}{suf}"
    return f"&#36;{v:,.0f}"


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _nombre_limpio(nombre, ticker):
    """Nombre sin comas ni puntos colgados al final (Yahoo viejo lo cortaba a ~30 letras: 'Financial Group,')."""
    n = _txt(nombre, ticker).strip()
    while n and n[-1] in ",;:-/ ":
        n = n[:-1].rstrip()
    return n or ticker


def _celda_empresa(row):
    """Nombre • TICKER (mismo tono y tamano) con el Market Cap en negrita al lado; abajo, sector (industria) y bandera."""
    t = _txt(row.get("ticker"), "—")
    nombre = html.escape(_nombre_limpio(row.get("nombre"), t))
    g = row.get("sector")
    sec = sector_html(g, en_linea=True) if isinstance(g, str) and g else ""
    pais = row.get("pais")
    bandera = bandera_html(pais, chica=True) if isinstance(pais, str) and pais else ""
    l2 = " ".join(x for x in (sec, bandera) if x)
    return (f'<div class="tv2-emp">{logo_html(t, 38)}<div class="tv2-ec">'
            f'<div class="tv2-l1"><span class="tv2-nm">{nombre} • {html.escape(t)}</span>'
            f'<span class="tv2-mc">{_mcap(row.get("market_cap"))}</span></div>'
            f'<div class="tv2-l2">{l2}</div></div></div>')


def _franja_fv(precios, fv):
    """(bajo, alto) de la franja de Fair Value segun config/ajustes.py, o None si no se puede dibujar."""
    try:
        from config.ajustes import FRANJA_FV_MODO as modo, FRANJA_FV_MARGEN as margen
    except Exception:  # noqa: BLE001
        modo, margen = "margen", 0.15
    if not fv or fv <= 0:
        return None
    if modo == "promedio_metodos":
        abajo = [p for p in precios if p < fv * 0.999]
        arriba = [p for p in precios if p > fv * 1.001]
        if not abajo and not arriba:
            return None
        return (sum(abajo) / len(abajo) if abajo else fv), (sum(arriba) / len(arriba) if arriba else fv)
    return fv * (1 - margen), fv * (1 + margen)


def _celda_valoracion(row, con_categoria=True):
    cat = _txt(row.get("categoria"), "—")
    color = _txt(row.get("color_hex"), "#6e7781")
    txt = texto_categoria(color)
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    det = row.get("fair_value_detalle")
    precios = []
    if isinstance(det, dict):
        for v in det.values():
            p = _n(v.get("precio")) if isinstance(v, dict) else None
            if p and p > 0:
                precios.append(p)
    cabeza = (f'<div class="tv-cat" style="color:{txt}"><span>{html.escape(cat.capitalize())}</span></div>'
              if con_categoria else "")
    if not precio or not fv:
        return cabeza + f'<div class="tv-sub">Sin Fair Value · precio {_money(precio)}</div>'
    up = (fv - precio) / precio
    up_txt = f'<b class="tv-up" title="Distancia entre el precio y el Fair Value promedio">{"+" if up >= 0 else ""}{up * 100:.0f}%</b>'
    fr = _franja_fv(precios, fv)
    lo, hi = fr if fr else (fv, fv)
    a, b = min(precio, lo, fv), max(precio, hi, fv)
    span = (b - a) or precio * 0.2
    a, b = a - span * 0.12, b + span * 0.12
    pos = lambda x: _clamp((x - a) / (b - a) * 100.0)
    pl, ph, pf, pp = pos(lo), pos(hi), pos(fv), pos(precio)
    banda = (f'<div class="tv-band" style="left:{pl:.1f}%;width:{max(ph - pl, 1.5):.1f}%"></div>' if fr else "")
    return (cabeza + '<div class="tv-v2">'
            + f'<div class="tv-pl" style="left:{_clamp(pp, 10, 90):.1f}%">{_money(precio)}</div>'
            + '<div class="tv-line">' + banda
            + f'<div class="tv-fv" style="left:{pf:.1f}%"></div>'
            + f'<div class="tv-dot" style="left:{pp:.1f}%;background:{color}"></div></div>'
            + f'<div class="tv-leg"><span><i class="tv-ld" style="background:{color}"></i>Precio</span>'
            + f'<span><i class="tv-lf"></i>Fair Value {_money(fv)} {up_txt}</span></div></div>')


def celda_valoracion(row):
    """Barra de valoracion para la tabla clasica (sin el nombre de la categoria)."""
    return _celda_valoracion(row, con_categoria=False)


def _celda_puntaje(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    s = _n(row.get("score_total"))
    num = f"{s:.0f}" if s is not None else "—"
    u, t = _n(row.get("metricas_usadas")), _n(row.get("metricas_total"))
    met = f"{int(u)}/{int(t)} métr." if u is not None and t else "—"
    return (f'<div class="tv-score" title="Puntaje total (0 = caro, 100 = barato) y métricas usadas">'
            f'<div class="tv-num">{num}</div><div class="tv-met" style="background:#64748b">{met}</div></div>')


def _celda_52s(row):
    pos = _n(row.get("posicion_52s"))
    if pos is None:
        return '<div class="tv-sub">—</div>'
    pct = _clamp(pos * 100)
    c = "#64748b"   # un solo color (gris azulado)
    return (f'<div title="El precio está al {pct:.0f}% del rango de las últimas 52 semanas (0% = mínimo, 100% = máximo)">'
            f'<div class="tv-t2"><div class="tv-d2" style="left:{pct:.0f}%;background:{c}"></div></div>'
            f'<div class="tv-lbls"><span>{_money(row.get("precio_min_52s"))}</span><span>{_money(row.get("precio_max_52s"))}</span></div></div>')


def _svg_dy(serie, dy_pct, med_pct, etiqueta):
    """Minigrafico del Div. Yield como imagen (data URI): serie anual en gris, linea de la mediana y punto de hoy."""
    W, H, px, py = 156, 44, 5, 8
    vals = [v * 100 if v <= 1 else v for v in serie] + [dy_pct] if serie and len(serie) >= 2 else None
    cand = list(vals or [dy_pct]) + ([med_pct] if med_pct else [])
    lo, hi = min(cand), max(cand)
    if hi - lo < 1e-9:
        hi = lo + 1.0
    pad = (hi - lo) * 0.18
    lo, hi = lo - pad, hi + pad
    y = lambda v: H - py - (v - lo) / (hi - lo) * (H - 2 * py)
    partes = []
    if vals:
        xs = [px + i * (W - 2 * px - 4) / (len(vals) - 1) for i in range(len(vals))]
        pts = " ".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, vals))
        partes.append(f'<polyline points="{pts}" fill="none" stroke="#c3cad4" stroke-width="1.6" stroke-linejoin="round"/>')
        cx, cy = xs[-1], y(vals[-1])
    else:
        cx, cy = W - px - 4, y(dy_pct)
    if med_pct:
        ym = y(med_pct)
        partes.append(f'<line x1="{px}" y1="{ym:.1f}" x2="{W - px}" y2="{ym:.1f}" stroke="#8793a3" stroke-width="1"/>')
        ty = ym - 4 if ym > 17 else ym + 11
        partes.append(f'<text x="{px}" y="{ty:.1f}" font-size="10" fill="#5b6675" stroke="#fff" stroke-width="3" paint-order="stroke" stroke-linejoin="round" font-family="Arial,Helvetica,sans-serif">{html.escape(etiqueta)}</text>')
    partes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="#475569" stroke="#fff" stroke-width="1.5"/>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(partes)}</svg>'
    return f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" width="{W}" height="{H}" alt="">'


def _celda_dy(row):
    """Rendimiento por dividendo: numero grande y, abajo, minigrafico contra su mediana de los ultimos anios.
    Si el cache todavia no trae la serie anual, no se dibuja un grafico a medias: se muestra la mediana en texto."""
    dy, med = _n(row.get("dividend_yield_actual")), _n(row.get("dividend_yield_mediana"))
    if not dy or dy <= 0:
        return '<div class="tv2-dy"><div class="tv2-dyn" style="color:#9ca3af">—</div></div>'
    pct = dy if dy > 1 else dy * 100
    m = (med if med > 1 else med * 100) if med and med > 0 else None
    serie = row.get("dividend_yield_serie")
    serie = [v for v in (_n(x) for x in serie) if v is not None] if isinstance(serie, (list, tuple)) else None
    anios = (row.get("anios_historia") or {}).get("dividend_yield") if isinstance(row.get("anios_historia"), dict) else None
    n = len(serie) if serie else (int(anios) if anios else None)
    etiqueta = f"Mediana {n} años" if n and n >= 2 else "Mediana histórica"
    mtxt = f"{m:.1f}%" if m and m >= 1 else (f"{m:.2f}%" if m else "")
    tip = (f"Rendimiento por dividendo de hoy. La línea es su mediana histórica ({mtxt}); el punto es hoy." if m
           else "Rendimiento por dividendo de hoy.")
    if serie and len(serie) >= 2:
        pie = _svg_dy(serie, pct, m, etiqueta)
    elif m:
        pie = f'<div class="tv2-dym">{html.escape(etiqueta)}: <b>{mtxt}</b></div>'
    else:
        pie = ""
    return f'<div class="tv2-dy" title="{html.escape(tip)}"><div class="tv2-dyn">{pct:.2f}%</div>{pie}</div>'


def html_tabla_visual(df: pd.DataFrame) -> str:
    """HTML de las filas de `df`, en el orden recibido (los encabezados ordenables los dibuja la app)."""
    filas = []
    for _, row in df.iterrows():
        r = row.to_dict()
        filas.append('<div class="tv2-r">' + f'<div>{_celda_empresa(r)}</div>' + f'<div class="tv2-v">{_celda_valoracion(r)}</div>'
                     + f'<div class="tv2-c">{_celda_puntaje(r)}</div>' + f'<div class="tv2-c">{_celda_dy(r)}</div></div>')
    nota = ('<div class="tv-nota">Cómo leer la valoración: el <b>punto</b> es el precio de hoy (con el color de la categoría y su valor arriba), la <b>rayita azul</b> '
            'es el Fair Value promedio (con su valor abajo) y la <b>franja celeste</b> es una zona de referencia alrededor del Fair Value. Es solo una guía visual: '
            'la categoría sale del puntaje. El rango de 52 semanas está en el detalle de cada empresa.</div>')
    return f'<div class="tv2">{"".join(filas)}{nota}</div>'
