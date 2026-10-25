"""
Ficha de la pagina de una empresa (v1.2.46; formato tipo Fiscal AI desde la v1.2.47; mosaicos desplegables desde la v1.2.49).

Estructura (arriba la banda con el nombre y el precio; abajo, mosaicos que se pueden plegar):
  1. Encabezado: logo, nombre, mercado donde cotiza y ticker (con ADR si es un certificado de deposito), bandera y pais. A la derecha el precio en
     dolares y, mas chico y menos llamativo, "Precio en pesos $ X (ratio N : 1)" del CEDEAR y "Dato al dd/mm/aaaa hh:mm".
  2. "Resumen de la empresa" (desplegable, abierto): la descripcion completa de Yahoo en una banda ancha, la lista de datos (nombre, CEO, sitio web,
     sector, industria, mercado, sede y empleados) y, al lado, la capitalizacion bursatil, el rango de 52 semanas (barrita con el precio de hoy y los
     precios extremos) y el Dividend Yield con su dibujito.
  3. Score de calidad y Valoracion (con un "?" que cuenta, sin detalles del metodo, como se llega a la lectura).
  4. "Estadisticas de la empresa" (desplegable): Perfil, Crecimiento y Valoracion; cada multiplo con su mediana historica, un dibujito (hoy contra
     su mediana), el Fair Value que da y su peso.
  5. "Precio contra el Fair Value de cada metodo" (desplegable): la linea de precios.
  (v1.2.50: se quito "Revision de los metodos del Fair Value" y la columna "Peso": el metodo y los pesos no se muestran al publico.)
Las fuentes no se nombran en cada dato: hay una sola linea "Fuente" debajo del Aviso (ver texto_fuente y ui/marca.py).
Los datos de Yahoo (descripcion, CEO, web, mercado, valor de empresa, acciones, ingresos y crecimiento) vienen de data/fichas.json (bajar_fichas.py).
Si falta alguno, esa fila no se muestra: nunca se inventa un dato (y desde la v1.2.49 ya no hay un resumen escrito a mano de respaldo).

Linea de precios: el precio actual abajo (punto del color de la categoria) y arriba, una flecha celeste por cada metodo del Fair Value
(con su nombre y su valor); la flecha azul oscura es el Fair Value promedio. El PEG sale aparte, en gris, "solo informativo": no entra
al puntaje ni al promedio. La escala es logaritmica (la mitad y el doble del precio quedan a la misma distancia).

No usa JavaScript (los desplegables son <details>). Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import ast
import html
import math
from urllib.parse import urlparse

from config.industrias import industria_de
from config.sectors import metricas_de, partes_sector
from data import cedears as _cedears
from data import fichas as _fichas
from ui.banderas import bandera_html
from ui.tabla_visual import (_TEXTO_EN_RELLENO, _celda_dy, _clamp, _mcap, _money, _n, _svg_dy, _texto_categoria, _txt, texto_categoria)

ETIQUETAS_METODO = {"ev_ebitda": "EV/EBITDA", "per": "P/E", "p_fcf": "P/FCF", "p_b": "P/Book", "dividend_yield": "Dividend Yield",
                    "peg": "PEG", "p_ffo": "P/FFO", "p_affo": "P/AFFO", "ps": "P/S", "ev_ventas": "EV/Ventas",
                    "rend_total": "Rendimiento total"}
CELESTE = "#38bdf8"
AZUL = "#1f6aa5"
GRIS_PEG = "#94a3b8"
ALTO_NIVEL = 40            # px por nivel de etiquetas
ANCHO_ETIQUETA = 15.0      # % del ancho que ocupa una etiqueta (para que no se pisen)
PEG_RANGO_MAX = 6.0        # el PEG se dibuja si su precio implicito esta entre 1/6 y 6 veces el precio; si no, queda como nota
ABIERTOS = {"resumen"}     # mosaicos que arrancan desplegados (los demas, plegados); se cambia aca
TEXTO_VALORACION = ("Cómo llegamos a esta lectura: miramos qué tan cara o barata cotiza hoy la empresa frente a cómo cotizó históricamente, "
                    "con varias medidas a la vez, y lo resumimos en una escala que va de «Muy cara» a «Muy barata». El Fair Value es el precio que "
                    "resultaría si volviera a cotizar como suele hacerlo. Es una estimación para filtrar, no una recomendación.")

CSS = """
.fch{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;margin:14px 0 8px}
.fch-t{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);padding:14px 16px 16px;min-width:0;position:relative}
.fch-t::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--ac,#cbd5e1);border-radius:14px 0 0 14px}
.fch-h{font-size:11.5px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:#6b7280;margin:0 0 8px;padding-left:4px}
.fch-h small{text-transform:none;letter-spacing:0;font-weight:500;color:#9ca3af;margin-left:4px}
.fch-b{padding-left:4px;min-width:0}
.s3{grid-column:span 3}.s4{grid-column:span 4}.s5{grid-column:span 5}.s6{grid-column:span 6}.s7{grid-column:span 7}.s8{grid-column:span 8}.s12{grid-column:span 12}
.r2{grid-row:span 2}.r3{grid-row:span 3}
.fch-big{font-size:26px;font-weight:700;color:#0f172a;line-height:1.15;letter-spacing:-.3px}
.fch-big small{display:block;font-size:12px;font-weight:500;color:#6b7280;letter-spacing:0;margin-top:3px}
.fch-mid{font-size:17px;font-weight:600;color:#111827}
.fch-sub{font-size:12.5px;color:#4b5563;margin-top:6px;line-height:1.4}
.fch-sub b{color:#111827}
.fch-val .tv-vl{text-align:left}
.fch-val .tv-ln1,.fch-val .tv-ln2{display:inline}
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
.fch-hd{display:flex;align-items:center;gap:18px;flex-wrap:wrap;justify-content:space-between}
.fch-hd .id{display:flex;align-items:center;gap:16px;min-width:0}
.fch-hd .nm{font-size:1.9rem;font-weight:800;line-height:1.15;color:#0f172a;letter-spacing:-.4px}
.fch-hd .sb{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:5px;font-size:14px;color:#374151}
.fch-hd .tk{font-weight:700;color:#111827}
.fch-hd .pr{text-align:right}
.fch-hd .pr .v{font-size:2rem;font-weight:800;color:#0f172a;letter-spacing:-.4px;line-height:1.1}
.fch-hd .pr .ars{font-size:12.5px;color:#6b7280;margin-top:4px}
.fch-hd .pr .n{font-size:11.5px;color:#9ca3af;margin-top:2px}
.adr{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.4px;color:#1d4ed8;background:#e8f0fe;border-radius:6px;padding:1px 7px}
.fch-kv{display:grid;grid-template-columns:1fr;margin-top:14px;border-top:1px solid #eef1f4}
.fch-kv>div{display:flex;justify-content:space-between;gap:16px;padding:8px 2px;border-bottom:1px solid #eef1f4;font-size:14px}
.fch-kv .k{color:#4b5563;flex:none}
.fch-kv .v{color:#111827;text-align:right;min-width:0;overflow-wrap:anywhere}
.fch-kv .v a{color:#1d4ed8;text-decoration:none}
.fch-kv .v a:hover{text-decoration:underline}
/* v1.2.49: mosaicos desplegables */
.fch-t.fch-d{padding:0}
.fch-d>summary.fch-h{list-style:none;cursor:pointer;margin:0;padding:14px 16px 14px 20px;display:flex;align-items:center;gap:6px;user-select:none}
.fch-d>summary.fch-h::-webkit-details-marker{display:none}
.fch-d>summary.fch-h::after{content:"";margin-left:auto;width:8px;height:8px;border-right:2px solid #6b7280;border-bottom:2px solid #6b7280;transform:rotate(45deg);transition:transform .15s;flex:none;margin-right:4px}
.fch-d[open]>summary.fch-h::after{transform:rotate(-135deg)}
.fch-d>.fch-b{padding:0 16px 16px 20px}
.fch-q{position:relative;display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#e5e7eb;color:#4b5563;font-size:11px;font-weight:700;margin-left:6px;cursor:help;text-transform:none;letter-spacing:0;line-height:1}
.fch-q .fch-qt{display:none;position:absolute;left:-8px;top:24px;width:max-content;max-width:300px;background:#1f2937;color:#fff;font-size:12.5px;font-weight:400;line-height:1.45;padding:9px 11px;border-radius:8px;z-index:30;text-align:left;white-space:normal;box-shadow:0 6px 18px rgba(15,23,42,.25)}
.fch-q:hover .fch-qt,.fch-q:focus .fch-qt{display:block}
.fch-desc{font-size:14.5px;line-height:1.6;color:#1f2937;margin:0}
.fch-res{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px 40px;margin-top:16px}
.fch-res .fch-kv{margin-top:0}
.fch-cifras{display:flex;flex-direction:column;gap:18px;min-width:0}
.fch-cf .fch-k{font-size:11.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:#6b7280;margin-bottom:4px}
.fch-cf .grande{font-size:26px;font-weight:700;color:#0f172a;line-height:1.1;letter-spacing:-.3px}
.rng{position:relative;height:8px;border-radius:4px;background:#e5e7eb;margin:30px 8px 4px}
.rng-m{position:absolute;top:-6px;width:3px;height:20px;background:#0f172a;border-radius:2px;transform:translateX(-50%)}
.rng-h{position:absolute;bottom:18px;transform:translateX(-50%);white-space:nowrap;font-size:12.5px;font-weight:700;color:#0f172a}
.rng-x{display:flex;justify-content:space-between;margin-top:8px;font-size:13px;font-weight:600;color:#111827}
.rng-x small{display:block;font-size:11px;font-weight:400;color:#6b7280}
.rng-x span:last-child{text-align:right}
.fch-st2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2.2fr);gap:12px 40px}
.fch-st2 h4{margin:0 0 6px;font-size:13.5px;font-weight:700;color:#111827}
.fch-st2 .f{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:6px 0;border-bottom:1px solid #eef1f4;font-size:13.5px}
.fch-st2 .f .k{color:#4b5563}
.fch-st2 .f .v{font-weight:600;color:#111827;text-align:right;white-space:nowrap}
.fch-st2 .f .v.neg{color:#b91c1c}
.fch-st2 .f .v.pos{color:#15803d}
.fch-st2 .izq>div+div{margin-top:18px}
.vr{display:grid;grid-template-columns:minmax(72px,1.1fr) minmax(56px,.8fr) minmax(70px,1fr) 108px minmax(90px,1.1fr);gap:0 10px;align-items:center;padding:7px 0;border-bottom:1px solid #eef1f4;font-size:13.5px}
.vr.hd{font-size:11px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;color:#6b7280;padding:2px 0 6px}
.vr .m{font-weight:600;color:#111827}
.vr .n{text-align:right;white-space:nowrap}
.vr .d{line-height:0}
.vr .d img{display:block}
.vr .fv small{display:block;font-size:11px;font-weight:600}
.vr .fv .no{color:#9ca3af}
.vr .md small{display:block;font-size:11px;color:#6b7280}
.fch-st2 .nota{font-size:11.5px;color:#6b7280;margin-top:8px;line-height:1.45}
@media (max-width:900px){
.fch-hd .pr{text-align:left}
.fch-res{grid-template-columns:1fr}
.fch-st2{grid-template-columns:1fr}
.vr{grid-template-columns:1fr 1fr 1fr;grid-template-areas:"m h md" "d fv fv";gap:4px 10px}
.vr.hd{display:none}
.vr .m{grid-area:m}.vr .h{grid-area:h}.vr .md{grid-area:md}.vr .d{grid-area:d}.vr .fv{grid-area:fv}
.vr .n{text-align:left}
.fch-hd .nm{font-size:1.5rem}
}
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
    titulo = "Precio contra el Fair Value de cada método"
    if not precio or precio <= 0:
        return _plegable("linea", titulo, '<div class="fch-sub">Sin precio para dibujar la línea.</div>', ac=AZUL, cls="s12 fch-pl")
    metodos, peg_info, peg_nota = metodos_fair_value(row)
    items = [{"tipo": "m", "n": et, "v": p, "tit": f"{et}: precio que resulta de su múltiplo histórico (peso {w*100:.0f}%)"} for _, et, p, w in metodos]
    if fv and fv > 0 and metodos:
        items.append({"tipo": "avg", "n": "Fair Value promedio", "v": fv, "tit": "Promedio de los métodos, con los pesos de su sector"})
    if peg_info:
        items.append({"tipo": "peg", "n": "PEG (informativo)", "v": peg_info, "tit": "El PEG no entra al puntaje ni al Fair Value: se muestra solo como dato"})
    if not items:
        sin = '<div class="fch-sub">Esta empresa no tiene un Fair Value calculado (faltan datos para sus métodos).</div>'
        return _plegable("linea", titulo, sin, ac=AZUL, cls="s12 fch-pl")
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
    titulo = f"Precio contra el Fair Value de cada método{chip}"
    exp = ('<div class="fch-ex">Abajo, el precio de hoy. Arriba, cada flecha es el precio que resultaría de aplicar un método con la mediana histórica '
           'de su múltiplo; la azul oscura es el promedio ponderado (el Fair Value). Escala logarítmica. Es una estimación, no una recomendación.</div>')
    cuerpo = (f'{exp}<div class="pl-wrap"><div class="pl" style="height:{alto}px">' + "".join(partes) + f'</div></div>{ley}{nota}')
    return _plegable("linea", titulo, cuerpo, ac=AZUL, cls="s12 fch-pl")


def _texto_plano_categoria(cat):
    from scoring.engine import nombre_visible
    from ui.tabla_visual import _mayusculas, _partes_nombre
    return html.escape(_mayusculas(_partes_nombre(nombre_visible(cat))[1]))


def _tile(cls, titulo, cuerpo, ac="#cbd5e1", extra=""):
    return f'<div class="fch-t {cls}" style="--ac:{ac}"><div class="fch-h">{titulo}</div><div class="fch-b">{cuerpo}</div>{extra}</div>'


def _plegable(clave, titulo, cuerpo, ac="#cbd5e1", cls="s12"):
    """Mosaico que se despliega y se pliega (<details>). `clave` decide si arranca abierto (ABIERTOS)."""
    abierto = " open" if clave in ABIERTOS else ""
    return (f'<details class="fch-t fch-d {cls}" data-mosaico="{clave}" style="--ac:{ac}"{abierto}>'
            f'<summary class="fch-h">{titulo}</summary><div class="fch-b">{cuerpo}</div></details>')


def _ayuda(texto):
    """Signo de pregunta con una nota que aparece al pasar el mouse (o al tocarlo en el celular). Solo CSS."""
    return f'<span class="fch-q" tabindex="0">?<span class="fch-qt">{html.escape(texto)}</span></span>'


# ---------------------------------------------------------------------------
# v1.2.47: formato nuevo
# ---------------------------------------------------------------------------

def _abrev(x, prefijo=""):
    """1.234.567.890 -> '1.2B' (M = millon, B = mil millones, T = billon), con un prefijo opcional ('US$ ')."""
    v = _n(x)
    if v is None or v <= 0:
        return "—"
    for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= lim:
            return f"{prefijo}{v / lim:.1f}{suf}"
    return f"{prefijo}{v:,.0f}"


def _usd_abrev(x):
    t = _abrev(x, "US&#36;&nbsp;")
    return t


def _pct_sig(x):
    """0.123 -> '+12.3%' (con color: verde si crece, rojo si cae)."""
    v = _n(x)
    if v is None:
        return None, ""
    return f"{v * 100:+.1f}%", ("pos" if v > 0 else "neg" if v < 0 else "")


def _dominio(url):
    """'https://www.apple.com/' -> 'apple.com' (solo si es un link http/https)."""
    try:
        u = urlparse(str(url or "").strip())
        if u.scheme not in ("http", "https") or not u.netloc:
            return None, None
        return u.netloc.removeprefix("www."), f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}"
    except Exception:  # noqa: BLE001
        return None, None


def _texto_descripcion(ficha):
    """La descripcion de Yahoo en castellano; si solo hay la original, en ingles; si no hay nada, ''. (Desde la v1.2.49 ya no hay un resumen
    escrito a mano de respaldo: sin dato de Yahoo, el mosaico dice que la descripcion esta pendiente.)"""
    es, en = (ficha or {}).get("descripcion_es"), (ficha or {}).get("descripcion_en")
    if isinstance(es, str) and es.strip():
        return es.strip()
    if isinstance(en, str) and en.strip():
        return en.strip()
    return ""


def texto_fuente(ficha=None):
    """Linea "Fuente" que va debajo del Aviso (v1.2.49). Las fuentes no se nombran en cada dato. Si la descripcion es una traduccion automatica,
    lo aclara."""
    t = "Stock Analysis y Yahoo Finance."
    es = (ficha or {}).get("descripcion_es") if ficha is not None else None
    if isinstance(es, str) and es.strip():
        t += " La descripción de la empresa es una traducción automática del texto de Yahoo Finance y puede tener errores."
    return t


def _fecha_ar(texto):
    """'2026-10-22' -> '22/10/2026' (si no tiene ese formato, se devuelve igual)."""
    t = str(texto or "").strip()
    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
        return f"{t[8:10]}/{t[5:7]}/{t[0:4]}"
    return t


def _linea_pesos(row, datos):
    """'Precio en pesos $ 25.394 (ratio 20 : 1)' (chico y gris, debajo del precio en dolares). Sin ratio confirmado no se muestra nada."""
    d = (datos or {}).get(str(row.get("ticker", "")).upper()) or {}
    if not d.get("ratio"):
        return ""
    ratio = _cedears.ratio_texto(d.get("ratio"))
    ars = _n(d.get("precio_ars"))
    if ars:
        return f'Precio en pesos {_ars(ars)} (ratio {html.escape(ratio)})'
    return f'Precio en pesos: sin dato por ahora (ratio {html.escape(ratio)})'


def _encabezado(row, mercado, ficha, datos=None, fecha_datos=None):
    t = str(row.get("ticker", ""))
    nombre = html.escape(str(row.get("nombre") or t).strip())
    from ui.logos import logo_html
    adr = _fichas.es_adr(t)
    tk_txt = f"{html.escape(mercado)}: {html.escape(t)}" if mercado else html.escape(t)
    adr_html = ('<span class="adr" title="ADR: certificado que representa acciones de una empresa extranjera y cotiza en Estados Unidos">ADR</span>' if adr else "")
    pais = row.get("pais")
    pa = f'<span>{bandera_html(pais, chica=True)} {html.escape(pais)}</span>' if isinstance(pais, str) and pais else ""
    p = _n(row.get("precio_actual"))
    if p and p > 0:
        if row.get("precio_en_vivo") == True:  # noqa: E712  (puede ser numpy.bool_)
            # v1.2.49: "Dato al dd/mm/aaaa hh:mm" (solo el dia y la hora; sin nombrar la fuente)
            f, h = _txt(row.get("precio_fecha"), ""), _txt(row.get("precio_hora"), "")
            nota = "Dato al " + " ".join(x for x in (html.escape(f), html.escape(h)) if x) if (f or h) else "Precio en vivo"
        else:
            f = _fecha_ar(fecha_datos)
            nota = f"Dato al {html.escape(f)}" if f else "Precio de la última actualización de los datos"
        pesos = _linea_pesos(row, datos)
        pesos_html = f'<div class="ars">{pesos}</div>' if pesos else ""
        precio = f'<div class="pr"><div class="v">{_money(p)}</div>{pesos_html}<div class="n">{nota}</div></div>'
    else:
        precio = ""
    return (f'<div class="fch-t s12" style="--ac:#64748b"><div class="fch-hd"><div class="id">{logo_html(t, 56)}<div>'
            f'<div class="nm">{nombre}</div><div class="sb"><span class="tk">{tk_txt}</span>{adr_html}{pa}</div></div></div>{precio}</div></div>')


def _fila_kv(k, v):
    return f'<div><span class="k">{k}</span><span class="v">{v}</span></div>'


def _barra_52s(row):
    """Rango de 52 semanas: una barrita con una marca en el lugar del precio de hoy (con su valor encima) y, en los extremos, el minimo y el maximo."""
    lo, hi, p = _n(row.get("precio_min_52s")), _n(row.get("precio_max_52s")), _n(row.get("precio_actual"))
    pos = _n(row.get("posicion_52s"))
    if lo is None or hi is None or hi <= lo:
        return '<div class="fch-sub" style="margin:0">Sin datos de rango de 52 semanas.</div>'
    if p and p > 0:
        pct = _clamp((p - lo) / (hi - lo) * 100)
    elif pos is not None:
        pct = _clamp(pos * 100)
    else:
        pct = 50.0
    hoy = f"Hoy {_money(p)}" if p and p > 0 else ""
    marca = (f'<div class="rng-h" style="left:{_clamp(pct, 14, 86):.1f}%">{hoy}</div>' if hoy else "")
    return (f'<div class="rng" title="Rango de los últimos 12 meses: de su precio más bajo a su precio más alto. La marca es el precio de hoy.">{marca}'
            f'<div class="rng-m" style="left:{pct:.1f}%"></div></div>'
            f'<div class="rng-x"><span>{_money(lo)}<small>Mínimo</small></span><span>{_money(hi)}<small>Máximo</small></span></div>')


_FOSO_CACHE = {}


def _foso_de(ticker):
    """Foso competitivo de la empresa (data/foso.json, armado con foso_desde_lote.py a partir del Modo lote del DCF) o None si no esta."""
    import json, os
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "foso.json")
    try:
        m = os.path.getmtime(ruta)
        if _FOSO_CACHE.get("m") != m:
            with open(ruta, encoding="utf-8") as f:
                _FOSO_CACHE.update(m=m, d=(json.load(f) or {}).get("empresas", {}))
        return _FOSO_CACHE["d"].get(str(ticker).upper())
    except (OSError, ValueError):
        return None


def _tile_resumen(row, ficha, mercado):
    t = str(row.get("ticker", ""))
    texto = _texto_descripcion(ficha)
    desc = (f'<p class="fch-desc">{html.escape(texto)}</p>' if texto
            else '<div class="fch-sub" style="margin:0">Descripción pendiente de cargar.</div>')
    sector, industria = partes_sector(row.get("sector"))
    sector = _txt(row.get("sector_macro"), "") or sector or ""
    industria = _txt(row.get("industria"), "") or industria_de(t) or ""
    filas = [_fila_kv("Nombre", html.escape(str(row.get("nombre") or t).strip()))]
    ceo = (ficha or {}).get("ceo")
    if ceo:
        filas.append(_fila_kv("CEO", html.escape(str(ceo))))
    dom, url = _dominio((ficha or {}).get("web"))
    if dom:
        filas.append(_fila_kv("Sitio web", f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(dom)}</a>'))
    filas.append(_fila_kv("Sector", html.escape(sector) or "—"))
    filas.append(_fila_kv("Industria", html.escape(industria) or "—"))
    foso = _foso_de(t)      # v1.2.51: foso competitivo (Amplio / Estrecho / Ninguno), solo donde hay dato
    if foso and foso.get("foso"):
        filas.append(_fila_kv("Foso competitivo", f'<span title="Ventaja competitiva que se sostiene en el tiempo: retorno sobre el capital por encima del costo del capital, márgenes estables y mejores que los de su sector.">{html.escape(foso["foso"])}</span>'))
    if mercado:
        adr = ' · <span title="ADR: certificado que representa acciones de una empresa extranjera y cotiza en Estados Unidos">ADR</span>' if _fichas.es_adr(t) else ""
        filas.append(_fila_kv("Mercado donde cotiza", html.escape(mercado) + adr))
    pais = row.get("pais")
    ciudad = ", ".join(x for x in ((ficha or {}).get("ciudad"), (ficha or {}).get("region")) if x)
    if isinstance(pais, str) and pais:
        filas.append(_fila_kv("Sede fiscal", f'{bandera_html(pais, chica=True)} ' + html.escape(f"{ciudad}, {pais}" if ciudad else pais)))
    emp = _n((ficha or {}).get("empleados"))
    if emp:
        filas.append(_fila_kv("Empleados", f"{emp:,.0f}"))
    izq = '<div class="fch-kv">' + "".join(filas) + "</div>"
    der = ('<div class="fch-cifras">'
           f'<div class="fch-cf"><div class="fch-k">Capitalización bursátil</div><div class="grande">{_mcap(row.get("market_cap"))}</div></div>'
           f'<div class="fch-cf"><div class="fch-k">Rango de 52 semanas</div>{_barra_52s(row)}</div>'
           f'<div class="fch-cf fch-dy"><div class="fch-k">Dividend Yield</div>{_celda_dy(row, grande=True)}</div>'
           '</div>')
    return _plegable("resumen", "Resumen de la empresa", desc + f'<div class="fch-res">{izq}{der}</div>', ac="#a78bfa")


def _color_por_ratio(ratio):
    """Color del punto cuando la metrica no tiene puntaje propio: mismos cortes que usa el Dividend Yield (ratio > 1 = mas barata que lo habitual)."""
    from scoring.engine import get_categoria_label
    sc = 85 if ratio >= 1.25 else 64 if ratio >= 1.08 else 50 if ratio >= 0.92 else 36 if ratio >= 0.75 else 15
    return get_categoria_label(sc)[1]


def _dibujo_metrica(actual, mediana, score, invertir):
    """Dibujito de una metrica: la marca del centro es su mediana historica y el punto es hoy; a la derecha = mas barata que lo habitual.
    Para los multiplos (menos es mas barato) se invierte la relacion; para el Dividend Yield (mas es mas barato) no."""
    if not actual or not mediana or actual <= 0 or mediana <= 0:
        return ""
    from scoring.engine import get_categoria_label
    ratio = (mediana / actual) if invertir else (actual / mediana)
    color = get_categoria_label(score)[1] if score is not None else _color_por_ratio(ratio)
    return _svg_dy(ratio, color, W=108, H=18)


def _tile_estadisticas(row, ficha):
    """Estadisticas de la empresa (v1.2.49: une las estadisticas con el desglose de metricas). Izquierda: Perfil y Crecimiento. Derecha: Valoracion,
    una fila por multiplo con el valor de hoy, su mediana historica, un dibujito (hoy contra la mediana), el Fair Value que da y su peso."""
    f = ficha or {}
    precio = _n(row.get("precio_actual"))
    # --- Perfil ---
    perfil = [("Capitalización bursátil", _mcap(row.get("market_cap")))]
    if _n(f.get("ev")):
        perfil.append(("Valor de empresa (EV)", _usd_abrev(f.get("ev"))))
    if _n(f.get("acciones")):
        perfil.append(("Acciones en circulación", _abrev(f.get("acciones"))))
    if _n(f.get("ingresos_ttm")):
        perfil.append(("Ingresos (12 meses)", _usd_abrev(f.get("ingresos_ttm"))))
    # --- Crecimiento ---
    cre = []
    for clave, etiqueta in (("cagr_ingresos_3a", "Ingresos, 3 años (anual compuesto)"), ("cagr_eps_3a", "Ganancia por acción, 3 años (anual compuesto)"),
                            ("crec_ingresos_trim", "Ingresos, último trimestre vs año anterior"), ("crec_ganancias_trim", "Ganancias, último trimestre vs año anterior")):
        txt, cls = _pct_sig(f.get(clave))
        if txt:
            cre.append((etiqueta, f'<span class="v {cls}">{txt}</span>'))

    def col(titulo, filas):
        if not filas:
            return ""
        h = "".join(f'<div class="f"><span class="k">{k}</span>' + (v if v.startswith('<span class="v') else f'<span class="v">{v}</span>') + "</div>" for k, v in filas)
        return f'<div><h4>{titulo}</h4>{h}</div>'

    # --- Valoracion ---
    det = _dict(row.get("detalle"))
    fvd = _dict(row.get("fair_value_detalle"))
    esperados = (metricas_de(row, row.get("sector")) or {}) if row.get("sector") else {}
    filas_v, hay_sin_fv = [], False
    for clave, etiqueta, col_a, col_m in (("per", "P/E", "per_actual", "per_mediana"), ("p_b", "P/Book", "p_b_actual", "p_b_mediana"),
                                           ("ps", "P/S", "ps_actual", "ps_mediana"), ("ev_ventas", "EV/Ventas", "ev_ventas_actual", "ev_ventas_mediana"),
                                           ("ev_ebitda", "EV/EBITDA", "ev_ebitda_actual", "ev_ebitda_mediana"),
                                           ("p_fcf", "P/FCF", "p_fcf_actual", "p_fcf_mediana"), ("p_ffo", "P/FFO", "p_ffo_actual", "p_ffo_mediana"),
                                           ("p_affo", "P/AFFO", "p_affo_actual", "p_affo_mediana"), ("peg", "PEG", "peg_actual", "peg_mediana"),
                                           ("dividend_yield", "Dividend Yield", "dividend_yield_actual", "dividend_yield_mediana"),
                                           ("rend_total", "Rendimiento total", "rend_total_actual", "rend_total_mediana")):
        a, m = _n(row.get(col_a)), _n(row.get(col_m))
        if not a or a <= 0:
            continue
        d = det.get(clave) if isinstance(det.get(clave), dict) else {}
        if d.get("estado") == "descartada":
            continue
        if clave in ("p_ffo", "p_affo", "ev_ventas", "rend_total") and clave not in esperados:
            continue            # P/FFO y P/AFFO solo tienen sentido en los REITs; EV/Ventas y Rendimiento total solo se muestran si la empresa los usa
        es_dy = clave in ("dividend_yield", "rend_total")
        if es_dy:                # el caché guarda el rendimiento como fraccion; la pantalla lo muestra en %
            a = a if a > 1 else a * 100
            m = (m if m > 1 else m * 100) if m and m > 0 else None
            hoy = f"{a:.2f}%"
            med = f"{m:.2f}%" if m else "—"
        else:
            hoy = f"{a:.1f}x"
            med = f"{m:.1f}x" if m and m > 0 else "—"
        sub = '<small>de su sector</small>' if d.get("referencia") == "sector" else ""
        dib = _dibujo_metrica(a, m, _n(d.get("score")), invertir=not es_dy)
        tip = "Marca del centro: su mediana histórica. Punto: hoy. A la derecha, más barata que lo habitual; a la izquierda, más cara."
        dib_html = f'<span class="d" title="{html.escape(tip)}">{dib}</span>' if dib else '<span class="d"></span>'
        pm = _n((fvd.get(clave) or {}).get("precio")) if isinstance(fvd.get(clave), dict) else None
        if pm and pm > 0:
            extra = ""
            if precio and precio > 0:
                v = (pm - precio) / precio
                colr = "#15803d" if v > 0.05 else "#b91c1c" if v < -0.05 else "#a16207"
                extra = f'<small style="color:{colr}">{_pct(precio, pm)}</small>'
            fv_html = f'<span class="n fv"><b>{_money(pm)}</b>{extra}</span>'
        else:
            hay_sin_fv = True
            fv_html = '<span class="n fv"><span class="no" title="No entra al Fair Value de esta empresa">—</span></span>'
        filas_v.append(f'<div class="vr"><span class="m">{etiqueta}</span><span class="n h">{hoy}</span><span class="n md">{med}{sub}</span>'
                       f'{dib_html}{fv_html}</div>')
    val = ""
    if filas_v:
        cab = ('<div class="vr hd"><span>Métrica</span><span class="n">Hoy</span><span class="n">Mediana histórica</span><span>Hoy vs. mediana</span>'
               '<span class="n">Fair Value</span></div>')
        nota = ('<div class="nota">En el dibujito, la marca del centro es la mediana histórica y el punto es hoy: a la derecha, más barata que lo habitual; '
                'a la izquierda, más cara.' + (' Un “—” en Fair Value significa que ese dato se muestra pero no entra al cálculo de esta empresa.' if hay_sin_fv else '')
                + '</div>')
        nota_moneda = row.get("moneda_nota")      # v1.2.50: antes se mostraba en la "Revisión de los métodos", que se quitó
        moneda = f'<div class="fch-nota">Moneda: {html.escape(nota_moneda)}</div>' if isinstance(nota_moneda, str) and nota_moneda.strip() else ""
        val = f'<div><h4>Valoración (12 meses)</h4>{cab}{"".join(filas_v)}{nota}{moneda}</div>'
    izq = "".join(c for c in (col("Perfil", perfil), col("Crecimiento", cre)) if c)
    cuerpo = f'<div class="fch-st2"><div class="izq">{izq}</div>{val}</div>' if val else f'<div class="fch-st2" style="grid-template-columns:1fr"><div class="izq">{izq}</div></div>'
    return _plegable("estadisticas", "Estadísticas de la empresa", cuerpo, ac="#3b82f6")


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
    return _tile("s6", "Score de calidad", cuerpo, ac=color)


def _tile_valoracion(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    cat = _texto_categoria(_txt(row.get("categoria"), "—"), color, True)
    if precio and fv and precio > 0 and fv > 0:
        fvt = f'<div class="fch-sub">Fair Value <b>{_money(fv)}</b> ({_pct(precio, fv)} frente al precio de hoy)</div>'
    else:
        fvt = '<div class="fch-sub">Sin Fair Value: faltan datos para calcularlo.</div>'
    return _tile("s6", "Valoración" + _ayuda(TEXTO_VALORACION), f'<div style="text-align:left" class="fch-val">{cat}</div>{fvt}', ac=color)


def ficha_html(row, cedears=None, ficha=None, mercado_codigo=None, fecha_datos=None):
    """Todos los mosaicos de la pagina de la empresa. `row` es el dict de la fila; `cedears` el resultado de data.cedears.cargar() (con el precio en
    pesos si se pudo); `ficha` los datos de Yahoo de la empresa (data/fichas.json); `mercado_codigo` el codigo del mercado pedido a Yahoo en el momento;
    `fecha_datos` la fecha de los datos del cache (para el "Dato al ..." cuando el precio no es el de hoy)."""
    datos = cedears if cedears is not None else _cedears.cargar()
    mercado, adr = _fichas.mercado_y_adr(row.get("ticker"), ficha, mercado_codigo)
    mosaicos = [_encabezado(row, mercado, ficha, datos, fecha_datos), _tile_resumen(row, ficha, mercado), _tile_score(row), _tile_valoracion(row),
                _tile_estadisticas(row, ficha), linea_precios_html(row)]
    return '<div class="fch">' + "".join(m for m in mosaicos if m) + "</div>"
