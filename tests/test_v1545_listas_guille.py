"""v1.5.45: listas de Aristócratas, Reyes y Aspirantes cargadas por Guille el 08/11/2026; Dividendos Altos con el rendimiento de hoy."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)
import pandas as pd
from ui import ideas as I
from data import precios_vivos as PV
L = I.cargar_listas()
chk(len(L["aristocratas"]["anios"]) == 68 and len(L["reyes"]["anios"]) == 60 and len(L["aspirantes"]["tickers"]) == 414, "listas completas: 68, 60 y 414")
chk(L["aristocratas"]["fecha"] == "08/11/2026", "fecha de las listas")
df = pd.DataFrame(json.load(open("data/cache_datos.json", encoding="utf-8"))["data"])
ar = {x["ticker"] for x in I.miembros("aristocratas", df, listas=L)}
ki = {x["ticker"] for x in I.miembros("reyes", df, listas=L)}
asp = {x["ticker"] for x in I.miembros("aspirantes", df, listas=L)}
chk(len(ar) >= 26 and len(ki) >= 16 and len(asp) >= 45, f"en la app: {len(ar)} aristócratas, {len(ki)} reyes, {len(asp)} aspirantes")
chk({"KO", "PG", "JNJ"} <= ar & ki and "MO" in ki and "MO" not in ar, "KO, PG y JNJ en las dos; MO solo en Reyes")
chk({"AAPL", "MSFT", "JPM", "V"} <= asp and not asp & (ar | ki), "aspirantes sin repetir aristócratas ni reyes")
# Dividendos Altos dinámico: si el precio de hoy sube al doble, el rendimiento baja a la mitad y sale de la lista
t = I.miembros("altos", df, listas=L)[0]["ticker"] if I.miembros("altos", df, listas=L) else None
fila = df[df.ticker == t].iloc[0]
d2, n = PV.aplicar_precios(df, {t: float(fila["precio_actual"]) * 2.0})
chk(n == 1 and t not in {x["ticker"] for x in I.miembros("altos", d2, listas=L)} or float(fila["dividend_yield_actual"]) / 2 >= I.UMBRAL_DY, "la lista de altos cambia con el precio de hoy")
chk(abs(I.dy_etf({"rendimiento": 5.0, "precio": 10}, 12.5) - 0.04) < 1e-9 and I.dy_etf({"rendimiento": 5.0}) == 0.05 and I.dy_etf({}) is None, "rendimiento de ETF con el precio de hoy")
e = [{"ticker": "ZZZ", "nombre": "Prueba"}]
chk([x["ticker"] for x in I.miembros("altos", df.iloc[0:0], etfs=e, etfs_datos={"ZZZ": {"rendimiento": 5.0, "precio": 10}}, listas=L, precios_etfs={"ZZZ": 10})] == ["ZZZ"]
    and not I.miembros("altos", df.iloc[0:0], etfs=e, etfs_datos={"ZZZ": {"rendimiento": 5.0, "precio": 10}}, listas=L, precios_etfs={"ZZZ": 20}), "ETF entra o sale según el precio")
h = I.lista_html("reyes", I.miembros("reyes", df, listas=L), L)
chk("Div. Yield" in h and "08/11/2026" in h and "Años seguidos" in h, "tabla de Reyes con años y rendimiento")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)
