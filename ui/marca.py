"""
Marca de la app (v1.2.36): franja negra de punta a punta arriba de todo (como Investing), con el nombre TodoCedears a la
izquierda (la imagen del titulo si esta en assets/marca/titulo-todocedears.png; si no, el nombre escrito en letras blancas)
y, a la derecha, los iconos de YouTube / Instagram / mail / WhatsApp, un menu desplegable (Quienes somos, Abrite una
cuenta) y el toro de "Finanzas para Medicos" chiquito. Los links se cargan en config/ajustes.py (ENLACES_MARCA y CUENTAS_MARCA): lo que
no tiene link no se muestra. El resto de la pantalla es blanco.

El logo es de propiedad del dueño de la herramienta y viene en assets/marca/. Tambien es el icono de la pestaña.
"""
import base64
import html
import os
import re

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "marca")
LOGO = os.path.join(_DIR, "finanzas-para-medicos-128.png")
TITULO = os.path.join(_DIR, "titulo-todocedears.png")      # opcional: imagen del titulo
NOMBRE_MARCA = "Finanzas para Médicos"

try:
    from config.ajustes import ENLACES_MARCA
except Exception:  # noqa: BLE001
    ENLACES_MARCA = {}
try:
    from config.ajustes import CUENTAS_MARCA
except Exception:  # noqa: BLE001
    CUENTAS_MARCA = []
try:
    from config.ajustes import LOGOS_EN_LINEA
except Exception:  # noqa: BLE001
    LOGOS_EN_LINEA = "google"

CSS = """
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{overflow-x:hidden}
[data-testid="stMainBlockContainer"]{padding-top:0!important}
.mc-band{width:100vw;margin-left:calc(50% - 50vw);background:#000;border-bottom:3px solid #00e85c}
.mc-in{display:flex;align-items:center;justify-content:space-between;gap:20px;height:80px;padding:0 clamp(16px,3vw,48px);box-sizing:border-box}
.mc-izq{min-width:0;display:flex;align-items:center}
.mc-t{font-size:2.5rem;font-weight:800;line-height:1;letter-spacing:-1px;color:#fff;white-space:nowrap}
.mc-t span{color:#00e85c}
.mc-img{display:block;height:48px;width:auto;max-width:100%}
.mc-der{display:flex;align-items:center;gap:18px;flex:none}
.mc-ic{display:flex;align-items:center;gap:14px}
.mc-ic a{display:flex;opacity:.78;transition:opacity .12s}
.mc-ic a:hover{opacity:1}
.mc-ic svg{width:22px;height:22px;display:block}
.mc-menu{position:relative}
.mc-menu summary{list-style:none;cursor:pointer;color:#e5e7eb;font-size:.92rem;font-weight:600;padding:7px 12px;border:1px solid #3a3f45;border-radius:8px;user-select:none}
.mc-menu summary::-webkit-details-marker{display:none}
.mc-menu summary:hover,.mc-menu[open] summary{background:#1b1f23;color:#fff}
.mc-pop{position:absolute;right:0;top:calc(100% + 8px);min-width:330px;background:#0c0f12;border:1px solid #3a3f45;border-radius:10px;padding:6px;z-index:1000;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.mc-pop a{display:block;padding:10px 12px;border-radius:7px;color:#f3f4f6!important;text-decoration:none!important;font-size:.95rem}
.mc-pop a:hover{background:#1f2937}
.mc-sep{margin:8px 12px 4px;padding-top:10px;border-top:1px solid #2a3037;font-size:.74rem;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#9ca3af}
.mc-pop a.mc-cta{display:flex;align-items:center;gap:12px}
.mc-lg{flex:none;width:34px;height:34px;border-radius:8px;background:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden}
.mc-lg img{width:100%;height:100%;object-fit:contain;display:block}
.mc-fv{display:block;width:100%;height:100%;background:#fff center/72% no-repeat}
.mc-lg i{font-style:normal;font-weight:800;font-size:1rem;color:#334155}
.mc-tx{min-width:0;display:flex;flex-direction:column;gap:2px}
.mc-tx b{font-size:.98rem;font-weight:700;color:#fff}
.mc-tx small{font-size:.76rem;line-height:1.3;color:#9ca3af}
.mc-toro{flex:none;width:44px;height:44px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center}
.mc-toro img{width:36px;height:auto;display:block}
.mc-datos{text-align:right;font-size:12.5px;color:#4b5563;margin:6px 4px -18px}
.mc-datos b{color:#1f2937;font-weight:600}
.mc-pie{margin:26px 0 10px;text-align:center;font-size:12.5px;color:#4b5563}
.mc-pie b{color:#1f2937;font-weight:600}
@media (max-width:760px){.mc-t{font-size:1.7rem}.mc-in{height:64px;gap:10px}.mc-ic{display:none}.mc-img{height:34px}}
"""

_SVG = {
    "youtube": '<svg viewBox="0 0 24 24" fill="#fff"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4.2"/><circle cx="17.6" cy="6.4" r="1.1" fill="#fff" stroke="none"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M3.5 7.5l8.5 6 8.5-6"/></svg>',
    "whatsapp": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"><path d="M12 3a9 9 0 0 0-7.7 13.6L3 21l4.6-1.2A9 9 0 1 0 12 3z"/><path d="M9 8.4c.2-.4.5-.5.8-.5h.5c.2 0 .3.1.4.3l.8 1.8c.1.2 0 .4-.1.6l-.6.7c-.1.1-.1.3 0 .4.7 1.1 1.5 1.8 2.6 2.4.2.1.3.1.4 0l.7-.8c.2-.2.4-.2.6-.1l1.7.8c.2.1.3.2.3.4 0 .8-.4 1.4-1 1.7-.6.3-1.3.3-1.9.1-2.9-1-4.8-3-5.7-5.4-.2-.6-.1-1.3.3-1.9z" fill="#fff" stroke="none"/></svg>',
}
_TITULOS_ICONO = {"youtube": "YouTube", "instagram": "Instagram", "mail": "Contacto por mail", "whatsapp": "WhatsApp"}
_ITEMS_MENU = [("quienes_somos", "Quiénes somos"), ("intramed", "Intramed")]
_TITULO_CUENTAS = "Abrite una cuenta con nosotros"
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml"}


def icono_pagina(defecto="📊"):
    """Icono de la pestaña: el logo (como imagen) o `defecto` si el archivo no esta."""
    try:
        from PIL import Image
        return Image.open(LOGO)
    except Exception:  # noqa: BLE001
        return defecto


def _uri(ruta, mime="image/png"):
    try:
        with open(ruta, "rb") as f:
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    except OSError:
        return ""


def logo_uri():
    return _uri(LOGO)


def _titulo(nombre):
    """'TodoCedears' -> 'Todo' en blanco y 'Cedears' en celeste (si el nombre no tiene ese formato, todo en blanco)."""
    n = str(nombre)
    if n.lower().startswith("todo") and len(n) > 4:
        return f"{html.escape(n[:4])}<span>{html.escape(n[4:])}</span>"
    return html.escape(n)


def _url(clave, valor):
    """URL lista para usar a partir de lo que se escribio en ENLACES_MARCA, o '' si esta vacio o no es seguro.
    Mail: acepta 'nombre@dominio.com'. WhatsApp: acepta el numero (solo digitos, con codigo de pais) o el link."""
    v = str(valor or "").strip()
    if not v:
        return ""
    if clave == "mail" and "@" in v and not v.lower().startswith("mailto:"):
        v = "mailto:" + v
    if clave == "whatsapp" and re.fullmatch(r"\+?[\d\s\-]{6,}", v):
        v = "https://wa.me/" + re.sub(r"\D", "", v)
    if not re.match(r"(?i)^(https?://|mailto:|#|/|\?)", v):
        v = "https://" + v
    return v


def _enlaces(enlaces):
    e = ENLACES_MARCA if enlaces is None else enlaces
    return {k: _url(k, e.get(k)) for k in ("youtube", "instagram", "mail", "whatsapp", "quienes_somos", "intramed")}


def _logo_cuenta(c):
    """Logo de una cuenta del menu: el archivo local de assets/marca/ si esta; si no, el icono del sitio (Google) cuando hay
    dominio; si no, la inicial del nombre en un cuadradito."""
    nombre = str(c.get("nombre") or "")
    arch = str(c.get("logo") or "")
    if arch:
        ext = os.path.splitext(arch)[1].lower()
        uri = _uri(os.path.join(_DIR, arch), _MIME.get(ext, "image/png"))
        if uri:
            return f'<img src="{uri}" alt="{html.escape(nombre)}">'
    dom = str(c.get("dominio") or "").strip()
    if dom and LOGOS_EN_LINEA == "google" and re.fullmatch(r"[A-Za-z0-9.\-]+", dom):
        # como fondo (no como <img>): si el icono no carga queda un cuadradito blanco en vez del icono de imagen rota
        return f'<span class="mc-fv" style="background-image:url(https://www.google.com/s2/favicons?domain={dom}&amp;sz=64)"></span>'
    return f'<i>{html.escape(nombre[:1].upper() or "?")}</i>'


def _cuentas_html(cuentas=None):
    """Filas del menu "Abrite una cuenta con nosotros": logo, nombre y renglon chico (solo las que tienen link)."""
    filas = []
    for c in (CUENTAS_MARCA if cuentas is None else cuentas):
        url = _url("cuenta", c.get("url"))
        if not url or not str(c.get("nombre") or "").strip():
            continue
        det = f'<small>{html.escape(str(c.get("detalle")))}</small>' if c.get("detalle") else ""
        filas.append(f'<a class="mc-cta" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
                     f'<span class="mc-lg">{_logo_cuenta(c)}</span><span class="mc-tx"><b>{html.escape(str(c["nombre"]))}</b>{det}</span></a>')
    return (f'<div class="mc-sep">{html.escape(_TITULO_CUENTAS)}</div>' + "".join(filas)) if filas else ""


def encabezado_html(nombre, datos_al=None, enlaces=None, cuentas=None):
    """Franja negra de punta a punta con el nombre (o la imagen del titulo) a la izquierda y, a la derecha, iconos, menu y el
    toro chico. Debajo, la fecha de los datos (chica, a la derecha)."""
    uri_titulo = _uri(TITULO)
    izq = (f'<img class="mc-img" src="{uri_titulo}" alt="{html.escape(str(nombre))}">' if uri_titulo
           else f'<div class="mc-t">{_titulo(nombre)}</div>')
    e = _enlaces(enlaces)
    iconos = "".join(f'<a href="{html.escape(e[k], quote=True)}" target="_blank" rel="noopener noreferrer" title="{_TITULOS_ICONO[k]}" '
                     f'aria-label="{_TITULOS_ICONO[k]}">{_SVG[k]}</a>' for k in ("youtube", "instagram", "mail", "whatsapp") if e[k])
    items = "".join(f'<a href="{html.escape(e[k], quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(t)}</a>'
                    for k, t in _ITEMS_MENU if e[k])
    items += _cuentas_html(cuentas)
    menu = f'<details class="mc-menu"><summary>Menú ▾</summary><div class="mc-pop">{items}</div></details>' if items else ""
    uri = logo_uri()
    toro = (f'<div class="mc-toro"><img src="{uri}" alt="{html.escape(NOMBRE_MARCA)}" title="{html.escape(NOMBRE_MARCA)}"></div>'
            if uri else "")
    der = (f'<div class="mc-ic">{iconos}</div>' if iconos else "") + menu + toro
    datos = f'<div class="mc-datos">Datos al <b>{html.escape(str(datos_al))}</b></div>' if datos_al else ""
    return f'<div class="mc-band"><div class="mc-in"><div class="mc-izq">{izq}</div><div class="mc-der">{der}</div></div></div>{datos}'


def pie_html(version):
    """Renglon chico del final de la pagina."""
    return f'<div class="mc-pie">Powered by <b>Claude AI</b> · v{html.escape(str(version))}</div>'
