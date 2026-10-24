"""
Criterios que se pueden sumar a la tabla (v1.2.47), al estilo del "Add Screener Criteria" de Fiscal AI.

La tabla por defecto muestra solo Empresa, Sector e industria, Precio, Capitalizacion bursatil, Valoracion y Puntaje de calidad. En el Filtro de
empresas, "Agregar criterios" permite elegir otros datos (Dividend Yield, Fair Value, P/E...): cada criterio elegido suma una columna a la tabla
y, si se escribe un minimo y/o un maximo, deja solo las empresas dentro de ese rango. Sin minimo ni maximo, solo suma la columna.

Cada criterio sale de una columna que ya existe en los datos (no se calcula nada nuevo):
  clave        nombre interno (tambien nombre de la columna de ordenamiento)
  nombre       texto que ve la persona
  col          columna de `df` de donde sale el numero
  escala       factor para pasarlo a las unidades que se escriben (el Dividend Yield se guarda como fraccion: 0,0125 = 1,25 %)
  unidad       "%" o "x" (veces)
  paso         salto de los campos minimo / maximo
  ayuda        texto que se ve al pasar el mouse por el titulo de la columna
"""
import math

import pandas as pd



def _n(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def _money(x):
    """US$ con el signo escrito como &#36; (para que el markdown no lo tome como formula)."""
    v = _n(x)
    if v is None:
        return "—"
    return f"US&#36;&nbsp;{v:,.0f}" if abs(v) >= 100 else f"US&#36;&nbsp;{v:,.2f}"


CRITERIOS = [
    {"clave": "dividend_yield_actual", "nombre": "Dividend Yield", "col": "dividend_yield_actual", "escala": 100.0, "unidad": "%", "paso": 0.5,
     "ayuda": "Lo que paga por año en dividendos, como porcentaje del precio de hoy. Sin dato o sin dividendo: —. "
              "En la página de cada empresa lo ves comparado con su mediana histórica."},
    {"clave": "fv_dist", "nombre": "Fair Value", "col": "fv_dist", "escala": 100.0, "unidad": "%", "paso": 5.0,
     "ayuda": "El precio que resultaría de aplicar a la empresa sus propios múltiplos históricos (promedio de los métodos de su sector) y, entre "
              "paréntesis, cuánto más (+) o menos (−) que el precio de hoy. Es una estimación, no una recomendación. "
              "Al filtrar, el mínimo y el máximo se refieren a esa diferencia en %."},
    {"clave": "per_actual", "nombre": "P/E (precio / ganancias)", "col": "per_actual", "escala": 1.0, "unidad": "x", "paso": 1.0,
     "ayuda": "Cuántas veces las ganancias de un año paga el mercado por la empresa. Más bajo = más barata frente a lo que gana."},
    {"clave": "ev_ebitda_actual", "nombre": "EV/EBITDA", "col": "ev_ebitda_actual", "escala": 1.0, "unidad": "x", "paso": 1.0,
     "ayuda": "Valor de la empresa (con su deuda) dividido su resultado operativo antes de amortizaciones. Más bajo = más barata."},
    {"clave": "p_fcf_actual", "nombre": "P/FCF (precio / flujo libre)", "col": "p_fcf_actual", "escala": 1.0, "unidad": "x", "paso": 1.0,
     "ayuda": "Cuántas veces el flujo de caja libre paga el mercado por la empresa. Más bajo = más barata."},
    {"clave": "p_b_actual", "nombre": "P/Book (precio / valor libro)", "col": "p_b_actual", "escala": 1.0, "unidad": "x", "paso": 0.5,
     "ayuda": "Precio dividido el patrimonio contable por acción. Se usa sobre todo en bancos y seguros."},
    {"clave": "ps_actual", "nombre": "P/S (precio / ventas)", "col": "ps_actual", "escala": 1.0, "unidad": "x", "paso": 0.5,
     "ayuda": "Cuántas veces las ventas de un año paga el mercado por la empresa."},
    {"clave": "peg_actual", "nombre": "PEG", "col": "peg_actual", "escala": 1.0, "unidad": "x", "paso": 0.5,
     "ayuda": "El P/E dividido el crecimiento esperado de las ganancias. Solo informativo: no entra al puntaje."},
    {"clave": "posicion_52s", "nombre": "Posición en el rango de 52 semanas", "col": "posicion_52s", "escala": 100.0, "unidad": "%", "paso": 10.0,
     "ayuda": "Dónde está el precio entre el mínimo (0 %) y el máximo (100 %) de las últimas 52 semanas."},
]
POR_CLAVE = {c["clave"]: c for c in CRITERIOS}
POR_NOMBRE = {c["nombre"]: c for c in CRITERIOS}
NOMBRES = [c["nombre"] for c in CRITERIOS]


def agregar_columnas(df):
    """Copia de `df` con la columna `fv_dist` (diferencia entre el Fair Value y el precio, como fraccion). Necesaria para el criterio Fair Value."""
    df = df.copy()

    def dist(r):
        p, fv = _n(r.get("precio_actual")), _n(r.get("fair_value"))
        return (fv - p) / p if p and fv and p > 0 and fv > 0 else None

    df["fv_dist"] = df.apply(dist, axis=1) if len(df) else pd.Series(dtype=float)
    df["fv_dist"] = pd.to_numeric(df["fv_dist"], errors="coerce")
    return df


def valores(df, c):
    """Serie con el valor del criterio `c` en las unidades que se escriben (porcentaje o veces). Sin dato = NaN.
    Dividend Yield: sin dato o cero = no paga dividendo = 0 (asi "maximo 2 %" no deja afuera a las que no pagan)."""
    if c["col"] not in df.columns:
        return pd.Series([float("nan")] * len(df), index=df.index)
    s = pd.to_numeric(df[c["col"]], errors="coerce")
    if c["clave"] == "dividend_yield_actual":
        # el cache viejo a veces trae el rendimiento ya en % (mayor a 1): se lleva todo a fraccion
        s = s.where(~(s > 1), s / 100.0).fillna(0.0)
    return s * c["escala"]


def filtrar(df, activos):
    """Deja las empresas que cumplen todos los criterios. activos: {clave: (minimo, maximo)} (None = sin limite). Una empresa sin dato queda afuera
    si el criterio tiene algun limite."""
    out = df
    for clave, (mn, mx) in (activos or {}).items():
        c = POR_CLAVE.get(clave)
        if not c or (mn is None and mx is None):
            continue
        v = valores(out, c)
        m = v.notna()
        if mn is not None:
            m &= v >= mn
        if mx is not None:
            m &= v <= mx
        out = out[m]
    return out


def fmt_valor(c, v):
    """Texto de un valor para mostrar (en las unidades del criterio)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if c["unidad"] == "%":
        return f"{v:.2f}%" if c["clave"] == "dividend_yield_actual" else f"{v:.0f}%"
    return f"{v:.1f}x"


def celda(c, row):
    """HTML de la celda de un criterio para una fila (dict)."""
    clave = c["clave"]
    if clave == "fv_dist":
        p, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
        if not p or not fv or p <= 0 or fv <= 0:
            return '<span class="tv2-pr" title="No hubo datos para calcular un Fair Value">—</span>'
        v = int(round((fv - p) / p * 100))
        d = f"{v:+d}%" if v else "0%"
        return f'<span class="tv2-pr">{_money(fv)} <span class="tv2-fvs">({d})</span></span>'
    if clave == "dividend_yield_actual":
        x = _n(row.get("dividend_yield_actual"))
        if not x or x <= 0:
            return '<span class="tv2-pr" style="color:#9ca3af" title="No paga dividendo o no hay dato">—</span>'
        pct = x if x > 1 else x * 100
        return f'<span class="tv2-pr">{pct:.2f}%</span>'
    x = _n(row.get(c["col"]))
    if x is None or (c["unidad"] == "x" and x <= 0):
        return '<span class="tv2-pr" style="color:#9ca3af">—</span>'
    return f'<span class="tv2-pr">{fmt_valor(c, x * c["escala"])}</span>'
