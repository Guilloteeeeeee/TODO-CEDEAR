"""v1.5.70: Evalúa tu Portfolio. Moneda de los montos (pedido de Guille: «el sistema no sabe detectar la o las monedas»), regla de 2 a 5% sobre
la Renta Variable, oro chico, liquidez estimada, aviso al principio, % pegado, Vista Energy en Argentina y palabras prohibidas del validador.
Uso: python tests/test_v1570_cartera_monedas.py  ->  "OK n MAL 0"."""
import os
import re
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)
os.chdir(AQUI)

from ui import cartera as C  # noqa: E402

ok = mal = 0


def chk(c, txt):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("FALLA:", txt)


TC = 1645.0
ENC = ["Ticker", "Tipo de Instrumento", "Descripcion", "Nominales", "Precio", "Porcentaje de tenencia", "Valor actual", "Moneda"]
# Como el Excel de IOL: la columna Moneda es la del INSTRUMENTO (los bonos dicen Dólares) pero «Valor actual» está en pesos en todas las filas
pos_ars = [("AL29", "Bonos", "BONO USD 2029", 376, 835.8, "Dólares"), ("AO27", "Bonos", "BONO USD 2027", 3951, 1622.7, "Dólares"),
           ("GD30", "Bonos", "BONO USD 2030", 2000, 1100.0, "Dólares"), ("YCA6O", "Corporativos", "ON YPF USD", 1500, 1500.0, "Dólares"),
           ("AAPL", "Cedears", "CEDEAR APPLE", 7, 27960.0, "Pesos"), ("KO", "Cedears", "CEDEAR COCA", 40, 23100.0, "Pesos"),
           ("SPY", "Cedears", "CEDEAR SPY", 30, 45000.0, "Pesos"), ("MSFT", "Cedears", "CEDEAR MSFT", 20, 21000.0, "Pesos")]
tot = sum(c * p for _, _, _, c, p, _ in pos_ars) / 0.9          # 10% de efectivo que el archivo no lista
filas = [ENC] + [[t, ti, d, c, p, round(c * p / tot * 100, 2), c * p, m] for t, ti, d, c, p, m in pos_ars]
pos, notas = C.leer_tabla_info(filas)
chk(all(p["moneda"] == "ars" for p in pos), "IOL: todos los montos en pesos aunque la columna diga Dólares en los bonos")
chk(any("misma moneda" in n for n in notas), "IOL: nota que explica el cambio de moneda")
chk(any(p["ticker"].startswith("Liquidez de la cuenta") for p in pos), "IOL: liquidez estimada con los %")
chk(all(p.get("pct_archivo") for p in pos if not p["ticker"].startswith("Liquidez")), "IOL: se guarda el % del archivo")
chk(C.chequeo_monedas(pos) == [], "IOL leído bien: sin avisos")

# La persona elige «Dólares» en los bonos a mano: aviso
mezcla = [dict(p, moneda="usd") if p["tipo"] in ("Bonos", "Corporativos") else p for p in pos]
av = C.chequeo_monedas(mezcla)
chk(av and "misma moneda" in av[0] and "AL29" in av[0], "aviso si la tabla mezcla monedas y los % dicen que es una sola")

# Un archivo con montos de verdad en dos monedas (los bonos en dólares) no se toca ni avisa
real = [[t, ti, d, c, (p / TC if m == "Dólares" else p), 0, (c * p / TC if m == "Dólares" else c * p), m] for t, ti, d, c, p, m in pos_ars]
for f in real:
    f[5] = round((f[6] * (TC if f[7] == "Dólares" else 1)) / tot * 100, 2)
pos_r, notas_r = C.leer_tabla_info([ENC] + real)
chk(sorted({p["moneda"] for p in pos_r if not p["ticker"].startswith("Liquidez")}) == ["ars", "usd"], "montos de verdad en dos monedas: se respetan")
chk(not any("misma moneda" in n for n in notas_r), "montos de verdad en dos monedas: sin nota de cambio")
chk(C.chequeo_monedas(pos_r) == [], "montos de verdad en dos monedas: sin aviso")

# Precio por unidad de un CEDEAR: 27.960 pesos × ratio 20 ÷ 270 dólares ≈ 2.071 = pesos; 13,5 × 20 ÷ 270 = 1 = dólares
emp, rat = {"AAPL": {"precio_usd": 270.0}}, {"AAPL": 20}
chk(C.moneda_por_precio({"ticker": "AAPL", "precio": 27960.0}, emp, rat) == "ars", "precio por unidad en pesos")
chk(C.moneda_por_precio({"ticker": "AAPL", "precio": 13.5}, emp, rat) == "usd", "precio por unidad en dólares")
chk(C.moneda_por_precio({"ticker": "AAPL", "precio": 300.0}, emp, rat) is None, "precio por unidad que no dice nada")
av = C.chequeo_monedas([{"ticker": "AAPL", "monto": 195720, "moneda": "usd", "precio": 27960.0, "cantidad": 7}], emp, rat)
chk(av and "AAPL" in av[-1], "aviso si el precio por unidad dice otra moneda que la elegida")

# Fila cuyo % no cierra con su monto (por ejemplo, un monto mal cargado)
malo = [dict(p) for p in pos]
malo[4]["monto"] *= 10
chk(any("no cierra" in a and malo[4]["ticker"] in a for a in C.chequeo_monedas(malo)), "aviso si una fila no cierra con su %")

# Regla de 2 a 5% sobre la Renta Variable, oro chico, liquidez estimada, % pegado
empresas = {t: {"nombre": t, "sector": "Tecnología", "pais": "Estados Unidos", "categoria": None} for t in
            ["AAPL", "MSFT", "KO", "PG", "JNJ", "XOM", "JPM", "V", "MA", "UNH", "HD", "PEP", "COST", "WMT", "NVDA", "GOOGL", "AMZN", "META", "LLY", "ABBV"]}
etfs = {"GLD": {"ticker": "GLD", "categoria": "Materias Primas"}}
cart = [{"ticker": t, "monto": 1000.0, "tipo": "Cedear", "moneda": "usd"} for t in empresas]          # 20 empresas, 5% cada una de la RV
cart += [{"ticker": "AL30", "monto": 28000.0, "tipo": "Bono", "moneda": "usd"}, {"ticker": "GLD", "monto": 200.0, "tipo": "", "moneda": "usd"},
         {"ticker": "Liquidez de la cuenta (estimada)", "monto": 6000.0, "tipo": "Efectivo", "moneda": "usd"}]
res = C.analizar(cart, 58, "Moderado", empresas, etfs)
dev = dict(C.devolucion(res, 58, "Moderado", "Ana"))
gics = " ".join(dev.get("Diversificación sectorial (detalle GICS)", []))
chk("pesan menos del 2%" not in gics, "2 a 5% sobre la RV: 20 empresas al 5% de la RV no «pesan menos del 2%»")
chk("2 a 5% de la Renta Variable" in gics, "la teoría dice «de la Renta Variable»")
est = " ".join(dev["Estructura de tu cartera"])
chk("Tu exposición a **Oro** es pequeña" in est and "Sería prudente aumentar tu exposición a Oro" in est, "oro chico: redacción de Guille")
liq = " ".join(dev["Liquidez"])
chk("Según el archivo proporcionado, cerca del" in liq and "Liquidez de la cuenta (estimada) (" not in liq, "liquidez estimada: redacción de Guille, sin repetir")
todo = " ".join(x for _, ps in C.devolucion(res, 58, "Moderado", "Ana") for x in ps)
chk(not re.search(r"\d %", todo), "el % va pegado al número en toda la devolución")
chk("Comparada con la cartera de referencia" in todo and "ajustaríamos" not in todo, "conclusión sin «qué ajustaríamos»")
chk("No es una recomendación personalizada" in C.AVISO_INICIO, "aviso al principio de la evaluación")

# Vista Energy: su negocio está en Argentina aunque Yahoo diga México
emp_v = {"VIST": {"nombre": "Vista", "sector": "Energía", "pais": "Mexico", "categoria": None}}
chk(C.clasificar({"ticker": "VIST", "monto": 100, "tipo": "Cedear"}, emp_v, {})["info"]["pais"] == "Argentina", "VIST: Argentina")

# Validador de informes: palabras prohibidas por Guille
from data import af_v4 as V  # noqa: E402
for w in ("ojo", "remedios", "dosis chica"):
    chk(w in V.PROHIBIDAS, f"validador: «{w}» prohibida")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
