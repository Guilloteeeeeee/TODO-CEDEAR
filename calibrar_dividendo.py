"""
v1.5.58 (Guille, 10/11/2026: «correría el histórico, los analistas en la app real y hacemos una nueva comparación con Simply Safe Dividends»):
calcula el Score de Seguridad del Dividendo (scoring/dividendo.py, método v0.2) de las empresas que Guille comparó con SSD y escribe la comparación.

Usa lo que ya está en la carpeta del proyecto:
- data/cache_datos.json y data/paquetes_yahoo.json (los .bat de siempre);
- data/historico/dividendos.json (bajar_historico.bat: toda la historia de dividendos) y data/historico/estados.json (con los años viejos
  que suma bajar_sec.bat);
- y baja en el momento, de Yahoo, la estimación de ganancia de los analistas para este año y el próximo (se guarda en
  data/estimaciones_analistas.json).
No cambia el cache, los puntajes ni la pantalla.

Uso (desde la carpeta del proyecto, DESPUÉS de bajar_historico.bat y bajar_sec.bat):
    python calibrar_dividendo.py            (las empresas comparadas con SSD)
    python calibrar_dividendo.py --todas    (además, el score de todas las empresas de la app, en el .json)
Resultado: resultados_calibracion_dividendo.txt y data/calibracion_dividendo.json (mandámelos los dos).
"""
import datetime as dt
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import historico as H  # noqa: E402
from data import paquetes_yahoo as PY  # noqa: E402
from scoring import dividendo as SD  # noqa: E402

# Scores de Simply Safe Dividends que pasó Guille el 10/11/2026 (VALE: sin score en SSD).
SSD = {"KO": 80, "PG": 90, "JNJ": 99, "PEP": 80, "MCD": 77, "ADP": 90, "TXN": 80, "ABBV": 80, "MO": 60, "VZ": 70, "T": 70, "PFE": 50,
       "MMM": 60, "CVX": 90, "XOM": 80, "F": 40, "NEE": 80, "O": 80, "PLD": 61, "WELL": 80, "JPM": 70, "VALE": None}
FECHA_SSD = "10/11/2026"
TOPE_S = 30


def estimacion_yahoo(ticker):
    """{"actual": EPS estimado del año en curso, "proximo": del año próximo, "analistas": n} (Yahoo, promedio de analistas) o None."""
    import yfinance as yf
    df = yf.Ticker(ticker).earnings_estimate
    if df is None or df.empty or "avg" not in df:
        return None
    idx = {str(i): i for i in df.index}
    if "0y" not in idx or "+1y" not in idx:
        return None
    a, p = df.loc[idx["0y"], "avg"], df.loc[idx["+1y"], "avg"]
    n = df.loc[idx["+1y"], "numberOfAnalysts"] if "numberOfAnalysts" in df else None
    if a != a or p != p:
        return None
    return {"actual": float(a), "proximo": float(p), "analistas": int(n) if n == n and n is not None else None, "fecha": dt.date.today().isoformat()}


def _estimaciones(tickers):
    from data.fetcher import _con_tope
    ruta = os.path.join(AQUI, "data", "estimaciones_analistas.json")
    try:
        guard = json.load(open(ruta, encoding="utf-8")).get("datos", {})
    except Exception:  # noqa: BLE001
        guard = {}
    out, fallas = {}, []
    for i, t in enumerate(tickers, 1):
        try:
            termino, r = _con_tope(estimacion_yahoo, (t,), TOPE_S)
        except Exception:  # noqa: BLE001
            termino, r = True, None
        if termino and r:
            out[t] = r
            print(f"  {i:3d}/{len(tickers)} {t:6} estimación: {r['actual']:.2f} → {r['proximo']:.2f}")
        else:
            if guard.get(t):
                out[t] = guard[t]
            fallas.append(t)
            print(f"  {i:3d}/{len(tickers)} {t:6} sin estimación de analistas" + (" (uso la guardada)" if guard.get(t) else ""))
        time.sleep(0.5)
    json.dump({"fecha": dt.date.today().isoformat(), "datos": {**guard, **out}}, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
    return out, fallas


def _spearman(xs, ys):
    def rango(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r, i = [0.0] * len(v), 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    a, b = rango(xs), rango(ys)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / den if den else None


def _cat_n(s):
    return 0 if s <= 20 else 1 if s <= 40 else 2 if s <= 60 else 3 if s <= 80 else 4


def calcular_todo(tickers, cache, paquetes, archivo, splits, divs, precios, estimaciones):
    res = {}
    for t in tickers:
        row = cache.get(t)
        if not row:
            continue
        est = H.estados_completos(t, (paquetes.get(t) or {}).get("estados"), archivo=archivo, splits=splits.get(t, []), max_anios=13)
        hoy = None
        act = (precios.get(t) or {}).get("act")
        if act:
            try:
                hoy = dt.date.fromisoformat(act)
            except ValueError:
                hoy = None
        hist = SD.analizar_dividendos(divs.get(t), hoy=hoy, sigue_pagando=bool((row.get("annual_dividend") or 0) > 0)) if divs.get(t) else None
        ent = SD.entrada(row, est, hist, estimaciones.get(t))
        ent["hoy"] = hoy                     # v1.5.62: vigencia de la estimación de analistas contra la fecha de los datos
        r = SD.calcular(ent)
        fy = [a for a in ((est or {}).get("resultados") or {}).get("anios", []) if isinstance(a, int)]
        r["anios_estados"] = f"{min(fy)}–{max(fy)}" if fy else "sin estados"
        r["historial"] = {k: v for k, v in (hist or {}).items() if k != "tasa"} if hist else None
        res[t] = r
    return res


def main(args):
    todas = "--todas" in args
    cache = {r["ticker"]: r for r in json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]}
    paquetes = PY.cargar()[0]
    archivo = H.leer("estados.json", {})
    splits = H.leer("splits.json", {})
    divs = H.leer("dividendos.json", {})
    precios = H.leer("precios_mensuales.json", {})
    avisos = []
    if not divs:
        avisos.append("NO HAY HISTORIA DE DIVIDENDOS: corré primero bajar_historico.bat (sin eso no se puede calcular el pilar del historial).")
    sec = sum(1 for r in archivo.values() for a in (r.get("anios") or {}).values() if a.get("fuente") == "SEC")
    if not sec:
        avisos.append("No hay años de la SEC en el archivo: si querés 12 años de ganancias, corré bajar_sec.bat antes.")
    lista = [t for t in SSD if t in cache]
    otros = [t for t in cache if t not in SSD] if todas else []
    print(f"Bajando las estimaciones de los analistas de {len(lista) + len(otros)} empresas (Yahoo)...")
    estim, fallas = _estimaciones(lista + otros)
    res = calcular_todo(lista + otros, cache, paquetes, archivo, splits, divs, precios, estim)
    pares = [(res[t]["score"], SSD[t]) for t in lista if res.get(t) and res[t]["score"] is not None and SSD[t] is not None]
    lin = [f"CALIBRACIÓN DEL SCORE DE SEGURIDAD DEL DIVIDENDO contra Simply Safe Dividends ({dt.datetime.now():%d/%m/%Y %H:%M})",
           f"Método v0.2 (aprobado + 3 ajustes del 10/11/2026). Scores de SSD del {FECHA_SSD}.", ""]
    lin += [f"!! {a}" for a in avisos] + ([""] if avisos else [])
    if pares:
        n = len(pares)
        mae = sum(abs(a - b) for a, b in pares) / n
        misma = sum(1 for a, b in pares if _cat_n(a) == _cat_n(b))
        lejos = sum(1 for a, b in pares if abs(_cat_n(a) - _cat_n(b)) >= 2)
        sp = _spearman([a for a, _ in pares], [b for _, b in pares])
        lin += [f"Empresas comparadas: {n}", f"Diferencia media con SSD: {mae:.1f} puntos", f"Misma categoría que SSD: {misma} de {n}",
                f"A dos categorías o más: {lejos}", f"Parecido en el orden (1 = el mismo orden, 0 = nada que ver): {sp:.2f}" if sp is not None else "", ""]
    lin.append(f"{'Empresa':8}{'SSD':>5}{'Nuestro':>9}{'Dif':>5}  {'Categoría nuestra / SSD':28} P1   P2   P3   P4   P5   Años est.  Notas")
    for t in lista:
        r = res.get(t)
        if not r:
            continue
        ssd = SSD[t]
        cat_s = SD.categoria(ssd)[0] if ssd is not None else "sin score"
        dif = (r["score"] - ssd) if (r["score"] is not None and ssd is not None) else None
        p = r["pilares"]
        pp = "  ".join(f"{p[k][0]:>4.1f}" if k in p else "  — " for k in (1, 2, 3, 4, 5))
        lin.append(f"{t:8}{str(ssd if ssd is not None else '—'):>5}{str(r['score'] if r['score'] is not None else '—'):>9}{str(dif if dif is not None else ''):>5}  "
                   f"{(r['categoria'] or '—') + ' / ' + cat_s:28} {pp}  {r.get('anios_estados', ''):10} {', '.join(r['notas'] + [c for c, _ in r['topes']])}")
    lin += ["", "DETALLE (conclusión que vería el usuario e historial del dividendo)", ""]
    for t in lista:
        r = res.get(t)
        if not r:
            continue
        h = r.get("historial")
        hist = (f"años sin recortar {h['anios_sin_recorte']}, pagando {h['anios_pagando']}, aumentos en 12 años {h['aumentos_12']}, "
                f"2008-09: {h['crisis_0809']}, 2020: {h['crisis_2020']}, pagos por año {h['frecuencia']}") if h else "sin historial"
        tend = next((v for v in r["variables"] if v["clave"] == "tendencia"), None)
        lin += [f"■ {t} ({r['score']}): {r['conclusion'] or '—'}", f"   Historial: {hist}",
                f"   Tendencia: {'%+.1f%% (%s)' % (tend['valor'], tend['fuente']) if tend else 'sin dato'}", ""]
    if fallas:
        lin += [f"Sin estimación de analistas en Yahoo: {', '.join(fallas)}"]
    texto = "\n".join(lin) + "\n"
    with open(os.path.join(AQUI, "resultados_calibracion_dividendo.txt"), "w", encoding="utf-8") as f:
        f.write(texto)
    with open(os.path.join(AQUI, "data", "calibracion_dividendo.json"), "w", encoding="utf-8") as f:
        json.dump({"fecha": dt.date.today().isoformat(), "ssd": SSD, "resultados": res}, f, ensure_ascii=False, default=str)
    print("\n" + texto)
    print("Listo. Mandame resultados_calibracion_dividendo.txt y data/calibracion_dividendo.json")


if __name__ == "__main__":
    main(sys.argv[1:])
