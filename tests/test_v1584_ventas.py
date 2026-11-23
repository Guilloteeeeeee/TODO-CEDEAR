"""v1.5.84 (Guille 23/11/2026: «ok ventas»): si la empresa separó un negocio y volvió a presentar solo los años recientes sin él
(data/ventas_comparables.json), el crecimiento de ventas del score v1 se mide desde el primer año comparable (2 años como mínimo)."""
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

AN = ["2026 (TTM)", 2025, 2024, 2023, 2022]


def entrada(ingresos, comparables=None):
    fila = lambda n, v: [n, list(v) if isinstance(v, (list, tuple)) else [v] * len(AN), "m"]  # noqa: E731
    est = {"resultados": {"anios": AN, "filas": [fila("Resultado operativo", 6e9), fila("EBITDA", 7e9), fila("Gasto por intereses", 2e8),
                                                  fila("Ingresos", ingresos), fila("Resultado neto", 4e9), fila("Ganancia por acción (diluida)", 4.0)]},
           "balance": {"anios": AN, "filas": [fila("Deuda total", 1.5e10), fila("Caja e inversiones de corto plazo", 9e9), fila("Activo total", 4e10),
                                               fila("Activo corriente", 2e10), fila("Pasivo corriente", 1e10), fila("Inventarios", 2e9)]},
           "flujo": {"anios": AN, "filas": [fila("Flujo de efectivo libre", 4e9), fila("Dividendos pagados", -1e9), fila("Flujo de efectivo operativo", 5e9)]}}
    e = {"grupo": "Consumo Básico", "estados": est, "dividendo_anual": 2.4,
         "historial": {"racha_subas": 3, "anios_sin_suba": 0, "recortes": [], "ultimo_completo": 2025, "anios_sin_recorte": 10}, "fuente_historial": "dolares"}
    if comparables:
        e["ventas_comparables"] = comparables
    return e


def ventas(r):
    return next(v for v in r["variables"] if v["clave"] == "ventas")


# Ejemplo A de Guille: 2022 con el negocio separado (100), 2023 a 2025 sin él (80, 82, 84)
serie = (85e9, 84e9, 82e9, 80e9, 100e9)
r = V1.calcular(entrada(serie))
chk(ventas(r)["valor"] < -5 and ventas(r)["pts"] == 0, f"como lo trae Yahoo: cae ({ventas(r)})")
r = V1.calcular(entrada(serie, {"desde": 2023}))
chk(abs(ventas(r)["valor"] - ((84 / 80) ** 0.5 - 1) * 100) < 1e-6 and ventas(r)["pts"] == 5, f"desde 2023: +2,5 % por año, zona gris ({ventas(r)})")
chk(any("ventas desde 2023" in n for n in r["notas"]), "lo anota")
r = V1.calcular(entrada(serie, {"desde": 2024}))
chk(ventas(r)["valor"] is None, "con menos de 2 años comparables no se mide")
r = V1.calcular(entrada(serie, {"desde": 2020}))
chk(ventas(r)["valor"] < -5 and not any("ventas desde" in n for n in r["notas"]), "un «desde» anterior a la ventana no cambia nada")

# el archivo: cada empresa con desde, motivo, fuente y fecha de revisión
d = json.load(open(os.path.join(RAIZ, "data", "ventas_comparables.json"), encoding="utf-8"))
for tk, x in d["empresas"].items():
    chk(isinstance(x.get("desde"), int) and x.get("motivo") and x.get("fuente") and x.get("revisado"), f"{tk}: desde, motivo, fuente y revisado")
chk(V1.ventas_comparables("UL")["desde"] == 2023 and V1.ventas_comparables("KO") is None, "lectura del archivo")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
