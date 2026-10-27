"""ETFs (v1.2.64): la tabla sale de data/etfs.csv, que Guille va armando de a poco (hoy: PDF "Ideas de Inversion - Especial ETFs, Agosto-Septiembre 2026"
y los 5 nuevos CEDEARs de ETF). Se edita con Excel o con el Bloc de notas: una fila por ETF, separada con ";" (tambien se lee con ",").
Columnas: ticker; nombre (completo); gestor (empresa que lo administra); mercado (donde cotiza; si esta vacio se usa el de Yahoo); icono (un emoji, o
"svg:bitcoin" / "svg:ethereum"); categoria; descripcion; acceso (CEDEAR o "Solo por mesa del broker"); nuevo (Si, opcional); etiqueta (opcional);
perfil (ya no se muestra; se guarda por las dudas); distribucion (vacio = se deduce de los dividendos de Yahoo; o "Acumulacion" / "Distribucion");
ratio (del CEDEAR, ej. 20 = 20 CEDEARs por 1 cuota; vacio = sin confirmar); simbolo (el de BYMA, si es distinto del ticker); web (sitio oficial del ETF,
si se conoce); yahoo (simbolo de Yahoo si es distinto del ticker, ej. IWDA.L); pais (solo si el indice es de un unico pais, ej. Japon: la torta
de paises sale de ahi).
v1.2.67: icono pasa a ser "svg:<nombre>" (ver ui/etf_iconos.py: dibujos propios y banderas), ya no emojis."""
import csv
import io
import os
import re
import unicodedata

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etfs.csv")
CAMPOS = ("ticker", "nombre", "gestor", "mercado", "icono", "categoria", "descripcion", "acceso", "nuevo", "etiqueta", "perfil", "distribucion", "ratio", "simbolo", "web", "yahoo", "pais")


def norm(s):
    """Minusculas, sin tildes ni signos: 'Petróleo' -> 'petroleo'."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def cargar(ruta=None):
    """Lista de ETFs (diccionarios con CAMPOS) en el orden del archivo. [] si el archivo no esta o no se puede leer. Ignora filas sin ticker."""
    try:
        with open(ruta or RUTA, encoding="utf-8-sig", newline="") as f:
            texto = f.read()
    except Exception:  # noqa: BLE001
        return []
    primera = texto.split("\n", 1)[0]
    sep = ";" if primera.count(";") >= primera.count(",") else ","
    out, vistos = [], set()
    for fila in csv.DictReader(io.StringIO(texto), delimiter=sep):
        d = {k: str(fila.get(k) or "").strip() for k in CAMPOS}
        t = d["ticker"].upper()
        if not t or t in vistos:
            continue
        vistos.add(t)
        d["ticker"] = t
        out.append(d)
    return out


def categorias(etfs):
    """Categorias en el orden en que aparecen."""
    return list(dict.fromkeys(e["categoria"] for e in etfs if e["categoria"]))


def por_ticker(etfs, ticker):
    t = str(ticker or "").strip().upper()
    return next((e for e in etfs if e["ticker"] == t), None)


def simbolo_yahoo(e):
    return (e.get("yahoo") or e["ticker"]).strip()


def filtrar(etfs, texto="", cats=()):
    """ETFs que coinciden con lo escrito (ticker, nombre, gestor, descripcion, categoria o etiqueta; sin importar mayusculas ni tildes; todas las
    palabras escritas tienen que estar) y con las categorias elegidas (ninguna = todas)."""
    palabras = norm(texto).split()
    out = []
    for e in etfs:
        if cats and e["categoria"] not in cats:
            continue
        pajar = norm(" ".join((e["ticker"], e["nombre"], e["gestor"], e["descripcion"], e["categoria"], e["etiqueta"])))
        if all(p in pajar for p in palabras):
            out.append(e)
    return out
