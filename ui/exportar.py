"""
Descarga de la tabla en Excel (v1.2.42; columnas de la tabla y criterios agregados desde la v1.2.47).

Arma un archivo .xlsx con las empresas que se ven en pantalla (respeta los filtros y el orden elegidos) y, en una segunda hoja,
el aviso legal y la fecha de los datos. Son numeros (no texto), asi que se pueden ordenar y filtrar en Excel.
Los valores salen de las mismas columnas que usa la tabla: no se recalcula nada.
"""
import io
import math

import pandas as pd


# (titulo de la columna, ancho, formato de numero de Excel o None). v1.2.47: las columnas de siempre de la tabla y, al final, una por cada
# criterio agregado (ver COLUMNAS_CRITERIO): el Excel trae "lo que ves".
COLUMNAS = [
    ("Empresa", 34, None), ("Ticker", 9, None), ("País", 16, None), ("Sector", 22, None), ("Industria", 30, None),
    ("Precio (USD)", 14, "#,##0.00"), ("Capitalización bursátil (USD)", 26, "#,##0"), ("Valoración", 34, None), ("Puntaje de calidad (0 a 100)", 14, "0.0"),
    ("Métricas usadas", 11, "0"), ("Métricas totales", 11, "0"),
]
# clave del criterio -> lista de (titulo, ancho, formato) de las columnas que agrega al Excel
COLUMNAS_CRITERIO = {
    "dividend_yield_actual": [("Dividend Yield (%)", 14, "0.00"), ("Mediana histórica Dividend Yield (%)", 20, "0.00")],
    "fv_dist": [("Fair Value (USD)", 16, "#,##0.00"), ("Fair Value vs precio (%)", 15, "0.0")],
    "per_actual": [("P/E (veces)", 12, "0.0")], "ev_ebitda_actual": [("EV/EBITDA (veces)", 14, "0.0")], "p_fcf_actual": [("P/FCF (veces)", 12, "0.0")],
    "p_b_actual": [("P/Book (veces)", 12, "0.0")], "ps_actual": [("P/S (veces)", 12, "0.0")], "peg_actual": [("PEG (veces)", 12, "0.0")],
    "posicion_52s": [("Posición en el rango de 52 semanas (%)", 20, "0")],
}


def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def _pct(x):
    """El caché guarda el rendimiento como fraccion (0.0239 = 2,39 %); la tabla muestra el numero ya en %."""
    v = _n(x)
    if v is None or v <= 0:
        return None
    return v if v > 1 else v * 100


def _valores_criterio(clave, r):
    """Valores de las columnas que agrega un criterio, para una fila."""
    if clave == "dividend_yield_actual":
        return [_pct(r.get("dividend_yield_actual")), _pct(r.get("dividend_yield_mediana"))]
    if clave == "fv_dist":
        precio, fv = _n(r.get("precio_actual")), _n(r.get("fair_value"))
        ok = precio and fv and precio > 0 and fv > 0
        return [fv if ok else None, (fv - precio) / precio * 100 if ok else None]
    if clave == "posicion_52s":
        v = _n(r.get("posicion_52s"))
        return [v * 100 if v is not None else None]
    v = _n(r.get(clave))
    return [v if v is not None and v > 0 else None]


def columnas_excel(extras=()):
    """Titulos, anchos y formatos de las columnas del Excel: las de siempre y las de los criterios agregados (`extras`: lista de criterios)."""
    cols = list(COLUMNAS)
    for c in extras or ():
        cols += COLUMNAS_CRITERIO.get(c["clave"], [])
    return cols


def filas(df, extras=()):
    """Lista de filas (una por empresa, en el orden de `df`) con los valores que van al Excel."""
    from scoring.engine import nombre_visible
    from ui.tabla_visual import sector_industria
    out = []
    for _, r in df.iterrows():
        sector, industria = sector_industria(r)
        precio = _n(r.get("precio_actual"))
        cat = r.get("categoria")
        cat_txt = nombre_visible(cat) if isinstance(cat, str) and cat else ""
        nombre = r.get("nombre")
        fila = [
            nombre if isinstance(nombre, str) and nombre.strip() else str(r.get("ticker", "")),
            str(r.get("ticker", "")), r.get("pais") if isinstance(r.get("pais"), str) else "", sector or "", industria or "",
            precio, _n(r.get("market_cap")), cat_txt, _n(r.get("score_total")), _n(r.get("metricas_usadas")), _n(r.get("metricas_total")),
        ]
        for c in extras or ():
            if c["clave"] in COLUMNAS_CRITERIO:
                fila += _valores_criterio(c["clave"], r)
        out.append(fila)
    return out


def excel_bytes(df, fecha_datos=None, aviso="", version="", extras=()):
    """Contenido del .xlsx (bytes). Hoja "Empresas" con la tabla y hoja "Aviso" con el texto legal, la fecha de los datos y la version."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Empresas"
    columnas = columnas_excel(extras)
    ws.append([c[0] for c in columnas])
    for fila in filas(df, extras):
        ws.append(fila)
    relleno = PatternFill("solid", fgColor="222D36")
    for j, (titulo, ancho, fmt) in enumerate(columnas, start=1):
        c = ws.cell(row=1, column=j)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), relleno
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(j)].width = ancho
        if fmt:
            for i in range(2, ws.max_row + 1):
                ws.cell(row=i, column=j).number_format = fmt
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "C2"
    if ws.max_row > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{ws.max_row}"

    av = wb.create_sheet("Aviso")
    av.column_dimensions["A"].width = 120
    av["A1"] = "TodoCedears"
    av["A1"].font = Font(bold=True, size=14)
    av["A2"] = f"Datos al {fecha_datos}" if fecha_datos else "Fecha de los datos no disponible"
    av["A3"] = f"Versión {version}" if version else ""
    av["A5"] = "Aviso:"
    av["A5"].font = Font(bold=True)
    av["A6"] = aviso or ""
    av["A6"].alignment = Alignment(wrap_text=True, vertical="top")
    av.row_dimensions[6].height = 60
    av["A8"] = ("Los valores de Valoración y Puntaje (y de Fair Value, si se agregó como criterio) son estimaciones de una herramienta de filtrado inicial; "
                "no son una recomendación de inversión.")
    av["A8"].alignment = Alignment(wrap_text=True, vertical="top")
    av.row_dimensions[8].height = 34

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
