# Traspaso: charla aparte para los Análisis Fundamentales (informes)

**Para qué sirve:** separar los informes de las tareas de la app. Esta charla/carpeta es solo de los Análisis Fundamentales; el código de la app (pantallas, evaluación de cartera, noticias, etc.) va en otra charla.

## Cómo arrancar la charla nueva
1. **Cambiar el modelo a Opus** (regla de Guille: antes de escribir cualquier informe se le avisa para que cambie a Opus).
2. Leer primero `CLAUDE.md` (reglas de Guille y mapa del código) y este archivo. No releer toda la app.
3. Leer solo lo que hace falta de los informes:
   - `data/prompt_analisis_fundamental_v4.txt` (el prompt con las reglas de redacción: sin repetir palabras en una oración, sin múltiplos extremos).
   - `data/af_v4.py` (`contexto`, `tomar_foto`, `texto_html`, `validar`, `armar_prompt`).
   - `generar_analisis_fundamental.py` (cómo se generan).
   - `data/analisis_fundamental.json` (informes guardados: `{"fecha","datos":{TICKER:{…,"valuacion":{"foto":…}}}}`). Pesa ~1,8 MB: leer solo el ticker que se trabaja.
   - `data/macro_actual.txt` y `data/macro_numeros.json` (contexto macro; mantener al día).

## Condición previa (tareas de Guille en su PC)
Correr `generar_cache.bat`, `bajar_fichas.bat` y `bajar_etfs_yahoo.bat DBB DBA WEAT JMOM ILIT REMX`, y subir a GitHub `data/cache_datos.json`, `data/fichas.json`, `data/etfs_yahoo.json` y `data/historial`. Sin el caché fresco, la valuación de los 139 informes queda con el precio del 22/10.

## Las tres tareas (todas con Opus)
1. **Renovar la valuación de los 139 informes.** Hoy dicen "Escrito el 29/10 - 01/11" pero la foto de valuación es del 22/10. Con el caché nuevo: tomar la foto el mismo día que la fecha escrita y revisar que las frases (barata/cara, margen de seguridad) sigan teniendo sentido. La valuación arranca "Con el precio de X dólares al momento de escribir este informe (dd/mm/aaaa)".
2. **Pasada de redacción** (palabras repetidas, normas de escritura del prompt v4) sobre los informes.
3. **21 empresas nuevas y 10 renovaciones** (AMGN, ANET, SHOP, PFE, QCOM, MCD, NVO, COP, SONY, PBR).

## Reglas de Guille que valen acá
- Castellano rioplatense con voseo, simple, sin jerga; cruda verdad; no inventar datos; cerrar con "Conclusión resumen".
- Información educativa, nunca recomendaciones.
- En el texto de los informes no nombrar a Damodaran ni a Nelissen (en la línea de fuentes sí puede ir Damodaran).
- No cambiar metodología (score, categorías, Fair Value) sin su decisión explícita: primero el problema, la teoría y los pros y contras.
- Antes de escribir informes, avisarle (por la cuota y para que cambie a Opus).
- Hay poca cuota: trabajar de a tandas y mostrar el primer informe para que lo apruebe antes de seguir con el resto.

## Otros pendientes sueltos de informes
HWM (caída 265→199,2: investigar), HON/FDX (spin-offs) y DEO, textos escritos a mano con múltiplos altos (PLTR, CRWD, ARM, PANW, AMD, TSLA), tarea programada de renovación semanal (todavía no creada).
