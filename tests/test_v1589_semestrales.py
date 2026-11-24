"""v1.5.89 — En las que pagan a cuenta y final, el año calendario mezcla dos ejercicios: el recorte se confirma corriendo los pagos medio año.
python tests/test_v1589_semestrales.py  →  "OK n MAL 0"."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring import dividendo as SD  # noqa: E402

OK = MAL = 0
HOY = dt.date(2026, 11, 24)


def chk(cond, txt):
    global OK, MAL
    if cond:
        OK += 1
    else:
        MAL += 1
        print("MAL:", txt)


def semestral(ejercicios, mes_cuenta=12, mes_final=6):
    """{ejercicio: (a cuenta, final)}: a cuenta en `mes_cuenta` del año anterior al cierre (Toyota: diciembre), final en `mes_final` del año del cierre."""
    pagos = []
    for e, (c, f) in sorted(ejercicios.items()):
        pagos.append([f"{e - 1 if mes_cuenta > mes_final else e}-{mes_cuenta:02d}-27", c])
        pagos.append([f"{e}-{mes_final:02d}-27", f])
    return sorted(pagos)


# 1. Toyota: ejercicios 200 → 210 → 210 (a cuenta 75 → 100, final 125 → 110). Año calendario 2015 = 125 + 100 = 225, 2016 = 110 + 100 = 210
ej = {2010 + i: (50 + 5 * i, 60 + 5 * i) for i in range(5)}
ej.update({2015: (75, 125), 2016: (100, 110), 2017: (100, 110), 2018: (100, 120), 2019: (100, 120), 2020: (100, 120), 2021: (105, 135),
           2022: (110, 140), 2023: (115, 145), 2024: (120, 150), 2025: (125, 155), 2026: (130, 160)})
toyota = [p for p in semestral(ej) if p[0] <= HOY.isoformat()]
h = SD.analizar_dividendos(toyota, hoy=HOY, sigue_pagando=True)
chk(h["tasa"][2015] > h["tasa"][2016], f"el año calendario 2016 baja (225 → 210): {h['tasa'].get(2015)} → {h['tasa'].get(2016)}")
chk(2016 not in h["recortes"], f"Toyota 2016 no es recorte: {h['recortes']}")
chk(h.get("solo_calendario") == [2016], f"queda anotado como baja solo del año calendario: {h.get('solo_calendario')}")
chk(h["anios_sin_recorte"] >= 10, f"años sin recortar: {h['anios_sin_recorte']}")

# 2. Recorte de verdad en una semestral: el ejercicio 2023 baja de 260 a 200 (a cuenta y final más bajos) → recorte, aunque se corra medio año
ej2 = dict(ej)
ej2.update({2023: (90, 110), 2024: (95, 115), 2025: (100, 120), 2026: (105, 125)})
h2 = SD.analizar_dividendos([p for p in semestral(ej2) if p[0] <= HOY.isoformat()], hoy=HOY, sigue_pagando=True)
chk(any(a in h2["recortes"] for a in (2022, 2023)), f"recorte real en una semestral: {h2['recortes']}")
chk(h2["anios_sin_recorte"] <= 4, f"años sin recortar después del recorte real: {h2['anios_sin_recorte']}")

# 3. Suspensión (Vale 2019: un solo pago y después nada en un año) → sigue siendo recorte
vale = [[f"{a}-03-07", 1.0] for a in range(2010, 2019)] + [[f"{a}-08-03", 1.0] for a in range(2010, 2019)]
vale += [["2019-12-27", 1.4], ["2020-09-22", 2.4], ["2021-03-05", 2.0], ["2021-09-23", 2.2]]
vale += [[f"{a}-03-05", 2.5] for a in range(2022, 2027)] + [[f"{a}-09-05", 2.5] for a in range(2022, 2026)]
h3 = SD.analizar_dividendos(sorted(vale), hoy=HOY, sigue_pagando=True)
chk(2019 in h3["recortes"], f"la suspensión de 2019 sigue contando: {h3['recortes']}")

# 4. Las que pagan 4 veces no se tocan (sin año corrido)
trim = [[f"{a}-{m:02d}-15", 0.25 if a < 2022 else 0.20] for a in range(2010, 2027) for m in (3, 6, 9, 12) if f"{a}-{m:02d}-15" <= HOY.isoformat()]
h4 = SD.analizar_dividendos(trim, hoy=HOY, sigue_pagando=True)
chk(h4["recortes"] == [2022] and h4.get("solo_calendario") == [], f"trimestral con recorte en 2022: {h4['recortes']} {h4.get('solo_calendario')}")

# 5. Novo Nordisk: empieza a pagar a cuenta en 2016 (2016 = final 2015 + a cuenta 2016) → 2017 no es recorte
novo = [[f"{a}-03-20", 1.0 + 0.1 * (a - 2005)] for a in range(2005, 2016)]
novo += [["2016-03-21", 3.2], ["2016-08-12", 1.5], ["2017-03-24", 2.3], ["2017-08-18", 1.5], ["2018-03-23", 2.45], ["2018-08-17", 1.6],
         ["2019-03-22", 2.6], ["2019-08-16", 1.7], ["2020-03-27", 2.8], ["2020-08-14", 1.8]]
novo += [[f"{a}-03-25", 3.0 + 0.4 * (a - 2021)] for a in range(2021, 2027)] + [[f"{a}-08-15", 2.0 + 0.3 * (a - 2021)] for a in range(2021, 2026)]
h5 = SD.analizar_dividendos(sorted(novo), hoy=HOY, sigue_pagando=True)
chk(2017 not in h5["recortes"], f"Novo Nordisk 2017 no es recorte: {h5['recortes']}")

print(f"OK {OK} MAL {MAL}")
sys.exit(1 if MAL else 0)
