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


# ---------------------------------------------------------------------------
# v1.2.52: tipografia condensada (Roboto Condensed, licencia Apache 2.0, assets/fuentes/LICENCIA-RobotoCondensed.txt) para titulos, tickers y numeros
# financieros, al estilo de las planillas de Morningstar / Univers Condensed. El texto corrido sigue en Inter. Se apaga con FUENTE_NUMEROS = "".
# ---------------------------------------------------------------------------
def css_condensada(nombre: str = None) -> str:
    """CSS de la fuente condensada para titulos y numeros ('' si esta apagada o faltan los archivos). Va DESPUES de css_fuente()."""
    if nombre is None:
        try:
            from config.ajustes import FUENTE_NUMEROS as nombre
        except Exception:  # noqa: BLE001
            nombre = ""
    if str(nombre).strip().lower() != "roboto condensed":
        return ""
    if "cond" not in _cache:
        caras = []
        for peso in (400, 500, 600, 700):
            try:
                with open(os.path.join(_DIR, f"roboto-condensed-latin-{peso}.woff2"), "rb") as f:
                    datos = base64.b64encode(f.read()).decode()
            except OSError:
                caras = []
                break
            caras.append("@font-face{font-family:'RobotoCond';font-style:normal;font-display:swap;font-weight:%d;"
                         "src:url(data:font/woff2;base64,%s) format('woff2')}" % (peso, datos))
        _cache["cond"] = "".join(caras)
    if not _cache["cond"]:
        return ""
    # v1.2.52 (pedido de Guille): la fuente condensada va en TODA la app, menos el titulo TodoCedears (que es una imagen; si falta, el titulo de texto
    # .mc-t conserva su tipografia). Se excluyen los iconos de Streamlit.
    fam = "'RobotoCond','Roboto Condensed','Arial Narrow',sans-serif"
    return (_cache["cond"]
            + ".stApp.stApp.stApp :is(p,li,label,h1,h2,h3,h4,h5,h6,button,input,textarea,select,table,th,td,div,span,a,small,b,strong,summary)"
              f":not([data-testid='stIconMaterial']):not([class*='material-symbols']):not(.mc-t):not(.mc-t *){{font-family:{fam}!important}}")
