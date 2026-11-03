# Apuestas deportes: modelo de predicción de fútbol

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tontoni0/apuestas-deportes/blob/modelo-champions/notebooks/modelo_champions.ipynb)

Modelo para predecir partidos de la Champions League y de 15 ligas europeas. Combina Elo, Dixon-Coles, regresión logística, regresión lineal, regresión de Poisson y XGBoost, lo mezcla con las cuotas del mercado y simula cada partido 100,000 veces con Monte Carlo.

Además del 1X2 predice goles totales por línea, goles por equipo, goles al descanso, ambos anotan, doble oportunidad, córners, tarjetas (amarillas, rojas y puntos), faltas, tiros, tiros a puerta y fueras de juego.

## Archivos

| Archivo | Qué es |
|---|---|
| `notebooks/modelo_champions.ipynb` | Notebook para Google Colab, ya ejecutado (puedes ver resultados sin correrlo) |
| `reportes/informe_jornada4_champions.pdf` | Informe de la jornada 4 (3 y 4 de noviembre de 2026) |
| `resultados/jornada4_predicciones.csv` | Probabilidades de cada modelo, mercado y final para los 18 partidos |
| `resultados/backtest_2024_2026.csv` | Métricas del backtest por modelo |
| `resultados/jornada4_estadisticas.csv` | Goles, córners, tarjetas, faltas, tiros y fueras de juego esperados con probabilidades por línea |
| `resultados/backtest_estadisticas_2024_2026.csv` | Backtest de las estadísticas contra el promedio de la liga |
| `resultados/jornada4_parlays.csv` | Parlays sugeridos con probabilidad y cuota justa |
| `resultados/jornada4_patas_parlay.csv` | Todas las patas posibles por partido (moneyline, goles, córners, tiros) con su probabilidad |
| `src/futbol_modelo.py` | Código del modelo (cada bloque `# %%` es una celda del notebook) |
| `src/config_jornada.py` | Resultados, partidos, cuotas y bajas de la jornada |
| `tools/build_notebook.py` | Regenera el notebook a partir de `src/` |
| `tools/make_report.py` | Genera el PDF a partir de las salidas del notebook |

## Uso semanal

1. Abre el notebook con el botón de Colab.
2. Edita la celda **Configuración**: agrega los resultados nuevos a `UCL_2026_27`, cambia `PARTIDOS` (fecha, equipos, cuotas), `AJUSTES_BAJAS` y `ARBITROS`.
3. `Entorno de ejecución` > `Ejecutar todo` (2 a 4 minutos).
4. Para la liga del fin de semana usa la sección 6: baja calendario y cuotas de football-data.co.uk.

## Backtest (regla 3 + 2)

Entrenado con 2021-22, 2022-23 y 2023-24; evaluado en 2024-25 y 2025-26 sin ver esos resultados.

| | Champions (378 partidos) | Top 5 ligas (3,503 partidos) |
|---|---|---|
| Ensamble, walk-forward | 58.2% de acierto | 52.1% |
| Ensamble, congelado | 56.9% | 51.0% |
| Sin modelo (frecuencias) | 50.5% | 43.0% |
| Bet365 (partidos de liga con cuotas) | | 53.4% |

El modelo está bien calibrado pero no le gana al mercado. Apostar cada vez que veía valor contra Bet365 dio un ROI de -12.4% en 3,701 apuestas.

Estadísticas (misma regla, 6,789 partidos de liga), acierto en over/under contra usar el promedio de la liga:

| Estadística | Línea | Modelo | Promedio de la liga |
|---|---|---|---|
| Córners | 9.5 | 55.4% | 54.1% |
| Tarjetas | 4.5 | 60.4% | 60.3% |
| Faltas | 23.5 | 66.0% | 64.0% |
| Tiros | 24.5 | 59.5% | 55.1% |
| Tiros a puerta | 8.5 | 57.0% | 53.7% |

Córners y tarjetas casi no se predicen mejor que con el promedio. Los fueras de juego son una estimación sin validar porque no hay datos libres por partido.
