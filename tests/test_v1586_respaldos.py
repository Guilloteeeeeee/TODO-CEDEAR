"""v1.5.86 (Guille 23/11/2026: «no podés buscarlos vos?»): mientras no corran los .bat, las ganancias retenidas y la tesorería salen de Stock
Analysis (data/ganancias_retenidas_manuales.json) y los dividendos de la bolsa de origen de las 16 de afuera con número de SSD también
(data/dividendos_locales_manuales.json). Si Yahoo trae el dato, manda Yahoo. CET1 de XP cargado."""
import json
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
from data import moneda_dividendo as MD  # noqa: E402

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def entrada(retenidas=None, recompra=-1e9, manual=None):
    fila = lambda n, v: [n, [v] * len(AN), "m"]  # noqa: E731
    bal = [fila("Deuda total", 1.5e10), fila("Caja e inversiones de corto plazo", 9e9), fila("Activo total", 4e10),
           fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]
    if retenidas is not None:
        bal.append(fila("Ganancias retenidas", retenidas))
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8),
                                                  fila("Ingresos", 3e10), fila("Resultado neto", 4e9), fila("Ganancia por acción (diluida)", 4.0)]},
           "balance": {"anios": AN, "filas": bal},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 4e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 5e9),
                                             fila("Recompra de acciones", recompra)]}}
    hist = {"racha_subas": 3, "anios_sin_suba": 0, "recortes": [], "ultimo_completo": 2025, "tasa": {a: 1 + 0.05 * (a - 2020) for a in range(2020, 2026)},
            "anios_sin_recorte": 10}
    return {"grupo": "Industrial", "estados": est, "dividendo_anual": 2.4, "historial": hist, "fuente_historial": "dolares", "ganancias_retenidas": manual}


def reta(r):
    return next(v for v in r["variables"] if v["clave"] == "re_ta")


# --- 1) sin la fila de Yahoo: usa Stock Analysis, con su propio activo total -------------------------------------------------------
m = {"fecha": "2026-09-30", "activo_total": 40000.0, "ganancias_retenidas": 12000.0, "tesoreria": -2000.0}
r = V1.calcular(entrada(manual=m))
z = reta(r)
# recompras de 4 años = 4.000 millones > tesorería 2.000 → (12.000 + 4.000) / 40.000 = 40 %
chk(abs(z["valor"] - 40.0) < 0.01 and z["pts"] == 10, f"(12.000 + recompras 4.000) / 40.000 = 40 % ({z['valor']}, {z['pts']})")
chk(any("Stock Analysis" in n for n in r["notas"]), "anota la fuente")
m2 = dict(m, tesoreria=-6000.0)
z = reta(V1.calcular(entrada(manual=m2)))
chk(abs(z["valor"] - 45.0) < 0.01, f"tesorería 6.000 > recompras 4.000: (12.000 + 6.000) / 40.000 = 45 % ({z['valor']})")
# activo de Stock Analysis en otra escala (otro trimestre o moneda): las recompras se llevan a esa escala
m3 = {"fecha": "2026-06-30", "activo_total": 80000.0, "ganancias_retenidas": 24000.0, "tesoreria": 0.0}
z = reta(V1.calcular(entrada(manual=m3)))
chk(abs(z["valor"] - 40.0) < 0.01, f"activo de SA el doble que el de Yahoo: recompras × 2 → (24.000 + 8.000) / 80.000 = 40 % ({z['valor']})")

# --- 2) con la fila de Yahoo, manda Yahoo -------------------------------------------------------------------------------------------
r = V1.calcular(entrada(retenidas=4e9, manual=m))
z = reta(r)
chk(abs(z["valor"] - 20.0) < 0.01 and not any("Stock Analysis" in n for n in r["notas"]), f"Yahoo trae la fila: (4.000 + 4.000) / 40.000 = 20 % ({z['valor']})")

# --- 3) sin ninguno de los dos, la variable queda sin dato ---------------------------------------------------------------------------
chk(reta(V1.calcular(entrada()))["pts"] is None, "sin fila ni respaldo: sin dato")

# --- 4) archivo de Stock Analysis ----------------------------------------------------------------------------------------------------
g = json.load(open("data/ganancias_retenidas_manuales.json", encoding="utf-8"))
chk(len(g["datos"]) == 155 and all(d.get("activo_total") and d.get("ganancias_retenidas") is not None and d.get("url") for d in g["datos"].values()),
    f"155 empresas con activo, ganancias retenidas y fuente ({len(g['datos'])})")
chk(V1.ganancias_retenidas("KO")["ganancias_retenidas"] == 85898.0, "Coca-Cola: 85.898 millones al 02/10/2026")

# --- 5) dividendos locales: respaldo de Stock Analysis, Yahoo manda --------------------------------------------------------------------
loc = MD.locales_con_respaldo({})
chk(len(loc) == 16 and all(d["ok"] for d in loc.values()), f"16 empresas de afuera con su dividendo en su moneda ({len(loc)})")
chk(loc["SONY"]["pagos"][-1] == ["2026-09-29", 17.5] and ["2024-09-27", 10.0] in loc["SONY"]["pagos"], "Sony: pago de 2024 llevado al split 5 por 1")
yahoo = {"SONY": {"ok": True, "pagos": [["2025-03-28", 10.0]], "simbolo": "6758.T"}}
chk(MD.locales_con_respaldo(yahoo)["SONY"]["pagos"] == [["2025-03-28", 10.0]], "si Yahoo la trajo bien, manda Yahoo")
malo = {"SONY": {"ok": False, "pagos": [["2025-03-28", 10.0]]}}
chk(len(MD.locales_con_respaldo(malo)["SONY"]["pagos"]) > 1, "si lo de Yahoo no sirve, queda el respaldo")
fut = [f for d in loc.values() for f, _ in d["pagos"] if f > "2026-11-23"]
chk(not fut, f"sin pagos anunciados para después del 23/11/2026 ({fut})")

# --- 6) CET1 de XP -----------------------------------------------------------------------------------------------------------------------
c = json.load(open("data/cet1_bancos.json", encoding="utf-8"))["datos"]["XP"]
chk(c.get("cet1") == 17.2 and c.get("fuentes"), "XP: CET1 17,2 % al 30/09/2026 con fuente")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
