"""Carteras de referencia por edad y perfil (v1.2.73), de las series "Cartera para inversores…" de Finanzas para Médicos Argentina (María Laura García y Guillermo Di Palma).
ES UN INSUMO INTERNO: la app NO muestra estas tablas; las usa solo para armar la devolución de "Tu cartera" (cuánto se pasa o falta cada tipo de activo).
Son guías teóricas con fines educativos, no un consejo de inversión personalizado.

Cada cartera: {"rf": renta fija (soberana + corporativa), "rv": renta variable (acciones y ETFs), "oro": .., "cripto": ..} en % de la cartera total.
v1.2.74: rangos 30-39, 60-69 y 70+ cargados con las tablas que paso Guille. Cada rango con perfiles suma 100. "efectivo" solo existe en 70+ (cuentas remuneradas y cauciones);
en los demas rangos el efectivo de la persona se cuenta junto con la renta fija.
"""

PERFILES = ("Conservador", "Moderado", "Agresivo")

# (edad desde, edad hasta, nombre del rango, {perfil: cartera} o {None: cartera} si hay una sola). Todo en % de la cartera total.
RANGOS = (
    # Menores de 30: una sola cartera (la del PDF de 21 a 29: crecimiento 50, blue chips 20, ETFs 20, cripto 10). Pendiente: confirmar si tiene perfiles.
    (0, 29, "menos de 30 años", {None: {"rf": 0, "rv": 90, "oro": 0, "cripto": 10}}),
    (30, 39, "30 a 39 años", {"Conservador": {"rf": 40, "rv": 55, "oro": 0, "cripto": 5},
                              "Moderado": {"rf": 30, "rv": 65, "oro": 0, "cripto": 5},
                              "Agresivo": {"rf": 10, "rv": 80, "oro": 0, "cripto": 10}}),
    (40, 49, "40 a 49 años", {"Conservador": {"rf": 50, "rv": 40, "oro": 10, "cripto": 0},
                              "Moderado": {"rf": 35, "rv": 55, "oro": 5, "cripto": 5},
                              "Agresivo": {"rf": 20, "rv": 70, "oro": 5, "cripto": 5}}),
    (50, 59, "50 a 59 años", {"Conservador": {"rf": 50, "rv": 40, "oro": 10, "cripto": 0},
                              "Moderado": {"rf": 40, "rv": 50, "oro": 10, "cripto": 0},
                              "Agresivo": {"rf": 30, "rv": 55, "oro": 10, "cripto": 5}}),
    (60, 69, "60 a 69 años", {"Conservador": {"rf": 70, "rv": 20, "oro": 10, "cripto": 0},
                              "Moderado": {"rf": 60, "rv": 30, "oro": 10, "cripto": 0},
                              "Agresivo": {"rf": 50, "rv": 35, "oro": 10, "cripto": 5}}),
    # 70 o mas: una sola cartera; la mitad en cuentas remuneradas y cauciones (efectivo y liquidez)
    (70, 200, "70 años o más", {None: {"rf": 40, "rv": 0, "oro": 10, "cripto": 0, "efectivo": 50}}),
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
