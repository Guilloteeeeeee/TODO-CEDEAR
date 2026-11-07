"""v1.5.40: los 30 ETFs de la lista de Rava que no tienen CEDEAR (acceso: solo por mesa del broker)."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
NUEVOS = "EIDO EWG EWH EWQ EWT EWU EWW EZA EZU INDA MCHI VWO FXA FXB FXC FXE FXF FXY UUP BNO CPER DBC PALL PPLT UNG BITO BITQ ETHE FBTC GBTC".split()
import data.etfs as E
from ui import etf_iconos, etfs as UE
d = E.cargar(); pt = {e["ticker"]: e for e in d}
chk(len(d) == 96 and len(set(pt)) == 96, f"96 ETFs sin repetir ({len(d)})")
for t in NUEVOS:
    e = pt.get(t)
    chk(e is not None, f"{t} cargado")
    if not e: continue
    chk(e["acceso"] == "Solo por mesa del broker", f"{t}: acceso")
    chk(not e["ratio"], f"{t}: sin ratio (no tiene CEDEAR)")
    nom = e["icono"].replace("svg:", "")
    chk(nom in etf_iconos.ICONOS or nom in ("bitcoin", "ethereum"), f"{t}: icono existe")
    chk(e["categoria"] and e["descripcion"] and e["nombre"] and e["gestor"], f"{t}: campos básicos")
chk(sum(1 for e in d if e["acceso"] == "CEDEAR") == 66, "los 66 con CEDEAR siguen igual")
chk({pt[t]["categoria"] for t in "FXA FXB FXC FXE FXF FXY UUP".split()} == {"Monedas"}, "monedas en categoría Monedas")
chk(all(t in UE.SIN_PAISES for t in "FXA UUP BNO CPER DBC PALL PPLT UNG BITO ETHE FBTC GBTC".split()), "sin torta de países donde no hay empresas")
chk(pt["EWG"]["pais"] == "Alemania" and pt["EWT"]["pais"] == "Taiwán", "país único")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
