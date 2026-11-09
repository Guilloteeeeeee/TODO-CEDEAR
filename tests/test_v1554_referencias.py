"""v1.5.54: referencias de respaldo de GuruFocus (PER, P/FCF, P/B, P/S) y Finviz (PEG) por industria, con franja anti-disparates;
EV/EBITDA con la app; PER de Boeing descartado hasta enero de 2027."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from data import referencias_externas as RX
T = RX.tablas()
chk(len(T["gurufocus"].get("industrias", {})) == 55 and len(T["gurufocus"].get("sectores", {})) >= 11, "tabla de GuruFocus (55 industrias, 11 sectores)")
chk(len(T["finviz"].get("industrias", {})) == 144 and len(T["finviz"].get("sectores", {})) == 11, "tabla de Finviz (144 industrias, 11 sectores)")
chk(all(v in T["gurufocus"]["industrias"] for v in RX.INDUSTRIA_GURUFOCUS.values()), "cada industria de Yahoo apunta a un grupo que existe en GuruFocus")
from data import fichas
F, _ = fichas.cargar()
inds = {v.get("industria_yahoo") for v in F.values() if v.get("industria_yahoo")}
chk(inds <= set(RX.INDUSTRIA_GURUFOCUS), f"todas las industrias de la app tienen su grupo de GuruFocus ({sorted(inds - set(RX.INDUSTRIA_GURUFOCUS))})")
# franja
chk(RX.en_franja("per", 23.7) and not RX.en_franja("per", 64.24) and not RX.en_franja("p_fcf", 210.25) and not RX.en_franja("peg", 22.24)
    and not RX.en_franja("per", None), "la franja deja afuera los disparates")
CL = {"UPST": ("Financial Services", "Credit Services"), "HIMS": ("Healthcare", "Drug Manufacturers - Specialty & Generic"),
      "KEP": ("Utilities", "Utilities - Regulated Electric"), "XX": (None, None)}
app = {"per": 26.88, "p_fcf": 26.17, "ev_ebitda": 24.61, "peg": 1.1}
r, o = RX.referencias("UPST", app, CL)
chk(r["per"] == 8.64 and o["per"] == "industria GuruFocus", "PER: mediana de la industria en GuruFocus")
chk(r["p_fcf"] == 11.37 and o["p_fcf"] == "sector GuruFocus", "P/FCF de la industria fuera de franja (4,66) → sector de GuruFocus")
chk(r["ev_ebitda"] == 24.61 and o["ev_ebitda"] == "app", "EV/EBITDA: siempre la referencia de la app")
chk(o["peg"] == "industria Finviz" and r["peg"] == T["finviz"]["industrias"]["Credit Services"]["peg"], "PEG: Finviz")
r, o = RX.referencias("HIMS", {}, CL)
chk(o["per"] == "sector GuruFocus" and r["per"] == 24.62, "sin PER de la industria en GuruFocus → su sector")
r, o = RX.referencias("KEP", {}, CL)
chk("p_fcf" not in r, "servicios públicos: P/FCF disparate en GuruFocus (falta) y sin referencia de la app → no se usa")
chk(RX.referencias("XX", app, CL) == (app, {m: "app" for m in app}), "empresa sin industria conocida: todo como antes")
# score
import pandas as pd
from scoring import engine as E
from config.sectors import METRICAS_EXCLUIDAS
df = pd.DataFrame(json.load(open("data/cache_datos.json", encoding="utf-8"))["data"])
n = E.score_dataframe(df).set_index("ticker")
chk("per" in METRICAS_EXCLUIDAS.get("BA", {}) and "2027" in METRICAS_EXCLUIDAS["BA"]["per"], "PER de Boeing descartado a mano hasta enero de 2027")
chk(n.loc["BA", "detalle"]["per"]["estado"] == "descartada", "Boeing: el PER no cuenta")
chk(n.loc["UPST", "detalle"]["per"].get("referencia_origen") == "industria GuruFocus", "el detalle guarda de dónde salió la referencia")
cache = pd.DataFrame(json.load(open("data/cache_datos.json", encoding="utf-8"))["data"]).set_index("ticker")
chk(all(cache.loc[t, "categoria"] == n.loc[t, "categoria"] for t in n.index), "el cache ya está puntuado con la regla nueva")
chk(sum(1 for x in n["respaldo_sector"] if x) == 51, "51 empresas usan respaldo")
src = open("ui/ficha.py", encoding="utf-8").read()
chk("de su industria" in src, "la ficha dice «de su industria» cuando corresponde")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
