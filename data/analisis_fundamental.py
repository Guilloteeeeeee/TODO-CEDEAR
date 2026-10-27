"""Análisis Fundamental automático (v1.2.68): una visión general de cada empresa con Resumen, Desarrollo (incluida la Tesis de inversión) y Conclusión.

Cómo funciona (nada se calcula ni se revisa a mano):
  1. `bloque_datos()` arma, con los estados financieros que ya baja `bajar_paquetes_yahoo.py` (último año móvil TTM + 4 años fiscales), la descripción del negocio y
     el foso/etapa, un bloque de texto con las cifras, los ratios y las variaciones YA calculados por el código. Si un dato no está, dice "no disponible".
  2. `generar_analisis_fundamental.py` manda ese bloque junto con `data/prompt_analisis_fundamental.txt` a la API de Claude (hace falta una clave, ver el .bat) y
     guarda lo que contesta en `data/analisis_fundamental.json`.
  3. La solapa "Análisis Fundamental" de la ficha muestra lo guardado (`para_ficha()`), con la fecha y la aclaración de que es un texto generado con IA, informativo y
     sin recomendación. Si la empresa no tiene análisis, la solapa dice "Próximamente".
No hay puntaje, ni PASA / NO PASA, ni filtros de exclusión (decisión de Guille del 27/10/2026): el texto es una lectura de conjunto para decidir si vale la pena seguir
investigando. Las funciones de este módulo no tocan la red."""
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(AQUI, "analisis_fundamental.json")
RUTA_PROMPT = os.path.join(AQUI, "prompt_analisis_fundamental.txt")
RIESGOS_IA = ("muy alto", "alto", "moderado", "bajo", "muy bajo")
TITULOS = ("El negocio", "Crecimiento y márgenes", "Ganancias por acción y acciones en circulación", "Caja y retorno sobre el capital", "Salud financiera",
           "Competidores", "Puntos fuertes", "Puntos débiles y riesgos", "Tesis de inversión")


# --- formato de números (castellano: punto de miles, coma decimal) -----------------------------------------------------------

def _es(txt):
    return txt.replace(",", "§").replace(".", ",").replace("§", ".")


def _n(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _fmt(v, tipo):
    v = _n(v)
    if v is None:
        return "no disp."
    if tipo == "pct":
        return _es(f"{v * 100:,.1f} %")
    if tipo == "x":
        return _es(f"{v:,.2f}")
    if tipo == "eps":
        return _es(f"{v:,.2f}")
    if tipo == "n":
        return _es(f"{v / 1e6:,.0f} M")
    return _es(f"{v / 1e6:,.0f}")          # montos en millones


def _tabla(grupo, nombre):
    t = grupo or {}
    if not t.get("filas"):
        return []
    anios = [str(a) for a in t["anios"]]
    out = [f"{nombre} (columnas: {' | '.join(anios)})"]
    for fila in t["filas"]:
        rot, vals, tipo = fila[0], fila[1], fila[2]
        out.append(f"- {rot}: " + " | ".join(_fmt(v, tipo) for v in vals))
    return out


def _serie(estados, clave, rot):
    t = (estados or {}).get(clave) or {}
    for fila in t.get("filas", []):
        if fila[0] == rot:
            return dict(zip(t["anios"], fila[1]))
    return {}


def _anios_fiscales(serie):
    """Años fiscales completos (enteros) de la serie, de menor a mayor, y la clave del TTM (texto) si existe."""
    fy = sorted(a for a in serie if isinstance(a, int))
    ttm = next((a for a in serie if isinstance(a, str)), None)
    return fy, ttm


def _cagr(serie):
    """(CAGR entre el primer y el último año fiscal, primer año, último año) o None si no se puede (base <= 0, un solo año...)."""
    fy, _ = _anios_fiscales(serie)
    if len(fy) < 2:
        return None
    a, b = _n(serie.get(fy[0])), _n(serie.get(fy[-1]))
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return (b / a) ** (1.0 / (fy[-1] - fy[0])) - 1.0, fy[0], fy[-1]


def derivados(estados):
    """Líneas de texto con lo que calcula el código: crecimiento anual compuesto de los años fiscales, margen del último año contra el promedio de los años
    completos, y cambio de las acciones en circulación. Todo con los mismos datos del bloque."""
    est = estados or {}
    out = []
    for clave, rot, nom in (("resultados", "Ingresos", "Ingresos"), ("resultados", "Utilidad bruta", "Utilidad bruta"),
                            ("resultados", "Resultado operativo", "Resultado operativo"), ("resultados", "Resultado neto", "Resultado neto"),
                            ("resultados", "Ganancia por acción (diluida)", "Ganancia por acción diluida"),
                            ("flujo", "Flujo de efectivo operativo", "Flujo de efectivo operativo"), ("flujo", "Flujo de efectivo libre", "Flujo de efectivo libre")):
        r = _cagr(_serie(est, clave, rot))
        out.append(f"- {nom}: crecimiento anual compuesto {r[1]}-{r[2]} = {_fmt(r[0], 'pct')}" if r else f"- {nom}: crecimiento anual compuesto no calculable (datos insuficientes o base negativa)")
    for rot in ("Margen bruto", "Margen operativo"):
        s = _serie(est, "ratios", rot)
        fy, ttm = _anios_fiscales(s)
        # con TTM: el TTM contra el promedio de los años fiscales completos; sin TTM: el último año fiscal contra el promedio de los anteriores
        base = fy if ttm else fy[:-1]
        vals = [_n(s.get(a)) for a in base if _n(s.get(a)) is not None]
        ult = _n(s.get(ttm)) if ttm else (_n(s.get(fy[-1])) if fy else None)
        if len(vals) >= 2 and ult is not None:
            prom = sum(vals) / len(vals)
            dif = (ult - prom) * 100
            marca = "  <- ALERTA: más de 1 punto porcentual por debajo del promedio" if dif < -1.0 else ""
            out.append(f"- {rot}: promedio de los años fiscales {base[0]}-{base[-1]} = {_fmt(prom, 'pct')}; último dato ({ttm or fy[-1]}) = {_fmt(ult, 'pct')}; diferencia = {_es(f'{dif:+.1f}')} puntos porcentuales{marca}")
    sh = _serie(est, "resultados", "Acciones promedio (diluidas)")
    fy, ttm = _anios_fiscales(sh)
    if len(fy) >= 1:
        a, b = _n(sh.get(fy[0])), _n(sh.get(ttm)) if ttm else _n(sh.get(fy[-1]))
        if a and b:
            out.append(f"- Acciones diluidas: de {_fmt(a, 'n')} en {fy[0]} a {_fmt(b, 'n')} en {ttm or fy[-1]} ({_es(f'{(b / a - 1) * 100:+.1f}')} %)")
    return out


def alertas(estados, moneda=None):
    """AVISOS DE DATOS: cosas raras o faltantes que el análisis tiene que mencionar como 'dato a verificar' en vez de apoyarse en ellas."""
    est = estados or {}
    av = []
    if moneda and str(moneda).upper() != "USD":
        av.append(f"Los estados financieros están en {moneda}, no en dólares: las cifras de este bloque están en esa moneda.")
    if not _serie(est, "resultados", "Gasto por intereses"):
        av.append("Gasto por intereses: no disponible en los datos guardados (se carga al volver a bajar los datos de Yahoo). No calcules la cobertura de intereses.")
    if not _serie(est, "balance", "Deuda de largo plazo") and not _serie(est, "balance", "Deuda de corto plazo"):
        av.append("No hay separación de deuda de corto y largo plazo en los datos guardados: usá solo la deuda total.")
    for clave, rot in (("flujo", "Flujo de efectivo operativo"), ("flujo", "Flujo de efectivo libre"), ("resultados", "Ingresos")):
        s = _serie(est, clave, rot)
        fy, ttm = _anios_fiscales(s)
        if ttm and fy:
            a, b = _n(s.get(ttm)), _n(s.get(max(fy)))
            if a and b and b > 0 and a > 0 and not (0.5 <= a / b <= 1.8):
                av.append(f"{rot}: el último año móvil ({_fmt(a, 'm')} M) es {_es(f'{a / b:.1f}')} veces el del último año fiscal ({_fmt(b, 'm')} M): variación fuera de lo común, dato a verificar.")
    fy_res = _anios_fiscales(_serie(est, "resultados", "Ingresos"))[0]
    if len(fy_res) < 3:
        av.append(f"Solo hay {len(fy_res)} año(s) fiscal(es) completo(s) de resultados: las tendencias son poco confiables.")
    return av


def bloque_datos(ticker, nombre="", sector="", industria="", pais="", descripcion="", estados=None, foso=None, etapa=None, moneda=None):
    """Texto con todo lo que ve el modelo sobre la empresa. Nada se inventa: lo que falta dice 'no disponible'."""
    est = estados or {}
    moneda = moneda or est.get("moneda")
    L = [f"EMPRESA: {nombre or ticker} ({ticker})"]
    L.append("Sector / industria: " + (" / ".join(x for x in (sector, industria) if x) or "no disponible") + (f" · País: {pais}" if pais else ""))
    if foso or etapa:
        L.append("Ventaja competitiva (foso) estimada: " + (foso or "no disponible") + " · Etapa de la empresa: " + (etapa or "no disponible"))
    L.append("")
    L.append("DESCRIPCIÓN DEL NEGOCIO (Yahoo Finance):")
    L.append((descripcion or "no disponible").strip())
    L.append("")
    if not any(est.get(k) for k in ("resultados", "balance", "flujo")):
        L.append("ESTADOS FINANCIEROS: no disponibles. No hagas análisis numérico; limitate a lo cualitativo y decilo en el resumen.")
        return "\n".join(L)
    L.append(f"ESTADOS FINANCIEROS (montos en millones de {moneda or 'la moneda de reporte'}; ganancia por acción en unidades; acciones en millones). TTM = últimos 12 meses.")
    for clave, nom in (("resultados", "Resultados"), ("balance", "Balance"), ("flujo", "Flujo de efectivo")):
        L += _tabla(est.get(clave), nom)
        L.append("")
    L += _tabla(est.get("ratios"), "Ratios calculados")
    L.append("")
    L.append("VARIACIONES Y COMPARACIONES CALCULADAS:")
    L += derivados(est)
    av = alertas(est, moneda)
    if av:
        L.append("")
        L.append("AVISOS DE DATOS:")
        L += [f"- {a}" for a in av]
    return "\n".join(L)


def armar_prompt(bloque, ruta=None):
    with open(ruta or RUTA_PROMPT, encoding="utf-8") as f:
        return f.read().replace("{BLOQUE_DATOS}", bloque)


# --- respuesta del modelo -----------------------------------------------------------------------------------------------------

def parsear_respuesta(texto):
    """Diccionario {'resumen', 'desarrollo': [{'titulo','texto'}], 'conclusion', 'riesgo_ia'} a partir de lo que contestó el modelo, o None si no es utilizable
    (sin JSON, sin resumen o sin conclusión, o sin ningún apartado del desarrollo)."""
    if not isinstance(texto, str):
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(t[i:j + 1])
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    resumen = str(d.get("resumen") or "").strip()
    concl = str(d.get("conclusion") or d.get("conclusión") or "").strip()
    sec = []
    for x in d.get("desarrollo") or []:
        if isinstance(x, dict) and str(x.get("titulo") or "").strip() and str(x.get("texto") or "").strip():
            sec.append({"titulo": str(x["titulo"]).strip(), "texto": str(x["texto"]).strip()})
    if not resumen or not concl or not sec:
        return None
    riesgo = str(d.get("riesgo_ia") or "").strip().lower()
    return {"resumen": resumen, "desarrollo": sec, "conclusion": concl, "riesgo_ia": riesgo if riesgo in RIESGOS_IA else ""}


# --- archivo ------------------------------------------------------------------------------------------------------------------

def cargar(ruta=None):
    """({TICKER: {...}}, fecha|None). ({}, None) si el archivo no está o no se puede leer."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            j = json.load(f)
        datos = {str(t).upper(): v for t, v in (j.get("datos") or {}).items() if isinstance(v, dict) and v.get("resumen")}
        return datos, (j.get("fecha") if isinstance(j.get("fecha"), str) else None)
    except Exception:  # noqa: BLE001
        return {}, None


def guardar(datos, fecha, ruta=None):
    with open(ruta or RUTA, "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha, "datos": datos}, f, ensure_ascii=False, indent=1)


def para_ficha(ticker, ruta=None):
    """El análisis de la empresa para mostrar en la ficha (con 'fecha' y 'modelo' propios), o None si no tiene."""
    datos, fecha = cargar(ruta)
    d = datos.get(str(ticker).upper())
    if not d:
        return None
    d = dict(d)
    d.setdefault("fecha", fecha)
    return d
