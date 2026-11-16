"""v1.5.70: valoración con el precio de hoy (decisión de Guille, 16/11/2026) y «prueba de foto» del puntaje y del Fair Value.
Uso: python tests/test_v1570_valoracion_hoy.py  ->  "OK n MAL 0"."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)
os.chdir(AQUI)

import pandas as pd  # noqa: E402

from config import sectors as S  # noqa: E402
from data import precios_vivos as PV  # noqa: E402
from scoring import engine as EN  # noqa: E402

ok = mal = 0


def chk(c, txt):
    global ok, mal
    if c:
        ok += 1
    else:
        mal += 1
        print("FALLA:", txt)


cache = json.load(open(os.path.join("data", "cache_datos.json"), encoding="utf-8"))["data"]
df = pd.DataFrame(cache)
base = {r["ticker"]: r["precio_actual"] for r in cache if r.get("precio_actual")}

# 1) Prueba de foto: volver a puntuar el cache con el código de hoy da lo mismo que lo guardado (score, categoría y Fair Value)
cols_res = ["score_fundamental", "score_tecnico", "score_total", "metricas_usadas", "metricas_total", "categoria", "color_hex", "emoji", "detalle",
            "fair_value", "fair_value_detalle", "fair_value_metodos", "fair_value_descartados", "respaldo_sector", "score_total_sector",
            "categoria_sector", "metricas_usadas_sector"]
raw = df.drop(columns=[c for c in cols_res if c in df.columns])
re_ = EN.score_dataframe(raw, S.TICKER_TO_SECTOR)
m = df[["ticker", "score_total", "categoria", "fair_value"]].merge(re_[["ticker", "score_total", "categoria", "fair_value"]], on="ticker", suffixes=("_c", "_h"))
chk(len(m) == len(df), "foto: todas las empresas")
chk(((m.score_total_c.fillna(-1) - m.score_total_h.fillna(-1)).abs() <= 0.05).all(), "foto: mismo puntaje que el cache")
chk((m.categoria_c == m.categoria_h).all(), "foto: misma categoría que el cache")
chk(((m.fair_value_c.fillna(-1) - m.fair_value_h.fillna(-1)).abs() <= 0.011).all(), "foto: mismo Fair Value que el cache")

# 2) Con el mismo precio, recalcular no cambia nada (identidad)
dfp, n = PV.aplicar_precios(df, dict(base))
dfr, cambios = EN.rescorar_con_precios(dfp)
chk(n == len(base) and cambios == 0, "identidad: nadie cambia de categoría con el mismo precio")
chk(((dfr["score_total"] - dfr["score_cache"]).abs().fillna(0) < 1e-9).all(), "identidad: mismo puntaje")

# 3) Precio +10%: los múltiplos de precio suben 10%, los rendimientos bajan, el Fair Value no cambia, el puntaje baja
dfp, _ = PV.aplicar_precios(df, {t: p * 1.1 for t, p in base.items()})
dfr, cambios = EN.rescorar_con_precios(dfp)
chk(cambios > 0, "con +10% alguna empresa cambia de categoría")
chk((dfr["fair_value"].fillna(-1) == df["fair_value"].fillna(-1)).all(), "el Fair Value no cambia con el precio")
bajan = ((dfr["score_total"] <= dfr["score_cache"] + 1e-9) | dfr["score_total"].isna()).mean()
chk(bajan > 0.99, f"con el precio más alto el puntaje no sube ({bajan:.3f})")
ko = dfr[dfr.ticker == "KO"].iloc[0]
ko0 = df[df.ticker == "KO"].iloc[0]
per0, per1 = ko0["detalle"]["per"]["actual"], ko["detalle"]["per"]["actual"]
chk(abs(per1 / per0 - 1.1) < 1e-9, "KO: el PER sube 10%")
chk(ko["score_total"] < ko0["score_total"], "KO: el puntaje baja")
chk(ko["categoria_cache"] == ko0["categoria"], "se guarda la categoría del cache")
dy = [r for r in cache if (r.get("detalle") or {}).get("dividend_yield", {}).get("score") is not None]
if dy:
    t = dy[0]["ticker"]
    a0, a1 = dy[0]["detalle"]["dividend_yield"]["actual"], dfr[dfr.ticker == t].iloc[0]["detalle"]["dividend_yield"]["actual"]
    chk(abs(a1 / a0 - 1 / 1.1) < 1e-9, f"{t}: el Dividend Yield baja (1/1,1)")

# 4) factor de cada métrica
chk(abs(EN.factor_metrica("per", 1.1) - 1.1) < 1e-12, "PER: igual que el precio")
chk(abs(EN.factor_metrica("ev_ebitda", 1.1, 1.5) - 1.6 / 1.5) < 1e-12, "EV/EBITDA con deuda de la mitad de la capitalización: +6,7%")
chk(abs(EN.factor_metrica("ev_ebitda", 1.1, None) - 1.1) < 1e-12, "EV/EBITDA sin dato de deuda: como el precio")
chk(abs(EN.factor_metrica("dividend_yield", 1.25) - 0.8) < 1e-12, "Dividend Yield: al revés")
chk(abs(EN.factor_metrica("rend_total", 2.0) - 0.5) < 1e-12, "rendimiento total: al revés")

# 5) sin precio en vivo no se toca nada; filas sin detalle se dejan
dfn, nn = EN.rescorar_con_precios(df)
chk(nn == 0 and (dfn["score_total"].fillna(-1) == df["score_total"].fillna(-1)).all(), "sin precios de hoy queda el cache")

# 6) la app lo usa en los dos lugares donde pone el precio de hoy, con su llave en config
src = open("app.py", encoding="utf-8").read()
chk(src.count("df = _con_precios_de_hoy(df_p)") == 2, "app: los dos lugares recalculan con el precio de hoy")
from config import ajustes as AJ  # noqa: E402
chk(getattr(AJ, "VALORACION_CON_PRECIO_DE_HOY", None) is True, "llave VALORACION_CON_PRECIO_DE_HOY encendida")
chk("_swr.obtener((\"etfs\", items)" in src, "precios de ETFs en segundo plano (swr)")

print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
