"""v1.5.79 (Guille 17/11/2026: «mitad y mitad, 15 puntos de 100 la deuda» / «bancos, misma lógica» / «revisá National Grid y KEPCO»):
deuda de las utilities repartida 7,5 + 7,5, pago futuro de los bancos con su corte (50 / 75), ganancia por acción pasada a dólares por ADR
en las empresas con estados en otra moneda, deuda del último trimestre que no cierra con el pasivo (KEPCO) y dividendo regular de las que
pagan a cuenta y final con un pago de más en el año (National Grid)."""
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


from scoring import dividendo as V0, dividendo_v1 as V1  # noqa: E402

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def entrada(grupo="Industrial", eps=4.0, neto=4e9, dpa=2.4, est_g=None, deuda=15.6e9, pasivo=2e10, **extra):
    fila = lambda n, v: [n, list(v) if isinstance(v, (list, tuple)) else [v] * len(AN), "m"]  # noqa: E731
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8),
                                                  fila("Ingresos", (3.3e10, 3.2e10, 3.1e10, 3.0e10, 2.8e10)), fila("Resultado neto", neto),
                                                  fila("Ganancia por acción (diluida)", eps)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", deuda), fila("Caja e inversiones de corto plazo", 9.3e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9),
                                               fila("Pasivo total", pasivo)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 4e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 3e9)]}}
    hist = {"racha_subas": 3, "anios_sin_suba": 0, "recortes": [], "ultimo_completo": 2025, "tasa": {2024: 2.3, 2025: 2.4}, "anios_sin_recorte": 3}
    e = {"grupo": grupo, "estados": est, "dividendo_anual": dpa, "historial": hist, "fuente_historial": "dolares"}
    if est_g is not None:
        e["estimacion"] = est_g
    e.update(extra)
    return e


def var(r, clave):
    return next((v for v in r["variables"] if v["clave"] == clave), None)


# --- 1) utilities: 15 puntos de deuda = 7,5 deuda neta ÷ EBITDA + 7,5 FFO ÷ Deuda; total sobre 100 ----------------------------------
r = V1.calcular(entrada(grupo="Utilities"))
chk(var(r, "deuda")["max"] == 7.5 and var(r, "ffo_deuda")["max"] == 7.5, "deuda 7,5 + FFO ÷ Deuda 7,5")
chk(sum(v["max"] for v in r["variables"]) == 100, f"utility: máximo 100 ({sum(v['max'] for v in r['variables'])})")
r = V1.calcular(entrada(grupo="Utilities", ffo_deuda_sp={"ffo_deuda": 12.0, "anio": 2025}))
chk(var(r, "ffo_deuda")["pts"] == 3.5, "FFO ÷ Deuda en zona gris: 3,5")
r = V1.calcular(entrada(grupo="Utilities", deuda=7e9 * 6.5 + 9.3e9))     # deuda neta ÷ EBITDA = 6,5 (crítica > 6)
chk(var(r, "deuda")["pts"] == 0, "deuda neta ÷ EBITDA crítica: 0")
r = V1.calcular(entrada())
chk(var(r, "deuda")["max"] == 15 and var(r, "ffo_deuda") is None, "las demás siguen con 15 de deuda")

# --- 2) bancos: pago futuro con su corte (segura < 50 %, crítica ≥ 75 %) -----------------------------------------------------------
for g, pts in ((6.0, 15), (4.0, 7), (3.0, 0)):                         # 2,4 ÷ g = 40 %, 60 %, 80 %
    r = V1.calcular(entrada(grupo="Bancos y seguros", eps=4.0, est_g={"actual": g, "proximo": g}, cet1=13.0))
    chk(var(r, "payout_futuro")["pts"] == pts, f"banco, pago futuro {round(2.4 / g * 100)} % → {pts} ({var(r, 'payout_futuro')})")
r = V1.calcular(entrada(est_g={"actual": 4.0, "proximo": 4.0}))        # 60 %: en las generales sigue la escala 55 / 80
chk(var(r, "payout_futuro")["pts"] == 7, "general con 60 %: 7")

# --- 3) estados en otra moneda: la ganancia se pasa a dólares por ADR ---------------------------------------------------------------
# National Grid: 3,24 dólares de dividendo por ADR, 3,26 libras de ganancia por ADR, 1,345 dólares por libra → 74 % (no 99 %)
ngg = dict(grupo="Utilities", eps=3.26, neto=3.24e9, dpa=3.24, moneda_estados="GBP", fx=1.34539, market_cap=1.0e9 * 85.78, precio=85.78)
r = V1.calcular(entrada(**ngg))
chk(abs(var(r, "eps_payout")["valor"] - 73.9) < 0.2, f"National Grid: pago sobre ganancias 73,9 % ({var(r, 'eps_payout')['valor']})")
# banco coreano: ganancia en wones por acción y estimación de los analistas en wones (KB)
kb = dict(grupo="Bancos y seguros", eps=16000.0, neto=16000.0 * 3.6e8, dpa=3.0, moneda_estados="KRW", fx=0.00074, market_cap=3.6e8 * 110, precio=110.0,
          cet1=13.0, est_g={"actual": 18000.0, "proximo": 18000.0})
r = V1.calcular(entrada(**kb))
chk(abs(var(r, "eps_payout")["valor"] - 3.0 / (16000 * 0.00074) * 100) < 0.1, f"KB: pago sobre ganancias en dólares ({var(r, 'eps_payout')['valor']})")
chk(abs(var(r, "payout_futuro")["valor"] - 3.0 / (18000 * 0.00074) * 100) < 0.1, f"KB: estimación en wones pasada a dólares ({var(r, 'payout_futuro')['valor']})")
# estimación ya en dólares por ADR (TSMC): no se vuelve a convertir
r = V1.calcular(entrada(**dict(kb, est_g={"actual": 13.5, "proximo": 13.5})))
chk(abs(var(r, "payout_futuro")["valor"] - 3.0 / 13.5 * 100) < 0.1, "estimación en dólares: queda como está")
# acciones del balance que no son las del ADR (Santander Brasil: 2 por ADR)
bsbr = dict(grupo="Bancos y seguros", eps=1.6, neto=1.6 * 7.8e9, dpa=0.5, moneda_estados="BRL", fx=0.182, market_cap=3.9e9 * 5.5, precio=5.5, cet1=13.0)
r = V1.calcular(entrada(**bsbr))
chk(abs(var(r, "eps_payout")["valor"] - 0.5 / (1.6 * 0.182 * 2) * 100) < 0.2, f"2 acciones por ADR ({var(r, 'eps_payout')['valor']})")
# Yahoo marca reales pero los estados vienen en dólares (Petrobras): precio ÷ PER coincide con la ganancia sin convertir
pbr = dict(eps=3.04, neto=3.04 * 6.45e9, dpa=1.5, moneda_estados="BRL", fx=0.182, market_cap=6.45e9 * 19, precio=19.0, per=5.0,
           est_g={"actual": 4.66, "proximo": 4.66})
r = V1.calcular(entrada(**pbr))
chk(any("estados en dólares" in n for n in r["notas"]), "Petrobras: estados en dólares aunque Yahoo diga reales")
chk(abs(var(r, "payout_futuro")["valor"] - 1.5 / 4.66 * 100) < 0.1, f"Petrobras: pago futuro sin convertir ({var(r, 'payout_futuro')['valor']})")
r = V1.calcular(entrada(**dict(pbr, per=34.0)))                         # si el PER dice que sí están en reales, se convierten
chk(not any("estados en dólares" in n for n in r["notas"]), "con PER coherente con reales, se convierte")
# sin capitalización: las acciones por ADR salen de precio ÷ PER (Coca-Cola FEMSA: 10 por ADR)
kof = dict(eps=14.5, neto=14.5 * 2.1e9, dpa=3.7, moneda_estados="MXN", fx=0.05377, precio=114.4, per=114.4 / (14.5 * 0.05377 * 10),
           est_g={"actual": 6.6, "proximo": 6.6})
r = V1.calcular(entrada(**kof))
chk(abs(var(r, "payout_futuro")["valor"] - 3.7 / 6.6 * 100) < 1, f"KOF: estimación por ADR ({var(r, 'payout_futuro')['valor']})")
# con pérdida en los dos últimos períodos, la base se reconoce con un año anterior (Honda)
fila_eps = [-318.0, -300.0, 480.0, 450.0, 400.0]
hmc = dict(eps=fila_eps, neto=-4e11, dpa=1.4, moneda_estados="JPY", fx=0.00634, est_g={"actual": 2.6, "proximo": 2.6})
r = V1.calcular(entrada(**hmc))
chk(var(r, "payout_futuro") is not None and abs(var(r, "payout_futuro")["valor"] - 1.4 / 2.6 * 100) < 0.5,
    f"Honda: pago futuro con la base de un año con ganancia ({var(r, 'payout_futuro')})")
# las de dólares no cambian
r = V1.calcular(entrada(grupo="Utilities", eps=4.0))
chk(abs(var(r, "eps_payout")["valor"] - 60.0) < 0.01, "en dólares sigue dividendo ÷ ganancia por acción")

# --- 4) deuda del último trimestre que no cierra con el pasivo (KEPCO) ---------------------------------------------------------------
kep = entrada(grupo="Utilities", deuda=[3.1e12, 132.9e12, 130e12, 125e12, 120e12], pasivo=[210.7e12, 205.6e12, 200e12, 195e12, 190e12])
r = V1.calcular(kep)
chk(any("deuda del último trimestre descartada" in n for n in r["notas"]), "KEPCO: deuda del trimestre descartada")
chk(abs(var(r, "ffo_deuda")["valor"] - 3e9 / 132.9e12 * 100) < 1e-6, "usa la deuda del cierre del año")
pago = entrada(deuda=[0.45e9, 1.96e9, 2.0e9, 2.0e9, 2.0e9], pasivo=[5.57e9, 6.69e9, 6.5e9, 6.4e9, 6.3e9])   # Spotify: pagó de verdad
r = V1.calcular(pago)
chk(not any("descartada" in n for n in r["notas"]), "si el pasivo baja con la deuda, es un pago: queda")

# --- 5) dividendo regular con pagos a cuenta y final y un pago de más en el año (National Grid) ---------------------------------------
import datetime as dt  # noqa: E402
pagos = [("2022-06-02", 2.093), ("2022-11-23", 1.031), ("2023-06-01", 2.346), ("2023-11-22", 1.19),
         ("2024-05-31", 3.506), ("2024-06-07", 2.494), ("2024-11-22", 1.02), ("2025-05-30", 2.60), ("2025-11-21", 1.25), ("2026-05-29", 2.7)]
h = V0.analizar_dividendos(pagos, hoy=dt.date(2026, 11, 17))
chk(2025 not in h["recortes"], f"el «pago» de la ampliación de 2024 no infla el año ni hace ver un recorte en 2025 ({h['recortes']})")
chk(abs(h["tasa"][2024] - (2.494 + 1.02)) < 1e-6, f"2024 = final + a cuenta ({h['tasa'][2024]})")
pagos_b = pagos[:7] + [("2025-05-30", 2.00), ("2025-11-21", 1.0), ("2026-05-29", 2.1)]
h = V0.analizar_dividendos(pagos_b, hoy=dt.date(2026, 11, 17))
chk(2025 in h["recortes"], "si de verdad baja, sigue siendo recorte")
# trimestrales con un extraordinario: sin cambios (mediana × 4)
q = [(f"{a}-{m:02d}-15", 1.0 + 0.04 * (a - 2020)) for a in range(2020, 2026) for m in (2, 5, 8, 11)] + [("2023-12-20", 5.0)]
h = V0.analizar_dividendos(q, hoy=dt.date(2026, 11, 17))
chk(h["recortes"] == [] and abs(h["tasa"][2023] - 1.12 * 4) < 1e-6, f"trimestral con extraordinario: igual que antes ({h['recortes']}, {h['tasa'][2023]})")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
