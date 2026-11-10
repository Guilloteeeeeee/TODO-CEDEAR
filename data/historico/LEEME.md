# Archivo histórico propio de TodoCedears

Desde el 08/11/2026 (v1.5.48), todo lo que la app baja de Yahoo Finance y Stock Analysis se guarda acá **para siempre**. Así la base crece con el tiempo
y la app no depende de que esas fuentes respondan. Lo maneja `data/historico.py`; nadie tiene que editar estos archivos a mano.

## Qué hay

| Archivo | Qué guarda | Regla |
|---|---|---|
| `estados.json` | Años fiscales de Estado de Resultados, Balance, Flujo de Efectivo y Ratios de cada empresa | **Solo se agrega.** Mientras Yahoo siga trayendo un año, manda su versión más nueva; cuando lo deja de traer, queda congelado. Un dato vacío nunca borra uno guardado. Los «últimos 12 meses» van aparte (`ttm`). Desde la v1.5.58, `bajar_sec.bat` suma años más viejos de la SEC (marcados `"fuente": "SEC"`), solo hacia atrás y sin tocar los de Yahoo |
| `precios_mensuales.json` | Cierre del último día hábil de cada mes, de toda la historia | Ajustado por splits (no por dividendos) |
| `dividendos.json` | Cada dividendo pagado: fecha y monto por acción | Ajustado por splits |
| `splits.json` | Cada split: fecha y factor (10 = 10 por 1; 0,1 = contra-split 1 por 10) | Con esto se ajusta todo lo anterior |
| `multiplos_anuales.json` | Múltiplos de cada año fiscal (Stock Analysis) | Solo se agregan años |
| `fotos/AAAA-MM.json` | Una foto por mes de lo que cambia todos los días: precio, múltiplos y sus medianas, Fair Value, score, categoría, calidad del Análisis Fundamental; de los ETFs, precio, patrimonio, comisión, posiciones, sectores y dividendos; de las fichas, CEO, empleados, acciones | Si en el mes se corre varias veces, queda la última |
| `informes/TICKER_AAAA-MM-DD.json` | Cada versión de cada Análisis Fundamental | Nunca se pisa |
| `cambios.json` | Registro de correcciones de años ya guardados (más de 5% en ventas, resultado, activo, deuda, patrimonio o flujos), cambios de moneda y splits aplicados | Para revisar |

## Splits (lo más delicado)

Yahoo entrega precios, dividendos y cifras por acción **ya ajustados por todos los splits hasta el día de la bajada**. Lo guardado antes de un split nuevo no lo está:

- **Precios y dividendos:** cuando `bajar_historico` encuentra un split que no conocíamos, divide por el factor todos los valores guardados anteriores a esa fecha (y lo anota en `cambios.json`). Un split ya conocido nunca se aplica dos veces.
- **Estados:** cada año guarda la fecha en que se capturaron sus cifras por acción (`captura_acc`). Al leerlo, la ganancia por acción se divide y la cantidad de acciones se multiplica por los splits ocurridos **después** de esa fecha. Las cifras por acción de un año van siempre en bloque (todas de la misma bajada), para no mezclar números de antes y después de un split.
- **Fotos mensuales:** al leer una foto vieja, los campos de precio (precio, Fair Value, máximos y mínimos, dividendo anual) se ajustan por los splits posteriores; los múltiplos no cambian.

## Quién lo llena

| Se actualiza con… | Qué suma |
|---|---|
| `generar_cache.bat` | Foto del mes de las empresas |
| `bajar_paquetes_yahoo.bat` | Años fiscales nuevos de los estados |
| `bajar_etfs_yahoo.bat` | Foto del mes de los ETFs |
| `bajar_fichas.bat` | Foto del mes de las fichas |
| `bajar_multiplos_anuales.bat` | Múltiplos de los años nuevos |
| `bajar_historico.bat` | Precios mensuales, dividendos y splits de toda la historia (la primera vez, todo; después, los meses nuevos). **Correrlo una vez por mes** |
| `bajar_sec.bat` (v1.5.58) | Años fiscales viejos de la SEC (ingresos, resultados, ganancia por acción, activo, patrimonio, flujos, CAPEX, dividendos pagados). Con correrlo una vez alcanza; después, una vez por año |
| Renovar o escribir un informe | La versión nueva del informe |

Después de correr cualquiera de esos `.bat`, se sube la carpeta `data/historico` a GitHub junto con el resto.
`arrancar_historico.py` reconstruye el archivo desde el historial de GitHub (se usó el 08/11/2026 para arrancar; repetirlo no duplica nada).

## Qué tenía al arrancar (08/11/2026)

- Estados: 323 empresas, 1.296 años fiscales (el más viejo, 2021; 5 empresas ya tienen un año que Yahoo dejó de traer, como Apple 2022).
- Fotos: octubre 2026 (166 empresas, 59 ETFs) y noviembre 2026 (323 empresas, 96 ETFs, 323 fichas).
- Informes: 306 versiones.
- Precios, dividendos y splits: se completan con la primera corrida de `bajar_historico.bat`.
