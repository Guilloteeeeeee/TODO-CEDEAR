"""Informe descargable de "Tu Cartera" (v1.2.74): PDF con el membrete de Finanzas para Médicos Argentina (logo, nombre y línea de color), la cartera tal como la cargó
la persona, la devolución y el aviso legal. Se arma en el momento, en memoria, y se baja al dispositivo: no se guarda en ningún servidor.
Usa reportlab (requirements.txt); si no estuviera disponible, `html_informe` da el mismo informe en una página que se puede imprimir como PDF."""
import datetime
import html
import io
import os
import re

from ui.cartera import AVISO_CARTERA, CLASES, despedida, devolucion, resumen_para_pdf, saludo

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(_RAIZ, "assets", "marca", "finanzas-para-medicos-128.png")
NOMBRE = "Finanzas para Médicos Argentina"
AUTORES = "Guillermo Di Palma AP 2372 y María Laura García"
TITULO = "Evaluación de tu Portfolio"


def _saludo(nombre):
    n = (nombre or "").strip()
    return f"Hola {n}" if n else "Hola, colega inversor"


def _fecha(f=None):
    return (f or datetime.date.today()).strftime("%d/%m/%Y")


def _filas_cartera(res):
    """[(ticker, clase en castellano, % de la cartera)] ordenadas de mayor a menor peso."""
    return [(p["ticker"], CLASES.get(p["clase"], p["clase"]), p["pct"]) for p in res.get("posiciones", [])]


def _md(t):
    """**negrita** -> <b>, con el resto escapado (para los párrafos de reportlab)."""
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(t).replace(" %", "\u00a0%"), quote=False))
    t = re.sub(r"==(.+?)==", r"<b>\1</b>", t)
    return re.sub(r"__(.+?)__", r"<i>\1</i>", t)


def _hex(c):
    from reportlab.lib import colors
    return colors.HexColor(c)


def _pie(items, tam, centro=""):
    """Torta tipo dona con los grandes grupos. items: [(valor, color)]."""
    from reportlab.graphics.charts.doughnut import Doughnut
    from reportlab.graphics.shapes import Drawing, String
    d = Drawing(tam, tam)
    if not items or sum(v for v, _ in items) <= 0:
        items = [(1, "#e5e9f0")]          # nada invertido (por ejemplo, solo liquidez): anillo gris
    g = Doughnut()
    g.x, g.y, g.width, g.height = 2, 2, tam - 4, tam - 4
    tot_ = sum(v for v, _ in items) or 1
    g.data = [max(v, 0.03 * tot_) for v, _ in items]      # una porción chica (1 %) se dibuja con un mínimo para que se vea
    for i, (_, c) in enumerate(items):
        g.slices[i].fillColor = _hex(c)
        g.slices[i].strokeColor = _hex("#ffffff")
        g.slices[i].strokeWidth = 1
    g.slices.strokeWidth = 1
    d.add(g)
    if centro:
        d.add(String(tam / 2, tam / 2 - 3, centro, fontName="Helvetica-Bold", fontSize=7, fillColor=_hex("#111827"), textAnchor="middle"))
    return d


def _leyenda(partes, ancho):
    """Leyenda con cuadradito de color; se acomoda en renglones. partes: [(texto, color)]."""
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.pdfbase.pdfmetrics import stringWidth
    x, y, filas = 0, 0, []
    for t, c in partes:
        w = 12 + stringWidth(t, "Helvetica", 8) + 12
        if x and x + w > ancho:
            x, y = 0, y - 13
        filas.append((x, y, t, c))
        x += w
    alto = -y + 13
    d = Drawing(ancho, alto)
    for x, y, t, c in filas:
        d.add(Rect(x, alto - 11 + y, 7, 7, fillColor=_hex(c), strokeColor=None))
        d.add(String(x + 11, alto - 11 + y, t, fontName="Helvetica", fontSize=8, fillColor=_hex("#334155")))
    return d


def _barra_apilada_pdf(partes, ancho):
    """partes: [(nombre, %, color)] -> barra apilada + leyenda."""
    from reportlab.graphics.shapes import Drawing, Rect, String
    partes = [(n, v, c) for n, v, c in partes if v >= 0.5]
    tot = sum(v for _, v, _ in partes) or 1
    d = Drawing(ancho, 14)
    x = 0
    for n, v, c in partes:
        w = ancho * v / tot
        d.add(Rect(x, 0, w, 14, fillColor=_hex(c), strokeColor=_hex("#ffffff"), strokeWidth=0.8))
        if v >= 8:
            d.add(String(x + w / 2, 4, f"{v:.0f}%", fontName="Helvetica-Bold", fontSize=8, fillColor=_hex("#ffffff"), textAnchor="middle"))
        x += w
    return [d, _leyenda([(f"{n} {v:.0f} %", c) for n, v, c in partes], ancho)]


def _barra_peso(valor, color, ancho):
    from reportlab.graphics.shapes import Drawing, Rect
    d = Drawing(ancho, 8)
    d.add(Rect(0, 0, ancho, 8, fillColor=_hex("#e5e9f0"), strokeColor=None))
    d.add(Rect(0, 0, ancho * min(max(valor, 0), 100) / 100, 8, fillColor=_hex(color), strokeColor=None))
    return d


def _chip_txt(d, umbral=5.0):
    if d > umbral:
        return f"te pasás {abs(d):.0f} pts"
    if d < -umbral:
        return f"te faltan {abs(d):.0f} pts"
    return "en línea"


def pdf_informe(res, edad, perfil, aviso="", hoy=None, nombre="", previa=None):
    """Bytes del PDF con la MISMA información que se ve en la app (saludo, tortas, barras, secciones, conclusiones y avisos) más el membrete con la fecha. Lanza ImportError si no está reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from data import carteras_modelo as CM
    from ui import cartera_visual as CV
    from ui.cartera import comparar, nivel

    azul, verde, gris = colors.HexColor("#1e3a8a"), colors.HexColor("#15803d"), colors.HexColor("#64748b")
    st = {
        "tit": ParagraphStyle("tit", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#111827")),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=gris),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=colors.HexColor("#111827"), spaceBefore=16, spaceAfter=3),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#1f2937"), alignment=4),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.6, leading=13.5, textColor=colors.HexColor("#1f2937"), leftIndent=11, firstLineIndent=-11, spaceAfter=3, alignment=4),
        "pq": ParagraphStyle("pq", fontName="Helvetica", fontSize=8, leading=11, textColor=gris, spaceAfter=3, alignment=4),
        "sm": ParagraphStyle("sm", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.HexColor("#111827"), spaceBefore=6, spaceAfter=4, keepWithNext=1),
        "marca": ParagraphStyle("marca", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#111827")),
    }
    colnivel = {"ok": "#16a34a", "warn": "#ea580c", "info": "#64748b"}
    buf = io.BytesIO()

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#e5e9f0"))
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(gris)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title=f"{TITULO} - {NOMBRE}", author=NOMBRE,
                            subject=resumen_para_pdf(res, edad, perfil, (hoy or datetime.date.today()).isoformat()))
    ancho = A4[0] - 36 * mm

    def seccion(titulo, cuerpo, junto=2):
        cuerpo = [c for c in cuerpo if c is not None]
        return [KeepTogether([Paragraph(html.escape(titulo), st["h"]), HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e3e8ee"), spaceAfter=8)] + cuerpo[:junto])] + cuerpo[junto:]

    sec = dict(devolucion(res, edad, perfil, nombre))
    pe, d = res["peso"], res["desvio"]
    pi = res.get("peso_inv") or pe
    ef = res.get("efectivo_propio")
    ps = res["posiciones"]
    # --- membrete
    marca = [Paragraph(NOMBRE, st["marca"]), Paragraph(AUTORES, st["sub"])]
    fch = Paragraph(f"Fecha del análisis:<br/><b>{_fecha(hoy)}</b>", ParagraphStyle("d", parent=st["sub"], alignment=2))
    if os.path.exists(LOGO):
        cab = Table([[Image(LOGO, 15 * mm, 15 * mm), marca, fch]], colWidths=[19 * mm, ancho - 19 * mm - 40 * mm, 40 * mm])
    else:
        cab = Table([[marca, fch]], colWidths=[ancho - 40 * mm, 40 * mm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("LINEBELOW", (0, 0), (-1, 0), 2, verde), ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]))
    s1, s2 = saludo(nombre, edad, perfil)
    el = [cab, Spacer(1, 8), Paragraph(TITULO, st["tit"]), Spacer(1, 8), Paragraph(f"<b>{html.escape(s1)}</b>", st["p"]), Spacer(1, 3), Paragraph(html.escape(s2), st["p"]), Spacer(1, 6)]
    el += [Paragraph(_md(x), st["p"]) for x in sec.get("Objetivo como inversor", [])]

    # --- tortas (sin título ni texto adentro)
    def torta(items, medida=30 * mm):
        items = [(n, v, c) for n, v, c in items if v >= 0.5]
        tot = sum(v for _, v, _ in items) or 1
        leyenda = [Paragraph(f'<font color="{c}"><b>•</b></font> {html.escape(n)}: <b>{v / tot * 100:.0f} %</b>', st["pq"]) for n, v, c in items] or [Paragraph("Sin inversiones cargadas en estos grupos.", st["pq"])]
        celda = Table([[_pie([(v, c) for _, v, c in items], medida), leyenda]], colWidths=[medida + 4 * mm, 62 * mm], hAlign="CENTER")
        celda.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        return [celda, Spacer(1, 8)]

    def cuerpo_de(frases):
        out, i = [], 0
        while i < len(frases):
            x = frases[i]
            if x.startswith("- "):
                while i < len(frases) and frases[i].startswith("- "):
                    out += [Paragraph(f"•&nbsp;&nbsp;{_md(frases[i][2:])}", st["li"]), Spacer(1, 2)]
                    i += 1
                out.append(Spacer(1, 4))
                continue
            out += [Paragraph(_md(x), st["p"]), Spacer(1, 6)]
            i += 1
        return out
    parrafos = cuerpo_de
    clases_ = [(CLASES[k], max(pi[k], 0.5), CV.COL_CLASE[k]) for k in ("rv", "rf", "efectivo", "oro", "cripto", "otros") if pi.get(k, 0) >= 0.05 and (ef or k != "efectivo")]
    el += seccion("Estructura de tu Cartera", torta(clases_) + parrafos(sec["Estructura de tu cartera"]), junto=3)
    g = res.get("geo")
    cuerpo = []
    if g:
        partes = [(CV.NOM_GEO[k], g[k], CV.COL_GEO[k]) for k in ("usa", "desarrollados", "emergentes", "fuera_sd", "global")]
        partes.append((CV.NOM_GEO["sin"], max(0.0, 100 - sum(v for _, v, _ in partes)), CV.COL_GEO["sin"]))
        cuerpo = torta(partes)
    el += seccion("Diversificación Geográfica", cuerpo + parrafos(sec["Diversificación geográfica"]), junto=3)
    sp = res.get("super")
    c1 = torta([(CV.NOM_SUP[k], sp[k], CV.COL_SUP[k]) for k in ("defensivo", "sensible", "ciclico")]) if sp else []
    gi = res.get("sectores_gics") or []
    c2 = torta([(n, v, CV.COL_GICS[i % len(CV.COL_GICS)]) for i, (n, v) in enumerate(gi)]) if (sp and gi) else []
    el += seccion("Diversificación Sectorial", c1 + parrafos(sec["Diversificación sectorial"]) + c2 + parrafos(sec.get("Diversificación sectorial (detalle GICS)", [])), junto=3)
    el += seccion("Liquidez", parrafos(sec["Liquidez"]))
    if "Sensibilidad al mercado (beta)" in sec:
        el += seccion("Sensibilidad al mercado (beta)", parrafos(sec["Sensibilidad al mercado (beta)"]))
    comp = comparar(previa, res) if previa else []
    if comp:
        el += seccion("Comparación con tu evaluación anterior", parrafos(comp))
    fr = sec["Conclusiones finales"]
    cuerpo = parrafos([fr[0]])
    i = 1
    while i < len(fr):
        x = fr[i]
        m = re.match(r"^([0-9]+)[.] (.*)$", x)
        if x.startswith("##"):
            cuerpo += [Paragraph(f"<b>{_md(x.lstrip('#'))}</b>", st["sm"])]
            i += 1
        elif x.startswith("- "):
            j = i
            while j < len(fr) and fr[j].startswith("- "):
                j += 1
            cuerpo += parrafos(fr[i:j])
            i = j
        elif m:
            txt = m.group(2)
            if " **Por qué:** " in txt:
                a_, b_ = txt.split(" **Por qué:** ", 1)
                txt_h = f"<b>{_md(a_)}</b> <i>Por qué: {_md(b_)}</i>"
            else:
                txt_h = _md(txt)
            cuerpo += [Paragraph(f"<b>{m.group(1)}.</b>&nbsp;{txt_h}", st["li"]), Spacer(1, 3)]
            i += 1
        else:
            cuerpo += parrafos([x])
            i += 1
    d1, d2 = despedida(nombre)
    cuerpo += [Spacer(1, 8), Paragraph(html.escape(d1), st["p"]), Spacer(1, 4), Paragraph(f"<b>{html.escape(d2)}</b>", st["p"])]
    el += seccion("Conclusiones Finales", cuerpo, junto=4)
    el += [Spacer(1, 14), Paragraph(f"<b>Aviso Legal:</b> {html.escape(AVISO_CARTERA[0])}", st["pq"])]
    doc.build(el, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()


def html_informe(res, edad, perfil, aviso="", hoy=None, nombre="", previa=None):
    """Mismo informe, con la misma información que la app, como página HTML con el membrete (para imprimir como PDF si no hubiera reportlab)."""
    import base64
    from ui import cartera_visual as CV
    logo = ""
    if os.path.exists(LOGO):
        logo = '<img src="data:image/png;base64,' + base64.b64encode(open(LOGO, "rb").read()).decode() + '" width="56" height="56" alt="">'
    return ("<!doctype html><html lang='es'><head><meta charset='utf-8'><title>" + html.escape(TITULO) + "</title><style>"
            "body{font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:820px;margin:24px auto;padding:0 16px;font-size:14px;line-height:1.5}"
            ".mb{display:flex;align-items:center;gap:14px;border-bottom:3px solid #15803d;padding-bottom:8px;margin-bottom:14px}.mb b{font-size:20px}.mb small{display:block;color:#64748b}"
            + CV.CSS + "</style></head><body>"
            f"<div class='mb'>{logo}<div><b>{html.escape(NOMBRE)}</b><small>{html.escape(AUTORES)}</small></div><div style='margin-left:auto;color:#64748b;text-align:right'>Fecha del análisis<br><b>{_fecha(hoy)}</b></div></div>"
            + CV.visual_html(res, edad, perfil, nombre, _fecha(hoy), previa)
            + "</body></html>").encode("utf-8")
