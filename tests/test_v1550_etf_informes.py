"""v1.5.50: Análisis de ETF (informes, PDF, solapa) y líneas de referencia con la mediana del sector propio."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from ui import etf_informe as E
from data import historico as HI
D = E.cargar()
SECTORES = {"XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"}
chk(SECTORES <= set(D), "están los 11 fondos de sectores de State Street")
for tk, inf in D.items():
    chk(not E.validar(tk, inf), f"{tk}: informe completo y sin palabras prohibidas ({E.validar(tk, inf)})")
    chk(E.ruta_pdf(tk, inf) and os.path.getsize(E.ruta_pdf(tk, inf)) > 20000, f"{tk}: PDF armado")
    chk(f"ETF-{tk}_{E.fecha_iso(inf['fecha'])}" in HI.informes_guardados(f"ETF-{tk}"), f"{tk}: versión guardada en el archivo histórico")
    h = E.app_html(tk, inf)
    chk("[[" not in h and "**" not in h, f"{tk}: marcadores y negritas resueltos")
    chk("<svg" in h and 'class="t10"' in h and 'class="rend"' in h, f"{tk}: torta, principales posiciones y rendimientos")
    texto = json.dumps({k: v for k, v in inf.items() if k != "fuentes"}, ensure_ascii=False)
    chk(not re.search(r"\d %", texto), f"{tk}: el % va pegado al número")
    d = sum(v for _, v in inf["dona"]["items"])
    chk(abs(d - 100) < 1.5, f"{tk}: la torta suma 100 ({d})")
    chk(0 < sum(p for _, _, p in inf["top10"]) <= 100 and len(inf["top10"]) == 10, f"{tk}: 10 principales posiciones")
    r = inf["rend"]
    chk(r["ref"] == "S&P 500 (SPY)" and r["al"] in ("31/10/2026", "30/09/2026") and all(f[2] is not None for f in r["filas"]), f"{tk}: comparado con SPY a la misma fecha")
    chk(r["al"] in " ".join(s["texto"] for s in inf["secciones"]), f"{tk}: el texto dice a qué fecha son los rendimientos")
    chk("dosis" not in texto, f"{tk}: nada de «dosis»")
# misma fecha: los del 30/09 se comparan con SPY al 30/09
chk(D["XLRE"]["rend"]["filas"][0][2] == 15.60 and D["XLK"]["rend"]["filas"][0][2] == 11.98, "SPY al 30/09 y al 31/10 según corresponda")
chk(E.validar("X", {**D["XLK"], "intro": "una dosis chica"}) != [], "validar avisa «dosis chica»")
chk(E.validar("X", {**D["XLK"], "intro": "un año flojo y rojo"}) == [], "validar no confunde «rojo» con la palabra prohibida")
chk(E.informe("NOEXISTE") is None and E.ruta_pdf("NOEXISTE") is None, "sin informe, sin PDF")
doc = E.documento_html("XLV", D["XLV"])
chk("@page" in doc and "Finanzas para Médicos Argentina" in doc and "TodoCedears" in doc.replace("<span>", "").replace("</span>", ""), "el PDF lleva membrete")
chk("Finanzas para Médicos" not in E.app_html("XLV", D["XLV"]), "en la app, sin membrete (ya está el encabezado del ETF)")
app = open("app.py", encoding="utf-8").read()
chk('"Análisis del ETF"' in app and "def _render_analisis_etf" in app and "_ei.ruta_pdf(" in app, "solapa «Análisis del ETF» con el PDF para bajar")
from ui import etfs as UE
chk("analisis" in UE.INTROS, "la solapa tiene su explicación arriba")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
