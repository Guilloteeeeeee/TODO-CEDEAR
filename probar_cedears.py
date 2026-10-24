"""
Prueba aparte (v1.2.46; en la v1.2.47 usa tambien Rava y Stock Analysis; no cambia ningun puntaje): controla los ratios de conversion de data/cedears.csv y los precios en pesos de Yahoo.

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
    print(f"Bajando {len(tickers)} precios en dolares (Yahoo y, si falta alguno, Stock Analysis) y los CEDEARs en pesos (Yahoo y Rava)...")
    info = pv.bajar_usd(tickers)
    usd, fuente_usd = info["usd"], info.get("fuente", {})
    simbolos = cedears.simbolos_yahoo(datos)
    byma = {t: d["simbolo"] for t, d in datos.items()}
    cand = pv.bajar_ars_fuentes(simbolos, byma)
    n_yahoo = sum(1 for l in cand.values() if any(f == pv.FUENTE_YAHOO for f, _ in l))
    n_rava = sum(1 for l in cand.values() if any(f == pv.FUENTE_RAVA for f, _ in l))
    n_sa = sum(1 for f in fuente_usd.values() if f == pv.FUENTE_SA)
    print(f"  dolares: {len(usd)} de {len(tickers)} (respaldo Stock Analysis: {n_sa}) | pesos: Yahoo {n_yahoo}, Rava {n_rava} de {len(datos)}")
    if len(usd) < 5:
        print("Yahoo respondio muy poco en dolares (puede estar bloqueando). Probá de nuevo en un rato.")
    if n_rava == 0:
        print("Rava no devolvio ningun precio: si pasa seguido, avisame (puede haber cambiado el formato de su pagina).")
    buenos, med = pv.elegir_ars(cand, {t: d["ratio"] for t, d in datos.items()}, usd)
    lineas = [f"{'ticker':7} {'simbolo':9} {'ratio':>8} {'US$':>10} {'pesos':>12} {'dolar impl.':>12} {'desvio':>8}  {'fuente':14} nota"]
    revisar = []
    for t in tickers:
        d = datos.get(t) or {}
        r, u = d.get("ratio"), usd.get(t)
        b = buenos.get(t)
        if not (r and u and b):
            if not r:
                falta = "sin ratio (no figura en data/cedears.csv)"
            elif not u:
                falta = "sin precio en dolares"
            elif t in cand:
                falta = "REVISAR: ningun precio en pesos cierra con el ratio (" + ", ".join(f"{f} {p:,.2f}" for f, p in cand[t]) + ")"
            else:
                falta = "sin precio en pesos (ni Yahoo ni Rava)"
            lineas.append(f"{t:7} {str(d.get('simbolo', '')):9} {cedears.ratio_texto(r):>8} {'' if not u else f'{u:10.2f}':>10} {'':>12} {'':>12} {'':>8}  {'':14} {falta}")
            revisar.append((t, falta))
            continue
        c, a = b["ccl"], b["ars"]
        dev = (c / med - 1) if med else None
        otros = [(f, p) for f, p in cand.get(t, []) if (f, p) != (b["fuente"], a)]
        nota = ""
        if dev is not None and abs(dev) > UMBRAL:
            nota = "REVISAR"
            revisar.append((t, nota))
        elif otros:
            ot = ", ".join(f"{f} {p:,.2f}" for f, p in otros)
            nota = f"(otro precio descartado: {ot})"
        lineas.append(f"{t:7} {str(d.get('simbolo', '')):9} {cedears.ratio_texto(r):>8} {u:10.2f} {a:12.2f} {c:12.2f} {'' if dev is None else f'{dev * 100:+7.1f}%':>8}  {b['fuente']:14} {nota}")
    cab = [f"Dolar implicito mediano: {med:.2f}" if med else "Sin mediana (muy pocos datos)",
           f"Con precio en pesos validado: {len(buenos)} | para revisar o sin dato: {len(revisar)}", ""]
    texto = "\n".join(cab + lineas + ["", "Para revisar:"] + [f"  {t}: {n}" for t, n in revisar])
    print(texto)
    with open(os.path.join(AQUI, "resultados_cedears.txt"), "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    print("\nListo. Se guardo resultados_cedears.txt")


if __name__ == "__main__":
    main()
