"""
Descarga los logos de las empresas a assets/logos/<TICKER>.png (CEDEAR Screener v1.2.16).

Corre UNA vez en la PC (y cuando se sume una empresa nueva). Despues subi la carpeta assets/logos/
a GitHub (TODO-CEDEAR): la app los incrusta, asi que no depende de ningun servicio externo.

Para cada ticker prueba, en este orden, estas fuentes y se queda con la primera que devuelva una imagen:
  1. parqet     -> logo por simbolo (ticker)
  2. fmp        -> Financial Modeling Prep, logo por simbolo (ticker)
  3. google     -> favicon del dominio de la empresa (el mas seguro; baja resolucion)
No pude probar estas direcciones desde mi entorno: el resumen (resultados_logos.txt) dice cual funciono.
Las imagenes se achican a 64x64 para que la pagina pese poco (si Pillow esta instalado).

Uso:  python descargar_logos.py            (todos los tickers que falten)
      python descargar_logos.py --todo     (vuelve a bajar todos)
      python descargar_logos.py AAPL MSFT  (solo esos)
"""
import io
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from config.sectors import TICKER_TO_SECTOR
from ui.logos import CARPETA_LOGOS, DOMINIOS

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
           "Accept": "image/*,*/*;q=0.8", "Accept-Encoding": "gzip, deflate"}
PAUSA = 0.4
MIN_BYTES = 150


def _fuentes(ticker):
    yield "parqet", f"https://assets.parqet.com/logos/symbol/{ticker.upper()}?format=png"
    yield "fmp", f"https://financialmodelingprep.com/image-stock/{ticker.upper()}.png"
    dom = DOMINIOS.get(ticker)
    if dom:
        yield "google", f"https://www.google.com/s2/favicons?domain={dom}&sz=128"


def _a_png_chico(contenido: bytes):
    """Devuelve (bytes, extension). Achica a 64x64 si hay Pillow; si no, deja el original."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(contenido)).convert("RGBA")
        img.thumbnail((64, 64))
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue(), ".png"
    except Exception:  # noqa: BLE001
        return contenido, ".png"


def bajar(ticker):
    for nombre, url in _fuentes(ticker):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:  # noqa: BLE001
            yield nombre, None, f"{type(e).__name__}"
            continue
        tipo = (r.headers.get("Content-Type") or "").lower()
        if r.status_code == 200 and tipo.startswith("image/") and "svg" not in tipo and len(r.content) >= MIN_BYTES:
            yield nombre, _a_png_chico(r.content), "ok"
            return
        yield nombre, None, f"HTTP {r.status_code} {tipo[:20]} {len(r.content)}B"
        time.sleep(0.1)


def main(args):
    todo = "--todo" in args
    pedidos = [a.upper() for a in args if not a.startswith("--")]
    tickers = pedidos or list(TICKER_TO_SECTOR)
    os.makedirs(CARPETA_LOGOS, exist_ok=True)
    por_fuente, faltan, intentos = {}, [], {}
    print(f"Bajando logos de {len(tickers)} empresas a {CARPETA_LOGOS} ...")
    for i, t in enumerate(tickers, 1):
        destino = CARPETA_LOGOS / f"{t}.png"
        if destino.exists() and not todo and not pedidos:
            continue
        ok = False
        for nombre, res, detalle in bajar(t):
            intentos.setdefault(nombre, {"ok": 0, "fallo": 0, "ejemplo": ""})
            if res:
                datos, ext = res
                (CARPETA_LOGOS / f"{t}{ext}").write_bytes(datos)
                por_fuente[nombre] = por_fuente.get(nombre, 0) + 1
                intentos[nombre]["ok"] += 1
                ok = True
                break
            intentos[nombre]["fallo"] += 1
            intentos[nombre]["ejemplo"] = f"{t}: {detalle}"
        if not ok:
            faltan.append(t)
        print(f"  [{i:3d}/{len(tickers)}] {t:7s} {'OK (' + nombre + ')' if ok else 'sin logo'}")
        time.sleep(PAUSA)
    lineas = ["Descarga de logos — resumen", ""]
    lineas.append("Logos guardados por fuente: " + (", ".join(f"{k}={v}" for k, v in por_fuente.items()) or "ninguno"))
    lineas.append("")
    for nombre, d in intentos.items():
        lineas.append(f"  {nombre:8s} aciertos={d['ok']:3d} fallos={d['fallo']:3d}  ultimo fallo: {d['ejemplo']}")
    lineas.append("")
    lineas.append(f"Sin logo ({len(faltan)}): " + (", ".join(faltan) or "(ninguno)") + "  -> en la app se ven con iniciales")
    txt = "\n".join(lineas)
    with open("resultados_logos.txt", "w", encoding="utf-8") as f:
        f.write(txt)
    print("\n" + txt)
    print("\nListo. Subi la carpeta assets/logos/ a GitHub y mandame resultados_logos.txt")


if __name__ == "__main__":
    main(sys.argv[1:])
    try:
        input("\nPresiona Enter para cerrar...")
    except EOFError:
        pass
