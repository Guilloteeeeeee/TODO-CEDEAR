"""
Ajustes del CEDEAR Screener que se pueden cambiar sin tocar el resto del codigo.

STOCK_ANALYSIS_MODO
    "apagado"   -> no se consulta Stock Analysis (solo Yahoo Finance).
    "respaldo"  -> (v1.2.11, por defecto) Yahoo es la fuente principal; Stock Analysis se consulta
                   solo para completar medianas que Yahoo dejo vacias.
    "principal" -> (v1.2.12) Stock Analysis es la fuente principal: valor actual y mediana de los
                   ultimos 5 anios fiscales salen de la MISMA pagina; Yahoo queda como respaldo
                   para lo que Stock Analysis no trae.

IMPORTANTE: los terminos de uso de Stock Analysis (segun una copia publicada por un sitio que los
resume) piden uso personal y manual en el navegador y no permiten scripts o scrapers, salvo
rastreadores que respeten su robots.txt. Cambiar a "principal" aumenta ese uso: es una decision
del dueño de la herramienta.
"""

STOCK_ANALYSIS_MODO = "respaldo"
