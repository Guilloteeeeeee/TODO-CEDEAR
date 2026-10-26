"""Prueba la foto del CEO sin abrir la app: python probar_foto_ceo.py  (o probar_foto_ceo.bat). Guarda resultados_foto_ceo.txt.
Para cada empresa pide a Yahoo el nombre del CEO y busca su foto en Wikipedia; muestra por que se acepta o se descarta cada pagina."""
import sys
from data import foto_ceo as FC

TICKERS = sys.argv[1:] or ["AAPL", "NVDA", "MSFT", "TSM", "JPM", "DIS"]


def main():
    import yfinance as yf
    lineas = []
    for t in TICKERS:
        try:
            info = yf.Ticker(t).info or {}
        except Exception as e:  # noqa: BLE001
            lineas.append(f"{t}: Yahoo fallo: {e}")
            continue
        emp = info.get("longName") or info.get("shortName") or t
        ceo = next((o.get("name") for o in info.get("companyOfficers") or [] if "ceo" in str(o.get("title", "")).lower() or "chief executive" in str(o.get("title", "")).lower()), None)
        if not ceo:
            lineas.append(f"{t} ({emp}): Yahoo no trae CEO")
            continue
        lineas.append(f"{t} ({emp}) CEO={ceo}: {FC.diagnostico(ceo, emp)}")
    txt = "\n\n".join(lineas)
    print(txt)
    open("resultados_foto_ceo.txt", "w", encoding="utf-8").write(txt + "\n")


if __name__ == "__main__":
    main()
