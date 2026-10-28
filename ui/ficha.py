"""
Ficha de la pagina de una empresa (v1.2.46; formato tipo Fiscal AI desde la v1.2.47; mosaicos desplegables desde la v1.2.49).

Estructura (arriba la banda con el nombre y el precio; abajo, mosaicos que se pueden plegar):
  1. Encabezado (v1.2.52): logo, nombre, mercado y ticker. A la derecha el precio en dolares y, mas chico, "Precio en pesos $ X (ratio N : 1)".
     (v1.2.52: el "Dato al ..." esta en el pie; el resumen lleva links, cambios de precio y grafico de 10 años; "Estadisticas" paso a "Multiplos de la Empresa".)
  2. "Resumen de la empresa" (desplegable, abierto): la descripcion completa de Yahoo en una banda ancha, la lista de datos (nombre, CEO, sitio web,
     sector, industria, mercado, sede y empleados) y, al lado, la capitalizacion bursatil, el rango de 52 semanas (barrita con el precio de hoy y los
     precios extremos) y el Dividend Yield con su dibujito.
  3. Score de calidad y Valoracion (con un "?" que cuenta, sin detalles del metodo, como se llega a la lectura).
  4. "Estadisticas de la empresa" (desplegable): Perfil, Crecimiento y Valoracion; cada multiplo con su mediana historica, un dibujito (hoy contra
     su mediana), el Fair Value que da y su peso.
  5. "Precio contra el Fair Value de cada metodo" (desplegable): la linea de precios.
  (v1.2.50: se quito "Revision de los metodos del Fair Value" y la columna "Peso": el metodo y los pesos no se muestran al publico.)
Las fuentes no se nombran en cada dato: hay una sola linea "Fuente" debajo del Aviso (ver texto_fuente y ui/marca.py).
Los datos de Yahoo (descripcion, CEO, web, mercado, valor de empresa, acciones, ingresos y crecimiento) vienen de data/fichas.json (bajar_fichas.py).
Si falta alguno, esa fila no se muestra: nunca se inventa un dato (y desde la v1.2.49 ya no hay un resumen escrito a mano de respaldo).

Linea de precios: el precio actual abajo (punto del color de la categoria) y arriba, una flecha celeste por cada metodo del Fair Value
(con su nombre y su valor); la flecha azul oscura es el Fair Value promedio. El PEG sale aparte, en gris, "solo informativo": no entra
al puntaje ni al promedio. La escala es logaritmica (la mitad y el doble del precio quedan a la misma distancia).

No usa JavaScript (los desplegables son <details>). Los signos $ se escriben como &#36; para que el markdown no los tome como formulas.
"""
import ast
import html
import math
import re
from urllib.parse import quote_plus, urlparse

from config.industrias import industria_de
from config.sectors import metricas_de, partes_sector
from data import cedears as _cedears
from data import fichas as _fichas
from ui.banderas import bandera_html
from ui.tabla_visual import (_TEXTO_EN_RELLENO, _celda_dy, _clamp, _dy_datos, _mcap, _money, _n, _svg_dy, _texto_categoria, _txt, barra_52s_html, texto_categoria)

ETIQUETAS_METODO = {"ev_ebitda": "EV/EBITDA", "per": "P/E", "p_fcf": "P/FCF", "p_b": "P/Book", "dividend_yield": "Dividend Yield",
                    "peg": "PEG", "p_ffo": "P/FFO", "p_affo": "P/AFFO", "ps": "P/S", "ev_ventas": "EV/Ventas",
                    "rend_total": "Rendimiento total"}
CELESTE = "#38bdf8"
AZUL = "#1f6aa5"
GRIS_PEG = "#94a3b8"
ALTO_NIVEL = 40            # px por nivel de etiquetas
ANCHO_ETIQUETA = 15.0      # % del ancho que ocupa una etiqueta (para que no se pisen)
PEG_RANGO_MAX = 6.0        # el PEG se dibuja si su precio implicito esta entre 1/6 y 6 veces el precio; si no, queda como nota
ABIERTOS = {"resumen", "estadisticas", "linea"}     # mosaicos que arrancan desplegados (los demas, plegados); se cambia aca
TEXTO_VALORACION = ("Es un modelo basado en múltiplos: compara cuánto cotiza hoy la empresa con lo que solía valer históricamente y lo resume en una escala "
                    "que va de «Significativamente infravalorada» a «Significativamente sobrevalorada». Ejemplo: si suele cotizar a 20 veces su ganancia y hoy "
                    "cotiza a 15, hoy está más barata que lo habitual. El Fair Value es el precio que resultaría si volviera a cotizar como suele hacerlo. "
                    "Ojo: estar barata contra su propia historia no significa que sea un buen negocio. Es una estimación para filtrar y estudiar, no una "
                    "recomendación: investigá la empresa antes de decidir.")

# Mensaje "Aguarde mientras se cargan los datos..." (pagina de la empresa y, desde la v1.2.59, tambien el inicio)
CSS_CARGA = (".fch-carga{display:flex;align-items:center;gap:12px;margin:10px 0;padding:14px 18px;border-radius:12px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a;font-size:17px;font-weight:600}"
             ".fch-giro{width:18px;height:18px;border:3px solid #93c5fd;border-top-color:#1d4ed8;border-radius:50%;animation:fchg 0.9s linear infinite;flex:none}"
             "@keyframes fchg{to{transform:rotate(360deg)}}")

CSS = """
.fch{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;margin:14px 0 8px}
.fch-t{background:#fff;border-radius:14px;box-shadow:0 1px 2px rgba(15,23,42,.05),0 6px 18px rgba(15,23,42,.07);padding:14px 16px 16px;min-width:0;position:relative}
.fch-t::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--ac,#cbd5e1);border-radius:14px 0 0 14px}
.fch-h{font-size:14.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:#0f172a;margin:0 0 10px;padding-left:4px}
.fch-intro{font-size:14px;line-height:1.5;color:#4b5563;margin:2px 4px 12px}
.fch-h small{text-transform:none;letter-spacing:0;font-weight:500;font-size:12px;color:#9ca3af;margin-left:4px}
.fch-b{padding-left:4px;min-width:0}
.s3{grid-column:span 3}.s4{grid-column:span 4}.s5{grid-column:span 5}.s6{grid-column:span 6}.s7{grid-column:span 7}.s8{grid-column:span 8}.s12{grid-column:span 12}
.r2{grid-row:span 2}.r3{grid-row:span 3}
.fch-big{font-size:26px;font-weight:700;color:#0f172a;line-height:1.15;letter-spacing:-.3px}
.fch-big small{display:block;font-size:12px;font-weight:500;color:#6b7280;letter-spacing:0;margin-top:3px}
.fch-mid{font-size:17px;font-weight:600;color:#111827}
.fch-sub{font-size:12.5px;color:#4b5563;margin-top:6px;line-height:1.4}
.fch-sub b{color:#111827}
.fch-val .tv-vl{text-align:left}
.fch-val .tv-ln1,.fch-val .tv-ln2{display:inline}
.fch-val .tv-vh{font-size:12.5px;font-weight:500;color:#6b7280;margin-bottom:1px}
.fch-val .tv-vn{font-size:21px}
.fch-txt{font-size:14.5px;line-height:1.55;color:#1f2937}
.fch-nota{font-size:11.5px;color:#9ca3af;margin-top:8px}
.fch-par{display:flex;gap:18px;flex-wrap:wrap}
.fch-par>div{min-width:0}
.fch-par .fch-k{font-size:11.5px;color:#6b7280;margin-bottom:2px}
.fch-par .fch-v{font-size:19px;font-weight:600;color:#111827}
.fch-sc{display:flex;flex-direction:column;align-items:flex-start;gap:12px}
.fch-sc .num{font-size:72px;line-height:1;font-weight:800;border-radius:16px;padding:16px 22px;min-width:130px;text-align:center;letter-spacing:-2px}
.fch-sc .sub{font-size:12.5px;color:#4b5563;line-height:1.45}
.fch-sc .sub b{color:#111827}
.fch-dy .tv2-dy{text-align:left}
.fch-dy .tv2-dyn{font-size:26px;font-weight:700;color:#0f172a;line-height:1.1}
.fch-dy .tv2-dy img{margin:6px 0 0}
.fch-dy .tv2-dym{font-size:12.5px;margin-top:4px}
.fch-dy .tv2-dym b{font-weight:600}
.fch-sec b{display:block;font-size:16px;font-weight:600;color:#111827}
.fch-sec span{display:block;margin-top:3px;font-size:13.5px;color:#4b5563}
.fch-pais{display:flex;align-items:center;gap:9px;font-size:17px;font-weight:600;color:#111827}
.fch-pl .fch-ex{font-size:12.5px;color:#4b5563;line-height:1.5;margin:0 0 6px 4px}
.pl-wrap{overflow-x:auto;padding:4px 4px 2px}
.pl{position:relative;min-width:640px;margin:0 14px}
.pl-ln{position:absolute;left:0;right:0;height:4px;border-radius:2px;background:#d6e4f0}
.pl-ar{position:absolute;width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;border-top:11px solid var(--c);transform:translateX(-50%)}
.pl-ar.avg{border-left-width:9px;border-right-width:9px;border-top-width:14px}
.pl-st{position:absolute;z-index:1;width:1px;background:var(--c);opacity:.55;transform:translateX(-50%)}
.pl-lb{position:absolute;transform:translateX(-50%);text-align:center;white-space:nowrap;line-height:1.2;width:max-content;background:#fff;padding:1px 4px;border-radius:4px;z-index:2}
.pl-lb .n{font-size:12px;font-weight:600;color:#1f2937}
.pl-lb .v{font-size:12px;color:#4b5563}
.pl-lb.avg .n{color:#1f6aa5}
.pl-lb.peg .n{color:#64748b}
.pl-pt{position:absolute;width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 0 1px #475569,0 1px 3px rgba(15,23,42,.35);transform:translateX(-50%);box-sizing:border-box}
.pl-pl{position:absolute;transform:translateX(-50%);text-align:center;white-space:nowrap;font-size:12.5px;color:#111827;line-height:1.25}
.pl-pl b{font-weight:700}
.pl-leyenda{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 4px 0;font-size:12px;color:#4b5563}
.pl-leyenda i{display:inline-block;width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:8px solid var(--c);margin-right:6px;vertical-align:1px}
.fch-hd{display:flex;align-items:center;gap:18px;flex-wrap:wrap;justify-content:space-between}
.fch-hd .id{display:flex;align-items:center;gap:20px;min-width:0}
.fch-hd .nm{font-size:1.9rem;font-weight:800;line-height:1.15;color:#0f172a;letter-spacing:-.4px}
.fch-hd .sb{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:5px;font-size:14px;color:#374151}
.fch-hd .tk{font-weight:700;color:#111827}
.fch-hd .pr{text-align:right}
.fch-hd .pr .v{font-size:2rem;font-weight:800;color:#0f172a;letter-spacing:-.4px;line-height:1.1}
.fch-hd .pr .ars{font-size:15px;font-weight:400;color:#4b5563;margin-top:4px}
.fch-hd .pr .n{font-size:11.5px;color:#9ca3af;margin-top:2px}
.adr{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.4px;color:#1d4ed8;background:#e8f0fe;border-radius:6px;padding:1px 7px}
.fch-kv{display:grid;grid-template-columns:1fr;margin-top:14px;border-top:1px solid #eef1f4}
.fch-kv>div{display:flex;justify-content:space-between;gap:16px;padding:8px 2px;border-bottom:1px solid #eef1f4;font-size:14px}
.fch-kv .k{color:#4b5563;flex:none}
.fch-kv .v{color:#111827;text-align:right;min-width:0;overflow-wrap:anywhere}
.fch-kv .v a{color:#1d4ed8;text-decoration:none}
.fch-kv .v a:hover{text-decoration:underline}
/* v1.2.49: mosaicos desplegables */
.fch-t.fch-d{padding:0}
.fch-d>summary.fch-h{list-style:none;cursor:pointer;margin:0;padding:14px 16px 14px 20px;display:flex;align-items:center;gap:6px;user-select:none}
.fch-d>summary.fch-h::-webkit-details-marker{display:none}
.fch-d>summary.fch-h::after{content:"";margin-left:auto;width:8px;height:8px;border-right:2px solid #6b7280;border-bottom:2px solid #6b7280;transform:rotate(45deg);transition:transform .15s;flex:none;margin-right:4px}
.fch-d[open]>summary.fch-h::after{transform:rotate(-135deg)}
.fch-d>.fch-b{padding:0 16px 16px 20px}
.fch-q{position:relative;display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#e5e7eb;color:#4b5563;font-size:11px;font-weight:700;margin-left:6px;cursor:help;text-transform:none;letter-spacing:0;line-height:1}
.fch-q .fch-qt{display:none;position:absolute;left:-8px;top:24px;width:max-content;max-width:300px;background:#1f2937;color:#fff;font-size:12.5px;font-weight:400;line-height:1.45;padding:9px 11px;border-radius:8px;z-index:30;text-align:left;white-space:normal;box-shadow:0 6px 18px rgba(15,23,42,.25)}
.fch-q:hover .fch-qt,.fch-q:focus .fch-qt{display:block}
.fch-desc{font-size:14.5px;line-height:1.6;color:#1f2937;margin:0;text-align:justify}
.fch-res{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px 40px;margin-top:16px}
.fch-res .fch-kv{margin-top:0}
.fch-cifras{display:flex;flex-direction:column;gap:18px;min-width:0}
.fch-cf .fch-k{font-size:11.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:#6b7280;margin-bottom:4px}
.fch-cf .grande{font-size:26px;font-weight:700;color:#0f172a;line-height:1.1;letter-spacing:-.3px}
.rng{position:relative;height:8px;border-radius:4px;background:#e5e7eb;margin:30px 8px 4px}
.rng-m{position:absolute;top:-6px;width:3px;height:20px;background:#0f172a;border-radius:2px;transform:translateX(-50%)}
.rng-h{position:absolute;bottom:18px;transform:translateX(-50%);white-space:nowrap;font-size:12.5px;font-weight:700;color:#0f172a}
.rng-x{display:flex;justify-content:space-between;margin-top:8px;font-size:13px;font-weight:600;color:#111827}
.rng-x small{display:block;font-size:11px;font-weight:400;color:#6b7280}
.rng-x span:last-child{text-align:right}
.fch-st2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2.2fr);gap:12px 40px}
.fch-st2 h4{margin:0 0 6px;font-size:13.5px;font-weight:700;color:#111827}
.fch-st2 .f{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:6px 0;border-bottom:1px solid #eef1f4;font-size:13.5px}
.fch-st2 .f .k{color:#4b5563}
.fch-st2 .f .v{font-weight:600;color:#111827;text-align:right;white-space:nowrap}
.fch-st2 .f .v.neg{color:#b91c1c}
.fch-st2 .f .v.pos{color:#15803d}
.fch-st2 .izq>div+div{margin-top:18px}
.vr{display:grid;grid-template-columns:minmax(72px,1.1fr) minmax(56px,.8fr) minmax(70px,1fr) 108px minmax(90px,1.1fr);gap:0 10px;align-items:center;padding:7px 0;border-bottom:1px solid #eef1f4;font-size:13.5px}
.vr.hd{font-size:11px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;color:#6b7280;padding:2px 0 6px}
.vr .m{font-weight:600;color:#111827}
.vr .n{text-align:right;white-space:nowrap}
.vr .d{line-height:0}
.vr .d img{display:block}
.vr .fv small{display:block;font-size:11px;font-weight:600}
.vr .fv .no{color:#9ca3af}
.vr .md small{display:block;font-size:11px;color:#6b7280}
.fch-st2 .nota{font-size:11.5px;color:#6b7280;margin-top:8px;line-height:1.45}
@media (max-width:900px){
.fch-hd .pr{text-align:left}
.fch-res{grid-template-columns:1fr}
.fch-cifras{grid-template-columns:1fr 1fr}
.fch-st2{grid-template-columns:1fr}
.vr{grid-template-columns:1fr 1fr 1fr;grid-template-areas:"m h md" "d fv fv";gap:4px 10px}
.vr.hd{display:none}
.vr .m{grid-area:m}.vr .h{grid-area:h}.vr .md{grid-area:md}.vr .d{grid-area:d}.vr .fv{grid-area:fv}
.vr .n{text-align:left}
.fch-hd .nm{font-size:1.5rem}
}
/* v1.2.52: encabezado mas simple, resumen en mosaico, links, cambios de precio y grafico */
.fch-hd .sb{font-size:15.5px;margin-top:6px}
.fch-hd .tk{font-size:15.5px;font-weight:600;color:#111827}
.fch-k[title],.fch-kv .k[title],.vr .m[title],.hv{cursor:help;border-radius:4px;padding:1px 4px;margin:0 -4px;transition:background .15s}
.fch-k[title]:hover,.fch-kv .k[title]:hover,.vr .m[title]:hover,.hv:hover,.vr.hd [title]:hover{background:#dbe4ff}
.fch-links{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0}
.fch-links a{display:inline-flex;align-items:center;gap:5px;font-size:13px;font-weight:600;color:#1d4ed8!important;background:#eef4ff;border:1px solid #d4e2fb;border-radius:16px;padding:4px 12px;text-decoration:none!important}
.fch-links a:hover{background:#e0ebff}
.fch-res{grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:10px 36px;margin-top:14px;align-items:start}
.fch-cifras{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px 22px}
.fch-cifras .ancho{grid-column:1 / -1}
.cf-fila{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.cf-fila .num{font-size:24px;font-weight:700;color:#0f172a;line-height:1.1;letter-spacing:-.3px}
.cf-fila .med{font-size:11.5px;color:#6b7280;line-height:1.3}
.cf-fila .med b{display:block;font-size:14px;color:#111827}
.cf-fila .dib{line-height:0}
.cambios{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.cambios>div{background:#f8fafc;border:1px solid #eef1f4;border-radius:10px;padding:6px 8px;text-align:center}
.cambios .k{font-size:11px;color:#6b7280}
.cambios .v{font-size:15px;font-weight:700;color:#6b7280}
.cambios .v.pos{color:#15803d}.cambios .v.neg{color:#b91c1c}
.grafico{margin-top:18px;border-top:1px solid #eef1f4;padding-top:12px}
.grafico .gt{font-size:11.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:#6b7280;margin-bottom:6px}
.grafico .gt small{text-transform:none;letter-spacing:0;font-weight:400;color:#9ca3af;margin-left:6px}
.gf{position:relative;height:170px}
.gf svg{position:absolute;left:0;top:0;width:100%;height:100%;display:block}
.gf .ym{position:absolute;right:4px;font-size:11px;font-weight:600;color:#475569;background:rgba(255,255,255,.8);padding:0 3px;border-radius:3px}
.gx{display:flex;justify-content:space-between;font-size:11px;color:#6b7280;margin-top:3px}
.gf-no{font-size:12.5px;color:#6b7280;padding:6px 0}
.fch-carga{display:flex;align-items:center;gap:12px;margin:10px 0;padding:14px 18px;border-radius:12px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a;font-size:17px;font-weight:600}
.fch-giro{width:18px;height:18px;border:3px solid #93c5fd;border-top-color:#1d4ed8;border-radius:50%;animation:fchg 0.9s linear infinite;flex:none}
@keyframes fchg{to{transform:rotate(360deg)}}
.fch-kv .v{white-space:nowrap}
.ddet{margin:0}.ddet>summary{list-style:none;cursor:pointer;display:block}.ddet>summary::-webkit-details-marker{display:none}
.ddet .pv{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:14.5px;line-height:1.6;color:#1f2937;text-align:justify;
-webkit-mask-image:linear-gradient(to bottom,#000 45%,transparent 100%);mask-image:linear-gradient(to bottom,#000 45%,transparent 100%)}
.ddet .vm,.ddet .vl{display:inline-block;margin-top:4px;color:#111827;font-weight:700;font-size:14px}.ddet .vl{display:none}
.ddet[open] .pv,.ddet[open] .vm{display:none}.ddet[open] .vl{display:inline-block;margin-top:8px}
.ddet .full{margin:0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.stats>div{text-align:center;padding:6px 14px;border-left:1px solid #e5e7eb}.stats>div:first-child{border-left:0}
.stats .l{font-size:14px;color:#374151}.stats .v{font-size:30px;font-weight:700;color:#0f172a;line-height:1.25;margin-top:2px}
.stats .v.c{font-size:24px}.stats .n{font-size:13px;color:#9ca3af;margin-top:2px}
.vbar{position:relative;margin:30px 0 4px;padding-top:34px}
.vbar .br{position:absolute;top:0;height:26px;border:1px solid #9ca3af;border-bottom:0;text-align:center}
.vbar .br b{position:absolute;left:50%;top:-24px;transform:translateX(-50%);font-size:16px;white-space:nowrap}
.vbar .bb{height:34px;border-radius:4px;display:flex;align-items:center;padding:0 12px;color:#fff;font-weight:600;font-size:14px;margin-top:6px;white-space:nowrap;min-width:fit-content}
.dps{width:100%;height:auto;display:block}.dps .lb,.dps .gu{opacity:0;pointer-events:none}.dps .gu{stroke:#9ca3af;stroke-dasharray:3 3}.dps .pt:hover .lb,.dps .pt:hover .gu{opacity:1}.dps .pt:hover circle:first-of-type{r:5}.dps .lb text{font-family:inherit}
.vr .y{color:#4b5563}.vscroll{overflow-x:auto}.vwrap{min-width:640px}
@media (max-width:900px){.vr .y{display:none}}
.valrow{display:flex;align-items:center;gap:10px 28px;flex-wrap:wrap}
.valrow .fch-sub{margin:0;font-size:14px}
.vr{text-align:center}.vr .n,.vr.hd .n{text-align:center}.vr .m{text-align:left}.vr.hd span:first-child{text-align:left}
.vr .d{justify-self:center}.vr.hd [title]{cursor:help;border-radius:4px;transition:background .15s}
.fch-2c{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px 40px;align-items:start}
.fch-2c h4{margin:0 0 6px;font-size:13.5px;font-weight:700;color:#111827}
.fch-2c .fch-kv{margin-top:0}
.comp td,.comp th{text-align:center!important}.comp th:first-child,.comp td:first-child{text-align:left!important}.comp.der th:first-child,.comp.der td:first-child{text-align:right!important}
.ceo{display:flex;align-items:center;gap:16px}
.ceo .ft{position:relative;overflow:hidden;width:92px;height:92px;border-radius:50%;background:#e2e8f0;color:#475569;font-size:32px;font-weight:700;display:flex;align-items:center;justify-content:center;flex:none}
.ceo .ft img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center top}
.ceo .nm{font-size:22px;font-weight:700;color:#0f172a;line-height:1.2}.ceo .cg{font-size:14px;color:#4b5563;margin-top:3px}
.fch-st2 .nota,.fch-nota[title]{cursor:help}
.cambios8{grid-template-columns:repeat(8,minmax(0,1fr))}
/* v1.2.54: solapas de la pagina de la empresa (Streamlit las dibuja como div con role=tab): texto gris, la activa en oscuro, mas grandes */
[role="tablist"]{gap:4px;border-bottom:1px solid #d9dee5;flex-wrap:wrap}
[role="tablist"] [role="tab"]{padding:12px 16px;background:transparent}
[role="tablist"] [role="tab"] p{font-size:18px!important;color:#6b7280!important;font-weight:500!important;margin:0}
[role="tablist"] [role="tab"][aria-selected="true"] p{color:#111827!important;font-weight:700!important}
[role="tablist"] [role="tab"]:hover p{color:#111827!important}
[data-testid="stTabsHighlight"],[data-baseweb="tab-highlight"]{background:#111827!important;height:3px!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{font-size:15px!important}
[data-testid="stWidgetLabel"] p{font-size:16px!important}
@media (min-width:901px){.fch>.fch-t:not(:has(.fch-hd)){zoom:1.14}}
.comp tr.tot td{font-weight:700;color:#111827}
.comp-w{overflow-x:auto}
.comp{width:100%;border-collapse:collapse;font-size:14px}
.comp th{font-size:11px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;color:#6b7280;text-align:right;padding:6px 8px;border-bottom:1px solid #e5e7eb;white-space:nowrap}
.comp td{text-align:right;padding:8px;border-bottom:1px solid #eef1f4;white-space:nowrap}
.comp th:first-child,.comp td:first-child{text-align:left}
.comp a{color:#1d4ed8;text-decoration:none;font-weight:600}.comp a:hover{text-decoration:underline}
.comp .tkc{color:#6b7280;font-size:12px;margin-left:4px}
.nlist{list-style:none;margin:0 0 6px;padding:0}.nlist li{padding:9px 0;border-bottom:1px solid #eef1f4}
.nlist a{color:#111827;text-decoration:none;font-weight:600;font-size:15px}.nlist a:hover{color:#1d4ed8;text-decoration:underline}
.nlist .nf{display:block;font-size:12px;color:#6b7280;margin-top:2px}
@media (max-width:900px){
.fch-2c{grid-template-columns:1fr}
.fch-res{grid-template-columns:1fr}
.cambios,.cambios8{grid-template-columns:repeat(4,minmax(0,1fr))}
.fch{gap:12px}
.fch>.fch-t{grid-column:span 12!important;grid-row:auto!important}
.fch-sc .num{font-size:60px}
}
"""


def _dict(x):
    if isinstance(x, dict):
        return x
    if isinstance(x, str) and x.strip():
        try:
            d = ast.literal_eval(x)
            return d if isinstance(d, dict) else {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _ars(v):
    """Pesos: $ 12.345 (sin decimales desde 100) o $ 85.5 (un decimal con punto)."""
    v = _n(v)
    if v is None:
        return "—"
    if v < 100:                      # v1.2.60: un decimal con punto ($ 85.5); desde 100 sin decimales y con punto de miles ($ 15.050)
        return f"&#36;&nbsp;{v:.1f}"
    return "&#36;&nbsp;" + f"{v:,.0f}".replace(",", ".")


def _pct(precio, valor):
    v = int(round((valor - precio) / precio * 100))
    return f"{v:+d}%" if v else "0%"


def metodos_fair_value(row):
    """(metodos, peg_info, peg_nota): metodos = [(clave, etiqueta, precio, peso)] los que entran al Fair Value;
    peg_info = precio implicito por PEG (solo informativo) o None; peg_nota = texto si el PEG quedo fuera de escala."""
    det = _dict(row.get("fair_value_detalle"))
    metodos = []
    for k, d in det.items():
        p = _n(d.get("precio")) if isinstance(d, dict) else None
        if p and p > 0:
            metodos.append((k, ETIQUETAS_METODO.get(k, str(k).upper()), p, _n(d.get("peso")) or 0.0))
    peg_info, nota = None, None
    precio = _n(row.get("precio_cache")) or _n(row.get("precio_actual"))     # el PEG de hoy sale del precio del cache: se usa ese mismo precio
    if "peg" not in det and precio and precio > 0:
        act, med = _n(row.get("peg_actual")), _n(row.get("peg_mediana"))
        if act and med and act > 0 and med > 0:
            impl = precio * med / act
            r = impl / precio
            if 1 / PEG_RANGO_MAX <= r <= PEG_RANGO_MAX:
                peg_info = impl
            else:
                nota = f"El PEG (solo informativo) implicaría un precio de {r:.1f} veces el actual: queda fuera de la escala."
    return metodos, peg_info, nota


def _niveles(items, ancho=ANCHO_ETIQUETA, max_niveles=5):
    """Asigna a cada etiqueta (ya ordenada por posicion) el nivel mas bajo donde no pisa a otra: [(item, nivel)]."""
    ocupados = []     # por nivel: lista de x de etiquetas ya puestas
    res = []
    for it in items:
        for n in range(max_niveles):
            if n == len(ocupados):
                ocupados.append([])
            if all(abs(it["xl"] - x) >= ancho for x in ocupados[n]):
                ocupados[n].append(it["xl"])
                res.append((it, n))
                break
        else:
            n = max_niveles - 1
            ocupados[n].append(it["xl"])
            res.append((it, n))
    return res, max(1, len(ocupados))


def linea_precios_html(row):
    """Mosaico ancho: precio actual abajo y, arriba, el Fair Value de cada metodo (flechas celestes) y el PEG informativo."""
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    color = _txt(row.get("color_hex"), "#6e7781")
    titulo = "Precio contra el Fair Value de cada método"
    if not precio or precio <= 0:
        return _plegable("linea", titulo, '<div class="fch-sub">Sin precio para dibujar la línea.</div>', ac=AZUL, cls="s12 fch-pl")
    metodos, peg_info, peg_nota = metodos_fair_value(row)
    items = [{"tipo": "m", "n": et, "v": p, "tit": f"{et}: precio que resulta de su múltiplo histórico (peso {w*100:.0f}%)"} for _, et, p, w in metodos]
    if fv and fv > 0 and metodos:
        items.append({"tipo": "avg", "n": "Fair Value promedio", "v": fv, "tit": "Promedio de los métodos, con los pesos de su sector"})
    if peg_info:
        items.append({"tipo": "peg", "n": "PEG", "v": peg_info, "tit": "El PEG no entra al puntaje ni al Fair Value: se muestra solo como dato"})
    if not items:
        sin = '<div class="fch-sub">Esta empresa no tiene un Fair Value calculado (faltan datos para sus métodos).</div>'
        return _plegable("linea", titulo, sin, ac=AZUL, cls="s12 fch-pl")
    valores = [i["v"] for i in items] + [precio]
    lo, hi = math.log(min(valores) / 1.12), math.log(max(valores) * 1.12)
    xs = lambda v: 100.0 * (math.log(v) - lo) / (hi - lo)
    for i in items:
        i["x"] = xs(i["v"])
        i["xl"] = _clamp(i["x"], 8.0, 92.0)
    items.sort(key=lambda i: i["x"])
    colocados, T = _niveles(items)
    linea_y = T * ALTO_NIVEL + 16
    alto = linea_y + 64
    xp = xs(precio)
    partes = [f'<div class="pl-ln" style="top:{linea_y}px"></div>']
    for it, n in colocados:
        c = {"m": CELESTE, "avg": AZUL, "peg": GRIS_PEG}[it["tipo"]]
        top_lb = (T - 1 - n) * ALTO_NIVEL
        tope_st = top_lb + 33
        extra = {"m": "", "avg": " avg", "peg": " peg"}[it["tipo"]]
        pct = _pct(precio, it["v"])
        partes.append(f'<div class="pl-lb{extra}" style="left:{it["xl"]:.1f}%;top:{top_lb}px" title="{html.escape(it["tit"], quote=True)}">'
                      f'<div class="n">{html.escape(it["n"])}</div><div class="v">{_money(it["v"])} · {pct}</div></div>')
        partes.append(f'<div class="pl-st" style="--c:{c};left:{it["x"]:.1f}%;top:{tope_st}px;height:{max(0, linea_y - 11 - tope_st)}px"></div>')
        partes.append(f'<div class="pl-ar{extra.replace(" peg", "")}" style="--c:{c};left:{it["x"]:.1f}%;top:{linea_y - (14 if it["tipo"] == "avg" else 11)}px"></div>')
    xpl = _clamp(xp, 9.0, 91.0)
    partes.append(f'<div class="pl-pt" style="left:{xp:.1f}%;top:{linea_y - 7}px;background:{color}" title="Precio actual"></div>')
    partes.append(f'<div class="pl-pl" style="left:{xpl:.1f}%;top:{linea_y + 18}px">Precio actual<br><b>{_money(precio)}</b></div>')
    ley = (f'<div class="pl-leyenda"><span style="--c:{CELESTE}"><i></i>Fair Value según cada método</span>'
           f'<span style="--c:{AZUL}"><i></i>Fair Value promedio</span>'
           + (f'<span style="--c:{GRIS_PEG}"><i></i>PEG: solo informativo, no entra al puntaje</span>' if peg_info else '')
           + '</div>')
    nota = f'<div class="fch-nota">{html.escape(peg_nota)}</div>' if peg_nota else ""
    cat = _txt(row.get("categoria"), "")
    chip = ""
    if cat:
        chip = f' <small style="color:{texto_categoria(color)};font-weight:600">· {_texto_plano_categoria(cat)}</small>'
    titulo = f"Precio contra el Fair Value de cada método{chip}"
    exp = ('<div class="fch-ex">Cada flecha es el precio que resultaría de aplicar un método con la mediana histórica '
           'de su múltiplo; la azul oscura es el promedio ponderado (el Fair Value). Escala logarítmica. Es una estimación, no una recomendación.</div>')
    cuerpo = (f'{exp}<div class="pl-wrap"><div class="pl" style="height:{alto}px">' + "".join(partes) + f'</div></div>{ley}{nota}')
    return _plegable("linea", titulo, cuerpo, ac=AZUL, cls="s12 fch-pl")


def _texto_plano_categoria(cat):
    from scoring.engine import nombre_visible
    from ui.tabla_visual import _mayusculas, _partes_nombre
    return html.escape(_mayusculas(_partes_nombre(nombre_visible(cat))[1]))


def _tile(cls, titulo, cuerpo, ac="#cbd5e1", extra=""):
    return f'<div class="fch-t {cls}" style="--ac:{ac}"><div class="fch-h">{titulo}</div><div class="fch-b">{cuerpo}</div>{extra}</div>'


def _plegable(clave, titulo, cuerpo, ac="#cbd5e1", cls="s12"):
    """Mosaico que se despliega y se pliega (<details>). `clave` decide si arranca abierto (ABIERTOS)."""
    abierto = " open" if clave in ABIERTOS else ""
    return (f'<details class="fch-t fch-d {cls}" data-mosaico="{clave}" style="--ac:{ac}"{abierto}>'
            f'<summary class="fch-h">{titulo}</summary><div class="fch-b">{cuerpo}</div></details>')


def _ayuda(texto):
    """Signo de pregunta con una nota que aparece al pasar el mouse (o al tocarlo en el celular). Solo CSS."""
    return f'<span class="fch-q" tabindex="0">?<span class="fch-qt">{html.escape(texto)}</span></span>'


# ---------------------------------------------------------------------------
# v1.2.47: formato nuevo
# ---------------------------------------------------------------------------

def _abrev(x, prefijo=""):
    """1.234.567.890 -> '1.2B' (M = millon, B = mil millones, T = billon), con un prefijo opcional ('US$ ')."""
    v = _n(x)
    if v is None or v <= 0:
        return "—"
    for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= lim:
            return f"{prefijo}{v / lim:.1f}{suf}"
    return f"{prefijo}{v:,.0f}"


def _usd_abrev(x):
    t = _abrev(x, "US&#36;&nbsp;")
    return t


def _pct_sig(x):
    """0.123 -> '+12.3%' (con color: verde si crece, rojo si cae)."""
    v = _n(x)
    if v is None:
        return None, ""
    return f"{v * 100:+.1f}%", ("pos" if v > 0 else "neg" if v < 0 else "")


def _dominio(url):
    """'https://www.apple.com/' -> 'apple.com' (solo si es un link http/https)."""
    try:
        u = urlparse(str(url or "").strip())
        if u.scheme not in ("http", "https") or not u.netloc:
            return None, None
        return u.netloc.removeprefix("www."), f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}"
    except Exception:  # noqa: BLE001
        return None, None


def _texto_descripcion(ficha):
    """La descripcion de Yahoo en castellano; si solo hay la original, en ingles; si no hay nada, ''. (Desde la v1.2.49 ya no hay un resumen
    escrito a mano de respaldo: sin dato de Yahoo, el mosaico dice que la descripcion esta pendiente.)"""
    es, en = (ficha or {}).get("descripcion_es"), (ficha or {}).get("descripcion_en")
    if isinstance(es, str) and es.strip():
        return es.strip()
    if isinstance(en, str) and en.strip():
        return en.strip()
    return ""


def texto_fuente(ficha=None):
    """Linea "Fuente" que va debajo del Aviso (v1.2.49). Las fuentes no se nombran en cada dato. Si la descripcion es una traduccion automatica,
    lo aclara."""
    t = "Stock Analysis y Yahoo Finance."
    es = (ficha or {}).get("descripcion_es") if ficha is not None else None
    if isinstance(es, str) and es.strip():
        t += " La descripción de la empresa es una traducción automática del texto de Yahoo Finance y puede tener errores."
    return t


def _fecha_ar(texto):
    """'2026-10-22' -> '22/10/2026' (si no tiene ese formato, se devuelve igual)."""
    t = str(texto or "").strip()
    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
        return f"{t[8:10]}/{t[5:7]}/{t[0:4]}"
    return t


def _linea_pesos(row, datos):
    """'CEDEAR: $ 25.394 (ratio 20 : 1)' (chico y gris, debajo del precio en dolares). Sin ratio confirmado no se muestra nada."""
    d = (datos or {}).get(str(row.get("ticker", "")).upper()) or {}
    if not d.get("ratio"):
        return ""
    ratio = _cedears.ratio_texto(d.get("ratio")).replace(" : ", ":")      # v1.2.59: "24:1" (antes "24 : 1")
    ars = _n(d.get("precio_ars"))
    if ars:
        return f'CEDEAR: {_ars(ars)} (Ratio {html.escape(ratio)})'
    return f'CEDEAR: sin precio por ahora (Ratio {html.escape(ratio)})'


def _encabezado(row, mercado, ficha, datos=None, fecha_datos=None):
    """v1.2.52: solo logo, nombre, mercado y ticker (el pais esta en el resumen y el ADR en "Mercado donde cotiza"); el "Dato al ..." paso al pie."""
    t = str(row.get("ticker", ""))
    nombre = html.escape(str(row.get("nombre") or t).strip())
    from ui.logos import logo_html
    tk_txt = f"{html.escape(mercado)}: {html.escape(t)}" if mercado else html.escape(t)
    p = _n(row.get("precio_actual"))
    if p and p > 0:
        pesos = _linea_pesos(row, datos)
        pesos_html = f'<div class="ars">{pesos}</div>' if pesos else ""
        precio = f'<div class="pr"><div class="v">{_money(p)}</div>{pesos_html}</div>'
    else:
        precio = ""
    return (f'<div class="fch-t s12" style="--ac:#64748b"><div class="fch-hd"><div class="id">{logo_html(t, 72)}<div>'
            f'<div class="nm">{nombre}</div><div class="sb"><span class="tk">{tk_txt}</span></div></div></div>{precio}</div></div>')


def _fila_kv(k, v, tip=None):
    t = f' title="{html.escape(tip, quote=True)}"' if tip else ""
    return f'<div><span class="k"{t}>{k}</span><span class="v">{v}</span></div>'


def _barra_52s(row):
    """Rango de 52 semanas (v1.2.52): barrita gris con el precio de hoy arriba y minimo / medio / maximo abajo (ui/tabla_visual.py: barra_52s_html)."""
    return barra_52s_html(row, grande=True) or '<div class="fch-sub" style="margin:0">Sin datos de rango de 52 semanas.</div>'


_FOSO_CACHE = {}

ETAPAS_TIP = {
    "En crecimiento": "Está expandiendo ventas y ganancias a buen ritmo.",
    "Madura": "Negocio estable y consolidado: crece poco y suele repartir buena parte de sus ganancias.",
    "Cíclica o de materias primas": "Sus resultados suben y bajan con el ciclo económico o con el precio de lo que vende.",
    "En declive o dificultades": "Sus ventas o ganancias vienen cayendo o enfrenta problemas importantes.",
    "Con pérdidas y creciendo": "Todavía no gana plata, pero sus ventas crecen.",
}


def _foso_de(ticker):
    """Foso competitivo de la empresa (data/foso.json, armado con foso_desde_lote.py a partir del Modo lote del DCF) o None si no esta."""
    import json, os
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "foso.json")
    try:
        m = os.path.getmtime(ruta)
        if _FOSO_CACHE.get("m") != m:
            with open(ruta, encoding="utf-8") as f:
                _FOSO_CACHE.update(m=m, d=(json.load(f) or {}).get("empresas", {}))
        return _FOSO_CACHE["d"].get(str(ticker).upper())
    except (OSError, ValueError):
        return None


def _fila_dy(row):
    """Dividend Yield con la misma forma que los multiplos: valor de hoy, su mediana historica y el dibujito (hoy contra la mediana)."""
    d = _dy_datos(row)
    if not d:
        return '<div class="cf-fila"><span class="num" style="color:#9ca3af">—</span><span class="med">Sin dato de dividendo</span></div>'
    pct, m, etiqueta, _ = d
    det = _dict(row.get("detalle")).get("dividend_yield")
    score = _n(det.get("score")) if isinstance(det, dict) else None
    med = ""
    if m:
        mtxt = f"{m:.1f}%" if m >= 1 else f"{m:.2f}%"
        med = f'<span class="med">{html.escape(etiqueta)}<b>{mtxt}</b></span>'
    dib = _dibujo_metrica(pct, m, score, invertir=False) if m else ""
    tip = "Marca del centro: su mediana histórica. Punto: hoy. A la derecha, rinde más que lo habitual; a la izquierda, menos."
    dib = f'<span class="dib" title="{html.escape(tip)}">{dib}</span>' if dib else ""
    return f'<div class="cf-fila"><span class="num">{pct:.2f}%</span>{med}{dib}</div>'


def _cambios_html(pares):
    """Cambio del precio en el dia, la semana, el mes y el año (de los cierres de Yahoo, pedidos en el momento). Sin datos: 'no disponible'."""
    from data import historial_precios as _hp
    if not pares:
        return ('<div class="cambios">' + "".join(f'<div><div class="k">{n}</div><div class="v">—</div></div>' for n, _ in _hp.VENTANAS)
                + '</div><div class="fch-nota" style="margin-top:6px">No disponible por ahora (Yahoo no respondió).</div>')
    cel = []
    for nombre, v in _hp.cambios(pares):
        if v is None:
            cel.append(f'<div><div class="k">{nombre}</div><div class="v">—</div></div>')
        else:
            cls = "pos" if v > 0.0005 else "neg" if v < -0.0005 else ""
            txt = f"{v * 100:+.1f}%" if round(v * 100, 1) != 0 else "0.0%"
            cel.append(f'<div><div class="k">{nombre}</div><div class="v {cls}">{txt}</div></div>')
    return '<div class="cambios">' + "".join(cel) + '</div>'


def _grafico_html(pares):
    """Grafico basico del precio de los ultimos 10 años (cierre diario, no en tiempo real), dibujado en SVG sin JavaScript."""
    from data import historial_precios as _hp
    if not pares or len(pares) < 2:
        return ('<div class="grafico"><div class="gt">Precio histórico</div>'
                '<div class="gf-no">Gráfico no disponible por ahora (Yahoo no respondió). Probá de nuevo en unos minutos.</div></div>')
    pts = _hp.reducir(pares, 260)
    f0, f1 = pts[0][0], pts[-1][0]
    dias = max(1, (f1 - f0).days)
    vals = [c for _, c in pts]
    lo, hi = min(vals), max(vals)
    rango = (hi - lo) or 1.0

    def X(f):
        return (f - f0).days / dias * 1000.0

    def Y(c):
        return 96.0 - (c - lo) / rango * 90.0
    lin = " ".join(f"{X(f):.1f},{Y(c):.1f}" for f, c in pts)
    area = f"0,100 {lin} 1000,100"
    guias = "".join(f'<line x1="0" x2="1000" y1="{y}" y2="{y}" stroke="#eef1f4" stroke-width="1" vector-effect="non-scaling-stroke"/>' for y in (6, 51, 96))
    svg = (f'<svg viewBox="0 0 1000 100" preserveAspectRatio="none" role="img" aria-label="Precio de los últimos años">{guias}'
           f'<polygon points="{area}" fill="#1f6aa5" fill-opacity=".10"/>'
           f'<polyline points="{lin}" fill="none" stroke="#1f6aa5" stroke-width="1.6" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>')
    etiquetas = (f'<span class="ym" style="top:0">{_money(hi)}</span><span class="ym" style="bottom:0">{_money(lo)}</span>')
    anios = []
    paso = 1 if f1.year - f0.year <= 6 else 2
    import datetime as _dt
    for a_ in range(f0.year + 1, f1.year + 1, paso):
        x = X(_dt.date(a_, 1, 1)) / 10.0
        if 3 <= x <= 97:
            anios.append(f'<span style="position:absolute;left:{x:.1f}%;transform:translateX(-50%)">{a_}</span>')
    eje = f'<div class="gx" style="position:relative;height:15px">{"".join(anios)}</div>'
    n_anios = dias / 365.25
    titulo = f"Precio de los últimos {round(n_anios)} años" if n_anios >= 1.5 else "Precio histórico"
    return (f'<div class="grafico"><div class="gt">{titulo}<small>cierre diario; no es en tiempo real</small></div>'
            f'<div class="gf">{svg}{etiquetas}</div>{eje}</div>')


def _links_empresa(row, ficha):
    """Links de la empresa, en este orden: Sitio web, SEC Filings y Relaciones con inversores. Esta ultima es una busqueda en Google (con el sitio de la
    empresa, si lo sabemos): no se inventan direcciones, asi que puede no caer directo en la pagina de inversores."""
    t = str(row.get("ticker", ""))
    nombre = str(row.get("nombre") or t).strip()
    dom, url = _dominio((ficha or {}).get("web"))
    q = quote_plus(f'"{nombre}" investor relations' + (f" site:{dom}" if dom else ""))
    tipo = "20-F" if _fichas.es_adr(t) else "10-K"
    sec = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={quote_plus(t)}&type={tipo}&dateb=&owner=include&count=40"
    enl = []
    if dom:
        enl.append((url, f"Sitio web · {dom}", "Sitio oficial de la empresa."))
    enl.append((sec, "SEC Filings", "Informes oficiales que la empresa presenta ante la SEC (10-K anual, 10-Q trimestral; los ADR presentan 20-F). Solo figuran las que reportan a la SEC."))
    enl.append((f"https://www.google.com/search?q={q}", "Relaciones con inversores", "Busca en Google la página de relaciones con inversores de la empresa (informes, presentaciones, resultados)."))
    return '<div class="fch-links">' + "".join(
        f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer" title="{html.escape(tt, quote=True)}">{html.escape(n)} ↗</a>'
        for u, n, tt in enl) + '</div>'


def _tiles_resumen(row, ficha, mercado, agenda=None):
    """v1.2.52: tres mosaicos. Arriba, a todo el ancho, lo que hace la empresa (con sus links); abajo a la izquierda los datos cualitativos (nombre, CEO,
    sector, industria, foso, mercado, sede, empleados) y abajo a la derecha los cuantitativos (capitalizacion, Dividend Yield, rango de 52 semanas, EV,
    acciones, ingresos y crecimiento)."""
    t = str(row.get("ticker", ""))
    f = ficha or {}
    texto = _texto_descripcion(ficha)
    desc = (f'<details class="ddet"><summary><div class="pv">{html.escape(texto)}</div><span class="vm">Ver más ▾</span><span class="vl">Ver menos ▴</span></summary>'
            f'<p class="fch-desc full">{html.escape(texto)}</p></details>' if texto
            else '<div class="fch-sub" style="margin:0">Descripción pendiente de cargar.</div>')
    sector, industria = partes_sector(row.get("sector"))
    sector = _txt(row.get("sector_macro"), "") or sector or ""
    industria = _txt(row.get("industria"), "") or industria_de(t) or ""
    filas = [_fila_kv("Nombre", html.escape(str(row.get("nombre") or t).strip()))]
    if f.get("ceo"):
        filas.append(_fila_kv("CEO", html.escape(re.sub(r"\s+", " ", str(f["ceo"]))), "Director ejecutivo: quien conduce la empresa día a día."))
    filas.append(_fila_kv("Sector", html.escape(sector) or "—", "Gran rubro de la economía al que pertenece la empresa."))
    filas.append(_fila_kv("Industria", html.escape(industria) or "—", "Actividad específica dentro de su sector."))
    foso = _foso_de(t)      # v1.2.51: foso competitivo (Amplio / Estrecho / Ninguno), solo donde hay dato
    if foso and foso.get("foso"):
        filas.append(_fila_kv("Foso competitivo", "<b>" + html.escape(foso["foso"]) + "</b>",
                              "Ventaja competitiva que se sostiene en el tiempo: retorno sobre el capital por encima del costo del capital, márgenes estables y mejores que los de su sector."))
    if foso and foso.get("etapa"):      # v1.2.65: etapa de la empresa (del mismo archivo del foso)
        et = str(foso["etapa"])
        filas.append(_fila_kv("Etapa de la empresa", "<b>" + html.escape(et) + "</b>", ETAPAS_TIP.get(et, "Momento del negocio en el que se encuentra la empresa.")))
    if mercado:
        adr = ' · <span title="ADR: certificado que representa acciones de una empresa extranjera y cotiza en Estados Unidos">ADR</span>' if _fichas.es_adr(t) else ""
        filas.append(_fila_kv("Mercado donde cotiza", html.escape(mercado) + adr, "Bolsa donde se negocia la acción original."))
    pais = row.get("pais")
    ciudad = ", ".join(x for x in (f.get("ciudad"), f.get("region")) if x)
    if isinstance(pais, str) and pais:
        filas.append(_fila_kv("Sede fiscal", f'{bandera_html(pais, chica=True)} ' + html.escape(f"{ciudad}, {pais}" if ciudad else pais),
                              "Lugar donde la empresa tiene su sede y tributa: define en qué país y moneda gana la mayor parte de su negocio y qué impuestos se le aplican."))
    emp = _n(f.get("empleados"))
    if emp:
        filas.append(_fila_kv("Empleados", f"{emp:,.0f}", "Personas empleadas a tiempo completo."))
    cual = '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>"
    # cuantitativos (v1.2.54: todos como filas del mismo estilo; el rango de 52 semanas, en texto)
    dd = _dy_datos(row)
    dy_txt = f"{dd[0]:.2f}%" if dd else "—"
    cuan = [_fila_kv("Capitalización bursátil", _mcap(row.get("market_cap")),
                     "Valor de mercado de la empresa: precio de la acción por la cantidad de acciones en circulación."),
            _fila_kv("Dividend Yield", dy_txt, "Dividendo anual que paga la empresa como porcentaje del precio. El detalle está en las solapas Dividendos y Valuación.")]
    lo, hi = _n(row.get("precio_min_52s")), _n(row.get("precio_max_52s"))
    if lo and hi and hi > lo:
        cuan.append(_fila_kv("Rango de 52 semanas", f"{_money(lo)} – {_money(hi)}", "Del precio más bajo al más alto de los últimos 12 meses."))
    ag = agenda or {}
    beta = _n(ag.get("beta")) if ag.get("beta") is not None else _n(f.get("beta"))
    if beta is not None:
        cuan.append(_fila_kv("Beta", f"{beta:.2f}", "Cuánto se mueve la acción respecto del mercado: 1 se mueve igual; más de 1, más que el mercado; menos de 1, menos."))
    res = ag.get("resultados")
    if res and res[0]:
        f0, f1 = res
        txt = f"{f0.strftime('%d/%m/%Y')} – {f1.strftime('%d/%m/%Y')}" if f1 else f0.strftime("%d/%m/%Y")
        cuan.append(_fila_kv("Fecha de resultados (Earnings Date)", txt,
                             "Día en que la empresa presenta sus resultados trimestrales. Si todavía no la confirmó, es una estimación y puede cambiar."))
    if _n(f.get("ev")):
        cuan.append(_fila_kv("Valor de empresa (EV)", _usd_abrev(f.get("ev")), "Lo que costaría comprar toda la empresa: valor de mercado más deuda, menos caja."))
    if _n(f.get("acciones")):
        cuan.append(_fila_kv("Acciones en circulación", _abrev(f.get("acciones")), "Cantidad de acciones que hay en manos de los inversores."))
    if _n(f.get("ingresos_ttm")):
        cuan.append(_fila_kv("Ingresos (12 meses)", _usd_abrev(f.get("ingresos_ttm")), "Ventas de los últimos 12 meses."))
    for clave, etiqueta in (("cagr_ingresos_3a", "Ingresos, 3 años (anual compuesto)"), ("cagr_eps_3a", "Ganancia por acción, 3 años (anual compuesto)"),
                            ("crec_ingresos_trim", "Ingresos, último trimestre vs año anterior"), ("crec_ganancias_trim", "Ganancias, último trimestre vs año anterior")):
        txt, cls = _pct_sig(f.get(clave))
        if txt:
            cuan.append(_fila_kv(etiqueta, f'<span class="{cls}" style="font-weight:600">{txt}</span>'))
    cuan_h = '<div class="fch-kv" style="margin-top:0">' + "".join(cuan) + "</div>"
    return [_tile("s12", "Resumen de la empresa", desc + _links_empresa(row, ficha), ac="#a78bfa"),
            _tile("s6", "Datos de la empresa", cual, ac="#a78bfa"),
            _tile("s6", "Cifras", cuan_h, ac="#7c3aed")]


def _color_por_ratio(ratio):
    """Color del punto cuando la metrica no tiene puntaje propio: mismos cortes que usa el Dividend Yield (ratio > 1 = mas barata que lo habitual)."""
    from scoring.engine import get_categoria_label
    sc = 85 if ratio >= 1.25 else 64 if ratio >= 1.08 else 50 if ratio >= 0.92 else 36 if ratio >= 0.75 else 15
    return get_categoria_label(sc)[1]


def _dibujo_metrica(actual, mediana, score, invertir):
    """Dibujito de una metrica: la marca del centro es su mediana historica y el punto es hoy; a la derecha = mas barata que lo habitual.
    Para los multiplos (menos es mas barato) se invierte la relacion; para el Dividend Yield (mas es mas barato) no."""
    if not actual or not mediana or actual <= 0 or mediana <= 0:
        return ""
    from scoring.engine import get_categoria_label
    ratio = (mediana / actual) if invertir else (actual / mediana)
    color = get_categoria_label(score)[1] if score is not None else _color_por_ratio(ratio)
    return _svg_dy(ratio, color, W=108, H=18)


def _tile_tamano(row, ficha):
    """v1.2.52: "Tamaño y crecimiento" (plegado): lo que antes estaba a la izquierda de las Estadisticas, sin la capitalizacion (que paso al Resumen)."""
    f = ficha or {}
    perfil = []
    if _n(f.get("ev")):
        perfil.append(("Valor de empresa (EV)", _usd_abrev(f.get("ev"))))
    if _n(f.get("acciones")):
        perfil.append(("Acciones en circulación", _abrev(f.get("acciones"))))
    if _n(f.get("ingresos_ttm")):
        perfil.append(("Ingresos (12 meses)", _usd_abrev(f.get("ingresos_ttm"))))
    # --- Crecimiento ---
    cre = []
    for clave, etiqueta in (("cagr_ingresos_3a", "Ingresos, 3 años (anual compuesto)"), ("cagr_eps_3a", "Ganancia por acción, 3 años (anual compuesto)"),
                            ("crec_ingresos_trim", "Ingresos, último trimestre vs año anterior"), ("crec_ganancias_trim", "Ganancias, último trimestre vs año anterior")):
        txt, cls = _pct_sig(f.get(clave))
        if txt:
            cre.append((etiqueta, f'<span class="v {cls}">{txt}</span>'))

    def col(titulo, filas):
        if not filas:
            return ""
        h = "".join(f'<div class="f"><span class="k">{k}</span>' + (v if v.startswith('<span class="v') else f'<span class="v">{v}</span>') + "</div>" for k, v in filas)
        return f'<div><h4>{titulo}</h4>{h}</div>'

    cuerpo = "".join(c for c in (col("Perfil", perfil), col("Crecimiento", cre)) if c)
    if not cuerpo:
        return ""
    return _plegable("tamano", "Tamaño y crecimiento", f'<div class="fch-st2" style="grid-template-columns:1fr 1fr">{cuerpo}</div>', ac="#0ea5e9")


def _tile_estadisticas(row, ficha, anuales=None):
    """Multiplos de la Empresa (v1.2.52; antes "Estadisticas de la empresa"): solo los multiplos. Una fila por multiplo con el valor de hoy, su mediana
    historica, un dibujito (hoy contra la mediana) y el Fair Value que da."""
    precio = _n(row.get("precio_actual"))
    # --- Valoracion ---
    det = _dict(row.get("detalle"))
    fvd = _dict(row.get("fair_value_detalle"))
    esperados = (metricas_de(row, row.get("sector")) or {}) if row.get("sector") else {}
    filas_v, hay_sin_fv = [], False
    for clave, etiqueta, col_a, col_m in (("per", "P/E", "per_actual", "per_mediana"), ("p_b", "P/Book", "p_b_actual", "p_b_mediana"),
                                           ("ps", "P/S", "ps_actual", "ps_mediana"), ("ev_ventas", "EV/Ventas", "ev_ventas_actual", "ev_ventas_mediana"),
                                           ("ev_ebitda", "EV/EBITDA", "ev_ebitda_actual", "ev_ebitda_mediana"),
                                           ("p_fcf", "P/FCF", "p_fcf_actual", "p_fcf_mediana"), ("p_ffo", "P/FFO", "p_ffo_actual", "p_ffo_mediana"),
                                           ("p_affo", "P/AFFO", "p_affo_actual", "p_affo_mediana"), ("peg", "PEG", "peg_actual", "peg_mediana"),
                                           ("dividend_yield", "Dividend Yield", "dividend_yield_actual", "dividend_yield_mediana"),
                                           ("rend_total", "Rendimiento total", "rend_total_actual", "rend_total_mediana")):
        a, m = _n(row.get(col_a)), _n(row.get(col_m))
        if not a or a <= 0:
            continue
        d = det.get(clave) if isinstance(det.get(clave), dict) else {}
        if d.get("estado") == "descartada":
            continue
        if clave in ("p_ffo", "p_affo", "ev_ventas", "rend_total") and clave not in esperados:
            continue            # P/FFO y P/AFFO solo tienen sentido en los REITs; EV/Ventas y Rendimiento total solo se muestran si la empresa los usa
        es_dy = clave in ("dividend_yield", "rend_total")
        if es_dy:                # el caché guarda el rendimiento como fraccion; la pantalla lo muestra en %
            a = a if a > 1 else a * 100
            m = (m if m > 1 else m * 100) if m and m > 0 else None
            hoy = f"{a:.2f}%"
            med = f"{m:.2f}%" if m else "—"
        else:
            hoy = f"{a:.1f}x"
            med = f"{m:.1f}x" if m and m > 0 else "—"
        sub = '<small>de su sector</small>' if d.get("referencia") == "sector" else ""
        dib = _dibujo_metrica(a, m, _n(d.get("score")), invertir=not es_dy)
        tip = "Marca del centro: su mediana histórica. Punto: hoy. A la derecha, más barata que lo habitual; a la izquierda, más cara."
        dib_html = f'<span class="d" title="{html.escape(tip)}">{dib}</span>' if dib else '<span class="d"></span>'
        pm = _n((fvd.get(clave) or {}).get("precio")) if isinstance(fvd.get(clave), dict) else None
        if pm and pm > 0:
            extra = ""
            if precio and precio > 0:
                v = (pm - precio) / precio
                colr = "#15803d" if v > 0.05 else "#b91c1c" if v < -0.05 else "#a16207"
                extra = f'<small style="color:{colr}">{_pct(precio, pm)}</small>'
            fv_html = f'<span class="n fv"><b>{_money(pm)}</b>{extra}</span>'
        else:
            hay_sin_fv = True
            fv_html = '<span class="n fv"><span class="no" title="No entra al Fair Value de esta empresa">—</span></span>'
        xs = (anuales or {}).get(clave) or {}
        ys = {}
        for an, v in xs.items():
            if v is not None and v > 0:
                v2 = v * 100 if es_dy and v < 1 else v
                ys[an] = f"{v2:.2f}%" if es_dy else f"{v2:.1f}x"
        filas_v.append((etiqueta, ys, hoy, f'<span class="n md">{med}{sub}</span>{dib_html}{fv_html}'))
    val = ""
    if filas_v:
        tip_d = "Marca del centro: su mediana histórica. Punto: hoy. A la derecha, más barata que lo habitual; a la izquierda, más cara."
        tip_f = "Precio que resultaría de aplicar la mediana histórica del múltiplo. Un “—” significa que ese dato se muestra pero no entra al cálculo de esta empresa."
        anios = sorted({a for _, ys, _, _ in filas_v for a in ys})[-5:]
        cols = "minmax(72px,1.1fr) " + "".join("minmax(46px,.6fr) " for _ in anios) + "minmax(56px,.8fr) minmax(70px,1fr) 108px minmax(90px,1.1fr)"
        est = f' style="grid-template-columns:{cols}"'
        cab_y = "".join(f'<span class="n y">{a}</span>' for a in anios)
        cab = (f'<div class="vr hd"{est}><span>Métrica</span>{cab_y}<span class="n">Hoy</span><span class="n">Mediana histórica</span>'
               f'<span title="{html.escape(tip_d)}">Hoy vs. mediana</span><span class="n" title="{html.escape(tip_f)}">Fair Value</span></div>')
        filas_h = []
        for etiqueta, ys, hoy, resto in filas_v:
            cel_y = "".join(f'<span class="n y">{ys.get(a, "—")}</span>' for a in anios)
            filas_h.append(f'<div class="vr"{est}><span class="m">{etiqueta}</span>{cel_y}<span class="n h">{hoy}</span>{resto}</div>')
        nota_moneda = row.get("moneda_nota")      # v1.2.50: antes se mostraba en la "Revisión de los métodos", que se quitó
        moneda = f'<div class="fch-nota">Moneda: {html.escape(nota_moneda)}</div>' if isinstance(nota_moneda, str) and nota_moneda.strip() else ""
        val = f'<div class="vscroll"><div class="vwrap">{cab}{"".join(filas_h)}</div>{moneda}</div>'
    cuerpo = f'<div class="fch-st2" style="grid-template-columns:1fr">{val}</div>' if val else '<div class="fch-sub">Sin múltiplos disponibles para esta empresa.</div>'
    return _plegable("estadisticas", "Múltiplos de la Empresa", cuerpo, ac="#3b82f6")


def _tile_score(row):
    color = _txt(row.get("color_hex"), "#6e7781")
    s = _n(row.get("score_total"))
    num = f"{s:.0f}" if s is not None else "—"
    txt = _TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")
    u, t = _n(row.get("metricas_usadas")), _n(row.get("metricas_total"))
    met = f" Calculado con {int(u)} de {int(t)} métricas." if u is not None and t else ""
    cuerpo = (f'<div class="fch-sc"><div class="num" style="background:{color};color:{txt}">{num}</div>'
              f'<div class="sub"><b>De 0 a 100.</b> Por ahora es el puntaje de precio del screener (0 = más cara, 100 = más barata): '
              f'más adelante el Score de calidad sumará la calidad del negocio.{met}</div></div>')
    return _tile("s6", "Score de calidad", cuerpo, ac=color)


def _tile_valoracion(row):
    """v1.2.56: numeros grandes (precio de hoy, Fair Value, distancia y categoria con su "?") y, debajo, dos barras a la misma escala: el precio y el Fair Value."""
    color = _txt(row.get("color_hex"), "#6e7781")
    precio, fv = _n(row.get("precio_actual")), _n(row.get("fair_value"))
    cat = _texto_categoria(_txt(row.get("categoria"), "—"), color, True)
    bloque_cat = f'<div><div class="l">Valoración por Múltiplos {_ayuda(TEXTO_VALORACION)}</div><div class="v c">{cat}</div></div>'
    if not (precio and fv and precio > 0 and fv > 0):
        cuerpo = f'<div class="stats">{bloque_cat}</div><div class="fch-sub" style="margin:10px 0 0">Sin Fair Value: faltan datos para calcularlo.</div>'
        return f'<div class="fch-t s12" style="--ac:{color}"><div class="fch-b">{cuerpo}</div></div>'
    dif = (fv - precio) / precio
    dif_cls = "pos" if dif > 0.0005 else "neg" if dif < -0.0005 else ""
    dif_txt = f"{dif * 100:+.0f}%" if round(dif * 100) != 0 else "0%"
    stats = ('<div class="stats">'
             f'<div><div class="l">Precio de hoy</div><div class="v">{_money(precio)}</div><div class="n">Cotización actual</div></div>'
             f'<div><div class="l">Fair Value</div><div class="v">{_money(fv)}</div><div class="n">Precio estimado según múltiplos históricos</div></div>'
             f'<div><div class="l">Fair Value vs. precio</div><div class="v {dif_cls}">{dif_txt}</div></div>'
             + bloque_cat + '</div>')
    M = max(precio, fv) * 1.12
    wp, wf = precio / M * 100, fv / M * 100
    lo, hi = min(wp, wf), max(wp, wf)
    col_dif = "#15803d" if dif > 0.0005 else "#b91c1c" if dif < -0.0005 else "#6b7280"
    barras = (f'<div class="vbar"><div class="br" style="left:{lo:.2f}%;width:{hi - lo:.2f}%"><b style="color:{col_dif}">{dif_txt}</b></div>'
              f'<div class="bb" style="width:{wp:.2f}%;background:#4b5563">Precio de hoy · {_money(precio)}</div>'
              f'<div class="bb" style="width:{wf:.2f}%;background:#2563eb">Fair Value · {_money(fv)}</div></div>')
    return f'<div class="fch-t s12" style="--ac:{color}"><div class="fch-b">{stats}{barras}</div></div>'


def ficha_html(row, cedears=None, ficha=None, mercado_codigo=None, fecha_datos=None, historial=None):
    """Compatibilidad (v1.2.52): encabezado + solapas Resumen, Analisis y Valuacion juntas. La pagina usa `encabezado_html` y las `tab_*` por separado."""
    datos = cedears if cedears is not None else _cedears.cargar()
    mercado, adr = _fichas.mercado_y_adr(row.get("ticker"), ficha, mercado_codigo)
    mosaicos = [_encabezado(row, mercado, ficha, datos, fecha_datos), tab_resumen(row, ficha, mercado, False), tab_analisis(row), tab_valuacion(row, ficha, False)]
    return '<div class="fch">' + "".join(m for m in mosaicos if m) + "</div>"


def encabezado_html(row, cedears=None, ficha=None, mercado_codigo=None, fecha_datos=None):
    """La banda de arriba de la pagina de la empresa (logo, nombre, mercado, ticker y precio), fuera de las solapas."""
    datos = cedears if cedears is not None else _cedears.cargar()
    mercado, _ = _fichas.mercado_y_adr(row.get("ticker"), ficha, mercado_codigo)
    return '<div class="fch">' + _encabezado(row, mercado, ficha, datos, fecha_datos) + "</div>"


INTROS = {
    "resumen": "Qué hace la empresa, dónde cotiza y sus números básicos de un vistazo: tamaño, dividendo, rango de precio del último año y cuándo presenta resultados.",
    "analisis": "Un informe breve de la empresa: resumen con su conclusión y el Score, el negocio y su ventaja, puntos fuertes y débiles, cómo entender los números (deuda y gerencia incluidas), qué vigilar y conclusión. La tabla la calcula el programa; el texto es de inteligencia artificial. Informativo: no es una recomendación.",
    "grafico": "Cómo se movió el precio de la acción, cuánto rindió en distintos plazos y qué dicen los indicadores técnicos (rango de 52 semanas, promedios móviles, RSI, MACD y riesgo). Es información sobre el pasado del precio, no una señal de compra o venta.",
    "valuacion": "Una estimación sobre si la empresa cotiza cara o barata frente a sí misma: compara sus múltiplos de hoy con los de años anteriores y con su mediana.",
    "estados": "Las cuentas que la empresa publica: qué vende y cuánto gana (resultados), qué tiene y qué debe (balance) y cómo entra y sale el dinero (flujo de efectivo). Pasá el mouse por cada concepto para ver qué significa.",
    "dividendos": "Cuánto paga la empresa a sus accionistas en concepto de dividendo y si el mismo es sostenible.",
    "competidores": "Las empresas del mismo sector que cotizan como CEDEARs, para compararlas lado a lado en valoración y puntaje de calidad.",
    "directivos": "Quiénes conducen la empresa y cuánto cobran. El CEO es el máximo responsable ejecutivo: el que toma las decisiones del día a día.",
    "accionariado": "Quiénes son los dueños: los directivos (insiders) y las instituciones (fondos, bancos). Que los directivos tengan acciones suele alinear sus intereses con los de los demás accionistas.",
    "noticias": "Los últimos titulares sobre la empresa, en su idioma original, con link a cada nota.",
}


def con_intro(clave, cuerpo):
    """Antepone a una solapa su explicacion corta (breve y educativa)."""
    t = INTROS.get(clave)
    return (f'<div class="fch-intro">{html.escape(t)}</div>' if t else "") + cuerpo


def _env(*partes):
    return '<div class="fch">' + "".join(p for p in partes if p) + "</div>"


def tab_resumen(row, ficha, mercado, envolver=True, agenda=None):
    t = _tiles_resumen(row, ficha, mercado, agenda)
    return _env(*t) if envolver else "".join(t)


def _negrita(txt):
    """Escapa el texto y convierte **frase** en negrita (el único formato que admiten los textos del análisis)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(txt or "")))


def _texto_af(txt):
    """Texto del análisis: párrafos separados por línea en blanco; las líneas que empiezan con "- " forman una lista; **así** = negrita."""
    out, lista = [], []

    def cerrar():
        if lista:
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in lista) + "</ul>")
            lista.clear()
    for linea in str(txt or "").replace("\r", "").split("\n"):
        l = linea.strip()
        if l.startswith(("- ", "• ", "* ")):
            lista.append(_negrita(l[2:].strip()))
        elif not l:
            cerrar()
        else:
            cerrar()
            out.append(f"<p>{_negrita(l)}</p>")
    cerrar()
    return "".join(out)


_CSS_AF = ('<style>.af p{margin:0 0 .75em;font-size:14.5px;line-height:1.6;color:#1f2937;text-align:justify}.af ul,.af ol{margin:0 0 .7em 1.1em;padding:0}'
           '.af li{margin:0 0 .4em;font-size:14.5px;line-height:1.55;color:#1f2937;text-align:justify}.af b{font-weight:700;color:#0f172a}'
           '.af h4{margin:1.1em 0 .4em;font-size:14.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:#0f172a}.af h4:first-child{margin-top:0}'
           '.af-rs{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}.af-rs>.af-rt{flex:1 1 420px;min-width:0}.af-rs>.af-sc{flex:0 0 190px;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center}'
           '.af-sc .num{font-size:64px;line-height:1;font-weight:800;border-radius:16px;padding:16px 22px;min-width:130px;letter-spacing:-2px}.af-sc .l{font-size:12.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#0f172a}'
           '.af-sc .s{font-size:12px;color:#4b5563;line-height:1.4}.af-cx{margin:.8em 0 0;padding:12px 14px;border-radius:12px;line-height:1.6}.af-cx p{margin:0 0 .5em}.af-cx p:last-child{margin:0}'
           '.af-ia{display:inline-block;margin:0 0 .6em;padding:2px 10px;'
           'border-radius:999px;background:#eef2f7;font-size:.82rem}.af-pie{font-size:.8rem;opacity:.75;line-height:1.45}'
           '.af-tw{overflow-x:auto;margin:0 0 .6em}.af-tb{border-collapse:collapse;width:100%;font-size:.84rem;white-space:nowrap}'
           '.af-tb th{text-align:right;font-weight:600;padding:5px 9px;border-bottom:2px solid #cbd5e1;background:#f8fafc}.af-tb th:first-child{text-align:left}'
           '.af-tb td{text-align:right;padding:4px 9px;border-bottom:1px solid #e2e8f0}.af-tb td.a{text-align:left;font-weight:600}.af-tb tr:last-child td{background:#f8fafc}'
           '.af-st{font-size:.86rem;margin:0 0 .6em 1.1em;padding:0;opacity:.9}.af-st li{margin:0 0 .2em}.af-nt{font-size:.82rem;margin:0 0 .6em;padding:6px 10px;border-left:3px solid #f59e0b;'
           'background:#fffbeb}.af-ch{display:inline-block;margin-left:8px;padding:1px 9px;border-radius:999px;font-size:.74rem;font-weight:700;vertical-align:middle;white-space:nowrap}'
           '.af-ch.f{background:#dcfce7;color:#166534}.af-ch.m{background:#fef3c7;color:#92400e}.af-ch.v{background:#fee2e2;color:#991b1b}.af-ch.i{background:#e2e8f0;color:#334155}'
           '.af-lb{font-weight:700;font-size:.85rem;margin:.5em 0 .2em}.af-sin{width:100%;border-collapse:collapse;font-size:.88rem}.af-sin td{padding:5px 8px;border-bottom:1px solid #e2e8f0;vertical-align:top}'
           '.af-sin td:first-child{font-weight:600;white-space:nowrap}.af-cc{margin:.6em 0 0;padding:8px 12px;border-radius:10px;background:#f1f5f9;line-height:1.5}'
           '.af-vd{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;margin:0 0 .8em}.af-cal{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:700;font-size:.86rem}'
           '.af-vt{font-weight:700;font-size:1rem;line-height:1.35}.af-vz th:first-child,.af-vz td:first-child{text-align:left;font-weight:600}'
           '.af-vz tbody th{text-align:left;font-weight:600;padding:5px 9px;border-bottom:1px solid #e2e8f0;background:transparent}'
           '.af ol{margin:0 0 .7em 1.2em;padding:0}</style>')

_CH_AF = {"Favorable": "f", "Mixto": "m", "A vigilar": "v", "Informativo": "i"}


def _chip_af(et):
    return f'<span class="af-ch {_CH_AF[et]}">{html.escape(et)}</span>' if et in _CH_AF else ""


def _pie_af(af):
    modelo = html.escape(str(af.get("modelo") or ""))
    return ('<div class="fch-sub af-pie" style="margin:4px 4px 0;grid-column:1/-1">Informe redactado con inteligencia artificial'
            + (f" ({modelo})" if modelo else "") + (f", el {html.escape(str(af['fecha']))}" if af.get("fecha") else "")
            + ', a partir de los datos de Yahoo Finance (la tabla la calcula el programa). Puede contener errores o quedar desactualizado: verificá siempre con los documentos '
            'oficiales de la empresa. Es información con fines educativos, no una recomendación de inversión.</div>')


def _tiles_analisis_v1(af):
    """Formato de la v1.2.68 (Resumen / Desarrollo / Conclusión), por si quedó algún análisis guardado con ese esquema."""
    ia = (f'<div class="af-ia">Riesgo de la inteligencia artificial a 10 años: <b>{html.escape(af["riesgo_ia"].capitalize())}</b></div>') if af.get("riesgo_ia") else ""
    res = _tile("s12", "Resumen", _CSS_AF + f'<div class="af">{ia}{_texto_af(af.get("resumen"))}</div>', ac="#0ea5e9")
    cuerpo = "".join(f"<h4>{html.escape(x['titulo'])}</h4>{_texto_af(x['texto'])}" for x in af.get("desarrollo") or [])
    des = _tile("s12", "Desarrollo y tesis de inversión", f'<div class="af">{cuerpo}</div>', ac="#8b5cf6")
    con = _tile("s12", "Conclusión", f'<div class="af">{_texto_af(af.get("conclusion"))}</div>', ac="#16a34a")
    return [res, des, con, _pie_af(af)]


def _lista_af(items, ordenada=False):
    tag = "ol" if ordenada else "ul"
    return f'<div class="af"><{tag}>' + "".join(f"<li>{_negrita(x)}</li>" for x in items) + f"</{tag}></div>"


def _score_af(row):
    """Columna derecha del Resumen: Score (por ahora, el puntaje del modelo) en color con el número en blanco o negro según el fondo."""
    color = _txt((row or {}).get("color_hex"), "#6e7781")
    sc = _n((row or {}).get("score_total"))
    num = f"{sc:.0f}" if sc is not None else "—"
    txt = _TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")
    return (f'<div class="af-sc"><div class="l">Score de calidad</div><div class="num" style="background:{color};color:{txt}">{num}</div>'
            '<div class="s"><b>De 0 a 100.</b> Por ahora es el puntaje del modelo (0 = más cara, 100 = más barata); luego sumará la calidad del negocio.</div></div>')


def tiles_analisis(af, estados=None, row=None):
    """Análisis Fundamental v3 (data/analisis_fundamental.py), igual para todas las empresas: Resumen (texto a la izquierda, Score a la derecha), el negocio, el foso,
    puntos fuertes y débiles, "Entendiendo los números" (números, deuda y gerencia), qué vigilar, conclusión (con el color de la calidad y una frase que la cruza con la
    valoración de hoy), fuentes (siempre las mismas) y aclaración. Sin 'calidad' en el análisis (formato viejo) usa el formato anterior."""
    from data import af_perfiles as AP
    from data import analisis_fundamental as AF
    cal = af.get("calidad")
    if cal not in AF.CALIDADES:
        return _tiles_analisis_v1(af)
    color = AF.CALIDADES[cal]
    txt_color = _TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")
    perfil = af.get("perfil") if af.get("perfil") in AP.PERFILES else "general"
    cabeza = (f'<div class="af-vd" style="--cc:{color}"><span class="af-cal" style="background:{color};color:{txt_color}">Calidad del negocio: {html.escape(cal)}</span>'
              f'<span class="af-vt">{html.escape(af.get("veredicto", ""))}</span></div>')
    resumen = re.sub(r"(?<!\*)Conclusión:", "**Conclusión:**", str(af.get("resumen") or ""))
    texto = f'<div class="af-rt">{cabeza}{_texto_af(resumen)}</div>'
    cuerpo = f'<div class="af"><div class="af-rs">{texto}{_score_af(row) if row is not None else ""}</div></div>'
    t = [_tile("s12", "Resumen", _CSS_AF + cuerpo, ac=color)]
    titulos = dict(AF.SECCIONES)
    titulos["balance"] = AP.titulo_balance(perfil)
    for clave in ("negocio", "foso"):
        if af.get(clave):
            t.append(_tile("s12", html.escape(titulos[clave]), f'<div class="af">{_texto_af(af[clave])}</div>', ac="#8b5cf6"))
    if af.get("fortalezas"):
        t.append(_tile("s6", "Puntos fuertes", _lista_af(af["fortalezas"]), ac="#16a34a"))
    if af.get("debilidades"):
        t.append(_tile("s6", "Puntos débiles y riesgos", _lista_af(af["debilidades"], True) + '<div class="fch-sub af-pie" style="margin:0">Del más al menos importante.</div>', ac="#dc2626"))
    nums = "".join(f"<h4>{html.escape(titulos[c])}</h4>{_texto_af(af[c])}" for c in ("numeros", "balance", "gerencia") if af.get(c))
    if nums:
        t.append(_tile("s12", "Entendiendo los números", f'<div class="af">{nums}</div>', ac="#0ea5e9"))
    if af.get("vigilar"):
        t.append(_tile("s12", "Qué vigilar", _lista_af(af["vigilar"]), ac="#f59e0b"))
    cr = AF.cruce(cal, (row or {}).get("categoria")) if row is not None else ""
    est = f' style="color:{txt_color}"'
    cr_html = (f'<p{est[:-1]};margin-top:.7em;padding-top:.6em;border-top:1px solid {txt_color}66"><b{est}>Calidad y precio hoy:</b> {html.escape(cr)}</p>') if cr else ""
    conc = _texto_af(af.get("conclusion")).replace("<p>", f"<p{est}>").replace("<b>", f"<b{est}>")
    t.append(_tile("s12", "Conclusión", f'<div class="af"><div class="af-cx" style="background:{color};color:{txt_color}">'
                   f'<p{est[:-1]};font-size:16px"><b{est}>{html.escape(af.get("veredicto", ""))}</b></p>{conc}{cr_html}</div></div>', ac=color))
    t.append(_tile("s12", "Fuentes", '<div class="af"><ul class="af-st" style="margin-left:1.1em">' + "".join(f"<li>{html.escape(x)}</li>" for x in AF.FUENTES) + "</ul></div>", ac="#94a3b8"))
    t.append(_pie_af(af))
    return t


def tab_analisis(row, envolver=True, af=None, estados=None):
    """Análisis Fundamental: Resumen, parte cualitativa, los números punto por punto, fortalezas/debilidades, tesis y conclusión (ver data/analisis_fundamental.py); al final,
    el puntaje actual del modelo (el Score de calidad llega más adelante). Sin análisis guardado para la empresa: 'Próximamente'."""
    if af and af.get("resumen"):
        t = tiles_analisis(af, estados, row)
    else:
        t = [_tile_score(row), _tile("s12", "Resumen fundamental", '<div class="fch-sub" style="margin:0">Próximamente: un resumen del negocio y de sus fundamentos, con sus puntos fuertes, débiles y la tesis de inversión.</div>', ac="#94a3b8")]
    return _env(*t) if envolver else "".join(t)


def tab_valuacion(row, ficha, envolver=True, anuales=None):
    t = [_tile_valoracion(row), _tile_estadisticas(row, ficha, anuales), linea_precios_html(row)]
    return _env(*t) if envolver else "".join(t)


def rendimientos_html(pares):
    """Tabla de retornos: 1D, 5D, 1M, 3M, YTD, 1A, 5A y MAX (de los cierres de Yahoo). Sin datos: lo dice."""
    from data import historial_precios as _hp
    if not pares:
        return '<div class="fch-sub" style="margin:0">Rendimientos no disponibles por ahora (Yahoo no respondió).</div>'
    cel = []
    for m, v in _hp.rendimientos(pares):
        if v is None:
            cel.append(f'<div><div class="k">{m}</div><div class="v">—</div></div>')
        else:
            cls = "pos" if v > 0.0005 else "neg" if v < -0.0005 else ""
            txt = f"{v * 100:+.1f}%" if round(v * 100, 1) != 0 else "0.0%"
            cel.append(f'<div><div class="k">{m}</div><div class="v {cls}">{txt}</div></div>')
    return '<div class="cambios cambios8">' + "".join(cel) + '</div>'


def tab_grafico_tabla(pares):
    """Parte HTML de la solapa Grafico y rendimiento (el grafico interactivo lo dibuja la app con Altair)."""
    return _env(_tile("s12", "Rendimiento", rendimientos_html(pares), ac="#0ea5e9"))


def _fmt_fecha(f):
    return f.strftime("%d/%m/%Y") if f else "—"


def _money_dec(m):
    v = _n(m)
    if v is None:
        return "—"
    return f"US&#36;&nbsp;{v:,.2f}" if v >= 0.1 else f"US&#36;&nbsp;{v:,.4f}"


def _svg_dps(anuales):
    """Dividendo anual por accion (anios completos): area y puntos, en SVG."""
    pts = [(int(y), float(v)) for y, v in (anuales or []) if v is not None]
    if len(pts) < 2:
        return ""
    W, H, ml, mr, mt, mb = 640, 220, 46, 12, 14, 26
    y0, y1 = pts[0][0], pts[-1][0]
    vmax = max(v for _, v in pts) * 1.1 or 1.0
    X = lambda y: ml + (y - y0) / max(1, (y1 - y0)) * (W - ml - mr)
    Y = lambda v: mt + (1 - v / vmax) * (H - mt - mb)
    linea = " ".join(f"{X(y):.1f},{Y(v):.1f}" for y, v in pts)
    area = f"{X(y0):.1f},{H - mb} " + linea + f" {X(y1):.1f},{H - mb}"
    grid = ""
    for k in range(5):
        v = vmax * k / 4
        yy = Y(v)
        grid += f'<line x1="{ml}" y1="{yy:.1f}" x2="{W - mr}" y2="{yy:.1f}" stroke="#e5e7eb" stroke-dasharray="2 3"/><text x="{ml - 6}" y="{yy + 4:.1f}" font-size="11" text-anchor="end" fill="#9ca3af">${v:.2f}</text>'
    paso = max(1, round((y1 - y0) / 6))
    ejes = "".join(f'<text x="{X(y):.1f}" y="{H - 8}" font-size="11" text-anchor="middle" fill="#9ca3af">{y}</text>' for y in range(y0, y1 + 1, paso))
    puntos = ""
    for y, v in pts:
        cx, cy = X(y), Y(v)
        ancho = 62
        tx = min(max(cx, ml + ancho / 2), W - mr - ancho / 2)
        puntos += (f'<g class="pt"><line x1="{cx:.1f}" y1="{mt}" x2="{cx:.1f}" y2="{H - mb}" class="gu"/>'
                   f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#374151"/><circle cx="{cx:.1f}" cy="{cy:.1f}" r="16" fill="transparent"><title>{y}: US$ {v:.2f}</title></circle>'
                   f'<g class="lb"><rect x="{tx - ancho / 2:.1f}" y="{max(0, cy - 34):.1f}" width="{ancho}" height="22" rx="5" fill="#111827"/>'
                   f'<text x="{tx:.1f}" y="{max(0, cy - 34) + 15:.1f}" font-size="12" font-weight="600" text-anchor="middle" fill="#fff">{y} · ${v:.2f}</text></g></g>')
    return (f'<svg class="dps" viewBox="0 0 {W} {H}" role="img" aria-label="Dividendo anual por acción">{grid}{ejes}'
            f'<polygon points="{area}" fill="#16a34a" fill-opacity=".10"/><polyline points="{linea}" fill="none" stroke="#16a34a" stroke-width="2"/>{puntos}</svg>')


_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _frecuencia(tray):
    n = (tray or {}).get("pagos_anio")
    if not n:
        return None
    nombre = {1: "Anual", 2: "Semestral", 4: "Trimestral", 12: "Mensual"}.get(n, f"{n} pagos por año")
    meses = ", ".join(_MESES[m - 1] for m in (tray.get("meses_pago") or []) if 1 <= m <= 12)
    return nombre, meses


def _tile_recesion(rec):
    """Como se comporto el dividendo de la empresa en la crisis de 2007-09 (total pagado en 2009 contra el de 2007). Sin dato: no se muestra."""
    rec = rec or {}
    d = rec.get("dividendo")
    txt = {"aumento": "Aumentó", "igual": "Se mantuvo", "recorte": "Recortó", "no_pagaba": "No pagaba"}.get(d)
    if not txt:
        return ""
    bl = f'<div><div class="l">Dividendo en la recesión</div><div class="v c">{txt}</div><div class="n">Total pagado en 2009 contra el de 2007</div></div>'
    return _tile("s12", "Comportamiento en la recesión 2007-09", '<div class="stats">' + bl + "</div>", ac="#16a34a")


def tab_dividendos(row, div, rec=None):
    """Dividend Yield contra su mediana (dibujito) y, de Yahoo: ultima fecha ex-dividendo, fecha de pago, monto, anios pagando, anios de aumentos seguidos y
    crecimiento anual compuesto (CAGR) del dividendo. v1.2.53: mas compacto (dos mosaicos lado a lado)."""
    dy = _tile("s4", "Dividend Yield contra su mediana", f'<div class="fch-dy">{_celda_dy(row, grande=True)}</div>', ac="#16a34a")
    if not div:
        return _env(dy, _tile("s12", "Fechas y montos", '<div class="fch-sub" style="margin:0">Datos de dividendos no disponibles por ahora (la empresa no paga, o no hubo respuesta).</div>', ac="#16a34a"), _tile_recesion(rec))
    filas = [_fila_kv("Última fecha ex-dividendo", _fmt_fecha(div.get("ex_fecha")),
                      "Si comprás la acción antes de esta fecha, cobrás ese dividendo; si comprás desde esa fecha, no."),
             _fila_kv("Fecha de pago", _fmt_fecha(div.get("pago_fecha")), "Día en que la empresa deposita el dividendo."),
             _fila_kv("Monto por acción (último)", _money_dec(div.get("monto")), "Dólares por acción del último pago.")]
    if div.get("tasa_anual"):
        filas.append(_fila_kv("Dividendo anual por acción", _money_dec(div["tasa_anual"]), "Lo que se estima que paga en un año."))
    fr = _frecuencia(div.get("trayectoria"))
    if fr:
        filas.append(_fila_kv("Frecuencia", fr[0] + (f" ({fr[1]})" if fr[1] else ""), "Cada cuánto paga, según los pagos del último año completo."))
    cuerpo_izq = '<div class="fch-kv" style="margin-top:0">' + "".join(filas) + "</div>"
    if div.get("ultimos"):
        tip = "Fechas y montos de los pagos; si la empresa no anunció el próximo pago, se ve el último."
        cuerpo_izq += (f'<div class="hv fch-k" title="{html.escape(tip, quote=True)}" style="margin:14px 0 4px;font-size:11.5px;font-weight:600;letter-spacing:.4px;'
                       'text-transform:uppercase;color:#6b7280;display:inline-block">Últimos pagos</div>'
                       '<div class="fch-kv" style="margin-top:0">' + "".join(_fila_kv(_fmt_fecha(f), _money_dec(m)) for f, m in div["ultimos"]) + "</div>")
    izq = _tile("s4", "Próximo pago", cuerpo_izq, ac="#16a34a")
    tr = div.get("trayectoria") or {}
    fil2 = []
    for n, rot in ((1, "1 año"), (3, "3 años"), (5, "5 años"), (10, "10 años")):
        v = (tr.get("cagr") or {}).get(n)
        if v is not None:
            txt, cls = _pct_sig(v)
            fil2.append(_fila_kv(f"Crecimiento anual, {rot}", f'<span class="{cls}" style="font-weight:600">{txt}</span>',
                                 "Cuánto creció por año, en promedio (anual compuesto), el total de dividendos pagados por acción en ese plazo."))
    if not fil2:
        fil2 = [_fila_kv("Historial", "sin datos suficientes")]
    der = _tile("s4", "Crecimiento del dividendo", '<div class="fch-kv" style="margin-top:0">' + "".join(fil2) + "</div>", ac="#16a34a")
    tiles = [dy, izq, der]
    m = div.get("metricas") or {}
    def _pc(v):
        return f"{v * 100:.0f}%" if v is not None else "—"
    bloques = []
    if m.get("payout_eps") is not None:
        bloques.append(f'<div><div class="l">Payout de ganancias</div><div class="v">{_pc(m["payout_eps"])}</div><div class="n">Parte de las ganancias que se paga como dividendo</div></div>')
    if m.get("payout_fcf") is not None:
        bloques.append(f'<div><div class="l">Payout de flujo de caja</div><div class="v">{_pc(m["payout_fcf"])}</div><div class="n">Parte del flujo de caja libre que se paga como dividendo</div></div>')
    if m.get("deuda_neta_ebitda") is not None:
        bloques.append(f'<div><div class="l">Deuda neta / EBITDA</div><div class="v">{m["deuda_neta_ebitda"]:.2f}</div><div class="n">Años de EBITDA que haría falta para pagar la deuda neta</div></div>')
    if tr.get("anios_pagando"):
        bloques.append(f'<div><div class="l">Racha de pagos</div><div class="v">{tr["anios_pagando"]} {"año" if tr["anios_pagando"] == 1 else "años"}</div><div class="n">Pagando dividendos, según el historial disponible</div></div>')
        bloques.append(f'<div><div class="l">Aumentos seguidos</div><div class="v">{tr.get("anios_crece", 0)} {"año" if tr.get("anios_crece", 0) == 1 else "años"}</div><div class="n">Años consecutivos con aumento del total anual</div></div>')
    if bloques:
        tiles.append(_tile("s12", "Métricas clave del dividendo", '<div class="stats">' + "".join(bloques) + "</div>", ac="#16a34a"))
    graf = _svg_dps(tr.get("anuales"))
    if graf:
        tiles.append(_tile("s12", "Dividendo anual por acción", graf + '<div class="fch-sub" style="margin:4px 0 0;text-align:center">Total pagado por año calendario, en dólares por acción (años completos). Pasá el mouse por un punto para ver el monto.</div>', ac="#16a34a"))
    tiles.append(_tile_recesion(rec))
    return _env(*tiles)


def tab_competidores(row, df):
    """Empresas del screener en la misma industria (o sector) con sus metricas, para comparar. Solo muestra las del universo del screener."""
    if df is None or len(df) == 0:
        return _env(_tile("s12", "Competidores", '<div class="fch-sub" style="margin:0">Sin datos.</div>'))
    t = str(row.get("ticker", ""))
    ind, sec = _txt(row.get("industria"), ""), _txt(row.get("sector_macro"), "")
    pares = df[(df["industria"] == ind)] if ind and "industria" in df.columns else df.iloc[0:0]
    base = f"la industria de los {ind}"
    if len(pares) < 4 and sec and "sector_macro" in df.columns:
        pares = df[df["sector_macro"] == sec]
        base = f"el sector {sec}"
    pares = pares.sort_values("market_cap", ascending=False) if "market_cap" in pares.columns else pares
    yo = pares[pares["ticker"] == t]
    otros = pares[pares["ticker"] != t].head(9)
    import pandas as _pd
    tabla = _pd.concat([yo, otros])
    if len(tabla) < 2:
        return _env(_tile("s12", "Competidores", '<div class="fch-sub" style="margin:0">No hay otras empresas comparables en el screener.</div>', ac="#f59e0b"))

    def ratio(v, suf="x"):
        v = _n(v)
        return f"{v:.1f}{suf}" if v and v > 0 else "—"

    def dy(v):
        v = _n(v)
        if not v or v <= 0:
            return "—"
        return f"{(v if v > 1 else v * 100):.2f}%"
    filas = []
    for _, r in tabla.iterrows():
        tk = str(r.get("ticker"))
        color = _txt(r.get("color_hex"), "#6e7781")
        cat = _txt(r.get("categoria"), "")
        cat_h = f'<span style="color:{texto_categoria(color)};font-weight:700">{_texto_plano_categoria(cat)}</span>' if cat else "—"
        sc = _n(r.get("score_total"))
        sc_h = (f'<span style="display:inline-block;min-width:34px;padding:2px 8px;border-radius:999px;font-weight:700;background:{color};'
                f'color:{_TEXTO_EN_RELLENO.get(color.lower(), "#ffffff")}">{sc:.0f}</span>') if sc is not None else "—"
        me = ' style="background:#f1f5f9"' if tk == t else ""
        filas.append(f'<tr{me}><td><a href="?empresa={html.escape(tk, quote=True)}" target="_self">{html.escape(str(r.get("nombre") or tk))}</a> <span class="tkc">{html.escape(tk)}</span></td>'
                     f'<td>{_mcap(r.get("market_cap"))}</td><td>{ratio(r.get("per_actual"))}</td><td>{ratio(r.get("ev_ebitda_actual"))}</td>'
                     f'<td>{ratio(r.get("p_fcf_actual"))}</td><td>{dy(r.get("dividend_yield_actual"))}</td><td>{sc_h}</td><td>{cat_h}</td></tr>')
    cab = "<tr><th>Empresa</th><th>Cap. bursátil</th><th>P/E</th><th>EV/EBITDA</th><th>P/FCF</th><th>Dividend Yield</th><th>Score de calidad</th><th>Valoración</th></tr>"
    cuerpo = (f'<div class="fch-sub" style="margin:0 0 8px">Comparación contra empresas de {html.escape(base)}, de mayor a menor capitalización.</div>'
              f'<div class="comp-w"><table class="comp">{cab}{"".join(filas)}</table></div>')
    return _env(_tile("s12", "Competidores", cuerpo, ac="#f59e0b"))


def _iniciales(nombre):
    pal = [p for p in re.split(r"[\s.]+", str(nombre)) if p and p[0].isalpha() and p.lower() not in ("mr", "mrs", "ms", "dr", "sir", "jr", "sr")]
    return ((pal[0][0] + pal[-1][0]) if len(pal) > 1 else (pal[0][:2] if pal else "?")).upper()


def _sin_honorifico(nombre):
    return re.sub(r"\s+", " ", re.sub(r"^(mr|mrs|ms|miss|dr|sir|prof)\.?\s+", "", str(nombre or "").strip(), flags=re.I))


def _es_ceo(cargo):
    c = str(cargo or "").lower()
    return "chief executive" in c or re.search(r"\bceo\b", c) is not None


def nombre_ceo(g):
    """Nombre del CEO segun la lista de directivos de Yahoo ('' si no figura)."""
    for d in (g or {}).get("directivos") or []:
        if _es_ceo(d.get("cargo")):
            return _sin_honorifico(d.get("nombre"))
    return ""


def tab_directivos(g, foto=None):
    """Directivos (v1.2.53): el CEO en un mosaico grande a la izquierda y el resto del equipo a la derecha. Yahoo no da fotos: el CEO lleva sus iniciales."""
    dirs = (g or {}).get("directivos") or []
    if not dirs:
        return _env(_tile("s12", "Directivos", '<div class="fch-sub" style="margin:0">No disponible por ahora.</div>', ac="#64748b"))
    ceo = next((d for d in dirs if _es_ceo(d.get("cargo"))), None)
    resto = [d for d in dirs if d is not ceo]
    tiles = []
    if ceo:
        det = []
        if ceo.get("edad"):
            det.append(_fila_kv("Edad", f'{int(ceo["edad"])} años'))
        if ceo.get("pago"):
            det.append(_fila_kv("Remuneración (último año informado)", _usd_abrev(ceo["pago"])))
        capa = (f'<img src="{html.escape(foto, quote=True)}" alt="" title="Foto: Wikipedia" loading="lazy" referrerpolicy="no-referrer">' if foto else "")
        cab = (f'<div class="ceo"><div class="ft" aria-hidden="true">{html.escape(_iniciales(ceo["nombre"]))}{capa}</div>'
               f'<div><div class="nm">{html.escape(_sin_honorifico(ceo["nombre"]))}</div><div class="cg">{html.escape(ceo.get("cargo") or "CEO")}</div></div></div>')
        tiles.append(_tile("s5", "CEO", cab + ('<div class="fch-kv" style="margin-top:14px">' + "".join(det) + "</div>" if det else ""), ac="#64748b"))
    if resto:
        fil = "".join(f'<tr><td>{html.escape(_sin_honorifico(d["nombre"]))}</td><td>{html.escape(d["cargo"])}</td><td>{int(d["edad"]) if d.get("edad") else "—"}</td>'
                      f'<td>{_usd_abrev(d["pago"]) if d.get("pago") else "—"}</td></tr>' for d in resto)
        tiles.append(_tile("s7" if ceo else "s12", "Equipo directivo",
                           f'<div class="comp-w"><table class="comp"><tr><th>Nombre</th><th>Cargo</th><th>Edad</th><th>Remuneración</th></tr>{fil}</table></div>', ac="#64748b"))
    return _env(*tiles)


def tab_accionariado(g):
    """Accionariado (v1.2.53): participacion de directivos e instituciones y mayores accionistas institucionales."""
    g = g or {}
    acc = []
    if g.get("insiders") is not None:
        acc.append(_fila_kv("En manos de directivos (insiders)", f'{g["insiders"] * 100:.1f}%', "Porcentaje de las acciones que tienen los directivos y miembros del directorio."))
    if g.get("instituciones") is not None:
        acc.append(_fila_kv("En manos de instituciones", f'{g["instituciones"] * 100:.1f}%', "Fondos, bancos y otras instituciones."))
    cuerpo = '<div class="fch-kv" style="margin-top:0">' + "".join(acc) + "</div>" if acc else ""
    if g.get("principales"):
        def _pc(p):
            return f"{p['pct'] * 100:.2f}%" if p.get("pct") is not None else "—"
        fil = "".join(f'<tr><td>{html.escape(p["nombre"])}</td><td>{_pc(p)}</td></tr>' for p in g["principales"])
        cuerpo += f'<div class="comp-w" style="margin-top:12px"><table class="comp"><tr><th>Mayores accionistas institucionales</th><th>% de la empresa</th></tr>{fil}</table></div>'
    if not cuerpo:
        return _env(_tile("s12", "Accionariado", '<div class="fch-sub" style="margin:0">No disponible por ahora.</div>', ac="#64748b"))
    return _env(_tile("s12", "Accionariado", cuerpo, ac="#64748b"))


def _monto_estado(v, tipo, moneda):
    if v is None:
        return "—"
    if tipo == "pct":
        return f"{v * 100:.1f}%"
    if tipo == "x":
        return f"{v:.2f}x"
    if tipo == "eps":
        return f"{v:.2f}"
    a = abs(v)
    for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= lim:
            txt = f"{a / lim:,.2f}{suf}"
            break
    else:
        txt = f"{a:,.0f}"
    pre = "US&#36; " if (tipo != "n" and (moneda in (None, "", "USD"))) else ""
    return ("-" if v < 0 else "") + pre + txt


AYUDA_ESTADOS = {
    "Ingresos": "Lo que la empresa vendió en el período, antes de descontar ningún costo.",
    "Costo de ventas": "Lo que le costó producir o comprar lo que vendió.",
    "Utilidad bruta": "Ingresos menos costo de ventas: lo que queda para pagar el resto de los gastos.",
    "Gastos operativos": "Los gastos de funcionar: sueldos, marketing, investigación y administración.",
    "Resultado operativo": "La ganancia del negocio en sí, antes de intereses e impuestos.",
    "EBITDA": "Ganancia operativa antes de depreciaciones y amortizaciones: una forma de ver cuánto genera el negocio sin efectos contables.",
    "Resultado antes de impuestos": "Ganancia una vez descontados los intereses y antes de pagar impuestos.",
    "Impuesto a las ganancias": "Lo que la empresa pagó (o provisionó) de impuesto sobre sus ganancias.",
    "Tasa de impuesto": "Impuesto ÷ resultado antes de impuestos: qué porcentaje de la ganancia se va en impuestos.",
    "Resultado neto": "La ganancia final: lo que queda para los accionistas después de todo.",
    "Ganancia por acción (diluida)": "Resultado neto ÷ cantidad de acciones, contando también las que podrían crearse (opciones, bonos convertibles).",
    "Acciones promedio (diluidas)": "Cantidad promedio de acciones. Si baja año tras año, la empresa está recomprando sus acciones.",
    "Caja e inversiones de corto plazo": "Efectivo y colocaciones que se pueden convertir en efectivo rápido.",
    "Cuentas por cobrar": "Lo que los clientes le deben a la empresa por ventas ya hechas.",
    "Inventarios": "Mercadería y materiales guardados para vender o producir.",
    "Activo corriente": "Lo que la empresa tiene y puede convertir en efectivo en menos de un año.",
    "Propiedad, planta y equipo (neto)": "Terrenos, fábricas, edificios y maquinaria, ya descontado el desgaste.",
    "Plusvalía (goodwill)": "Lo que pagó de más, sobre el valor contable, al comprar otras empresas.",
    "Activo total": "Todo lo que la empresa tiene: efectivo, inventarios, equipos, inversiones y demás.",
    "Pasivo corriente": "Deudas y obligaciones que vencen en menos de un año.",
    "Deuda total": "Todo lo que la empresa debe a bancos y tenedores de bonos, de corto y largo plazo.",
    "Pasivo total": "Todo lo que la empresa debe: deuda financiera más proveedores, impuestos y otras obligaciones.",
    "Patrimonio neto": "Activos menos pasivos: lo que les pertenece a los accionistas.",
    "Capital invertido (según Yahoo)": "El dinero que está puesto en el negocio (deuda más patrimonio, según el cálculo de Yahoo).",
    "Flujo de efectivo operativo": "El efectivo que genera el negocio con su actividad habitual. Es más difícil de maquillar que la ganancia contable.",
    "Inversión en activos fijos (CAPEX)": "Dinero gastado en fábricas, equipos y tecnología. Se ve negativo porque es una salida de efectivo.",
    "Flujo de efectivo libre": "Efectivo operativo menos CAPEX: lo que le queda a la empresa para dividendos, recompras o pagar deuda.",
    "Flujo de efectivo de inversión": "Efectivo usado en comprar o vender inversiones y activos. Suele ser negativo si la empresa está invirtiendo.",
    "Flujo de efectivo de financiamiento": "Efectivo por emitir o pagar deuda, recomprar acciones y pagar dividendos. Negativo suele significar que devuelve dinero a inversores y acreedores.",
    "Recompra de acciones": "Dinero que la empresa usó para comprar sus propias acciones.",
    "Dividendos pagados": "Dinero que la empresa pagó a sus accionistas como dividendo.",
    "Margen bruto": "Utilidad bruta ÷ ingresos. Ejemplo: 45% significa que de cada $100 vendidos quedan $45 después del costo de ventas.",
    "Margen operativo": "Resultado operativo ÷ ingresos: cuánto queda de cada $100 vendidos después de todos los gastos del negocio.",
    "Margen neto": "Resultado neto ÷ ingresos: cuánto de cada $100 vendidos termina como ganancia final.",
    "Margen de flujo de efectivo libre": "Flujo de efectivo libre ÷ ingresos: cuánto de cada $100 vendidos queda en efectivo libre.",
    "Retorno sobre el patrimonio (ROE)": "Resultado neto ÷ patrimonio: qué ganancia genera la empresa con el dinero de los accionistas.",
    "Retorno sobre el capital invertido (ROIC)": "Ganancia operativa después de impuestos ÷ capital invertido: qué rinde cada dólar puesto en el negocio, venga de deuda o de accionistas.",
    "Deuda total / Patrimonio": "Cuánta deuda tiene por cada dólar de patrimonio. Más alto significa más apalancada.",
    "Liquidez corriente (activo / pasivo corriente)": "Activo corriente ÷ pasivo corriente. Por encima de 1 indica que puede cubrir lo que vence en el año.",
}


def _tabla_estado_html(t, moneda):
    cab = "<tr><th>Concepto</th>" + "".join(f"<th>{a}</th>" for a in t["anios"]) + "</tr>"
    filas = ""
    for rot, vals, tipo in t["filas"]:
        negrita = ' class="tot"' if tipo == "t" else ""
        tip = AYUDA_ESTADOS.get(rot)
        nom = f'<span class="hv" title="{html.escape(tip, quote=True)}">{html.escape(rot)}</span>' if tip else html.escape(rot)
        filas += f"<tr{negrita}><td>{nom}</td>" + "".join(f"<td>{_monto_estado(v, tipo, moneda)}</td>" for v in vals) + "</tr>"
    return f'<div class="comp-w"><table class="comp">{cab}{filas}</table></div>'


def tab_estados(est):
    """Estados financieros de Yahoo: la columna TTM (ultimos 12 meses) y los ultimos 4 anios fiscales, el mas nuevo a la izquierda (v1.2.58):
    Estado de Resultados, Balance, Estado de Flujo de Efectivo y Ratios Financieros (calculados con esas cifras, con ROIC)."""
    vacio = _env(_tile("s12", "Estados Financieros", '<div class="fch-sub" style="margin:0">No disponibles por ahora.</div>', ac="#0ea5e9"))
    if not est:
        return vacio
    moneda = est.get("moneda")
    if moneda and moneda != "USD":
        nota = f"Cifras en {html.escape(str(moneda))}, la moneda en que la empresa informa (no se convierten a dólares)."
    else:
        nota = "Cifras en dólares: T = billones, B = miles de millones, M = millones."
    hay_ttm = any(isinstance(a, str) for k in ("resultados", "balance", "flujo") for a in (est.get(k) or {}).get("anios", []))
    if hay_ttm:
        nota += " TTM = últimos 12 meses (suma de los 4 últimos trimestres; en el balance, el último trimestre). Los demás son años fiscales de la empresa."
    else:
        nota += " Años fiscales de la empresa."
    nota_roic = ("ROIC = resultado operativo × (1 − tasa de impuesto) ÷ capital invertido (deuda + patrimonio, según Yahoo): cuánto gana la empresa por cada dólar "
                 "puesto en el negocio. ROE = resultado neto ÷ patrimonio. Con cifras de fin de período, no promedios.")
    tiles = []
    for clave, titulo, color in (("resultados", "Estado de Resultados", "#0ea5e9"), ("balance", "Balance", "#6366f1"), ("flujo", "Estado de Flujo de Efectivo", "#14b8a6"),
                                 ("ratios", "Ratios Financieros", "#f59e0b")):
        if est.get(clave):
            pre = f'<div class="fch-nota" style="margin:0 0 8px">{nota}</div>' if not tiles else ""
            post = f'<div class="fch-nota" style="margin:8px 0 0">{nota_roic}</div>' if clave == "ratios" else ""
            tiles.append(_tile("s12", titulo, pre + _tabla_estado_html(est[clave], moneda) + post, ac=color))
    return _env(*tiles) if tiles else vacio


def tab_gobierno(g):
    """Compatibilidad: directivos y accionariado juntos."""
    return tab_directivos(g) + tab_accionariado(g)


def tab_noticias(ticker, items):
    """Noticias de la empresa: titulares de Yahoo Finance y links a CNBC y Yahoo Finance."""
    t = quote_plus(str(ticker))
    enl = [(f"https://www.cnbc.com/quotes/{t}?tab=news", "Ver más noticias en CNBC"), (f"https://finance.yahoo.com/quote/{t}/news/", "Ver más noticias en Yahoo Finance")]
    botones = '<div class="fch-links">' + "".join(f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(n)} ↗</a>' for u, n in enl) + "</div>"
    if items:
        li = "".join(f'<li><a href="{html.escape(i["link"], quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(i["titulo"])}</a>'
                     f'<span class="nf">{html.escape(i["fuente"])}{" · " + _fmt_fecha(i["fecha"]) if i.get("fecha") else ""}</span></li>' for i in items)
        cuerpo = f'<ul class="nlist">{li}</ul><div class="fch-nota">Titulares en su idioma original.</div>' + botones
    else:
        cuerpo = '<div class="fch-sub" style="margin:0 0 10px">No pudimos traer titulares ahora. Mirá las últimas noticias directamente en:</div>' + botones
    return _env(_tile("s12", "Noticias", cuerpo, ac="#ef4444"))
