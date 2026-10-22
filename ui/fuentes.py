"""
Tipografia de la app (v1.2.33; numeros tabulares en toda la app desde la v1.2.34). La fuente Inter (licencia SIL OFL, ver assets/fuentes/LICENCIA-Inter.txt) viene dentro
del proyecto y se incrusta en el CSS, asi no depende de internet ni de Google Fonts. Se elige en config/ajustes.py (FUENTE_APP).
"""
import base64
import os

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fuentes")
_PESOS = (400, 500, 600, 700)
_cache = {}


def _face(peso: int):
    ruta = os.path.join(_DIR, f"inter-latin-{peso}.woff2")
    try:
        with open(ruta, "rb") as f:
            datos = base64.b64encode(f.read()).decode()
    except OSError:
        return None
    return ("@font-face{font-family:'Inter';font-style:normal;font-display:swap;font-weight:%d;"
            "src:url(data:font/woff2;base64,%s) format('woff2')}" % (peso, datos))


def css_fuente(nombre: str = None) -> str:
    """CSS que aplica la fuente a toda la pantalla ('' si se usa la de Streamlit o si faltan los archivos)."""
    if nombre is None:
        try:
            from config.ajustes import FUENTE_APP as nombre
        except Exception:  # noqa: BLE001
            nombre = ""
    if str(nombre).strip().lower() != "inter":
        return ""
    if "inter" not in _cache:
        caras = [c for c in (_face(p) for p in _PESOS) if c]
        _cache["inter"] = "".join(caras) if len(caras) == len(_PESOS) else ""
    if not _cache["inter"]:
        return ""
    familia = "'Inter','Source Sans Pro',-apple-system,'Segoe UI',Roboto,Arial,sans-serif"
    # Se excluyen los iconos de Streamlit (usan su propia fuente de simbolos)
    return (_cache["inter"]
            + f".stApp,.stApp :is(p,li,label,h1,h2,h3,h4,h5,h6,button,input,textarea,select,table,th,td,div,span,a,small,b,strong)"
              f":not([data-testid='stIconMaterial']):not([class*='material-symbols']){{font-family:{familia}!important}}"
            # Numeros tabulares (todas las cifras con el mismo ancho: los totales y porcentajes quedan alineados, como en
            # una planilla) en toda la app, y la "a" simple de Inter (cv11) solo en la tabla
            + ".stApp{font-variant-numeric:tabular-nums}"
            + ".tv2,.tv-ini{font-feature-settings:'tnum' 1,'cv11' 1}")
