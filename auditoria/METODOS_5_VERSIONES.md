# Score de Seguridad del Dividendo: métodos exactos de las 5 versiones

24/11/2026 · Guille · copia del documento https://claude.ai/artifact/52y6z7kwiBEkmf68psJ9cx

Este documento describe, regla por regla, cómo se calcula cada versión del score tal como está programada al 24/11/2026 (TodoCedears v1.5.91). Es el texto base para la auditoría: cada número y cada corte sale del código, no de memoria.

## 1. Numeración y alcance

Hay cinco versiones. Las tres primeras están programadas en la app; la 3.1 y la 3.2 existen solo en la simulación, fuera de la app. Ninguna se muestra en pantalla.

| Versión | Qué es | Dónde está en el código |
| --- | --- | --- |
| Versión 1 | El primer método (Weiss + Simply Safe Dividends), aprobado por Guille el 10/11/2026, con los 3 ajustes de la primera calibración y las decisiones del 10 y 11/11 | `scoring/dividendo.py`, función `calcular` (en el código se llama «v0.2») |
| Versión 2 | El Word de Guille «Score de Seguridad de Dividendos (Escala 0 - 100)» del 16/11/2026, con las definiciones que Guille dio ese día para los huecos del documento | `scoring/dividendo_v1.py`, `calcular(e, version=2)` |
| Versión 3 | La versión 2 con las decisiones posteriores de Guille (17/11 al 23/11) | `scoring/dividendo_v1.py`, `calcular(e)` (antes llamada «v1») |
| Versión 3.1 | Versión 3 + opción 1: bloque de ciclo y compresión arriba de 60 | `auditoria/calcular_5_versiones.py` (función `capa`) |
| Versión 3.2 | Versión 3 + opción 2: bloque de ciclo y techo de 80 si una variable principal no está en zona segura | `auditoria/calcular_5_versiones.py` (función `capa`) |

Los arreglos de lectura de datos (sección 2) no son una versión: se aplican igual a las cinco, así la comparación mide solo el método. Las cinco se calcularon con los mismos datos: los de los .bat de Guille del 24/11/2026 (Yahoo Finance y SEC) y la lista de SSD del 21/11/2026.

Categorías, iguales en todas las versiones y en SSD: 0 a 20 muy inseguro, 21 a 40 inseguro, 41 a 60 al límite, 61 a 80 seguro, 81 a 100 muy seguro (el borde va con la categoría de abajo: 80 es «seguro»).

En este documento «12 meses» es el dato de los últimos 12 meses (TTM) y «último año» el último año fiscal completo. «Zona segura / gris / crítica» son las tres franjas de cada variable.

## 2. Reglas de datos comunes a todas las versiones

Estas reglas deciden qué número entra a cada fórmula. Son iguales en las cinco versiones.

### 2.1 Fuentes y períodos

1. Estados contables: los de Yahoo Finance que bajan los .bat (`bajar_paquetes_yahoo.bat`), más los años viejos de la SEC (`bajar_sec.bat`), unidos en el archivo histórico (`data/historico/estados.json`, función `historico.estados_completos`, hasta 13 años). La SEC solo suma años más viejos que el primero de Yahoo y solo si en el año en común el resultado neto o los ingresos coinciden dentro de 5 %. Desde la v1.5.90, si la etiqueta de moneda de Yahoo difiere de la de la SEC pero las cifras coinciden (Yahoo rotula BRL lo que está en dólares en Vale, Embraer y Petrobras), los años se suman con la etiqueta de lo guardado.
2. Columna de 12 meses: suma de los últimos 4 trimestres, completada celda por celda con el dato de 12 meses de Yahoo (`_con_ttm`).
3. Regla de datos: se usa el dato de 12 meses; si falta, el del último año fiscal; nada más viejo.
4. Celdas que Yahoo deja vacías en el gasto por intereses o los intereses pagados: se completan con la SEC del mismo año (misma moneda o cifras coincidentes) y, si tampoco están, con `data/intereses_manuales.json` (cargado a mano con fuente: Apple, Garmin, PACCAR, Nike, NetEase, GE Vernova, Arcos Dorados, Salesforce, Eli Lilly; NextEra con intereses pagados porque su gasto mezcla coberturas de tasa).
5. Precio, dividendo anual por acción (`annual_dividend`), rendimiento, mediana de rendimiento de 5 años, capitalización, beta y PER: del cache de la app (`data/cache_datos.json`, `generar_cache.bat`).
6. Estimaciones de analistas (ganancia por acción del año fiscal en curso y del próximo, cantidad de analistas, fecha): `data/estimaciones_analistas.json` (`bajar_estimaciones.bat`, trimestral). Vigencia: 130 días.
7. Datos cargados a mano con fuente (los renueva la tarea trimestral): AFFO de los REIT (`data/ffo_reit.json`), CET1 y su requisito (`data/cet1_bancos.json`), solvencia de aseguradoras, FFO ÷ Deuda de utilities, financieras propias, ventas comparables. Cuáles usa cada versión está en sus secciones.
8. Mes de cierre del ejercicio: de `data/fichas.json`. Hoy falta en las 323 empresas (Yahoo dejó de darlo; la v1.5.90 lo saca del último balance anual cuando Guille corra `bajar_fichas.bat`). Mientras falte, se usa diciembre para todas.

### 2.2 Monedas y ADR

1. Estados en otra moneda o con acciones distintas a las del ADR: las cifras por acción se pasan a dólares por ADR con el tipo de cambio del cache y la relación acciones/ADR (resultado neto ÷ ganancia por acción contra capitalización ÷ precio). Si Yahoo marca otra moneda pero las cifras ya están en dólares (se detecta porque precio ÷ PER coincide con la ganancia sin convertir), no se convierten.
2. La estimación de analistas se lleva a dólares por ADR eligiendo la base (moneda y acción o ADR) más cercana a la ganancia contable.
3. Versión 1: con estados en otra moneda, el payout sobre ganancias se mide con montos de la misma moneda (dividendos pagados ÷ resultado neto).
4. Deuda del último trimestre que no cierra con el pasivo (menos de la mitad de la del año, con el pasivo casi igual): se descarta y se usa la del último año (KEPCO).

### 2.3 Historial de dividendos (`analizar_dividendos` y `data/moneda_dividendo.historial`)

1. **Moneda en que se mide.** El recorte se busca en la moneda en que la empresa fija su dividendo. Si es dólares (EE.UU., y las de afuera que pagan en dólares: Shell, BP, BHP, Rio Tinto, AstraZeneca, Diageo, Alibaba, XP, PagBank, NetEase, JD), la serie del ADR. Si es otra moneda: la serie de su bolsa de origen (`dividendos_locales.json`, 50 de 57 válidas); si no hay, los pagos del ADR pasados a su moneda con `monedas.json` o los fondos de monedas (tolerancia 5 %); si tampoco, queda «variable» (no se puede medir: sin castigo por recorte ni premio). Excepciones verificadas en `EXCEPCIONES` (Novartis, TotalEnergies, Gold Fields, Infosys, Vale en su moneda; XP, PagBank, Alibaba, NetEase, JD, Diageo en dólares).
2. **Dividendo regular de cada año calendario** = mediana de sus pagos × frecuencia habitual de ese año (la más repetida entre el año anterior, ese y el siguiente; 1, 2, 4 o 12). La mediana deja afuera un extraordinario suelto. Con 2 pagos desparejos (a cuenta y final) y uno de más, se descarta el que menos se parece al del año anterior en la misma época.
3. **Recorte** en el año *a*: el dividendo regular baja más que la tolerancia (1 %; 5 % con serie convertida) y más de 0,001 por pago; o no paga en todo el año (suspensión); o paga menos veces que lo habitual y cobra menos del 75 % del año anterior (salvo que el pago que falta se haya corrido a menos de 45 días del año). No es recorte: un cambio de frecuencia si el año siguiente vuelve al nivel anterior (Accenture 2019); un pago que Yahoo perdió si antes y después el pago no bajó (dato faltante); y, desde la v1.5.89, en las que pagan 2 veces, una baja que solo aparece en el año calendario (si el año y el anterior tienen sus 2 pagos, se confirma corriendo los pagos 182 días; si no baja en el año corrido, no es recorte: Toyota 2016, Novo Nordisk 2017, ASML 2020).
4. **Consolidaciones comparables**: cuando Yahoo ajusta como split una consolidación que acompaña una escisión (Unilever 2025, National Grid 2017), se deshace el ajuste. La ampliación de capital de National Grid de 2024 sí cuenta como recorte (decisión de Guille del 21/11).
5. **Año en curso**: si la mediana de los últimos pagos × frecuencia baja respecto del último año completo, o dejó de pagar (más de 365 ÷ frecuencia × 1,6 + 15 días sin pago, salvo que el cache diga que paga), hay «recorte en curso».
6. Derivados: años sin recortar, años pagando, aumentos en los últimos 12 años, racha de subas (años seguidos con dividendo regular mayor en más de 0,1 %), años seguidos sin subir al final, recortes por año, y qué hizo en 2008-09 (contra 2007) y en 2020-21 (contra 2019): sin recorte, recortó o no pagaba.
7. Antes de que empiece la serie en su moneda, los años se cuentan con el beneficio de la duda (si en lo medido no hubo recorte, los años sin recortar se extienden a los años pagando del ADR).

## 3. Versión 1 (el primer método)

Método completo y su historia: documento «Score de Seguridad del Dividendo — Metodología» (https://claude.ai/artifact/URhosGmC1bjRMBFwr8q85e). Acá va lo que el código hace hoy.

### 3.1 Estructura

Cinco pilares con máximo fijo: 1 cobertura del dividendo 35 · 2 solidez del balance 25 · 3 historial del dividendo 20 · 4 estabilidad del negocio 15 · 5 tendencia 5. Cada pilar = puntos de sus variables con dato ÷ máximo de esas variables × máximo del pilar. Puntaje = suma de pilares con dato ÷ suma de sus máximos × 100. Sin pilar 1 o sin pilar 3, no hay puntaje. Valores redondeados a 2 decimales. En las escalas «menos es mejor» el borde va con la franja de más puntos; en las de calificación, cada franja empieza en su número (incluido).

### 3.2 Pilar 1: cobertura del dividendo (35)

**Empresas generales**:

| Variable | Cómo se mide | Escala (hasta el valor, incluido → puntos) |
| --- | --- | --- |
| Payout de flujo libre (20) | El menor entre: dividendos pagados de los últimos 3 años fiscales ÷ flujo libre de esos años (con 2 o más años), y dividendos pagados ÷ flujo libre de 12 meses. Flujo libre ≤ 0 = 9999 | 50 → 20 · 60 → 17 · 70 → 14 · 80 → 10 · 90 → 6 · 100 → 3 · más → 0 |
| Payout de ganancias (15) | Dividendo anual por acción ÷ la mayor ganancia por acción positiva entre 12 meses y último año. Con estados en otra moneda: dividendos pagados ÷ resultado neto (el menor de 12 meses y último año) | 50 → 15 · 60 → 12 · 75 → 9 · 90 → 5 · 100 → 2 · más → 0. Con pérdida: 0 |

**Excepción con la ganancia de los analistas** (solo empresas generales): si la estimación del año en curso está vigente, tiene 5 o más analistas y el payout de flujo libre es 100 % o menos, la ganancia usada pasa de a poco a la estimada según el salto (estimada ÷ contable): peso 0 hasta 1,25 veces, 1 desde 1,75 veces, lineal en el medio (1,5 = 0,5). Payout = payout contable ÷ (1 + peso × (salto − 1)). Con pérdida contable y estimación positiva en la moneda del dividendo: dividendo ÷ estimada. El salto se homologa probando las bases posibles de moneda y acción y quedando la de salto más chico.

**Bancos y seguros**: solo payout de ganancias, con la escala general llevada a 35 (puntos × 35 ÷ 15); sin excepción de analistas.

**Utilities** (payout de ganancias) y **REITs** (payout de FFO), todo el pilar en una variable: hasta 75 → 35 · 85 → 27 · 95 → 18 · 100 → 8 · más → 0. FFO del REIT: el informado por la empresa (`ffo_reit.json`, normalizado, vigente 200 días, el mejor de 12 meses y último año); si falta o venció, precio ÷ P/FFO de Stock Analysis; sin FFO, el REIT va con la escala general.

### 3.3 Pilar 2: solidez del balance (25; no se usa en bancos y seguros)

| Variable | Cómo se mide | Escala |
| --- | --- | --- |
| Cobertura de intereses (12) | Resultado operativo ÷ intereses (EBITDA ÷ intereses en utilities y REITs), dato de 12 meses o último año de cada uno. Se pasa a calificación con la tabla de Damodaran (empresas grandes; con capitalización menor a US$1.000 millones, la de chicas o riesgosas). Sin intereses y sin deuda: 12 | AAA o AA: 12 · A+ o A: 10 · A−: 8 · BBB: 6 · BB+ o BB: 3 · resto: 0 |
| Deuda neta ÷ EBITDA (9) | Cociente de Yahoo, o deuda neta ÷ EBITDA. Caja neta: 9 | Generales: 1 → 9 · 2 → 7 · 3 → 5 · 4 → 2 · más → 0. Utilities y REITs: 4,5 → 9 · 5,5 → 7 · 6,5 → 5 · 7,5 → 2 |
| Deuda neta ÷ (deuda neta + patrimonio) (4) | Con deuda neta negativa cuenta 0. Patrimonio + deuda ≤ 0: 100 % | 50 → 4 · 75 → 2 · más → 0. «Posible caníbal»: con patrimonio ≤ 0 o este cociente ≥ 90 % y cobertura de 10 puntos o más, la variable no se usa |

Tabla de cobertura → calificación (desde, incluido). Grandes: 8,5 AAA · 6,5 AA · 5,5 A+ · 4,25 A · 3 A− · 2,5 BBB · 2,25 BB+ · 2 BB · 1,75 B+ · 1,5 B · 1,25 B− · 0,8 CCC · 0,65 CC · 0,2 C · menos D. Chicas: 12,5 AAA · 9,5 AA · 7,5 A+ · 6 A · 4,5 A− · 4 BBB · 3,5 BB+ · 3 BB · 2,5 B+ · 2 B · 1,5 B− · 1,25 CCC · 0,8 CC · 0,5 C.

### 3.4 Pilar 3: historial del dividendo (20)

| Variable | Escala |
| --- | --- |
| Años sin recortar (10). Si no se puede medir en su moneda («variable»), años pagando | 25 o más → 10 · 20 → 8 · 15 → 6 · 10 → 4 · 5 → 2 · menos → 0 |
| Aumentos en los últimos 12 años (5) | 10 o más → 5 · 7 → 4 · 5 → 3 · 3 → 1 · menos → 0 |
| Crisis 2008-09 y 2020-21 (5) | Cada crisis: sin recorte 2,5 · no pagaba 1 · recortó 0 |

### 3.5 Pilar 4: estabilidad del negocio (15)

| Variable | Escala |
| --- | --- |
| Años con suba de la ganancia por acción (6), sobre hasta 12 comparaciones de años fiscales (3 o más) | 75 % o más → 6 · 7/12 → 4 · 5/12 → 2 · menos → 0 |
| Supersector Morningstar (5) | Defensivo (consumo básico, utilities, salud) 5 · Sensible (tecnología, software, hardware, comunicación, telecomunicaciones, industrial, energía, semiconductores) 3 · Cíclico (materiales, REITs, bancos y seguros, pagos y datos, consumo discrecional) 0 |
| Años con flujo libre negativo en los últimos 12 (4; no en utilities ni bancos) | 0 → 4 · 1 → 2 · más → 0 |

### 3.6 Pilar 5: tendencia (5)

Crecimiento de la ganancia: estimación del próximo año ÷ la del año en curso − 1 (si está vigente); si no, ganancia por acción actual contra la de 3 años antes. 0 % o más → 5 · desde −10 % → 3 · menos → 0.

### 3.7 Topes y alarma (después del puntaje)

1. El dividendo supera lo que gana (ganancia ≤ 0 o dividendo por acción mayor que la ganancia; con otra moneda, dividendos pagados mayores al resultado neto de 12 meses) **y** los dividendos pagados de 12 meses superan el flujo libre de 12 meses → máximo 40. En bancos alcanza con lo primero.
2. Cobertura de intereses menor a 1,5 → máximo 40.
3. Ganancia ≤ 0 y flujo libre de los últimos 3 años sumado ≤ 0 → máximo 20.
4. Alarma de rendimiento: rendimiento actual ≥ 2 veces su mediana de 5 años → −10.

Puntaje final: redondeado, entre 0 y 100.

## 4. Versión 2 (el Word del 16/11 con lo definido ese día)

Fuente: el Word de Guille del 16/11/2026 (el archivo que subió el 24/11 es idéntico byte por byte; copia en `auditoria/Word_Guille_16-11-2026.docx`). Donde el Word no decía algo, valen las definiciones que Guille dio el 16/11 y las de implementación de la v1.5.71, marcadas.

### 4.1 Reglas generales

1. **Zonas con puntaje fijo**: cada variable da los puntos de su zona segura, gris o crítica (no hay puntos intermedios).
2. **Bordes** (Guille, 16/11: «cada zona va hasta el punto inmediato anterior de la siguiente»): la gris cubre todo lo que no es seguro ni crítico. En el código, el valor exacto del corte seguro va a la gris (cobertura de 5,0 = gris) y el del corte crítico también, salvo en el payout futuro general y en el payout de ganancias de bancos, donde el valor exacto del corte crítico ya es crítico (80 % y 75 %). Donde el Word deja un hueco entre la gris y la crítica, cae en gris.
3. **Base** = puntos obtenidos ÷ máximo de las variables con dato × 100. Si el máximo con dato es menor a 40, no hay puntaje. Si una empresa que no es banco no tiene cobertura de intereses, no hay puntaje («tiene que estar sí o sí», 16/11; dato del mismo período, 17/11).
4. Sin dividendo, no hay puntaje.
5. Puntaje final = base + ajustes, después los topes, redondeado, entre 0 y 100.

### 4.2 Variables de las empresas generales

| Variable (máx.) | Cómo se mide | Segura | Gris | Crítica |
| --- | --- | --- | --- | --- |
| Cobertura de intereses (25) | Resultado operativo ÷ gasto por intereses, los dos del mismo período: 12 meses o, si falta, el último año. Intereses: gasto (Yahoo, SEC) → intereses pagados → carga manual. Sin resultado operativo: resultado antes de impuestos + intereses. Sin deuda, o con deuda que es solo alquileres y sin intereses: 99 | más de 5,0 → 25 | 2,0 a 5,0 → 10 | menos de 2,0 → 0 |
| Payout de flujo libre 12 meses (20) | Dividendos pagados ÷ flujo de caja libre (12 meses o último año). Flujo libre ≤ 0 = 999 % | menos de 60 % → 20 | 60 a 85 % → 10 | más de 85 % → 0 |
| Payout futuro (15), plan B | Dividendo anual por acción ÷ ganancia por acción de los próximos 12 meses = mezcla de la estimación del año fiscal en curso y la del próximo, ponderada por los meses que faltan para el cierre (hoy con cierre en diciembre para todas). El plan A (flujo libre futuro) no se usa: no hay consenso gratis | menos de 55 % → 15 | 55 a menos de 80 % → 7 | 80 % o más → 0 |
| Crecimiento de ventas (10) | Anual compuesto entre el último año fiscal y 3 años antes | más de 3 % → 10 | 0 a 3 % → 5 | menos de 0 % → 0 |
| Deuda neta ÷ EBITDA (15) | 12 meses o último año. Caja neta = segura. EBITDA ≤ 0 = 99 | menos de 2,5 → 15 | 2,5 a 4,5 → 7 | más de 4,5 → 0 |
| Ganancias retenidas ajustadas ÷ activos (10) | (Ganancias retenidas + valor absoluto de las acciones en tesorería) ÷ activo total (definición del 16/11) | más de 35 % → 10 | 15 a 35 % → 5 | menos de 15 % → 0 |
| Prueba ácida (5) | (Activo corriente − inventarios) ÷ pasivo corriente | más de 1,1 → 5 | 0,7 a 1,1 → 2 | menos de 0,7 → 0 |

Prueba ácida por sector: asset-light (Hardware y servicios TI, Semiconductores, Software y nube, Salud, Pagos y datos) segura más de 1,5, gris 1,0 a 1,5, crítica menos de 1,0; Consumo Básico segura más de 0,6, gris 0,4 a 0,6, crítica menos de 0,4.

### 4.3 Sectores especiales

| Sector | Qué cambia |
| --- | --- |
| REITs | Cobertura de cargos fijos ≈ EBITDA ÷ intereses (definición del 16/11): más de 3,0 → 25, 1,5 a 3,0 → 10, menos de 1,5 → 0. En lugar del payout de flujo libre, payout de AFFO (20) con el AFFO que publica la empresa (`ffo_reit.json`; sin AFFO publicado la variable no cuenta): menos de 80 % → 20, 80 a 90 % → 10, más de 90 % → 0. Deuda neta ÷ EBITDA: menos de 5,5 → 15, 5,5 a 6,5 → 7, más de 6,5 → 0. Sin payout futuro y sin ganancias retenidas |
| Utilities | En lugar del payout de flujo libre, payout de ganancias (20): dividendo ÷ ganancia por acción de 12 meses en dólares por ADR; menos de 70 % → 20, 70 a 80 % → 10, más de 80 % → 0. Deuda neta ÷ EBITDA (15): menos de 5,0 → 15, 5,0 a 6,0 → 7, más de 6,0 → 0. FFO ÷ Deuda (10, **propuesta de Claude en la v1.5.71**: el Word no da su peso; el total queda sobre 110 y se lleva a 100): el que publica la empresa o, si no, flujo operativo ÷ deuda total; más de 15 % → 10, 10 a 15 % → 5, menos de 10 % → 0. Prueba ácida: menos de 0,4 → 0, si no 5. Payout futuro con el corte general |
| Bancos y seguros | En lugar de la cobertura, CET1 (25): más de 11 % → 25, desde el requisito regulatorio de ese banco (`cet1_bancos.json`; si no está, 9,5 %) hasta 11 % → 10, debajo del requisito → 0. Payout de ganancias (20): menos de 50 % → 20, 50 a menos de 75 % → 10, 75 % o más → 0. Sin deuda neta ÷ EBITDA, sin prueba ácida. Con ganancias retenidas ÷ activos. Payout futuro con el corte general. Las aseguradoras sin CET1 quedan sin esa variable |

BDCs y MLPs: no hay en la app (a Guille no le importan, 16/11).

### 4.4 Ajustes (en orden)

1. **Recorte** del dividendo regular en su moneda (sección 2.3), contado desde el primer año de cada tramo seguido de recortes y medido contra el último año completo (recorte en curso = 0 años): menos de 5 años → −25; de 5 a 10 años → −10; más de 10 → 0. Si el historial no se puede medir en su moneda («variable»), ni castigo ni premio.
2. **Dividendo errático o variable**: 3 o más recortes en los últimos 10 años (**propuesta de Claude**, sin OK formal), o política de dividendo variable declarada (Gold Fields, con fuente). Consecuencia: techo 80 y sin premio. El recorte y el techo se aplican los dos.
3. **Congelamiento crónico** (Word): 3 o más años seguidos sin subir al final de la serie (vigente) → −5 y sin premio.
4. **Premio** por racha de aumentos del dividendo regular en su moneda: 25 años o más → +10 (aristócrata); 10 a 24 → +5 (aspirante). Se anula si es errático o variable, o si la cobertura (o el CET1) o el payout principal (flujo libre, AFFO o ganancias) están en zona crítica.
5. **Trampa de rendimiento** (definición del 16/11, en lugar del T-DTS del Word): rendimiento mayor a 8 % y payout de flujo libre mayor a 100 % → −30 y techo 40.

### 4.5 Topes (después de los ajustes)

1. **Freno por pérdida**: resultado neto negativo en el último año fiscal completo → máximo 20, sin excepciones (16/11), también en REITs.
2. **Colapso de solvencia**: cobertura de intereses (o de cargos fijos) menor a 1,5 → máximo 20 (no en bancos).
3. Trampa de rendimiento → máximo 40.
4. Errático o variable → máximo 80.

## 5. Versión 3 (versión 2 + las decisiones posteriores de Guille)

Todo lo de la sección 4 vale, salvo estos cambios. Cada uno está en el código con su fecha y la frase de Guille.

| # | Fecha y versión | Qué cambia respecto de la versión 2 | Frase de Guille |
| --- | --- | --- | --- |
| 1 | 17/11, v1.5.74 | Ganancias retenidas ajustadas = ganancias retenidas + lo mayor entre el valor absoluto de las acciones en tesorería y las recompras de los últimos 10 años fiscales (recompras viejas de la SEC) | «me gusta la solución» |
| 2 | 17/11, v1.5.74 | Aseguradoras con índice de solvencia (25) en lugar del CET1: más de 150 % → 25; desde el requisito (100 %) hasta 150 % → 10; debajo del requisito → 0 (`solvencia_aseguradoras.json`). Cuenta para anular el premio | «hagamos con índice de solvencia»; cortes: «OK, de acuerdo» |
| 3 | 17/11, v1.5.75 | Welltower, que no publica AFFO, usa su FFO normalizado de 12 meses en el lugar del AFFO, sin aclararlo | «WELL con FFO, pero no aclares» |
| 4 | 17/11, v1.5.76 | Empresas con financiera propia (PACCAR, Deere, Caterpillar, GM, Ford, Harley-Davidson, IBM, Toyota, Honda; `financieras_propias.json`): cobertura de intereses y deuda neta ÷ EBITDA del negocio industrial, sin la financiera, como SSD | «sí, hagámoslo como hace SSD» |
| 5 | 17/11, v1.5.78 | Medio premio con aumentos simbólicos: si el dividendo regular creció menos de 1,5 % anual en los últimos 3 años completos, aristócrata +5 y aspirante +2,5 | «de acuerdo, vamos con eso» |
| 6 | 17/11, v1.5.78 | El puntaje no muestra 100: tope 99 | por estética |
| 7 | 17/11, v1.5.78 | Utilities: el payout futuro usa el corte del payout de ganancias: menos de 70 % → 15, 70 a 80 % → 7, más de 80 % → 0 | «sí, obvio, deberías haberlo hecho así de arranque» |
| 8 | 17/11, v1.5.79 | Bancos: el payout futuro usa el corte de su payout de ganancias: menos de 50 % → 15, 50 a menos de 75 % → 7, 75 % o más → 0 | «bancos, misma lógica» |
| 9 | 17/11, v1.5.79 | Utilities: los 15 puntos de deuda se reparten entre deuda neta ÷ EBITDA (7,5: segura 7,5, gris 3,5, crítica 0; cortes 5,0 y 6,0) y FFO ÷ Deuda (7,5: segura 7,5, gris 3,5, crítica 0; cortes 15 % y 10 %). El total queda sobre 100 | «mitad y mitad, 15 puntos de 100 la deuda» |
| 10 | 21/11, v1.5.83 | Congelamiento (3 o más años seguidos sin subir, terminado en los últimos 10 años o vigente, medido en la moneda de emisión; con la serie convertida queda sin medir) = dividendo errático: techo 80 y sin premio. Ya no resta 5 | «no lo consideres como recorte sino como dividendo errático» |
| 11 | 23/11, v1.5.84 | Ventas comparables: si la empresa separó un negocio y volvió a presentar los años recientes sin él (`ventas_comparables.json`), el crecimiento se mide desde el primer año presentado así (mínimo 2 años) | «ok ventas» |
| 12 | 23/11, v1.5.85 | Con dividendo errático o variable y recorte, cuenta solo el castigo que resta más (techo de 80 o −25/−10). Matemáticamente da siempre el mismo número que aplicar los dos (si el techo resta más, el puntaje menos el recorte igual queda arriba de 80): cambia solo la explicación | «castiga el que reste más puntos de los 2» |
| 13 | 23/11, v1.5.88 | Bancos con CET1 cargado: sin ganancias retenidas ÷ activos (la base se reparte entre las demás). Aseguradoras y brokers sin CET1 siguen con la medida | «bancos, opción B» |
| 14 | 23/11, v1.5.88 | Sin freno por pérdida si la pérdida del último año viene de operaciones discontinuadas y el resultado de las operaciones continuas de ese año fue positivo (Sony) | «Sony, vamos con la B» |

Decisiones de esos días que no separan la versión 2 de la 3 porque coinciden con el Word o son reglas de datos, y valen en las dos: cobertura con datos del mismo período y obligatoria (17/11), AFFO de la empresa y nada de FFO provisorio (17/11), CET1 con el requisito de cada banco (Word), intereses cargados a mano y NextEra con intereses pagados (17/11), FFO ÷ Deuda publicado por la empresa (17/11, el Word pide el de S&P), sin deuda o con deuda solo de alquileres = cobertura máxima (17/11), el «rebase» de National Grid cuenta como recorte (21/11, el Word dice que toda reducción nominal es recorte), medir en la moneda de emisión (21/11, Word punto 6).

## 6. Versiones 3.1 y 3.2 (solo simulación)

Se calculan sobre el resultado de la versión 3 de cada empresa: su base y sus ajustes ya resueltos (incluido «cuenta el castigo que resta más») y sus topes. No cambian ninguna variable ni ningún corte. Los parámetros se eligieron el 23/11 con datos de Stock Analysis (simulación fuera de la app) y se probaron sin cambios con los datos reales del 24/11.

### 6.1 Pasos, en orden

1. Puntaje parcial = base de la versión 3 (recalculada con sus variables) + sus ajustes.
2. Bloque de ciclo (restas fijas, se suman si se cumplen varias):
    1. Sector cíclico: Energía, Materiales Básicos, Semiconductores, Industrial, Consumo Discrecional, Hardware y servicios TI (por grupo de la app; hoy no por industria).
    2. Sector Bancos y seguros (incluye aseguradoras, brokers y administradoras).
    3. Beta del cache mayor a 1,2.
    4. Recortó en la crisis 2008-09 (historial en su moneda).
    5. Recortó en 2020-21.
    6. Menos de 10 años pagando dividendo.
3. Solo versión 3.1: si el parcial pasa 60, lo que excede 60 se multiplica por 0,6.
4. Topes de la versión 3, con el freno por pérdida y el de cobertura menor a 1,5 cambiados (tabla); el de dividendo variable (80) y el de trampa (40) quedan.
5. Redondeo, entre 0 y 99.
6. Solo versión 3.2: si alguna variable principal no tiene sus puntos máximos (zona gris o crítica), techo 80. Variables principales: cobertura, CET1, solvencia, payout de flujo libre, payout de ganancias, AFFO, payout futuro, deuda neta ÷ EBITDA, FFO ÷ Deuda.

### 6.2 Parámetros

| Parámetro | Versión 3.1 (opción 1) | Versión 3.2 (opción 2) |
| --- | --- | --- |
| Sector cíclico | −10 | −15 |
| Bancos y seguros | −10 | −15 |
| Beta mayor a 1,2 | −10 | −5 |
| Recortó en 2008-09 | −5 | −10 |
| Recortó en 2020-21 | −5 | −5 |
| Menos de 10 años pagando | −5 | −10 |
| Arriba de 60 | cada punto vale 0,6 | sin cambio |
| Freno por pérdida | máximo 60 | máximo 40 |
| Cobertura menor a 1,5 | máximo 40 | máximo 20 |
| Techo si una variable principal no está en zona segura | no | 80 |

Ejemplo, versión 3.2: una semiconductora con base 95, sin ajustes ni topes, beta 1,4 y payout futuro en gris. 95 − 15 (cíclica) − 5 (beta) = 75; el techo de 80 no actúa porque ya está debajo. La misma empresa en la 3.1: 95 − 10 − 10 = 75 → 60 + (75 − 60) × 0,6 = 69.

## 7. Propuestas de Claude y decisiones pendientes

### 7.1 Definiciones de Claude sin OK formal de Guille

1. **Pagos erráticos = 3 o más recortes en los últimos 10 años** (versiones 2 y 3; en la 3 se suma el congelamiento). El 24/11 Guille dio su definición: «pagos erráticos son subidas, bajadas, congelamientos, omisiones, todo lo que no sea un pago creciente y regular año a año; una ventana de más de 10 años con dividendos crecientes y regulares limpia las manchas del historial». Todavía no está programada. Faltan tres detalles: (a) si un solo año sin suba ya es mancha (el Word llamaba «transitorio» al congelamiento de 1 a 2 años y no lo penalizaba); (b) si «más de 10 años» son 11 seguidos subiendo o alcanza con 10; (c) si una empresa con poca historia que siempre subió queda limpia. Primer conteo, sin depurar bajas del año calendario: las erráticas o variables pasarían de 32 a 91 de las 158, y 27 de las que hoy tienen más de 80 bajarían a 80.
2. **Peso del FFO ÷ Deuda en utilities en la versión 2** (10 puntos más, total 110 llevado a 100). En la versión 3 lo decidió Guille (7,5 + 7,5).

### 7.2 Interpretaciones del Word para revisar

1. **Bordes del corte crítico**: el Word dice «crítica > 80 %» en el payout futuro y «> 75 %» en el payout de ganancias de bancos; el código toma el valor exacto (80 % y 75 %) como crítico. En el resto de las variables el valor exacto del corte va a la gris.
2. **Huecos del Word**: payout futuro gris 55 a 75 % y crítica más de 80 %; bancos gris 50 a 70 % y crítica más de 75 %; cargos fijos de REITs gris 2,0 a 3,0 y crítica menos de 1,5. Lo que queda entre la gris y la crítica va a gris.
3. **Trampa de rendimiento**: el Word pide un indicador técnico (T-DTS mayor a 1); se usa rendimiento mayor a 8 % y payout de flujo libre mayor a 100 % (Guille, 16/11).
4. **Payout futuro**: siempre el plan B (ganancias estimadas); el plan A (flujo libre futuro) no tiene fuente gratis.
5. **Cobertura de cargos fijos de los REIT y FFO ÷ Deuda de S&P**: se aproximan con EBITDA ÷ intereses y con el FFO ÷ Deuda que publica la empresa (o flujo operativo ÷ deuda total).

### 7.3 Decisiones que esperan a Guille

1. Bloque de ciclo sí o no. Si sí, la lista de cíclicas por industria (hoy va por sector y entran McDonald's, ADP y Lockheed).
2. Opción 1 u opción 2 (versión 3.1 o 3.2).
3. Freno por pérdida de 20 a 40 (elegido en 16 de 20 mitades al azar con datos reales).
4. TotalEnergies: en 2021 pasó de 0,68 a 0,66 € por trimestre (−1,5 % en el año). Con la tolerancia de 1 % es recorte (versión 3: 61; SSD 50).
5. Series mexicanas de la bolsa de origen (Coca-Cola FEMSA, FEMSA, América Móvil, Aeropuerto del Pacífico): Yahoo pierde y junta pagos. Propuesta: cargar su historia de dividendos desde los informes de cada empresa, con fuente.

### 7.4 Datos para revisar

1. Mes de cierre del ejercicio: falta en todas las fichas (sección 2.1); afecta el payout futuro de las versiones 2, 3, 3.1 y 3.2 en las empresas que no cierran en diciembre.
2. Honda 2022: figura un recorte dudoso (pasó de pagar 4 veces a 2 en 2021, con datos raros de Yahoo).
3. Sony: versión 3 = 97 contra SSD 60 (sin freno por la pérdida de 2026, que vino de la escisión de su financiera).
4. Siete series de la bolsa de origen no se usan (HMY, SUZ, HDB, ITUB, BBD, VIV, EMBJ): saltos de unidad o fechas que no coinciden con el ADR.
5. La SEC no devolvió datos de ICICI (IBN, error 404).

## 8. Archivos, datos y fuentes

| Qué | Dónde |
| --- | --- |
| Versión 1 | `scoring/dividendo.py` (`calcular`, `entrada`, escalas arriba del archivo) |
| Versiones 2 y 3 | `scoring/dividendo_v1.py` (`calcular(e, version)`) |
| Historial de dividendos | `scoring/dividendo.py` (`analizar_dividendos`) y `data/moneda_dividendo.py` (`historial`) |
| Cálculo de las 5 versiones para las 158 empresas | `calibrar_dividendo.calcular_todo` (versiones 1, 2 y 3) y `auditoria/calcular_5_versiones.py` (las 5, con 3.1 y 3.2) |
| Pruebas | `tests/test_v1571_score_v1.py`, `test_v1591_version2.py` y las de cada versión (`correr_pruebas.py`) |
| Puntajes, concordancia y detalle por empresa | `auditoria/puntajes_5_versiones.xlsx` (copia de la planilla https://claude.ai/artifact/V1r357MtwqX9Ei8MkZeDBt) |
| Word de Guille (versión 2) | `auditoria/Word_Guille_16-11-2026.docx` |
| Método de la versión 1 | https://claude.ai/artifact/URhosGmC1bjRMBFwr8q85e |
| Referencia de comparación | Simply Safe Dividends, lista de Guille del 21/11/2026 (`data/referencias/ssd_2026-11-21.json`), 158 empresas con número y dividendo |

Datos usados: los de la PC de Guille del 24/11/2026 (paquetes de Yahoo, SEC, dividendos de la bolsa de origen, monedas, múltiplos anuales), cache del 09/11, estimaciones del 11/11, fichas del 24/11. Código: TodoCedears v1.5.91.
