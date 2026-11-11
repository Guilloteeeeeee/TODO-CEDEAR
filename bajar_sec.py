"""
v1.5.58 (Guille, 10/11/2026): suma al archivo histórico propio los AÑOS VIEJOS de la SEC (gratis: data.sec.gov, «companyfacts») de todas las
empresas de la app que presentan informes allí. Así el Score de Seguridad del Dividendo puede mirar 12 años de ganancias (la vara de Weiss)
y no solo los 4 que trae Yahoo.

- Solo suma años MÁS VIEJOS que el más viejo de Yahoo, en la misma moneda. Nunca toca los años de Yahoo (mandan). Los que ya habían venido de la
  SEC se rehacen en cada corrida (v1.5.61), así una corrección llega también a lo ya sumado.
- Antes de sumar, controla que en el año que tienen los dos la SEC y lo guardado coincidan (resultado neto o ingresos dentro de 5 %).
- v1.5.61: pasa la ganancia por acción de la SEC a la base de Yahoo (en los ADR la SEC informa por acción ordinaria y Yahoo por ADR).
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


def _cifras(rec):
    return {g: rec.get(g) for g in H.GRUPOS if rec.get(g)}


# v1.5.66: empresas que cambiaron de registrante en la SEC: el número nuevo todavía no tiene informes anuales y la historia quedó en el viejo.
# ExxonMobil: desde el 1/7/2026 la que cotiza como XOM es ExxonMobil Holdings Corporation (cambio de domicilio a Texas); los 10-K hasta 2025
# los presentó Exxon Mobil Corporation.
CIK_ANTERIOR = {"XOM": "0000034088"}


def procesar(ticker, facts, archivo, cambios, hoy=None, splits=None):
    """Suma los años viejos de un ticker al archivo (dict de estados.json ya leído). -> (estado, detalle, años sumados).
    v1.5.61: los años que ya habían venido de la SEC se rehacen cada vez (son de la SEC, no de Yahoo: se pueden volver a bajar), con la ganancia
    por acción pasada a la base de Yahoo (data/sec.factor_por_accion: ADR). Un año que cambia queda anotado en cambios.json («sec_corregido»).
    Estados: ok (años nuevos), corregido (solo se corrigieron años ya sumados), nada_nuevo, no_coincide, sin_datos."""
    tk = ticker.upper()
    hoy = hoy or dt.date.today().isoformat()
    sec_anios = S.a_anios(facts)
    if not sec_anios:
        return "sin_datos", "la SEC no tiene informes anuales con estos datos (" + S.diagnostico(facts) + ")", []
    reg = archivo.get(tk) or {}
    previos = {a: r for a, r in (reg.get("anios") or {}).items() if r.get("fuente") == "SEC"}
    base = dict(reg)
    if previos:
        base["anios"] = {a: r for a, r in reg["anios"].items() if a not in previos}
    ok, det = S.coincide(sec_anios, base)
    if ok is False:
        return "no_coincide", det, []
    if ok is None and base.get("anios"):
        return "no_coincide", det, []
    # v1.5.66: cada informe de la SEC se lleva a la base de hoy de Yahoo con su propio factor (directo o encadenado: sec.llevar_a_base)
    sec_b, fac, sin_base = S.llevar_a_base(sec_anios, facts, base, splits, hoy)
    nuevo, todos = H.sumar_anios_viejos(base, sec_b, tk, None, hoy=hoy)
    distintos = sorted({f for f, _ in fac.values() if f != 1.0})
    det_f = (f"ganancia por acción llevada a la base de Yahoo (factores {', '.join(f'{x:g}' for x in distintos)})" if distintos else "")
    if sin_base:
        det_f = (det_f + "; " if det_f else "") + f"{len(sin_base)} años sin ganancia por acción (su informe no se pudo llevar a la base de Yahoo)"
    factor = distintos[0] if distintos else 1.0
    # red de seguridad (v1.5.63): si la unión SEC → Yahoo salta y el año de la unión no se verificó en directo, queda afuera la ganancia por
    # acción de la SEC (los montos sí se guardan). Con verificación directa un salto es real (fusión, preferidas: Agnico Eagle, Corning).
    ok_u, rel = S.union_por_accion(nuevo, splits)
    if ok_u is False:
        an_n = nuevo.get("anios") or {}
        ult = max((a for a, r in an_n.items() if r.get("fuente") == "SEC" and S.EPS_ROT in (r.get("resultados") or {})), default=None)
        if not ult or an_n[ult].get("modo_accion") != "directo":
            S.quitar_por_accion(nuevo)
            det_f = f"ganancia por acción de la SEC sin verificar (relación de acciones {rel} en la unión): queda afuera"
            factor = "sin_eps"
    anios = dict(nuevo.get("anios") or {})
    sumados, corregidos = [], []
    for a in todos:
        if a not in previos:
            sumados.append(a)
        elif _cifras(previos[a]) == _cifras(anios[a]):
            anios[a] = previos[a]                    # sin cambios: queda el registro de antes (con su fecha de captura)
        else:
            corregidos.append(a)
    for a, r in previos.items():                     # lo que ya estaba y ahora no vino, queda (solo se agrega)
        anios.setdefault(a, r)
    if det_f:
        det = f"{det} · {det_f}"
    if not sumados and not corregidos:
        return "nada_nuevo", det, []
    nuevo["anios"] = dict(sorted(anios.items()))
    archivo[tk] = nuevo
    if sumados:
        H._anotar(cambios, "anios_sec", tk, anios=sumados, detalle="años sumados desde SEC (hacia atrás)")
    if corregidos:
        H._anotar(cambios, "sec_corregido", tk, anios=corregidos,
                  detalle=f"años de la SEC rehechos ({det_f})" if det_f else "años de la SEC rehechos")
    if sumados:
        return "ok", det + (f" · además se corrigieron {len(corregidos)} años ya sumados" if corregidos else ""), sumados
    return "corregido", f"{len(corregidos)} años corregidos · {det}", corregidos


def main(tickers=None):
    tickers = [t.upper() for t in (tickers or _empresas())]
    ua = _contacto()
    print("Bajando la lista de empresas de la SEC...")
    mapa = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in _get("https://www.sec.gov/files/company_tickers.json", ua).values()}
    time.sleep(PAUSA)
    archivo = H.leer("estados.json", {})
    cambios = H.leer("cambios.json", [])
    splits = H.leer("splits.json", {})
    filas, seguidos = {"ok": [], "corregido": [], "nada_nuevo": [], "no_coincide": [], "sin_datos": [], "sin_cik": [], "error": []}, 0
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
        if not S.a_anios(facts) and t in CIK_ANTERIOR:
            try:
                time.sleep(PAUSA)
                viejo = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK_ANTERIOR[t]}.json", ua)
                if S.a_anios(viejo):
                    facts = viejo
                    print(f"  {i:3d}/{len(tickers)} {t:6} usa los informes de su registrante anterior ({viejo.get('entityName', '?')})")
            except Exception:  # noqa: BLE001
                pass
        estado, det, sumados = procesar(t, facts, archivo, cambios, splits=splits.get(t))
        if estado == "ok":
            filas["ok"].append(f"{t}: +{len(sumados)} años ({sumados[0]}–{sumados[-1]})" + (f" · {det.split(' · ', 1)[1]}" if " · " in det else ""))
        else:
            filas[estado].append(f"{t}: {det}")
        print(f"  {i:3d}/{len(tickers)} {t:6} {estado}" + (f" +{len(sumados)} años desde {sumados[0]}" if sumados and estado == "ok" else ""))
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
             "", f"■ Años ya sumados que se corrigieron (base por acción de los ADR, por ejemplo): {len(filas['corregido'])}"] + [
             f"   {x}" for x in filas["corregido"]] + [
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
