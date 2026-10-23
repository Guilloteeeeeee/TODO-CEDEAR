"""
Prueba de P/S (precio / ventas) y otros multiplos de la misma pagina. SOLO TRAE DATOS: no cambia ningun puntaje ni el cache.

Para cada empresa baja UNA pagina de Stock Analysis (la misma de ratios anuales que ya usa generar_cache y que
ya se uso para el ROE) y guarda, con su historia de hasta 5 anios fiscales, estas filas:
    PS Ratio (P/S), EV/Sales, Forward PE, PE Ratio, P/FCF, P/OCF, EV/EBITDA, PEG, P/B, FCF Yield.
Con eso se puede probar, aparte y sin tocar la app, si el P/S (o EV/Sales) ayuda a ordenar mejor las empresas de
Semiconductores y Hardware (donde el PEG hoy no se parece a GuruFocus) y si sirve en otros sectores.

IMPORTANTE: correrlo HOY o MANANA. La lista de GuruFocus que paso Guille es del 23/10/2026 y los precios se
mueven: cuanto mas tarde se baje, menos comparable queda. El script anota la fecha y hora de cada descarga.

Uso (desde la carpeta del proyecto):
    python probar_ps.py                (todas las empresas, unos 5 a 10 minutos)
    python probar_ps.py NVDA AMD INTC  (solo esas)
    python probar_ps.py bancos         (solo las de Bancos y seguros)

Trato con el sitio: igual que generar_cache (respeta robots.txt, una pagina a la vez con pausa, se detiene si
lo bloquean). Se guarda de a poco, asi que si se corta queda lo ya bajado.

Guarda dos archivos: resultados_ps.json (los datos) y resultados_ps.txt (resumen). Mandalos para revisarlos.
"""
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import stockanalysis as sa

# nombre -> (palabras que debe tener la etiqueta (sin espacios, en minuscula), palabras que no)
FILAS = {
    "ps":         (["psratio"], []),
    "ev_sales":   (["ev/sales"], []),
    "forward_pe": (["forwardpe"], []),
    "per":        (["peratio"], ["forward"]),
    "p_fcf":      (["p/fcf"], []),
    "p_ocf":      (["p/ocf"], []),
    "ev_ebitda":  (["ev/ebitda"], []),
    "peg":        (["pegratio"], []),
    "p_b":        (["pbratio"], []),
    "fcf_yield":  (["fcfyield"], []),
    "mkt_cap":    (["marketcap"], []),
}

# La pagina trae varias tablas y el lector se queda solo con las que tienen alguna de estas palabras en sus filas.
# Hay una palabra por cada tabla que interesa (la de multiplos y la de rendimientos).
PALABRAS_TABLAS = ["PS Ratio", "PE Ratio", "EV/Sales", "Forward PE", "PEG Ratio", "FCF Yield", "Market Cap"]

# Filas que tienen que estar para dar la empresa por leida
FILAS_CLAVE = ("ps",)

SALIDA_JSON = "resultados_ps.json"
SALIDA_TXT = "resultados_ps.txt"


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
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if not html:
        return {"ok": False, "filas": {}, "bajado": ahora,
                "error": "no se pudo bajar la pagina" + (f" ({sa.ULTIMO_ERROR})" if sa.ULTIMO_ERROR else "")}
    tabla = sa._parse_page(html, PALABRAS_TABLAS)
    if not tabla:
        sa._FALLOS_LECTURA += 1
        return {"ok": False, "filas": {}, "bajado": ahora, "error": "la pagina se bajo pero no se pudo leer la tabla"}
    sa._FALLOS_LECTURA = 0
    filas = extraer_filas(tabla)
    if not all(k in filas for k in FILAS_CLAVE):
        # por si la ruta por JSON embebido devolvio una sola tabla: se vuelve a leer todo el HTML
        extra = sa._parse_html_table(html, PALABRAS_TABLAS)
        if extra:
            tabla = {**extra, **tabla}
            filas = extraer_filas(tabla)
    ok = all(k in filas for k in FILAS_CLAVE)
    return {"ok": ok, "filas": filas, "etiquetas": list(tabla)[:120], "bajado": ahora,
            "error": None if ok else "la tabla no trae la fila de P/S (PS Ratio)"}


def _fmt(v, d=1):
    return "—" if v is None else f"{v:,.{d}f}"


def _serie(fila, d=2):
    if not fila:
        return "no hay fila"
    anios = fila["anios"]
    return f"hoy {_fmt(fila['actual'], d)} | " + ", ".join(f"{a}: {_fmt(v, d)}" for a, v in anios.items())


def resumen(resultados: dict) -> list:
    lineas = ["P/S y otros multiplos desde Stock Analysis (veces, no porcentaje; FCF Yield en %)", ""]
    sin_pagina, sin_ps, sin_evs, sin_fwd = [], [], [], []
    for t, r in resultados.items():
        if not r["ok"]:
            sin_pagina.append(f"{t} ({r['error']})")
            continue
        f = r["filas"]
        if not (f.get("ps") or {}).get("actual"):
            sin_ps.append(t)
        if "ev_sales" not in f:
            sin_evs.append(t)
        if "forward_pe" not in f:
            sin_fwd.append(t)
        lineas.append(f"== {t}  (bajado {r.get('bajado', '?')})")
        for nombre, rotulo in (("ps", "P/S"), ("ev_sales", "EV/Sales"), ("forward_pe", "PER adelantado"),
                               ("per", "PER"), ("peg", "PEG"), ("p_fcf", "P/FCF")):
            lineas.append(f"   {rotulo:16s}: {_serie(f.get(nombre))}")
    leidas = sum(1 for r in resultados.values() if r["ok"])
    lineas += ["", f"Empresas leidas: {leidas} de {len(resultados)}"]
    if sin_pagina:
        lineas.append("Sin pagina o sin tabla: " + ", ".join(sin_pagina))
    if sin_ps:
        lineas.append("Sin valor de P/S hoy: " + ", ".join(sin_ps))
    if sin_evs:
        lineas.append("Sin fila de EV/Sales: " + ", ".join(sin_evs))
    if sin_fwd:
        lineas.append("Sin fila de PER adelantado: " + ", ".join(sin_fwd))
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
    print("  P/S y multiplos (solo trae datos)")
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
