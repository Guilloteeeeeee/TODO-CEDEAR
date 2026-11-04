"""
Control de cobertura: compara la lista oficial de CEDEARs de BYMA (data/byma_cedears.json) con lo que carga la app
(data/cedears.csv para empresas y data/etfs.csv para ETFs) y dice, de cada CEDEAR que NO esta, POR QUE no esta.
Ningun CEDEAR puede quedar ausente sin figurar abajo con su motivo: si aparece uno sin motivo, el control avisa (y la prueba falla).
Uso:  python control_cobertura.py        (escribe tambien cobertura_byma.txt)
"""
import csv, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))

# simbolo de BYMA -> ticker con el que la app lo conoce
ALIAS = {"BK": "BNY", "MMC": "MRSH", "BNG": "BG", "BRKB": "BRK-B", "BA.C": "BAC", "BBV": "BBVA"}

# Pendientes de cargar (se arman de a 50, Guille revisa el sector de cada una)
PENDIENTES = {
    "Tanda 3 en adelante (a revisar una por una)": "AAP ABEV ADGO AEG AKO.B AOCA ARCO ASR AUY BAK BB BBD BIOX BMNR BRFS BSBR CAAP CAJ CAR CBRD CLS CX E EBR ELP ERJ FMCC FNMA GGB GLNG GLOB GPRK HNPIY HUT HWM IREN JMIA JOYY KEEL KEP KOFM LAR LFC LND MFG MUX NG NMR NOKA ONDS ORAN PAC PBI PKS PSO PTR RIOT SATL SDA SHPW SID SNP SPCE SUZ TEN TIIAY TIMB TTM TV TXR UGP VIST VIV VXX WBO XROX YZCA".split(),
}
# No se cargan (o se cargan distinto), con el motivo
EXCLUIDAS = {
    "Segundo ticker de una empresa que ya tiene ficha (se muestra como segunda línea en la ficha del ADR)":
        "ABEV3 BBDC3 ITUB3 CSNA3 SUZB3 TIMS3 VALE3 VIVT3 PETR3".split(),
    "Ya no cotiza (cerrada, comprada o fusionada)": "AABA TWTR CS SI EA WBA".split(),
    "Empresa rusa: sin datos confiables": "ATAD LKOD OGZD NLM MBT".split(),
    "Símbolo mal escrito en la lista de BYMA (hay que confirmarlo con BYMA)": "TRVV NYSE UN".split(),
    "Acción que cotiza solo en Brasil (reporta en reales, otra fuente de datos)": "BBAS3 BPA11 HAPV3 LREN3 MGLU3 NATU3 PRIO3 RCTB4 RENT3 SBSP3 WEGE3".split(),
    "Cotiza en bolsa de Europa o Asia (otra moneda, otra fuente de datos)": "ADS BAS BAYN BSN DTEA EOAN MBG NEC1 SKHY SMSN HHPD PCRF NSAN".split(),
}
# En la app y no en el PDF del 16/09/2026 (nuevos CEDEARs que entran): se dejan
EXTRAS_APP = {"NU", "JMOM", "ILIT", "REMX", "DBB", "DBA", "WEAT"}


def _leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def calcular():
    byma = json.load(open(os.path.join(AQUI, "data", "byma_cedears.json"), encoding="utf-8"))["cedears"]
    en_app = set()
    for r in _leer_csv(os.path.join(AQUI, "data", "cedears.csv")):
        en_app |= {(r.get("ticker") or "").strip().upper(), (r.get("simbolo") or "").strip().upper()}
    try:
        for r in _leer_csv(os.path.join(AQUI, "data", "etfs.csv")):
            en_app |= {v.strip().upper() for k, v in r.items() if k and v and k.lower() in ("ticker", "simbolo")}
    except Exception:
        pass
    cargadas, motivo, sin_motivo = [], {}, []
    pend = {t: k for k, v in PENDIENTES.items() for t in v}
    excl = {t: k for k, v in EXCLUIDAS.items() for t in v}
    for s in byma:
        if s in en_app or ALIAS.get(s) in en_app:
            cargadas.append(s)
        elif s in pend:
            motivo[s] = "Pendiente: " + pend[s]
        elif s in excl:
            motivo[s] = "No se carga: " + excl[s]
        else:
            sin_motivo.append(s)
    return byma, cargadas, motivo, sin_motivo


def texto():
    byma, cargadas, motivo, sin_motivo = calcular()
    pend = [s for s, m in motivo.items() if m.startswith("Pendiente")]
    excl = [s for s, m in motivo.items() if m.startswith("No se carga")]
    out = [f"Lista de BYMA: {len(byma)} CEDEARs. En la app: {len(cargadas)}. Pendientes de cargar: {len(pend)}. No se cargan (con motivo): {len(excl)}.",
           f"SIN MOTIVO (hay que revisarlos): {len(sin_motivo)} {sin_motivo}", ""]
    for m in sorted(set(motivo.values())):
        ts = sorted(s for s, v in motivo.items() if v == m)
        out.append(f"- {m} ({len(ts)}): {' '.join(ts)}")
    return "\n".join(out)


if __name__ == "__main__":
    t = texto()
    print(t)
    try:
        open(os.path.join(AQUI, "cobertura_byma.txt"), "w", encoding="utf-8").write(t + "\n")
    except Exception:
        pass
    sys.exit(0 if not calcular()[3] else 1)
