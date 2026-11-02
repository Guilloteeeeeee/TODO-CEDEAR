"""Pantalla de inicio (v1.5.7), según la maqueta aprobada por Guille: una frase fuerte, un solo botón («Comenzar») y una vista previa de la app (tortas, tabla con valoración y la
ficha de una empresa en un celular). Todo lo de la vista previa son datos de ejemplo («Empresa de ejemplo A»): no se muestra ninguna empresa ni número real. Sin otros links.
«Comenzar» lleva a la tabla de empresas (?inicio=0)."""
import html

TITULO_1 = "No compres CEDEARs a ciegas."
TITULO_2 = "Conocelos antes de invertir."
TEXTO = "Filtrá Acciones y ETFs que cotizan como CEDEARs en Argentina, leé el análisis de cada empresa y enterate cuáles están baratas. Evalúa tu Portfolio. Todo Gratuito!"
BOTON = "Comenzar"
AVISO = "Información educativa, no es una recomendación."

AZ, CE, NA, VE, MO = "#2563eb", "#0ea5e9", "#f59e0b", "#15803d", "#7c3aed"


def _torta(partes, size=84, hueco=54):
    acc, tramos = 0, []
    for col, p in partes:
        tramos.append(f"{col} {acc}% {acc + p}%")
        acc += p
    m = f"radial-gradient(circle,transparent {hueco}%,#000 {hueco + 1}%)"
    return (f'<span style="display:block;width:{size}px;height:{size}px;border-radius:50%;flex:none;background:conic-gradient({",".join(tramos)});'
            f'-webkit-mask:{m};mask:{m}"></span>')


def _leyenda(items):
    return ('<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;color:#374151">'
            + "".join(f'<span style="display:flex;align-items:center;gap:6px"><i style="width:9px;height:9px;border-radius:50%;background:{c};display:block"></i>{html.escape(t)}</span>'
                      for c, t in items) + "</div>")


def _tarjeta(titulo, partes, items):
    return ('<div style="background:#fff;border:1px solid #e3e8ee;border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:10px">'
            f'<span style="font-size:14px;font-weight:700;color:#111827">{html.escape(titulo)}</span>'
            f'<div style="display:flex;align-items:center;gap:12px">{_torta(partes)}{_leyenda(items)}</div></div>')


def _barra(pos, col):
    return (f'<span style="display:block;position:relative;height:6px;border-radius:3px;background:#e5e7eb;width:120px">'
            f'<i style="position:absolute;left:{pos}%;top:-3px;width:12px;height:12px;border-radius:50%;background:{col};display:block;margin-left:-6px"></i></span>')


def _score(n, col):
    return (f'<span style="display:inline-flex;flex-direction:column;align-items:center;border:2px solid {col};border-radius:8px;overflow:hidden;width:40px">'
            f'<b style="font-size:16px;line-height:26px;color:#111827">{n}</b><i style="font-style:normal;background:{col};color:#fff;font-size:9px;width:100%;text-align:center;line-height:12px">SCORE</i></span>')


def _fila(nom, tk, pos, col, txt, sc, dy):
    return ('<div class="hr-fila">'
            f'<span style="display:flex;flex-direction:column"><b style="font-size:13px;color:#111827">{nom}</b><small style="color:#6b7280;font-size:11px">{tk}</small></span>'
            f'<span style="display:flex;flex-direction:column;gap:6px"><small style="color:{col};font-weight:700;font-size:11px">{txt}</small>{_barra(pos, col)}</span>'
            f'{_score(sc, col)}<b style="font-size:13px;color:#111827;text-align:right">{dy}</b></div>')


def _marco():
    tarjetas = ('<div class="hr-tres">'
                + _tarjeta("Estructura", [(AZ, 50), (CE, 40), (NA, 10)], [(AZ, "Renta Variable"), (CE, "Renta Fija"), (NA, "Oro")])
                + _tarjeta("Geografía", [(AZ, 75), (CE, 20), (MO, 5)], [(AZ, "EE.UU."), (CE, "Desarrollados"), (MO, "Emergentes")])
                + _tarjeta("Supersectores", [(CE, 30), (AZ, 20), (VE, 50)], [(VE, "Defensivo"), (CE, "Sensible"), (AZ, "Cíclico")]) + "</div>")
    tabla = ('<div class="hr-tabla"><div class="hr-fila hr-th"><span>Empresa</span><span>Valoración</span><span>Score</span><span style="text-align:right">Dividendo</span></div>'
             + _fila("Empresa de ejemplo A", "EJ-A · Consumo defensivo", 35, "#15803d", "Podría estar moderadamente infravalorada", 78, "2,9 %")
             + _fila("Empresa de ejemplo B", "EJ-B · Tecnología", 60, "#b45309", "Podría estar razonablemente valuada", 55, "0,6 %")
             + _fila("Empresa de ejemplo C", "EJ-C · Salud", 85, "#b91c1c", "Podría estar sobrevalorada", 31, "1,4 %") + "</div>")
    return ('<div class="hr-marco"><div style="text-align:center;font-size:20px;font-weight:700;color:#111827">Evaluá tu Portfolio</div>' + tarjetas
            + '<div style="text-align:center;font-size:15px;font-weight:700;color:#111827;margin-top:4px">Empresas con su valoración</div>' + tabla + "</div>")


def _celular():
    chips = "".join(f'<span style="border:1px solid #e3e8ee;border-radius:999px;padding:3px 8px;font-size:10px;color:#374151">{t}</span>' for t in ("Resumen", "Análisis Fundamental", "Valuación"))
    return ('<div class="hr-cel"><div class="hr-tel">'
            '<span style="width:46px;height:5px;border-radius:3px;background:#d1d5db;display:block"></span>'
            '<b style="font-size:17px;color:#111827">Empresa de ejemplo</b><small style="color:#6b7280;font-size:11px;margin-top:-6px">EJ-A · Consumo defensivo</small>'
            f'<div style="display:flex;gap:14px;align-items:center">{_score(78, "#15803d")}<span style="display:flex;flex-direction:column"><small style="color:#6b7280;font-size:10px">Dividendo</small><b style="font-size:15px">2,9 %</b></span></div>'
            f'<span style="color:#15803d;font-weight:700;font-size:11px;text-align:center">Podría estar moderadamente infravalorada</span>{_barra(35, "#15803d")}'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-top:4px">{chips}</div></div></div>')


CSS = """
.hr-wrap{width:100vw;margin-left:calc(50% - 50vw);margin-top:-64px;background:#fff;box-sizing:border-box;padding:clamp(24px,4vw,48px) clamp(16px,3vw,48px) 40px;display:flex;flex-wrap:wrap;align-items:center;gap:32px 40px;min-height:calc(100vh - 140px)}
.hr-izq{flex:1 1 360px;min-width:0;max-width:440px;display:flex;flex-direction:column;gap:16px}
.hr-h1{margin:0;padding:0;font-size:clamp(2.2rem,4.2vw,3.3rem);line-height:1.06;font-weight:800;color:#111827!important;letter-spacing:-.5px}
.hr-h1 .hr-v{color:#15803d}
.hr-izq p{margin:0;font-size:1.2rem;line-height:1.5;color:#374151}
a.hr-btn{display:flex;align-items:center;justify-content:center;background:#15803d;color:#fff!important;border-radius:14px;padding:14px 22px;font-size:1.25rem;font-weight:800;min-height:48px;box-sizing:border-box;text-decoration:none!important;max-width:340px;box-shadow:0 4px 14px rgba(21,128,61,.28)}
a.hr-btn:hover{filter:brightness(1.07)}
.hr-izq small{font-size:.9rem;color:#6b7280}
.hr-der{flex:1 1 560px;min-width:0;position:relative;padding-bottom:30px}
.hr-marco{background:linear-gradient(135deg,#e6f0ea,#f3f6fb);border:1px solid #d5dde6;border-radius:18px;padding:16px;box-shadow:0 20px 50px rgba(15,23,42,.18);display:flex;flex-direction:column;gap:12px}
.hr-tres{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.hr-tabla{background:#fff;border:1px solid #e3e8ee;border-radius:12px;overflow:hidden;margin-left:196px}
.hr-fila{display:grid;grid-template-columns:1.5fr 1.7fr 56px 60px;gap:10px;align-items:center;padding:9px 12px;border-top:1px solid #eef1f5}
.hr-th{background:#111827;color:#fff;font-size:11px;font-weight:700;border-top:0}
.hr-cel{position:absolute;left:-24px;bottom:-14px}
.hr-tel{width:190px;border:7px solid #111827;border-radius:28px;background:#fff;padding:14px 12px 16px;box-shadow:0 18px 40px rgba(15,23,42,.30);display:flex;flex-direction:column;gap:9px;align-items:center;box-sizing:content-box}
@media (max-width:980px){
 .hr-wrap{min-height:0;padding-bottom:0}
 .hr-izq{max-width:none;flex-basis:100%}
 .hr-der{flex-basis:100%;padding:22px 0;margin:0 calc(-1 * clamp(16px,3vw,48px));background:linear-gradient(135deg,#e6f0ea,#f3f6fb);display:flex;justify-content:center}
 .hr-marco{display:none}
 .hr-cel{position:static}
 .hr-tel{width:230px}
 a.hr-btn{max-width:none}
}
"""


def hero_html():
    return (f"<style>{CSS}</style>"
            f'<div class="hr-wrap"><div class="hr-izq"><div class="hr-h1" role="heading" aria-level="1">{html.escape(TITULO_1)}<br><span class="hr-v">{html.escape(TITULO_2)}</span></div>'
            f"<p>{html.escape(TEXTO)}</p>"
            f'<a class="hr-btn" href="?inicio=0" target="_self">{html.escape(BOTON)}</a><small>{html.escape(AVISO)}</small></div>'
            f'<div class="hr-der">{_marco()}{_celular()}</div></div>')
