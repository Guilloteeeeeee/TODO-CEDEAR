"""
Prueba de ROE y recompras de acciones (v1.2.30; v1.2.31 corrige la lectura de la tabla de ROE). SOLO TRAE DATOS: no cambia ningun puntaje ni el cache.

Para cada empresa baja UNA pagina de Stock Analysis (la misma de ratios anuales que ya usa generar_cache) y
guarda, con su historia de hasta 5 anios fiscales, estas filas:
    ROE (Return on Equity), ROIC, Buyback Yield / Dilution (recompras netas de nuevas acciones),
    Payout Ratio, Dividend Yield, PB Ratio y PE Ratio.
Con eso se puede probar, aparte y sin tocar la app, (1) si ajustar el P/B de los bancos por su ROE cambia
el resultado y (2) si sumar las recompras al dividendo cambia el resultado.

Uso (desde la carpeta del proyecto):
    python probar_roe_recompras.py              (todas las empresas, unos 5 a 10 minutos)
    python probar_roe_recompras.py JPM BAC C    (solo esas)
    python probar_roe_recompras.py bancos       (solo las 22 de Bancos y seguros, 2 o 3 minutos)

Trato con el sitio: igual que generar_cache (respeta robots.txt, una pagina a la vez con pausa, se detiene si
lo bloquean). Se guarda de a poco, asi que si se corta queda lo ya bajado.

Guarda dos archivos: resultados_roe_recompras.json (los datos) y resultados_roe_recompras.txt (resumen).
Mandalos para revisarlos.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import stockanalysis as sa

# nombre -> (palabras que debe tener la etiqueta (sin espacios, en minuscula), palabras que no)
FILAS = {
    "roe":            (["returnonequity"], []),
    "roic":           (["roic"], []),
    "recompras":      (["buybackyield"], []),
    "payout":         (["payoutratio"], []),
    "dividend_yield": (["dividendyield"], []),
    "p_b":            (["pbratio"], []),
    "per":            (["peratio"], ["forward"]),
}

# v1.2.31: la pagina trae 4 tablas (Total Valuation, Price Ratios, Financial Efficiency, Yields) y el lector
# se queda solo con las que tienen alguna de estas palabras en sus filas. En la v1.2.30 faltaban las de ROE/ROIC,
# por eso el ROE no se bajo. Ahora hay una palabra por cada tabla que interesa.
PALABRAS_TABLAS = ["PE Ratio", "PB Ratio", "Return on Equity", "ROIC", "Dividend Yield", "Buyback"]

SALIDA_JSON = "resultados_roe_recompras.json"
SALIDA_TXT = "resultados_roe_recompras.txt"


def extraer_filas(tabla: dict) -> dict:
    """
    tabla: {etiqueta_de_fila: {encabezado_de_columna: valor}} (salida del lector de Stock Analysis).
    Devuelve {nombre: {"etiqueta": str, "actual": float|None, "anios": {2025: valor, ...}}} solo con las filas que existen.
    """
    salida = {}
    for nombre, (claves, excluir) in FILAS.items():
        etiqueta = sa._find_label(tabla, *claves, exclude=excluir)
        if not etiqueta:
            continue
        actual, anios = None, {}
        for columna, valor in tabla[etiqueta].items():
            if sa._es_columna_actual(columna):
                actual = valor
            else:
                anio = sa._anio_columna(columna)
                if anio is not None:
                    anios[anio] = valor
        salida[nombre] = {"etiqueta": etiqueta, "actual": actual, "anios": dict(sorted(anios.items(), reverse=True))}
    return salida


def bajar(ticker: str, session=None) -> dict:
    """Baja la pagina de ratios de un ticker y devuelve {"ok": bool, "filas": {...}, "error": str|None}."""
    url = f"https://stockanalysis.com/stocks/{ticker.lower().replace('.', '-')}/financials/ratios/?p=annual"
    time.sleep(sa.REQUEST_DELAY)
    html = sa._fetch_html(url, session)
    if not html:
        return {"ok": False, "filas": {}, "error": "no se pudo bajar la pagina" + (f" ({sa.ULTIMO_ERROR})" if sa.ULTIMO_ERROR else "")}
    tabla = sa._parse_page(html, PALABRAS_TABLAS)
    if not tabla:
        sa._FALLOS_LECTURA += 1
        return {"ok": False, "filas": {}, "error": "la pagina se bajo pero no se pudo leer la tabla"}
    sa._FALLOS_LECTURA = 0
    filas = extraer_filas(tabla)
    if "roe" not in filas:
        # por si la ruta por JSON embebido devolvio una sola tabla: se vuelve a leer todo el HTML
        extra = sa._parse_html_table(html, PALABRAS_TABLAS)
        if extra:
            tabla = {**extra, **tabla}
            filas = extraer_filas(tabla)
    return {"ok": bool(filas), "filas": filas, "etiquetas": list(tabla)[:120],
            "error": None if filas else "la tabla no trae ninguna de las filas buscadas"}


def _fmt(v, d=1):
    return "—" if v is None else f"{v:,.{d}f}"


def _serie(fila, d=1):
    if not fila:
        return "no hay fila"
    anios = fila["anios"]
    return f"hoy {_fmt(fila['actual'], d)} | " + ", ".join(f"{a}: {_fmt(v, d)}" for a, v in anios.items())


def resumen(resultados: dict) -> list:
    lineas = ["ROE y recompras desde Stock Analysis (numeros en %, salvo P/B y PER)", ""]
    sin_pagina, sin_roe, sin_recompras = [], [], []
    for t, r in resultados.items():
        if not r["ok"]:
            sin_pagina.append(f"{t} ({r['error']})")
            continue
        f = r["filas"]
        if "roe" not in f:
            sin_roe.append(t)
        if "recompras" not in f:
            sin_recompras.append(t)
        lineas.append(f"== {t}")
        for nombre, rotulo in (("roe", "ROE"), ("recompras", "Recompras netas"), ("payout", "Payout"),
                               ("dividend_yield", "Dividendo"), ("p_b", "P/B")):
            lineas.append(f"   {rotulo:16s}: {_serie(f.get(nombre), 2 if nombre == 'p_b' else 1)}")
    lineas += ["", f"Empresas leidas: {sum(1 for r in resultados.values() if r['ok'])} de {len(resultados)}"]
    if sin_pagina:
        lineas.append("Sin pagina o sin tabla: " + ", ".join(sin_pagina))
    if sin_roe:
        lineas.append("Sin fila de ROE: " + ", ".join(sin_roe))
    if sin_recompras:
        lineas.append("Sin fila de recompras: " + ", ".join(sin_recompras))
    for t, r in resultados.items():
        if r.get("etiquetas"):
            lineas += ["", f"Filas que trae la pagina de {t} (para revisar los nombres): " + " | ".join(r["etiquetas"])]
            break
    return lineas


def _guardar(resultados: dict):
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False)
    with open(SALIDA_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(resumen(resultados)))


def main(tickers):
    import requests
    print("=" * 44)
    print("  ROE y recompras (solo trae datos)")
    print("=" * 44)
    print(f"{len(tickers)} empresas. Una pagina por empresa, con pausa. Esperá...\n")
    s = requests.Session()
    resultados = {}
    for i, t in enumerate(tickers, 1):
        try:
            r = bajar(t, s)
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "filas": {}, "error": f"{type(e).__name__}: {e}"}
        resultados[t] = r
        print(f"[{i}/{len(tickers)}] {t}: " + ("ok" if r["ok"] else f"NO ({r['error']})"))
        if i % 20 == 0:
            _guardar(resultados)
        if not sa.sa_disponible():
            print("\nStock Analysis se dejo de consultar (bloqueos o paginas ilegibles seguidas). Se guarda lo que haya.")
            break
    _guardar(resultados)
    print(f"\nListo. Guardé {SALIDA_JSON} y {SALIDA_TXT}. Mandalos para revisarlos.")


def lista_desde_args(args):
    """Sin argumentos: todas las empresas. "bancos": solo las de Bancos y seguros. Si no, los tickers que se pasen."""
    from config.sectors import TICKER_UNIVERSE
    if args and args[0].lower() == "bancos":
        return list(TICKER_UNIVERSE.get("Bancos y seguros", []))
    if args:
        return [a.upper() for a in args]
    return [t for ts in TICKER_UNIVERSE.values() for t in ts]


if __name__ == "__main__":
    main(lista_desde_args(sys.argv[1:]))
