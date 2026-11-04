"""Busca y prueba los RSS de elEconomista.es (CEDEAR Screener v1.5.23). Solo LEE páginas públicas. Deja resultados_eleconomista.txt (mandámelo)."""
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; TodoCedears/1.5; lector de titulares; contacto: finanzas.medicos@gmail.com)"
PAGINAS = ["https://www.eleconomista.es/rss/", "https://www.eleconomista.es/rss/rss.php", "https://www.eleconomista.es/"]


def bajar(url, n=2_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, r.read(n).decode("utf-8", "replace")


def main():
    out, feeds = ["PRUEBA elEconomista.es", ""], []
    for p in PAGINAS:
        try:
            cod, h = bajar(p)
        except Exception as e:  # noqa: BLE001
            out.append(f"NO  {p}: {getattr(e, 'code', '') or type(e).__name__}")
            continue
        enc = sorted(set(re.findall(r'https?://[^\s"\'<>]*eleconomista\.es[^\s"\'<>]*(?:rss|feed|xml)[^\s"\'<>]*', h, re.I)))
        rel = sorted(set("https://www.eleconomista.es" + x for x in re.findall(r'href="(/[^"\s]*(?:rss|feed)[^"\s]*)"', h, re.I)))
        out.append(f"SI  {p}: responde; direcciones con rss/feed: {len(enc) + len(rel)}")
        feeds += enc + rel
        if feeds:
            break
    vistos = []
    for f in feeds:
        if f not in vistos and not f.rstrip("/").endswith("/rss"):
            vistos.append(f)
    out += ["", "== Feeds encontrados (se prueban hasta 25) =="]
    for f in vistos[:25]:
        try:
            cod, x = bajar(f, 3_000_000)
            raiz = ET.fromstring(x.encode("utf-8"))
            it = [e for e in raiz.iter() if e.tag.split("}")[-1] in ("item", "entry")]
            tit = next((e.text for e in it[0].iter() if e.tag.split("}")[-1] == "title" and e.text), "") if it else ""
            fec = next((e.text for e in it[0].iter() if e.tag.split("}")[-1] in ("pubDate", "published", "updated", "date") and e.text), "?") if it else "?"
            out.append(f"SI  {f}: {len(it)} notas · más nueva: {fec[:31]} · ej.: {tit[:90]}")
        except Exception as e:  # noqa: BLE001
            out.append(f"NO  {f}: {getattr(e, 'code', '') or type(e).__name__}")
        print(out[-1][:150], flush=True)
    if not vistos:
        out.append("(no se encontró ningún feed en las páginas probadas)")
    with open("resultados_eleconomista.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("\nListo. Mandame resultados_eleconomista.txt")


if __name__ == "__main__":
    sys.exit(main())
