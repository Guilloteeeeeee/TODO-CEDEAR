"""v1.5.75: intereses de las 6 empresas que faltaban (cargados con fuente, «sí o sí»), Welltower con su FFO en el lugar del AFFO (sin aclarar),
cortes de solvencia aprobados, y control: toda empresa con dividendo (menos bancos y aseguradoras) tiene cobertura de intereses."""
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

# --- 1) intereses cargados a mano: las 6 que faltaban, con año, monto, medida y fuente ------------------------------------------
man = json.load(open(os.path.join(RAIZ, "data", "intereses_manuales.json"), encoding="utf-8"))["datos"]
esperado = {"ARCO": (2025, 59352000), "CRM": (2026, 324000000), "GEV": (2025, 53000000), "LLY": (2025, 895000000),
            "NKE": (2026, 323000000), "NTES": (2025, 387982000)}
for t, (anio, monto) in esperado.items():
    m = man.get(t) or {}
    chk(m.get("anio") == anio and m.get("monto") == monto, f"{t}: año {anio} y monto {monto} ({m.get('anio')}, {m.get('monto')})")
    chk(bool(m.get("fuentes")) and all(u.startswith("https://") for u in m["fuentes"]), f"{t}: con fuente")
    chk(len(m.get("medida") or "") > 30, f"{t}: dice qué es el dato")
    chk(V1.intereses_manual(t) is not None, f"{t}: lo lee intereses_manual")
for t in ("AAPL", "GRMN", "PCAR"):
    chk(t in man, f"{t}: sigue cargada")

# --- 2) Welltower: FFO en el lugar del AFFO, sin aclaración ---------------------------------------------------------------------
ffo = json.load(open(os.path.join(RAIZ, "data", "ffo_reit.json"), encoding="utf-8"))["datos"]
w = ffo["WELL"]
chk(w.get("usar_ffo_como_affo") is True and w.get("ffo_12m"), "WELL: marcada para usar el FFO")
chk("Pendiente de decisión" not in (w.get("affo_no_informa") or ""), "WELL: ya no figura pendiente")
src = open(os.path.join(RAIZ, "calibrar_dividendo.py"), encoding="utf-8").read()
chk('usar_ffo_como_affo' in src and 'e1["affo"], e1["affo_nombre"], e1["affo_es_ffo"] = f["ffo_12m"], "AFFO", True' in src, "calibrar: usa el FFO y lo nombra AFFO")
for t, f in ffo.items():
    if t != "WELL":
        chk(not f.get("usar_ffo_como_affo"), f"{t}: solo WELL usa el FFO en lugar del AFFO")


def reit(dpa=3.40, affo=6.19):
    an = ["2026 (TTM)", 2025, 2024, 2023, 2022]
    fila = lambda n, v: [n, [v] * len(an), "m"]  # noqa: E731
    est = {"resultados": {"anios": an, "filas": [fila("Resultado operativo", 3e9), fila("EBITDA", 5e9), fila("Gasto por intereses", 1e9),
                                                   fila("Ingresos", 1e10), fila("Resultado neto", 1e9)]},
           "balance": {"anios": an, "filas": [fila("Deuda total", 2e10), fila("Caja e inversiones de corto plazo", 1e9), fila("Activo total", 5e10),
                                               fila("Activo corriente", 3e9), fila("Pasivo corriente", 2e9)]},
           "flujo": {"anios": an, "filas": [fila("Flujo de efectivo libre", 2e9), fila("Dividendos pagados", -1e9)]}}
    return {"grupo": "REITs", "estados": est, "dividendo_anual": dpa, "affo": affo, "affo_nombre": "AFFO", "hist": None}


r = V1.calcular(reit())
a = next(v for v in r["variables"] if v["clave"] == "affo")
chk(a["pts"] == 20 and abs(a["valor"] - 3.40 / 6.19 * 100) < 0.01, f"payout con el FFO de 6,19: 54,9 % → 20 puntos ({a})")
chk(a.get("nombre") == "AFFO", "sin aclaración: la métrica se llama AFFO")

# --- 3) cortes de solvencia aprobados -------------------------------------------------------------------------------------------
v1src = open(os.path.join(RAIZ, "scoring", "dividendo_v1.py"), encoding="utf-8").read()
lin = next(x for x in v1src.splitlines() if x.startswith("SOLVENCIA_SEGURA"))
chk("PROPUESTA" not in lin and "aprobado" in lin and V1.SOLVENCIA_SEGURA == 150.0, "solvencia: 150 % aprobado")

# --- 4) control «sí o sí»: con los datos del repositorio, toda empresa con dividendo tiene cobertura ---------------------------
try:
    import calibrar_dividendo as C
    from data import historico as H, paquetes_yahoo as PY
    cache = {r["ticker"]: r for r in json.load(open("data/cache_datos.json", encoding="utf-8"))["data"]}
    est = json.load(open("data/estimaciones_analistas.json", encoding="utf-8"))["datos"]
    tks = [t for t, x in cache.items() if (x.get("annual_dividend") or 0) > 0]
    res = C.calcular_todo(tks, cache, PY.cargar()[0], H.leer("estados.json", {}), H.leer("splits.json", {}), H.leer("dividendos.json", {}),
                          H.leer("precios_mensuales.json", {}), est)
    sin = []
    for t, x in res.items():
        v = x.get("v1") or {}
        claves = {y["clave"] for y in v.get("variables", [])}
        if "cet1" in claves or "solvencia" in claves:
            continue
        if not any(y["clave"] == "cobertura" and y["valor"] is not None for y in v.get("variables", [])):
            sin.append(t)
    chk(not sin, f"empresas con dividendo sin cobertura de intereses: {sin}")
    chk(len(res) > 150, f"se calcularon {len(res)} empresas")
    w = (res.get("WELL") or {}).get("v1") or {}
    wa = next((y for y in w.get("variables", []) if y["clave"] == "affo"), None)
    chk(wa is not None and wa["valor"] is not None and wa["pts"] == 20, f"WELL con los datos reales: payout sobre FFO ({wa})")
except ImportError as ex:          # sin pandas/yfinance no se puede armar el cálculo completo
    print("aviso: control completo salteado:", ex)

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
