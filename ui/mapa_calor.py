"""Mapa de calor (v1.5.29, pedido de Guille): empresas o ETFs como recuadros, agrupados por sector (o categoría), con el color de la variación del día.

- Tamaño del recuadro: capitalización bursátil (empresas) o patrimonio AUM (ETFs), suavizada (potencia 0,6) para que las más chicas también se vean.
- Color: variación de hoy contra el cierre anterior. Rojo = baja, verde = suba, gris = sin cambios o sin dato (nunca se inventa un dato).
- Sin librerías de gráficos: el acomodo (squarified treemap) se calcula acá y se dibuja con HTML + CSS puro (recuadros con posición en %), igual de rápido que el resto de la app.
Es información de mercado, no una recomendación.
"""
import html
from urllib.parse import quote

POTENCIA = 0.6           # suaviza la diferencia de tamaño entre las más grandes y las más chicas
TOPE_COLOR = 3.0         # a partir de ±3 % el color ya no cambia
SIN_DATO = "#4b5263"
# (variación %, color): igual que los mapas de calor más usados (rojo - gris - verde)
_ESCALA = [(-3.0, (246, 53, 56)), (-2.0, (191, 64, 69)), (-1.0, (139, 68, 78)), (0.0, (65, 69, 84)),
           (1.0, (53, 118, 78)), (2.0, (47, 158, 79)), (3.0, (48, 204, 90))]


def color_var(v):
    """Color de fondo de un recuadro según la variación del día (en %). None -> gris de «sin dato»."""
    if v is None or v != v:
        return SIN_DATO
    v = max(-TOPE_COLOR, min(TOPE_COLOR, float(v)))
    for (a, ca), (b, cb) in zip(_ESCALA, _ESCALA[1:]):
        if a <= v <= b:
            t = (v - a) / (b - a)
            r, g, bl = (round(ca[i] + (cb[i] - ca[i]) * t) for i in range(3))
            return f"#{r:02x}{g:02x}{bl:02x}"
    return SIN_DATO


def _peor(fila, lado):
    """Peor relación de aspecto de una fila de áreas pegadas al lado más corto (algoritmo squarified, Bruls et al.)."""
    s = sum(fila)
    if s <= 0:
        return float("inf")
    return max(max(lado * lado * a / (s * s), s * s / (lado * lado * a)) for a in fila if a > 0)


def squarify(valores, x, y, w, h):
    """Acomoda `valores` (en el orden dado, de mayor a menor) dentro del rectángulo x,y,w,h. Devuelve una lista de (x, y, w, h), una por valor."""
    n = len(valores)
    if n == 0:
        return []
    tot = float(sum(valores))
    if tot <= 0 or w <= 0 or h <= 0:
        return [(x, y, 0.0, 0.0)] * n
    areas = [v * w * h / tot for v in valores]
    out = []
    i = 0
    while i < n:
        lado = min(w, h)
        fila = [areas[i]]
        j = i + 1
        while j < n and _peor(fila + [areas[j]], lado) <= _peor(fila, lado):
            fila.append(areas[j])
            j += 1
        s = sum(fila)
        if w >= h:                        # fila vertical pegada a la izquierda
            ancho = s / h if h else 0
            yy = y
            for a in fila:
                alto = a / ancho if ancho else 0
                out.append((x, yy, ancho, alto))
                yy += alto
            x += ancho
            w -= ancho
        else:                             # fila horizontal pegada arriba
            alto = s / w if w else 0
            xx = x
            for a in fila:
                ancho = a / alto if alto else 0
                out.append((xx, y, ancho, alto))
                xx += ancho
            y += alto
            h -= alto
        i = j
    return out


def _peso(tam):
    try:
        t = float(tam)
    except (TypeError, ValueError):
        return 0.0
    return t ** POTENCIA if t > 0 else 0.0


def armar_grupos(items):
    """items: [{'tk','nombre','grupo','tam','var','precio','href'}] -> [(grupo, [items ordenados por tamaño], peso_total)] de mayor a menor. Se descartan los que no tienen tamaño."""
    g = {}
    for it in items:
        p = _peso(it.get("tam"))
        if p <= 0:
            continue
        it = dict(it, _p=p)
        g.setdefault(it.get("grupo") or "Otros", []).append(it)
    res = []
    for nombre, lst in g.items():
        lst.sort(key=lambda z: -z["_p"])
        res.append((nombre, lst, sum(z["_p"] for z in lst)))
    res.sort(key=lambda z: -z[2])
    return res


def _fmt_var(v):
    if v is None or v != v:
        return "s/d"
    if abs(v) < 0.05:
        return "0,0%"
    return f"{v:+.1f}%".replace(".", ",")


def _fmt_precio(p):
    try:
        p = float(p)
    except (TypeError, ValueError):
        return ""
    return "US$ " + (f"{p:,.1f}" if p >= 1000 else f"{p:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")


def _var_grupo(lst):
    """Variación del grupo: promedio de las variaciones ponderado por tamaño (solo los que tienen dato). None si ninguno trae dato."""
    num = den = 0.0
    for z in lst:
        v = z.get("var")
        if v is not None and v == v:
            num += v * z["_p"]
            den += z["_p"]
    return num / den if den else None


def _layout(grupos, ancho, alto, banda, px_min):
    """Dos niveles: primero los grupos (sectores) y adentro sus recuadros. Devuelve las piezas HTML de un mapa de `ancho` x `alto` unidades.
    `banda`: alto (en unidades) del rótulo de cada sector. `px_min`: tamaño mínimo de letra (en unidades) para escribir algo en un recuadro."""
    cajas = squarify([g[2] for g in grupos], 0, 0, ancho, alto)
    partes = []
    for (nombre, lst, _), (gx, gy, gw, gh) in zip(grupos, cajas):
        if gw <= 0 or gh <= 0:
            continue
        pct = lambda a, tot: f"{a / tot * 100:.3f}%"      # noqa: E731
        gv = _var_grupo(lst)
        rot = banda if (gh > banda * 2.2 and gw > banda * 4) else 0
        etiqueta = ""
        if rot:
            etiqueta = (f'<div class="mpc-gl" style="height:{pct(rot, gh)};font-size:{min(banda * 0.62, gw / max(len(nombre), 6) * 1.25):.3f}cqw">'
                        f'{html.escape(nombre)}</div>')
        hijos = squarify([z["_p"] for z in lst], 0, 0, gw, gh - rot)
        tiles = []
        for z, (tx, ty, tw, th) in zip(lst, hijos):
            if tw <= 0 or th <= 0:
                continue
            tk = str(z.get("tk") or "")
            fs = min(tw / (max(len(tk), 3) * 0.64), th / 2.5, banda * 1.6)
            txt = ""
            if fs >= px_min:
                v2 = f'<span class="mpc-v" style="font-size:{fs * 0.78:.3f}cqw">{_fmt_var(z.get("var"))}</span>' if th >= fs * 2.35 else ""
                txt = f'<span class="mpc-k" style="font-size:{fs:.3f}cqw">{html.escape(tk)}</span>{v2}'
            tip = " · ".join(x for x in (str(z.get("nombre") or tk), _fmt_precio(z.get("precio")), _fmt_var(z.get("var"))) if x)
            tiles.append(f'<a class="mpc-t" href="{html.escape(z.get("href") or "#", quote=True)}" target="_self" title="{html.escape(tip, quote=True)}" '
                         f'style="left:{pct(tx, gw)};top:{pct(ty, gh - rot)};width:{pct(tw, gw)};height:{pct(th, gh - rot)};background:{color_var(z.get("var"))}">{txt}</a>')
        cuerpo = f'<div class="mpc-gb" style="top:{pct(rot, gh)}">{"".join(tiles)}</div>' if rot else f'<div class="mpc-gb" style="top:0">{"".join(tiles)}</div>'
        partes.append(f'<div class="mpc-g" title="{html.escape(nombre, quote=True)}: {_fmt_var(gv)}" style="left:{pct(gx, ancho)};top:{pct(gy, alto)};width:{pct(gw, ancho)};height:{pct(gh, alto)}">'
                      f'{etiqueta}{cuerpo}</div>')
    return "".join(partes)


CSS = """
.mpc-w{max-width:1120px;margin:-84px auto 0;position:relative;font-family:'Roboto Condensed','Roboto',Arial,sans-serif}
.mpc-tit{display:flex;flex-wrap:wrap;align-items:center;gap:14px;margin:4px 0 10px}
.mpc-tit h2{margin:0;font-size:1.5rem;color:#0f172a;font-weight:800}
.mpc-sw{display:inline-flex;border:1px solid #c3ccd8;border-radius:9px;overflow:hidden;background:#fff}
.mpc-sw a{padding:7px 20px;font-size:14.5px;font-weight:700;color:#374151!important;text-decoration:none!important;background:#fff}
.mpc-sw a.on{background:#15803d;color:#fff!important}
.mpc-leyenda{display:flex;align-items:center;gap:8px;margin-left:auto;font-size:12.5px;color:#475569}
.mpc-esc{display:flex;border-radius:4px;overflow:hidden}
.mpc-esc span{display:block;width:34px;height:14px}
.mpc-nota{font-size:12.5px;color:#64748b;margin:8px 0 0;line-height:1.5;text-align:justify}
.mpc-caja{position:relative;width:100%;max-width:1120px;margin:0 auto;container-type:inline-size;background:#1f2330;border-radius:10px;overflow:hidden}
.mpc-mapa{position:relative;width:100%}
.mpc-d{aspect-ratio:100/48;display:block}
.mpc-m{aspect-ratio:100/150;display:none}
.mpc-g{position:absolute;box-sizing:border-box;border:1.5px solid #1f2330;background:#2a2f3e;overflow:hidden}
.mpc-gl{position:absolute;left:0;right:0;top:0;box-sizing:border-box;padding:0 5px;color:#e5e7eb;font-weight:700;text-transform:uppercase;letter-spacing:.3px;line-height:1;
 display:flex;align-items:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:#2a2f3e}
.mpc-gb{position:absolute;left:0;right:0;bottom:0}
.mpc-t{position:absolute;box-sizing:border-box;border:1px solid #1f2330;color:#fff!important;text-decoration:none!important;display:flex;flex-direction:column;align-items:center;justify-content:center;
 text-align:center;overflow:hidden;line-height:1.1}
.mpc-t span{color:#fff!important;text-shadow:0 0 2px rgba(0,0,0,.35)}
.mpc-t:hover{outline:2px solid #fff;outline-offset:-2px;z-index:5;filter:brightness(1.12)}
.mpc-k{font-weight:800}
.mpc-v{font-weight:500;opacity:.95}
@media (max-width:900px){.mpc-w{margin-top:-40px}.mpc-d{display:none}.mpc-m{display:block}.mpc-leyenda{margin-left:0}.mpc-w{padding:0 2px}}
"""


def mapa_html(items, titulo, activo, hay_var=True, texto_precios=None, nota_tam=""):
    """La pantalla completa: título, interruptor Empresas | ETFs, leyenda de colores, el mapa (versión de compu y versión de celular) y una nota al pie."""
    grupos = armar_grupos(items)
    sw = "".join(f'<a href="?pagina=mapa&tipo={k}" target="_self"{" class=on" if k == activo else ""}>{t}</a>' for k, t in (("empresas", "Empresas"), ("etfs", "ETFs")))
    esc = "".join(f'<span style="background:{color_var(v)}"></span>' for v in (-3, -2, -1, 0, 1, 2, 3))
    leyenda = f'<div class="mpc-leyenda"><span>−3%</span><div class="mpc-esc">{esc}</div><span>+3%</span></div>'
    if not grupos:
        cuerpo = '<div class="mpc-nota" style="text-align:center;padding:40px 0">Todavía no hay datos para armar el mapa.</div>'
    else:
        d = _layout(grupos, 100.0, 48.0, 1.8, 0.75)
        m = _layout(grupos, 100.0, 150.0, 3.6, 2.3)
        cuerpo = f'<div class="mpc-caja"><div class="mpc-mapa mpc-d">{d}</div><div class="mpc-mapa mpc-m">{m}</div></div>'
    aviso = ""
    if not hay_var:
        aviso = ('<p class="mpc-nota" style="color:#b45309">Por ahora no pudimos traer la variación de hoy: los recuadros se ven en gris. '
                 'Se actualiza sola en la próxima carga.</p>')
    hora = f" Datos al {texto_precios}." if texto_precios else ""
    nota = (f'<p class="mpc-nota">Cada recuadro es una {"empresa" if activo == "empresas" else "ETF"}; el color muestra cuánto subió o bajó hoy respecto del cierre anterior '
            f'(rojo = baja, verde = suba, gris = sin cambios o sin dato). {nota_tam}{hora} Tocá un recuadro para abrir su ficha. '
            f'Es información de mercado, no una recomendación.</p>')
    return f'<div class="mpc-w"><div class="mpc-tit"><h2>{html.escape(titulo)}</h2><div class="mpc-sw">{sw}</div>{leyenda}</div>{aviso}{cuerpo}{nota}</div>'


def items_empresas(df):
    """Recuadros de las empresas: tamaño = capitalización; grupo = sector; variación = columna var_dia (precios de hoy)."""
    out = []
    if df is None or len(df) == 0:
        return out
    for _, r in df.iterrows():
        tk = str(r.get("ticker") or "")
        if not tk:
            continue
        v = r.get("var_dia") if "var_dia" in df.columns else None
        try:
            v = None if v is None or v != v else float(v)
        except (TypeError, ValueError):
            v = None
        out.append({"tk": tk, "nombre": r.get("nombre") or tk, "grupo": r.get("sector") or "Otros", "tam": r.get("market_cap"),
                    "var": v, "precio": r.get("precio_actual"), "href": f"?empresa={quote(tk, safe='')}"})
    return out


def items_etfs(etfs, datos, precios, variaciones):
    """Recuadros de los ETFs: tamaño = AUM (patrimonio); grupo = categoría; variación = la del día que trae Yahoo."""
    out = []
    for e in etfs or []:
        tk = e["ticker"]
        d = (datos or {}).get(tk) or {}
        aum = d.get("aum")
        v = (variaciones or {}).get(tk)
        out.append({"tk": tk, "nombre": e.get("nombre") or tk, "grupo": e.get("categoria") or "Otros", "tam": aum, "var": v,
                    "precio": (precios or {}).get(tk) or d.get("precio"), "href": f"?etf={quote(tk, safe='')}"})
    return out
