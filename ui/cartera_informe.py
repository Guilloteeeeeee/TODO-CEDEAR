"""Informe descargable de "Tu Cartera" (v1.2.74): PDF con el membrete de Finanzas para Médicos Argentina (logo, nombre y línea de color), la cartera tal como la cargó
la persona, la devolución y el aviso legal. Se arma en el momento, en memoria, y se baja al dispositivo: no se guarda en ningún servidor.
Usa reportlab (requirements.txt); si no estuviera disponible, `html_informe` da el mismo informe en una página que se puede imprimir como PDF."""
import datetime
import html
import io
import os
import re

from ui.cartera import CLASES, devolucion

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(_RAIZ, "assets", "marca", "finanzas-para-medicos-128.png")
NOMBRE = "Finanzas para Médicos Argentina"
AUTORES = "Guillermo Di Palma AP 2372 y María Laura García"
TITULO = "Informe de orientación de cartera"
NOTA_PRIVACIDAD = "Este informe se armó en el momento con los datos que cargaste. No guardamos tu cartera ni este informe: solo existe en tu dispositivo."


def _fecha(f=None):
    return (f or datetime.date.today()).strftime("%d/%m/%Y")


def _filas_cartera(res):
    """[(ticker, clase en castellano, % de la cartera)] ordenadas de mayor a menor peso."""
    return [(p["ticker"], CLASES.get(p["clase"], p["clase"]), p["pct"]) for p in res.get("posiciones", [])]


def _md(t):
    """**negrita** -> <b>, con el resto escapado (para los párrafos de reportlab)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(t), quote=False))


def pdf_informe(res, edad, perfil, aviso="", hoy=None):
    """Bytes del PDF. Lanza ImportError si no está reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    azul, verde, gris = colors.HexColor("#1e3a8a"), colors.HexColor("#15803d"), colors.HexColor("#64748b")
    st = {
        "tit": ParagraphStyle("tit", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#111827")),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=gris),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=azul, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#1f2937")),
        "pq": ParagraphStyle("pq", fontName="Helvetica", fontSize=8, leading=11, textColor=gris),
        "marca": ParagraphStyle("marca", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#111827")),
    }
    buf = io.BytesIO()

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#e5e9f0"))
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(gris)
        canvas.drawString(18 * mm, 10 * mm, f"{NOMBRE} · TodoCedears · Información con fines educativos, no es una recomendación de inversión")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title=f"{TITULO} - {NOMBRE}", author=NOMBRE)
    ancho = A4[0] - 36 * mm
    # --- membrete
    marca = [Paragraph(NOMBRE, st["marca"]), Paragraph(AUTORES, st["sub"])]
    if os.path.exists(LOGO):
        cab = Table([[Image(LOGO, 15 * mm, 15 * mm), marca, Paragraph(f"Fecha: {_fecha(hoy)}", ParagraphStyle("d", parent=st["sub"], alignment=2))]],
                    colWidths=[19 * mm, ancho - 19 * mm - 40 * mm, 40 * mm])
    else:
        cab = Table([[marca, Paragraph(f"Fecha: {_fecha(hoy)}", ParagraphStyle("d", parent=st["sub"], alignment=2))]], colWidths=[ancho - 40 * mm, 40 * mm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("LINEBELOW", (0, 0), (-1, 0), 2, verde), ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]))
    el = [cab, Spacer(1, 8), Paragraph(TITULO, st["tit"])]
    perfil_txt = f", perfil {str(perfil).lower()}" if perfil else ""
    el += [Paragraph(f"Persona de {int(edad)} años{perfil_txt}", st["sub"]), Spacer(1, 4)]
    # --- cartera cargada
    filas = _filas_cartera(res)
    if filas:
        el.append(Paragraph("Tu cartera tal como la cargaste", st["h"]))
        datos = [["Activo", "Tipo", "% de la cartera"]] + [[t, c, f"{p:.1f} %"] for t, c, p in filas[:40]]
        tb = Table(datos, colWidths=[ancho * 0.34, ancho * 0.40, ancho * 0.26], repeatRows=1)
        tb.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9), ("FONT", (0, 1), (-1, -1), "Helvetica", 9), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), azul), ("ALIGN", (2, 0), (2, -1), "RIGHT"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e9f0")),
                                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        el.append(tb)
        if len(filas) > 40:
            el.append(Paragraph(f"(se muestran las 40 posiciones más grandes de {len(filas)})", st["pq"]))
    # --- devolucion
    for titulo, frases in devolucion(res, edad, perfil):
        el.append(Paragraph(html.escape(titulo), st["h"]))
        el.append(ListFlowable([ListItem(Paragraph(_md(x), st["p"]), leftIndent=10) for x in frases], bulletType="bullet", start="•", leftIndent=10, bulletFontSize=8))
    # --- avisos
    el += [Spacer(1, 12), Paragraph("<b>Cómo leer este informe.</b> Es una orientación general con fines informativos y educativos, armada con reglas fijas a partir de lo que cargaste. "
                                    "No es una recomendación de compra o venta ni un consejo personalizado: cada situación (objetivos, plazos, impuestos, otros ingresos) es distinta.", st["pq"]),
           Spacer(1, 4), Paragraph(f"<b>Privacidad.</b> {html.escape(NOTA_PRIVACIDAD)}", st["pq"])]
    if aviso:
        el += [Spacer(1, 4), Paragraph(f"<b>Aviso legal.</b> {html.escape(str(aviso))}", st["pq"])]
    doc.build(el, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()


def html_informe(res, edad, perfil, aviso="", hoy=None):
    """Mismo informe como página HTML con el membrete (para imprimir como PDF si no hay reportlab)."""
    import base64
    from ui.cartera import devolucion_html
    logo = ""
    if os.path.exists(LOGO):
        logo = '<img src="data:image/png;base64,' + base64.b64encode(open(LOGO, "rb").read()).decode() + '" width="56" height="56" alt="">'
    perfil_txt = f", perfil {html.escape(str(perfil).lower())}" if perfil else ""
    filas = "".join(f"<tr><td>{html.escape(str(t))}</td><td>{html.escape(str(c))}</td><td style='text-align:right'>{p:.1f} %</td></tr>" for t, c, p in _filas_cartera(res))
    return ("<!doctype html><html lang='es'><head><meta charset='utf-8'><title>" + html.escape(TITULO) + "</title><style>"
            "body{font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:780px;margin:24px auto;padding:0 16px;font-size:14px;line-height:1.5}"
            ".mb{display:flex;align-items:center;gap:14px;border-bottom:3px solid #15803d;padding-bottom:8px}.mb b{font-size:20px}.mb small{display:block;color:#64748b}"
            "h1{font-size:22px;margin:16px 0 2px}h4{color:#1e3a8a;margin:14px 0 4px}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e9f0;padding:4px 6px;text-align:left}"
            ".q{color:#64748b;font-size:11.5px;margin-top:12px}</style></head><body>"
            f"<div class='mb'>{logo}<div><b>{html.escape(NOMBRE)}</b><small>{html.escape(AUTORES)}</small></div><div style='margin-left:auto;color:#64748b'>Fecha: {_fecha(hoy)}</div></div>"
            f"<h1>{html.escape(TITULO)}</h1><div style='color:#64748b'>Persona de {int(edad)} años{perfil_txt}</div>"
            f"<h4>Tu cartera tal como la cargaste</h4><table><tr><th>Activo</th><th>Tipo</th><th style='text-align:right'>% de la cartera</th></tr>{filas}</table>"
            + devolucion_html(devolucion(res, edad, perfil)) +
            f"<p class='q'><b>Cómo leer este informe.</b> Orientación general con fines informativos y educativos; no es una recomendación de compra o venta ni un consejo personalizado.</p>"
            f"<p class='q'><b>Privacidad.</b> {html.escape(NOTA_PRIVACIDAD)}</p>"
            + (f"<p class='q'><b>Aviso legal.</b> {html.escape(str(aviso))}</p>" if aviso else "") + "</body></html>").encode("utf-8")
