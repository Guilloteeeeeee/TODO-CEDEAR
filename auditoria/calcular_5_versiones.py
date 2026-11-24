"""Calcula las 5 versiones del Score de Seguridad del Dividendo para las empresas con puntaje de SSD y deja el resultado en
auditoria/resultado_5_versiones.json (mismo cálculo que la planilla de la auditoría del 24/11/2026).
Uso, desde la carpeta del repo:  python auditoria/calcular_5_versiones.py
V1 = scoring/dividendo.py · V2 = dividendo_v1.calcular(version=2) · V3 = dividendo_v1.calcular() · V3.1 y V3.2 = capa sobre V3 (abajo)."""
import json, os, statistics as st, sys
AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI); os.chdir(AQUI)
import calibrar_dividendo as C
from data import historico as H, paquetes_yahoo as PY

CIC = {"Energía", "Materiales Básicos", "Semiconductores", "Industrial", "Consumo Discrecional", "Hardware y servicios TI"}
PRINC = ("cobertura", "cet1", "solvencia", "fcf_payout", "eps_payout", "affo", "payout_futuro", "deuda", "ffo_deuda")
OP1 = {"ciclico": 10, "banco": 10, "beta": 10, "c08": 5, "c20": 5, "joven": 5, "cap_perdida": 60, "cap_cob": 40, "k": 0.6}
OP2 = {"ciclico": 15, "banco": 15, "beta": 5, "c08": 10, "c20": 5, "joven": 10, "cap_perdida": 40, "cap_cob": 20, "techo_gris": 80}


def capa(row, hist, r3, p):
    """Versión 3.1 (OP1) o 3.2 (OP2) sobre el resultado de la versión 3. -> (puntaje, pasos)"""
    h = hist or {}
    con = [v for v in r3["variables"] if v["pts"] is not None]
    base = sum(v["pts"] for v in con) / sum(v["max"] for v in con) * 100
    tot = base + sum(a for _, a in r3["ajustes"]); pasos = [("base + ajustes de la versión 3", round(tot, 1))]
    sec = row.get("sector")
    for cond, clave in ((sec in CIC, "ciclico"), (sec == "Bancos y seguros", "banco"), ((row.get("beta") or 1) > 1.2, "beta"),
                        (h.get("crisis_0809") == "recorto", "c08"), (h.get("crisis_2020") == "recorto", "c20"),
                        ((h.get("anios_pagando") or 0) < 10, "joven")):
        if cond and p.get(clave):
            tot -= p[clave]; pasos.append((f"{clave} −{p[clave]}", round(tot, 1)))
    k = p.get("k", 1.0)
    if tot > 60 and k != 1.0:
        tot = 60 + (tot - 60) * k; pasos.append((f"arriba de 60 × {k}", round(tot, 1)))
    for kk, tp in r3["topes"]:
        tp2 = p.get("cap_perdida", 20) if kk == "perdida" else p.get("cap_cob", 20) if kk == "cobertura_letal" else tp
        if tot > tp2:
            tot = tp2; pasos.append((f"tope {kk} {tp2}", tot))
    s = max(0, min(99, int(round(round(tot, 6)))))
    if p.get("techo_gris"):
        if any(v["clave"] in PRINC and v["pts"] is not None and v["pts"] < v["max"] for v in r3["variables"]) and s > p["techo_gris"]:
            s = p["techo_gris"]; pasos.append(("techo 80 por variable principal fuera de zona segura", s))
    return s, pasos


def cat(x):
    return 0 if x <= 20 else 1 if x <= 40 else 2 if x <= 60 else 3 if x <= 80 else 4


if __name__ == "__main__":
    cache = {r["ticker"]: r for r in json.load(open("data/cache_datos.json", encoding="utf-8"))["data"]}
    ssd = {t: v for t, v in json.load(open("data/referencias/ssd_2026-11-21.json", encoding="utf-8"))["scores"].items() if isinstance(v, (int, float))}
    est = json.load(open("data/estimaciones_analistas.json", encoding="utf-8"))["datos"]
    tks = [t for t in ssd if t in cache]
    res = C.calcular_todo(tks, cache, PY.cargar()[0], H.leer("estados.json", {}), H.leer("splits.json", {}), H.leer("dividendos.json", {}),
                          H.leer("precios_mensuales.json", {}), est)
    out = {}
    for t in tks:
        r = res.get(t) or {}; r3 = r.get("v1") or {}
        if r3.get("score") is None:
            continue
        s31, p31 = capa(cache[t], r.get("historial"), r3, OP1); s32, p32 = capa(cache[t], r.get("historial"), r3, OP2)
        out[t] = {"ssd": ssd[t], "v1": r.get("score"), "v2": (r.get("v2") or {}).get("score"), "v3": r3["score"], "v31": s31, "v32": s32,
                  "detalle_v1": {k: r.get(k) for k in ("pilares", "variables", "topes", "notas")}, "detalle_v2": r.get("v2"), "detalle_v3": r3,
                  "pasos_v31": p31, "pasos_v32": p32, "historial": r.get("historial"), "fuente_historial": r.get("fuente_historial")}
    json.dump(out, open("auditoria/resultado_5_versiones.json", "w", encoding="utf-8"), ensure_ascii=False, default=str, indent=1)
    for k in ("v1", "v2", "v3", "v31", "v32"):
        p = [(x["ssd"], x[k]) for x in out.values() if x[k] is not None]
        d = [abs(cat(b) - cat(a)) for a, b in p]
        print(f"{k:4} n={len(p)} misma {sum(x == 0 for x in d) / len(p):.1%} · a 1 {sum(x == 1 for x in d) / len(p):.1%} · a 2 {sum(x == 2 for x in d) / len(p):.1%}"
              f" · a 3 {sum(x == 3 for x in d) / len(p):.1%} · diferencia media {st.mean(abs(b - a) for a, b in p):.1f}")
