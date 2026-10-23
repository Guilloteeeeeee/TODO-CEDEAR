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

# AVISO LEGAL (v1.2.29; desde la v1.2.41 va al final de la pagina, en el pie, y no en una barra fija). Se puede cambiar el texto aca;
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

# --- Franja negra de arriba (v1.2.36; links cargados en la v1.2.37; menu rehecho en la v1.2.38) --------------------
# La franja lleva el nombre TodoCedears a la izquierda (la imagen assets/marca/titulo-todocedears.png; si el archivo no esta,
# se escribe el nombre en letras blancas). A la derecha van los iconos, "Quiénes somos", "Abrite una cuenta con nosotros"
# (desplegable) y "Comentarios". Lo que quede vacio ("") no se muestra, salvo "Quiénes somos", que se muestra siempre (sin
# link queda como texto, sin hacer nada al tocarlo, hasta que se cargue el link).
#   youtube / instagram : el link del canal / del perfil
#   mail                : el mail de contacto (nombre@dominio.com) o un link
#   whatsapp            : el link de invitacion al WhatsApp de la COMUNIDAD (https://chat.whatsapp.com/...) o un numero
#                         con codigo de pais. Vacio: no se muestra el icono.
#   intramed            : tu pagina institucional en Intramed (el icono es assets/marca/intramed.png)
#   quienes_somos       : el link que quieras abrir (hoy vacio)
#   comentarios         : si lo dejas vacio (hoy), "Comentarios" despliega un cuadro para escribir cuyo mensaje te llega por mail
#                         (ver COMENTARIOS_MAIL mas abajo). Si pones un link (ej. un Google Forms), se usa ese link y no el cuadro.
ENLACES_MARCA = {
    "youtube": "https://www.youtube.com/@FinanzasparaMedicosArgentina",
    "instagram": "https://www.instagram.com/finanzasparamedicos.argentina/",
    "mail": "finanzas.medicos@gmail.com",
    "whatsapp": "",
    "intramed": "https://www.intramed.net/institution/finanzas-para-medicos-argentina",
    "quienes_somos": "",
    "comentarios": "",
}

# "Comentarios" (v1.2.40): el cuadro de la franja manda el mensaje por mail a esta casilla, a traves del servicio gratuito
# FormSubmit (formsubmit.co), sin servidor ni claves propias. La PRIMERA vez que alguien envie algo, FormSubmit te manda un mail
# de activacion: hay que abrirlo y confirmar (los mensajes enviados antes de confirmar se guardan y llegan al activar).
# Vacio ("") = no se muestra el cuadro. El mensaje pasa por los servidores de FormSubmit (el cuadro lo avisa).
COMENTARIOS_MAIL = "finanzas.medicos@gmail.com"

# "Abrite una cuenta con nosotros" (desplegable): una fila por agente. El logo es un archivo de assets/marca/ ("logo") y al
# tocarlo abre el link de apertura de cuenta ("url"). "detalle" es un renglon chico opcional debajo del logo (desde la v1.2.39
# va vacio: el desplegable muestra solo los logos). Datos de referencia, por si se quieren volver a mostrar:
#   Balanz -> Ap: Guillermo Di Palma · Mat. 2372 · gdipalma@ap.balanz.com
#   Inviu  -> Alias: G.DIPALMA.INVIU
# Si falta el archivo del logo, se usa el icono del sitio servido por Google cuando se indica "dominio"; si no, el nombre.
CUENTAS_MARCA = [
    {"nombre": "Balanz", "url": "https://www.balanz.com/abrir-cuenta-2.aspx?reference=gdipalma@ap.balanz.com",
     "logo": "balanz.png", "dominio": "balanz.com", "detalle": ""},
    {"nombre": "Inviu", "url": "https://inviu.page.link/4Yo7",
     "logo": "inviu.png", "dominio": "", "detalle": ""},
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

# --- Noticias Calientes (v1.2.39; CNBC en la v1.2.40; titulares en español desde la v1.2.41) ----------------
# Titulares con solo titulo + fuente + link. Orden: primero los que nombran empresas del screener, despues los de la
# portada, y a igualdad el mas reciente. Ver ui/noticias.py.
# NOTICIAS_IDIOMA elige que fuente se usa:
#   "es" = Ambito (titulares en español; mucha economia y mercados argentinos, poca tecnologia de Estados Unidos).
#   "en" = CNBC (titulares en ingles; cubre mejor las empresas de Estados Unidos). Los articulos "CNBC Pro" (de pago) se sacan.
# Bloomberg se descarto porque sus notas son de pago.
NOTICIAS_ACTIVAS = True          # False = no se muestra ni se descarga nada
NOTICIAS_IDIOMA = "es"           # "es" (Ambito) o "en" (CNBC)
NOTICIAS_CANTIDAD = 5            # cuantos titulares
NOTICIAS_HORAS = 24              # ventana de tiempo; si hay menos de NOTICIAS_CANTIDAD se amplia a 48 y 72 h (NOTICIAS_HORAS_MAX)
NOTICIAS_HORAS_MAX = 72
NOTICIAS_MINUTOS_CACHE = 15      # cada cuanto se vuelve a bajar (todos los visitantes comparten la descarga)
NOTICIAS_ABIERTO = False         # True = el recuadro aparece desplegado; False = cerrado (se abre con un toque)
# Traduccion automatica (v1.2.42): con NOTICIAS_IDIOMA = "en", True traduce al español los titulares de CNBC con el servicio
# gratuito MyMemory. Es traduccion automatica (puede tener errores); si falla, el titular queda en ingles. Con "es" no hace nada.
NOTICIAS_TRADUCIR = False
NOTICIAS_TRADUCIR_MAIL = ""      # opcional: mail para subir la cuota gratuita de MyMemory de 5.000 a 50.000 caracteres por dia (vacio = COMENTARIOS_MAIL)
# Por idioma: nombre de la fuente y sus feeds (nombre que se muestra, url del RSS, es_portada). La "portada" solo marca
# cuales notas estan ahi; no se muestra por separado.
NOTICIAS_FUENTES = {
    "es": {"fuente": "Ámbito", "feeds": (
        ("Finanzas", "https://www.ambito.com/rss/pages/finanzas.xml", False),
        ("Economía", "https://www.ambito.com/rss/pages/economia.xml", False),
        ("Portada", "https://www.ambito.com/rss/home.xml", True),
    )},
    "en": {"fuente": "CNBC", "feeds": (
        ("Mercados", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20409666", False),
        ("Tecnología", "https://www.cnbc.com/id/19854910/device/rss/rss.html", False),
        ("Economía", "https://www.cnbc.com/id/20910258/device/rss/rss.html", False),
        ("Portada", "https://www.cnbc.com/id/100003114/device/rss/rss.html", True),
    )},
}
