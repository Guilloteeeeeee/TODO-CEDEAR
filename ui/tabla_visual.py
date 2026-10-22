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
.tv-score{width:62px;border-radius:8px;overflow:hidden;border:2px solid #d1d5db;text-align:center;background:#fff}
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
    sec = sector_html(row.get("sector"), en_linea=True) if isinstance(row.get("sector"), str) and row.get("sector") else None
    partes = [html.escape(t)] + ([sec] if sec else [])
    pais = row.get("pais")
    if isinstance(pais, str) and pais:
        partes.append(bandera_html(pais, chica=True))
    meta = " • ".join(partes)
    return (f'<div class="tv-emp">{logo_html(t, 34)}<div><div class="tv-meta">{meta}</div>'
            f'<div class="tv-nm">{nombre}</div></div></div>')


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
            sub = f'<small style="color:#6b7280">▲ sobre su mediana ({mtxt})</small>'
        elif pct < m * 0.9:
            sub = f'<small style="color:#6b7280">▼ bajo su mediana ({mtxt})</small>'
        else:
            sub = f'<small style="color:#6b7280">≈ su mediana ({mtxt})</small>'
    return f'<div class="tv-dy" style="color:#374151">{pct:.2f}%{sub}</div>'


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
    nota = ('<div class="tv-nota">Cómo leer la valoración: el <b>punto</b> es el precio de hoy (con el color de la categoría y su valor arriba), la <b>raya oscura</b> '
            'es el Fair Value promedio (con su valor abajo) y la <b>franja gris</b> es una zona de referencia alrededor del Fair Value. Es solo una guía visual: '
            'la categoría sale del puntaje.</div>')
    return f'<style>{CSS}</style><div class="tv-wrap"><div class="tv-grid">{cab}{"".join(filas)}{nota}</div></div>'
