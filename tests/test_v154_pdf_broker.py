"""v1.5.4: lectura de resúmenes de IOL (tabla con coma decimal, sin puntos de miles), sección Fondos de Balanz (Money Market = liquidez), alias de tickers BYMA,
frases nuevas (calificación crediticia, «posición pequeña») y guardas de sectores/geografía."""
import io, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ui import cartera as C
import data.etfs as DE
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1
    else: bad += 1; print("FALLA:", m)

def pdf(lineas):
    from reportlab.pdfgen import canvas
    b = io.BytesIO(); c = canvas.Canvas(b); y = 800
    for l in lineas:
        c.drawString(30, y, l); y -= 14
    c.save(); return b.getvalue()

iol = pdf(["Resumen de Cuenta", "Disponible Pesos *", "Títulos Valorizados",
           "Cedear Apple Inc. AAPL BCBA 27,0000 AR$ 28620,000 772740,000",
           "Bono Rep. Argentina Usd Step Up 2030 AL30 BCBA 1,0000 AR$ 84110,000 841,100",
           "Cresud CRES BCBA 48,0000 AR$ 1630,000 78240,000",
           "Saldo Total Títulos Val.: AR$ 851821,10", "MERVAL 2.995,56", "COL 20 1.305,056", "BOVESPA 59.600,66"])
pos, notas, tc = C.leer_pdf_info(iol)
d = {p["ticker"]: p for p in pos}
chk(len(pos) == 3, f"IOL: 3 posiciones, hubo {len(pos)}")
chk(abs(d["AAPL"]["monto"] - 772740) < 1 and d["AAPL"]["moneda"] == "ars", "IOL: AAPL 772.740 en pesos")
chk(abs(d["AL30"]["monto"] - 841.1) < 0.01, "IOL: AL30 841,10")
chk(not any(p["ticker"] in ("COL", "MERVAL", "BOVESPA") for p in pos), "IOL: sin líneas de índices")
chk(abs(sum(p["monto"] for p in pos) - 851821.1) < 0.5, "IOL: la suma coincide con el total del resumen")

bz = pdf(["Instrumentos", "Fondos USD 3.392", "Monedas", "Pesos $ 1.996,04", "Tipo de cambio para esa fecha: MEP $ 1.567,23 | US Dollar $ 1.658,33",
          "Corporativos", "Especie Descripción Cantidad Garantía Precio Valor Actual",
          "IRCPO ON IRSA INVERSIONES 8% 31/03/35 300,00 0.00 u$s 1,05 u$s 316",
          "Fondos", "Especie Descripción Cantidad Garantía Precio Valor Actual",
          "BCMMUSDA Balanz Money Market USD Clase A 3.302,44 0.00 u$s 1,03 u$s 3.392"])
pos, notas, tc = C.leer_pdf_info(bz)
d = {p["ticker"]: p for p in pos}
chk("BCMMUSDA" in d and d["BCMMUSDA"]["tipo"] == "Money Market", f"Balanz: fondo money market, hubo {d.get('BCMMUSDA')}")
chk(C.clase_de_tipo(d["BCMMUSDA"]["tipo"]) == "efectivo", "Balanz: money market = liquidez")
chk(d["IRCPO"]["tipo"] == "Corporativos", "Balanz: la ON sigue en Corporativos")
chk(tc and abs(tc - 1567.23) < 0.01, "Balanz: dólar MEP del resumen")

rows = json.load(open(os.path.join(ROOT, "data", "cache_datos.json")))["data"]
emp = {C.clave_tk(r["ticker"]): {"nombre": r.get("nombre"), "sector": r.get("sector"), "pais": r.get("pais"), "categoria": r.get("categoria"), "beta": r.get("beta")} for r in rows}
etfs = {C.clave_tk(e["ticker"]): e for e in DE.cargar()}
def P(t, m, tipo=""): return {"ticker": t, "monto": m, "tipo": tipo, "moneda": "usd"}
chk(C.clasificar(P("DISN", 100, "Cedear"), emp, etfs)["fuente"] == "empresa", "alias: DISN = DIS")
chk(C.clasificar(P("PETR3", 100, "Cedears"), emp, etfs)["fuente"] == "empresa", "alias: PETR3 = PBR")
chk(C.clasificar(P("VIST", 100, "Cedear"), emp, etfs)["info"]["pais"] == "Argentina", "VIST: Argentina")
chk(C.clasificar(P("AO27", 100, "Bonos"), emp, etfs)["clase"] == "rf" and C.subtipo_rf("AO27", "Bonos") == "ar", "AO27: bono argentino")

# el caso de poca renta variable con mucha liquidez: no debe decir «no tenés Renta Variable» si el texto de arriba da un porcentaje
pos = [P("Efectivo", 9800, "Efectivo"), P("AAPL", 100, "Cedear"), P("KO", 100, "Cedear")]
res = C.analizar(pos, 55, "Moderado", emp, etfs)
txt = " ".join(" ".join(ps) for _, ps in C.devolucion(res, 55, "Moderado", "Ana"))
chk("no hay sectores para analizar" not in txt, "no dice «no hay sectores» si hay Renta Variable")
chk("dosis chic" not in txt.lower(), "sin «dosis chica»")
pos = [P("AAPL", 5000, "Cedear"), P("AL30", 1000, "Renta fija"), P("IRCPO", 1000, "Obligación negociable")]
txt = " ".join(" ".join(ps) for _, ps in C.devolucion(C.analizar(pos, 40, "Moderado", emp, etfs), 40, "Moderado", ""))
chk("el programa no evalúa la calidad de cada empresa emisora: sería prudente mirar la calificación crediticia de cada una" in txt, "frase de calificación crediticia")
src = open(os.path.join(ROOT, "ui", "cartera.py"), encoding="utf-8").read()
chk("dosis chic" not in src.lower(), "el código no tiene «dosis chica»")
print(f"OK {ok} MAL {bad}")
