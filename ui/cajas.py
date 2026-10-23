"""
Estilo de los recuadros "Filtro de empresas" (antes "Screener") y "Noticias Calientes" (v1.2.40; desde la v1.2.45: paneles blancos
limpios con sombra suave, sin bordes duros, uno al lado del otro).
Noticias Calientes usa su propio CSS (ui/noticias.py, clase .nt) con la misma sombra; aca va el del Filtro de empresas, que es un
st.expander de Streamlit (con widgets adentro) metido en un contenedor con clave "caja_screener". Las dos cajas estan dentro de
un contenedor con clave "fila_cajas" (dos columnas): en pantallas anchas la columna que se abre se ensancha (flex 1,7 contra 1).
Para cambiar la sombra de los dos recuadros: --sombra-panel (abajo) y .nt en ui/noticias.py.
"""

CSS = """
.st-key-fila_cajas{margin:0 0 2px}
.st-key-fila_cajas [data-testid="stHorizontalBlock"]{align-items:flex-start}
.st-key-caja_screener{margin:0}
.st-key-caja_screener [data-testid="stExpander"]{background:#fff;border:0!important;border-radius:14px;overflow:visible;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07)}
.st-key-caja_screener [data-testid="stExpander"] details{border:0!important;background:transparent!important}
.st-key-caja_screener [data-testid="stExpander"] summary{padding:0 1rem;min-height:48px;display:flex;align-items:center;background:transparent!important;border-radius:14px}
.st-key-caja_screener [data-testid="stExpander"] summary:hover{background:#f6f8fa!important}
.st-key-caja_screener [data-testid="stExpander"] summary p{font-weight:700;font-size:1.02rem;color:#111827}
.st-key-caja_screener [data-testid="stExpanderDetails"]{padding:.5rem 1rem 1rem;border-top:1px solid #eef1f4!important}
.st-key-caja_screener [data-testid="stExpander"] .flt-t{margin-top:.2rem}
@media (min-width:821px){
.st-key-fila_cajas [data-testid="stHorizontalBlock"]:has(.st-key-caja_screener)>[data-testid="stColumn"]{flex:1 1 0!important;width:auto!important;min-width:0!important;transition:flex-grow .18s ease}
.st-key-fila_cajas [data-testid="stHorizontalBlock"]:has(.st-key-caja_screener)>[data-testid="stColumn"]:has(details[open]){flex:1.7 1 0!important}
}
"""
