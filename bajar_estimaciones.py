"""
v1.5.62 (Guille, 10/11/2026: una vez por trimestre, «cuando terminen los earnings», con recordatorio por mail): baja de Yahoo (gratis) la
ganancia por acción que esperan los analistas para el año en curso y el próximo, de todas las empresas de la app que pagan dividendo.

La usa el Score de Seguridad del Dividendo (scoring/dividendo.py):
- tendencia (pilar 5): estimación del año próximo contra la del año en curso;
- excepción del payout (pilar 1): si los analistas esperan 1,5 veces o más la ganancia contable (o la contable fue pérdida), el payout se mide
  contra la estimada (con al menos 5 analistas y el dividendo cubierto por el flujo de caja libre).
Una estimación con más de 130 días no se usa: por eso hay que correrlo cada trimestre (el mail del día 1 de marzo, junio, septiembre y
diciembre lo recuerda).

Guarda data/estimaciones_analistas.json (la última de cada empresa) y suma cada bajada al archivo histórico (data/historico/estimaciones.json,
solo se agrega). Si Yahoo no responde para una empresa, queda la estimación anterior (y el score deja de usarla cuando pase de 130 días).

Uso (desde la carpeta del proyecto):
    python bajar_estimaciones.py           (todas las que pagan dividendo, unos 5 a 10 minutos)
    python bajar_estimaciones.py KO PEP    (solo esas)
"""
import datetime as dt
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import historico as H  # noqa: E402


def _empresas():
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    return [r["ticker"] for r in cache if (r.get("annual_dividend") or 0) > 0]


def archivar(nuevas, archivo):
    """Suma las estimaciones al histórico {ticker: {fecha: {actual, proximo, analistas}}}. Solo agrega; devuelve cuántas sumó."""
    n = 0
    for t, r in (nuevas or {}).items():
        f = r.get("fecha")
        if not f:
            continue
        reg = archivo.setdefault(t, {})
        if f not in reg:
            reg[f] = {k: r.get(k) for k in ("actual", "proximo", "analistas")}
            n += 1
    return n


def main(tickers=None):
    from calibrar_dividendo import _estimaciones
    tickers = [t.upper() for t in (tickers or _empresas())]
    print(f"Bajando estimaciones de analistas de {len(tickers)} empresas (no cierres la ventana)...")
    out, fallas = _estimaciones(tickers)
    hoy = dt.date.today().isoformat()
    nuevas = {t: r for t, r in out.items() if r.get("fecha") == hoy}
    hist = H.leer("estimaciones.json", {})
    sumadas = archivar(nuevas, hist)
    H.escribir("estimaciones.json", dict(sorted(hist.items())))
    texto = [f"ESTIMACIONES DE ANALISTAS ({dt.datetime.now():%d/%m/%Y %H:%M})", "",
             f"■ Bajadas hoy: {len(nuevas)} de {len(tickers)}",
             f"■ Sin estimación nueva (queda la anterior, si había): {len(fallas)}" + (f" ({', '.join(fallas)})" if fallas else ""),
             f"■ Sumadas al archivo histórico: {sumadas}"]
    with open(os.path.join(AQUI, "resultados_estimaciones.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Mandame data/estimaciones_analistas.json, data/historico/estimaciones.json y resultados_estimaciones.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
