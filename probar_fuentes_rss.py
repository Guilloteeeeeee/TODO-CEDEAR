"""Prueba qué fuentes de noticias se pueden leer por RSS (CEDEAR Screener v1.5.23). Sin tocar la app: solo LEE los feeds públicos.
Uso:  python probar_fuentes_rss.py        -> deja resultados_fuentes_rss.txt (mandámelo).
Para cada feed dice: si responde, cuántas notas trae, la fecha de la más nueva, un ejemplo de titular y si hay marcas de nota paga.
Se lee igual que lo haría la app publicada (mismo User-Agent), para saber si el sitio la deja pasar o la bloquea."""
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = "Mozilla/5.0 (compatible; TodoCedears/1.5; lector de titulares; contacto: finanzas.medicos@gmail.com)"

# (grupo, nombre, url)
FEEDS = [
    ("CONTROL (ya usadas)", "Ámbito Finanzas", "https://www.ambito.com/rss/pages/finanzas.xml"),
    ("CONTROL (ya usadas)", "CNBC Mercados", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20409666"),
    ("Mercados de Estados Unidos", "Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("Mercados de Estados Unidos", "MarketWatch (titulares)", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Mercados de Estados Unidos", "MarketWatch (pulso del mercado)", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ("Mercados de Estados Unidos", "Nasdaq (mercados)", "https://www.nasdaq.com/feed/rssoutbound?category=Markets"),
    ("Mercados de Estados Unidos", "Seeking Alpha (al instante)", "https://seekingalpha.com/market_currents.xml"),
    ("Mercados de Estados Unidos", "Benzinga", "https://www.benzinga.com/feed"),
    ("Investing.com", "Investing (inglés, general)", "https://www.investing.com/rss/news.rss"),
    ("Investing.com", "Investing (inglés, bolsas)", "https://www.investing.com/rss/news_25.rss"),
    ("Investing.com", "Investing (español, general)", "https://es.investing.com/rss/news.rss"),
    ("Investing.com", "Investing (español, bolsas)", "https://es.investing.com/rss/news_25.rss"),
    ("Resto del mundo", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Resto del mundo", "The Guardian Business", "https://www.theguardian.com/uk/business/rss"),
    ("Resto del mundo", "Euronews Business", "https://www.euronews.com/rss?level=theme&name=business"),
    ("Resto del mundo", "DW Business", "https://rss.dw.com/rdf/rss-en-bus"),
    ("Resto del mundo", "Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar"),
    ("Resto del mundo", "South China Morning Post (negocios)", "https://www.scmp.com/rss/92/feed"),
    ("Resto del mundo (en español)", "El País Economía", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"),
    ("Resto del mundo (en español)", "Expansión (mercados)", "https://e00-expansion.uecdn.es/rss/mercados.xml"),
    ("Argentina", "El Cronista (finanzas)", "https://www.cronista.com/files/rss/finanzas-mercados.xml"),
    ("Argentina", "Infobae Economía", "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/"),
    ("Argentina", "iProfesional Finanzas", "https://www.iprofesional.com/rss/finanzas"),
    ("Argentina", "La Nación Economía", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/"),
    ("Fuentes oficiales (el dato, sin opinión)", "Reserva Federal (comunicados)", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("Fuentes oficiales (el dato, sin opinión)", "SEC (comunicados)", "https://www.sec.gov/news/pressreleases.rss"),
    ("Fuentes oficiales (el dato, sin opinión)", "Banco Central Europeo (prensa)", "https://www.ecb.europa.eu/rss/press.html"),
]
PAGA = re.compile(r"(?i)\bpro\b|premium|suscri|subscriber|paywall|/pro/|/premium/")


def _fecha(txt):
    try:
        return parsedate_to_datetime(txt)
    except Exception:  # noqa: BLE001
        m = re.match(r"(\d{4}-\d{2}-\d{2})", txt or "")
        return m.group(1) if m else None


def probar(nombre, url):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.5"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cod, datos = r.status, r.read(3_000_000)
    except Exception as e:  # noqa: BLE001
        cod = getattr(e, "code", None)
        return f"NO  {nombre}: {('HTTP ' + str(cod)) if cod else type(e).__name__ + ' ' + str(e)[:80]}"
    seg = time.time() - t0
    try:
        raiz = ET.fromstring(datos)
    except Exception:  # noqa: BLE001
        return f"NO  {nombre}: respondió (HTTP {cod}) pero no es un RSS legible (¿página de bloqueo?): {datos[:60]!r}"
    items = [e for e in raiz.iter() if e.tag.split("}")[-1] in ("item", "entry")]
    if not items:
        return f"NO  {nombre}: RSS vacío"

    def hijo(it, *tags):
        for e in it.iter():
            if e.tag.split("}")[-1] in tags and (e.text or "").strip():
                return e.text.strip()
        return ""
    tit = [hijo(it, "title") for it in items]
    fechas = [hijo(it, "pubDate", "published", "updated", "date") for it in items]
    pagas = sum(1 for t, it in zip(tit, items) if PAGA.search(t) or PAGA.search(hijo(it, "link")))
    return (f"SI  {nombre}: {len(items)} notas · más nueva: {fechas[0][:31] or '?'} · {seg:.1f} s · con marca de pago: {pagas}\n"
            f"       ej.: {tit[0][:110]}")


def main():
    out, grupo = ["PRUEBA DE FUENTES RSS · " + time.strftime("%d/%m/%Y %H:%M"), ""], None
    for g, n, u in FEEDS:
        if g != grupo:
            out += ["", "== " + g + " =="]
            grupo = g
        r = probar(n, u)
        print(r.split("\n")[0], flush=True)
        out.append(r)
    out += ["", "SI = responde y trae notas; NO = bloqueada, caída o dirección equivocada (no es lo mismo: si dice HTTP 404 probablemente la dirección cambió)."]
    with open("resultados_fuentes_rss.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("\nListo. Mandame resultados_fuentes_rss.txt")


if __name__ == "__main__":
    sys.exit(main())
