"""
Detector de análisis fundamentales que hay que RENOVAR (sin listas a mano). Sin red y sin costo: solo compara archivos que ya están en el proyecto.

Una empresa figura como pendiente cuando pasa alguna de estas cosas:
  1. NUEVOS RESULTADOS: los estados de Yahoo (data/paquetes_yahoo.json) cambiaron desde que se escribió su análisis (cambió el período o los ingresos de los últimos
     12 meses). Es la señal más segura: significa que la empresa publicó un trimestre nuevo y Yahoo ya lo tiene.
  2. FECHA DE RESULTADOS PASADA: Yahoo marca que presentó resultados después de la fecha del análisis (agenda.resultados), pero los estados todavía no se actualizaron:
     se avisa como "esperar datos" (hay que correr bajar_paquetes_yahoo.bat para traer el trimestre nuevo y recién ahí renovar).
  3. SIN ANÁLISIS: la empresa no tiene análisis.
  4. VIEJO: el análisis tiene más de 120 días (por si Yahoo no avisó nada).

Uso (desde la carpeta del proyecto):
    python af_pendientes.py              lista de pendientes, con el motivo
    python af_pendientes.py --json       lo mismo en JSON (para una tarea programada)
    python af_pendientes.py --sellar     guarda en cada análisis la "firma" de los estados con los que se escribió (se hace sola al agregar un análisis nuevo con
                                         generar_analisis_fundamental.py --agregar; esto sirve para los que se escribieron antes)
Después de renovar un análisis (generar_analisis_fundamental.py --prompt TICKER  ->  redactar  ->  --agregar), la firma se actualiza sola y la empresa sale de la lista.
"""
import datetime
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import analisis_fundamental as AF  # noqa: E402
from data import paquetes_yahoo as py  # noqa: E402

DIAS_VIEJO = 120


def firma(estados):
    """Resumen chico de los estados (período más reciente + ingresos de los últimos 12 meses) para saber si Yahoo trajo un trimestre nuevo. None si no hay estados."""
    try:
        res = (estados or {}).get("resultados") or {}
        anios = res.get("anios") or []
        ing = next((f for f in res.get("filas") or [] if str(f[0]).strip().lower() in ("ingresos", "ventas", "ingresos totales")), None)
        if not anios or not ing:
            return None
        return {"periodo": str(anios[0]), "ingresos": ing[1][0], "anios": [str(a) for a in anios]}
    except Exception:  # noqa: BLE001
        return None


def _fecha(txt):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(str(txt), fmt).date()
        except ValueError:
            continue
    return None


def _prox_resultados(paq):
    """Fecha (date) que Yahoo marca para los resultados de la empresa ("d:2026-11-02"), o None."""
    r = ((paq or {}).get("agenda") or {}).get("resultados")
    x = r[0] if isinstance(r, list) and r else r
    if isinstance(x, str) and x.startswith("d:"):
        return _fecha(x[2:])
    return None


def pendientes(datos=None, paquetes=None, empresas=None, hoy=None):
    """[(ticker, estado, motivo)] ordenadas por urgencia. estado: 'renovar' (ya hay datos nuevos), 'esperar datos' (presentó resultados pero Yahoo no actualizó), 'sin análisis', 'viejo'."""
    datos = AF.cargar()[0] if datos is None else datos
    paquetes = py.cargar()[0] if paquetes is None else paquetes
    hoy = hoy or datetime.date.today()
    tickers = list(empresas) if empresas else sorted(set(datos) | set(paquetes))
    out = []
    for t in tickers:
        d = datos.get(t)
        if not d:
            out.append((t, "sin análisis", "todavía no tiene análisis"))
            continue
        f_an = _fecha(d.get("fecha"))
        f_actual = firma((paquetes.get(t) or {}).get("estados"))
        f_base = d.get("base")
        if f_actual and f_base and (f_actual.get("periodo") != f_base.get("periodo") or f_actual.get("ingresos") != f_base.get("ingresos")):
            out.append((t, "renovar", f"Yahoo trae datos nuevos ({f_base.get('periodo')} -> {f_actual.get('periodo')})"))
            continue
        prox = _prox_resultados(paquetes.get(t))
        if f_an and prox and f_an < prox <= hoy:
            out.append((t, "esperar datos", f"presentó resultados el {prox.strftime('%d/%m/%Y')} (después de su análisis) y Yahoo todavía no actualizó los estados"))
            continue
        if f_an and (hoy - f_an).days > DIAS_VIEJO:
            out.append((t, "viejo", f"el análisis tiene {(hoy - f_an).days} días"))
    orden = {"renovar": 0, "esperar datos": 1, "viejo": 2, "sin análisis": 3}
    return sorted(out, key=lambda x: (orden[x[1]], x[0]))


def sellar(ruta=None):
    """Agrega a cada análisis la firma de los estados actuales de Yahoo (para los análisis que se escribieron antes de que existiera). Devuelve la cantidad sellada."""
    datos, fecha = AF.cargar(ruta)
    paquetes = py.cargar()[0]
    n = 0
    for t, d in datos.items():
        f = firma((paquetes.get(t) or {}).get("estados"))
        if f and d.get("base") != f:
            d["base"] = f
            n += 1
    if n:
        AF.guardar(datos, fecha, ruta)
    return n


def main(args):
    if "--sellar" in args:
        print(f"Selladas {sellar()} análisis.")
        return
    p = pendientes()
    if "--json" in args:
        print(json.dumps([{"ticker": t, "estado": e, "motivo": m} for t, e, m in p], ensure_ascii=False, indent=1))
        return
    if not p:
        print("Todos los análisis están al día.")
        return
    for estado in ("renovar", "esperar datos", "viejo", "sin análisis"):
        fila = [(t, m) for t, e, m in p if e == estado]
        if fila:
            print(f"\n{estado.upper()} ({len(fila)})")
            for t, m in fila[:60]:
                print(f"  {t:8s} {m}")
            if len(fila) > 60:
                print(f"  ... y {len(fila) - 60} más")


if __name__ == "__main__":
    main(sys.argv[1:])
