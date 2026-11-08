"""
v1.5.50: Análisis de cada ETF (pedido de Guille, 08/11/2026: «informes de los ETFs como hacés con las empresas»; modelo aprobado: XLV).

Los informes viven en data/analisis_etf.json: {"fecha", "datos": {TICKER: informe}}. Cada informe es un dict con:
  fecha "dd/mm/aaaa", etiqueta, titulo, resumen [3 frases], datos_clave [[rótulo, valor]], intro (párrafos separados por línea en blanco),
  secciones [{titulo, texto}], dona {centro1, centro2, items [[nombre, %]]}, top10 [[nombre, ticker, %]],
  rend {al, ref, filas [[período, fondo, referencia]]} (referencia puede ser null), pros, contras, riesgos, conclusion, fuentes.
En el texto de las secciones van los marcadores [[dona]], [[top10]] y [[rend]] (cada uno solo en su párrafo), listas con «- » y **negrita**.

La misma pieza de HTML se usa en la app (solapa «Análisis del ETF») y en el PDF (generar_informe_etf.py, con Playwright, en static/informes_etf/).
"""
import html
import json
import math
import os
import re

H = html.escape
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA = os.path.join(RAIZ, "data", "analisis_etf.json")
CARPETA_PDF = os.path.join(RAIZ, "static", "informes_etf")
COL = ["#2a78d6", "#1baf7a", "#eb6834", "#eda100", "#8e5bd0", "#0ea5b7", "#d14d8b", "#94a3b8"]
AVISO = ("Información con fines educativos. No es una recomendación de compra ni de venta. Rendimientos pasados no aseguran rendimientos futuros. "
         "Cifras en dólares.")
_CACHE = {}


def cargar():
    """{TICKER: informe} (se relee solo si cambió el archivo)."""
    try:
        mt = os.path.getmtime(RUTA)
    except OSError:
        return {}
    if _CACHE.get("mt") != mt:
        try:
            datos = (json.load(open(RUTA, encoding="utf-8")) or {}).get("datos") or {}
        except Exception:  # noqa: BLE001
            datos = {}
        _CACHE.clear()
        _CACHE.update(mt=mt, datos={str(k).upper(): v for k, v in datos.items()})
    return _CACHE["datos"]


def informe(ticker):
    return cargar().get(str(ticker or "").upper())


def fecha_iso(fecha):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(fecha or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def ruta_pdf(ticker, inf=None):
    """Ruta del PDF ya armado del informe vigente (o None si todavía no se armó)."""
    inf = inf or informe(ticker)
    iso = fecha_iso((inf or {}).get("fecha"))
    if not iso:
        return None
    p = os.path.join(CARPETA_PDF, f"{str(ticker).upper()}_{iso}.pdf")
    return p if os.path.isfile(p) else None


def pct(x, d=1):
    return f"{x:.{d}f}%".replace(".", ",")


def md(t):
    t = H(str(t))
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def dona(d):
    items = [(n, float(v)) for n, v in (d or {}).get("items") or [] if v]
    if not items:
        return ""
    tot = sum(v for _, v in items)
    r, R, cx, cy = 62, 100, 110, 110
    a0, piezas = -math.pi / 2, []
    for (n, v), c in zip(items, COL):
        a1 = a0 + 2 * math.pi * v / tot
        if a1 - a0 >= 2 * math.pi - 1e-9:        # un solo pedazo: anillo entero
            piezas.append(f'<circle cx="{cx}" cy="{cy}" r="{(R + r) / 2}" fill="none" stroke="{c}" stroke-width="{R - r}"><title>{H(n)}: {pct(v)}</title></circle>')
            break
        grande = 1 if a1 - a0 > math.pi else 0
        p = (f"M{cx + R * math.cos(a0):.2f},{cy + R * math.sin(a0):.2f} A{R},{R} 0 {grande} 1 {cx + R * math.cos(a1):.2f},{cy + R * math.sin(a1):.2f} "
             f"L{cx + r * math.cos(a1):.2f},{cy + r * math.sin(a1):.2f} A{r},{r} 0 {grande} 0 {cx + r * math.cos(a0):.2f},{cy + r * math.sin(a0):.2f} Z")
        piezas.append(f'<path d="{p}" fill="{c}" stroke="#fff" stroke-width="2"><title>{H(n)}: {pct(v)}</title></path>')
        a0 = a1
    ley = "".join(f'<div class="ly"><i style="background:{c}"></i><span>{H(n)}</span><b>{pct(v)}</b></div>' for (n, v), c in zip(items, COL))
    return (f'<div class="dona"><svg viewBox="0 0 220 220" width="210" height="210">{"".join(piezas)}'
            f'<text x="110" y="106" text-anchor="middle" font-size="13" fill="#64748b">{H(d.get("centro1") or "")}</text>'
            f'<text x="110" y="126" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">{H(d.get("centro2") or "")}</text></svg>'
            f'<div class="leyenda">{ley}</div></div>')


def top10_html(filas, titulo="Empresa"):
    filas = [(n, t, float(p)) for n, t, p in filas or []]
    if not filas:
        return ""
    mx = max(p for _, _, p in filas) or 1
    cuerpo = "".join(f'<tr><td>{i}</td><td><b>{H(n)}</b> <span class="tk">{H(t or "")}</span></td><td><div class="bar"><i style="width:{p / mx * 100:.0f}%"></i></div></td>'
                     f'<td class="n">{pct(p)}</td></tr>' for i, (n, t, p) in enumerate(filas, 1))
    tot = f'<tr class="tot"><td></td><td>Las {len(filas)} juntas</td><td></td><td class="n">{pct(sum(p for _, _, p in filas))}</td></tr>' if len(filas) > 1 else ""
    return f'<table class="t10"><thead><tr><th>#</th><th>{H(titulo)}</th><th></th><th>Peso</th></tr></thead><tbody>{cuerpo}{tot}</tbody></table>'


def rend_html(r, ticker):
    filas = (r or {}).get("filas") or []
    if not filas:
        return ""
    ref = r.get("ref")
    out = []
    for p, x, s in filas:
        if x is None:
            continue
        celdas = f'<td>{H(p)}</td><td class="n"><b>{pct(x)}</b></td>'
        if ref:
            if s is None:
                celdas += '<td class="n">—</td><td class="n">—</td>'
            else:
                dif = x - s
                celdas += (f'<td class="n">{pct(s)}</td><td class="n {"up" if dif > 0 else "dn"}">{"+" if dif > 0 else "−"}'
                           f'{abs(dif):.1f}'.replace(".", ",") + " pts</td>")
        out.append(f"<tr>{celdas}</tr>")
    cab = f'<th>Período (por año)</th><th>{H(ticker)}</th>' + (f'<th>{H(ref)}</th><th>Diferencia</th>' if ref else "")
    nota = r.get("nota") or "Rendimiento anual promedio en dólares, con dividendos reinvertidos y después de la comisión."
    return (f'<div class="rd"><table class="rend"><tr>{cab}</tr>{"".join(out)}</table>'
            f'<p class="chica">{H(nota)} Rendimientos pasados no aseguran rendimientos futuros.</p></div>')


def bloque(texto, inf, ticker):
    out = []
    for par in str(texto or "").split("\n\n"):
        par = par.strip()
        if not par:
            continue
        if par == "[[dona]]":
            out.append(dona(inf.get("dona")))
        elif par == "[[top10]]":
            out.append(top10_html(inf.get("top10"), inf.get("top10_titulo") or "Empresa"))
        elif par == "[[rend]]":
            previo = out.pop() if out and out[-1].startswith("<p>") else ""      # la frase que presenta la tabla no queda sola al pie de una página
            out.append(rend_html(inf.get("rend"), ticker).replace('<div class="rd">', f'<div class="rd">{previo}', 1))
        elif par.startswith("- "):
            out.append("<ul>" + "".join(f"<li>{md(x[2:])}</li>" for x in par.split("\n") if x.startswith("- ")) + "</ul>")
        else:
            out.append(f"<p>{md(par)}</p>")
    return "".join(out)


def _parrafos(t):
    return "".join(f"<p>{md(x.strip())}</p>" for x in str(t or "").split("\n\n") if x.strip())


def cuerpo_html(ticker, inf, membrete=True):
    """El informe en HTML (dentro de <div class="ei">). membrete=False lo deja sin la franja de arriba (en la app ya está el encabezado del ETF)."""
    tk = str(ticker).upper()
    top = (f'<div class="top"><div class="m">Todo<span>Cedears</span></div><div class="f">Análisis del ETF · {H(inf.get("fecha") or "")}'
           f'<br>Finanzas para Médicos Argentina</div></div>') if membrete else ""
    res = "".join(f"<li>{md(x)}</li>" for x in inf.get("resumen") or [])
    dc = "".join(f'<div class="dc"><span>{H(k)}</span><b>{H(v)}</b></div>' for k, v in inf.get("datos_clave") or [])
    secs = "".join(f'<section><h2>{H(s.get("titulo") or "")}</h2>{bloque(s.get("texto"), inf, tk)}</section>' for s in inf.get("secciones") or [])
    pc = ""
    if inf.get("pros") or inf.get("contras"):
        pc = (f'<section><h2>Pros y contras</h2><div class="pc"><div class="p"><h3>A favor</h3><ul>{"".join(f"<li>{md(x)}</li>" for x in inf.get("pros") or [])}</ul></div>'
              f'<div class="c"><h3>En contra</h3><ul>{"".join(f"<li>{md(x)}</li>" for x in inf.get("contras") or [])}</ul></div></div></section>')
    rg = f'<section><h2>Riesgos a seguir</h2><ul>{"".join(f"<li>{md(x)}</li>" for x in inf.get("riesgos"))}</ul></section>' if inf.get("riesgos") else ""
    co = f'<section class="concl"><h2>Conclusión</h2>{_parrafos(inf.get("conclusion"))}</section>' if inf.get("conclusion") else ""
    fu = f'<div class="fu"><b>Fuentes</b><ul>{"".join(f"<li>{H(x)}</li>" for x in inf.get("fuentes") or [])}</ul></div>' if inf.get("fuentes") else ""
    return (f'<div class="ei">{top}<div class="eti">{H(inf.get("etiqueta") or "ETF")}</div><h1>{H(inf.get("titulo") or tk)}</h1>'
            f'{"<div class=res><ul>" + res + "</ul></div>" if res else ""}<div class="dcg">{dc}</div>'
            f'<section>{_parrafos(inf.get("intro"))}</section>{secs}{pc}{rg}{co}{fu}<div class="aviso">{H(AVISO)}</div></div>')


CSS = """
.ei{color:#0f172a;line-height:1.5}
.ei .top{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid #0f172a;padding-bottom:8px;margin-bottom:14px}
.ei .top .m{font-weight:800;font-size:15pt} .ei .top .m span{color:#2a78d6} .ei .top .f{font-size:10pt;color:#64748b;text-align:right}
.ei .eti{display:inline-block;background:#e0f2fe;color:#075985;font-weight:700;font-size:.78em;border-radius:999px;padding:3px 10px;margin-bottom:6px}
.ei h1{font-size:1.65em;line-height:1.2;margin:2px 0 10px;padding:0;font-weight:800}
.ei .res{background:#f1f5f9;border-radius:12px;padding:10px 16px;margin:0 0 14px} .ei .res ul{margin:0 0 0 18px} .ei .res li{margin:3px 0}
.ei .dcg{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 16px}
.ei .dc{border:1px solid #e3e8ee;border-radius:10px;padding:8px 10px;background:#fff} .ei .dc span{display:block;font-size:.78em;color:#64748b} .ei .dc b{font-size:.92em}
.ei p{text-align:justify;margin:0 0 9px}
.ei h2{font-size:1.06em;text-transform:uppercase;letter-spacing:.05em;border-left:5px solid #2a78d6;padding:0 0 0 9px;margin:20px 0 9px;font-weight:700;break-after:avoid}
.ei ul{margin:0 0 10px 18px;padding:0} .ei li{text-align:justify;margin:0 0 5px}
.ei .dona{display:flex;align-items:center;gap:22px;margin:6px 0 12px;break-inside:avoid} .ei .leyenda{flex:1}
.ei .ly{display:flex;align-items:center;gap:8px;font-size:.88em;margin:3px 0} .ei .ly i{width:12px;height:12px;border-radius:3px;flex:none} .ei .ly span{flex:1}
.ei table{width:100%;border-collapse:collapse;margin:4px 0 10px;font-size:.88em;break-inside:avoid}
.ei th{background:#d3e6fa;color:#1e3a5f;font-weight:600;padding:6px 8px;text-align:center;border:none} .ei td{padding:5px 8px;border:none;border-top:1px solid #eef1f5}
.ei .t10 td:first-child{color:#64748b;width:22px;text-align:center} .ei .tk{color:#64748b;font-size:.85em} .ei .n{text-align:center;white-space:nowrap}
.ei .bar{background:#eef2f7;border-radius:4px;height:9px;width:160px;max-width:30vw} .ei .bar i{display:block;height:9px;border-radius:4px;background:#2a78d6}
.ei .tot td{font-weight:700;border-top:2px solid #cbd5e1} .ei .up{color:#15803d;font-weight:700} .ei .dn{color:#b91c1c;font-weight:700}
.ei .chica{font-size:.78em;color:#64748b}
.ei .pc{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:6px 0 4px;break-inside:avoid} .ei .pc>div{border-radius:12px;padding:10px 14px}
.ei .rd{break-inside:avoid} .ei table.t10{break-inside:auto} .ei tr{break-inside:avoid} .ei .pc li{text-align:left} .ei .pc .p{background:#ecfdf3} .ei .pc .c{background:#fef2f2} .ei .pc h3{margin:0 0 6px;padding:0;font-size:.95em;font-weight:700} .ei .pc ul{margin:0 0 0 16px}
.ei .concl{break-inside:avoid;background:#0f172a;color:#fff;border-radius:12px;padding:12px 16px;margin-top:8px} .ei .concl p{color:#e5e7eb} .ei .concl h2{color:#fff;border-color:#60a5fa;margin-top:2px}
.ei .fu{font-size:.78em;color:#64748b;margin-top:14px} .ei .fu li{margin:2px 0}
.ei .aviso{font-size:.74em;color:#94a3b8;margin-top:10px;text-align:justify}
@media (max-width:700px){.ei .dcg{grid-template-columns:1fr 1fr}.ei .pc{grid-template-columns:1fr}.ei .dona{flex-direction:column;gap:8px}.ei .leyenda{width:100%}}
"""


def documento_html(ticker, inf):
    """Página completa, lista para imprimir en PDF (A4)."""
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{H(str(ticker).upper())} · Análisis del ETF</title>'
            '<link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;600;700;800&display=swap" rel="stylesheet">'
            "<style>@page{size:A4;margin:16mm 15mm}body{font-family:'Roboto Condensed',Arial,sans-serif;font-size:12.6pt;margin:0}"
            f"{CSS}</style></head><body>{cuerpo_html(ticker, inf)}</body></html>")


def app_html(ticker, inf):
    """Lo que va en la solapa de la app: el informe sin membrete, con su CSS."""
    return f"<style>{CSS}</style>{cuerpo_html(ticker, inf, membrete=False)}"


def validar(ticker, inf):
    """Lista de problemas (vacía si está bien). Las reglas de Guille: nada de «dosis chica», nada de nombres prohibidos en el texto."""
    prob = []
    for k in ("fecha", "titulo", "resumen", "datos_clave", "intro", "secciones", "conclusion", "fuentes"):
        if not inf.get(k):
            prob.append(f"falta {k}")
    if not fecha_iso(inf.get("fecha")):
        prob.append("fecha con formato raro")
    texto = json.dumps({k: v for k, v in inf.items() if k != "fuentes"}, ensure_ascii=False)
    for mala in ("dosis chica", "Damodaran", "Nelissen", "ojo", "remedios"):
        if re.search(rf"\b{mala}\b", texto, re.I):
            prob.append(f"palabra prohibida: {mala}")
    todo = " ".join(s.get("texto") or "" for s in inf.get("secciones") or [])
    for marca, campo in (("[[dona]]", "dona"), ("[[top10]]", "top10"), ("[[rend]]", "rend")):
        if marca in todo and not inf.get(campo):
            prob.append(f"{marca} sin datos")
    return prob
