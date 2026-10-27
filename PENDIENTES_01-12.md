# Lista maestra de pendientes para el 01/12/2026 (TodoCedears)

Esta es la lista de verdad. Los recordatorios programados del 1/12 mandan a leer este archivo. Regla de oro: **no se cambia ningún método sin la decisión explícita de Guille** (primero problema, teoría y pros y contras). Y hay que decirle siempre la verdad cruda; con ~40 días de datos nada es concluyente.

Reglas fijas: español simple con voseo, estilo Dorsey (definición + ejemplo con números), trato de amigo, cerrar con "Conclusión resumen", no inventar datos, no más puntajes en sombra, no mostrar método ni pesos en pantalla. En el tema GuruFocus incluir siempre: "Que nos parezcamos más a GuruFocus no prueba que tengamos razón. El PEG podría estar captando algo que a ellos se les escapa."

## A. Antes de mirar nada (tareas de él en su PC)
- [ ] Actualización trimestral: `generar_cache.bat` (valida antes de reemplazar; si sale rota guarda `data/cache_rechazado.json`) y `bajar_fichas.bat` (sin `data/fichas.json` la ficha depende de Yahoo en vivo).
- [ ] Confirmar que en `data/historial` están `cache_2026-10-22.json` (re-puntuado) y el de hoy.
- [ ] Correr el Modo lote del DCF para las empresas que faltan y luego `python foso_desde_lote.py Lote_DCF_*.xlsx` (hoy `data/foso.json` cubre 53 de 166).
- [ ] **Pendientes de la PC (v1.2.68):** `bajar_etfs_yahoo.bat` (datos, Composición y descripción traducida de los ETFs → `data/etfs_yahoo.json`); `bajar_paquetes_yahoo.bat` de nuevo (agrega intereses y deuda de corto/largo plazo a los estados → `data/paquetes_yahoo.json`); Modo lote del DCF con los 4 bloques de la lista de foso; `probar_fuentes_noticias.bat`; después `generar_analisis_fundamental.bat` (necesita clave de API; primero revisar con `--bloque KO` y probar con 2 o 3 empresas).
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
