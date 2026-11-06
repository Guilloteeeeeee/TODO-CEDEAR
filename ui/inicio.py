"""Pantalla de inicio (v1.5.7), según la maqueta aprobada por Guille: una frase fuerte, un solo botón («Comenzar») y una vista previa de la app (tortas, tabla con valoración y la
ficha de una empresa en un celular). Sin otros links. «Comenzar» lleva a la tabla de empresas (?inicio=0).
v1.5.9/1.5.10: la vista previa va un poco desenfocada y es una FOTO FIJA de la app (FOTO, abajo): empresas reales con los datos de la app del 02/11/2026, congelados a propósito.
No se actualiza sola ni lee el caché al entrar (el uso de verdad está adentro de la app); se cambia a mano cuando se arme el score nuevo."""
import html

TITULO_1 = "No compres CEDEARs a ciegas."
TITULO_2 = "Conocelos antes de invertir."
TEXTO = "Todos los CEDEARs de Acciones y ETFs en un solo lugar. Análisis de empresas y filtros para saber cuáles están baratas."
TEXTO_NEGRITA = "Todo Gratuito!"
BOTON = "Comenzar"

AZ, CE, NA, VE, MO = "#2563eb", "#0ea5e9", "#f59e0b", "#15803d", "#7c3aed"


def _torta(partes, size=84, hueco=54):
    acc, tramos = 0, []
    for col, p in partes:
        tramos.append(f"{col} {acc}% {acc + p}%")
        acc += p
    m = f"radial-gradient(circle,transparent {hueco}%,#000 {hueco + 1}%)"
    return (f'<span class="hr-tt" style="display:block;width:{size}px;height:{size}px;border-radius:50%;flex:none;background:conic-gradient({",".join(tramos)});'
            f'-webkit-mask:{m};mask:{m}"></span>')


def _leyenda(items):
    return ('<div class="hr-ley" style="display:flex;flex-direction:column;gap:4px;font-size:12px;color:#374151">'
            + "".join(f'<span style="display:flex;align-items:center;gap:6px"><i style="width:9px;height:9px;border-radius:50%;background:{c};display:block"></i>{html.escape(t)}</span>'
                      for c, t in items) + "</div>")


def _tarjeta(titulo, partes, items):
    return ('<div class="hr-tj" style="background:#fff;border:1px solid #e3e8ee;border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:10px">'
            f'<span style="font-size:14px;font-weight:700;color:#111827">{html.escape(titulo)}</span>'
            f'<div class="hr-tr" style="display:flex;align-items:center;gap:12px">{_torta(partes)}{_leyenda(items)}</div></div>')


def _barra(pos, col):
    return (f'<span class="hr-bar" style="display:block;position:relative;height:6px;border-radius:3px;background:#e5e7eb;width:120px">'
            f'<i style="position:absolute;left:{pos}%;top:-3px;width:12px;height:12px;border-radius:50%;background:{col};display:block;margin-left:-6px"></i></span>')


def _score(n, col):
    return (f'<span style="display:inline-flex;flex-direction:column;align-items:center;border:2px solid {col};border-radius:8px;overflow:hidden;width:40px">'
            f'<b style="font-size:16px;line-height:26px;color:#111827">{n}</b><i style="font-style:normal;background:{col};color:#fff;font-size:9px;width:100%;text-align:center;line-height:12px">SCORE</i></span>')


# Foto fija del 02/11/2026 (datos de la app: nombre, sector, valoración con su barra, score y dividendo). Los colores ya están oscurecidos para que se lean sobre blanco.
FOTO = [
    {"nombre": "Microsoft Corporation", "sub": "MSFT · Software y nube", "pos": 28.5, "col": "#10632f", "txt": "Podría estar significativamente infravalorada", "sc": 71, "dy": "0,8 %"},
    {"nombre": "Alphabet Inc.", "sub": "GOOGL · Comunicación", "pos": 44.1, "col": "#b68b06", "txt": "Podría estar razonablemente valuada", "sc": 53, "dy": "0,3 %"},
    {"nombre": "The Coca-Cola Company", "sub": "KO · Consumo Básico", "pos": 64.2, "col": "#c25911", "txt": "Podría estar moderadamente sobrevalorada", "sc": 36, "dy": "2,2 %"},
]


def _fila(nom, tk, pos, col, txt, sc, dy):
    return ('<div class="hr-fila">'
            f'<span style="display:flex;flex-direction:column"><b style="font-size:13px;color:#111827">{nom}</b><small style="color:#6b7280;font-size:11px">{tk}</small></span>'
            f'<span style="display:flex;flex-direction:column;gap:6px"><small style="color:{col};font-weight:700;font-size:11px">{txt}</small>{_barra(pos, col)}</span>'
            f'{_score(sc, col)}<b style="font-size:13px;color:#111827;text-align:right">{dy}</b></div>')


def _marco(filas):
    tarjetas = ('<div class="hr-tres">'
                + _tarjeta("Estructura", [(AZ, 50), (CE, 40), (NA, 10)], [(AZ, "Renta Variable"), (CE, "Renta Fija"), (NA, "Oro")])
                + _tarjeta("Geografía", [(AZ, 75), (CE, 20), (MO, 5)], [(AZ, "EE.UU."), (CE, "Desarrollados"), (MO, "Emergentes")])
                + _tarjeta("Supersectores", [(CE, 30), (AZ, 20), (VE, 50)], [(VE, "Defensivo"), (CE, "Sensible"), (AZ, "Cíclico")]) + "</div>")
    tabla = ('<div class="hr-tabla"><div class="hr-fila hr-th"><span>Empresa</span><span>Valoración</span><span>Score</span><span style="text-align:right">Dividendo</span></div>'
             + "".join(_fila(html.escape(f["nombre"]), html.escape(f["sub"]), f["pos"], f["col"], html.escape(f["txt"]), f["sc"], f["dy"]) for f in filas) + "</div>")
    return ('<div class="hr-marco"><div style="text-align:center;font-size:20px;font-weight:700;color:#111827">Evaluá tu Portfolio</div>' + tarjetas
            + '<div style="text-align:center;font-size:15px;font-weight:700;color:#111827;margin-top:4px">Empresas con su valoración</div>' + tabla + "</div>")


def _celular(f):
    chips = "".join(f'<span style="border:1px solid #e3e8ee;border-radius:999px;padding:3px 8px;font-size:10px;color:#374151">{t}</span>' for t in ("Resumen", "Análisis Fundamental", "Valuación"))
    return ('<div class="hr-cel"><div class="hr-tel">'
            '<span style="width:46px;height:5px;border-radius:3px;background:#d1d5db;display:block"></span>'
            f'<b style="font-size:17px;color:#111827;text-align:center">{html.escape(f["nombre"])}</b><small style="color:#6b7280;font-size:11px;margin-top:-6px;text-align:center">{html.escape(f["sub"])}</small>'
            f'<div style="display:flex;gap:14px;align-items:center">{_score(f["sc"], f["col"])}<span style="display:flex;flex-direction:column"><small style="color:#6b7280;font-size:10px">Dividendo</small><b style="font-size:15px">{f["dy"]}</b></span></div>'
            f'<span style="color:{f["col"]};font-weight:700;font-size:11px;text-align:center">{html.escape(f["txt"])}</span>{_barra(f["pos"], f["col"])}'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-top:4px">{chips}</div></div></div>')


CSS = """
.hr-wrap{width:100vw;margin-left:calc(50% - 50vw);margin-top:-64px;background:#fff;box-sizing:border-box;padding:clamp(24px,4vw,48px) clamp(16px,3vw,48px) 40px;display:flex;flex-wrap:wrap;align-items:center;gap:32px 40px;min-height:calc(100vh - 140px)}
.hr-izq{flex:1 1 360px;min-width:0;max-width:440px;display:flex;flex-direction:column;gap:16px}
.hr-h1{margin:0;padding:0;font-size:clamp(2.2rem,4.2vw,3.3rem);line-height:1.06;font-weight:800;color:#111827!important;letter-spacing:-.5px}
.hr-h1 .hr-v{color:#15803d}
.hr-izq p{text-align:justify;margin:0;font-size:1.2rem;line-height:1.5;color:#374151}
a.hr-btn{display:flex;align-items:center;justify-content:center;background:#15803d;color:#fff!important;border-radius:14px;padding:14px 22px;font-size:1.25rem;font-weight:800;min-height:48px;box-sizing:border-box;text-decoration:none!important;max-width:340px;box-shadow:0 4px 14px rgba(21,128,61,.28)}
a.hr-btn:hover{filter:brightness(1.07)}
.hr-der{flex:1 1 560px;min-width:0;position:relative;padding-bottom:30px}
.hr-marco,.hr-cel{filter:blur(1.8px);opacity:.92;pointer-events:none;user-select:none;-webkit-user-select:none}
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
 .hr-der{flex-basis:100%;padding:22px 14px 26px;margin:0 calc(-1 * clamp(16px,3vw,48px));background:linear-gradient(135deg,#e6f0ea,#f3f6fb);display:flex;flex-direction:column;align-items:center;gap:0;box-sizing:border-box}
 .hr-marco{display:flex;width:100%;box-sizing:border-box;padding:10px;gap:10px;border-radius:16px}
 .hr-marco>div:first-child{font-size:17px!important}
 .hr-tres{gap:6px}
 .hr-tj{padding:9px 6px!important;gap:6px!important;align-items:center}
 .hr-tj>span{font-size:12px!important}
 .hr-tr{flex-direction:column!important;gap:6px!important}
 .hr-tt{width:58px!important;height:58px!important}
 .hr-ley{font-size:9.5px!important;gap:2px!important}
 .hr-ley span{align-items:center;gap:4px!important}
 .hr-tabla{margin-left:0}
 .hr-fila{grid-template-columns:minmax(0,1.15fr) minmax(0,1.25fr) 42px;gap:8px;padding:8px 9px}
 .hr-fila>:nth-child(4){display:none}
 .hr-fila b{font-size:12px!important}
 .hr-fila small{font-size:9.5px!important;line-height:1.25}
 .hr-bar{width:100%!important}
 .hr-cel{position:static;margin-top:-26px;align-self:flex-start;margin-left:6px}
 .hr-tel{width:150px;padding:11px 10px 13px;gap:7px;border-width:6px;border-radius:24px}
 a.hr-btn{max-width:none}
}
"""


def hero_html():
    filas = FOTO
    return (f"<style>{CSS}</style>"
            f'<div class="hr-wrap"><div class="hr-izq"><div class="hr-h1" role="heading" aria-level="1">{html.escape(TITULO_1)}<br><span class="hr-v">{html.escape(TITULO_2)}</span></div>'
            f"<p>{html.escape(TEXTO)} <b>{html.escape(TEXTO_NEGRITA)}</b></p>"
            f'<a class="hr-btn" href="?inicio=0" target="_self">{html.escape(BOTON)}</a></div>'
            f'<div class="hr-der" aria-hidden="true">{_marco(filas)}{_celular(filas[0])}</div></div>')
