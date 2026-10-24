"""
Prueba aparte (v1.2.46, no cambia ningun puntaje): controla los ratios de conversion de data/cedears.csv y los precios en pesos de Yahoo.

Para cada empresa baja el precio en dolares (ticker) y el precio en pesos de su CEDEAR (simbolo de BYMA + ".BA") y calcula el dolar que
implica:  dolar implicito = precio en pesos x ratio / precio en dolares.  Si el ratio esta bien, casi todos dan parecido (el dolar CCL, con
unos pocos puntos de diferencia). El que se aleja de la mediana tiene un ratio desactualizado o un simbolo equivocado: revisarlo contra la
tabla de BYMA (https://www.byma.com.ar) antes de confiar en su precio en pesos.

Uso:  python probar_cedears.py        (o doble clic en probar_cedears.bat).  Escribe resultados_cedears.txt; mandamelo si algo no cierra.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from data import cedears, precios_vivos as pv  # noqa: E402

UMBRAL = 0.10      # se marca "REVISAR" si el dolar implicito se aparta mas de 10% de la mediana (la app descarta a partir de 25%)


def main():
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    tickers = sorted(r["ticker"] for r in cache)
    datos = cedears.cargar()
    print(f"Bajando {len(tickers)} precios en dolares y los CEDEARs en pesos (un solo pedido cada uno)...")
    usd = pv.bajar_usd(tickers)["usd"]
    ars = pv.bajar_ars(cedears.simbolos_yahoo(datos))
    print(f"  dolares: {len(usd)} de {len(tickers)} | pesos: {len(ars)} de {len(datos)}")
    if len(usd) < 5 or len(ars) < 5:
        print("Yahoo respondio muy poco (puede estar bloqueando). Probá de nuevo en un rato.")
    buenos, med = pv.validar_ars(ars, {t: d["ratio"] for t, d in datos.items()}, usd)
    lineas = [f"{'ticker':7} {'simbolo':9} {'ratio':>8} {'US$':>10} {'pesos':>12} {'dolar impl.':>12} {'desvio':>8}  nota"]
    revisar = []
    for t in tickers:
        d = datos.get(t) or {}
        r, u, a = d.get("ratio"), usd.get(t), ars.get(t)
        if not (r and u and a):
            falta = "sin ratio" if not r else "sin precio en dolares" if not u else "sin precio en pesos"
            lineas.append(f"{t:7} {str(d.get('simbolo', '')):9} {cedears.ratio_texto(r):>8} {'' if not u else f'{u:10.2f}':>10} {'':>12} {'':>12} {'':>8}  {falta}")
            revisar.append((t, falta))
            continue
        c = a * r / u
        dev = (c / med - 1) if med else None
        nota = ""
        if dev is not None and abs(dev) > UMBRAL:
            nota = "REVISAR" + (" (la app lo descarta)" if abs(dev) > pv.BANDA_CCL else "")
            revisar.append((t, nota))
        lineas.append(f"{t:7} {str(d.get('simbolo', '')):9} {cedears.ratio_texto(r):>8} {u:10.2f} {a:12.2f} {c:12.2f} {'' if dev is None else f'{dev * 100:+7.1f}%':>8}  {nota}")
    cab = [f"Dolar implicito mediano: {med:.2f}" if med else "Sin mediana (muy pocos datos)",
           f"Con precio en pesos validado: {len(buenos)} | para revisar o sin dato: {len(revisar)}", ""]
    texto = "\n".join(cab + lineas + ["", "Para revisar:"] + [f"  {t}: {n}" for t, n in revisar])
    print(texto)
    with open(os.path.join(AQUI, "resultados_cedears.txt"), "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    print("\nListo. Se guardo resultados_cedears.txt")


if __name__ == "__main__":
    main()
