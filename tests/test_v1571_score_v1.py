"""v1.5.71: score de dividendos nuevo de Guille (scoring/dividendo_v1.py), programado aparte del v0.2."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


from scoring import dividendo_v1 as V1  # noqa: E402

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def est(ebit=500.0, inte=50.0, ebitda=700.0, neto=300.0, ventas=(1200, 1150, 1100, 1050, 1000), fcf=400.0, divp=-150.0,
        dn=1000.0, deuda=1500.0, ac=800.0, inv=100.0, pc=500.0, at=5000.0, rr=2500.0, tes=0.0, cfo=600.0, eps=4.0):
    f = lambda v: [v] * 5  # noqa: E731
    return {"resultados": {"anios": AN, "filas": [["Ingresos", list(ventas), "t"], ["Resultado operativo", f(ebit), "t"], ["EBITDA", f(ebitda), "m"],
                                                  ["Gasto por intereses", f(inte), "m"], ["Resultado neto", f(neto), "t"], ["Ganancia por acción (diluida)", f(eps), "eps"]]},
            "balance": {"anios": AN, "filas": [["Deuda total", f(deuda), "m"], ["Deuda neta", f(dn), "m"], ["Caja e inversiones de corto plazo", f(500.0), "m"],
                                               ["Activo corriente", f(ac), "t"], ["Inventarios", f(inv), "m"], ["Pasivo corriente", f(pc), "t"],
                                               ["Activo total", f(at), "t"], ["Ganancias retenidas", f(rr), "m"], ["Acciones en tesorería", f(tes), "m"]]},
            "flujo": {"anios": AN, "filas": [["Flujo de efectivo libre", f(fcf), "t"], ["Dividendos pagados", f(divp), "m"], ["Flujo de efectivo operativo", f(cfo), "t"]]}}


HIST = {"recortes": [], "racha_subas": 12, "anios_sin_suba": 0, "ultimo_completo": 2025, "recorte_en_curso": False}


def e(**k):
    base = {"ticker": "X", "grupo": "Industrial", "dividendo_anual": 1.5, "estados": est(), "historial": dict(HIST),
            "estimacion": {"actual": 4.0, "proximo": 4.0}, "mes_cierre": 12, "hoy": dt.date(2026, 11, 16), "rend": 0.03, "fuente_historial": "dolares"}
    base.update(k)
    return base


def v(r, clave):
    return next((x for x in r["variables"] if x["clave"] == clave), None)


# 1) empresa sana: base 100, aspirante (+5), tope 99 (v1.5.78: Guille prefiere que el score no muestre 100)
r = V1.calcular(e())
chk(r["base"] == 100 and r["score"] == 99 and ("aspirante", 5) in r["ajustes"], f"empresa sana: {r['base']} {r['score']} {r['ajustes']}")
chk(r["categoria"] == "Muy seguro", "categoría")

# 2) bordes (Guille: cada zona va hasta el punto inmediato anterior de la siguiente)
chk(v(V1.calcular(e(estados=est(ebit=250.0))), "cobertura")["pts"] == 10, "cobertura 5,0 veces: gris")
chk(v(V1.calcular(e(estados=est(ebit=251.0))), "cobertura")["pts"] == 25, "cobertura 5,02: segura")
chk(v(V1.calcular(e(estados=est(ebit=100.0))), "cobertura")["pts"] == 10, "cobertura 2,0: gris")
chk(v(V1.calcular(e(estados=est(ebit=99.0))), "cobertura")["pts"] == 0, "cobertura 1,98: crítica")
chk(v(V1.calcular(e(estados=est(divp=-240.0))), "fcf_payout")["pts"] == 10, "payout de flujo 60%: gris")
chk(v(V1.calcular(e(estados=est(divp=-340.0))), "fcf_payout")["pts"] == 10, "payout de flujo 85%: gris")
chk(v(V1.calcular(e(estados=est(divp=-344.0))), "fcf_payout")["pts"] == 0, "payout de flujo 86%: crítica")
chk(v(V1.calcular(e(dividendo_anual=3.16)), "payout_futuro")["pts"] == 7, "payout futuro 79%: gris")
chk(v(V1.calcular(e(dividendo_anual=3.2)), "payout_futuro")["pts"] == 0, "payout futuro 80%: crítica (55 a 79 es gris)")
chk(v(V1.calcular(e(dividendo_anual=2.2)), "payout_futuro")["pts"] == 7, "payout futuro 55%: gris")
rb = V1.calcular(e(grupo="Bancos y seguros", dividendo_anual=2.96, cet1=12.0))
chk(v(rb, "eps_payout")["pts"] == 10 and v(rb, "cobertura") is None and v(rb, "cet1")["pts"] == 25, "banco 74%: gris; CET1 12%: seguro; sin cobertura de intereses")
chk(v(V1.calcular(e(grupo="Bancos y seguros", dividendo_anual=3.0)), "eps_payout")["pts"] == 0, "banco 75%: crítica")

# 3) frenos
rp = V1.calcular(e(estados=est(neto=-10.0)))
chk(rp["score"] <= 20 and ("perdida", 20) in rp["topes"], "pérdida en el último año completo: máximo 20")
rr = V1.calcular(e(grupo="REITs", estados=est(neto=-10.0), affo=3.0))
chk(rr["score"] <= 20, "la pérdida también topa a los REIT")
rc = V1.calcular(e(estados=est(ebit=70.0)))
chk(rc["score"] <= 20 and ("cobertura_letal", 20) in rc["topes"], "cobertura menor a 1,5: máximo 20")
rt = V1.calcular(e(rend=0.09, estados=est(divp=-480.0)))
chk(("trampa_rendimiento", -30) in rt["ajustes"] and rt["score"] <= 40, f"trampa de rendimiento: {rt['score']}")
chk(not any(a == "trampa_rendimiento" for a, _ in V1.calcular(e(rend=0.09))["ajustes"]), "rendimiento alto con caja que alcanza: no es trampa")

# 4) historial
r5 = V1.calcular(e(historial=dict(HIST, recortes=[2022], racha_subas=3)))
chk(("recorte_menos_5", -25) in r5["ajustes"], "recorte hace 3 años: −25")
r10 = V1.calcular(e(historial=dict(HIST, recortes=[2017], racha_subas=8)))
chk(("recorte_5_10", -10) in r10["ajustes"], "recorte hace 8 años: −10")
rm = V1.calcular(e(historial=dict(HIST, recortes=[2020, 2021], racha_subas=4)))
chk(("recorte_5_10", -10) in rm["ajustes"], "recorte a mitad de 2020 que se ve también en 2021: cuenta desde 2020")
r11 = V1.calcular(e(historial=dict(HIST, recortes=[2013], racha_subas=12)))
chk(not any(a.startswith("recorte") for a, _ in r11["ajustes"]), "recorte hace más de 10 años: sin castigo")
ra = V1.calcular(e(historial=dict(HIST, racha_subas=30)))
chk(("aristocrata", 10) in ra["ajustes"], "25 años o más de subas: +10")
rg = V1.calcular(e(historial=dict(HIST, racha_subas=0, anios_sin_suba=4)))
chk(("congelamiento", -5) in rg["ajustes"] and not any(a in ("aristocrata", "aspirante") for a, _ in rg["ajustes"]), "congelado 4 años: −5 y sin bono")
rx = V1.calcular(e(historial=dict(HIST, racha_subas=30), estados=est(divp=-350.0)))
chk(not any(a == "aristocrata" for a, _ in rx["ajustes"]), "payout de flujo crítico: se anula el bono")
rv = V1.calcular(e(ticker="GFI", historial=dict(HIST, racha_subas=30)))
chk(rv["score"] <= 80 and not any(a == "aristocrata" for a, _ in rv["ajustes"]), "política variable declarada: máximo 80 y sin bono")
re_ = V1.calcular(e(historial=dict(HIST, recortes=[2017, 2020, 2023], racha_subas=2)))
chk(re_["erratico"] and re_["score"] <= 80, "3 recortes en 10 años: pagos erráticos, máximo 80")
rs = V1.calcular(e(fuente_historial="variable", historial=dict(HIST, recortes=[2023], racha_subas=2)))
chk(not any(a.startswith("recorte") for a, _ in rs["ajustes"]), "sin el dividendo en su moneda: ni castigo ni bono")

# 5) ganancias retenidas ajustadas: las recompras en tesorería no castigan
r_neg = V1.calcular(e(estados=est(rr=-500.0, tes=0.0)))
r_tes = V1.calcular(e(estados=est(rr=-500.0, tes=-3000.0)))
chk(v(r_neg, "re_ta")["pts"] == 0 and v(r_tes, "re_ta")["pts"] == 10, "ganancias retenidas + |tesorería|")

# 6) sectores: REIT sin payout futuro ni ganancias retenidas, base sobre 75 llevada a 100; utilities con flujo operativo ÷ deuda
rre = V1.calcular(e(grupo="REITs", affo=2.0))
chk(v(rre, "payout_futuro") is None and v(rre, "re_ta") is None and v(rre, "affo")["pts"] == 20, "REIT: variables")
ru = V1.calcular(e(grupo="Utilities"))
chk(v(ru, "ffo_deuda")["pts"] == 7.5 and v(ru, "deuda")["max"] == 7.5 and v(ru, "fcf_payout") is None and v(ru, "eps_payout")["pts"] == 20,
    "utilities: variables (v1.5.79: deuda 7,5 + FFO ÷ Deuda 7,5)")
rq = V1.calcular(e(grupo="Software y nube", estados=est(ac=600.0, inv=0.0, pc=500.0)))
chk(v(rq, "acida")["pts"] == 2, "tecnología: ácida 1,2 es gris (segura arriba de 1,5)")

# 7) ganancia de los próximos 12 meses
g = V1.ntm({"actual": 4.0, "proximo": 5.0}, 12, dt.date(2026, 11, 16))
chk(4.8 < g < 5.0, f"noviembre con cierre en diciembre: casi todo el año próximo ({g:.2f})")
g2 = V1.ntm({"actual": 4.0, "proximo": 5.0}, 12, dt.date(2026, 1, 10))
chk(4.0 < g2 < 4.1, f"enero: casi todo el año en curso ({g2:.2f})")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
