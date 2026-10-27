"""
Baja de Yahoo Finance, para cada ETF de data/etfs.csv, los datos de su pagina: precio, NAV, patrimonio (AUM), comision, dividendo y frecuencia, descripcion (traducida al castellano), principales
tenencias, sectores y noticias. Todo se guarda en data/etfs_yahoo.json. NO cambia nada mas.
La app usa este archivo cuando Yahoo no responde desde la nube (pasa seguido: Yahoo limita los pedidos de las IP compartidas).

Uso (desde la carpeta del proyecto):
    python bajar_etfs_yahoo.py            (todos los ETFs, unos 3 a 5 minutos)
    python bajar_etfs_yahoo.py SPY QQQ    (solo esos)

Uno a la vez, con pausa; se guarda de a poco. Si Yahoo empieza a rechazar, se frena y lo dice.
"""
import datetime
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import etfs as et  # noqa: E402
from data import etfs_yahoo as ey  # noqa: E402

PAUSA_S = 2.0


def _guardar(datos, fecha):
    with open(ey.RUTA, "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha, "datos": {t: ey.a_json(v) for t, v in datos.items()}}, f, ensure_ascii=False)


def main(tickers=None):
    todos = et.cargar()
    elegidos = [e for e in todos if not tickers or e["ticker"] in {t.upper() for t in tickers}]
    datos, _ = ey.cargar()
    fecha = datetime.datetime.now().strftime("%d/%m/%Y")
    avisos, seguidos = [], 0
    print(f"Bajando los datos de Yahoo de {len(elegidos)} ETFs (uno por uno, con pausa; no cierres la ventana)...")
    for i, e in enumerate(elegidos, 1):
        t, sim = e["ticker"], et.simbolo_yahoo(e)
        t0 = time.time()
        try:
            d = ey.bajar(sim, timeout=30.0)
        except Exception as ex:  # noqa: BLE001
            d = {}
            avisos.append(f"{t}: error {type(ex).__name__}")
        if not d:
            seguidos += 1
            avisos.append(f"{t}: Yahoo no devolvio nada")
            print(f"  {i:3d}/{len(elegidos)} {t:6} SIN DATOS")
            if seguidos >= 5:
                avisos.append("Yahoo dejo de responder (5 seguidos sin datos): se corta aca. Espera un rato y volve a correrlo; lo ya bajado queda guardado.")
                break
            time.sleep(PAUSA_S * 3)
            continue
        seguidos = 0
        if d.get("resumen_en") and not d.get("resumen_es"):
            es = ey.traducir_es(d["resumen_en"])
            if es:
                d["resumen_es"] = es
            else:
                avisos.append(f"{t}: la descripcion quedo en ingles (no se pudo traducir; probá 'pip install deep-translator')")
        datos[t] = d
        faltan = [k for k in ("nav", "aum", "comision", "rendimiento", "holdings", "mercado") if k not in d]
        print(f"  {i:3d}/{len(elegidos)} {t:6} ok" + (f"  (faltan: {', '.join(faltan)})" if faltan else ""))
        if faltan:
            avisos.append(f"{t}: faltan {', '.join(faltan)}")
        if i % 10 == 0:
            _guardar(datos, fecha)
        time.sleep(max(0.0, PAUSA_S - (time.time() - t0)))
    _guardar(datos, fecha)
    texto = [f"ETFs con datos de Yahoo guardados: {len(datos)} de {len(todos)}", ""] + [f"- {a}" for a in avisos]
    with open(os.path.join(AQUI, "resultados_etfs_yahoo.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Se guardo data/etfs_yahoo.json (mandamelo o subilo a GitHub) y resultados_etfs_yahoo.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
