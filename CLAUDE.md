# TodoCedears — mapa del código (leer ESTO primero, antes de abrir archivos)

App Streamlit de **Guille** (Finanzas para Médicos Argentina) que filtra CEDEARs y ETFs, escribe Análisis Fundamentales y evalúa carteras.
Este archivo existe para no tener que releer toda la app en cada sesión: buscá acá dónde está cada cosa y abrí **solo** el archivo y la función que hacen falta
(con `grep -n "def nombre"` + Read con offset/limit). Actualizalo cuando cambie la estructura.

## Reglas de Guille (no negociables)
- Castellano rioplatense con voseo, simple, sin jerga. Respuestas con "Conclusión resumen" al final. Cruda verdad y sin inventar datos.
- Información educativa, **nunca recomendaciones**. No mostrar en pantalla el método ni los pesos del score.
- **No cambiar metodología** (score, categorías, Fair Value, carteras modelo) sin su decisión explícita.
- **Antes de escribir cualquier informe** (Análisis Fundamental nuevo, renovación, reescritura) **avisarle** para que cambie a Opus.
- Nada pago ni instalaciones en su PC. En el texto de los informes no nombrar a Damodaran ni a Nelissen (en la línea de fuentes sí puede ir Damodaran).
- Palabras prohibidas en informes y devoluciones: «dosis chica(s)» (usar «posición pequeña»).
- Textos justificados; tortas, no barras; nada de "malas noticias" en la evaluación de cartera (ver abajo).

## Cómo fluyen los datos
1. En la PC de Guille corren los `.bat` (Yahoo/Stock Analysis): `generar_cache.bat` → `data/cache_datos.json` (balances, múltiplos, score; fecha en `timestamp`),
   `bajar_fichas.bat` → `data/fichas.json`, `bajar_etfs_yahoo.bat T1 T2…` → `data/etfs_yahoo.json`, `bajar_tecnicos.bat` → `data/tecnicos.json`,
   `bajar_paquetes_yahoo.bat`, `bajar_multiplos_anuales.bat`, `bajar_fotos_ceo.bat`, `descargar_logos.bat`, `actualizar_ticker.bat TICKER`.
2. La app publicada **solo lee** esos JSON. Precios de hoy: `data/precios_vivos.py` (Yahoo → Stock Analysis de respaldo). Desde este entorno Yahoo está bloqueado.
3. Score: `scoring/engine.py` (`score_dataframe`, `calcular_score`, respaldo por sector). Pesos/ajustes: `config/ajustes.py`, sectores: `config/sectors.py`.

## app.py (≈2.250 líneas) — rutas y funciones clave
- `APP_VERSION` (línea ~9). `main()` (~1870): lee `?pagina=quienes|cartera|ideas`, `?empresa=TICKER`, `?etf=TICKER`, `?tabla=etfs`, `?menu=1`, `?debug=1`.
- Tabla de empresas: `render_filtros_inline`, `filtrar_ordenar`, `render_tabla_visual`, `render_main_table`. ETFs: `render_filtro_etfs`, `render_tabla_etfs`, `render_pagina_etf`.
- Ficha de empresa: `render_pagina_empresa` (~1310) → `ui/ficha.py`. Botón PDF del análisis: `_boton_pdf_analisis` → `ui/af_pdf.py`.
- Evaluá tu Portfolio (`?pagina=cartera`): `render_cartera` (~1470, dos mosaicos) → `_evaluar_cartera` (~1577) y `_rentabilidad_anual` (~1723).
  Textos de entrada: `_INTRO_EVAL`, `_INTRO_RENT`, `_OPC_RENT`, `_CSS_COMENZAR`, `_presentacion`; lectura de archivos `_leer_archivos`, tabla editable `_tabla_a_mano`.
- Pie: `pie_html(APP_VERSION, aviso=…, precios=…)` de `ui/marca.py`. En la página de cartera **no va pie**. "Datos al dd/mm/aaaa (hh:mm)" = precios de hoy (nunca la fecha del cache).

## ui/ (presentación)
| Archivo | Qué hace |
|---|---|
| `marca.py` | Franja negra (desde la v1.5.14: logo · Noticias, Calendario, Ideas, Evalúa tu Portfolio en el medio (`links_html`, radios `bn-*`, `?abrir=noticias\|cal`) · iconos), menú lateral (`menu_lista_html`, `.mn-sep`), pie (`pie_html`), modo oscuro. El Filtro se despliega con el botón `.fl-btn` de la fila de la tabla (`_fila_tabla` en app.py, panel `fly_filtro` casi a todo el ancho). El buscador ya no va en la franja. |
| `tabla_visual.py` | Tabla de empresas (celdas, columna Valoración, ayudas de columnas). Desde la v1.5.8 el CSS de `.st-key-fila_excel` deja el Excel como ícono flotante sobre los títulos (alto 0) y el «?» de Empresa/ETF lleva la frase «Presioná en…»; desde la v1.5.10 en esa franja va también el interruptor «Empresas \| ETFs» (`_switch_tablas` en app.py, `.st-key-sw_tablas`) y en las tablas ya no hay botón de la otra tabla en la franja negra. Vale también para ETFs. |
| `ficha.py` | Página de empresa en solapas: resumen, Análisis Fundamental (`tiles_analisis_v4`, `tab_analisis`), valuación, dividendos, competidores, directivos, estados. |
| `af_pdf.py` | PDF del Análisis Fundamental. |
| `etfs.py`, `etf_iconos.py` | Tabla y página de ETFs, íconos SVG por categoría (`SIN_PAISES`). |
| `cartera.py` | **Motor de la evaluación de cartera** (ver sección propia). |
| `cartera_visual.py` | Tarjetas HTML de la evaluación (`visual_html`, `_bloque`, `_bloque_donut`, `_md`: `**negrita**`, `==dato==` (negrita negra) y `__cursiva__` para las Notas; `_ajuste`; estilo = tarjetas blancas como el resto del sitio). |
| `cartera_informe.py` | PDF de la evaluación con membrete (`pdf_informe`, reportlab, tortas `Doughnut`) y HTML de respaldo (`html_informe`). |
| `mercados.py`, `inicio.py` | Barra de mercados (dólares, Merval, bolsas, petróleo…; `obtener`, `armar`, `barra_html`) y pantalla de inicio con «Comenzar» (`hero_html`; vista previa desenfocada y FOTO FIJA de la app con empresas reales (`FOTO`, del 02/11/2026; no se actualiza sola: se cambia a mano cuando se arme el score nuevo); se muestra con `en_landing` en `main()`; `?inicio=0` la salta). |
| `cartera_ocr.py` | Lectura de capturas con RapidOCR (opcional; si no está, la app sigue). |
| `noticias.py` (`ordenar`, `ordenar_bloques`: sin tickers repetidos, una macro, mercado AR en Locales; `_MACRO`, `_MERCADO_AR`), `calendario.py` (Hoy en verde), `quienes.py`, `exportar.py` (Excel), `criterios.py`, `tecnico.py`, `logos.py`, `banderas.py`, `traducir.py` | Lo que dice el nombre. |

## data/ (datos y lógica)
- `fetcher.py` (bajada Yahoo, incluye `beta`), `stockanalysis.py`, `yahoo_extra.py`, `moneda.py` (estados en otra moneda / ADR), `precios_vivos.py`, `historial_precios.py`.
- `cedears.py` / `cedears.csv` / `byma_cedears.json` (lista oficial BYMA), `etfs.py` / `etfs.csv` (categorías: USA, Internacionales no USA, USA según Sectores, Temáticos, Minería, Materias Primas, Criptomonedas, Apalancados, Inversos).
- `damodaran.py`, `damodaran_mapa.py`, `data/damodaran/` (medianas por industria y región).
- **Análisis Fundamental v4**: `af_v4.py` (`contexto`, `tomar_foto`, `texto_html`, `validar`, `armar_prompt`), prompt `prompt_analisis_fundamental_v4.txt`,
  informes guardados en `analisis_fundamental.json` (`{"fecha","datos":{TICKER:{…,"valuacion":{"foto":…}}}}`), generación `generar_analisis_fundamental.py`.
  Regla: la valuación arranca "Con el precio de X dólares al momento de escribir este informe (dd/mm/aaaa)" y usa la **foto** congelada de ese día.
- `carteras_modelo.py`: `RANGOS` (cartera de referencia por edad y perfil), `GEOGRAFIA` 75/20/5, `SUPERSECTOR` 20/30/50, `OBJETIVOS` (diapositivas de Guille),
  `OBJETIVO_RESUMEN` (su redacción "normalmente un inversor de tu edad…"), `referencia(edad, perfil)`.
- `macro_actual.txt` / `macro_numeros.json`: contexto macro para los informes (mantener al día).

## Evaluación de cartera (ui/cartera.py)
- Lectura: PDFs de broker en `leer_pdf_info` (formato IOL aparte: `_iol_filas`/`_iol_efectivo`; sección «Fondos» de Balanz); alias de tickers BYMA en `_alias_tk`/`_EXTRA_EMPRESAS`; `leer_archivo_info` (Excel/CSV, columnas `_columnas`: ticker, monto, tipo, **país**, cantidad, precio, moneda), `leer_pdf_info`, `leer_texto_info`; `convertir` (pesos→USD), `fusionar` (varios brokers).
- **Paso «Esto es lo que leímos»** (v1.5.5): `_confirmar_lectura` en app.py (tabla editable con OK obligatorio antes de `convertir`/`analizar`; `_pais_sugerido`, `_CLASES_TABLA`).
- `clasificar` → clase rv/rf/oro/cripto/efectivo/otros; `analizar` → `peso`, `peso_inv` (sin liquidez salvo 70+), `desvio`, `geo` (RV **y** RF; país declarado manda), `super`, `sectores_gics`, `rf_det`, `beta`.
- `devolucion(res, edad, perfil, nombre)` → `[(título, [párrafos])]`: Objetivo como inversor · Estructura de tu cartera · Diversificación geográfica · Diversificación sectorial (+ «detalle GICS») · Liquidez (teoría primero) · (beta) · Conclusiones finales («Lo que no tocaríamos» + ajustes).
  `saludo()` ("Hola X.", sin edad ni perfil) y `despedida()` ("Hasta aquí nuestro aporte… Abrazo grande y buenas inversiones.").
- **Tono (modelo escrito por Guille, 02/11/2026)**: primero lo que *notamos*, después la base teórica (que va SIEMPRE); nunca "te pasás", "te faltan", "Ojo", "demasiado";
  ajustes en positivo (aumentar, sumar, considerar) en orden de importancia con "Por qué:"; elogios solo cuando son ciertos; sectores GICS (no industrias).
- `resumen_guardable` / `comparar`: el resumen viaja dentro del PDF descargado (`resumen_para_pdf` / `resumen_de_pdf`, en el campo «subject»); el inversor sube ese PDF la próxima vez. Sin .json. `AVISO_CARTERA`: único aviso legal de la evaluación.
- Rentabilidad: `rentabilidad_con_fechas` (TIR / Dietz), `rentabilidad_anual` (rango estimado), `duracion_txt`. Todo en dólares.

## Pruebas
- `tests/test_v145_cartera.py`, `tests/test_v152_noticias.py`, `tests/test_v154_pdf_broker.py` (PDFs de IOL/Balanz), `tests/test_v157_mercados.py` y `tests/test_v149_carteras_todo_tipo.py` (70 carteras × 8 edades × 3 perfiles; revisa tono, bases fijas, PDF): `python tests/<archivo>.py` → "OK n MAL 0".
- Para ver una pantalla sin la app entera: armar un harness que importe solo las funciones (ver `_evaluar_cartera`) y usar Playwright; Yahoo no responde acá.

## Publicar una versión
1. Subir `APP_VERSION` en app.py y agregar la sección en `README.md`.
2. `git commit` + `git push origin HEAD:main` en este repo (SCREENER-CEDEAR).
3. Copiar a TODO-CEDEAR: `git archive HEAD | tar -x -C ../todo-cedear` → commit + push allí.
4. Zip para Guille: `git archive --format=zip HEAD -o TodoCedears_vX.Y.Z.zip`.

## Pendientes
Ver `PENDIENTES_01-12.md` (lista del 01/12/2026 y pendientes urgentes al principio). Los informes (Análisis Fundamental) se trabajan en una charla aparte: ver `TRASPASO_ANALISIS.md`.
