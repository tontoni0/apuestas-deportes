# Apuestas deportes: modelo de predicción de fútbol

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tontoni0/apuestas-deportes/blob/modelo-champions/notebooks/modelo_champions.ipynb)

Modelo para predecir partidos de la Champions League y de 15 ligas europeas. Combina Elo, Dixon-Coles, regresión logística, regresión lineal, regresión de Poisson y XGBoost, lo mezcla con las cuotas del mercado y simula cada partido 100,000 veces con Monte Carlo.

## Archivos

| Archivo | Qué es |
|---|---|
| `notebooks/modelo_champions.ipynb` | Notebook para Google Colab, ya ejecutado (puedes ver resultados sin correrlo) |
| `reportes/informe_jornada4_champions.pdf` | Informe de la jornada 4 (3 y 4 de noviembre de 2026) |
| `resultados/jornada4_predicciones.csv` | Probabilidades de cada modelo, mercado y final para los 18 partidos |
| `resultados/backtest_2024_2026.csv` | Métricas del backtest por modelo |
| `src/futbol_modelo.py` | Código del modelo (cada bloque `# %%` es una celda del notebook) |
| `src/config_jornada.py` | Resultados, partidos, cuotas y bajas de la jornada |
| `tools/build_notebook.py` | Regenera el notebook a partir de `src/` |
| `tools/make_report.py` | Genera el PDF a partir de las salidas del notebook |

## Uso semanal

1. Abre el notebook con el botón de Colab.
2. Edita la celda **Configuración**: agrega los resultados nuevos a `UCL_2026_27`, cambia `PARTIDOS` (fecha, equipos, cuotas) y `AJUSTES_BAJAS`.
3. `Entorno de ejecución` > `Ejecutar todo` (2 a 4 minutos).
4. Para la liga del fin de semana usa la sección 5: baja calendario y cuotas de football-data.co.uk.

## Backtest (regla 3 + 2)

Entrenado con 2021-22, 2022-23 y 2023-24; evaluado en 2024-25 y 2025-26 sin ver esos resultados.

| | Champions (378 partidos) | Top 5 ligas (3,503 partidos) |
|---|---|---|
| Ensamble, walk-forward | 58.2% de acierto | 52.1% |
| Ensamble, congelado | 56.9% | 51.0% |
| Sin modelo (frecuencias) | 50.5% | 43.0% |
| Bet365 (partidos de liga con cuotas) | | 53.4% |

El modelo está bien calibrado pero no le gana al mercado. Apostar cada vez que veía valor contra Bet365 dio un ROI de -12.4% en 3,701 apuestas.
