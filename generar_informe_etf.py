"""
v1.5.50: arma el PDF de cada Análisis de ETF (data/analisis_etf.json) en static/informes_etf/<TICKER>_<aaaa-mm-dd>.pdf
y guarda cada versión del informe en el archivo histórico (data/historico/informes/ETF-<TICKER>_<aaaa-mm-dd>.json).

Se corre en el entorno de trabajo de los informes (necesita Playwright con Chromium); en la PC de Guille no hace falta: la app solo lee los PDF ya armados.
Uso: python generar_informe_etf.py            (todos los que no tienen PDF)
     python generar_informe_etf.py XLV XLK     (estos, aunque ya tengan PDF)
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from ui import etf_informe as E  # noqa: E402


def armar_pdf(ticker, inf, destino):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page()
        pag.set_content(E.documento_html(ticker, inf), wait_until="networkidle")
        pag.pdf(path=destino, format="A4", print_background=True, prefer_css_page_size=True)
        nav.close()


def main(tickers=None):
    datos = E.cargar()
    pedidos = [t.upper() for t in tickers] if tickers else [t for t, inf in datos.items() if not E.ruta_pdf(t, inf)]
    os.makedirs(E.CARPETA_PDF, exist_ok=True)
    hechos = []
    for tk in pedidos:
        inf = datos.get(tk)
        if not inf:
            print(f"{tk}: no tiene informe")
            continue
        prob = E.validar(tk, inf)
        if prob:
            print(f"{tk}: NO SE ARMA ({'; '.join(prob)})")
            continue
        destino = os.path.join(E.CARPETA_PDF, f"{tk}_{E.fecha_iso(inf['fecha'])}.pdf")
        armar_pdf(tk, inf, destino)
        try:
            from data import historico as _hist
            _hist.archivar_informe(f"ETF-{tk}", inf)
        except Exception as ex:  # noqa: BLE001
            print(f"{tk}: no se pudo guardar en el archivo histórico ({ex})")
        hechos.append(tk)
        print(f"{tk}: {os.path.relpath(destino, AQUI)}")
    print(f"Listo: {len(hechos)} PDF")
    return hechos


if __name__ == "__main__":
    main(sys.argv[1:] or None)
