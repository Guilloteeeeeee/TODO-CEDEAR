"""Carteras de referencia por edad y perfil (v1.2.73), de las series "Cartera para inversores…" de Finanzas para Médicos Argentina (María Laura García y Guillermo Di Palma).
ES UN INSUMO INTERNO: la app NO muestra estas tablas; las usa solo para armar la devolución de "Tu cartera" (cuánto se pasa o falta cada tipo de activo).
Son guías teóricas con fines educativos, no un consejo de inversión personalizado.

Cada cartera: {"rf": renta fija (soberana + corporativa), "rv": renta variable (acciones y ETFs), "oro": .., "cripto": ..} en % de la cartera total.
Menores de 40 (una sola cartera, sin perfiles): RF soberana 15 + corporativa 15, blue chips 25, crecimiento 15, ETFs 20, cripto 5 = 95 (el grafico original suma 95; no se inventa el 5 % que falta).
Mayores de 60 (una sola cartera): RF soberana 55 + corporativa 15, blue chips 20, oro 10.
"""

PERFILES = ("Conservador", "Moderado", "Agresivo")

# (edad desde, edad hasta, nombre del rango, {perfil: cartera} o {None: cartera} si hay una sola)
RANGOS = (
    (0, 39, "menos de 40 años", {None: {"rf": 30, "rv": 60, "oro": 0, "cripto": 5}}),
    (40, 49, "40 a 49 años", {"Conservador": {"rf": 50, "rv": 40, "oro": 10, "cripto": 0},
                              "Moderado": {"rf": 35, "rv": 55, "oro": 5, "cripto": 5},
                              "Agresivo": {"rf": 20, "rv": 70, "oro": 5, "cripto": 5}}),
    (50, 59, "50 a 59 años", {"Conservador": {"rf": 50, "rv": 40, "oro": 10, "cripto": 0},
                              "Moderado": {"rf": 40, "rv": 50, "oro": 10, "cripto": 0},
                              "Agresivo": {"rf": 30, "rv": 55, "oro": 10, "cripto": 5}}),
    (60, 200, "60 años o más", {None: {"rf": 70, "rv": 20, "oro": 10, "cripto": 0}}),
)

# Estructura de la renta variable que usa Guille (se aplica a lo que el inversor tiene en empresas)
GEOGRAFIA = {"usa": 75, "desarrollados": 20, "emergentes": 5}              # Estados Unidos / desarrollados sin USA / emergentes
SUPERSECTOR = {"ciclico": 20, "sensible": 30, "defensivo": 50}             # Cíclico / Sensible / Defensivo


def referencia(edad, perfil):
    """(nombre del rango, cartera de referencia) para la edad y el perfil; None si la edad no es valida. Si el rango tiene una sola cartera, el perfil no importa."""
    try:
        e = int(edad)
    except (TypeError, ValueError):
        return None
    for d, h, nombre, carts in RANGOS:
        if d <= e <= h:
            return nombre, (carts.get(perfil) or carts.get(None) or carts["Moderado"])
    return None
