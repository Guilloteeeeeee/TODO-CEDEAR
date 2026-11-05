"""Calendario de resultados (v1.2.71): "Proximos 60 dias" agrupado por dia, con logo, ticker y, si Yahoo lo informa, si la empresa reporta
ANTES o DESPUES de la apertura del mercado. Sale de `agenda.resultados` de data/paquetes_yahoo.json (lo baja bajar_paquetes_yahoo.bat).
Es informacion, no una recomendacion: las fechas las confirma cada empresa y pueden cambiar."""
import datetime
import html
import json
import os
from urllib.parse import quote

from ui.logos import logo_html

DIAS = 60
_SEM = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def proximos(paquetes, hoy=None, dias=DIAS, tickers=None):
    """[(fecha, [(ticker, momento, estimada)])] de las fechas entre hoy y hoy+dias, ordenado por dia y ticker.
    `momento`: 'antes' | 'despues' | None. `estimada`: True si Yahoo da un rango de fechas (todavia no confirmada)."""
    hoy = hoy or datetime.date.today()
    tope = hoy + datetime.timedelta(days=dias)
    permitidos = {str(t).upper() for t in tickers} if tickers is not None else None
    por_dia = {}
    for t, d in (paquetes or {}).items():
        if permitidos is not None and str(t).upper() not in permitidos:
            continue
        ag = (d or {}).get("agenda") or {}
        res = ag.get("resultados")
        if not res or not isinstance(res, (list, tuple)):
            continue
        f = res[0]
        if not isinstance(f, datetime.date) or isinstance(f, datetime.datetime):
            continue
        if not (hoy <= f <= tope):
            continue
        estimada = len(res) > 1 and res[1] is not None
        por_dia.setdefault(f, []).append((str(t).upper(), ag.get("momento"), estimada))
    return [(f, sorted(v)) for f, v in sorted(por_dia.items())]


CSS = """
.cal{font-family:inherit;color:#1f2937}
.cal-d{margin:.7rem 0 .25rem;font-weight:700;font-size:.92rem;color:#1f2937;display:flex;align-items:center;gap:.5rem}
.cal-d .cal-n{font-weight:600;font-size:.74rem;color:#64748b;background:#f1f5f9;border-radius:999px;padding:1px 8px}
.cal-d.hoy{color:#fff;background:linear-gradient(90deg,#15803d 0%,#22a35a 100%);border-radius:10px;padding:5px 10px;text-shadow:0 1px 2px rgba(5,60,30,.30)}
.cal-d.hoy .cal-n{background:rgba(255,255,255,.28);color:#fff}
.cal-g{display:flex;flex-wrap:wrap;gap:6px}
.cal-i{display:flex;align-items:center;gap:7px;background:#f8fafc;border:1px solid #e5e9f0;border-radius:10px;padding:5px 10px 5px 6px;text-decoration:none!important;color:#1f2937!important}
.cal-i:hover{background:#eef2ff;border-color:#c7d2fe}
.cal-i b{font-size:.86rem}
.cal-m{font-size:.74rem;font-weight:400;color:#6b7280;white-space:nowrap}
.cal-e{font-size:.68rem;color:#94a3b8}
.cal-h{font-size:.85rem;color:#475569}.cal-v{color:#64748b;font-size:.9rem;padding:.4rem 0}
.cal-p{color:#94a3b8;font-size:.74rem;margin-top:.8rem;line-height:1.4}
"""

_ETQ = {"antes": "Antes de la apertura", "despues": "Después del cierre"}


def _titulo_dia(f, hoy):
    base = f"{_SEM[f.weekday()]} {f.day} de {_MES[f.month - 1]}"
    base = base[0].upper() + base[1:]
    if f == hoy:
        return "Hoy · " + base
    if f == hoy + datetime.timedelta(days=1):
        return "Mañana · " + base
    return base


def calendario_html(grupos, hoy=None, nombres=None, cantidad=None):
    hoy = hoy or datetime.date.today()
    if not grupos:
        return (f'<div class="cal"><div class="cal-v">No hay resultados cargados para los próximos {DIAS} días.</div></div>')
    n = cantidad if cantidad is not None else sum(len(v) for _, v in grupos)
    out = [f'<div class="cal"><div class="cal-h">Próximos {DIAS} días · <b>{n}</b> empresas</div>']
    for f, items in grupos:
        out.append(f'<div class="cal-d{" hoy" if f == hoy else ""}">{html.escape(_titulo_dia(f, hoy))}<span class="cal-n">{len(items)}</span></div><div class="cal-g">')
        for t, momento, estimada in items:
            m = ""      # v1.5.23 (pedido de Guille): el calendario ya no muestra «antes de la apertura / después del cierre»
            e = '<span class="cal-e">fecha estimada</span>' if estimada else ""
            nom = html.escape((nombres or {}).get(t, t), quote=True)
            out.append(f'<a class="cal-i" href="?empresa={quote(t, safe="")}" target="_self" title="{nom}">{logo_html(t, 22)}<b>{html.escape(t)}</b>{m}{e}</a>')
        out.append("</div>")
    out.append(f'<div class="cal-p">Fechas informadas por Yahoo Finance; cada empresa las confirma y pueden cambiar. Información, no una recomendación.</div></div>')
    return "".join(out)


def buscar_ticker(paquetes, ticker, hoy=None):
    """Texto con cuándo presenta resultados la empresa `ticker` (de agenda.resultados), o '' si no hay dato. Es información: la fecha la confirma la empresa."""
    hoy = hoy or datetime.date.today()
    t = str(ticker or "").strip().upper()
    if not t:
        return ""
    ag = ((paquetes or {}).get(t) or {}).get("agenda") or {}
    res = ag.get("resultados")
    if not res or not isinstance(res, (list, tuple)) or not isinstance(res[0], datetime.date):
        return f"{t}: todavía no tenemos fecha de resultados informada por Yahoo Finance."
    f0 = res[0]
    f1 = res[1] if len(res) > 1 and isinstance(res[1], datetime.date) else None
    if f1:
        cuando = f"entre el {f0.strftime('%d/%m/%Y')} y el {f1.strftime('%d/%m/%Y')} (fecha estimada, todavía sin confirmar)"
    else:
        dias = (f0 - hoy).days
        faltan = "hoy" if dias == 0 else "mañana" if dias == 1 else f"en {dias} días" if dias > 1 else f"hace {-dias} días"
        cuando = f"el {_SEM[f0.weekday()]} {f0.strftime('%d/%m/%Y')} ({faltan})"
    mom = {"antes": ", antes de la apertura del mercado", "despues": ", después del cierre del mercado"}.get(ag.get("momento"), "")
    return f"{t} presenta resultados {cuando}{mom}."


# --- Calendario económico (v1.2.79): solo el evento y la fecha ------------------------------------------------------------------
# Las fechas salen de data/calendario_economico.json: calendarios oficiales de la Reserva Federal, el BLS y el BEA (EE.UU.) y el INDEC (Argentina).
# No es una conexión en vivo: se actualiza cargando el archivo (el calendario del INDEC se publica por semestre).
RUTA_ECO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "calendario_economico.json")

CSS_ECO = """
.eco{font-family:inherit;color:#1f2937}
.eco-d{margin:.7rem 0 .25rem;font-weight:700;font-size:.92rem;color:#1f2937}
.eco-d.hoy{color:#fff;background:linear-gradient(90deg,#15803d 0%,#22a35a 100%);border-radius:10px;padding:5px 10px;text-shadow:0 1px 2px rgba(5,60,30,.30)}
.eco-i{display:flex;align-items:baseline;gap:8px;padding:3px 0 3px 4px;font-size:.9rem;line-height:1.35}
.eco-p{flex:none;min-width:62px;text-align:center;font-size:.68rem;font-weight:700;border-radius:6px;padding:1px 6px;background:#1e3a8a;color:#fff;white-space:nowrap}
.eco-p.ar{background:#9fd0f2;color:#0b3a5c}
.eco-v{color:#64748b;font-size:.9rem;padding:.4rem 0}
.eco-n{color:#94a3b8;font-size:.74rem;margin-top:.8rem;line-height:1.4}
"""


def cargar_economico(ruta=None):
    """([{'f': date, 'e': evento, 'p': país}], texto de fuentes). ([], '') si el archivo no está o no se puede leer."""
    try:
        with open(ruta or RUTA_ECO, encoding="utf-8") as f:
            j = json.load(f)
        ev = []
        for x in j.get("eventos") or []:
            ev.append({"f": datetime.date.fromisoformat(str(x["f"])), "e": str(x["e"]), "p": str(x.get("p") or "")})
        return ev, " · ".join(j.get("fuentes") or [])
    except Exception:  # noqa: BLE001
        return [], ""


def economicos(eventos, hoy=None, dias=DIAS):
    """[(fecha, [(evento, país)])] entre hoy y hoy+dias."""
    hoy = hoy or datetime.date.today()
    tope = hoy + datetime.timedelta(days=dias)
    por_dia = {}
    for x in eventos or []:
        if hoy <= x["f"] <= tope:
            por_dia.setdefault(x["f"], []).append((x["e"], x["p"]))
    return [(f, v) for f, v in sorted(por_dia.items())]


def economico_html(grupos, fuentes="", hoy=None):
    hoy = hoy or datetime.date.today()
    if not grupos:
        return f'<div class="eco"><div class="eco-v">No hay eventos cargados para los próximos {DIAS} días.</div></div>'
    out = ['<div class="eco">']
    for f, items in grupos:
        out.append(f'<div class="eco-d{" hoy" if f == hoy else ""}">{html.escape(_titulo_dia(f, hoy))}</div>')
        for e, p in items:
            out.append(f'<div class="eco-i"><span class="eco-p{" ar" if p == "Argentina" else ""}">{html.escape(p)}</span><span>{html.escape(e)}</span></div>')
    out.append(f'<div class="eco-n">Fechas de los calendarios oficiales ({html.escape(fuentes)}). Pueden cambiar.</div></div>' if fuentes else "</div>")
    return "".join(out)


# --- Calendario de cuadraditos (v1.5.34, pedido de Guille): un mes por vez, con solapas de mes; cada día es un cuadrado con sus empresas / eventos -----------------
CSS_GRILLA = """
.cg{font-family:inherit;color:#1f2937}
.cg-r{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.cg-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}
.cg-tab{cursor:pointer;user-select:none;border:1px solid #c3ccd8;background:#fff;color:#374151;border-radius:9px;padding:7px 18px;font-size:.95rem;font-weight:700}
.cg-tab:hover{background:#eef2f7}
.cg-mes{display:none}
.cg-g{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}
.cg-wd{text-align:center;font-size:.76rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.6px;padding:2px 0 0}
.cg-c.pad{visibility:hidden}
.cg-c{min-height:84px;border:1px solid #e1e7ef;border-radius:10px;padding:6px 8px 8px;background:#fff;display:flex;flex-direction:column;gap:5px;box-sizing:border-box;min-width:0}
.cg-c.fin{background:#f8fafc}
.cg-c.fuera{background:#f6f8fa;border-color:#eef1f5}
.cg-c.fuera .cg-n{color:#c3cbd6}
.cg-c.hoy{border:2px solid #15803d;background:#f0fdf4}
.cg-n{font-size:.92rem;font-weight:800;color:#1f2937;display:flex;align-items:center;gap:6px}
.cg-c.hoy .cg-n b{background:#15803d;color:#fff;border-radius:999px;padding:0 8px}
.cg-hoy{font-size:.66rem;font-weight:700;color:#15803d;text-transform:uppercase;letter-spacing:.4px}
.cg-ds{display:none}
.cg-ts{display:flex;flex-wrap:wrap;gap:4px}
.cg-t{display:inline-block;font-size:.76rem;font-weight:700;background:#e8eefc;color:#1e3a8a!important;border-radius:6px;padding:2px 7px;text-decoration:none!important;line-height:1.35}
.cg-t:hover{background:#1e3a8a;color:#fff!important}
.cg-t.est{background:#fff;border:1px dashed #94a3b8;color:#475569!important;padding:1px 6px}
.cg-e{font-size:.78rem;line-height:1.3;color:#1f2937;border-left:3px solid #1e3a8a;padding:1px 0 1px 6px;background:#f1f5fd;border-radius:0 6px 6px 0}
.cg-e.ar{border-left-color:#5fb0e8;background:#eef7fd}
.cg-p{display:block;font-size:.64rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.4px}
.cg-v{color:#64748b;font-size:.9rem;padding:.4rem 0}
.cg-h{font-size:.85rem;color:#475569}
.cg-pie{color:#94a3b8;font-size:.74rem;margin-top:.8rem;line-height:1.4}
@media (max-width:900px){
.cg-g{display:block}.cg-wd,.cg-c.vacio,.cg-c.fuera,.cg-c.pad{display:none}
.cg-c{min-height:0;margin-bottom:6px}
.cg-ds{display:inline;font-weight:600;font-size:.86rem}.cg-n b{display:none}
}
"""


def _fin_de_mes(f):
    sig = datetime.date(f.year + (f.month == 12), f.month % 12 + 1, 1)
    return sig - datetime.timedelta(days=1)


def _grilla(por_dia, hoy, dias, uid, vacio):
    """`por_dia`: {fecha: HTML de lo que va en el cuadrado}. Un mes por solapa (de hoy hasta hoy+dias); días sin datos o fuera del rango, apagados."""
    tope = hoy + datetime.timedelta(days=dias)
    meses = []
    f = datetime.date(hoy.year, hoy.month, 1)
    while f <= tope:
        meses.append(f)
        f = _fin_de_mes(f) + datetime.timedelta(days=1)
    radios = "".join(f'<input type="radio" name="cg-{uid}" id="cg-{uid}-{i}" class="cg-r"{" checked" if i == 0 else ""} aria-hidden="true" tabindex="-1">' for i in range(len(meses)))
    css = "".join(f'#cg-{uid}-{i}:checked~.cg-mes-{i}{{display:block}}#cg-{uid}-{i}:checked~.cg-tabs label[for=cg-{uid}-{i}]{{background:#15803d;color:#fff;border-color:#15803d}}' for i in range(len(meses)))
    tabs, paneles = [], []
    for i, m in enumerate(meses):
        tabs.append(f'<label for="cg-{uid}-{i}" class="cg-tab">{_MES[m.month - 1].capitalize()} {m.year}</label>')
        ult = min(_fin_de_mes(m), tope)
        celdas = ['<div class="cg-wd">' + d + "</div>" for d in ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")]
        d = m
        if i == 0:                        # en el primer mes no se dibujan las semanas que ya pasaron: arranca el lunes de la semana de hoy
            d = max(m, hoy - datetime.timedelta(days=hoy.weekday()))
        celdas += ['<div class="cg-c pad"></div>'] * d.weekday()
        while d <= _fin_de_mes(m):
            if d > ult and d.weekday() == 0:
                break                     # en el último mes no se dibujan semanas enteras fuera del rango
            dentro = hoy <= d <= tope
            cont = por_dia.get(d, "") if dentro else ""
            cls = "cg-c" + (" fin" if d.weekday() >= 5 else "") + (" hoy" if d == hoy else "") + ("" if dentro else " fuera") + ("" if cont else " vacio")
            marca = '<span class="cg-hoy">hoy</span>' if d == hoy else ""
            celdas.append(f'<div class="{cls}"><div class="cg-n"><b>{d.day}</b><span class="cg-ds">{_SEM[d.weekday()].capitalize()} {d.day} de {_MES[d.month - 1]}</span>{marca}</div>{cont}</div>')
            d += datetime.timedelta(days=1)
        paneles.append(f'<div class="cg-mes cg-mes-{i}"><div class="cg-g">{"".join(celdas)}</div></div>')
    cuerpo = vacio if not por_dia else ""
    return f'<style>{css}</style><div class="cg">{radios}{cuerpo}<div class="cg-tabs">{"".join(tabs)}</div>{"".join(paneles)}</div>'


def calendario_grilla_html(grupos, hoy=None, nombres=None, cantidad=None):
    """Empresas que presentan resultados, en cuadraditos por día (solapa por mes). Cada empresa es un botón que lleva a su ficha."""
    hoy = hoy or datetime.date.today()
    n = cantidad if cantidad is not None else sum(len(v) for _, v in grupos)
    por_dia = {}
    for f, items in grupos:
        chips = []
        for t, _momento, estimada in items:
            nom = html.escape((nombres or {}).get(t, t), quote=True)
            extra = " (fecha estimada)" if estimada else ""
            chips.append(f'<a class="cg-t{" est" if estimada else ""}" href="?empresa={quote(t, safe="")}" target="_self" title="{nom}{extra}">{html.escape(t)}</a>')
        por_dia[f] = f'<div class="cg-ts">{"".join(chips)}</div>'
    vacio = f'<div class="cg-v">No hay resultados cargados para los próximos {DIAS} días.</div>' if not grupos else ""
    cab = f'<div class="cg-h">Próximos {DIAS} días · <b>{n}</b> empresas · el borde punteado es fecha estimada</div>' if grupos else ""
    pie = '<div class="cg-pie">Fechas informadas por Yahoo Finance; cada empresa las confirma y pueden cambiar. Información, no una recomendación.</div>'
    return cab + _grilla(por_dia, hoy, DIAS, "res", vacio) + pie


def economico_grilla_html(grupos, fuentes="", hoy=None):
    """Eventos económicos (Fed, empleo, inflación, INDEC…) en cuadraditos por día."""
    hoy = hoy or datetime.date.today()
    por_dia = {}
    for f, items in grupos:
        por_dia[f] = "".join(f'<div class="cg-e{" ar" if p == "Argentina" else ""}"><span class="cg-p">{html.escape(p)}</span>{html.escape(e)}</div>' for e, p in items)
    vacio = f'<div class="cg-v">No hay eventos cargados para los próximos {DIAS} días.</div>' if not grupos else ""
    pie = f'<div class="cg-pie">Fechas de los calendarios oficiales ({html.escape(fuentes)}). Pueden cambiar.</div>' if fuentes else ""
    return _grilla(por_dia, hoy, DIAS, "eco", vacio) + pie
