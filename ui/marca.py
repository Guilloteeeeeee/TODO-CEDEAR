"""
Marca de la app (v1.2.36; menu rehecho en la v1.2.38; v1.2.45: gris oscuro e iconos monocromaticos a la derecha): franja gris
oscura de punta a punta arriba de todo, con el nombre TodoCedears a la izquierda (la imagen del titulo si esta en
assets/marca/titulo-todocedears.png; si no, el nombre escrito en letras blancas) y, a la derecha (v1.2.48), un solo menu desplegable
"Sobre Nosotros" (panel claro con Quiénes somos, los logos de Balanz e Inviu para abrir una cuenta, Comentarios y las redes), despues
los iconos de colores neutros (YouTube, Instagram, mail, WhatsApp de la comunidad e Intramed) y el toro de "Finanzas para Medicos" chiquito. Los links se cargan en config/ajustes.py (ENLACES_MARCA y CUENTAS_MARCA): lo que
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
    from config.ajustes import COMENTARIOS_MAIL
except Exception:  # noqa: BLE001
    COMENTARIOS_MAIL = ""
try:
    from config.ajustes import FONDO_PAGINA
except Exception:  # noqa: BLE001
    FONDO_PAGINA = "#ffffff"
try:
    from config.ajustes import LOGOS_EN_LINEA
except Exception:  # noqa: BLE001
    LOGOS_EN_LINEA = "google"

CSS = """
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:__FONDO__!important}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{overflow-x:hidden}
[data-testid="stMainBlockContainer"]{padding-top:0!important}
.mc-band{width:100vw;margin-left:calc(50% - 50vw);background:#2b2f33;box-shadow:0 2px 10px rgba(15,23,42,.14)}
.mc-in{display:flex;align-items:center;gap:22px;height:80px;padding:0 clamp(16px,3vw,48px);box-sizing:border-box}
.mc-izq{flex:1;min-width:0;display:flex;align-items:center}
.mc-t{font-size:2.5rem;font-weight:800;line-height:1;letter-spacing:-1px;color:#fff;white-space:nowrap}
.mc-t span{color:#00e85c}
.mc-img{display:block;height:48px;width:auto;max-width:100%}
.mc-nav{display:flex;align-items:center;gap:6px;flex:none}
.mc-ic{display:flex;align-items:center;gap:14px;margin-left:14px}
.mc-ic a{display:flex;align-items:center;transition:transform .12s}
.mc-ic a:hover{transform:scale(1.12)}
.mc-b{width:22px;height:22px;display:flex;align-items:center;justify-content:center;flex:none;color:#d6dadf;transition:color .12s}
.mc-ic a:hover .mc-b{color:#fff}
.mc-b svg{width:22px;height:22px;display:block;fill:currentColor}
span.mc-b{cursor:default;opacity:.7}
.mc-ic img{width:30px;height:30px;display:block;opacity:.88;transition:opacity .12s;margin:0 -3px}
.mc-ic a:hover img{opacity:1}
.mc-ic a.mc-ib img{background:#fff;border-radius:50%;padding:2px;width:30px;height:30px;opacity:1;margin:0}
.mc-it{color:#e5e7eb!important;font-size:.92rem;font-weight:600;padding:8px 12px;border-radius:8px;white-space:nowrap;text-decoration:none!important;cursor:pointer;user-select:none;list-style:none}
a.mc-it:hover,.mc-d[open]>summary.mc-it,summary.mc-it:hover{background:#3b4046;color:#fff!important}
.mc-d{position:relative}
.mc-d summary::-webkit-details-marker{display:none}
/* Menu "Sobre Nosotros" (v1.2.48): panel claro (blanco, letras oscuras) para que los logos se vean enteros y en sus colores */
.mc-pop{position:absolute;right:0;top:calc(100% + 8px);width:320px;background:#fff;color:#1f2937;border:1px solid #e3e8ee;border-radius:14px;padding:6px;z-index:1000;box-shadow:0 14px 34px rgba(15,23,42,.30);text-align:left}
.mc-pop a.mc-pi,.mc-pop summary.mc-pi,.mc-pop span.mc-pi{display:block;padding:10px 12px;border-radius:9px;color:#111827!important;font-size:.92rem;font-weight:600;text-decoration:none!important;cursor:pointer;list-style:none}
.mc-pop a.mc-pi:hover,.mc-pop summary.mc-pi:hover,.mc-pop details[open]>summary.mc-pi{background:#f1f4f8}
.mc-pop span.mc-pi{cursor:default;color:#6b7280!important}
.mc-pop span.mc-pi small{font-weight:400;font-size:.76rem;margin-left:4px}
.mc-pop summary::-webkit-details-marker{display:none}
.mc-hr{height:1px;background:#eef1f4;margin:4px 8px}
.mc-ps{padding:8px 12px 2px;font-size:.78rem;font-weight:700;color:#4b5563;letter-spacing:.2px}
.mc-logos{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:6px 12px 10px}
.mc-pop a.mc-acc{display:inline-flex;border-radius:9px;text-decoration:none!important;transition:transform .12s,box-shadow .12s}
.mc-pop a.mc-acc:hover{transform:translateY(-1px);box-shadow:0 3px 10px rgba(15,23,42,.25)}
.mc-acc img{height:40px;width:auto;max-width:100%;display:block;border-radius:9px}
.mc-lg{height:40px;min-width:40px;padding:0 12px;border-radius:9px;background:#eef1f4;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:1rem;color:#334155}
.mc-fv{display:block;width:40px;height:40px;background:#fff center/72% no-repeat;border-radius:9px;border:1px solid #e3e8ee}
.mc-form{display:flex;flex-direction:column;gap:8px;margin:0;padding:6px 12px 12px}
.mc-form input,.mc-form textarea{width:100%;box-sizing:border-box;background:#f8fafc;border:1px solid #d5dbe3;border-radius:8px;color:#111827;font:inherit;font-size:.86rem;padding:8px 10px;outline:none}
.mc-form input:focus,.mc-form textarea:focus{border-color:#64748b;background:#fff}
.mc-form textarea{min-height:96px;resize:vertical}
.mc-form button{background:#222d36;color:#fff;border:0;border-radius:8px;padding:9px 12px;font:inherit;font-size:.9rem;font-weight:700;cursor:pointer}
.mc-form button:hover{background:#33414d}
.mc-form small{font-size:.72rem;line-height:1.3;color:#6b7280}
.mc-form-t{font-size:.84rem;font-weight:600;color:#1f2937}
.mc-red{display:flex;align-items:center;gap:14px;padding:6px 12px 10px}
.mc-red a{display:flex;align-items:center;transition:transform .12s}
.mc-red a:hover{transform:scale(1.1)}
.mc-red .mc-b{color:#4b5563;width:24px;height:24px}
.mc-red .mc-b svg{width:24px;height:24px}
.mc-red a:hover .mc-b{color:#111827}
.mc-red img{width:30px;height:30px;display:block;border-radius:50%}
.mc-toro{flex:none;width:44px;height:44px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center}
.mc-toro img{width:36px;height:auto;display:block}
.mc-datos{text-align:right;font-size:12.5px;color:#4b5563;margin:6px 4px -18px}
.mc-datos b{color:#1f2937;font-weight:600}
.mc-pie{margin:30px 0 10px;padding-top:14px;border-top:1px solid #e3e8ee;text-align:center;font-size:12.5px;color:#4b5563}
.mc-pie b{color:#1f2937;font-weight:600}
.mc-aviso{max-width:900px;margin:0 auto 8px;line-height:1.5}
@media (max-width:1180px){.mc-ic{display:none}}
@media (max-width:820px){
.mc-in{flex-wrap:wrap;height:auto;gap:2px 12px;padding:8px 16px 6px}
.mc-izq{order:1;flex:1 1 0}.mc-toro{order:2;width:40px;height:40px}.mc-toro img{width:32px}
.mc-nav{order:3;flex:1 1 100%;justify-content:center;gap:2px;border-top:1px solid #41464c;padding-top:4px;margin-top:2px}
.mc-t{font-size:1.7rem}.mc-img{height:36px}.mc-it{font-size:.8rem;padding:6px 8px}.mc-x{display:none}
.mc-pop{right:auto;left:50%;transform:translateX(-50%);width:min(92vw,320px)}
}
"""
CSS = CSS.replace("__FONDO__", str(FONDO_PAGINA or "#ffffff"))

# Iconos: el glifo oficial (paths de Simple Icons, licencia CC0), dibujado de un solo color; el de Intramed es assets/marca/intramed-mono.png.
_GLIFO = {
    "youtube": "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z",
    "instagram": "M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077",
    "gmail": "M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z",
    "whatsapp": "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z",
}
_GLIFO_DE = {"youtube": "youtube", "instagram": "instagram", "mail": "gmail", "whatsapp": "whatsapp"}
_TITULOS_ICONO = {"youtube": "YouTube", "instagram": "Instagram", "mail": "Contacto por mail", "whatsapp": "WhatsApp"}


def _insignia(clave, titulo=""):
    """Icono de una red social: solo el dibujo, de un solo color (gris claro; blanco al pasar el mouse), sin insignia de color."""
    t = f' title="{titulo}"' if titulo else ""
    return (f'<span class="mc-b"{t}><svg viewBox="0 0 24 24" aria-hidden="true">'
            f'<path d="{_GLIFO[_GLIFO_DE[clave]]}"/></svg></span>')


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


_CLAVES = ("youtube", "instagram", "mail", "whatsapp", "intramed", "quienes_somos", "comentarios")


def _enlaces(enlaces):
    e = ENLACES_MARCA if enlaces is None else enlaces
    return {k: _url(k, e.get(k)) for k in _CLAVES}


def _logo_cuenta(c):
    """Logo de una cuenta del desplegable: el archivo de assets/marca/ si esta; si no, el icono del sitio (Google) cuando hay
    dominio; si no, el nombre en un cuadradito blanco."""
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
    return f'<span class="mc-lg">{html.escape(nombre)}</span>'


def _cuentas_html(cuentas=None):
    """Logos de "Abrite una cuenta con nosotros" (v1.2.48: dentro del menu "Sobre Nosotros", en sus colores sobre fondo claro): cada logo
    abre el link de apertura de cuenta. Solo las que tienen link. Sin ninguna, devuelve ''."""
    filas = []
    for c in (CUENTAS_MARCA if cuentas is None else cuentas):
        url = _url("cuenta", c.get("url"))
        if not url or not str(c.get("nombre") or "").strip():
            continue
        det = f'<small>{html.escape(str(c.get("detalle")))}</small>' if c.get("detalle") else ""
        filas.append(f'<a class="mc-acc" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" '
                     f'title="Abrir cuenta en {html.escape(str(c["nombre"]))}">{_logo_cuenta(c)}{det}</a>')
    if not filas:
        return ""
    return f'<div class="mc-ps">Abrite una cuenta con nosotros</div><div class="mc-logos">{"".join(filas)}</div>'


_MAIL_OK = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _comentarios_html(destino):
    """"Comentarios" (adentro de "Sobre Nosotros"): un cuadro para escribir cuyo envio le llega por mail a `destino` (servicio FormSubmit).
    Es un formulario HTML comun (sin JavaScript): al enviar se abre una pestana de FormSubmit que confirma el envio.
    Nombre y mail son opcionales (el mail sirve para poder contestar). `_honey` es una trampa para robots."""
    d = str(destino or "").strip()
    if not _MAIL_OK.match(d):
        return ""
    d = html.escape(d, quote=True)
    return (
        '<details class="mc-d2"><summary class="mc-pi">Comentarios ▾</summary>'
        f'<form class="mc-form" action="https://formsubmit.co/{d}" method="POST" target="_blank" accept-charset="UTF-8">'
        '<div class="mc-form-t">Contanos tu sugerencia u opinión</div>'
        '<input type="hidden" name="_subject" value="Comentarios sobre TodoCedears">'
        '<input type="hidden" name="_template" value="table">'
        '<input type="hidden" name="_captcha" value="false">'
        '<input type="text" name="_honey" style="display:none" tabindex="-1" autocomplete="off">'
        '<textarea name="mensaje" required maxlength="2000" rows="4" placeholder="Escribí acá tu mensaje"></textarea>'
        '<input type="text" name="nombre" maxlength="80" placeholder="Tu nombre (opcional)">'
        '<input type="email" name="email" maxlength="120" placeholder="Tu mail (opcional, para contestarte)">'
        '<button type="submit">Enviar</button>'
        '<small>Se abre una pestaña que confirma el envío. El mensaje pasa por FormSubmit y nos llega por mail.</small>'
        '</form></details>')


def _icono_img(clave, titulo, url, clase=""):
    """Icono hecho con una imagen de assets/marca/<clave>.png (ej. el logo de Intramed). Sin archivo, no se muestra.
    v1.2.48: se usa el logo a todo color (el de un solo color casi no se veia); en la franja va sobre un circulo blanco (clase mc-ib)."""
    uri = _uri(os.path.join(_DIR, f"{clave}.png")) or _uri(os.path.join(_DIR, f"{clave}-mono.png"))
    if not url or not uri:
        return ""
    c = f' class="{clase}"' if clase else ""
    return (f'<a{c} href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" title="{titulo}" aria-label="{titulo}">'
            f'<img src="{uri}" alt="{titulo}"></a>')


def _sobre_nosotros_html(e, cuentas=None, comentarios_mail=None):
    """Menu desplegable "Sobre Nosotros" (v1.2.48): reemplaza a los textos sueltos de la franja. Adentro, en un panel claro: Quiénes somos,
    los logos para abrir una cuenta con nosotros, Comentarios y, abajo, las redes (YouTube, Instagram, mail, WhatsApp e Intramed: en el
    celular los iconos de la franja se esconden y asi siguen a mano). Lo que no tiene link no se muestra (Quiénes somos queda como 'próximamente')."""
    if e["quienes_somos"]:
        qs = f'<a class="mc-pi" href="{html.escape(e["quienes_somos"], quote=True)}" target="_blank" rel="noopener noreferrer">Quiénes somos</a>'
    else:
        qs = '<span class="mc-pi" title="Próximamente">Quiénes somos <small>(próximamente)</small></span>'
    bloques = [qs]
    cuentas_html = _cuentas_html(cuentas)
    if cuentas_html:
        bloques += ['<div class="mc-hr"></div>', cuentas_html]
    if e["comentarios"]:
        com = (f'<a class="mc-pi" href="{html.escape(e["comentarios"], quote=True)}" target="_blank" rel="noopener noreferrer" '
               f'title="Escribinos tus sugerencias u opiniones">Comentarios</a>')
    else:
        com = _comentarios_html(COMENTARIOS_MAIL if comentarios_mail is None else comentarios_mail)
    if com:
        bloques += ['<div class="mc-hr"></div>', com]
    redes = ""
    for k in ("youtube", "instagram", "mail", "whatsapp"):
        if e[k]:
            redes += (f'<a href="{html.escape(e[k], quote=True)}" target="_blank" rel="noopener noreferrer" '
                      f'title="{_TITULOS_ICONO[k]}" aria-label="{_TITULOS_ICONO[k]}">{_insignia(k)}</a>')
    redes += _icono_img("intramed", "Intramed", e["intramed"])
    if redes:
        bloques += ['<div class="mc-hr"></div>', '<div class="mc-ps">Seguinos</div>', f'<div class="mc-red">{redes}</div>']
    return f'<details class="mc-d"><summary class="mc-it">Sobre Nosotros ▾</summary><div class="mc-pop">{"".join(bloques)}</div></details>'


def encabezado_html(nombre, datos_al=None, enlaces=None, cuentas=None, comentarios_mail=None):
    """Franja gris oscura de punta a punta: a la izquierda el nombre (o la imagen del titulo); a la derecha el menu "Sobre Nosotros"
    (v1.2.48), los iconos de un solo color (Intramed a todo color sobre un circulo blanco) y el toro chico."""
    uri_titulo = _uri(TITULO)
    izq = (f'<img class="mc-img" src="{uri_titulo}" alt="{html.escape(str(nombre))}">' if uri_titulo
           else f'<div class="mc-t">{_titulo(nombre)}</div>')
    e = _enlaces(enlaces)
    iconos = ""
    for k in ("youtube", "instagram", "mail", "whatsapp"):
        if e[k]:
            iconos += (f'<a href="{html.escape(e[k], quote=True)}" target="_blank" rel="noopener noreferrer" '
                       f'title="{_TITULOS_ICONO[k]}" aria-label="{_TITULOS_ICONO[k]}">{_insignia(k)}</a>')
        elif k == "whatsapp":
            # visible desde ya; sin link todavia queda como insignia sin accion (se activa al cargar ENLACES_MARCA["whatsapp"])
            iconos += _insignia(k, "WhatsApp: próximamente")
    iconos += _icono_img("intramed", "Intramed", e["intramed"], "mc-ib")
    iconos = f'<div class="mc-ic">{iconos}</div>' if iconos else ""
    nav = f'<div class="mc-nav">{_sobre_nosotros_html(e, cuentas, comentarios_mail)}{iconos}</div>'
    uri = logo_uri()
    toro = (f'<div class="mc-toro"><img src="{uri}" alt="{html.escape(NOMBRE_MARCA)}" title="{html.escape(NOMBRE_MARCA)}"></div>'
            if uri else "")
    datos = f'<div class="mc-datos">Datos al <b>{html.escape(str(datos_al))}</b></div>' if datos_al else ""
    return f'<div class="mc-band"><div class="mc-in"><div class="mc-izq">{izq}</div>{nav}{toro}</div></div>{datos}'


def pie_html(version, aviso=None, datos_al=None, precios=None):
    """Final de la pagina (desde la v1.2.41): el aviso legal, la fecha de los datos ("Datos al ...") y "Powered by Claude AI · versión"."""
    av = f'<div class="mc-aviso"><b>Aviso:</b> {html.escape(str(aviso))}</div>' if aviso else ""
    dat = f'Datos al <b>{html.escape(str(datos_al))}</b> · ' if datos_al else ""
    if precios:      # v1.2.46: texto ya armado por la app (lleva un <b>); sin precios en vivo no se muestra nada
        dat += f'{precios} · '
    return f'<div class="mc-pie">{av}<div>{dat}Powered by <b>Claude AI</b> · v{html.escape(str(version))}</div></div>'
