"""v1.5.77: cifras trimestrales de las empresas con financiera propia («hasta»: balance del último trimestre, intereses de 12 meses) para que
las renueve la tarea trimestral (pedido de Guille del 17/11/2026), y aviso de «renovar» si quedaron viejas."""
import datetime as dt
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
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


def entrada(ebit=(4.0e9, 3.0e9, 3.0e9, 3.0e9, 3.0e9), ebitda=(5.0e9, 3.8e9, 3.8e9, 3.8e9, 3.8e9), **extra):
    fila = lambda n, v: [n, list(v) if isinstance(v, (list, tuple)) else [v] * len(AN), "m"]  # noqa: E731
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", ebit), fila("EBITDA", ebitda), fila("Gasto por intereses", 783e6),
                                                  fila("Ingresos", (3e10, 2.9e10, 2.8e10, 2.7e10, 2.6e10)), fila("Resultado neto", 2e9),
                                                  fila("Ganancia por acción (diluida)", 4.0)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", 15.6e9), fila("Caja e inversiones de corto plazo", 9.3e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 2e9), fila("Dividendos pagados", -1e9)]}}
    e = {"grupo": "Industrial", "estados": est, "dividendo_anual": 1.4, "hist": None, "hoy": dt.date(2026, 11, 17)}
    e.update(extra)
    return e


def var(r, clave):
    return next((v for v in r["variables"] if v["clave"] == clave), None)


# trimestral: intereses de 12 meses contra el resultado operativo de 12 meses de Yahoo; deuda contra el EBITDA de 12 meses
r = V1.calcular(entrada(financiera_propia={"hasta": "2026-09-30", "intereses": 400e6, "deuda": 9e9, "caja": 6e9}))
chk(abs(var(r, "cobertura")["valor"] - 4.0e9 / 400e6) < 0.01, "trimestral: resultado de 12 meses ÷ intereses de 12 meses")
chk(abs(var(r, "deuda")["valor"] - 3e9 / 5.0e9) < 0.01, "trimestral: deuda neta ÷ EBITDA de 12 meses")
chk(any("2026-09-30" in n for n in r["notas"]) and not any("renovar" in n for n in r["notas"]), "anota la fecha y no pide renovar")
# con ebit y ebitda propios del negocio industrial, mandan esos
r = V1.calcular(entrada(financiera_propia={"hasta": "2026-09-30", "intereses": 400e6, "ebit": 3.2e9, "deuda": 9e9, "caja": 6e9, "ebitda": 4e9}))
chk(abs(var(r, "cobertura")["valor"] - 3.2e9 / 400e6) < 0.01 and abs(var(r, "deuda")["valor"] - 3e9 / 4e9) < 0.01, "ebit/ebitda industriales cargados")
# viejo: más de 200 días
r = V1.calcular(entrada(financiera_propia={"hasta": "2026-03-31", "intereses": 400e6, "deuda": 9e9, "caja": 6e9}))
chk(any("renovar" in n for n in r["notas"]), "más de 200 días: avisa renovar")
# anual sigue igual que en la v1.5.76
r = V1.calcular(entrada(financiera_propia={"anio": 2025, "intereses": 300e6, "deuda": 9e9, "caja": 6e9}))
chk(abs(var(r, "cobertura")["valor"] - 3.0e9 / 300e6) < 0.01 and abs(var(r, "deuda")["valor"] - 3e9 / 3.8e9) < 0.01, "anual: todo del año fiscal")
chk(V1.VIGENCIA_FINANCIERA == 200, "vigencia 200 días")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
