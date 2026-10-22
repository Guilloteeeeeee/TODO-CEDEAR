"""
Banderas de los paises (v1.2.21).

Se usan imagenes (assets/flags/<codigo>.png) y no emojis: en Windows los emojis de banderas se ven como
dos letras ("US"). Las imagenes se incrustan en la pagina (no dependen de ningun servicio) y se declaran
una sola vez en un bloque de estilos (css_banderas), asi no se repiten en cada fila.

Fuente de las imagenes: paquete flag-icons (licencia MIT), reducidas a 48x36.
"""
import base64
import functools
import html
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "assets" / "flags"

# nombre del pais (en castellano o en ingles, como llega de Yahoo) -> codigo de 2 letras
ISO = {
    "United States": "us", "Estados Unidos": "us", "United Kingdom": "gb", "Reino Unido": "gb",
    "Brazil": "br", "Brasil": "br", "Japan": "jp", "Japón": "jp", "India": "in",
    "Ireland": "ie", "Irlanda": "ie", "Canada": "ca", "Canadá": "ca", "Spain": "es", "España": "es",
    "Netherlands": "nl", "Países Bajos": "nl", "China": "cn", "Germany": "de", "Alemania": "de",
    "Australia": "au", "Uruguay": "uy", "Italy": "it", "Italia": "it", "Sweden": "se", "Suecia": "se",
    "Taiwan": "tw", "Taiwán": "tw", "France": "fr", "Francia": "fr", "Norway": "no", "Noruega": "no",
    "Switzerland": "ch", "Suiza": "ch", "Denmark": "dk", "Dinamarca": "dk", "Argentina": "ar",
    "Mexico": "mx", "México": "mx", "Chile": "cl", "Colombia": "co", "Peru": "pe", "Perú": "pe",
    "Israel": "il", "South Korea": "kr", "Corea del Sur": "kr", "Hong Kong": "hk",
    "Singapore": "sg", "Singapur": "sg", "Belgium": "be", "Bélgica": "be", "Finland": "fi",
    "Finlandia": "fi", "Luxembourg": "lu", "Luxemburgo": "lu", "South Africa": "za",
    "Sudáfrica": "za", "Bermuda": "bm", "Bermudas": "bm", "Cayman Islands": "ky",
    "Islas Caimán": "ky", "Panama": "pa", "Panamá": "pa", "Portugal": "pt", "Austria": "at",
    "Greece": "gr", "Grecia": "gr", "Turkey": "tr", "Turquía": "tr", "Russia": "ru", "Rusia": "ru",
    "Jersey": "je", "Guernsey": "gg", "Poland": "pl", "Polonia": "pl", "New Zealand": "nz",
    "Nueva Zelanda": "nz", "Indonesia": "id", "Malaysia": "my", "Malasia": "my", "Thailand": "th",
    "Tailandia": "th", "Vietnam": "vn", "Philippines": "ph", "Filipinas": "ph",
}


def codigo(pais):
    """Codigo de 2 letras del pais, o None si no se conoce o no hay imagen."""
    if not isinstance(pais, str) or not pais:
        return None
    c = ISO.get(pais)
    return c if c and (CARPETA / f"{c}.png").exists() else None


@functools.lru_cache(maxsize=None)
def _data_uri(c):
    return "data:image/png;base64," + base64.b64encode((CARPETA / f"{c}.png").read_bytes()).decode()


@functools.lru_cache(maxsize=1)
def css_banderas():
    """Bloque <style> con todas las banderas disponibles (se pone una sola vez por pagina)."""
    reglas = [".bnd{display:inline-block;width:24px;height:18px;background-size:cover;background-position:center;"
              "border-radius:2px;border:1px solid rgba(0,0,0,.18);vertical-align:middle}",
              ".bnd-s{width:17px;height:13px}"]
    if CARPETA.exists():
        for f in sorted(CARPETA.glob("*.png")):
            reglas.append(f'.bnd-{f.stem}{{background-image:url("{_data_uri(f.stem)}")}}')
    return "<style>" + "".join(reglas) + "</style>"


def bandera_html(pais, con_nombre=False, chica=False):
    """
    Bandera como <span> (hay que haber puesto css_banderas() en la pagina). Con el nombre del pais
    como texto emergente. Si no hay imagen, devuelve el nombre del pais (o '—' si no hay pais).
    """
    if not isinstance(pais, str) or not pais:
        return "—"
    c = codigo(pais)
    if not c:
        return html.escape(pais)
    n = html.escape(pais, quote=True)
    clase = f"bnd bnd-s bnd-{c}" if chica else f"bnd bnd-{c}"
    img = f'<span class="{clase}" title="{n}" role="img" aria-label="{n}"></span>'
    return f'{img} {html.escape(pais)}' if con_nombre else img
