"""Análisis Fundamental v4 en PDF (v1.4.1): el mismo artículo que se ve en la app (título, resumen, introducción, secciones con sus gráficos, valuación con los números
del día, conclusión, a favor y en contra, fuentes), con el membrete de Finanzas para Médicos Argentina. Se arma en el momento, en memoria, y se baja al dispositivo.
Usa reportlab (ya está en requirements.txt). Los gráficos de la app son SVG propios muy simples (líneas, barras, textos): se redibujan acá con reportlab, sin librerías
extra; si algún gráfico no se puede dibujar, se omite y el resto del PDF sale igual."""
import html
import io
import os
import re

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(_RAIZ, "assets", "marca", "finanzas-para-medicos-128.png")
NOMBRE = "Finanzas para Médicos Argentina"
AUTORES = "Guillermo Di Palma AP 2372 y María Laura García"

_FUENTES = os.path.join(_RAIZ, "assets", "fuentes")
_FUENTE = {}


def _fuentes():
    """(normal, negrita, caracteres que tiene). La tipografía de la app (Roboto Condensed, assets/fuentes); si faltan los archivos, Helvetica."""
    if "f" not in _FUENTE:
        try:
            from fontTools.ttLib import TTFont as _TT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            n, b = os.path.join(_FUENTES, "RobotoCondensed-400.ttf"), os.path.join(_FUENTES, "RobotoCondensed-700.ttf")
            pdfmetrics.registerFont(TTFont("RobotoCond", n))
            pdfmetrics.registerFont(TTFont("RobotoCond-B", b))
            pdfmetrics.registerFontFamily("RobotoCond", normal="RobotoCond", bold="RobotoCond-B", italic="RobotoCond", boldItalic="RobotoCond-B")
            _FUENTE["f"] = ("RobotoCond", "RobotoCond-B", set(_TT(n).getBestCmap().keys()))
        except Exception:  # noqa: BLE001
            _FUENTE["f"] = ("Helvetica", "Helvetica-Bold", None)
    return _FUENTE["f"]


# Caracteres que la letra estándar del PDF (Helvetica, cp1252) no tiene
_CAMBIOS = {"≈": "~", "→": "->", "←": "<-", "≥": ">=", "≤": "<=", "−": "-", "‑": "-", " ": " ", " ": " ", "​": "", "✓": "", "•": "-"}


def _limpio(t):
    t = str(t or "")
    for a, b in _CAMBIOS.items():
        t = t.replace(a, b)
    cm = _fuentes()[2]
    if cm is None:
        return t.encode("cp1252", "replace").decode("cp1252")
    return "".join(c if (ord(c) in cm or c in "\n\t") else "?" for c in t)


def _md(t):
    """**negrita** -> <b>; el resto escapado y con los caracteres que Helvetica no tiene reemplazados."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(_limpio(t), quote=False))


def _attr(s, k, por_defecto=None):
    m = re.search(r'(?<![\w-])' + re.escape(k) + r'="([^"]*)"', s)
    return m.group(1) if m else por_defecto


def _color(c, colors, por_defecto="#000000"):
    try:
        return colors.HexColor(c or por_defecto)
    except Exception:  # noqa: BLE001
        return colors.HexColor(por_defecto)


def _dibujo(grafico_html, ancho_pt):
    """(Drawing de reportlab | None, [(color, texto)] de la leyenda) a partir del HTML del gráfico de la app. Nunca levanta excepciones."""
    try:
        from reportlab.graphics.shapes import Drawing, Line, Rect, String
        from reportlab.lib import colors
        m = re.search(r'<svg[^>]*viewBox="0 0 (\d+) (\d+)"[^>]*>(.*?)</svg>', grafico_html, re.S)
        if not m:
            return None, []
        W, H, cuerpo = float(m.group(1)), float(m.group(2)), m.group(3)
        esc = ancho_pt / W
        d = Drawing(ancho_pt, H * esc)
        Y = lambda y: (H - float(y)) * esc
        for el in re.finditer(r"<(line|rect|text)\b([^>]*?)(?:/>|>(.*?)</\1>)", cuerpo, re.S):
            tag, a, inner = el.group(1), el.group(2), el.group(3) or ""
            if tag == "line":
                ln = Line(float(_attr(a, "x1")) * esc, Y(_attr(a, "y1")), float(_attr(a, "x2")) * esc, Y(_attr(a, "y2")),
                          strokeColor=_color(_attr(a, "stroke"), colors, "#9ca3af"), strokeWidth=float(_attr(a, "stroke-width", "1")) * esc)
                da = _attr(a, "stroke-dasharray")
                if da:
                    ln.strokeDashArray = [max(1.0, float(x) * esc) for x in da.split()]
                d.add(ln)
            elif tag == "rect":
                x, y, w, h = (float(_attr(a, k)) for k in ("x", "y", "width", "height"))
                d.add(Rect(x * esc, (H - y - h) * esc, w * esc, h * esc, fillColor=_color(_attr(a, "fill"), colors, "#1d4ed8"), strokeColor=None))
            else:
                txt = html.unescape(re.sub(r"<[^>]+>", "", inner))
                fs = float(_attr(a, "font-size", "13")) * esc
                ancla = {"end": "end", "middle": "middle"}.get(_attr(a, "text-anchor"), "start")
                d.add(String(float(_attr(a, "x")) * esc, Y(_attr(a, "y")), _limpio(txt), fontName=B if _attr(a, "font-weight") else "Helvetica",
                             fontSize=fs, textAnchor=ancla, fillColor=_color(_attr(a, "fill"), colors, "#111827")))
        ley = []
        lg = re.search(r'<div class="af-gl">(.*?)</div>', grafico_html, re.S)
        if lg:
            for sp in re.finditer(r"<span><i([^>]*)></i>(.*?)</span>", lg.group(1), re.S):
                col = re.search(r"(?:background|border-top:[^#;]*)\s*:?\s*(#[0-9a-fA-F]{3,6})", sp.group(1))
                ley.append((col.group(1) if col else "#64748b", html.unescape(re.sub(r"<[^>]+>", "", sp.group(2)))))
        return d, ley
    except Exception:  # noqa: BLE001
        return None, []


def _titulo_figura(grafico_html):
    m = re.search(r"<figcaption>(.*?)</figcaption>", grafico_html, re.S)
    return html.unescape(m.group(1)) if m else ""


def pdf_analisis(af, estados=None, row=None, historial=None, dividendos=None, bono10=None, nombre_empresa=""):
    """Bytes del PDF del análisis v4. Lanza ImportError si no está reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from data import af_v4 as V
    from data import analisis_fundamental as AF

    row = row or {}
    tk = str(af.get("ticker") or row.get("ticker") or "").upper()
    try:
        from data import damodaran as _D
        dam = _D.valores(tk) or {}
    except Exception:  # noqa: BLE001
        dam = {}
    ctx = V.contexto(row, af, dam, bono10)
    dps = ((dividendos or {}).get("trayectoria") or {}).get("anuales")
    graf = lambda k: V.grafico(k, estados, row, dam, ctx, historial, dps)
    cal = af.get("calidad") if af.get("calidad") in AF.CALIDADES else "Buena"
    R, B, _ = _fuentes()
    azul, gris, tinta = colors.HexColor("#1e3a8a"), colors.HexColor("#64748b"), colors.HexColor("#1f2937")
    verde = colors.HexColor("#15803d")
    st = {
        "marca": ParagraphStyle("marca", fontName=B, fontSize=13, leading=16, textColor=colors.HexColor("#111827")),
        "sub": ParagraphStyle("sub", fontName=R, fontSize=10.5, leading=14, textColor=gris),
        "tit": ParagraphStyle("tit", fontName=B, fontSize=21, leading=25.5, textColor=colors.HexColor("#0f172a"), spaceBefore=4, spaceAfter=9),
        "h": ParagraphStyle("h", fontName=B, fontSize=14.5, leading=18, textColor=colors.HexColor("#0f172a"), spaceBefore=22, spaceAfter=8, keepWithNext=1),
        "p": ParagraphStyle("p", fontName=R, fontSize=11.2, leading=16, textColor=tinta, spaceAfter=8, alignment=TA_JUSTIFY),
        "li": ParagraphStyle("li", fontName=R, fontSize=11.2, leading=15.6, textColor=tinta, alignment=TA_JUSTIFY),
        "fig": ParagraphStyle("fig", fontName=B, fontSize=10, leading=13, textColor=colors.HexColor("#334155"), spaceBefore=4, keepWithNext=1),
        "ley": ParagraphStyle("ley", fontName=R, fontSize=9, leading=11.5, textColor=gris, spaceAfter=6),
        "peq": ParagraphStyle("peq", fontName=R, fontSize=9, leading=12, textColor=gris),
        "fu": ParagraphStyle("fu", fontName=R, fontSize=9.5, leading=12.5, textColor=colors.HexColor("#475569")),
        "ph": ParagraphStyle("ph", fontName=B, fontSize=9.5, leading=12, textColor=verde, spaceAfter=3),
        "ch": ParagraphStyle("ch", fontName=B, fontSize=9.5, leading=12, textColor=colors.HexColor("#b91c1c"), spaceAfter=3),
        "cp": ParagraphStyle("cp", fontName=R, fontSize=11.2, leading=15.6, textColor=tinta, spaceBefore=10, backColor=colors.HexColor("#f1f5f9"), borderPadding=6),
    }
    buf = io.BytesIO()
    fecha_ahora = __import__("datetime").date.today().strftime("%d/%m/%Y")

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#e5e9f0"))
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont(R, 8)
        canvas.setFillColor(gris)
        canvas.drawString(18 * mm, 10 * mm, _limpio(f"{NOMBRE} · TodoCedears · Información con fines educativos, no es una recomendación de inversión"))
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm,
                            title=_limpio(f"Análisis Fundamental {tk} - {NOMBRE}"), author=NOMBRE)
    ancho = A4[0] - 36 * mm
    ancho_graf = min(ancho, 150 * mm)
    marca = [Paragraph(_limpio(NOMBRE), st["marca"]), Paragraph(_limpio(AUTORES), st["sub"])]
    fch = Paragraph(f"Descargado el {fecha_ahora}", ParagraphStyle("d", parent=st["sub"], alignment=2))
    if os.path.exists(LOGO):
        cab = Table([[Image(LOGO, 15 * mm, 15 * mm), marca, fch]], colWidths=[19 * mm, ancho - 19 * mm - 40 * mm, 40 * mm])
    else:
        cab = Table([[marca, fch]], colWidths=[ancho - 40 * mm, 40 * mm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("LINEBELOW", (0, 0), (-1, 0), 2, verde), ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]))
    el = [cab, Spacer(1, 26)]
    quien = f"{nombre_empresa} ({tk})" if nombre_empresa and tk else (tk or nombre_empresa)
    if quien:
        el.append(Paragraph(_md("Análisis Fundamental · " + quien), st["sub"]))
        el.append(Spacer(1, 6))
    el.append(Paragraph(_md(af.get("titulo")), st["tit"]))
    el.append(Paragraph(_md(f"Escrito el {af.get('fecha') or ''}"), st["sub"]))
    el.append(Spacer(1, 16))
    res = af.get("resumen") if isinstance(af.get("resumen"), list) else []
    if res:
        el.append(ListFlowable([ListItem(Paragraph(_md(x), st["li"]), leftIndent=10, spaceAfter=3) for x in res], bulletType="bullet", start="•", leftIndent=10, bulletFontSize=9, bulletFontName=R))
    if af.get("desde_el_ultimo"):
        el.append(Spacer(1, 6))
        el.append(Paragraph(_md("**Desde el último análisis:** " + af["desde_el_ultimo"]), st["cp"]))

    def texto(txt, con_ctx=False):
        """Párrafos, listas y gráficos de un bloque de texto -> flowables."""
        if con_ctx:
            txt = V.rellenar(txt, ctx, marca=False)
        out = []
        for par in str(txt or "").replace("\r", "").split("\n\n"):
            par = par.strip()
            if not par:
                continue
            g = V.RE_GRAFICO.match(par)
            if g:
                gh = graf(g.group(1))
                dib, ley = _dibujo(gh, ancho_graf) if gh else (None, [])
                if dib is not None:
                    bloque = [Paragraph(_md(_titulo_figura(gh)), st["fig"]), dib]
                    if ley:
                        bloque.append(Paragraph("  ·  ".join(f'<font color="{c}">&#9632;</font> {html.escape(_limpio(t), quote=False)}' for c, t in ley), st["ley"]))
                    else:
                        bloque.append(Spacer(1, 6))
                    out.append(KeepTogether(bloque))
                continue
            lineas = [l.strip() for l in par.split("\n") if l.strip()]
            if lineas and all(l.startswith(("- ", "• ")) for l in lineas):
                out.append(ListFlowable([ListItem(Paragraph(_md(l[2:].strip()), st["li"]), leftIndent=10, spaceAfter=2) for l in lineas], bulletType="bullet", start="•", bulletFontName=R,
                                        leftIndent=10, bulletFontSize=8))
                out.append(Spacer(1, 5))
            else:
                out.append(Paragraph(_md(" ".join(lineas)), st["p"]))
        return out

    el.append(Spacer(1, 24))
    el += texto(af.get("introduccion"))
    for s in af.get("secciones") or []:
        el.append(Paragraph(_md(s.get("titulo")), st["h"]))
        el += texto(s.get("texto"))
        if af.get("clientes") and s is (af.get("secciones") or [None])[0]:
            el.append(Paragraph(_md("**Sus clientes:** " + "; ".join(str(c) for c in af["clientes"] if c)), st["p"]))
    val = af.get("valuacion") or {}
    if val.get("texto"):
        fp = ctx.get("fecha_precio")
        el.append(Paragraph("Valuación", st["h"]))
        el.append(Paragraph(_md(f"Los números son del día de descarga{f' (precio al {fp})' if fp else ''}."), st["peq"]))
        el.append(Spacer(1, 3))
        el += texto(val["texto"], con_ctx=True)
    cr = AF.cruce(cal, row.get("categoria")) if row else ""
    el.append(Paragraph(_md(f"Conclusión · Calidad del Negocio: {cal}"), st["h"]))
    el += texto(af.get("conclusion"))
    if cr:
        el.append(Paragraph(_md("**Calidad y Precio Hoy:** " + cr), st["cp"]))
    # A favor / en contra
    def col(titulo, items, est):
        return [Paragraph(titulo, est)] + [Paragraph("• " + _md(re.sub(r"^\s*([^:]{3,50}):", r"**\1:**", str(x), count=1)), st["li"]) for x in items]
    pc = Table([[col("A FAVOR", af.get("pros") or [], st["ph"]), col("EN CONTRA", af.get("contras") or [], st["ch"])]], colWidths=[ancho / 2, ancho / 2])
    pc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (1, 0), (1, 0), 0)]))
    el += [Spacer(1, 10), pc]
    # Fuentes
    el.append(Paragraph("Fuentes", st["h"]))
    for h in af.get("hechos") or []:
        if str(h.get("url", "")).startswith("https://"):
            u = html.escape(h["url"], quote=True)
            el.append(Paragraph(f"• {html.escape(_limpio(h['dato']), quote=False)}. <link href=\"{u}\" color=\"#1d4ed8\">{html.escape(_limpio(h.get('fuente') or 'Documento oficial'), quote=False)}</link>", st["fu"]))
            el.append(Spacer(1, 2))
    lsec = AF.link_sec(tk)
    el.append(Paragraph("• Estados financieros de 4 años y últimos 12 meses, dividendos y equipo directivo: Yahoo Finance."
                        + (f' <link href="{html.escape(lsec)}" color="#1d4ed8">Informes de la empresa en la SEC</link>' if lsec else ""), st["fu"]))
    el.append(Spacer(1, 2))
    el.append(Paragraph("• Promedios de la industria: Aswath Damodaran, NYU Stern (datos a enero de 2026). Precio, múltiplos y Fair Value del día: TodoCedears (Yahoo Finance); "
                        "bono del Tesoro a 10 años: Yahoo Finance.", st["fu"]))
    el += [Spacer(1, 12), Paragraph(_md(f"Análisis escrito el {af.get('fecha') or ''} por Finanzas para Médicos Argentina con asistencia de inteligencia artificial, a partir de los informes "
                                        "oficiales de la empresa y los datos de Yahoo Finance. Puede contener errores o quedar desactualizado: verificá siempre con los documentos oficiales. "
                                        "Es información con fines educativos, no una recomendación de inversión."), st["peq"])]
    doc.build(el, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()
