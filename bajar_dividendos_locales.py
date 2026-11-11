"""
v1.5.69 — Dividendos de las empresas de afuera en su propia moneda (Score de Seguridad del Dividendo, pilar 3).

Pedido de Guille (11/11/2026): el recorte se busca en la moneda en que la empresa fija su dividendo, no en dólares (así una devaluación o
una apreciación no se confunde con un recorte). Este programa baja de Yahoo Finance:

  1. Los dividendos de cada empresa de afuera en la bolsa de su país (Londres, Ámsterdam, París, Zúrich, Tokio, San Pablo, México,
     Seúl, Bombay, Johannesburgo, Taipéi…), en su moneda, sin pasar por el dólar → data/historico/dividendos_locales.json
     (símbolos en data/moneda_dividendo.py → LOCAL). Se controla que sea la misma empresa: las fechas de pago tienen que coincidir
     con las del ADR (al menos 60%).
  2. La historia semanal de cada moneda contra el dólar (para las que no tienen bolsa de origen en su moneda o la serie no alcanza)
     → data/historico/monedas.json.

No cambia el cache ni los puntajes. Lo ya guardado no se borra (si Yahoo trae menos pagos que la vez anterior, queda lo anterior).

Uso (desde la carpeta del proyecto):
    python bajar_dividendos_locales.py            (todas, unos 3 a 5 minutos)
    python bajar_dividendos_locales.py GSK TM     (solo esas)
Se corre solo al final de bajar_historico.bat (una vez por mes).
"""
import datetime
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import historico as H  # noqa: E402
from data import moneda_dividendo as MD  # noqa: E402
from data.fetcher import _con_tope  # noqa: E402

PAUSA_S = 0.6
TOPE_S = 45
MAX_FALLOS_SEGUIDOS = 8


def _empresas():
    """[(ticker, moneda, símbolo local o None)] de las empresas de afuera que pagan dividendo y no lo fijan en dólares."""
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    out = []
    for r in cache:
        if (r.get("annual_dividend") or 0) <= 0:
            continue
        mon = MD.moneda(r["ticker"], r.get("moneda_estados"), r.get("pais"))
        if mon != "USD":
            out.append((r["ticker"], mon, MD.LOCAL.get(r["ticker"])))
    return out


def bajar_dividendos(simbolo):
    """[[fecha, monto]] de toda la historia de dividendos del símbolo (en su moneda), o None."""
    import yfinance as yf
    s = yf.Ticker(str(simbolo)).dividends
    if s is None or len(s) == 0:
        return None
    return [[i.date().isoformat(), float(v)] for i, v in s.items() if v == v and v > 0]


def bajar_moneda(mon):
    """(símbolo usado, {fecha: dólares por unidad}) semanal de toda la historia, o (None, None)."""
    import yfinance as yf
    for par, inv in ((f"{mon}USD=X", False), (f"USD{mon}=X", True), (f"{mon}=X", True)):
        try:
            h = yf.Ticker(par).history(period="max", interval="1wk")
        except Exception:  # noqa: BLE001
            continue
        if h is None or h.empty or "Close" not in h:
            continue
        vals = {i.date().isoformat(): (1.0 / float(c) if inv else float(c)) for i, c in h["Close"].items() if c == c and c > 0}
        if len(vals) > 50:
            return par, {k: float(f"{v:.6g}") for k, v in sorted(vals.items())}
    return None, None


def main(tickers=None):
    empresas = _empresas()
    if tickers:
        pedidos = {t.upper() for t in tickers}
        empresas = [e for e in empresas if e[0] in pedidos]
    adr = H.leer("dividendos.json", {})
    guard = H.leer("dividendos_locales.json", {})
    datos = guard.get("datos", {})
    lineas, seguidos = [], 0
    hoy = datetime.date.today().isoformat()
    con_local = [e for e in empresas if e[2]]
    print(f"1) Dividendos en su moneda, en la bolsa de origen: {len(con_local)} empresas (no cierres la ventana)...")
    for i, (t, mon, sim) in enumerate(con_local, 1):
        t0 = time.time()
        try:
            termino, pagos = _con_tope(bajar_dividendos, (sim,), TOPE_S)
        except Exception as ex:  # noqa: BLE001
            termino, pagos = True, None
            lineas.append(f"{t:6} {sim:14} error: {type(ex).__name__}: {str(ex)[:80]}")
        if not termino or not pagos:
            seguidos += 1
            msg = "no respondió a tiempo" if not termino else "Yahoo no trajo dividendos"
            print(f"  {i:3d}/{len(con_local)} {t:6} {sim:14} SIN DATOS ({msg})")
            lineas.append(f"{t:6} {sim:14} SIN DATOS ({msg}): se usa el ADR convertido o la regla de antes")
            if seguidos >= MAX_FALLOS_SEGUIDOS:
                lineas.append(f"Yahoo dejó de responder ({seguidos} seguidos sin datos): se corta acá. Probá de nuevo en un rato.")
                break
            continue
        seguidos = 0
        previo = datos.get(t) or {}
        if previo.get("pagos") and len(pagos) < len(previo["pagos"]) * 0.9:
            lineas.append(f"{t:6} {sim:14} Yahoo trajo {len(pagos)} pagos y había {len(previo['pagos'])}: queda lo anterior")
            continue
        co = MD.coincidencia(adr.get(t), pagos)
        saltos = MD.saltos_de_unidad(pagos)
        ok = co >= MD.COINCIDENCIA_MIN and not saltos
        motivo = "" if ok else (f"saltos de unidad en {', '.join(saltos[:3])}" if saltos else f"fechas que coinciden con el ADR: {co:.0%}")
        datos[t] = {"simbolo": sim, "moneda": mon, "pagos": pagos, "coinciden": co, "ok": ok, "motivo": motivo, "act": hoy}
        estado = "ok" if ok else f"NO SE USA ({motivo})"
        print(f"  {i:3d}/{len(con_local)} {t:6} {sim:14} {len(pagos):3d} pagos desde {pagos[0][0][:4]}, coinciden {co:.0%}  {estado}")
        lineas.append(f"{t:6} {sim:14} {mon} {len(pagos):3d} pagos desde {pagos[0][0]}, coinciden con el ADR {co:.0%}: {estado}")
        if i % 15 == 0:
            H.escribir("dividendos_locales.json", {"fecha": hoy, "datos": datos})
        time.sleep(max(0.0, PAUSA_S - (time.time() - t0)))
    H.escribir("dividendos_locales.json", {"fecha": hoy, "datos": datos})

    mons = sorted({m for _, m, _ in empresas})
    print(f"\n2) Historia semanal de {len(mons)} monedas contra el dólar...")
    guard_m = H.leer("monedas.json", {})
    monedas = guard_m.get("monedas", {})
    lineas.append("")
    for mon in mons:
        try:
            termino, res = _con_tope(bajar_moneda, (mon,), TOPE_S)
        except Exception:  # noqa: BLE001
            termino, res = True, (None, None)
        par, vals = res if (termino and res) else (None, None)
        if not vals:
            print(f"  {mon}: SIN DATOS")
            lineas.append(f"Moneda {mon}: SIN DATOS (queda lo anterior, si había)")
            continue
        previo = (monedas.get(mon) or {}).get("usd_por_unidad") or {}
        monedas[mon] = {"simbolo": par, "usd_por_unidad": {**previo, **vals}, "act": hoy}
        print(f"  {mon}: ok ({len(vals)} semanas desde {min(vals)})")
        lineas.append(f"Moneda {mon} ({par}): {len(vals)} semanas desde {min(vals)}")
        time.sleep(PAUSA_S)
    H.escribir("monedas.json", {"fecha": hoy, "monedas": monedas})

    usables = sum(1 for d in datos.values() if d.get("ok"))
    texto = [f"Dividendos en su moneda ({datetime.datetime.now():%d/%m/%Y %H:%M}): {usables} de {len(con_local)} empresas con la bolsa de "
             f"origen; {len(monedas)} monedas con historia semanal.", ""] + lineas
    with open(os.path.join(AQUI, "resultados_dividendos_locales.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + texto[0])
    print("\nListo. Mandame data/historico/dividendos_locales.json, data/historico/monedas.json y resultados_dividendos_locales.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
