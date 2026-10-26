"""Busca la foto del CEO de cada empresa en Wikipedia usando lo ya guardado en data/paquetes_yahoo.json (no vuelve a pedir nada a Yahoo).
Uso:  python bajar_fotos_ceo.py            (las empresas que todavia no tienen foto)
      python bajar_fotos_ceo.py AAPL NVDA  (solo esas, aunque ya tengan)
Guarda de a poco en data/paquetes_yahoo.json y deja el detalle en resultados_fotos_ceo.txt. Si Wikipedia no responde, lo dice y corta."""
import datetime
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import foto_ceo as fc  # noqa: E402
from data import paquetes_yahoo as py  # noqa: E402

PAUSA_S = 0.7


def _ceo(gob):
    for d in (gob or {}).get("directivos") or []:
        c = str(d.get("cargo") or "").lower()
        if "ceo" in c or "chief executive" in c:
            return d.get("nombre")
    return None


def _guardar(datos, fecha):
    with open(py.RUTA, "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha, "datos": {t: py.a_json(v) for t, v in datos.items()}}, f, ensure_ascii=False)


def main(tickers=None):
    datos, fecha = py.cargar()
    if not datos:
        print("No encuentro data/paquetes_yahoo.json (o esta vacio). Primero corre bajar_paquetes_yahoo.bat.")
        return
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    nombres = {r["ticker"]: r.get("nombre") or r["ticker"] for r in cache}
    pedidos = [t.upper() for t in tickers] if tickers else [t for t in sorted(datos) if not datos[t].get("foto_ceo")]
    fecha = fecha or datetime.datetime.now().strftime("%d/%m/%Y")
    print(f"Buscando la foto del CEO de {len(pedidos)} empresas en Wikipedia (una por una)...")
    lineas, nuevas, errores_seguidos = [], 0, 0
    for i, t in enumerate(pedidos, 1):
        if t not in datos:
            lineas.append(f"{t}: no esta en el archivo de Yahoo")
            continue
        ceo = _ceo(datos[t].get("gobierno"))
        if not ceo:
            lineas.append(f"{t}: Yahoo no informo CEO")
            print(f"  {i:3d}/{len(pedidos)} {t:6} sin CEO en Yahoo")
            continue
        fc.ULTIMO_ERROR = None
        url = fc.buscar_foto(ceo, nombres.get(t, t))
        if url:
            datos[t]["foto_ceo"] = url
            nuevas += 1
            errores_seguidos = 0
            print(f"  {i:3d}/{len(pedidos)} {t:6} foto=si   ({ceo})")
        else:
            motivo = fc.diagnostico(ceo, nombres.get(t, t))
            lineas.append(f"{t} ({ceo}): {motivo}")
            print(f"  {i:3d}/{len(pedidos)} {t:6} foto=no   ({ceo})  {motivo[:200]}")
            errores_seguidos = errores_seguidos + 1 if fc.ULTIMO_ERROR else 0
            if errores_seguidos >= 5:
                lineas.append("Wikipedia no responde desde esta PC (5 errores de red seguidos): se corta aca. Mira el ultimo error de red de arriba.")
                print("\nWikipedia no responde desde esta PC (5 errores de red seguidos). Se corta aca.")
                break
        if i % 10 == 0:
            _guardar(datos, fecha)
        time.sleep(PAUSA_S)
    _guardar(datos, fecha)
    con = sum(1 for v in datos.values() if v.get("foto_ceo"))
    texto = [f"Fotos nuevas: {nuevas}. Empresas con foto: {con} de {len(datos)}", ""] + lineas
    with open(os.path.join(AQUI, "resultados_fotos_ceo.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print(f"\nListo: {nuevas} fotos nuevas ({con} de {len(datos)} empresas con foto). Subi data/paquetes_yahoo.json a GitHub y mandame resultados_fotos_ceo.txt.")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
