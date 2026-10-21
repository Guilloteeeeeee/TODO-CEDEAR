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
│   └── sectors.py          # Sectores, métricas, pesos y universo de tickers
├── data/
│   ├── fetcher.py          # Descarga de datos (Yahoo Finance)
│   ├── moneda.py           # Control de moneda y acciones por ADR (empresas de fuera de EEUU)
│   ├── historial/          # Copias con fecha del cache (se crean con generar_cache)
│   └── tickers_custom.json # Universo personalizado (se genera al editar)
└── scoring/
    └── engine.py           # Motor de scoring y categorías
```
