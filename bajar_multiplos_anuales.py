"""
Baja de Stock Analysis los multiplos de cada anio fiscal (P/E, P/Book, P/S, EV/Ventas, EV/EBITDA, P/FCF, PEG y Dividend Yield) y los guarda en
data/multiplos_anuales.json. NO cambia el cache ni los puntajes: es solo para mostrar la tabla por anio de la solapa Valuacion.

Uso (desde la carpeta del proyecto):
    python bajar_multiplos_anuales.py            (todas las empresas del cache, unos 10 minutos)
    python bajar_multiplos_anuales.py NVDA AMD   (solo esas)

Trato con el sitio: igual que generar_cache (respeta robots.txt, una pagina a la vez con pausa, se detiene si lo bloquean). Se guarda de a poco.
"""
import datetime
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import multiplos_anuales as ma  # noqa: E402
from data import stockanalysis as sa  # noqa: E402


def _guardar(datos):
    with open(ma.RUTA, "w", encoding="utf-8") as f:
        json.dump({"fecha": datetime.datetime.now().strftime("%d/%m/%Y"), "datos": {t: {m: {str(a): v for a, v in xs.items()} for m, xs in ms.items()} for t, ms in datos.items()}},
                  f, ensure_ascii=False, indent=1)


def main(tickers=None):
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    todos = sorted(r["ticker"] for r in cache)
    tickers = [t.upper() for t in tickers] if tickers else todos
    datos, _ = ma.cargar()
    avisos = []
    import requests
    session = requests.Session()
    print(f"Bajando los multiplos por anio de {len(tickers)} empresas (una por una, con pausa; no cierres la ventana)...")
    for i, t in enumerate(tickers, 1):
        r = sa.fetch_ratios_completos(t, session)
        if r.get("ok"):
            m = ma.desde_metricas(r["metricas"])
            if m:
                datos[t] = m
                print(f"  {i:3d}/{len(tickers)} {t:6} ok  ({', '.join(f'{k}:{len(v)}a' for k, v in m.items())})")
            else:
                avisos.append(f"{t}: la pagina no trajo anios")
        else:
            avisos.append(f"{t}: {r.get('error') or 'sin datos'}")
            print(f"  {i:3d}/{len(tickers)} {t:6} SIN DATOS: {r.get('error')}")
        if sa._FALLOS_LECTURA >= 3:
            avisos.append("Stock Analysis dejo de responder o cambio el formato: se corta aca (lo ya bajado queda guardado).")
            break
        if i % 10 == 0:
            _guardar(datos)
    _guardar(datos)
    texto = [f"Empresas con multiplos por anio: {len(datos)} de {len(todos)}", ""] + [f"- {a}" for a in avisos]
    with open(os.path.join(AQUI, "resultados_multiplos_anuales.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Se guardo data/multiplos_anuales.json (subilo a GitHub) y resultados_multiplos_anuales.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
