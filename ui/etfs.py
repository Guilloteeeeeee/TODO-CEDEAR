"""Tabla de ETFs (v1.2.63): ticker, descripcion, categoria y perfil orientativo (Todos / Moderado y Agresivo / Agresivo, el de las "Ideas de Inversion"
de Finanzas para Medicos Argentina). Es informacion educativa, no una recomendacion."""
import html

from ui.banderas import bandera_html

PERFILES = {
    "todos": ('<span class="etf-p etf-g">Todos</span>', "Todos los perfiles (riesgo bajo): puede usarse como parte de una estrategia de largo plazo."),
    "mod y agr": ('<span class="etf-p"><b class="etf-m">Mod</b> y <b class="etf-a">Agr</b></span>', "Perfil moderado (riesgo medio) y agresivo (riesgo alto)."),
    "agr": ('<span class="etf-p etf-a">Agr</span>', "Perfil agresivo (riesgo alto)."),
}

INTRO = ("Un ETF es una canasta de activos (acciones, bonos o materias primas) que se compra como si fuera una sola acción. "
         "«Perfil» es una categoría orientativa según la tolerancia al riesgo: Todos (riesgo bajo), Mod (moderado) y Agr (agresivo). "
         "Es información educativa, no una recomendación.")

CSS = """
.etf{max-width:1280px;margin:6px auto 0}
.etf-h{font-size:1.5rem;font-weight:800;color:#0f172a;margin:4px 0 2px}
.etf-s{font-size:14px;color:#4b5563;line-height:1.5;margin:0 0 10px}
.etf-n{font-size:13px;color:#6b7280;margin:8px 2px}
.etf-t{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);overflow:hidden}
.etf-r{display:grid;grid-template-columns:minmax(120px,1.1fr) minmax(0,5fr) minmax(150px,1.6fr) minmax(110px,1fr);gap:14px;align-items:center;padding:11px 18px;border-top:1px solid #eef1f4}
.etf-r:first-child{border-top:0}
.etf-hd{background:#2b2f33;color:#fff;font-size:13.5px;font-weight:700;padding:11px 18px}
.etf-hd div:last-child{text-align:center}
.etf-tk{font-weight:800;font-size:15.5px;color:#111827;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.etf-tk .fl,.etf-tk img{flex:none}
.etf-d{font-size:14px;color:#1f2937;line-height:1.45}
.etf-c{font-size:13.5px;color:#4b5563}
.etf-p{font-weight:700;font-size:14px;display:block;text-align:center}
.etf-g{color:#16a34a}.etf-m{color:#d97706}.etf-a{color:#dc2626}
.etf-nd{color:#9ca3af;font-weight:500}
.etf-tg{display:inline-block;font-size:11.5px;font-weight:700;border-radius:10px;padding:1px 8px;margin-left:2px;white-space:nowrap}
.etf-nv{background:#dcfce7;color:#166534}
.etf-bk{background:#fef3c7;color:#92400e}
.etf-et{background:#eef1f4;color:#4b5563;font-weight:600}
.etf-sub{display:block;margin-top:3px}
.etf-vacio{padding:26px;text-align:center;color:#6b7280}
@media (max-width:760px){
.etf-hd{display:none}
.etf-r{grid-template-columns:1fr auto;gap:4px 10px;padding:12px 14px}
.etf-tk{grid-column:1}.etf-pf{grid-column:2;grid-row:1}
.etf-d{grid-column:1 / -1}.etf-c{grid-column:1 / -1}
}
"""


def _perfil(p):
    h, tip = PERFILES.get(str(p or "").strip().lower(), ('<span class="etf-p etf-nd">—</span>', "Sin perfil asignado todavía."))
    return f'<div class="etf-pf" title="{html.escape(tip, quote=True)}">{h}</div>'


def _fila(e):
    banda = bandera_html(e["pais"], chica=True) if e.get("pais") else ""
    tk = f'<div class="etf-tk">{banda}<span>{html.escape(e["ticker"])}</span></div>'
    tags = ""
    if e.get("nuevo"):
        tags += '<span class="etf-tg etf-nv" title="CEDEAR de ETF nuevo">Nuevo</span>'
    if e.get("etiqueta"):
        tags += f'<span class="etf-tg etf-et">{html.escape(e["etiqueta"])}</span>'
    cat = html.escape(e.get("categoria") or "")
    if e.get("acceso") and e["acceso"].strip().lower() != "cedear":
        cat += f'<span class="etf-sub"><span class="etf-tg etf-bk" title="No tiene CEDEAR: no se puede comprar desde pesos en el mercado local; hay que pedirlo a la mesa del broker.">{html.escape(e["acceso"])}</span></span>'
    desc = html.escape(e.get("descripcion") or "")
    if tags:
        desc += f'<span class="etf-sub">{tags}</span>'
    return f'<div class="etf-r">{tk}<div class="etf-d">{desc}</div><div class="etf-c">{cat}</div>{_perfil(e.get("perfil"))}</div>'


def tabla_html(etfs):
    if not etfs:
        return '<div class="etf"><div class="etf-t"><div class="etf-vacio">No hay ETFs que coincidan con la búsqueda.</div></div></div>'
    cab = '<div class="etf-r etf-hd"><div>ETF</div><div>Descripción</div><div>Categoría</div><div>Perfil</div></div>'
    return f'<div class="etf"><div class="etf-t">{cab}{"".join(_fila(e) for e in etfs)}</div></div>'


def encabezado_html(total, mostrados):
    n = (f"{total} ETFs" if mostrados == total else f"{mostrados} de {total} ETFs")
    nuevos = ""
    return (f'<div class="etf"><div class="etf-h">ETFs</div><div class="etf-s">Ideas de inversión · Especial ETFs · Agosto – Septiembre 2026 · '
            f'Finanzas para Médicos Argentina</div><div class="etf-s">{html.escape(INTRO)}</div><div class="etf-n">{n}{nuevos}</div></div>')
