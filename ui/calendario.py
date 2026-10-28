"""Calendario de resultados (v1.2.71): "Proximos 30 dias" agrupado por dia, con logo, ticker y, si Yahoo lo informa, si la empresa reporta
ANTES o DESPUES de la apertura del mercado. Sale de `agenda.resultados` de data/paquetes_yahoo.json (lo baja bajar_paquetes_yahoo.bat).
Es informacion, no una recomendacion: las fechas las confirma cada empresa y pueden cambiar."""
import datetime
import html
from urllib.parse import quote

from ui.logos import logo_html

DIAS = 30
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
.cal-d{margin:.7rem 0 .25rem;font-weight:700;font-size:.92rem;color:#1e3a8a;display:flex;align-items:center;gap:.5rem}
.cal-d .cal-n{font-weight:600;font-size:.74rem;color:#64748b;background:#eef2ff;border-radius:999px;padding:1px 8px}
.cal-d.hoy{color:#15803d}
.cal-g{display:flex;flex-wrap:wrap;gap:6px}
.cal-i{display:flex;align-items:center;gap:7px;background:#f8fafc;border:1px solid #e5e9f0;border-radius:10px;padding:5px 10px 5px 6px;text-decoration:none!important;color:#1f2937!important}
.cal-i:hover{background:#eef2ff;border-color:#c7d2fe}
.cal-i b{font-size:.86rem}
.cal-m{font-size:.68rem;font-weight:700;border-radius:6px;padding:1px 6px;white-space:nowrap}
.cal-m.antes{background:#fef3c7;color:#92400e}
.cal-m.despues{background:#e0e7ff;color:#3730a3}
.cal-m.nd{background:#f1f5f9;color:#64748b;font-weight:600}
.cal-e{font-size:.68rem;color:#94a3b8}
.cal-v{color:#64748b;font-size:.9rem;padding:.4rem 0}
.cal-p{color:#94a3b8;font-size:.74rem;margin-top:.8rem;line-height:1.4}
"""

_ETQ = {"antes": "☀ Antes de la apertura", "despues": "☾ Después del cierre"}


def _titulo_dia(f, hoy):
    base = f"{_SEM[f.weekday()]} {f.day} de {_MES[f.month - 1]}"
    base = base[0].upper() + base[1:]
    if f == hoy:
        return "Hoy · " + base
    if f == hoy + datetime.timedelta(days=1):
        return "Mañana · " + base
    return base


def calendario_html(grupos, hoy=None, nombres=None):
    hoy = hoy or datetime.date.today()
    if not grupos:
        return (f'<div class="cal"><div class="cal-v">No hay resultados cargados para los próximos {DIAS} días.</div></div>')
    hay_hora = any(m for _, its in grupos for _, m, _e in its)         # mientras Yahoo no informe el horario, no se repite "a confirmar" en cada empresa
    out = ['<div class="cal">']
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
