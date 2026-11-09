"""v1.5.49: estados por tipo de empresa, referencia de industria rigurosa, precio vs fundamentales, piloto de la SEC, mes de cierre fiscal."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from ui import estados_visual as E, ficha as F, precio_vs as PV
from data import paquetes_yahoo as PY
P = PY.cargar()[0]
fam = {t: E.familia(t, v["estados"]) for t, v in P.items()}
chk(fam["JPM"] == "financiera" and fam["BAC"] == "financiera" and fam["AXP"] == "financiera", "bancos y financieras sin resultado operativo: familia financiera")
chk(fam["O"] == fam["PLD"] == fam["WELL"] == "reit" and fam["KO"] == fam["AAPL"] == "general", "REITs y generales")
g = E.graficos_html(P["JPM"]["estados"], "flujo", "JPM")
chk("Flujo de efectivo libre" not in g and "Dividendos pagados" in g and "bancos y aseguradoras" in g, "banco: sin flujo libre y con aviso")
chk("Retorno sobre el activo (ROA)" in E.graficos_html(P["JPM"]["estados"], "ratios", "JPM"), "banco: ROA en Ratios")
chk("Flujo operativo por acción" in E.graficos_html(P["O"]["estados"], "flujo", "O"), "REIT: flujo operativo por acción")
r = E.referencias("AAPL")
chk("roe" not in r and "roic" not in r and "mop" in r, "AAPL: sin ROE de industria negativo ni ROIC (otra definición); con margen operativo")
chk(set(E.referencias("JPM", "financiera")) <= {"mne", "roe"}, "financieras: solo margen neto y ROE de la industria")
gk = E.graficos_html(P["KO"]["estados"], "ratios", "KO")
import re as _re
chk("Referencia" not in gk and 'class="ev-ref"' in gk and _re.search(r'title="Promedio de la industria [^"]*Damodaran', gk), "línea de industria sin leyenda (el detalle va al pasar el mouse)")
chk(_re.search(r">Ideal: más de [\d,]+%</span>", gk) is not None, "v1.5.52: la línea dice «Ideal: más de X»")
chk(gk.count('class="ev-t"') == 9, "Ratios visual: 9 gráficos en una empresa general")
ga = E.graficos_html(P["AAPL"]["estados"], "ratios", "AAPL")
chk("la fuente no trae el gasto por intereses" in ga, "cobertura: explica por qué falta (Apple)")
ind, _ = F._industria_ratios("AAPL")
chk("Retorno sobre el capital invertido (ROIC)" not in ind and "Retorno sobre el patrimonio (ROE)" not in ind, "tabla: sin ROIC de industria ni ROE negativo")
for t in P:
    for k in ("resultados", "balance", "flujo", "ratios"):
        E.graficos_html(P[t]["estados"], k, t)
chk(True, "los gráficos se arman sin error en las 323")
# precio vs fundamentales
est = P["NFLX"]["estados"]
cierres = {"2022-12": 29.488, "2023-12": 48.688, "2024-12": 89.132, "2025-12": 93.76}
h = PV.precio_vs_html("NFLX", est, cierres, 64.795, 12)
chk("Precio vs fundamentales del negocio" in h and "Ganancia por acción" in h and "checked" in h and "0%" in h, "tarjeta con selector, por defecto contra la ganancia por acción, desde 0%")
c = PV.cambios(PV.puntos(est, cierres, 64.795, 12), "precio")
chk(abs(c[-1] - (64.795 / 29.488 - 1)) < 1e-9, "cambio del precio desde el primer cierre fiscal")
chk(PV.precio_vs_html("NFLX", est, {}, 64.795, 12) == "", "sin historia de precios no se muestra")
chk("Se toma diciembre" in PV.precio_vs_html("NFLX", est, cierres, 64.795, None), "avisa cuando no se sabe el mes de cierre fiscal")
chk(PV._precio_en({"2025-08": 10.0}, 2025, 9) == 10.0, "si falta el mes de cierre, usa el anterior")
app = open("app.py", encoding="utf-8").read()
chk("_pvs.precio_vs_html(" in app and "def _historico_precios" in app, "la solapa Valuación lo muestra")
chk('"mes_cierre_fiscal": _mes_cierre(' in open("bajar_fichas.py", encoding="utf-8").read(), "bajar_fichas trae el mes de cierre fiscal")
import piloto_sec as S
f = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [{"start": "2022-01-01", "end": "2022-12-31", "val": 101, "form": "10-K", "filed": "2024-02-01"},
                                                         {"start": "2022-01-01", "end": "2022-12-31", "val": 100, "form": "10-K", "filed": "2023-02-01"},
                                                         {"start": "2022-10-01", "end": "2022-12-31", "val": 30, "form": "10-K", "filed": "2023-02-01"}]}},
                           "SalesRevenueNet": {"units": {"USD": [{"start": "2012-01-01", "end": "2012-12-31", "val": 50, "form": "10-K", "filed": "2013-02-01"}]}}}}}
a = S.anuales(f, "Ingresos")
chk(a[2022][0] == 101 and a[2012][0] == 50 and len(a) == 2, "SEC: año completo, versión más nueva y conceptos viejos")
chk(os.path.isfile("piloto_sec.bat") and ".sec_contacto" in open(".gitignore", encoding="utf-8").read(), "piloto_sec.bat y el contacto no se sube")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
