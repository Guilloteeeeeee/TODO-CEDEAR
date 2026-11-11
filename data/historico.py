"""
v1.5.48 (pedido de Guille, 08/11/2026): ARCHIVO HISTÓRICO PROPIO. Lo que bajamos de Yahoo / Stock Analysis se guarda para siempre en data/historico/,
así la base crece con el tiempo y la app no depende de que esas fuentes respondan. Ver data/historico/LEEME.md.

Qué se guarda y con qué regla:
- estados.json      Años fiscales de los estados (resultados, balance, flujo, ratios). SOLO SE AGREGA: un año que Yahoo deja de traer queda guardado.
                    Mientras Yahoo siga trayendo un año, manda su versión más nueva (las empresas a veces corrigen años anteriores); si cambia más de
                    UMBRAL_CAMBIO un número clave ya guardado, se anota en cambios.json. Un dato vacío nunca borra uno guardado.
                    Los «últimos 12 meses» (TTM) no son un año: van aparte («ttm») y se reemplazan en cada corrida.
- precios_mensuales.json  Cierre del último día hábil de cada mes, ajustado por splits (no por dividendos), de toda la historia.
- dividendos.json   Cada dividendo pagado (fecha, monto por acción, ajustado por splits).
- splits.json       Cada split (fecha, factor: 10 = 10 por 1; 0.1 = contra-split 1 por 10). Con esto se ajusta todo lo anterior.
- multiplos_anuales.json  Múltiplos por año fiscal (Stock Analysis): solo se agregan años.
- fotos/AAAA-MM.json  Una foto por mes de lo que cambia todos los días (precio, múltiplos, score, categoría, ETFs, ficha). Si en el mes se corre varias
                    veces, queda la última. Los precios de una foto vieja se ajustan por los splits posteriores al leerla (ajustar_foto).
- informes/TICKER_AAAA-MM-DD.json  Cada versión de cada Análisis Fundamental.
- cambios.json      Registro de correcciones de años ya guardados y de splits nuevos aplicados.

SPLITS (pedido explícito de Guille: «superimportantes»). Yahoo entrega precios, dividendos y cifras por acción ya ajustados por todos los splits
hasta el día de la bajada. Lo guardado antes de un split nuevo NO lo está. Por eso:
- precios y dividendos guardados: cuando aparece un split que no conocíamos, se dividen por el factor todos los valores anteriores a su fecha
  (en el mismo momento de fusionar; queda anotado en cambios.json);
- estados: cada año guarda su fecha de captura y, al leerlo (estados_completos), la ganancia por acción se divide y la cantidad de acciones se
  multiplica por los splits ocurridos DESPUÉS de esa captura;
- fotos mensuales: lo mismo con los campos de precio (ajustar_foto).
"""
import datetime as _dt
import glob
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(AQUI, "historico")
UMBRAL_CAMBIO = 0.05
# (sin la ganancia por acción: un split la cambia sin que sea una corrección)
FILAS_CLAVE = {"resultados": ("Ingresos", "Resultado operativo", "Resultado neto"),
               "balance": ("Activo total", "Deuda total", "Patrimonio neto"), "flujo": ("Flujo de efectivo operativo", "Flujo de efectivo libre")}
GRUPOS = ("resultados", "balance", "flujo", "ratios")
# filas de los estados que dependen de la cantidad de acciones: se dividen (por_accion) o multiplican (acciones) por el factor del split
POR_ACCION = ("Ganancia por acción (diluida)", "Ganancia por acción (básica)", "Dividendo por acción")
ACCIONES = ("Acciones promedio (diluidas)", "Acciones promedio (básicas)", "Acciones en circulación")
# campos de las fotos mensuales que son precios por acción (se ajustan por splits al leerlas)
CAMPOS_PRECIO = ("precio_actual", "fair_value", "precio_max_52s", "precio_min_52s", "annual_dividend", "precio", "nav", "dividendo_anual")
CAMPOS_FOTO_EMPRESA = ("nombre", "sector", "precio_actual", "market_cap", "fair_value", "categoria", "score_total", "score_fundamental", "score_tecnico",
                       "metricas_usadas", "metricas_total", "dividend_yield_actual", "dividend_yield_mediana", "annual_dividend", "beta",
                       "precio_max_52s", "precio_min_52s", "per_actual", "per_mediana", "ev_ebitda_actual", "ev_ebitda_mediana", "p_fcf_actual",
                       "p_fcf_mediana", "ps_actual", "ps_mediana", "p_b_actual", "p_b_mediana", "ev_ventas_actual", "ev_ventas_mediana", "peg_actual",
                       "peg_mediana", "rend_total_actual", "rend_total_mediana", "p_ffo_actual", "p_ffo_mediana", "p_affo_actual", "p_affo_mediana",
                       "moneda_cotizacion", "moneda_estados", "fecha_dato")
CAMPOS_FOTO_ETF = ("nombre", "gestor", "precio", "nav", "aum", "comision", "rendimiento", "dividendo_anual", "beta", "volumen_prom", "max_52s", "min_52s",
                   "holdings", "sectores", "activos", "dividendos")
CAMPOS_FOTO_FICHA = ("ceo", "empleados", "acciones", "ev", "ingresos_ttm", "beta", "pais", "mercado_cod")


def _ruta(nombre, carpeta=None):
    return os.path.join(carpeta or CARPETA, nombre)


def _hoy():
    return _dt.date.today().isoformat()


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def leer(nombre, defecto=None, carpeta=None):
    try:
        with open(_ruta(nombre, carpeta), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if defecto is None else defecto


def escribir(nombre, datos, carpeta=None):
    """Escribe a un temporal y recién ahí reemplaza (si se corta a la mitad, el archivo bueno no se pierde)."""
    ruta = _ruta(nombre, carpeta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, ruta)


def _anotar(cambios, tipo, ticker, **datos):
    cambios.append({"fecha": _hoy(), "tipo": tipo, "ticker": ticker, **datos})


# ---------------------------------------------------------------------------------------------------------------------
# SPLITS
# ---------------------------------------------------------------------------------------------------------------------
def factor_despues(splits, desde, hasta=None):
    """Producto de los factores de los splits con fecha > desde (y <= hasta). `splits`: [[fecha ISO, factor]]. Fechas ISO (AAAA-MM-DD o AAAA-MM)."""
    f = 1.0
    for fecha, factor in splits or []:
        fac = _n(factor)
        if fac and fac > 0 and str(fecha) > str(desde) and (hasta is None or str(fecha) <= str(hasta)):
            f *= fac
    return f


def fusionar_splits(viejos, nuevos):
    """(lista unida, splits que no conocíamos). Un split se identifica por su fecha."""
    conocidos = {str(f): _n(x) for f, x in viejos or []}
    nuevos_v = [(str(f), _n(x)) for f, x in nuevos or [] if _n(x) and _n(x) > 0 and _n(x) != 1.0]
    sin_ver = [(f, x) for f, x in nuevos_v if f not in conocidos]
    for f, x in nuevos_v:
        conocidos[f] = x
    return sorted([[f, x] for f, x in conocidos.items() if x]), sin_ver


def _ajustar_serie(serie, splits_nuevos, campo_fecha=lambda k: k):
    """Divide por el factor los valores de fecha anterior a cada split nuevo. `serie`: {fecha: valor}."""
    out = {}
    for k, v in serie.items():
        fac = 1.0
        for fs, x in splits_nuevos:
            if str(campo_fecha(k)) < str(fs):
                fac *= x
        out[k] = v / fac if (v is not None and fac != 1.0) else v
    return out


# ---------------------------------------------------------------------------------------------------------------------
# PRECIOS MENSUALES Y DIVIDENDOS
# ---------------------------------------------------------------------------------------------------------------------
def cierres_mensuales(pares):
    """[(date, cierre)] diarios -> {"AAAA-MM": último cierre de ese mes}."""
    out = {}
    for f, c in sorted(pares or []):
        c = _n(c)
        if c is not None and c > 0:
            out[f"{f.year:04d}-{f.month:02d}"] = round(c, 6)
    return out


def fusionar_precios(guardado, nuevos_mensuales, splits_nuevos=(), mes_actual=None):
    """Une cierres mensuales. Lo que trae la bajada nueva manda (Yahoo ya lo ajustó por todos los splits). Lo que solo está guardado se conserva
    y, si hay splits nuevos, se ajusta. El mes en curso se guarda igual (se pisa en cada corrida hasta que termine el mes)."""
    g = _ajustar_serie(dict(guardado or {}), splits_nuevos, lambda k: f"{k}-31") if splits_nuevos else dict(guardado or {})
    for k, v in (nuevos_mensuales or {}).items():
        if _n(v):
            g[k] = round(float(v), 6)
    return dict(sorted(g.items()))


def fusionar_dividendos(guardados, nuevos, splits_nuevos=()):
    """[[fecha ISO, monto]] unidos por fecha (la bajada nueva manda); los guardados anteriores a un split nuevo se ajustan."""
    g = {str(f): _n(m) for f, m in guardados or [] if _n(m) is not None}
    if splits_nuevos:
        g = _ajustar_serie(g, splits_nuevos)
    for f, m in nuevos or []:
        if _n(m) is not None and _n(m) > 0:
            g[str(f)] = round(float(m), 8)
    return [[f, m] for f, m in sorted(g.items())]


def archivar_mercado(ticker, pares_diarios=None, dividendos=None, splits=None, carpeta=None, archivos=None, cambios=None):
    """Guarda cierres mensuales, dividendos y splits de un ticker (lo usa bajar_historico.py). `archivos`: dict ya leído para no releer en cada
    ticker ({"precios":…, "dividendos":…, "splits":…}); si se pasa, NO escribe (escribe quien llama con guardar_mercado). Devuelve los splits nuevos."""
    propio = archivos is None
    if propio:
        archivos = {"precios": leer("precios_mensuales.json", {}, carpeta), "dividendos": leer("dividendos.json", {}, carpeta),
                    "splits": leer("splits.json", {}, carpeta)}
        cambios = leer("cambios.json", [], carpeta)
    tk = str(ticker).upper()
    sp_todos, sp_nuevos = fusionar_splits(archivos["splits"].get(tk), splits)
    # un split nuevo solo obliga a ajustar si ya teníamos datos guardados de antes (si no, todo viene de Yahoo ya ajustado)
    hay_previo = bool((archivos["precios"].get(tk) or {}).get("m")) or bool(archivos["dividendos"].get(tk))
    a_ajustar = sp_nuevos if hay_previo else []
    if sp_todos:
        archivos["splits"][tk] = sp_todos
    if a_ajustar and cambios is not None:
        for f, x in a_ajustar:
            _anotar(cambios, "split", tk, split=f, factor=x, detalle="se ajustaron precios y dividendos guardados anteriores a esa fecha")
    if pares_diarios:
        reg = archivos["precios"].get(tk) or {}
        reg["m"] = fusionar_precios(reg.get("m"), cierres_mensuales(pares_diarios), a_ajustar)
        reg["act"] = _hoy()
        archivos["precios"][tk] = reg
    elif a_ajustar and tk in archivos["precios"]:
        archivos["precios"][tk]["m"] = fusionar_precios(archivos["precios"][tk].get("m"), {}, a_ajustar)
    if dividendos is not None or a_ajustar:
        archivos["dividendos"][tk] = fusionar_dividendos(archivos["dividendos"].get(tk), dividendos, a_ajustar)
        if not archivos["dividendos"][tk]:
            archivos["dividendos"].pop(tk, None)
    if propio:
        guardar_mercado(archivos, cambios, carpeta)
    return a_ajustar


def guardar_mercado(archivos, cambios=None, carpeta=None):
    escribir("precios_mensuales.json", archivos["precios"], carpeta)
    escribir("dividendos.json", archivos["dividendos"], carpeta)
    escribir("splits.json", archivos["splits"], carpeta)
    if cambios is not None:
        escribir("cambios.json", cambios, carpeta)


def cierres(ticker, carpeta=None):
    """{"AAAA-MM": cierre} guardado (ya ajustado por splits)."""
    return dict((leer("precios_mensuales.json", {}, carpeta).get(str(ticker).upper()) or {}).get("m") or {})


# ---------------------------------------------------------------------------------------------------------------------
# ESTADOS FINANCIEROS
# ---------------------------------------------------------------------------------------------------------------------
def _es_ttm(a):
    return isinstance(a, str)


def _tabla_a_dict(t):
    """{"anios":[…], "filas":[[rot, vals, tipo]]} -> ({año: {rot: v}}, [rots en orden], {rot: tipo})."""
    por_anio, orden, tipos = {}, [], {}
    for fila in (t or {}).get("filas", []):
        if not fila:
            continue
        rot, vals, tipo = fila[0], fila[1] if len(fila) > 1 else [], fila[2] if len(fila) > 2 else ""
        orden.append(rot)
        tipos[rot] = tipo
        for a, v in zip(t.get("anios", []), vals):
            por_anio.setdefault(a, {})[rot] = _n(v)
    return por_anio, orden, tipos


def _difiere(a, b):
    a, b = _n(a), _n(b)
    if a is None or b is None:
        return False
    if a == 0:
        return b != 0
    return abs(b - a) / abs(a) > UMBRAL_CAMBIO


def _ttm_vencido(ttm, anios):
    """True si ya hay un año fiscal guardado igual o posterior al año del TTM («2026 (TTM)» con el año 2026 ya cerrado)."""
    try:
        a = int(str(ttm.get("etq", "")).split()[0])
    except (ValueError, IndexError):
        return False
    return any(int(x) >= a for x in anios)


def fusionar_estados(reg, estados, ticker="", cambios=None, hoy=None):
    """Une los estados nuevos (formato de paquetes_yahoo: {"moneda", grupo: {"anios", "filas"}}) en el registro guardado de un ticker.
    reg = {"anios": {"2025": {"moneda", "captura", grupo: {rot: v}}}, "orden": {grupo: [rots]}, "tipos": {grupo: {rot: tipo}}, "ttm": {...}}."""
    hoy = hoy or _hoy()
    reg = dict(reg or {})
    anios = {k: dict(v) for k, v in (reg.get("anios") or {}).items()}
    orden = dict(reg.get("orden") or {})
    tipos = dict(reg.get("tipos") or {})
    if not estados:
        return reg
    moneda = estados.get("moneda") or "USD"
    nuevos_fy, ttm = {}, None
    for g in GRUPOS:
        por_anio, ord_g, tip_g = _tabla_a_dict(estados.get(g))
        if ord_g:
            vistos = list(orden.get(g) or [])
            orden[g] = vistos + [r for r in ord_g if r not in vistos] if vistos else ord_g
            tipos[g] = {**(tipos.get(g) or {}), **tip_g}
        for a, vals in por_anio.items():
            if _es_ttm(a):
                ttm = ttm or {"etq": a, "captura": hoy, "moneda": moneda}
                ttm[g] = vals
            else:
                nuevos_fy.setdefault(str(int(a)), {})[g] = vals
    for a, grupos in nuevos_fy.items():
        viejo = anios.get(a)
        if viejo and viejo.get("moneda", moneda) != moneda:
            # la empresa cambió la moneda en que informa: el año pasa a la moneda nueva entero (no se mezclan monedas)
            if cambios is not None:
                _anotar(cambios, "moneda", ticker, anio=a, antes=viejo.get("moneda"), despues=moneda)
            viejo = None
        nuevo = {"moneda": moneda, "captura": hoy}
        PS = set(POR_ACCION) | set(ACCIONES)
        trae_ps = any(v is not None for g in GRUPOS for r, v in (grupos.get(g) or {}).items() if r in PS)
        for g in GRUPOS:
            vn = grupos.get(g) or {}
            vv = (viejo or {}).get(g) or {}
            if cambios is not None and viejo:
                for rot in FILAS_CLAVE.get(g, ()):
                    if _difiere(vv.get(rot), vn.get(rot)):
                        _anotar(cambios, "correccion", ticker, anio=a, grupo=g, fila=rot, antes=vv.get(rot), despues=vn.get(rot))
            # manda lo nuevo, pero un dato vacío no borra uno guardado. Las filas por acción (ganancia por acción, cantidad de acciones) van en
            # bloque: o todas de la bajada nueva o todas de la guardada, para no mezclar números antes y después de un split.
            base = {r: v for r, v in vv.items() if not (trae_ps and r in PS)}
            unido = {**base, **{r: v for r, v in vn.items() if v is not None and (trae_ps or r not in PS)}}
            if unido:
                nuevo[g] = unido
        # fecha de las cifras por acción (decide el ajuste por splits posteriores al leerlas)
        nuevo["captura_acc"] = hoy if trae_ps or not viejo else viejo.get("captura_acc", viejo.get("captura", hoy))
        if viejo and all(nuevo.get(g) == viejo.get(g) for g in GRUPOS):
            nuevo["captura"] = viejo.get("captura", hoy)      # nada cambió: quedan las fechas originales
            nuevo["captura_acc"] = viejo.get("captura_acc", viejo.get("captura", hoy))
        anios[a] = nuevo
    reg.update({"anios": dict(sorted(anios.items())), "orden": orden, "tipos": tipos})
    if ttm:
        reg["ttm"] = ttm
    elif reg.get("ttm") and _ttm_vencido(reg["ttm"], anios):
        reg.pop("ttm", None)      # ya cerró el año fiscal que cubría: esos 12 meses ahora son un año guardado
    reg["act"] = hoy
    return reg


def archivar_estados(paquetes, carpeta=None):
    """{ticker: {"estados": …}} (paquetes_yahoo) -> fusiona todo en estados.json. Devuelve cuántos años nuevos y correcciones hubo."""
    arch = leer("estados.json", {}, carpeta)
    cambios = leer("cambios.json", [], carpeta)
    antes = sum(len((r or {}).get("anios") or {}) for r in arch.values())
    n0 = len(cambios)
    for tk, paq in (paquetes or {}).items():
        est = (paq or {}).get("estados") if isinstance(paq, dict) and "estados" in paq else paq
        if est:
            arch[str(tk).upper()] = fusionar_estados(arch.get(str(tk).upper()), est, str(tk).upper(), cambios)
    escribir("estados.json", dict(sorted(arch.items())), carpeta)
    escribir("cambios.json", cambios, carpeta)
    despues = sum(len((r or {}).get("anios") or {}) for r in arch.values())
    return {"anios_nuevos": despues - antes, "correcciones": sum(1 for c in cambios[n0:] if c["tipo"] == "correccion"), "empresas": len(arch)}


def sumar_anios_viejos(reg, anios_nuevos, ticker="", cambios=None, hoy=None, fuente="SEC", factor_accion=1.0):
    """v1.5.58: suma años fiscales de otra fuente (la SEC) SOLO hacia atrás: años más viejos que el más viejo guardado y en su misma moneda.
    Nunca toca un año que ya está (los de Yahoo mandan). anios_nuevos = {"2015": {"moneda", "presentado", grupo: {rot: v}}} (data/sec.a_anios).
    Cada año sumado lleva "fuente" y "captura_acc" = fecha de presentación del informe (decide el ajuste por splits posteriores).
    v1.5.61: factor_accion (data/sec.factor_por_accion) pasa las cifras por acción a la base de lo guardado (ADR): se multiplican y el año
    lleva "factor_accion". Devuelve (reg, [años sumados])."""
    hoy = hoy or _hoy()
    reg = dict(reg or {})
    anios = {k: dict(v) for k, v in (reg.get("anios") or {}).items()}
    orden = {g: list(v) for g, v in (reg.get("orden") or {}).items()}
    tipos = {g: dict(v) for g, v in (reg.get("tipos") or {}).items()}
    if anios:
        mas_viejo = min(anios)
        moneda = anios[mas_viejo].get("moneda", "USD")
    else:
        mas_viejo, moneda = "9999", None
    sumados = []
    for a, rec in sorted((anios_nuevos or {}).items()):
        if a >= mas_viejo or (moneda and rec.get("moneda") != moneda):
            continue
        nuevo = {"moneda": rec.get("moneda", "USD"), "captura": hoy, "captura_acc": rec.get("base_acc") or rec.get("presentado") or hoy,
                 "fuente": fuente}
        fac = _n(factor_accion) or 1.0
        if fac != 1.0:
            nuevo["factor_accion"] = fac
        for k in ("factor_accion", "modo_accion", "sin_por_accion"):     # v1.5.66: marcas que pone sec.llevar_a_base, año por año
            if rec.get(k) is not None:
                nuevo[k] = rec[k]
        for g in GRUPOS:
            vals = {r: _n(v) for r, v in (rec.get(g) or {}).items() if _n(v) is not None}
            if fac != 1.0:
                vals = {r: (v * fac if r in POR_ACCION else v / fac if r in ACCIONES else v) for r, v in vals.items()}
            if vals:
                nuevo[g] = vals
                vistos = orden.get(g) or []
                orden[g] = vistos + [r for r in vals if r not in vistos]
                tipos[g] = {**{r: ("eps" if r in POR_ACCION else "m") for r in vals}, **(tipos.get(g) or {})}
        anios[a] = nuevo
        sumados.append(a)
    if sumados:
        if cambios is not None:
            _anotar(cambios, "anios_" + fuente.lower(), ticker, anios=sumados, detalle=f"años sumados desde {fuente} (hacia atrás)")
        reg.update({"anios": dict(sorted(anios.items())), "orden": orden, "tipos": tipos})
    return reg, sumados


def _ajustar_por_splits(grupos, factor):
    if factor == 1.0:
        return grupos
    out = {}
    for g, vals in grupos.items():
        if g not in GRUPOS or not isinstance(vals, dict):
            out[g] = vals
            continue
        nv = {}
        for rot, v in vals.items():
            if v is not None and rot in POR_ACCION:
                v = v / factor
            elif v is not None and rot in ACCIONES:
                v = v * factor
            nv[rot] = v
        out[g] = nv
    return out


def estados_completos(ticker, estados=None, carpeta=None, archivo=None, splits=None, max_anios=10):
    """Estados para mostrar: los de Yahoo (si hay) más los años guardados que Yahoo ya no trae (misma moneda), ajustados por splits posteriores a su
    captura. Mismo formato que paquetes_yahoo (el más nuevo a la izquierda). Si Yahoo no trajo nada, se arman solo con lo guardado (y su TTM)."""
    tk = str(ticker).upper()
    reg = (archivo if archivo is not None else leer("estados.json", {}, carpeta)).get(tk)
    if not reg or not reg.get("anios"):
        return estados or {}
    sp = splits if splits is not None else leer("splits.json", {}, carpeta).get(tk, [])
    moneda = (estados or {}).get("moneda") or (reg.get("ttm") or {}).get("moneda") or next(iter(reg["anios"].values())).get("moneda") or "USD"
    actuales = set()
    if estados:
        an, _, _ = _tabla_a_dict(estados.get("resultados"))
        actuales = {str(int(a)) for a in an if not _es_ttm(a)}
    extra = {}
    for a, rec in reg["anios"].items():
        if a in actuales or rec.get("moneda", moneda) != moneda:
            continue
        extra[a] = _ajustar_por_splits(rec, factor_despues(sp, rec.get("captura_acc", rec.get("captura", ""))))
    if estados and not extra:
        return estados
    out = {"moneda": moneda}
    ttm = None
    if not estados and reg.get("ttm") and reg["ttm"].get("moneda", moneda) == moneda and not _ttm_vencido(reg["ttm"], reg["anios"]):
        ttm = (reg["ttm"]["etq"], _ajustar_por_splits(reg["ttm"], factor_despues(sp, reg["ttm"].get("captura", ""))))
    for g in GRUPOS:
        por_anio, ord_g, tip_g = _tabla_a_dict((estados or {}).get(g))
        ord_g = ord_g or list((reg.get("orden") or {}).get(g) or [])
        tip_g = {**((reg.get("tipos") or {}).get(g) or {}), **tip_g}
        for a, rec in extra.items():
            por_anio[int(a)] = rec.get(g) or {}
        if ttm:
            por_anio[ttm[0]] = ttm[1].get(g) or {}
        if not ord_g or not por_anio:
            continue
        ttms = [a for a in por_anio if _es_ttm(a)]
        fys = sorted((a for a in por_anio if not _es_ttm(a)), reverse=True)[:max_anios]
        cols = ttms + fys
        out[g] = {"anios": cols, "filas": [[r, [por_anio.get(a, {}).get(r) for a in cols], tip_g.get(r, "")] for r in ord_g]}
    return out if out.get("resultados") else (estados or {})


# ---------------------------------------------------------------------------------------------------------------------
# MÚLTIPLOS POR AÑO (Stock Analysis)
# ---------------------------------------------------------------------------------------------------------------------
def archivar_multiplos(datos, carpeta=None):
    """{ticker: {multiplo: {año: valor}}} -> solo agrega años (un año guardado se actualiza si viene con dato)."""
    arch = leer("multiplos_anuales.json", {}, carpeta)
    for tk, ms in (datos or {}).items():
        reg = arch.setdefault(str(tk).upper(), {})
        for m, xs in (ms or {}).items():
            serie = reg.setdefault(m, {})
            for a, v in (xs or {}).items():
                if _n(v) is not None:
                    serie[str(a)] = _n(v)
            reg[m] = dict(sorted(serie.items()))
    escribir("multiplos_anuales.json", dict(sorted(arch.items())), carpeta)
    return len(arch)


# ---------------------------------------------------------------------------------------------------------------------
# FOTOS MENSUALES
# ---------------------------------------------------------------------------------------------------------------------
def _limpio(v):
    if isinstance(v, float):
        return None if v != v else round(v, 6)
    if isinstance(v, dict):
        return {k: _limpio(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_limpio(x) for x in v]
    return v


def foto_mensual(seccion, filas, campos, mes=None, carpeta=None, fecha=None, extra=None):
    """Guarda (pisa) la sección del mes: `filas` {ticker: dict}; se guardan solo `campos`. Si en el mes se corre varias veces, queda la última.
    `extra` {ticker: {campo: valor}} se suma (por ejemplo la calidad del Análisis Fundamental)."""
    mes = mes or _dt.date.today().strftime("%Y-%m")
    nombre = os.path.join("fotos", f"{mes}.json")
    foto = leer(nombre, {}, carpeta)
    sec = {}
    for tk, f in (filas or {}).items():
        d = {c: _limpio(f.get(c)) for c in campos if f.get(c) is not None}
        d.update((extra or {}).get(tk) or {})
        if d:
            sec[str(tk).upper()] = d
    foto[seccion] = sec
    foto.setdefault("fechas", {})[seccion] = fecha or _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    escribir(nombre, foto, carpeta)
    return len(sec)


def fotos_disponibles(carpeta=None):
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(carpeta or CARPETA, "fotos", "*.json")))


def ajustar_foto(ticker, valores, mes, carpeta=None, splits=None):
    """Valores de una foto de `mes` (AAAA-MM) llevados a los splits de hoy: los campos de precio se dividen por los splits posteriores."""
    sp = splits if splits is not None else leer("splits.json", {}, carpeta).get(str(ticker).upper(), [])
    fac = factor_despues(sp, f"{mes}-31")
    if fac == 1.0:
        return dict(valores or {})
    return {k: (v / fac if (k in CAMPOS_PRECIO and _n(v) is not None) else v) for k, v in (valores or {}).items()}


# ---------------------------------------------------------------------------------------------------------------------
# INFORMES (Análisis Fundamental)
# ---------------------------------------------------------------------------------------------------------------------
def _fecha_iso(f):
    try:
        d, m, a = str(f).split("/")
        return f"{int(a):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return None


def archivar_informe(ticker, informe, carpeta=None):
    """Guarda una versión de un informe como informes/TICKER_AAAA-MM-DD.json (si ya existe esa fecha, no la pisa). Devuelve la ruta o None."""
    if not isinstance(informe, dict) or not informe.get("fecha"):
        return None
    iso = _fecha_iso(informe["fecha"])
    if not iso:
        return None
    nombre = os.path.join("informes", f"{str(ticker).upper()}_{iso}.json")
    if os.path.exists(_ruta(nombre, carpeta)):
        return None
    escribir(nombre, informe, carpeta)
    return _ruta(nombre, carpeta)


def informes_guardados(ticker=None, carpeta=None):
    patron = f"{str(ticker).upper()}_*.json" if ticker else "*.json"
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(carpeta or CARPETA, "informes", patron)))


def resumen(carpeta=None):
    """Números del archivo, para el LEEME y los .bat."""
    est = leer("estados.json", {}, carpeta)
    pre = leer("precios_mensuales.json", {}, carpeta)
    meses = [k for r in pre.values() for k in (r.get("m") or {})]
    anios = [int(a) for r in est.values() for a in (r.get("anios") or {})]
    return {"empresas_con_estados": len(est), "anios_fiscales": len(anios), "anio_mas_viejo": min(anios) if anios else None,
            "tickers_con_precios": len(pre), "cierres_mensuales": len(meses), "mes_mas_viejo": min(meses) if meses else None,
            "con_dividendos": len(leer("dividendos.json", {}, carpeta)), "con_splits": len(leer("splits.json", {}, carpeta)),
            "fotos": fotos_disponibles(carpeta), "informes": len(informes_guardados(carpeta=carpeta))}
