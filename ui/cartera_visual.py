"""Pantalla de "Evaluá tu Cartera" (v1.2.76): tarjetas con gráfico de torta, barras de colores, indicadores y los ajustes en pasos numerados.
Toma los resultados de ui/cartera.py (los mismos que usa el informe PDF) y solo se ocupa de cómo se ve. No muestra las carteras de referencia."""
import html
import re

from ui.cartera import CLASES, devolucion, nivel

COL_CLASE = {"rv": "#2563eb", "rf": "#7c3aed", "efectivo": "#14b8a6", "oro": "#f59e0b", "cripto": "#ec4899", "otros": "#94a3b8"}
COL_GEO = {"usa": "#2563eb", "desarrollados": "#0ea5e9", "emergentes": "#f97316", "fuera_sd": "#8b5cf6", "global": "#14b8a6", "sin": "#cbd5e1"}
NOM_GEO = {"usa": "Estados Unidos", "desarrollados": "Otros desarrollados", "emergentes": "Emergentes", "fuera_sd": "Fuera de EE.UU. (sin detalle)", "global": "Global (mezcla)", "sin": "Sin ubicar"}
COL_SUP = {"defensivo": "#16a34a", "sensible": "#2563eb", "ciclico": "#f59e0b"}
NOM_SUP = {"defensivo": "Defensivas", "sensible": "Sensibles", "ciclico": "Cíclicas"}
ICONO = {"ok": "✓", "warn": "!", "info": "i"}

CSS = """
.cv{font-family:inherit;color:#1f2937;margin:0 0 6px}
.cv-c{background:#fff;border-radius:18px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 8px 24px rgba(15,23,42,.08);padding:18px 22px 16px;margin:0 0 16px;position:relative;overflow:hidden}
.cv-c::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--ac,#2563eb)}
.cv-h{display:flex;align-items:center;gap:10px;margin:0 0 12px}
.cv-ic{width:34px;height:34px;border-radius:10px;background:var(--bg,#eff6ff);display:flex;align-items:center;justify-content:center;font-size:18px}
.cv-h h3{margin:0;font-size:1.12rem;font-weight:800;color:#0f172a;letter-spacing:.1px}
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
.cv-fin{background:linear-gradient(135deg,#f0fdf4 0%,#ecfeff 100%)}
.cv-con{font-size:1rem;line-height:1.6;margin:0 0 12px;color:#0f172a}
.cv-pasos{list-style:none;margin:0;padding:0;counter-reset:p}
.cv-pasos li{display:flex;gap:12px;align-items:flex-start;margin:0 0 9px;font-size:.96rem;line-height:1.5;background:#fff;border-radius:12px;padding:10px 14px;box-shadow:0 1px 2px rgba(15,23,42,.06)}
.cv-pasos li span{flex:none;width:26px;height:26px;border-radius:50%;background:#16a34a;color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:.85rem}
.cv-ay{font-weight:800;color:#166534;margin:0 0 8px}
@media (max-width:640px){.cv-row{grid-template-columns:1fr auto}.cv-row .cv-bar{grid-column:1 / -1;order:3}.cv-row{grid-template-columns:1fr auto}.cv-donut{margin:0 auto}.cv-c{padding:16px 14px}}
"""


CSS_ENTRADA = """
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
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(t), quote=False))


def _card(icono, titulo, cuerpo, ac="#2563eb", bg="#eff6ff", extra_cls="", pie=""):
    return (f'<div class="cv-c {extra_cls}" style="--ac:{ac};--bg:{bg}"><div class="cv-h"><div class="cv-ic">{icono}</div><h3>{html.escape(titulo)}</h3>'
            f'{f"<small>{pie}</small>" if pie else ""}</div>{cuerpo}</div>')


def _may(x):
    """Primera letra en mayúscula (v1.2.78: las listas con puntitos empiezan siempre con mayúscula)."""
    t = str(x or "")
    i = 2 if t.startswith("**") else 0
    return t[:i] + t[i:i + 1].upper() + t[i + 1:]


def _lista(frases):
    li = "".join(f'<li class="{nivel(x)}"><span class="cv-b">{ICONO[nivel(x)]}</span><div>{_md(_may(x))}</div></li>' for x in frases)
    return f'<ul class="cv-n">{li}</ul>' if li else ""


def _donut(peso):
    items = [(k, peso[k]) for k in ("rv", "rf", "efectivo", "oro", "cripto", "otros") if peso.get(k, 0) >= 0.05]
    tot = sum(v for _, v in items) or 1
    ini, tramos = 0.0, []
    for k, v in items:
        fin = ini + v / tot * 100
        tramos.append(f"{COL_CLASE[k]} {ini:.2f}% {fin:.2f}%")
        ini = fin
    leyenda = "".join(f'<div><i style="background:{COL_CLASE[k]}"></i>{html.escape(CLASES[k])}</div><b>{v:.0f} %</b>' for k, v in items)
    return tramos, leyenda


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


def visual_html(res, edad, perfil):
    """HTML de toda la evaluación (tarjetas)."""
    if not res or not res.get("total"):
        return ""
    sec = dict(devolucion(res, edad, perfil))
    pe, d = res["peso"], res["desvio"]
    ef = res.get("efectivo_propio")
    ps = res["posiciones"]
    out = []
    # --- 1. De un vistazo
    tramos, leyenda = _donut(pe)
    perf = f" · perfil {perfil.lower()}" if perfil and "perfil" in sec["Pesos"][0] else ""
    kp = (f'<div class="cv-k"><div class="cv-kp"><b>{html.escape(str(perfil)) if "perfil" in perf else "Perfil único"}</b><span>tu perfil</span></div><div class="cv-kp"><b>{len(ps)}</b><span>posiciones</span></div>'
          f'<div class="cv-kp"><b>{ps[0]["ticker"]} · {ps[0]["pct"]:.0f} %</b><span>mayor posición</span></div>'
          f'<div class="cv-kp"><b>{sum(p["pct"] for p in ps[:3]):.0f} %</b><span>en tus 3 mayores</span></div></div>')
    cuerpo = (f'<div class="cv-top"><div class="cv-donut" style="background:conic-gradient({", ".join(tramos)})"><b>{int(edad)}<small>años</small></b></div>'
              f'<div class="cv-lg">{leyenda}</div></div>{kp}')
    out.append(_card("🧭", "Tu cartera de un vistazo", cuerpo, "#2563eb", "#eff6ff", pie=f"{html.escape(res['rango'])}"))
    # --- 2. Pesos
    filas = []
    base = [("rv", "Renta variable"), ("rf", "Renta fija")] + ([("efectivo", "Efectivo y cauciones")] if ef else []) + [("oro", "Oro"), ("cripto", "Criptoactivos")]
    for k, nom in base:
        real = pe[k] + (pe["efectivo"] if (k == "rf" and not ef) else 0)
        if k == "rf" and not ef:
            nom = "Renta fija (con efectivo)"
        if real < 0.5 and abs(d.get(k, 0)) <= 5:
            continue
        filas.append(f'<div class="cv-row"><div>{nom}</div><div class="cv-bar"><i style="width:{min(100, real):.1f}%;background:{COL_CLASE[k]}"></i></div>'
                     f'<div><b>{real:.0f} %</b> {_chip(d.get(k, 0))}</div></div>')
    resto = [x for x in sec["Pesos"][1:] if not re.match(r"^\*\*.*(te pasás|te faltan)", x) and "estás en línea" not in x]
    out.append(_card("⚖️", "Pesos", "".join(filas) + _lista(resto), "#7c3aed", "#f5f3ff"))
    # --- 3. Geografía
    g = res.get("geo")
    if g:
        partes = [(NOM_GEO[k], g[k], COL_GEO[k]) for k in ("usa", "desarrollados", "emergentes", "fuera_sd", "global")]
        partes.append((NOM_GEO["sin"], max(0.0, 100 - sum(v for _, v, _ in partes)), COL_GEO["sin"]))
        cuerpo = _barra_apilada(partes) + _lista(sec["Diversificación geográfica"][1:])
    else:
        cuerpo = _lista(sec["Diversificación geográfica"])
    out.append(_card("🌎", "Diversificación geográfica", cuerpo, "#0ea5e9", "#f0f9ff", pie="sobre tu renta variable"))
    # --- 4. Sectores
    s = res.get("super")
    if s:
        cuerpo = _barra_apilada([(NOM_SUP[k], s[k], COL_SUP[k]) for k in ("defensivo", "sensible", "ciclico")])
        top = "".join(f'<span><b>{html.escape(n)}</b> {v:.0f} %</span>' for n, v in res.get("sectores", [])[:6])
        if top:
            cuerpo += f'<div class="cv-sec">{top}</div>'
        cuerpo += _lista(sec["Diversificación sectorial"][1:])
    else:
        cuerpo = _lista(sec["Diversificación sectorial"])
    out.append(_card("🏭", "Diversificación sectorial", cuerpo, "#f59e0b", "#fffbeb", pie="sobre tus empresas"))
    # --- 5. Conclusiones
    fr = sec["Conclusiones y qué ajustaría"]
    con = _md(fr[0].replace("**Conclusión:** ", ""))
    pasos = [re.sub(r"^\d+\. ", "", x) for x in fr[2:]] if len(fr) > 2 else []
    if pasos:
        lista = '<div class="cv-ay">Qué ajustaría, en este orden</div><ol class="cv-pasos">' + "".join(f"<li><span>{i}</span><div>{_md(x)}</div></li>" for i, x in enumerate(pasos, 1)) + "</ol>"
    else:
        lista = f'<div class="cv-ay">{_md(fr[1].replace("**", ""))}</div>' if len(fr) > 1 else ""
    out.append(_card("🎯", "Conclusiones y qué ajustaría", f'<p class="cv-con"><b>Conclusión.</b> {con}</p>{lista}', "#16a34a", "#f0fdf4", "cv-fin"))
    return f'<div class="cv">{"".join(out)}</div>'
