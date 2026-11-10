"""
v1.5.58 (Guille, 10/11/2026): suma al archivo histórico propio los AÑOS VIEJOS de la SEC (gratis: data.sec.gov, «companyfacts») de todas las
empresas de la app que presentan informes allí. Así el Score de Seguridad del Dividendo puede mirar 12 años de ganancias (la vara de Weiss)
y no solo los 4 que trae Yahoo.

- Solo suma años MÁS VIEJOS que el más viejo guardado, en la misma moneda. Nunca toca los años que ya están (los de Yahoo mandan).
- Antes de sumar, controla que en el año que tienen los dos la SEC y lo guardado coincidan (ingresos o resultado neto dentro de 5 %).
  Si no coinciden (por ejemplo, otra moneda o un año fiscal corrido), esa empresa se saltea y queda anotada en el resultado.
- No cambia el cache, los puntajes ni la pantalla. Lo guardado queda en data/historico/estados.json (y el registro en cambios.json).

La SEC pide (https://www.sec.gov/os/accessing-edgar-data) que cada programa se identifique con un nombre y un mail de contacto y que no haga más
de 10 pedidos por segundo. Este hace uno cada medio segundo. El contacto es el mismo de piloto_sec (archivo .sec_contacto, queda solo en tu PC).

Uso (desde la carpeta del proyecto):
    python bajar_sec.py           (todas las empresas, unos 10 a 15 minutos)
    python bajar_sec.py KO PEP    (solo esas)
"""
import datetime as dt
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from data import historico as H  # noqa: E402
from data import sec as S  # noqa: E402

ARCH_CONTACTO = os.path.join(AQUI, ".sec_contacto")
PAUSA = 0.5
MAX_FALLOS_SEGUIDOS = 8


def _contacto():
    c = os.environ.get("SEC_CONTACTO")
    if not c and os.path.exists(ARCH_CONTACTO):
        c = open(ARCH_CONTACTO, encoding="utf-8").read().strip()
    if not c:
        c = input("La SEC pide un nombre y un mail de contacto (por ejemplo: TodoCedears tu@mail.com): ").strip()
        with open(ARCH_CONTACTO, "w", encoding="utf-8") as f:
            f.write(c)
    return c


def _get(url, ua):
    import requests
    r = requests.get(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}, timeout=60)
    r.raise_for_status()
    return r.json()


def _empresas():
    cache = json.load(open(os.path.join(AQUI, "data", "cache_datos.json"), encoding="utf-8"))["data"]
    return [r["ticker"] for r in cache]


def procesar(ticker, facts, archivo, cambios, hoy=None):
    """Suma los años viejos de un ticker al archivo (dict de estados.json ya leído). -> (estado, detalle, años sumados)."""
    tk = ticker.upper()
    sec_anios = S.a_anios(facts)
    if not sec_anios:
        return "sin_datos", "la SEC no tiene informes anuales con estos datos", []
    reg = archivo.get(tk)
    ok, det = S.coincide(sec_anios, reg)
    if ok is False:
        return "no_coincide", det, []
    if ok is None and reg and reg.get("anios"):
        return "no_coincide", det, []
    nuevo, sumados = H.sumar_anios_viejos(reg, sec_anios, tk, cambios, hoy=hoy)
    if sumados:
        archivo[tk] = nuevo
        return "ok", det, sumados
    return "nada_nuevo", det, []


def main(tickers=None):
    tickers = [t.upper() for t in (tickers or _empresas())]
    ua = _contacto()
    print("Bajando la lista de empresas de la SEC...")
    mapa = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in _get("https://www.sec.gov/files/company_tickers.json", ua).values()}
    time.sleep(PAUSA)
    archivo = H.leer("estados.json", {})
    cambios = H.leer("cambios.json", [])
    filas, seguidos = {"ok": [], "nada_nuevo": [], "no_coincide": [], "sin_datos": [], "sin_cik": [], "error": []}, 0
    print(f"Sumando años viejos de la SEC a {len(tickers)} empresas (no cierres la ventana)...")
    for i, t in enumerate(tickers, 1):
        cik = mapa.get(t.replace("-", "."), mapa.get(t))
        if not cik:
            filas["sin_cik"].append(t)
            print(f"  {i:3d}/{len(tickers)} {t:6} no presenta informes en la SEC")
            continue
        try:
            facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", ua)
            seguidos = 0
        except Exception as ex:  # noqa: BLE001
            seguidos += 1
            filas["error"].append(f"{t}: {type(ex).__name__} {str(ex)[:60]}")
            print(f"  {i:3d}/{len(tickers)} {t:6} error al bajar")
            if seguidos >= MAX_FALLOS_SEGUIDOS:
                filas["error"].append(f"La SEC dejó de responder ({seguidos} seguidos): se corta acá. Lo ya sumado quedó guardado; probá de nuevo en un rato.")
                break
            time.sleep(PAUSA)
            continue
        estado, det, sumados = procesar(t, facts, archivo, cambios)
        if estado == "ok":
            filas["ok"].append(f"{t}: +{len(sumados)} años ({sumados[0]}–{sumados[-1]})")
        else:
            filas[estado].append(f"{t}: {det}")
        print(f"  {i:3d}/{len(tickers)} {t:6} {estado}" + (f" +{len(sumados)} años desde {sumados[0]}" if sumados else ""))
        if i % 25 == 0:
            H.escribir("estados.json", dict(sorted(archivo.items())))
            H.escribir("cambios.json", cambios)
        time.sleep(PAUSA)
    H.escribir("estados.json", dict(sorted(archivo.items())))
    H.escribir("cambios.json", cambios)
    r = H.resumen()
    texto = [f"AÑOS VIEJOS DE LA SEC ({dt.datetime.now():%d/%m/%Y %H:%M})",
             f"Archivo: {r['empresas_con_estados']} empresas, {r['anios_fiscales']} años fiscales (el más viejo, {r['anio_mas_viejo']})", "",
             f"■ Con años sumados: {len(filas['ok'])}"] + [f"   {x}" for x in filas["ok"]] + [
             "", f"■ Ya tenían todo (nada para sumar): {len(filas['nada_nuevo'])}",
             "", f"■ No coinciden con Yahoo (se saltearon, para revisar): {len(filas['no_coincide'])}"] + [f"   {x}" for x in filas["no_coincide"]] + [
             "", f"■ Sin datos anuales en la SEC: {len(filas['sin_datos'])}"] + [f"   {x}" for x in filas["sin_datos"]] + [
             "", f"■ No presentan informes en la SEC: {len(filas['sin_cik'])} ({', '.join(filas['sin_cik'])})",
             "", f"■ Errores: {len(filas['error'])}"] + [f"   {x}" for x in filas["error"]]
    with open(os.path.join(AQUI, "resultados_sec.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n")
    print("\n" + "\n".join(texto))
    print("\nListo. Mandame data/historico/estados.json, data/historico/cambios.json y resultados_sec.txt")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
