"""Iconos de los ETFs (v1.2.67): dibujos propios en SVG (circulo de color con un dibujo blanco), en el estilo del de Bitcoin. Los ETFs de un solo pais
llevan la bandera dibujada. Todo es vectorial: se ve nítido a cualquier tamaño y no depende de ningun servicio. La columna `icono` de data/etfs.csv
tiene "svg:<nombre>" (los nombres estan en ICONOS); si falta, la pagina muestra las iniciales del ticker."""
import math
import zlib


def _estrella(cx, cy, re, ri, n=5):
    pts = []
    for i in range(n * 2):
        r = re if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def _insignia(fondo, dibujo, etiqueta):
    return (f'<svg viewBox="0 0 64 64" role="img" aria-label="{etiqueta}"><circle cx="32" cy="32" r="32" fill="{fondo}"/>{dibujo}</svg>')


def _globo(fondo, etiqueta):
    d = ('<g fill="none" stroke="#fff" stroke-width="3"><circle cx="32" cy="32" r="18"/><ellipse cx="32" cy="32" rx="8" ry="18"/>'
         '<path d="M14 32h36M17 22h30M17 42h30" stroke-width="2.4"/></g>')
    return _insignia(fondo, d, etiqueta)


def _chip(fondo, etiqueta):
    pines = "".join(f'<rect x="{x}" y="13" width="3.4" height="7"/><rect x="{x}" y="44" width="3.4" height="7"/>'
                    f'<rect x="13" y="{x}" width="7" height="3.4"/><rect x="44" y="{x}" width="7" height="3.4"/>' for x in (24, 30.3, 36.6))
    d = f'<g fill="#fff">{pines}<rect x="19" y="19" width="26" height="26" rx="4"/></g><rect x="25" y="25" width="14" height="14" rx="2" fill="{fondo}"/>'
    return _insignia(fondo, d, etiqueta)


def _barras(fondo, etiqueta):
    d = ('<g fill="#fff"><rect x="15" y="36" width="9" height="14" rx="1.5"/><rect x="27.5" y="27" width="9" height="23" rx="1.5"/>'
         '<rect x="40" y="16" width="9" height="34" rx="1.5"/></g>')
    return _insignia(fondo, d, etiqueta)


def _lingotes(fondo, cara, borde, etiqueta):
    def lin(p):
        return f'<polygon points="{p}" fill="{cara}" stroke="{borde}" stroke-width="1.6" stroke-linejoin="round"/>'
    d = lin("11,49 16,39 31,39 36,49") + lin("29,49 34,39 49,39 54,49") + lin("20,37 25,27 40,27 45,37")
    return _insignia(fondo, d, etiqueta)


def _bandera(dibujo, etiqueta):
    i = zlib.crc32(etiqueta.encode()) % 99999
    return (f'<svg viewBox="0 0 64 64" role="img" aria-label="{etiqueta}"><defs><clipPath id="cb{i}"><circle cx="32" cy="32" r="32"/></clipPath></defs>'
            f'<g clip-path="url(#cb{i})">{dibujo}</g><circle cx="32" cy="32" r="31.4" fill="none" stroke="rgba(0,0,0,.18)" stroke-width="1.2"/></svg>')


_HOJA_ARCE = ("M32 14 L35 22 L40 20 L38 31 L46 26 L44 34 L50 35 L42 40 L43 44 L33 43 L33 52 L31 52 L31 43 L21 44 L22 40 L14 35 L20 34 L18 26 L26 31 L24 20 L29 22 Z")

ICONOS = {
    # --- indices de EE.UU.
    "indice": _barras("#2563eb", "Indice"),
    "indice2": _barras("#1d4ed8", "Indice"),
    "nasdaq": _insignia("#4f46e5", '<polyline points="14,44 24,32 32,38 50,18" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
                        '<polygon points="42,16 54,16 54,28" fill="#fff"/>', "Nasdaq"),
    "fabrica": _insignia("#475569", '<path d="M12 50V30L24 38V30L36 38V18H44V50Z" fill="#fff"/><rect x="38" y="24" width="3" height="5" fill="#475569"/>', "Industriales"),
    "estrella": _insignia("#d97706", f'<polygon points="{_estrella(32, 33, 18, 7.6)}" fill="#fff"/>', "Calidad"),
    "hoja": _insignia("#16a34a", '<path d="M18 46C18 28 29 17 47 17C47 35 36 46 18 46Z" fill="#fff"/><path d="M20 44L38 26" stroke="#16a34a" stroke-width="2.4" stroke-linecap="round"/>', "Hoja"),
    "igual": _insignia("#0891b2", '<g fill="#fff"><rect x="14" y="20" width="7" height="26" rx="1.5"/><rect x="24.5" y="20" width="7" height="26" rx="1.5"/>'
                       '<rect x="35" y="20" width="7" height="26" rx="1.5"/><rect x="45.5" y="20" width="7" height="26" rx="1.5"/></g>', "Igual ponderado"),
    "edificios": _insignia("#475569", '<g fill="#fff"><rect x="15" y="26" width="15" height="24" rx="1.5"/><rect x="33" y="16" width="17" height="34" rx="1.5"/></g>'
                           '<g fill="#475569"><rect x="19" y="31" width="3" height="3"/><rect x="24" y="31" width="3" height="3"/><rect x="19" y="38" width="3" height="3"/><rect x="24" y="38" width="3" height="3"/>'
                           '<rect x="37" y="21" width="3" height="3"/><rect x="43" y="21" width="3" height="3"/><rect x="37" y="28" width="3" height="3"/><rect x="43" y="28" width="3" height="3"/>'
                           '<rect x="37" y="35" width="3" height="3"/><rect x="43" y="35" width="3" height="3"/></g>', "Empresas medianas"),
    "casitas": _insignia("#0f766e", '<g fill="#fff"><rect x="13" y="36" width="12" height="14" rx="1.5"/><rect x="26.5" y="28" width="12" height="22" rx="1.5"/><rect x="40" y="38" width="12" height="12" rx="1.5"/></g>'
                         '<g fill="#0f766e"><rect x="16.5" y="40" width="3" height="3"/><rect x="30" y="33" width="3" height="3"/><rect x="30" y="40" width="3" height="3"/><rect x="43.5" y="42" width="3" height="3"/></g>', "Empresas chicas"),
    "diamante": _insignia("#0e7490", '<polygon points="32,15 47,28 32,50 17,28" fill="#fff"/><path d="M17 28H47M25 28L32 15L39 28M25 28L32 50L39 28" fill="none" stroke="#0e7490" stroke-width="1.8" stroke-linejoin="round"/>', "Valor"),
    "crecimiento": _insignia("#dc2626", '<polyline points="13,46 27,31 36,39 50,22" fill="none" stroke="#fff" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>'
                             '<polygon points="41,19 54,19 54,32" fill="#fff"/>', "Crecimiento"),
    "dolar": _insignia("#15803d", '<circle cx="32" cy="32" r="19" fill="#fff"/><text x="32" y="42" font-size="29" font-weight="800" text-anchor="middle" fill="#15803d" font-family="Arial,Helvetica,sans-serif">$</text>', "Dividendos"),
    # --- mundo
    "globo": _globo("#0284c7", "Mundo"), "globo2": _globo("#0369a1", "Mundo"), "globo3": _globo("#0891b2", "Mercados desarrollados"),
    "globo_em": _globo("#ea580c", "Mercados emergentes"), "globo_em2": _globo("#f97316", "Mercados emergentes"),
    "globo_la": _globo("#0d9488", "Latinoamerica"), "globo_ap": _globo("#7c3aed", "Asia Pacifico"),
    "europa": _insignia("#1e40af", "".join(f'<polygon points="{_estrella(32 + 17 * math.cos(math.radians(a)), 32 + 17 * math.sin(math.radians(a)), 4.2, 1.8)}" fill="#facc15"/>'
                                           for a in range(0, 360, 30)), "Europa"),
    # --- banderas de un solo pais
    "bandera_jp": _bandera('<rect width="64" height="64" fill="#fff"/><circle cx="32" cy="32" r="14" fill="#bc002d"/>', "Japon"),
    "bandera_br": _bandera('<rect width="64" height="64" fill="#009b3a"/><polygon points="32,10 58,32 32,54 6,32" fill="#fedf00"/><circle cx="32" cy="32" r="11" fill="#002776"/>'
                           '<path d="M21.3 29.5C28 27 37 28.5 42.7 34.5" fill="none" stroke="#fff" stroke-width="2.2"/>', "Brasil"),
    "bandera_cn": _bandera('<rect width="64" height="64" fill="#de2910"/>' + f'<polygon points="{_estrella(16, 17, 9, 3.6)}" fill="#ffde00"/>'
                           + "".join(f'<polygon points="{_estrella(x, y, 3.2, 1.3)}" fill="#ffde00"/>' for x, y in ((29, 8), (35, 15), (35, 23), (29, 30))), "China"),
    "bandera_kr": _bandera('<rect width="64" height="64" fill="#fff"/><path d="M20 32a12 12 0 0 1 24 0z" fill="#cd2e3a"/><path d="M20 32a12 12 0 0 0 24 0z" fill="#0047a0"/>'
                           '<circle cx="26" cy="32" r="6" fill="#cd2e3a"/><circle cx="38" cy="32" r="6" fill="#0047a0"/>'
                           '<g fill="#000"><rect x="6" y="8" width="12" height="2.4" transform="rotate(-35 12 9)"/><rect x="6" y="12" width="12" height="2.4" transform="rotate(-35 12 13)"/>'
                           '<rect x="46" y="52" width="12" height="2.4" transform="rotate(-35 52 53)"/><rect x="46" y="48" width="12" height="2.4" transform="rotate(-35 52 49)"/>'
                           '<rect x="46" y="8" width="12" height="2.4" transform="rotate(35 52 9)"/><rect x="46" y="12" width="12" height="2.4" transform="rotate(35 52 13)"/>'
                           '<rect x="6" y="52" width="12" height="2.4" transform="rotate(35 12 53)"/><rect x="6" y="48" width="12" height="2.4" transform="rotate(35 12 49)"/></g>', "Corea del Sur"),
    "bandera_ca": _bandera('<rect width="64" height="64" fill="#fff"/><rect width="16" height="64" fill="#d52b1e"/><rect x="48" width="16" height="64" fill="#d52b1e"/>'
                           f'<path d="{_HOJA_ARCE}" fill="#d52b1e"/>', "Canada"),
    # --- sectores de EE.UU.
    "matraz": _insignia("#a16207", '<path d="M26 14h12v3h-2v10l10 17a4.5 4.5 0 0 1-3.9 6.8H21.9A4.5 4.5 0 0 1 18 44l10-17V17h-2z" fill="#fff"/><path d="M22 41h20" stroke="#a16207" stroke-width="2.2"/>', "Materiales"),
    "casa": _insignia("#be123c", '<polygon points="12,32 32,15 52,32 47,32 47,50 17,50 17,32" fill="#fff"/><rect x="28" y="37" width="8" height="13" fill="#be123c"/>', "Inmobiliario"),
    "banco": _insignia("#1e3a8a", '<polygon points="32,13 51,25 13,25" fill="#fff"/><g fill="#fff"><rect x="17" y="28" width="5.5" height="16"/><rect x="25" y="28" width="5.5" height="16"/>'
                       '<rect x="33.5" y="28" width="5.5" height="16"/><rect x="41.5" y="28" width="5.5" height="16"/><rect x="13" y="46" width="38" height="5" rx="1"/></g>', "Financiero"),
    "bolsa": _insignia("#db2777", '<rect x="17" y="26" width="30" height="25" rx="3.5" fill="#fff"/><path d="M25 30v-5a7 7 0 0 1 14 0v5" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round"/>', "Consumo discrecional"),
    "antena": _insignia("#7e22ce", '<circle cx="32" cy="33" r="4.5" fill="#fff"/><path d="M32 38v13" stroke="#fff" stroke-width="3.5" stroke-linecap="round"/>'
                        '<path d="M23 25a13 13 0 0 0 0 16M41 25a13 13 0 0 1 0 16M17 19a21 21 0 0 0 0 28M47 19a21 21 0 0 1 0 28" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>', "Comunicaciones"),
    "engranaje": _insignia("#52525b", "".join(f'<rect x="29" y="12" width="6" height="9" rx="1" fill="#fff" transform="rotate({a} 32 32)"/>' for a in range(0, 360, 45))
                           + '<circle cx="32" cy="32" r="15" fill="#fff"/><circle cx="32" cy="32" r="6" fill="#52525b"/>', "Industriales"),
    "chip": _chip("#6d28d9", "Tecnologia"), "chip2": _chip("#0f172a", "Semiconductores"),
    "gota": _insignia("#92400e", '<path d="M32 13C32 13 17 29 17 38a15 15 0 0 0 30 0C47 29 32 13 32 13z" fill="#fff"/><path d="M25 39a7 7 0 0 0 7 7" fill="none" stroke="#92400e" stroke-width="2.6" stroke-linecap="round"/>', "Energia"),
    "barril": _insignia("#374151", '<rect x="19" y="14" width="26" height="36" rx="6" fill="#fff"/><rect x="19" y="24" width="26" height="3.2" fill="#374151"/><rect x="19" y="37" width="26" height="3.2" fill="#374151"/>', "Petroleo"),
    "carrito": _insignia("#ea580c", '<path d="M12 17h7l5 21h21l5-15H21" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="27" cy="47" r="3.6" fill="#fff"/><circle cx="43" cy="47" r="3.6" fill="#fff"/>', "Consumo basico"),
    "cruz": _insignia("#dc2626", '<rect x="26" y="13" width="12" height="38" rx="3" fill="#fff"/><rect x="13" y="26" width="38" height="12" rx="3" fill="#fff"/>', "Salud"),
    "rayo": _insignia("#ca8a04", '<polygon points="37,11 19,36 30,36 26,53 45,27 33,27" fill="#fff"/>', "Servicios publicos"),
    # --- materias primas
    "oro": _lingotes("#a16207", "#fde047", "#92400e", "Oro"),
    "plata": _lingotes("#64748b", "#f1f5f9", "#94a3b8", "Plata"),
    "cobre": _lingotes("#9a3412", "#fb923c", "#7c2d12", "Cobre"),
    "pico": _insignia("#78350f", '<path d="M13 31C21 14 43 14 51 31" fill="none" stroke="#fff" stroke-width="5.5" stroke-linecap="round"/><path d="M32 21V52" stroke="#fff" stroke-width="5.5" stroke-linecap="round"/>', "Mineria"),
    "pepita": _insignia("#a16207", '<polygon points="16,41 21,28 33,21 47,25 52,37 45,48 29,50" fill="#fde047" stroke="#92400e" stroke-width="1.8" stroke-linejoin="round"/>'
                        '<path d="M26 31l7-3M34 40l6-4" stroke="#fffbeb" stroke-width="2.6" stroke-linecap="round"/>', "Mineras de oro"),
    "atomo": _insignia("#4d7c0f", '<g fill="none" stroke="#fff" stroke-width="2.8"><ellipse cx="32" cy="32" rx="20" ry="8"/><ellipse cx="32" cy="32" rx="20" ry="8" transform="rotate(60 32 32)"/>'
                       '<ellipse cx="32" cy="32" rx="20" ry="8" transform="rotate(120 32 32)"/></g><circle cx="32" cy="32" r="4.2" fill="#fff"/>', "Uranio"),
    "cubos": _insignia("#475569", '<polygon points="32,12 50,22 32,32 14,22" fill="#fff"/><polygon points="14,25 31,35 31,54 14,44" fill="#fff" fill-opacity=".8"/><polygon points="50,25 33,35 33,54 50,44" fill="#fff" fill-opacity=".55"/>', "Materias primas"),
    "maiz": _insignia("#ca8a04", '<g transform="rotate(18 32 30)"><ellipse cx="32" cy="29" rx="9.5" ry="18" fill="#fde047"/>'
                      + "".join(f'<circle cx="{x}" cy="{y}" r="1.7" fill="#ca8a04"/>' for x in (27.5, 32, 36.5) for y in (16, 22, 28, 34, 40)) + '</g>'
                      '<path d="M32 49C22 49 17 38 18 30C23 36 27 40 32 41Z" fill="#4ade80"/><path d="M32 49C42 49 47 38 46 30C41 36 37 40 32 41Z" fill="#22c55e"/>', "Maiz"),
    "soja": _insignia("#4d7c0f", '<path d="M13 41C13 28 29 17 49 17C51 36 37 51 21 49C16 48 13 45 13 41Z" fill="#bef264"/><g fill="#65a30d"><circle cx="24" cy="38" r="5.4"/><circle cx="33" cy="32" r="5.4"/><circle cx="42" cy="25.5" r="5.4"/></g>', "Soja"),
    # --- temas
    "adn": _insignia("#0f766e", '<g fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round"><path d="M22 13C45 24 19 40 42 51"/><path d="M42 13C19 24 45 40 22 51"/></g>'
                     '<g stroke="#fff" stroke-width="2.2" stroke-linecap="round"><path d="M25 21h14M24 32h16M25 43h14"/></g>', "Biotecnologia"),
    "sol": _insignia("#f59e0b", '<circle cx="32" cy="32" r="10" fill="#fff"/><g stroke="#fff" stroke-width="3.6" stroke-linecap="round">'
                     + "".join(f'<line x1="32" y1="12" x2="32" y2="17" transform="rotate({a} 32 32)"/>' for a in range(0, 360, 45)) + '</g>', "Energia limpia"),
    "avion": _insignia("#1d4ed8", '<polygon points="32,11 36,25 53,35 53,40 36,35.5 35,46 41,50 41,53 32,51 23,53 23,50 29,46 28,35.5 11,40 11,35 28,25" fill="#fff"/>', "Aeroespacial"),
    "escudo": _insignia("#1e40af", '<path d="M32 12L49 18V31C49 42 42 49 32 53C22 49 15 42 15 31V18Z" fill="#fff"/><rect x="25.5" y="30" width="13" height="11" rx="2" fill="#1e40af"/>'
                        '<path d="M28.5 30v-3.5a3.5 3.5 0 0 1 7 0V30" fill="none" stroke="#1e40af" stroke-width="2.6"/>', "Ciberseguridad"),
    "idea": _insignia("#be185d", '<circle cx="32" cy="27" r="13" fill="#fff"/><path d="M26 38h12v5a3 3 0 0 1-3 3h-6a3 3 0 0 1-3-3z" fill="#fff"/><rect x="27.5" y="48" width="9" height="3.4" rx="1.7" fill="#fff"/>'
                    '<path d="M28 27l4 4 4-4" fill="none" stroke="#be185d" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>', "Innovacion"),
    # --- apalancados e inversos
    "apalancado": _insignia("#b91c1c", '<path d="M13 41L26 28l8 8 16-17" fill="none" stroke="#fff" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"/>'
                            '<polygon points="52,14 52,28 38,14" fill="#fff"/><text x="21" y="55" font-family="Arial,sans-serif" font-size="15" font-weight="700" fill="#fff" text-anchor="middle">3x</text>', "Apalancado 3x"),
    "inverso": _insignia("#334155", '<path d="M32 13v30" stroke="#fff" stroke-width="5.5" stroke-linecap="round"/><polygon points="18,38 46,38 32,53" fill="#fff"/>', "Inverso"),
}

# Para los que se cargan con otro nombre (compatibilidad con los dibujos de Bitcoin y Ethereum, que viven en ui/etfs.py)
NOMBRES = sorted(ICONOS)


def icono(nombre):
    """SVG del icono `nombre` o None si no existe."""
    return ICONOS.get(str(nombre or "").strip())
