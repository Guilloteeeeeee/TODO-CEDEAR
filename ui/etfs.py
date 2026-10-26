"""ETFs (v1.2.64): la tabla de la pantalla de ETFs y la pagina de cada ETF (?etf=TICKER), con el mismo estilo que las de empresas.
Todo es informacion educativa, no una recomendacion. Los datos salen de data/etfs.csv (los arma Guille), de Yahoo (en vivo o del archivo
data/etfs_yahoo.json) y del precio de hoy; lo que no hay se muestra como "—" (nunca se inventa)."""
import datetime as _dt
import html
from urllib.parse import quote, quote_plus

from ui import ficha as F
from ui.tabla_visual import _money, _n, barra_52s_html

INTRO = ("Un ETF es una canasta de activos (acciones, bonos o materias primas) que se compra como si fuera una sola acción. "
         "Pasá el mouse por los títulos de cada columna para ver qué significan. Es información educativa, no una recomendación.")

INTROS = {
    "resumen": "Qué es el ETF, qué tiene adentro, cuánto cuesta (comisión), si paga dividendos o los reinvierte, y dónde cotiza, con el link a su sitio oficial.",
    "grafico": "Cómo se movió el precio del ETF y cuánto rindió en distintos plazos. Rendimientos pasados no son garantías de resultados futuros.",
    "noticias": "Los últimos titulares sobre el ETF, en su idioma original, con link a cada nota.",
}

TIPS = {
    "Precio": "Precio de una cuota del ETF en dólares, en su mercado de origen (no en tiempo real).",
    "Descripción": "Qué replica o en qué invierte el ETF.",
    "Categoría": "Grupo al que pertenece (Solo USA, Internacionales, Sectoriales, Commodities...).",
    "Gestor": "Empresa que administra el ETF (la que lo crea y lo mantiene).",
    "AUM": "Activos bajo gestión: cuánto dinero tiene invertido el ETF en total. Más grande suele significar más liquidez y más permanencia en el tiempo. B = mil millones, M = millón.",
    "Comisión": "Lo que cobra el ETF por año, como porcentaje de lo invertido (expense ratio). Ya está descontada del precio de la cuota; no se paga aparte.",
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
.etf-s{font-size:14px;color:#4b5563;line-height:1.5;margin:6px 2px 4px}
.etf-n{font-size:13px;color:#6b7280;margin:2px 2px 8px}
.etf-t{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);overflow:hidden}
.etf-r{display:grid;grid-template-columns:minmax(190px,2.1fr) minmax(88px,.8fr) minmax(0,3.2fr) minmax(110px,1.1fr) minmax(120px,1.2fr) minmax(82px,.8fr) minmax(74px,.7fr);gap:14px;align-items:center;padding:11px 18px;border-top:1px solid #eef1f4}
.etf-r:first-child{border-top:0}
.etf-hd{background:#2b2f33;color:#fff;font-size:13.5px;font-weight:700;padding:11px 18px}
.etf-hd [title]{cursor:help}
.etf-hd .num,.etf-r .num{text-align:right}
.etf-nm{font-size:15px;font-weight:700;line-height:1.3}
.etf-nm a{color:#111827;text-decoration:none}
.etf-nm a:hover{text-decoration:underline;color:#1d4ed8}
.etf-tk{font-size:13px;font-weight:700;color:#6b7280;margin-top:2px}
.etf-d{font-size:13.5px;color:#1f2937;line-height:1.45}
.etf-c,.etf-g{font-size:13.5px;color:#4b5563}
.etf-pr{font-size:14.5px;font-weight:700;color:#111827;white-space:nowrap}
.etf-v{font-size:14px;color:#111827;white-space:nowrap}
.etf-nd{color:#9ca3af;font-weight:500}
.etf-tg{display:inline-block;font-size:11.5px;font-weight:700;border-radius:10px;padding:1px 8px;margin:3px 4px 0 0;white-space:nowrap}
.etf-nv{background:#dcfce7;color:#166534}
.etf-bk{background:#fef3c7;color:#92400e}
.etf-et{background:#eef1f4;color:#4b5563;font-weight:600}
.etf-vacio{padding:26px;text-align:center;color:#6b7280}
.etf-lab{display:none}
@media (max-width:900px){
.etf-hd{display:none}
.etf-r{grid-template-columns:1fr 1fr;gap:6px 14px;padding:12px 14px}
.etf-r>div:nth-child(1){grid-column:1 / -1}
.etf-r>div:nth-child(3){grid-column:1 / -1}
.etf-r>div:nth-child(2),.etf-r .num{text-align:left}
.etf-lab{display:block;font-size:11.5px;color:#9ca3af;font-weight:600}
}
/* pagina de cada ETF */
.etf-ico{width:72px;height:72px;border-radius:16px;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:42px;line-height:1;flex:none;overflow:hidden}
.etf-ico svg{width:72px;height:72px;display:block}
.etf-pill{display:inline-block;font-size:12px;font-weight:700;border-radius:10px;padding:2px 9px;background:#eef1f4;color:#4b5563}
.etf-hold{display:grid;grid-template-columns:minmax(0,1fr) 62px;gap:4px 10px;align-items:center;font-size:13.5px}
.etf-hold .bar{height:7px;background:#eef1f4;border-radius:4px;overflow:hidden;grid-column:1 / -1;margin:-2px 0 6px}
.etf-hold .bar i{display:block;height:100%;background:#0ea5e9;border-radius:4px}
.etf-hold .nm{color:#1f2937;min-width:0;overflow-wrap:anywhere}.etf-hold .nm b{color:#111827}
.etf-hold .pc{text-align:right;font-weight:700;color:#111827}
.etf-ej{font-size:13px;color:#4b5563;line-height:1.5;margin-top:10px;background:#f8fafc;border-radius:10px;padding:9px 12px}
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
    """Lo que representa el ETF: un dibujo (Bitcoin, Ethereum) o un emoji. Sin dato, las iniciales."""
    ic = str(e.get("icono") or "").strip()
    if ic.startswith("svg:") and ic[4:] in _SVG:
        return f'<div class="etf-ico">{_SVG[ic[4:]]}</div>'
    if ic:
        return f'<div class="etf-ico">{html.escape(ic)}</div>'
    return f'<div class="etf-ico" style="font-size:24px;font-weight:800;color:#475569">{html.escape(e["ticker"][:3])}</div>'


# --- tabla -------------------------------------------------------------------------------------------------------------

def _fila(e, d, precio):
    tk = e["ticker"]
    nombre = html.escape(e.get("nombre") or tk)
    tags = ""
    if e.get("nuevo"):
        tags += '<span class="etf-tg etf-nv" title="CEDEAR de ETF nuevo">Nuevo</span>'
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
            f'<div class="etf-pr num">{lab("Precio")}{p}</div>'
            f'<div class="etf-d">{html.escape(e.get("descripcion") or "")}</div>'
            f'<div class="etf-c">{lab("Categoría")}{html.escape(e.get("categoria") or "")}</div>'
            f'<div class="etf-g">{lab("Gestor")}{g}</div>'
            f'<div class="etf-v num">{lab("AUM")}{aum_texto((d or {}).get("aum"))}</div>'
            f'<div class="etf-v num">{lab("Comisión")}{comision_texto((d or {}).get("comision"))}</div></div>')


def tabla_html(etfs, datos=None, precios=None):
    datos, precios = datos or {}, precios or {}
    if not etfs:
        return '<div class="etf"><div class="etf-t"><div class="etf-vacio">No hay ETFs que coincidan con el filtro.</div></div></div>'
    def th(t, cls=""):
        return f'<div class="{cls}" title="{html.escape(TIPS.get(t, ""), quote=True)}">{t}</div>'
    cab = ('<div class="etf-r etf-hd"><div>ETF</div>' + th("Precio", "num") + th("Descripción") + th("Categoría") + th("Gestor") + th("AUM", "num") + th("Comisión", "num") + "</div>")
    filas = "".join(_fila(e, datos.get(e["ticker"]), precios.get(e["ticker"]) or (datos.get(e["ticker"]) or {}).get("precio")) for e in etfs)
    return f'<div class="etf"><div class="etf-t">{cab}{filas}</div></div>'


def encabezado_html(total, mostrados):
    n = (f"{total} ETFs" if mostrados == total else f"{mostrados} de {total} ETFs")
    return f'<div class="etf"><div class="etf-s">{html.escape(INTRO)}</div><div class="etf-n">{n}</div></div>'


# --- pagina del ETF ---------------------------------------------------------------------------------------------------------

def tipo_distribucion(e, d):
    """('Distribución' | 'Acumulación' | 'Sin dividendos' | None, explicacion). Primero lo que puso Guille en el CSV; si no, se deduce de los pagos de Yahoo."""
    e = e or {}
    d = d or {}
    c = str(e.get("distribucion") or "").strip().lower()
    if c.startswith("acum"):
        return "Acumulación", "El ETF reinvierte dentro del fondo los dividendos que cobra: no te paga nada en efectivo y el valor de la cuota los incluye."
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


def _barras(items, vacio):
    if not items:
        return f'<div class="fch-sub" style="margin:0">{html.escape(vacio)}</div>'
    tope = max(i["pct"] for i in items) or 1
    out = []
    for i in items:
        nom = html.escape(i["nombre"] or "")
        if i.get("simbolo"):
            nom = f'<b>{html.escape(i["simbolo"])}</b> · {nom}' if nom else f'<b>{html.escape(i["simbolo"])}</b>'
        out.append(f'<div class="nm">{nom}</div><div class="pc">{i["pct"]:.1f}%</div><div class="bar"><i style="width:{max(2.0, i["pct"] / tope * 100):.0f}%"></i></div>')
    return '<div class="etf-hold">' + "".join(out) + "</div>"


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


def tab_resumen(e, d, precio, cedear=None):
    d = d or {}
    tk = e["ticker"]
    desc = (f'<p class="fch-desc" style="margin:0 0 4px">{html.escape(e.get("descripcion") or "")}</p>' if e.get("descripcion") else "")
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
    if e.get("nuevo"):
        filas.append(k("Novedad", "CEDEAR nuevo"))
    datos_h = F._tile("s6", "Datos del ETF", '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>", ac="#0ea5e9")
    # --- cifras ---
    p = _n(precio) or _n(d.get("precio"))
    nav = _n(d.get("nav"))
    c = [k("Precio", _usd(p), "Precio al que cotiza una cuota del ETF en el mercado.")]
    c.append(k("NAV (valor de la cuota)", _usd(nav), "Net Asset Value: lo que valen realmente los activos que tiene el ETF, dividido por la cantidad de cuotas. El precio de mercado suele estar muy cerca."))
    if p and nav and nav > 0:
        dif = (p / nav - 1) * 100
        c.append(k("Precio vs NAV", f"{dif:+.2f}%", "Si es positivo, la cuota cotiza con prima (más cara que sus activos); si es negativo, con descuento. En los ETFs grandes suele ser mínimo."))
    c.append(k("AUM (patrimonio)", aum_texto(d.get("aum")), "Activos bajo gestión: el dinero total que tiene invertido el ETF."))
    com = _n(d.get("comision"))
    c.append(k("Comisión anual", comision_texto(com), "Lo que cobra el ETF por año (expense ratio), como porcentaje de lo invertido. Ya está descontada del precio de la cuota."))
    tipo, tipo_tip = tipo_distribucion(e, d)
    c.append(k("Dividendos", f"<b>{html.escape(tipo)}</b>" if tipo else "—", tipo_tip or "Si el ETF paga los dividendos en efectivo (distribución) o los reinvierte (acumulación)."))
    div = d.get("dividendos") or {}
    if tipo == "Distribución":
        if _n(d.get("rendimiento")):
            c.append(k("Rendimiento por dividendo", _pct(d["rendimiento"]), "Dividendos pagados en el último año como porcentaje del precio actual."))
        if _n(d.get("dividendo_anual")) or _n(div.get("total_12m")):
            c.append(k("Dividendo anual por cuota", _usd(d.get("dividendo_anual") or div.get("total_12m")), "Suma de lo pagado en los últimos 12 meses por cada cuota."))
        if div.get("frecuencia"):
            c.append(k("Frecuencia de pago", html.escape(div["frecuencia"]), "Cada cuánto paga: mensual, trimestral, semestral o anual."))
        if div.get("ultimo") and div["ultimo"].get("fecha"):
            u = div["ultimo"]
            c.append(k("Último pago", f'{_usd(u.get("monto"))} · {_fecha(u["fecha"])}', "Monto por cuota y fecha del último dividendo."))
    lo, hi = _n(d.get("min_52s")), _n(d.get("max_52s"))
    if lo and hi and hi > lo:
        c.append(k("Rango de 52 semanas", f"{_money(lo)} – {_money(hi)}", "Del precio más bajo al más alto de los últimos 12 meses."))
    if _n(d.get("beta")):
        c.append(k("Beta (3 años)", f"{d['beta']:.2f}", "Cuánto se mueve el ETF respecto del mercado: 1 se mueve igual; más de 1, más que el mercado; menos de 1, menos."))
    cuerpo = '<div class="fch-kv" style="margin-top:0">' + "".join(c) + "</div>"
    if com is not None and com >= 0:
        cuerpo += (f'<div class="etf-ej"><b>Ejemplo:</b> con US&#36;&nbsp;10,000 invertidos, una comisión de {comision_texto(com)} anual equivale a unos '
                   f'US&#36;&nbsp;{10000 * com / 100:,.1f} por año. Se descuenta sola del valor de la cuota.</div>')
    cifras = F._tile("s6", "Cifras", cuerpo, ac="#0369a1")
    # --- adentro ---
    hold = d.get("holdings") or []
    sect = d.get("sectores") or []
    act = d.get("activos") or []
    izq = "<h4 style='margin:0 0 8px;font-size:14px'>Principales tenencias</h4>" + _barras(hold, "Yahoo no informó las tenencias de este ETF todavía.")
    der = "<h4 style='margin:0 0 8px;font-size:14px'>Por sector</h4>" + _barras(sect, "Sin desglose por sector.")
    if act:
        der += "<h4 style='margin:14px 0 8px;font-size:14px'>Por tipo de activo</h4>" + _barras(act, "")
    adentro = F._tile("s12", "Qué tiene adentro", f'<div class="etf-2c"><div>{izq}</div><div>{der}</div></div>', ac="#0ea5e9")
    return F._env(arriba, datos_h, cifras, adentro)


def tab_grafico_etf(pares):
    return F.tab_grafico_tabla(pares)


def tab_noticias_etf(ticker, items):
    return F.tab_noticias(ticker, items)


def con_intro(clave, cuerpo):
    t = INTROS.get(clave)
    return (f'<div class="fch-intro">{html.escape(t)}</div>' if t else "") + cuerpo
