# Lista maestra de pendientes para el 01/12/2026 (TodoCedears)

Esta es la lista de verdad. Los recordatorios programados del 1/12 mandan a leer este archivo. Regla de oro: **no se cambia ningún método sin la decisión explícita de Guille** (primero problema, teoría y pros y contras). Y hay que decirle siempre la verdad cruda; con ~40 días de datos nada es concluyente.

Reglas fijas: español simple con voseo, estilo Dorsey (definición + ejemplo con números), trato de amigo, cerrar con "Conclusión resumen", no inventar datos, no más puntajes en sombra, no mostrar método ni pesos en pantalla. En el tema GuruFocus incluir siempre: "Que nos parezcamos más a GuruFocus no prueba que tengamos razón. El PEG podría estar captando algo que a ellos se les escapa."

## 🆕 Actualización 04/11/2026 (lo último; manda sobre lo de abajo si se contradice)
**v1.5.65 (10/11) — Sin escalón en la excepción de los analistas:** la estimada entra de a poco entre 1,3 y 1,7 veces (1,5 ± desvío estándar 0,2). Recalcular el desvío cuando estén las estimaciones de todas las empresas.

**v1.5.63 (10/11) — Años de la SEC de la segunda corrida incorporados** (Altria y bancos con 13 años; 29 ADR en la base de Yahoo; 5 sin ganancia por acción de la SEC por unión rara). **Falta:** que Guille mande `resultados_sec.txt` para ver por qué ExxonMobil no trae datos de la SEC.

**v1.5.62 (10/11) — Excepción del payout con la ganancia de los analistas** (aprobada por Guille: salto de 1,5 veces o más, o pérdida contable; resguardos de 5 analistas, 130 días y flujo libre; afuera bancos, REITs y utilities). Diferencia media con SSD: 6,7 puntos. **Guille tiene que correr `bajar_estimaciones.bat`** (todas las empresas; después, una vez por trimestre, lo recuerda el mail del día 1 de marzo, junio, septiembre y diciembre). Siguen para decidir: B (aumentos desde el último recorte) y C (FFO de los REIT).

**v1.5.61 (10/11) — Score de Seguridad del Dividendo, segunda calibración:** con datos completos da 7,4 puntos de diferencia media con SSD, 13 de 21 en la misma categoría, ninguna a dos. Guille decidió: tendencia con analistas «peras con peras», dividendo variable = no estadounidenses, tabla de empresas chicas por debajo de US$1.000 millones. **Guille debe volver a correr** `bajar_sec.bat` (suma Altria, bancos, etc., y pone la ganancia por acción de los ADR en la base de Yahoo) y después `calibrar_dividendo.bat`, y mandar `data/historico/estados.json`, `cambios.json`, `resultados_sec.txt` y `resultados_calibracion_dividendo.txt`. **Para decidir Guille (no aplicar sin su OK):** A) ya decidida en la v1.5.62 (excepción con salto de 1,5 veces); B) aumentos solo desde el último recorte; C) FFO de los 3 REIT (O, PLD, WELL) de los informes de cada empresa (Welltower: Stock Analysis da US$3,79 por acción contra un FFO normalizado de la empresa de US$6,47 a 6,53 para 2026). Después: mostrarlo en la app (cajitas + conclusión) y actualizar la FOTO del inicio.

**v1.5.58 (10/11) — Score de Seguridad del Dividendo:** método v0.2 programado (`scoring/dividendo.py`), todavía sin pantalla. Documento del método: https://claude.ai/artifact/URhosGmC1bjRMBFwr8q85e. **Guille debe correr en su PC, en este orden:** `bajar_historico.bat` → `bajar_sec.bat` → `calibrar_dividendo.bat`, y mandar `data/historico/` (dividendos, splits, precios, estados, cambios), `resultados_sec.txt`, `resultados_calibracion_dividendo.txt` y `data/calibracion_dividendo.json`. Con eso se hace la segunda comparación con SSD (con historial exacto, 12 años de la SEC y analistas) y Guille decide si hace falta un ajuste nuevo. Pendientes del método (v1.5.61: chicas y dividendo variable ya decididos): medida de capital para bancos. Después: mostrarlo en la app (cajitas + conclusión) y actualizar la FOTO del inicio.

**Decisión 05/11/2026 (Guille): el Fair Value queda como está (contra la mediana de la industria). Se revisa más adelante; no tocar el método hasta que él lo decida.**

**v1.5.56 (10/11):** Puntos de corte de Guille en los gráficos de Estados Financieros (reemplazan a las líneas «Ideal»: tema resuelto). Renovar el Excel cuando Damodaran publique su base nueva (enero) o cuando Guille lo actualice.

**v1.5.55 (09/11):** PER de GE Vernova descartado (ganancia de Prolec GE). **Fines de abril de 2027: SACAR "GEV" de `METRICAS_EXCLUIDAS`** con los resultados del 1.er trimestre de 2027. Cache del 09/11 cargado.

**v1.5.54 (09/11):** Respaldo del score con referencias de afuera (decisión de Guille): GuruFocus (medianas) para PER, P/FCF, P/B y P/S; Finviz para PEG; EV/EBITDA con la app (el de GuruFocus está roto: no se puede arreglar sin los datos empresa por empresa). Franja anti-disparates. 9 empresas cambian de categoría. **Fines de enero de 2027: SACAR el PER de Boeing de `METRICAS_EXCLUIDAS`** (config/sectors.py) cuando salgan los resultados del 4.º trimestre de 2026. **Noviembre de cada año:** Guille copia las tablas de GuruFocus (Sector Comparison › Overview) y Finviz (Groups › Sector e Industry › Valuation) → nuevos `data/referencias/<fuente>_<fecha>.json` + `python rescorar_cache.py`.

**v1.5.53 (09/11):** líneas «Ideal» apagadas hasta que Guille resuelva la referencia. **Múltiplos (respaldo del score, 51 empresas sin 5 años de historia):** Guille eligió probar Finviz (él consigue los valores por industria; actualizar al menos una vez por año). Simulación con Finviz POR SECTOR (captura del 09/11): 15 de las 51 cambian de categoría (10 empeoran, 5 mejoran; cambio medio 6,6 puntos); además KEP pasaría de 47 a 96 por el P/FCF de Utilities de Finviz (137,65, número sin sentido por ser suma). EV/EBITDA no está en Finviz. Falta: correrla con las industrias de Finviz cuando las mande; decidir qué hacer con EV/EBITDA. Script: scratchpad/finviz/sim.py (copiar al repo si se adopta).

**v1.5.52 (09/11):** globitos de solapas, «Ideal: más de», score centrado, logo ASML, ETF «Análisis Fundamental» solo con informe, ROIC arreglado, carga sin esperas a Yahoo. Guille está armando su plan de búsqueda de medianas (18 variables, 72 industrias); mandó Finviz (grupos por sector): no dice cómo calcula y son valores de hoy, no medianas de 5 años.

**v1.5.51 (08/11):** Sacadas las líneas con mediana de empresas de la app (Guille: muestras chicas). **Decisión pendiente de Guille** sobre las líneas que faltan: (a) calcular nuestros ROIC, cobertura y deuda/EBITDA como Damodaran para poder usar su dato; (b) payout de Damodaran (divfund, misma fórmula); (c) liquidez, margen de flujo libre, ROA y solvencia: sin fuente gratuita bien documentada. Avisarle además: el respaldo de sector del score (v1.2.12, 51 de 323 empresas) y el ROIC «promedio de su industria» de los informes (comparación despareja: Damodaran resta la caja).

**v1.5.50 (08/11):** Análisis de ETF (solapa + PDF) y primera tanda: los 11 fondos de sectores de State Street. (Líneas con mediana del sector propio: sacadas en la v1.5.51.) Piloto de la SEC analizado: sirve con reglas (signos, splits, ratio de ADR, más conceptos, empalmar solo si los años en común coinciden). **Siguen:** (1) informes de ETF por tandas (USA amplios: SPY, IVV, QQQ, DIA, IWM, RSP…; después internacionales, temáticos, minería, materias primas, cripto, apalancados/inversos, monedas); (2) `bajar_sec.py` para las 323; (3) «precio vs fundamentales» en los informes. **Guille debe:** subir `data/historico` (precios_mensuales, dividendos, splits, cambios) y correr `bajar_fichas.bat` (mes de cierre fiscal: su fichas.json del 08/11 todavía no lo trae).

**v1.5.49 (08/11):** Estados por familia y Ratios visual; línea de industria rigurosa; precio vs fundamentales en Valuación; piloto SEC; recordatorio mensual por mail. **Guille debe:** (1) subir a GitHub o mandar `data/historico` (precios_mensuales, dividendos, splits, cambios) de la corrida del 08/11 (417 de 419; PANW y TWLO sin datos: correr `bajar_historico.bat PANW TWLO`); (2) correr `bajar_fichas.bat` (mes de cierre fiscal); (3) correr `piloto_sec.bat` y mandar resultados_piloto_sec.txt y data/sec_piloto.json; (4) aprobar el informe modelo de ETF (XLV). Pendiente técnico: «precio vs fundamentales» en los informes (app y PDF) cuando estén los precios; cargar más planillas de Damodaran (deuda, dividendos) para sumar referencias de cobertura, deuda/EBITDA y payout.

**v1.5.48 (08/11):** Archivo histórico propio (`data/historico/`). **Guille debe correr** `bajar_historico.bat` (la primera vez trae toda la historia de precios, dividendos y splits; después, una vez por mes) y subir la carpeta `data/historico`. Próximos pasos del archivo: precios guardados en la ficha cuando Yahoo no responde, gráfico precio contra el negocio con ellos, prueba piloto de la SEC (10 empresas) para sumar años hacia atrás, medianas propias en paralelo (decisión de Guille).

**v1.5.47 (08/11):** Atrás · Inicio en todas las páginas, Ideas con estética de la tabla principal y orden por título, estados financieros visuales en subsolapas, barra de mercados centrada; paquetes y fichas de las 323 cargados. Pendiente de decisión: gráfico «precio contra fundamentales» (estilo App Economy Insights) en la ficha. Avisos de bajar_fichas: BB, IREN y MUX (Canadá/Australia) no están en la lista de ADR: revisar.

**v1.5.46 (08/11):** Guille aprobó: corte 4%, columnas de competidores (hechas), estados financieros visuales con 4 años (falta que elija dónde va; propuesta: arriba de la solapa «Estados Financieros», en 3 filas Crecimiento / Rentabilidad / Solidez, con las tablas plegadas debajo). Cita de la gerencia solo en informes nuevos. Cache del 08/11 cargado (323). **Guille debe correr** `bajar_paquetes_yahoo.bat` (sin nada más: baja las 323; hoy hay estados de 166 y sin ellos la tabla de competidores y los gráficos quedan con «—») y `bajar_fichas.bat`, y mandar `data/paquetes_yahoo.json` y `data/fichas.json`.

**v1.5.45 (08/11):** Listas de Aristócratas/Reyes/Aspirantes reemplazadas por las de Guille (08/11/2026). Falta: el nombre del sitio de cada lista para la línea de fuente; actualizarlas en febrero.

**v1.5.44 (08/11):** Ideas de Inversión con 5 listas, Div. Yield en ETFs, cita de la gerencia en los informes. **Esperan decisión de Guille:** (1) umbral de «Dividendos Altos» (hoy 4%); (2) columnas nuevas de la tabla de competidores (maqueta KO: Valoración, Calidad, crecimiento de ventas 3 años, margen operativo, ROIC, deuda neta/EBITDA, Div. Yield, colores relativos al grupo); (3) si se hace la sección visual de estados financieros (maqueta KO con 12 gráficos de barras). Listas de aristócratas/reyes/aspirantes: actualizar en febrero de cada año.

**v1.5.36 (06/11):** Guille debe correr `descargar_logos.bat ASML SPCX` y subir `static/logos/`. Tanda 3: espera la lista de 70 corregida (Excel `Tanda3_pendientes_70.xlsx`); BRFS, CAJ, CBRD y EBR propuestos NO CARGAR (ya no cotizan en EE.UU.), ERJ→EMBJ, E = Eni, VXX a ETFs.

**v1.5.43 (07/11):** generar_cache se colgó 4 h en la PC de Guille (Python 3.15). Ahora tiene tope por empresa y reanudación. Guille debe: (1) volver a correr `generar_cache.bat` y mandar `data/cache_datos.json` + `resultados_cache.txt`; (2) DESPUÉS `bajar_fichas.bat` (toma la lista del cache: con el cache viejo bajó 265, faltan las 58 de la tanda 3); (3) `descargar_logos.bat` (rehace ASML). Si vuelve a trabarse, instalar Python 3.13 (gratis) en vez del 3.15.

**v1.5.42 (07/11):** Renovados con los resultados del trimestre (estilo pedido por Guille: un poco más técnico, % pegado, año de los hechos): AMGN, ANET, SHOP, PFE, QCOM, MCD, NVO, COP y SONY; cada uno guardó su informe anterior (PDF en `static/informes`). **PBR queda para después del 10/11/2026** (ese día presenta el 3T26; hoy solo está el informe de producción). Pendiente sin apuro: cargar `APP_URL` (data/analisis_fundamental.py) cuando la app tenga dirección pública, para que los informes anteriores se puedan tocar desde el PDF. Siguiente: los 49 de la tanda 1 sin informe (de a tandas).

**v1.5.40 (07/11):** 30 ETFs sin CEDEAR cargados (acceso «Solo por mesa del broker», categoría nueva Monedas). Guille debe correr `bajar_etfs_yahoo.bat` con los 30 tickers para traer comisión, tamaño y dividendos; si algún ETF sí tiene CEDEAR, avisar el ratio.

**v1.5.39 (07/11):** Tanda 3 = 58 (sin ELPC ni AXIA); HWM 52:1; VXX en ETFs (categoría Volatilidad). Falta decidir las 18 acciones de Brasil/Europa-Asia que Balanz lista y correr `bajar_etfs_yahoo.bat VXX`.

**v1.5.38 (07/11):** SBS 1:2 confirmado con Rava. Rava lista VXX (5:1, activo). Revisar ratio o precio de BAK, PAC, SDA y URBN (dólar implícito fuera de ±6% de la mediana de Rava).

**v1.5.37 (06/11):** Tanda 3 cargada (60). Pendientes: ratio de HWM; categoría de VXX en ETFs; ratio de ELPC, SBS y AXIAY; confirmar el ratio de KEEL (cambió de nombre); decidir las 18 acciones de Brasil/Europa-Asia que Balanz lista (BBAS3 BPA11 HAPV3 LREN3 MGLU3 NATU3 PRIO3 RENT3 SBSP3 WEGE3 / ADS BAS BAYN BSN EOAN MBG NSAN SKHY); correr `generar_cache.bat`, `bajar_fichas.bat` y `descargar_logos.bat`.

**Con Opus (avisar antes de arrancar):**
- Renovar la valuación de los 139 informes y la pasada de redacción (esperar a los resultados de las empresas, ~10 al 17/11).
- Renovar 10 informes: AMGN, ANET, SHOP, PFE, QCOM, MCD, NVO, COP, SONY, PBR.
- Escribir los informes que faltan: hoy hay 166 informes y 215 empresas (**49 de la tanda 1 sin informe**: NUE MOS DD DOW IP IFF WFC BCS LYG F EBAY CCL LVS DECK JD AVY PINS SNAP ROKU BIDU AMX VOD JCI SNA DAL UAL AAL SWKS ALAB DOCU TWLO TEAM VRSN HPQ GLW GRMN SNDK OXY BKR HAL CCJ HSY KMB SYY BG BIIB MRNA CAH NTRA). Se suman las 50 de la tanda 2 (ya cargadas en la app) y las siguientes.
- Textos a mano para empresas de múltiplos muy altos: PLTR, CRWD, ARM, PANW, AMD, TSLA.

**Decisiones de Guille (no se implementa nada sin su OK; primero problema, teoría y pros/contras):**
- **Empresas jóvenes o con pérdidas (MRNA, NTRA; también SNDK y ALAB con historia corta):** opciones A (dejar como está), B (mínimo 2 métricas; si no, «Datos insuficientes»; recomendada), C (rango de 52 semanas técnico como información), D (DCF aparte, fuera del puntaje, proyecto separado). Teoría del libro: en empresas jóvenes o con pérdidas los múltiplos no sirven, se proyecta y se ajusta por supervivencia; en cíclicas se normalizan las ganancias de un ciclo completo.
- **Historia no comparable** (menos de 3 años, spin-offs, ganancias extraordinarias: GEV, HON, AMZN, CRWD, MRK, WDC, DIS).
- **DCF como segunda mirada** (A dejar como está, B informativo en la ficha, C alerta si se contradicen).
- **Score de calidad** (foso, Piotroski/Altman, deuda/EBITDA, calidad de ganancias).
- ~~Nota informativa para cíclicas (SNDK, MOS, OXY, aerolíneas)~~: **DESCARTADA por Guille** («la gente lo sabe»).

**Carga de CEDEARs:** tanda 2 (50 empresas) **CARGADA en la v1.5.26** con el Excel de Guille del 04/11 (amarillos como estaban, naranjas cambiados). A confirmar con él: UPST (puse Pagos y datos), FSLR (dejé Semiconductores), RGTI (celda naranja sin texto: dejé Hardware y servicios TI) y las industrias de Damodaran (propuesta). Falta en su PC: `generar_cache.bat`, `bajar_fichas.bat`, `descargar_logos.bat`. Después vienen las 77 de «tanda 3 en adelante». Símbolos raros de la lista de BYMA (TRVV, NYSE, UN) y acciones que cotizan solo en Brasil (11): **no son tarea de Guille**; quedan excluidas con motivo en `control_cobertura.py`; se revisan solas cuando BYMA publique una lista nueva. Industrias de Damodaran de la tanda 1: **HECHO** (v1.5.24, propuesta a revisar).

**Noticias (v1.5.24 hecho):** pendiente revisar términos de uso de cada medio (título + link), ver si el servidor de la app llega a Investing.com (si no, quedan los otros medios) y, si se quiere, buscar la dirección nueva del RSS de Yahoo Finance y de El Cronista (dan 404).

**En la PC de Guille:** `bajar_tecnicos.bat` y `bajar_paquetes_yahoo.bat` (datos del 29/10, sin las empresas nuevas); cada tanda nueva repite `generar_cache.bat`, `bajar_fichas.bat` y `descargar_logos.bat`.

**Datos que se desactualizan:** HWM (ratio 265 → 199,2), HON/FDX (spin-offs), DEO; mantener al día `data/macro_actual.txt` (la «foto macro»: tasas, inflación, petróleo, mercado; Opus la usa al escribir cada informe).

---

## 🔴 URGENTE (pedido de Guille, 01/11/2026: "es super importante", no perder)
1. **Tareas de él en la PC:** correr `generar_cache.bat` (caché fresco: sin eso la valuación de los 139 informes queda con el precio del 22/10), `bajar_fichas.bat` y `bajar_etfs_yahoo.bat DBB DBA WEAT JMOM ILIT REMX` (los 6 ETFs nuevos). Subir `data/cache_datos.json` y `data/historial` a GitHub.
2. **Arreglar la valuación de los 139 informes (con Opus, AVISAR ANTES):** hoy "Escrito el 29/10 - 01/11" pero la foto de valuación es del 22/10 (discordancia). Con el caché nuevo: tomar la foto el mismo día que la fecha del informe y revisar que las frases (barata/cara, margen de seguridad) sigan teniendo sentido. Va junto con el barrido de redacción (palabras repetidas, normas de escritura), las 21 empresas nuevas y las 10 renovaciones.
3. ~~Rehacer "Evalúa Gratis tu Portfolio"~~ **HECHO** (v1.4.5 a v1.5.1, con la estructura y el tono del modelo escrito por Guille).

**Cómo lo dejó anotado Guille (02/11/2026):**
* Correr `generar_cache.bat`, `bajar_fichas.bat` y `bajar_etfs_yahoo.bat DBB DBA WEAT JMOM ILIT REMX`.
* Renovar la valuación de los 139 informes para que el precio coincida con la fecha escrita.
* La pasada de redacción, las 21 empresas nuevas y las 10 renovaciones (AMGN, ANET, SHOP, PFE, QCOM, MCD, NVO, COP, SONY, PBR).
* Estos tres pendientes se hacen con Opus; avisarle antes de arrancar.

## A. Antes de mirar nada (tareas de él en su PC)
- [ ] Actualización trimestral: `generar_cache.bat` (valida antes de reemplazar; si sale rota guarda `data/cache_rechazado.json`) y `bajar_fichas.bat` (sin `data/fichas.json` la ficha depende de Yahoo en vivo).
- [ ] Confirmar que en `data/historial` están `cache_2026-10-22.json` (re-puntuado) y el de hoy.
- [ ] Correr el Modo lote del DCF para las empresas que faltan y luego `python foso_desde_lote.py Lote_DCF_*.xlsx` (hoy `data/foso.json` cubre 53 de 166).
- [ ] **Pendientes de la PC (v1.2.69):** `bajar_etfs_yahoo.bat` (datos, Composición y descripción traducida de los ETFs → `data/etfs_yahoo.json`); `bajar_paquetes_yahoo.bat` de nuevo (agrega intereses y deuda de corto/largo plazo a los estados → `data/paquetes_yahoo.json`); Modo lote del DCF con los 4 bloques de la lista de foso; `probar_fuentes_noticias.bat`. El Análisis Fundamental ya no usa API: el texto lo redacta Claude en la sesión y se carga con `generar_analisis_fundamental.py --agregar` (tras tu OK al ejemplo de TJX).
- [ ] Pedirle una lista NUEVA de GuruFocus (la del 23/10 es `gurufocus_23-10-2026.txt`, 163 empresas).

## B. Balance principal (fijar la regla ANTES de ver números)
1. **Medir los 3 escenarios** del 15 % técnico con `data/escenarios_tecnico_22-10-2026.csv` (A = como estaba, B = técnico dado vuelta, C = sin técnico, vigente desde la v1.2.51). Por escenario: Spearman entre puntaje y retorno desde el 22/10, retorno del quintil más barato menos el del más caro, aciertos de categoría. Decirle que ~40 días no es concluyente.
2. **Concordancia con GuruFocus** (Spearman entre puntaje y −precio/GF Value; referencias: v1.2.42 0,683; v1.2.49 0,800; v1.2.50 0,769; sin técnico 0,744) y contra retornos reales. No ajustar umbrales mirando el resultado. Recordar que el GF Value usa P/S, P/E, P/FCF y P/B históricos, así que el parecido es en parte por construcción.
3. **"Historia no comparable"**: marcar empresas con menos de 3 años de historia, spin-offs o ganancias extraordinarias (GEV, HON, AMZN, CRWD, MRK, WDC, DIS). Decisión suya.
4. **Validar el PEG con historia creíble** en Semiconductores y Hardware (v1.2.44, 25 %).

## C. Ideas abiertas (cada una necesita su OK)
- [ ] **Score de calidad** (más adelante, por decisión suya): foso (ROIC vs costo de capital, Damodaran), Piotroski/Altman, deuda/EBITDA, calidad de ganancias. Acá vuelve el aviso "Posible trampa de valor" para score de calidad bajo + infravalorada. Texto: "Una empresa con score alto no garantiza que esté infravalorada. El precio bajo puede reflejar deterioro real del negocio no capturado por los múltiplos históricos. Investigá los fundamentales antes de tomar una decisión."
- [ ] **Idea 9**: comparar el múltiplo contra su historia Y la "variable compañera" (P/E vs crecimiento, EV/Ventas vs margen, P/B vs ROE).
- [ ] **Damodaran** como respaldo de la mediana del sector (hoy 5 empresas usan sector: NTES, GEV, INTC, SAP, SNOW).
- [ ] **DCF como segunda mirada**: A = dejar como está (recomendada), B = mostrarlo informativo en la ficha, C = alerta cuando se contradicen. Contradicciones graves del 24/10: MRK, PFE, LLY. Faltan AVGO, SNOW, AIG, COIN, VST, TLN, ECL, UNP, ADP, MS.
- [ ] **Momentum / tendencia del precio**: recomendación mía previa: dejarlo fuera del puntaje; si lo quiere, mostrarlo aparte como "Tendencia del precio", informativo.
- [ ] **Revisión de otra IA sobre la planilla original** (25/10): estimaciones a 12 meses y su revisión, comparar contra competidores del subsector, ajuste por tasas, DCF inverso, retorno esperado con escenarios. Ver la sección "Lo que queda" abajo.
- [ ] Fair Value: contradicciones categoría vs Fair Value (quedan DIS y MU); decidió "dejar así por ahora".
- [ ] Desglose del Fair Value por método y línea de precios: ofrecerle ocultarlos si quiere.
- [ ] Topes (1/3x–3x del Fair Value, 30 % de rendimiento al accionista, factor 0,5 a los 3 años): él los aprobó; revisarlos con datos nuevos.

## D. Cosas sin probar contra servicios reales (el entorno de desarrollo no llega a Yahoo, Rava ni Stock Analysis)
- [ ] **v1.2.52**: que abra una empresa en la app real y confirmar que aparecen: descripción en vivo (si falta en `fichas.json`), gráfico de 10 años y cambios de precio día/semana/mes/año. Si Yahoo bloquea a Streamlit Cloud, correr `bajar_fichas.bat` y pensar en guardar el historial en un archivo.
- [ ] **Fuente condensada** (Roboto Condensed) y estilo de la tabla: que la mire en su PC y su teléfono.
- [ ] Precios en vivo (`probar_cedears.bat` → `resultados_cedears.txt`; si Rava trae 0 precios, ajustar el lector).
- [ ] Ratios de `data/cedears.csv` (Rankia 20/10; SCHW 13:1 sin confirmar; no inventar ratios).
- [ ] Noticias de CNBC traducidas (MyMemory): ¿aparecen y sirve la traducción?
- [ ] Comentarios por FormSubmit a finanzas.medicos@gmail.com: ¿llegan?
- [ ] Lista de ADR de `config/mercados.py` (curada a mano, sin confirmar).
- [ ] Botón de Excel: revisar términos de uso de terceros antes de promoverlo.
- [ ] Streamlit Cloud: confirmar que la app funciona con los repos privados (hay que dar acceso a Streamlit en GitHub) y revisar `SCREENER-CEDEAR-ULTIMO` (público; ¿expone el método?).

## E. Comunidad, legales y marca (cosas de él)
- [ ] Link de WhatsApp ya está cargado; falta el QR si lo quiere.
- [ ] Textos legales: el original decía "avalado por la CNV" (se escribió "registrado"); "Asesoría Financiera Integral" suena a servicio regulado: consultar con compliance/abogado. Se sacó ese párrafo de Quiénes somos en la v1.2.52.
- [ ] Aviso legal v1.2.52 (modelado en Club de Bonos): que lo revise un abogado/compliance.
- [ ] Ofrecerle poner la matrícula en el pie.
- [ ] Registro con mail, portfolio simulado y dominio .com.ar: costos ya informados (Streamlit Cloud $0 sin dominio propio; Render Free $0 / Starter US$7 / Standard US$25 por mes; .com.ar ≈ $8.500 ARS/año dato 2024, verificar en nic.ar). Portfolio liviano sin login antes que login + base de datos; si guarda datos personales, consultar con un abogado.

## F. Lo que queda de la revisión de la otra IA (25/10)
Ya resuelto en la app: datos faltantes no penalizan, topes y descarte de absurdos, medianas desde fuente, puente de deuda, métricas por sector, técnica fuera del puntaje, validación del cache. Pendiente y sin decidir: estimaciones a futuro (necesita fuente confiable), comparar contra competidores, ajuste por tasas, DCF inverso, backtest (necesita datos históricos de cada fecha: el historial mensual del cache es el comienzo).

## G. Cómo se mide ("cruda verdad")
- Con ~40 días es ruido; el balance serio necesita varios trimestres de historial.
- Cualquier ajuste que mejore la concordancia con GuruFocus no prueba que esté bien.
- No implementar nada sin su OK.
