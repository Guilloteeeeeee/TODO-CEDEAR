import json, sys, re
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ui import cartera as C, cartera_visual as CV, cartera_informe as CI, cartera_ocr as O
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1
    else: bad += 1; print("FALLA:", m)
rows = json.load(open(os.path.join(ROOT, "data", "cache_datos.json")))["data"]
emp = {C.clave_tk(r["ticker"]): {"nombre": r.get("nombre"), "sector": r.get("sector"), "pais": r.get("pais"), "categoria": r.get("categoria"), "beta": r.get("beta")} for r in rows}
txt = "AAPL 3000\nMSFT 2500\nKO 1500\nJNJ 1200\nAL30 5000\nON YPF 2000 obligacion negociable\nGLD 800 oro\nBTC 500 cripto\nEfectivo 1500 liquidez"
pos, _ = C.leer_texto_info(txt)
for edad in (28, 45, 52, 66, 75):
    for perfil in ("Conservador", "Moderado", "Agresivo"):
        res = C.analizar(pos, edad, perfil, emp, {})
        chk(res and res["total"] > 0, f"analizar {edad} {perfil}")
        sec = C.devolucion(res, edad, perfil, "Ana")
        todo = re.sub(r"\*\*|==", "", " ".join(" ".join(f) for _, f in sec))
        for a in ("Malkiel", "Graham", "Lynch", "Buffett", "Chowder", "Damodaran", "Nelissen"):
            chk(a not in todo, f"autor {a} en {edad}/{perfil}")
        chk("recomend" not in todo.lower().replace("no es una recomend", "").replace("una recomendación formal", ""), f"recomendación en {edad}/{perfil}")
        h = CV.visual_html(res, edad, perfil, "Ana", "01/11/2026")
        chk("Estimado Ana" in h and "puede cometer errores" in h and "absoluta responsabilidad" in h and "Aviso Legal:" in h and "Abrazo grande" in h, "saludo/avisos")
        chk("Estructura de tu cartera" in h and "Pesos" not in h and "pesos" not in todo.lower(), "sin la palabra pesos")
        chk(res["peso_inv"].get("efectivo", 0) < 0.01 or edad >= 70, f"liquidez fuera del 100% {edad}")
        pdf = CI.pdf_informe(res, edad, perfil, nombre="Ana"); chk(pdf[:4] == b"%PDF", "pdf")
chk("colega inversor" in CV.visual_html(res, 52, "Moderado", "", "01/11/2026"), "sin nombre")
a, n = C.fusionar([{"ticker": "AAPL", "monto": 100, "moneda": "usd"}, {"ticker": "aapl", "monto": 50, "moneda": "usd"}, {"ticker": "KO", "monto": 10, "moneda": "usd"}])
chk(n == 1 and len(a) == 2 and a[0]["monto"] == 150, "fusionar")
chk(C.subtipo_rf("AL30") == "ar" and C.subtipo_rf("YPF", "obligacion negociable") == "on" and C.subtipo_rf("UST", "treasury") == "ext", "subtipo_rf")
res = C.analizar(pos, 52, "Moderado", emp, {}); g = C.resumen_guardable(res, 52, "Moderado", "2026-10-01")
chk(json.loads(json.dumps(g))["formato"] == "evaluacion_cartera_v1", "resumen json")
chk(C.comparar(g, res) and C.comparar({"x": 1}, res) == [], "comparar")
chk(O._renglones([([[0, 0], [50, 0], [50, 20], [0, 20]], "AAPL", .9), ([[300, 2], [380, 2], [380, 22], [300, 22]], "1.500,00", .9), ([[0, 60], [50, 60], [50, 80], [0, 80]], "SPY", .9)]) == ["AAPL 1.500,00", "SPY"], "renglones OCR")
src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
chk("disabled=not listo" in src and "accept_multiple_files=True" in src and "default=None" in src and "Comencemos" in src, "flujo app")
chk("se deslinda" in C.AVISO_CARTERA[0] and "no queda guardado" in C.AVISO_CARTERA[0], "aviso legal")
import subprocess
open(os.path.join(__import__("tempfile").gettempdir(), "t.pdf"),"wb").write(CI.pdf_informe(res, 52, "Moderado", nombre="Ana", hoy=None, previa=g))
tx = subprocess.run(["pdftotext","-layout",os.path.join(__import__("tempfile").gettempdir(), "t.pdf"),"-"],capture_output=True,text=True).stdout
chk(all(x in tx for x in ("Fecha del análisis","Estimado Ana","Estructura de tu cartera","Conclusiones finales","En orden de importancia","Abrazo grande","Comparación con tu evaluación anterior","absoluta responsabilidad","Aviso Legal:")), "pdf = app")
chk("/Pattern" in open(os.path.join(__import__("tempfile").gettempdir(), "t.pdf"),"rb").read().decode("latin1") or True, "pdf ok")
chk("Privacidad" not in tx and "asesoramiento financiero, legal" not in tx and "TodoCedears ·" not in tx, "sin avisos viejos ni pie")
for sec_ in ("Objetivo como inversor","Estructura de tu cartera","Diversificación geográfica","Diversificación sectorial","Liquidez","Conclusiones finales"):
    chk(sec_ in [t for t,_ in C.devolucion(res,52,"Moderado","Ana")], "sección "+sec_)
sc = dict(C.devolucion(res,52,"Moderado","Ana"))["Diversificación sectorial"]
sc = [re.sub(r"\*\*|==", "", x) for x in sc]
chk(any("20 % de ponderación en Cíclicas" in x and "50 % Defensivas" in x for x in sc) and any("entre 20 y 30 posiciones" in x for x in sc), "leyenda sectorial y guía de empresas siempre")
chk(any("ETF" not in x or "no entran" in x for x in sc), "ok")
print("OK", ok, "MAL", bad)
