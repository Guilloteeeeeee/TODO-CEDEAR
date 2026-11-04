"""Cada empresa de la app tiene industria de Damodaran, con el nombre EXACTO de la planilla, y las extranjeras la región correcta. Correr: python tests/test_damodaran_mapa.py"""
import os, re, sys, json
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ); os.chdir(RAIZ)
from data import damodaran_mapa as M
from config.sectors import TICKER_UNIVERSE
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
nombres = set()
for l in open("data/damodaran/margin.txt", encoding="utf-8", errors="replace"):
    c = l.split("\t")
    if len(c) > 3 and re.match(r"^[A-Za-z]", c[0]) and c[1].strip().isdigit(): nombres.add(c[0].strip())
chk(len(nombres) >= 90, f"no se pudo leer la lista de industrias ({len(nombres)})")
chk(not [i for i in set(M.MAPA.values()) if i not in nombres], f"industrias que no existen en la planilla: {sorted(set(M.MAPA.values()) - nombres)}")
tk = sorted({t for v in TICKER_UNIVERSE.values() for t in v})
chk(not [t for t in tk if t not in M.MAPA], f"empresas sin industria de Damodaran: {[t for t in tk if t not in M.MAPA]}")
chk(not [t for t in M.MAPA if t not in tk], f"industria asignada a una empresa que no está en la app: {[t for t in M.MAPA if t not in tk]}")
for t, r in (("BCS", "europa"), ("LYG", "europa"), ("VOD", "europa"), ("AMX", "emergentes"), ("BIDU", "emergentes"), ("JD", "emergentes"), ("CCJ", "aus_nz_canada")):
    chk(M.REGION.get(t) == r, f"{t} tendría que comparar con {r}")
chk(M.MAPA.get("NTRA") == "Healthcare Products" and M.MAPA.get("MRNA") == "Drugs (Biotechnology)", "MRNA / NTRA")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
