"""
Ajustes del CEDEAR Screener que se pueden cambiar sin tocar el resto del codigo.

STOCK_ANALYSIS_MODO
    "apagado"   -> no se consulta Stock Analysis (solo Yahoo Finance).
    "respaldo"  -> (v1.2.11) Yahoo es la fuente principal; Stock Analysis se consulta
                   solo para completar medianas que Yahoo dejo vacias.
    "principal" -> (v1.2.13, por defecto) Stock Analysis es la fuente principal: valor actual y mediana de los
                   ultimos 5 anios fiscales salen de la MISMA pagina; Yahoo queda como respaldo
                   para lo que Stock Analysis no trae.

Este ajuste rige para los scripts que generan el cache en la PC (generar_cache, actualizar_ticker).
La app publicada NO consulta Stock Analysis: solo lee el cache.

IMPORTANTE: los terminos de uso de Stock Analysis (segun una copia publicada por un sitio que los
resume) piden uso personal y manual en el navegador y no permiten scripts o scrapers, salvo
rastreadores que respeten su robots.txt. El programa respeta su robots.txt, baja una sola pagina
por empresa, con pausa entre pedidos y solo al generar el cache (una vez por trimestre). Elegir "principal"
es una decision informada del dueño de la herramienta (v1.2.13).

CADA CUANTO ACTUALIZAR EL CACHE (v1.2.15)
    Se actualiza una vez por trimestre, el dia 1 de MESES_ACTUALIZACION (marzo, junio, septiembre y
    diciembre): para esa fecha casi todas las empresas ya presentaron los resultados del trimestre, que
    es cuando cambian de verdad los balances (las medianas de 5 anios cambian una sola vez por anio).
    Lo que se mueve todos los meses es el PRECIO: con el cache de un mes de antiguedad, aprox. 1 de cada
    3 empresas queda en una categoria vecina a la de hoy; con 3 meses, aprox. 45% (estimacion hecha
    con el motor real moviendo solo los precios; el panel "Seguimiento" lo va a medir de verdad).
    DIAS_AVISO_CACHE_VIEJO: pasados estos dias la app muestra el cartel "es hora de actualizar".
"""

STOCK_ANALYSIS_MODO = "principal"

# AVISO LEGAL (v1.2.29): se muestra en una barra fija al pie de la pantalla. Se puede cambiar el texto aca;
# si se deja vacio ("") la barra no se muestra. Lo redacto el programa como texto base: conviene que lo
# revise el dueño de la herramienta (por ser asesor registrado) y lo ajuste a lo que corresponda.
AVISO_LEGAL = ("Herramienta de filtrado inicial, con fines informativos y educativos. No es una recomendación de inversión "
               "ni una oferta de compra o venta. Los datos pueden tener errores o estar desactualizados: "
               "investigá cada empresa antes de decidir.")

import datetime as _dt

MESES_ACTUALIZACION = (3, 6, 9, 12)   # se actualiza el dia 1 de estos meses (despues de la temporada de resultados)
DIAS_AVISO_CACHE_VIEJO = 100          # un trimestre (~90 dias) mas un margen


def proxima_actualizacion(hoy=None):
    """Fecha sugerida (dia 1) de la proxima actualizacion completa del cache, posterior a `hoy`."""
    hoy = hoy or _dt.date.today()
    if isinstance(hoy, _dt.datetime):
        hoy = hoy.date()
    for delta in range(0, 25):                       # busca hasta 2 anios hacia adelante
        y, m = divmod(hoy.year * 12 + (hoy.month - 1) + delta, 12)
        cand = _dt.date(y, m + 1, 1)
        if cand > hoy and cand.month in MESES_ACTUALIZACION:
            return cand
    return None


# --- Logos y vista de la tabla (v1.2.16) ---------------------------------------------------------
# "google": si no hay archivo local assets/logos/<TICKER>.png se usa el favicon de la empresa servido
#           por Google (lo carga el navegador de quien mira la app). "ninguno": solo archivos locales
#           e iniciales.
LOGOS_EN_LINEA = "google"

# Vista con la que abre la tabla principal: "clasica" o "visual".
VISTA_POR_DEFECTO = "clasica"


# --- Tipografia de la app (v1.2.33) ---------------------------------------------------------------
# "Inter": fuente pensada para pantallas y tablas de numeros (viene incluida en assets/fuentes, no se baja de internet).
# "": usa la tipografia que trae Streamlit (Source Sans).
FUENTE_APP = "Inter"

# --- Nombre de la app (v1.2.34) --------------------------------------------------------------------
NOMBRE_APP = "TodoCedears"

# --- Franja negra de arriba (v1.2.36; links cargados en la v1.2.37) ----------------------------------
# La franja lleva el nombre TodoCedears a la izquierda (la imagen assets/marca/titulo-todocedears.png; si el archivo no esta,
# se escribe el nombre en letras blancas). A la derecha van los iconos y el menu desplegable.
# Lo que quede vacio ("") no se muestra:
#   youtube / instagram : el link del canal / del perfil
#   mail                : tu mail (nombre@dominio.com) o un link
#   whatsapp            : tu numero con codigo de pais (ej. +5491112345678) o el link
#   intramed            : tu pagina institucional en Intramed (va en el menu)
#   quienes_somos       : el link que quieras abrir desde el menu (hoy vacio: no se muestra)
ENLACES_MARCA = {
    "youtube": "https://www.youtube.com/@FinanzasparaMedicosArgentina",
    "instagram": "https://www.instagram.com/finanzasparamedicos.argentina/",
    "mail": "finanzas.medicos@gmail.com",
    "whatsapp": "+5491132321659",
    "intramed": "https://www.intramed.net/institution/finanzas-para-medicos-argentina",
    "quienes_somos": "",
}

# "Abrite una cuenta con nosotros" (menu desplegable): una fila por agente. "logo" es el nombre del archivo en assets/marca/
# (si no esta, se usa el icono del sitio servido por Google cuando se indica "dominio"; si tampoco, solo el nombre).
# "detalle" es el renglon chico de abajo (identificacion del agente / alias).
CUENTAS_MARCA = [
    {"nombre": "Balanz", "url": "https://www.balanz.com/abrir-cuenta-2.aspx?reference=gdipalma@ap.balanz.com",
     "logo": "balanz.png", "dominio": "balanz.com",
     "detalle": "Ap: Guillermo Di Palma · Mat. 2372 · gdipalma@ap.balanz.com"},
    {"nombre": "Inviu", "url": "https://inviu.page.link/4Yo7",
     "logo": "inviu.png", "dominio": "",
     "detalle": "Alias: G.DIPALMA.INVIU"},
]

# En la tabla, la valoracion se muestra solo como letras de color ("moderadamente infravalorada"). True agrega, chico arriba,
# el "Podría estar" que usa la escala de arriba y la pagina de cada empresa (es el aviso de que es una estimacion).
AVISO_PODRIA_EN_TABLA = False

# --- Barra de valoracion (v1.2.34; franja y escala ajustadas en la v1.2.35) --------------------------
# Es solo dibujo: no cambia el Fair Value, el puntaje ni la categoria.
# El Fair Value va SIEMPRE en el centro de la barra; el punto del precio se mueve a su izquierda (cotiza mas barata)
# o a su derecha (mas cara).
# RANGO_FV_MARGEN: la franja celeste va del Fair Value menos X % al Fair Value mas X % (0.20 = 20 %). Es una zona
#                  de referencia, NO un intervalo de confianza: los metodos suelen discrepar bastante mas que eso.
# ESCALA_BARRA_VECES: el punto llega al borde de la barra cuando el precio vale esta cantidad de veces el Fair Value
#                  (o su inversa): con 1.8, en el borde derecho el precio es 1,8 veces el Fair Value y en el izquierdo, 1/1,8.
#                  Mas chica = franja mas ancha pero mas empresas "pegadas" al borde (hoy ~9 %); el numero de abajo (+N %) siempre es el real.
RANGO_FV_MARGEN = 0.20
ESCALA_BARRA_VECES = 1.8
