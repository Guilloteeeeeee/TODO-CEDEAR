"""Tanda 3 (v1.5.37): 60 empresas cargadas (grupo según el Excel de Guille del 06/11/2026, ratio de BYMA, industria, logo, ADR, noticias, Damodaran). python tests/test_v1537_tanda3.py"""
import os, sys, csv
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ); os.chdir(RAIZ)
from config.sectors import TICKER_TO_SECTOR, TICKER_UNIVERSE
from config.industrias import INDUSTRIA
from ui.logos import DOMINIOS
from ui import noticias as N
from config.mercados import ADR, NO_ADR
from data import damodaran_mapa as M, cedears as C
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
T3 = ("AAP ABEV AGRO AEG AKO-B ARCO ASR BAK BB BBD BIOX BMNR BSBR CAAP CAR CLS CX E ELPC EMBJ GGB GLNG GLOB GPRK HUT IREN JMIA JOYY KEEL KEP KOF LAR LND MFG MUX NG NMR NOK ONDS PAC PBI PKX "
      "RIOT SATL SBS SDA SID SPCE SUZ TS TIMB TV TX UGP VIST VIV WB XRX TRV AXIAY").split()
chk(len(T3) == 60 and len(set(T3)) == 60, "son 60 distintas")
filas = list(csv.DictReader(open("data/cedears.csv", encoding="utf-8-sig"), delimiter=";"))
tk = [r["ticker"] for r in filas]
chk(len(tk) == len(set(tk)), "tickers repetidos en cedears.csv")
for t in T3:
    chk(t in tk, f"{t} falta en cedears.csv"); chk(t in TICKER_TO_SECTOR, f"{t} sin grupo"); chk(t in INDUSTRIA, f"{t} sin industria")
    chk(t in DOMINIOS, f"{t} sin dominio"); chk(t in N.ALIAS, f"{t} sin alias de noticias"); chk(t in M.MAPA, f"{t} sin industria de Damodaran")
    chk(sum(t in x for x in TICKER_UNIVERSE.values()) == 1, f"{t} en mas de un grupo")
# decisiones de Guille (06/11/2026)
for t, g in (("IREN", "Pagos y datos"), ("XRX", "Industrial"), ("EMBJ", "Industrial"), ("ELPC", "Utilities"), ("SBS", "Utilities"), ("AXIAY", "Utilities"),
             ("KEEL", "Hardware y servicios TI"), ("TX", "Materiales Básicos"), ("E", "Energía"), ("TRV", "Bancos y seguros")):
    chk(TICKER_TO_SECTOR.get(t) == g, f"{t} va en {g}")
# simbolos de BYMA y ratios
sim = {r["ticker"]: r["simbolo"] for r in filas}
for t, s in (("AGRO", "ADGO"), ("AKO-B", "AKO.B"), ("KOF", "KOFM"), ("NOK", "NOKA"), ("PKX", "PKS"), ("TS", "TEN"), ("TX", "TXR"), ("WB", "WBO"), ("XRX", "XROX"), ("TRV", "TRVV"), ("AXIAY", "AXIA")):
    chk(sim.get(t) == s, f"{t}: simbolo BYMA {s}")
rat = {r["ticker"]: r["ratio"] for r in filas}
chk(rat["AAP"] == "14:1" and rat["ABEV"] == "1:3" and rat["TRV"] == "6:1" and rat["E"] == "4:1" and rat["EMBJ"] == "1:1", "ratios de BYMA")
chk(rat["ELPC"] == "" and rat["AXIAY"] == "", "ELPC y AXIAY quedan sin ratio hasta confirmarlo (no se inventa)")
chk(rat["SBS"] == "1:2", "SBS: ratio 1:2 según Rava (07/11/2026; el CCL implícito, 1.671,88, es coherente)")
# no se cargan
for t in ("BRFS", "CAJ", "CBRD", "EBR", "AOCA", "AUY", "FMCC", "FNMA", "HNPIY", "SHPW", "YZCA", "LFC", "PTR", "SNP", "ORAN", "TTM", "PSO", "TIIAY", "HWM", "DJNJ3"):
    chk(t not in tk, f"{t} NO debe estar cargada")
chk(TICKER_TO_SECTOR.get("HWM") == "Industrial", "HWM sigue en su grupo (ya estaba)")
extr = [t for t in T3 if t in ADR or t in NO_ADR]
chk(len(extr) == 45, f"extranjeras marcadas ADR / no ADR: {len(extr)}")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
