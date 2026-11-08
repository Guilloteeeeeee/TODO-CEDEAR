"""v1.5.46: tabla de competidores con las columnas de Guille, mosaicos de Ideas en orden (Reyes primero) y más arriba, cache nuevo (323)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
import pandas as pd
from config.sectors import partes_sector
from config.industrias import industria_de
from ui import ficha as F, ideas as I
from data import paquetes_yahoo as PY
c = json.load(open("data/cache_datos.json", encoding="utf-8"))
chk(len(c["data"]) == 323 and c["timestamp"].startswith("2026-11-08"), "cache del 08/11 con las 323 empresas")
df = pd.DataFrame(c["data"])
df["sector_macro"] = [partes_sector(g)[0] or "" for g in df.sector]
df["industria"] = [industria_de(t) or partes_sector(g)[1] or "" for g, t in zip(df.sector, df.ticker)]
P = PY.cargar()[0]
h = F.tab_competidores(df[df.ticker == "PG"].iloc[0].to_dict(), df, P)
for t in ("Ventas<br>(crec. 3 años)", "EPS<br>(crec. 3 años)", "Margen<br>operativo", "ROIC", "Deuda neta<br>/ EBITDA", "Dividend<br>Yield", "Score de<br>calidad", "Valoración"):
    chk(t in h, f"columna {t}")
chk(not any(x in h for x in ("<th>P/E</th>", "EV/EBITDA</th>", "<th>P/FCF</th>", "Cap. bursátil")), "sin P/E, EV/EBITDA, P/FCF ni capitalización")
chk("#15803d" in h and "#b91c1c" in h and "mejor tercio" in h, "colores relativos al grupo")
m = F.metricas_competidor(P["KO"]["estados"])
chk(abs(m["ventas"] - ((47941 / 43004) ** (1 / 3) - 1)) < 1e-6 and abs(m["eps"] - ((3.04 / 2.19) ** (1 / 3) - 1)) < 1e-6, "crecimiento 3 años de ventas y EPS de KO")
chk(m["mop"] and m["roic"] and m["dne"] is not None, "margen, ROIC y deuda de KO")
chk(F.metricas_competidor(None) == {}, "sin estados: sin números")
chk("-0.0%" not in F.tab_competidores(df[df.ticker == "JPM"].iloc[0].to_dict(), df, P), "sin «-0.0%»")
chk([x["clave"] for x in I.LISTAS] == ["reyes", "aristocratas", "aspirantes", "altos", "fundamentales"], "orden de los mosaicos")
mh = I.mosaicos_html({})
chk('class="id-top"' in mh and "Volver al inicio" in mh and mh.index("Reyes") < mh.index("Aristócratas"), "título y casita en la misma fila, Reyes primero")
app = open("app.py", encoding="utf-8").read()
chk("tab_competidores(rd, df, _paquetes_guardados()[0])" in app and "if en_quienes or en_cartera:      #" in app, "la ficha pasa los estados; en Ideas la casita va en la fila del título")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
