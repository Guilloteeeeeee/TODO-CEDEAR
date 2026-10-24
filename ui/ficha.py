"""
Ficha de la pagina de una empresa (v1.2.46; formato tipo Fiscal AI desde la v1.2.47).

Estructura (los datos y su orden siguen la ficha "Company Overview / Company Statistics" de Fiscal AI; el estilo es el de TodoCedears):
  1. Encabezado: logo, nombre, mercado donde cotiza y ticker (con ADR si es un certificado de deposito), bandera y pais, y el precio de hoy.
  2. Resumen de la empresa: la descripcion (de Yahoo Finance, traducida) y, abajo, una lista de datos: nombre, CEO, sitio web, sector, industria,
     mercado, sede y empleados. A la derecha: el Score de calidad, la Valoracion (con el Fair Value) y el CEDEAR (ratio y precio en pesos).
  3. Estadisticas de la empresa, en tres columnas: Perfil (capitalizacion, valor de empresa, acciones, ingresos), Valoracion (los multiplos de hoy
     con su mediana historica) y Crecimiento.
  4. Rango de 52 semanas, Dividend Yield contra su mediana y como sale el puntaje.
  5. La linea de precios: el precio actual abajo y arriba el Fair Value de cada metodo (flechas celestes) y el PEG informativo.
  6. Revision de los metodos del Fair Value (antes era una vista de la tabla): que metodos se usaron, con su peso y su precio, y cuales no y por que.
Los datos de Yahoo (descripcion, CEO, web, mercado, valor de empresa, acciones, ingresos y crecimiento) vienen de data/fichas.json (bajar_fichas.py).
Si falta alguno, esa fila no se muestra: nunca se inventa un dato.

Linea de precios: el precio actual abajo (punto del color de la categoria) y arriba, una flecha celeste por cada metodo del Fair Value
(con su nombre y su valor); la flecha azul oscura es el Fair Value promedio. El PEG sale aparte, en gris, "solo informativo": no entra
al puntaje ni al promedio. La escala es logaritmica (la mitad y el doble del precio quedan a la misma distancia).

No usa JavaScript. Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import ast
import html
import math
from urllib.parse import urlparse

from config.descripciones import descripcion_de
from config.industrias import industria_de
from config.sectors import metricas_de, partes_sector
from data import cedears as _cedears
from data import fichas as _fichas
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
CORTE_DESCRIPCION = 430    # letras que se ven de la descripcion antes de "Mostrar mas"

CSS = """
.fch{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;margin:14px 0 8px}
.fch-t{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);padding:14px 16px 16px;min-width:0;position:relative;overflow:hidden}
.fch-t::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--ac,#cbd5e1)}
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
.fch-hd{display:flex;align-items:center;gap:18px;flex-wrap:wrap;justify-content:space-between}
.fch-hd .id{display:flex;align-items:center;gap:16px;min-width:0}
.fch-hd .nm{font-size:1.9rem;font-weight:800;line-height:1.15;color:#0f172a;letter-spacing:-.4px}
.fch-hd .sb{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:5px;font-size:14px;color:#374151}
.fch-hd .tk{font-weight:700;color:#111827}
.fch-hd .pr{text-align:right}
.fch-hd .pr .v{font-size:2rem;font-weight:800;color:#0f172a;letter-spacing:-.4px;line-height:1.1}
.fch-hd .pr .n{font-size:12px;color:#6b7280;margin-top:3px}
.adr{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.4px;color:#1d4ed8;background:#e8f0fe;border-radius:6px;padding:1px 7px}
.fch-kv{display:grid;grid-template-columns:1fr;margin-top:14px;border-top:1px solid #eef1f4}
.fch-kv>div{display:flex;justify-content:space-between;gap:16px;padding:8px 2px;border-bottom:1px solid #eef1f4;font-size:14px}
.fch-kv .k{color:#4b5563;flex:none}
.fch-kv .v{color:#111827;text-align:right;min-width:0;overflow-wrap:anywhere}
.fch-kv .v a{color:#1d4ed8;text-decoration:none}
.fch-kv .v a:hover{text-decoration:underline}
.fch-mas{display:block;margin-top:2px}
.fch-mas summary{cursor:pointer;color:#1d4ed8;font-weight:600;font-size:13.5px;margin:4px 0;list-style:none}
.fch-mas summary::-webkit-details-marker{display:none}
.fch-mas[open] summary{display:none}
.fch-st{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px 36px}
.fch-st h4{margin:0 0 6px;font-size:13.5px;font-weight:700;color:#111827}
.fch-st .f{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:6px 0;border-bottom:1px solid #eef1f4;font-size:13.5px}
.fch-st .f .k{color:#4b5563}
.fch-st .f .v{font-weight:600;color:#111827;text-align:right;white-space:nowrap}
.fch-st .f .v small{display:block;font-weight:400;font-size:11px;color:#6b7280}
.fch-st .f .v.neg{color:#b91c1c}
.fch-st .f .v.pos{color:#15803d}
.fch-st .nota{font-size:11.5px;color:#9ca3af;margin-top:6px}
.rev{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:2px}
.rev th{text-align:left;font-size:11.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:#6b7280;padding:4px 8px 6px 0;border:0!important;border-bottom:1px solid #e5e7eb!important}
.rev td{padding:7px 8px 7px 0;border:0!important;border-bottom:1px solid #f0f2f5!important;color:#1f2937;vertical-align:top}
.rev .ok{font-weight:600}
.rev .no{color:#6b7280}
.rev td.n,.rev th.n{text-align:right;white-space:nowrap}
.rev-r{font-size:12.5px;color:#4b5563;margin:8px 0 0;line-height:1.5}
@media (max-width:900px){
.fch-hd .pr{text-align:left}
.fch-hd .nm{font-size:1.5rem}
.fch-st{grid-template-columns:1fr;gap:18px}
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
    cab = ('<div class="fch-h">Precio contra el Fair Value de cada método</div>')
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


def _veces(x):
    v = _n(x)
    return "—" if v is None or v <= 0 else f"{v:.1f}x"


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


def _texto_descripcion(row, ficha):
    """(texto, nota): la descripcion de Yahoo en castellano; si solo hay la original, en ingles; si no hay nada de Yahoo, el resumen propio."""
    es, en = (ficha or {}).get("descripcion_es"), (ficha or {}).get("descripcion_en")
    if isinstance(es, str) and es.strip():
        return es.strip(), "Fuente: Yahoo Finance, traducida automáticamente (puede tener errores)."
    if isinstance(en, str) and en.strip():
        return en.strip(), "Fuente: Yahoo Finance (texto original, en inglés)."
    d = descripcion_de(row.get("ticker"))
    return (d, "Resumen general de lo que hace la empresa, sin cifras.") if d else ("", "")


def _cortar(texto, corte=CORTE_DESCRIPCION):
    """(primera parte, resto): se corta en el fin de una oracion cerca de `corte` letras."""
    if len(texto) <= corte + 60:
        return texto, ""
    i = max(texto.rfind(". ", 0, corte + 60), texto.rfind("? ", 0, corte + 60))
    if i < corte // 2:
        i = texto.find(" ", corte)
    return (texto[: i + 1].strip(), texto[i + 1:].strip()) if i > 0 else (texto, "")


def _encabezado(row, mercado, ficha):
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
            fuente = _txt(row.get("precio_fuente"), "Yahoo Finance")
            f, h = _txt(row.get("precio_fecha"), ""), _txt(row.get("precio_hora"), "")
            nota = html.escape(fuente) + (f" · dato del {html.escape(f)}" if f else "") + (f" (consultado {html.escape(h)})" if h else "")
        else:
            nota = "Precio de la última actualización de los datos"
        precio = f'<div class="pr"><div class="v">{_money(p)}</div><div class="n">{nota}</div></div>'
    else:
        precio = ""
    return (f'<div class="fch-t s12" style="--ac:#64748b"><div class="fch-hd"><div class="id">{logo_html(t, 56)}<div>'
            f'<div class="nm">{nombre}</div><div class="sb"><span class="tk">{tk_txt}</span>{adr_html}{pa}</div></div></div>{precio}</div></div>')


def _fila_kv(k, v):
    return f'<div><span class="k">{k}</span><span class="v">{v}</span></div>'


def _tile_resumen(row, ficha, mercado):
    t = str(row.get("ticker", ""))
    texto, nota = _texto_descripcion(row, ficha)
    if texto:
        a, b = _cortar(texto)
        masa = f'<details class="fch-mas"><summary>Mostrar más</summary>{html.escape(b)}</details>' if b else ""
        desc = f'<div class="fch-txt">{html.escape(a)}{masa}</div><div class="fch-nota">{html.escape(nota)}</div>'
    else:
        desc = '<div class="fch-sub">Descripción pendiente de cargar.</div>'
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
    cuerpo = desc + '<div class="fch-kv">' + "".join(filas) + "</div>"
    return _tile("s7 r3", "Resumen de la empresa", cuerpo, ac="#a78bfa")


def _tile_estadisticas(row, ficha):
    f = ficha or {}
    # --- Perfil ---
    perfil = [("Capitalización bursátil", _mcap(row.get("market_cap")))]
    if _n(f.get("ev")):
        perfil.append(("Valor de empresa (EV)", _usd_abrev(f.get("ev"))))
    if _n(f.get("acciones")):
        perfil.append(("Acciones en circulación", _abrev(f.get("acciones"))))
    if _n(f.get("ingresos_ttm")):
        perfil.append(("Ingresos (12 meses)", _usd_abrev(f.get("ingresos_ttm"))))
    # --- Valoracion (los multiplos de hoy, con su mediana historica) ---
    det = _dict(row.get("detalle"))
    usadas = set(metricas_de(row, row.get("sector")) or {}) if row.get("sector") else set()
    val = []
    for clave, etiqueta, col_a, col_m in (("per", "P/E", "per_actual", "per_mediana"), ("p_b", "P/Book", "p_b_actual", "p_b_mediana"),
                                           ("ps", "P/S", "ps_actual", "ps_mediana"), ("ev_ebitda", "EV/EBITDA", "ev_ebitda_actual", "ev_ebitda_mediana"),
                                           ("p_fcf", "P/FCF", "p_fcf_actual", "p_fcf_mediana"), ("p_ffo", "P/FFO", "p_ffo_actual", "p_ffo_mediana"),
                                           ("peg", "PEG", "peg_actual", "peg_mediana")):
        a, m = _n(row.get(col_a)), _n(row.get(col_m))
        if not a or a <= 0:
            continue
        d = det.get(clave) if isinstance(det.get(clave), dict) else {}
        if d.get("estado") == "descartada":
            continue
        if clave == "p_ffo" and clave not in usadas:
            continue            # el P/FFO solo tiene sentido en los REITs
        info = "" if clave in usadas else " (informativo)"
        sub = f"<small>mediana {m:.1f}x</small>" if m and m > 0 else ""
        val.append((etiqueta + info, f"{a:.1f}x{sub}"))
    dy, dm = _n(row.get("dividend_yield_actual")), _n(row.get("dividend_yield_mediana"))
    if dy and dy > 0:
        dyp = dy if dy > 1 else dy * 100
        dmp = (dm if dm > 1 else dm * 100) if dm and dm > 0 else None
        val.append(("Dividend Yield", f"{dyp:.2f}%" + (f"<small>mediana {dmp:.2f}%</small>" if dmp else "")))
    # --- Crecimiento ---
    cre = []
    for clave, etiqueta in (("cagr_ingresos_3a", "Ingresos, 3 años (anual compuesto)"), ("cagr_eps_3a", "Ganancia por acción, 3 años (anual compuesto)"),
                            ("crec_ingresos_trim", "Ingresos, último trimestre vs año anterior"), ("crec_ganancias_trim", "Ganancias, último trimestre vs año anterior")):
        txt, cls = _pct_sig(f.get(clave))
        if txt:
            cre.append((etiqueta, f'<span class="v {cls}">{txt}</span>'))

    def col(titulo, filas, nota=""):
        if not filas:
            return ""
        h = "".join(f'<div class="f"><span class="k">{k}</span>' + (v if v.startswith('<span class="v') else f'<span class="v">{v}</span>') + "</div>" for k, v in filas)
        return f'<div><h4>{titulo}</h4>{h}{nota}</div>'

    nota_val = '<div class="nota">Múltiplos de hoy; abajo, su mediana histórica. “Informativo”: no entra al puntaje.</div>'
    cols = [col("Perfil", perfil), col("Valoración (12 meses)", val, nota_val), col("Crecimiento", cre)]
    cols = [c for c in cols if c]
    st = f'<div class="fch-st" style="grid-template-columns:repeat({len(cols)},minmax(0,1fr))">' + "".join(cols) + "</div>"
    return _tile("s12", "Estadísticas de la empresa <small>en dólares (US$)</small>", st, ac="#3b82f6")


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
    return _tile("s5", "Score de calidad", cuerpo, ac=color)


def _tile_valoracion(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    cat = _texto_categoria(_txt(row.get("categoria"), "—"), color, True)
    if precio and fv and precio > 0 and fv > 0:
        fvt = f'<div class="fch-sub">Fair Value <b>{_money(fv)}</b> ({_pct(precio, fv)} frente al precio de hoy)</div>'
    else:
        fvt = '<div class="fch-sub">Sin Fair Value: faltan datos para calcularlo.</div>'
    return _tile("s5", "Valoración", f'<div style="text-align:left" class="fch-val">{cat}</div>{fvt}', ac=color)


def _tile_cedear(row, datos):
    d = datos.get(str(row.get("ticker", "")).upper()) or {}
    ratio = _cedears.ratio_texto(d.get("ratio"))
    ars = _n(d.get("precio_ars"))
    precio = _ars(ars) if ars else "—"
    hora = f' <span style="color:#9ca3af;font-size:12px">({html.escape(str(d["hora"]))})</span>' if ars and d.get("hora") else ""
    ccl = _n(d.get("ccl"))
    sim = html.escape(str(d.get("simbolo") or ""))
    if ars and ccl:
        fuente = d.get("fuente_ars") or "Yahoo Finance"
        de = f"{fuente} ({sim}.BA)" if "yahoo" in str(fuente).lower() else f"{fuente} ({sim})"
        nota = f'<div class="fch-nota">Dólar implícito: {_ars(ccl)} · Fuente: {html.escape(de)}</div>'
    elif d.get("ratio"):
        nota = '<div class="fch-nota">Sin precio en pesos ahora: ninguna fuente (Yahoo, Rava) lo entregó o no pasó el control de coherencia.</div>'
    else:
        nota = '<div class="fch-nota">No tenemos el ratio de conversión de este CEDEAR confirmado, por eso no mostramos su precio en pesos.</div>'
    cuerpo = (f'<div class="fch-par"><div><div class="fch-k">Ratio de conversión</div><div class="fch-v">{ratio}</div></div>'
              f'<div><div class="fch-k">Precio en pesos</div><div class="fch-v">{precio}{hora}</div></div></div>{nota}')
    return _tile("s5", "CEDEAR", cuerpo, ac="#38bdf8")


def _motivo_metodo_faltante(row, metrica):
    """Por que un metodo del sector no aporto precio al Fair Value."""
    descartados = row.get("fair_value_descartados")
    if isinstance(descartados, dict) and descartados.get(metrica):
        return str(descartados[metrica])
    mediana, actual = _n(row.get(f"{metrica}_mediana")), _n(row.get(f"{metrica}_actual"))
    if metrica == "dividend_yield":
        div = _n(row.get("annual_dividend"))
        if not (div and div > 0) and not (actual and actual > 0):
            return "no paga dividendo"
    if not mediana or mediana <= 0:
        return "sin mediana histórica"
    if metrica != "dividend_yield" and (not actual or actual <= 0):
        return "sin dato actual"
    return "sin precio implícito válido"


def _tile_revision(row):
    """Revision de los metodos del Fair Value (v1.2.47; antes era una vista de la tabla): una fila por metodo del sector, con su peso, el precio que
    resulta y cuanto mas o menos que el precio de hoy, o el motivo por el que no se pudo usar."""
    esperados = metricas_de(row, row.get("sector")) if row.get("sector") else {}
    if not esperados:
        return ""
    det = _dict(row.get("fair_value_detalle"))
    precio = _n(row.get("precio_actual"))
    filas, ok = [], 0
    for m, peso in esperados.items():
        et = ETIQUETAS_METODO.get(m, m)
        d = det.get(m) if isinstance(det.get(m), dict) else None
        pm = _n(d.get("precio")) if d else None
        if pm and pm > 0:
            ok += 1
            up = ""
            if precio and precio > 0:
                v = (pm - precio) / precio
                col = "#15803d" if v > 0.05 else "#b91c1c" if v < -0.05 else "#a16207"
                up = f'<span style="color:{col}">{v * 100:+.0f}%</span>'
            filas.append(f'<tr><td class="ok">✓ {html.escape(et)}</td><td class="n">{peso * 100:.0f}%</td><td class="n ok">{_money(pm)}</td><td class="n">{up}</td><td></td></tr>')
        else:
            filas.append(f'<tr><td class="no">✗ {html.escape(et)}</td><td class="n no">{peso * 100:.0f}%</td><td class="n no">—</td><td class="n"></td>'
                         f'<td class="no"><i>{html.escape(_motivo_metodo_faltante(row, m))}</i></td></tr>')
    cab = '<tr><th>Método</th><th class="n">Peso</th><th class="n">Precio que resulta</th><th class="n">Contra el precio</th><th>Motivo si no se usó</th></tr>'
    nota_moneda = row.get("moneda_nota")
    moneda = f'<div class="fch-nota">Moneda: {html.escape(nota_moneda)}</div>' if isinstance(nota_moneda, str) and nota_moneda.strip() else ""
    resumen = (f'<div class="rev-r"><b>{ok} de {len(esperados)} métodos</b> entraron al Fair Value. Cuando uno no se puede usar, su peso se reparte entre los otros. '
               'El PEG es solo informativo: no entra al puntaje ni al promedio.</div>')
    return _tile("s12", "Revisión de los métodos del Fair Value", f'<table class="rev">{cab}{"".join(filas)}</table>{resumen}{moneda}', ac="#94a3b8")


def ficha_html(row, cedears=None, ficha=None, mercado_codigo=None):
    """Todos los mosaicos de la pagina de la empresa. `row` es el dict de la fila; `cedears` el resultado de data.cedears.cargar() (con el precio en
    pesos si se pudo); `ficha` los datos de Yahoo de la empresa (data/fichas.json); `mercado_codigo` el codigo del mercado pedido a Yahoo en el momento."""
    datos = cedears if cedears is not None else _cedears.cargar()
    mercado, adr = _fichas.mercado_y_adr(row.get("ticker"), ficha, mercado_codigo)
    mosaicos = [_encabezado(row, mercado, ficha), _tile_resumen(row, ficha, mercado), _tile_score(row), _tile_valoracion(row), _tile_cedear(row, datos),
                _tile_estadisticas(row, ficha), _tile_52s(row), _tile_dy(row), _tile_detalle(row), linea_precios_html(row), _tile_revision(row)]
    return '<div class="fch">' + "".join(m for m in mosaicos if m) + "</div>"
