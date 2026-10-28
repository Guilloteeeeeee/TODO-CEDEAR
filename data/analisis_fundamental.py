"""Análisis Fundamental (v1.2.70): un informe breve de cada empresa, escrito al estilo de Pat Dorsey ("Las cinco reglas para invertir en acciones con éxito"): Resumen con
conclusión primero, los números de un vistazo, el negocio, el foso, los números, la deuda, la gerencia, puntos fuertes y débiles, qué vigilar y conclusión.

El FORMATO es el mismo para todas las empresas. Lo que cambia según el tipo de negocio (banco, seguro, inmobiliaria, servicios públicos, empresa joven, software...) lo elige
el programa solo (data/af_perfiles.py): qué filas lleva la tabla de números, cómo se llama la sección de deuda y qué guía de análisis recibe quien redacta.

Cómo funciona:
  1. La TABLA de números la arma el código con los estados financieros de Yahoo que ya guarda `data/paquetes_yahoo.json`. Nada se tipea a mano.
  2. El TEXTO lo redacta una persona o un asistente de IA a partir de `bloque_datos()` y las reglas de `data/prompt_analisis_fundamental.txt`, y se guarda en
     `data/analisis_fundamental.json` con `generar_analisis_fundamental.py --agregar archivo.json` (que valida el formato). No hace falta ninguna clave ni pago.
  3. La solapa "Análisis Fundamental" de la ficha muestra el texto, la tabla, el color de la calidad (escala de la valoración) y la aclaración de que es información,
     no una recomendación. Las FUENTES son siempre las mismas y las pone el código (FUENTES).
Las funciones de este módulo no tocan la red."""
import json
import os
import re

from data import af_perfiles as AP
from data import af_tablas as T

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(AQUI, "analisis_fundamental.json")
RUTA_PROMPT = os.path.join(AQUI, "prompt_analisis_fundamental.txt")
RIESGOS_IA = ("muy alto", "alto", "moderado", "bajo", "muy bajo")
# Calidad del negocio -> color (misma escala de colores que la Valoración, de verde a rojo)
CALIDADES = {"Excelente": "#15803d", "Muy buena": "#82b93f", "Buena": "#eab308", "Regular": "#f97316", "Pobre": "#dc2626"}
# Color de las LETRAS de la conclusión (versión más oscura de cada color de arriba, para que se lea sobre fondo blanco); la gente asocia el color con la calidad
CALIDADES_TEXTO = {"Excelente": "#15803d", "Muy buena": "#4d7c0f", "Buena": "#a16207", "Regular": "#c2410c", "Pobre": "#b91c1c"}
# Secciones de texto, en este orden: (clave, título). El título de "balance" depende del perfil (AP.titulo_balance).
SECCIONES = (("negocio", "El negocio"), ("foso", "La ventaja competitiva (foso)"), ("numeros", "Los números"), ("balance", "Deuda y solidez financiera"),
             ("gerencia", "Gerencia y uso del capital"))
# Calidad + valoración del modelo hoy -> una frase armada por el código (siempre vigente: el texto del informe habla de la calidad y no del precio, que cambia a diario)
_CRUCE = {
    ("alta", "barata"): "Calidad alta y precio por debajo de su Fair Value: puede ser una inversión que vale la pena analizar a fondo.",
    ("alta", "justa"): "Calidad alta a un precio razonable: una buena empresa que vale la pena tener en seguimiento.",
    ("alta", "cara"): "Calidad alta, pero el precio ya está por encima de su Fair Value: buena empresa a un precio exigente; mejor esperar una mejor oportunidad.",
    ("media", "barata"): "Calidad media con el precio por debajo de su Fair Value: el descuento compensa parte de sus límites, pero hay que revisar bien sus riesgos.",
    ("media", "justa"): "Calidad media a un precio razonable: nada sobresale, así que no hay apuro.",
    ("media", "cara"): "Calidad media y precio por encima de su Fair Value: lo que ofrece no justifica lo que cuesta hoy.",
    ("baja", "barata"): "Precio bajo, pero calidad débil: puede estar barata por una buena razón. Cuidado con las trampas de valor.",
    ("baja", "justa"): "Calidad débil a un precio razonable: no hay un motivo claro para elegirla.",
    ("baja", "cara"): "Calidad débil y precio por encima de su Fair Value: la peor combinación.",
}


def precio_vs_fv(precio, fair_value):
    """Frase con el precio de hoy contra el Fair Value estimado por múltiplos (con las cifras), o '' si falta alguno."""
    try:
        p, f = float(precio), float(fair_value)
    except (TypeError, ValueError):
        return ""
    if not (p > 0 and f > 0) or p != p or f != f:
        return ""
    d = (f - p) / p * 100
    fmt = lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(d) <= 0.5:
        return f"Hoy cotiza a US$ {fmt(p)}, en línea con su Fair Value estimado por múltiplos (US$ {fmt(f)})."
    if d > 0:
        return f"Hoy cotiza a US$ {fmt(p)}, por debajo de su Fair Value estimado por múltiplos (US$ {fmt(f)}): el Fair Value está {abs(d):.0f} % por encima del precio."
    return f"Hoy cotiza a US$ {fmt(p)}, por encima de su Fair Value estimado por múltiplos (US$ {fmt(f)}): el precio está {(p - f) / f * 100:.0f} % por encima del Fair Value."


def cruce(calidad, categoria):
    """Frase que combina la calidad del informe con la valoración de hoy (categoría de la app, por múltiplos), o '' si falta algún dato."""
    c = str(categoria or "").upper()
    if calidad not in CALIDADES or not c:
        return ""
    v = "barata" if "INFRAVALORADA" in c else "cara" if "SOBREVALORADA" in c else "justa" if "BIEN VALUADA" in c else ""
    q = "alta" if calidad in ("Excelente", "Muy buena") else "media" if calidad == "Buena" else "baja"
    return _CRUCE.get((q, v), "")


# Fuentes: las mismas para TODOS los análisis (decisión de Guille del 28/10/2026). Las pone el código; el texto no lleva fuentes propias.
FUENTES = ("Estados financieros (hasta 4 años fiscales y últimos 12 meses), descripción del negocio, dividendos y equipo directivo: Yahoo Finance.",
           "Base oficial de esas cifras: los informes que la empresa presenta ante la SEC, el 10-K (anual) y el 10-Q (trimestral); las empresas extranjeras presentan el 20-F y el 6-K. "
           "Si una cifra no coincide, manda el informe de la empresa.",
           "Ventaja competitiva (foso) y etapa de la empresa: estimación propia de TodoCedears.")
# Lugar de la lista donde va el link a los informes de la SEC (la línea de la base oficial)
FUENTE_SEC = 1


def link_sec(ticker):
    """Búsqueda de los informes de la empresa (10-K, 10-Q, 20-F, 6-K...) en EDGAR, el sitio oficial de la SEC."""
    t = re.sub(r"[^A-Za-z0-9.\-]", "", str(ticker or ""))
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={t}&owner=include&count=40" if t else ""


# Frases que NO pueden aparecer fuera de la conclusión: la calidad se juzga con los datos que hay; si falta un dato importante, solo se dice en la conclusión
# ("es recomendable investigar ...").
_FALTA_DATO = ("no hay datos", "no tenemos datos", "no tenemos los datos", "no contamos con datos", "sin datos para", "no se puede evaluar", "no se puede medir", "no se puede juzgar",
               "no se puede analizar", "de eso no tenemos", "no hay información", "no tenemos información", "no disponemos de")


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


def alertas(estados, moneda=None, perfil=None):
    """AVISOS DE DATOS: cosas raras o faltantes que el análisis tiene que mencionar como 'dato a verificar' en vez de apoyarse en ellas."""
    est = estados or {}
    av = []
    if moneda and str(moneda).upper() != "USD":
        av.append(f"Los estados financieros están en {moneda}, no en dólares: las cifras de este bloque están en esa moneda.")
    financiera = perfil in ("banco", "seguros", "mercados")
    if not financiera and not _serie(est, "resultados", "Gasto por intereses"):
        av.append("Gasto por intereses: no disponible en los datos guardados (se carga al volver a bajar los datos de Yahoo). No calcules la cobertura de intereses.")
    if not financiera and not _serie(est, "balance", "Deuda de largo plazo") and not _serie(est, "balance", "Deuda de corto plazo"):
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


def perfil_de(sector, industria, etapa, estados, foso=None, ticker=None, sector_app=None):
    """(perfil, capas) de la empresa (ver data/af_perfiles.py). `sector` e `industria` son los de Yahoo (en inglés)."""
    p = AP.perfil(sector, industria, etapa, estados, ticker, sector_app)
    return p, AP.capas(p, etapa, foso, estados)


def bloque_datos(ticker, nombre="", sector="", industria="", pais="", descripcion="", estados=None, foso=None, etapa=None, moneda=None, extra=None, sector_app=""):
    """Texto con todo lo que ve quien redacta. Nada se inventa: lo que falta dice 'no disponible'."""
    est = estados or {}
    moneda = moneda or est.get("moneda")
    perfil, capas = perfil_de(sector, industria, etapa, est, foso, ticker, sector_app)
    L = [f"EMPRESA: {nombre or ticker} ({ticker})"]
    L.append("Sector / industria: " + (sector_app + " (Yahoo: " if sector_app else "(") + (" / ".join(x for x in (sector, industria) if x) or "no disponible") + ")" + (f" · País: {pais}" if pais else ""))
    L.append("Ventaja competitiva (foso) estimada: " + (foso or "no disponible") + " · Etapa de la empresa: " + (etapa or "no disponible"))
    L.append(f"PERFIL DE ANÁLISIS (elegido por el programa): {AP.NOMBRE_PERFIL[perfil]}" + (" + " + " + ".join(capas) if capas else "") + f" · título de la sección de deuda: \"{AP.titulo_balance(perfil)}\"")
    L.append("")
    L.append("GUÍA PARA ESTE TIPO DE EMPRESA (qué mirar y qué no):")
    L.append(AP.guia(perfil, capas))
    L.append("")
    L.append("DESCRIPCIÓN DEL NEGOCIO (Yahoo Finance):")
    L.append((descripcion or "no disponible").strip())
    L.append("")
    if not any(est.get(k) for k in ("resultados", "balance", "flujo")):
        L.append("ESTADOS FINANCIEROS: no disponibles. No hagas análisis numérico; limitate a lo cualitativo y decilo en el resumen.")
        return "\n".join(L)
    L.append("LA TABLA 'LOS NÚMEROS DE UN VISTAZO' QUE VA A VER EL LECTOR (usá estas cifras tal cual):")
    L.append(AP.vistazo_texto(est, perfil))
    L.append("")
    L.append("DETALLE PARA TU ANÁLISIS (las cifras y los CAGR ya están calculados, usalos tal cual; el lector ve el detalle completo en otra solapa):")
    L.append(T.bloque_texto(est, AP.CLAVES_DETALLE.get(perfil)))
    L += _bloque_extra(extra)
    av = alertas(est, moneda, perfil)
    if av:
        L.append("")
        L.append("AVISOS DE DATOS:")
        L += [f"- {a}" for a in av]
    return "\n".join(L)


def _bloque_extra(extra):
    """Líneas con dividendos y gerencia (de paquetes_yahoo.json: 'dividendos' y 'gobierno'), si están. Sin datos no agrega nada."""
    ex = extra or {}
    out = []
    dv = ex.get("dividendos") or {}
    if dv.get("tasa_anual") is not None:
        tr = dv.get("trayectoria") or {}
        cg = tr.get("cagr") or {}
        tasa = _es("%.2f" % float(dv["tasa_anual"]))
        partes = [f"dividendo anual actual {tasa} por acción"]
        if tr.get("anios_pagando"):
            partes.append(f"paga desde {tr.get('primer_anio')} ({tr['anios_pagando']} años)")
        for k, r in ((3, "3 años"), (10, "10 años")):
            v = cg.get(k, cg.get(str(k)))
            if v is not None:
                partes.append(f"crecimiento anual compuesto del dividendo a {r}: {_fmt(v, 'pct')}")
        out += ["", "DIVIDENDOS (Yahoo): " + "; ".join(partes) + "."]
    gb = (ex.get("gobierno") or {}).get("directivos") or []
    if gb:
        out += ["", "EQUIPO DIRECTIVO (Yahoo; edad y pago anual en dólares si figuran):"]
        for d in gb[:5]:
            edad = ", %d años" % int(d["edad"]) if d.get("edad") else ""
            pago = ", pago %s M" % _es("%.1f" % (d["pago"] / 1e6)) if d.get("pago") else ""
            out.append(f"- {d.get('nombre', '').strip()} — {d.get('cargo', '')}{edad}{pago}")
    ag = (ex.get("agenda") or {}).get("resultados")
    if ag and ag[0]:
        out += ["", f"PRÓXIMOS RESULTADOS (Yahoo): {str(ag[0]).replace('d:', '')}."]
    return out


def armar_prompt(bloque, ruta=None):
    with open(ruta or RUTA_PROMPT, encoding="utf-8") as f:
        return f.read().replace("{BLOQUE_DATOS}", bloque)


# --- respuesta del modelo -----------------------------------------------------------------------------------------------------

def _txt(x):
    return str(x or "").strip()


def _lista(x):
    return [_txt(i) for i in (x if isinstance(x, list) else []) if _txt(i)]


def validar(d, estados=None):
    """(análisis limpio | None, [problemas]). Esquema v3 (el mismo para todas las empresas):
      resumen: abstract de la empresa que TERMINA con su conclusión (postura sin recomendar)
      calidad: Excelente | Muy buena | Buena | Regular | Pobre      (calidad del NEGOCIO; decide el color)
      veredicto: frase corta con la postura (ej.: "Excelente empresa; conviene mirarla a precios adecuados")
      riesgo_ia: muy alto | alto | moderado | bajo | muy bajo
      negocio, foso, numeros, balance, gerencia: texto (párrafos separados por una línea en blanco)
      fortalezas, debilidades: listas (las debilidades, de la más a la menos importante)
      ideal_para (2 a 4) y menos_ideal (1 a 3): perfiles de inversor a los que les encaja / no les encaja (siguen "Ideal para inversores que..."), sin recomendar
      vigilar: lista de 3 a 4 puntos con la forma "INDICADOR: por qué importa y qué señal mirar" (qué mirar, y después de los dos puntos el porqué); conclusion: 3 a 4 oraciones
      clientes: lista de 1 a 8 principales clientes ("Nombre (TICKER)" si cotiza y está en la app, o una descripción corta); se muestran con links al final de "El negocio"
      perfil, capas, ticker: los pone el programa (si vienen, se validan)"""
    pr = []
    if not isinstance(d, dict):
        return None, ["no es un objeto JSON"]
    out = {k: _txt(d.get(k)) for k in ("resumen", "veredicto", "conclusion")}
    out["conclusion"] = out["conclusion"] or _txt(d.get("conclusión"))
    for k in ("resumen", "conclusion"):                      # v1.2.72: el veredicto ya no se muestra (queda como dato opcional)
        if not out[k]:
            pr.append(f"falta '{k}'")
    rs = out["resumen"]
    if rs:
        if "Conclusión:" not in rs:
            pr.append("el 'resumen' tiene que terminar con \"Conclusión: ...\" (una oración que se la juega sobre la calidad)")
        if "foso" not in rs.lower():
            pr.append("el 'resumen' tiene que nombrar el foso (Amplio, Estrecho o sin foso)")
        if "inteligencia artificial" not in rs.lower():
            pr.append("el 'resumen' tiene que decir, con palabras claras, el riesgo de que la inteligencia artificial perjudique el negocio en 10 años")
        if rs.count("**") < 4:
            pr.append("el 'resumen' tiene que resaltar en **negrita** lo más importante (al menos 2 frases)")
    cal = _txt(d.get("calidad")).capitalize()
    out["calidad"] = cal if cal in CALIDADES else ""
    if not out["calidad"]:
        pr.append("'calidad' tiene que ser: " + " | ".join(CALIDADES))
    r = _txt(d.get("riesgo_ia")).lower()
    out["riesgo_ia"] = r if r in RIESGOS_IA else ""
    if not out["riesgo_ia"]:
        pr.append("'riesgo_ia' tiene que ser: " + " | ".join(RIESGOS_IA))
    for c, _ in SECCIONES:
        out[c] = _txt(d.get(c))
        if len(out[c]) < 80:
            pr.append(f"falta '{c}' (o es demasiado corto)")
    if len(out["veredicto"]) > 140:
        pr.append("'veredicto' tiene que ser una frase corta (hasta 140 caracteres)")
    out["fortalezas"], out["debilidades"], out["vigilar"] = _lista(d.get("fortalezas")), _lista(d.get("debilidades")), _lista(d.get("vigilar"))
    if len(out["fortalezas"]) < 2:
        pr.append("'fortalezas' necesita al menos 2")
    if len(out["debilidades"]) < 2:
        pr.append("'debilidades' necesita al menos 2")
    if not 2 <= len(out["vigilar"]) <= 5:
        pr.append("'vigilar' necesita de 2 a 5 puntos (lo ideal: 3 o 4)")
    for x in out["vigilar"]:
        if not re.match(r"^[^:]{3,60}:\s+\S", x):
            pr.append("cada punto de 'vigilar' tiene que tener la forma \"INDICADOR: por qué importa y qué señal mirar\" (qué mirar, dos puntos y el porqué)")
            break
    out["clientes"] = _lista(d.get("clientes"))
    if not 1 <= len(out["clientes"]) <= 8:
        pr.append("'clientes' necesita de 1 a 8 principales clientes (\"Nombre (TICKER)\" si cotiza, o una descripción corta; si no hay un cliente dominante, decilo)")
    cn = re.sub(r"^\*{0,2}Conclusión:\s*", "", rs[rs.rfind("Conclusión:"):].replace("**", "")).strip() if "Conclusión:" in rs else ""
    if cn and len(cn.split()) < 22:
        pr.append("la oración \"Conclusión:\" del resumen tiene que cerrar la idea: si nombra un riesgo, decí qué pasaría con la empresa si ocurre (impacto en ingresos, márgenes, caja...)")
    if cn and len(cn.split()) > 45:
        pr.append("la oración \"Conclusión:\" del resumen es solo una conclusión: una oración de hasta 45 palabras (calidad, puntos fuertes, riesgo y su consecuencia en una frase corta, sin explicar el porqué)")
    out["ideal_para"], out["menos_ideal"] = _lista(d.get("ideal_para")), _lista(d.get("menos_ideal"))
    if not 2 <= len(out["ideal_para"]) <= 4:
        pr.append("'ideal_para' necesita de 2 a 4 ideas (cada una sigue la frase \"Ideal para inversores que...\")")
    if not 1 <= len(out["menos_ideal"]) <= 3:
        pr.append("'menos_ideal' necesita de 1 a 3 ideas (cada una sigue la frase \"Menos adecuada para inversores que...\")")
    for x in out["ideal_para"] + out["menos_ideal"]:
        if len(x) > 220:
            pr.append("cada idea de 'ideal_para' / 'menos_ideal' tiene que ser corta (hasta 220 caracteres)")
            break
    sin_conclusion = " ".join(str(v) for k, v in d.items() if k not in ("conclusion", "conclusión")).lower()
    falta = [w for w in _FALTA_DATO if w in sin_conclusion]
    if falta:
        pr.append("no digas que faltan datos fuera de la 'conclusion' (" + ", ".join(falta) + "): juzgá con los datos que hay; si falta uno importante, en la 'conclusion' escribí que es recomendable investigarlo")
    prohibidas = [w for w in ("Morningstar", "recomendamos comprar", "te recomendamos", "precio objetivo", "bloque", "datos guardados", "lo único que no sabemos", "según el modelo") if w.lower() in " ".join(str(x) for x in d.values()).lower()]
    if prohibidas:
        pr.append("el texto menciona algo que no corresponde: " + ", ".join(prohibidas))
    pf = _txt(d.get("perfil"))
    out["perfil"] = pf if pf in AP.PERFILES else "general"
    out["capas"] = [c for c in _lista(d.get("capas")) if c in ("compounder", "ciclica")]
    if _txt(d.get("ticker")):
        out["ticker"] = _txt(d.get("ticker")).upper()
    return (None if pr else out), pr


def parsear_respuesta(texto, estados=None):
    """Análisis validado a partir del texto (JSON, con o sin ```), o None si no sirve. Para ver los problemas: `validar(json.loads(...))`."""
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
    return validar(d, estados)[0]


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
    d.setdefault("ticker", str(ticker).upper())
    return d
