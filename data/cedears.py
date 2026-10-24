"""
Datos de cada CEDEAR (v1.2.46): simbolo en BYMA y ratio de conversion, para la pagina de la empresa.

Se leen de data/cedears.csv (separador coma o punto y coma). Columnas:
    ticker    el mismo ticker de la tabla (por ejemplo AAPL, BRK-B)
    simbolo   el simbolo del CEDEAR en BYMA (casi siempre es el mismo; cambian BAC -> BA.C, BBVA -> BBV, BNY -> BK, BRK-B -> BRKB,
              DIS -> DISN y MRSH -> MMC). Con ".BA" al final es el simbolo que usa Yahoo Finance para el precio en pesos.
    ratio     cuantos CEDEARs equivalen a una accion: "20" o "20:1" (si es al reves, "1:4": un CEDEAR equivale a 4 acciones)
Fuente de los ratios: tabla oficial de BYMA, tal como la publica Rankia (actualizada el 20/10/2026; BYMA la actualizo en septiembre de 2026).
No se inventa ningun dato: si una empresa no esta en el archivo, la pagina muestra "—". Los ratios cambian con splits y programas nuevos:
conviene revisarlos cada tanto (probar_cedears.bat compara el dolar que implica cada CEDEAR y marca los que no cierran).
"""
import csv
import os

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cedears.csv")


def _numero(txt):
    try:
        t = str(txt).strip().replace(" ", "")
        if not t:
            return None
        if "," in t and "." in t:                 # 1.234,56 (formato argentino)
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", ".")
        v = float(t)
        return v if v == v and v > 0 else None
    except (TypeError, ValueError):
        return None


def leer_ratio(txt):
    """'20', '20:1' -> 20.0 ; '1:4' -> 0.25 ; vacio o roto -> None."""
    t = str(txt or "").strip()
    if ":" in t:
        a, _, b = t.partition(":")
        x, y = _numero(a), _numero(b)
        return (x / y) if x and y else None
    return _numero(t)


def ratio_texto(ratio):
    """20.0 -> '20 : 1' ; 0.25 -> '1 : 4' ; None -> '—'."""
    if not ratio or ratio <= 0:
        return "—"
    if ratio >= 1:
        n = int(ratio) if abs(ratio - round(ratio)) < 1e-9 else round(ratio, 2)
        return f"{n} : 1"
    inv = 1 / ratio
    n = int(round(inv)) if abs(inv - round(inv)) < 1e-6 else round(inv, 2)
    return f"1 : {n}"


def cargar(archivo=None):
    """{TICKER: {'simbolo': str, 'ratio': float|None}}. Archivo ausente o roto -> {} (nunca rompe la pagina)."""
    ruta = archivo or ARCHIVO
    if not os.path.exists(ruta):
        return {}
    out = {}
    try:
        with open(ruta, newline="", encoding="utf-8-sig") as f:
            muestra = f.read(2048)
            f.seek(0)
            delim = ";" if muestra.count(";") > muestra.count(",") else ","
            for fila in csv.DictReader(f, delimiter=delim):
                fila = {str(k or "").strip().lower(): (v or "").strip() for k, v in fila.items()}
                t = fila.get("ticker", "").upper()
                if not t:
                    continue
                out[t] = {"simbolo": (fila.get("simbolo") or t.replace("-", "")).upper(), "ratio": leer_ratio(fila.get("ratio"))}
    except Exception:  # noqa: BLE001
        return {}
    return out


def simbolos_yahoo(datos):
    """{TICKER: [simbolos de Yahoo a probar]}: el simbolo de BYMA con ".BA" y, si tiene punto (BA.C), tambien sin punto (BAC.BA)."""
    out = {}
    for t, d in (datos or {}).items():
        s = d.get("simbolo") or t
        c = [f"{s}.BA"]
        if "." in s:
            c.append(f"{s.replace('.', '')}.BA")
        out[t] = c
    return out
