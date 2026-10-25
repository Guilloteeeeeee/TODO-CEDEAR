"""
v1.2.51 - Arma data/foso.json (el foso competitivo de cada empresa) a partir de los Excel del "Modo lote" de tu DCF (Lote_DCF_*.xlsx).
Cada Excel trae una fila por empresa con las columnas "Ticker", "Foso", "Etapa" y "Estado de datos".
Si una empresa esta en varios Excel, vale el mas nuevo (por fecha del nombre del archivo). Las que ya estaban y no vienen en los Excel nuevos se conservan.

Uso (desde la carpeta del proyecto):
    python foso_desde_lote.py Lote_DCF_20261024_2031.xlsx Lote_DCF_20261024_2216.xlsx ...
Despues subi data/foso.json al repositorio junto con el resto. Para cubrir las 166 empresas, corre el Modo lote de tu DCF con las que falten.
"""
import json
import os
import re
import sys

import pandas as pd

RUTA = "data/foso.json"
VALIDOS = ("Amplio", "Estrecho", "Ninguno")


def leer(ruta):
    x = pd.ExcelFile(ruta)
    hoja = next((s for s in x.sheet_names if "foso" in " ".join(map(str, x.parse(s, nrows=0).columns)).lower()), x.sheet_names[0])
    d = x.parse(hoja)
    col = {str(c).strip().lower(): c for c in d.columns}
    tk = col.get("ticker") or col.get("empresa") or d.columns[0]
    out = {}
    for _, r in d.iterrows():
        t = str(r[tk]).strip().upper()
        foso = str(r.get(col.get("foso"), "")).strip()
        if t and foso in VALIDOS:
            out[t] = {"foso": foso, "etapa": str(r.get(col.get("etapa"), "") or "").strip()}
    return out


def fecha_de(nombre):
    m = re.search(r"(\d{8})_(\d{4})", nombre)
    return m.group(1) + m.group(2) if m else "0"


def main(rutas):
    actual = {}
    if os.path.exists(RUTA):
        with open(RUTA, encoding="utf-8") as f:
            actual = json.load(f)
    empresas = dict(actual.get("empresas", {}))
    for ruta in sorted(rutas, key=lambda p: fecha_de(os.path.basename(p))):
        nuevo = leer(ruta)
        f = fecha_de(os.path.basename(ruta))
        fecha = f"{f[:4]}-{f[4:6]}-{f[6:8]}" if f != "0" else ""
        for t, v in nuevo.items():
            v["fecha"] = fecha
            empresas[t] = v
        print(f"{os.path.basename(ruta)}: {len(nuevo)} empresas con foso")
    with open(RUTA, "w", encoding="utf-8") as f:
        json.dump({"empresas": empresas}, f, ensure_ascii=False, indent=0)
    print(f"{RUTA}: {len(empresas)} empresas en total")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
