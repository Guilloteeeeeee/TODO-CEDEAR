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

- **Vista visual (en prueba):** arriba de la tabla hay un selector "Tabla clásica / Vista visual (prueba)". La vista visual muestra, por empresa: logo y nombre, la categoría con color y una barra de valoración (punto = precio de hoy, franja = rango de los métodos del Fair Value, raya = Fair Value promedio), una caja con el puntaje y las métricas usadas, el rango de 52 semanas, el Dividend Yield contra su mediana y el Mkt Cap. Se ordena con el selector de al lado. Con qué vista abre la app se cambia en `config/ajustes.py` (`VISTA_POR_DEFECTO`). El código está en `ui/tabla_visual.py`.
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

| Color | Categoría | Score |
|---|---|---|
| 🟢 Verde oscuro | Podría estar infravalorada | ≥ 70 |
| 🟩 Verde claro | Tendencia a infravalorada | 58–69 |
| 🟡 Amarillo | Parece bien valuada | 42–57 |
| 🟠 Naranja | Tendencia a sobrevalorada | 30–41 |
| 🔴 Rojo | Podría estar sobrevalorada | < 30 |
| ⚫ Gris | Sin datos (ni métricas ni rango de 52 semanas) | — |

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

Los datos se actualizan automáticamente cada 6 horas.

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
│   └── logos.py            # Logos: archivo local, favicon o iniciales
├── assets/logos/           # Logos 64x64 (<TICKER>.png), ya incluidos desde la v1.2.17
└── descargar_logos.py/.bat # Baja los logos a assets/logos/
```
