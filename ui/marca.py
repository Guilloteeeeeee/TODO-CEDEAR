"""
Marca de la app (v1.2.34): el logo de "Finanzas para Médicos" (la comunidad y el canal de YouTube del dueño de la herramienta)
al lado del nombre, y como icono de la pestaña del navegador. El logo es de su propiedad y viene en assets/marca/.
"""
import base64
import html
import os

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "marca")
LOGO = os.path.join(_DIR, "finanzas-para-medicos-128.png")
NOMBRE_MARCA = "Finanzas para Médicos"

CSS = """
.marca{display:flex;align-items:center;gap:18px;margin:0 0 4px}
.marca img{width:68px;height:auto;flex:none}
.marca-t{font-size:2.6rem;font-weight:700;line-height:1.1;letter-spacing:-.5px;color:#0f172a}
.marca-s{margin-top:6px;font-size:1rem;color:#334155}
.marca-v{margin-left:auto;align-self:flex-start;padding-top:10px;font-size:.85rem;color:#64748b;white-space:nowrap}
"""


def icono_pagina(defecto="📊"):
    """Icono de la pestaña: el logo (como imagen) o `defecto` si el archivo no esta."""
    try:
        from PIL import Image
        return Image.open(LOGO)
    except Exception:  # noqa: BLE001
        return defecto


def logo_uri():
    try:
        with open(LOGO, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except OSError:
        return ""


def encabezado_html(nombre, subtitulo, version):
    """Logo + nombre + subtitulo (+ version a la derecha). Si falta el logo, se muestra igual sin el."""
    uri = logo_uri()
    img = f'<img src="{uri}" alt="{html.escape(NOMBRE_MARCA)}" title="{html.escape(NOMBRE_MARCA)}">' if uri else ""
    return (f'<div class="marca">{img}<div><div class="marca-t">{html.escape(nombre)}</div>'
            f'<div class="marca-s">{html.escape(subtitulo)}</div></div>'
            f'<div class="marca-v">v{html.escape(str(version))}</div></div>')
