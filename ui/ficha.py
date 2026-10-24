"""
Ficha de la pagina de una empresa, en mosaicos (v1.2.46).

Cada dato va en su propio mosaico (tarjeta blanca con sombra suave), repartidos en una grilla de 12 columnas: el Score de calidad
grande a la izquierda, al lado la valoracion y el precio, despues capitalizacion, sede, CEDEAR, la descripcion, el sector, el rango de
52 semanas y el Dividend Yield contra su mediana, y abajo de todo la linea de precios con el Fair Value de cada metodo.
En pantallas angostas (celular) los mosaicos pasan a ir uno abajo del otro.

Linea de precios: el precio actual abajo (punto del color de la categoria) y arriba, una flecha celeste por cada metodo del Fair Value
(con su nombre y su valor); la flecha azul oscura es el Fair Value promedio. El PEG sale aparte, en gris, "solo informativo": no entra
al puntaje ni al promedio. La escala es logaritmica (la mitad y el doble del precio quedan a la misma distancia).

No usa JavaScript. Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import ast
import html
import math

from config.descripciones import descripcion_de
from config.sectors import partes_sector
from data import cedears as _cedears
from ui.banderas import bandera_html
from ui.tabla_visual import (_TEXTO_EN_RELLENO, _celda_dy, _clamp, _mcap, _money, _n, _texto_categoria, _txt, texto_categoria)

ETIQUETAS_METODO = {"ev_ebitda": "EV/EBITDA", "per": "P/E", "p_fcf": "P/FCF", "p_b": "P/Book", "dividend_yield": "Dividend Yield",
                    "peg": "PEG", "p_ffo": "P/FFO", "p_affo": "P/AFFO", "ps": "P/S"}
CELESTE = "#38bdf8"
AZUL = "#1f6aa5"
GRIS_PEG = "#94a3b8"
ALTO_NIVEL = 40            # px por nivel de etiquetas
ANCHO_ETIQUETA = 15.0      # % del ancho que ocupa una etiqueta (para que no se pisen)
PEG_RANGO_MAX = 6.0        # el PEG se dibuja si su precio implicito esta entre 1/6 y 6 veces el precio; si no, queda como nota

CSS = """
.fch{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;margin:14px 0 8px}
.fch-t{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);padding:14px 16px 16px;min-width:0;position:relative;overflow:hidden}
.fch-t::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--ac,#cbd5e1)}
.fch-h{font-size:11.5px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:#6b7280;margin:0 0 8px;padding-left:4px}
.fch-h small{text-transform:none;letter-spacing:0;font-weight:500;color:#9ca3af;margin-left:4px}
.fch-b{padding-left:4px;min-width:0}
.s3{grid-column:span 3}.s4{grid-column:span 4}.s5{grid-column:span 5}.s6{grid-column:span 6}.s7{grid-column:span 7}.s8{grid-column:span 8}.s12{grid-column:span 12}
.r2{grid-row:span 2}
.fch-big{font-size:26px;font-weight:700;color:#0f172a;line-height:1.15;letter-spacing:-.3px}
.fch-big small{display:block;font-size:12px;font-weight:500;color:#6b7280;letter-spacing:0;margin-top:3px}
.fch-mid{font-size:17px;font-weight:600;color:#111827}
.fch-sub{font-size:12.5px;color:#4b5563;margin-top:6px;line-height:1.4}
.fch-sub b{color:#111827}
.fch-val .tv-vl{text-align:left}
.fch-val .tv-vh{font-size:12.5px;font-weight:500;color:#6b7280;margin-bottom:1px}
.fch-val .tv-vn{font-size:21px}
.fch-txt{font-size:14.5px;line-height:1.55;color:#1f2937}
.fch-nota{font-size:11.5px;color:#9ca3af;margin-top:8px}
.fch-par{display:flex;gap:18px;flex-wrap:wrap}
.fch-par>div{min-width:0}
.fch-par .fch-k{font-size:11.5px;color:#6b7280;margin-bottom:2px}
.fch-par .fch-v{font-size:19px;font-weight:600;color:#111827}
.fch-sc{display:flex;flex-direction:column;align-items:flex-start;gap:12px}
.fch-sc .num{font-size:72px;line-height:1;font-weight:800;border-radius:16px;padding:16px 22px;min-width:130px;text-align:center;letter-spacing:-2px}
.fch-sc .sub{font-size:12.5px;color:#4b5563;line-height:1.45}
.fch-sc .sub b{color:#111827}
.fch-52 .tv-t2{margin-top:14px}
.fch-52 .tv-lbls{font-size:12.5px}
.fch-dy .tv2-dy{text-align:left}
.fch-dy .tv2-dyn{font-size:26px;font-weight:700;color:#0f172a;line-height:1.1}
.fch-dy .tv2-dy img{margin:6px 0 0}
.fch-dy .tv2-dym{font-size:12.5px;margin-top:4px}
.fch-dy .tv2-dym b{font-weight:600}
.fch-sec b{display:block;font-size:16px;font-weight:600;color:#111827}
.fch-sec span{display:block;margin-top:3px;font-size:13.5px;color:#4b5563}
.fch-pais{display:flex;align-items:center;gap:9px;font-size:17px;font-weight:600;color:#111827}
.fch-pl .fch-ex{font-size:12.5px;color:#4b5563;line-height:1.5;margin:0 0 6px 4px}
.pl-wrap{overflow-x:auto;padding:4px 4px 2px}
.pl{position:relative;min-width:640px;margin:0 14px}
.pl-ln{position:absolute;left:0;right:0;height:4px;border-radius:2px;background:#d6e4f0}
.pl-ar{position:absolute;width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;border-top:11px solid var(--c);transform:translateX(-50%)}
.pl-ar.avg{border-left-width:9px;border-right-width:9px;border-top-width:14px}
.pl-st{position:absolute;z-index:1;width:1px;background:var(--c);opacity:.55;transform:translateX(-50%)}
.pl-lb{position:absolute;transform:translateX(-50%);text-align:center;white-space:nowrap;line-height:1.2;width:max-content;background:#fff;padding:1px 4px;border-radius:4px;z-index:2}
.pl-lb .n{font-size:12px;font-weight:600;color:#1f2937}
.pl-lb .v{font-size:12px;color:#4b5563}
.pl-lb.avg .n{color:#1f6aa5}
.pl-lb.peg .n{color:#64748b;font-style:italic}
.pl-pt{position:absolute;width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 0 1px #475569,0 1px 3px rgba(15,23,42,.35);transform:translateX(-50%);box-sizing:border-box}
.pl-pl{position:absolute;transform:translateX(-50%);text-align:center;white-space:nowrap;font-size:12.5px;color:#111827;line-height:1.25}
.pl-pl b{font-weight:700}
.pl-leyenda{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 4px 0;font-size:12px;color:#4b5563}
.pl-leyenda i{display:inline-block;width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:8px solid var(--c);margin-right:6px;vertical-align:1px}
@media (max-width:900px){
.fch{gap:12px}
.fch>.fch-t{grid-column:span 12!important;grid-row:auto!important}
.fch-sc .num{font-size:60px}
}
"""


def _dict(x):
    if isinstance(x, dict):
        return x
    if isinstance(x, str) and x.strip():
        try:
            d = ast.literal_eval(x)
            return d if isinstance(d, dict) else {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _ars(v):
    """Pesos con formato argentino: $ 12.345 (sin decimales si pasa de 100)."""
    v = _n(v)
    if v is None:
        return "—"
    txt = f"{v:,.0f}" if v >= 100 else f"{v:,.2f}"
    return "&#36;&nbsp;" + txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(precio, valor):
    v = int(round((valor - precio) / precio * 100))
    return f"{v:+d}%" if v else "0%"


def metodos_fair_value(row):
    """(metodos, peg_info, peg_nota): metodos = [(clave, etiqueta, precio, peso)] los que entran al Fair Value;
    peg_info = precio implicito por PEG (solo informativo) o None; peg_nota = texto si el PEG quedo fuera de escala."""
    det = _dict(row.get("fair_value_detalle"))
    metodos = []
    for k, d in det.items():
        p = _n(d.get("precio")) if isinstance(d, dict) else None
        if p and p > 0:
            metodos.append((k, ETIQUETAS_METODO.get(k, str(k).upper()), p, _n(d.get("peso")) or 0.0))
    peg_info, nota = None, None
    precio = _n(row.get("precio_cache")) or _n(row.get("precio_actual"))     # el PEG de hoy sale del precio del cache: se usa ese mismo precio
    if "peg" not in det and precio and precio > 0:
        act, med = _n(row.get("peg_actual")), _n(row.get("peg_mediana"))
        if act and med and act > 0 and med > 0:
            impl = precio * med / act
            r = impl / precio
            if 1 / PEG_RANGO_MAX <= r <= PEG_RANGO_MAX:
                peg_info = impl
            else:
                nota = f"El PEG (solo informativo) implicaría un precio de {r:.1f} veces el actual: queda fuera de la escala."
    return metodos, peg_info, nota


def _niveles(items, ancho=ANCHO_ETIQUETA, max_niveles=5):
    """Asigna a cada etiqueta (ya ordenada por posicion) el nivel mas bajo donde no pisa a otra: [(item, nivel)]."""
    ocupados = []     # por nivel: lista de x de etiquetas ya puestas
    res = []
    for it in items:
        for n in range(max_niveles):
            if n == len(ocupados):
                ocupados.append([])
            if all(abs(it["xl"] - x) >= ancho for x in ocupados[n]):
                ocupados[n].append(it["xl"])
                res.append((it, n))
                break
        else:
            n = max_niveles - 1
            ocupados[n].append(it["xl"])
            res.append((it, n))
    return res, max(1, len(ocupados))


def linea_precios_html(row):
    """Mosaico ancho: precio actual abajo y, arriba, el Fair Value de cada metodo (flechas celestes) y el PEG informativo."""
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    color = _txt(row.get("color_hex"), "#6e7781")
    cab = (f'<div class="fch-h">Precio contra el Fair Value de cada método</div>')
    if not precio or precio <= 0:
        return f'<div class="fch-t s12 fch-pl" style="--ac:{AZUL}">{cab}<div class="fch-sub">Sin precio para dibujar la línea.</div></div>'
    metodos, peg_info, peg_nota = metodos_fair_value(row)
    items = [{"tipo": "m", "n": et, "v": p, "tit": f"{et}: precio que resulta de su múltiplo histórico (peso {w*100:.0f}%)"} for _, et, p, w in metodos]
    if fv and fv > 0 and metodos:
        items.append({"tipo": "avg", "n": "Fair Value promedio", "v": fv, "tit": "Promedio de los métodos, con los pesos de su sector"})
    if peg_info:
        items.append({"tipo": "peg", "n": "PEG (informativo)", "v": peg_info, "tit": "El PEG no entra al puntaje ni al Fair Value: se muestra solo como dato"})
    if not items:
        sin = '<div class="fch-sub">Esta empresa no tiene un Fair Value calculado (faltan datos para sus métodos).</div>'
        return f'<div class="fch-t s12 fch-pl" style="--ac:{AZUL}">{cab}{sin}</div>'
    valores = [i["v"] for i in items] + [precio]
    lo, hi = math.log(min(valores) / 1.12), math.log(max(valores) * 1.12)
    xs = lambda v: 100.0 * (math.log(v) - lo) / (hi - lo)
    for i in items:
        i["x"] = xs(i["v"])
        i["xl"] = _clamp(i["x"], 8.0, 92.0)
    items.sort(key=lambda i: i["x"])
    colocados, T = _niveles(items)
    linea_y = T * ALTO_NIVEL + 16
    alto = linea_y + 64
    xp = xs(precio)
    partes = [f'<div class="pl-ln" style="top:{linea_y}px"></div>']
    for it, n in colocados:
        c = {"m": CELESTE, "avg": AZUL, "peg": GRIS_PEG}[it["tipo"]]
        top_lb = (T - 1 - n) * ALTO_NIVEL
        tope_st = top_lb + 33
        extra = {"m": "", "avg": " avg", "peg": " peg"}[it["tipo"]]
        pct = _pct(precio, it["v"])
        partes.append(f'<div class="pl-lb{extra}" style="left:{it["xl"]:.1f}%;top:{top_lb}px" title="{html.escape(it["tit"], quote=True)}">'
                      f'<div class="n">{html.escape(it["n"])}</div><div class="v">{_money(it["v"])} · {pct}</div></div>')
        partes.append(f'<div class="pl-st" style="--c:{c};left:{it["x"]:.1f}%;top:{tope_st}px;height:{max(0, linea_y - 11 - tope_st)}px"></div>')
        partes.append(f'<div class="pl-ar{extra.replace(" peg", "")}" style="--c:{c};left:{it["x"]:.1f}%;top:{linea_y - (14 if it["tipo"] == "avg" else 11)}px"></div>')
    xpl = _clamp(xp, 9.0, 91.0)
    partes.append(f'<div class="pl-pt" style="left:{xp:.1f}%;top:{linea_y - 7}px;background:{color}" title="Precio actual"></div>')
    partes.append(f'<div class="pl-pl" style="left:{xpl:.1f}%;top:{linea_y + 18}px">Precio actual<br><b>{_money(precio)}</b></div>')
    ley = (f'<div class="pl-leyenda"><span style="--c:{CELESTE}"><i></i>Fair Value según cada método</span>'
           f'<span style="--c:{AZUL}"><i></i>Fair Value promedio</span>'
           + (f'<span style="--c:{GRIS_PEG}"><i></i>PEG: solo informativo, no entra al puntaje</span>' if peg_info else '')
           + '</div>')
    nota = f'<div class="fch-nota">{html.escape(peg_nota)}</div>' if peg_nota else ""
    cat = _txt(row.get("categoria"), "")
    chip = ""
    if cat:
        chip = f' <small style="color:{texto_categoria(color)};font-weight:600">· {_texto_plano_categoria(cat)}</small>'
    cab = f'<div class="fch-h">Precio contra el Fair Value de cada método{chip}</div>'
    exp = ('<div class="fch-ex">Abajo, el precio de hoy. Arriba, cada flecha es el precio que resultaría de aplicar un método con la mediana histórica '
           'de su múltiplo; la azul oscura es el promedio ponderado (el Fair Value). Escala logarítmica. Es una estimación, no una recomendación.</div>')
    return (f'<div class="fch-t s12 fch-pl" style="--ac:{AZUL}">{cab}{exp}<div class="pl-wrap"><div class="pl" style="height:{alto}px">'
            + "".join(partes) + f'</div></div>{ley}{nota}</div>')


def _texto_plano_categoria(cat):
    from scoring.engine import nombre_visible
    from ui.tabla_visual import _mayusculas, _partes_nombre
    return html.escape(_mayusculas(_partes_nombre(nombre_visible(cat))[1]))


def _tile(cls, titulo, cuerpo, ac="#cbd5e1", extra=""):
    return f'<div class="fch-t {cls}" style="--ac:{ac}"><div class="fch-h">{titulo}</div><div class="fch-b">{cuerpo}</div>{extra}</div>'


def _tile_score(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    s = _n(row.get("score_total"))
    num = f"{s:.0f}" if s is not None else "—"
    txt = _TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")
    u, t = _n(row.get("metricas_usadas")), _n(row.get("metricas_total"))
    met = f" Calculado con {int(u)} de {int(t)} métricas." if u is not None and t else ""
    cuerpo = (f'<div class="fch-sc"><div class="num" style="background:{color};color:{txt}">{num}</div>'
              f'<div class="sub"><b>De 0 a 100.</b> Por ahora es el puntaje de precio del screener (0 = más cara, 100 = más barata): '
              f'más adelante el Score de calidad sumará la calidad del negocio.{met}</div></div>')
    return _tile("s3 r2", "Score de calidad", cuerpo, ac=color)


def _tile_valoracion(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    cat = _texto_categoria(_txt(row.get("categoria"), "—"), color, True)
    if precio and fv and precio > 0 and fv > 0:
        fvt = f'<div class="fch-sub">Fair Value <b>{_money(fv)}</b> ({_pct(precio, fv)} frente al precio)</div>'
    else:
        fvt = '<div class="fch-sub">Sin Fair Value: faltan datos para calcularlo.</div>'
    return _tile("s5", "Valoración", f'<div style="text-align:left" class="fch-val">{cat}</div>{fvt}', ac=color)


def _tile_precio(row):
    p = _n(row.get("precio_actual"))
    val = _money(p) if p and p > 0 else "—"
    if row.get("precio_en_vivo") is True:
        f, h = _txt(row.get("precio_fecha"), ""), _txt(row.get("precio_hora"), "")
        nota = "Yahoo Finance" + (f" · dato del {html.escape(f)}" if f else "") + (f" (consultado {html.escape(h)})" if h else "")
    else:
        nota = "Precio de la última actualización de los datos (Yahoo no respondió o los precios en vivo están apagados)"
    return _tile("s4", "Precio <small>(Cotización origen)</small>", f'<div class="fch-big">{val}<small>{nota}</small></div>', ac="#64748b")


def _tile_cap(row):
    return _tile("s3", "Capitalización bursátil", f'<div class="fch-big">{_mcap(row.get("market_cap"))}</div>', ac="#64748b")


def _tile_sede(row):
    pais = row.get("pais")
    if isinstance(pais, str) and pais:
        cuerpo = f'<div class="fch-pais">{bandera_html(pais, con_nombre=True)}</div><div class="fch-sub">País de la sede, según Yahoo Finance</div>'
    else:
        cuerpo = '<div class="fch-mid">—</div>'
    return _tile("s3", "Sede fiscal", cuerpo, ac="#64748b")


def _tile_cedear(row, datos):
    d = datos.get(str(row.get("ticker", "")).upper()) or {}
    ratio = _cedears.ratio_texto(d.get("ratio"))
    ars = _n(d.get("precio_ars"))
    precio = _ars(ars) if ars else "—"
    hora = f' <span style="color:#9ca3af;font-size:12px">({html.escape(str(d["hora"]))})</span>' if ars and d.get("hora") else ""
    ccl = _n(d.get("ccl"))
    if ars and ccl:
        nota = (f'<div class="fch-nota">Dólar implícito: {_ars(ccl)} · Yahoo Finance ({html.escape(str(d.get("simbolo") or ""))}.BA)</div>')
    elif d.get("ratio"):
        nota = '<div class="fch-nota">Sin precio en pesos ahora: Yahoo no lo entregó o no pasó el control de coherencia.</div>'
    else:
        nota = '<div class="fch-nota">Sin datos de CEDEAR para esta empresa (data/cedears.csv).</div>'
    cuerpo = (f'<div class="fch-par"><div><div class="fch-k">Ratio de conversión</div><div class="fch-v">{ratio}</div></div>'
              f'<div><div class="fch-k">Precio en pesos</div><div class="fch-v">{precio}{hora}</div></div></div>{nota}')
    return _tile("s3", "CEDEAR", cuerpo, ac="#38bdf8")


def _tile_descripcion(row):
    d = descripcion_de(row.get("ticker"))
    cuerpo = (f'<div class="fch-txt">{html.escape(d)}</div><div class="fch-nota">Resumen general de lo que hace la empresa, sin cifras.</div>'
              if d else '<div class="fch-sub">Descripción pendiente de cargar.</div>')
    return _tile("s7", "Descripción de la empresa", cuerpo, ac="#a78bfa")


def _tile_sector(row):
    sector, industria = partes_sector(row.get("sector"))
    if not sector:
        cuerpo = '<div class="fch-mid">—</div>'
    else:
        cuerpo = f'<div class="fch-sec"><b>{html.escape(sector)}</b>' + (f'<span>{html.escape(industria)}</span>' if industria else "") + "</div>"
    return _tile("s5", "Sector e industria", cuerpo, ac="#a78bfa")


def _tile_52s(row):
    pos = _n(row.get("posicion_52s"))
    if pos is None:
        cuerpo = '<div class="fch-sub">Sin datos de rango de 52 semanas.</div>'
    else:
        pct = _clamp(pos * 100)
        cuerpo = (f'<div class="fch-52"><div class="fch-sub" style="margin:0">El precio está al <b>{pct:.0f}%</b> del rango (0% = mínimo, 100% = máximo)</div>'
                  f'<div class="tv-t2"><div class="tv-d2" style="left:{pct:.0f}%;background:#64748b"></div></div>'
                  f'<div class="tv-lbls"><span>Mín. {_money(row.get("precio_min_52s"))}</span><span>Máx. {_money(row.get("precio_max_52s"))}</span></div></div>')
    return _tile("s4", "Rango de 52 semanas", cuerpo, ac="#f59e0b")


def _tile_dy(row):
    return _tile("s4", "Dividend Yield <small>contra su mediana</small>", f'<div class="fch-dy">{_celda_dy(row, grande=True)}</div>', ac="#10b981")


def _tile_detalle(row):
    f, t, c = _n(row.get("score_fundamental")), _n(row.get("score_tecnico")), _n(row.get("score_total"))
    def n(x):
        return f"{x:.0f}" if x is not None else "—"
    cuerpo = (f'<div class="fch-par"><div><div class="fch-k">Fundamental</div><div class="fch-v">{n(f)}</div></div>'
              f'<div><div class="fch-k">Técnico (52 sem.)</div><div class="fch-v">{n(t)}</div></div>'
              f'<div><div class="fch-k">Total</div><div class="fch-v">{n(c)}</div></div></div>'
              '<div class="fch-sub">El total pesa 85% el fundamental (múltiplos contra su historia) y 15% el técnico (posición en el rango de 52 semanas).</div>')
    return _tile("s4", "Cómo sale el puntaje", cuerpo, ac="#94a3b8")


def ficha_html(row, cedears=None):
    """Todos los mosaicos de la pagina de la empresa (`row` es el dict de la fila; `cedears` el resultado de data.cedears.cargar())."""
    datos = cedears if cedears is not None else _cedears.cargar()
    mosaicos = [_tile_score(row), _tile_valoracion(row), _tile_precio(row), _tile_cap(row), _tile_sede(row), _tile_cedear(row, datos),
                _tile_descripcion(row), _tile_sector(row), _tile_52s(row), _tile_dy(row), _tile_detalle(row), linea_precios_html(row)]
    return '<div class="fch">' + "".join(mosaicos) + "</div>"
