"""v1.5.41: informes anteriores (archivo + PDF + link), % pegado al número, gráficos en el PDF, sin «Calidad del Negocio» ni «día de descarga»."""
import json, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from data import analisis_fundamental as AF, paquetes_yahoo as PY
from ui import af_pdf, ficha
import generar_analisis_fundamental as G
af = json.load(open("data/analisis_fundamental.json", encoding="utf-8"))["datos"]["AMGN"]
ants = AF.anteriores("AMGN")
chk(ants and ants[0]["fecha"] == "31/10/2026" and ants[0]["url"] == "app/static/informes/AMGN_2026-10-31.pdf", "AMGN tiene su informe anterior")
chk(os.path.isfile(os.path.join(AF.CARPETA_INFORMES, "AMGN_2026-10-31.pdf")), "PDF anterior guardado en static/informes")
# archivar en carpeta temporal: no duplica la misma fecha
with tempfile.TemporaryDirectory() as d:
    r = os.path.join(d, "a.json")
    AF.archivar("ZZZ", {"fecha": "01/02/2026", "titulo": "Uno"}, b"%PDF-1", r, d)
    AF.archivar("ZZZ", {"fecha": "01/02/2026", "titulo": "Uno bis"}, b"%PDF-1", r, d)
    AF.archivar("ZZZ", {"fecha": "05/03/2026", "titulo": "Dos"}, b"%PDF-1", r, d)
    L = AF.anteriores("ZZZ", r, d)
    chk([x["titulo"] for x in L] == ["Dos", "Uno bis"], f"orden y sin duplicados {L}")
chk(af_pdf.pct_pegado("subió 8 % y 30,0 %") == "subió 8% y 30,0%", "% pegado")
p = PY.cargar()[0]["AMGN"]; row = G._fila_cache("AMGN")
h = ficha.tab_analisis(row, af=af, estados=p["estados"])
chk('class="af-ant"' in h and "download=" in h, "link de descarga al informe anterior")
chk("Informes anteriores" in h, "lista de informes anteriores en la ficha")
chk(not re.search(r"\d %", h), "ficha sin espacio antes de %")
chk("Calidad del Negocio" not in h, "sin pastilla Calidad del Negocio")
chk(h.count("<svg") >= 2, "gráficos en la ficha")
b = af_pdf.pdf_analisis(af, p["estados"], row, None, p.get("dividendos"), None, "Amgen")
import subprocess
t = subprocess.run(["pdftotext", "-", "-"], input=b, capture_output=True).stdout.decode("utf-8", "replace")
chk("Informes anteriores" in t and "31/10/2026" in t, "PDF lista los informes anteriores")
chk("día de descarga" not in t and "Calidad del Negocio" not in t, "PDF sin las dos líneas que se sacaron")
chk(not re.search(r"\d %", t), "PDF sin espacio antes de %")
d0 = af_pdf._dibujo(__import__("data.af_v4", fromlist=["x"]).grafico("margen_operativo", p["estados"], row, {}, {}, None, None), 400)[0]
chk(d0 is not None, "los gráficos se dibujan en el PDF")
pr = open("data/prompt_analisis_fundamental_v4.txt", encoding="utf-8").read()
chk("REGISTRO" in pr and "remedios" in pr and "Horizon (2023)" in pr and '"8%"' in pr, "reglas nuevas en el prompt")
# v1.5.42: gráficos de empresas con estados en otra moneda
from data import af_v4 as V
P = PY.cargar()[0]
for tk, nom in (("NVO", "coronas danesas"), ("SONY", "yenes")):
    g = V.grafico("flujo_libre", P[tk]["estados"], G._fila_cache(tk), {}, {}, None, None)
    chk(f"millones de {nom}" in g and "millones de dólares" not in g, f"{tk}: gráfico en {nom}")
D = json.load(open("data/analisis_fundamental.json", encoding="utf-8"))["datos"]
for tk in ("AMGN", "ANET", "SHOP", "PFE", "QCOM", "MCD", "NVO", "COP", "SONY"):
    chk(D[tk]["fecha"] == "07/11/2026" and AF.anteriores(tk), f"{tk}: renovado el 07/11 con su informe anterior")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
