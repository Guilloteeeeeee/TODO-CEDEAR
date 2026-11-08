"""v1.5.44: Ideas de Inversión (5 mosaicos y listas), Dividend Yield en la tabla de ETFs, cita de la gerencia en los informes."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
import pandas as pd
from ui import ideas as I, etfs as UE, ficha as F, af_pdf
from data import analisis_fundamental as AF, etfs as E, af_v4 as V
df = pd.DataFrame(json.load(open("data/cache_datos.json", encoding="utf-8"))["data"])
cal = {t: a.get("calidad") for t, a in AF.cargar()[0].items()}
ey = json.load(open("data/etfs_yahoo.json", encoding="utf-8"))["datos"]
L = I.cargar_listas()
chk(all(k in L and L[k].get("fuente") for k in ("aristocratas", "reyes", "aspirantes")) and L["aristocratas"].get("anios") and L["aspirantes"].get("tickers"), "listas con fuente")
m = {k: I.miembros(k, df, cal, E.cargar(), ey, L) for k in ("aristocratas", "reyes", "aspirantes", "altos", "fundamentales")}
chk(len(m["aristocratas"]) >= 20 and all(x["dato"] >= 25 for x in m["aristocratas"]), "aristócratas: 25 años o más")
chk(len(m["reyes"]) >= 10 and all(x["dato"] >= 50 for x in m["reyes"]), "reyes: 50 años o más")
chk(m["aspirantes"] and not ({x["ticker"] for x in m["aspirantes"]} & ({x["ticker"] for x in m["aristocratas"]} | {x["ticker"] for x in m["reyes"]})), "aspirantes: ni aristócratas ni reyes")
chk(all(x["dato"] >= 0.04 for x in m["altos"]) and any(x["tipo"] == "etf" for x in m["altos"]), "dividendos altos: 4% o más, con ETFs")
chk(all(x["tipo"] == "empresa" for k in ("aristocratas", "reyes", "aspirantes", "fundamentales") for x in m[k]), "en las demás listas solo empresas")
chk(all(x["row"]["categoria"] in I.INFRAVALORADAS and x["dato"] in I.CALIDADES_FUERTES for x in m["fundamentales"]), "fundamentales fuertes: calidad alta e infravalorada")
h = I.mosaicos_html({k: len(v) for k, v in m.items()})
chk(h.count('class="id-t"') == 5 and "diamante.png" in h and "\n<path" not in h, "5 mosaicos con dibujo, SVG en una sola línea")
chk(os.path.isfile("static/ideas/diamante.png"), "imagen del diamante con lupa")
lh = I.lista_html("altos", m["altos"], L, celda_empresa=lambda r: r["ticker"], celda_sector=lambda r: "", celda_categoria=lambda r: "")
chk("id-tab" in lh and "Información con fines educativos" in lh, "lista con tabla y aviso")
app = open("app.py", encoding="utf-8").read()
chk("def render_ideas" in app and "Estamos armando esta sección" not in app, "la página Ideas ya no es un aviso")
chk(("dy", "Div. Yield", 1.0) in UE.COLUMNAS and UE.dy_texto({"rendimiento": 1.0}) == "1,00%" and UE.dy_texto({"rendimiento": 4.0, "precio": 100}, 200) == "2,00%" and "—" in UE.dy_texto({}), "Dividend Yield en la tabla de ETFs")
D = AF.cargar()[0]
for t in ("AMGN", "ANET", "SHOP", "PFE", "QCOM", "MCD", "NVO", "COP"):
    ci = D[t].get("cita") or {}
    txt = json.dumps(D[t].get("secciones"), ensure_ascii=False)
    chk(ci.get("texto") and ci.get("autor") and ci.get("url", "").startswith("http") and ci["texto"][:25] not in txt, f"{t}: cita destacada y no repetida en el texto")
chk("af-cita" in F.cita_html(D["NVO"]["cita"]) and F.cita_html(None) == "", "recuadro de la cita en la ficha")
r, pr = V.validar(D["NVO"]); chk(not pr and "cita" in r, "el validador conserva la cita")
pr_txt = open("data/prompt_analisis_fundamental_v4.txt", encoding="utf-8").read()
chk("CITA DE LA GERENCIA" in pr_txt and '"cita"' in pr_txt, "regla de la cita en el prompt")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
