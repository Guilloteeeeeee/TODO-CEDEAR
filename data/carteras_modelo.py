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


# Objetivo y estrategia de cada rango de edad (textos de Guille, diapositivas de Finanzas para Médicos, 02/11/2026). Clave = nombre del rango (ver RANGOS).
OBJETIVOS = {
    "menos de 30 años": ("Formar hábitos financieros sólidos, potenciando el crecimiento a largo plazo priorizando activos de mayor riesgo.",
                         "Acumular capital con mayor ponderación en activos más agresivos aprovechando el amplio horizonte de inversión. Podrán correr riesgos controlados ya que, "
                         "ante reveses del mercado o decisiones erróneas, tienen más tiempo para resolver situaciones adversas."),
    "30 a 39 años": ("Mantener el crecimiento de la cartera sin perder de vista la estabilidad y la seguridad de la misma.",
                     "Acumular capital manteniendo exposición a oportunidades rentables aunque gestionando el riesgo para lograr un equilibrio justo entre activos volátiles y defensivos."),
    "40 a 49 años": ("Mantener la apreciación del capital con un ajuste progresivo hacia activos más seguros. Dado que el horizonte de inversión se está acortando, "
                     "el objetivo principal pasa por consolidar el patrimonio logrado.",
                     "Comenzar a reducir el riesgo de la cartera pero sin dejar de buscar crecimiento."),
    "50 a 59 años": ("Consolidar el capital y comenzar a reducir el riesgo, preparando una base sólida para la jubilación.",
                     "Se prioriza la preservación del capital y la generación de estabilidad financiera, mientras se mantiene una exposición moderada al crecimiento "
                     "priorizando activos que generen ingresos pasivos."),
    "60 a 69 años": ("Minimizar los riesgos preservando el patrimonio, mientras se busca estabilidad en la generación de ingresos pasivos.",
                     "Priorizar las inversiones más seguras, con énfasis en activos que generen ingresos constantes."),
    "70 años o más": ("Priorizar la estabilidad total y asegurar un flujo de ingresos constante que cubra total o parcialmente las necesidades.",
                      "Buscamos la preservación del capital, enfocándonos solo en activos que generen ingresos predecibles y reduzcan el riesgo de la cartera."),
}


# Resumen del objetivo y la estrategia de cada rango, con la redacción de Guille (modelo de 40 a 49 años escrito por él; los demás, armados a partir de sus diapositivas).
OBJETIVO_RESUMEN = {
    "menos de 30 años": "normalmente un inversor de tu edad busca formar hábitos financieros sólidos y potenciar el crecimiento de su capital a largo plazo. "
                        "La clave es aprovechar el amplio horizonte de inversión dando más peso a activos de mayor crecimiento, con riesgos controlados, ya que ante reveses del mercado hay más tiempo para recuperarse.",
    "30 a 39 años": "normalmente un inversor de tu edad y perfil de riesgo busca mantener el crecimiento de su cartera sin perder de vista la estabilidad y la seguridad. "
                    "La clave es seguir acumulando capital con exposición a oportunidades rentables, gestionando el riesgo para lograr un equilibrio justo entre activos volátiles y defensivos.",
    "40 a 49 años": "normalmente un inversor de tu edad y perfil de riesgo busca consolidar el patrimonio manteniendo apreciación del capital. "
                    "La clave es comenzar progresivamente a reducir el riesgo pero sin dejar de buscar crecimiento.",
    "50 a 59 años": "normalmente un inversor de tu edad y perfil de riesgo busca consolidar el capital y preparar una base sólida para la jubilación. "
                    "La clave es priorizar la preservación del capital y la estabilidad, manteniendo una exposición moderada al crecimiento con activos que generen ingresos pasivos.",
    "60 a 69 años": "normalmente un inversor de tu edad y perfil de riesgo busca preservar el patrimonio minimizando los riesgos, con estabilidad en la generación de ingresos pasivos. "
                    "La clave es priorizar las inversiones más seguras, con énfasis en activos que generen ingresos constantes.",
    "70 años o más": "normalmente un inversor de tu edad busca estabilidad y un flujo de ingresos constante que cubra total o parcialmente sus necesidades. "
                     "La clave es preservar el capital, enfocándose en activos que generen ingresos predecibles y reduzcan el riesgo de la cartera.",
}
