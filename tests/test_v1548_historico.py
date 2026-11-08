"""v1.5.48: archivo histórico propio (data/historico/). Reglas de fusión, splits (pedido explícito de Guille) y lectura desde la app."""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0


def chk(c, m):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("MAL:", m)


from data import historico as H  # noqa: E402

tmp = tempfile.mkdtemp()


def est(anios, ingresos, eps, acciones, moneda="USD"):
    return {"moneda": moneda,
            "resultados": {"anios": anios, "filas": [["Ingresos", ingresos, "t"], ["Ganancia por acción (diluida)", eps, "eps"],
                                                     ["Acciones promedio (diluidas)", acciones, "n"]]},
            "balance": {"anios": anios, "filas": [["Activo total", [100.0] * len(anios), "t"]]}}


# --- años: solo se agregan, manda lo nuevo, un vacío no borra, TTM aparte ---
cam = []
r = H.fusionar_estados(None, est(["2026 (TTM)", 2025, 2024, 2023, 2022], [50, 45, 40, 35, 30], [5, 4.5, 4, 3.5, 3], [10, 10, 10, 10, 10]), "X", cam, "2026-11-08")
chk(sorted(r["anios"]) == ["2022", "2023", "2024", "2025"] and r["ttm"]["etq"] == "2026 (TTM)", "años fiscales guardados y TTM aparte")
r = H.fusionar_estados(r, est(["2027 (TTM)", 2026, 2025, 2024, 2023], [60, 55, 45, 40, 35], [6, 5.5, 4.5, 4, 3.5], [10, 10, 10, 10, 10]), "X", cam, "2027-03-01")
chk(sorted(r["anios"]) == ["2022", "2023", "2024", "2025", "2026"], "Yahoo dejó de traer 2022: queda guardado y se suma 2026")
chk(r["anios"]["2025"]["captura"] == "2026-11-08", "un año sin cambios conserva su fecha de captura")
r = H.fusionar_estados(r, est([2026, 2025, 2024, 2023], [55, 50, 40, None], [5.5, 4.5, 4, 3.5], [10, 10, 10, 10]), "X", cam, "2027-04-01")
chk(r["anios"]["2025"]["resultados"]["Ingresos"] == 50 and any(c["tipo"] == "correccion" and c["anio"] == "2025" for c in cam), "corrección de un año ya guardado: manda la nueva y queda anotada")
chk(r["anios"]["2023"]["resultados"]["Ingresos"] == 35, "un dato vacío no borra uno guardado")
chk(not any(c["tipo"] == "correccion" and c["anio"] == "2024" for c in cam), "sin cambios no se anota nada")

# --- splits en los estados: las cifras por acción guardadas antes de un split se ajustan al leerlas ---
reg = H.fusionar_estados(None, est([2022, 2021], [30, 25], [10.0, 8.0], [100.0, 100.0]), "NF", [], "2025-01-10")
yahoo_hoy = est(["2026 (TTM)", 2025, 2024, 2023], [50, 45, 40, 35], [3.4, 3.0, 2.0, 1.2], [1000, 1000, 1000, 1000])      # ya ajustado por el 10 a 1
comp = H.estados_completos("NF", yahoo_hoy, archivo={"NF": reg}, splits=[["2025-11-17", 10.0]])
an = comp["resultados"]["anios"]
fila = {f[0]: dict(zip(an, f[1])) for f in comp["resultados"]["filas"]}
chk(an[0] == "2026 (TTM)" and 2022 in an and 2021 in an, "se suman los años guardados que Yahoo ya no trae")
chk(abs(fila["Ganancia por acción (diluida)"][2022] - 1.0) < 1e-9 and abs(fila["Acciones promedio (diluidas)"][2022] - 1000) < 1e-9, "split 10 a 1: ganancia por acción ÷10 y acciones ×10 en los años guardados antes")
chk(fila["Ingresos"][2022] == 30, "los montos totales no se tocan con un split")
comp2 = H.estados_completos("NF", yahoo_hoy, archivo={"NF": reg}, splits=[["2024-06-01", 4.0]])
f2 = {f[0]: dict(zip(comp2["resultados"]["anios"], f[1])) for f in comp2["resultados"]["filas"]}
chk(f2["Ganancia por acción (diluida)"][2022] == 10.0, "un split ANTERIOR a la captura no se vuelve a aplicar")
comp3 = H.estados_completos("NF", yahoo_hoy, archivo={"NF": reg}, splits=[["2025-11-17", 0.1]])
f3 = {f[0]: dict(zip(comp3["resultados"]["anios"], f[1])) for f in comp3["resultados"]["filas"]}
chk(abs(f3["Ganancia por acción (diluida)"][2022] - 100.0) < 1e-9, "contra-split 1 por 10 (factor 0,1): ganancia por acción ×10")
# filas por acción en bloque: si Yahoo trae una ya ajustada, no se mezcla con la vieja
r5 = H.fusionar_estados(reg, est([2022], [30], [1.0], [None]), "NF", [], "2025-12-01")
chk(r5["anios"]["2022"]["resultados"].get("Acciones promedio (diluidas)") is None and r5["anios"]["2022"]["captura_acc"] == "2025-12-01",
    "las cifras por acción van en bloque y con su propia fecha de captura")
# solo lo guardado (Yahoo caído)
solo = H.estados_completos("NF", None, archivo={"NF": reg}, splits=[])
chk(solo["resultados"]["anios"] == [2022, 2021], "si Yahoo no trae nada, se arma con lo guardado")
# otra moneda: no se mezclan
regm = H.fusionar_estados(None, est([2020], [9], [1], [1], moneda="EUR"), "M", [], "2025-01-01")
chk(H.estados_completos("M", est([2025], [10], [1], [1], moneda="USD"), archivo={"M": regm}, splits=[])["resultados"]["anios"] == [2025], "años en otra moneda no se mezclan")

# --- precios mensuales, dividendos y splits ---
pares = [(dt.date(2025, 10, 30), 900.0), (dt.date(2025, 10, 31), 910.0), (dt.date(2025, 11, 28), 95.0)]
chk(H.cierres_mensuales(pares) == {"2025-10": 910.0, "2025-11": 95.0}, "cierre mensual = último cierre del mes")
d = os.path.join(tmp, "h1")
H.archivar_mercado("NF", [(dt.date(2025, 9, 30), 1000.0), (dt.date(2025, 10, 31), 1100.0)], [["2025-08-01", 2.0]], [], carpeta=d)
nuevos = H.archivar_mercado("NF", [(dt.date(2025, 12, 31), 93.0)], [], [["2025-11-17", 10.0]], carpeta=d)
cm = H.cierres("NF", carpeta=d)
chk(nuevos == [("2025-11-17", 10.0)] and abs(cm["2025-09"] - 100.0) < 1e-9 and abs(cm["2025-10"] - 110.0) < 1e-9 and cm["2025-12"] == 93.0,
    "split nuevo: los precios guardados anteriores se dividen por 10")
dv = H.leer("dividendos.json", {}, d)["NF"]
chk(dv == [["2025-08-01", 0.2]], "split nuevo: los dividendos guardados anteriores también se ajustan")
chk(any(c["tipo"] == "split" for c in H.leer("cambios.json", [], d)), "el split aplicado queda anotado")
nuevos2 = H.archivar_mercado("NF", [(dt.date(2026, 1, 30), 90.0)], [], [["2025-11-17", 10.0]], carpeta=d)
chk(nuevos2 == [] and abs(H.cierres("NF", carpeta=d)["2025-09"] - 100.0) < 1e-9, "un split ya conocido no se aplica dos veces")
H.archivar_mercado("NUEVA", [(dt.date(2020, 1, 31), 5.0)], [], [["2019-05-01", 2.0]], carpeta=d)
chk(H.cierres("NUEVA", carpeta=d)["2020-01"] == 5.0, "empresa nueva: lo que trae Yahoo ya viene ajustado, no se toca")
chk(H.factor_despues([["2025-11-17", 10], ["2026-06-01", 0.5]], "2025-01-01") == 5.0, "varios splits se multiplican")

# --- fotos mensuales ---
n = H.foto_mensual("empresas", {"KO": {"precio_actual": 70.0, "categoria": "X", "otro": 1}}, ("precio_actual", "categoria"), mes="2026-11", carpeta=d,
                   extra={"KO": {"calidad": "Excelente"}})
H.foto_mensual("empresas", {"KO": {"precio_actual": 71.0}}, ("precio_actual",), mes="2026-11", carpeta=d)
f = H.leer(os.path.join("fotos", "2026-11.json"), {}, d)
chk(n == 1 and f["empresas"]["KO"] == {"precio_actual": 71.0} and "empresas" in f["fechas"], "una foto por mes: si se corre de nuevo, queda la última")
H.foto_mensual("etfs", {"SPY": {"precio": 700.0}}, ("precio",), mes="2026-11", carpeta=d)
f = H.leer(os.path.join("fotos", "2026-11.json"), {}, d)
chk("empresas" in f and "etfs" in f, "cada .bat pisa solo su parte de la foto")
chk(H.ajustar_foto("NF", {"precio_actual": 900.0, "per_actual": 40.0}, "2025-10", splits=[["2025-11-17", 10.0]]) == {"precio_actual": 90.0, "per_actual": 40.0},
    "foto vieja: el precio se ajusta por splits posteriores, los múltiplos no")

# --- múltiplos e informes ---
H.archivar_multiplos({"KO": {"per": {2023: 25.0, 2024: 24.0}}}, carpeta=d)
H.archivar_multiplos({"KO": {"per": {2025: 26.0, 2024: None}}}, carpeta=d)
chk(H.leer("multiplos_anuales.json", {}, d)["KO"]["per"] == {"2023": 25.0, "2024": 24.0, "2025": 26.0}, "múltiplos por año: solo se agregan")
chk(H.archivar_informe("KO", {"fecha": "07/11/2026", "titulo": "t"}, carpeta=d) and not H.archivar_informe("KO", {"fecha": "07/11/2026"}, carpeta=d),
    "cada versión de un informe se guarda una sola vez")
chk(H.informes_guardados("KO", carpeta=d) == ["KO_2026-11-07"], "listado de informes guardados")

# --- el archivo real (arranque del 08/11/2026) ---
R = H.resumen()
chk(R["empresas_con_estados"] >= 323 and R["anio_mas_viejo"] is not None and R["anio_mas_viejo"] <= 2022, "estados de las 323 empresas congelados")
chk("2026-11" in R["fotos"] and "2026-10" in R["fotos"], "fotos de octubre y noviembre de 2026")
chk(R["informes"] >= 60, "todas las versiones de los informes guardadas")
foto = H.leer(os.path.join("fotos", "2026-11.json"))
chk(len(foto.get("empresas", {})) >= 323 and len(foto.get("etfs", {})) >= 90 and len(foto.get("fichas", {})) >= 323, "foto de noviembre: empresas, ETFs y fichas")
chk(os.path.isfile(os.path.join(H.CARPETA, "LEEME.md")), "LEEME del archivo")
# enganches en los .bat y en la app
src = {p: open(p, encoding="utf-8").read() for p in ("generar_cache.py", "bajar_paquetes_yahoo.py", "bajar_etfs_yahoo.py", "bajar_fichas.py",
                                                       "bajar_multiplos_anuales.py", "generar_analisis_fundamental.py", "bajar_historico.py", "app.py")}
chk(all("historico" in v for v in src.values()), "todos los .bat y la app usan el archivo")
chk(os.path.isfile("bajar_historico.bat"), "bajar_historico.bat")
chk("estados_completos(" in src["app.py"], "la ficha suma los años guardados")

shutil.rmtree(tmp, ignore_errors=True)
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
