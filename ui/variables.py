"""
"Variables a ver en la tabla" (v1.2.49): el control que va arriba de todo en el Filtro de empresas.

Reemplaza a "Columnas de la tabla" y a "Agregar criterios" (v1.2.47 y v1.2.48): ahora hay UNA sola lista con todas las variables que se pueden ver en la
tabla. Las de siempre (Empresa, Sector e Industria, Precio, Capitalizacion bursatil, Valoracion y Puntaje de calidad) vienen elegidas; las demas
(Dividend Yield, Fair Value, P/E...) se suman. Cada una es una pastilla que se prende y se apaga; al pasar el mouse se ve una explicacion corta, y al
prenderla aparecen abajo sus filtros (Sector e Industria, un minimo y un maximo de precio, etc.). Empresa se ve siempre.

Este modulo solo sabe de la lista (nombres, ayudas, orden y que columnas o criterios representa cada una); la pantalla la dibuja app.py.
"""
import unicodedata

from ui import criterios as _criterios
from ui.tabla_visual import COLUMNAS_BASE, OPCIONALES

# Explicaciones cortas de las variables de siempre (se ven al pasar el mouse por la pastilla). Las de los criterios salen de ui/criterios.py.
AYUDA_BASE = {
    "nombre": "Nombre de la empresa y, abajo, su país y su ticker (el código con el que cotiza). Tocá el nombre para ver su página con todo el detalle. "
              "Se ve siempre.",
    "sector_txt": "A qué se dedica la empresa: el sector y, abajo, su industria. Es solo información: no cambia la valoración.",
    "precio_actual": "Lo que cuesta una acción en su mercado de origen, en dólares (US$).",
    "market_cap": "Lo que vale la empresa entera en la bolsa (precio × cantidad de acciones), en dólares (US$).",
    "fv_upside": "Una estimación (no una recomendación) de si la empresa cotiza barata, razonable o cara frente a sus propios múltiplos históricos.",
    "score_total": "De 0 (más cara) a 100 (más barata). Hoy mide el precio contra su historia; más adelante sumará la calidad del negocio.",
}

# Lista completa, en el orden en que se muestran las pastillas: las de siempre y despues los criterios.
VARIABLES = (
    [{"clave": k, "nombre": t, "ayuda": AYUDA_BASE[k], "base": True, "fija": k == "nombre"} for k, t, _ in COLUMNAS_BASE]
    + [{"clave": c["clave"], "nombre": c["nombre"], "ayuda": c["ayuda"], "base": False, "fija": False} for c in _criterios.CRITERIOS]
)
POR_CLAVE = {v["clave"]: v for v in VARIABLES}
DEFECTO = [v["clave"] for v in VARIABLES if v["base"]]          # las que vienen elegidas
CLAVES = [v["clave"] for v in VARIABLES]


# v1.2.50: las pastillas se muestran en dos grupos para que no sean una lista de 15: "Datos básicos" y "Múltiplos" (las razones precio/algo).
CLAVES_MULTIPLOS = ("per_actual", "ev_ebitda_actual", "p_fcf_actual", "p_b_actual", "ps_actual", "peg_actual")
GRUPOS = (("Datos básicos", lambda v: v["clave"] not in CLAVES_MULTIPLOS), ("Múltiplos", lambda v: v["clave"] in CLAVES_MULTIPLOS))


def agrupar(variables):
    """[(titulo del grupo, [variables])] en el orden de GRUPOS, sin los grupos vacios (el buscador puede dejar uno sin pastillas)."""
    return [(titulo, [v for v in variables if pertenece(v)]) for titulo, pertenece in GRUPOS if any(pertenece(v) for v in variables)]


def normalizar(texto):
    """Minusculas, sin tildes ni signos: 'Posición' -> 'posicion'. Para el buscador de variables."""
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii").casefold()
    return "".join(ch for ch in t if ch.isalnum())


def seleccion_valida(sel):
    """Lista de claves elegidas, sin repetidas ni desconocidas y siempre con Empresa. None o algo roto = las de siempre."""
    if not isinstance(sel, (list, tuple, set)):
        return list(DEFECTO)
    vistas = {c for c in sel if c in POR_CLAVE}
    vistas.add("nombre")
    return [c for c in CLAVES if c in vistas]


def visibles_de(sel):
    """Claves de las columnas de siempre (sin Empresa) que se ven, segun lo elegido."""
    s = set(seleccion_valida(sel))
    return [k for k, _ in OPCIONALES if k in s]


def extras_de(sel):
    """Criterios elegidos (los que suman una columna), en el orden de ui/criterios.py."""
    s = set(seleccion_valida(sel))
    return [c for c in _criterios.CRITERIOS if c["clave"] in s]


def buscar(consulta):
    """Variables cuyo nombre contiene lo escrito (o, si ninguna, su explicacion), sin importar mayusculas ni tildes. Sin texto, todas."""
    q = normalizar(consulta)
    if not q:
        return list(VARIABLES)
    por_nombre = [v for v in VARIABLES if q in normalizar(v["nombre"])]
    if por_nombre:                              # si el nombre ya coincide, no se suman las que solo lo nombran en su explicacion
        return por_nombre
    return [v for v in VARIABLES if q in normalizar(v["ayuda"])]
