"""
Resumen de que fuente aporto cada dato al generar el cache (v1.2.13).
Sirve para saber, al terminar generar_cache / actualizar_ticker, si Stock Analysis respondio
y cuantas metricas quedaron con dato de cada fuente.
"""
from collections import Counter
import pandas as pd


def _es_dict(x):
    return isinstance(x, dict)


def resumen_fuentes(df: pd.DataFrame, modo: str = "") -> str:
    n = len(df)
    lineas = [f"RESUMEN DE FUENTES (modo Stock Analysis: {modo or '?'}) - {n} empresas"]
    if n == 0:
        return lineas[0]

    con_sa, sin_sa = [], []
    for _, r in df.iterrows():
        f = r.get("fuentes")
        usa = _es_dict(f) and any(v == "Stock Analysis" for v in f.values())
        (con_sa if usa else sin_sa).append(r["ticker"])
    lineas.append(f"Con datos de Stock Analysis: {len(con_sa)} de {n}")
    if sin_sa:
        lineas.append(f"Solo Yahoo ({len(sin_sa)}): " + ", ".join(sin_sa[:60]) + (" ..." if len(sin_sa) > 60 else ""))

    por_metrica = {}
    for _, r in df.iterrows():
        det = r.get("detalle")
        if not _es_dict(det):
            continue
        f = r.get("fuentes") if _es_dict(r.get("fuentes")) else {}
        for m, d in det.items():
            c = por_metrica.setdefault(m, Counter())
            if d.get("estado") != "ok":
                c["sin dato / descartada"] += 1
            elif d.get("referencia") == "sector":
                c["mediana del sector"] += 1
            elif f.get(m) == "Stock Analysis":
                c["Stock Analysis"] += 1
            elif f.get(m):
                c["Yahoo"] += 1
            else:
                c["otra"] += 1
    lineas.append("")
    lineas.append("Por metrica (cuantas empresas la usan, segun la fuente):")
    for m, c in sorted(por_metrica.items()):
        lineas.append("  " + f"{m:15s}" + " | ".join(f"{k}: {v}" for k, v in c.most_common()))

    if "metricas_usadas" in df.columns and "metricas_total" in df.columns:
        dist = Counter(f"{int(u)}/{int(t)}" for u, t in zip(df["metricas_usadas"], df["metricas_total"]) if pd.notna(u) and pd.notna(t))
        lineas.append("")
        lineas.append("Metricas usadas por empresa: " + ", ".join(f"{k}: {v}" for k, v in sorted(dist.items(), reverse=True)))

    if modo == "principal" and len(con_sa) == 0:
        lineas.append("")
        lineas.append("AVISO: Stock Analysis no aporto ningun dato. Puede estar bloqueando o haber cambiado la pagina.")
        lineas.append("Los datos salieron de Yahoo. Corre probar_stockanalysis.bat y mandame resultados_stockanalysis.txt.")
    elif modo == "principal" and len(con_sa) < 0.6 * n:
        lineas.append("")
        lineas.append("AVISO: Stock Analysis aporto datos a menos del 60% de las empresas. Mandame este archivo.")
    return "\n".join(lineas)
