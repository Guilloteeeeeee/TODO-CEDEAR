"""
v1.5.49: PRUEBA PILOTO de la SEC (pedido de Guille, 08/11/2026). ¿Sirve la SEC para sumar años hacia atrás al archivo histórico propio?

Baja de la SEC (gratis: data.sec.gov, «companyfacts») los números de los informes anuales de 10 empresas bien distintas y los compara, año por año,
con los de Yahoo que ya tenemos (data/paquetes_yahoo.json). Escribe:
- resultados_piloto_sec.txt: cuántos años trae cada dato, desde qué año, y cuánto coincide con Yahoo;
- data/sec_piloto.json: los números bajados (para revisarlos).
NO cambia nada de la app ni del archivo histórico. Es solo para decidir si vale la pena.

La SEC pide (https://www.sec.gov/os/accessing-edgar-data) que cada programa se identifique con un nombre y un mail de contacto, y que no haga más
de 10 pedidos por segundo. Este hace uno cada medio segundo. El mail se escribe la primera vez (o en la variable SEC_CONTACTO) y queda solo en tu PC.

Uso: python piloto_sec.py            (las 10 del piloto)
     python piloto_sec.py KO PEP     (otras)
"""
import datetime as dt
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

PILOTO = ["KO", "MSFT", "AAPL", "JPM", "O", "NFLX", "MELI", "NVO", "TSM", "BABA"]
ARCH_CONTACTO = os.path.join(AQUI, ".sec_contacto")
PAUSA = 0.5

# Concepto de la SEC -> nuestro rótulo. Se prueban en orden; el primero con datos gana. us-gaap = normas de EE.UU.; ifrs-full = internacionales.
CONCEPTOS = {
    "Ingresos": [("us-gaap", "Revenues"), ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"), ("us-gaap", "SalesRevenueNet"),
                 ("us-gaap", "RevenuesNetOfInterestExpense"), ("ifrs-full", "Revenue")],
    "Resultado operativo": [("us-gaap", "OperatingIncomeLoss"), ("ifrs-full", "ProfitLossFromOperatingActivities")],
    "Resultado neto": [("us-gaap", "NetIncomeLoss"), ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"), ("ifrs-full", "ProfitLoss")],
    "Ganancia por acción (diluida)": [("us-gaap", "EarningsPerShareDiluted"), ("ifrs-full", "DilutedEarningsLossPerShare")],
    "Activo total": [("us-gaap", "Assets"), ("ifrs-full", "Assets")],
    "Patrimonio neto": [("us-gaap", "StockholdersEquity"), ("ifrs-full", "EquityAttributableToOwnersOfParent"), ("ifrs-full", "Equity")],
    "Flujo de efectivo operativo": [("us-gaap", "NetCashProvidedByUsedInOperatingActivities"), ("ifrs-full", "CashFlowsFromUsedInOperatingActivities")],
    "Inversión en activos fijos (CAPEX)": [("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
                                           ("ifrs-full", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities")],
    "Dividendos pagados": [("us-gaap", "PaymentsOfDividendsCommonStock"), ("us-gaap", "PaymentsOfDividends"),
                           ("ifrs-full", "DividendsPaidClassifiedAsFinancingActivities")],
}
INSTANTANEOS = {"Activo total", "Patrimonio neto"}      # se miden a una fecha (balance), no durante un año
FORMULARIOS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")


def _contacto():
    c = os.environ.get("SEC_CONTACTO")
    if not c and os.path.exists(ARCH_CONTACTO):
        c = open(ARCH_CONTACTO, encoding="utf-8").read().strip()
    if not c:
        c = input("La SEC pide un nombre y un mail de contacto (por ejemplo: TodoCedears tu@mail.com): ").strip()
        with open(ARCH_CONTACTO, "w", encoding="utf-8") as f:
            f.write(c)
    return c


def _get(url, ua):
    import requests
    r = requests.get(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}, timeout=60)
    r.raise_for_status()
    return r.json()


def anuales(facts, rotulo):
    """{año: (valor, moneda, concepto, fecha fin, formulario, presentado)} de los informes anuales. Si un año aparece en varios informes (cada informe
    repite los años anteriores, a veces corregidos), gana el presentado más nuevo. Las empresas cambian de concepto con los años (por ejemplo, las
    ventas pasaron de SalesRevenueNet a RevenueFromContractWithCustomer… en 2018): se usa el primero de la lista que tenga ese año."""
    out = {}
    for tax, concepto in CONCEPTOS[rotulo]:
        c = ((facts.get("facts") or {}).get(tax) or {}).get(concepto)
        if not c:
            continue
        este = {}
        for unidad, filas in (c.get("units") or {}).items():
            for f in filas:
                if f.get("form") not in FORMULARIOS or f.get("val") is None:
                    continue
                fin = f.get("end")
                if rotulo not in INSTANTANEOS:
                    ini = f.get("start")
                    if not ini:
                        continue
                    dias = (dt.date.fromisoformat(fin) - dt.date.fromisoformat(ini)).days
                    if not 350 <= dias <= 380:      # solo años completos (no trimestres)
                        continue
                anio = int(fin[:4])
                prev = este.get(anio)
                if not prev or f.get("filed", "") > prev[5]:
                    este[anio] = (float(f["val"]), unidad.split("/")[0], f"{tax}:{concepto}", fin, f.get("form"), f.get("filed", ""))
        for anio, v in este.items():
            out.setdefault(anio, v)
    return out


def _yahoo(ticker):
    try:
        from data import paquetes_yahoo as PY, af_tablas as T
        e = (PY.cargar()[0].get(ticker) or {}).get("estados") or {}
        grupos = {"Ingresos": "resultados", "Resultado operativo": "resultados", "Resultado neto": "resultados",
                  "Ganancia por acción (diluida)": "resultados", "Activo total": "balance", "Patrimonio neto": "balance",
                  "Flujo de efectivo operativo": "flujo", "Inversión en activos fijos (CAPEX)": "flujo", "Dividendos pagados": "flujo"}
        return {r: {int(a): v for a, v in T._serie(e, g, r).items() if not isinstance(a, str) and v is not None} for r, g in grupos.items()}, e.get("moneda")
    except Exception:  # noqa: BLE001
        return {}, None


def main(tickers=None):
    tickers = [t.upper() for t in (tickers or PILOTO)]
    ua = _contacto()
    print("Bajando la lista de empresas de la SEC...")
    mapa = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in _get("https://www.sec.gov/files/company_tickers.json", ua).values()}
    time.sleep(PAUSA)
    lineas, guardado = [f"PRUEBA PILOTO SEC ({dt.datetime.now():%d/%m/%Y %H:%M}) — {len(tickers)} empresas", ""], {}
    for t in tickers:
        cik = mapa.get(t.replace("-", "."), mapa.get(t))
        if not cik:
            lineas += [f"■ {t}: no figura en la lista de la SEC (no presenta informes ahí).", ""]
            continue
        try:
            facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", ua)
        except Exception as ex:  # noqa: BLE001
            lineas += [f"■ {t}: error al bajar ({ex})", ""]
            continue
        time.sleep(PAUSA)
        yh, mon_y = _yahoo(t)
        lineas.append(f"■ {t} — {facts.get('entityName')} (CIK {cik})")
        guardado[t] = {}
        for r in CONCEPTOS:
            a = anuales(facts, r)
            guardado[t][r] = {str(k): list(v) for k, v in sorted(a.items())}
            if not a:
                lineas.append(f"   {r}: SIN DATO en la SEC")
                continue
            anios = sorted(a)
            mon = a[anios[-1]][1]
            comunes = [y for y in anios if y in (yh.get(r) or {})]
            iguales = [y for y in comunes if yh[r][y] and abs(a[y][0] - yh[r][y]) / abs(yh[r][y]) <= 0.02]
            dif = [f"{y}: SEC {a[y][0]:,.2f} vs Yahoo {yh[r][y]:,.2f}" for y in comunes if y not in iguales][:2]
            lineas.append(f"   {r}: {len(anios)} años ({anios[0]}–{anios[-1]}, {mon}; concepto {a[anios[-1]][2]}); "
                          f"coincide con Yahoo en {len(iguales)} de {len(comunes)} años" + (f" — diferencias: {'; '.join(dif)}" if dif else ""))
        if mon_y:
            lineas.append(f"   (Yahoo informa en {mon_y})")
        lineas.append("")
        print(f"  {t} ok")
    with open(os.path.join(AQUI, "resultados_piloto_sec.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    with open(os.path.join(AQUI, "data", "sec_piloto.json"), "w", encoding="utf-8") as f:
        json.dump({"fecha": dt.date.today().isoformat(), "datos": guardado}, f, ensure_ascii=False)
    print("\n" + "\n".join(lineas))
    print("Listo. Mandame resultados_piloto_sec.txt y data/sec_piloto.json")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
