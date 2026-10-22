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
| Semiconductores | PEG (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Software y nube | PEG (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Hardware y servicios TI | PEG (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Energía | P/FCF (35%) | EV/EBITDA (30%) | Div. Yield (25%) | P/B (10%) |
| Salud | P/FCF (30%) | EV/EBITDA (25%) | PER (25%) | Div. Yield (20%) |
| Utilities | Div. Yield (45%) | P/FCF (20%) | EV/EBITDA (20%) | PER (15%) |

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
- **(Desde la v1.2.33 la franjita ya no se dibuja.)** Era solo dibujo: no cambiaba el Fair Value, el puntaje ni la categoría. Por defecto va del Fair Value −15% al +15%. En `config/ajustes.py`: `FRANJA_FV_MARGEN` cambia ese porcentaje, y `FRANJA_FV_MODO = "promedio_metodos"` la dibuja desde el promedio de los métodos que dan menos que el Fair Value hasta el promedio de los que dan más (con un solo método no hay franja).
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

### Aviso legal fijo (v1.2.29)

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
- **Barra de valoración:** sin franja ni leyenda. El **punto** es el precio (con su valor arriba) y la **rayita azul** es el Fair Value promedio, con su valor y la distancia al precio **justo abajo**. La barra solo deja un margen del 15 % a cada lado para que dos valores parecidos queden cerca (es solo dibujo).
- **Div. Yield:** debajo del número hay una escala corta: la marca del centro es la **mediana histórica** y el punto es hoy. A la derecha rinde más que lo habitual y a la izquierda menos. El punto es **rojo, naranja, amarillo, verde claro o verde** según el puntaje que ese dividendo le da a la empresa en el score (mismos cortes que las categorías); si ese dato no está, según cuánto se aleja de su mediana. Si el puntaje usó la mediana de su sector (poca historia propia, ej. GEV), el dibujo y el texto muestran esa misma mediana ("Mediana del sector"). El texto dice "Mediana 5 años" cuando el caché trae los años de historia y "Mediana histórica" cuando no (el caché del 22/10 todavía no los trae; con la actualización de diciembre sale solo).
- **Empresa:** **Nombre** en negrita y (TICKER) sin negrita ni punto de separación; abajo, sector (industria) y bandera, sin negrita. **Market Cap** pasó a una columna propia, con ese nombre completo y los números centrados.
- **Tipografía:** Inter (pensada para pantallas y tablas de números; viene incluida en `assets/fuentes/`, no se baja de internet). Para volver a la de Streamlit: `FUENTE_APP = ""` en `config/ajustes.py`.
- **Vista de revisión (tabla clásica):** se ensancharon las columnas y la etiqueta de categoría puede ocupar más de una línea.
- **`probar_roe_bancos.bat`:** igual que `probar_roe_recompras.bat` pero solo para las 22 empresas de Bancos y seguros (2 o 3 minutos). Deja los mismos dos archivos de resultados.

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
│   └── ajustes.py          # Interruptor de Stock Analysis (apagado / respaldo / principal)
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
│   ├── logos.py            # Logos: archivo local, favicon o iniciales
│   └── banderas.py         # Banderas de los paises (v1.2.21)
├── assets/logos/           # Logos 64x64 (<TICKER>.png), ya incluidos desde la v1.2.17
├── assets/flags/           # Banderas 48x36 (<codigo>.png) de los paises
├── assets/fuentes/         # Tipografia Inter (incluida, licencia SIL OFL); se elige en config/ajustes.py (FUENTE_APP)
└── descargar_logos.py/.bat # Baja los logos a assets/logos/
```
