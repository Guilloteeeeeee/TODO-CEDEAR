# Auditoría del Score de Seguridad del Dividendo (TodoCedears) — prompt para Opus

ultrathink

Pensá a fondo antes de responder. Esta auditoría es para decidir con qué método sigo, así que necesito rigor y exactitud extrema.

## Quién soy y qué te pido

Soy Guille, médico y asesor financiero registrado en la CNV. Armo una app (TodoCedears) que, entre otras cosas, va a mostrar un **Score de Seguridad del Dividendo** de 0 a 100 para cada empresa. Hay cinco versiones del score. Quiero que audites **absolutamente todo**: los métodos, cómo están programados, las reglas de datos, los resultados por empresa y la comparación con Simply Safe Dividends (SSD). Al final necesito que me ayudes a decidir los puntos pendientes y con qué versión seguir.

No cambies nada vos: proponé, con pros y contras, y yo decido.

## Material (todo está en este repositorio; no hace falta adjuntar nada)

1. **`auditoria/METODOS_5_VERSIONES.md`**: métodos exactos de las 5 versiones. Es la referencia: cada regla, corte, puntaje, freno y premio de cada versión, las reglas de datos comunes y los pendientes. Las secciones están numeradas: citá siempre el número.
2. **`auditoria/puntajes_5_versiones.xlsx`**: planilla «Score de dividendos: 5 versiones contra SSD». Solapas: Cómo leer · Puntajes (las 5 versiones + SSD, categoría y distancia por empresa) · Concordancia (igual, ±1, ±2, ±3, ±4, acumulados, diferencias medias y empresas por categoría) · Detalle V1 · Detalle V2 · Detalle V3 · Detalle V3.1 y V3.2 · Historial de dividendos. Para leerla: `pip install openpyxl --break-system-packages` (o pandas).
3. **`auditoria/Word_Guille_16-11-2026.docx`**: mi Word original «Score de Seguridad de Dividendos (Escala 0 - 100)» (base de la versión 2). Para leerlo: `pip install python-docx --break-system-packages`.
4. **Código**: `scoring/dividendo.py` (versión 1 y el historial de dividendos, `analizar_dividendos`), `scoring/dividendo_v1.py` (versiones 2 y 3: `calcular(e, version)`), `data/moneda_dividendo.py` (moneda en que se mide el dividendo), `calibrar_dividendo.py` (`entrada`, `calcular_todo`: arma la entrada de cada empresa), `auditoria/calcular_5_versiones.py` (las 5 versiones; la función `capa` hace la 3.1 y la 3.2).
5. **Datos** (los mismos con que se calculó la planilla): `data/cache_datos.json`, `data/paquetes_yahoo.json`, `data/historico/` (estados, dividendos, splits, precios, dividendos de la bolsa de origen, monedas), `data/estimaciones_analistas.json`, los archivos cargados a mano (`data/ffo_reit.json`, `data/cet1_bancos.json`, `data/solvencia_aseguradoras.json`, `data/intereses_manuales.json`, `data/financieras_propias.json`, `data/ffo_deuda_utilities.json`, `data/ventas_comparables.json`) y la lista de SSD (`data/referencias/ssd_2026-11-21.json`).
6. **Mapa del repositorio**: `CLAUDE.md` (leelo primero, sección «Cómo fluyen los datos», punto 3).

**Podés y tenés que correr código para verificar.** `python auditoria/calcular_5_versiones.py` recalcula las 5 versiones de las 158 empresas (tarda unos minutos) y deja `auditoria/resultado_5_versiones.json` con el detalle de cada una; tiene que dar las mismas concordancias que la planilla. Las pruebas: `python correr_pruebas.py` (la de rapidez falla sin streamlit, es normal) o `python tests/test_v1591_version2.py`. Podés escribir scripts propios en una carpeta temporal para probar casos (por ejemplo, cambiar un corte y ver qué pasa), pero **sin modificar los archivos del repositorio**. Internet: Yahoo y la SEC no responden desde la nube; trabajá con los datos guardados.

Las versiones:
- **Versión 1**: el primer método (Weiss + SSD, 10/11/2026).
- **Versión 2**: mi Word del 16/11 con lo que definí ese día.
- **Versión 3**: la versión 2 con mis decisiones posteriores (14 cambios, sección 5 del documento).
- **Versión 3.1**: versión 3 + opción 1 (bloque de ciclo y compresión arriba de 60).
- **Versión 3.2**: versión 3 + opción 2 (bloque de ciclo y techo de 80 si una variable principal no está en zona segura).

Las cinco se calcularon con los mismos datos (Yahoo Finance y SEC del 24/11/2026; SSD del 21/11/2026; 158 empresas).

## Cómo quiero que trabajes: 10 auditores y 10 refutadores

Si tu entorno te permite lanzar subagentes, lanzá **10 auditores** y **10 refutadores** independientes. Si no, hacé las 20 pasadas en orden, cada una con su rol, y no mires las conclusiones de un auditor hasta su fase de refutación.

### Fase 1: auditores (cada uno con su área)

| # | Auditor | Qué revisa |
| --- | --- | --- |
| A1 | Fidelidad al Word | Que la versión 2 haga exactamente lo que dice el Word, regla por regla (sección 4 contra el Word y contra `dividendo_v1.py` con `version=2`). Dónde el Word deja huecos y si las definiciones usadas son razonables |
| A2 | Decisiones de la versión 3 | Cada uno de los 14 cambios (sección 5): si está bien programado, si es coherente con el resto del método, qué efecto tiene en los puntajes y si tiene efectos no buscados |
| A3 | Versión 1 | Coherencia interna del primer método (sección 3): pilares, escalas, tabla de calificación por cobertura, topes, excepción con la ganancia de los analistas |
| A4 | Historial de dividendos | Sección 2.3 y `analizar_dividendos`/`historial`: definición de dividendo regular, recorte, suspensión, cambios de frecuencia, año calendario contra año corrido, año en curso, moneda de emisión, series convertidas, consolidaciones. Buscá recortes falsos o recortes reales que no se ven (solapa Historial) |
| A5 | Datos contables | Sección 2.1 y 2.2: 12 meses contra último año, mismo período en la cobertura, años de la SEC, monedas y ADR, intereses cargados a mano, deuda del trimestre descartada, mes de cierre que falta |
| A6 | Sectores especiales | Bancos (CET1, requisito, payout), aseguradoras (solvencia), REITs (AFFO, cargos fijos), utilities (pesos, FFO ÷ Deuda), financieras propias, empresas asset-light y de consumo básico en la prueba ácida |
| A7 | Estadística de la comparación | Solapa Concordancia: si las medidas están bien calculadas, cuánto pesa que 55 de los 158 puntajes de SSD caigan justo en un borde (20/40/60/80), riesgo de sobreajuste en las opciones 1 y 2, tamaño de muestra, y si parecerse a SSD es un buen criterio |
| A8 | Versiones 3.1 y 3.2 | Sección 6: bloque de ciclo (sector cíclico por grupo y no por industria, bancos, beta, crisis, años pagando), compresión arriba de 60, techo de 80 por zona gris, frenos cambiados. Qué se gana y qué se pierde con cada una |
| A9 | Respaldo teórico | Los cortes y pesos contra la literatura que cita el Word (DeAngelo, Jensen, Altman, Michaely, Grullon y otros) y contra la práctica de las calificadoras. Qué cortes no tienen respaldo |
| A10 | Casos por empresa | Las 30 diferencias más grandes con SSD en cada versión, y todas las que la versión 3 pone en «Muy segura» y SSD no: revisá en las solapas de detalle cómo se formó cada puntaje y si el número es correcto según el método |

Cada auditor entrega hallazgos con: número, versión, sección del documento (y archivo/función o solapa/empresa), tipo (**error de programación**, **inconsistencia del método**, **regla sin respaldo**, **problema de datos**, **duda de interpretación**), gravedad (alta / media / baja), evidencia concreta y qué propondría.

### Fase 2: refutadores (uno por auditor)

El refutador R*n* recibe solo los hallazgos del auditor A*n* y trata de **refutarlos** con el material: busca la regla, la decisión o el dato que muestre que el hallazgo está mal, exagerado o ya resuelto. Para cada hallazgo deja un veredicto: **confirmado**, **refutado** o **dudoso**, con su razón.

### Fase 3: síntesis

Un juez final arma el informe con los hallazgos confirmados y dudosos, ordenados por gravedad. Lo refutado va al final, en una línea cada uno.

## Puntos pendientes que tenés que contestar sí o sí

Para cada uno: el problema, la teoría, pros y contras de cada opción, y qué harías vos y por qué.

1. **Pagos erráticos** (sección 7.1). Mi definición del 24/11: «pagos erráticos son subidas, bajadas, congelamientos, omisiones, todo lo que no sea un pago creciente y regular año a año; una ventana de más de 10 años con dividendos crecientes y regulares limpia las manchas del historial». Necesito que me ayudes con: (a) si un solo año sin suba ya es mancha (el Word llamaba «transitorio» al congelamiento de 1 a 2 años); (b) si la ventana limpia es de 11 años seguidos o de 10; (c) qué pasa con una empresa nueva que siempre subió; (d) si la consecuencia debe seguir siendo techo 80 y sin premio. Ojo con el impacto: en un primer conteo pasarían de 32 a 91 de 158 empresas.
2. **Peso del FFO ÷ Deuda en utilities** en la versión 2 (propuesta de Claude: 10 puntos sobre 110).
3. **Bloque de ciclo**: ¿sí o no? Si sí, ¿por sector o por industria? Hoy entran McDonald's, ADP y Lockheed como cíclicas por su sector.
4. **Opción 1 u opción 2** (versión 3.1 o 3.2).
5. **Freno por pérdida**: ¿máximo 20 (Word) o 40?
6. **TotalEnergies 2021**: bajó 0,68 → 0,66 € por trimestre (−1,5 % en el año). ¿Es recorte con tolerancia de 1 %, o la tolerancia tiene que ser otra?
7. **Series de dividendos de México** (Coca-Cola FEMSA, FEMSA, América Móvil, Aeropuerto del Pacífico): Yahoo pierde y junta pagos. ¿Las cargamos a mano desde los informes de cada empresa?
8. **Bordes del corte crítico** (sección 7.2): el código toma 80 % (payout futuro) y 75 % (bancos) como críticos; el Word dice «más de».
9. **Trampa de rendimiento** simplificada en lugar del T-DTS, y **payout futuro** siempre con ganancias (sin flujo libre futuro).
10. **Sony**: versión 3 = 97 contra SSD 60. ¿Está bien no frenar por una pérdida que viene de operaciones discontinuadas?
11. **Con qué versión sigo** (1, 2, 3, 3.1 o 3.2, o una combinación), y qué cambiarías antes de mostrarla al público.

## Reglas

- Castellano rioplatense, simple, sin jerga. Soy médico, no contador: cada concepto técnico, con una definición corta y un ejemplo con números reales del material.
- **No inventes nada.** Si algo no se puede verificar con el material, decilo («no verificable con el material») en vez de suponer.
- Citá siempre de dónde sale cada afirmación: sección del documento, archivo y función, o solapa y empresa.
- Separá siempre un **error de programación** (el código no hace lo que dice el método) de una **decisión de método** (el código hace lo que se decidió, pero la decisión se puede discutir).
- Parecerse más a SSD no prueba que el score sea mejor: SSD es una referencia, no la verdad. Decí cuándo una mejora de concordancia puede ser sobreajuste.
- Es información educativa: nada de recomendaciones de inversión sobre empresas.
- No propongas cambios de método sin pros y contras; la decisión es mía.

## Dónde dejar el resultado

- Escribí el informe completo en **`auditoria/INFORME_AUDITORIA.md`** (formato de abajo). Si armás tablas o cálculos extra, dejalos en `auditoria/anexos/`.
- **No cambies ningún otro archivo del repositorio** (ni código, ni datos, ni pruebas). Esto es solo auditoría.
- Al terminar, hacé commit solo de `auditoria/INFORME_AUDITORIA.md` y `auditoria/anexos/`, y subilo a una rama nueva llamada `auditoria-score-dividendos` (no a `main`).
- En el chat, al final, mostrame el resumen y la conclusión resumen.

## Formato de la respuesta

1. **Resumen** en 10 líneas como máximo.
2. **Tabla de hallazgos**: número, auditor, versión, sección/archivo/empresa, tipo, gravedad, evidencia, veredicto del refutador, qué harías.
3. **Respuestas a los 11 puntos pendientes**, uno por subtítulo, con pros, contras y tu propuesta.
4. **Recomendación de método**: con qué versión seguir y qué cambiar primero, en orden de importancia.
5. **Lo que no pudiste verificar** y qué dato haría falta.
6. **Conclusión resumen** al final, breve.
