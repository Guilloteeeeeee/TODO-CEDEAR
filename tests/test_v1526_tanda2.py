"""Tanda 2 (v1.5.26): las 50 empresas están cargadas con el grupo que corrigió Guille en su Excel. Correr: python tests/test_v1526_tanda2.py"""
import os, sys, csv
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ); os.chdir(RAIZ)
from config.sectors import TICKER_TO_SECTOR, TICKER_UNIVERSE
from config.industrias import INDUSTRIA
from ui.logos import DOMINIOS
from ui import noticias as N
from config.mercados import ADR, NO_ADR
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)

T2 = "SPCX HOOD MSTR CRWV RBLX RKLB OKLO NBIS FSLR XPEV NIO SE TCOM STNE XP PAGS EFX ZM UPST HIMS PATH AI ETSY TEM ASTS RGTI B KGC HMY GFI PAAS CDE HL MP NXE LAC FMX STLA HMC ERIC PHG NGG GT HOG ANF URBN YELP TRIP XYZ KB".split()
# grupo final (propuesta de Claude + correcciones naranjas de Guille, 04/11/2026)
GRUPO = {
 "Industrial": "SPCX RKLB EFX", "Bancos y seguros": "HOOD XP KB", "Pagos y datos": "UPST",
 "Software y nube": "MSTR CRWV ZM PATH AI STNE PAGS XYZ", "Comunicación": "RBLX NBIS YELP",
 "Utilities": "OKLO NGG", "Semiconductores": "FSLR", "Hardware y servicios TI": "RGTI ERIC ASTS", "Energía": "NXE", "Consumo Básico": "FMX",
 "Salud": "HIMS TEM PHG", "Materiales Básicos": "B KGC HMY GFI PAAS CDE HL MP LAC",
 "Consumo Discrecional": "XPEV NIO SE TCOM ETSY STLA HMC GT HOG ANF URBN TRIP",
}
esperado = {t: g for g, ts in GRUPO.items() for t in ts.split()}
chk(sorted(esperado) == sorted(T2), "la tabla del test no cubre las 50 de la tanda 2")
for t in T2:
    chk(TICKER_TO_SECTOR.get(t) == esperado[t], f"{t}: grupo {TICKER_TO_SECTOR.get(t)} en vez de {esperado[t]}")
    chk(t in INDUSTRIA, f"{t} sin industria"); chk(t in DOMINIOS, f"{t} sin dominio para el logo")
    chk(t in N.ALIAS, f"{t} sin nombre para las noticias")
    if t not in ("SPCX","HOOD","MSTR","CRWV","RBLX","RKLB","OKLO","FSLR","EFX","ZM","UPST","HIMS","PATH","AI","ETSY","TEM","ASTS","RGTI","MP","CDE","HL","LAC","GT","HOG","ANF","URBN","YELP","TRIP","XYZ"):
        chk(t in ADR or t in NO_ADR, f"{t} (extranjera) sin marcar como ADR / no ADR")
# las correcciones de Guille (naranjas) que cambiaron el grupo propuesto
for t, g in (("CRWV", "Software y nube"), ("NBIS", "Comunicación"), ("STNE", "Software y nube"), ("PAGS", "Software y nube"), ("XYZ", "Software y nube"),
             ("EFX", "Industrial"), ("ASTS", "Hardware y servicios TI"), ("TRIP", "Consumo Discrecional")):
    chk(TICKER_TO_SECTOR.get(t) == g, f"corrección de Guille: {t} va en {g}")
filas = list(csv.DictReader(open("data/cedears.csv", encoding="utf-8-sig"), delimiter=";"))
tk = [r["ticker"] for r in filas]
chk(len(tk) == len(set(tk)), "tickers repetidos en cedears.csv")
chk(all(t in tk for t in T2), "falta alguna de la tanda 2 en cedears.csv")
r = {x["ticker"]: x["ratio"] for x in filas}
for t, v in (("SPCX", "50"), ("XP", "4"), ("NXE", "1"), ("SE", "32"), ("KGC", "1")):
    chk(r.get(t) == v, f"ratio de {t}: {r.get(t)} en vez de {v}")
chk(sum(len(v) for v in TICKER_UNIVERSE.values()) == len({t for v in TICKER_UNIVERSE.values() for t in v}), "una empresa figura en dos grupos")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
