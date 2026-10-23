"""
Estilo de los recuadros "Screener" y "Noticias Calientes" (v1.2.40): fondo celeste muy suave, borde fino y esquinas redondeadas.
Noticias Calientes usa su propio CSS (ui/noticias.py, clase .nt) con los mismos colores; aca va el del Screener, que es un
st.expander de Streamlit (con widgets adentro) metido en un contenedor con clave "caja_screener".
Para cambiar el color de los dos recuadros: fondo #f1f6fc, borde #d3e2f2, texto de titulo #0f2a43 (ver tambien ui/noticias.py).
"""

CSS = """
.st-key-caja_screener{margin:6px 0 14px}
.st-key-caja_screener [data-testid="stExpander"]{background:#f1f6fc;border:1px solid #d3e2f2;border-radius:14px;overflow:visible}
.st-key-caja_screener [data-testid="stExpander"] details{border:0!important;background:transparent!important}
.st-key-caja_screener [data-testid="stExpander"] summary{padding:.65rem 1rem;background:transparent!important;border-radius:14px}
.st-key-caja_screener [data-testid="stExpander"] summary:hover{background:#e8f0fa!important}
.st-key-caja_screener [data-testid="stExpander"] summary p{font-weight:700;font-size:1.02rem;color:#0f2a43}
.st-key-caja_screener [data-testid="stExpanderDetails"]{padding:.5rem 1rem 1rem;border-top:1px solid #dde8f4!important}
.st-key-caja_screener [data-testid="stExpander"] .flt-t{margin-top:.2rem}
"""
