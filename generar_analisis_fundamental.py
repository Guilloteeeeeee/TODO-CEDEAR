"""
Herramientas del ANÁLISIS FUNDAMENTAL (solapa de cada empresa). Sin API y sin costo: las TABLAS las calcula el programa con los estados de Yahoo
(data/af_tablas.py) y el TEXTO (resumen, lectura de cada punto, tesis...) se redacta aparte y se guarda en data/analisis_fundamental.json.

Uso (desde la carpeta del proyecto):
    python generar_analisis_fundamental.py --bloque KO       muestra los datos de KO tal como los ve quien redacta (tablas incluidas)
    python generar_analisis_fundamental.py --prompt KO       prompt completo de KO (reglas + datos), listo para pegar en un chat de IA
    python generar_analisis_fundamental.py --agregar a.json  valida el/los archivo(s) JSON con el análisis ({"KO": {...}} o un análisis suelto con "ticker") y los suma a
                                                             data/analisis_fundamental.json (si algo no cumple el formato, lo dice y NO guarda ese)
    python generar_analisis_fundamental.py --estado          cuántas empresas tienen análisis y cuáles faltan
"""
import datetime
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import analisis_fundamental as AF  # noqa: E402
from data import fichas as fi  # noqa: E402
from data import paquetes_yahoo as py  # noqa: E402


def _foso():
    try:
        with open(os.path.join(AQUI, "data", "foso.json"), encoding="utf-8") as f:
            return (json.load(f) or {}).get("empresas") or {}
    except Exception:  # noqa: BLE001
        return {}


def _lista_empresas():
    """[(ticker, nombre, sector)] de las empresas de la app (las del caché)."""
    try:
        with open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8") as f:
            j = json.load(f)
        filas = j.get("data") or []
        if isinstance(filas, dict):
            filas = list(filas.values())
        return [(str(r.get("ticker")), str(r.get("nombre") or ""), str(r.get("sector") or "")) for r in filas if isinstance(r, dict) and r.get("ticker")]
    except Exception:  # noqa: BLE001
        return []


def armar(ticker, nombre="", sector="", paquetes=None, fichas=None, foso=None):
    paquetes = paquetes if paquetes is not None else py.cargar()[0]
    fichas = fichas if fichas is not None else fi.cargar()[0]
    foso = foso if foso is not None else _foso()
    f = fichas.get(ticker, {})
    p = paquetes.get(ticker) or {}
    fo = foso.get(ticker) or {}
    return AF.bloque_datos(ticker, nombre or ticker, f.get("sector_yahoo", ""), f.get("industria_yahoo", ""), f.get("pais", ""),
                           f.get("descripcion_es") or f.get("descripcion_en") or "", p.get("estados") or {}, fo.get("foso"), fo.get("etapa"),
                           extra={k: p.get(k) for k in ("dividendos", "gobierno", "agenda")}, sector_app=sector)


def perfil_de(ticker, paquetes=None, fichas=None, foso=None):
    """(perfil, capas) que el programa elige para la empresa (mismos datos que usa armar())."""
    sector_app = {t: s for t, _n, s in _lista_empresas()}.get(ticker, "")
    paquetes = paquetes if paquetes is not None else py.cargar()[0]
    fichas = fichas if fichas is not None else fi.cargar()[0]
    foso = foso if foso is not None else _foso()
    f, fo = fichas.get(ticker, {}), foso.get(ticker) or {}
    return AF.perfil_de(f.get("sector_yahoo", ""), f.get("industria_yahoo", ""), fo.get("etapa"), (paquetes.get(ticker) or {}).get("estados") or {}, fo.get("foso"), ticker, sector_app)


def agregar(archivos, modelo="Claude"):
    datos, _ = AF.cargar()
    paquetes = py.cargar()[0]
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    ok, mal = [], []
    for ruta in archivos:
        try:
            with open(ruta, encoding="utf-8") as f:
                j = json.load(f)
        except Exception as ex:  # noqa: BLE001
            mal.append(f"{ruta}: no se pudo leer ({type(ex).__name__})")
            continue
        items = j if all(isinstance(v, dict) for v in j.values()) and "resumen" not in j else {str(j.get("ticker", "")).upper(): j}
        for t, d in items.items():
            t = str(t).upper()
            res, problemas = AF.validar(d, (paquetes.get(t) or {}).get("estados") or {})
            if res is not None:
                res["perfil"], res["capas"] = perfil_de(t, paquetes)
                res["ticker"] = t
            if res is None:
                mal.append(f"{t} ({os.path.basename(ruta)}): " + "; ".join(problemas))
                continue
            res.update({"fecha": hoy, "modelo": modelo})
            datos[t] = res
            ok.append(t)
    if ok:
        AF.guardar(datos, hoy)
    print(f"Agregados: {', '.join(ok) or 'ninguno'}  (total guardados: {len(datos)})")
    for m in mal:
        print("  NO se guardó -> " + m)
    return not mal


def main(args):
    empresas = {t: (n, s) for t, n, s in _lista_empresas()}
    if len(args) >= 2 and args[0] in ("--bloque", "--prompt"):
        t = args[1].upper()
        b = armar(t, *(empresas.get(t) or ("", "")))
        print(b if args[0] == "--bloque" else AF.armar_prompt(b))
    elif args and args[0] == "--agregar" and len(args) >= 2:
        sys.exit(0 if agregar(args[1:]) else 1)
    elif args and args[0] == "--estado":
        datos, _ = AF.cargar()
        faltan = [t for t in empresas if t not in datos]
        print(f"Con análisis: {len(datos)} de {len(empresas)}. Faltan {len(faltan)}: {' '.join(faltan)}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
