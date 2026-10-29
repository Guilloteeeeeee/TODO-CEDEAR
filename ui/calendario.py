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
.cal-d.hoy{color:#fff;background:linear-gradient(90deg,#e8668f 0%,#f4909f 100%);border-radius:10px;padding:5px 10px;text-shadow:0 1px 2px rgba(120,20,60,.30)}
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
    hay_hora = any(m for _, its in grupos for _, m, _e in its)         # mientras Yahoo no informe el horario, no se repite "a confirmar" en cada empresa
    n = cantidad if cantidad is not None else sum(len(v) for _, v in grupos)
    out = [f'<div class="cal"><div class="cal-h">Próximos {DIAS} días · <b>{n}</b> empresas</div>']
    for f, items in grupos:
        out.append(f'<div class="cal-d{" hoy" if f == hoy else ""}">{html.escape(_titulo_dia(f, hoy))}<span class="cal-n">{len(items)}</span></div><div class="cal-g">')
        for t, momento, estimada in items:
            etq = _ETQ.get(momento)
            m = f'<span class="cal-m {momento}">{etq}</span>' if etq else ('<span class="cal-m nd">Horario a confirmar</span>' if hay_hora else "")
            e = '<span class="cal-e">fecha estimada</span>' if estimada else ""
            nom = html.escape((nombres or {}).get(t, t), quote=True)
            out.append(f'<a class="cal-i" href="?empresa={quote(t, safe="")}" target="_self" title="{nom}">{logo_html(t, 22)}<b>{html.escape(t)}</b>{m}{e}</a>')
        out.append("</div>")
    out.append(f'<div class="cal-p">{"" if hay_hora else "Todavía no hay horarios (antes o después de la apertura) cargados: se completan al actualizar los datos. "}Fechas informadas por Yahoo Finance; cada empresa las confirma y pueden cambiar. Información, no una recomendación.</div></div>')
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
.eco-d.hoy{color:#fff;background:linear-gradient(90deg,#e8668f 0%,#f4909f 100%);border-radius:10px;padding:5px 10px;text-shadow:0 1px 2px rgba(120,20,60,.30)}
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
