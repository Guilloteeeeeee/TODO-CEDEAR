"""
Pagina "Quiénes somos" (v1.2.49): se abre desde el menu "Sobre Nosotros" de la barra (?pagina=quienes). El texto es el que mando Guille, con retoques
minimos de redaccion (marcados abajo). Las dos fotos son assets/marca/foto-guillermo.png y foto-maria-laura.png (recortes circulares de la imagen
original); si faltan, se muestran las iniciales. Para cambiar el texto o los datos de cada persona, editar las constantes de este archivo.
"""
import html

from ui import marca as _marca

TITULO = "Quiénes somos"
# Retoques de redaccion respecto del original: "la primer comunidad" -> "la primera comunidad", "surgió en la necesidad" -> "surgió de la necesidad",
# un espacio doble sacado, una coma agregada ("dinero, lo cual") y "para que podamos estar" -> "para poder estar".
PARRAFOS = [
    "Este espacio surgió de la necesidad de gestionar e invertir el dinero que ganamos con nuestra profesión. Estamos acostumbrados a trabajar por el "
    "dinero, lo cual nos significa restarle tiempo a nuestros seres queridos y a nosotros mismos. Tenemos que cambiar esto en forma urgente.",
    "Desde Finanzas para Médicos Argentina tomamos un compromiso para con la sociedad médica y otros actores del sistema de salud. Nos fijamos el "
    "propósito de ayudar educando financieramente. Este es un tema del que no se habla; nos propusimos cambiar eso.",
]
# v1.2.52: la primera frase va en negrita (texto nuevo de Guille: "para profesionales de la salud", "hecha por médicos").
PRIMERA = ("Somos Finanzas para Médicos Argentina, la primera comunidad de educación financiera para profesionales de la salud de nuestro país, "
           "hecha por médicos")
CIERRE = "Construí el futuro financiero que te merecés. Contás con nosotros."
# Cada persona: nombre, foto (archivo de assets/marca/), iniciales (si no esta la foto) y las lineas de abajo.
# Ojo: el original decia "Agente Productor avalado por la Comisión Nacional de Valores"; la CNV no "avala" a las personas: las registra. Se escribio
# "registrado en la CNV" (se puede volver a la frase original editando la linea).
PERSONAS = [
    {"nombre": "Guillermo Di Palma", "foto": "foto-guillermo.png", "iniciales": "GD",
     "lineas": ["Médico gastroenterólogo, MN 140583.",
                "Agente Productor registrado en la Comisión Nacional de Valores (CNV), Matrícula 2372."]},
    {"nombre": "María Laura García", "foto": "foto-maria-laura.png", "iniciales": "MG",
     "lineas": ["Médica gastroenteróloga, MN 100403.",
                "Community Manager a cargo de los medios de difusión. Inversora Individual."]},
]

CSS = """
.qs{max-width:820px;margin:26px auto 8px;background:#fff;border-radius:16px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 8px 24px rgba(15,23,42,.08);padding:30px 34px 34px}
.qs-vol{display:inline-block;margin:22px 0 0;font-size:14px;font-weight:600;color:#1d4ed8!important;text-decoration:none!important}
.qs-vol:hover{text-decoration:underline!important}
.qs-tit{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:0 0 16px}
.qs-tit img{width:52px;height:auto;display:block;flex:none}
.qs h1{font-size:2rem;font-weight:800;letter-spacing:-.5px;color:#0f172a;margin:0;padding:0}
.qs p.prim{font-weight:700;color:#0f172a;font-size:17px}
.qs .bajada{font-size:13px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:#6b7280;margin:0 0 18px}
.qs p{font-size:16px;line-height:1.65;color:#1f2937;margin:0 0 14px}
.qs p.cierre{font-weight:700;color:#0f172a;font-size:17px;margin-top:20px}
.qs-pers{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:30px;padding-top:26px;border-top:1px solid #eef1f4}
.qs-p{text-align:center}
.qs-p img,.qs-p .ini{width:112px;height:112px;border-radius:50%;display:block;margin:0 auto 12px;object-fit:cover;box-shadow:0 2px 10px rgba(15,23,42,.18)}
.qs-p .ini{background:#e5e7eb;color:#374151;font-size:34px;font-weight:700;display:flex;align-items:center;justify-content:center}
.qs-p .nm{font-size:17px;font-weight:700;color:#0f172a;margin-bottom:6px}
.qs-p .ln{font-size:13.5px;line-height:1.5;color:#4b5563}
@media (max-width:700px){.qs-tit img{width:40px}.qs{padding:22px 18px 26px;margin-top:14px}.qs-pers{grid-template-columns:1fr}.qs h1{font-size:1.6rem}}
"""


def _persona(p):
    uri = _marca._uri(_marca._DIR + "/" + p["foto"]) if p.get("foto") else ""
    if uri:
        foto = f'<img src="{uri}" alt="{html.escape(p["nombre"])}">'
    else:
        foto = f'<div class="ini">{html.escape(p.get("iniciales", ""))}</div>'
    lineas = "".join(f'<div class="ln">{html.escape(t)}</div>' for t in p["lineas"])
    return f'<div class="qs-p">{foto}<div class="nm">{html.escape(p["nombre"])}</div>{lineas}</div>'


def quienes_html():
    """La pagina completa (el enlace para volver y la tarjeta con el texto y las dos personas). v1.2.52: el toro va a la derecha del titulo y
    se saco el nombre de la marca que estaba debajo del titulo."""
    parrafos = "".join(f"<p>{html.escape(t)}</p>" for t in PARRAFOS)
    personas = "".join(_persona(p) for p in PERSONAS)
    uri = _marca.logo_uri()
    toro = f'<img src="{uri}" alt="{html.escape(_marca.NOMBRE_MARCA)}">' if uri else ""
    return ('<a class="qs-vol" href="?" target="_self">← Volver al Inicio</a>'
            f'<div class="qs"><div class="qs-tit"><h1>{TITULO}</h1>{toro}</div>'
            f'<p class="prim">{html.escape(PRIMERA)}.</p>{parrafos}<p class="cierre">{html.escape(CIERRE)}</p><div class="qs-pers">{personas}</div></div>')
