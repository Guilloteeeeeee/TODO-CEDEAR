"""
Tabla visual (definitiva desde v1.2.28; columnas nuevas en la v1.2.36; 6 columnas desde la v1.2.37; 7 columnas y filas mas
compactas desde la v1.2.41). Una pieza de HTML (sin JavaScript) con una fila por empresa.
Los titulos son botones de Streamlit (los dibuja app.py, con los mismos anchos) y ordenan al tocarlos.
  Empresa        logo y nombre en negrita; abajo, sector (industria) y bandera, sin negrita. Al tocar el nombre se
                 abre la pagina de la empresa (?empresa=TICKER)
  Ticker         el ticker solo, en su propia columna (sin parentesis); tambien abre la pagina de la empresa
  Market Cap     numero centrado (sin negrita)
  Precio         precio de hoy
  Valoracion     arriba, la categoria en letras de color y negrita (sin bloque de color y, por defecto, sin el "Podría estar");
                 abajo, el Fair Value y, entre parentesis, la distancia del precio al Fair Value (sin negrita, sin barra)
  Puntaje        caja con el puntaje (0-100) y, abajo, cuantas metricas se pudieron usar
  Dividend Yield rendimiento actual y, al lado, el recorrido de los años fiscales (linea gris), la mediana
                 (linea horizontal; abajo el texto "Mediana histórica X %", sin cantidad de años) y hoy (punto con el color
                 segun donde esta respecto de esa mediana). Si no hay serie de años, una escala corta con la marca de la mediana.
La barra con el Fair Value al centro (celda_valoracion) ya no va en la tabla: esta en la pagina de cada empresa.
El rango de 52 semanas tampoco va en la tabla: esta en la pagina de cada empresa.

Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import base64
import html
import math
import statistics
from urllib.parse import quote

import pandas as pd

from config.sectors import etiqueta_sector, partes_sector
from ui.banderas import bandera_html
from ui.logos import logo_html

# Color de texto (para leer sobre blanco) de cada color de categoria, y color del texto sobre el relleno de la etiqueta
_TEXTO_OSCURO = {"#eab308": "#ca8a04", "#82b93f": "#4d7a12", "#f97316": "#c2410c", "#dc2626": "#b91c1c"}
_TEXTO_EN_RELLENO = {"#15803d": "#ffffff", "#82b93f": "#1a2e05", "#eab308": "#3b2f00", "#f97316": "#2b1300", "#dc2626": "#ffffff"}

try:
    from config.ajustes import RANGO_FV_MARGEN, ESCALA_BARRA_VECES
except ImportError:      # ajustes.py viejo
    RANGO_FV_MARGEN, ESCALA_BARRA_VECES = 0.20, 1.8
try:
    from config.ajustes import AVISO_PODRIA_EN_TABLA
except ImportError:      # ajustes.py viejo
    AVISO_PODRIA_EN_TABLA = False


def texto_categoria(color):
    """Color de texto legible sobre blanco para una categoria con ese color de relleno."""
    return _TEXTO_OSCURO.get(str(color).lower(), color)


def sector_html(grupo, en_linea=False):
    """Sector en negrita y la industria entre parentesis (detalle de la empresa). Dos lineas, o una sola si en_linea."""
    sector, industria = partes_sector(grupo)
    if not sector:
        return "—"
    s = f"<b>{html.escape(sector)}</b>"
    if not industria:
        return s if en_linea else f'<div class="tv-sec">{s}</div>'
    ind = html.escape(industria)
    return f'{s} <span class="tv-ind">({ind})</span>' if en_linea else f'<div class="tv-sec">{s}<span class="tv-ind">({ind})</span></div>'


def sector_plano(grupo):
    """Sector (industria) en texto normal, sin negrita: es lo que va debajo del nombre en la tabla."""
    sector, industria = partes_sector(grupo)
    if not sector:
        return ""
    return html.escape(sector) + (f" ({html.escape(industria)})" if industria else "")


def escala_valoracion_html(mostrar_gris=False):
    """Escala de valoracion: cinco tramos de color con el nombre de cada categoria, de la mas barata (izquierda) a la mas cara
    (derecha) - el mismo orden y los mismos colores que el medidor de cada fila. El rango de puntaje de cada tramo queda en
    el texto que aparece al pasar el mouse."""
    from scoring.engine import CATEGORIAS, CATEGORIA_GRIS, nombre_visible
    rangos = ["70 o más", "58 a 69", "42 a 57", "30 a 41", "menos de 30"]
    tramos = []
    for (umbral, nombre, color, _), rango in zip(CATEGORIAS, rangos):
        txt = _TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")
        aviso, principal = _partes_nombre(nombre_visible(nombre))
        hd = f'<span class="esc-hd">{html.escape(aviso)}</span>' if aviso else ""
        tramos.append(f'<div class="esc-s" style="background:{color};color:{txt}" title="Puntaje {rango}">'
                      f'<div>{hd}<b>{html.escape(_mayusculas(principal))}</b></div></div>')
    gris = (f'<div class="esc-gp"><span class="esc-gc" style="background:{CATEGORIA_GRIS[1]}">{html.escape(nombre_visible(CATEGORIA_GRIS[0]))}</span>'
            f'<span class="esc-gt">sin métricas ni rango de 52 semanas</span></div>') if mostrar_gris else ""
    return ('<div class="esc"><div class="esc-t"><b>Escala de valoración</b></div>'
            f'<div class="esc-b">{"".join(tramos)}</div>'
            '<div class="esc-ej"><span>◀ más barata</span><span>más cara ▶</span></div>'
            f'{gris}</div>')

def leyenda_tabla_html():
    """"Cómo leer la tabla": va dentro del recuadro Screener, debajo de la escala de valoracion."""
    return ('<div class="tv-leyenda"><b>Cómo leer la tabla:</b> en <b>Valoración</b>, la frase de color sale del puntaje (de 0 a 100) y es una '
            'estimación ("podría estar…"), no una recomendación; debajo va el <b>Fair Value</b>, el precio que sale de promediar, con los pesos '
            'de su sector, lo que valdría la empresa si cotizara a su múltiplo histórico, y entre paréntesis cuánto más (+) o menos (−) que el '
            'precio de hoy. En el <b>Dividend Yield</b>, la línea gris es el rendimiento de cada año fiscal, la punteada es su mediana y el punto '
            'es hoy: arriba de la línea rinde más que lo habitual, abajo menos. Tocá el nombre o el ticker de una empresa para ver su página con '
            'todo el detalle (métodos del Fair Value, rango de 52 semanas).</div>')


# Anchos relativos de las 7 columnas (Empresa, Ticker, Market Cap, Precio, Valoracion, Puntaje, Dividend Yield): los usan los
# encabezados (botones de Streamlit) y las filas (grilla CSS), asi quedan alineados.
ANCHOS_VISUAL = [3.0, 0.9, 1.15, 1.0, 3.0, 0.95, 1.9]

CSS = """
.tv2{border:1px solid #d5dde6;border-top:0;border-radius:0 0 10px 10px;background:#fff;color:#1f2328;overflow:hidden;font-family:inherit}
.tv2-r{display:grid;grid-template-columns:__COLS__;align-items:stretch;border-top:1px solid #e8ecf1}
.tv2-r:first-child{border-top:0}
.tv2-r>div{padding:8px 12px;min-width:0;display:flex;flex-direction:column;justify-content:center}
.tv2-r>.tv2-v{background:#f2f6fa}
.tv2-r:hover>div{background:#f8fafc}
.tv2-r:hover>.tv2-v{background:#e9f0f7}
.tv2-c{align-items:center;text-align:center}
.tv2-emp{display:flex;align-items:center;gap:10px;min-width:0}
.tv2-ec{min-width:0;flex:1}
.tv2-l1{display:flex;align-items:baseline;gap:5px;min-width:0}
.tv2-nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px;font-weight:700;color:#111827}
.tv2-tk{flex:none;font-size:13.5px;font-weight:700;color:#374151;letter-spacing:.3px}
.tv2-mc{font-size:14px;font-weight:400;color:#111827;white-space:nowrap}
.tv2-l2{margin-top:2px;font-size:11.5px;font-weight:400;color:#4b5563;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tv2-dy{text-align:center}
.tv2-dyn{font-size:15px;font-weight:600;color:#111827;line-height:1.15}
.tv2-dy img{display:block;margin:4px auto 0}
.tv2-dyc .tv2-dyr{display:flex;align-items:center;justify-content:center;gap:8px}
.tv2-dyc img{margin:0}
.tv2-dym{font-size:11px;color:#4b5563;margin-top:2px}
.tv2-dym b{color:#374151;font-weight:600}
.tv-cat{display:flex;justify-content:center;margin-bottom:8px}
.tv2-vc{display:flex;flex-direction:column;align-items:center;gap:2px}
.tv2-vc .tv-cat{margin-bottom:0}
.tv-vl{text-align:center;line-height:1.2}
.tv-vh{display:block;font-size:12px;font-weight:600;opacity:.85}
.tv-vn{display:block;font-size:14px;font-weight:700}
.tv-up{font-weight:700;color:#374151}
.tv2-pr{font-size:14px;font-weight:400;color:#111827;white-space:nowrap}
.tv2-fvc{font-size:14px;font-weight:400;color:#111827;white-space:nowrap}
.tv2-fvc span{font-size:13px;color:#4b5563}
a.tv2-l1,a.tv2-lg{text-decoration:none!important;color:inherit!important}
a.tv2-lg{flex:none;display:flex}
a.tv2-l1:hover .tv2-nm{text-decoration:underline;color:#1d4ed8}
a.tv2-l1:hover .tv2-tk,a.tv2-tkc:hover .tv2-tk{color:#1d4ed8}
a.tv2-tkc{text-decoration:none!important;color:inherit!important}
.tv-v2{position:relative;height:66px;margin:0 10px}
.tv-pl{position:absolute;top:0;transform:translateX(-50%);font-size:13px;font-weight:700;color:#111827;white-space:nowrap}
.tv-line{position:absolute;left:0;right:0;top:30px;height:4px;border-radius:2px;background:#bcd2e6}
.tv-band{position:absolute;top:-7px;height:18px;background:rgba(47,127,184,.24);border:1px solid rgba(31,106,165,.6);border-radius:4px;box-sizing:border-box}
.tv-fv{position:absolute;top:-9px;left:50%;width:3px;height:22px;background:#1f6aa5;border-radius:1px;transform:translateX(-50%)}
.tv-dot{position:absolute;top:-7px;width:18px;height:18px;border-radius:50%;border:2.5px solid #fff;box-shadow:0 0 0 1px #475569,0 1px 3px rgba(15,23,42,.35);transform:translateX(-50%);box-sizing:border-box}
.tv-fl{position:absolute;top:46px;left:50%;transform:translateX(-50%);font-size:13px;font-weight:600;color:#1f4e79;white-space:nowrap}
.tv-lbls{display:flex;justify-content:space-between;font-size:11.5px;color:#4b5563;margin-top:5px}
.tv-sub{font-size:12px;color:#4b5563;margin-top:4px}
.tv-score{margin:0 auto;width:56px;border-radius:7px;overflow:hidden;border:2px solid #d1d5db;text-align:center;background:#fff}
.tv-num{font-size:17px;font-weight:700;line-height:26px;color:#111827}
.tv-met{font-size:10px;font-weight:600;color:#fff;line-height:15px}
.tv-t2{position:relative;height:8px;border-radius:4px;background:#e5e7eb;margin-top:12px}
.tv-d2{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #94a3b8;transform:translateX(-50%);box-sizing:border-box}
.tv-dy{font-weight:700;font-size:15px}
.tv-dy small{font-weight:600;font-size:12px;display:block;margin-top:2px}
.tv-mc{font-size:14px;font-weight:700;color:#111827}
.tv-sec{line-height:1.25}
.tv-sec b{display:block;font-size:14px;color:#111827}
.tv-ind{display:block;margin-top:1px;font-size:12px;color:#4b5563}
.tv-meta .tv-ind{display:inline;margin:0}
.tv-emp .tv-meta b{color:#374151;font-weight:700}
.emp-vol{display:inline-block;margin:14px 0 6px;font-size:14.5px;font-weight:600;color:#1d4ed8!important;text-decoration:none!important}
.emp-vol:hover{text-decoration:underline!important}
.emp-h{display:flex;align-items:center;gap:16px;margin:8px 0 4px}
.emp-n{font-size:2rem;font-weight:800;line-height:1.15;color:#0f172a;letter-spacing:-.4px}
.emp-n span{font-weight:700;color:#475569;font-size:1.5rem}
.emp-s{margin-top:5px;font-size:14.5px;color:#374151}
.emp-s b{color:#111827}
.emp-k{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:14px 0 6px}
.emp-b{border:1px solid #d5dde6;border-radius:12px;padding:12px 14px 14px;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:flex-start}
.emp-bt{font-size:12.5px;font-weight:600;color:#4b5563;margin-bottom:8px;letter-spacing:.2px}
.emp-b .tv2-pr,.emp-b .tv2-fvc{font-size:22px}
.emp-b .tv-score{width:66px;border-radius:8px}
.emp-b .tv-num{font-size:21px;line-height:36px}
.emp-b .tv-met{font-size:11px;line-height:19px}
.emp-b .tv2-dyn{font-size:22px}
.emp-b .tv2-dym{font-size:12px;margin-top:3px}
.emp-b .tv2-dy img{margin:5px auto 0}
.emp-b .tv2-fvc span{font-size:16px}
.emp-b .tv-vn{font-size:17px}
.emp-barra{border:1px solid #d5dde6;border-radius:12px;padding:14px 18px 6px;margin:10px 0;background:#f8fafc}
.emp-barra .tv-v2{margin:0 24px}
.emp-barra small{display:block;color:#4b5563;font-size:12.5px;margin:2px 0 10px;line-height:1.4}
.esc{margin:14px 0 4px}
.esc-t{display:flex;align-items:baseline;gap:10px;margin-bottom:6px;font-size:14px;color:#111827}
.esc-t span{font-size:12px;color:#4b5563}
.esc-b{display:flex;flex-wrap:wrap;gap:2px}
.esc-s{flex:1 1 150px;padding:10px 12px;text-align:center;line-height:1.25;display:flex;align-items:center;justify-content:center}
.esc-s:first-child{border-radius:8px 0 0 8px}
.esc-s:last-child{border-radius:0 8px 8px 0}
.esc-s b{display:block;font-size:14px;font-weight:700}
.esc-hd{display:block;font-size:11px;font-weight:500;opacity:.9}
.esc-ej{display:flex;justify-content:space-between;margin-top:4px;font-size:11.5px;font-weight:600;color:#4b5563}
.esc-gp{margin-top:6px}
.esc-gc{display:inline-block;color:#fff;font-size:11.5px;font-weight:700;padding:2px 10px;border-radius:10px;margin-right:8px}
.esc-gt{font-size:12px;color:#4b5563}
.tv-leyenda{font-size:12.5px;color:#41566b;border-top:1px solid #dde8f4;margin:12px 0 4px;padding:10px 0 6px;line-height:1.5}
.tv-ini{font-family:inherit}
.flt-t{font-size:13px;font-weight:700;color:#374151;margin:12px 0 2px}
[data-testid="stButtonGroup"] button{border:1px solid #cfd8e3;border-radius:18px;background-color:#fff;color:#374151;padding:3px 13px;font-size:13.5px;transition:background .12s,border-color .12s}
[data-testid="stButtonGroup"] button:hover{background:#eef3f8;border-color:#9fb3c8;color:#222d36}
[data-testid="stButtonGroup"] button[aria-pressed="true"],[data-testid="stButtonGroup"] button[data-testid="stBaseButton-pillsActive"]{background:#222d36!important;border-color:#222d36!important;color:#fff!important;font-weight:600}
[data-testid="stButtonGroup"] button[aria-pressed="true"] p,[data-testid="stButtonGroup"] button[data-testid="stBaseButton-pillsActive"] p{color:#fff}
[data-testid="stButtonGroup"] button[aria-pressed="true"]:hover{background:#33414d!important;border-color:#33414d!important;color:#fff!important}
span[data-baseweb="tag"]{background:#e8eef5!important;border-radius:14px!important}
span[data-baseweb="tag"],span[data-baseweb="tag"] span{color:#1f2937!important}
span[data-baseweb="tag"] svg{fill:#475569!important}
"""
CSS = CSS.replace("__COLS__", " ".join(f"minmax(0,{w}fr)" for w in ANCHOS_VISUAL))

# Colores del encabezado (barra gris pizarra oscura, la misma gama del logo, con titulos blancos centrados; la columna Valoracion un poco mas oscura)
_BARRA = "#222d36"
_BARRA_VAL = "#141c23"


def css_encabezado(sort_col=None):
    """CSS de la fila de titulos (botones de Streamlit con la clave 'tvh_<columna>'). Desde la v1.2.41 se resalta solo la columna
    Valoracion (mas oscura); la columna por la que se ordena se reconoce por la flecha, ya no por el color. `sort_col` se acepta
    por compatibilidad."""
    base = 'div[data-testid="stHorizontalBlock"]:has(.st-key-tvh_nombre)'
    return (
        f'{base}{{gap:0!important;background:{_BARRA};border:1px solid {_BARRA};border-radius:10px 10px 0 0;align-items:stretch!important}}'
        f'{base} [data-testid="stColumn"]{{min-width:0!important;padding:0!important}}'
        f'{base} [data-testid="stElementContainer"]{{width:100%}}'
        '[class*="st-key-tvh_"] button{width:100%;min-height:46px;background:transparent;border:0;border-radius:0;box-shadow:none;color:#fff}'
        '[class*="st-key-tvh_"] button p{font-size:14.5px;font-weight:700;color:#fff;margin:0;letter-spacing:.2px}'
        '[class*="st-key-tvh_"] button:hover{background:rgba(255,255,255,.12);color:#fff}'
        '[class*="st-key-tvh_"] button:focus,[class*="st-key-tvh_"] button:active{color:#fff;box-shadow:none;background:rgba(255,255,255,.12)}'
        f'.st-key-tvh_fv_upside button{{background:{_BARRA_VAL}}}'
        'div[data-testid="stElementContainer"]:has(.tv2){margin-top:-1rem}'
    )


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def _txt(x, defecto=""):
    """Texto no vacio o `defecto` (los vacios de pandas llegan como NaN y no deben verse como 'nan')."""
    return x if isinstance(x, str) and x.strip() else defecto


def _money(x):
    v = _n(x)
    if v is None:
        return "—"
    return f"&#36;{v:,.0f}" if abs(v) >= 100 else f"&#36;{v:,.2f}"


def _mcap(x):
    v = _n(x)
    if not v or v <= 0:
        return "—"
    for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= lim:
            return f"&#36;{v / lim:.1f}{suf}"
    return f"&#36;{v:,.0f}"


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _nombre_limpio(nombre, ticker):
    """Nombre sin comas ni puntos colgados al final (Yahoo viejo lo cortaba a ~30 letras: 'Financial Group,')."""
    n = _txt(nombre, ticker).strip()
    while n and n[-1] in ",;:-/ ":
        n = n[:-1].rstrip()
    return n or ticker


def _href_empresa(ticker, estado=None):
    """Link a la pagina de una empresa. `estado` (opcional) lleva los filtros para poder volver a la tabla tal como estaba."""
    h = "?empresa=" + quote(str(ticker), safe="")
    return h + ("&f=" + estado if estado else "")


def _celda_empresa(row, estado=None):
    """Logo y nombre en negrita (todo es un link a la pagina de la empresa); abajo, sector (industria) sin negrita y la bandera.
    El ticker va en su propia columna (_celda_ticker)."""
    t = _txt(row.get("ticker"), "—")
    nombre = html.escape(_nombre_limpio(row.get("nombre"), t))
    g = row.get("sector")
    sec = sector_plano(g) if isinstance(g, str) and g else ""
    pais = row.get("pais")
    bandera = bandera_html(pais, chica=True) if isinstance(pais, str) and pais else ""
    l2 = " ".join(x for x in (sec, bandera) if x)
    href = html.escape(_href_empresa(t, estado), quote=True)
    ttl = f'Ver la página de {nombre}'
    return (f'<div class="tv2-emp"><a class="tv2-lg" href="{href}" target="_self" title="{ttl}">{logo_html(t, 32)}</a><div class="tv2-ec">'
            f'<a class="tv2-l1" href="{href}" target="_self" title="{ttl}"><span class="tv2-nm">{nombre}</span></a>'
            f'<div class="tv2-l2">{l2}</div></div></div>')


def _celda_ticker(row, estado=None):
    """El ticker solo (sin parentesis), en su propia columna; tambien abre la pagina de la empresa."""
    t = _txt(row.get("ticker"), "—")
    href = html.escape(_href_empresa(t, estado), quote=True)
    return f'<a class="tv2-tkc" href="{href}" target="_self" title="Ver la página de {html.escape(t)}"><span class="tv2-tk">{html.escape(t)}</span></a>'


def _celda_mcap(row):
    return f'<span class="tv2-mc">{_mcap(row.get("market_cap"))}</span>'


def _mayusculas(texto):
    """Cada palabra con su inicial en mayuscula ("significativamente sobrevalorada" -> "Significativamente Sobrevalorada")."""
    return " ".join(w[:1].upper() + w[1:] for w in str(texto).split(" "))


def _partes_nombre(texto):
    """('Podría estar', 'significativamente infravalorada'): el aviso de que es una estimacion va chico arriba y la categoria
    grande abajo. Si el nombre no empieza con 'Podría estar' (p. ej. 'Datos insuficientes'), no hay aviso."""
    pref = "Podría estar "
    if texto.startswith(pref):
        return pref.strip(), texto[len(pref):]
    return "", texto


def _pos_barra(x, fv):
    """Posicion (0 a 100) de un precio en la barra: el Fair Value queda siempre en el 50. La escala es logaritmica, asi
    la mitad y el doble del Fair Value quedan a la misma distancia del centro."""
    k = math.log(ESCALA_BARRA_VECES)
    return 50.0 + 50.0 * _clamp(math.log(x / fv) / k, -1.0, 1.0)


def _texto_categoria(cat, color, con_aviso=True):
    """La categoria como texto de color y negrita, sin bloque de fondo: "Podría estar" chico arriba (si `con_aviso`) y la
    categoria abajo. El color es el de la categoria, un poco mas oscuro cuando es claro (para que se lea sobre blanco)."""
    from scoring.engine import nombre_visible
    aviso, nombre = _partes_nombre(nombre_visible(cat))
    hd = f'<span class="tv-vh">{html.escape(aviso)}</span>' if aviso and con_aviso else ""
    return f'<div class="tv-vl" style="color:{texto_categoria(color)}">{hd}<span class="tv-vn">{html.escape(_mayusculas(nombre))}</span></div>'


def _celda_valoracion(row, con_categoria=True):
    cat = _txt(row.get("categoria"), "—")
    color = _txt(row.get("color_hex"), "#6e7781")
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    cabeza = f'<div class="tv-cat">{_texto_categoria(cat, color)}</div>' if con_categoria else ""
    if not precio or not fv or precio <= 0 or fv <= 0:
        return cabeza + f'<div class="tv-sub">Sin Fair Value · precio {_money(precio)}</div>'
    up = (fv - precio) / precio
    v = int(round(up * 100))
    up_txt = f'<span class="tv-up" title="Distancia entre el precio y el Fair Value promedio">{f"{v:+d}%" if v else "0%"}</span>'
    pp = _pos_barra(precio, fv)
    # La franja es simetrica alrededor del centro (en la escala logaritmica +15 % y -15 % no quedarian a la misma distancia)
    medio = 50.0 * math.log(1 + RANGO_FV_MARGEN) / math.log(ESCALA_BARRA_VECES)
    b0, b1 = 50.0 - medio, 50.0 + medio
    pct = int(round(RANGO_FV_MARGEN * 100))
    return (cabeza + '<div class="tv-v2">'
            + f'<div class="tv-pl" style="left:{_clamp(pp, 9, 91):.1f}%" title="Precio actual">{_money(precio)}</div>'
            + '<div class="tv-line">'
            + f'<div class="tv-band" style="left:{b0:.1f}%;width:{b1 - b0:.1f}%" title="Zona de referencia: Fair Value ±{pct}%. Es solo una guía visual."></div>'
            + '<div class="tv-fv"></div>'
            + f'<div class="tv-dot" style="left:{pp:.1f}%;background:{color}"></div></div>'
            + f'<div class="tv-fl" title="Fair Value promedio">{_money(fv)} {up_txt}</div></div>')


def celda_valoracion(row):
    """Barra de valoracion para la tabla clasica (sin el nombre de la categoria)."""
    return _celda_valoracion(row, con_categoria=False)


def _celda_precio(row):
    p = _n(row.get("precio_actual"))
    return f'<span class="tv2-pr" title="Precio actual">{_money(p)}</span>' if p and p > 0 else '<span class="tv2-pr">—</span>'


def _celda_fv(row):
    """Fair Value y, entre parentesis, cuanto mas (+) o menos (-) que el precio de hoy. Sin negrita y sin barra."""
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    if not precio or not fv or precio <= 0 or fv <= 0:
        return '<span class="tv2-fvc" title="No hubo datos para calcular un Fair Value">—</span>'
    v = int(round((fv - precio) / precio * 100))
    d = f"{v:+d}%" if v else "0%"
    return (f'<span class="tv2-fvc" title="Fair Value promedio. Entre paréntesis: cuánto más o menos que el precio de hoy">'
            f'{_money(fv)} <span>({d})</span></span>')


def _celda_categoria(row, con_aviso=True):
    return _texto_categoria(_txt(row.get("categoria"), "—"), _txt(row.get("color_hex"), "#6e7781"), con_aviso)


def _celda_valoracion_tabla(row):
    """Celda "Valoración" de la tabla: arriba la categoria (letras de color en negrita) y abajo el Fair Value con la distancia
    al precio entre parentesis. El "Podría estar" chico se agrega solo si AVISO_PODRIA_EN_TABLA es True."""
    return (f'<div class="tv2-vc">{_celda_categoria(row, con_aviso=bool(AVISO_PODRIA_EN_TABLA))}{_celda_fv(row)}</div>')


def resumen_empresa_html(row):
    """Bloques de arriba de la pagina de una empresa: precio, Fair Value, valoracion, puntaje y Dividend Yield (los mismos de la tabla, un poco mas grandes)."""
    bloques = [("Precio", _celda_precio(row)), ("Fair Value", _celda_fv(row)), ("Valoración", _celda_categoria(row)),
               ("Puntaje", _celda_puntaje(row)), ("Dividend Yield", _celda_dy(row, grande=True))]
    return '<div class="emp-k">' + "".join(f'<div class="emp-b"><div class="emp-bt">{t}</div>{h}</div>' for t, h in bloques) + "</div>"


def barra_empresa_html(row):
    """La barra de la v1.2.34 (Fair Value al centro, franja de referencia y punto del precio) con su explicacion, para la pagina de la empresa."""
    pct = int(round(RANGO_FV_MARGEN * 100))
    return ('<div class="emp-barra"><small><b>Precio de hoy contra el Fair Value.</b> La rayita azul del centro es el Fair Value y la franja celeste una '
            f'zona de referencia de ±{pct}% (no es un intervalo de confianza). El punto es el precio: a la izquierda cotiza por debajo del Fair Value, '
            'a la derecha por encima. Es solo una guía visual.</small>' + _celda_valoracion(row, con_categoria=False) + '</div>')


def _celda_puntaje(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    s = _n(row.get("score_total"))
    num = f"{s:.0f}" if s is not None else "—"
    u, t = _n(row.get("metricas_usadas")), _n(row.get("metricas_total"))
    met = f"{int(u)}/{int(t)} métr." if u is not None and t else "—"
    return (f'<div class="tv-score" title="Puntaje total (0 = caro, 100 = barato) y métricas usadas">'
            f'<div class="tv-num">{num}</div><div class="tv-met" style="background:#64748b">{met}</div></div>')


def _celda_52s(row):
    pos = _n(row.get("posicion_52s"))
    if pos is None:
        return '<div class="tv-sub">—</div>'
    pct = _clamp(pos * 100)
    c = "#64748b"   # un solo color (gris azulado)
    return (f'<div title="El precio está al {pct:.0f}% del rango de las últimas 52 semanas (0% = mínimo, 100% = máximo)">'
            f'<div class="tv-t2"><div class="tv-d2" style="left:{pct:.0f}%;background:{c}"></div></div>'
            f'<div class="tv-lbls"><span>{_money(row.get("precio_min_52s"))}</span><span>{_money(row.get("precio_max_52s"))}</span></div></div>')


def _color_dy(row, ratio):
    """Color del punto del Dividend Yield segun donde esta respecto de su mediana. Usa el puntaje de esa metrica en el score
    (mismos cortes que las categorias: 70/58/42/30); si no esta, usa la relacion hoy / mediana."""
    from scoring.engine import get_categoria_label
    det = row.get("detalle")
    sc = _n(det.get("dividend_yield", {}).get("score")) if isinstance(det, dict) and isinstance(det.get("dividend_yield"), dict) else None
    if sc is None:
        # relacion hoy / mediana: mas rendimiento que lo habitual = mas barata
        sc = 85 if ratio >= 1.25 else 64 if ratio >= 1.08 else 50 if ratio >= 0.92 else 36 if ratio >= 0.75 else 15
    return get_categoria_label(sc)[1]


def _svg_dy(ratio, color, W=150, H=24):
    """Escala corta del Dividend Yield como imagen (data URI): la marca del centro es la mediana historica y el punto es hoy.
    A la derecha = rinde mas que lo habitual. El punto lleva el color segun su posicion. 150x24 (pagina de la empresa) o chica (tabla)."""
    k = H / 24.0
    x_med = W / 2
    lo, hi = 1 / 1.8, 1.8
    x = x_med + (W / 2 - 10) * math.log(_clamp(ratio, lo, hi)) / math.log(hi)
    cy = H / 2
    partes = [
        f'<line x1="6" y1="{cy:.1f}" x2="{W - 6}" y2="{cy:.1f}" stroke="#d1d5db" stroke-width="{3 * k:.1f}" stroke-linecap="round"/>',
        f'<line x1="{x_med}" y1="{cy - 8 * k:.1f}" x2="{x_med}" y2="{cy + 8 * k:.1f}" stroke="#4b5563" stroke-width="{2 * k:.1f}" stroke-linecap="round"/>',
        f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="{7.5 * k:.1f}" fill="none" stroke="#9ca3af" stroke-width="1" opacity=".7"/>',
        f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="{6 * k:.1f}" fill="{color}" stroke="#fff" stroke-width="{2 * k:.1f}"/>',
    ]
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(partes)}</svg>'
    return f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" width="{W}" height="{H}" alt="">'


def _svg_serie(serie, actual, mediana, color, W=156, H=46):
    """Recorrido del Dividend Yield como imagen (data URI): linea gris con un puntito por año fiscal, linea horizontal en la
    mediana y, al final, un punto grande con el color segun su posicion respecto de esa mediana (hoy). Valores en %.
    156x46 (pagina de la empresa) o chico (tabla)."""
    k = H / 46.0
    r_hoy, r_aro = max(4.0, 6 * k + 0.6), max(5.2, 8 * k + 0.6)
    vals = list(serie) + [actual]
    n = len(vals)
    todos = vals + [mediana]
    lo, hi = min(todos), max(todos)
    pad = (hi - lo) * 0.14 or hi * 0.1
    lo, hi = lo - pad, hi + pad
    x0, x1 = 6.0, W - 10.0
    xs = [x0 + i * (x1 - x0) / (n - 1) for i in range(n)]
    y = lambda v: (H - 7) - (v - lo) / (hi - lo) * (H - 14)
    linea = " ".join(f"{px:.1f},{y(v):.1f}" for px, v in zip(xs, vals))
    partes = [
        f'<line x1="2" y1="{y(mediana):.1f}" x2="{W - 2}" y2="{y(mediana):.1f}" stroke="#64748b" stroke-width="1" stroke-dasharray="4 3"/>',
        f'<polyline points="{linea}" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>',
    ]
    partes += [f'<circle cx="{px:.1f}" cy="{y(v):.1f}" r="2" fill="#94a3b8"/>' for px, v in zip(xs[:-1], vals[:-1])]
    partes += [
        f'<circle cx="{xs[-1]:.1f}" cy="{y(vals[-1]):.1f}" r="{r_aro:.1f}" fill="none" stroke="#9ca3af" stroke-width="1" opacity=".7"/>',
        f'<circle cx="{xs[-1]:.1f}" cy="{y(vals[-1]):.1f}" r="{r_hoy:.1f}" fill="{color}" stroke="#fff" stroke-width="{2 if k > .8 else 1.5}"/>',
    ]
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(partes)}</svg>'
    return f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" width="{W}" height="{H}" alt="">'


def _dy_serie(row, m):
    """Serie de rendimientos de los ultimos años fiscales (en %, de la mas vieja a la mas nueva) o None si no sirve:
    hace falta tener 3 o mas años y que su mediana coincida con la mediana que uso el puntaje."""
    s = row.get("dividend_yield_serie")
    if not isinstance(s, (list, tuple)) or len(s) < 3 or not m:
        return None
    vals = [_n(v) for v in s]
    if any(v is None or v <= 0 for v in vals):
        return None
    if max(vals) < 1:                      # el cache guarda fracciones (0.0239 = 2,39 %)
        vals = [v * 100 for v in vals]
    med = statistics.median(vals)
    return vals if abs(med - m) / m < 0.03 else None


def _dy_datos(row):
    """(rendimiento de hoy en %, mediana en % o None, texto de la mediana, serie de años en % o None) o None si no paga dividendo."""
    dy, med = _n(row.get("dividend_yield_actual")), _n(row.get("dividend_yield_mediana"))
    if not dy or dy <= 0:
        return None
    pct = dy if dy > 1 else dy * 100
    m = (med if med > 1 else med * 100) if med and med > 0 else None
    serie = _dy_serie(row, m)
    etiqueta = "Mediana histórica"      # sin la cantidad de años: cada empresa tiene una historia distinta
    # Si el puntaje comparo contra la mediana de su sector (poca historia propia), el dibujito muestra esa misma mediana
    det = row.get("detalle")
    det = det.get("dividend_yield") if isinstance(det, dict) else None
    if isinstance(det, dict) and det.get("referencia") == "sector" and _n(det.get("mediana")) and _n(det.get("mediana")) > 0:
        dm = _n(det.get("mediana"))
        m = dm if dm > 1 else dm * 100
        etiqueta = "Mediana del sector"
        serie = None
    return pct, m, etiqueta, serie


def _celda_dy(row, grande=False):
    """Rendimiento por dividendo. Tabla (por defecto): el numero y, al lado, el recorrido de los años fiscales contra la mediana
    (punto de hoy con color segun la posicion); abajo, "Mediana histórica: X%". Pagina de la empresa (`grande`): el numero
    grande arriba y el dibujo mas grande abajo. Sin serie de años, una escala corta."""
    datos = _dy_datos(row)
    cls = "tv2-dy" if grande else "tv2-dy tv2-dyc"
    if not datos:
        return f'<div class="{cls}"><div class="tv2-dyn" style="color:#9ca3af">—</div></div>'
    pct, m, etiqueta, serie = datos
    mtxt = f"{m:.1f}%" if m and m >= 1 else (f"{m:.2f}%" if m else "")
    if not m:
        return f'<div class="{cls}" title="Rendimiento por dividendo de hoy."><div class="tv2-dyn">{pct:.2f}%</div></div>'
    ratio = pct / m
    if ratio >= 1.02:
        lectura = f"Hoy rinde más que lo habitual ({pct:.2f}% contra una mediana de {mtxt})."
    elif ratio <= 0.98:
        lectura = f"Hoy rinde menos que lo habitual ({pct:.2f}% contra una mediana de {mtxt})."
    else:
        lectura = f"Hoy rinde lo mismo que lo habitual (mediana de {mtxt})."
    color = _color_dy(row, ratio)
    if serie:
        tip = lectura + " Línea gris: rendimiento de cada año fiscal. Línea punteada: su mediana histórica. Punto de color: hoy."
        dibujo = _svg_serie(serie, pct, m, color) if grande else _svg_serie(serie, pct, m, color, W=112, H=30)
    else:
        tip = lectura + " La marca del centro es su mediana histórica; el punto es hoy."
        dibujo = _svg_dy(ratio, color) if grande else _svg_dy(ratio, color, W=96, H=18)
    pie = f'<div class="tv2-dym">{html.escape(etiqueta)}: <b>{mtxt}</b></div>'
    if grande:
        return f'<div class="{cls}" title="{html.escape(tip)}"><div class="tv2-dyn">{pct:.2f}%</div>{dibujo}{pie}</div>'
    return f'<div class="{cls}" title="{html.escape(tip)}"><div class="tv2-dyr"><span class="tv2-dyn">{pct:.2f}%</span>{dibujo}</div>{pie}</div>'


def html_tabla_visual(df: pd.DataFrame, estado=None) -> str:
    """HTML de las filas de `df`, en el orden recibido (los encabezados ordenables los dibuja la app). `estado` es el texto con
    los filtros que viajan en el link de cada empresa para poder volver a la tabla tal cual estaba. La leyenda "Cómo leer la
    tabla" ya no va aca: esta en el recuadro Screener (leyenda_tabla_html)."""
    filas = []
    for _, row in df.iterrows():
        r = row.to_dict()
        filas.append('<div class="tv2-r">' + f'<div>{_celda_empresa(r, estado)}</div>' + f'<div class="tv2-c">{_celda_ticker(r, estado)}</div>'
                     + f'<div class="tv2-c">{_celda_mcap(r)}</div>' + f'<div class="tv2-c">{_celda_precio(r)}</div>'
                     + f'<div class="tv2-v">{_celda_valoracion_tabla(r)}</div>'
                     + f'<div class="tv2-c">{_celda_puntaje(r)}</div>' + f'<div class="tv2-c">{_celda_dy(r)}</div></div>')
    return f'<div class="tv2">{"".join(filas)}</div>'
