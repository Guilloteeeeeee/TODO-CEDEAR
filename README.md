# 📊 CEDEAR Screener

Detector de CEDEARs potencialmente infravalorados. Descarga datos automáticamente desde Yahoo Finance y calcula un score de valuación usando métricas fundamentales adaptadas por sector.

## Cómo funciona

**Score total = 85% fundamental + 15% técnico (rango 52 semanas)**

### Métricas por sector

| Sector | Métrica 1 | Métrica 2 | Métrica 3 | Métrica 4 |
|---|---|---|---|---|
| Materiales Básicos | EV/EBITDA (35%) | P/FCF (30%) | Div. Yield (25%) | P/B (10%) |
| REITs | P/FFO (30%) | P/AFFO (30%) | Div. Yield (30%) | EV/EBITDA (10%) |
| Bancos y seguros | P/B (40%) | PER (35%) | Div. Yield (25%) | — |
| Pagos y datos | PER (35%) | P/FCF (35%) | EV/EBITDA (20%) | Div. Yield (10%) |
| Consumo Discrecional | P/FCF (30%) | EV/EBITDA (30%) | PER (25%) | Div. Yield (15%) |
| Consumo Básico | Div. Yield (35%) | EV/EBITDA (25%) | PER (25%) | P/FCF (15%) |
| Comunicación (internet y medios) | PEG (30%) | EV/EBITDA (30%) | Div. Yield (20%) | PER (20%) |
| Telecomunicaciones | Div. Yield (30%) | EV/EBITDA (30%) | P/FCF (25%) | PER (15%) |
| Industrial | EV/EBITDA (30%) | PER (30%) | P/FCF (25%) | Div. Yield (15%) |
| Semiconductores | P/S (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Software y nube | PEG (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Hardware y servicios TI | P/S (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Energía | P/FCF (35%) | EV/EBITDA (30%) | Div. Yield (25%) | P/B (10%) |
| Salud | P/FCF (30%) | EV/EBITDA (25%) | PER (25%) | Div. Yield (20%) |
| Utilities | Div. Yield (45%) | P/FCF (20%) | EV/EBITDA (20%) | PER (15%) |

*Semiconductores y Hardware:* los pesos de la fila son los que se usan (desde la v1.2.45 la regla del "PEG creíble" de la v1.2.44 está apagada; ver esa sección).

### Fuentes de datos y respaldo de sector (v1.2.12 / v1.2.13 / v1.2.14)

- **Stock Analysis es la fuente principal (v1.2.13):** para cada empresa se baja una sola página (ratios anuales) y de ahí salen el valor actual y la mediana de los últimos 5 años fiscales, incluidos PEG y, en REITs, Price/FFO y Price/AFFO reales. Yahoo Finance queda de respaldo para lo que Stock Analysis no trae (con el control de moneda de `data/moneda.py`).
- **v1.2.14 (arreglo de lectura):** en la primera prueba real Stock Analysis respondió bien (HTTP 200) pero la página llegaba ilegible porque el pedido aceptaba compresión `br` y la PC no tiene cómo abrirla. Ahora se pide solo `gzip/deflate`, si llega algo que no parece HTML se reintenta sin compresión, el lector de tabla es más tolerante (encabezado en cualquier fila, textos partidos, años sin "FY") y, si varias páginas seguidas no se pueden leer, se deja de consultar en esa corrida. `probar_stockanalysis.bat` ahora escribe un diagnóstico de lo que llega y guarda `sa_pagina_cruda.bin`.
- **Respaldo de sector:** si a una empresa le falta (o tiene imposible) la mediana histórica propia de una métrica, se compara contra la mediana de su sector (mediana de las medianas de sus pares, mínimo 5). Se ve en el detalle de cada empresa.
- **PEG:** usa su propia historia (5 años fiscales) cuando viene de Stock Analysis; si no, la mediana del sector. Nunca se compara contra sí mismo.
- **Fuente de cada métrica:** el detalle muestra si salió de Yahoo, de Stock Analysis o de la mediana del sector. Al terminar `generar_cache.bat` queda `resultados_cache.txt` con el resumen de fuentes.
- **La app publicada solo lee el caché guardado.** Nunca baja datos de Stock Analysis ni de Yahoo por su cuenta: el caché se genera una vez por trimestre en la PC con `generar_cache.bat` (ver "Cada cuánto actualizar").
- **Trato con Stock Analysis:** respeta su `robots.txt`, una página por empresa con pausa entre pedidos, reintenta una vez si pide frenar y se detiene si lo bloquean. Sus términos de uso piden uso personal y manual, sin scripts, salvo rastreadores que respeten el `robots.txt`: usarlo es una decisión informada del dueño de la herramienta. El interruptor está en `config/ajustes.py` (`STOCK_ANALYSIS_MODO`: `"apagado"`, `"respaldo"` o `"principal"`).
- **Puntaje en sombra vs sector y Seguimiento:** cada fila guarda además `score_total_sector` / `categoria_sector` (la misma cuenta, pero comparando contra los pares del sector hoy). No cambia la categoría oficial. El panel "📈 Seguimiento" de la app compara, entre una copia y la siguiente, cuánto cambió el precio según cada categoría, usando las copias de `data/historial/`. Empieza a medir desde la segunda copia (con al menos 20 días de diferencia).
- **Cada cuánto actualizar (v1.2.15):** una vez por trimestre, el día 1 de marzo, junio, septiembre y diciembre (`MESES_ACTUALIZACION` en `config/ajustes.py`). Para esas fechas casi todas las empresas ya presentaron resultados, que es cuando cambian de verdad los balances; las medianas de 5 años cambian una sola vez por año. Lo que sí se mueve todos los meses es el precio: con un caché de 1 mes, aproximadamente 1 de cada 3 empresas queda en una categoría vecina a la de hoy (solo ~2% se corre 2 o más escalones); con 3 meses, ~45% (y ~9% a 2 o más escalones). Es una estimación hecha moviendo solo los precios con el motor real (volatilidad tomada del rango de 52 semanas); el panel "Seguimiento" va a medirlo con datos reales.
- **Aviso:** si el caché tiene más de 100 días (`DIAS_AVISO_CACHE_VIEJO`), la app muestra un cartel para actualizarlo.

### Vista visual y logos (v1.2.16)

- **Vista visual (en prueba; ver la v1.2.33 para cómo quedó):** arriba de la tabla hay un selector "Tabla clásica / Vista visual (prueba)". La vista visual muestra, por empresa: logo y nombre, la categoría con color y una barra de valoración (punto = precio de hoy, franja = rango de los métodos del Fair Value, raya = Fair Value promedio), una caja con el puntaje y las métricas usadas, el rango de 52 semanas, el Dividend Yield contra su mediana y el Mkt Cap. Se ordena con el selector de al lado. Con qué vista abre la app se cambia en `config/ajustes.py` (`VISTA_POR_DEFECTO`). El código está en `ui/tabla_visual.py`.
- **Logos:** el servicio que se usaba (Clearbit) dejó de funcionar. Ahora cada logo sale, en este orden, de `assets/logos/<TICKER>.png` (incrustado en la página), del favicon de la empresa servido por Google (`LOGOS_EN_LINEA` en `config/ajustes.py`) o, si no hay nada, de un círculo con las iniciales. Desde la v1.2.17 la carpeta ya viene con los logos; `descargar_logos.bat` queda como opcional para mejorar o completar alguno (deja `resultados_logos.txt` con el resumen de qué fuente funcionó).

### Financieros separados y logos incluidos (v1.2.17)

- **"Financieros" ahora son dos grupos:** *Bancos y seguros* (P/B 40%, PER 35%, Div. Yield 25%: los bancos y aseguradoras se valúan por su valor contable y sus ganancias) y *Pagos y datos* (V, MA, SPGI, PYPL, COIN, FISV, MRSH: negocios de comisiones y datos, que no prestan plata y se miden mejor por PER, P/FCF y EV/EBITDA). BRK-B, AIG, BX, IBKR y los brokers quedan en *Bancos y seguros*. Mientras no se agregue MRSH al caché, *Pagos y datos* tiene 6 empresas (el respaldo de sector pide al menos 5).
- **Corrección:** MMC (Marsh McLennan) cambió su ticker a **MRSH** el 14/01/2026. En una versión intermedia se había puesto "MMS" por error: MMS es Maximus, otra empresa. Quedó MRSH. Sus datos entran con la próxima corrida en la PC (`actualizar_ticker.bat MRSH` o `generar_cache.bat`); que Yahoo Finance reconozca ya "MRSH" todavía no está verificado.
- **Logos incluidos:** `assets/logos/` trae los logos de 64×64 ya armados (fuente: el repositorio público `nvstly/icons` en GitHub; los logos son marcas de cada empresa y se usan solo para identificarla). Los logos blancos se apoyan sobre un fondo gris oscuro para que se vean. MS, IBN, PCAR y SIEGY se agregaron en la v1.2.19.

### Telecomunicaciones aparte (v1.2.18)

- **AT&T, Verizon y T-Mobile salen de "Comunicación"** y forman *Telecomunicaciones*. Son negocios lentos, con mucha deuda y que pagan dividendo: el PEG (crecimiento) no las describe bien, y se miden mejor por dividendo, EV/EBITDA y flujo de caja. *Comunicación* queda para internet y medios (GOOGL, META, NFLX, DIS, SPOT, NTES), con los mismos pesos de antes (PEG incluido).
- **Efecto en el caché:** VZ 52,9 → 40,6 y T 44,6 → 39,9 (las dos pasan de "parece bien valuada" a "tendencia a sobrevaluada"); TMUS 88,9 → 88,2 (sigue "podría estar infravalorada"). Los otros 6 de Comunicación se mueven menos de 1 punto, porque su mediana de PEG ahora se calcula solo entre pares de internet y medios.
- **Pares:** Telecomunicaciones tiene 3 empresas, menos que los 5 que pide el respaldo de sector. No hay problema porque las tres tienen historia propia; si algún día les falta, ese dato se descarta en vez de compararse con el sector.
- **Subgrupos:** Tecnología se dividió en la v1.2.19 (ver abajo). Salud y los demás sectores quedan como están.

### Tecnología en tres grupos (v1.2.19)

- **Grupos:** *Semiconductores* (15: NVDA, TSM, AVGO, MU, AMD, ASML, INTC, AMAT, ARM, TXN, MRVL, ADI, QCOM, LRCX, KLAC), *Software y nube* (11: MSFT, ORCL, PLTR, PANW, CRWD, SAP, SHOP, CRM, NOW, ADBE, SNOW) y *Hardware y servicios TI* (10: AAPL, CSCO, ANET, IBM, ACN, ADP, INFY, DELL, MSI, WDC). El reparto es un criterio mío (una empresa como AVGO podría estar en dos); se cambia en `TICKER_UNIVERSE` de `config/sectors.py`.
- **Los pesos no cambian** (PEG 40 / P/FCF 20 / EV/EBITDA 20 / PER 20) y el PEG se mantiene en todos. Lo que cambia es contra quién se compara cuando falta la historia propia. El PEG de referencia pasa de 1,125 (toda Tecnología) a 0,78 en semiconductores, 1,72 en software y 2,06 en hardware y servicios TI.
- **Efecto en el caché:** 30 de las 36 empresas cambian 1 punto o más y 15 cambian de categoría (ejemplos: TSM 79 → 50, ASML 44 → 29, CSCO 38 → 50, ANET 30 → 48, TXN 45 → 33). Casi todo sale del PEG comparado con el sector, que hoy se usa porque Yahoo no trae la historia de PEG. Con Stock Analysis cada empresa tendrá su propio PEG histórico y el efecto debería achicarse; después de esa corrida se repite la medición y, si el cambio no se justifica, se puede volver al grupo único.
- **Logos:** con MS, IBN, PCAR y SIEGY (logos que pasó Guille) ya están los 166.

### Sector / Industria en pantalla (v1.2.20)

- Las tablas, el filtro y el detalle muestran **"Sector / Industria"** para los grupos que son una industria dentro de un sector más grande. Ejemplos: *Financiero / Pagos y datos*, *Financiero / Bancos y seguros*, *Tecnología / Semiconductores*, *Tecnología / Software y nube*, *Tecnología / Hardware y servicios TI*, *Comunicación / Internet y medios*, *Comunicación / Telecomunicaciones*. Los demás (Salud, Industrial, Energía, etc.) se muestran solo con el nombre del sector.
- Es solo una etiqueta: el puntaje sigue usando los grupos de siempre. El cuadro se define en `SECTOR_E_INDUSTRIA` de `config/sectors.py`, y el orden del filtro y de la columna "Sector" agrupa las industrias del mismo sector.

### Banderas (v1.2.21)

- En la columna **País** de la tabla clásica, en la vista visual y en el detalle de cada empresa se muestra la **bandera** en lugar del nombre (al pasar el mouse por encima aparece el nombre del país). Si el país no está en la lista o no vino de Yahoo, se muestra el nombre o un guion.
- Son imágenes (`assets/flags/<código>.png`, 48×36, del paquete `flag-icons`, licencia MIT) y no emojis, porque en Windows los emojis de banderas se ven como dos letras ("US"). Están las de los países de la lista de traducción de `app.py`; para sumar uno nuevo se agrega la imagen y su nombre en `ISO` de `ui/banderas.py`.
- El filtro "País" y el orden de la columna siguen usando el nombre.

### Colores sobrios y país de respaldo (v1.2.22)

- **Menos colores:** el color queda solo para la **categoría** (el cartel de la tabla clásica y el texto de la vista visual). El Fair Value (+% / −%), el Div. Yield, la cantidad de métricas (4/4), el punto de la barra de valoración y el rango de 52 semanas pasan a gris. Antes el +16% de MELI salía en verde mientras su categoría decía "parece bien valuada", y el semáforo del rango de 52 semanas sumaba otro color más. El rango de 52 semanas es ahora una barrita de un solo color (gris azulado).
- **Colores de Streamlit:** `.streamlit/config.toml` cambia el rojo que Streamlit trae por defecto (filtros, controles deslizantes, selectores) por un gris azulado.
- **País de respaldo:** `PAIS_MANUAL` en `config/sectors.py` completa el país cuando Yahoo no lo informa (hoy FISV y MRSH). El país que informa Yahoo siempre tiene prioridad.
- **Por qué una empresa puede mostrar pocas métricas (1/3, 1/4):** (1) las extranjeras (ADR) con datos de Yahoo en otra moneda tienen la mediana histórica rota y la métrica se descarta; Stock Analysis es la solución prevista; (2) si no paga dividendo, el Div. Yield no se puede calcular; (3) huecos de Yahoo en el valor actual (por ejemplo, P/FCF de FISV o EV/EBITDA negativo de Boeing); (4) BRK-B: Yahoo calcula el P/B con el valor de una acción A, y el resultado no sirve para la B.
- **Por qué el Fair Value y la categoría pueden no coincidir:** el Fair Value descarta un método cuyo precio implícito queda fuera de 1/3x–3x el precio, pero el puntaje sigue usando esa métrica; además el PEG entra en el puntaje y no en el Fair Value, y el puntaje incluye 15% de rango de 52 semanas. Ejemplo MELI (cache del 21/10): su P/FCF (269 vs mediana 14,7) se descarta del Fair Value (+16%) pero pesa 30% en el puntaje, con 2,2 puntos.

### Columna "Valoración" en la tabla clásica (v1.2.23)

- La tabla clásica reemplaza las columnas **Precio** y **Fair Value** por una sola columna **Valoración**, la misma barra de la vista visual: el **punto** es el precio de hoy (con su valor arriba), la **raya oscura** es el Fair Value promedio y la franja gris va alrededor de él (ver v1.2.24). El precio va arriba del punto y el Fair Value con su distancia (por ejemplo "+183%") va abajo, en la leyenda (ver v1.2.25).
- Al hacer clic en el encabezado **Valoración** se ordena por esa distancia (lo que antes ordenaba "Fair Value"). La categoría sigue en su columna y sigue saliendo del puntaje; la franja es solo una ayuda visual.

### Barra de valoración simplificada (v1.2.24)

- La barra de **Valoración** (tabla clásica y vista visual) ahora tiene: una **raya** fina, el **punto del precio** con el color de la categoría, la **raya oscura** del Fair Value promedio y una **franjita** gris alrededor del Fair Value. (La leyenda cambió de lugar en v1.2.25.) Ya no se dibuja el rango entre el método más bajo y el más alto.
- **(La franjita se sacó en la v1.2.33 y volvió en la v1.2.34, ahora siempre centrada en el Fair Value; ver esa sección. Los ajustes `FRANJA_FV_MODO` y `FRANJA_FV_MARGEN` ya no existen: ahora es `RANGO_FV_MARGEN`.)** Era solo dibujo: no cambiaba el Fair Value, el puntaje ni la categoría. Por defecto va del Fair Value −15% al +15%. En `config/ajustes.py`: `FRANJA_FV_MARGEN` cambia ese porcentaje, y `FRANJA_FV_MODO = "promedio_metodos"` la dibuja desde el promedio de los métodos que dan menos que el Fair Value hasta el promedio de los que dan más (con un solo método no hay franja).
- Como la categoría sale del puntaje y no de la franja, un precio puede quedar dentro de la franja con una categoría de "sobrevalorada" o "infravalorada".

### Precio sobre el punto y leyenda abajo (v1.2.25)

- En la barra de **Valoración** el precio de hoy se muestra **solo como número** (por ejemplo `$130`), justo arriba del punto de color. Sin la palabra "Precio".
- Debajo de la raya va la **leyenda**: a la izquierda "● Precio" (con el mismo punto del color de la categoría) y a la derecha "▌ Fair Value $Y +N%" (con la raya oscura y la distancia al Fair Value).
- Es solo un cambio de diseño: el Fair Value, el puntaje y la categoría no cambian. Si el precio queda muy cerca de un borde, el número se corre un poco para que no se corte.

### Caché del 22/10 con Stock Analysis como fuente principal (v1.2.26)

- **Resultado de la corrida:** Stock Analysis aportó datos a **165 de 166** empresas. Solo GEV quedó con Yahoo, probablemente por tener poca historia (la regla pide al menos 3 años fiscales). MRSH (Marsh McLennan) ya está incluida.
- **Métricas por empresa:** antes 9 empresas tenían 0 o 1 métrica; ahora ninguna. Quedan 3 con 2 métricas: BRK-B y NU (no pagan dividendo) y BA (sin EV/EBITDA actual ni dividendo). Reparto actual: 4/4 en 122 empresas, 3/4 en 21, 3/3 en 20, 2/4 en 1 y 2/3 en 2.
- **Datos rotos que se corrigieron:** el caché viejo traía medianas imposibles de empresas de afuera (por ejemplo MUFG: mediana de P/B 0,01 y de PER 0,10; ahora 1,00 y 17,62). Por eso 71 de 165 empresas cambiaron de categoría; la mayoría se movió un solo escalón. Parte del cambio puede deberse a un día de diferencia en los precios (21/10 vs 22/10), pero la mayor parte viene del cambio de fuente.
- **Fair Value y categoría:** solo 3 empresas quedan en contra por más de 5% (INTC, WDC y VST).
- **Cosas a tener en cuenta (no se cambió nada):**
  - **Dividend Yield de ITUB:** la app muestra ~1,5% (Stock Analysis y Yahoo coinciden en la tasa regular). Trendlyne informa 5,65% sobre los últimos 12 meses; en 2025 los dividendos fueron mucho mayores que en años anteriores (posibles pagos extra: es una inferencia, no lo confirmé). Es una diferencia de definición.
  - **GEV:** su mediana histórica sale de pocos años; es menos confiable que la del resto.
  - **Grupos con muchas "sobrevaluadas":** Energía (8 de 10) y Bancos y seguros (10 de 22). Puede ser real o efecto de compararse con una mediana de años de múltiplos bajos; queda para revisar.
  - **MELI:** el P/FCF de Stock Analysis (7,58) parece bajo; su flujo de caja incluye el negocio financiero. No está verificado.

### Pantalla: Sector en negrita, celeste en el Fair Value y nueva escala (v1.2.27)

- **Sector / Industria:** el sector va en **negrita** y la industria entre paréntesis (por ejemplo **Financiero** (Pagos y datos)). En el filtro, como no admite negrita, se ve "Financiero (Pagos y datos)". Los sectores sin industria muestran solo el nombre en negrita.
- **Market Cap** en negrita (tabla clásica y vista visual).
- **Barra de Valoración:** la raya y la franja del Fair Value usan tonos de **celeste claro**; la rayita del Fair Value es un celeste más fuerte. El punto del precio sigue con el color de la categoría.
- **Escala de valoración** (arriba de la tabla, estilo GuruFocus): título y cinco tramos de color con su rango de puntaje (70 o más, 58 a 69, 42 a 57, 30 a 41, menos de 30). Sin circulitos ni cuadraditos, también en el filtro y en el cartel de la categoría. El filtro de categorías ahora se llama **Valoración**.
- **Colores de las categorías** (más fáciles de distinguir): verde oscuro, verde lima, amarillo, naranja y rojo. El código repinta solo los cachés viejos según el nombre de la categoría, así que no hace falta regenerar nada.

### Tabla visual definitiva, filtros nuevos y reglas para GEV y MELI (v1.2.28)

**Las cuatro cosas que habían quedado anotadas en v1.2.26 (decididas con Guille):**
- **Dividend Yield de ITUB:** se deja como está (~1,5%, la tasa regular; la diferencia con otros sitios es de definición).
- **GEV (poca historia):** si una métrica tiene menos de **3 años** de historia propia (`MIN_ANIOS_MEDIANA_PROPIA` en `config/sectors.py`), la app no usa su mediana propia sino la **mediana de su sector** (la misma regla de respaldo que ya existía, con al menos 5 empresas pares). El caché ahora guarda cuántos años hay detrás de cada mediana (`anios_historia`). **Ojo:** el caché del 22/10 todavía no traía ese dato, así que para GEV se cargó a mano "2 años" (es una inferencia mía: cotiza desde abril de 2024). En la próxima corrida de `generar_cache.bat` el dato real reemplaza a ese. Efecto: GEV pasó de 92 puntos ("Podría estar infravalorada") a 39 ("Tendencia a sobrevalorada").
- **Energía y Bancos y seguros ("muchas sobrevaluadas"):** se deja como está.
- **MELI:** el P/FCF se descarta con una lista corta y explícita (`METRICAS_EXCLUIDAS` en `config/sectors.py`): su flujo de caja libre es unas 6,5 veces su ganancia y parece incluir fondos de clientes de Mercado Pago. MELI queda con 2 de 4 métricas; pasó de 81 a 74 puntos y sigue "Podría estar infravalorada". El motivo se ve en el detalle de la empresa. Ninguna otra empresa cambió.

**Tabla visual (ahora es la tabla principal):**
- Los **títulos ordenan al tocarlos** (flecha ▼ / ▲, la columna ordenada se oscurece): Empresa, Mkt Cap, Valoración (por distancia al Fair Value), Puntaje y Div. Yield. Títulos centrados, en blanco y más grandes; la columna Valoración tiene un tono azul clarito.
- **Empresa:** "Nombre • TICKER" con el mismo tono y tamaño; abajo, **sector** (industria) y la bandera del país. El **Market Cap** va en negrita, en la misma línea del nombre (a la derecha) y bajo su propio título "Mkt Cap", que también ordena. Los nombres salen completos desde la próxima corrida de `generar_cache.bat` (Yahoo daba nombres cortados; ahora se usa el nombre largo); mientras tanto se limpian las comas que quedaban colgadas.
- **Div. Yield:** número grande y mini gráfico con la serie anual contra su línea de **mediana de N años**. Mientras el caché no traiga la serie (se genera con la próxima corrida de `generar_cache.bat`) se ve el número y debajo "Mediana histórica: X%".
- **Rango de 52 semanas:** ya no está en la tabla; sigue en el detalle de cada empresa.
- La **tabla clásica** queda solo para revisión: tildando "Vista de revisión: métodos del Fair Value".
- Sector, industria y país **se siguen pudiendo filtrar** aunque ya no sean columnas (lo único que se pierde es ordenar por esas columnas).

**Filtros:** Sector / Industria y Valoración ahora son **pastillas** (sin selección = todas; la elegida se ve en azul oscuro). Requiere `streamlit>=1.46.0` (ya está en `requirements.txt`).

### Aviso legal fijo (v1.2.29; desde la v1.2.41 va al final de la página, ver esa sección)

- Barra fija al pie de la pantalla: "Herramienta de filtrado inicial, con fines informativos y educativos. No es una recomendación de inversión ni una oferta de compra o venta. Los datos pueden tener errores o estar desactualizados: investigá cada empresa antes de decidir." Se ve siempre.
- El texto es una base: se cambia en `config/ajustes.py` (`AVISO_LEGAL`; si se deja vacío no se muestra). Por ser Guille asesor registrado, conviene que lo revise y lo ajuste a lo que corresponda.
- README: se corrigió la frase vieja de "cada 6 horas" (la app solo lee el caché) y se agregó cómo limitar quién ve la app.

### Prueba de ROE y recompras, y notas sobre las tasas (v1.2.30, solo herramienta: no cambia ningún puntaje)

- **Nuevo `probar_roe_recompras.bat`:** baja de Stock Analysis (la misma página de ratios anuales que ya usa `generar_cache`, una por empresa, con pausa y respetando robots.txt) el **ROE**, el ROIC, las **recompras netas de acciones** ("Buyback Yield / Dilution"), el payout, el dividendo, el P/B y el PER, con hasta 5 años de historia. Guarda `resultados_roe_recompras.json` y `.txt`. Sirve para probar **aparte** (sin tocar la app) si ajustar el P/B de los bancos por su ROE, o sumar las recompras al dividendo, cambia el resultado y vale la pena. Se corre una sola vez; `python probar_roe_recompras.py JPM BAC` prueba solo algunas.
- **Puntaje "en sombra" (vs sector):** ya existe desde la v1.2.13 y se guarda en el caché (`score_total_sector`). Se ve solo en el panel "Seguimiento" (no en el detalle de cada empresa), que compara oficial contra sombra apenas hay dos copias del caché separadas por el mínimo de días. Con la actualización trimestral, la primera comparación posible es en diciembre.
- **Nota del 22/10 (simulación, no está en la app):** hoy el múltiplo medio de cada sector está muy por encima de su mediana de 5 años en Bancos (P/B 1,65 veces), Energía (P/FCF 1,46; EV/EBITDA 1,32) y Materiales, y por debajo en Software (0,63) y Comunicación (0,61–0,80). Por eso Energía (90 %) y Bancos (64 %) concentran las "sobrevaluadas". No se puede distinguir con estos datos si el sector está realmente caro o si cambió el nivel de tasas/mercado. Decisión pendiente (opciones: esperar el historial, ajustar cada empresa por lo que se encareció su sector, o combinar).

### Tabla visual: categorías tipo GuruFocus, dibujito del yield, nombre y ticker, tipografía (v1.2.33)

- **Categorías (solo cambia cómo se leen en pantalla):** son cinco niveles al estilo GuruFocus y todos empiezan con "Podría estar" porque es una estimación y no una afirmación: *significativamente infravalorada*, *moderadamente infravalorada*, *razonablemente valuada*, *moderadamente sobrevalorada* y *significativamente sobrevalorada*. Los cortes de puntaje no cambiaron (70 / 58 / 42 / 30). Los nombres que guardan el caché y las copias del historial siguen siendo los de siempre (`PODRÍA ESTAR INFRAVALORADA`, etc.); la tabla de equivalencias es `NOMBRE_VISIBLE` en `scoring/engine.py`. Por eso no hay que regenerar nada.
- **Etiqueta de valoración:** ahora es una pieza de color lleno, más grande (15 px) y centrada, para que los cinco colores se distingan bien. La escala de arriba muestra solo los nombres; el rango de puntaje de cada tramo aparece al pasar el mouse.
- **Barra de valoración (reemplazada en la v1.2.34):** sin franja ni leyenda. El **punto** es el precio (con su valor arriba) y la **rayita azul** es el Fair Value promedio, con su valor y la distancia al precio **justo abajo**. La barra solo deja un margen del 15 % a cada lado para que dos valores parecidos queden cerca (es solo dibujo).
- **Div. Yield (el dibujo cambió en la v1.2.34: ahora muestra el recorrido de los años; la escala corta queda de respaldo):** debajo del número hay una escala corta: la marca del centro es la **mediana histórica** y el punto es hoy. A la derecha rinde más que lo habitual y a la izquierda menos. El punto es **rojo, naranja, amarillo, verde claro o verde** según el puntaje que ese dividendo le da a la empresa en el score (mismos cortes que las categorías); si ese dato no está, según cuánto se aleja de su mediana. Si el puntaje usó la mediana de su sector (poca historia propia, ej. GEV), el dibujo y el texto muestran esa misma mediana ("Mediana del sector"). El texto dice "Mediana histórica" (desde la v1.2.35 ya no muestra la cantidad de años).
- **Empresa:** **Nombre** en negrita y (TICKER) sin negrita ni punto de separación; abajo, sector (industria) y bandera, sin negrita. **Market Cap** pasó a una columna propia, con ese nombre completo y los números centrados.
- **Tipografía:** Inter (pensada para pantallas y tablas de números; viene incluida en `assets/fuentes/`, no se baja de internet). Para volver a la de Streamlit: `FUENTE_APP = ""` en `config/ajustes.py`.
- **Vista de revisión (tabla clásica):** se ensancharon las columnas y la etiqueta de categoría puede ocupar más de una línea.
- **`probar_roe_bancos.bat`:** igual que `probar_roe_recompras.bat` pero solo para las 22 empresas de Bancos y seguros (2 o 3 minutos). Deja los mismos dos archivos de resultados.

### Vuelta a la v1.2.43, segunda mirada con el DCF y cambios de pantalla (v1.2.45)

**1) Vuelta atrás (decisión de Guille del 23/10/2026: "volvamos un paso para atrás").** La regla del PEG creíble (v1.2.44) quedó **apagada**: `PEG_CONDICIONAL["sectores"] = ()` en `config/sectors.py`. El puntaje, la categoría y el Fair Value de las 166 empresas son **idénticos a los de la v1.2.43** (se comprobó campo por campo). El código de la regla sigue ahí y probado; para prenderla de nuevo hay que poner `("Semiconductores", "Hardware y servicios TI")` en `"sectores"` y re-puntuar el caché. Motivo: la regla acercaba AVGO y NVDA a GuruFocus pero alejaba a AMAT, ADI, LRCX y DELL, subía mucho sus Fair Value, y dejaba a AVGO "razonablemente valuada" con un Fair Value 40 % por debajo del precio. En vez de afinar el PEG se prueba otra cosa: la segunda mirada con el DCF.

**2) Segunda mirada con el DCF (en curso, no cambia ningún puntaje).** La idea: para las empresas que el screener ve caras (categorías "tendencia a sobrevalorada" o "podría estar sobrevalorada"), ver qué dice el DCF propio (repositorio `M-todo-DCF`, pantalla "Modo lote") y así detectar los casos donde el screener se equivoca por mirar solo múltiplos contra su propia historia (AVGO: todos sus múltiplos están por encima de su historia, salvo el PEG). Hoy son **85 empresas**; en **23** de ellas GuruFocus no las ve caras (marcadas primero en la lista): TSLA, V, JPM, AVGO, VRTX, ABNB, RIO, MSI, LIN, ANET, SBUX, ARM, ORLY, CL, UNP, ADP, MS, SNOW, AIG, COIN, VST, TLN, ECL. Lista completa para pegar en el lote (las 23 primero, el resto de la más cara a la menos cara): `TSLA, V, JPM, AVGO, VRTX, ABNB, RIO, MSI, LIN, ANET, SBUX, ARM, ORLY, CL, UNP, ADP, MS, SNOW, AIG, COIN, VST, TLN, ECL, PBR, DELL, SAN, ITUB, PANW, XOM, AMD, ABBV, DE, BBVA, EQNR, AAPL, CSCO, SHEL, PSX, HSBC, PM, FCX, TTE, WMT, AMAT, AMGN, CAT, MO, JNJ, ING, LRCX, BNY, MRVL, MRK, MMM, CVX, NVS, MUFG, COP, WELL, BRK-B, INTC, KO, C, KLAC, SCCO, BP, SIEGY, WDC, CRWD, BHP, GILD, ADI, PFE, TSM, TXN, CVS, ASML, GEV, TMO, USB, ROST, SONY, PCAR, IBKR, GSK`. El lote lo corre Guille en su app de DCF (Yahoo está bloqueado desde el entorno de Claude) y devuelve el Excel. Con ese Excel se comparan, por empresa: categoría del screener, Fair Value del screener, valor por DCF y por múltiplos del DCF, y categoría de GuruFocus; y se mira si una segunda mirada mejoraría el método. **No se implementa nada en el screener sin decisión explícita de Guille.**

**3) Cambios de pantalla (todos pedidos por Guille el 23/10/2026):**
- **Encabezado:** franja **gris oscuro** (antes negra con filete verde); los textos ("Quiénes somos", "Abrite una cuenta con nosotros", "Comentarios") y, **a la derecha de ellos**, los iconos (YouTube, Instagram, mail, WhatsApp, Intramed) **de un solo color** (gris claro, blanco al pasar el mouse); el icono de Intramed es `assets/marca/intramed-mono.png` (versión blanca del original, que sigue en `intramed.png`). **"Abrite una cuenta con nosotros" ya no lleva recuadro.** Los iconos siguen escondidos en pantallas de menos de 1180 px, como antes.
- **Paneles blancos con sombra suave y sin bordes duros:** la tabla, los recuadros de Noticias y Filtro de empresas, las tarjetas del celular y las de la página de cada empresa. El **fondo de la página** pasa a un gris casi blanco (`FONDO_PAGINA = "#f5f6f8"` en `config/ajustes.py`) para que los paneles blancos se noten; con `"#ffffff"` vuelve al blanco de siempre. El encabezado de la tabla usa el mismo gris oscuro del encabezado de la página.
- **Columna Valoración:** la categoría en **negrita y con el color de su categoría** (verde para las baratas, rojo para las caras, etc.; se mantuvo el color por categoría para no mostrar en verde una empresa cara) y, debajo, **más chico y en gris**, "Fair Value $315 (+48%)".
- **Orden inicial por capitalización bursátil**, de mayor a menor (antes por Valoración); se puede cambiar tocando cualquier título, como siempre. `ORDEN_INICIAL` en `app.py`.
- **"Market Cap" se llama ahora "Capitalización bursátil"** en la tabla, el filtro, el selector del celular, la página de la empresa y el Excel.
- **Signo de pregunta "?"** al lado de "N empresas": despliega una descripción breve de cada una de las 7 columnas (`AYUDA_TABLA` en `ui/tabla_visual.py`).
- **Empresas subrayadas** (línea fina gris, azul al pasar el mouse): en el celular no existe el "pasar el mouse", así que el subrayado fijo es lo que avisa que se puede tocar. Vale para el nombre y el ticker.
- **Noticias Calientes y Filtro de empresas, uno al lado del otro** (en el celular quedan uno abajo del otro). Cada uno se despliega hacia abajo en su mitad y la mitad que se abre se **ensancha** (más ancho para los filtros). Los controles del filtro pasaron a ir de a dos por fila.
- **"Screener" se llama ahora "Filtro de empresas".**
- **Precio:** el título lleva debajo, chico y menos llamativo, "(Cotización origen)"; igual en las tarjetas del celular, en la página de la empresa y en el Excel ("Precio (USD, cotización origen)"). Es el precio de la acción en su mercado de origen, no el del CEDEAR en pesos.

**Lo que NO cambió:** metodología, pesos, categorías, Fair Value y datos (el caché es el de la v1.2.43).

### PEG con historia creíble en Semiconductores y Hardware (v1.2.44)

> **Apagada el mismo día (v1.2.45):** Guille pidió "volver un paso para atrás" porque no tenía sentido lo que se mostraba. Esta sección queda como registro de lo probado y de cómo se enciende de nuevo.

**Qué cambió (decisión de Guille del 23/10/2026):** en *Semiconductores* y *Hardware y servicios TI* el PEG vuelve **solo para las empresas donde es creíble**, con **25 %**; las otras cuatro métricas se achican a 0,75 de su peso (P/S 30 %, P/FCF, EV/EBITDA y PER 15 % cada una). Para las demás empresas de estas dos industrias queda la v1.2.43 sin cambios (P/S 40 %, sin PEG). El resto de los sectores no cambia.

**Cuándo el PEG es creíble (las 5 condiciones juntas, en `PEG_CONDICIONAL` de `config/sectors.py`):** (1) PEG de hoy de 0,1 o más; (2) mediana propia entre 0,3 y 3; (3) la mediana es al menos 2 veces el PEG de hoy; (4) ambos datos vienen de Stock Analysis; (5) la mediana tiene al menos 3 años de historia (si la fila no informa los años, esta condición no se aplica, igual que en el motor). La idea: el PEG sirve cuando su historia es normal y hoy está muy por debajo; no sirve cuando la historia es un disparate de ciclo (WDC: mediana 170; INTC: 6,4) o el PEG de hoy es un piso de ciclo (MU: 0,07).

**A quién le aplica hoy:** NVDA, AVGO, AMAT, ADI, LRCX y DELL (5 de 5 métricas). Las otras 19 de Semis y Hardware siguen con 4. Las otras 141 empresas quedan **idénticas** (se comprobó campo por campo).

| Empresa | Puntaje v1.2.43 → v1.2.44 | Categoría hoy | Fair Value v1.2.43 → v1.2.44 | GuruFocus |
|---|---|---|---|---|
| NVDA | 77,0 → 80,4 | Podría estar infravalorada | 314,64 → 372,35 (+48 % → +75 %) | Muy infravalorada |
| AVGO | 27,5 → 45,0 | Razonablemente valuada | 194,15 → 194,15 (-40 %) | Muy infravalorada |
| AMAT | 21,9 → 40,1 | Tendencia a sobrevalorada | 202,56 → 368,12 (-47 % → -3 %) | Muy sobrevalorada |
| ADI | 33,9 → 47,3 | Razonablemente valuada | 326,40 → 441,02 (-16 % → +14 %) | Sobrevalorada |
| LRCX | 24,8 → 42,4 | Razonablemente valuada | 138,73 → 248,02 (-40 % → +7 %) | Sobrevalorada |
| DELL | 11,6 → 30,8 | Tendencia a sobrevalorada | 186,92 → 414,77 (-59 % → -8 %) | Muy sobrevalorada |

**Resultado medido contra GuruFocus (163 empresas, lista del 23/10/2026):**

| | v1.2.42 (PEG 40 %) | v1.2.43 (P/S 40 %) | v1.2.44 (PEG creíble) |
|---|---|---|---|
| Correlación de orden | 0,683 | 0,800 | 0,796 |
| Categoría exacta | 39,3 % | 46,0 % | 44,2 % |
| A una categoría o menos | 84 % | 89 % | 89 % |
| Categorías opuestas | 18 | 14 | 13 |
| Contradicciones categoría / Fair Value | 9 | 4 | 5 |
| Correlación del Fair Value | 0,636 | 0,754 | 0,722 |
| Semis y Hardware (25 empresas) | 0,253 | 0,756 | 0,744 |

**Costos que hay que tener presentes:**
- **Nos aleja de GuruFocus en 4 de las 6:** AMAT, ADI, LRCX y DELL las ve caras y con la regla nuestro puntaje las ve más baratas. Nos acerca en AVGO y NVDA. El saldo neto es casi cero (0,800 → 0,796), con una categoría opuesta menos.
- **El Fair Value de las 5 empresas que lo recalculan sube mucho** (tabla de arriba) porque usa los mismos pesos. El de AVGO no cambia: el precio implícito por PEG (324 × 1,45 / 0,36 ≈ 1.300) supera 3 veces el precio y se descarta, así que AVGO queda "razonablemente valuada" en el puntaje con un Fair Value 40 % por debajo del precio: es la contradicción nueva (4 → 5).
- **AVGO sigue con todos los múltiplos por encima de su propia historia** salvo el PEG (P/S 17,3 contra 9,7; P/FCF 40,9 contra 19,6; EV/EBITDA 31,5 contra 18,2). Es un límite de comparar contra la historia propia: el crecimiento esperado de AVGO lo mide el PEG, no los otros cuatro. Una segunda mirada con flujos descontados es el complemento natural.
- **La regla se diseñó después de ver AVGO** (riesgo de sobreajuste) y el piso de 0,1 contradice el criterio anterior de "nunca descartar un PEG por bajo" (MU). Además la métrica pesa distinto según la empresa (4 o 5 métricas), lo que es más difícil de explicar.

**VALIDAR EL 1/12/2026 (compromiso con Guille):** la regla queda **fija hasta entonces**: no se tocan los umbrales antes de validar. Con la lista nueva de GuruFocus (fuera de muestra) y los retornos reales desde el 22/10 se compara, con el historial, v1.2.42 (PEG 40 %) contra v1.2.43 (P/S 40 %) contra v1.2.44 (PEG creíble): (1) ¿las 6 empresas con PEG creíble rindieron mejor que las otras de Semis y Hardware?; (2) ¿mejoró o empeoró la concordancia con GuruFocus fuera de muestra?; (3) ¿las contradicciones con el Fair Value crecieron? Los tres métodos se pueden recomputar porque el caché trae los campos `peg_*` y `ps_*`.

**Para volver atrás:** en `config/sectors.py` poner `PEG_CONDICIONAL["sectores"] = ()` y volver a puntuar (`python actualizar_ticker.py` re-puntúa todo el caché sin descargar). Eso devuelve la v1.2.43.

**Lo que cambió en el código:** `config/sectors.py` (`PEG_CONDICIONAL`, `peg_creible`, `metricas_de`), `scoring/engine.py` y `data/fetcher.py` (usan `metricas_de` en lugar de los pesos fijos del sector, tanto en el puntaje como en el Fair Value) y `app.py` (el detalle de la empresa muestra las columnas que corresponden a cada una).

### P/S en lugar del PEG en Semiconductores y Hardware (v1.2.43)

**Qué cambió (decisión de Guille del 23/10/2026, "prueba 2"):** en *Semiconductores* y *Hardware y servicios TI* el **PEG (40 %) sale y entra el P/S (precio / ventas) con el mismo 40 %**. Los otros tres métodos (P/FCF, EV/EBITDA y PER, 20 % cada uno) quedan igual. *Software y nube* y *Comunicación* **conservan el PEG**. En el resto de los sectores no cambia nada.

**Por qué:** al comparar con la lista de GuruFocus del 23/10/2026 (163 empresas) el mayor desacuerdo estaba en estas dos industrias (correlación de orden local 0,25). El PEG se distorsiona en las cíclicas: el crecimiento sale de un piso del ciclo y el cociente se vuelve inestable (WDC: PEG 0,25 contra mediana propia 170; MU: 0,07 contra 1,63; INTC: 0,78 contra 6,42). El P/S no se rompe con ganancias bajas, cíclicas o negativas y Stock Analysis lo trae para las 166 empresas, en la misma página que ya se baja.

**Resultado medido (simulación aparte, todo en `Ronda2_P-S_concordancia_GuruFocus_23-10-2026.xlsx`):** correlación de orden con GuruFocus 0,683 a 0,800; categorías opuestas 18 a 14; contradicciones entre categoría y Fair Value 9 a 4; en Semis y Hardware 0,25 a 0,76. La mejora supera al azar (remuestreo 100 %, permutación p = 0,02) y no depende de los 4 valores más extremos de GuruFocus. **Límites:** (1) el GF Value usa P/S, PER, P/FCF y P/B históricos, así que el parecido es en parte por construcción: **que nos parezcamos más a GuruFocus no prueba que tengamos razón** y el PEG podría estar captando algo que a ellos se les escapa (ej.: AVGO, que GuruFocus ve significativamente infravalorada, pasa de "razonablemente valuada" a "significativamente sobrevalorada"); (2) el P/S no mira márgenes ni deuda; (3) con 25 empresas el efecto local es orientativo. La validación contra la realidad llega con el historial del 1/12.

**Qué cambia en pantalla:** las 25 empresas de Semis y Hardware cambian de puntaje (ver lista abajo) y su **Fair Value** (usa los mismos pesos): ej. NVDA +100 % a +48 % sobre el precio, AMAT +23 % a -47 %, DELL +31 % a -59 %. El detalle de cada una muestra P/S en lugar de PEG y el método P/S en "Fair Value por método". Las otras 141 empresas quedan **idénticas** (se comprobó campo por campo).

**Lo que cambió en el código:** `config/sectors.py` (pesos), `data/stockanalysis.py` (lee la fila "PS Ratio"), `data/fetcher.py` (campos `ps_actual` / `ps_mediana` y método P/S del Fair Value: precio × mediana / actual, igual que EV/EBITDA) y `app.py` (nombre "P/S"). El motor no cambió: es genérico por métrica. P/S sin rango de descarte propio: solo se exige valor actual positivo y al menos 3 años de historia (la regla de Stock Analysis); sin eso queda el respaldo de la mediana del sector.

**Datos del caché:** el P/S de las 166 empresas se bajó el 23/10/2026 a las 18:17 con `probar_ps.bat` y se cargó con `incorporar_ps.py` (sin volver a bajar el resto: el caché conserva su fecha del 22/10). 165 empresas lo tienen; GEV queda sin P/S (2 años de historia), y no le afecta porque su sector (Industrial) no lo usa. Con el próximo `generar_cache.bat` el P/S se baja junto con las demás métricas.

**Historial:** la copia `data/historial/cache_2026-10-22.json` se reemplazó por el caché nuevo (mismos datos del 22/10, más el P/S del 23/10). Trae los dos juegos de datos, PEG y P/S, así que el 1/12 se puede puntuar con cualquiera de los dos métodos y comparar cuál acierta más; la copia anterior (v1.2.42, con PEG) queda en el historial de cambios de GitHub.

**Para volver atrás:** en `config/sectors.py` poner de nuevo `"peg": 0.40` en lugar de `"ps": 0.40` en las dos industrias y volver a puntuar (`python actualizar_ticker.py` re-puntúa todo el caché sin descargar).

**Pendiente (decisión de Guille):** sumar P/S con 0,15 en el resto de los sectores (sin bancos ni REITs) = "prueba 5": correlación 0,822, pero toca 13 sectores y se parece más a GuruFocus por construcción. Ya es solo cambiar pesos. Tampoco se ajustan los pesos del P/S sector por sector (la validación cruzada no mejora el 0,15 parejo).

### Tabla en el celular, descarga en Excel y traducción opcional de titulares (v1.2.42)

- **Celular: cada empresa es una tarjeta.** Con pantallas de hasta 900 px de ancho, la tabla ya no se muestra en 7 columnas apretadas: cada fila pasa a una tarjeta con el logo y el nombre arriba, el ticker a la derecha, la Valoración y el Puntaje, y debajo (con su etiqueta) Market Cap, Precio y Dividend Yield. En el celular desaparecen los títulos de columna y aparece un selector **"Ordenar por"** con 14 opciones (Valoración, Puntaje, Empresa, Ticker, Market Cap, Precio y Dividend Yield, en los dos sentidos). Elegir una opción ordena igual que tocar el título en la compu (comparten el mismo orden guardado). En la compu no cambia nada. El CSS está al final de `ui/tabla_visual.py` y el selector en `app.py` (`ORDENES_MOVIL`). Se revisó en capturas de 390 px de ancho; falta que Guille lo mire en su teléfono.
- **Botón "Descargar la tabla en Excel"** (al lado del conteo de empresas, solo en la vista visual). Baja un `.xlsx` con **las empresas que se ven en ese momento**, con los filtros y el orden elegidos. Hoja "Empresas" con 15 columnas (Empresa, Ticker, País, Sector, Industria, Market Cap, Precio, Fair Value, Fair Value vs precio, Valoración, Puntaje, Métricas usadas, Métricas totales, Dividend Yield y su mediana histórica); los números van como números (se pueden ordenar y sumar), con encabezado fijo y filtros de Excel. Hoja "Aviso" con la fecha de los datos, la versión y el aviso legal. El código está en `ui/exportar.py` y necesita `openpyxl` (agregado a `requirements.txt`). Si la generación falla, el botón no se muestra y la página sigue normal. Ojo: los datos vienen de fuentes de terceros (Yahoo Finance, Stock Analysis) con términos de uso propios; conviene revisarlos antes de promover la descarga como producto.
- **Traducción opcional de titulares de CNBC.** Con `NOTICIAS_IDIOMA = "en"` y `NOTICIAS_TRADUCIR = True` (`config/ajustes.py`), los titulares de CNBC se muestran en español usando el servicio gratuito MyMemory (`ui/traducir.py`); el titular original queda en el texto que aparece al pasar el mouse. Es traducción automática (puede tener errores) y, si el servicio falla o tarda más de 4 segundos, el titular queda en inglés. Sin mail se pueden traducir ~5.000 caracteres por día; con `NOTICIAS_TRADUCIR_MAIL` (o el mail de Comentarios) sube a ~50.000. Viene **apagado**: por defecto las noticias son de Ámbito, que ya está en español.
- **Qué no se pudo probar (igual que en la v1.2.41):** el entorno de desarrollo no tiene salida a internet, así que ni los feeds de Ámbito/CNBC ni MyMemory se probaron en vivo (sí se probó con feeds y respuestas simuladas). Hay que mirar en la PC de Guille si aparecen los titulares.
- **Comentarios (formulario):** Guille mandó un comentario y, después de habilitar el mail, la pestaña quedó en blanco. No se cambió código: la causa no está confirmada (puede ser la página de agradecimiento del servicio FormSubmit o que Streamlit Cloud bloquea la ventana nueva). Alternativa sólida: un Google Form propio y pasar solo su link en `ENLACES_MARCA["comentarios"]` (ya está soportado).
- **Contraste:** las etiquetas de Market Cap / Precio / Dividend Yield en la tarjeta del celular usan el mismo gris oscuro (`#4b5563`) que el resto del texto secundario.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

### Tabla más compacta con columna Ticker, orden de Valoración por categoría, noticias en español y aviso al final (v1.2.41)

- **Noticias Calientes y Screener vienen cerrados** al abrir la página (`NOTICIAS_ABIERTO = False` en `config/ajustes.py`; el Screener se abre con un toque y, cerrado, sus filtros siguen valiendo).
- **La escala de valoración y "Cómo leer la tabla" van adentro del Screener**, debajo de los filtros: primero la escala de colores y debajo la leyenda. Se sacó el subtítulo "según el puntaje final: 100 = muy barata, 0 = muy cara" (el rango de puntaje de cada tramo sigue en el texto que aparece al pasar el mouse). La leyenda ya no va al pie de la tabla.
- **Columna Ticker aparte, sin paréntesis** (la tabla pasa a 7 columnas: Empresa, Ticker, Market Cap, Precio, Valoración, Puntaje, Dividend Yield). El ticker también abre la página de la empresa y se puede ordenar (alfabético; primer toque de A a Z). Los anchos están en `ANCHOS_VISUAL` (`ui/tabla_visual.py`).
- **Tabla más compacta: entran casi el doble de empresas en la misma pantalla.** Medido en pantalla: las filas pasaron de 88 a 127 px de alto a 61 a 67 px. Se achicaron el relleno de las filas (14 → 8 px), el logo (38 → 32 px), el nombre (16 → 14 px), el sector (12,5 → 11,5 px), Market Cap, Precio y Fair Value (15,5 → 14 px), la categoría (15,5 → 14 px), la caja del puntaje y el encabezado. **Market Cap y Precio van con el mismo estilo que el resto**: ya no se oscurece el encabezado de la columna por la que se ordena (se reconoce por la flecha ▲ / ▼); **solo Valoración queda resaltada** (encabezado más oscuro y fondo celeste en las filas).
- **"Dividend Yield" sin abreviar** en el título de la tabla, en el filtro, en la leyenda y en la página de la empresa. En la tabla el rendimiento va **más chico (15 px, antes 22)** y el dibujito de los años fiscales a su lado (112 × 30 px, antes 156 × 46) con "Mediana histórica: X%" debajo. La página de cada empresa conserva el tamaño grande.
- **Razonablemente Valuada en amarillo** (`#CA8A04`, antes un marrón `#854D0E`). Los demás colores de letra no cambian.
- **"Significativamente Infravalorada ¿está al mismo tamaño?":** se midió en pantalla. Los cinco recuadros de la escala eran idénticos (266 × 51 px) y las etiquetas de la tabla medían todas 15,5 px, pero **el texto de la tabla (15,5 px) era más grande que el de la escala (13,5 px)**, y por eso parecía de otro tamaño. Ahora la etiqueta de la tabla y la de la escala miden lo mismo (14 px). Si Guille se refería a otra cosa, hay que decirlo.
- **Valoración ordena por categoría, sin mezclarse.** Antes se ordenaba por la distancia al Fair Value, y como la categoría sale del puntaje (y no del Fair Value), las categorías se intercalaban (hoy hay 9 empresas donde puntaje y Fair Value se contradicen). Ahora el primer orden (flecha ▼) es: Significativamente Infravalorada → Moderadamente Infravalorada → Razonablemente Valuada → Moderadamente Sobrevalorada → Significativamente Sobrevalorada; **adentro de cada categoría**, de mayor a menor distancia entre el Fair Value y el precio; "Datos insuficientes" siempre al final. Con la flecha ▲ se invierte todo. Se probó con el caché real: cada categoría queda en un solo bloque (5 bloques) en los dos sentidos. Ordenar por Puntaje no cambió (y también deja las categorías en bloque).
- **Aviso legal y "Datos al …" al final de la página**, en el pie (aviso, después "Datos al 22/10/2026 · Powered by Claude AI · v1.2.41"). Se sacó la barra fija de abajo de la pantalla y el renglón "Datos al" que estaba debajo de la franja negra. El texto del aviso sigue en `AVISO_LEGAL` (`config/ajustes.py`). También aparece en la página de cada empresa.
- **Titulares en español.** La fuente por defecto pasa a **Ámbito** (`NOTICIAS_IDIOMA = "es"`): feeds de Finanzas y Economía, y la Portada para saber qué notas están destacadas. CNBC (inglés) queda como alternativa: `NOTICIAS_IDIOMA = "en"`. Las fuentes y sus feeds están en `NOTICIAS_FUENTES` (reemplaza a `NOTICIAS_FUENTE` y `NOTICIAS_FEEDS`). El texto del recuadro cambia según el idioma (solo con CNBC dice "titulares en inglés"). Ajustes para español: "Meta de inflación" o "Vale la pena" no cuentan como las empresas Meta y Vale (solo si están en medio del titular), "Coca Cola" sin guion, "Visa y Mastercard" marca las dos, "Shell" solo.
- **Qué no se pudo probar:** desde el entorno de desarrollo no hay salida a internet, así que **los feeds de Ámbito no se probaron en vivo** (se probó el armado, el orden, las menciones y las fechas con feeds simulados). Las direcciones salen de un listado de terceros (feeder.co): `https://www.ambito.com/rss/pages/finanzas.xml`, `.../pages/economia.xml` y `.../home.xml`. Limitaciones conocidas: Ámbito tiene mucha economía y mercados argentinos y **poca tecnología y bolsa de Estados Unidos**, así que habrá menos titulares que nombren empresas del screener que con CNBC; y no se confirmó si alguna nota de Ámbito es solo para suscriptores (el filtro de notas de pago solo reconoce las de CNBC Pro). Si la fuente no responde, aparece el renglón chico de siempre.
- **En el celular la tabla se amontonaba** (7 columnas en pantallas de ~400 px): se resolvió en la v1.2.42 con tarjetas por empresa.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

### Noticias Calientes (ahora con CNBC), recuadros Screener / Noticias, formulario de Comentarios (v1.2.40)

- **Fair Value: queda como está** (decisión de Guille del 23/10, "que quede así por ahora, le veremos más adelante"). Equivale a la opción A. Ver el análisis del 23/10 en la sección v1.2.39 de más abajo.
- **Fuente de noticias: Bloomberg se descartó porque sus notas son de pago.** Ahora salen de CNBC, donde casi todo se lee gratis: Mercados (Market Insider), Tecnología, Economía y, para saber qué está en portada, Top News. Los feeds están en `NOTICIAS_FEEDS` (`config/ajustes.py`) y el nombre que se muestra en `NOTICIAS_FUENTE`. La regla de orden no cambió (empresas del screener, portada, recencia; 5 titulares; solo título, fuente y link). Las notas marcadas "CNBC Pro" (de pago) se sacan de la lista: se detectan por "CNBC Pro" en el título o `/pro/` en el link; **ese patrón no se pudo verificar contra datos reales**.
- **Qué falta confirmar:** (1) los links de los feeds salen de una página de terceros (feeder.co, actualizada el 17/10/2026, feeds probados el 3/10/2026: 30 notas cada uno); desde el entorno de desarrollo no hay internet, así que **no se probó la conexión real con CNBC**. Si en la PC aparece "CNBC no respondió", es lo primero para revisar. (2) No se pudieron leer las condiciones de uso de los RSS de CNBC (https://www.cnbc.com/rss-feeds/): conviene leerlas, porque la app solo muestra título, fuente y link pero el sitio tiene fines comerciales (apertura de cuentas). Se puede apagar todo con `NOTICIAS_ACTIVAS = False`.
- **Recuadros:** "Noticias Calientes" y "Screener" son dos recuadros desplegables con el mismo estilo (fondo celeste muy suave `#f1f6fc`, borde fino `#d3e2f2`, esquinas redondeadas). **Screener** tiene adentro todos los filtros (Sector / Industria, Valoración, País, Market Cap mínimo, Div. Yield mínimo, Métricas mínimas, vista de revisión y Actualizar datos); cerrado, los filtros siguen valiendo (solo se esconden). La tabla va debajo. Estilo en `ui/cajas.py` (Screener) y `ui/noticias.py` (Noticias). El orden es Noticias Calientes arriba y Screener debajo; el rediseño de los filtros queda para la próxima versión.
- **Comentarios:** ahora despliega un cuadro para escribir (mensaje obligatorio, nombre y mail opcionales, hasta 2.000 caracteres). **El mensaje llega por mail a `COMENTARIOS_MAIL` (`finanzas.medicos@gmail.com`)** a través del servicio gratuito FormSubmit (formsubmit.co), sin servidor ni claves propias. Detalles a tener en cuenta: (1) **la primera vez que alguien envíe un mensaje, FormSubmit manda un mail de activación a esa casilla y hay que confirmarlo**; los mensajes enviados antes de confirmar se guardan y llegan al activar. (2) Al enviar se abre una pestaña de FormSubmit que confirma el envío. (3) El mensaje pasa por los servidores de FormSubmit (el cuadro lo avisa); FormSubmit no ofrece garantía de disponibilidad ni panel, y guarda los mensajes 30 días. (4) Se desactivó el captcha de FormSubmit para que sea más simple; protege solo un campo oculto contra robots (`_honey`). Si llegara spam, se puede reactivar el captcha cambiando `_captcha` a `true` en `ui/marca.py`. (5) **No se pudo probar un envío real desde el entorno de desarrollo**: se comprobó que el formulario se dibuja bien y que arma el envío correcto (campos y destino), pero la entrega del mail se verifica enviando un mensaje de prueba. Si se arma un formulario propio (por ejemplo Google Forms), se pone su link en `ENLACES_MARCA["comentarios"]` y se usa ese en lugar del cuadro.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

### Noticias de Bloomberg, iconos de colores, WhatsApp visible y cuentas solo con logos (v1.2.39)

- **(Reemplazado en la v1.2.40: Bloomberg es de pago y la fuente pasó a CNBC.) Noticias de mercado (arriba de los filtros):** 5 titulares de Bloomberg (secciones Mercados, Tecnología y Economía) de las últimas 24 horas. **Regla de orden** (aprobada el 23/10): primero los que nombran empresas del screener (se marcan con una etiqueta verde con el ticker), después los que están en la portada de Bloomberg, y a igualdad, el más reciente. Cada renglón muestra solo **título, fuente y link** (no se copia el texto de la nota). Si hay menos de 5 notas en 24 h se amplía a 48 y a 72 h. Los titulares están en inglés (así los publica Bloomberg).
- **Cómo se baja:** 4 feeds RSS públicos (`NOTICIAS_FEEDS` en `config/ajustes.py`, hoy `NOTICIAS_FUENTES`: las tres secciones y la portada, que solo se usa para saber cuáles notas están ahí), todos a la vez y en segundo plano mientras se cargan los datos; se guardan 15 minutos (los visitantes comparten la descarga). Si Bloomberg no responde, la app sigue normal y aparece un renglón chico avisándolo. Código en `ui/noticias.py`; `NOTICIAS_ACTIVAS = False` lo apaga y `NOTICIAS_ABIERTO = False` lo deja plegado.
- **Qué se probó y qué no:** el armado, el orden, las menciones, el vencimiento de 15 minutos y las fallas se probaron con feeds simulados (56 chequeos). **No se pudo probar la conexión real con Bloomberg desde el entorno de desarrollo** (sin acceso a internet): los links de los feeds están tomados de una página de terceros (feeder.co). Si en la PC no aparecen titulares, es lo primero para revisar.
- **Cómo se detectan las empresas:** por nombre usado en los titulares (por ejemplo "Alphabet" o "Google" para GOOGL; tabla `ALIAS` en `ui/noticias.py`, con las 166 empresas) y por ticker en mayúsculas cuando tiene 3 letras o más. Los nombres que también son palabras comunes se buscan más largos (`Visa Inc`, `Target Corp`, `Shell Plc`) para no confundir "visa" de inmigración con Visa. Limitación: un titular que hable de una empresa sin nombrarla ("el mayor fabricante de chips") no cuenta como mención.
- **Iconos de colores:** YouTube, Instagram, Gmail y WhatsApp como insignias redondas (como la de Intramed), con el dibujo oficial de cada marca (paquete Simple Icons, licencia CC0). **WhatsApp ya se ve**, sin acción hasta que se cargue el link en `ENLACES_MARCA["whatsapp"]` (al pasar el mouse dice "WhatsApp: próximamente").
- **Abrite una cuenta con nosotros:** el desplegable muestra **solo los logos de Balanz e Inviu** (cada uno es un link a la apertura de cuenta). Se sacaron los renglones de abajo; los datos quedan anotados como comentario en `config/ajustes.py` por si se quieren volver a mostrar.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

#### Análisis del 23/10 (solo lectura, sin implementar): ¿se arregla el Fair Value usando solo el mejor método, o descartando el que "está raro"?

Pregunta de Guille: si el P/E de AMZN está inflado por una ganancia contable puntual, ¿no habría que descartarlo?, ¿y qué pasa si el Fair Value usa solo el mejor método? Se simuló sobre las 166 empresas del caché del 22/10. Se cuenta como "contradicción" una empresa cuya categoría va al revés del Fair Value en más de 15 % (barata con Fair Value por debajo del precio, o cara con Fair Value por encima), o que figura como "razonablemente valuada" con el Fair Value a más de 30 % del precio.

| Variante | Contradicciones | Correlación puntaje / FV (Spearman) | Empresas cuyo FV cambia más de 10 % |
|---|---|---|---|
| Hoy (promedio ponderado, corte 1/3x a 3x) | 9 | 0,913 | — |
| S1: solo el método de mayor peso | **17** | 0,800 | 78 |
| O1: tirar los métodos que se alejan más de 50 % de la mediana de todos | 7 | 0,865 | 47 |
| O2: corte actual + tirar los que se alejan más de 50 % de la mediana | 11 | 0,835 | 40 |

- **S1 (solo el mejor método) empeora:** arregla 3 casos (AMZN, DIS, INTC) y rompe 11 (GS, BX, BABA, AMD, AMAT, MRVL, KLAC, CSCO, MSI, MDLZ, VST). En semiconductores el método de mayor peso es el PEG (40 %), justo el más inestable: ADI pasa de +34 % a +102 %, LRCX de +35 % a +149 % y DELL de +31 % a +113 %.
- **O1 mejora poco y a un costo grande:** arregla 4 casos (AMZN, DIS, INTC, ADI), rompe 2 (AMAT, KLAC) y mueve más de 10 % el Fair Value de 47 empresas (28 %) para ganar 2 contradicciones. Baja la coherencia general (0,913 a 0,865).
- **AMZN:** hoy el Fair Value da +65 % (P/E 557 USD implícitos, EV/EBITDA 291, P/FCF descartado por ser 0,08x). Con S1 u O1 daría +16 %, coherente con "razonablemente valuada". Pero el P/E de AMZN no se descarta hoy porque 557 USD es solo 1,9 veces el precio (el corte es 3x).
- **Lo que ninguna regla automática resuelve:** detectar una ganancia "volada" por un hecho contable puntual (como la revalorización de la participación en Anthropic) requiere mirar la ganancia normalizada o las partidas extraordinarias de cada balance; el caché no tiene ese dato (ni el P/E forward). Descartar "lo que se aleja de los demás" detecta desacuerdo entre métodos, no cuál de ellos es el correcto: a veces el que se aleja es el bueno (GEV).
- **Nota técnica:** de 592 precios implícitos, 10 no se reproducen exactos con la fórmula simple (GEV P/E y P/FCF; PEG de NTES, TSM, ASML y SAP; P/FCF de INTC); la comparación igual vale porque la fila "Hoy" usa el Fair Value guardado.
- **Estado:** nada de esto se implementó. Queda abierta la decisión de Guille entre las opciones A, C y D (ver el análisis anterior).

### Franja con Quiénes somos / Abrite una cuenta / Comentarios, título con tipografía nueva y mayúsculas (v1.2.38)

- **Franja negra (derecha):** de izquierda a derecha, los iconos (YouTube, Instagram, mail, WhatsApp de la comunidad e **Intramed con su logo**), **Quiénes somos** (se muestra siempre; sin link queda como texto hasta que se cargue), **Abrite una cuenta con nosotros ▾** (con un borde verde, siempre visible) y **Comentarios**, y el toro chico. Se sacó el botón "Menú". En el celular el título y el toro quedan arriba y los textos pasan a un segundo renglón (el texto se acorta a "Abrite una cuenta"; los iconos se ocultan).
- **Abrite una cuenta con nosotros:** al tocarlo se despliega con los logos de **Balanz** (bordes redondeados) e **Inviu**; cada logo es un link a la apertura de cuenta (Balanz: `…/abrir-cuenta-2.aspx?reference=gdipalma@ap.balanz.com`; Inviu: `https://inviu.page.link/4Yo7`). Debajo de cada logo va un renglón chico: la identificación del agente de Balanz (Ap, matrícula y mail) y el alias de Inviu (solo texto, no es un link). Los logos son `assets/marca/balanz.png` e `inviu.png`; el de Intramed, `assets/marca/intramed.png`. Se cargan en `CUENTAS_MARCA` y `ENLACES_MARCA` de `config/ajustes.py`.
- **Comentarios:** por ahora abre un mail a `finanzas.medicos@gmail.com` con el asunto "Comentarios sobre TodoCedears" ya escrito. Si se arma un formulario (por ejemplo, Google Forms), se pone su link en `ENLACES_MARCA["comentarios"]`.
- **WhatsApp:** se sacó el número personal. El icono vuelve a aparecer cuando se cargue en `ENLACES_MARCA["whatsapp"]` el link de invitación a la comunidad (`https://chat.whatsapp.com/...`).
- **Título:** nueva tipografía (Poppins Bold, de aspecto parecido a la de Investing: redondeada y gruesa), con las letras superpuestas y un fino corte negro entre una y otra; la T y la C en verde vivo `#00E85C`. PNG con fondo transparente en `assets/marca/titulo-todocedears.png`.
- **Mayúsculas en la valoración:** cada palabra con su inicial en mayúscula ("Significativamente Sobrevalorada", "Razonablemente Valuada") en la tabla, la página de cada empresa, la escala de colores y las pastillas del filtro.
- **Imágenes más livianas:** los logos y el título se redujeron al tamaño que se usa en pantalla.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

#### Análisis del 23/10 (solo lectura, sin implementar): qué tira del promedio en las empresas que cambiarían con la opción B

- **Qué son los números:** 22 de 166 empresas tienen al menos un método descartado por el Fair Value (precio implícito fuera de 1/3x a 3x). Por método, el Fair Value descarta: PEG 7 de 42 empresas que lo usan, Div. Yield 6 de 113, P/E 4 de 143, P/FCF 4 de 129, EV/EBITDA 3 de 141, P/B 1 de 41. Además acepta, sin descartar, precios implícitos de 2x o más (o de 0,5x o menos) en 21 casos de P/FCF, 13 de P/E, 9 de PEG y 9 de EV/EBITDA: el corte es grueso.
- **Tres familias de causas** (ver el detalle en la respuesta del 23/10): (1) PEG en semiconductores (peso 40 %): 9 de 15 tienen un PEG de 0,07 a 0,97 que llena el puntaje de la métrica (95 a 100) porque depende de proyecciones de crecimiento; INTC, TXN, WDC y AVGO cambiarían de categoría solo por descartarlo; (2) múltiplos actuales distorsionados por un hecho puntual (AMZN: P/E de 20,1 con ganancias que incluyen una revalorización contable de Anthropic y P/FCF de 838,7 por la inversión en capacidad; MRK: P/E de 117 por un resultado contable deprimido); (3) medianas de 5 años que reflejan otra época (CRWD, P/E mediano 925; WDC, PEG mediano 170; DIS y AMZN, P/E mediano de 55 y 45).
- **Conclusión:** la opción B alinea el puntaje con el Fair Value, pero no corrige la causa (datos puntuales o referencias distorsionadas). En AMZN la haría pasar de "razonablemente valuada" a "significativamente infravalorada" apoyándose en un P/E que está inflado por una ganancia contable no operativa. Pendiente de decisión de Guille.

### Título nuevo, links cargados, menú con cuentas y tabla de 6 columnas (v1.2.37)

- **Título:** `assets/marca/titulo-todocedears.png` es el nuevo título (PNG con fondo transparente, letras superpuestas con un fino corte negro entre una y otra, la T y la C en verde vivo `#00E85C` sobre blanco). Se dibujó a partir de la imagen de Guille con la tipografía Inter Black; si se reemplaza el archivo por otro, la franja lo usa sin tocar código. La línea de abajo de la franja pasó de celeste a ese mismo verde.
- **Links (en `config/ajustes.py`, `ENLACES_MARCA`):** YouTube, Instagram, mail y WhatsApp salen como iconos arriba a la derecha (en el celular se ven solo el menú y el toro). **Intramed** va dentro del menú. **"Quiénes somos" sigue vacío** (no hay link: no se muestra).
- **Menú "Abrite una cuenta con nosotros" (`CUENTAS_MARCA`):** una fila por agente con logo, nombre y un renglón chico: **Balanz** ("Ap: Guillermo Di Palma · Mat. 2372 · gdipalma@ap.balanz.com") e **Inviu** ("Alias: G.DIPALMA.INVIU"). Logos: si existe `assets/marca/balanz.png` / `assets/marca/inviu.png` se usan esos archivos. Si no están, Balanz usa el icono del sitio que sirve Google (lo carga el navegador de quien mira; si no carga queda un cuadradito blanco) e Inviu muestra una inicial: **no se inventó ningún dominio** para Inviu.
- **Tabla de 6 columnas:** Empresa | Market Cap | Precio | **Valoración** | Puntaje | Div. Yield. La columna Valoración junta lo que antes eran dos: **arriba la leyenda** en letras de color y negrita (sin "Podría estar") y **abajo el Fair Value con la distancia al precio entre paréntesis** (`$693 (+157%)`). El título "Valoración" ordena por esa distancia al Fair Value (el orden de arranque); "Puntaje" ordena por puntaje. **Market Cap sin negrita.**
- **"Podría estar":** se sacó de las filas de la tabla. Se mantiene en la escala de colores de arriba, en la página de cada empresa y en la nota de cómo leer la tabla ("podría estar…"), que son los lugares donde queda claro que es una estimación y no una recomendación. Si se quiere volver al aviso chico sobre cada fila: `AVISO_PODRIA_EN_TABLA = True` en `config/ajustes.py`.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

(Reemplazado en la v1.2.37: la tabla tiene 6 columnas y la Valoración incluye el Fair Value.)
### Franja negra, tabla de 7 columnas, página de empresa y pie (v1.2.36)

- **Franja negra de punta a punta** arriba de todo (como Investing): **TodoCedears** en letras blancas y grandes a la izquierda, el toro de Finanzas para Médicos chiquito a la derecha, y el resto de la pantalla en blanco. Si guardás tu imagen del título como `assets/marca/titulo-todocedears.png`, se usa esa imagen en lugar del nombre escrito. A la derecha, **solo si cargaste los links** en `ENLACES_MARCA` (`config/ajustes.py`): iconos de YouTube, Instagram, mail y WhatsApp, y un **menú desplegable** con "Quiénes somos" y "Abrite una cuenta con nosotros". Lo que queda vacío (`""`) no se muestra: no hay links inventados. En WhatsApp alcanza con el número con código de país; en mail, con la dirección. Se ocultó la barra de Streamlit (Deploy y menú de los tres puntos). Sin subtítulo ni descripción debajo. La fecha de los datos va chica, a la derecha debajo de la franja ("Datos al 22/10/2026"), y al final de la página, "Powered by Claude AI · v1.2.36".
- **Tabla de 7 columnas (hoy 6, ver v1.2.37):** Empresa | Market Cap | Precio | Fair Value | Valoración | Puntaje | Div. Yield.
  - *Empresa:* **nombre y (TICKER) en negrita**; debajo, sector (industria) y bandera, sin negrita.
  - *Fair Value:* el valor y, entre paréntesis, cuánto más (+) o menos (−) que el precio de hoy; sin negrita y **sin barra**.
  - *Valoración:* solo la categoría, **en letras de color y negrita** ("Podría estar" chico arriba), sin bloque de color. La escala de arriba (con bloques de color) queda como leyenda.
  - Todos los títulos ordenan al tocarlos; "Valoración" ordena por puntaje y "Fair Value" por la distancia al precio.
- **Página de empresa:** al tocar el nombre o el logo de una empresa se abre su página (`?empresa=TICKER`): precio, Fair Value, valoración, puntaje y Div. Yield; la barra del Fair Value (al centro, con la franja de ±20 %, que salió de la tabla); el rango de 52 semanas; el desglose de métricas y el Fair Value método por método. Arriba, "← Volver a la tabla" devuelve la tabla **con los mismos filtros y el mismo orden** (viajan en el link como un texto corto `f=`). Si se usa el botón "atrás" del navegador, la tabla vuelve con los filtros por defecto. Se sacó el panel de detalle que estaba al final de la tabla. Todavía no hay descripción del negocio: esa información no está en los datos.
- **Corregido:** en el rango de 52 semanas los signos `$` se leían como fórmula y mostraban "Min: 464.01 — Max:" mal formado.
- **Sin cambios de método:** ninguna fórmula, peso, umbral, Fair Value, puntaje ni categoría cambió.

#### Prueba del 23/10 (solo simulación, no se implementó): Fair Value con los pesos del puntaje y el 15 % de 52 semanas

- **El Fair Value ya se calcula así:** es un promedio ponderado de los precios que da cada método, con **los mismos pesos del puntaje** (`SECTOR_CONFIG`), incluido el PEG (ej. MSFT: PEG 0,40; P/FCF, EV/EBITDA y P/E 0,20 cada uno; 639,35 es exactamente ese promedio). El PEG entra al Fair Value en 35 de las 42 empresas cuyo sector lo usa; en el resto da un precio absurdo o falta el dato.
- **Lo que el Fair Value no tiene** es el 15 % técnico del puntaje, y **descarta** los métodos que dan un precio fuera de 1/3 a 3 veces el actual (el puntaje los sigue contando).
- **Variante V1** (85 % el Fair Value de hoy + 15 % el punto medio del rango de 52 semanas; el caché no guarda el promedio de 52 semanas): las contradicciones categoría vs Fair Value bajan de 9 a 5 y la correlación de orden entre puntaje y distancia al Fair Value sube de 0,913 a 0,928. **Pero es en parte mecánico:** un 15 % del Fair Value pasa a ser un precio cercano al de hoy, así que la distancia mediana al precio se achica de 20,7 % a 17,0 % sin que haya más información sobre el valor de la empresa.
- **Variante V2** (no descartar nada, como hace el puntaje): 4 contradicciones, pero con Fair Values absurdos (WDC 273 veces el precio, MU 10, INTC 3,8). **No sirve:** el descarte es necesario.
- **Conclusión:** alinear el Fair Value hacia el puntaje no aporta información y esconde diferencias; la alternativa lógica sigue siendo alinear el puntaje hacia el Fair Value (que el puntaje descarte lo mismo), medida el 22/10: baja las contradicciones de 9 a 3 pero cambia 11 categorías. Ninguna se implementó.

### Cartel oscuro, medidor de valoración, franja más grande, "Mediana histórica" y IBKR corregida (v1.2.35)

- **(Reemplazado en la v1.2.36 por la franja negra.) Cartel de arriba:** fondo azul noche con **letras blancas** ("Todo" en blanco y "Cedears" en celeste), el logo de Finanzas para Médicos sobre un disco blanco y un **subtítulo nuevo** (`SUBTITULO_APP` en `config/ajustes.py`, se cambia a gusto). Se sacó el subtítulo viejo ("Detector de empresas potencialmente infravaloradas — datos de Stock Analysis y Yahoo Finance") y el **cuadro azul grande del caché**: ahora la fecha de los datos va chica, arriba a la derecha del cartel ("Datos al 22/10/2026", con la versión). Los avisos que sí importan siguen: caché con más de 100 días y Yahoo caído.
- **(Reemplazada en la v1.2.36: ahora son solo letras de color, sin medidor ni píldora; `ESTILO_ETIQUETA` ya no existe.) Etiqueta de valoración:** por defecto es un **medidor** de cinco tramos de color, de la más barata (izquierda) a la más cara (derecha), con el tramo de la empresa encendido y su nombre debajo ("Podría estar" chico y la categoría grande). La escala de arriba tiene el mismo orden y los mismos colores. Con `"pildora"` vuelve la etiqueta de color de la v1.2.34.
- **Barra (desde la v1.2.36 está en la página de cada empresa, no en la tabla):** la franja ahora es de ±20 % (`RANGO_FV_MARGEN`) y la escala llega a 1,8 veces el Fair Value (`ESCALA_BARRA_VECES`): la franja pasó de ocupar el 20 % del largo de la barra al 31 %, y quedan pegadas al borde 15 de las 166 empresas (9 %; el número de abajo, +N %, siempre es el real). La franja, la rayita y el punto son más grandes. Sigue siendo una zona de referencia, no un intervalo de confianza; es solo dibujo.
- **Div. Yield:** la leyenda dice solo **"Mediana histórica: X %"**, sin la cantidad de años (cada empresa tiene una historia distinta). Si el puntaje usó la mediana de su sector (poca historia propia, ej. GEV) dice "Mediana del sector", porque ahí el número no es de la empresa.
- **IBKR (decisión del 22/10):** se descartó a mano su **P/B** (`METRICAS_EXCLUIDAS` en `config/sectors.py`): el de hoy (6,2) y los de años anteriores en la fuente (0,6 a 1,4) parecen calculados con distinta base. Su puntaje pasó de 27,6 a 40,3: de "significativamente sobrevalorada" a **"moderadamente sobrevalorada"**. Se re-puntuó el caché y se verificó fila por fila que **no cambió ninguna otra empresa**. La copia `data/historial/cache_2026-10-22.json` es idéntica al caché.
- **Sin cambios de método:** no se tocó ninguna fórmula, peso, umbral ni Fair Value. La corrección por re-valuación del sector (el 42 %) **sigue en espera hasta la comparación del 1/12**.
- **Pendiente de decisión (no implementado):** hay 9 de 166 empresas (5 %) donde la categoría y el Fair Value no cuentan la misma historia (2 de lados opuestos: GEV e INTC; 7 "razonablemente valuadas" con el Fair Value a más de 30 % del precio: NEM, AMZN, DIS, AVGO, ADI, LRCX, DELL). Causas: el puntaje le da peso al PEG (que el Fair Value no usa) y sigue contando métodos que el Fair Value descarta por dar precios absurdos (fuera de 1/3 a 3 veces el precio). Contado con los datos del 22/10: si el puntaje descartara lo mismo que el Fair Value, las contradicciones bajarían de 9 a 3, pero 11 empresas cambiarían de categoría (algunas con saltos grandes, ej. AVGO de razonable a significativamente sobrevalorada). Es un cambio de método: solo con decisión explícita.

### Barra con el Fair Value al centro, recorrido del yield, nombre TodoCedears y tema de finanzas (v1.2.34)

- **Barra de valoración:** el **Fair Value (rayita azul, con su valor y su distancia abajo) va siempre en el centro**. La **franja celeste** (Fair Value ±15 %, simétrica) también está siempre en el centro. El **punto** es el precio de hoy, con el color de la categoría y su valor arriba: a la izquierda cotiza por debajo del Fair Value, a la derecha por encima. La escala es logarítmica: el punto llega al borde cuando el precio es el **doble** (derecha) o la **mitad** (izquierda) del Fair Value, así que la mitad y el doble quedan a la misma distancia del centro; más allá de eso el punto se queda en el borde. Es solo dibujo: no cambia el Fair Value, el puntaje ni la categoría. Se cambia en `config/ajustes.py`: `RANGO_FV_MARGEN` (0.15) y `ESCALA_BARRA_VECES` (2.0). **La franja es una zona de referencia, no un intervalo de confianza:** con los datos del 22/10, los métodos del Fair Value discrepan entre sí (mediana de las 165 empresas con 2 métodos o más) cerca de ±23 % alrededor del Fair Value promedio, y en 1 de cada 4 empresas más de ±37 %.
- **Etiqueta de valoración:** "Podría estar" va chico arriba (aviso de que es una estimación) y la categoría grande abajo. En los filtros y en el Seguimiento se usa el nombre corto, sin "Podría estar" ("Significativamente infravalorada"); el aviso queda en cada empresa, en la escala y en el aviso legal.
- **Div. Yield con su recorrido:** debajo del número hay una línea con el rendimiento de **cada año fiscal** de los últimos 5 años (un puntito por año), una línea punteada con su **mediana** y, al final, **hoy** (punto con el color según su puntaje: rojo, naranja, amarillo, verde claro, verde). Los datos son anuales, no diarios. Se dibuja cuando hay 3 años o más y la mediana de esos años coincide con la mediana que usó el puntaje; si no, queda la escala corta de la v1.2.33. El caché trae la serie en el campo `dividend_yield_serie` (el generador ya la guardaba desde la v1.2.28). **Los datos del 22/10 se completaron con la corrida de `probar_roe_recompras.bat` del mismo día** (mismos datos de Stock Analysis): 131 empresas tienen serie; el resto no paga dividendo, tiene menos de 3 años o su serie no coincide con la mediana (INTC). **No cambió ningún puntaje ni categoría** (se comparó campo por campo con el caché anterior). Con la actualización de diciembre, el generador la guarda solo.
- **Nombre y logo:** la app se llama **TodoCedears** (`NOMBRE_APP` en `config/ajustes.py`). Desde la v1.2.36 el nombre va en la franja negra de arriba y el logo de **Finanzas para Médicos** va chiquito a la derecha (la comunidad y el canal de YouTube del dueño; `assets/marca/`, código en `ui/marca.py`), que también es el icono de la pestaña del navegador. Los iconos y el menú se completan en `ENLACES_MARCA` (ver v1.2.36).
- **Tipografía y colores:** se mantiene Inter y ahora con **números tabulares** en toda la app (todas las cifras con el mismo ancho: los totales y porcentajes quedan alineados como en una planilla). Para ganar contraste (tomando como modelo la tabla de Investing): encabezado de la tabla y controles en **gris pizarra oscuro** (la gama del logo, `#222d36`), texto secundario más oscuro (del gris `#6b7280` al `#4b5563`), texto principal casi negro azulado y gris azulado muy claro en los controles (`.streamlit/config.toml`). El rojo/naranja/amarillo/verde queda solo para la valoración.
- **Columna Puntaje:** se mantiene por ahora, para detectar errores; la idea es sacarla más adelante.
- **Corrección de la copia del 22/10 (`data/historial/cache_2026-10-22.json`):** en la v1.2.32 había quedado una versión vieja, sin las reglas de GEV y MELI de la v1.2.28 (GEV figuraba como "significativamente infravalorada" con 92 puntos en vez de "moderadamente sobrevalorada" con 39; MELI con 81 en vez de 74). Eso habría ensuciado la primera medición del Seguimiento. Ahora la copia es **idéntica** al caché del 22/10 (incluida la serie del yield). **Hay que reemplazar también esa copia en tu carpeta** (copiar el contenido del ZIP encima, sin borrar `data/historial/`).

#### Prueba del ROE real en los 22 bancos (22/10; solo análisis, no cambia ningún puntaje)

Con los datos de `probar_roe_bancos.bat`. Los criterios se fijaron antes de calcular.
- **T1 — "P/B ajustado por ROE" = PER:** P/B ÷ ROE es, por definición, el PER (si el ROE se calcula sobre el mismo patrimonio y ganancia). En los 22 bancos la diferencia mediana es 6,9 % (14 de 22 con menos de 10 %). Ajustar el P/B por el ROE **no agrega información nueva**: el PER ya pesa 35 % en el puntaje de Bancos y seguros.
- **T2 — ¿el ROE explica el P/B?** Hoy, entre bancos (sin IBKR): **sí**, R² = 0,80 (más ROE, más P/B). A lo largo de los años dentro de cada banco (105 observaciones banco × año): **no tanto**, R² = 0,22 (0,58 sin ROE extremos). Por el criterio previo (R² ≥ 0,40 en los dos cortes) **no pasa**.
- **T3 — ¿el cambio del ROE explica la re-valuación del P/B?** Correlación entre P/B de hoy ÷ su mediana y ROE de hoy ÷ su mediana: Pearson 0,42, Spearman 0,36 (criterio: ≥ 0,50). **No pasa.** Casos: SAN (P/B 2,4 veces su mediana con ROE 1,2 veces), BBVA (2,2 y 1,2), HSBC (2,0 y 1,1), C (1,8 y 1,4). Pero MUFG (1,6 y 1,4) sí tiene fundamentos.
- **T4 — impacto:** (A) dividir el P/B por el cambio de ROE movería 6 de 22 bancos un escalón hacia "más barata"; (B) pesos P/B 0,20 / PER 0,55 / DY 0,25 moverían 5. Como T2 y T3 no pasan, **no se propone cambiar el puntaje de bancos**.
- **Dato a revisar (IBKR):** su P/B de hoy es 6,2 contra una mediana de 0,76 (el último año fiscal figura en 1,40). Parece una inconsistencia de la fuente (la capitalización de hoy no es la misma base que la de los años anteriores) y empuja su categoría a "significativamente sobrevalorada". Falta verificarlo; si se confirma, correspondería excluir su P/B a mano (`METRICAS_EXCLUIDAS`, como MELI), cosa que no se hizo sin una decisión explícita. También: Stock Analysis no trae el ROE de hoy de MS (se usó el del último año fiscal) y el de HDB está afectado por su fusión con HDFC.

### Se prueba y se descarta el puntaje "ajustado"; panel de Seguimiento más claro; ROE corregido (v1.2.32)

- **Qué pasó:** la v1.2.31 agregó un tercer puntaje en sombra ("ajustado": la historia de cada empresa corregida por cuánto se encareció su sector). Con los datos del 22/10 cambiaba la categoría de 69 de las 166 empresas (42 %; 58 por un escalón y 11 por dos) y llevaba el promedio de cada sector hacia el centro (Energía 24 → 44, Bancos 39 → 54, Comunicación 65 → 54). Por construcción un ajuste así no puede decir que un sector entero está caro o barato, y no se puede saber hoy si acierta más. Como no cambia el puntaje oficial y solo agrega datos al panel, **se sacó en la v1.2.32**: el puntaje oficial no cambia y ya no se guarda ninguna columna `*_ajustado`. La simulación se puede rehacer cuando haga falta, fuera de la app, con las copias de `data/historial/` (guardan los valores actuales y las medianas de cada empresa).
- **Sigue en la app el puntaje en sombra "vs sector"** (v1.2.13, aprobado el 21/10): solo se ve dentro del panel "Seguimiento", que está cerrado por defecto. No aparece en la tabla ni en el detalle de cada empresa. Si se quiere sacar también, es una línea en `scoring/engine.py`.
- **Seguimiento más claro:** una sola tabla "Por categoría" con oficial y vs sector lado a lado, y, mientras falta la segunda copia, el cartel dice desde qué fecha se puede medir (última copia + 20 días).
- **Copia del 22/10:** `data/historial/cache_2026-10-22.json` queda en el ZIP, sin columnas ajustadas. **No borrar la carpeta `data/historial/`**: copiar el contenido del ZIP encima de la carpeta actual. En diciembre, al correr `generar_cache.bat`, se crea la segunda copia y el panel mide solo.
- **`probar_roe_recompras.py` corregido:** en la v1.2.30 el lector se quedaba solo con las tablas de múltiplos y rendimientos y descartaba la de "Financial Efficiency", así que el **ROE y el ROIC no se bajaron**. Ahora pide también esa tabla (`PALABRAS_TABLAS`). Para tener el ROE real hay que volver a correr `probar_roe_recompras.bat`. Es una herramienta aparte: no cambia ningún puntaje.

### Reglas de datos (v1.2.11)

- **Valores imposibles se descartan y el peso se reparte entre las métricas que quedan.** Se descarta una métrica si su valor actual o su mediana histórica cae fuera de un rango posible (ej.: un PER de 0,1). Los rangos están en `config/sectors.py` (`RANGOS_PLAUSIBLES`) y solo cortan lo imposible, no los valores altos pero reales.
- **Mínimo de métricas: 1.** Si no queda ninguna métrica fundamental, la categoría se arma solo con el rango de 52 semanas (la columna "Métricas" muestra 0/N). Gris solo si no hay ni eso.
- **PEG: se compara contra la mediana de su sector** (Tecnología y Comunicación), no contra sí mismo. El PEG nunca se descarta por ser alto o bajo.
- **Fair Value:** un método cuyo precio implícito queda fuera de 1/3× – 3× el precio actual no entra al promedio del Fair Value (el motivo se ve en el detalle). No cambia el score.
- **Empresas de fuera de EEUU (`data/moneda.py`):** los estados contables se convierten a la moneda de cotización (tipo de cambio anual para la historia) y las acciones se expresan en equivalentes del ADR. Si Yahoo rotula mal la moneda de los estados (caso VALE), se detecta comparando contra los múltiplos de Yahoo y no se convierte.
- **Historial:** cada vez que corrés `generar_cache.bat` queda una copia con fecha en `data/historial/`.

Para aplicar el control de moneda a las empresas de afuera sin bajar todo: `actualizar_extranjeras.bat`.
Para ver qué hace con cada ADR: `probar_moneda_screener.bat` (guarda `resultados_moneda_screener.txt`).

### Categorías de color

| Color | Categoría (como se lee en pantalla desde la v1.2.33) | Score |
|---|---|---|
| 🟢 Verde oscuro | Podría estar significativamente infravalorada | ≥ 70 |
| 🟩 Verde claro | Podría estar moderadamente infravalorada | 58–69 |
| 🟡 Amarillo | Podría estar razonablemente valuada | 42–57 |
| 🟠 Naranja | Podría estar moderadamente sobrevalorada | 30–41 |
| 🔴 Rojo | Podría estar significativamente sobrevalorada | < 30 |
| ⚫ Gris | Datos insuficientes (ni métricas ni rango de 52 semanas) | — |

> ⚠️ **Aviso:** Este screener es una herramienta de filtrado inicial. Una empresa con score alto puede ser una trampa de valor. Siempre investigá más antes de invertir.

## Instalación

```bash
git clone https://github.com/TU_USUARIO/cedear-screener.git
cd cedear-screener
pip install -r requirements.txt
streamlit run app.py
```

## Deploy en Streamlit Cloud

1. Fork este repositorio en tu GitHub
2. Entrá a [share.streamlit.io](https://share.streamlit.io)
3. "New app" → elegís el repo → `app.py` como archivo principal
4. Deploy

La app solo **lee el caché** (`data/cache_datos.json`) y no consulta Yahoo ni Stock Analysis: los datos se actualizan una vez por trimestre corriendo `generar_cache.bat` en la PC y subiendo el caché nuevo a GitHub (Streamlit Cloud se actualiza solo al subirlo).

Si la app es pública, cualquiera con el link la puede usar; para limitar quién entra: *App settings → Sharing → "Only specific people can view this app"*.

## Estructura del proyecto

```
cedear-screener/
├── app.py                  # App Streamlit principal
├── requirements.txt
├── config/
│   ├── sectors.py          # Sectores, métricas, pesos y universo de tickers
│   └── ajustes.py          # Interruptor de Stock Analysis, nombre de la app, tipografia, barra de valoracion, aviso legal
├── data/
│   ├── fetcher.py          # Descarga de datos (Yahoo Finance)
│   ├── moneda.py           # Control de moneda y acciones por ADR (empresas de fuera de EEUU)
│   ├── stockanalysis.py    # Ratios de Stock Analysis (respaldo o fuente principal)
│   ├── resumen.py          # Resumen de fuentes al generar el caché
│   ├── historial/          # Copias con fecha del cache (se crean con generar_cache)
│   └── tickers_custom.json # Universo personalizado (se genera al editar)
├── scoring/
│   ├── engine.py           # Motor de scoring y categorías
│   └── seguimiento.py      # Seguimiento con las copias del historial
├── ui/
│   ├── tabla_visual.py     # Vista visual de la tabla (v1.2.16)
│   ├── fuentes.py          # Tipografia Inter incrustada en el CSS (v1.2.33)
│   ├── marca.py            # Franja negra de arriba, iconos de colores, textos, desplegable de cuentas y pie (v1.2.36 a v1.2.39) e icono de la pestaña
│   ├── noticias.py         # Noticias Calientes (v1.2.39; CNBC desde la v1.2.40): descarga, orden por la regla aprobada y dibujo
│   ├── traducir.py         # Traducción opcional de titulares de CNBC con MyMemory (v1.2.42)
│   ├── exportar.py         # Descarga de la tabla en Excel (v1.2.42)
│   ├── cajas.py            # Estilo del recuadro Screener (v1.2.40)
│   ├── estado.py           # Filtros y orden en la URL para volver desde la pagina de una empresa (v1.2.36)
│   ├── logos.py            # Logos: archivo local, favicon o iniciales
│   └── banderas.py         # Banderas de los paises (v1.2.21)
├── assets/logos/           # Logos 64x64 (<TICKER>.png), ya incluidos desde la v1.2.17
├── assets/flags/           # Banderas 48x36 (<codigo>.png) de los paises
├── assets/marca/           # Logo de Finanzas para Medicos (128 px)
├── assets/fuentes/         # Tipografia Inter (incluida, licencia SIL OFL); se elige en config/ajustes.py (FUENTE_APP)
├── probar_ps.py/.bat       # Baja el P/S y otros multiplos de Stock Analysis (solo trae datos, v1.2.43)
├── incorporar_ps.py        # Carga esos datos en el cache y vuelve a puntuar sin descargar nada (v1.2.43)
└── descargar_logos.py/.bat # Baja los logos a assets/logos/
```
