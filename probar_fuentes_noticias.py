"""Mira, sin tocar la app, si se pueden leer noticias de otcfinancialmarkets.com y de canales publicos de Telegram.
Uso:  python probar_fuentes_noticias.py                      (solo OTC Financial Markets)
      python probar_fuentes_noticias.py canal1 canal2        (OTC + los canales de Telegram que le pases, el nombre sin @)
Guarda el detalle en resultados_fuentes_noticias.txt (mandamelo). Solo LEE paginas publicas; no se registra en nada."""
import html as _html
import re
import sys

OTC = "https://otcfinancialmarkets.com"
CANDIDATAS = ["/noticias-24h", "/robots.txt", "/feed", "/rss", "/feed.xml", "/rss.xml", "/noticias-24h/feed", "/sitemap.xml"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; TodoCedears/1.2; prueba de lectura de titulares; contacto: finanzas.medicos@gmail.com)"}


def _get(url):
    import requests
    r = requests.get(url, headers=UA, timeout=15)
    return r.status_code, r.headers.get("content-type", ""), r.text


def _texto(h):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def probar_otc():
    out = ["== OTC Financial Markets =="]
    for ruta in CANDIDATAS:
        try:
            st, ct, cuerpo = _get(OTC + ruta)
        except Exception as e:  # noqa: BLE001
            out.append(f"{ruta}: error {type(e).__name__}: {str(e)[:120]}")
            continue
        extra = ""
        if ruta == "/robots.txt" and st == 200:
            extra = " | contenido: " + cuerpo[:600].replace("\n", " / ")
        elif ruta == "/noticias-24h" and st == 200:
            titulos = [_texto(t) for t in re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", cuerpo, flags=re.S)][:12]
            apis = sorted(set(re.findall(r"https?://[^\"' <>]*(?:api|feed|rss|json|news)[^\"' <>]*", cuerpo, flags=re.I)))[:15]
            extra = (f" | titulos en el HTML: {len(titulos)} {titulos[:8]} | next_data={'__NEXT_DATA__' in cuerpo} | json-ld={'ld+json' in cuerpo}"
                     f" | direcciones que parecen api/feed: {apis}")
        out.append(f"{ruta}: HTTP {st} {ct.split(';')[0]} {len(cuerpo)} bytes{extra}")
    return out


def probar_telegram(canal):
    out = [f"== Telegram: {canal} =="]
    try:
        st, ct, cuerpo = _get(f"https://t.me/s/{canal}")
    except Exception as e:  # noqa: BLE001
        return out + [f"error {type(e).__name__}: {str(e)[:120]}"]
    msgs = re.findall(r'<div class="tgme_widget_message_wrap.*?(?=<div class="tgme_widget_message_wrap|\Z)', cuerpo, flags=re.S)
    out.append(f"HTTP {st}; mensajes visibles: {len(msgs)}")
    for m in msgs[-5:]:
        link = re.search(r'class="tgme_widget_message_date" href="([^"]+)"', m)
        fecha = re.search(r'<time[^>]*datetime="([^"]+)"', m)
        txt = re.search(r'class="tgme_widget_message_text[^>]*>(.*?)</div>', m, flags=re.S)
        out.append(f"  {fecha.group(1) if fecha else '?'} {link.group(1) if link else '?'} :: {(_texto(txt.group(1)) if txt else '(sin texto)')[:160]}")
    return out


def main(canales):
    texto = probar_otc()
    for c in canales:
        texto += [""] + probar_telegram(c.lstrip("@"))
    s = "\n".join(texto)
    print(s)
    open("resultados_fuentes_noticias.txt", "w", encoding="utf-8").write(s + "\n")
    print("\nListo. Mandame resultados_fuentes_noticias.txt")


if __name__ == "__main__":
    main(sys.argv[1:])
