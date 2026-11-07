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
chk(re.search(r'SOLO_POR_DOMINIO = \{[^}]*"ASML"', d) is not None, "ASML se baja por dominio")
print(f"OK {ok} MAL {mal}")
