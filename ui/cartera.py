"""Tu cartera (v1.2.73): la persona pone su edad y su perfil, sube su cartera (Excel o CSV, o la pega como texto) y la app devuelve una ORIENTACION: en qué
tipo de activo se está pasando o le falta peso, cómo está repartida la renta variable (geografía y tipo de empresa), si hay posiciones muy concentradas y
qué dice el screener de las empresas que tiene. Sin recomendaciones de compra o venta y SIN mostrar las carteras de referencia (data/carteras_modelo.py).
Todo se calcula con reglas (sin IA paga) y la cartera no se guarda. Las funciones de acá no usan Streamlit: se prueban solas."""
import html
import io
import re
import unicodedata

from data import carteras_modelo as CM

CLASES = {"rf": "Renta fija", "rv": "Renta variable", "oro": "Oro", "cripto": "Criptoactivos", "efectivo": "Efectivo y liquidez", "otros": "Otras materias primas"}

SUPERSECTOR_DE = {   # sector de la app -> supersector (estructura Cíclico / Sensible / Defensivo)
    "Materiales Básicos": "ciclico", "REITs": "ciclico", "Bancos y seguros": "ciclico", "Pagos y datos": "ciclico", "Consumo Discrecional": "ciclico",
    "Comunicación": "sensible", "Telecomunicaciones": "sensible", "Industrial": "sensible", "Semiconductores": "sensible", "Software y nube": "sensible",
    "Hardware y servicios TI": "sensible", "Energía": "sensible",
    "Consumo Básico": "defensivo", "Salud": "defensivo", "Utilities": "defensivo",
}
NOMBRE_SUPER = {"ciclico": "cíclico", "sensible": "sensible", "defensivo": "defensivo"}
_USA = {"united states", "estados unidos", "usa", "ee uu", "eeuu", "us"}
_EMERGENTES = {"brazil", "brasil", "china", "india", "taiwan", "taiwán", "mexico", "méxico", "south korea", "corea del sur", "south africa", "sudafrica", "sudáfrica",
               "argentina", "uruguay", "chile", "colombia", "peru", "perú", "indonesia", "thailand", "tailandia", "turkey", "turquia", "turquía", "saudi arabia", "arabia saudita",
               "united arab emirates", "emiratos arabes unidos", "philippines", "filipinas", "hong kong"}


def norm(t):
    s = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%.,\- ]", " ", s)).strip()


def clave_tk(t):
    return re.sub(r"[^A-Z0-9]", "", str(t or "").upper())


# --- lectura de la cartera --------------------------------------------------------------------------------------------------------

def numero(x):
    """Numero desde 1.234,56 / 1,234.56 / 12,5 % / 3000; None si no se puede."""
    if isinstance(x, (int, float)):
        return float(x) if x == x else None
    t = str(x or "").strip().replace("%", "").replace("$", "").replace("US", "").replace("u$s", "").strip()
    if not t or not re.search(r"\d", t):
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        partes = t.split(",")
        t = t.replace(",", ".") if len(partes) == 2 and len(partes[1]) != 3 else t.replace(",", "")
    elif t.count(".") > 1 or (t.count(".") == 1 and len(t.split(".")[1]) == 3 and len(t.split(".")[0]) <= 3 and False):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def _columnas(cols):
    """(indice del ticker, del monto, del tipo) segun los encabezados; None si no se reconocen."""
    n = [norm(c) for c in cols]

    def buscar(claves):
        for i, c in enumerate(n):
            if any(k in c for k in claves):
                return i
        return None
    return (buscar(("ticker", "simbolo", "especie", "activo", "instrumento", "nombre")), buscar(("monto", "valor", "importe", "total", "tenencia", "valuacion", "valorizado", "peso", "%")),
            buscar(("tipo", "clase", "categoria")))


def leer_tabla(filas):
    """`filas`: lista de listas (la primera puede ser el encabezado). Devuelve [{'ticker', 'monto', 'tipo'}] con monto > 0."""
    filas = [list(f) for f in filas if f and any(str(c or "").strip() for c in f)]
    if not filas:
        return []
    it, im, ity = _columnas(filas[0])
    datos = filas[1:] if (it is not None and im is not None) else filas
    if it is None or im is None:
        it, im, ity = 0, 1, (2 if any(len(f) > 2 for f in filas) else None)
    out = []
    for f in datos:
        if max(it, im) >= len(f):
            continue
        tk, m = str(f[it] or "").strip(), numero(f[im])
        if not tk or m is None or m <= 0:
            continue
        tipo = str(f[ity] or "").strip() if ity is not None and ity < len(f) else ""
        out.append({"ticker": tk, "monto": m, "tipo": tipo})
    return out


def leer_texto(texto):
    """Cartera pegada como texto: una posicion por linea ('AAPL 1500', 'SPY: 20%', 'AL30;2000;bono soberano')."""
    filas = []
    for linea in str(texto or "").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        partes = [p.strip() for p in re.split(r"[;\t|]+", linea)] if re.search(r"[;\t|]", linea) else None
        if partes is None:
            m = re.match(r"^([A-Za-z0-9.\-]+)\s*[:=\-]?\s+(.+)$", linea)
            partes = [m.group(1), m.group(2)] if m else [linea]
        filas.append(partes)
    return leer_tabla(filas)


def leer_archivo(nombre, datos):
    """Posiciones desde un .xlsx / .xls / .csv (bytes). Lanza ValueError con un mensaje claro si no se puede leer."""
    import pandas as pd
    n = str(nombre or "").lower()
    try:
        if n.endswith(".csv") or n.endswith(".txt"):
            txt = datos.decode("utf-8-sig", "replace") if isinstance(datos, (bytes, bytearray)) else str(datos)
            sep = ";" if txt.count(";") > txt.count(",") else ","
            df = pd.read_csv(io.StringIO(txt), sep=sep, header=None, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(io.BytesIO(datos), header=None, dtype=str, keep_default_na=False)
    except Exception as e:  # noqa: BLE001
        raise ValueError("No pude leer el archivo. Probá con el Excel de ejemplo (botón de arriba) o con un .csv.") from e
    return leer_tabla(df.values.tolist())


def plantilla_excel():
    """Bytes de un .xlsx de ejemplo (Ticker, Monto, Tipo)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Cartera"
    ws.append(["Ticker", "Monto", "Tipo (opcional)"])
    for r in (("AAPL", 1500, ""), ("KO", 800, ""), ("SPY", 3000, ""), ("AL30", 2000, "Renta fija soberana"), ("ON YPF", 1000, "Renta fija corporativa"),
              ("GLD", 500, "Oro"), ("BTC", 300, "Cripto"), ("Dólares", 700, "Efectivo")):
        ws.append(list(r))
    ws.append([])
    ws.append(["Montos: el valor actual de cada tenencia, todos en la misma moneda (dólares o pesos). El Tipo solo hace falta para lo que no es una empresa o ETF "
               "de la lista (bonos, obligaciones negociables, efectivo)."])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 26
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


# --- clasificacion ----------------------------------------------------------------------------------------------------------------

def clase_de_tipo(tipo):
    """Clase ('rf', 'rv', 'oro', 'cripto', 'efectivo') a partir de lo que escribió la persona en 'Tipo'; None si no se entiende."""
    t = norm(tipo)
    if not t:
        return None
    if any(k in t for k in ("cripto", "bitcoin", "ether", "btc", "eth")):
        return "cripto"
    if re.search(r"\b(oro|gold)\b", t):
        return "oro"
    if any(k in t for k in ("efectivo", "cash", "liquidez", "dolar", "peso", "plazo fijo", "money market", "caja")):
        return "efectivo"
    if any(k in t for k in ("renta fija", "bono", "sobera", "corpor", "obligacion", "letra", "lecap", "tesoro", "treasury", "on ")) or t in ("rf", "on"):
        return "rf"
    if any(k in t for k in ("accion", "cedear", "etf", "renta variable", "rv", "fondo")):
        return "rv"
    return None


def clasificar(pos, empresas, etfs):
    """Agrega a la posicion: 'clase' (o None), 'fuente' ('empresa' | 'etf' | 'tipo' | 'regla'), 'info' (datos de la empresa si es una de la lista).
    `empresas`: {CLAVE_TICKER: {nombre, sector, pais, categoria}}; `etfs`: {CLAVE_TICKER: {categoria, ...}}."""
    tk = clave_tk(pos["ticker"])
    pos = dict(pos)
    pos["clase"], pos["fuente"], pos["info"] = None, None, None
    por_tipo = clase_de_tipo(pos.get("tipo"))
    if tk in empresas and por_tipo in (None, "rv"):
        pos.update(clase="rv", fuente="empresa", info=empresas[tk], ticker=str(pos["ticker"]).upper())
    elif tk in etfs and por_tipo in (None, "rv", "oro", "cripto"):
        cat = norm(etfs[tk].get("categoria"))
        clase = "oro" if tk in ("GLD", "IAU", "GLDM") else "cripto" if "cripto" in cat else "otros" if "materias primas" in cat else "rv"
        pos.update(clase=clase, fuente="etf", ticker=str(pos["ticker"]).upper())
    elif por_tipo:
        pos.update(clase=por_tipo, fuente="tipo")
    elif (" " in norm(pos["ticker"]) or len(norm(pos["ticker"])) >= 5 or norm(pos["ticker"]) in ("oro", "cash", "on")) and clase_de_tipo(pos["ticker"]):      # el nombre mismo lo dice: "Dólares", "ON YPF", "Bono AL30", "Plazo fijo"
        pos.update(clase=clase_de_tipo(pos["ticker"]), fuente="tipo")
    elif re.match(r"^(AL|GD|AE)\d{2}[DC]?$", tk):
        pos.update(clase="rf", fuente="regla")
    elif tk in ("BTC", "ETH", "BTCUSD", "ETHUSD", "BITCOIN", "ETHEREUM"):
        pos.update(clase="cripto", fuente="regla")
    return pos


def region(pais):
    p = norm(pais)
    return "usa" if p in _USA else "emergentes" if p in _EMERGENTES else "desarrollados" if p else None


def valoracion(categoria):
    c = str(categoria or "").upper()
    return "infravalorada" if "INFRAVALORADA" in c else "sobrevalorada" if "SOBREVALORADA" in c else "bien valuada" if "BIEN VALUADA" in c else None


# --- analisis ---------------------------------------------------------------------------------------------------------------------

UMBRAL = 5.0          # puntos de diferencia a partir de los cuales se avisa (la devolución es una orientación, no un cálculo fino)


def analizar(posiciones, edad, perfil, empresas, etfs):
    """Resultado con los porcentajes de la cartera, los desvios contra la referencia (interna) y los detalles; None si la edad no es valida o no hay nada para analizar."""
    ref = CM.referencia(edad, perfil)
    if not ref or not posiciones:
        return None
    cl = [clasificar(p, empresas, etfs) for p in posiciones]
    sin = [p for p in cl if not p["clase"]]
    ok = [p for p in cl if p["clase"]]
    total = sum(p["monto"] for p in ok)
    if total <= 0:
        return {"sin_clasificar": sin, "total": 0}
    peso = {k: 0.0 for k in CLASES}
    for p in ok:
        peso[p["clase"]] += p["monto"] / total * 100
    # comparacion: el efectivo cuenta como renta fija (liquidez), las otras materias primas no se comparan
    cmp_real = {"rf": peso["rf"] + peso["efectivo"], "rv": peso["rv"], "oro": peso["oro"], "cripto": peso["cripto"]}
    nombre_rango, carts = ref
    desvio = {k: cmp_real[k] - carts[k] for k in cmp_real}
    emp = [p for p in ok if p["fuente"] == "empresa"]
    rv_total = sum(p["monto"] for p in ok if p["clase"] == "rv")
    emp_total = sum(p["monto"] for p in emp)
    geo = {"usa": 0.0, "desarrollados": 0.0, "emergentes": 0.0}
    sup = {"ciclico": 0.0, "sensible": 0.0, "defensivo": 0.0}
    sect = {}
    for p in emp:
        g = region(p["info"].get("pais"))
        if g:
            geo[g] += p["monto"]
        s = p["info"].get("sector")
        if SUPERSECTOR_DE.get(s):
            sup[SUPERSECTOR_DE[s]] += p["monto"]
            sect[s] = sect.get(s, 0.0) + p["monto"]
    gt, st_ = sum(geo.values()), sum(sup.values())
    por_pos = sorted(ok, key=lambda p: -p["monto"])
    val = {"infravalorada": [], "bien valuada": [], "sobrevalorada": []}
    for p in emp:
        v = valoracion(p["info"].get("categoria"))
        if v:
            val[v].append(p)
    return {
        "rango": nombre_rango, "total": total, "peso": peso, "desvio": desvio,
        "rv_empresas_pct": (emp_total / rv_total * 100) if rv_total else 0.0, "n_empresas": len(emp), "rv_total": rv_total,
        "geo": {k: v / gt * 100 for k, v in geo.items()} if gt else None, "super": {k: v / st_ * 100 for k, v in sup.items()} if st_ else None,
        "sector_top": (max(sect.items(), key=lambda kv: kv[1])[0], max(sect.values()) / st_ * 100) if sect and st_ else None,
        "posiciones": [{"ticker": p["ticker"], "pct": p["monto"] / total * 100, "clase": p["clase"]} for p in por_pos],
        "valoracion": val, "sin_clasificar": sin, "pct_sin_clasificar": (sum(p["monto"] for p in sin) / (total + sum(p["monto"] for p in sin)) * 100) if sin else 0.0,
    }


def _pts(x):
    return f"{abs(x):.0f}"


def devolucion(res, edad, perfil):
    """[(titulo, [frases])] con la orientación, en castellano simple. Sin recomendaciones de compra o venta y sin las carteras de referencia."""
    sec = []
    if not res or not res.get("total"):
        return sec
    pe = res["peso"]
    comp = [f"{CLASES[k]} {pe[k]:.0f} %" for k in ("rv", "rf", "oro", "cripto", "efectivo", "otros") if pe[k] >= 0.5]
    perf = f", perfil {perfil.lower()}" if perfil and any(len(c[3]) > 1 for c in CM.RANGOS if c[0] <= int(edad) <= c[1]) else ""
    sec.append(("Tu cartera de un vistazo", [f"Para una persona de {int(edad)} años{perf}, tu cartera está repartida así: " + ", ".join(comp) + "."]))
    # --- peso de cada tipo de activo
    f = []
    d = res["desvio"]
    nombres = {"rv": "renta variable", "rf": "renta fija (con el efectivo)", "oro": "oro", "cripto": "criptoactivos"}
    for k in ("rv", "rf", "oro", "cripto"):
        if d[k] > UMBRAL:
            f.append(f"**{nombres[k].capitalize()}: te pasás unos {_pts(d[k])} puntos** respecto de lo que suele ser razonable para tu edad y tu perfil.")
        elif d[k] < -UMBRAL:
            f.append(f"**{nombres[k].capitalize()}: te faltan unos {_pts(d[k])} puntos** respecto de lo que suele ser razonable para tu edad y tu perfil.")
    if not f:
        f.append("**En los grandes grupos (renta variable, renta fija, oro y criptoactivos) estás en línea** con lo que suele ser razonable para tu edad y tu perfil.")
    else:
        pasa = [k for k in ("rv", "rf", "oro", "cripto") if d[k] > UMBRAL]
        falta = [k for k in ("rv", "rf", "oro", "cripto") if d[k] < -UMBRAL]
        if pasa and falta:
            f.append(f"Una orientación: si quisieras acercarte, el ajuste iría de **{nombres[pasa[0]]}** hacia **{nombres[falta[0]]}**; hacerlo de a poco y por partes evita decidir todo en un mismo día.")
        elif pasa:
            f.append(f"Una orientación: si quisieras acercarte, bajar el peso de **{nombres[pasa[0]]}** (y mandar esa parte a lo que más te falta).")
        elif falta:
            f.append(f"Una orientación: si quisieras acercarte, subir de a poco el peso de **{nombres[falta[0]]}** (con lo que se libere de lo que más pesa).")
    if pe["cripto"] > 10:
        f.append("Los criptoactivos son muy volátiles: con más de un 10 % de la cartera, una caída fuerte se siente mucho en el total.")
    if pe["efectivo"] > 20:
        f.append(f"Tenés {pe['efectivo']:.0f} % en efectivo: es seguridad, pero sin rendimiento propio; conviene que sea una decisión y no un descuido.")
    if pe["otros"] >= 5:
        f.append(f"Tenés {pe['otros']:.0f} % en otras materias primas (petróleo, granos…): no son ni renta fija ni variable típica y no las comparé con tu edad y perfil.")
    sec.append(("Cuánto pesa cada tipo de activo", f))
    # --- renta variable por dentro
    f = []
    if res["n_empresas"] and res["geo"]:
        g = res["geo"]
        f.append(f"De tu renta variable, **{res['rv_empresas_pct']:.0f} %** está en empresas individuales de la lista de TodoCedears ({res['n_empresas']}); el resto son ETFs u otros activos, que no abrí por dentro.")
        if g["usa"] > CM.GEOGRAFIA["usa"] + 12:
            f.append(f"**Geografía:** {g['usa']:.0f} % de tus empresas son de Estados Unidos: está muy concentrado ahí. Hay margen para diversificar hacia otros países desarrollados y, en menor medida, emergentes.")
        elif g["usa"] < CM.GEOGRAFIA["usa"] - 25:
            f.append(f"**Geografía:** solo {g['usa']:.0f} % de tus empresas son de Estados Unidos, el mercado más grande y profundo; revisá si la diferencia es una decisión tuya.")
        else:
            f.append(f"**Geografía:** {g['usa']:.0f} % Estados Unidos, {g['desarrollados']:.0f} % otros países desarrollados y {g['emergentes']:.0f} % emergentes: razonablemente repartido.")
        if g["emergentes"] > CM.GEOGRAFIA["emergentes"] + 12:
            f.append(f"Los emergentes pesan {g['emergentes']:.0f} % de tus empresas: más riesgo y más volatilidad que lo habitual.")
        if res["super"]:
            s = res["super"]
            if s["defensivo"] < CM.SUPERSECTOR["defensivo"] - 20:
                f.append(f"**Tipo de empresa:** solo {s['defensivo']:.0f} % es defensivo (consumo básico, salud, servicios públicos), las que mejor aguantan cuando la economía se enfría. "
                         f"Hoy tenés {s['sensible']:.0f} % sensible (tecnología, industria, energía, comunicación) y {s['ciclico']:.0f} % cíclico (financieras, consumo discrecional, materiales, inmobiliarias): una cartera que depende bastante del ciclo económico.")
            elif s["defensivo"] > CM.SUPERSECTOR["defensivo"] + 20:
                f.append(f"**Tipo de empresa:** {s['defensivo']:.0f} % es defensivo: aguanta bien las caídas, pero puede quedarse atrás cuando el mercado sube con fuerza. Tenés {s['sensible']:.0f} % sensible y {s['ciclico']:.0f} % cíclico.")
            else:
                f.append(f"**Tipo de empresa:** {s['defensivo']:.0f} % defensivo, {s['sensible']:.0f} % sensible y {s['ciclico']:.0f} % cíclico: equilibrado.")
        if res["sector_top"] and res["sector_top"][1] > 40:
            f.append(f"**Un solo sector pesa mucho:** {res['sector_top'][0]} es el {res['sector_top'][1]:.0f} % de tus empresas.")
    elif pe["rv"] > 0:
        f.append("Tu renta variable no tiene empresas de la lista de TodoCedears (o son solo ETFs), así que no pude abrirla por país ni por tipo de empresa.")
    if f:
        sec.append(("Tu renta variable por dentro", f))
    # --- concentracion
    f = []
    ps = res["posiciones"]
    if ps and ps[0]["pct"] > 15:
        f.append(f"**Tu mayor posición, {ps[0]['ticker']}, pesa {ps[0]['pct']:.0f} %** de la cartera: si le va mal, se nota mucho en el total.")
    top3 = sum(p["pct"] for p in ps[:3])
    if len(ps) >= 4 and top3 > 50:
        f.append(f"Tus 3 posiciones más grandes suman {top3:.0f} %: la cartera depende de pocas ideas.")
    if len(ps) < 5:
        f.append(f"Tenés {len(ps)} posiciones: con tan pocas, cada una pesa mucho.")
    if not f:
        f.append("No veo una posición que domine la cartera: la concentración está razonablemente repartida.")
    sec.append(("Concentración", f))
    # --- que dice el screener
    v = res["valoracion"]
    if any(v.values()):
        f = [f"De las empresas que tenés, hoy el screener (por múltiplos) muestra: **{len(v['infravalorada'])} con precio por debajo de su valor estimado**, {len(v['bien valuada'])} razonables y **{len(v['sobrevalorada'])} por encima**. Es información, no una señal de compra o venta."]
        if v["sobrevalorada"]:
            gr = sorted(v["sobrevalorada"], key=lambda p: -p["monto"])[:3]
            f.append("Las de mayor peso con precio por encima de su valor estimado: " + ", ".join(p["ticker"] for p in gr) + ". Mirá su página para ver los números.")
        sec.append(("Qué dice el screener de tus empresas", f))
    if res["sin_clasificar"]:
        nombres_ = ", ".join(dict.fromkeys(str(p["ticker"]) for p in res["sin_clasificar"]))
        sec.append(("Lo que no pude clasificar", [f"No pude ubicar: {nombres_} ({res['pct_sin_clasificar']:.0f} % del total). Quedaron afuera del cálculo. Si son bonos, obligaciones negociables o efectivo, completá la columna Tipo del Excel."]))
    return sec


def devolucion_html(secciones):
    out = []
    for titulo, frases in secciones:
        li = "".join(f"<li>{_negrita(html.escape(x))}</li>" for x in frases)
        out.append(f'<div class="cr-s"><h4>{html.escape(titulo)}</h4><ul>{li}</ul></div>')
    return "".join(out)


def _negrita(t):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


CSS = """
.cr{font-family:inherit;color:#1f2937;margin:0}
.cr h1{font-size:1.5rem;margin:.2em 0 .3em}.cr .cr-i{color:#475569;font-size:.95rem;line-height:1.55;margin:0 0 .8em}
.cr-s{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);padding:12px 18px 8px;margin:0 0 12px}
.cr-s h4{margin:.2em 0 .4em;font-size:1rem;color:#1e3a8a}.cr-s ul{margin:0 0 .6em 1.1em;padding:0}.cr-s li{margin:0 0 .45em;line-height:1.55;font-size:.95rem;text-align:justify}
.cr-av{background:#f8fafc;border:1px solid #e5e9f0;border-radius:12px;padding:10px 14px;color:#64748b;font-size:.82rem;line-height:1.5;margin-top:8px}
"""
