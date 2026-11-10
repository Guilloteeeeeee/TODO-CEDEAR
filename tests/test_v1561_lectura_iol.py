"""v1.5.61: Excel «Mis Instrumentos» de IOL: Money Market = liquidez, efectivo no listado estimado con el % de tenencia; moneda declarada en el paso 2."""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
from ui import cartera as C
import io, openpyxl
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["Ticker", "Tipo de Instrumento", "Descripcion", "Nominales", "Valor actual", "Porcentaje de tenencia", "Moneda"])
filas = [("AAPL", "Cedears", "CEDEAR APPLE", 10, 100000, 10), ("MSFT", "Cedears", "CEDEAR MICROSOFT", 10, 200000, 20), ("KO", "Cedears", "CEDEAR COCA", 10, 100000, 10),
         ("AL29", "Bonos", "BONO REP ARGENTINA", 10, 200000, 20), ("DNC7O", "Corporativos", "ON EDENOR", 10, 150000, 15), ("BCMMA", "Fondos", "Money Market Clase A", 10, 50000, 5)]
for t, ti, d, n, v, p in filas:
    ws.append([t, ti, d, n, v, p, "Dólares" if t == "AL29" else "Pesos"])
b = io.BytesIO(); wb.save(b)
pos, nota = C.leer_archivo_info("x.xlsx", b.getvalue())
d = {p["ticker"]: p for p in pos}
chk(d["BCMMA"]["tipo"] == "Money Market" and C.clase_de_tipo(d["BCMMA"]["tipo"]) == "efectivo", "Money Market por la descripción")
liq = d.get("Liquidez de la cuenta (estimada)")
chk(liq and liq["tipo"] == "Efectivo" and abs(liq["monto"] - 200000) < 1, f"efectivo estimado: 80 % listado → 20 % = 200.000 ({liq})")
chk("suman 80" in nota, "la nota avisa")
# sin porcentaje que falte: no se inventa efectivo
ws2 = openpyxl.Workbook().active
ws2.append(["Ticker", "Tipo", "Valor actual", "Porcentaje de tenencia"])
for t, v, p in (("AAPL", 100, 20), ("MSFT", 100, 20), ("KO", 100, 20), ("PG", 100, 20), ("JNJ", 100, 20)): ws2.append([t, "Cedears", v, p])
b2 = io.BytesIO(); ws2.parent.save(b2)
p2, _ = C.leer_archivo_info("y.xlsx", b2.getvalue())
chk(not any("Liquidez" in x["ticker"] for x in p2), "con 100 % no se agrega efectivo")
src = open("app.py", encoding="utf-8").read()
chk("_OPC_MONEDA" in src and "elegir la moneda de tu archivo" in src, "el paso 2 pide la moneda y es obligatoria")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
