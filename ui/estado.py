"""
Estado de la tabla en la URL (v1.2.36).

Al tocar una empresa de la tabla, el link lleva a su pagina (?empresa=TICKER) y es una pagina nueva: los filtros y el orden
elegidos se perderian. Para poder volver a la tabla tal como estaba, cada link lleva ademas un parametro corto "f" con lo que
estaba elegido (solo lo que se aparta de lo normal), y "Volver a la tabla" lo devuelve. Es solo comodidad: no cambia ningun
numero, y si el parametro viene roto o con valores que ya no existen, se ignora sin romper nada.
"""
import base64
import json

# Valores de arranque (lo que NO hace falta guardar)
DEFECTO = {"mc": "Sin mínimo", "dy": 0.0, "met": 1, "ord": "fv_upside", "asc": False, "rev": False}


def codificar(sectores_sel=(), sectores_todos=(), cats_sel=(), cats_todas=(), paises=(), mc="Sin mínimo", dy=0.0, met=1,
              ord_="fv_upside", asc=False, rev=False) -> str:
    """Texto corto (base64 de un JSON chico) con los filtros y el orden. Sin nada elegido devuelve ''.
    Sectores y categorias se guardan por su posicion en la lista completa (mas corto que el nombre)."""
    e = {}
    s = [i for i, x in enumerate(sectores_todos) if x in set(sectores_sel)]
    if s and len(s) < len(sectores_todos):
        e["s"] = s
    v = [i for i, x in enumerate(cats_todas) if x in set(cats_sel)]
    if v and len(v) < len(cats_todas):
        e["v"] = v
    if paises:
        e["p"] = list(paises)
    for k, val in (("mc", mc), ("dy", dy), ("met", met), ("ord", ord_), ("asc", asc), ("rev", rev)):
        if val != DEFECTO[k]:
            e[k] = val
    if not e:
        return ""
    return base64.urlsafe_b64encode(json.dumps(e, separators=(",", ":"), ensure_ascii=False).encode()).decode().rstrip("=")


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


def valores(e, sectores_todos, cats_todas, paises_ok, mc_ok, ordenes_ok) -> dict:
    """Pasa el dict decodificado a valores validos (solo lo que existe hoy). Devuelve las claves de session_state a fijar."""
    out = {}
    try:
        s = [sectores_todos[i] for i in e.get("s", []) if isinstance(i, int) and 0 <= i < len(sectores_todos)]
        if s:
            out["flt_sector"] = s
        v = [cats_todas[i] for i in e.get("v", []) if isinstance(i, int) and 0 <= i < len(cats_todas)]
        if v:
            out["flt_valoracion"] = v
        p = [x for x in e.get("p", []) if x in paises_ok]
        if p:
            out["flt_pais"] = p
        if e.get("mc") in mc_ok:
            out["flt_mkt"] = e["mc"]
        if isinstance(e.get("dy"), (int, float)) and not isinstance(e.get("dy"), bool):
            out["flt_dy"] = float(min(10.0, max(0.0, e["dy"])))
        if isinstance(e.get("met"), int) and not isinstance(e.get("met"), bool):
            out["flt_met"] = int(min(4, max(1, e["met"])))
        if e.get("ord") in ordenes_ok:
            out["sort_col"] = e["ord"]
            out["sort_asc"] = bool(e.get("asc", False))
        if e.get("rev") is True:
            out["ver_metodos_fv"] = True
    except Exception:  # noqa: BLE001
        return {}
    return out
