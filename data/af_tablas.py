"""Tablas del Análisis Fundamental (v1.2.69), al estilo del análisis de TJX: una tabla por punto con una fila por año (años fiscales y último año móvil TTM), el
crecimiento anual compuesto (CAGR) y el promedio contra el último dato.

TODAS las cifras salen de los estados financieros de Yahoo que ya guarda `data/paquetes_yahoo.json` (`estados`); no se inventa nada. Lo que no está se omite (una
columna sin ningún dato no se muestra; un punto sin datos no aparece). Las funciones no tocan la red.

Se usan en dos lugares: la solapa Análisis Fundamental (ui/ficha.py) dibuja las tablas, y `bloque_texto()` las pasa a texto para quien redacta la lectura de cada punto
(así el texto y la tabla hablan siempre de los mismos números)."""
import html

# (clave, título). El orden es el de la solapa. Los puntos de TJX que no tienen datos propios (peers, dividendos) quedan para más adelante.
PUNTOS = (
    ("ingresos", "Ingresos y margen bruto"),
    ("ebit", "Resultado operativo (EBIT)"),
    ("eps", "Ganancia por acción (EPS)"),
    ("acciones", "Acciones en circulación"),
    ("fco", "Flujo de caja operativo"),
    ("fcf", "Flujo libre de caja y CAPEX"),
    ("roic", "Retorno sobre el capital (ROIC y ROE)"),
    ("salud", "Salud financiera: deuda e intereses"),
)
CLAVES = tuple(c for c, _ in PUNTOS)
ETIQUETAS = ("Favorable", "Mixto", "A vigilar", "Informativo")


def _es(txt):
    return txt.replace(",", "§").replace(".", ",").replace("§", ".")


def _n(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _serie(estados, grupo, rot):
    t = (estados or {}).get(grupo) or {}
    for fila in t.get("filas", []):
        if fila and fila[0] == rot:
            return {a: _n(v) for a, v in zip(t.get("anios", []), fila[1])}
    return {}


def _anios(estados):
    """(años fiscales de menor a mayor, clave del TTM o None), mirando la tabla de resultados."""
    t = (estados or {}).get("resultados") or {}
    an = t.get("anios") or []
    fy = sorted(a for a in an if isinstance(a, int))
    ttm = next((a for a in an if isinstance(a, str)), None)
    return fy, ttm


def _etq(a):
    return "TTM" if isinstance(a, str) else str(a)


# --- formatos ---------------------------------------------------------------------------------------------------------------

def _f(v, tipo):
    v = _n(v)
    if v is None:
        return "–"
    if tipo == "m":
        return _es(f"{v / 1e6:,.0f}")
    if tipo == "pct":
        return _es(f"{v * 100:.1f} %")
    if tipo == "x":
        return _es(f"{v:.2f}x")
    if tipo == "eps":
        return _es(f"{v:.2f}")
    if tipo == "var":
        return _es(f"{v * 100:+.1f} %")
    return str(v)


def _var(s, fy, a):
    """Variación contra el año fiscal anterior (solo entre años fiscales consecutivos; el TTM no se compara)."""
    if not isinstance(a, int) or a - 1 not in fy:
        return None
    x, y = s.get(a), s.get(a - 1)
    if x is None or y is None or y <= 0 or x < 0:
        return None
    return x / y - 1


def cagr(serie, fy):
    """(CAGR, año inicial, año final) entre el primer y el último año fiscal con datos positivos, o None."""
    pts = [(a, serie.get(a)) for a in fy if serie.get(a) is not None]
    if len(pts) < 2:
        return None
    (a0, v0), (a1, v1) = pts[0], pts[-1]
    if v0 <= 0 or v1 <= 0 or a1 <= a0:
        return None
    return (v1 / v0) ** (1.0 / (a1 - a0)) - 1.0, a0, a1


# --- construcción de cada tabla ------------------------------------------------------------------------------------------------

def _cols(estados, clave):
    """Lista de (encabezado, {año: valor}, tipo, con_variacion) para el punto."""
    S = lambda g, r: _serie(estados, g, r)  # noqa: E731
    ing, ebitda = S("resultados", "Ingresos"), S("resultados", "EBITDA")
    ebit, neto = S("resultados", "Resultado operativo"), S("resultados", "Resultado neto")
    fco, capex, fcf = S("flujo", "Flujo de efectivo operativo"), S("flujo", "Inversión en activos fijos (CAPEX)"), S("flujo", "Flujo de efectivo libre")
    caja = S("balance", "Caja e inversiones de corto plazo")
    deuda = S("balance", "Deuda total")
    interes = S("resultados", "Gasto por intereses")
    pat, act, ac_, pc = S("balance", "Patrimonio neto"), S("balance", "Activo total"), S("balance", "Activo corriente"), S("balance", "Pasivo corriente")

    def ab(d):
        return {k: (abs(v) if v is not None else None) for k, v in d.items()}

    def razon(a, b, signo=1):
        return {k: (signo * a[k] / b[k] if a.get(k) is not None and b.get(k) not in (None, 0) else None) for k in a}

    if clave == "ingresos":
        return [("Ingresos (M)", ing, "m", True), ("Utilidad bruta (M)", S("resultados", "Utilidad bruta"), "m", True), ("Margen bruto", S("ratios", "Margen bruto"), "pct", False)]
    if clave == "ebit":
        return [("EBIT (M)", ebit, "m", True), ("Margen operativo", S("ratios", "Margen operativo"), "pct", False), ("Resultado neto (M)", neto, "m", True), ("Margen neto", S("ratios", "Margen neto"), "pct", False)]
    if clave == "eps":
        return [("EPS diluido", S("resultados", "Ganancia por acción (diluida)"), "eps", True), ("Resultado neto (M)", neto, "m", True)]
    if clave == "acciones":
        return [("Acciones diluidas (M)", S("resultados", "Acciones promedio (diluidas)"), "m", True), ("Recompra de acciones (M)", ab(S("flujo", "Recompra de acciones")), "m", False)]
    if clave == "fco":
        return [("Flujo operativo (M)", fco, "m", True), ("Resultado neto (M)", neto, "m", False), ("Flujo operativo / Resultado neto", razon(fco, neto), "pct", False),
                ("EBITDA (M)", ebitda, "m", False), ("Flujo operativo / EBITDA", razon(fco, ebitda), "pct", False)]
    if clave == "fcf":
        return [("Flujo libre (M)", fcf, "m", True), ("CAPEX (M)", ab(capex), "m", False), ("Margen de flujo libre", S("ratios", "Margen de flujo de efectivo libre"), "pct", False),
                ("CAPEX / Resultado neto", razon(capex, neto, -1), "pct", False), ("Dividendos pagados (M)", ab(S("flujo", "Dividendos pagados")), "m", False)]
    if clave == "roic":
        return [("ROIC (según Yahoo)", S("ratios", "Retorno sobre el capital invertido (ROIC)"), "pct", False), ("ROE", S("ratios", "Retorno sobre el patrimonio (ROE)"), "pct", False),
                ("Margen operativo", S("ratios", "Margen operativo"), "pct", False), ("Capital invertido (M)", S("balance", "Capital invertido (según Yahoo)"), "m", False)]
    if clave == "salud":
        dneta = S("balance", "Deuda neta") or {k: (deuda[k] - caja[k] if deuda.get(k) is not None and caja.get(k) is not None else None) for k in deuda}
        cobertura = {k: (ebit[k] / abs(interes[k]) if ebit.get(k) is not None and interes.get(k) not in (None, 0) else None) for k in ebit}
        return [("Caja (M)", caja, "m", False), ("Deuda corto plazo (M)", S("balance", "Deuda de corto plazo"), "m", False), ("Deuda largo plazo (M)", S("balance", "Deuda de largo plazo"), "m", False),
                ("Deuda total (M)", deuda, "m", False), ("Deuda neta (M)", dneta, "m", False), ("Patrimonio neto (M)", pat, "m", False),
                ("Gasto por intereses (M)", interes, "m", False), ("Cobertura de intereses (EBIT / intereses)", cobertura, "x", False),
                ("Deuda neta / EBITDA", razon(dneta, ebitda), "x", False), ("Deuda total / Patrimonio", S("ratios", "Deuda total / Patrimonio"), "x", False),
                ("Activo total / Patrimonio", razon(act, pat), "x", False), ("Liquidez corriente", razon(ac_, pc), "x", False)]
    return []


def tabla(estados, clave):
    """{'titulo', 'cols': [encabezados], 'filas': [[año, celdas...]], 'stats': [líneas], 'notas': [líneas]} o None si el punto no tiene ningún dato.
    Una fila por año: los fiscales de menor a mayor y al final el TTM. Las columnas con alguna variación llevan al lado 'Var. anual' (solo la de la primera columna)."""
    fy, ttm = _anios(estados)
    años = fy + ([ttm] if ttm else [])
    if not años:
        return None
    cols = [c for c in _cols(estados, clave) if any(c[1].get(a) is not None for a in años)]
    if not cols:
        return None
    enc, usadas = ["Año"], []
    for nombre, s, tipo, conv in cols:
        enc.append(nombre)
        usadas.append((nombre, s, tipo, conv))
        if conv and len(usadas) == 1:
            enc.append("Var. anual")
    filas = []
    for a in años:
        fila = [_etq(a)]
        for i, (nombre, s, tipo, conv) in enumerate(usadas):
            fila.append(_f(s.get(a), tipo))
            if conv and i == 0:
                fila.append(_f(_var(s, fy, a), "var"))
        if any(c != "–" for c in fila[1:]):
            filas.append(fila)
    if not filas:
        return None
    titulo = dict(PUNTOS).get(clave, clave)
    return {"clave": clave, "titulo": titulo, "cols": enc, "filas": filas, "stats": _stats(estados, clave, usadas, fy, ttm), "notas": _notas(usadas, fy, ttm)}


def _prom(s, fy, ttm):
    """(promedio de los años fiscales, último dato, etiqueta del último dato) de una serie de razones; None si faltan datos."""
    vals = [s[a] for a in fy if s.get(a) is not None]
    ult_a = ttm if ttm and s.get(ttm) is not None else (fy[-1] if fy and s.get(fy[-1]) is not None else None)
    if len(vals) < 2 or ult_a is None:
        return None
    return sum(vals) / len(vals), s[ult_a], _etq(ult_a)


def _stats(estados, clave, usadas, fy, ttm):
    out = []
    por = {n: (s, tipo) for n, s, tipo, _ in usadas}
    primera = usadas[0]
    if clave in ("ingresos", "ebit", "eps", "acciones", "fco", "fcf"):
        for nombre, s, tipo, conv in usadas:
            if conv:
                r = cagr(s, fy)
                if r:
                    txt = f"{nombre.replace(' (M)', '')}: crecimiento anual compuesto (CAGR) {r[1]}→{r[2]} = {_f(r[0], 'pct')} por año."
                    out.append(txt)
                elif nombre == primera[0]:
                    out.append(f"{nombre.replace(' (M)', '')}: CAGR no calculable (datos insuficientes o base negativa).")
    if clave == "acciones":
        s = primera[1]
        a0 = s.get(fy[0]) if fy else None
        a1 = s.get(ttm) if ttm and s.get(ttm) is not None else (s.get(fy[-1]) if fy else None)
        if a0 and a1 and a0 > 0:
            años = (fy[-1] - fy[0]) if fy and len(fy) > 1 else None
            anual = f" ({_f((a1 / a0) ** (1 / años) - 1, 'var')} por año)" if años and not ttm else ""
            out.append(f"Cambio total de las acciones diluidas, {fy[0]}→{_etq(ttm) if ttm else fy[-1]}: {_f(a1 / a0 - 1, 'var')}{anual}.")
    for nombre in ("Margen bruto", "Margen operativo", "Margen neto", "Margen de flujo libre", "Flujo operativo / Resultado neto", "Flujo operativo / EBITDA", "ROIC (según Yahoo)", "ROE"):
        if nombre in por and not (clave == "roic" and nombre == "Margen operativo"):
            p = _prom(por[nombre][0], fy, ttm)
            if p:
                dif = (p[1] - p[0]) * 100
                out.append(f"{nombre}: promedio de los años fiscales = {_f(p[0], 'pct')}; último dato ({p[2]}) = {_f(p[1], 'pct')} ({_es(f'{dif:+.1f}')} puntos porcentuales frente al promedio).")
    return out


def _notas(usadas, fy, ttm):
    """Avisos de dato: el último año móvil se aleja mucho del último año fiscal (Yahoo a veces mezcla períodos): se avisa en vez de apoyarse en él."""
    out = []
    if not (ttm and fy):
        return out
    for nombre, s, tipo, conv in usadas:
        if tipo != "m" or nombre.startswith(("CAPEX", "Recompra", "Dividendos")):
            continue
        a, b = s.get(ttm), s.get(fy[-1])
        if a and b and a > 0 and b > 0 and not (0.5 <= a / b <= 1.8):
            out.append(f"{nombre.replace(' (M)', '')}: el TTM ({_f(a, 'm')}) es {_es(f'{a / b:.1f}')} veces el último año fiscal ({_f(b, 'm')}). Variación fuera de lo común: dato a verificar.")
    return out


def todas(estados):
    """{clave: tabla} de los puntos que tienen datos, en el orden de PUNTOS."""
    return {c: t for c, _ in PUNTOS for t in [tabla(estados, c)] if t}


def moneda(estados):
    return str((estados or {}).get("moneda") or "").upper() or None


# --- salidas -------------------------------------------------------------------------------------------------------------------

def bloque_texto(estados, claves=None):
    """Las tablas por punto en texto plano, para redactar con los números exactos. `claves` limita los puntos (por ejemplo, un banco no usa EBIT ni flujo de caja)."""
    mon = moneda(estados)
    L = [f"(Montos en millones{' de ' + mon if mon else ''}; TTM = últimos 12 meses; \"–\" = dato no disponible)"]
    for c, t in todas(estados).items():
        if claves is not None and c not in claves:
            continue
        L += ["", f"[{c}] {t['titulo']}", " | ".join(t["cols"])]
        L += [" | ".join(f) for f in t["filas"]]
        L += ["  · " + x for x in t["stats"]]
        L += ["  ! " + x for x in t["notas"]]
    return "\n".join(L)


def tabla_html(t):
    """Tabla HTML (con desplazamiento lateral en pantallas angostas)."""
    cab = "".join(f"<th>{html.escape(c)}</th>" for c in t["cols"])
    cuerpo = ""
    for f in t["filas"]:
        cuerpo += "<tr>" + f'<td class="a">{html.escape(f[0])}</td>' + "".join(f"<td>{html.escape(x)}</td>" for x in f[1:]) + "</tr>"
    return f'<div class="af-tw"><table class="af-tb"><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table></div>'
