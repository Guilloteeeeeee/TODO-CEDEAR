"""
Baja de Yahoo Finance, para cada empresa, los datos que usan las solapas de la pagina de la empresa (dividendos, directivos, accionistas, calendario y estados
financieros con los 4 ultimos trimestres) y busca la foto del CEO en Wikipedia. Todo se guarda en data/paquetes_yahoo.json. NO cambia el cache ni los puntajes.
La app usa este archivo cuando Yahoo no responde desde la nube (pasa seguido: Yahoo limita los pedidos de las IP compartidas).

Uso (desde la carpeta del proyecto):
    python bajar_paquetes_yahoo.py            (todas las empresas, unos 20 a 30 minutos)
    python bajar_paquetes_yahoo.py NVDA AMD   (solo esas)

Una empresa a la vez, con pausa; se guarda de a poco (si lo cortas, lo ya bajado queda). Si Yahoo empieza a rechazar, se frena y lo dice.
"""
import datetime
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import foto_ceo as fc  # noqa: E402
from data import paquetes_yahoo as py  # noqa: E402
from data import yahoo_extra as yx  # noqa: E402

PAUSA_S = 2.0


def _guardar(datos, fecha):
    with open(py.RUTA, "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha, "datos": {t: py.a_json(v) for t, v in datos.items()}}, f, ensure_ascii=False)


def _ceo(gob):
    for d in (gob or {}).get("directivos") or []:
        c = str(d.get("cargo") or "").lower()
        if "ceo" in c or "chief executive" in c:
            return d.get("nombre")
    return None


def main(tickers=None):
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    nombres = {r["ticker"]: r.get("nombre") or r["ticker"] for r in cache}
    todos = sorted(nombres)
    tickers = [t.upper() for t in tickers] if tickers else todos
    datos, _ = py.cargar()
    fecha = datetime.datetime.now().strftime("%d/%m/%Y")
    avisos, seguidos_sin_dato, fallos_foto = [], 0, 0
    print(f"Bajando los datos de Yahoo de {len(tickers)} empresas (una por una, con pausa; no cierres la ventana)...")
    for i, t in enumerate(tickers, 1):
        t0 = time.time()
        try:
            p = yx.bajar_paquete(t, timeout=30.0)
        except Exception as e:  # noqa: BLE001
            p = {}
            avisos.append(f"{t}: error {type(e).__name__}")
        util = {k: p.get(k) for k in py.CLAVES if p.get(k)}
        if not util:
            seguidos_sin_dato += 1
            avisos.append(f"{t}: Yahoo no devolvio nada")
            print(f"  {i:3d}/{len(tickers)} {t:6} SIN DATOS")
            if seguidos_sin_dato >= 5:
                avisos.append("Yahoo dejo de responder (5 seguidas sin datos): se corta aca. Espera un rato y volve a correrlo; lo ya bajado queda guardado.")
                break
            time.sleep(PAUSA_S * 3)
            continue
        seguidos_sin_dato = 0
        ceo = _ceo(p.get("gobierno"))
        util["foto_ceo"] = fc.buscar_foto(ceo, nombres.get(t, t)) if ceo else None
        datos[t] = util
        faltan = [k for k in py.CLAVES if k not in util]
        motivo = ""
        if not util["foto_ceo"] and fallos_foto < 3:      # v1.2.60: el motivo de las primeras fotos que no salen (queda tambien en el .txt)
            fallos_foto += 1
            motivo = f"sin CEO en Yahoo" if not ceo else fc.diagnostico(ceo, nombres.get(t, t))
            avisos.append(f"{t}: foto no encontrada ({ceo}): {motivo}")
            print(f"        motivo foto: {motivo[:300]}")
        print(f"  {i:3d}/{len(tickers)} {t:6} ok  foto={'si' if util['foto_ceo'] else 'no'}" + (f"  (faltan: {', '.join(faltan)})" if faltan else ""))
        if i % 10 == 0:
            _guardar(datos, fecha)
        time.sleep(max(0.0, PAUSA_S - (time.time() - t0)))
    _guardar(datos, fecha)
    con_foto = sum(1 for v in datos.values() if v.get("foto_ceo"))
    texto = [f"Empresas con datos de Yahoo guardados: {len(datos)} de {len(todos)}", f"Con foto del CEO: {con_foto}", ""] + [f"- {a}" for a in avisos]
    with open(os.path.join(AQUI, "resultados_paquetes_yahoo.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Se guardo data/paquetes_yahoo.json (subilo a GitHub) y resultados_paquetes_yahoo.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
