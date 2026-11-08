"""
v1.5.48: ARRANQUE del archivo histórico (data/historico/) con todo lo que ya teníamos al 08/11/2026. Se corre una vez (se puede repetir: no duplica nada).

Reconstruye desde el historial de GitHub (cada versión subida de los archivos de datos):
- estados.json: todas las versiones de data/paquetes_yahoo.json, en orden, con su fecha (así queda anotado cuándo se capturó cada año);
- fotos/AAAA-MM.json: la última versión de cada mes de cache_datos.json, etfs_yahoo.json y fichas.json (+ la calidad del Análisis Fundamental);
- informes/: cada versión de cada informe que pasó por data/analisis_fundamental.json;
- multiplos_anuales.json: data/multiplos_anuales.json, si está.
Los precios mensuales, dividendos y splits de toda la historia los baja bajar_historico.bat en la PC (Yahoo no responde desde la nube).

Uso: python arrancar_historico.py
"""
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from data import historico as H  # noqa: E402


def _git(*args):
    return subprocess.run(["git", *args], cwd=AQUI, capture_output=True, text=True, check=False).stdout


def versiones(ruta):
    """[(commit, fecha AAAA-MM-DD)] de un archivo, de la más vieja a la más nueva."""
    out = _git("log", "--format=%H %ad", "--date=short", "--", ruta)
    return [tuple(x.split()) for x in reversed(out.strip().splitlines()) if x.strip()]


def contenido(commit, ruta):
    try:
        return json.loads(_git("show", f"{commit}:{ruta}"))
    except ValueError:
        return None


def ultima_por_mes(ruta):
    meses = {}
    for c, f in versiones(ruta):
        meses[f[:7]] = (c, f)
    return meses


def main():
    os.makedirs(H.CARPETA, exist_ok=True)
    # 1) estados: todas las versiones, en orden
    arch, cambios = {}, H.leer("cambios.json", [])
    vs = versiones("data/paquetes_yahoo.json")
    for c, f in vs:
        d = contenido(c, "data/paquetes_yahoo.json") or {}
        for tk, paq in (d.get("datos") or {}).items():
            if (paq or {}).get("estados"):
                arch[tk.upper()] = H.fusionar_estados(arch.get(tk.upper()), paq["estados"], tk.upper(), cambios, hoy=f)
    previo = H.leer("estados.json", {})
    for tk, reg in previo.items():      # si ya había un archivo, se respeta lo que tenga de más
        if tk not in arch:
            arch[tk] = reg
    H.escribir("estados.json", dict(sorted(arch.items())))
    H.escribir("cambios.json", cambios)
    print(f"Estados: {len(arch)} empresas, {sum(len(r.get('anios') or {}) for r in arch.values())} años fiscales ({len(vs)} versiones leídas)")

    # 2) fotos mensuales
    af_mes = ultima_por_mes("data/analisis_fundamental.json")
    for ruta, sec, campos in (("data/cache_datos.json", "empresas", H.CAMPOS_FOTO_EMPRESA), ("data/etfs_yahoo.json", "etfs", H.CAMPOS_FOTO_ETF),
                              ("data/fichas.json", "fichas", H.CAMPOS_FOTO_FICHA)):
        for mes, (c, f) in ultima_por_mes(ruta).items():
            d = contenido(c, ruta) or {}
            filas = {r["ticker"]: r for r in d.get("data", [])} if sec == "empresas" else (d.get("datos") or {})
            extra = None
            if sec == "empresas" and mes in af_mes:
                af = (contenido(af_mes[mes][0], "data/analisis_fundamental.json") or {}).get("datos") or {}
                extra = {t: {"calidad_af": a.get("calidad"), "fecha_af": a.get("fecha")} for t, a in af.items() if isinstance(a, dict) and a.get("calidad")}
            n = H.foto_mensual(sec, filas, campos, mes=mes, fecha=f, extra=extra)
            print(f"Foto {mes} · {sec}: {n} (versión del {f})")

    # 3) informes: cada versión que pasó por el archivo
    n = 0
    for c, f in versiones("data/analisis_fundamental.json"):
        d = (contenido(c, "data/analisis_fundamental.json") or {}).get("datos") or {}
        for tk, inf in d.items():
            if H.archivar_informe(tk, inf):
                n += 1
    print(f"Informes: {n} versiones nuevas guardadas (total {len(H.informes_guardados())})")

    # 4) múltiplos por año
    try:
        with open(os.path.join(AQUI, "data", "multiplos_anuales.json"), encoding="utf-8") as fh:
            ma = json.load(fh).get("datos") or {}
        print(f"Múltiplos por año: {H.archivar_multiplos(ma)} empresas")
    except OSError:
        print("Múltiplos por año: todavía no hay data/multiplos_anuales.json (se suma solo cuando corras bajar_multiplos_anuales.bat)")
    print("\nResumen:", json.dumps(H.resumen(), ensure_ascii=False))


if __name__ == "__main__":
    main()
