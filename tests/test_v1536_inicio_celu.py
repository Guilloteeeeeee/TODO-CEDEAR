"""v1.5.36: pantalla de inicio en celu (tortas + tabla), «Aguarde» antes de la barra de mercados, ASML por dominio."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import inicio
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
h = inicio.hero_html()
media = re.search(r"@media \(max-width:980px\)\{(.*?)\n\}", inicio.CSS, re.S).group(1)
chk(".hr-marco{display:none}" not in media, "el mosaico de tortas y tabla ya no se esconde en el celu")
for c in ("hr-tt", "hr-ley", "hr-tj", "hr-tr", "hr-bar"):
    chk(f'class="{c}"' in h, f"clase {c} en el HTML")
    chk(f".{c}" in media, f"regla celu para {c}")
chk("display:none" in media and "nth-child(4)" in media, "en el celu se oculta la columna Dividendo")
chk("Evalu" in h and "Microsoft" in h, "sigue la vista previa con empresas reales")
src = open("app.py", encoding="utf-8").read()
# v1.5.43: la barra ya no frena la página (se dibuja al final si no estaba guardada), así que no hace falta el «Aguarde» previo
chk("_mk.obtener(esperar=0)" in src and 'ctx["barra"] = st.empty()' in src, "la barra de mercados no frena la página (v1.5.43)")
chk('APP_VERSION = "1.5.' in src, "version")
d = open("descargar_logos.py", encoding="utf-8").read()
# v1.5.52: el logo de ASML es el que mandó Guille (azul sobre blanco) y el programa de logos no lo pisa
chk(re.search(r'MANUALES = \{[^}]*"ASML"', d) is not None, "ASML: logo puesto a mano, no se pisa")
from PIL import Image
_px = Image.open("static/logos/ASML.png").convert("RGB").getpixel((2, 2))
chk(min(_px) > 240, "ASML: logo con fondo blanco (no el oscuro)")
print(f"OK {ok} MAL {mal}")
