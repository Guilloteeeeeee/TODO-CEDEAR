"""v1.5.81 (Guille 21/11/2026: «el congelamiento debe correr la misma suerte que un recorte, suspensiones u omisiones»): 3 o más años
seguidos sin subir el dividendo son un evento como un recorte (−25 si terminó hace menos de 5 años, −10 si hace 5 a 10); manda el evento
más reciente; con la serie convertida no se mide; sin dividendo no hay score."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
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


def entrada(tasa, recortes=(), fuente="dolares", dpa=2.4, racha=0, sin_suba=0):
    fila = lambda n, v: [n, [v] * len(AN), "m"]  # noqa: E731
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8),
                                                  fila("Ingresos", 3e10), fila("Resultado neto", 4e9), fila("Ganancia por acción (diluida)", 4.0)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", 1.5e10), fila("Caja e inversiones de corto plazo", 9e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 4e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 5e9)]}}
    hist = {"racha_subas": racha, "anios_sin_suba": sin_suba, "recortes": list(recortes), "ultimo_completo": 2025, "tasa": tasa,
            "anios_sin_recorte": 10}
    return {"grupo": "Industrial", "estados": est, "dividendo_anual": dpa, "historial": hist, "fuente_historial": fuente}


def aj(r):
    return dict(r["ajustes"])


plano = lambda desde, hasta, v=1.0: {a: v for a in range(desde, hasta + 1)}  # noqa: E731

# --- 1) tramos congelados ---------------------------------------------------------------------------------------------------------
t = {2015: 0.8, 2016: 0.9, **plano(2017, 2021), 2022: 1.1, 2023: 1.2, 2024: 1.3, 2025: 1.4}
chk(V1.congelamientos({"tasa": t, "ultimo_completo": 2025}) == [2021], f"2017 a 2021 sin subir: termina en 2021 ({V1.congelamientos({'tasa': t, 'ultimo_completo': 2025})})")
t2 = {2019: 0.9, **plano(2020, 2022), 2023: 1.1, 2024: 1.2, 2025: 1.3}
chk(V1.congelamientos({"tasa": t2, "ultimo_completo": 2025}) == [], "2 años sin subir (2021 y 2022) no es congelamiento crónico")

# --- 2) cuenta como un recorte, según cuándo terminó --------------------------------------------------------------------------------
nvda = {2019: 0.9, **plano(2020, 2023), 2024: 1.1, 2025: 1.2}         # congelado hasta 2023: hace 2 años
r = V1.calcular(entrada(nvda, racha=2))
chk(aj(r).get("congelamiento_menos_5") == -25, f"terminó hace 2 años: −25 ({r['ajustes']})")
r = V1.calcular(entrada(t, racha=4))                                   # terminó en 2021: hace 4 años
chk(aj(r).get("congelamiento_menos_5") == -25, "terminó hace 4 años: −25")
viejo = {2012: 0.9, **plano(2013, 2017), **{a: 1.0 + 0.1 * (a - 2017) for a in range(2018, 2026)}}
r = V1.calcular(entrada(viejo, racha=8))
chk(aj(r).get("congelamiento_5_10") == -10, f"terminó hace 8 años: −10 ({r['ajustes']})")
muy_viejo = {2008: 0.9, **plano(2009, 2013), **{a: 1.0 + 0.1 * (a - 2013) for a in range(2014, 2026)}}
r = V1.calcular(entrada(muy_viejo, racha=12))
chk(not any(k.startswith("congelamiento") for k in aj(r)), "terminó hace 12 años: sin castigo")
r = V1.calcular(entrada({2021: 0.9, **plano(2022, 2025)}, sin_suba=3))
chk(aj(r).get("congelamiento_menos_5") == -25, "sigue congelado: −25")

# --- 3) manda el evento más reciente, no se suman -----------------------------------------------------------------------------------
r = V1.calcular(entrada(nvda, recortes=[2019], racha=2))
chk(aj(r).get("congelamiento_menos_5") == -25 and "recorte_menos_5" not in aj(r) and "recorte_5_10" not in aj(r),
    f"recorte en 2019 y congelamiento hasta 2023: un solo castigo ({r['ajustes']})")
r = V1.calcular(entrada(t, recortes=[2024], racha=1))
chk(aj(r).get("recorte_menos_5") == -25 and not any(k.startswith("congelamiento") for k in aj(r)), "el recorte es más reciente: manda el recorte")

# --- 4) con la serie convertida no se mide; no cuenta para los pagos erráticos ------------------------------------------------------
r = V1.calcular(entrada(nvda, fuente="convertido", racha=2))
chk(not any(k.startswith("congelamiento") for k in aj(r)), "serie convertida: no se mide el congelamiento")
r = V1.calcular(entrada({**plano(2014, 2017), 2018: 1.1, **plano(2019, 2021, 1.1), 2022: 1.2, **plano(2023, 2025, 1.2)}, racha=0, sin_suba=3))
chk(not any(k == "dividendo_variable" for k, _ in r["topes"]), "tres congelamientos no lo vuelven «errático»")

# --- 5) sin dividendo no hay score ---------------------------------------------------------------------------------------------------
r = V1.calcular(entrada(nvda, dpa=None))
chk(r["score"] is None and "no paga dividendo" in r["notas"], "sin dividendo: sin score")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
