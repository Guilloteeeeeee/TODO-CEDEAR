# 📊 CEDEAR Screener

Detector de CEDEARs potencialmente infravalorados. Descarga datos automáticamente desde Yahoo Finance y calcula un score de valuación usando métricas fundamentales adaptadas por sector.

## Cómo funciona

**Score total = 85% fundamental + 15% técnico (rango 52 semanas)**

### Métricas por sector

| Sector | Métrica 1 | Métrica 2 | Métrica 3 | Métrica 4 |
|---|---|---|---|---|
| Materiales Básicos | EV/EBITDA (35%) | P/FCF (30%) | Div. Yield (25%) | P/B (10%) |
| REITs | P/FFO (30%) | P/AFFO (30%) | Div. Yield (30%) | EV/EBITDA (10%) |
| Financieros | P/B (40%) | PER (30%) | Div. Yield (20%) | P/FCF (10%) |
| Consumo Discrecional | P/FCF (30%) | EV/EBITDA (30%) | PER (25%) | Div. Yield (15%) |
| Consumo Básico | Div. Yield (35%) | EV/EBITDA (25%) | PER (25%) | P/FCF (15%) |
| Comunicación | PEG (30%) | EV/EBITDA (30%) | Div. Yield (20%) | PER (20%) |
| Industrial | EV/EBITDA (30%) | PER (30%) | P/FCF (25%) | Div. Yield (15%) |
| Tecnología | PEG (40%) | P/FCF (20%) | EV/EBITDA (20%) | PER (20%) |
| Energía | P/FCF (35%) | EV/EBITDA (30%) | Div. Yield (25%) | P/B (10%) |
| Salud | P/FCF (30%) | EV/EBITDA (25%) | PER (25%) | Div. Yield (20%) |
| Utilities | Div. Yield (45%) | P/FCF (20%) | EV/EBITDA (20%) | PER (15%) |

### Fuentes de datos y respaldo de sector (v1.2.12 / v1.2.13 / v1.2.14)

- **Stock Analysis es la fuente principal (v1.2.13):** para cada empresa se baja una sola página (ratios anuales) y de ahí salen el valor actual y la mediana de los últimos 5 años fiscales, incluidos PEG y, en REITs, Price/FFO y Price/AFFO reales. Yahoo Finance queda de respaldo para lo que Stock Analysis no trae (con el control de moneda de `data/moneda.py`).
- **v1.2.14 (arreglo de lectura):** en la primera prueba real Stock Analysis respondió bien (HTTP 200) pero la página llegaba ilegible porque el pedido aceptaba compresión `br` y la PC no tiene cómo abrirla. Ahora se pide solo `gzip/deflate`, si llega algo que no parece HTML se reintenta sin compresión, el lector de tabla es más tolerante (encabezado en cualquier fila, textos partidos, años sin "FY") y, si varias páginas seguidas no se pueden leer, se deja de consultar en esa corrida. `probar_stockanalysis.bat` ahora escribe un diagnóstico de lo que llega y guarda `sa_pagina_cruda.bin`.
- **Respaldo de sector:** si a una empresa le falta (o tiene imposible) la mediana histórica propia de una métrica, se compara contra la mediana de su sector (mediana de las medianas de sus pares, mínimo 5). Se ve en el detalle de cada empresa.
- **PEG:** usa su propia historia (5 años fiscales) cuando viene de Stock Analysis; si no, la mediana del sector. Nunca se compara contra sí mismo.
- **Fuente de cada métrica:** el detalle muestra si salió de Yahoo, de Stock Analysis o de la mediana del sector. Al terminar `generar_cache.bat` queda `resultados_cache.txt` con el resumen de fuentes.
- **La app publicada solo lee el caché guardado.** Nunca baja datos de Stock Analysis ni de Yahoo por su cuenta: el caché se genera una vez al mes en la PC con `generar_cache.bat`.
- **Trato con Stock Analysis:** respeta su `robots.txt`, una página por empresa con pausa entre pedidos, reintenta una vez si pide frenar y se detiene si lo bloquean. Sus términos de uso piden uso personal y manual, sin scripts, salvo rastreadores que respeten el `robots.txt`: usarlo es una decisión informada del dueño de la herramienta. El interruptor está en `config/ajustes.py` (`STOCK_ANALYSIS_MODO`: `"apagado"`, `"respaldo"` o `"principal"`).
- **Puntaje en sombra vs sector y Seguimiento:** cada fila guarda además `score_total_sector` / `categoria_sector` (la misma cuenta, pero comparando contra los pares del sector hoy). No cambia la categoría oficial. El panel "📈 Seguimiento" de la app compara, mes a mes, cuánto cambió el precio según cada categoría, usando las copias de `data/historial/`. Empieza a medir desde la segunda copia (con al menos 20 días de diferencia).
- **Aviso:** si el caché tiene más de 35 días, la app muestra un cartel para actualizarlo.

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
└── scoring/
    ├── engine.py           # Motor de scoring y categorías
    └── seguimiento.py      # Seguimiento mensual con las copias del historial
```
