"""
Vista visual de la tabla principal (v1.2.16, en prueba).

Una sola pieza de HTML (sin JavaScript) con una fila por empresa:
  Empresa        logo, nombre, ticker, sector y pais
  Valoracion     categoria con color + barra: franja = rango de los metodos del Fair Value (del menor
                 al mayor), raya = Fair Value promedio, punto = precio actual
  Puntaje        caja con el puntaje (0-100) y, abajo, cuantas metricas se pudieron usar
  Rango 52 sem.  barra con el punto donde esta el precio entre el minimo y el maximo del anio
  Div. Yield     rendimiento actual y comparacion con su mediana historica
  Mkt Cap        tamano de la empresa

Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import html
import math

import pandas as pd

from config.sectors import etiqueta_sector
from ui.logos import logo_html

_TEXTO_OSCURO = {"#d4a017": "#8a6100", "#2da44e": "#1f7a3a", "#e16a1a": "#b24a0a"}   # para que se lea sobre blanco

CSS = """
.tv-wrap{overflow-x:auto;border:1px solid #e5e7eb;border-radius:10px;background:#fff;color:#1f2328;font-family:inherit}
.tv-grid{min-width:1010px}
.tv-h,.tv-r{display:grid;grid-template-columns:minmax(250px,2.4fr) minmax(270px,2.6fr) 92px minmax(150px,1.5fr) minmax(120px,1.1fr) 84px;align-items:center;column-gap:14px;padding:0 16px}
.tv-h{background:#1f2937;color:#f3f4f6;font-size:13px;font-weight:600;height:44px;border-radius:10px 10px 0 0;letter-spacing:.2px}
.tv-h div{white-space:nowrap}
.tv-r{padding-top:14px;padding-bottom:14px;border-top:1px solid #eef0f2}
.tv-r:hover{background:#f8fafc}
.tv-emp{display:flex;align-items:center;gap:12px;min-width:0}
.tv-emp .tv-nm{font-weight:700;font-size:15px;line-height:1.25;color:#111827}
.tv-emp .tv-meta{font-size:12px;color:#6b7280;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tv-emp>div{min-width:0}
.tv-cat{font-weight:700;font-size:13.5px;display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.tv-up{font-size:12px;font-weight:600}
.tv-val{position:relative;padding-top:20px}
.tv-track{position:relative;height:8px;border-radius:4px;background:#e5e7eb;margin-top:3px}
.tv-band{position:absolute;top:0;height:8px;border-radius:4px;background:#a7b4c6}
.tv-fv{position:absolute;top:-3px;width:2px;height:14px;background:#475569;border-radius:1px}
.tv-dot{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #94a3b8;transform:translateX(-50%);box-sizing:border-box}
.tv-plbl{position:absolute;top:0;transform:translateX(-50%);font-size:12px;font-weight:700;color:#111827;white-space:nowrap}
.tv-lbls{display:flex;justify-content:space-between;font-size:11.5px;color:#6b7280;margin-top:5px}
.tv-sub{font-size:12px;color:#6b7280;margin-top:4px}
.tv-score{width:62px;border-radius:8px;overflow:hidden;border:2px solid #d1d5db;text-align:center;background:#fff}
.tv-num{font-size:21px;font-weight:700;line-height:36px;color:#111827}
.tv-met{font-size:11px;font-weight:600;color:#fff;line-height:19px}
.tv-t2{position:relative;height:8px;border-radius:4px;background:#e5e7eb;margin-top:12px}
.tv-d2{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #94a3b8;transform:translateX(-50%);box-sizing:border-box}
.tv-dy{font-weight:700;font-size:15px}
.tv-dy small{font-weight:600;font-size:12px;display:block;margin-top:2px}
.tv-mc{font-size:14px;font-weight:600;color:#374151}
.tv-nota{font-size:12px;color:#6b7280;padding:10px 16px;border-top:1px solid #eef0f2}
.tv-ini{font-family:inherit}
"""


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


def _celda_empresa(row):
    t = _txt(row.get("ticker"), "—")
    nombre = html.escape(_txt(row.get("nombre"), t))
    sec = etiqueta_sector(row.get("sector")) if isinstance(row.get("sector"), str) and row.get("sector") else None
    meta = " • ".join(html.escape(str(x)) for x in (t, sec, row.get("pais")) if isinstance(x, str) and x)
    return (f'<div class="tv-emp">{logo_html(t, 34)}<div><div class="tv-meta">{meta}</div>'
            f'<div class="tv-nm">{nombre}</div></div></div>')


def _celda_valoracion(row):
    cat = _txt(row.get("categoria"), "—")
    color = _txt(row.get("color_hex"), "#6e7781")
    txt = _TEXTO_OSCURO.get(color.lower(), color)
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    det = row.get("fair_value_detalle")
    precios = []
    if isinstance(det, dict):
        for v in det.values():
            p = _n(v.get("precio")) if isinstance(v, dict) else None
            if p and p > 0:
                precios.append(p)
    up_html = ""
    if precio and fv and precio > 0:
        up = (fv - precio) / precio
        c_up = "#1f7a3a" if up > 0.05 else "#cf222e" if up < -0.05 else "#6b7280"
        up_html = (f'<span class="tv-up" style="color:{c_up}" title="Distancia entre el precio y el Fair Value promedio">'
                   f'{"+" if up >= 0 else ""}{up * 100:.0f}% a FV</span>')
    cabeza = f'<div class="tv-cat" style="color:{txt}"><span>{html.escape(cat.capitalize())}</span>{up_html}</div>'
    if not precio or not (precios or fv):
        return cabeza + f'<div class="tv-sub">Sin Fair Value · precio {_money(precio)}</div>'
    lo, hi = (min(precios), max(precios)) if precios else (fv, fv)
    fv = fv or (lo + hi) / 2
    a, b = min(precio, lo), max(precio, hi)
    span = (b - a) or precio * 0.2
    a, b = a - span * 0.18, b + span * 0.18
    pos = lambda x: _clamp((x - a) / (b - a) * 100.0)
    pl, ph, pf, pp = pos(lo), pos(hi), pos(fv), pos(precio)
    return (cabeza + '<div class="tv-val">'
            f'<div class="tv-plbl" style="left:{_clamp(pp, 9, 91):.1f}%">{_money(precio)}</div>'
            f'<div class="tv-track"><div class="tv-band" style="left:{pl:.1f}%;width:{max(ph - pl, 1.5):.1f}%"></div>'
            f'<div class="tv-fv" style="left:{pf:.1f}%"></div>'
            f'<div class="tv-dot" style="left:{pp:.1f}%;background:{color}"></div></div>'
            f'<div class="tv-lbls"><span>{_money(lo)}</span><span>Fair Value {_money(fv)}</span><span>{_money(hi)}</span></div>'
            '</div>')


def _celda_puntaje(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    s = _n(row.get("score_total"))
    num = f"{s:.0f}" if s is not None else "—"
    u, t = _n(row.get("metricas_usadas")), _n(row.get("metricas_total"))
    met = f"{int(u)}/{int(t)} métr." if u is not None and t else "—"
    return (f'<div class="tv-score" style="border-color:{color}" title="Puntaje total (0 = caro, 100 = barato) y métricas usadas">'
            f'<div class="tv-num">{num}</div><div class="tv-met" style="background:{color}">{met}</div></div>')


def _celda_52s(row):
    pos = _n(row.get("posicion_52s"))
    if pos is None:
        return '<div class="tv-sub">—</div>'
    pct = _clamp(pos * 100)
    c = "#2da44e" if pct <= 30 else "#d4a017" if pct <= 70 else "#cf222e"
    return (f'<div title="El precio está al {pct:.0f}% del rango de las últimas 52 semanas (0% = mínimo, 100% = máximo)">'
            f'<div class="tv-t2"><div class="tv-d2" style="left:{pct:.0f}%;background:{c}"></div></div>'
            f'<div class="tv-lbls"><span>{_money(row.get("precio_min_52s"))}</span><span>{_money(row.get("precio_max_52s"))}</span></div></div>')


def _celda_dy(row):
    dy, med = _n(row.get("dividend_yield_actual")), _n(row.get("dividend_yield_mediana"))
    if not dy or dy <= 0:
        return '<div class="tv-sub">—</div>'
    pct = dy if dy > 1 else dy * 100
    sub = ""
    if med and med > 0:
        m = med if med > 1 else med * 100
        mtxt = f"{m:.1f}%" if m >= 1 else f"{m:.2f}%"
        if pct > m * 1.1:
            sub = f'<small style="color:#1f7a3a">▲ sobre su mediana ({mtxt})</small>'
        elif pct < m * 0.9:
            sub = f'<small style="color:#b45309">▼ bajo su mediana ({mtxt})</small>'
        else:
            sub = f'<small style="color:#6b7280">≈ su mediana ({mtxt})</small>'
    return f'<div class="tv-dy" style="color:{"#1f7a3a" if pct >= 3 else "#374151"}">{pct:.2f}%{sub}</div>'


def html_tabla_visual(df: pd.DataFrame) -> str:
    """HTML completo (estilos + tabla) para las filas de `df`, en el orden recibido."""
    filas = []
    for _, row in df.iterrows():
        r = row.to_dict()
        filas.append('<div class="tv-r">' + _celda_empresa(r) + f'<div>{_celda_valoracion(r)}</div>'
                     + f'<div>{_celda_puntaje(r)}</div>' + f'<div>{_celda_52s(r)}</div>'
                     + f'<div>{_celda_dy(r)}</div>' + f'<div class="tv-mc">{_mcap(r.get("market_cap"))}</div></div>')
    cab = ('<div class="tv-h"><div>Empresa</div><div>Valoración: precio vs Fair Value</div><div>Puntaje</div>'
           '<div>Rango 52 semanas</div><div>Div. Yield</div><div>Mkt Cap</div></div>')
    nota = ('<div class="tv-nota">Cómo leer la valoración: el <b>punto</b> es el precio de hoy, la <b>franja gris</b> va del método de Fair Value '
            'más bajo al más alto, y la <b>raya oscura</b> es el Fair Value promedio. Si el punto está a la izquierda de la franja, '
            'el precio queda por debajo de lo que dan los métodos.</div>')
    return f'<style>{CSS}</style><div class="tv-wrap"><div class="tv-grid">{cab}{"".join(filas)}{nota}</div></div>'
