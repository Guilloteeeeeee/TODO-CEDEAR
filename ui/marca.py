"""
Marca de la app: el cartel oscuro de arriba (v1.2.35) con el nombre en letras blancas, el subtitulo y el logo de
"Finanzas para Médicos" (la comunidad y el canal de YouTube del dueño de la herramienta) sobre un disco blanco.
El logo es de su propiedad y viene en assets/marca/. Tambien es el icono de la pestaña del navegador.
"""
import base64
import html
import os

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "marca")
LOGO = os.path.join(_DIR, "finanzas-para-medicos-128.png")
NOMBRE_MARCA = "Finanzas para Médicos"

# Azul noche con un leve degradado; el nombre en blanco ("Todo") y celeste ("Cedears"), como los titulos de los sitios de finanzas.
CSS = """
.marca{display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin:0 0 18px;padding:20px 28px;border-radius:14px;
  background:linear-gradient(120deg,#07121f 0%,#0c2038 55%,#123354 100%);box-shadow:0 4px 14px rgba(7,18,31,.28);
  border-bottom:3px solid #2fa4f0}
.marca-logo{flex:none;width:68px;height:68px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 0 3px rgba(255,255,255,.18)}
.marca-logo img{width:50px;height:auto;display:block}
.marca-tx{flex:1 1 320px;min-width:0}
.marca-t{font-size:2.7rem;font-weight:800;line-height:1.05;letter-spacing:-.8px;color:#ffffff}
.marca-t span{color:#4cb8ff}
.marca-s{margin-top:7px;font-size:1.05rem;line-height:1.35;font-weight:400;color:#cbd9e8}
.marca-d{margin-left:auto;align-self:flex-start;text-align:right;font-size:.8rem;line-height:1.5;color:#8fa6bd;white-space:nowrap}
.marca-d b{color:#c3d3e3;font-weight:600}
@media (max-width:760px){.marca{padding:16px 18px}.marca-t{font-size:2.1rem}.marca-d{margin-left:0;text-align:left}}
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


def _titulo(nombre):
    """'TodoCedears' -> 'Todo' en blanco y 'Cedears' en celeste (si el nombre no tiene ese formato, todo en blanco)."""
    n = str(nombre)
    if n.lower().startswith("todo") and len(n) > 4:
        return f"{html.escape(n[:4])}<span>{html.escape(n[4:])}</span>"
    return html.escape(n)


def encabezado_html(nombre, subtitulo, version, datos_al=None):
    """Cartel oscuro: logo sobre disco blanco + nombre + subtitulo; a la derecha, en chico, la fecha de los datos y la version.
    Si falta el logo, se muestra igual sin el."""
    uri = logo_uri()
    logo = (f'<div class="marca-logo"><img src="{uri}" alt="{html.escape(NOMBRE_MARCA)}" title="{html.escape(NOMBRE_MARCA)}"></div>'
            if uri else "")
    datos = f"Datos al <b>{html.escape(str(datos_al))}</b><br>" if datos_al else ""
    return (f'<div class="marca">{logo}<div class="marca-tx"><div class="marca-t">{_titulo(nombre)}</div>'
            f'<div class="marca-s">{html.escape(subtitulo)}</div></div>'
            f'<div class="marca-d">{datos}v{html.escape(str(version))}</div></div>')
