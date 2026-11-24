"""v1.5.90 — La SEC con cifras iguales y etiqueta de moneda distinta (Yahoo rotula BRL lo que está en dólares: Vale, Embraer, Petrobras)
y el mes de cierre del ejercicio de las fichas sacado de la fecha del último balance anual.
python tests/test_v1590_sec_etiqueta_fichas.py  →  "OK n MAL 0"."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bajar_fichas as BF  # noqa: E402
import bajar_sec as BS  # noqa: E402
from data import historico as H  # noqa: E402
from data import sec as S  # noqa: E402

OK = MAL = 0


def chk(cond, txt):
    global OK, MAL
    if cond:
        OK += 1
    else:
        MAL += 1
        print("MAL:", txt)


def hecho(val, ini, fin, form, filed):
    return {"val": val, "start": ini, "end": fin, "form": form, "filed": filed}


# SEC en dólares, años 2019 a 2022 (como Petrobras: informa a la SEC en USD)
facts = {"facts": {"us-gaap": {
    "Revenues": {"units": {"USD": [hecho(70.0 + 10 * i, f"{2019 + i}-01-01", f"{2019 + i}-12-31", "20-F", f"{2020 + i}-03-30") for i in range(4)]}},
    "NetIncomeLoss": {"units": {"USD": [hecho(7.0 + i, f"{2019 + i}-01-01", f"{2019 + i}-12-31", "20-F", f"{2020 + i}-03-30") for i in range(4)]}},
    "InterestExpense": {"units": {"USD": [hecho(2.0, f"{2019 + i}-01-01", f"{2019 + i}-12-31", "20-F", f"{2020 + i}-03-30") for i in range(4)]}},
}}}
sec = S.a_anios(facts)


def guardado(moneda, factor=1.0):
    """Lo de Yahoo: 2022 (ingresos 100, resultado neto 10) con la etiqueta `moneda`; factor ≠ 1 = cifras de verdad en otra moneda."""
    return H.fusionar_estados(None, {"moneda": moneda, "resultados": {"anios": [2022], "filas": [["Ingresos", [100.0 * factor], "t"],
                                                                                                 ["Resultado neto", [10.0 * factor], "t"]]}},
                              "PBR", [], "2026-11-24")


# 1. Etiqueta BRL con cifras en dólares (las de la SEC): se usan con la etiqueta de lo guardado
reg = guardado("BRL")
chk(S.coincide(sec, reg)[0] is False, "antes del arreglo la comparación saltea por la etiqueta")
sec2, nota = S.con_etiqueta_de_lo_guardado(sec, reg)
chk(sec2["2019"]["moneda"] == "BRL" and sec2["2019"].get("moneda_sec") == "USD" and "rotula mal" in nota, f"años de la SEC con la etiqueta de lo guardado: {nota}")
chk(S.coincide(sec2, reg)[0] is True, "con la etiqueta corregida, las cifras coinciden")
archivo = {"PBR": reg}
estado, det, sumados = BS.procesar("PBR", facts, archivo, [], hoy="2026-11-24")
an = archivo["PBR"]["anios"]
chk(estado == "ok" and sumados == ["2019", "2020", "2021"], f"bajar_sec suma los años viejos: {estado} {sumados} ({det})")
chk(an["2019"]["moneda"] == "BRL" and an["2019"].get("moneda_sec") == "USD" and an["2019"]["fuente"] == "SEC", "el año sumado lleva BRL y la marca moneda_sec")
chk(an["2022"] == reg["anios"]["2022"], "el año de Yahoo no se toca")

# 2. Etiqueta BRL con cifras de verdad en reales (5,5 veces más): sigue sin sumarse
reg_r = guardado("BRL", factor=5.5)
sec3, nota3 = S.con_etiqueta_de_lo_guardado(sec, reg_r)
chk(nota3 == "" and sec3["2019"]["moneda"] == "USD", "cifras distintas: la etiqueta no se cambia")
archivo = {"PBR": reg_r}
estado, det, _ = BS.procesar("PBR", facts, archivo, [], hoy="2026-11-24")
chk(estado == "no_coincide" and archivo["PBR"] == reg_r, f"cifras en otra moneda: se saltea ({estado})")

# 3. Misma etiqueta: nada cambia
sec4, nota4 = S.con_etiqueta_de_lo_guardado(sec, guardado("USD"))
chk(sec4 == sec and nota4 == "", "misma etiqueta: sin cambios")

# 4. Huecos (intereses): con etiqueta distinta y cifras iguales se completan con la etiqueta de lo guardado
hz, no = S.huecos(sec, guardado("BRL"))
chk("2022" in hz and hz["2022"]["moneda"] == "BRL" and not no, f"huecos de intereses con la etiqueta de lo guardado: {hz} {no}")
hz2, no2 = S.huecos(sec, guardado("BRL", factor=5.5))
chk(not hz2 and no2, f"huecos con cifras en otra moneda: no se completan ({no2})")

# 5. Fichas: mes de cierre desde las fechas de las columnas del estado anual
chk(BF._mes_de_columnas([dt.datetime(2026, 3, 31), dt.datetime(2025, 3, 31), dt.datetime(2024, 3, 31)]) == 3, "Toyota: cierre en marzo")
chk(BF._mes_de_columnas([dt.datetime(2025, 6, 30), dt.datetime(2024, 6, 30)]) == 6, "Microsoft: cierre en junio")
chk(BF._mes_de_columnas([]) is None and BF._mes_de_columnas(None) is None, "sin columnas: sin mes")
chk("_mes_de_columnas(getattr(est, \"columns\", None))" in open(os.path.join(os.path.dirname(BF.__file__), "bajar_fichas.py"), encoding="utf-8").read(),
    "bajar_fichas usa la fecha del último balance cuando Yahoo no da lastFiscalYearEnd")

print(f"OK {OK} MAL {MAL}")
sys.exit(1 if MAL else 0)
