"""
Prueba de Stock Analysis para el Screener (v1.2.12).
Baja UNA pagina por empresa (la de ratios anuales) y muestra lo que el programa entiende de ella,
comparado con lo que dice Yahoo, para ver si conviene usar Stock Analysis como fuente principal.

Uso (desde la carpeta del proyecto):
    python probar_stockanalysis.py
    python probar_stockanalysis.py SAP TSM        (otros tickers)

Guarda resultados_stockanalysis.txt: mandalo para revisarlo (y sa_pagina_cruda.bin si aparece).
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import yfinance as yf

from data import stockanalysis as sa

TICKERS_DEFECTO = ["NVDA", "MU", "AAPL", "CRWD", "SAP", "TSM", "BABA", "VALE", "ITUB", "MUFG", "HDB", "SONY", "O", "BRK-B"]
YAHOO_CAMPOS = {"per": "trailingPE", "p_b": "priceToBook", "ev_ebitda": "enterpriseToEbitda", "peg": "pegRatio"}


def _fmt(x, d=2):
    try:
        return f"{float(x):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def main(tickers):
    out = ["Prueba de Stock Analysis — " + ", ".join(tickers)]
    # Diagnostico de la primera pagina: que llega realmente (sirve si no se puede leer la tabla)
    try:
        lineas, crudo = sa.diagnosticar_pagina(tickers[0])
        out.append(f"Diagnostico de la pagina de {tickers[0]}:")
        out.extend("  " + l for l in lineas)
        if crudo:
            with open("sa_pagina_cruda.bin", "wb") as f:
                f.write(crudo)
            out.append("  (se guardo sa_pagina_cruda.bin con lo que llego, por si hace falta mandarlo)")
    except Exception as e:  # noqa: BLE001
        out.append(f"Diagnostico: FALLO {type(e).__name__}: {e}")

    for sym in tickers:
        out.append(f"\n===== {sym} =====")
        try:
            datos = sa.fetch_ratios_completos(sym)
            if not datos["ok"]:
                out.append(f"  Stock Analysis: NO se pudo leer ({datos.get('error')}).")
                if datos.get("etiquetas"):
                    out.append("  Etiquetas vistas: " + ", ".join(datos["etiquetas"][:25]))
                continue
            out.append("  Columnas: " + ", ".join(datos["columnas"]))
            try:
                info = yf.Ticker(sym).info or {}
            except Exception:  # noqa: BLE001
                info = {}
            out.append(f"  Yahoo: pais={info.get('country')} | moneda={info.get('currency')}/{info.get('financialCurrency')}")
            for m, d in datos["metricas"].items():
                serie = d["historia"]
                med = float(np.median(serie)) if serie else None
                dec = 4 if m == "dividend_yield" else 2
                linea = (f"  {m:15s} actual={_fmt(d['actual'], dec):>9s} | mediana={_fmt(med, dec):>9s} "
                         f"| años={len(serie)} {[round(v, dec) for v in serie]}")
                y = info.get(YAHOO_CAMPOS.get(m, ""))
                if y is not None and d["actual"]:
                    razon = float(y) / d["actual"]
                    linea += f" | Yahoo={_fmt(y)}" + ("  <-- REVISAR (difiere mas de 2x)" if razon > 2 or razon < 0.5 else "")
                out.append(linea)
            falta = [m for m in sa.SA_ETIQUETAS if m not in datos["metricas"]]
            out.append("  Sin fila en la pagina: " + (", ".join(falta) if falta else "(ninguna)"))
        except Exception as e:  # noqa: BLE001
            out.append(f"  FALLO: {type(e).__name__}: {e}")
            out.append(traceback.format_exc(limit=3))
    txt = "\n".join(out)
    with open("resultados_stockanalysis.txt", "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print("\nListo. Se guardo resultados_stockanalysis.txt: mandalo.")


if __name__ == "__main__":
    main([a.upper() for a in sys.argv[1:]] or TICKERS_DEFECTO)
    try:
        input("\nPresiona Enter para cerrar...")
    except EOFError:
        pass
