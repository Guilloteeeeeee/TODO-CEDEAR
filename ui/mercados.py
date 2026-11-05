"""Barra de mercados (v1.5.7): una franja finita debajo de la franja negra, en todas las páginas, con dólares argentinos (oficial, MEP y CCL), Merval, bolsas de EE.UU. y de
Europa, bono a 10 años, VIX, oro, petróleo y Bitcoin. Sin gráficos chicos y sin links. Los precios vienen de Yahoo Finance (igual que el resto de la app) y los dólares de
DolarApi (https://dolarapi.com). Si un dato no llega, ese casillero se oculta; nunca se muestra un error ni un número inventado.
Se actualiza cada 5 minutos en segundo plano: quien entra ve lo último que haya (si es la primera vez desde que arrancó la app, espera unos segundos)."""
import html
import threading
import time

# (nombre que se ve, símbolo en Yahoo, decimales, sufijo)
INDICES = [
    ("Merval", "^MERV", 0, ""),
    ("S&P 500", "^GSPC", 2, ""),
    ("Nasdaq", "^IXIC", 2, ""),
    ("Dow 30", "^DJI", 2, ""),
    ("Russell 2000", "^RUT", 2, ""),
    ("Bono EE.UU. 10 años", "^TNX", 3, " %"),
    ("VIX", "^VIX", 2, ""),
    ("Oro (US$)", "GC=F", 2, ""),
    ("Petróleo Brent (US$)", "BZ=F", 2, ""),
    ("Bitcoin (US$)", "BTC-USD", 0, ""),
    ("Euro Stoxx 50", "^STOXX50E", 2, ""),
    ("DAX (Alemania)", "^GDAXI", 2, ""),
    ("FTSE 100 (Reino Unido)", "^FTSE", 2, ""),
    ("CAC 40 (Francia)", "^FCHI", 2, ""),
]
DOLARES = [("Dólar oficial", "oficial"), ("Dólar MEP", "bolsa"), ("Dólar CCL", "contadoconliqui")]
TTL = 300.0
_LOCK = threading.Lock()
_EST = {"t": 0.0, "items": None, "hilo": None}


def num_es(v, dec=2):
    """1234567.891 -> '1.234.567,89' (formato argentino)."""
    t = f"{abs(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 and float(t.replace(".", "").replace(",", ".")) != 0 else "") + t


def _ultimos_dos(datos, simbolos):
    """{símbolo: (último, anterior)} sacado de lo que devuelve yfinance.download (una o varias columnas); lo que no se pueda leer se salta."""
    out = {}
    try:
        if datos is None or len(datos) == 0:
            return out
        multi = hasattr(datos.columns, "nlevels") and datos.columns.nlevels > 1
        for s in simbolos:
            try:
                if multi:
                    nivel0 = set(datos.columns.get_level_values(0))
                    serie = datos[s]["Close"] if s in nivel0 else datos["Close"][s]
                else:
                    serie = datos["Close"] if len(simbolos) == 1 else None
                if serie is None:
                    continue
                serie = serie.dropna()
                if len(serie) < 2:
                    continue
                u, a = float(serie.iloc[-1]), float(serie.iloc[-2])
                if u > 0 and a > 0:
                    out[s] = (u, a)
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        return {}
    return out


def descargar_indices(timeout=15):
    simbolos = [s for _, s, _, _ in INDICES]
    try:
        import yfinance as yf
        datos = yf.download(simbolos, period="5d", interval="1d", auto_adjust=False, progress=False, threads=True, group_by="ticker", timeout=timeout)
    except Exception:  # noqa: BLE001
        return {}
    return _ultimos_dos(datos, simbolos)


def descargar_dolares(timeout=8, get=None):
    """{'oficial': venta, 'bolsa': venta, 'contadoconliqui': venta} desde DolarApi; {} si no responde."""
    try:
        if get is None:
            import requests
            r = requests.get("https://dolarapi.com/v1/dolares", timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            datos = r.json() if r.status_code == 200 else []
        else:
            datos = get()
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for d in datos if isinstance(datos, list) else []:
        try:
            v = float(d.get("venta"))
            if v > 0:
                out[str(d.get("casa"))] = v
        except (TypeError, ValueError, AttributeError):
            continue
    return out


def armar(indices, dolares):
    """Lista de casilleros [{'nombre','valor','var','pct','signo'}] (signo: 1 sube, -1 baja, 0 sin variación) en el orden de la barra."""
    items = []
    for nom, clave in DOLARES:
        if dolares.get(clave):
            items.append({"nombre": nom, "valor": "$ " + num_es(dolares[clave], 2), "var": "", "pct": "", "signo": 0})
    for nom, sim, dec, suf in INDICES:
        if sim not in indices:
            continue
        u, a = indices[sim]
        dif, pct = u - a, (u / a - 1) * 100
        sg = 1 if round(dif, dec) > 0 else (-1 if round(dif, dec) < 0 else 0)
        mas = "+" if sg > 0 else ""
        items.append({"nombre": nom, "valor": num_es(u, dec) + suf, "var": mas + num_es(dif, dec), "pct": mas + num_es(pct, 2) + " %", "signo": sg})
    return items


def _refrescar(indices_fn=None, dolares_fn=None):
    ind = (indices_fn or descargar_indices)()
    dol = (dolares_fn or descargar_dolares)()
    items = armar(ind, dol)
    with _LOCK:
        if items:
            _EST["items"], _EST["t"] = items, time.time()
        else:
            _EST["t"] = time.time() - TTL + 60       # si no llegó nada, se reintenta en un minuto y se sigue mostrando lo anterior (si lo hay)


def obtener(esperar=8.0, indices_fn=None, dolares_fn=None):
    """Casilleros a mostrar. Lo vencido (más de 5 minutos) se refresca en segundo plano; solo la primera vez se espera (hasta `esperar` segundos)."""
    with _LOCK:
        vencido = time.time() - _EST["t"] > TTL
        h = _EST["hilo"]
        if vencido and not (h and h.is_alive()):
            h = threading.Thread(target=_refrescar, args=(indices_fn, dolares_fn), daemon=True)
            _EST["hilo"] = h
            h.start()
        items = _EST["items"]
    if items is None and h is not None:
        h.join(esperar)
        with _LOCK:
            items = _EST["items"]
    return items or []


CSS_BARRA = """
.mk-bar{width:100vw;margin-left:calc(50% - 50vw);background:#fff;border-bottom:1px solid #e3e8ee;box-sizing:border-box}
.mk-in{display:flex;gap:0;overflow-x:auto;scrollbar-width:thin;padding:0 clamp(8px,2vw,32px);-webkit-overflow-scrolling:touch}
.mk-it{flex:none;display:flex;flex-direction:column;gap:1px;padding:7px 18px 7px 0;margin-right:18px;border-right:1px solid #eef1f5;white-space:nowrap;line-height:1.25}
.mk-it:nth-last-child(2){border-right:0}
.mk-n{font-size:.78rem;font-weight:700;color:#1d4ed8}
.mk-v{font-size:.95rem;font-weight:700;color:#111827}
.mk-c{font-size:.78rem;font-weight:700;min-height:1em}
.mk-fl{position:sticky;right:0;flex:none;align-self:stretch;width:40px;margin-left:-40px;display:flex;align-items:center;justify-content:flex-end;padding-right:4px;box-sizing:border-box;background:linear-gradient(to right,rgba(255,255,255,0),#fff 60%);color:#1d4ed8;font-size:1.7rem;font-weight:700;line-height:1;pointer-events:none}
@supports (animation-timeline:scroll()){.mk-fl{animation:mk-fl linear both;animation-timeline:scroll(nearest inline)}}
@keyframes mk-fl{0%,90%{opacity:1}100%{opacity:0}}
.mk-sube{color:#15803d}.mk-baja{color:#b91c1c}.mk-igual{color:#6b7280}
"""


def barra_html(items):
    """La franja lista para st.markdown; '' si no hay nada para mostrar (la página se ve igual que antes)."""
    if not items:
        return ""
    celdas = []
    for it in items:
        cls = {1: "mk-sube", -1: "mk-baja"}.get(it["signo"], "mk-igual")
        if it["var"]:
            celdas.append(f'<div class="mk-it"><span class="mk-n">{html.escape(it["nombre"])}</span><span class="mk-v">{html.escape(it["valor"])}</span>'
                          f'<span class="mk-c {cls}">{html.escape(it["pct"])}</span></div>')      # v1.5.34: solo el porcentaje del día, sin la variación en puntos
        else:       # dólares: sin tercera línea; nombre y valor a la misma altura que en los demás casilleros
            celdas.append(f'<div class="mk-it"><span class="mk-n">{html.escape(it["nombre"])}</span><span class="mk-v">{html.escape(it["valor"])}</span></div>')
    flecha = '<div class="mk-fl" aria-hidden="true">&rsaquo;</div>'   # puntita: avisa que se puede deslizar hacia la derecha
    return f'<style>{CSS_BARRA}</style><div class="mk-bar"><div class="mk-in">{"".join(celdas)}{flecha}</div></div>'
