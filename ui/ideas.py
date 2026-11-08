"""Ideas de Inversión (v1.5.44, pedido de Guille del 08/11/2026): mosaicos con dibujo, título, una frase y la cantidad; al tocar uno se abre la lista
de empresas (o ETFs, solo en «Dividendos Altos»). Las listas por años de aumento del dividendo vienen de data/ideas_listas.json (fuentes externas,
se actualizan a mano una vez por año); «Dividendos Altos» y «Fundamentales fuertes» salen de los datos de la app. Es información, no recomendación."""
import html
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_LISTAS = os.path.join(os.path.dirname(AQUI), "data", "ideas_listas.json")

UMBRAL_DY = 0.04            # «Dividendos Altos»: rendimiento por dividendo de 4% o más
INFRAVALORADAS = ("PODRÍA ESTAR INFRAVALORADA", "TENDENCIA A INFRAVALORADA")
CALIDADES_FUERTES = ("Excelente", "Muy buena")

# Dibujos propios, sobrios (no copian ningún sitio): sombrero de copa, corona, escalera con estrella, «4%+» y la foto del diamante con lupa.
_SVG = {
    "aristocratas": '''<svg viewBox="0 0 120 110" aria-hidden="true"><ellipse cx="60" cy="94" rx="47" ry="9" fill="#1e293b"/>
<path d="M36 92 L40 26 Q60 17 80 26 L84 92 Z" fill="#334155"/><path d="M40 26 Q60 17 80 26 L80.6 34 Q60 25 39.4 34 Z" fill="#475569"/>
<path d="M37.6 68 L82.4 68 L83.3 82 L36.7 82 Z" fill="#b8892e"/><path d="M46 30 L44 86" stroke="#64748b" stroke-width="3" stroke-linecap="round" opacity=".55"/></svg>''',
    "reyes": '''<svg viewBox="0 0 120 110" aria-hidden="true"><path d="M18 80 L24 30 L44 56 L60 22 L76 56 L96 30 L102 80 Z" fill="#d4a530" stroke="#8a6a1c" stroke-width="3" stroke-linejoin="round"/>
<rect x="17" y="80" width="86" height="15" rx="3" fill="#b8892e" stroke="#8a6a1c" stroke-width="3"/><circle cx="24" cy="29" r="5" fill="#8a6a1c"/><circle cx="60" cy="21" r="5" fill="#8a6a1c"/>
<circle cx="96" cy="29" r="5" fill="#8a6a1c"/><circle cx="40" cy="87.5" r="3.5" fill="#1d4ed8"/><circle cx="60" cy="87.5" r="3.5" fill="#b91c1c"/><circle cx="80" cy="87.5" r="3.5" fill="#15803d"/></svg>''',
    "aspirantes": '''<svg viewBox="0 0 120 110" aria-hidden="true"><rect x="14" y="78" width="16" height="18" rx="2" fill="#93c5fd"/><rect x="34" y="66" width="16" height="30" rx="2" fill="#60a5fa"/>
<rect x="54" y="52" width="16" height="44" rx="2" fill="#3b82f6"/><rect x="74" y="38" width="16" height="58" rx="2" fill="#2563eb"/>
<path d="M98 10 L102.6 20.4 L114 21.6 L105.4 29.2 L108 40.4 L98 34.6 L88 40.4 L90.6 29.2 L82 21.6 L93.4 20.4 Z" fill="#d4a530" stroke="#8a6a1c" stroke-width="2" stroke-linejoin="round"/>
<line x1="10" y1="97" x2="110" y2="97" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/></svg>''',
    "altos": '''<svg viewBox="0 0 120 110" aria-hidden="true"><text x="10" y="88" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="82" fill="#15803d">4</text>
<text x="62" y="92" font-family="Arial,sans-serif" font-weight="700" font-size="40" fill="#0e7490">%</text>
<path d="M92 14 v26 M79 27 h26" stroke="#0e7490" stroke-width="7" stroke-linecap="round"/></svg>''',
}

LISTAS = [
    {"clave": "reyes", "titulo": "Reyes del Dividendo",
     "desc": "Un club muy exclusivo: empresas que aumentaron su dividendo durante al menos 50 años seguidos."},
    {"clave": "aristocratas", "titulo": "Aristócratas del Dividendo",
     "desc": "Empresas del S&P 500 que aumentaron su dividendo todos los años durante al menos 25 años seguidos."},
    {"clave": "aspirantes", "titulo": "Aspirantes del Dividendo",
     "desc": "Empresas con una larga racha aumentando su dividendo todos los años que todavía no son Aristócratas ni Reyes: van en camino."},
    {"clave": "altos", "titulo": "Dividendos Altos",
     "desc": "Empresas y ETFs que hoy pagan un rendimiento por dividendo de 4% o más."},
    {"clave": "fundamentales", "titulo": "Fundamentales Fuertes",
     "desc": "Empresas con calidad Excelente o Muy buena en su Análisis Fundamental que, por múltiplos, podrían estar infravaloradas."},
]
_POR_CLAVE = {x["clave"]: x for x in LISTAS}


def cargar_listas(ruta=None):
    try:
        with open(ruta or RUTA_LISTAS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _n(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def dy_etf(d, precio_hoy=None):
    """v1.5.45: rendimiento por dividendo de un ETF como fracción (0,04 = 4%). Yahoo lo da en % con el precio del día en que se bajó;
    con el precio de hoy se recalcula (el dividendo anual no cambia: si el precio sube, el rendimiento baja). None si no reparte."""
    rto, p0, p1 = _n((d or {}).get("rendimiento")), _n((d or {}).get("precio")), _n(precio_hoy)
    if not rto or rto <= 0:
        return None
    return (rto / 100) * (p0 / p1) if (p0 and p1) else rto / 100


def miembros(clave, df, calidades=None, etfs=None, etfs_datos=None, listas=None, precios_etfs=None):
    """Filas de la lista: [{"tipo": "empresa"|"etf", "ticker", "row" (fila del cache o del ETF), "dato" (años / rendimiento / calidad), "dy"}], ya ordenadas.
    v1.5.45: Aristócratas y Reyes, por años (listas de Guille del 08/11/2026); Aspirantes = las de su lista que no son Aristócratas ni Reyes, por
    rendimiento; Dividendos Altos se arma en el momento con el rendimiento de hoy (empresas y ETFs)."""
    listas = listas if listas is not None else cargar_listas()
    calidades = calidades or {}
    filas = {str(r.get("ticker")): r for r in (df.to_dict("records") if df is not None and not df.empty else [])}
    dy = lambda r: _n(r.get("dividend_yield_actual"))   # noqa: E731
    out = []
    if clave in ("aristocratas", "reyes"):
        anios = (listas.get(clave) or {}).get("anios") or {}
        for t, a in anios.items():
            t2 = t.replace(".", "-")
            if t2 in filas:
                out.append({"tipo": "empresa", "ticker": t2, "row": filas[t2], "dato": int(a), "dy": dy(filas[t2])})
        out.sort(key=lambda x: (-x["dato"], x["ticker"]))
    elif clave == "aspirantes":
        fuera = set((listas.get("aristocratas") or {}).get("anios") or {}) | set((listas.get("reyes") or {}).get("anios") or {})
        for t in (listas.get("aspirantes") or {}).get("tickers") or []:
            t2 = t.replace(".", "-")
            if t2 in filas and t not in fuera:
                out.append({"tipo": "empresa", "ticker": t2, "row": filas[t2], "dato": dy(filas[t2]), "dy": dy(filas[t2])})
        out.sort(key=lambda x: (-(x["dato"] or 0), x["ticker"]))
    elif clave == "altos":
        for t, r in filas.items():
            v = dy(r)
            if v is not None and v >= UMBRAL_DY:
                out.append({"tipo": "empresa", "ticker": t, "row": r, "dato": v, "dy": v})
        for e in etfs or []:
            v = dy_etf((etfs_datos or {}).get(e.get("ticker")), (precios_etfs or {}).get(e.get("ticker")))
            if v is not None and v >= UMBRAL_DY:
                out.append({"tipo": "etf", "ticker": e["ticker"], "row": e, "dato": v, "dy": v})
        out.sort(key=lambda x: (-x["dato"], x["ticker"]))
    elif clave == "fundamentales":
        for t, r in filas.items():
            if r.get("categoria") in INFRAVALORADAS and calidades.get(t) in CALIDADES_FUERTES:
                p, fv = _n(r.get("precio_actual")), _n(r.get("fair_value"))
                out.append({"tipo": "empresa", "ticker": t, "row": r, "dato": calidades[t], "dy": dy(r), "_up": (fv / p - 1) if p and fv else 0})
        out.sort(key=lambda x: (-x["_up"], x["ticker"]))
    return out


CSS = """
.id-w{max-width:1120px;margin:0 auto 40px;padding:0 4px}
.id-w h2{font-size:1.9rem;margin:0 0 2px;padding-top:0!important;color:#0f172a}
.id-w>p.id-sub{margin:0 0 16px;color:#475569;font-size:1.02rem}
.id-g{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}
a.id-t{display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px;background:#fff;border:1px solid #e3e8ee;border-radius:16px;padding:16px 22px 14px;
  text-decoration:none!important;color:#1f2937!important;transition:box-shadow .15s,transform .15s}
a.id-t:hover{box-shadow:0 10px 28px rgba(15,23,42,.12);transform:translateY(-2px)}
.id-ic{height:100px;display:flex;align-items:center;justify-content:center}
.id-ic svg{width:110px;height:100px}
.id-ic img{height:96px;border-radius:12px;object-fit:cover}
.id-tt{font-size:1.32rem;font-weight:800;color:#0e7490;text-decoration:underline;text-underline-offset:4px;text-decoration-thickness:2px}
.id-d{font-size:1rem;line-height:1.45;color:#334155;max-width:330px}
.id-c{font-size:.95rem;color:#94a3b8}
.id-vol{display:inline-flex;align-items:center;gap:6px;font-weight:700;color:#1f2937!important;text-decoration:none!important}
.id-tw{border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 8px 22px rgba(15,23,42,.07);background:#fff}
.id-tab{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border-radius:14px}
.id-tab thead th{background:#d3e6fa;color:#1e3a5f;font-size:14.5px;font-weight:600;text-align:center;padding:0;position:relative;vertical-align:middle}
.id-tab thead th:first-child{border-radius:14px 0 0 0}.id-tab thead th:last-child{border-radius:0 14px 0 0}
.id-tab thead th a{display:flex;align-items:center;justify-content:center;gap:5px;min-height:46px;padding:4px 8px;color:#1e3a5f!important;text-decoration:none!important;line-height:1.2}
.id-tab thead th a:hover{background:rgba(30,64,120,.10)}
.id-fl{font-size:9px;opacity:.45}.id-on .id-fl{font-size:10px;opacity:1}
.id-tab thead th[data-tip]:hover::after{content:attr(data-tip);position:absolute;top:calc(100% + 6px);left:50%;margin-left:-135px;width:270px;box-sizing:border-box;z-index:300;
  background:#1f2937;color:#fff;font-size:.8rem;font-weight:400;line-height:1.4;text-align:left;white-space:normal;padding:9px 12px;border-radius:8px;
  box-shadow:0 8px 22px rgba(15,23,42,.35);pointer-events:none;animation:idtip .16s ease .3s both}
.id-tab thead th.id-tip-izq:hover::after{left:0;margin-left:0}.id-tab thead th.id-tip-der:hover::after{left:auto;right:0;margin-left:0}
@keyframes idtip{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.id-tab td{padding:9px 12px;border-top:1px solid #eef1f5;vertical-align:middle;font-size:14.5px;text-align:center}
.id-tab tbody tr:nth-child(even) td{background:#f6f9fc}
.id-tab td.id-c-nombre,.id-tab td.id-c-sector{text-align:left}
.id-tab tbody tr:last-child td:first-child{border-radius:0 0 0 14px}.id-tab tbody tr:last-child td:last-child{border-radius:0 0 14px 0}
.id-tab .tv2-vc{text-align:center}.id-tab .tv2-vc *{white-space:nowrap}
.id-tab .tv-score{width:auto;min-width:54px;border:0;border-radius:999px;background:#e9edf2;padding:3px 12px 4px;overflow:visible;margin:0 auto}
.id-tab .tv-num{font-size:19px;line-height:22px;font-weight:700;color:#1f2937}
.id-tab .tv-met{background:transparent!important;color:#6b7280;font-size:10.5px;line-height:12px}
.id-tab th.id-c-tipo,.id-tab th.id-c-score,.id-tab th.id-c-dy,.id-tab th.id-c-anios{width:1%}
.id-tab th.id-c-tipo a,.id-tab th.id-c-score a,.id-tab th.id-c-dy a,.id-tab th.id-c-anios a{white-space:nowrap}
.id-nd{color:#9ca3af}
.id-tipo{display:inline-block;font-size:.78rem;font-weight:700;border-radius:999px;padding:3px 10px;background:#eef2f7;color:#334155}
.id-tipo-etf{background:#e0f2fe;color:#075985}
.id-nota{font-size:.88rem;color:#64748b;margin-top:12px;line-height:1.5;text-align:justify}
.id-cab{display:flex;align-items:center;gap:16px;margin:2px 0 12px}
.id-cab .id-ic{height:76px}.id-cab .id-ic svg{width:84px;height:76px}.id-cab .id-ic img{height:72px}
.id-cab h2{margin:0}
.id-cab p{margin:4px 0 0;color:#475569}
.id-tab .etf-lg{width:26px;height:26px;flex:none;overflow:hidden;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0}
.id-tab .etf-lg img,.id-tab .etf-lg svg{width:100%;height:100%;object-fit:contain}
.id-etf{font-size:.72rem;font-weight:800;background:#e0f2fe;color:#075985;border-radius:999px;padding:2px 7px;margin-left:6px}
.id-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 2px}   /* v1.5.46: título (o «← Ideas») y la casita en la misma fila, más arriba */
.id-top .vol-ini{flex:none}
@media (max-width:900px){.id-g{grid-template-columns:1fr}.id-w{margin-top:-20px}.id-tw{overflow-x:auto}.id-tab .id-c-sector,.id-tab .id-c-score{display:none}.id-tab td,.id-tab thead th a{padding-left:6px;padding-right:6px;font-size:13px}}
"""


CASITA = ('<a class="vol-ini" href="?inicio=0" target="_self" title="Volver al inicio"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
          'stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>Volver al inicio</a>')


def _icono(clave, static_url="app/static/ideas"):
    if clave == "fundamentales":
        return f'<img src="{static_url}/diamante.png" alt="">'
    return " ".join(_SVG.get(clave, "").split())      # en una sola línea: el markdown de Streamlit corta el SVG en los saltos de línea


def mosaicos_html(conteos):
    t = []
    for x in LISTAS:
        n = conteos.get(x["clave"], 0)
        unidad = "empresas y ETFs" if x["clave"] == "altos" else "empresas"
        t.append(f'<a class="id-t" href="?pagina=ideas&lista={x["clave"]}" target="_self"><div class="id-ic">{_icono(x["clave"])}</div>'
                 f'<span class="id-tt">{html.escape(x["titulo"])}</span><span class="id-d">{html.escape(x["desc"])}</span>'
                 f'<span class="id-c">{n} {unidad}</span></a>')
    return (f'<div class="id-w"><h2>Ideas de Inversión</h2><p class="id-sub">Listas de empresas y ETFs agrupadas por tema. Tocá una para ver quiénes la forman.</p>'
            f'<div class="id-g">{"".join(t)}</div>'
            '<p class="id-nota">Información con fines educativos: no es una recomendación de compra ni de venta. Cada lista muestra solo las empresas y ETFs '
            'que cotizan como CEDEAR y están en TodoCedears.</p></div>')


# v1.5.47 (Guille): las tablas de Ideas con la misma estética que la tabla principal (títulos celestes centrados, explicación al pasar el mouse,
# orden al tocar el título) y, en las listas que mezclan empresas y ETFs, una columna «Tipo».
AYUDAS = {
    "nombre": ("Empresa", "Presioná en la empresa (o en el ETF) para ver su información detallada."),
    "tipo": ("Tipo", "Si es una empresa (acción, vía CEDEAR) o un ETF (un fondo que reúne muchas acciones o bonos)."),
    "sector": ("Sector e Industria", "A qué se dedica la empresa: su sector y su industria. En los ETFs, su categoría."),
    "anios": ("Años seguidos aumentando", "Cuántos años seguidos la empresa aumentó su dividendo, según la lista de referencia."),
    "calidad": ("Calidad del negocio", "La calidad que le asigna el Análisis Fundamental de la empresa."),
    "valoracion": ("Valoración", "Una estimación, no una recomendación: si la empresa cotiza barata, razonable o cara frente a sus propios múltiplos históricos."),
    "score": ("Puntaje de calidad", "De 0 (más cara) a 100 (más barata), el puntaje de la tabla principal. Abajo, cuántas métricas se pudieron usar."),
    "dy": ("Dividend Yield", "El dividendo anual dividido por el precio de hoy: cuánto rinde por año en dividendos lo que pagás hoy por la acción o el ETF."),
}
_ORDEN_CAL = {"Excelente": 3, "Muy buena": 2, "Buena": 1}


def columnas_lista(clave):
    """Columnas de cada lista, en orden (claves de AYUDAS)."""
    c = ["nombre"] + (["tipo"] if clave == "altos" else []) + ["sector"]
    c += {"reyes": ["anios"], "aristocratas": ["anios"], "fundamentales": ["calidad"]}.get(clave, [])
    return c + ["valoracion", "score", "dy"]


def orden_inicial(clave):
    return {"reyes": ("anios", False), "aristocratas": ("anios", False), "fundamentales": ("valoracion", False)}.get(clave, ("dy", False))


def _valor_orden(col, f):
    r = f["row"]
    if col == "nombre":
        return str(r.get("nombre") or f["ticker"]).lower()
    if col == "tipo":
        return f["tipo"]
    if col == "sector":
        return str(r.get("sector") if f["tipo"] == "empresa" else r.get("categoria") or "").lower()
    if col == "anios":
        return f["dato"] if isinstance(f["dato"], (int, float)) else None
    if col == "calidad":
        return _ORDEN_CAL.get(f["dato"] if isinstance(f["dato"], str) else "", 0)
    if col == "valoracion":
        return _n(r.get("fv_upside")) if f["tipo"] == "empresa" else None
    if col == "score":
        return _n(r.get("score_total")) if f["tipo"] == "empresa" else None
    if col == "dy":
        return f.get("dy")
    return None


def ordenar(filas, col, asc):
    """Ordena las filas por la columna; las que no tienen dato van siempre al final."""
    con = [f for f in filas if _valor_orden(col, f) is not None]
    sin = [f for f in filas if _valor_orden(col, f) is None]
    con.sort(key=lambda f: (_valor_orden(col, f), f["ticker"]), reverse=not asc)
    return con + sin


def lista_html(clave, filas, listas=None, celda_empresa=None, celda_sector=None, celda_categoria=None, logo_etf=None, celda_puntaje=None,
               orden=None, asc=None):
    """Tabla de la lista. Las celdas de empresa, sector, valoración y puntaje se reciben de ui/tabla_visual.py (mismo aspecto que la tabla principal).
    `orden`/`asc`: columna y sentido (de ?orden=…&dir=asc|desc); al tocar un título se ordena por esa columna (y otra vez, al revés)."""
    x = _POR_CLAVE.get(clave)
    if not x:
        return ""
    listas = listas if listas is not None else cargar_listas()
    cols = columnas_lista(clave)
    o0, a0 = orden_inicial(clave)
    orden = orden if orden in cols else o0
    asc = a0 if (asc is None or orden == o0 and asc is None) else bool(asc)
    filas = ordenar(filas, orden, asc)
    pct = lambda v: (f"{v * 100:.2f}%" if v is not None else '<span class="id-nd">—</span>')   # noqa: E731
    cuerpo = []
    for f in filas:
        r = f["row"]
        es_etf = f["tipo"] == "etf"
        cel = {}
        if es_etf:
            t = html.escape(f["ticker"])
            cel["nombre"] = (f'<a class="tv2-l1" href="?etf={t}" target="_self" style="display:flex;align-items:center;gap:10px">{logo_etf(r) if logo_etf else ""}'
                             f'<span class="tv2-nm">{html.escape(str(r.get("nombre") or t))}</span><span class="tv2-pt">·</span><span class="tv2-tk">{t}</span></a>')
            cel["sector"] = html.escape(str(r.get("categoria") or "—"))
            cel["valoracion"] = cel["score"] = '<span class="id-nd">—</span>'
        else:
            cel["nombre"] = celda_empresa(r) if celda_empresa else html.escape(f["ticker"])
            cel["sector"] = celda_sector(r) if celda_sector else ""
            cel["valoracion"] = celda_categoria(r) if celda_categoria else html.escape(str(r.get("categoria") or ""))
            cel["score"] = celda_puntaje(r) if celda_puntaje else html.escape(str(r.get("score_total") or "—"))
        cel["tipo"] = f'<span class="id-tipo {"id-tipo-etf" if es_etf else ""}">{"ETF" if es_etf else "Empresa"}</span>'
        cel["anios"] = f'<b>{f["dato"]}</b>' if isinstance(f["dato"], (int, float)) else "—"
        cel["calidad"] = f'<b>{html.escape(str(f["dato"]))}</b>' if isinstance(f["dato"], str) else "—"
        cel["dy"] = pct(f.get("dy"))
        cuerpo.append("<tr>" + "".join(f'<td class="id-c-{c}">{cel[c]}</td>' for c in cols) + "</tr>")
    if not cuerpo:
        cuerpo.append(f'<tr><td colspan="{len(cols)}" style="text-align:center;color:#64748b;padding:22px">Hoy no hay empresas que cumplan esta condición.</td></tr>')
    cab = []
    n = len(cols)
    for i, c in enumerate(cols):
        tit, ayuda = AYUDAS[c]
        activo = c == orden
        nuevo_asc = (not asc) if activo else (c in ("nombre", "tipo", "sector"))
        flecha = ("▴" if asc else "▾") if activo else "▾"
        lado = "id-tip-izq" if i == 0 else ("id-tip-der" if i >= n - 2 else "")
        href = f"?pagina=ideas&lista={clave}&orden={c}&dir={'asc' if nuevo_asc else 'desc'}"
        cab.append(f'<th class="id-c-{c} {lado}{" id-on" if activo else ""}" data-tip="{html.escape(tit + ". " + ayuda, quote=True)}">'
                   f'<a href="{href}" target="_self">{html.escape(tit)}<span class="id-fl">{flecha}</span></a></th>')
    notas = []
    info = listas.get(clave) or {}
    if info.get("fuente"):
        notas.append(f'Fuente de la lista: {html.escape(info["fuente"])}, al {html.escape(str(info.get("fecha") or ""))}. Se muestran solo las que se pueden comprar como CEDEAR.')
    if clave in ("aristocratas", "reyes", "aspirantes", "altos"):
        notas.append("El rendimiento por dividendo es el de hoy: el dividendo anual dividido por el precio actual, así que cambia día a día con el precio.")
    if clave == "altos":
        notas.append("Un dividendo muy alto no siempre es una buena noticia: a veces refleja que el precio cayó por problemas en el negocio, o que el pago "
                     "no se puede sostener. En algunos ETFs (por ejemplo, los que invierten en contratos de futuros) lo que distribuyen no proviene de dividendos de empresas.")
    if clave == "fundamentales":
        notas.append("La calidad sale del Análisis Fundamental de cada empresa y la valoración, de los múltiplos de la app.")
    notas.append("Tocá el título de una columna para ordenar la tabla. Información con fines educativos: no es una recomendación de compra ni de venta.")
    return (f'<div class="id-w">'
            f'<div class="id-cab"><div class="id-ic">{_icono(clave)}</div><div><h2>{html.escape(x["titulo"])}</h2><p>{html.escape(x["desc"])}</p></div></div>'
            f'<div class="id-tw"><table class="id-tab"><thead><tr>{"".join(cab)}</tr></thead>'
            f'<tbody>{"".join(cuerpo)}</tbody></table></div><p class="id-nota">{" ".join(notas)}</p></div>')
