"""Informe descargable de "Tu Cartera" (v1.2.74): PDF con el membrete de Finanzas para Médicos Argentina (logo, nombre y línea de color), la cartera tal como la cargó
la persona, la devolución y el aviso legal. Se arma en el momento, en memoria, y se baja al dispositivo: no se guarda en ningún servidor.
Usa reportlab (requirements.txt); si no estuviera disponible, `html_informe` da el mismo informe en una página que se puede imprimir como PDF."""
import datetime
import html
import io
import os
import re

from ui.cartera import AVISO_CARTERA, CLASES, SALUDO_FINAL, devolucion

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
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(t), quote=False))


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
    g.data = [max(v, 0.01) for v, _ in items]
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
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from data import carteras_modelo as CM
    from ui import cartera_visual as CV
    from ui.cartera import comparar, nivel

    azul, verde, gris = colors.HexColor("#1e3a8a"), colors.HexColor("#15803d"), colors.HexColor("#64748b")
    st = {
        "tit": ParagraphStyle("tit", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#111827")),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=gris),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=azul, spaceBefore=12, spaceAfter=5),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#1f2937"), alignment=4),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.6, leading=13.5, textColor=colors.HexColor("#1f2937"), leftIndent=11, firstLineIndent=-11, spaceAfter=3, alignment=4),
        "pq": ParagraphStyle("pq", fontName="Helvetica", fontSize=8, leading=11, textColor=gris, spaceAfter=3, alignment=4),
        "sm": ParagraphStyle("sm", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#334155")),
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

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title=f"{TITULO} - {NOMBRE}", author=NOMBRE)
    ancho = A4[0] - 36 * mm

    def lista(frases):
        out = []
        for x in frases:
            c = colnivel[nivel(x)]
            out.append(Paragraph(f'<font color="{c}"><b>•</b></font>&nbsp;&nbsp;{_md(x)}', st["li"]))
        return out

    def seccion(titulo, cuerpo, junto=2):
        cuerpo = [c for c in cuerpo if c is not None]
        return [KeepTogether([Paragraph(html.escape(titulo), st["h"])] + cuerpo[:junto])] + cuerpo[junto:]

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
    quien = (nombre or "").strip() or "colega inversor"
    el = [cab, Spacer(1, 8), Paragraph(TITULO, st["tit"])]
    perfil_txt = f", perfil {str(perfil).lower()}" if perfil else ""
    el += [Paragraph(f"Persona de {int(edad)} años{perfil_txt}", st["sub"]), Spacer(1, 6),
           Paragraph(f"<b>Hola {html.escape(quien)}.</b> Gracias por tomarte el tiempo de evaluar tu cartera con nosotros. Esperamos que nuestros aportes te ayuden a lograr tus objetivos financieros.", st["p"])]

    # --- 1. Ponderaciones: dos tortas por grandes grupos (la liquidez no entra en el 100 %)
    def torta(titulo, items, centro, medida=30 * mm):
        items = [(n, v, c) for n, v, c in items if v >= 0.5]
        tot = sum(v for _, v, _ in items) or 1
        leyenda = [Paragraph(f'<font color="{c}"><b>•</b></font> {html.escape(n)}: <b>{v / tot * 100:.0f} %</b>', st["pq"]) for n, v, c in items] or [Paragraph("Sin inversiones cargadas en estos grupos.", st["pq"])]
        celda = Table([[_pie([(v, c) for _, v, c in items], medida, centro), leyenda]], colWidths=[medida + 3 * mm, ancho / 2 - medida - 8 * mm])
        celda.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        return [Paragraph(html.escape(titulo), st["sm"]), celda]

    def clases(peso, con_liq):
        return [(CLASES[k], peso[k], CV.COL_CLASE[k]) for k in ("rv", "rf", "efectivo", "oro", "cripto", "otros") if peso.get(k, 0) >= 0.05 and (con_liq or k != "efectivo")]
    ref = CM.referencia(edad, perfil)
    mitades = []
    if ref:
        mitades.append(torta("Referencia teórica para tu edad y perfil", clases(ref[1], True), "teórica"))
    mitades.append(torta("Tu cartera", clases(pi, bool(ef)), f"{int(edad)} años"))
    tb = Table([mitades], colWidths=[ancho / len(mitades)] * len(mitades))
    tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    el += seccion("Ponderaciones", [tb, Spacer(1, 4)] + lista(sec["Ponderaciones"]))
    # --- 2. Geografía (renta variable y renta fija)
    g = res.get("geo")
    cuerpo = []
    if g:
        partes = [(CV.NOM_GEO[k], g[k], CV.COL_GEO[k]) for k in ("usa", "desarrollados", "emergentes", "fuera_sd", "global")]
        partes.append((CV.NOM_GEO["sin"], max(0.0, 100 - sum(v for _, v, _ in partes)), CV.COL_GEO["sin"]))
        t1 = torta("Distribución geográfica (renta variable y renta fija)", partes, "países")
        cuerpo = [Table([[t1]], colWidths=[ancho]), Spacer(1, 4)]
    el += seccion("Diversificación geográfica", cuerpo + lista(sec["Diversificación geográfica"]))
    # --- 3. Sectorial
    sp = res.get("super")
    cuerpo = []
    if sp:
        t1 = torta("Supersectores", [(CV.NOM_SUP[k], sp[k], CV.COL_SUP[k]) for k in ("defensivo", "sensible", "ciclico")], "sectores")
        cuerpo = [Table([[t1]], colWidths=[ancho]), Spacer(1, 4)]
    el += seccion("Diversificación sectorial", cuerpo + lista(sec["Diversificación sectorial"]))
    el += seccion("Oro y Criptomonedas", lista(sec["Oro y Criptomonedas"]))
    el += seccion("Liquidez (aparte, optativa)", lista(sec["Liquidez"]))
    if "Sensibilidad al mercado (beta)" in sec:
        el += seccion("Sensibilidad al mercado (beta)", lista(sec["Sensibilidad al mercado (beta)"]))
    comp = comparar(previa, res) if previa else []
    if comp:
        el += seccion("Comparación con tu evaluación anterior", lista(comp))
    # --- 4. Qué ajustaría
    fr = sec["Qué ajustaría"]
    cuerpo = [Paragraph(_md(fr[0]), st["p"]), Spacer(1, 5), Paragraph(f"<b>{_md(fr[1].lstrip('#'))}</b>", st["sm"]), Spacer(1, 3), Paragraph(_md(fr[2]), st["p"]), Spacer(1, 3)]
    for x in fr[3:]:
        m = re.match(r"^([0-9]+)[.] (.*)$", x)
        cuerpo.append(Paragraph(f"<b>{m.group(1)}.</b>&nbsp;{_md(m.group(2))}" if m else _md(x), st["li"]))
    el += seccion("Qué ajustaría", cuerpo, junto=6)
    # --- saludo final y aviso legal
    el += [Spacer(1, 12), Paragraph(f"<b>{html.escape(SALUDO_FINAL)}</b><br/>Finanzas para Médicos Argentina", ParagraphStyle("sf", parent=st["p"], alignment=1)), Spacer(1, 14)]
    el += [Paragraph(f"<b>Aviso Legal:</b> {html.escape(AVISO_CARTERA[0])}", st["pq"])]
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
