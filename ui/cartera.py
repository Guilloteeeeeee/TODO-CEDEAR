"""Tu cartera (v1.2.73): la persona pone su edad y su perfil, sube su cartera (Excel o CSV, o la pega como texto) y la app devuelve una ORIENTACION: en qué
tipo de activo se está pasando o le falta peso, cómo está repartida la renta variable (geografía y tipo de empresa), si hay posiciones muy concentradas y
qué dice el screener de las empresas que tiene. Sin recomendaciones de compra o venta y SIN mostrar las carteras de referencia (data/carteras_modelo.py).
Todo se calcula con reglas (sin IA paga) y la cartera no se guarda. Las funciones de acá no usan Streamlit: se prueban solas."""
import html
import io
import re
import unicodedata

from data import carteras_modelo as CM

CLASES = {"rf": "Renta fija", "rv": "Renta variable", "oro": "Oro", "cripto": "Criptoactivos", "efectivo": "Liquidez", "otros": "Otras materias primas"}

SUPERSECTOR_DE = {   # sector de la app -> supersector (estructura Cíclico / Sensible / Defensivo)
    "Materiales Básicos": "ciclico", "REITs": "ciclico", "Bancos y seguros": "ciclico", "Pagos y datos": "ciclico", "Consumo Discrecional": "ciclico",
    "Comunicación": "sensible", "Telecomunicaciones": "sensible", "Industrial": "sensible", "Semiconductores": "sensible", "Software y nube": "sensible",
    "Hardware y servicios TI": "sensible", "Energía": "sensible",
    "Consumo Básico": "defensivo", "Salud": "defensivo", "Utilities": "defensivo",
}
GICS_DE = {   # sector de la app -> sector GICS (solo sectores, sin industrias)
    "Materiales Básicos": "Materiales Básicos", "REITs": "Inmobiliario", "Bancos y seguros": "Finanzas", "Pagos y datos": "Finanzas", "Consumo Discrecional": "Consumo Discrecional",
    "Comunicación": "Comunicación", "Telecomunicaciones": "Comunicación", "Industrial": "Industria", "Semiconductores": "Tecnología", "Software y nube": "Tecnología",
    "Hardware y servicios TI": "Tecnología", "Energía": "Energía", "Consumo Básico": "Consumo Básico", "Salud": "Salud", "Utilities": "Servicios Públicos",
}
NOMBRE_SUPER = {"ciclico": "cíclico", "sensible": "sensible", "defensivo": "defensivo"}
_USA = {"united states", "estados unidos", "usa", "ee uu", "eeuu", "us"}
_EMERGENTES = {"brazil", "brasil", "china", "india", "taiwan", "taiwán", "mexico", "méxico", "south korea", "corea del sur", "south africa", "sudafrica", "sudáfrica",
               "argentina", "uruguay", "chile", "colombia", "peru", "perú", "indonesia", "thailand", "tailandia", "turkey", "turquia", "turquía", "saudi arabia", "arabia saudita",
               "united arab emirates", "emiratos arabes unidos", "philippines", "filipinas", "hong kong"}


def norm(t):
    s = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%.,\- ]", " ", s)).strip()


def clave_tk(t):
    return re.sub(r"[^A-Z0-9]", "", str(t or "").upper())


# --- lectura de la cartera --------------------------------------------------------------------------------------------------------

def numero(x):
    """Numero desde 1.234,56 / 1,234.56 / 12,5 % / 3000; None si no se puede."""
    if isinstance(x, (int, float)):
        return float(x) if x == x else None
    t = str(x or "").strip().replace("%", "").replace("$", "").replace("US", "").replace("u$s", "").strip()
    if not t or not re.search(r"\d", t):
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        partes = t.split(",")
        t = t.replace(",", ".") if len(partes) == 2 and len(partes[1]) != 3 else t.replace(",", "")
    elif t.count(".") > 1 or (t.count(".") == 1 and re.fullmatch(r"-?[1-9]\d{0,2}\.\d{3}", t)):      # 1.500 = mil quinientos (punto de miles); 0.125 o 1.5 son decimales
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


# Palabras que identifican cada columna (se comparan contra el encabezado sin tildes ni mayusculas). Van por PRIORIDAD: se prueba la primera palabra en todas las columnas, despues la segunda...
_K_TICKER = ("ticker", "simbolo", "especie", "codigo", "nemonico", "symbol", "activo", "instrumento", "papel", "descripcion", "denominacion", "nombre", "name")
_K_MONTO = ("valuacion", "valorizado", "valorizacion", "valor actual", "valor de mercado", "valor mercado", "market value", "monto", "importe", "capital invertido", "invertido", "tenencia valorizada", "total", "valor",
            "tenencia", "saldo", "position value")
_K_MONTO_MAL = ("precio", "variacion", "resultado", "ganancia", "perdida", "rendimiento", "costo", "compra", "ppc", "inicial", "coste", "diario", "dia", "%", "pnl", "p l", "tna", "tir",
                "cantidad", "nominal", "disponible", "cotiz")
_K_PAIS = ("pais", "country", "region", "origen", "emisor pais")
_K_TIPO = ("tipo", "clase", "categoria", "rubro", "panel", "mercado", "asset class", "sector")
_K_CANT = ("cantidad", "nominales", "cant", "tenencia", "quantity", "unidades", "titulos")
_K_PRECIO = ("ultimo", "precio actual", "precio", "cotizacion", "price")
_K_PRECIO_MAL = ("compra", "ppc", "costo", "coste", "base", "promedio", "variacion", "cierre anterior", "apertura")
_K_MONEDA = ("moneda", "divisa", "currency")
_K_PESO = ("peso", "ponderacion", "% de la cartera", "% cartera", "participacion", "porcentaje")


def _buscar(n, claves, excluir=(), usados=()):
    for k in claves:
        for i, c in enumerate(n):
            if i in usados or not c:
                continue
            if (k in c if " " in k or len(k) > 3 else k in c.split()) and not any((x in c.split()) if (len(x) <= 3 and x.isalpha()) else (x in c) for x in excluir):
                return i
    return None


def _columnas(cols):
    """Devuelve un diccionario con los indices de las columnas segun los encabezados (None si no hay): ticker, monto (lista de (indice, moneda del encabezado)),
    tipo, cantidad, precio, moneda, peso. Los Excel de los brokers traen nombres muy distintos (Especie, Símbolo, Valuación, Total valorizado, Nominales...)."""
    n = [norm(c) for c in cols]
    it = _buscar(n, _K_TICKER)
    # columnas de monto: puede haber una en pesos y otra en dolares (Balanz, IOL); se guardan todas, en orden de prioridad
    montos = []
    for k in _K_MONTO:
        for i, c in enumerate(n):
            if i == it or any(i == m[0] for m in montos) or not c:
                continue
            if (k in c) and not any((x in c.split()) if (len(x) <= 3 and x.isalpha()) else (x in c) for x in _K_MONTO_MAL):
                montos.append((i, _moneda_encabezado(cols[i])))
    ic = _buscar(n, _K_CANT, usados=(it,))
    ip = _buscar(n, _K_PRECIO, excluir=_K_PRECIO_MAL, usados=(it, ic))
    # "Tenencia" a secas es ambiguo: si ya hay una columna de monto mas clara, es la cantidad
    solo = [m for m in montos if m[0] != ic]
    montos = solo if solo else ([] if (ic is not None and ip is not None) else montos)
    montos.sort(key=lambda m: {"usd": 0, None: 1, "ars": 2}[m[1]])        # si el archivo trae pesos y dolares, se prefiere dolares (no hace falta convertir)
    ipeso = _buscar(n, _K_PESO, usados=(it,))
    if not montos and ipeso is not None and not (ic is not None and ip is not None):
        montos = [(ipeso, None)]                                            # archivo con solo porcentajes de cada posicion
    return {"ticker": it, "monto": montos, "tipo": _buscar(n, _K_TIPO, usados=(it,)), "pais": _buscar(n, _K_PAIS, usados=(it,)), "cantidad": ic, "precio": ip,
            "moneda": _buscar(n, _K_MONEDA, usados=(it,)), "peso": ipeso}


def _moneda_encabezado(txt):
    """Moneda que dice el encabezado de una columna de monto ('Valuación USD', 'Total en pesos', 'Valorizado ($)'); None si no dice."""
    t = norm(txt)
    if re.search(r"\b(usd|u s|us|dolar|dolares|dollar|dollars|mep|ccl|usdt)\b", t) or "u$s" in str(txt).lower() or "us$" in str(txt).lower():
        return "usd"
    if re.search(r"\b(ars|peso|pesos|arg)\b", t) or "($)" in str(txt) or re.search(r"(^|\s)\$(\s|$)", str(txt)):
        return "ars"
    return None


def _puntaje_encabezado(fila):
    c = _columnas(fila)
    if c["ticker"] is None:
        return 0
    if c["monto"]:
        return 3 + (1 if c["tipo"] is not None else 0) + (1 if c["moneda"] is not None else 0)
    if c["cantidad"] is not None and c["precio"] is not None:
        return 3
    return 0


_TOTALES = re.compile(r"^(sub ?total|total|totales|suma|saldo total|resumen|valor total|total general|cartera|patrimonio|disponible)\b")


def _ticker_limpio(txt):
    """'AAPL - Apple Inc' -> 'AAPL'; 'AAPL.BA' queda igual; 'ON YPF' queda igual."""
    t = re.sub(r"^(etf|cedear)\s+(?=[A-Za-z0-9.]{2,10}$)", "", str(txt or "").strip(), flags=re.I)
    m = re.match(r"^([A-Za-z0-9.]{2,10})\s*(?:[-–—:(]\s+|\()", t)
    if m and not re.match(r"^(ON|FCI|BONO|LETRA|PLAZO)$", m.group(1), re.I):
        return m.group(1)
    return t


def _es_numerica(col, filas):
    v = [numero(f[col]) for f in filas if col < len(f) and str(f[col] or "").strip()]
    return len(v) >= 1 and sum(x is not None for x in v) / len(v) >= 0.7


def moneda_ticker(tk):
    """Los bonos argentinos terminan en D (dólar MEP) o C (dólar cable/CCL): AL30D, GD30C. Sin esa letra cotizan en pesos. Para el resto no se deduce nada (None)."""
    t = str(tk or "").strip().upper()
    if re.fullmatch(r"[A-Z]{2,3}\d{2}[DC]", t):
        return "usd"
    return None


_USD_GLOBAL = re.compile(r"(?:\ben|expresad[oa]s? en|valores en|montos en|importes en|valuado en|valorizado en)\s+(?:dolares|dolar|usd|u\$s|us\$|u s d)\b")
_ARS_GLOBAL = re.compile(r"(?:\ben|expresad[oa]s? en|valores en|montos en|importes en|valuado en|valorizado en)\s+(?:pesos|ars|\$)(?:\s|$)")


def _moneda_global(filas):
    """Moneda declarada en los títulos de arriba de la tabla ('Valores expresados en dólares'); None si no dice."""
    for f in filas:
        t = norm(" ".join(str(c or "") for c in f))
        if _USD_GLOBAL.search(t):
            return "usd"
        if _ARS_GLOBAL.search(t):
            return "ars"
    return None


def leer_tabla_info(filas):
    """(posiciones, notas). Ver `leer_tabla`. Las notas avisan de cosas que la persona tiene que saber (por ejemplo, que el monto es lo que pagó y no el valor de hoy)."""
    filas = [list(f) for f in filas if f and any(str(c or "").strip() for c in f)]
    if not filas:
        return [], []
    mejor, mejor_p = None, 0
    for i, f in enumerate(filas[:30]):
        p = _puntaje_encabezado(f)
        if p > mejor_p:
            mejor, mejor_p = i, p
    notas = []
    mon_global = None
    if mejor is not None:
        mon_global = _moneda_global(filas[:mejor + 1])
        c = _columnas(filas[mejor])
        datos = filas[mejor + 1:]
        for im, _ in c["monto"][:1]:
            if re.search(r"invertido|costo|coste|compra", norm(filas[mejor][im])):
                notas.append(f"Usé la columna «{str(filas[mejor][im]).strip()}»: es lo que pagaste, no el valor de hoy, así que los porcentajes salen sobre ese costo.")
    else:           # sin encabezado: ticker = primera columna, monto = primera columna que tenga numeros
        ancho = max(len(f) for f in filas)
        im = next((j for j in range(1, ancho) if _es_numerica(j, filas)), 1)
        c = {"ticker": 0, "monto": [(im, None)], "tipo": next((j for j in range(1, ancho) if j != im and not _es_numerica(j, filas)), None), "pais": None, "cantidad": None, "precio": None,
             "moneda": None, "peso": None}
        datos = filas
    it = c["ticker"]
    out, seccion, ultimo = [], "", ""
    for f in datos:
        tk = str(f[it] or "").strip() if it < len(f) else ""
        if tk and _TOTALES.match(norm(tk)):
            seccion, ultimo = "", ""                      # fila de total o subtotal: no es una posicion y corta el grupo
            continue
        m, mo_enc = None, None
        for im, mon in c["monto"]:
            v = numero(f[im]) if im < len(f) else None
            if v is not None and v > 0:
                m, mo_enc = v, mon
                break
        if m is None and c["cantidad"] is not None and c["precio"] is not None and max(c["cantidad"], c["precio"]) < len(f):
            c_, p_ = numero(f[c["cantidad"]]), numero(f[c["precio"]])
            m = c_ * p_ if c_ and p_ and c_ > 0 and p_ > 0 else None
        if m is None:
            # titulo de grupo ("Acciones", "Bonos", "Renta Fija"): sin ningun numero en la fila y que diga de que tipo es
            if tk and not any(numero(x) is not None for j, x in enumerate(f) if j != it and str(x or "").strip()) and len(tk) <= 40:
                seccion = tk if clase_de_tipo(tk) else ""      # un grupo que no se entiende ("Fondos") corta el anterior
            continue
        if not tk:
            tk = ultimo                                    # varias compras de la misma empresa: la primera fila lleva el ticker y las otras lo dejan vacio
            if not tk:
                continue
        else:
            ultimo = tk
        tipo = str(f[c["tipo"]] or "").strip() if c["tipo"] is not None and c["tipo"] < len(f) else ""
        if seccion and (not tipo or not clase_de_tipo(tipo)):
            tipo = seccion              # el título de grupo ("Renta Fija") vale más que una columna que no se entiende
        if re.match(r"^etf\s+", tk, re.I) and not clase_de_tipo(tipo):
            tipo = "ETF"
        mo = mo_enc or (moneda_de(f[c["moneda"]]) if c["moneda"] is not None and c["moneda"] < len(f) else None) or moneda_ticker(tk) or mon_global
        pais = str(f[c["pais"]] or "").strip() if c.get("pais") is not None and c["pais"] < len(f) else ""
        out.append({"ticker": _ticker_limpio(tk), "monto": m, "tipo": tipo, "moneda": mo, "pais": pais})
    # una empresa con varias compras (lotes) es UNA posicion: se suman
    agr, orden = {}, []
    for p in out:
        k = (clave_tk(p["ticker"]) or p["ticker"].upper(), p["moneda"])
        if k in agr:
            agr[k]["monto"] += p["monto"]
            agr[k]["tipo"] = agr[k]["tipo"] or p["tipo"]
            agr[k]["pais"] = agr[k].get("pais") or p.get("pais")
        else:
            agr[k] = dict(p)
            orden.append(k)
    return [agr[k] for k in orden], notas


def leer_tabla(filas):
    """`filas`: lista de listas. Se adapta a lo que venga: el encabezado puede estar en cualquiera de las primeras 30 filas (se saltean títulos y datos de la cuenta),
    las columnas se reconocen por sus nombres (Símbolo, Especie, Valuación, Total valorizado, Capital invertido, Cantidad × Precio…), puede haber una columna de monto en pesos y otra en dólares,
    se ignoran las filas de totales y subtotales, los títulos de grupo ("Acciones", "Bonos"…) se usan como Tipo, las filas sin ticker son otra compra del ticker de arriba y las compras
    repetidas se suman. Sin encabezado: primera columna = ticker, primera columna con números = monto. Devuelve [{'ticker', 'monto', 'tipo', 'moneda'}] con monto > 0."""
    return leer_tabla_info(filas)[0]


def moneda_de(txt):
    """'usd' | 'ars' | None según lo escrito en la columna Moneda (USD, U$S, dólares, MEP, CCL, ARS, $, pesos...)."""
    if str(txt).strip() == "$":
        return "ars"
    t = norm(txt)
    if not t:
        return None
    if re.search(r"\b(usd|u s|us|u\$s|dolar|dolares|dollar|dollars|mep|ccl|cable|usdt)\b", t) or "us$" in str(txt).lower() or "u$s" in str(txt).lower():
        return "usd"
    if re.search(r"\b(ars|peso|pesos|pesos argentinos|arg)\b", t) or str(txt).strip() == "$":
        return "ars"
    return None


def convertir(posiciones, base, tc):
    """Pasa todos los montos a dólares. `base`: moneda de los montos sin Moneda ('usd' o 'ars'); `tc`: pesos por dólar (necesario si hay algo en pesos).
    Devuelve (posiciones en dólares, cantidad convertida desde pesos, True si faltó el tipo de cambio)."""
    out, n, falta = [], 0, False
    for p in posiciones:
        q = dict(p)
        mon = p.get("moneda") or base
        if mon == "ars":
            if tc and tc > 0:
                q["monto"] = p["monto"] / tc
                n += 1
            else:
                falta = True
        out.append(q)
    return out, n, falta


def leer_texto_info(texto):
    """(posiciones, notas) de una cartera pegada como texto: una posicion por linea ('AAPL 1500', 'SPY: 20%', 'AL30;2000;bono soberano') o una tabla copiada de Excel (separada por tabulaciones)."""
    filas = []
    for linea in str(texto or "").splitlines():
        if not linea.strip():
            continue
        if "\t" in linea:
            partes = [p.strip() for p in linea.rstrip("\r\n").split("\t")]          # tabla de Excel: las celdas vacias cuentan (si no, las columnas se corren)
        elif re.search(r"[;|]", linea):
            partes = [p.strip() for p in re.split(r"[;|]", linea.strip())]
        else:
            linea = linea.strip()
            m = re.match(r"^([A-Za-z0-9.\-]+)\s*[:=\-]?\s+(.+)$", linea)
            partes = [m.group(1), m.group(2)] if m else [linea]
        filas.append(partes)
    return leer_tabla_info(filas)


def leer_texto(texto):
    return leer_texto_info(texto)[0]


def _filas_csv(datos):
    """Filas de un .csv / .txt: detecta la codificacion (UTF-8 o Windows) y el separador (; , tab |) mirando las primeras lineas."""
    import csv
    if isinstance(datos, (bytes, bytearray)):
        try:
            txt = bytes(datos).decode("utf-8-sig")
        except UnicodeDecodeError:
            txt = bytes(datos).decode("cp1252", "replace")
    else:
        txt = str(datos)
    lineas = [l for l in txt.splitlines() if l.strip()][:40]
    mejor, mejor_p = ",", -1
    for d in (";", "\t", "|", ","):
        cuentas = [l.count(d) for l in lineas]
        if not any(cuentas):
            continue
        moda = max(set(c for c in cuentas if c), key=lambda c: cuentas.count(c))
        p = cuentas.count(moda) * 10 + (1 if d == ";" else 0)
        if p > mejor_p:
            mejor, mejor_p = d, p
    return [list(r) for r in csv.reader(io.StringIO(txt), delimiter=mejor)]


def leer_archivo_info(nombre, datos):
    """(posiciones, nota) desde un .xlsx / .xlsm / .xls / .csv / .txt (bytes). Si el Excel tiene varias hojas usa la que tenga más posiciones y lo avisa en `nota`.
    Lanza ValueError con un mensaje claro si no se puede leer."""
    import pandas as pd
    n = str(nombre or "").lower()
    if n.endswith(".pdf"):
        pos, notas, _tc = leer_pdf_info(datos)
        return pos, " ".join(notas)
    if n.endswith((".csv", ".txt", ".tsv")):
        try:
            pos, notas = leer_tabla_info(_filas_csv(datos))
            return pos, " ".join(notas)
        except Exception as e:  # noqa: BLE001
            raise ValueError("No pude leer el archivo. Probá con el Excel de ejemplo (botón de arriba) o guardalo como .csv.") from e
    try:
        hojas = pd.read_excel(io.BytesIO(datos), header=None, dtype=str, keep_default_na=False, sheet_name=None)
    except ImportError as e:
        raise ValueError("Ese formato de Excel viejo (.xls) no se puede leer acá: guardalo como .xlsx o .csv y subilo de nuevo.") from e
    except Exception as e:  # noqa: BLE001
        raise ValueError("No pude leer el archivo. Probá con el Excel de ejemplo (botón de arriba) o guardalo como .xlsx o .csv.") from e
    mejor, mejor_n, mejor_t = None, 0, 0.0
    for nom, df in hojas.items():
        try:
            pos, notas = leer_tabla_info(df.values.tolist())
        except Exception:  # noqa: BLE001
            continue
        t = sum(p["monto"] for p in pos)
        if len(pos) > mejor_n or (len(pos) == mejor_n and t > mejor_t):
            mejor, mejor_n, mejor_t = (nom, pos, notas), len(pos), t
    if mejor is None:
        return [], ""
    nota = f"Tu archivo tiene {len(hojas)} hojas: usé «{mejor[0]}», que es la que tiene más posiciones." if len(hojas) > 1 else ""
    return mejor[1], " ".join([nota] + mejor[2]).strip()


def leer_archivo(nombre, datos):
    """Posiciones desde un .xlsx / .xls / .csv (bytes). Lanza ValueError con un mensaje claro si no se puede leer."""
    return leer_archivo_info(nombre, datos)[0]


# --- PDF del broker (resumen de cuenta / tenencias) -----------------------------------------------------------------------------------------------------------

_SIMB = {"$": "ars", "ars": "ars", "usd": "usd", "us$": "usd", "u$s": "usd", "us": "usd"}
_TK_PDF = re.compile(r"^[A-Z0-9][A-Z0-9.\-/]{0,11}$")
_ENC_PDF = re.compile(r"(especie|ticker|simbolo|instrumento|activo|descripcion)")
_EFECTIVO_TIT = ("monedas", "efectivo", "liquidez", "disponible", "disponibilidades", "saldos", "caja", "cuentas")


def _texto_pdf(datos):
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ValueError("Para leer PDFs falta un componente en el servidor. Mientras tanto subí el Excel o pegá tu cartera como texto.") from e
    try:
        lector = PdfReader(io.BytesIO(datos))
        if getattr(lector, "is_encrypted", False):
            try:
                lector.decrypt("")
            except Exception:  # noqa: BLE001
                pass
        return "\n".join((pg.extract_text() or "") for pg in lector.pages)
    except Exception as e:  # noqa: BLE001
        raise ValueError("No pude abrir ese PDF. Probá con el Excel del broker o pegá tu cartera como texto.") from e


def _cola_numerica(linea):
    """Separa una línea en (texto, [(moneda, número)...]) tomando los números del final: 'AO28 BONO … USD 546,00 0.00 $ 1.417,50 $ 773.955' -> texto + 4 números."""
    tok = linea.split()
    cola, i = [], len(tok)
    while i > 0:
        t = tok[i - 1]
        if re.fullmatch(r"-?\d[\d.,]*", t) and numero(t) is not None:
            mon = None
            if i - 1 > 0 and tok[i - 2].lower() in _SIMB:
                mon = _SIMB[tok[i - 2].lower()]
                i -= 1
            elif re.match(r"^(\$|us\$|u\$s)", t.lower()):
                mon = "ars" if t.startswith("$") else "usd"
            cola.append((mon, numero(t)))
            i -= 1
        else:
            m = re.fullmatch(r"(\$|US\$|U\$S)(-?\d[\d.,]*)", t, re.I)
            if m and numero(m.group(2)) is not None:
                cola.append((_SIMB[m.group(1).lower()], numero(m.group(2))))
                i -= 1
            else:
                break
    cola.reverse()
    return " ".join(tok[:i]), cola


def tipo_cambio_texto(texto):
    """Dólar MEP/CCL que figura en el resumen ('Tipo de cambio para esa fecha: MEP $ 1.564,29'); None si no hay."""
    m = re.search(r"\b(?:MEP|CCL|contado con liqui\w*)\s*[:=]?\s*\$?\s*(\d[\d.]*,\d+|\d+\.\d{2})", texto or "", re.I)
    v = numero(m.group(1)) if m else None
    return v if v and v > 50 else None


def leer_pdf_info(datos):
    """(posiciones, notas, tipo de cambio del resumen) desde el PDF de un broker. Entiende los resúmenes con tablas por tipo de activo (Bonos, Cedears, Corporativos… con
    especie, descripción, cantidad, precio y valor actual) y la sección de monedas/efectivo; la moneda de cada valor sale del símbolo ($ o USD). Si no encuentra ese formato,
    prueba con las tablas en columnas. No se guardan datos personales: solo se toman tickers y montos."""
    texto = _texto_pdf(datos)
    if not texto.strip():
        raise ValueError("Ese PDF no tiene texto que pueda leer (parece una foto o un escaneo). Subí el Excel del broker o pegá tu cartera como texto.")
    out, seccion, modo, hay_efectivo = [], "", "", False
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        n = norm(linea)
        sin_num = not re.search(r"\d", linea)
        if sin_num and len(linea) <= 45:
            if n in _EFECTIVO_TIT:
                modo, seccion = "efectivo", ""
                continue
            if clase_de_tipo(linea) and n not in ("monedas",):
                modo, seccion = "tabla", linea
                continue
            if modo == "efectivo" or re.search(r"evolucion|distribucion|resumen|informacion|instrumentos|composicion", n):
                modo = "" if modo == "efectivo" else modo
                continue
        if _ENC_PDF.search(n) and re.search(r"(valor|monto|importe|valuacion|total)", n) and sin_num:
            modo = "tabla"
            continue
        if _TOTALES.match(n) or re.search(r"tipo de cambio|cotizacion|dolar mep|\|", n):
            continue
        texto_l, cola = _cola_numerica(linea)
        if not cola or not texto_l:
            continue
        mon, valor = cola[-1]
        if valor <= 0:
            continue
        if modo == "efectivo":
            if mon is None and not moneda_de(texto_l):
                continue
            mon = mon or moneda_de(texto_l)
            if len(cola) != 1 or not re.search(r"peso|dolar|dollar|usd|cable|mep|ccl|euro|real", n):
                continue
            nombre = "Efectivo en pesos" if mon == "ars" else "Efectivo en dólares"
            out.append({"ticker": nombre, "monto": round(valor, 2), "tipo": "Efectivo", "moneda": mon})
            hay_efectivo = True
        elif modo == "tabla":
            tk, _, desc = texto_l.partition(" ")
            if not _TK_PDF.match(tk) or not re.search(r"[A-Z]", tk) or len(cola) < 2 or re.fullmatch(r"\d+", tk):
                continue
            tipo = seccion
            if not clase_de_tipo(tipo):
                d = norm(desc)
                tipo = "Cedear" if d.startswith("cedear") else ("Obligación negociable" if re.search(r"\bon\b", d) else ("Bono" if re.search(r"\b(bono|letra|lecap|boncap)\b", d) else ""))
            out.append({"ticker": _ticker_limpio(tk), "monto": valor, "tipo": tipo, "moneda": mon})
    notas = []
    if out:
        agr, orden = {}, []
        for p in out:
            k = (clave_tk(p["ticker"]) or p["ticker"].upper(), p["moneda"])
            if k in agr:
                agr[k]["monto"] += p["monto"]
            else:
                agr[k] = dict(p)
                orden.append(k)
        out = [dict(agr[k], monto=round(agr[k]["monto"], 2)) for k in orden]
        if hay_efectivo:
            notas.append("Incluí el efectivo que figura en tu resumen.")
        return out, notas, tipo_cambio_texto(texto)
    # sin el formato "una tabla por tipo de activo": se prueba con las filas en columnas (separadas por 2+ espacios) del PDF
    try:
        from pypdf import PdfReader
        filas = []
        for pg in PdfReader(io.BytesIO(datos)).pages:
            for l in (pg.extract_text(extraction_mode="layout") or "").splitlines():
                celdas = [c.strip() for c in re.split(r"\s{2,}", l.strip()) if c.strip()]
                if len(celdas) >= 2:
                    filas.append(celdas)
        pos, notas = leer_tabla_info(filas)
    except Exception:  # noqa: BLE001
        pos, notas = [], []
    return pos, notas, tipo_cambio_texto(texto)



def rentabilidad_anual(aportado, final, anios, retirado=0):
    """Rentabilidad anualizada ESTIMADA de una cartera cuando no se conocen las fechas exactas de los aportes.
    Devuelve {'total': ganancia % sobre lo aportado, 'anual_inicio': anual si todo se aportó al principio, 'anual_parejo': anual si se aportó en cuotas iguales, una por mes}.
    Si se aportó de a poco, el dinero estuvo menos tiempo invertido y la tasa verdadera es mayor que la de 'todo al principio' (cuando hubo ganancia): por eso se muestran las dos.
    v1.4.4: `retirado` es lo que el inversor sacó en total; se cuenta como si lo hubiera sacado hoy (capital final + retirado).
    None si los datos no sirven (aportes o capital <= 0, o menos de un mes)."""
    try:
        a, f, y = float(aportado), float(final), float(anios)
        ret = float(retirado or 0)
    except (TypeError, ValueError):
        return None
    if a <= 0 or f <= 0 or ret < 0 or y < 1 / 12:
        return None
    f = f + ret
    r0 = (f / a) ** (1 / y) - 1
    n = max(1, int(round(y * 12)))
    c = a / n

    def valor_final(r):
        return sum(c * (1 + r) ** (y - i / 12) for i in range(n))
    lo, hi = -0.95, 20.0
    if valor_final(lo) > f or valor_final(hi) < f:
        r1 = None
    else:
        for _ in range(200):
            mid = (lo + hi) / 2
            if valor_final(mid) < f:
                lo = mid
            else:
                hi = mid
        r1 = (lo + hi) / 2
    return {"total": (f / a - 1) * 100, "anual_inicio": r0 * 100, "anual_parejo": r1 * 100 if r1 is not None else None, "anios": y}


def duracion_txt(dias):
    """Cuánto tiempo pasó, en palabras: '5 días', '3 semanas y 2 días', '4 meses y 12 días', '1 año y 3 meses', '3 años'."""
    d = int(max(0, round(dias)))

    def u(n, uno, varios):
        return f"{n} {uno if n == 1 else varios}"
    if d < 14:
        return u(d, "día", "días")
    if d < 60:
        sem, rest = divmod(d, 7)
        return u(sem, "semana", "semanas") + (f" y {u(rest, 'día', 'días')}" if rest else "")
    if d < 365:
        mes = int(d / 30.4375)
        rest = int(round(d - mes * 30.4375))
        if rest >= 30:
            mes, rest = mes + 1, max(0, rest - 30)
        return u(mes, "mes", "meses") + (f" y {u(rest, 'día', 'días')}" if rest > 0 else "")
    anios = int(d / 365.25)
    mes = int(round((d - anios * 365.25) / 30.4375))
    if mes >= 12:
        anios, mes = anios + 1, 0
    return u(anios, "año", "años") + (f" y {u(mes, 'mes', 'meses')}" if mes else "")


def rentabilidad_con_fechas(movimientos, final, hoy):
    """Rentabilidad con las fechas EXACTAS de cada aporte y retiro (v1.4.4).
    movimientos: [(fecha, monto)], monto > 0 = aporte, monto < 0 = retiro. final: lo que vale la cartera hoy (misma moneda). hoy: fecha de hoy.
    Devuelve un dict {aportado, retirado, final, ganancia, total_pct (ganancia sobre lo aportado), dias, periodo_pct (rendimiento del período, método Dietz modificado:
    ganancia / dinero medio invertido, sirve también para períodos cortos), anual (% por año con TIR por fechas; None si pasó menos de 1 año o no converge)}
    o {"error": "texto"} si los datos no sirven."""
    try:
        movs = sorted(((m[0], float(m[1])) for m in (movimientos or []) if m and m[0] is not None and m[1] not in (None, 0)), key=lambda x: x[0])
        fin = float(final)
    except (TypeError, ValueError):
        return {"error": "Revisá los montos: tienen que ser números."}
    if not movs:
        return {"error": "Cargá al menos un aporte con su fecha."}
    if fin < 0:
        return {"error": "El capital final no puede ser negativo."}
    if any(f > hoy for f, _ in movs):
        return {"error": "Hay una fecha posterior a hoy: revisá la tabla."}
    if movs[0][1] < 0:
        return {"error": "El primer movimiento tiene que ser un aporte (no se puede retirar antes de haber puesto plata)."}
    aportado = sum(m for _, m in movs if m > 0)
    retirado = -sum(m for _, m in movs if m < 0)
    f0 = movs[0][0]
    dias = (hoy - f0).days
    if dias < 1:
        return {"error": "Para calcular necesito que el primer aporte sea de ayer o antes."}
    ganancia = fin + retirado - aportado
    ponderado = sum(m * (dias - (f - f0).days) / dias for f, m in movs)       # dinero medio invertido durante el período
    if ponderado <= 0:
        return {"error": "Con esos retiros no hay dinero invertido para medir el rendimiento: revisá la tabla."}
    out = {"aportado": aportado, "retirado": retirado, "final": fin, "ganancia": ganancia, "total_pct": ganancia / aportado * 100,
           "dias": dias, "periodo_pct": ganancia / ponderado * 100, "anual": None}
    if dias >= 365:
        taus = [((hoy - f).days / 365.0, m) for f, m in movs]

        def valor(r):
            return sum(m * (1 + r) ** t for t, m in taus)
        lo, hi = -0.9999, 50.0
        if (valor(lo) - fin) * (valor(hi) - fin) < 0:
            for _ in range(300):
                mid = (lo + hi) / 2
                if (valor(lo) - fin) * (valor(mid) - fin) <= 0:
                    hi = mid
                else:
                    lo = mid
            out["anual"] = (lo + hi) / 2 * 100
    return out


def plantilla_excel():
    """Bytes de un .xlsx de ejemplo (Ticker, Monto, Tipo)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Cartera"
    ws.append(["Ticker", "Monto", "Moneda (opcional)", "Tipo (opcional)", "País (opcional)"])
    for r in (("AAPL", 1500, "USD", "", ""), ("KO", 800, "USD", "", ""), ("SPY", 3000, "USD", "", ""), ("AL30", 2000000, "ARS", "Renta fija soberana", "Argentina"),
              ("ON YPF", 1000, "USD", "Renta fija corporativa", "Argentina"), ("Bono del Tesoro EE.UU.", 1000, "USD", "Renta fija soberana", "Estados Unidos"),
              ("GLD", 500, "USD", "Oro", ""), ("BTC", 300, "USD", "Cripto", ""), ("Caución", 500000, "ARS", "Efectivo", "Argentina")):
        ws.append(list(r))
    ws.append([])
    ws.append(["Monto: el valor actual de cada tenencia. Moneda: USD o ARS (si la dejás vacía se usa la que elijas en la página); todo se pasa a dólares automáticamente con el dólar CCL. "
               "Tipo y País: solo hacen falta para lo que no es un CEDEAR, una empresa o un ETF de la lista (bonos, obligaciones negociables, fondos, efectivo)."])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 26
    ws.column_dimensions["E"].width = 18
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


# --- clasificacion ----------------------------------------------------------------------------------------------------------------

def clase_de_tipo(tipo):
    """Clase ('rf', 'rv', 'oro', 'cripto', 'efectivo') a partir de lo que escribió la persona en 'Tipo' (o lo que trae el Excel del broker); None si no se entiende."""
    t = norm(tipo)
    if not t:
        return None
    if any(k in t for k in ("cripto", "bitcoin", "ether", "btc", "eth")):
        return "cripto"
    if re.search(r"\b(oro|gold)\b", t):
        return "oro"
    if any(k in t for k in ("efectivo", "cash", "liquidez", "plazo fijo", "money market", "caucion", "cuenta remunerada", "cuentas remuneradas", "billetera")):
        return "efectivo"
    if (any(k in t for k in ("renta fija", "bono", "sobera", "corpor", "obligacion", "letra", "lecap", "boncap", "boncer", "lecer", "tesoro", "treasury", "titulo publico",
                             "titulos publicos", "dolar linked", "dollar linked", "bonar"))
            or re.search(r"\b(rf|on|ons|cer)\b", t)):
        return "rf"
    if any(k in t for k in ("accion", "cedear", "etf", "renta variable")) or re.search(r"\brv\b", t):
        return "rv"
    if re.search(r"\b(dolar|dolares|peso|pesos|caja)\b", t):
        return "efectivo"
    # sectores y rubros de renta variable (planillas que traen una columna "Sector": Technology, Consumer Def, Energy, Healthcare, REIT...)
    if (re.search(r"\b(technology|tecnologia|healthcare|health care|salud|financial|financials|financiero|financieras|utilities|utility|energy|energia|industrial|industrials|industrial goods|"
                  r"communication|communications|comunicacion|comunicaciones|telecom|telecomunicaciones|consumer|consumo|basic materials|materials|materiales|reit|reits|real estate|inmobiliario|"
                  r"mlp|mlps|divis|dividend|dividendos|emergentes|acciones)\b", t)):
        return "rv"
    return None          # por ejemplo "FCI" a secas: depende de en que invierta, asi que se pide aclararlo


# Renta fija argentina por formato de ticker (BYMA). No es una lista completa: lo que no se reconoce se pide en la columna Tipo.
_RF_AR = (
    r"^(AL|GD|AE)\d{2}[DC]?$",                        # Bonares y Globales: AL29, AL30, AL35, AE38, AL41, GD29, GD30, GD35, GD38, GD41, GD46 (y sus versiones D / C)
    r"^[ST]\d{1,2}[A-Z]\d[DC]?$",                     # Letras y Bonos capitalizables (LECAP / BONCAP): S31G6, S30S6, T15E7...
    r"^X\d{2}[A-Z]\d$",                               # Letras ajustadas por CER (LECER)
    r"^TZX[A-Z0-9]{2,3}[DC]?$", r"^TX\d{2}[DC]?$",      # Bonos ajustados por CER (Boncer): TZX26, TZXD6, TX26, TX28
    r"^(DICP|PARP|CUAP|DIP0|PAP0|CUAP)[DC]?$",          # Discount, Par y Cuasipar
    r"^TT[A-Z]\d{2}[DC]?$", r"^TV\d{2}[DC]?$", r"^TY\d{2}P$",   # Duales, dolar linked y Bonte
    r"^BPO[A-Z]\d[DC]?$", r"^CO\d{2}[DC]?$",           # Provincia de Buenos Aires (BPOA7...) y Cordoba (CO26...)
)
# Acciones argentinas mas comunes (panel lider y algunas del general) -> sector de la app, para poder evaluar la diversificacion. Pais: Argentina.
ACCIONES_AR = {"GGAL": "Bancos y seguros", "BMA": "Bancos y seguros", "BBAR": "Bancos y seguros", "SUPV": "Bancos y seguros", "BYMA": "Bancos y seguros",
               "YPFD": "Energía", "TGSU2": "Energía", "TGNO4": "Energía", "PAMP": "Utilities", "CEPU": "Utilities", "EDN": "Utilities", "TRAN": "Utilities",
               "ALUA": "Materiales Básicos", "TXAR": "Materiales Básicos", "LOMA": "Materiales Básicos", "TECO2": "Telecomunicaciones", "IRSA": "REITs",
               "CRES": None, "COME": None, "VALO": None, "MIRG": None, "AGRO": None, "CVH": None, "HARG": None, "METR": None, "BHIP": None}


def _es_rf_ar(tk):
    return any(re.match(p, tk) for p in _RF_AR)


def clasificar(pos, empresas, etfs):
    """Agrega a la posicion: 'clase' (o None), 'fuente' ('empresa' | 'etf' | 'tipo' | 'regla'), 'info' (datos de la empresa si es una de la lista).
    `empresas`: {CLAVE_TICKER: {nombre, sector, pais, categoria}}; `etfs`: {CLAVE_TICKER: {categoria, ...}}."""
    tk = clave_tk(re.sub(r"\.BA$", "", str(pos["ticker"]).strip(), flags=re.I))
    pos = dict(pos)
    pos["clase"], pos["fuente"], pos["info"] = None, None, None
    por_tipo = clase_de_tipo(pos.get("tipo"))
    nom = norm(pos["ticker"])
    if tk in empresas and por_tipo in (None, "rv"):
        pos.update(clase="rv", fuente="empresa", info=empresas[tk], ticker=str(pos["ticker"]).upper())
    elif tk in etfs and por_tipo in (None, "rv", "oro", "cripto"):
        cat = norm(etfs[tk].get("categoria"))
        clase = "oro" if tk in ("GLD", "IAU", "GLDM") else "cripto" if "cripto" in cat else "otros" if "materias primas" in cat else "rv"
        pos.update(clase=clase, fuente="etf", ticker=str(pos["ticker"]).upper())
    elif tk in ACCIONES_AR and por_tipo in (None, "rv"):
        pos.update(clase="rv", fuente="empresa", info={"nombre": tk, "sector": ACCIONES_AR[tk], "pais": "Argentina", "categoria": None}, ticker=str(pos["ticker"]).upper())
    elif por_tipo:
        pos.update(clase=por_tipo, fuente="tipo")
    elif _es_rf_ar(tk):
        pos.update(clase="rf", fuente="regla")
    elif (" " in nom or len(nom) >= 5 or nom in ("oro", "cash", "on")) and clase_de_tipo(pos["ticker"]):      # el nombre mismo lo dice: "Dólares", "ON YPF", "Bono AL30", "Plazo fijo", "Caución"
        pos.update(clase=clase_de_tipo(pos["ticker"]), fuente="tipo")
    elif tk in ("BTC", "ETH", "BTCUSD", "ETHUSD", "BITCOIN", "ETHEREUM"):
        pos.update(clase="cripto", fuente="regla")
    return pos


def region(pais):
    p = norm(pais)
    if p in ("global", "mundial", "mundo", "internacional", "world"):
        return "global"
    if p in ("emergentes", "emergente", "mercados emergentes", "latam", "latinoamerica", "america latina"):
        return "emergentes"
    return "usa" if p in _USA else "emergentes" if p in _EMERGENTES else "desarrollados" if p else None


def valoracion(categoria):
    c = str(categoria or "").upper()
    return "infravalorada" if "INFRAVALORADA" in c else "sobrevalorada" if "SOBREVALORADA" in c else "bien valuada" if "BIEN VALUADA" in c else None


# --- analisis ---------------------------------------------------------------------------------------------------------------------

EMP_MIN, EMP_MAX = 20, 30          # guía de cantidad de empresas individuales (pedido de Guille 01/11/2026)
NOM_SUPER = {"ciclico": "cíclicas", "sensible": "sensibles", "defensivo": "defensivas"}
PESO_MIN, PESO_MAX = 2.0, 5.0      # ideal de diversificación (no es una regla obligatoria): cada empresa (acción o CEDEAR) entre 2 % y 5 % de la cartera; los ETFs no entran
UMBRAL = 5.0          # puntos de diferencia a partir de los cuales se avisa (la devolución es una orientación, no un cálculo fino)
_CAT_ETF_GEO = {"usa": "usa", "usa segun sectores": "usa", "internacionales no usa": "fuera_sd", "internacionales con usa": "global"}


def _geo_rf(p):
    """Bucket geográfico de una posición de renta fija que no es ETF: bonos y ONs argentinos -> emergentes; Tesoro de EE.UU. -> usa; Bund o Gilt -> desarrollados; el resto, sin ubicar."""
    sub = subtipo_rf(p["ticker"], p.get("tipo"))
    if sub in ("ar", "on"):
        return "emergentes"
    if sub == "ext":
        t = norm(f"{p['ticker']} {p.get('tipo') or ''}")
        return "desarrollados" if re.search(r"\b(bund|bunds|gilt|europa|europeo)\b", t) else "usa"
    return None


def _geo_de(p, etfs):
    """Bucket geográfico de una posición de renta variable: 'usa' | 'desarrollados' | 'emergentes' | 'fuera_sd' (fuera de EE.UU., sin detalle) | 'global' (mezcla) | None."""
    if p["fuente"] == "empresa":
        return region(p["info"].get("pais"))
    if p["fuente"] == "etf":
        e = etfs.get(clave_tk(p["ticker"])) or {}
        return region(e.get("pais")) if e.get("pais") else _CAT_ETF_GEO.get(norm(e.get("categoria")))
    return None


# Aviso legal de la devolución de cartera (texto de Guille, 01/11/2026). Va en pantalla y en el PDF, y NO se agrega el aviso largo del sitio.
AVISO_CARTERA = (
    "Recordá que tenés absoluta responsabilidad de tus operaciones. Por lo tanto, hacé tus propios análisis y definí si las ideas descriptas en esta devolución son adecuadas para tus objetivos individuales. "
    "Finanzas para Médicos se deslinda de cualquier responsabilidad por las acciones que puedan derivar de la mala interpretación del material precedente. "
    "Esta evaluación es automática y puede cometer errores o no contemplar algún dato de tu cartera. Este informe es de carácter personal, no queda guardado y no podemos usarlo como parte de nuestras actividades. "
    "Si tenés dudas o querés una devolución personalizada, podés contactarnos por nuestras vías de comunicación.",
)


def _flt(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def subtipo_rf(ticker, tipo=""):
    """'ar' (soberano o letra argentina), 'on' (obligación negociable / corporativo), 'ext' (Tesoro de EE.UU. o Europa) u 'otros'. Solo por el nombre o el tipo: no se opina sobre la calidad del emisor."""
    tk = clave_tk(re.sub(r"\.BA$", "", str(ticker or "").strip(), flags=re.I))
    t = norm(f"{ticker} {tipo or ''}")
    if re.search(r"\b(treasury|treasuries|t bill|tbill|bund|bunds|gilt)\b", t) or "tesoro de ee" in t or "tesoro de estados" in t or "tesoro estadounidense" in t:
        return "ext"
    if _es_rf_ar(tk) or "sobera" in t or re.search(r"\b(bonar|bonares|global|globales|letra|letras|lecap|boncap|lecer|boncer|bopreal|tesoro nacional|bono argentino)\b", t):
        return "ar"
    if "corpor" in t or "obligacion" in t or "negociable" in t or re.search(r"\b(on|ons)\b", t):
        return "on"
    return "otros"


def fusionar(posiciones):
    """Suma las posiciones repetidas (el mismo activo en dos brokers o dos archivos). Devuelve (posiciones, cantidad de repetidas que se unieron)."""
    agr, orden, n = {}, [], 0
    for p in posiciones:
        k = (clave_tk(p["ticker"]) or str(p["ticker"]).upper(), p.get("moneda") or "")
        if k in agr:
            agr[k]["monto"] += p["monto"]
            agr[k]["tipo"] = agr[k].get("tipo") or p.get("tipo")
            agr[k]["pais"] = agr[k].get("pais") or p.get("pais")
            n += 1
        else:
            agr[k] = dict(p)
            orden.append(k)
    return [agr[k] for k in orden], n


def resumen_guardable(res, edad, perfil, fecha):
    """Lo mínimo de una evaluación para poder comparar la próxima vez (el inversor lo baja y lo vuelve a subir: no guardamos nada nosotros)."""
    pe = res["peso_inv"]
    g = res.get("geo") or {}
    return {"formato": "evaluacion_cartera_v1", "fecha": str(fecha), "edad": int(edad), "perfil": perfil, "peso": {k: round(v, 1) for k, v in pe.items()},
            "liquidez": round(res.get("liquidez", 0.0), 1), "n_empresas": res.get("n_empresas", 0), "n_posiciones": len(res.get("posiciones", [])),
            "usa_pct": round(g.get("usa", 0.0), 1) if g else None, "defensivo_pct": round((res.get("super") or {}).get("defensivo", 0.0), 1) if res.get("super") else None,
            "desvio": {k: round(v, 1) for k, v in res.get("desvio", {}).items()}}


def comparar(previa, res):
    """Frases que comparan la evaluación anterior (el archivo que subió el inversor) con la de hoy. [] si el archivo no sirve."""
    if not isinstance(previa, dict) or previa.get("formato") != "evaluacion_cartera_v1" or not isinstance(previa.get("peso"), dict):
        return []
    f = []
    ahora = res["peso_inv"]
    nom = {"rv": "renta variable", "rf": "renta fija", "oro": "oro", "cripto": "criptoactivos", "efectivo": "liquidez (cuentas remuneradas y cauciones)", "otros": "otras materias primas"}
    cambios = []
    for k in ("rv", "rf", "oro", "cripto", "efectivo", "otros"):
        a, b = _flt(previa["peso"].get(k)) or 0.0, ahora.get(k, 0.0)
        if abs(b - a) >= 2:
            cambios.append(f"{nom[k]} pasó de {a:.0f} % a {b:.0f} %")
    fp = str(previa.get("fecha", ""))
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", fp)
    fp = f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else (fp or "una fecha que no figura")
    f.append(f"Tu evaluación anterior es del {fp}. " + ("Qué cambió en los grandes grupos: " + "; ".join(cambios) + "." if cambios else "Los grandes grupos casi no cambiaron."))
    dprev = previa.get("desvio") if isinstance(previa.get("desvio"), dict) else {}
    cerca, lejos = [], []
    for k, d in res["desvio"].items():
        dp = _flt(dprev.get(k))
        if dp is None or k not in nom:
            continue
        if abs(d) <= abs(dp) - 2:
            cerca.append(nom[k])
        elif abs(d) >= abs(dp) + 2:
            lejos.append(nom[k])
    if cerca:
        f.append("**Te acercaste a lo que suele ser razonable para tu edad y perfil en:** " + ", ".join(cerca) + ". Se nota el trabajo.")
    if lejos:
        f.append("Te alejaste un poco en: " + ", ".join(lejos) + ". No es bueno ni malo en sí: puede ser una decisión tuya; solo es para que lo tengas presente.")
    ne_p, ne = previa.get("n_empresas"), res.get("n_empresas", 0)
    if isinstance(ne_p, int) and ne_p != ne:
        f.append(f"Cantidad de empresas individuales: antes {ne_p}, ahora {ne}.")
    lp = _flt(previa.get("liquidez"))
    if lp is not None and abs(lp - res.get("liquidez", 0.0)) >= 2:
        f.append(f"Liquidez: antes {lp:.0f} %, ahora {res.get('liquidez', 0.0):.0f} %.")
    return f


def analizar(posiciones, edad, perfil, empresas, etfs):
    """Resultado con los porcentajes de la cartera, los desvios contra la referencia (interna) y los detalles; None si la edad no es valida o no hay nada para analizar."""
    ref = CM.referencia(edad, perfil)
    if not ref or not posiciones:
        return None
    cl = [clasificar(p, empresas, etfs) for p in posiciones]
    sin = [p for p in cl if not p["clase"]]
    ok = [p for p in cl if p["clase"]]
    total = sum(p["monto"] for p in ok)
    if total <= 0:
        return {"sin_clasificar": sin, "total": 0}
    peso = {k: 0.0 for k in CLASES}
    for p in ok:
        peso[p["clase"]] += p["monto"] / total * 100
    nombre_rango, carts = ref
    sep_efectivo = carts.get("efectivo", 0) > 0          # solo la cartera de 70+ tiene efectivo propio (cuentas remuneradas y cauciones)
    # v1.2.85: el efectivo es LIQUIDEZ, no renta fija: nunca se suma a la renta fija. Cuando la referencia no tiene liquidez propia, lo invertido (renta variable, renta fija,
    # oro y criptoactivos) se compara sobre lo que queda sin la liquidez; la liquidez se evalúa aparte (10 a 15 % está bien tolerado).
    liq = peso["efectivo"]
    base = 100.0 if sep_efectivo else max(100.0 - liq, 1.0)
    cmp_real = {k: peso[k] / base * 100 for k in ("rf", "rv", "oro", "cripto")}
    if sep_efectivo:
        cmp_real["efectivo"] = peso["efectivo"]
    desvio = {k: cmp_real[k] - carts.get(k, 0) for k in cmp_real}
    rv = [p for p in ok if p["clase"] == "rv"]
    rv_total = sum(p["monto"] for p in rv)
    emp = [p for p in rv if p["fuente"] == "empresa"]
    geo = {k: 0.0 for k in ("usa", "desarrollados", "emergentes", "fuera_sd", "global")}
    rf_pos = [p for p in ok if p["clase"] == "rf"]
    rf_total = sum(p["monto"] for p in rf_pos)
    for p in rv + rf_pos:                     # v1.4.6: la geografía contempla renta variable Y renta fija
        if p["fuente"] in ("tipo", "regla") and str(p.get("pais") or "").strip():
            g = region(p["pais"])                 # v1.4.9: el país que la persona puso en la columna «País»
        else:
            g = _geo_de(p, etfs) if (p["clase"] == "rv" or p["fuente"] == "etf") else _geo_rf(p)
        if g:
            geo[g] += p["monto"]
    geo_tot = sum(geo.values())
    geo_base = rv_total + rf_total
    sup = {"ciclico": 0.0, "sensible": 0.0, "defensivo": 0.0}
    sect, sect_tk, gics = {}, {}, {}
    for p in sorted(emp, key=lambda q: -q["monto"]):
        s = p["info"].get("sector")
        if SUPERSECTOR_DE.get(s):
            sup[SUPERSECTOR_DE[s]] += p["monto"]
            sect[s] = sect.get(s, 0.0) + p["monto"]
            gics[GICS_DE[s]] = gics.get(GICS_DE[s], 0.0) + p["monto"]
            sect_tk.setdefault(s, []).append(str(p["ticker"]))
    st_ = sum(sup.values())
    por_pos = sorted(ok, key=lambda p: -p["monto"])
    # v1.4.5: los grandes grupos SIN la liquidez (la liquidez es optativa y va aparte; solo entra en el 100 % cuando la referencia tiene efectivo propio, 70+)
    peso_inv = {k: peso[k] / base * 100 for k in peso if k != "efectivo" or sep_efectivo}
    etf_m = sum(p["monto"] for p in rv if p["fuente"] == "etf")
    rf_det = {}
    for p in ok:
        if p["clase"] == "rf":
            sub = subtipo_rf(p["ticker"], p.get("tipo"))
            rf_det.setdefault(sub, []).append((str(p["ticker"]), p["monto"] / total * 100))
    num_b = den_b = 0.0
    for p in rv:
        b = None
        if p["fuente"] == "empresa":
            b = _flt((p.get("info") or {}).get("beta"))
        elif p["fuente"] == "etf":
            b = _flt((etfs.get(clave_tk(p["ticker"])) or {}).get("beta"))
        if b is not None and b > 0:
            num_b += b * p["monto"]
            den_b += p["monto"]
    beta = {"valor": num_b / den_b, "cubierto_pct": den_b / rv_total * 100} if den_b and rv_total and den_b / rv_total >= 0.5 else None
    return {
        "peso_inv": peso_inv, "etf_rv_pct": (etf_m / rv_total * 100) if rv_total else 0.0, "n_etfs": sum(1 for p in rv if p["fuente"] == "etf"), "rf_det": rf_det, "beta": beta,
        "rango": nombre_rango, "efectivo_propio": sep_efectivo, "liquidez": liq, "total": total, "peso": peso, "desvio": desvio, "rv_total": rv_total, "n_empresas": len(emp),
        "geo": ({k: v / geo_base * 100 for k, v in geo.items()} if geo_base and geo_tot else None), "geo_ubicado_pct": (geo_tot / geo_base * 100) if geo_base else 0.0,
        "sectores_gics": sorted(((k, v / st_ * 100) for k, v in gics.items()), key=lambda kv: -kv[1]) if st_ else [],
        "super": {k: v / st_ * 100 for k, v in sup.items()} if st_ else None, "sector_ubicado_pct": (st_ / rv_total * 100) if rv_total else 0.0,
        "sectores": sorted(((k, v / st_ * 100) for k, v in sect.items()), key=lambda kv: -kv[1]) if st_ else [],
        "sector_tk": sect_tk,
        "sector_top": (max(sect.items(), key=lambda kv: kv[1])[0], max(sect.values()) / st_ * 100) if sect and st_ else None,
        "posiciones": [{"ticker": p["ticker"], "pct": p["monto"] / total * 100, "clase": p["clase"], "fuente": p.get("fuente")} for p in por_pos],
        "sin_clasificar": sin, "pct_sin_clasificar": (sum(p["monto"] for p in sin) / (total + sum(p["monto"] for p in sin)) * 100) if sin else 0.0,
    }


def _pts(x):
    return f"{abs(x):.0f}"


LIQ_MIN, LIQ_MAX = 5.0, 15.0      # v1.4.5 (regla de Guille, 01/11/2026): una liquidez de 5 a 15 % está perfecta; es optativa y va aparte del 100 % invertido
_NOMBRE_CLASE = {"rv": "renta variable", "oro": "oro", "cripto": "criptoactivos", "efectivo": "liquidez (cuentas remuneradas y cauciones)"}


_PQ_SUBIR = {"oro": "el oro suele funcionar como reaseguro contra la inflación y como sostén de la cartera en momentos de incertidumbre, cuando las acciones caen",
             "rf": "la renta fija aporta ingresos más previsibles y amortigua las caídas de las acciones",
             "rv": "a largo plazo la renta variable es lo que más hace crecer el capital por encima de la inflación",
             "cripto": "en dosis chicas puede sumar crecimiento, aunque es muy volátil",
             "efectivo": "la liquidez da margen para imprevistos y para aprovechar oportunidades"}
_PQ_BAJAR = {"rv": "hoy tenés más riesgo de caída del que suele ser razonable para tu edad y tu perfil",
             "rf": "con tanta renta fija el capital crece más despacio de lo que suele ser razonable para tu edad y tu perfil",
             "oro": "el oro no genera ingresos y su precio puede quedarse años sin moverse",
             "cripto": "son muy volátiles y una caída fuerte se siente mucho en el total",
             "efectivo": "la plata quieta no rinde y pierde poder de compra con la inflación"}


def _nom(lst, n=4):
    lst = list(dict.fromkeys(str(x) for x in lst))
    if not lst:
        return ""
    if len(lst) > n:
        return ", ".join(lst[:n]) + f" y {len(lst) - n} más"
    return lst[0] if len(lst) == 1 else ", ".join(lst[:-1]) + " y " + lst[-1]


def _y(lst, n=4):
    """Lista en castellano con «y» (o «e» antes de palabra que empieza con i / hi): «BTC e IBIT»."""
    t = _nom(lst, n)
    return re.sub(r" y ((?:[IiÍí]|[Hh][IiÍí])\w*)$", r" e \1", t)


_CONT = {"ciclico": "cíclico", "sensible": "sensible", "defensivo": "defensivo"}
_SUPERS_TXT = {"ciclico": "Materiales Básicos, REITs, Financiero y Consumo Discrecional", "sensible": "Comunicación, Industrial, Tecnología y Energía",
               "defensivo": "Consumo Básico, Salud y Servicios Públicos"}
_POR_QUE_SUMAR = {
    "rf": "la renta fija aporta ingresos más previsibles y disminuye la volatilidad. Idealmente apuntar a bonos soberanos y corporativos de alto grado de inversión, que son los de menor riesgo de default.",
    "oro": "el oro le da equilibrio al portfolio en momentos de incertidumbre y contextos de alta inflación.",
    "rv": "la renta variable es la que más hace crecer el capital a largo plazo. Idealmente de forma diversificada, con empresas sólidas o ETFs.",
    "cripto": "en dosis chicas, los criptoactivos pueden sumar crecimiento, siempre sabiendo que son muy volátiles.",
    "efectivo": "las cuentas remuneradas y las cauciones dan estabilidad y disponibilidad inmediata.",
}
_POR_QUE_ACERCAR = {
    "rv": "acercarla a la de referencia le baja volatilidad a la cartera, algo acorde a tu momento como inversor.",
    "rf": "acercarla a la de referencia le da más lugar al crecimiento del capital, algo acorde a tu momento como inversor.",
    "oro": "el oro no genera ingresos y su precio puede quedarse años sin moverse.",
    "cripto": "son muy volátiles y, con esa ponderación, un movimiento fuerte se siente mucho en el total.",
    "efectivo": "la plata quieta no rinde y pierde poder de compra con la inflación.",
}


def devolucion(res, edad, perfil, nombre=""):
    """[(titulo, [párrafos])] (v1.5.0, con el tono y la estructura del modelo escrito por Guille, 02/11/2026): Objetivo como inversor, Estructura de tu cartera,
    Diversificación geográfica, Diversificación sectorial, Liquidez, (beta si hay dato) y Conclusiones finales. En cada apartado primero lo que NOTAMOS en la cartera
    (observación, sin dar malas noticias ni castigar) y después la base teórica, que va SIEMPRE. Los ajustes se proponen en positivo (sumar, aumentar, considerar),
    en orden de importancia y con su porqué. Sin recomendar activos puntuales, sin opinar sobre emisores y sin autores."""
    sec = []
    if not res or not res.get("total"):
        return sec
    pe, d = res["peso"], res["desvio"]
    pi = res.get("peso_inv") or pe
    ef = res.get("efectivo_propio")
    ps = res["posiciones"]
    ref = CM.referencia(edad, perfil)
    refk = ref[1] if ref else {}
    varios = any(len(c[3]) > 1 for c in CM.RANGOS if c[0] <= int(edad) <= c[1])
    tu_edad = "tu edad y perfil de riesgo" if varios else "tu edad"
    claves = ("rv", "rf", "efectivo", "oro", "cripto") if ef else ("rv", "rf", "oro", "cripto")
    nombres = dict(_NOMBRE_CLASE, rf="renta fija")
    ajustes, bien = [], []

    def _de(k):
        n = _y([p["ticker"] for p in ps if p.get("clase") == k])
        return f" ({n})" if n else ""
    # ---------------- Objetivo como inversor
    f = []
    if ref:
        res_obj = CM.OBJETIVO_RESUMEN.get(ref[0])
        if res_obj:
            f.append(f"**Objetivo como inversor:** {res_obj} **Esta premisa es la base de nuestra devolución.**")
    sec.append(("Objetivo como inversor", f))
    # ---------------- Estructura de tu cartera
    f = []
    obs = []
    for k in ("rv", "rf"):
        v, r_ = pi.get(k, 0.0), refk.get(k, 0)
        if d.get(k, 0) > UMBRAL:
            obs.append(f"**la {nombres[k]} ocupa un lugar considerable** en tu portfolio (=={v:.0f} %==)")
        elif d.get(k, 0) < -UMBRAL:
            obs.append(f"**no tenés {nombres[k]}**" if v < 0.5 else f"**la {nombres[k]} tiene una presencia menor** (=={v:.0f} %==)")
    if obs:
        t = "Al analizar tus posiciones notamos que " + " y que ".join(obs) + "."
    else:
        t = ("Al analizar tus posiciones notamos que **la distribución entre renta variable y renta fija está muy en línea** con la cartera de referencia para " + tu_edad + ".")
        bien.append("la distribución entre renta variable y renta fija está muy en línea con la de referencia")
    f.append(t)
    if pi.get("oro", 0) >= 0.5:
        f.append(f"Tenés =={pi['oro']:.0f} %== en **oro**{_de('oro')}. El oro suele funcionar como reaseguro contra la inflación y como sostén de la cartera en momentos de incertidumbre.")
    elif refk.get("oro", 0) > 0:
        f.append("**No tenés oro.** El oro suele funcionar como reaseguro contra la inflación y como sostén de la cartera en momentos de incertidumbre.")
    if pi.get("cripto", 0) >= 0.5:
        f.append(f"Tenés =={pi['cripto']:.0f} %== en **criptomonedas**{_de('cripto')}. Los criptoactivos pueden sumar crecimiento en dosis chicas, pero son muy volátiles.")
    elif refk.get("cripto", 0) > 0:
        f.append("**No tenés criptomonedas.** En dosis chicas pueden sumar crecimiento, aunque son muy volátiles.")
    det = res.get("rf_det") or {}
    if det.get("ar"):
        f.append("Tené presente que los bonos argentinos tienen más riesgo que los de Estados Unidos o Europa de grado de inversión; en general, cuanto más corto el plazo, menos expuestos están a los cambios que puedan venir.")
    if det.get("on"):
        f.append("En las obligaciones negociables no evaluamos la calidad de cada empresa emisora: conviene mirar la calificación crediticia de cada una.")
    if det.get("ext") and not det.get("ar") and not det.get("on"):
        bien.append("tu renta fija está en bonos de Estados Unidos o Europa, que suelen ser de los de menor riesgo")
    if pe["otros"] >= 5:
        f.append(f"Tenés {pe['otros']:.0f} % en otras materias primas (metales, granos, energía): no las comparamos con la cartera de referencia.")
    if res["sin_clasificar"]:
        n_ = ", ".join(dict.fromkeys(str(p["ticker"]) for p in res["sin_clasificar"]))
        f.append(f"No pudimos ubicar: {n_} ({res['pct_sin_clasificar']:.0f} % del total), así que quedaron afuera del análisis. Si son bonos, obligaciones negociables, fondos o efectivo, completá las columnas **Tipo** y **País** del Excel.")
    if ref:
        partes = [f"**{CLASES[k]} {refk[k]:.0f} %**" for k in ("rv", "rf", "oro", "cripto", "efectivo") if refk.get(k, 0) > 0]
        f.append(f"La cartera teórica de referencia para una persona de {tu_edad} tiene: " + ", ".join(partes[:-1]) + (" y " if len(partes) > 1 else "") + partes[-1] + ".")
    sec.append(("Estructura de tu cartera", f))
    falta = [k for k in ("rf", "rv", "oro", "efectivo") if k in claves and (d[k] < -UMBRAL or (k == "oro" and pi.get("oro", 0) < 0.5 and refk.get("oro", 0) >= 5))]
    pasa = sorted((k for k in claves if d[k] > UMBRAL), key=lambda k: -d[k])
    aj_geo, aj_liq = [], []
    if falta:
        nom_f = [{"rf": "Renta Fija", "rv": "Renta Variable", "oro": "Oro", "efectivo": "Liquidez"}[k] for k in falta]
        pq = [_POR_QUE_SUMAR[k] for k in falta]
        pq_txt = pq[0] + "".join(" " + x[0].upper() + x[1:] for x in pq[1:])
        pq_txt = pq_txt.replace(" El oro le da", " El oro, por su parte, le da")
        ajustes.append(f"Aumentar progresivamente la ponderación de {_y(nom_f)}. **Por qué:** {pq_txt}")
    elif pasa:
        k = pasa[0]
        ajustes.append(f"Ir acercando de a poco la ponderación de {nombres[k]} a la de la cartera de referencia. **Por qué:** {_POR_QUE_ACERCAR[k]}")
    # ---------------- Diversificación geográfica
    g = res.get("geo")
    f = []
    GU, GD, GE = CM.GEOGRAFIA["usa"], CM.GEOGRAFIA["desarrollados"], CM.GEOGRAFIA["emergentes"]
    if pe["rv"] < 1 and pe["rf"] < 1:
        f.append("Como no tenés renta variable ni renta fija, no hay países para analizar.")
    elif not g:
        f.append("No pudimos ubicar por país tus posiciones, así que no podemos analizar este punto. Si cargás la columna **País** del Excel, lo incluimos.")
    else:
        base_g = g["usa"] + g["desarrollados"] + g["emergentes"] + g["fuera_sd"]
        if base_g > 0:
            usa, emer, des = g["usa"] / base_g * 100, g["emergentes"] / base_g * 100, g["desarrollados"] / base_g * 100
            obs_g = False
            if usa >= 97:
                obs_g = True
                f.append("Notamos que **estás expuesto puramente a Estados Unidos**. Si bien es la economía más importante del mundo, es importante estar diversificado en otros mercados.")
            elif usa > GU + 10:
                obs_g = True
                f.append(f"Notamos que **tu cartera está muy concentrada en Estados Unidos** (=={usa:.0f} %==). Si bien es la economía más importante del mundo, es importante estar diversificado en otros mercados.")
            elif usa < GU - 15:
                obs_g = True
                f.append(f"Notamos que **Estados Unidos tiene una presencia menor** en tu cartera (=={usa:.0f} %==). Al ser la economía más importante del mundo, suele ser conveniente que ocupe el lugar principal.")
            if emer > GE + 10:
                obs_g = True
                f.append(f"También notamos **una presencia importante de mercados emergentes** (=={emer:.0f} %==), que suelen ser más volátiles por sus monedas, su política y su economía más cambiantes.")
            if usa > GU + 10:
                aj_geo.append("Sumar otros países desarrollados (Europa, Japón, Canadá) y, en menor medida, emergentes. **Por qué:** hoy todo depende de una sola economía y de una sola moneda; repartir en otros países reduce ese riesgo.")
            elif usa < GU - 15:
                aj_geo.append("Darle más lugar a Estados Unidos, sin dejar de lado otros países desarrollados y emergentes. **Por qué:** es la economía más importante del mundo y donde están las empresas más grandes y líquidas.")
            if emer > GE + 10:
                aj_geo.append("Ir dándole más lugar a países desarrollados frente a los emergentes. **Por qué:** los desarrollados aportan más estabilidad a la cartera.")
            if not obs_g:
                f.append(f"Notamos que **tu distribución geográfica está muy bien equilibrada** (Estados Unidos {usa:.0f} %, otros desarrollados {des:.0f} %, emergentes {emer:.0f} %).")
                bien.append("tu distribución geográfica está muy bien equilibrada")
        if res["geo_ubicado_pct"] < 60:
            f.append("Parte de tu cartera no pudo ubicarse por país, así que esta lectura es parcial. Si completás la columna **País** del Excel, la afinamos.")
    f.append(f"**La diversificación geográfica es clave.** Por eso, la cartera teórica de referencia pone a Estados Unidos como el país con más asignación (**{GU} %**), sin dejar de lado otros países desarrollados (**{GD} %**) y mercados emergentes (**{GE} %**).")
    sec.append(("Diversificación geográfica", f))
    # ---------------- Diversificación sectorial (+ empresas individuales)
    f = []
    s = res.get("super")
    SC, SS, SD = CM.SUPERSECTOR["ciclico"], CM.SUPERSECTOR["sensible"], CM.SUPERSECTOR["defensivo"]
    if pe["rv"] < 1:
        f.append("Como no tenés renta variable, no hay sectores para analizar.")
    elif not s:
        f.append("No pudimos ubicar por sector tus posiciones de renta variable (los ETFs no se abren por dentro), así que este punto queda sin analizar.")
    else:
        dif = {k: s[k] - CM.SUPERSECTOR[k] for k in s}
        sobre = [k for k in ("sensible", "ciclico", "defensivo") if dif[k] > 20]
        sub = [k for k in ("defensivo", "sensible", "ciclico") if dif[k] < -20]
        if sobre or sub:
            partes_s = [f"**empresas del supersector {_CONT[k]} están sobreponderadas** (=={s[k]:.0f} %==)" for k in sobre]
            partes_s += [(f"**las del supersector {_CONT[k]} están infraponderadas** (=={s[k]:.0f} %==)" if s[k] >= 0.5 else f"**no tenés empresas del supersector {_CONT[k]}**") for k in sub]
            f.append("Analizando tu caso vemos que " + " y ".join(partes_s) + ".")
            for k in sub:
                if k == "defensivo":
                    ajustes.append("Sumar empresas defensivas (consumo básico, salud, servicios públicos) para diversificar por sectores. **Por qué:** son las que mejor aguantan cuando la economía se enfría, blindando tu cartera ante recesiones. Además se sostienen muy bien ante correcciones del mercado.")
                else:
                    ajustes.append(f"Sumar empresas del supersector {_CONT[k]} ({_SUPERS_TXT[k].lower()}) para diversificar por sectores. **Por qué:** así la cartera no depende tanto de un solo tipo de empresa y se acerca a una estructura que soporta mejor los distintos momentos del ciclo.")
        else:
            f.append(f"Analizando tu caso vemos que **tus empresas están muy bien repartidas entre los supersectores** (defensivo {s['defensivo']:.0f} %, sensible {s['sensible']:.0f} %, cíclico {s['ciclico']:.0f} %).")
            bien.append("tus empresas están muy bien repartidas entre los supersectores")
        gtop = (res.get("sectores_gics") or [None])[0]
        if gtop and gtop[1] > 35:
            tk_g = [t for sct, lst in (res.get("sector_tk") or {}).items() if GICS_DE.get(sct) == gtop[0] for t in lst]
            sup_g = next((SUPERSECTOR_DE[sct] for sct in SUPERSECTOR_DE if GICS_DE.get(sct) == gtop[0]), None)
            f.append(f"Dentro del supersector {_CONT.get(sup_g, '')}, **{gtop[0]}**{f' ({_y(tk_g)})' if tk_g else ''} constituye el =={gtop[1]:.0f} %== de tus posiciones.")
            ajustes.append(f"Considerar otros sectores además de {gtop[0]}. **Por qué:** si a ese sector le va mal, arrastra a buena parte de tus empresas al mismo tiempo.")
    if pe["rv"] >= 1:
        emp_ps = [p for p in ps if p.get("clase") == "rv" and p.get("fuente") in ("empresa", "regla")]
        n_emp, n_etf = res.get("n_empresas", 0), res.get("n_etfs", 0)
        arriba = [p for p in emp_ps if p["pct"] > PESO_MAX + 0.05]
        abajo = [p for p in emp_ps if p["pct"] < PESO_MIN - 0.05]
        partes_e = []
        if n_emp:
            partes_e.append(f"{n_emp} empresa{'s' if n_emp != 1 else ''} individual{'es' if n_emp != 1 else ''}")
        if n_etf:
            partes_e.append(f"{n_etf} ETF{'s' if n_etf != 1 else ''}")
        if partes_e:
            t = "En cuanto a tus posiciones, tenés " + " y ".join(partes_e) + "."
            if arriba:
                t += f" {_y([p['ticker'] for p in arriba])} {'superan' if len(arriba) > 1 else 'supera'} el {PESO_MAX:.0f} % de la cartera."
            if len(abajo) >= 2:
                t += f" {_y([p['ticker'] for p in abajo])} pesan menos del {PESO_MIN:.0f} %."
            f.append(t)
        if emp_ps and not arriba and len(abajo) < 2 and n_emp >= EMP_MIN:
            bien.append(f"tenés {n_emp} empresas individuales y cada una pesa entre {PESO_MIN:.0f} y {PESO_MAX:.0f} %")
        elif n_etf and n_emp < EMP_MIN:
            bien.append("usás ETFs, que resuelven buena parte de la diversificación")
        if 0 < n_emp < EMP_MIN and not n_etf:
            ajustes.append(f"Sumar de a poco más empresas, o algún ETF, para acercarte a las {EMP_MIN} posiciones. **Por qué:** con más posiciones, una sola que tenga un mal momento pesa menos en el total.")
        if n_emp > 45:
            ajustes.append("Considerar si todas tus posiciones siguen teniendo sentido. **Por qué:** más de 40 a 50 acciones ya no disminuye el riesgo y puede atentar contra la rentabilidad.")
        if arriba:
            ajustes.append(f"Si querés diversificar más, ir llevando de a poco las empresas que superan el {PESO_MAX:.0f} % ({_y([p['ticker'] for p in arriba], 3)}) hacia el rango de {PESO_MIN:.0f} a {PESO_MAX:.0f} %. **Por qué:** si una sola empresa tiene un mal momento, con ese peso arrastra mucho al total.")
        if len(abajo) >= 2:
            ajustes.append(f"Las empresas que pesan menos de {PESO_MIN:.0f} % casi no mueven tu cartera: es una decisión tuya si las subís hacia el rango de {PESO_MIN:.0f} a {PESO_MAX:.0f} % o las dejás como están. **Por qué:** con menos de ese peso, aunque la empresa suba mucho, casi no cambia el resultado total.")
        f.append(f"Nuestra idea en este apartado es presentarte una estructura de cartera que permita soportar los diferentes momentos de los ciclos del mercado con la menor volatilidad posible. "
                 f"Para ello la diversificación debería contemplar un **{SC} % de ponderación en Cíclicas** ({_SUPERS_TXT['ciclico']}), **{SS} % Sensibles** ({_SUPERS_TXT['sensible']}) y **{SD} % Defensivas** ({_SUPERS_TXT['defensivo']}).")
        f.append(f"Respecto a la distribución de empresas individuales, la teoría marca que mínimamente hay que tener **entre {EMP_MIN} y {EMP_MAX} posiciones**, con un peso de **{PESO_MIN:.0f} a {PESO_MAX:.0f} %** en cada una. "
                 "Más de 40 a 50 acciones no disminuye el riesgo de la cartera y expone al inversor a sobrediversificación, lo cual puede atentar contra la rentabilidad. "
                 "Importante destacar que los ETFs participan en la diversificación, ya que traen muchas empresas dentro contemplando una correcta distribución del riesgo.")
    sec.append(("Diversificación sectorial", f))
    # ---------------- Liquidez
    liq = pe["efectivo"]
    f = []
    if ef:
        f.append(f"Para tu edad, la cartera de referencia incluye la liquidez (cuentas remuneradas y cauciones) como parte central de la cartera: hoy tenés {liq:.0f} %.")
    elif liq < 0.5:
        f.append("**Hoy no tenés liquidez cargada.** Es una decisión tuya, pero un colchón así te da margen sin tener que vender inversiones a destiempo.")
        aj_liq.append(f"Considerar armar un colchón de liquidez de {LIQ_MIN:.0f} a {LIQ_MAX:.0f} %. **Por qué:** te da margen para imprevistos y para aprovechar oportunidades del mercado sin vender inversiones a destiempo.")
    elif liq > LIQ_MAX:
        f.append(f"Tenés =={liq:.0f} %== de liquidez, unos {liq - LIQ_MAX:.0f} puntos por encima del rango sugerido. Es seguridad, pero sin rendimiento propio y con la inflación en contra; pasarse de ahí conviene que sea una decisión y no un descuido.")
        aj_liq.append(f"Llevar la liquidez de a poco hacia el rango de {LIQ_MIN:.0f} a {LIQ_MAX:.0f} %. **Por qué:** la plata quieta no rinde y pierde poder de compra con la inflación.")
    elif liq >= LIQ_MIN:
        f.append(f"Tenés =={liq:.0f} %== de liquidez, **dentro del rango sugerido: está perfecto.**")
        bien.append(f"tu liquidez ({liq:.0f} %) está en un muy buen nivel")
    else:
        f.append(f"Tenés =={liq:.0f} %== de liquidez, un poco por debajo del rango sugerido.")
    if not ef:
        f.append(f"La liquidez (efectivo, cuentas remuneradas, cauciones) es optativa, pero en general habría que contemplar **entre un {LIQ_MIN:.0f} y {LIQ_MAX:.0f} %** para aprovechar oportunidades del mercado.")
    sec.append(("Liquidez", f))
    # ---------------- Beta (solo si hay datos)
    b = res.get("beta")
    if b:
        v = b["valor"]
        lec = "se movió bastante más que el mercado" if v > 1.2 else "se movió algo más que el mercado" if v > 1.05 else "se movió casi igual que el mercado" if v >= 0.95 else "tendió a moverse menos que el mercado"
        sec.append(("Sensibilidad al mercado (beta)", [f"El beta aproximado de tu renta variable es {v:.2f} (calculado sobre el {b['cubierto_pct']:.0f} % de ella para el que hay dato). "
                                                       f"Históricamente, ese nivel significa que tu renta variable {lec}: si el mercado se mueve 10 %, tu renta variable tendió a moverse alrededor de {v * 10:.0f} %. Es una aproximación basada en el pasado, no una predicción."]))
    # ---------------- Conclusiones finales (orden de importancia: ponderaciones, sectores, empresas, geografía, liquidez)
    ajustes += aj_geo + aj_liq
    f = ["**Armar una cartera lleva tiempo, estudio y decisiones, y detrás de cada posición hay un esfuerzo que se reconoce.** "
         + (("En tu caso, además, " + "; ".join(bien) + ". ") if bien else "")
         + "Puede que tu cartera tenga este diseño intencionalmente y lo respetamos. Recordá que nuestro análisis constituye una guía educativa más que una recomendación formal."]
    if ajustes:
        f.append("##En orden de importancia te enumeramos qué ajustaríamos:")
        f += [f"{n}. {a}" for n, a in enumerate(ajustes, 1)]
    else:
        f.append("En tu caso no vemos ajustes importantes para proponerte. Te sugerimos revisarla una o dos veces al año para que las ponderaciones no se vayan corriendo.")
    sec.append(("Conclusiones finales", f))
    return sec


def despedida(nombre=""):
    """Cierre de la devolución (texto de Guille)."""
    n = (nombre or "").strip() or "colega inversor"
    return (f"Hasta aquí nuestro aporte, estimado {n}. Esperamos te sirva para tener otra mirada sobre tu portfolio y te ayude a construir el futuro financiero que te merecés. "
            "Si necesitás una consulta personalizada podés contactarnos.", "Abrazo grande y buenas inversiones.")


def saludo(nombre, edad, perfil):
    """Encabezado de la devolución (texto de Guille)."""
    n = (nombre or "").strip() or "colega inversor"
    varios = any(len(c[3]) > 1 for c in CM.RANGOS if c[0] <= int(edad) <= c[1])
    extra = f"{int(edad)} años - Perfil {str(perfil).title()}" if (perfil and varios) else f"{int(edad)} años"
    return (f"Estimado {n} ({extra}).", "Todo inversor de éxito evalúa periódicamente su portfolio. Agradecemos que lo hagas con nosotros.")


_WARN = ("pasan de", "pesan menos de", "te pasás", "te faltan", "muy concentrada", "poco estados", "los emergentes pesan", "hay poco", "hay mucho", "un solo sector", "tu mayor posición", "posiciones más grandes",
         "tenés ", "no pude ubicar", "ojo:", "volátiles", "no tenés renta variable", "no pude ubicar por")
_OK = ("están dentro de lo habitual", "estás en línea", "reparto razonable", "es razonable", "razonablemente", "dentro de la guía", "dentro del rango", "está perfecto", "dentro del ideal", "bien resuelta", "está en línea")


def nivel(frase):
    """'ok' | 'warn' | 'info' según la frase (para los iconos y colores de la pantalla)."""
    t = str(frase).lower()
    if t.startswith("en tu caso tenés"):
        return "info"
    if any(k in t for k in _OK):
        return "ok"
    if any(k in t for k in _WARN) and not t.startswith("para una persona"):
        return "warn"
    return "info"


def devolucion_html(secciones):
    out = []
    for titulo, frases in secciones:
        li = "".join(f'<li class="cr-n">{_negrita(html.escape(x))}</li>' if re.match(r"^\d+\. ", x) else f"<li>{_negrita(html.escape(x))}</li>" for x in frases)
        out.append(f'<div class="cr-s"><h4>{html.escape(titulo)}</h4><ul>{li}</ul></div>')
    return "".join(out)


def _negrita(t):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


CSS = """
.cr{font-family:inherit;color:#1f2937;margin:0}
.cr h1{font-size:1.5rem;margin:.2em 0 .3em}.cr .cr-i{color:#475569;font-size:.95rem;line-height:1.55;margin:0 0 .8em}
.cr-s{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);padding:12px 18px 8px;margin:0 0 12px}
.cr-s h4{margin:.2em 0 .4em;font-size:1rem;color:#1e3a8a}.cr-s ul{margin:0 0 .6em 1.1em;padding:0}.cr-s li{margin:0 0 .45em;line-height:1.55;font-size:.95rem;text-align:justify}
.cr-s li.cr-n{list-style:none;margin-left:-.4em}
.cr-av{background:#f8fafc;border:1px solid #e5e9f0;border-radius:12px;padding:10px 14px;color:#64748b;font-size:.82rem;line-height:1.5;margin-top:8px}
"""
