"""
Estado de la tabla en la URL (v1.2.36; criterios agregados en la v1.2.47; variables elegidas, precio y puntaje en la v1.2.49).

Al tocar una empresa de la tabla, el link lleva a su pagina (?empresa=TICKER) y es una pagina nueva: los filtros y el orden
elegidos se perderian. Para poder volver a la tabla tal como estaba, cada link lleva ademas un parametro corto "f" con lo que
estaba elegido (solo lo que se aparta de lo normal), y "Volver a la tabla" lo devuelve. Es solo comodidad: no cambia ningun
numero, y si el parametro viene roto o con valores que ya no existen, se ignora sin romper nada.
"""
import base64
import json

# Valores de arranque (lo que NO hace falta guardar)
DEFECTO = {"mc": "Sin mínimo", "ord": "market_cap", "asc": False}   # v1.2.45: orden inicial por capitalizacion bursatil (v1.2.49: ya no hay "metricas minimas")


def codificar(sectores_sel=(), sectores_todos=(), cats_sel=(), cats_todas=(), paises=(), mc="Sin mínimo",
              ord_="market_cap", asc=False, q="", industrias_sel=(), industrias_todas=(), criterios=None, variables=None, precio=None, puntaje=None) -> str:
    """Texto corto (base64 de un JSON chico) con los filtros y el orden. Sin nada elegido devuelve ''.
    Sectores, industrias y categorias se guardan por su posicion en la lista completa (mas corto que el nombre).
    `criterios`: {clave: (minimo, maximo)} de los criterios agregados (v1.2.47); un criterio sin limites tambien se guarda (suma la columna).
    `variables` (v1.2.49): claves de las variables elegidas en "Variables a ver en la tabla" (se guardan solo si no son las de siempre).
    `precio` y `puntaje` (v1.2.49): (minimo, maximo) de esos filtros; se guardan solo si hay algun limite."""
    e = {}
    s = [i for i, x in enumerate(sectores_todos) if x in set(sectores_sel)]
    if s and len(s) < len(sectores_todos):
        e["s"] = s
    n = [i for i, x in enumerate(industrias_todas) if x in set(industrias_sel)]
    if n and len(n) < len(industrias_todas):
        e["i"] = n
    v = [i for i, x in enumerate(cats_todas) if x in set(cats_sel)]
    if v and len(v) < len(cats_todas):
        e["v"] = v
    if paises:
        e["p"] = list(paises)
    if isinstance(q, str) and q.strip():                 # v1.2.46: texto del buscador
        e["q"] = q.strip()[:40]
    if criterios:
        e["c"] = {k: [mn, mx] for k, (mn, mx) in criterios.items()}
    if variables is not None and set(variables) != set(_defecto()):
        e["x"] = [str(x) for x in variables]
    for clave, lim in (("pr", precio), ("sc", puntaje)):
        if lim and any(x is not None for x in lim):
            e[clave] = [lim[0], lim[1]]
    for k, val in (("mc", mc), ("ord", ord_), ("asc", asc)):
        if val != DEFECTO[k]:
            e[k] = val
    if not e:
        return ""
    return base64.urlsafe_b64encode(json.dumps(e, separators=(",", ":"), ensure_ascii=False).encode()).decode().rstrip("=")


def _defecto():
    from ui.variables import DEFECTO as _d
    return _d


def decodificar(texto) -> dict:
    """Inverso de codificar: un dict (vacio si el texto no sirve)."""
    try:
        t = str(texto or "").strip()
        if not t or len(t) > 4000:
            return {}
        e = json.loads(base64.urlsafe_b64decode(t + "=" * (-len(t) % 4)).decode())
        return e if isinstance(e, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and x == x else None


def valores(e, sectores_todos, cats_todas, paises_ok, mc_ok, ordenes_ok, industrias_todas=(), criterios_ok=None, variables_ok=None) -> dict:
    """Pasa el dict decodificado a valores validos (solo lo que existe hoy). Devuelve las claves de session_state a fijar.
    `criterios_ok`: {clave: nombre que se ve} de los criterios que existen hoy.
    `variables_ok` (v1.2.49): claves de las variables que existen hoy; se devuelve "flt_vars" con las elegidas (siempre con Empresa)."""
    out = {}
    try:
        s = [sectores_todos[i] for i in e.get("s", []) if isinstance(i, int) and 0 <= i < len(sectores_todos)]
        if s:
            out["flt_sector"] = s
        n = [industrias_todas[i] for i in e.get("i", []) if isinstance(i, int) and 0 <= i < len(industrias_todas)]
        if n:
            out["flt_industria"] = n
        v = [cats_todas[i] for i in e.get("v", []) if isinstance(i, int) and 0 <= i < len(cats_todas)]
        if v:
            out["flt_valoracion"] = v
        p = [x for x in e.get("p", []) if x in paises_ok]
        if p:
            out["flt_pais"] = p
        if e.get("mc") in mc_ok:
            out["flt_mkt"] = e["mc"]
        if e.get("ord") in ordenes_ok:
            out["sort_col"] = e["ord"]
            out["sort_asc"] = bool(e.get("asc", False))
        if isinstance(e.get("q"), str) and e["q"].strip():
            out["flt_busqueda"] = e["q"].strip()[:40]
        elegidas = None
        x = e.get("x")
        if isinstance(x, list) and variables_ok:
            elegidas = {v for v in x if v in variables_ok}
        c = e.get("c")
        if isinstance(c, dict) and criterios_ok:
            for clave, lim in c.items():
                if clave in criterios_ok:
                    elegidas = (elegidas if elegidas is not None else set(_defecto())) | {clave}     # un criterio con limites implica verlo
                    if isinstance(lim, (list, tuple)) and len(lim) == 2:
                        out[f"crit_{clave}_min"], out[f"crit_{clave}_max"] = _num(lim[0]), _num(lim[1])
        if elegidas is not None:
            out["flt_vars"] = [v for v in (variables_ok or []) if v in elegidas or v == "nombre"]
        for clave, base in (("pr", "flt_precio"), ("sc", "flt_score")):
            lim = e.get(clave)
            if isinstance(lim, (list, tuple)) and len(lim) == 2:
                out[f"{base}_min"], out[f"{base}_max"] = _num(lim[0]), _num(lim[1])
    except Exception:  # noqa: BLE001
        return {}
    return out
