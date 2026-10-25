"""
Historial de precios de una empresa (v1.2.52): cambios del dia, la semana, el mes y el año, y la serie para el grafico basico de 10 años.

Sale de Yahoo Finance (yfinance), pedido en el momento al abrir la pagina de la empresa (la app lo guarda en memoria un rato). NO es en tiempo real:
son cierres diarios (el ultimo es el del dia habil mas reciente o el precio de hoy, segun Yahoo). Si Yahoo no responde, devuelve None y la pagina
muestra "no disponible": nunca se inventa un numero. Las funciones de calculo (cambios, reducir) no tocan la red y se prueban solas.
"""
import datetime as _dt
import threading

# Cuantos dias hacia atras es cada cambio (se toma el ultimo cierre disponible en esa fecha o antes)
VENTANAS = (("Día", 1), ("Semana", 7), ("Mes", 30), ("Año", 365))
# v1.2.52: marcos de tiempo de la solapa "Gráfico y rendimiento". Dias de calendario hacia atras ("YTD" = desde el 1 de enero, "MAX" = toda la historia).
MARCOS = ("1D", "5D", "1M", "3M", "YTD", "1A", "5A", "MAX")
_DIAS_MARCO = {"1M": 30, "3M": 91, "1A": 365, "5A": 5 * 365}


def _ok(v):
    try:
        v = float(v)
        return v if v == v and v > 0 and v != float("inf") else None
    except (TypeError, ValueError):
        return None


def limpiar(fechas, cierres):
    """Pares (fecha, cierre) validos, ordenados por fecha, sin repetidos. `fechas` son datetime.date."""
    pares = {}
    for f, c in zip(fechas or [], cierres or []):
        c = _ok(c)
        if c is not None and isinstance(f, _dt.date):
            pares[f] = c
    return sorted(pares.items())


def cambios(pares, ventanas=VENTANAS):
    """[(nombre, variacion o None)] del ultimo cierre contra el de hace N dias. "Día" es contra el cierre anterior. Si no hay un cierre de esa
    fecha o antes (historia mas corta que la ventana), queda None."""
    if not pares or len(pares) < 2:
        return [(n, None) for n, _ in ventanas]
    ult_f, ult_c = pares[-1]
    res = []
    for nombre, dias in ventanas:
        if dias == 1:
            base = pares[-2][1]
        else:
            lim = ult_f - _dt.timedelta(days=dias)
            if pares[0][0] > lim:
                res.append((nombre, None))
                continue
            base = None
            for f, c in reversed(pares):
                if f <= lim:
                    base = c
                    break
        res.append((nombre, (ult_c / base - 1.0) if base else None))
    return res


def reducir(pares, max_puntos=260):
    """Deja a lo sumo `max_puntos` puntos repartidos parejo (siempre incluye el primero y el ultimo), para que el dibujo sea liviano."""
    n = len(pares)
    if n <= max_puntos:
        return list(pares)
    paso = (n - 1) / (max_puntos - 1)
    idx = sorted({int(round(i * paso)) for i in range(max_puntos)} | {0, n - 1})
    return [pares[i] for i in idx]


def bajar(ticker, timeout=12.0, obtener=None):
    """Lista de pares (date, cierre) de toda la historia disponible (diario), o None si Yahoo no respondio. Con tope de tiempo; nunca levanta excepciones.
    `obtener(ticker)` -> (fechas, cierres) es para las pruebas."""
    res = {}

    def _pedir():
        try:
            if obtener is not None:
                res["v"] = obtener(ticker)
                return
            import yfinance as yf
            h = yf.Ticker(str(ticker)).history(period="max", interval="1d", auto_adjust=False)
            if h is None or h.empty or "Close" not in h:
                res["v"] = None
                return
            fechas = [i.date() if hasattr(i, "date") else i for i in h.index]
            res["v"] = (fechas, list(h["Close"]))
        except Exception:  # noqa: BLE001
            res["v"] = None

    hilo = threading.Thread(target=_pedir, daemon=True)
    hilo.start()
    hilo.join(timeout)
    v = res.get("v")
    if not v:
        return None
    pares = limpiar(*v)
    return pares if len(pares) >= 2 else None


def rendimientos(pares):
    """[(marco, variacion o None)] para 1D, 5D, 1M, 3M, YTD, 1A, 5A y MAX, del ultimo cierre contra el de esa fecha (o el primero anterior). 1D es contra el
    cierre anterior y 5D contra el de hace 5 ruedas. Si la historia no llega hasta esa fecha, None (nunca se inventa)."""
    if not pares or len(pares) < 2:
        return [(m, None) for m in MARCOS]
    uf, uc = pares[-1]
    res = []
    for m in MARCOS:
        base = None
        if m == "1D":
            base = pares[-2][1]
        elif m == "5D":
            base = pares[-6][1] if len(pares) >= 6 else None
        elif m == "MAX":
            base = pares[0][1]
        else:
            lim = _dt.date(uf.year - 1, 12, 31) if m == "YTD" else uf - _dt.timedelta(days=_DIAS_MARCO[m])
            if pares[0][0] <= lim:
                base = next((c for f, c in reversed(pares) if f <= lim), None)
        res.append((m, (uc / base - 1.0) if base else None))
    return res


def recortar(pares, marco):
    """Los pares de `pares` que entran en el marco (para 1M, 3M, YTD, 1A, 5A y MAX; 1D y 5D salen de datos intradia, ver data/yahoo_extra.py)."""
    if not pares:
        return []
    if marco == "MAX":
        return list(pares)
    uf = pares[-1][0]
    lim = _dt.date(uf.year - 1, 12, 31) if marco == "YTD" else uf - _dt.timedelta(days=_DIAS_MARCO.get(marco, 365))
    return [p for p in pares if p[0] >= lim]
