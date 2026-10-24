"""
Baja de Yahoo Finance los datos de la ficha de cada empresa y los guarda en data/fichas.json (v1.2.47).

Para cada una de las empresas del cache pide a Yahoo: descripcion del negocio, CEO, sitio web, empleados, mercado donde cotiza, sector e industria
(en ingles, solo para comparar), valor de empresa, acciones en circulacion, ingresos de los ultimos 12 meses y crecimiento (ultimo trimestre y
promedio anual de 3 años, si hay datos). La descripcion se traduce al castellano con el traductor gratuito de Google (paquete deep-translator);
es traduccion automatica y puede tener errores: el original en ingles queda guardado en el mismo archivo. Si el traductor no esta o falla, queda
solo el original y la pagina lo muestra en ingles avisando.

Uso:  python bajar_fichas.py        (o doble clic en bajar_fichas.bat). Tarda unos minutos (una consulta por empresa, con pausas para que Yahoo no frene).
Si se corta o Yahoo frena, se puede correr de nuevo: lo que ya se bajo se conserva y solo se reintentan las que faltan.
Despues subir data/fichas.json a GitHub junto con el cache. Escribe tambien resultados_fichas.txt (resumen y avisos); mandamelo si algo no cierra.
"""
import json
import os
import re
import sys
import time
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from config.mercados import ADR, mercado_texto  # noqa: E402

SALIDA = os.path.join(AQUI, "data", "fichas.json")
PAUSA = 0.6
HONORIFICOS = re.compile(r"^(mr|mrs|ms|miss|dr|prof|sir|dame)\.?\s+", re.I)


def _num(x):
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _ceo(info):
    for o in info.get("companyOfficers") or []:
        t = str(o.get("title") or "").lower()
        if "chief executive" in t or re.search(r"\bceo\b", t):
            n = HONORIFICOS.sub("", str(o.get("name") or "").strip())
            if n:
                return n
    return None


def _cagr(df, fila, años=3):
    """Crecimiento anual compuesto de una fila de un estado anual de yfinance (columnas = ejercicios, de la mas nueva a la mas vieja)."""
    try:
        if df is None or fila not in df.index:
            return None
        v = [_num(x) for x in df.loc[fila].tolist()]
        if len(v) <= años or v[0] is None or v[años] is None or v[0] <= 0 or v[años] <= 0:
            return None
        return (v[0] / v[años]) ** (1.0 / años) - 1
    except Exception:  # noqa: BLE001
        return None


def _traducir(texto):
    """Traduccion al castellano con deep-translator (Google), por partes de hasta ~4000 letras cortadas en fin de oracion; None si no se pudo."""
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        return None
    try:
        partes, actual = [], ""
        for frase in re.split(r"(?<=[.!?])\s+", texto.strip()):
            if len(actual) + len(frase) + 1 > 4000 and actual:
                partes.append(actual)
                actual = ""
            actual = (actual + " " + frase).strip()
        if actual:
            partes.append(actual)
        tr = GoogleTranslator(source="en", target="es")
        out = [tr.translate(p) for p in partes]
        return " ".join(x for x in out if x).strip() or None
    except Exception:  # noqa: BLE001
        return None


def bajar_una(t):
    import yfinance as yf
    tk = yf.Ticker(t)
    info = tk.info or {}
    if not info or not (info.get("longBusinessSummary") or info.get("longName") or info.get("shortName")):
        return None
    d = {
        "descripcion_en": (info.get("longBusinessSummary") or "").strip() or None,
        "ceo": _ceo(info), "web": info.get("website"), "empleados": info.get("fullTimeEmployees"),
        "ciudad": info.get("city"), "region": info.get("state"), "pais": info.get("country"),
        "mercado_cod": info.get("exchange"), "mercado_nombre": info.get("fullExchangeName"),
        "sector_yahoo": info.get("sector"), "industria_yahoo": info.get("industry"),
        "ev": _num(info.get("enterpriseValue")), "acciones": _num(info.get("sharesOutstanding")),
        "ingresos_ttm": _num(info.get("totalRevenue")),
        "crec_ingresos_trim": _num(info.get("revenueGrowth")), "crec_ganancias_trim": _num(info.get("earningsGrowth")),
    }
    try:
        est = tk.income_stmt
        d["cagr_ingresos_3a"] = _cagr(est, "Total Revenue")
        d["cagr_eps_3a"] = _cagr(est, "Diluted EPS")
    except Exception:  # noqa: BLE001
        pass
    return {k: v for k, v in d.items() if v not in (None, "")}


def main():
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    tickers = sorted(r["ticker"] for r in cache)
    pais_cache = {r["ticker"]: r.get("pais") for r in cache}
    previo = {}
    if os.path.exists(SALIDA):
        try:
            previo = json.load(open(SALIDA, encoding="utf-8")).get("datos", {})
        except Exception:  # noqa: BLE001
            previo = {}
    datos = dict(previo)
    avisos, ok = [], 0
    try:
        from deep_translator import GoogleTranslator  # noqa: F401
        traductor = True
    except ImportError:
        traductor = False
        avisos.append("deep-translator no esta instalado: las descripciones quedan en ingles (pip install deep-translator)")
    print(f"Bajando la ficha de {len(tickers)} empresas (una por una, con pausa)...")
    for i, t in enumerate(tickers, 1):
        if datos.get(t, {}).get("descripcion_en") and datos.get(t, {}).get("mercado_cod"):
            ok += 1
            continue                      # ya estaba completa (corrida anterior)
        try:
            d = bajar_una(t)
        except Exception as e:  # noqa: BLE001
            d = None
            avisos.append(f"{t}: Yahoo no respondio ({type(e).__name__})")
        if not d:
            avisos.append(f"{t}: sin datos de Yahoo")
            time.sleep(PAUSA)
            continue
        if traductor and d.get("descripcion_en") and not datos.get(t, {}).get("descripcion_es"):
            es = _traducir(d["descripcion_en"])
            if es:
                d["descripcion_es"] = es
            else:
                avisos.append(f"{t}: no se pudo traducir la descripcion")
        datos[t] = {**datos.get(t, {}), **d}
        ok += 1
        print(f"  {i:3d}/{len(tickers)} {t:6} ok  {datos[t].get('mercado_cod', '?'):4} {(datos[t].get('ceo') or '—')[:28]}")
        if i % 10 == 0:                      # guarda de a poco, por si se corta
            _guardar(datos)
        time.sleep(PAUSA)
    _guardar(datos)
    # Controles de coherencia (no cambian nada: solo avisan)
    for t in tickers:
        f = datos.get(t) or {}
        m = mercado_texto(f.get("mercado_cod")) or mercado_texto(f.get("mercado_nombre"))
        pais = f.get("pais") or pais_cache.get(t)
        if m in ("NYSE", "Nasdaq") and pais and pais != "United States" and t not in ADR:
            avisos.append(f"{t}: empresa de {pais} que cotiza en {m} y NO esta en la lista de ADR (config/mercados.py): revisar si es ADR")
        if t in ADR and pais == "United States":
            avisos.append(f"{t}: figura como ADR pero Yahoo dice que es de Estados Unidos: revisar")
        if t in ADR and f and not m:
            avisos.append(f"{t}: figura como ADR y Yahoo no informo el mercado")
    faltan = [t for t in tickers if not datos.get(t, {}).get("descripcion_en")]
    texto = [f"Fichas bajadas: {ok} de {len(tickers)}. Sin descripcion: {len(faltan)} {faltan[:30]}", ""] + [f"- {a}" for a in avisos]
    print("\n" + "\n".join(texto))
    with open(os.path.join(AQUI, "resultados_fichas.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\nListo. Se guardo data/fichas.json (subilo a GitHub) y resultados_fichas.txt")


def _guardar(datos):
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"fecha": datetime.now().strftime("%d/%m/%Y"), "datos": datos}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
