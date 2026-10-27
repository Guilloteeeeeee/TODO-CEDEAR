"""Análisis técnico (v1.2.68): indicadores calculados SOLO con los cierres diarios que ya baja la app de Yahoo (los mismos del gráfico).

Es información, no una señal: no hay puntaje, ni "comprar" / "vender", ni nada que entre al Score. Si no alcanzan los datos (por ejemplo, menos de 200 cierres para el
promedio de 200 ruedas), se muestra "—": nunca se inventa un número. Las funciones de cálculo no tocan la red y se prueban solas.

Indicadores: rango y promedio de 52 semanas, distancia al máximo y al mínimo, promedios móviles de 50 y 200 ruedas (y su último cruce), RSI de 14 ruedas,
MACD (12, 26, 9), volatilidad anual y caída máxima (1 y 5 años). Los rendimientos por plazo los muestra la tabla "Rendimiento" que ya existe arriba."""
import datetime as _dt
import html
import math

VERDE, ROJO = "#15803d", "#b91c1c"


# --- cálculo ----------------------------------------------------------------------------------------------------------------

def sma(cierres, n):
    """Promedio simple de los últimos n cierres; None si hay menos de n."""
    if not cierres or len(cierres) < n:
        return None
    return sum(cierres[-n:]) / n


def _ema_serie(valores, n):
    k = 2.0 / (n + 1)
    out, e = [], None
    for v in valores:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(cierres, n=14):
    """RSI de Wilder (0 a 100) con los últimos cierres; None si hay menos de n + 1 cierres."""
    if not cierres or len(cierres) < n + 1:
        return None
    difs = [b - a for a, b in zip(cierres, cierres[1:])]
    gan = sum(max(d, 0.0) for d in difs[:n]) / n
    per = sum(max(-d, 0.0) for d in difs[:n]) / n
    for d in difs[n:]:
        gan = (gan * (n - 1) + max(d, 0.0)) / n
        per = (per * (n - 1) + max(-d, 0.0)) / n
    if per == 0:
        return 100.0 if gan > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + gan / per)


def macd(cierres, rapida=12, lenta=26, senal=9):
    """(macd, señal, histograma) del último cierre; None si hay menos de lenta + señal cierres."""
    if not cierres or len(cierres) < lenta + senal:
        return None
    m = [a - b for a, b in zip(_ema_serie(cierres, rapida), _ema_serie(cierres, lenta))]
    s = _ema_serie(m[lenta - 1:], senal)
    return m[-1], s[-1], m[-1] - s[-1]


def ultimo_cruce(pares, corta=50, larga=200, ventana=1100):
    """(fecha, 'dorada' | 'muerte') del último cruce entre el promedio de `corta` y el de `larga` ruedas dentro de las últimas `ventana` ruedas; None si
    no hubo (o si no alcanzan los datos). 'dorada': el de 50 pasó a estar por encima del de 200; 'muerte': al revés."""
    if not pares or len(pares) < larga + 1:
        return None
    c = [x for _, x in pares]
    acum = [0.0]
    for x in c:
        acum.append(acum[-1] + x)
    ini = max(larga - 1, len(c) - ventana)
    signo_ant, res = None, None
    for i in range(ini, len(c)):
        dif = (acum[i + 1] - acum[i + 1 - corta]) / corta - (acum[i + 1] - acum[i + 1 - larga]) / larga
        signo = 1 if dif > 0 else -1 if dif < 0 else signo_ant
        if signo_ant is not None and signo is not None and signo != signo_ant:
            res = (pares[i][0], "dorada" if signo > 0 else "muerte")
        signo_ant = signo if signo is not None else signo_ant
    return res


def volatilidad(cierres, ruedas=252):
    """Desvío estándar de los retornos diarios de las últimas `ruedas` ruedas, anualizado (fracción: 0.3 = 30 %); None si hay menos de 60 retornos."""
    if not cierres or len(cierres) < 61:
        return None
    c = cierres[-(ruedas + 1):]
    r = [math.log(b / a) for a, b in zip(c, c[1:]) if a > 0 and b > 0]
    if len(r) < 60:
        return None
    m = sum(r) / len(r)
    var = sum((x - m) ** 2 for x in r) / (len(r) - 1)
    return math.sqrt(var) * math.sqrt(252)


def caida_maxima(pares, anios):
    """Peor caída (fracción negativa: -0.35 = -35 %) de un pico a un piso posterior dentro de los últimos `anios` años; None si la historia es más corta
    que el período."""
    if not pares:
        return None
    uf = pares[-1][0]
    lim = uf - _dt.timedelta(days=int(365.25 * anios))
    if pares[0][0] > lim + _dt.timedelta(days=10):
        return None
    pico, peor = 0.0, 0.0
    for f, c in pares:
        if f < lim:
            continue
        pico = max(pico, c)
        if pico > 0:
            peor = min(peor, c / pico - 1.0)
    return peor


def rango_52s(pares):
    """(mínimo, máximo, promedio) de los cierres de los últimos 12 meses; None si no hay al menos 20 cierres en ese período."""
    if not pares:
        return None
    lim = pares[-1][0] - _dt.timedelta(days=365)
    c = [x for f, x in pares if f > lim]
    if len(c) < 20:
        return None
    return min(c), max(c), sum(c) / len(c)


def indicadores(pares):
    """Todos los indicadores juntos (cada uno es None si faltan datos). `pares`: [(fecha, cierre)] ordenados."""
    if not pares or len(pares) < 2:
        return {}
    c = [x for _, x in pares]
    precio = c[-1]
    out = {"precio": precio, "fecha": pares[-1][0], "rango": rango_52s(pares), "sma50": sma(c, 50), "sma200": sma(c, 200), "rsi": rsi(c),
           "macd": macd(c), "cruce": ultimo_cruce(pares), "vol": volatilidad(c), "dd1": caida_maxima(pares, 1), "dd5": caida_maxima(pares, 5)}
    return out


# --- pantalla -----------------------------------------------------------------------------------------------------------------

def _money(v):
    return f"US&#36;&nbsp;{v:,.2f}" if v >= 0.1 else f"US&#36;&nbsp;{v:,.4f}"


def _color(v, txt):
    c = VERDE if v > 0 else ROJO if v < 0 else "inherit"
    return f'<span style="color:{c};font-weight:600">{txt}</span>'


def _pct(v, signo=True):
    return f"{v * 100:+.1f}%" if signo else f"{v * 100:.1f}%"


def _fila(k, v, tip):
    from ui import ficha as F
    return F._fila_kv(k, v, tip)


def _vs(precio, prom):
    """'US$ 123,45 · el precio está +4,2% arriba' para un promedio móvil."""
    if prom is None:
        return "—"
    dif = precio / prom - 1.0
    return f"{_money(prom)} · precio {_color(dif, _pct(dif))}"


def tile_rango(ind):
    from ui import ficha as F
    from ui.tabla_visual import barra_52s_html
    r = ind.get("rango")
    if not r:
        return F._tile("s6", "Rango de 52 semanas", '<div class="fch-sub" style="margin:0">Sin datos suficientes.</div>', ac="#0ea5e9")
    lo, hi, med = r
    p = ind["precio"]
    barra = barra_52s_html({"precio_min_52s": lo, "precio_max_52s": hi, "precio_actual": p}, grande=True)
    desde_max = p / hi - 1.0 if hi else None
    desde_min = p / lo - 1.0 if lo else None
    filas = [_fila("Distancia al máximo", _color(desde_max, _pct(desde_max)) if desde_max is not None else "—",
                   "Cuánto está el precio por debajo del máximo de las últimas 52 semanas. Ej.: máximo US$ 100, hoy US$ 85 → -15,0 %."),
             _fila("Distancia al mínimo", _color(desde_min, _pct(desde_min)) if desde_min is not None else "—",
                   "Cuánto está el precio por encima del mínimo de las últimas 52 semanas. Ej.: mínimo US$ 70, hoy US$ 85 → +21,4 %."),
             _fila("Promedio de 52 semanas", _money(med),
                   "Promedio de todos los cierres del último año. Si el precio de hoy está por encima, el último año cotizó en promedio más barato que hoy."),
             _fila("Hoy vs promedio", _color(p / med - 1.0, _pct(p / med - 1.0)), "Diferencia entre el precio de hoy y ese promedio.")]
    cuerpo = barra + '<div class="fch-kv" style="margin-top:8px">' + "".join(filas) + "</div>"
    return F._tile("s6", "Rango de 52 semanas", cuerpo + '<div class="fch-sub" style="margin:6px 0 0">Calculado con los cierres diarios.</div>', ac="#0ea5e9")


def tile_promedios(ind):
    from ui import ficha as F
    p = ind["precio"]
    s50, s200 = ind.get("sma50"), ind.get("sma200")
    filas = [_fila("Promedio de 50 ruedas", _vs(p, s50),
                   "Promedio de los últimos 50 cierres (unos 2 meses y medio). Ej.: si promedió US$ 100 y hoy cotiza a US$ 110, el precio está +10 % por encima: viene subiendo en el corto plazo."),
             _fila("Promedio de 200 ruedas", _vs(p, s200),
                   "Promedio de los últimos 200 cierres (casi 10 meses): muestra la tendencia de fondo. Cuanto más arriba esté el precio, más fuerte viene el último tramo.")]
    if s50 is not None and s200 is not None:
        rel = "por encima" if s50 > s200 else "por debajo" if s50 < s200 else "igual"
        filas.append(_fila("Promedio de 50 vs 200", f"El de 50 está {rel} del de 200",
                           "Cuando el de 50 está por encima del de 200, el último tramo viene más fuerte que la tendencia de fondo; por debajo, más débil."))
    cr = ind.get("cruce")
    if cr:
        f, t = cr
        nombre = "Cruz dorada" if t == "dorada" else "Cruz de la muerte"
        filas.append(_fila("Último cruce", f"{nombre} · {f.strftime('%d/%m/%Y')}",
                           "Se llama cruz dorada cuando el promedio de 50 pasa por encima del de 200, y cruz de la muerte cuando pasa por debajo. "
                           "Describe lo que ya pasó; no predice nada."))
    elif s50 is not None and s200 is not None:
        filas.append(_fila("Último cruce", "Ninguno en los últimos 4 años", "No hubo cambio de posición entre los dos promedios en ese período."))
    return F._tile("s6", "Promedios móviles", '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>", ac="#8b5cf6")


def tile_impulso(ind):
    from ui import ficha as F
    r = ind.get("rsi")
    if r is None:
        txt = "—"
    else:
        zona = "sobrecomprado (más de 70)" if r > 70 else "sobrevendido (menos de 30)" if r < 30 else "zona neutral (30 a 70)"
        txt = f"{r:.0f} · {zona}"
    filas = [_fila("RSI de 14 ruedas", txt,
                   "Mide de 0 a 100 cuánto pesaron las subas frente a las bajas de las últimas 14 ruedas. Por convención, más de 70 se llama 'sobrecomprado' (subió mucho y rápido) "
                   "y menos de 30 'sobrevendido'. Ej.: un RSI de 75 indica que las subas de las últimas semanas pesaron mucho más que las bajas. No es una señal de compra ni de venta.")]
    m = ind.get("macd")
    if m:
        mac, sen, hist = m
        estado = "por encima de su señal: el impulso viene mejorando" if hist > 0 else "por debajo de su señal: el impulso viene flojeando" if hist < 0 else "igual a su señal"
        filas.append(_fila("MACD (12, 26, 9)", f'{_color(mac, f"{mac:+.2f}")} · {estado}',
                           "Es la diferencia entre un promedio rápido (12 ruedas) y uno lento (26 ruedas) del precio. Positivo: el precio reciente está por encima del promedio lento. "
                           "La 'señal' es el promedio de 9 ruedas del propio MACD: si el MACD está por encima, el impulso viene mejorando."))
        filas.append(_fila("Señal / histograma", f"{sen:+.2f} / {_color(hist, f'{hist:+.2f}')}", "Histograma = MACD menos su señal."))
    else:
        filas.append(_fila("MACD (12, 26, 9)", "—", "Faltan datos."))
    return F._tile("s6", "Impulso", '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>", ac="#f59e0b")


def tile_riesgo(ind):
    from ui import ficha as F
    v = ind.get("vol")
    filas = [_fila("Volatilidad anual", _pct(v, signo=False) if v is not None else "—",
                   "Cuánto suele moverse el precio en un año (desvío estándar de los retornos diarios, anualizado). Ej.: 30 % significa que un año típico puede traer movimientos de unos 30 % "
                   "hacia arriba o hacia abajo. Cuanto mayor, más sube y baja."),
             _fila("Caída máxima en 1 año", _color(ind["dd1"], _pct(ind["dd1"])) if ind.get("dd1") is not None else "—",
                   "La peor caída desde un pico hasta el piso siguiente dentro del último año. Ej.: -35 % quiere decir que quien compró justo en el pico llegó a perder el 35 %."),
             _fila("Caída máxima en 5 años", _color(ind["dd5"], _pct(ind["dd5"])) if ind.get("dd5") is not None else "—",
                   "Lo mismo, mirando los últimos 5 años (sólo si el activo tiene esa historia).")]
    return F._tile("s6", "Riesgo", '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>", ac="#ef4444")


def tab_tecnico_html(pares):
    """Los cuatro mosaicos del análisis técnico. '' si no hay historial (la solapa ya avisa que Yahoo no respondió)."""
    from ui import ficha as F
    ind = indicadores(pares)
    if not ind:
        return ""
    nota = ('<div class="fch-sub" style="margin:8px 0 0">Información calculada con los cierres diarios de Yahoo Finance (no es en tiempo real). '
            'Son descripciones de lo que pasó con el precio, no una señal de compra ni de venta ni una predicción.</div>')
    return F._env(tile_rango(ind), tile_promedios(ind), tile_impulso(ind), tile_riesgo(ind)) + nota
