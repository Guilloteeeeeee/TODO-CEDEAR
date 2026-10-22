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


# --- Franja del Fair Value en la barra de valoracion (v1.2.24) -------------------------------------
# Es solo dibujo: no cambia el Fair Value, el puntaje ni la categoria.
# "margen": la franja va del Fair Value promedio menos X% al promedio mas X% (FRANJA_FV_MARGEN).
# "promedio_metodos": desde el promedio de los metodos que dan menos que el Fair Value hasta el
#                     promedio de los que dan mas (si hay un solo metodo, no hay franja).
FRANJA_FV_MODO = "margen"
FRANJA_FV_MARGEN = 0.15
