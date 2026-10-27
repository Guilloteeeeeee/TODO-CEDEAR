"""ETFs (v1.2.64): la tabla de la pantalla de ETFs y la pagina de cada ETF (?etf=TICKER), con el mismo estilo que las de empresas.
Todo es informacion educativa, no una recomendacion. Los datos salen de data/etfs.csv (los arma Guille), de Yahoo (en vivo o del archivo
data/etfs_yahoo.json) y del precio de hoy; lo que no hay se muestra como "—" (nunca se inventa)."""
import datetime as _dt
import html
from urllib.parse import quote, quote_plus

from ui import etf_iconos as _ic
from ui import ficha as F
from ui.banderas import bandera_html
from ui.tabla_visual import _money, _n, barra_52s_html

INTRO = ("Un ETF es una canasta de activos (acciones, bonos o materias primas) que se compra como si fuera una sola acción. "
         "Es información educativa, no una recomendación.")        # v1.2.67: ya no es un texto fijo: sale al pasar el mouse por el título "ETF"

INTROS = {
    "resumen": "Qué es el ETF, cuánto cuesta (comisión), si paga dividendos o los reinvierte, y dónde cotiza, con el link a su sitio oficial.",
    "composicion": "Qué tiene adentro el ETF: sus principales tenencias y cómo se reparte por sector, por tipo de activo y por país.",
    "grafico": "Cómo se movió el precio del ETF, cuánto rindió en distintos plazos y qué dicen los indicadores técnicos (rango de 52 semanas, promedios móviles, RSI, MACD y riesgo). Es información sobre el pasado del precio, no una señal de compra o venta.",
    "noticias": "Los últimos titulares sobre el ETF, en su idioma original, con link a cada nota.",
}

TIPS = {
    "ETF": INTRO,
    "Precio": "Precio de una unidad del ETF en dólares, en su mercado de origen (no en tiempo real).",
    "Descripción": "Qué replica o en qué invierte el ETF.",
    "Categoría": "Grupo al que pertenece (Solo USA, Internacionales, Sectoriales, Commodities...).",
    "Gestor": "Empresa que administra el ETF (la que lo crea y lo mantiene).",
    "AUM": "Activos bajo gestión: cuánto dinero tiene invertido el ETF en total. Más grande suele significar más liquidez y más permanencia en el tiempo. B = mil millones, M = millón.",
    "Comisión": "Lo que cobra el ETF por año, como porcentaje de lo invertido (expense ratio). Ya está descontada del precio; no se paga aparte.",
}

# Sitio de cada gestor (pagina de ETFs). Solo se usa cuando el ETF no tiene su link propio en la columna "web" de data/etfs.csv.
GESTORES_WEB = {
    "State Street (SPDR)": "https://www.ssga.com/us/en/intermediary/etfs",
    "BlackRock (iShares)": "https://www.ishares.com/us",
    "Invesco": "https://www.invesco.com/us/financial-products/etfs",
    "Vanguard": "https://investor.vanguard.com/investment-products/etfs",
    "VanEck": "https://www.vaneck.com/us/en/",
    "Global X": "https://www.globalxetfs.com/",
    "ARK Invest": "https://ark-funds.com/",
    "First Trust": "https://www.ftportfolios.com/",
    "Charles Schwab": "https://www.schwabassetmanagement.com/",
    "United States Commodity Funds (USCF)": "https://www.uscfinvestments.com/",
    "Teucrium": "https://teucrium.com/",
    "J.P. Morgan Asset Management": "https://am.jpmorgan.com/us/en/asset-management/adv/products/etfs/",
    "World Gold Trust Services (SPDR)": "https://www.spdrgoldshares.com/",
}

CSS = """
.etf{max-width:1280px;margin:6px auto 0}
.etf-n{font-size:13px;color:#6b7280;margin:2px 2px 8px}
.etf-t{background:#fff;border-radius:0 0 14px 14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 8px 22px rgba(15,23,42,.07);overflow:hidden}
.etf-r{display:grid;grid-template-columns:minmax(0,2.3fr) minmax(0,1fr) minmax(0,3.2fr) minmax(0,1.4fr) minmax(0,1.5fr) minmax(0,1fr) minmax(0,1fr);align-items:stretch;border-top:1px solid #f0f2f5}
.etf-r:first-child{border-top:0}
.etf-r>div{padding:8px 12px;min-width:0;display:flex;flex-direction:column;justify-content:center}
.etf-r:nth-child(even){background:#f3f6f9}
.etf-r:hover>div{background:#f8fafc}
.etf-r>.ctr{align-items:center;text-align:center}
.etf-nm{font-size:14.5px;font-weight:700;line-height:1.3}
.etf-nm a{color:#111827;text-decoration:underline;text-decoration-color:rgba(75,85,99,.4);text-decoration-thickness:1px;text-underline-offset:2px}
.etf-nm a:hover{color:#1d4ed8;text-decoration-color:#1d4ed8}
.etf-tk{font-size:12.5px;font-weight:600;color:#4b5563;margin-top:1px;letter-spacing:.3px}
.etf-d{font-size:13.5px;color:#1f2937;line-height:1.45}
.etf-c,.etf-g{font-size:13.5px;color:#374151}
.etf-pr{font-size:14.5px;font-weight:700;color:#111827;white-space:nowrap}
.etf-v{font-size:14px;color:#111827;white-space:nowrap}
.etf-nd{color:#9ca3af;font-weight:500}
.etf-tg{display:inline-block;font-size:11.5px;font-weight:700;border-radius:10px;padding:1px 8px;margin:3px 4px 0 0;white-space:nowrap;width:fit-content}
.etf-nv{background:#dcfce7;color:#166534}
.etf-bk{background:#fef3c7;color:#92400e}
.etf-et{background:#eef1f4;color:#4b5563;font-weight:600}
.etf-vacio{padding:26px;text-align:center;color:#6b7280}
.etf-lab{display:none}
div[data-testid="stElementContainer"]:has(.etf-t){margin-top:-1rem}
@media (max-width:900px){
div[data-testid="stHorizontalBlock"]:has(.st-key-tvh_e_nombre){display:none!important}
.st-key-orden_movil_caja{display:block}
div[data-testid="stElementContainer"]:has(.etf-t){margin-top:0!important}
.etf-t{border-radius:14px}
.etf-r{grid-template-columns:1fr 1fr;gap:4px 14px;padding:10px 8px}
.etf-r>div{padding:3px 6px}
.etf-r>div:nth-child(1),.etf-r>div:nth-child(3){grid-column:1 / -1}
.etf-r>.ctr{align-items:flex-start;text-align:left}
.etf-lab{display:block;font-size:11.5px;color:#9ca3af;font-weight:600}
}
/* v1.2.67: caja de arriba de la tabla (leyenda + Excel), igual que la de Empresas */
.st-key-fila_excel{display:flex!important;flex-direction:row!important;flex-wrap:wrap;align-items:flex-start!important;justify-content:space-between;gap:4px 14px!important;margin:0 0 2px!important}
.st-key-fila_excel [data-testid="stMarkdownContainer"]{margin-bottom:0!important}
.st-key-fila_excel>div{width:auto!important;flex:0 0 auto;min-width:0}
/* pagina de cada ETF */
.etf-ico{width:72px;height:72px;border-radius:16px;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:42px;line-height:1;flex:none;overflow:hidden}
.etf-ico svg{width:72px;height:72px;display:block}
.etf-pill{display:inline-block;font-size:12px;font-weight:700;border-radius:10px;padding:2px 9px;background:#eef1f4;color:#4b5563}
.etf-hold{display:grid;grid-template-columns:minmax(0,1fr) 62px;gap:4px 10px;align-items:center;font-size:13.5px}
.etf-hold .bar{height:7px;background:#eef1f4;border-radius:4px;overflow:hidden;grid-column:1 / -1;margin:-2px 0 6px}
.etf-hold .bar i{display:block;height:100%;background:#0ea5e9;border-radius:4px}
.etf-hold .nm{color:#1f2937;min-width:0;overflow-wrap:anywhere}.etf-hold .nm b{color:#111827}
.etf-hold .pc{text-align:right;font-weight:700;color:#111827}
.etf-torta{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
.etf-torta .pie{width:190px;height:190px;border-radius:50%;flex:none;box-shadow:0 0 0 3px #fff,0 1px 6px rgba(15,23,42,.18)}
.etf-torta .lgs{flex:1 1 220px;min-width:0;display:grid;gap:6px}
.etf-torta .lg{display:grid;grid-template-columns:14px minmax(0,1fr) auto;gap:9px;align-items:center;font-size:13.5px}
.etf-torta .lg i{width:14px;height:14px;border-radius:4px;display:block}
.etf-torta .lg .pc{font-weight:700;color:#111827}
.etf-nota{font-size:12.5px;color:#6b7280;line-height:1.45;margin-top:10px}
.etf-2c{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media (max-width:760px){.etf-2c{grid-template-columns:1fr}}
"""


# --- numeros ---------------------------------------------------------------------------------------------------------------

def _usd(v):
    """US$ 580.1 (un decimal, punto) o '—'."""
    return _money(v) if _n(v) else "—"


def aum_texto(v):
    return F._usd_abrev(v) if _n(v) and _n(v) > 0 else "—"


def comision_texto(v):
    x = _n(v)
    if x is None:
        return "—"
    return f"{x:.2f}%" if x >= 0.1 else f"{x:.3f}%"


def _pct(v, dec=2):
    x = _n(v)
    return f"{x:.{dec}f}%" if x is not None else "—"


def _fecha(f):
    return f.strftime("%d/%m/%Y") if isinstance(f, (_dt.date, _dt.datetime)) else "—"


def dominio(url):
    u = str(url or "").replace("https://", "").replace("http://", "").replace("www.", "")
    return u.split("/")[0]


# --- iconos ---------------------------------------------------------------------------------------------------------------

_SVG = {
    "bitcoin": ('<svg viewBox="0 0 64 64" role="img" aria-label="Bitcoin"><circle cx="32" cy="32" r="32" fill="#f7931a"/>'
                '<g transform="rotate(14 32 32)" fill="#fff"><text x="32" y="45" font-size="38" font-weight="800" text-anchor="middle" font-family="Arial,Helvetica,sans-serif">B</text>'
                '<rect x="26.5" y="13" width="3.2" height="8"/><rect x="34" y="13" width="3.2" height="8"/><rect x="26.5" y="43" width="3.2" height="8"/><rect x="34" y="43" width="3.2" height="8"/></g></svg>'),
    "ethereum": ('<svg viewBox="0 0 64 64" role="img" aria-label="Ethereum"><circle cx="32" cy="32" r="32" fill="#627eea"/>'
                 '<g fill="#fff"><polygon points="32,10 18,32.5 32,26.5" fill-opacity=".6"/><polygon points="32,10 46,32.5 32,26.5"/>'
                 '<polygon points="32,28.5 18,34.5 32,54" fill-opacity=".6"/><polygon points="32,28.5 46,34.5 32,54"/><polygon points="18,32.5 32,26.5 46,32.5 32,38" fill-opacity=".35"/></g></svg>'),
}


def icono_html(e):
    """Lo que representa el ETF: un dibujo propio (ui/etf_iconos.py: bandera, globo, lingotes...) o, si falta, las iniciales del ticker. Los emojis de
    versiones anteriores se siguen mostrando si alguien los deja en la columna `icono`."""
    ic = str(e.get("icono") or "").strip()
    if ic.startswith("svg:"):
        dib = _SVG.get(ic[4:]) or _ic.icono(ic[4:])
        if dib:
            return f'<div class="etf-ico">{dib}</div>'
    elif ic:
        return f'<div class="etf-ico">{html.escape(ic)}</div>'
    return f'<div class="etf-ico" style="font-size:24px;font-weight:800;color:#475569">{html.escape(e["ticker"][:3])}</div>'


# --- tabla -------------------------------------------------------------------------------------------------------------

COLUMNAS = [("nombre", "ETF", 2.3), ("precio", "Precio", 1.0), ("descripcion", "Descripción", 3.2), ("categoria", "Categoría", 1.4),
            ("gestor", "Gestor", 1.5), ("aum", "AUM", 1.0), ("comision", "Comisión", 1.0)]
TEXTO = ("nombre", "descripcion", "categoria", "gestor")        # al tocar el título por primera vez: de la A a la Z (el resto, de mayor a menor)


def _fila(e, d, precio):
    tk = e["ticker"]
    nombre = html.escape(e.get("nombre") or tk)
    tags = ""
    if e.get("etiqueta"):
        tags += f'<span class="etf-tg etf-et">{html.escape(e["etiqueta"])}</span>'
    if e.get("acceso") and e["acceso"].strip().lower() != "cedear":
        tags += (f'<span class="etf-tg etf-bk" title="No tiene CEDEAR: no se puede comprar desde pesos en el mercado local; hay que pedirlo a la mesa del broker.">'
                 f'{html.escape(e["acceso"])}</span>')
    nd = '<span class="etf-nd">—</span>'
    p = _usd(precio) if _n(precio) else nd
    g = html.escape(e.get("gestor") or (d or {}).get("gestor") or "") or nd
    lab = lambda t: f'<span class="etf-lab">{t}</span>'   # noqa: E731
    return (f'<div class="etf-r"><div><div class="etf-nm"><a href="?etf={quote(tk, safe="")}" target="_self">{nombre}</a></div>'
            f'<div class="etf-tk">{html.escape(tk)}</div>{tags}</div>'
            f'<div class="etf-pr ctr">{lab("Precio")}{p}</div>'
            f'<div class="etf-d">{html.escape(e.get("descripcion") or "")}</div>'
            f'<div class="etf-c ctr">{lab("Categoría")}{html.escape(e.get("categoria") or "")}</div>'
            f'<div class="etf-g ctr">{lab("Gestor")}{g}</div>'
            f'<div class="etf-v ctr">{lab("AUM")}{aum_texto((d or {}).get("aum"))}</div>'
            f'<div class="etf-v ctr">{lab("Comisión")}{comision_texto((d or {}).get("comision"))}</div></div>')


def tabla_html(etfs, datos=None, precios=None):
    """Las filas de la tabla (los títulos son botones de Streamlit, ver app.render_tabla_etfs, para que se pueda ordenar)."""
    datos, precios = datos or {}, precios or {}
    if not etfs:
        return '<div class="etf"><div class="etf-t"><div class="etf-vacio">No hay ETFs que coincidan con el filtro.</div></div></div>'
    filas = "".join(_fila(e, datos.get(e["ticker"]), precios.get(e["ticker"]) or (datos.get(e["ticker"]) or {}).get("precio")) for e in etfs)
    return f'<div class="etf"><div class="etf-t">{filas}</div></div>'


def valor_orden(e, d, precio, col):
    """Valor por el que se ordena el ETF en la columna `col` (texto sin tildes ni mayúsculas, o número); None si no hay dato."""
    from data.etfs import norm
    d = d or {}
    if col == "nombre":
        return norm(e.get("nombre") or e["ticker"])
    if col == "descripcion":
        return norm(e.get("descripcion")) or None
    if col == "categoria":
        return norm(e.get("categoria")) or None
    if col == "gestor":
        return norm(e.get("gestor") or d.get("gestor")) or None
    if col == "precio":
        return _n(precio) or _n(d.get("precio"))
    if col == "aum":
        return _n(d.get("aum"))
    if col == "comision":
        return _n(d.get("comision"))
    return None


def ordenar(etfs, datos, precios, col, asc):
    """ETFs ordenados por `col` (los que no tienen el dato quedan siempre al final). Sin columna: el orden del archivo."""
    if not col or col not in {c for c, _, _ in COLUMNAS}:
        return list(etfs)
    datos, precios = datos or {}, precios or {}
    con, sin = [], []
    for e in etfs:
        v = valor_orden(e, datos.get(e["ticker"]), precios.get(e["ticker"]), col)
        (sin if v is None else con).append((v, e))
    con.sort(key=lambda x: x[0], reverse=not asc)
    return [e for _, e in con] + [e for _, e in sin]


def opciones_orden():
    """Opciones del selector "Ordenar por" del celular: (texto, columna, ascendente)."""
    o = []
    for col, titulo, _ in COLUMNAS:
        if col in TEXTO:
            o += [(f"{titulo}: de la A a la Z", col, True), (f"{titulo}: de la Z a la A", col, False)]
        elif col == "comision":
            o += [(f"{titulo}: de menor a mayor", col, True), (f"{titulo}: de mayor a menor", col, False)]
        else:
            o += [(f"{titulo}: de mayor a menor", col, False), (f"{titulo}: de menor a mayor", col, True)]
    return o


def css_cabecera(sort_col=None, asc=True):
    """Estilo de la fila de títulos (botones con la clave 'tvh_e_<columna>', los mismos botones grises de la tabla de Empresas, centrados y con flechitas)."""
    from ui import tabla_visual as TV
    base = 'div[data-testid="stHorizontalBlock"]:has(.st-key-tvh_e_nombre)'
    return (TV.css_encabezado(f"e_{sort_col}" if sort_col else None, 0, None, asc)
            + f'{base}{{gap:0!important;background:{TV._BARRA};border:1px solid {TV._BARRA};border-radius:14px 14px 0 0;align-items:stretch!important}}'
            f'{base} [data-testid="stColumn"]{{min-width:0!important;padding:0!important}}'
            f'{base} [data-testid="stElementContainer"]{{width:100%}}'
            f'{base} [data-testid="stColumn"] [data-testid="stVerticalBlock"]{{gap:0!important}}')


def encabezado_html(total, mostrados):
    n = (f"{total} ETFs" if mostrados == total else f"{mostrados} de {total} ETFs")
    return f'<div class="etf"><div class="etf-n">{n}</div></div>'


# --- pagina del ETF ---------------------------------------------------------------------------------------------------------

def tipo_distribucion(e, d):
    """('Distribución' | 'Acumulación' | 'Sin dividendos' | None, explicacion). Primero lo que puso Guille en el CSV; si no, se deduce de los pagos de Yahoo."""
    e = e or {}
    d = d or {}
    c = str(e.get("distribucion") or "").strip().lower()
    if c.startswith("acum"):
        return "Acumulación", "El ETF reinvierte dentro del fondo los dividendos que cobra: no te paga nada en efectivo y el valor del ETF los incluye."
    if c.startswith("distr"):
        return "Distribución", "El ETF te paga en efectivo los dividendos que cobra de las empresas o bonos que tiene."
    div = d.get("dividendos") or {}
    if div.get("pagos_12m"):
        return "Distribución", "El ETF te paga en efectivo los dividendos que cobra de las empresas o bonos que tiene."
    if d and ("nombre" in d or "precio" in d):
        return "Sin dividendos", "En el último año no pagó dividendos: su rendimiento viene solo de la variación del precio (los activos que tiene, como el oro o el bitcoin, no generan rentas)."
    return None, ""


def _links_etf(e, d):
    """Sitio oficial primero. Si no hay link propio del ETF (columna "web"), se usa la pagina del gestor y una busqueda de su ficha oficial."""
    tk, nombre = e["ticker"], e.get("nombre") or e["ticker"]
    enl = []
    web = str(e.get("web") or "").strip()
    gestor_web = GESTORES_WEB.get(e.get("gestor") or "", "")
    if web:
        enl.append((web, f"Sitio oficial del ETF · {dominio(web)}", "Página oficial del ETF en el sitio de su gestor."))
    elif gestor_web:
        enl.append((gestor_web, f"Sitio del gestor · {dominio(gestor_web)}", "Sitio oficial de la empresa que administra el ETF."))
    dom = dominio(web or gestor_web)
    q = quote_plus(f'"{nombre}" {tk}' + (f" site:{dom}" if dom else " ETF"))
    enl.append((f"https://www.google.com/search?q={q}", "Ficha oficial del ETF",
                "Busca en Google la ficha oficial del ETF en el sitio del gestor (composición, NAV, documentos, comisión)."))
    sim = e.get("yahoo") or tk
    enl.append((f"https://finance.yahoo.com/quote/{quote(sim, safe='')}/", "Yahoo Finance", "Cotización y datos del ETF en Yahoo Finance."))
    return '<div class="fch-links">' + "".join(
        f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer" title="{html.escape(t, quote=True)}">{html.escape(n)} ↗</a>' for u, n, t in enl) + "</div>"


COLORES = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569", "#0d9488", "#a16207"]


def _barras(items, vacio):
    """Barras horizontales, cada una de un color distinto (v1.2.67)."""
    if not items:
        return f'<div class="fch-sub" style="margin:0">{html.escape(vacio)}</div>'
    tope = max(i["pct"] for i in items) or 1
    out = []
    for k, i in enumerate(items):
        nom = html.escape(i["nombre"] or "")
        if i.get("simbolo"):
            nom = f'<b>{html.escape(i["simbolo"])}</b> · {nom}' if nom else f'<b>{html.escape(i["simbolo"])}</b>'
        col = COLORES[k % len(COLORES)]
        out.append(f'<div class="nm">{nom}</div><div class="pc">{i["pct"]:.1f}%</div>'
                   f'<div class="bar"><i style="width:{max(2.0, i["pct"] / tope * 100):.0f}%;background:{col}"></i></div>')
    return '<div class="etf-hold">' + "".join(out) + "</div>"


def torta_html(items):
    """Gráfico de torta (círculo dividido en porciones, cada una de un color) con su lista al costado. items: [{'nombre', 'pct'}] (pct en %)."""
    items = [i for i in items if _n(i.get("pct")) and i["pct"] > 0]
    if not items:
        return ""
    tot = sum(i["pct"] for i in items)
    if tot < 99.5:
        items = items + [{"nombre": "Otros / sin clasificar", "pct": 100 - tot, "_gris": True}]
        tot = 100.0
    ini, tramos, filas = 0.0, [], []
    for k, i in enumerate(items):
        col = "#cbd5e1" if i.get("_gris") else COLORES[k % len(COLORES)]
        fin = ini + i["pct"] / tot * 100
        tramos.append(f"{col} {ini:.2f}% {fin:.2f}%")
        ini = fin
        bnd = bandera_html(i["nombre"], chica=True) if not i.get("_gris") else ""
        bnd = "" if bnd in ("—", html.escape(i["nombre"])) else bnd + " "
        filas.append(f'<div class="lg"><i style="background:{col}"></i><span class="nm">{bnd}{html.escape(i["nombre"])}</span><span class="pc">{i["pct"]:.1f}%</span></div>')
    return (f'<div class="etf-torta"><div class="pie" role="img" aria-label="Gráfico de torta por país" style="background:conic-gradient({", ".join(tramos)})"></div>'
            f'<div class="lgs">{"".join(filas)}</div></div>')


def encabezado_etf(e, d, precio, cedear):
    """La banda de arriba de la pagina del ETF: lo que representa (icono), nombre, mercado, ticker, categoria; a la derecha, el precio en dolares y el del CEDEAR."""
    d = d or {}
    tk = e["ticker"]
    mercado = e.get("mercado") or d.get("mercado") or ""
    tk_txt = f"{html.escape(mercado)}: {html.escape(tk)}" if mercado else html.escape(tk)
    cat = f'<span class="etf-pill">{html.escape(e["categoria"])}</span>' if e.get("categoria") else ""
    p = _n(precio) or _n(d.get("precio"))
    pr = ""
    if p and p > 0:
        pr = f'<div class="pr"><div class="v">{_money(p)}</div><div class="ars">{cedear_linea(e, cedear)}</div></div>'
    return (f'<div class="fch"><div class="fch-t s12" style="--ac:#64748b"><div class="fch-hd"><div class="id">{icono_html(e)}<div>'
            f'<div class="nm">{html.escape(e.get("nombre") or d.get("nombre") or tk)}</div>'
            f'<div class="sb"><span class="tk">{tk_txt}</span>{cat}</div></div></div>{pr}</div></div></div>')


def cedear_linea(e, cedear):
    """'CEDEAR: $ 25.394 (Ratio 20:1)'. Sin ratio confirmado no se inventa nada; los que no tienen CEDEAR lo dicen."""
    acceso = str(e.get("acceso") or "").strip()
    if acceso and acceso.lower() != "cedear":
        return "Sin CEDEAR: solo por mesa del broker"
    ratio = (cedear or {}).get("ratio")
    if not ratio:
        return "CEDEAR: ratio pendiente de confirmar"
    from data import cedears as _c
    r = _c.ratio_texto(ratio).replace(" : ", ":")
    ars = _n((cedear or {}).get("precio_ars"))
    return f"CEDEAR: {F._ars(ars)} (Ratio {html.escape(r)})" if ars else f"CEDEAR: sin precio por ahora (Ratio {html.escape(r)})"


def descripcion_html(e, d):
    """Texto de "Qué es este ETF": la frase corta del CSV (si es una explicación y no solo el nombre) y la descripción que da Yahoo, traducida al
    castellano por bajar_etfs_yahoo.py (si no se pudo traducir se muestra en inglés, avisándolo)."""
    from data.etfs import norm
    d = d or {}
    corta = str(e.get("descripcion") or "").strip()
    nombre = str(e.get("nombre") or "").strip()
    if norm(corta) == norm(nombre):
        corta = ""
    out = f'<p class="fch-desc" style="margin:0 0 6px">{html.escape(corta)}</p>' if corta else ""
    largo = str(d.get("resumen_es") or "").strip()
    en = False
    if not largo and d.get("resumen_en"):
        largo, en = str(d["resumen_en"]).strip(), True
    if largo:
        out += f'<p class="fch-desc" style="margin:0 0 4px">{html.escape(largo)}</p>'
        out += ('<div class="etf-nota">Descripción de Yahoo Finance' + (" (en inglés: todavía no se tradujo)." if en else ", traducida al castellano.") + '</div>')
    return out


def tab_resumen(e, d, precio, cedear=None):
    d = d or {}
    tk = e["ticker"]
    desc = descripcion_html(e, d)
    if e.get("etiqueta"):
        desc += f'<div style="margin:4px 0 0"><span class="etf-tg etf-et">{html.escape(e["etiqueta"])}</span></div>'
    arriba = F._tile("s12", "Qué es este ETF", desc + _links_etf(e, d), ac="#0ea5e9")
    # --- datos del fondo ---
    k = F._fila_kv
    mercado = e.get("mercado") or d.get("mercado") or ""
    gestor = e.get("gestor") or d.get("gestor") or ""
    filas = [k("Nombre", html.escape(e.get("nombre") or d.get("nombre") or tk)),
             k("Ticker", html.escape(tk)),
             k("Gestor", html.escape(gestor) or "—", "Empresa que administra el ETF."),
             k("Mercado donde cotiza", html.escape(mercado) or "—", "Bolsa de valores donde se compra y vende el ETF."),
             k("Categoría", html.escape(e.get("categoria") or d.get("categoria_yahoo") or "—"))]
    if d.get("inicio"):
        filas.append(k("Inicio", _fecha(d["inicio"]), "Fecha en que el ETF empezó a cotizar. Cuanto más antiguo, más historia para evaluarlo."))
    acc = str(e.get("acceso") or "").strip()
    if acc:
        filas.append(k("Cómo se compra desde Argentina", "CEDEAR" if acc.lower() == "cedear" else html.escape(acc),
                       "CEDEAR: se compra en pesos en el mercado local. Mesa del broker: hay que pedirlo al broker, no tiene CEDEAR."))
    datos_h = F._tile("s6", "Datos del ETF", '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>", ac="#0ea5e9")
    # --- cifras ---
    p = _n(precio) or _n(d.get("precio"))
    nav = _n(d.get("nav"))
    c = [k("Precio", _usd(p), "Precio al que cotiza una unidad del ETF en el mercado.")]
    c.append(k("NAV (valor por unidad)", _usd(nav), "Net Asset Value: lo que valen realmente los activos que tiene el ETF, dividido por la cantidad de unidades emitidas. El precio de mercado suele estar muy cerca."))
    if p and nav and nav > 0:
        dif = (p / nav - 1) * 100
        c.append(k("Precio vs NAV", f"{dif:+.2f}%", "Si es positivo, el ETF cotiza con prima (más caro que sus activos); si es negativo, con descuento. En los ETFs grandes suele ser mínimo."))
    c.append(k("AUM (patrimonio)", aum_texto(d.get("aum")), "Activos bajo gestión: el dinero total que tiene invertido el ETF."))
    com = _n(d.get("comision"))
    c.append(k("Comisión anual", comision_texto(com), "Lo que cobra el ETF por año (expense ratio), como porcentaje de lo invertido. Ya está descontada del precio; no se paga aparte."))
    tipo, tipo_tip = tipo_distribucion(e, d)
    c.append(k("Dividendos", html.escape(tipo) if tipo else "—", tipo_tip or "Si el ETF paga los dividendos en efectivo (distribución) o los reinvierte (acumulación)."))
    div = d.get("dividendos") or {}
    if tipo == "Distribución":
        if _n(d.get("rendimiento")):
            c.append(k("Rendimiento por dividendo", _pct(d["rendimiento"]), "Dividendos pagados en el último año como porcentaje del precio actual."))
        if _n(d.get("dividendo_anual")) or _n(div.get("total_12m")):
            c.append(k("Dividendo anual por unidad", _usd(d.get("dividendo_anual") or div.get("total_12m")), "Suma de lo pagado en los últimos 12 meses por cada unidad del ETF."))
        if div.get("frecuencia"):
            c.append(k("Frecuencia de pago", html.escape(div["frecuencia"]), "Cada cuánto paga: mensual, trimestral, semestral o anual."))
        if div.get("ultimo") and div["ultimo"].get("fecha"):
            u = div["ultimo"]
            c.append(k("Último pago", f'{_usd(u.get("monto"))} · {_fecha(u["fecha"])}', "Monto por unidad y fecha del último dividendo."))
    lo, hi = _n(d.get("min_52s")), _n(d.get("max_52s"))
    if lo and hi and hi > lo:
        c.append(k("Rango de 52 semanas", f"{_money(lo)} – {_money(hi)}", "Del precio más bajo al más alto de los últimos 12 meses."))
    if _n(d.get("beta")):
        c.append(k("Beta (3 años)", f"{d['beta']:.2f}", "Cuánto se mueve el ETF respecto del mercado: 1 se mueve igual; más de 1, más que el mercado; menos de 1, menos."))
    cuerpo = '<div class="fch-kv" style="margin-top:0">' + "".join(c) + "</div>"
    cifras = F._tile("s6", "Cifras", cuerpo, ac="#0369a1")
    return F._env(arriba, datos_h, cifras)


# ETFs que no tienen empresas adentro (oro, plata, petroleo, materias primas, bitcoin, ether): no hay desglose por pais
SIN_PAISES = {"IBIT", "ETHA", "GLD", "SLV", "USO", "GSG", "CORN", "SOYB"}


def paises_de(e, d):
    """(lista [{'nombre','pct'}], nota). Primero el desglose que traiga el archivo de Yahoo (clave 'paises', si algún día se carga); si el índice es de un
    único país (columna `pais` del CSV), 100 % ese país por definición; si no, vacío (no se inventa nada)."""
    d = d or {}
    if d.get("paises"):
        return d["paises"], ""
    if e.get("pais"):
        return [{"nombre": e["pais"], "pct": 100.0}], "Por definición del índice: este ETF invierte solo en empresas de ese país."
    return [], ""


def tab_composicion(e, d):
    """Solapa "Composición" (v1.2.67): principales tenencias, por sector y por tipo de activo (barras de colores) y por país (gráfico de torta)."""
    d = d or {}
    hold = d.get("holdings") or []
    sect = d.get("sectores") or []
    act = d.get("activos") or []
    ten = F._tile("s6", "Principales tenencias", _barras(hold, "Yahoo no informó las tenencias de este ETF (los ETFs de oro, plata, petróleo o criptomonedas no tienen empresas adentro)."), ac="#0ea5e9")
    sec = F._tile("s6", "Por sector", _barras(sect, "Sin desglose por sector."), ac="#16a34a")
    piezas = [ten, sec]
    if act:
        piezas.append(F._tile("s6", "Por tipo de activo", _barras(act, ""), ac="#f59e0b"))
    paises, nota = paises_de(e, d)
    if paises:
        cuerpo = torta_html(paises) + (f'<div class="etf-nota">{html.escape(nota)}</div>' if nota else "")
    elif e["ticker"] in SIN_PAISES:
        cuerpo = '<div class="fch-sub" style="margin:0">No aplica: este ETF no tiene empresas adentro, así que no se reparte por país.</div>'
    else:
        cuerpo = ('<div class="fch-sub" style="margin:0">Todavía no tenemos el desglose por país de este ETF: Yahoo Finance no lo informa. '
                  'En cuanto se cargue, se muestra acá como un gráfico de torta.</div>')
    piezas.append(F._tile("s6" if act else "s12", "Por país", cuerpo, ac="#7c3aed"))
    return F._env(*piezas)


def tab_grafico_etf(pares):
    return F.tab_grafico_tabla(pares)


def tab_noticias_etf(ticker, items):
    return F.tab_noticias(ticker, items)


def con_intro(clave, cuerpo):
    t = INTROS.get(clave)
    return (f'<div class="fch-intro">{html.escape(t)}</div>' if t else "") + cuerpo
