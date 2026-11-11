"""v1.5.63/66: control de la unión SEC → Yahoo en la ganancia por acción (Telefônica Brasil, DuPont, AstraZeneca, Cemex, Lloyds) y factores chicos."""
import os
import sys

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
from data import sec as S  # noqa: E402
import bajar_sec as BS  # noqa: E402


def anual(a, v, filed=None):
    return {"val": v, "start": f"{a}-01-01", "end": f"{a}-12-31", "form": "20-F", "filed": filed or f"{a + 1}-04-01"}


def en_informes(valor, desde=2014, hasta=2023, base=lambda f: 1.0):
    """Como los informes reales: cada 20-F presentado en abril del año F trae los años F-3, F-2 y F-1 (en la base de ese informe)."""
    return [anual(a, valor(a) * base(f), f"{f}-04-01") for f in range(desde + 1, hasta + 2) for a in (f - 3, f - 2, f - 1) if desde <= a <= hasta]


EPS = "Ganancia por acción (diluida)"
yahoo = {"moneda": "USD", "resultados": {"anios": ["2024 (TTM)", 2023, 2022, 2021],
                                         "filas": [["Resultado neto", [800.0, 760.0, 720.0, 680.0], "t"], [EPS, [8.0, 7.6, 7.2, 6.8], "eps"]]}}
reg = H.fusionar_estados(None, yahoo, "ZZ", [], "2026-11-01")

# factor chico (6% de diferencia en los años en común): misma base, no se escala
NETO = {"ProfitLossAttributableToOwnersOfParent": {"units": {"USD": [anual(a, 400.0 + 40 * (a - 2014)) for a in range(2014, 2024)]}}}
f_chico = {"facts": {"ifrs-full": {**NETO, "DilutedEarningsLossPerShare": {"units": {"USD/shares": en_informes(lambda a: (4.0 + 0.4 * (a - 2014)) * 0.943)}}}}}
f, det = S.factor_por_accion(S.a_anios(f_chico), reg)
chk(f == 1.0 and "no es otra base" in det, f"factor 1,06: se toma 1 ({f}, {det})")
fac = S.factores_por_informe(f_chico, reg)
chk(set(fac.values()) == {(1.0, "directo"), (1.0, "encadenado")}, f"v1.5.66: informes con 6% de diferencia: factor 1 ({fac})")

# v1.5.66: split 2:1 en 2022 que Yahoo no tiene en su lista: los informes hasta 2021 traen el doble por acción. Se encadena informe por informe
f_split = {"facts": {"ifrs-full": {**NETO, "DilutedEarningsLossPerShare": {"units": {"USD/shares": en_informes(
    lambda a: 4.0 + 0.4 * (a - 2014), base=lambda f: 2.0 if f <= 2021 else 1.0)}}}}}
archivo = {"ZZ": H.fusionar_estados(None, yahoo, "ZZ", [], "2026-11-01")}
estado, det, sumados = BS.procesar("ZZ", f_split, archivo, [], hoy="2026-11-10")
an = archivo["ZZ"]["anios"]
chk(estado == "ok" and an["2015"]["resultados"][EPS] == 4.4 and an["2020"]["resultados"][EPS] == 6.4 and an["2015"].get("modo_accion") == "encadenado"
    and an["2015"]["captura_acc"] == "2026-11-10" and S.union_por_accion(archivo["ZZ"]) == (True, 1.0),
    f"split sin registrar: los informes viejos se encadenan a la base de Yahoo ({estado}, 2015 = {an['2015']['resultados'].get(EPS)}, {det})")
fz = S.factores_por_informe(f_split, reg)
chk(fz["2021-04-01"] == (0.5, "encadenado") and fz["2024-04-01"] == (1.0, "directo"), f"factores por informe: {fz}")

# ADR: la SEC por acción ordinaria y Yahoo por ADR (×5), con un cambio de relación del ADR (de 1:10 a 1:5) en 2019
f_adr = {"facts": {"ifrs-full": {**NETO, "DilutedEarningsLossPerShare": {"units": {"USD/shares": en_informes(
    lambda a: (4.0 + 0.4 * (a - 2014)) / 5)}}}}}
archivo = {"ZZ": H.fusionar_estados(None, yahoo, "ZZ", [], "2026-11-01")}
estado, det, _ = BS.procesar("ZZ", f_adr, archivo, [], hoy="2026-11-10")
chk(archivo["ZZ"]["anios"]["2014"]["resultados"][EPS] == 4.0 and archivo["ZZ"]["anios"]["2014"]["factor_accion"] == 5.0 and "factores 5" in det,
    f"ADR ×5: todos los años en la base de Yahoo ({det})")

# la SEC no trae ganancia por acción en los años recientes: no hay con qué llevarla a la base de Yahoo y queda afuera (los montos no)
f_sin = {"facts": {"ifrs-full": {**NETO, "DilutedEarningsLossPerShare": {"units": {"USD/shares": en_informes(lambda a: 0.4 + 0.04 * (a - 2014),
                                                                                                          hasta=2018)}}}}}
archivo = {"ZZ": H.fusionar_estados(None, yahoo, "ZZ", [], "2026-11-01")}
estado, det, sumados = BS.procesar("ZZ", f_sin, archivo, [], hoy="2026-11-10")
an = archivo["ZZ"]["anios"]
chk(estado == "ok" and sumados and all(EPS not in (an[a].get("resultados") or {}) for a in sumados)
    and all(an[a]["resultados"].get("Resultado neto") for a in sumados) and "sin ganancia por acción" in det,
    f"informes que no se pueden llevar a la base de Yahoo: sin ganancia por acción, los montos se guardan ({estado}, {det})")
chk(S.union_por_accion(archivo["ZZ"])[0] is None, "sin ganancia por acción en la SEC no hay unión que controlar")

# con factor verificado de 1 y un salto real en la unión (fusión, como Agnico Eagle), se guarda igual
reg_aem = {"anios": {"2021": {"fuente": "SEC", "captura_acc": "2023-03-27", "resultados": {"Resultado neto": 561.0, EPS: 2.3}},
                     "2022": {"captura_acc": "2026-10-28", "resultados": {"Resultado neto": 670.0, EPS: 1.53}}}}
chk(S.union_por_accion(reg_aem) == (False, 0.56), "la relación de la unión se mide bien (Agnico Eagle 2021-2022: 0,56)")
r = {"anios": {"2019": {"fuente": "SEC", "resultados": {EPS: 1.0, "Resultado neto": 5.0}}, "2022": {"resultados": {EPS: 2.0}}}}
chk(S.quitar_por_accion(r) == ["2019"] and r["anios"]["2022"]["resultados"][EPS] == 2.0 and r["anios"]["2019"]["sin_por_accion"],
    "quitar_por_accion solo toca los años de la SEC")

print(f"OK {ok} MAL {mal}")
