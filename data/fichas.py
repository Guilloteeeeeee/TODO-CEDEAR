"""
Datos de la ficha de cada empresa (v1.2.47): descripcion, CEO, sitio web, empleados, mercado donde cotiza, valor de empresa, acciones en
circulacion, ingresos y crecimiento. Salen de Yahoo Finance y se guardan en data/fichas.json, que arma bajar_fichas.py (doble clic en
bajar_fichas.bat en la PC, una vez por trimestre junto con el cache; tarda unos minutos). Asi la pagina no depende de que Yahoo responda en el
momento (Yahoo suele frenar a los servidores en la nube).

Formato de data/fichas.json:  {"fecha": "dd/mm/aaaa", "datos": {"AAPL": {campo: valor, ...}, ...}}  con estos campos (todos opcionales):
    descripcion_es    resumen del negocio en castellano (traduccion automatica hecha al armar el archivo; puede tener errores)
    descripcion_en    el texto original de Yahoo (en ingles)
    ceo, web, empleados, ciudad, region, pais
    mercado_cod       codigo de Yahoo del mercado (NMS, NYQ...)        mercado_nombre   nombre largo de Yahoo ("NasdaqGS")
    sector_yahoo, industria_yahoo     (en ingles; solo para comparar con config/industrias.py)
    ev, acciones, ingresos_ttm        en unidades (dolares / acciones)
    crec_ingresos_trim, crec_ganancias_trim     crecimiento del ultimo trimestre contra el mismo de hace un año (fraccion: 0.12 = 12 %)
    cagr_ingresos_3a, cagr_eps_3a    crecimiento anual compuesto de los ultimos 3 años (fraccion), si hubo datos para calcularlo
Si el archivo no esta o una empresa no figura, la pagina muestra lo que si tiene (nunca inventa un dato) y el mercado se pide a Yahoo en el momento.
"""
import json
import os
import threading

from config.mercados import es_adr, mercado_texto

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas.json")


def cargar(archivo=None):
    """({TICKER: {campo: valor}}, fecha_texto o None). Archivo ausente o roto -> ({}, None); nunca levanta excepciones."""
    ruta = archivo or ARCHIVO
    try:
        if not os.path.exists(ruta):
            return {}, None
        with open(ruta, encoding="utf-8") as f:
            j = json.load(f)
        datos = j.get("datos") if isinstance(j, dict) else None
        if not isinstance(datos, dict):
            return {}, None
        return {str(k).upper(): v for k, v in datos.items() if isinstance(v, dict)}, (j.get("fecha") if isinstance(j.get("fecha"), str) else None)
    except Exception:  # noqa: BLE001
        return {}, None


def mercado_en_vivo(ticker, timeout=6.0, obtener=None):
    """Codigo del mercado segun Yahoo (liviano: la misma consulta que el precio) o None. Con tope de tiempo; nunca levanta excepciones."""
    res = {}

    def _pedir():
        try:
            if obtener is not None:
                res["v"] = obtener(ticker)
                return
            import yfinance as yf
            fi = yf.Ticker(str(ticker)).fast_info
            res["v"] = fi["exchange"]
        except Exception:  # noqa: BLE001
            res["v"] = None

    h = threading.Thread(target=_pedir, daemon=True)
    h.start()
    h.join(timeout)
    v = res.get("v")
    return v if isinstance(v, str) and v.strip() else None


def ficha_en_vivo(ticker, timeout=12.0, obtener=None, traducir=True):
    """v1.2.52: ficha de Yahoo pedida en el momento, para las empresas que no estan en data/fichas.json (mismos campos que arma bajar_fichas.py, sin el
    crecimiento anual). La descripcion se traduce al castellano si el paquete deep-translator esta instalado; si no, queda en ingles. {} si Yahoo no
    responde; nunca levanta excepciones. `obtener(ticker)` -> dict `info` de Yahoo, para las pruebas."""
    res = {}

    def _pedir():
        try:
            if obtener is not None:
                res["v"] = obtener(ticker)
                return
            import yfinance as yf
            res["v"] = yf.Ticker(str(ticker)).info
        except Exception:  # noqa: BLE001
            res["v"] = None

    h = threading.Thread(target=_pedir, daemon=True)
    h.start()
    h.join(timeout)
    info = res.get("v")
    if not isinstance(info, dict) or not (info.get("longBusinessSummary") or info.get("longName") or info.get("shortName")):
        return {}
    import re

    def _num(x):
        try:
            v = float(x)
            return v if v == v and abs(v) != float("inf") else None
        except (TypeError, ValueError):
            return None

    ceo = None
    for o in info.get("companyOfficers") or []:
        t = str(o.get("title") or "").lower()
        if "chief executive" in t or re.search(r"\bceo\b", t):
            n = re.sub(r"^(mr|mrs|ms|miss|dr|prof|sir|dame)\.?\s+", "", str(o.get("name") or "").strip(), flags=re.I)
            if n:
                ceo = n
                break
    d = {"descripcion_en": (info.get("longBusinessSummary") or "").strip() or None, "ceo": ceo, "web": info.get("website"),
         "empleados": info.get("fullTimeEmployees"), "ciudad": info.get("city"), "region": info.get("state"), "pais": info.get("country"),
         "mercado_cod": info.get("exchange"), "mercado_nombre": info.get("fullExchangeName"),
         "ev": _num(info.get("enterpriseValue")), "acciones": _num(info.get("sharesOutstanding")), "ingresos_ttm": _num(info.get("totalRevenue")),
         "crec_ingresos_trim": _num(info.get("revenueGrowth")), "crec_ganancias_trim": _num(info.get("earningsGrowth"))}
    d = {k: v for k, v in d.items() if v not in (None, "")}
    if traducir and d.get("descripcion_en"):
        try:
            from deep_translator import GoogleTranslator
            partes, actual = [], ""
            for frase in re.split(r"(?<=[.!?])\s+", d["descripcion_en"]):
                if len(actual) + len(frase) + 1 > 4000 and actual:
                    partes.append(actual)
                    actual = ""
                actual = (actual + " " + frase).strip()
            if actual:
                partes.append(actual)
            tr = GoogleTranslator(source="en", target="es")
            es = " ".join(x for x in (tr.translate(p) for p in partes) if x).strip()
            if es:
                d["descripcion_es"] = es
        except Exception:  # noqa: BLE001
            pass
    return d


def mercado_y_adr(ticker, ficha=None, codigo_en_vivo=None):
    """(texto del mercado o None, es_adr) para mostrar en la ficha: 'NYSE', 'Nasdaq'... y, si es ADR, True. El mercado sale de la ficha de
    Yahoo (data/fichas.json) y, si no esta, del codigo pedido en el momento."""
    ficha = ficha or {}
    m = mercado_texto(ficha.get("mercado_cod")) or mercado_texto(ficha.get("mercado_nombre")) or mercado_texto(codigo_en_vivo)
    return m, es_adr(ticker)


def texto_mercado(ticker, ficha=None, codigo_en_vivo=None):
    """'NYSE · ADR', 'Nasdaq', o None si no se sabe el mercado."""
    m, adr = mercado_y_adr(ticker, ficha, codigo_en_vivo)
    if not m:
        return None
    return f"{m} · ADR" if adr else m
