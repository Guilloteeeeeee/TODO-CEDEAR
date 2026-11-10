"""v1.5.56: puntos de corte de Guille en los gráficos de Estados Financieros (frase en negrita + línea punteada con el número al costado)."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from data import puntos_corte as PC, paquetes_yahoo as PY, yahoo_extra as YX
from ui import estados_visual as E
T = PC.tabla()
chk(len(T.get("industrias", {})) == 72 and len(T.get("sectores", [])) == 19 and len(T.get("damodaran_a_sector", {})) == 94, "tabla de cortes completa (72 industrias, 19 filas de sector, 94 industrias de Damodaran)")
chk(set(T["industrias"]) <= set(PC.NOMBRES), "cada industria tiene su nombre en castellano para la frase")
chk(all(os.path.exists(f"data/referencias/puntos_corte{x}") for x in ("_2026-11-09.json", "_2026-11-09.xlsx", "_metodo_2026-11-09.txt")), "respaldo: Excel, método y cortes guardados")
cache = json.load(open("data/cache_datos.json", encoding="utf-8"))["data"]
sin = [r["ticker"] for r in cache if not PC.cortes(r["ticker"])]
chk(not sin, f"todas las empresas tienen su fila de cortes ({sin})")
c = PC.cortes("TXN")
chk(c["fila"] == "Semiconductor" and c["cortes"]["roic"] == 0.13, "Texas Instruments: ROIC 13% (ejemplo del método)")
chk(PC.cortes("JPM")["cortes"]["roic"] is None, "banco: ROIC n/a")
chk(E._fmt_corte(0.1308, "pct") == "13%" and E._fmt_corte(2.71, "x") == "2.7x" and E._fmt_corte(0.0986, "pct") == "9.9%" and E._fmt_corte(0.014, "pct") == "1.4%"
    and E._fmt_corte(7.0, "x") == "7x" and E._fmt_corte(0.05, "pct") == "5%" and E._fmt_corte(12.4, "x") == "12x", "v1.5.57: una cifra entera con decimal; de 10 para arriba, entero")
neg, resto = E.frase_corte("mop", "pct", (0.1308, "min", "los fabricantes de maquinaria"))
chk(neg == "Más de 13% es nuestra preferencia" and resto == "para los fabricantes de maquinaria.", "frase: negrita solo en la preferencia")
chk(E.frase_corte("dne", "x", (2.0, "max", "x"))[0].startswith("Menos de 2x"), "en deuda: «Menos de»")
P = PY.cargar()[0]
g = E.graficos_html(YX.reparar_roic(P["CAT"]["estados"]), "ratios", "CAT")
chk('<span class="ev-pref"><b>Más de 13% es nuestra preferencia</b> para los fabricantes de maquinaria.</span>' in g, "Caterpillar: frase del margen operativo")
chk(g.count('class="ev-ref"') == 7 and "Ideal" not in g, "Caterpillar: 7 líneas en Ratios (sin margen bruto ni neto)")
chk(re.search(r'class="ev-ref" style="bottom:\d+px"><span>61%</span>', g), "la línea lleva el número al costado")
m = re.search(r'Dividendos / flujo libre.*?class="ev-ref" style="bottom:(\d+)px"', g, re.S)
chk(m and int(m.group(1)) <= 34 + 124 - 12, "corte por encima de todas las barras: la línea queda debajo de la fila de números")
gj = E.graficos_html(P["JPM"]["estados"], "ratios", "JPM")
chk("los grandes bancos" in gj and gj.count('class="ev-ref"') == 3, "banco: ROE, ROA y payout con corte")
css = E.CSS
chk(".ev-pref{display:block;text-align:left" in css, "la frase va alineada a la izquierda (el resto, justificado)")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
