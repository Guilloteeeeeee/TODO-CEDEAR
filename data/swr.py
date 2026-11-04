"""
Datos "de la heladera" (v1.5.22): devuelve al instante lo ultimo que se bajo y, si ya pasó el tiempo, lo renueva en segundo plano.

Por qué: los precios de hoy se bajan de Yahoo (con Stock Analysis de respaldo) y se guardaban con st.cache_data durante 5 minutos. Cada vez que
vencían, la PRIMERA persona que entraba esperaba toda la bajada (215 empresas: de 5 a 20 segundos, y hasta 85 si Yahoo no respondía). Ahora esa persona
ve la página de inmediato con los últimos precios guardados, y la bajada nueva se hace aparte (la usa la visita siguiente). Solo la primera vez
después de prender la app se espera (hasta `esperar` segundos; si no alcanza, la página sale con los precios del cache y no se queda trabada).
Igual que ui/mercados.py con la barra de dólares y bolsas. No toca ningún cálculo: solo cuándo se baja el dato.
"""
import threading
import time

_LOCK = threading.Lock()
_EST = {}      # clave -> {"t": cuando se guardó, "res": último resultado, "hilo": hilo de renovación}


def _renovar(clave, fn, ttl, valido):
    try:
        res = fn()
    except Exception:  # noqa: BLE001
        res = None
    bueno = False
    try:
        bueno = res is not None and (valido is None or bool(valido(res)))
    except Exception:  # noqa: BLE001
        bueno = False
    with _LOCK:
        reg = _EST[clave]
        if bueno:
            reg["res"], reg["t"] = res, time.time()
        else:
            reg["t"] = time.time() - ttl + 60      # no llegó nada útil: se reintenta en un minuto y mientras tanto se sigue mostrando lo anterior


def obtener(clave, fn, ttl, esperar=15.0, max_viejo=7200.0, valido=None, vacio=None):
    """Resultado de `fn()` guardado `ttl` segundos. Con un resultado guardado lo devuelve ya (si venció, arranca una renovación en segundo plano).
    Sin ninguno (primera vez), espera hasta `esperar` segundos y, si no llegó, devuelve `vacio`. Un resultado de más de `max_viejo` segundos
    también espera a la renovación (hasta `esperar`), pero si no llega devuelve igual el que había. `valido(res)` decide si lo bajado sirve
    (por ejemplo, que tenga precios): si no sirve, no pisa al anterior."""
    with _LOCK:
        reg = _EST.setdefault(clave, {"t": 0.0, "res": None, "hilo": None})
        ahora = time.time()
        h = reg["hilo"]
        if ahora - reg["t"] > ttl and not (h and h.is_alive()):
            h = threading.Thread(target=_renovar, args=(clave, fn, ttl, valido), daemon=True)
            reg["hilo"] = h
            h.start()
        res = reg["res"]
        muy_viejo = res is not None and ahora - reg["t"] > max_viejo
    if (res is None or muy_viejo) and h is not None:
        h.join(esperar)
        with _LOCK:
            res = reg["res"] if reg["res"] is not None else res
    return res if res is not None else vacio


def olvidar(clave=None):
    """Borra lo guardado (para las pruebas, o si hace falta forzar una bajada nueva)."""
    with _LOCK:
        if clave is None:
            _EST.clear()
        else:
            _EST.pop(clave, None)
