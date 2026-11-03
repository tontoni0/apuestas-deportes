"""Genera notebooks/modelo_champions.ipynb a partir de src/futbol_modelo.py y src/config_jornada.py."""
import re
import nbformat as nbf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "tontoni0/apuestas-deportes"
BRANCH = "modelo-champions"


def sections(path):
    txt = path.read_text(encoding="utf-8")
    parts = re.split(r"^# %% \[(\w+)\] (.*)$", txt, flags=re.M)
    out = []
    for i in range(1, len(parts), 3):
        out.append((parts[i + 1].strip(), parts[i + 2].strip("\n")))
    return out


md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
cells = []

cells.append(md(f"""# Modelo de predicción para la Champions League (y cualquier liga)

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/notebooks/modelo_champions.ipynb)

**Qué hace este cuaderno**

1. Descarga resultados y cuotas de 15 ligas europeas y de la Champions/Europa League (2018 a hoy).
2. Calcula cinco modelos: Dixon-Coles, regresión logística con Elo, regresión lineal, regresión de Poisson y XGBoost.
3. Los combina en un ensamble y lo mezcla con las cuotas del mercado.
4. Simula cada partido 100,000 veces (Monte Carlo) para sacar marcadores, over/under y ambos anotan.
5. Hace el backtest que sugirió tu amigo: entrena con 3 temporadas, predice las 2 siguientes sin verlas y mide la tasa de acierto.

**Cómo usarlo desde el teléfono**

* Abre el enlace de Colab de arriba. Menú `Entorno de ejecución` > `Ejecutar todo`. Tarda de 2 a 4 minutos.
* Antes de cada jornada edita solo la celda **Configuración**: resultados nuevos, partidos, cuotas y bajas.
* En Colab el cuaderno baja datos frescos de football-data.co.uk. Si esa web falla, usa un espejo en GitHub con datos hasta septiembre de 2026.

**Advertencia.** En el backtest el modelo no le gana a las cuotas de Bet365. Úsalo para entender probabilidades, no como garantía de ganancia.
"""))

cells.append(code("!pip -q install xgboost scikit-learn scipy pandas matplotlib 2>/dev/null | tail -1"))

for title, body in sections(ROOT / "src" / "config_jornada.py"):
    cells.append(md(f"## {title}\n\nEsta es la única celda que necesitas editar. Los nombres de equipos siguen el formato de football-data.co.uk (por ejemplo `Ath Madrid`, `Sp Lisbon`, `Paris SG`, `Man United`)."))
    cells.append(code(body))

cells.append(md("""## Código del modelo

Las siguientes celdas definen las funciones. No hace falta tocarlas. Resumen de cada pieza:

* **Elo propio.** Cada equipo arranca con su Elo de ClubElo y sube o baja después de cada partido (liga o Europa). Ganar por más goles mueve más puntos. Los partidos europeos pesan más (K=30 contra K=20) porque son los únicos que conectan ligas distintas.
* **Dixon-Coles.** Estima ataque y defensa de cada equipo con un modelo de Poisson. Los partidos viejos pesan menos (vida media de un año). Corrige la frecuencia de 0-0, 1-0, 0-1 y 1-1. Los equipos con pocos datos (Sabah, Slavia, Slovan) se apoyan en su Elo.
* **Regresión logística.** Probabilidad de 1, X o 2 a partir de la diferencia de Elo y la localía.
* **Regresión lineal.** Predice la diferencia de goles y la convierte en 1X2 con una distribución normal.
* **Regresión de Poisson.** Predice goles de cada equipo con Elo y forma reciente.
* **XGBoost.** Árboles de decisión que combinan todas las variables anteriores.
* **Ensamble.** Promedio ponderado; los pesos salen de minimizar el error en temporadas que el modelo no vio.
* **Monte Carlo.** Simula 100,000 marcadores por partido con ruido en las tasas de gol para reflejar la incertidumbre del modelo."""))

for title, body in sections(ROOT / "src" / "futbol_modelo.py"):
    cells.append(md(f"### {title}"))
    cells.append(code(body))

cells.append(md("## 1. Carga de datos"))
cells.append(code("""os.makedirs("salidas", exist_ok=True)
df, seeds = build_dataset(UCL_2026_27, source=MODO_DATOS)
print("Partidos por temporada:")
print(df.groupby("season").size().rename(TEMPORADAS).to_string())"""))

cells.append(md("""## 2. Backtest: la regla 3 + 2 de tu amigo

**La idea.** Tomas 5 temporadas. El modelo aprende solo con las 3 primeras (2021-22, 2022-23, 2023-24). Después predice cada partido de las 2 últimas (2024-25 y 2025-26) sin conocer esos resultados. Comparas sus predicciones con lo que pasó. Así mides cómo le iría con partidos que nunca vio, que es tu situación real antes de una jornada.

**Por qué importa.** Si evalúas con los mismos partidos con los que entrenaste, el modelo se "sabe las respuestas" y la tasa de acierto sale inflada. Esto se llama sobreajuste o fuga de información.

**Dos versiones de la prueba**

* **Congelado** (la versión literal de la regla): todo se fija el 1 de julio de 2024. Elo, ataque y defensa no se actualizan durante dos años.
* **Walk-forward** (la versión realista): los parámetros del modelo se fijan con las 3 temporadas, pero antes de cada partido sí se usan los resultados ya jugados. Es lo que harías en la vida real. Ningún resultado futuro entra.

**Qué medir además de la tasa de acierto.** La tasa de acierto ignora la confianza. Un modelo que dice 34% local y otro que dice 80% local cuentan igual si gana el local. Por eso también se reportan:

* **Log loss:** castiga mucho estar muy seguro y fallar. Menor es mejor. Adivinar al azar da 1.099.
* **Brier y RPS:** error cuadrático de las probabilidades. El RPS respeta el orden local > empate > visita. Menor es mejor.
* **Comparación con el mercado:** si no le ganas a las cuotas, no hay ventaja para apostar."""))
cells.append(code("""t0 = time.time()
X, elo_wf = build_features(df, seeds)
X_frozen = frozen_features(df, seeds, f"{TEMPORADAS_ENTRENAR[-1] + 1}-07-01")
bt = run_backtest(df, X, seeds, TEMPORADAS_ENTRENAR, TEMPORADAS_PROBAR, X_frozen=X_frozen)
rep = backtest_report(df, bt)
rep.to_csv("salidas/backtest.csv", index=False)
print(f"Backtest listo en {time.time()-t0:.0f}s")
print("Pesos del ensamble (validados en 2023-24):", {k: round(v, 2) for k, v in bt["weights"].items()})
tabla = rep.pivot_table(index=["subconjunto", "modelo"], columns="modo", values=["accuracy", "log_loss"]).round(3)
tabla"""))
cells.append(code("""for sub in ["Champions League", "Top 5 ligas"]:
    plot_metricas(rep, "accuracy", sub, fn=f"salidas/acierto_{sub.split()[0].lower()}.png"); plt.show()
plot_metricas(rep, "log_loss", "Champions League", fn="salidas/logloss_champions.png"); plt.show()"""))
cells.append(md("""### Calibración, confianza y apuestas simuladas

Un modelo calibrado cumple esto: de los partidos donde dice 70%, el favorito gana cerca de 70% de las veces. Abajo se revisa eso y se simula apostar 1 unidad cada vez que el modelo ve valor contra Bet365."""))
cells.append(code("""te = bt["idx_test"]; y_te = df.loc[te, "res"].values
P_wf = bt["preds"]["walk-forward"]["ensamble"]
plot_calibracion(P_wf, y_te, fn="salidas/calibracion.png"); plt.show()

conf = P_wf.max(1); filas = []
for lo, hi in [(0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)]:
    m = (conf >= lo) & (conf < hi)
    filas.append({"confianza del favorito": f"{lo:.0%}-{min(hi,1):.0%}", "partidos": int(m.sum()),
                  "acierto real": (P_wf[m].argmax(1) == y_te[m]).mean(), "prob. media": conf[m].mean()})
conf_tab = pd.DataFrame(filas); conf_tab.to_csv("salidas/confianza.csv", index=False)
display(conf_tab.round(3))
print("Empates reales:", f"{(y_te==1).mean():.1%}", "| veces que el empate fue la opción más probable:", f"{(P_wf.argmax(1)==1).mean():.1%}")

odds = df.loc[te, ["oh", "od", "oa"]].values.astype(float)
ok = np.isfinite(odds).all(1) & (df.loc[te, "is_euro"] == 0).values
curvas, resumen = {}, []
for edge in [0.05, 0.10]:
    s, cur = value_bets_sim(P_wf[ok], *odds[ok].T, y_te[ok], edge=edge)
    curvas[f"Modelo, ventaja > {edge:.0%}"] = cur; s["estrategia"] = f"modelo con ventaja > {edge:.0%}"; resumen.append(s)
s, cur = value_bets_sim(market_probs(*odds[ok].T), *odds[ok].T, y_te[ok], edge=-1)
curvas["Siempre al favorito del mercado"] = cur; s["estrategia"] = "siempre al favorito"; resumen.append(s)
roi_tab = pd.DataFrame(resumen); roi_tab.to_csv("salidas/roi.csv", index=False)
display(roi_tab)
plot_roi(curvas, fn="salidas/roi.png"); plt.show()

for w in [0, .1, .2, .3, .5, 1]:
    PP = w * P_wf[ok] + (1 - w) * market_probs(*odds[ok].T)
    print(f"peso del modelo {w:.0%}: log loss {metrics(PP, y_te[ok])['log_loss']:.4f}")"""))

cells.append(md("### ¿Sirve para over/under y ambos anotan?\n\nLos mercados de goles se derivan de la matriz de marcadores de Dixon-Coles. Aquí se revisan en las mismas dos temporadas de prueba."))
cells.append(code("""idx = df.index[df.season.isin(TEMPORADAS_PROBAR) & X.dc_lh.notna()]
M = score_matrix(X.loc[idx, "dc_lh"].values, X.loc[idx, "dc_la"].values, X.loc[idx, "rho"].values)
tot = np.add.outer(np.arange(11), np.arange(11))
p_over = M[:, tot > 2.5].sum(1); p_btts = M[:, 1:, 1:].sum((1, 2))
y_over = ((df.loc[idx, "hg"] + df.loc[idx, "ag"]) > 2.5).values; y_btts = ((df.loc[idx, "hg"] > 0) & (df.loc[idx, "ag"] > 0)).values
o = df.loc[idx, ["o25", "u25"]].values.astype(float); okm = np.isfinite(o).all(1) & (df.loc[idx, "is_euro"] == 0).values
p_mk = (1 / o[okm, 0]) / (1 / o[okm, 0] + 1 / o[okm, 1]); ucl = (df.loc[idx, "div"] == "UCL").values
goles_tab = pd.DataFrame([
    {"mercado": "Over 2.5, ligas", "partidos": int(okm.sum()), "acierto modelo": ((p_over[okm] > .5) == y_over[okm]).mean(), "acierto Bet365": ((p_mk > .5) == y_over[okm]).mean()},
    {"mercado": "Over 2.5, Champions", "partidos": int(ucl.sum()), "acierto modelo": ((p_over[ucl] > .5) == y_over[ucl]).mean(), "acierto Bet365": np.nan},
    {"mercado": "Ambos anotan, Champions", "partidos": int(ucl.sum()), "acierto modelo": ((p_btts[ucl] > .5) == y_btts[ucl]).mean(), "acierto Bet365": np.nan}])
goles_tab.to_csv("salidas/goles.csv", index=False)
goles_tab.round(3)"""))

cells.append(md("""## 3. Modelos finales y predicciones de la jornada

Los modelos finales se entrenan con las 5 temporadas más lo jugado en 2026-27. La probabilidad **final** mezcla el ensamble con el mercado:

* El backtest dice que el peso óptimo del modelo frente a Bet365 es casi 0. Las cuotas de esta jornada salen de fuentes sueltas y algunas tienen días de antigüedad, así que aquí el modelo pesa 25% (`PESO_MODELO`). Súbelo a 50% si no tienes cuotas confiables.
* Las bajas se aplican como puntos Elo restados (celda Configuración) y mueven las tasas de gol de Dixon-Coles."""))
cells.append(code("""PESO_MODELO = 0.25
prod, w_prod = train_production(df, X, bt)
print("Pesos del ensamble final:", {k: round(v, 2) for k, v in w_prod.items()})
estado = current_state(df, seeds, ref_date=PARTIDOS[0][0])
fx = fixtures_df(PARTIDOS)
pred, sims, X_fx = predict_fixtures(fx, estado, prod, w_prod, PESO_MODELO, ajustes=AJUSTES_BAJAS, n_sims=N_SIMULACIONES)
pred_sin, _, _ = predict_fixtures(fx, estado, prod, w_prod, PESO_MODELO, ajustes={}, n_sims=20_000)
pred["final_1_sin_bajas"], pred["final_2_sin_bajas"] = pred_sin.final_1, pred_sin.final_2
pred["ens_1_sin_bajas"], pred["ens_2_sin_bajas"] = pred_sin.ensamble_1, pred_sin.ensamble_2
pred["fuente_cuotas"] = fx.fuente_cuotas
pred.drop(columns=["top_marcadores"]).to_csv("salidas/predicciones.csv", index=False)
json.dump({f"{r.local} vs {r.visita}": r.top_marcadores for r in pred.itertuples()}, open("salidas/marcadores.json", "w"), indent=1)

resumen = pred[["fecha", "hora_CET", "local", "visita", "final_1", "final_X", "final_2", "marcador_probable", "goles_esp", "over25", "btts"]].copy()
resumen.columns = ["fecha", "hora CET", "local", "visita", "1", "X", "2", "marcador", "goles", "over 2.5", "ambos anotan"]
display(resumen.style.format({"1": "{:.0%}", "X": "{:.0%}", "2": "{:.0%}", "goles": "{:.1f}", "over 2.5": "{:.0%}", "ambos anotan": "{:.0%}"}))
plot_partidos(pred, "Jornada 4: probabilidades finales (ensamble 25% + mercado 75%)", fn="salidas/partidos_final.png"); plt.show()
plot_partidos(pred, "Jornada 4: solo el ensamble de modelos (sin mercado)", col="ensamble", fn="salidas/partidos_modelo.png"); plt.show()"""))
cells.append(md("### Cada modelo por separado, mercado y señales de valor"))
cells.append(code("""cols = ["local", "visita"] + [f"{k}_{s}" for k in ["dc", "logit", "lineal", "poisson", "xgboost", "ensamble", "mercado"] for s in ["1", "X", "2"]] + ["cuotas"]
display(pred[cols].round(2))
print("Señales de valor (EV contra la cuota real, calculado con el ensamble).")
print("En el backtest este tipo de señal perdió dinero: tómalo como diferencia de opinión, no como apuesta.")
display(pred[["local", "visita", "posible_valor"]])"""))
cells.append(code("""for r in pred.itertuples():
    mc = sims[f"{r.local} vs {r.visita}"]
    top = ", ".join(f"{k} ({v:.0%})" for k, v in mc["top_marcadores"].items())
    print(f"{r.local} vs {r.visita}: 1 {mc['p_local']:.0%} | X {mc['p_empate']:.0%} | 2 {mc['p_visita']:.0%} | "
          f"goles {mc['goles_esp']:.1f} (90%: {mc['goles_p5_p95'][0]}-{mc['goles_p5_p95'][1]}) | "
          f"O1.5 {mc['over15']:.0%} O2.5 {mc['over25']:.0%} O3.5 {mc['over35']:.0%} | BTTS {mc['btts']:.0%}\\n   marcadores: {top}")"""))

cells.append(md("## 4. Tendencias de la Champions 2026-27 (jornadas 1 a 3)"))
cells.append(code("""cur = df[(df["div"] == "UCL") & (df.season == 2026)]
tabla_ucl = standings(cur); tabla_ucl.to_csv("salidas/tabla_ucl.csv")
print(f"Partidos: {len(cur)} | goles por partido: {(cur.hg + cur.ag).mean():.2f} | over 2.5: {((cur.hg + cur.ag) > 2.5).mean():.0%} | "
      f"ambos anotan: {((cur.hg > 0) & (cur.ag > 0)).mean():.0%} | gana local: {(cur.res == 0).mean():.0%} | empate: {(cur.res == 1).mean():.0%}")
hist = df[(df["div"] == "UCL") & df.season.isin([2024, 2025])]
print(f"Referencia 2024-25 y 2025-26: goles {(hist.hg + hist.ag).mean():.2f} | over 2.5 {((hist.hg + hist.ag) > 2.5).mean():.0%} | "
      f"gana local {(hist.res == 0).mean():.0%} | empate {(hist.res == 1).mean():.0%}")
tabla_ucl"""))

cells.append(md("""## 5. Modo fin de semana (ligas)

El mismo modelo sirve para cualquier partido de las 15 ligas cargadas. En Colab baja el calendario y las cuotas de football-data.co.uk. Para usarlo:

1. Cambia `dias` y `desde` en la celda de abajo.
2. Ejecuta la celda. Si no hay cuotas, la probabilidad final es solo la del modelo.

Para otra jornada de Champions edita `PARTIDOS`, `AJUSTES_BAJAS` y agrega los resultados nuevos a `UCL_2026_27`."""))
cells.append(code("""fin_semana = proximos_partidos_ligas(dias=5, desde=pd.Timestamp(PARTIDOS[-1][0]) + pd.Timedelta(days=1))
if len(fin_semana):
    pred_fs, _, _ = predict_fixtures(fin_semana, estado, prod, w_prod, PESO_MODELO, ajustes={}, n_sims=20_000)
    pred_fs["liga"] = fin_semana.competicion.values
    display(pred_fs[["fecha", "liga", "local", "visita", "final_1", "final_X", "final_2", "marcador_probable", "over25"]].round(2))
else:
    print("No hay partidos en la ventana elegida.")"""))

cells.append(md("""## 6. Límites del modelo (léelos antes de apostar)

* **No le gana al mercado.** En 7,069 partidos de liga de prueba, el log loss del mercado fue 0.967 y el del ensamble 0.984. Apostar a sus "valores" perdió entre 11% y 16% del dinero apostado.
* **El empate casi nunca es la opción más probable**, aunque ocurre en 1 de cada 4 partidos. Ningún modelo de este tipo lo predice bien.
* **Datos con huecos fuera de Colab.** El espejo de GitHub llega al 20 de septiembre de 2026 en ligas. Sin football-data.co.uk el modelo no ve la forma doméstica de octubre.
* **Equipos con poca historia** (Sabah, Slavia, Slovan, Kairat): su fuerza sale de un Elo por país más 3 a 10 partidos europeos. Ahí el error es mayor.
* **Las bajas son un ajuste manual**, con fuentes secundarias. Si un titular sí juega, el ajuste sobra.
* **Las cuotas cargadas son fotos de distintas casas y fechas.** Algunas se completaron con el modelo (columna `cuotas`). Revisa la cuota real antes de decidir."""))

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"}, "colab": {"provenance": []}})
out = ROOT / "notebooks" / "modelo_champions.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print("escrito", out, len(cells), "celdas")
