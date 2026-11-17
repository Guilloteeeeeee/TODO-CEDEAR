"""v1.5.76: empresas con financiera propia (cobertura y deuda del negocio industrial, como SSD; decisión de Guille) y NextEra con intereses
pagados en lugar del gasto (su línea de intereses mezcla coberturas de tasa; decisión de Guille)."""
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

# --- 1) archivo de financieras propias ------------------------------------------------------------------------------------------
fin = json.load(open(os.path.join(RAIZ, "data", "financieras_propias.json"), encoding="utf-8"))["datos"]
for t in ("PCAR", "DE", "GM", "F", "IBM", "TM", "HMC"):
    f = fin.get(t) or {}
    tiene_deuda = f.get("deuda_neta") is not None or (f.get("deuda") is not None and f.get("caja") is not None)
    chk(tiene_deuda and f.get("anio") and f.get("fuentes") and len(f.get("medida") or "") > 40, f"{t}: deuda del negocio industrial con año y fuente")
    chk(all(u.startswith("https://") for u in f.get("fuentes", [])), f"{t}: fuentes como enlaces")
for t in ("CAT", "HOG"):
    chk(bool((fin.get(t) or {}).get("pendiente")), f"{t}: figura como pendiente y explica por qué no cambia el puntaje")
chk(fin["PCAR"]["intereses"] == 0 and fin["PCAR"]["deuda"] == 0, "PACCAR: el negocio de camiones no tiene deuda ni intereses")
chk(fin["DE"]["intereses"] == 372000000 and fin["DE"]["deuda"] == 9170000000 and fin["DE"]["caja"] == 6557000000, "Deere: cifras de Equipment Operations")
chk(V1.financiera_propia("PCAR") is not None and V1.financiera_propia("KO") is None, "financiera_propia lee el archivo")

# --- 2) cálculo con una entrada armada ------------------------------------------------------------------------------------------
AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def entrada(gasto=783e6, pagados=None, deuda=15.6e9, caja=9.3e9, ebit=3.0e9, ebitda=3.8e9, **extra):
    fila = lambda n, v: [n, v if isinstance(v, list) else [v] * len(AN), "m"]  # noqa: E731
    flujo = [fila("Flujo de efectivo libre", 2e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 3e9)]
    if pagados is not None:
        flujo.append(fila("Intereses pagados", pagados))
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", ebit), fila("EBITDA", ebitda), fila("Gasto por intereses", gasto),
                                                  fila("Ingresos", [3e10, 2.9e10, 2.8e10, 2.7e10, 2.6e10]), fila("Resultado neto", 2e9),
                                                  fila("Ganancia por acción (diluida)", 4.0)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", deuda), fila("Caja e inversiones de corto plazo", caja), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]},
           "flujo": {"anios": AN, "filas": flujo}}
    e = {"grupo": "Industrial", "estados": est, "dividendo_anual": 1.4, "hist": None}
    e.update(extra)
    return e


def var(r, clave):
    return next((v for v in r["variables"] if v["clave"] == clave), None)


r = V1.calcular(entrada())
chk(abs(var(r, "cobertura")["valor"] - 3.0e9 / 783e6) < 0.01 and var(r, "cobertura")["pts"] == 10, "sin la regla: 3,8 veces → zona gris")
r = V1.calcular(entrada(financiera_propia={"anio": 2025, "intereses": 0, "deuda": 0, "caja": 9.25e9}))
chk(var(r, "cobertura")["valor"] == 99.0 and var(r, "cobertura")["pts"] == 25, "PACCAR: negocio de camiones sin intereses → cobertura máxima")
chk(var(r, "deuda")["valor"] == -1.0 and var(r, "deuda")["pts"] == 15, "PACCAR: le sobra caja → deuda segura")
chk(any("sin su financiera" in n for n in r["notas"]), "lo anota")
r = V1.calcular(entrada(financiera_propia={"anio": 2025, "intereses": 372e6, "ebit": 5.517e9, "deuda": 9.17e9, "caja": 6.557e9, "ebitda": 6.797e9}))
chk(abs(var(r, "cobertura")["valor"] - 5.517e9 / 372e6) < 0.01, "Deere: resultado operativo industrial ÷ intereses industriales")
chk(abs(var(r, "deuda")["valor"] - (9.17e9 - 6.557e9) / 6.797e9) < 0.01 and var(r, "deuda")["pts"] == 15, "Deere: deuda neta industrial ÷ EBITDA industrial")
r = V1.calcular(entrada(financiera_propia={"anio": 2025, "deuda": 46.2e9, "caja": 14.5e9}))
chk(abs(var(r, "cobertura")["valor"] - 3.0e9 / 783e6) < 0.01, "sin intereses cargados: cobertura normal (Yahoo ya los trae sin la financiera)")
chk(abs(var(r, "deuda")["valor"] - 31.7e9 / 3.8e9) < 0.01, "sin EBITDA industrial: EBITDA consolidado del año")
r = V1.calcular(entrada(financiera_propia={"anio": 2025, "deuda_neta": -3.3e12}))
chk(var(r, "deuda")["valor"] == -1.0, "deuda neta directa (Honda: caja neta)")
r = V1.calcular(entrada(financiera_propia={"anio": 2025, "pendiente": "falta la deuda"}))
chk(abs(var(r, "deuda")["valor"] - (15.6e9 - 9.3e9) / 3.8e9) < 0.01, "pendiente: sigue la deuda consolidada")
r = V1.calcular(entrada(financiera_propia={"anio": 2024, "intereses": 0, "deuda": 0, "caja": 1e9}))
chk(any("renovar" in n for n in r["notas"]), "cifras de un año viejo: avisa que hay que renovar")

# --- 3) NextEra: intereses pagados en lugar del gasto -----------------------------------------------------------------------------
man = {"anio": 2025, "monto": 3.5e9, "solo_pagados": True, "medida": "pagados"}
r = V1.calcular(entrada(gasto=[564e6, 4.572e9, 2.235e9, 3.324e9, 585e6], ebit=[8.35e9, 8.02e9, 7.1e9, 10e9, 4e9], intereses_manual=man))
chk(abs(var(r, "cobertura")["valor"] - 8.02e9 / 3.5e9) < 0.01 and var(r, "cobertura")["pts"] == 10, "NextEra sin la fila de Yahoo: pagados cargados (2,3 veces)")
r = V1.calcular(entrada(gasto=[564e6, 4.572e9, 2.235e9, 3.324e9, 585e6], pagados=[4.0e9, 3.5e9, 2.74e9, 2.46e9, 1.38e9],
                        ebit=[8.35e9, 8.02e9, 7.1e9, 10e9, 4e9], intereses_manual=man))
chk(abs(var(r, "cobertura")["valor"] - 8.35e9 / 4.0e9) < 0.01, "NextEra con la fila de Yahoo: pagados de los 12 meses, nunca el gasto de 564 millones")
r = V1.calcular(entrada(gasto=[564e6, 4.572e9, 2.235e9, 3.324e9, 585e6], ebit=[8.35e9, 8.02e9, 7.1e9, 10e9, 4e9]))
chk(var(r, "cobertura")["valor"] > 14, "sin la regla, la línea deformada daría 14,8 veces (por eso la regla)")
im = json.load(open(os.path.join(RAIZ, "data", "intereses_manuales.json"), encoding="utf-8"))["datos"]
chk(im["NEE"].get("solo_pagados") is True and im["NEE"]["monto"] == 3.5e9 and im["NEE"]["fuentes"], "NEE cargada con solo_pagados y fuente")
chk(sum(1 for v in im.values() if v.get("solo_pagados")) == 1, "solo NEE usa la regla por ahora")

# --- 4) listado de gasto contra pagados en la calibración -------------------------------------------------------------------------
try:
    import calibrar_dividendo as C
    est = {"resultados": {"anios": AN, "filas": [["Gasto por intereses", [564e6, 4.572e9, 2.235e9, None, None], "m"]]},
           "flujo": {"anios": AN, "filas": [["Intereses pagados", [None, 3.5e9, 2.74e9, None, None], "m"]]}}
    c = C.comparar_intereses(est)
    chk(c == {"anio": 2025, "gasto": 4.572e9, "pagados": 3.5e9}, f"compara el último año con los dos datos ({c})")
    lin = C.listado_intereses({"NEE": {"intereses_fy": c}, "KO": {"intereses_fy": {"anio": 2025, "gasto": 1e9, "pagados": 0.95e9}}})
    chk(any("NEE" in x for x in lin) and not any("KO " in x for x in lin), "lista solo las diferencias grandes")
    chk("bajar_paquetes" in C.listado_intereses({"X": {}})[0], "sin la fila de Yahoo avisa qué correr")

    # --- 5) con los datos reales del repositorio --------------------------------------------------------------------------------
    from data import historico as H, paquetes_yahoo as PY
    cache = {x["ticker"]: x for x in json.load(open("data/cache_datos.json", encoding="utf-8"))["data"]}
    esti = json.load(open("data/estimaciones_analistas.json", encoding="utf-8"))["datos"]
    res = C.calcular_todo(["PCAR", "DE", "GM", "TM", "IBM", "NEE"], cache, PY.cargar()[0], H.leer("estados.json", {}), H.leer("splits.json", {}),
                          H.leer("dividendos.json", {}), H.leer("precios_mensuales.json", {}), esti)
    v = {t: (res[t].get("v1") or {}) for t in res}
    for t in ("PCAR", "DE"):
        chk(var(v[t], "cobertura")["pts"] == 25, f"{t}: cobertura del negocio industrial en zona segura")
    for t in ("PCAR", "DE", "GM", "TM", "IBM"):
        chk(var(v[t], "deuda")["pts"] == 15, f"{t}: deuda del negocio industrial en zona segura ({var(v[t], 'deuda')})")
    nee = var(v["NEE"], "cobertura")
    chk(nee["valor"] is not None and nee["valor"] < 3, f"NEE: cobertura con intereses pagados, no la de 14,8 ({nee})")
except ImportError as ex:
    print("aviso: parte con datos reales salteada:", ex)

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
