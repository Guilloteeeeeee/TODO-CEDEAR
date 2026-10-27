"""
Genera el ANÁLISIS FUNDAMENTAL automático de las empresas (Resumen, Desarrollo y tesis de inversión, Conclusión) y lo guarda en data/analisis_fundamental.json,
que es lo que muestra la solapa "Análisis Fundamental" de cada empresa.

Qué hace, empresa por empresa:
  1. Arma el bloque de datos con los estados financieros que bajó bajar_paquetes_yahoo.py (último año móvil + 4 años fiscales), la descripción del negocio (data/fichas.json)
     y el foso / etapa (data/foso.json). Las cifras, ratios y variaciones las calcula el código, no el modelo.
  2. Lo manda junto con data/prompt_analisis_fundamental.txt a la API de Claude y guarda la respuesta.

Hace falta una clave de la API de Anthropic (https://console.anthropic.com): se pone en la variable de entorno ANTHROPIC_API_KEY (el .bat la pide si no está).
El modelo se cambia con la variable AF_MODELO (por defecto el de abajo). Se paga por uso: al final el programa muestra cuántos tokens gastó.

Uso (desde la carpeta del proyecto):
    python generar_analisis_fundamental.py                 (solo las empresas que todavía no tienen análisis)
    python generar_analisis_fundamental.py KO MSFT         (solo esas, aunque ya tengan: las pisa)
    python generar_analisis_fundamental.py --todas         (rehace todas)
    python generar_analisis_fundamental.py --bloque KO     (muestra el bloque de datos de KO y NO llama a la API: sirve para revisar qué ve el modelo)
    python generar_analisis_fundamental.py --prompt KO     (muestra el prompt completo de KO, listo para pegarlo en un chat si no querés usar la API)

Se guarda de a poco. Si la API falla 3 veces seguidas se corta y lo dice; lo ya hecho queda guardado.
"""
import datetime
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import analisis_fundamental as AF  # noqa: E402
from data import fichas as fi  # noqa: E402
from data import paquetes_yahoo as py  # noqa: E402

MODELO = os.environ.get("AF_MODELO", "claude-sonnet-5-5")
MAX_TOKENS = 5000
PAUSA_S = 1.0


def _foso():
    try:
        with open(os.path.join(AQUI, "data", "foso.json"), encoding="utf-8") as f:
            return (json.load(f) or {}).get("empresas") or {}
    except Exception:  # noqa: BLE001
        return {}


def _lista_empresas():
    """[(ticker, nombre, sector)] de las empresas de la app (las del caché)."""
    try:
        from data.fetcher import load_cache  # noqa: F401
    except Exception:  # noqa: BLE001
        pass
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
    e = (paquetes.get(ticker) or {}).get("estados") or {}
    fo = foso.get(ticker) or {}
    return AF.bloque_datos(ticker, nombre or ticker, sector or f.get("sector_yahoo", ""), f.get("industria_yahoo", ""), f.get("pais", ""),
                           f.get("descripcion_es") or f.get("descripcion_en") or "", e, fo.get("foso"), fo.get("etapa"))


def _llamar(cliente, prompt):
    r = cliente.messages.create(model=MODELO, max_tokens=MAX_TOKENS, messages=[{"role": "user", "content": prompt}])
    texto = "".join(getattr(b, "text", "") for b in r.content)
    u = getattr(r, "usage", None)
    return texto, (getattr(u, "input_tokens", 0) or 0), (getattr(u, "output_tokens", 0) or 0)


def main(args):
    empresas = {t: (n, s) for t, n, s in _lista_empresas()}
    if len(args) >= 2 and args[0] in ("--bloque", "--prompt"):
        t = args[1].upper()
        b = armar(t, *(empresas.get(t) or ("", "")))
        print(b if args[0] == "--bloque" else AF.armar_prompt(b))
        return
    todas = "--todas" in args
    pedidas = [a.upper() for a in args if not a.startswith("--")]
    datos, _ = AF.cargar()
    objetivo = pedidas or [t for t in empresas if todas or t not in datos]
    if not objetivo:
        print("Todas las empresas ya tienen análisis. Usá --todas para rehacerlas.")
        return
    clave = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not clave:
        print("Falta la clave de la API: poné la variable de entorno ANTHROPIC_API_KEY (se saca en https://console.anthropic.com).")
        return
    try:
        import anthropic
    except ImportError:
        print("Falta el paquete 'anthropic': pip install anthropic")
        return
    cliente = anthropic.Anthropic(api_key=clave)
    paquetes, fichas, foso = py.cargar()[0], fi.cargar()[0], _foso()
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    avisos, fallos_seguidos, t_in, t_out = [], 0, 0, 0
    print(f"Generando el análisis de {len(objetivo)} empresa(s) con el modelo {MODELO} (una por una; no cierres la ventana)...")
    for i, t in enumerate(objetivo, 1):
        nombre, sector = empresas.get(t) or ("", "")
        if not (paquetes.get(t) or {}).get("estados"):
            avisos.append(f"{t}: sin estados financieros guardados (se hizo igual, solo cualitativo)")
        prompt = AF.armar_prompt(armar(t, nombre, sector, paquetes, fichas, foso))
        res = None
        for intento in range(3):
            try:
                texto, ti, to = _llamar(cliente, prompt)
                t_in += ti
                t_out += to
                res = AF.parsear_respuesta(texto)
                if res:
                    break
                avisos.append(f"{t}: la respuesta no tenía el formato pedido (intento {intento + 1})")
            except Exception as ex:  # noqa: BLE001
                avisos.append(f"{t}: error {type(ex).__name__} (intento {intento + 1})")
                time.sleep(5 * (intento + 1))
        if not res:
            fallos_seguidos += 1
            print(f"  {i:3d}/{len(objetivo)} {t:6} FALLÓ")
            if fallos_seguidos >= 3:
                avisos.append("La API falló 3 empresas seguidas: se corta acá. Revisá la clave, el saldo o la conexión y volvé a correrlo; lo ya hecho queda guardado.")
                break
            continue
        fallos_seguidos = 0
        res.update({"fecha": hoy, "modelo": MODELO})
        datos[t] = res
        print(f"  {i:3d}/{len(objetivo)} {t:6} ok")
        if i % 5 == 0:
            AF.guardar(datos, hoy)
        time.sleep(PAUSA_S)
    AF.guardar(datos, hoy)
    texto = [f"Análisis guardados: {len(datos)} (en esta corrida se intentaron {len(objetivo)}). Modelo: {MODELO}. Tokens usados: {t_in:,} de entrada y {t_out:,} de salida.", ""] + [f"- {a}" for a in avisos]
    with open(os.path.join(AQUI, "resultados_analisis_fundamental.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Se guardó data/analisis_fundamental.json (mandámelo o subilo a GitHub) y resultados_analisis_fundamental.txt")


if __name__ == "__main__":
    main(sys.argv[1:])
