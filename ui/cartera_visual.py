"""Pantalla de "Evaluá tu Cartera" (v1.2.76; v1.5.3: estilo igual al del resto del sitio): tarjetas con tortas y los ajustes numerados.
Toma los resultados de ui/cartera.py (los mismos que usa el informe PDF) y solo se ocupa de cómo se ve. No muestra las carteras de referencia."""
import html
import re

from data import carteras_modelo as CM
from ui.cartera import AVISO_CARTERA, CLASES, despedida, saludo, LIQ_MAX, LIQ_MIN, comparar, devolucion, nivel

COL_CLASE = {"rv": "#2563eb", "rf": "#7c3aed", "efectivo": "#14b8a6", "oro": "#f59e0b", "cripto": "#ec4899", "otros": "#94a3b8"}
COL_GEO = {"usa": "#2563eb", "desarrollados": "#0ea5e9", "emergentes": "#f97316", "fuera_sd": "#8b5cf6", "global": "#14b8a6", "sin": "#cbd5e1"}
NOM_GEO = {"usa": "Estados Unidos", "desarrollados": "Otros desarrollados", "emergentes": "Emergentes", "fuera_sd": "Fuera de EE.UU. (sin detalle)", "global": "Global (mezcla)", "sin": "Sin ubicar"}
COL_SUP = {"defensivo": "#16a34a", "sensible": "#2563eb", "ciclico": "#f59e0b"}
NOM_SUP = {"defensivo": "Defensivo", "sensible": "Sensible", "ciclico": "Cíclico"}
COL_GICS = ["#2563eb", "#16a34a", "#f59e0b", "#ec4899", "#14b8a6", "#7c3aed", "#f97316", "#0ea5e9", "#84cc16", "#e11d48", "#64748b"]
ICONO = {"ok": "✓", "warn": "!", "info": "i"}

CSS = """
.cv{font-family:inherit;color:#1f2937;margin:0 0 6px}
.cv-c{background:#fff;border:1px solid #e3e8ee;border-radius:14px;padding:16px 22px 14px;margin:0 0 14px}
.cv-h{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding:0 0 10px;border-bottom:1px solid #eef1f4}
.cv-h h3{margin:0;font-size:1.18rem;font-weight:700;color:#111827}
.cv-h small{margin-left:auto;color:#64748b;font-size:.8rem}
.cv-top{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
.cv-donut{width:170px;height:170px;border-radius:50%;position:relative;flex:none}
.cv-donut::after{content:"";position:absolute;inset:34px;background:#fff;border-radius:50%;box-shadow:inset 0 0 0 1px #eef1f5}
.cv-donut b{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:2;font-size:1.5rem;color:#0f172a;line-height:1.1}
.cv-donut b small{font-size:.7rem;font-weight:600;color:#64748b}
.cv-lg{flex:1 1 240px;display:grid;grid-template-columns:1fr auto;gap:7px 14px;align-items:center;font-size:.95rem}
.cv-lg i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:8px;vertical-align:-1px}
.cv-lg b{text-align:right;color:#0f172a}
.cv-k{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.cv-kp{flex:1 1 130px;background:#f8fafc;border:1px solid #eef1f5;border-radius:12px;padding:8px 12px}
.cv-kp b{display:block;font-size:1.15rem;color:#0f172a}.cv-kp span{font-size:.76rem;color:#64748b}
.cv-row{display:grid;grid-template-columns:170px 1fr 190px;gap:6px 12px;align-items:center;margin:0 0 9px;font-size:.93rem}
.cv-bar{height:12px;background:#eef1f5;border-radius:7px;overflow:hidden}.cv-bar i{display:block;height:100%;border-radius:7px}
.cv-chip{font-size:.76rem;font-weight:700;border-radius:999px;padding:3px 10px;white-space:nowrap}
.cv-chip.ok{background:#dcfce7;color:#166534}.cv-chip.mas{background:#ffedd5;color:#9a3412}.cv-chip.menos{background:#dbeafe;color:#1e40af}
.cv-st{display:flex;height:26px;border-radius:9px;overflow:hidden;background:#eef1f5;margin:4px 0 10px}
.cv-st i{display:flex;align-items:center;justify-content:center;color:#fff;font-size:.72rem;font-weight:700;font-style:normal;min-width:0;overflow:hidden;white-space:nowrap}
.cv-lg2{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.85rem;color:#475569;margin:0 0 6px}.cv-lg2 i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
.cv-n{list-style:none;margin:10px 0 0;padding:0}
.cv-n li{display:flex;gap:10px;align-items:flex-start;padding:9px 12px;border-radius:12px;margin:0 0 7px;font-size:.93rem;line-height:1.5;background:#f8fafc}
.cv-n li.warn{background:#fff7ed}.cv-n li.ok{background:#f0fdf4}
.cv-b{flex:none;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:800;color:#fff;margin-top:1px;background:#64748b}
.warn .cv-b{background:#f97316}.ok .cv-b{background:#16a34a}
.cv-sec{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 6px}.cv-sec span{background:#f1f5f9;border-radius:8px;padding:3px 9px;font-size:.8rem;color:#334155}.cv-sec b{color:#0f172a}
.cv-con{font-size:1rem;line-height:1.6;margin:0 0 12px;color:#0f172a}
.cv-pasos{list-style:none;margin:0;padding:0;counter-reset:p}
.cv-pasos li{display:flex;gap:10px;align-items:flex-start;margin:0 0 9px;font-size:.97rem;line-height:1.6}
.cv-pasos li span{flex:none;font-weight:700;color:#111827}
.cv-ul{margin:0 0 10px 1.2em;padding:0}.cv-ul li{margin:0 0 6px;font-size:.97rem;line-height:1.6;text-align:justify}
.cv-ay{font-weight:700;color:#111827;margin:0 0 8px}
.cv-bd{flex:1 1 300px}.cv-bt{font-weight:800;color:#334155;font-size:.92rem;margin:0 0 8px}.cv-bd .cv-donut{width:130px;height:130px}.cv-bd .cv-donut::after{inset:28px}.cv-bd .cv-lg{font-size:.88rem;flex:1 1 140px}
.cv-dos{display:flex;gap:22px;flex-wrap:wrap}
.cv-av{background:#f8fafc;border:1px solid #e5e9f0;border-radius:12px;padding:10px 14px;color:#64748b;font-size:.8rem;line-height:1.5;margin:4px 0 8px;text-align:justify}.cv-av p{margin:0 0 6px}
.cv-p{text-align:justify;line-height:1.68;margin:0 0 13px;font-size:.97rem;color:#1f2937}.cv-p:last-child{margin-bottom:2px}.cv-hl{font-weight:700}.cv-dos{justify-content:center}.cv-dos .cv-bd{flex:0 1 430px}.cv-dos .cv-bt{text-align:center}.cv-dos .cv-top{justify-content:center}.cv-c .cv-dos{margin:4px 0 16px}.cv-sal{font-size:.98rem;line-height:1.6;color:#0f172a;margin:0 0 6px;text-align:justify}.cv-n li>div,.cv-con,.cv-pasos li>div,.cv-intro{text-align:justify}.cv-ayuda{text-align:justify}
@media (max-width:640px){.cv-row{grid-template-columns:1fr auto}.cv-row .cv-bar{grid-column:1 / -1;order:3}.cv-row{grid-template-columns:1fr auto}.cv-donut{margin:0 auto}.cv-c{padding:16px 14px}}
"""


CSS_ENTRADA = """
.cv-intro{background:#fff7fa;border:1px solid #fbd5e1;border-radius:14px;padding:16px 18px;color:#334155;line-height:1.6;font-size:1rem;margin:6px 0 12px}
/* barra naranja de punta a punta (v1.2.77; v1.2.79: es un link a la pantalla de la cartera) */
.st-key-caja_cart{margin:2px 0 0}
.st-key-caja_cart a.cr-barra{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:50px;padding:6px 1.1rem;border-radius:14px;text-decoration:none!important;
background:linear-gradient(90deg,#e8668f 0%,#f4909f 100%);box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(190,60,100,.22);color:#fff!important;text-shadow:0 1px 2px rgba(120,20,60,.35);font-weight:800;font-size:1.04rem;line-height:1.3}
.st-key-caja_cart a.cr-barra:hover{filter:brightness(1.04) saturate(1.1)}
.st-key-caja_cart a.cr-barra b{font-size:1.3rem;flex:none}
/* tarjetas de entrada de datos */
.st-key-cr_p1{background:linear-gradient(180deg,#fff7fa 0%,#fff 60%);border:1px solid #fbd5e1;border-radius:16px;padding:14px 18px 12px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.cv-paso{display:flex;align-items:center;gap:10px;font-weight:800;font-size:1.02rem;color:#0f172a;margin:0 0 6px}
.cv-paso span{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#e8668f,#f4909f);color:#fff;display:flex;align-items:center;justify-content:center;font-size:.9rem}
.cv-ayuda{color:#64748b;font-size:.86rem;line-height:1.45;margin:2px 0 8px}
.cv-cols{display:inline-block;background:#fff1f5;border:1px solid #fbcfe0;color:#9d174d;border-radius:8px;padding:1px 8px;font-weight:700;font-size:.82rem;margin:0 2px}
.st-key-cr_p1 [data-testid="stFileUploaderDropzone"]{border:2px dashed #f4909f;background:#fff7fa;border-radius:14px}
.st-key-cr_p1 [data-testid="stFileUploaderDropzone"]:hover{background:#ffeaf1}
.st-key-cr_p1 [data-testid="stNumberInput"] input{font-size:1.1rem;font-weight:700}
.st-key-cr_p1 [data-testid="stNumberInput"] input::placeholder{font-weight:400;opacity:.6}
@media (max-width:640px){.st-key-cr_p1{padding:12px 12px 10px}}
"""


def _md(t):
    """**negrita**, ==dato destacado== (también negrita, en negro) y __cursiva__ (las «Notas» teóricas)."""
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(t).replace(" %", "\u00a0%"), quote=False))
    t = re.sub(r"==(.+?)==", r"<b>\1</b>", t)
    return re.sub(r"__(.+?)__", r"<i>\1</i>", t)


def _ajuste(x):
    """Un ajuste de las conclusiones: la idea en negrita y el «Por qué:» hasta el final en cursiva."""
    if " **Por qué:** " in x:
        a, b = x.split(" **Por qué:** ", 1)
        return f"<b>{_md(a)}</b> <i>Por qué: {_md(b)}</i>"
    return _md(x)


def _card(titulo, cuerpo, pie=""):
    return (f'<div class="cv-c"><div class="cv-h"><h3>{html.escape(titulo)}</h3>'
            f'{f"<small>{pie}</small>" if pie else ""}</div>{cuerpo}</div>')


def _may(x):
    """Primera letra en mayúscula (v1.2.78: las listas con puntitos empiezan siempre con mayúscula)."""
    t = str(x or "")
    i = 2 if t.startswith("**") else 0
    return t[:i] + t[i:i + 1].upper() + t[i + 1:]


def _lista(frases):
    li = "".join(f'<li class="{nivel(x)}"><span class="cv-b">{ICONO[nivel(x)]}</span><div>{_md(_may(x))}</div></li>' for x in frases)
    return f'<ul class="cv-n">{li}</ul>' if li else ""


def _tramos(items):
    """Tramos del gráfico (conic-gradient). Una porción chica (por ejemplo 1 %) se dibuja con un mínimo para que se vea; la leyenda lleva el número real."""
    tot = sum(v for _, v, _ in items) or 1
    vis = [max(v / tot, 0.03) for _, v, _ in items]
    sv = sum(vis)
    ini, tramos = 0.0, []
    for (_, _, c), x in zip(items, vis):
        fin = ini + x / sv * 100
        tramos.append(f"{c} {ini:.2f}% {fin:.2f}%")
        ini = fin
    return tramos


def _bloque(items, vacio="Sin datos para graficar"):
    """Torta con leyenda, sin título ni texto en el centro. items: [(nombre, %, color)]."""
    items = [(n, v, c) for n, v, c in items if v >= 0.5]
    tot = sum(v for _, v, _ in items) or 1
    if items:
        tramos = _tramos(items)
        leyenda = "".join(f'<div><i style="background:{c}"></i>{html.escape(n)}</div><b>{v / tot * 100:.0f} %</b>' for n, v, c in items)
    else:
        tramos, leyenda = ["#e5e9f0 0% 100%"], f"<div>{vacio}</div><b></b>"
    return (f'<div class="cv-dos"><div class="cv-bd"><div class="cv-top"><div class="cv-donut" style="background:conic-gradient({", ".join(tramos)})"></div>'
            f'<div class="cv-lg">{leyenda}</div></div></div></div>')


def _bloque_donut(peso, con_liquidez=True):
    items = [(CLASES[k], peso[k], COL_CLASE[k]) for k in ("rv", "rf", "efectivo", "oro", "cripto", "otros") if peso.get(k, 0) >= 0.05 and (con_liquidez or k != "efectivo")]
    return _bloque([(n, max(v, 0.5), c) for n, v, c in items], "Sin inversiones cargadas en estos grupos")


def aviso_html():
    """Aviso Legal de la devolución (texto de Guille). Es el único aviso: no va el aviso largo del sitio."""
    return '<div class="cv-av"><p><b>Aviso Legal:</b> ' + html.escape(AVISO_CARTERA[0]) + "</p></div>"


def _barra_apilada(partes):
    """partes: [(nombre, %, color)]; barra apilada con la leyenda abajo."""
    partes = [(n, v, c) for n, v, c in partes if v >= 0.5]
    segs = "".join(f'<i style="width:{v:.2f}%;background:{c}" title="{html.escape(n)} {v:.0f} %">{f"{v:.0f}%" if v >= 7 else ""}</i>' for n, v, c in partes)
    lg = "".join(f'<span><i style="background:{c}"></i>{html.escape(n)} <b>{v:.0f} %</b></span>' for n, v, c in partes)
    return f'<div class="cv-st">{segs}</div><div class="cv-lg2">{lg}</div>'


def _chip(d, umbral=5.0):
    if d > umbral:
        return f'<span class="cv-chip mas">Te pasás {abs(d):.0f} pts</span>'
    if d < -umbral:
        return f'<span class="cv-chip menos">Te faltan {abs(d):.0f} pts</span>'
    return '<span class="cv-chip ok">En línea</span>'


def _parrafos(frases):
    return "".join(f'<p class="cv-p">{_md(x)}</p>' for x in frases)


def _cuerpo(frases):
    """Párrafos, y las listas con guion (- ) como viñetas."""
    out, ul = [], []
    for x in frases:
        if x.startswith("- "):
            ul.append(f"<li>{_md(x[2:])}</li>")
            continue
        if ul:
            out.append(f'<ul class="cv-ul">{"".join(ul)}</ul>')
            ul = []
        out.append(f'<p class="cv-p">{_md(x)}</p>')
    if ul:
        out.append(f'<ul class="cv-ul">{"".join(ul)}</ul>')
    return "".join(out)


def visual_html(res, edad, perfil, nombre="", fecha="", previa=None):
    """HTML de toda la evaluación. v1.5.3: mismo estilo que el resto del sitio (tarjetas blancas, sin íconos ni colores de tarjeta), tortas sin título ni texto adentro,
    notas teóricas en cursiva, dos tortas en lo sectorial (supersectores y sectores GICS) y «Lo que no tocaríamos» antes de los ajustes."""
    if not res or not res.get("total"):
        return ""
    secs = devolucion(res, edad, perfil, nombre)
    sec = dict(secs)
    pe = res["peso"]
    pi = res.get("peso_inv") or pe
    ef = res.get("efectivo_propio")
    out = []
    s1, s2 = saludo(nombre, edad, perfil)
    out.append(_card("Evaluación de tu Portfolio", f'<p class="cv-p"><b>{html.escape(s1)}</b></p><p class="cv-p">{html.escape(s2)}</p>' + _cuerpo(sec.get("Objetivo como inversor", [])),
                     pie=html.escape(str(fecha))))
    out.append(_card("Estructura de tu Cartera", _bloque_donut(pi, con_liquidez=bool(ef)) + _cuerpo(sec["Estructura de tu cartera"])))
    g = res.get("geo")
    cuerpo = ""
    if g:
        partes = [(NOM_GEO[k], g[k], COL_GEO[k]) for k in ("usa", "desarrollados", "emergentes", "fuera_sd", "global")]
        partes.append((NOM_GEO["sin"], max(0.0, 100 - sum(v for _, v, _ in partes)), COL_GEO["sin"]))
        cuerpo = _bloque(partes)
    out.append(_card("Diversificación Geográfica", cuerpo + _cuerpo(sec["Diversificación geográfica"])))
    sp = res.get("super")
    c1 = _bloque([(NOM_SUP[k], sp[k], COL_SUP[k]) for k in ("defensivo", "sensible", "ciclico")]) if sp else ""
    gi = res.get("sectores_gics") or []
    c2 = _bloque([(n, v, COL_GICS[i % len(COL_GICS)]) for i, (n, v) in enumerate(gi)]) if (sp and gi) else ""
    out.append(_card("Diversificación Sectorial", c1 + _cuerpo(sec["Diversificación sectorial"]) + c2 + _cuerpo(sec.get("Diversificación sectorial (detalle GICS)", []))))
    out.append(_card("Liquidez", _cuerpo(sec["Liquidez"])))
    if "Sensibilidad al mercado (beta)" in sec:
        out.append(_card("Sensibilidad al mercado (beta)", _cuerpo(sec["Sensibilidad al mercado (beta)"])))
    comp = comparar(previa, res) if previa else []
    if comp:
        out.append(_card("Comparación con tu evaluación anterior", _cuerpo(comp)))
    fr = sec["Conclusiones finales"]
    cuerpo = _cuerpo([fr[0]])
    i, n_ = 1, 0
    while i < len(fr):
        x = fr[i]
        if x.startswith("##"):
            cuerpo += f'<div class="cv-ay" style="margin:14px 0 8px">{_md(x.lstrip("#"))}</div>'
            i += 1
        elif x.startswith("- "):
            j = i
            while j < len(fr) and fr[j].startswith("- "):
                j += 1
            cuerpo += _cuerpo(fr[i:j])
            i = j
        elif re.match(r"^\d+\. ", x):
            j = i
            lis = ""
            while j < len(fr) and re.match(r"^\d+\. ", fr[j]):
                n_ += 1
                lis += f"<li><span>{n_}.</span><div>{_ajuste(re.sub(r'^\d+\. ', '', fr[j]))}</div></li>"
                j += 1
            cuerpo += f'<ol class="cv-pasos">{lis}</ol>'
            i = j
        else:
            cuerpo += _cuerpo([x])
            i += 1
    d1, d2 = despedida(nombre)
    cuerpo += f'<p class="cv-p" style="margin-top:14px">{html.escape(d1)}</p><p class="cv-p"><b>{html.escape(d2)}</b></p>'
    out.append(_card("Conclusiones Finales", cuerpo))
    out.append(aviso_html())
    return f'<div class="cv">{"".join(out)}</div>'
