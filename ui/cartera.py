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
    return {"ticker": it, "monto": montos, "tipo": _buscar(n, _K_TIPO, usados=(it,)), "cantidad": ic, "precio": ip,
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
        c = {"ticker": 0, "monto": [(im, None)], "tipo": next((j for j in range(1, ancho) if j != im and not _es_numerica(j, filas)), None), "cantidad": None, "precio": None,
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
        out.append({"ticker": _ticker_limpio(tk), "monto": m, "tipo": tipo, "moneda": mo})
    # una empresa con varias compras (lotes) es UNA posicion: se suman
    agr, orden = {}, []
    for p in out:
        k = (clave_tk(p["ticker"]) or p["ticker"].upper(), p["moneda"])
        if k in agr:
            agr[k]["monto"] += p["monto"]
            agr[k]["tipo"] = agr[k]["tipo"] or p["tipo"]
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



def rentabilidad_anual(aportado, final, anios):
    """Rentabilidad anualizada ESTIMADA de una cartera cuando no se conocen las fechas exactas de los aportes.
    Devuelve {'total': ganancia % sobre lo aportado, 'anual_inicio': anual si todo se aportó al principio, 'anual_parejo': anual si se aportó en cuotas iguales, una por mes}.
    Si se aportó de a poco, el dinero estuvo menos tiempo invertido y la tasa verdadera es mayor que la de 'todo al principio' (cuando hubo ganancia): por eso se muestran las dos.
    None si los datos no sirven (aportes o capital <= 0, o menos de un mes)."""
    try:
        a, f, y = float(aportado), float(final), float(anios)
    except (TypeError, ValueError):
        return None
    if a <= 0 or f <= 0 or y < 1 / 12:
        return None
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


def plantilla_excel():
    """Bytes de un .xlsx de ejemplo (Ticker, Monto, Tipo)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Cartera"
    ws.append(["Ticker", "Monto", "Moneda (opcional)", "Tipo (opcional)"])
    for r in (("AAPL", 1500, "USD", ""), ("KO", 800, "USD", ""), ("SPY", 3000, "USD", ""), ("AL30", 2000000, "ARS", "Renta fija soberana"), ("ON YPF", 1000, "USD", "Renta fija corporativa"),
              ("GLD", 500, "USD", "Oro"), ("BTC", 300, "USD", "Cripto"), ("Caución", 500000, "ARS", "Efectivo")):
        ws.append(list(r))
    ws.append([])
    ws.append(["Monto: el valor actual de cada tenencia. Moneda: USD o ARS (si la dejás vacía se usa la que elijas en la página); todo se pasa a dólares automáticamente con el dólar CCL. "
               "Tipo: solo hace falta para lo que no es una empresa o ETF de la lista (bonos, obligaciones negociables, fondos, efectivo)."])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 26
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
    return "usa" if p in _USA else "emergentes" if p in _EMERGENTES else "desarrollados" if p else None


def valoracion(categoria):
    c = str(categoria or "").upper()
    return "infravalorada" if "INFRAVALORADA" in c else "sobrevalorada" if "SOBREVALORADA" in c else "bien valuada" if "BIEN VALUADA" in c else None


# --- analisis ---------------------------------------------------------------------------------------------------------------------

PESO_MIN, PESO_MAX = 2.0, 5.0      # ideal de diversificación (no es una regla obligatoria): cada empresa (acción o CEDEAR) entre 2 % y 5 % de la cartera; los ETFs no entran
UMBRAL = 5.0          # puntos de diferencia a partir de los cuales se avisa (la devolución es una orientación, no un cálculo fino)
_CAT_ETF_GEO = {"usa": "usa", "usa segun sectores": "usa", "internacionales no usa": "fuera_sd", "internacionales con usa": "global"}


def _geo_de(p, etfs):
    """Bucket geográfico de una posición de renta variable: 'usa' | 'desarrollados' | 'emergentes' | 'fuera_sd' (fuera de EE.UU., sin detalle) | 'global' (mezcla) | None."""
    if p["fuente"] == "empresa":
        return region(p["info"].get("pais"))
    if p["fuente"] == "etf":
        e = etfs.get(clave_tk(p["ticker"])) or {}
        return region(e.get("pais")) if e.get("pais") else _CAT_ETF_GEO.get(norm(e.get("categoria")))
    return None


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
    for p in rv:
        g = _geo_de(p, etfs)
        if g:
            geo[g] += p["monto"]
    geo_tot = sum(geo.values())
    sup = {"ciclico": 0.0, "sensible": 0.0, "defensivo": 0.0}
    sect = {}
    for p in emp:
        s = p["info"].get("sector")
        if SUPERSECTOR_DE.get(s):
            sup[SUPERSECTOR_DE[s]] += p["monto"]
            sect[s] = sect.get(s, 0.0) + p["monto"]
    st_ = sum(sup.values())
    por_pos = sorted(ok, key=lambda p: -p["monto"])
    return {
        "rango": nombre_rango, "efectivo_propio": sep_efectivo, "liquidez": liq, "total": total, "peso": peso, "desvio": desvio, "rv_total": rv_total, "n_empresas": len(emp),
        "geo": ({k: v / rv_total * 100 for k, v in geo.items()} if rv_total and geo_tot else None), "geo_ubicado_pct": (geo_tot / rv_total * 100) if rv_total else 0.0,
        "super": {k: v / st_ * 100 for k, v in sup.items()} if st_ else None, "sector_ubicado_pct": (st_ / rv_total * 100) if rv_total else 0.0,
        "sectores": sorted(((k, v / st_ * 100) for k, v in sect.items()), key=lambda kv: -kv[1]) if st_ else [],
        "sector_top": (max(sect.items(), key=lambda kv: kv[1])[0], max(sect.values()) / st_ * 100) if sect and st_ else None,
        "posiciones": [{"ticker": p["ticker"], "pct": p["monto"] / total * 100, "clase": p["clase"], "fuente": p.get("fuente")} for p in por_pos],
        "sin_clasificar": sin, "pct_sin_clasificar": (sum(p["monto"] for p in sin) / (total + sum(p["monto"] for p in sin)) * 100) if sin else 0.0,
    }


def _pts(x):
    return f"{abs(x):.0f}"


LIQ_MIN, LIQ_MAX = 10.0, 15.0      # v1.2.85 (regla de Guille): una liquidez de 10 a 15 % de la cartera está muy bien tolerada
_NOMBRE_CLASE = {"rv": "renta variable", "oro": "oro", "cripto": "criptoactivos", "efectivo": "liquidez (cuentas remuneradas y cauciones)"}


def devolucion(res, edad, perfil):
    """[(titulo, [frases])] con la evaluación en 4 bloques (pesos, diversificación geográfica, diversificación sectorial, conclusiones y qué ajustaría), en castellano simple.
    Sin recomendaciones de compra o venta de activos puntuales y SIN las carteras de referencia."""
    sec = []
    if not res or not res.get("total"):
        return sec
    pe, d = res["peso"], res["desvio"]
    ef = res.get("efectivo_propio")
    nombres = dict(_NOMBRE_CLASE, rf="renta fija")
    claves = ("rv", "rf", "efectivo", "oro", "cripto") if ef else ("rv", "rf", "oro", "cripto")
    ajustes, hallazgos = [], []          # lo que alimenta el cuarto bloque
    # ---------------- 1. Pesos
    comp = [f"{CLASES[k]} {pe[k]:.0f} %" for k in ("rv", "rf", "oro", "cripto", "efectivo", "otros") if pe[k] >= 0.5]
    perf = f", perfil {perfil.lower()}" if perfil and any(len(c[3]) > 1 for c in CM.RANGOS if c[0] <= int(edad) <= c[1]) else ""
    f = [f"Para una persona de {int(edad)} años{perf}, tu cartera está repartida así: " + ", ".join(comp) + "."]
    pasa = sorted((k for k in claves if d[k] > UMBRAL), key=lambda k: -d[k])
    falta = sorted((k for k in claves if d[k] < -UMBRAL), key=lambda k: d[k])
    for k in pasa:
        f.append(f"**{nombres[k].capitalize()}: te pasás unos {_pts(d[k])} puntos** respecto de lo que suele ser razonable para tu edad y tu perfil.")
    for k in falta:
        f.append(f"**{nombres[k].capitalize()}: te faltan unos {_pts(d[k])} puntos** respecto de lo que suele ser razonable para tu edad y tu perfil.")
    if not pasa and not falta:
        f.append("**En los grandes grupos (renta variable, renta fija, oro y criptoactivos) estás en línea** con lo que suele ser razonable para tu edad y tu perfil.")
        hallazgos.append("Los pesos por tipo de activo están en línea con tu edad y tu perfil.")
    else:
        hallazgos.append("Pesos: " + "; ".join([f"te pasás en {nombres[k]}" for k in pasa] + [f"te falta {nombres[k]}" for k in falta]) + ".")
        if pasa and falta:
            ajustes.append(f"Mover peso de **{nombres[pasa[0]]}** hacia **{nombres[falta[0]]}**, de a poco y por partes (así no se decide todo en un mismo día).")
        elif pasa:
            dest = min((k for k in claves if k != pasa[0]), key=lambda k: d[k])
            ajustes.append(f"Bajar el peso de **{nombres[pasa[0]]}** y mandar esa parte a **{nombres[dest]}**.")
        else:
            orig = max((k for k in claves if k != falta[0]), key=lambda k: d[k])
            ajustes.append(f"Subir de a poco el peso de **{nombres[falta[0]]}**, con lo que se libere de **{nombres[orig]}**.")
    if pe["cripto"] > 10:
        f.append("Los criptoactivos son muy volátiles: con más de un 10 % de la cartera, una caída fuerte se siente mucho en el total.")
    liq = pe["efectivo"]
    if not ef and liq >= 0.5:
        if liq > LIQ_MAX:
            f.append(f"**Liquidez: tenés {liq:.0f} %, te pasás unos {liq - LIQ_MAX:.0f} puntos del 15 %.** La liquidez (efectivo, cuentas remuneradas, cauciones) es seguridad, pero sin rendimiento propio; "
                     f"una liquidez de {LIQ_MIN:.0f} a {LIQ_MAX:.0f} % está muy bien tolerada y conviene que lo de más sea una decisión y no un descuido.")
            hallazgos.append(f"Liquidez alta ({liq:.0f} %).")
            ajustes.append(f"Llevar la liquidez de a poco hacia el rango de {LIQ_MIN:.0f} a {LIQ_MAX:.0f} %, repartiendo el excedente entre los grupos donde te faltan puntos.")
        elif liq >= LIQ_MIN:
            f.append(f"**Liquidez: tenés {liq:.0f} %, dentro del rango de {LIQ_MIN:.0f} a {LIQ_MAX:.0f} %** que está muy bien tolerado (te da margen para imprevistos y oportunidades).")
        else:
            f.append(f"Liquidez: tenés {liq:.0f} %. Una liquidez de {LIQ_MIN:.0f} a {LIQ_MAX:.0f} % de la cartera está muy bien tolerada: te da margen para imprevistos y oportunidades, sin dejar demasiado plata quieta.")
    if pe["otros"] >= 5:
        f.append(f"Tenés {pe['otros']:.0f} % en otras materias primas (petróleo, granos…): no son ni renta fija ni variable típica y no las comparé con tu edad y perfil.")
    ps = res["posiciones"]
    # v1.2.79 (regla de Guille): cada empresa (acción o CEDEAR) debería pesar entre 3 % y 5 % de la cartera. ETFs, bonos, fondos, oro y efectivo no entran en esta regla.
    emp_ps = [p for p in ps if p.get("clase") == "rv" and p.get("fuente") in ("empresa", "regla")]
    arriba = [p for p in emp_ps if p["pct"] > PESO_MAX + 0.05]
    abajo = [p for p in emp_ps if p["pct"] < PESO_MIN - 0.05]
    en_rango = len(emp_ps) - len(arriba) - len(abajo)
    if emp_ps:
        def _lista_tk(lst, n=4):
            t = ", ".join(f"{p['ticker']} {p['pct']:.0f} %" for p in lst[:n])
            return t + (f" y {len(lst) - n} más" if len(lst) > n else "")
        if arriba:
            f.append(f"**Como ideal de diversificación, cada empresa suele pesar entre {PESO_MIN:.0f} y {PESO_MAX:.0f} % de la cartera** (es una guía, no una obligación). Pasan de {PESO_MAX:.0f} %: {_lista_tk(arriba)}.")
            hallazgos.append(f"{len(arriba)} empresa(s) pasan de {PESO_MAX:.0f} % de la cartera.")
            ajustes.append(f"Si querés diversificar más, ir llevando de a poco las empresas que pasan de {PESO_MAX:.0f} % ({', '.join(p['ticker'] for p in arriba[:3])}{'…' if len(arriba) > 3 else ''}) hacia el rango de {PESO_MIN:.0f} a {PESO_MAX:.0f} %.")
        if len(abajo) >= 2:
            f.append(f"Pesan menos de {PESO_MIN:.0f} % (casi no mueven el resultado de tu cartera): {_lista_tk(abajo)}.")
            hallazgos.append(f"{len(abajo)} empresas pesan menos de {PESO_MIN:.0f} %.")
            ajustes.append(f"Las empresas que pesan menos de {PESO_MIN:.0f} % casi no mueven tu cartera: es una decisión tuya si las subís hacia el rango de {PESO_MIN:.0f} a {PESO_MAX:.0f} % o las dejás como están.")
        if not arriba and len(abajo) < 2:
            f.append(f"**Las empresas están dentro del ideal de diversificación** ({PESO_MIN:.0f} a {PESO_MAX:.0f} % de la cartera cada una): {en_rango} de {len(emp_ps)}.")
    if ps and ps[0]["pct"] > 15 and ps[0].get("clase") == "rv" and ps[0].get("fuente") in ("empresa", "regla"):
        f.append(f"**Tu mayor posición, {ps[0]['ticker']}, pesa {ps[0]['pct']:.0f} %** de la cartera: si le va mal, se nota mucho en el total.")
    top3 = sum(p["pct"] for p in ps[:3])
    if len(ps) >= 4 and top3 > 50:
        f.append(f"Tus 3 posiciones más grandes suman {top3:.0f} %: la cartera depende de pocas ideas.")
    if len(ps) < 5:
        f.append(f"Tenés {len(ps)} posiciones: con tan pocas, cada una pesa mucho.")
        hallazgos.append(f"Pocas posiciones ({len(ps)}).")
    if res["sin_clasificar"]:
        n_ = ", ".join(dict.fromkeys(str(p["ticker"]) for p in res["sin_clasificar"]))
        f.append(f"No pude ubicar: {n_} ({res['pct_sin_clasificar']:.0f} % del total). Quedaron afuera del cálculo; si son bonos, obligaciones negociables, fondos o efectivo, completá la columna **Tipo** del Excel.")
    sec.append(("Pesos", f))
    # ---------------- 2. Diversificación geográfica
    g = res.get("geo")
    f = []
    if pe["rv"] < 1:
        f.append("No tenés renta variable, así que no hay geografía de acciones para evaluar.")
    elif not g:
        f.append("No pude ubicar por país ninguna de tus posiciones de renta variable (hace falta que sean empresas de la lista de TodoCedears o ETFs de la lista).")
    else:
        ub = res["geo_ubicado_pct"]
        partes = [(k, t) for k, t in (("usa", "Estados Unidos"), ("desarrollados", "otros países desarrollados"), ("emergentes", "emergentes"),
                                      ("fuera_sd", "internacional fuera de EE.UU. (sin detalle)"), ("global", "global (mezcla)")) if g[k] >= 0.5]
        f.append("Sobre tu renta variable, esto es lo que pude ubicar por país: " + ", ".join(f"{t} {g[k]:.0f} %" for k, t in partes) + f" (sin ubicar: {100 - ub:.0f} %).")
        base = g["usa"] + g["desarrollados"] + g["emergentes"] + g["fuera_sd"]
        if base > 0:
            usa, emer = g["usa"] / base * 100, g["emergentes"] / base * 100
            if usa > CM.GEOGRAFIA["usa"] + 12:
                f.append(f"**Muy concentrada en Estados Unidos ({usa:.0f} %).** Es el mercado más grande, pero todo depende de una sola economía y de una sola moneda.")
                hallazgos.append("Geografía muy concentrada en Estados Unidos.")
                ajustes.append("Sumar otros países desarrollados (Europa, Japón, Canadá) y, en menor medida, emergentes, para depender menos de Estados Unidos.")
            elif usa < CM.GEOGRAFIA["usa"] - 25:
                f.append(f"**Poco Estados Unidos ({usa:.0f} %)**, el mercado más grande y profundo: revisá si es una decisión tuya.")
                hallazgos.append("Poco peso en Estados Unidos.")
            else:
                f.append(f"**Reparto razonable:** Estados Unidos {usa:.0f} % de lo ubicado, sin una concentración excesiva.")
                hallazgos.append("Geografía razonablemente repartida.")
            if emer > CM.GEOGRAFIA["emergentes"] + 12:
                f.append(f"**Los emergentes pesan {emer:.0f} %** de lo ubicado: más riesgo y más volatilidad que lo habitual.")
                hallazgos.append("Mucho peso en mercados emergentes.")
                ajustes.append("Bajar el peso de los mercados emergentes hacia desarrollados.")
        if ub < 60:
            f.append("Ojo: menos de 60 % de tu renta variable pudo ubicarse por país, así que esta lectura es parcial.")
    sec.append(("Diversificación geográfica", f))
    # ---------------- 3. Diversificación sectorial
    f = []
    s = res.get("super")
    if pe["rv"] < 1:
        f.append("No tenés renta variable, así que no hay sectores de acciones para evaluar.")
    elif not s:
        f.append("No pude ubicar por sector ninguna posición (hace falta que sean empresas de la lista de TodoCedears; los ETFs no se abren por dentro).")
    else:
        f.append(f"Sobre las empresas que pude ubicar ({res['sector_ubicado_pct']:.0f} % de tu renta variable): **{s['defensivo']:.0f} % defensivas** (consumo básico, salud, servicios públicos), "
                 f"**{s['sensible']:.0f} % sensibles** (tecnología, industria, energía, comunicación) y **{s['ciclico']:.0f} % cíclicas** (bancos y seguros, consumo discrecional, materiales, inmobiliarias).")
        if s["defensivo"] < CM.SUPERSECTOR["defensivo"] - 20:
            f.append("Hay poco de lo defensivo, que es lo que mejor aguanta cuando la economía se enfría: la cartera depende bastante del ciclo económico.")
            hallazgos.append("Poco peso en sectores defensivos.")
            ajustes.append("Sumar empresas defensivas (consumo básico, salud, servicios públicos) para equilibrar el ciclo.")
        elif s["defensivo"] > CM.SUPERSECTOR["defensivo"] + 20:
            f.append("Hay mucho de lo defensivo: aguanta bien las caídas, pero puede quedarse atrás cuando el mercado sube con fuerza.")
            hallazgos.append("Mucho peso en sectores defensivos.")
        else:
            f.append("El equilibrio entre defensivas, sensibles y cíclicas es razonable.")
            hallazgos.append("Equilibrio sectorial razonable.")
        if res["sector_top"] and res["sector_top"][1] > 40:
            f.append(f"**Un solo sector pesa demasiado:** {res['sector_top'][0]} es el {res['sector_top'][1]:.0f} % de tus empresas.")
            hallazgos.append(f"{res['sector_top'][0]} concentra {res['sector_top'][1]:.0f} % de las empresas.")
            ajustes.append(f"Repartir el peso de {res['sector_top'][0]} en otros sectores.")
    sec.append(("Diversificación sectorial", f))
    # ---------------- 4. Conclusiones y qué ajustaría
    f = ["**Conclusión:** " + (" ".join(hallazgos) if hallazgos else "no encontré desvíos importantes.")]
    if ajustes:
        f.append("**Qué ajustaría, en este orden:**")
        f += [f"{n}. {a}" for n, a in enumerate(ajustes, 1)]
    else:
        f.append("**Qué ajustaría:** por ahora nada importante; revisala una o dos veces al año para que los pesos no se vayan corriendo.")
    sec.append(("Conclusiones y qué ajustaría", f))
    return sec


_WARN = ("pasan de", "pesan menos de", "te pasás", "te faltan", "muy concentrada", "poco estados", "los emergentes pesan", "hay poco", "hay mucho", "un solo sector", "tu mayor posición", "posiciones más grandes",
         "tenés ", "no pude ubicar", "ojo:", "volátiles", "no tenés renta variable", "no pude ubicar por")
_OK = ("están dentro de lo habitual", "estás en línea", "reparto razonable", "es razonable", "razonablemente")


def nivel(frase):
    """'ok' | 'warn' | 'info' según la frase (para los iconos y colores de la pantalla)."""
    t = str(frase).lower()
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
