"""v1.5.63: control de la unión SEC → Yahoo en la ganancia por acción (Telefônica Brasil, DuPont, AstraZeneca, Cemex, Lloyds) y factores chicos."""
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


EPS = "Ganancia por acción (diluida)"
yahoo = {"moneda": "USD", "resultados": {"anios": ["2024 (TTM)", 2023, 2022, 2021],
                                         "filas": [["Resultado neto", [800.0, 760.0, 720.0, 680.0], "t"], [EPS, [8.0, 7.6, 7.2, 6.8], "eps"]]}}
reg = H.fusionar_estados(None, yahoo, "ZZ", [], "2026-11-01")

# factor chico (6% de diferencia en el año en común): misma base, no se escala
f_chico = {"facts": {"ifrs-full": {
    "ProfitLossAttributableToOwnersOfParent": {"units": {"USD": [anual(a, 400.0 + 40 * (a - 2014)) for a in range(2014, 2024)]}},
    "DilutedEarningsLossPerShare": {"units": {"USD/shares": [anual(a, (4.0 + 0.4 * (a - 2014)) * 0.943) for a in range(2014, 2024)]}}}}}
f, det = S.factor_por_accion(S.a_anios(f_chico), reg)
chk(f == 1.0 and "no es otra base" in det, f"factor 1,06: se toma 1 ({f}, {det})")

# la SEC no trae ganancia por acción en los años en común (no se puede verificar) y la de los años viejos está en otra base (×10)
f_sin = {"facts": {"ifrs-full": {
    "ProfitLossAttributableToOwnersOfParent": {"units": {"USD": [anual(a, 400.0 + 40 * (a - 2014)) for a in range(2014, 2024)]}},
    "DilutedEarningsLossPerShare": {"units": {"USD/shares": [anual(a, 0.4 + 0.04 * (a - 2014)) for a in range(2014, 2021)]}}}}}
archivo, cambios = {"ZZ": reg}, []
estado, det, sumados = BS.procesar("ZZ", f_sin, archivo, cambios, hoy="2026-11-10")
an = archivo["ZZ"]["anios"]
chk(estado == "ok" and sumados and all(EPS not in (an[a].get("resultados") or {}) for a in sumados)
    and all(an[a]["resultados"].get("Resultado neto") for a in sumados) and "sin verificar" in det,
    f"base sin verificar y unión rara: la ganancia por acción de la SEC queda afuera, los montos no ({estado}, {det})")
chk(S.union_por_accion(archivo["ZZ"])[0] is None, "sin ganancia por acción en la SEC no hay unión que controlar")

# misma situación pero con la ganancia vieja en la base correcta: se guarda
f_bien = {"facts": {"ifrs-full": {
    "ProfitLossAttributableToOwnersOfParent": {"units": {"USD": [anual(a, 400.0 + 40 * (a - 2014)) for a in range(2014, 2024)]}},
    "DilutedEarningsLossPerShare": {"units": {"USD/shares": [anual(a, 4.0 + 0.4 * (a - 2014)) for a in range(2014, 2021)]}}}}}
archivo = {"ZZ": H.fusionar_estados(None, yahoo, "ZZ", [], "2026-11-01")}
estado, det, sumados = BS.procesar("ZZ", f_bien, archivo, [], hoy="2026-11-10")
chk(estado == "ok" and archivo["ZZ"]["anios"]["2020"]["resultados"].get(EPS) == 6.4 and S.union_por_accion(archivo["ZZ"]) == (True, 1.0),
    f"base sin verificar pero unión normal: se guarda ({det})")

# con factor verificado de 1 y un salto real en la unión (fusión, como Agnico Eagle), se guarda igual
reg_aem = {"anios": {"2021": {"fuente": "SEC", "captura_acc": "2023-03-27", "resultados": {"Resultado neto": 561.0, EPS: 2.3}},
                     "2022": {"captura_acc": "2026-10-28", "resultados": {"Resultado neto": 670.0, EPS: 1.53}}}}
chk(S.union_por_accion(reg_aem) == (False, 0.56), "la relación de la unión se mide bien (Agnico Eagle 2021-2022: 0,56)")
r = {"anios": {"2019": {"fuente": "SEC", "resultados": {EPS: 1.0, "Resultado neto": 5.0}}, "2022": {"resultados": {EPS: 2.0}}}}
chk(S.quitar_por_accion(r) == ["2019"] and r["anios"]["2022"]["resultados"][EPS] == 2.0 and r["anios"]["2019"]["sin_por_accion"],
    "quitar_por_accion solo toca los años de la SEC")

print(f"OK {ok} MAL {mal}")
