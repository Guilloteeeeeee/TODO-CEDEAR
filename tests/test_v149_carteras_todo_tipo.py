"""v1.4.9: carteras de todo tipo (pedido de Guille: 'va a haber inversores de todo tipo con todo tipo de cartera')."""
import json, sys, random, re, io
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ui import cartera as C, cartera_visual as CV, cartera_informe as CI
from data import carteras_modelo as CM
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1
    else: bad += 1; print("FALLA:", m)
rows = json.load(open(os.path.join(ROOT, "data", "cache_datos.json")))["data"]
emp = {C.clave_tk(r["ticker"]): {"nombre": r.get("nombre"), "sector": r.get("sector"), "pais": r.get("pais"), "categoria": r.get("categoria"), "beta": r.get("beta")} for r in rows}
import data.etfs as DE
etfs = {C.clave_tk(e["ticker"]): e for e in DE.cargar()}
tks = list(emp)[:150]; etk = list(etfs)
def P(t, m, tipo="", pais=""):
    return {"ticker": t, "monto": m, "tipo": tipo, "moneda": "usd", "pais": pais}
casos = {
 "solo_efectivo": [P("Efectivo", 1000, "Liquidez")],
 "solo_cripto": [P("BTC", 1000, "Cripto"), P("ETH", 500, "Cripto")],
 "solo_oro": [P("GLD", 1000)],
 "solo_bonos_ar": [P("AL30", 1000, "Renta fija"), P("GD35", 2000, "Renta fija"), P("ON YPF", 500, "Obligación negociable")],
 "solo_treasuries": [P("UST 2030", 5000, "Renta fija", "Estados Unidos")],
 "solo_etfs": [P(t, 1000) for t in etk[:6]],
 "una_accion": [P(tks[0], 5000)],
 "cuarenta_acciones": [P(t, 100 + i) for i, t in enumerate(tks[:40])],
 "desconocidos": [P("ZZZZ", 100), P("QQQQ1", 200)],
 "mezcla_con_pais": [P(tks[1], 3000), P("Bono Bund", 2000, "Renta fija", "Alemania"), P("Fondo Brasil", 1000, "Renta variable", "Brasil"), P("Efectivo", 300, "Efectivo", "Argentina")],
}
random.seed(7)
for i in range(60):
    pos = [P(random.choice(tks), random.randint(100, 9000)) for _ in range(random.randint(1, 25))]
    pos += [P(random.choice(etk), random.randint(100, 9000)) for _ in range(random.randint(0, 4))]
    if random.random() < .6: pos.append(P("AL30", random.randint(100, 20000), "Renta fija"))
    if random.random() < .4: pos.append(P("Caución", random.randint(100, 5000), "Efectivo"))
    if random.random() < .4: pos.append(P("BTC", random.randint(50, 3000), "Cripto"))
    if random.random() < .4: pos.append(P("GLD", random.randint(50, 3000)))
    casos[f"azar{i}"] = pos
malas = re.compile(r"\bNone\b|\bnan\b|\{|\}|Pesos|Malkiel|Graham|Lynch|Buffett|Chowder")
for nom, pos in casos.items():
    for edad in (18, 25, 35, 45, 55, 65, 72, 95):
        for perfil in ("Conservador", "Moderado", "Agresivo"):
            try:
                res = C.analizar(pos, edad, perfil, emp, etfs)
                if not res or not res.get("total"):
                    chk(nom == "desconocidos", f"{nom} sin resultado"); continue
                sec = C.devolucion(res, edad, perfil, "Ana")
                txt = re.sub(r"\*\*|==|__", "", " ".join(" ".join(f) for _, f in sec))
                chk(not malas.search(txt), f"{nom}/{edad}/{perfil}: texto raro {malas.search(txt)}")
                titulos = [t for t, _ in sec]
                for t in ("Objetivo como inversor", "Estructura de tu cartera", "Diversificación geográfica", "Diversificación sectorial", "Liquidez", "Conclusiones finales"):
                    chk(t in titulos, f"{nom}: falta {t}")
                if res["peso"]["rv"] >= 1 and res.get("super"):
                    chk("Defensivo 50 %, Cíclico 20 % y Sensible 30 %" in txt and "entre 20 y 30 posiciones" in txt, f"{nom}: leyenda sectorial")
                ref = CM.referencia(edad, perfil)
                chk("Objetivo:" in txt and re.sub(r"^normalmente ", "generalmente ", CM.OBJETIVO_RESUMEN[ref[0]]) in txt, f"{nom}/{edad}: objetivo")
                chk("La diversificación geográfica es clave" in txt and "Armar una cartera lleva tiempo" in txt and "La cartera teórica de referencia para una persona de" in txt, f"{nom}: bases fijas")
                duro = re.search(r"te pasás|te faltan|Ojo|mala noticia|demasiado|reducirla|Bajar |castig", txt)
                chk(not duro, f"{nom}/{edad}/{perfil}: tono duro {duro and duro.group(0)}")
                h = CV.visual_html(res, edad, perfil, "Ana", "02/11/2026", C.resumen_guardable(res, edad, perfil, "2026-10-01"))
                chk("==" not in h and "**" not in h and "__" not in h and "Aviso Legal:" in h and "Abrazo grande y buenas inversiones." in h and "Hola Ana" in h and not re.search(r"\bNone\b|\bnan\b", h), f"{nom}: html")
                if edad in (45, 72) and perfil == "Moderado":
                    pdf = CI.pdf_informe(res, edad, perfil, nombre="Ana"); chk(pdf[:4] == b"%PDF", f"{nom}: pdf")
            except Exception as e:
                chk(False, f"{nom}/{edad}/{perfil}: EXCEPCIÓN {type(e).__name__}: {e}")
# país desde la columna
res = C.analizar(casos["mezcla_con_pais"], 45, "Moderado", emp, etfs)
chk(res["geo"]["desarrollados"] > 0 and res["geo"]["emergentes"] > 0, "país declarado entra en la geografía")
pos, _ = C.leer_tabla_info([["Ticker", "Monto", "Tipo", "País"], ["Bono X", "1000", "Renta fija", "Alemania"], ["AAPL", "500", "", ""]])
chk(pos[0].get("pais") == "Alemania", "columna País leída")
import openpyxl
wb = openpyxl.load_workbook(io.BytesIO(C.plantilla_excel())); chk("País (opcional)" in [c.value for c in wb.active[1]], "plantilla con País")
print("OK", ok, "MAL", bad)
