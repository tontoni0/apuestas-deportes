"""Genera el informe PDF a partir de las salidas del notebook (carpeta salidas/)."""
import sys, json, os, re
from pathlib import Path
import pandas as pd
import matplotlib
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

SAL = Path(sys.argv[1])
OUT = Path(sys.argv[2])
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config_jornada import AJUSTES_BAJAS, PARTIDOS  # noqa

FD = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(FD / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(FD / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB")

INK, INK2, MUTED, LINE, SOFT = (colors.HexColor(c) for c in ["#0b0b0b", "#52514e", "#898781", "#c3c2b7", "#f0efec"])
BLUE, RED = colors.HexColor("#2a78d6"), colors.HexColor("#e34948")
st = {
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=17, leading=21, textColor=INK, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=12.5, leading=16, textColor=INK, spaceBefore=10, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="DVB", fontSize=10, leading=13, textColor=INK, spaceBefore=6, spaceAfter=2),
    "p": ParagraphStyle("p", fontName="DV", fontSize=9, leading=12.6, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("s", fontName="DV", fontSize=7.6, leading=10, textColor=INK2, spaceAfter=3),
    "cell": ParagraphStyle("c", fontName="DV", fontSize=7.6, leading=9.4, textColor=INK),
    "cellb": ParagraphStyle("cb", fontName="DVB", fontSize=7.6, leading=9.4, textColor=INK),
    "cellh": ParagraphStyle("ch", fontName="DVB", fontSize=6.8, leading=8.2, textColor=INK),
}
P = lambda t, s="p": Paragraph(t, st[s])


def IMG(path, width):
    w, h = ImageReader(str(path)).getSize()
    return Image(str(path), width=width, height=width * h / w)

NOMBRE = {"Ath Madrid": "Atlético de Madrid", "Sp Lisbon": "Sporting CP", "Paris SG": "PSG", "Man United": "Manchester United",
          "Man City": "Manchester City", "Bodo/Glimt": "Bodø/Glimt", "Fenerbahce": "Fenerbahçe", "Shakhtar Donetsk": "Shakhtar",
          "Slavia Praha": "Slavia Praga", "PSV Eindhoven": "PSV", "Bayern Munich": "Bayern Múnich", "AEK": "AEK Atenas",
          "Betis": "Real Betis", "Club Brugge": "Club Brujas"}
N = lambda t: NOMBRE.get(t, t)
CDMX = {"18:45": "11:45", "21:00": "14:00"}

pred = pd.read_csv(SAL / "predicciones.csv")
rep = pd.read_csv(SAL / "backtest.csv")
conf = pd.read_csv(SAL / "confianza.csv")
roi = pd.read_csv(SAL / "roi.csv")
goles = pd.read_csv(SAL / "goles.csv")
tabla = pd.read_csv(SAL / "tabla_ucl.csv")
marc = json.load(open(SAL / "marcadores.json"))
est = pd.read_csv(SAL / "estadisticas.csv")
bte = pd.read_csv(SAL / "backtest_estadisticas.csv")
par = pd.read_csv(SAL / "parlays.csv")


def tbl(data, widths, header_rows=1, zebra=True, align_right_from=None):
    data = [[Paragraph(str(c), st["cellh"]) if isinstance(c, str) else c for c in row] if i < header_rows else row
            for i, row in enumerate(data)]
    t = Table(data, colWidths=widths, repeatRows=header_rows)
    style = [("FONT", (0, 0), (-1, -1), "DV", 7.6), ("FONT", (0, 0), (-1, header_rows - 1), "DVB", 7.6),
             ("TEXTCOLOR", (0, 0), (-1, -1), INK), ("LINEBELOW", (0, header_rows - 1), (-1, header_rows - 1), 0.6, LINE),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if zebra:
        for r in range(header_rows, len(data)):
            if (r - header_rows) % 2 == 1:
                style.append(("BACKGROUND", (0, r), (-1, r), SOFT))
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def pct(x):
    return f"{x:.0%}"


def m(sub, modelo, modo, col):
    r = rep[(rep.subconjunto == sub) & (rep.modelo == modelo) & (rep.modo == modo)]
    return float(r[col].iloc[0])


story = []
# ------------------------------------------------------------------ portada y resumen
story += [P("Champions League, jornada 4: predicciones y backtest", "h1"),
          P("Partidos del martes 3 y miércoles 4 de noviembre de 2026. Informe generado el 3 de noviembre de 2026 con datos hasta el 21 de octubre (Champions) y el 20 de septiembre (ligas).", "small"),
          Spacer(1, 6)]

acc_ucl_wf, acc_ucl_fr = m("Champions League", "Ensamble", "walk-forward", "accuracy"), m("Champions League", "Ensamble", "congelado", "accuracy")
acc_top_wf = m("Top 5 ligas", "Ensamble", "walk-forward", "accuracy")
ll_mk = m("Ligas con cuotas", "Mercado (Bet365) (solo partidos con cuotas)", "walk-forward", "log_loss")
ll_en = m("Ligas con cuotas", "Ensamble (solo partidos con cuotas)", "walk-forward", "log_loss")
acc_mk = m("Ligas con cuotas", "Mercado (Bet365) (solo partidos con cuotas)", "walk-forward", "accuracy")
acc_en = m("Ligas con cuotas", "Ensamble (solo partidos con cuotas)", "walk-forward", "accuracy")
roi5 = roi[roi.estrategia.str.contains("5%")].iloc[0]
story += [P("Resumen", "h2"),
          P(f"<b>Qué se hizo.</b> Se juntaron 34,863 partidos de 15 ligas europeas y de la Champions/Europa League desde 2018. Con ellos se entrenaron cinco modelos (Dixon-Coles, regresión logística con Elo, regresión lineal, regresión de Poisson y XGBoost), se combinaron en un ensamble y se mezclaron con las cuotas del mercado. Cada partido se simuló 100,000 veces con Monte Carlo."),
          P(f"<b>Backtest con la regla de tu amigo.</b> Entrenado con 2021-22 a 2023-24 y probado en 2024-25 y 2025-26 sin ver esos resultados, el ensamble acertó el ganador en {acc_ucl_wf:.1%} de los partidos de Champions y en {acc_top_wf:.1%} de los de las cinco grandes ligas. En la versión literal (todo congelado dos años) baja a {acc_ucl_fr:.1%} en Champions."),
          P(f"<b>Lo más importante.</b> El modelo no le gana a Bet365. En los mismos partidos de liga el mercado acertó {acc_mk:.1%} contra {acc_en:.1%} del ensamble, con mejor log loss ({ll_mk:.3f} contra {ll_en:.3f}). Apostar cada vez que el modelo veía valor dio un ROI de {roi5.roi:.1%} en {int(roi5.apuestas):,} apuestas. Las probabilidades de abajo sirven para entender cada partido. No son una ventaja sobre las casas."),
          P("<b>Estadísticas del partido.</b> Además del 1X2 el informe da goles totales por línea, goles por equipo y al descanso, córners, tarjetas, faltas, tiros, tiros a puerta y fueras de juego. En el backtest el modelo de estadísticas apenas le gana al promedio de la liga: acierta el over/under 9.5 de córners {:.0%} de las veces contra {:.0%} del promedio, y el 4.5 de tarjetas {:.0%} contra {:.0%}. Tómalas como referencia del partido típico, no como ventaja.".format(
              *[float(bte[bte["estadística"] == n][c].iloc[0]) for n, c in [("Córners", "acierto O/U modelo"), ("Córners", "acierto O/U liga"),
                ("Tarjetas (amarillas + rojas)", "acierto O/U modelo"), ("Tarjetas (amarillas + rojas)", "acierto O/U liga")]])),
          P("<b>Probabilidad final.</b> 75% mercado y 25% ensamble. El peso del modelo es mayor que el óptimo del backtest (casi 0%) porque varias cuotas de esta jornada son fotos de distintas casas, algunas con días de antigüedad, y en 11 partidos faltaba al menos una cuota."),
          ]

# ------------------------------------------------------------------ predicciones
story += [PageBreak(), P("Predicciones de la jornada 4", "h2"),
          P("Hora del centro de México = hora CET menos 7. Probabilidades finales con bajas aplicadas. Goles, over 2.5 y ambos anotan salen del Monte Carlo.", "small")]
head = ["Fecha", "CET", "CDMX", "Partido", "1", "X", "2", "Marcador", "Goles", "O2.5", "BTTS"]
rows = [head]
for r in pred.itertuples():
    rows.append([r.fecha[5:], r.hora_CET, CDMX.get(r.hora_CET, ""), Paragraph(f"{N(r.local)} vs {N(r.visita)}", st["cell"]),
                 pct(r.final_1), pct(r.final_X), pct(r.final_2), r.marcador_probable, f"{r.goles_esp:.1f}", pct(r.over25), pct(r.btts)])
story.append(tbl(rows, [1.1 * cm, 1.0 * cm, 1.1 * cm, 5.6 * cm, 1.0 * cm, 1.0 * cm, 1.0 * cm, 1.5 * cm, 1.1 * cm, 1.1 * cm, 1.1 * cm], align_right_from=4))
story += [Spacer(1, 6), IMG(SAL / "partidos_final.png", 16.5 * cm)]

# ------------------------------------------------------------------ modelo vs mercado
story += [PageBreak(), P("Modelo contra mercado", "h2"),
          P("E = ensamble (promedio ponderado de los cinco modelos). M = mercado (cuotas sin margen). Si faltaba una cuota, esa probabilidad se tomó del modelo y las otras dos conservan la proporción del mercado. La columna Dif. es local del ensamble menos local del mercado.", "small")]
rows = [["Partido", "E1", "EX", "E2", "M1", "MX", "M2", "Dif", "Cuotas", "Fuente"]]
FALTA = {"completo": "completas", "imputado (1 cuota)": "falta 1", "imputado (2 cuotas)": "faltan 2"}
for r in pred.itertuples():
    rows.append([Paragraph(f"{N(r.local)} vs {N(r.visita)}", st["cell"]), pct(r.ensamble_1), pct(r.ensamble_X), pct(r.ensamble_2),
                 pct(r.mercado_1), pct(r.mercado_X), pct(r.mercado_2), f"{(r.ensamble_1 - r.mercado_1) * 100:+.0f}",
                 FALTA.get(r.cuotas, r.cuotas), Paragraph(str(r.fuente_cuotas), st["cell"])])
story.append(tbl(rows, [4.3 * cm, 1.05 * cm, 1.05 * cm, 1.05 * cm, 1.15 * cm, 1.15 * cm, 1.15 * cm, 0.9 * cm, 1.6 * cm, 3.6 * cm]))
story += [Spacer(1, 4), IMG(SAL / "partidos_modelo.png", 13 * cm)]

notas = [
    ("Barcelona vs Aston Villa", "Es el mayor desacuerdo. El ensamble da 61% al Barça y el mercado entre 72% y 78% (Kalshi 78%). El modelo ve una diferencia de unos 100 puntos Elo; el mercado actúa como si fueran 250. El modelo no tiene la forma de liga de octubre y un agregador ubica al Villa 12° en la Premier (dato sin confirmar). El valor esperado de +100% en el Villa es casi seguro un error del modelo, no una oportunidad."),
    ("Viking vs Sabah", "Baja confianza. Sabah no tiene historial en los datos: su fuerza sale de un Elo por país más tres partidos. El modelo lo ve parejo (47% Viking); Kalshi da 66% al Viking. Ve este partido como una incógnita."),
    ("Villarreal vs PSG", "PSG llega sin Dembélé, Kvaratskhelia, Marquinhos y Nuno Mendes (confianza media). Con esas bajas el modelo baja al PSG de 61% a 56%. Es el partido con más goles esperados de la jornada y la línea del mercado está en 3.5."),
    ("Atlético vs Bayern", "Sin Luis Díaz y con Olise y Neuer en duda, el Bayern pasa de 52% a 49% en el ensamble. Coincide con Polymarket (50%). El Atlético solo recibió 3 goles en 3 partidos; el Bayern recibió 5."),
    ("Feyenoord vs Inter", "La baja de Lautaro y la sanción de Bastoni salen de una sola fuente que mezcla jugadores de otros equipos. Si Lautaro juega, el Inter sube unos 3 puntos."),
    ("Dortmund vs Betis", "El Betis tiene 9 puntos con tres victorias por un gol (diferencia +3). Ese tipo de racha suele regresar a la media. Modelo y mercado coinciden en 54% para el Dortmund."),
    ("Porto vs Napoli", "Porto suma 0 puntos y 2 goles a favor, pero su Elo y su liga lo sostienen. Napoli sin De Bruyne y, según Covers, con siete partidos de Champions fuera de casa sin ganar. Es el partido con menos goles esperados."),
    ("PSV vs Club Brujas", "Los partidos de Champions del PSV suman 2 goles en 3 juegos, pero Dixon-Coles espera casi 4 por su producción en la Eredivisie. Desconfía del over/under aquí. Covers pronostica empate."),
    ("Galatasaray vs Stuttgart", "Las cuotas cargadas tienen 20 días y otra fuente da 1.62 al Galatasaray. Si esa es la cuota real, el mercado ve al Gala bastante más favorito que el modelo (40%)."),
    ("Shakhtar vs Sporting", "El Shakhtar juega fuera de Ucrania; se le dio 40% de la ventaja normal de local. Modelo y mercado coinciden (47% Sporting)."),
]
story += [P("Notas por partido", "h3")]
for t, txt in notas:
    story.append(P(f"<b>{t}.</b> {txt}"))

# ------------------------------------------------------------------ marcadores y bajas
story += [PageBreak(), P("Marcadores más probables (Monte Carlo, 100,000 simulaciones)", "h2")]
rows = [["Partido", "1°", "2°", "3°", "4°", "5°"]]
for r in pred.itertuples():
    tops = list(marc[f"{r.local} vs {r.visita}"].items())
    rows.append([Paragraph(f"{N(r.local)} vs {N(r.visita)}", st["cell"])] + [f"{k} ({v:.0%})" for k, v in tops])
story.append(tbl(rows, [5.5 * cm] + [2.2 * cm] * 5))
story += [P("Ningún marcador exacto pasa de 13%. Apostar a un marcador exacto pierde la gran mayoría de las veces aunque elijas el más probable.", "small"),
          P("Ajustes por bajas", "h2"),
          P("Cada baja resta puntos Elo al equipo: titular de ataque de élite 15 a 20, defensa titular 8 a 12, portero 10 a 15, suplente 3 a 5. El ajuste mueve el Elo de los modelos de regresión y las tasas de gol de Dixon-Coles. Las listas salen de previas publicadas el 2 y 3 de noviembre; confirma con las alineaciones oficiales, que salen una hora antes.", "small")]
rows = [["Equipo", "Elo", "Bajas consideradas", "Ens. sin bajas", "Ens. con bajas"]]
src = Path(__file__).resolve().parents[1] / "src" / "config_jornada.py"
comentarios = {}
for line in src.read_text(encoding="utf-8").splitlines():
    if line.strip().startswith('"') and "#" in line and ":" in line and line.strip().split(":")[0].strip('" ') in AJUSTES_BAJAS:
        comentarios[line.strip().split(":")[0].strip('" ')] = line.split("#", 1)[1].strip()
for team, d in AJUSTES_BAJAS.items():
    r = pred[(pred.local == team) | (pred.visita == team)].iloc[0]
    sin, con = (r.ens_1_sin_bajas, r.ensamble_1) if r.local == team else (r.ens_2_sin_bajas, r.ensamble_2)
    rows.append([N(team), f"{d}", Paragraph(comentarios.get(team, ""), st["cell"]), pct(sin), pct(con)])
story.append(tbl(rows, [3.2 * cm, 1.0 * cm, 8.8 * cm, 2.0 * cm, 2.0 * cm]))
story.append(P("Las dos últimas columnas son la probabilidad de victoria del equipo según el ensamble, antes y después del ajuste. La probabilidad final cambia menos porque 75% viene del mercado, que ya descuenta las bajas.", "small"))

# ------------------------------------------------------------------ estadísticas
E = est.copy()
E["nombre"] = [" vs ".join(N(t) for t in p.split(" vs ")) for p in E.partido]
story += [PageBreak(), P("Estadísticas del partido", "h2"),
          P("Valores esperados del Monte Carlo (100,000 simulaciones por partido). Córners y tarjetas aparecen como local + visita. Tarjetas = amarillas + rojas. La última columna dice cuántos de los últimos 20 partidos de liga con estadísticas tiene cada equipo; con 0 el perfil del equipo es el promedio y solo cuenta la diferencia de Elo.", "small")]
rows = [["Partido", "Goles", "Córners", "Tarjetas", "P(roja)", "Faltas", "Tiros", "A puerta", "F. juego", "Árbitro", "Datos"]]
for d in E.to_dict("records"):
    r = pd.Series(d)
    rows.append([Paragraph(r.nombre, st["cell"]), f"{r.goles_total:.1f}", f"{r.corners_local:.1f}+{r.corners_visita:.1f}={r.corners_total:.1f}",
                 f"{r.tarjetas_local:.1f}+{r.tarjetas_visita:.1f}={r.tarjetas_total:.1f}", pct(r.p_roja), f"{r.fouls_total:.0f}",
                 f"{r.shots_total:.0f}", f"{r.sot_total:.1f}", f"{r.offsides_total:.1f}", Paragraph(str(r.arbitro), st["cell"]), r.partidos_con_estadisticas])
story.append(tbl(rows, [3.3 * cm, 1.0 * cm, 2.2 * cm, 2.2 * cm, 1.1 * cm, 1.05 * cm, 1.0 * cm, 1.15 * cm, 1.15 * cm, 2.65 * cm, 1.0 * cm]))
story += [Spacer(1, 6), IMG(SAL / "estadisticas.png", 16 * cm)]

story += [PageBreak(), P("Goles: líneas, por equipo y primer tiempo", "h3")]
rows = [["Partido", "O0.5", "O1.5", "O2.5", "O3.5", "O4.5", "BTTS", "Local O1.5", "Visita O1.5", "1T O0.5", "1T O1.5", "1X", "X2"]]
for d in E.to_dict("records"):
    rows.append([Paragraph(d["nombre"], st["cell"])] + [pct(d[k]) for k in ["goles_O0.5", "goles_O1.5", "goles_O2.5", "goles_O3.5", "goles_O4.5", "btts",
                 "local_O1.5", "visita_O1.5", "ht_O0.5", "ht_O1.5", "doble_1X", "doble_X2"]])
story.append(tbl(rows, [3.9 * cm] + [1.08 * cm] * 12, align_right_from=1))
story += [P("Córners", "h3")]
rows = [["Partido", "O7.5", "O8.5", "O9.5", "O10.5", "O11.5", "O12.5", "Local O4.5", "Visita O4.5", "Más córners local", "Rango 80%"]]
for d in E.to_dict("records"):
    rows.append([Paragraph(d["nombre"], st["cell"])] + [pct(d[k]) for k in ["corners_O7.5", "corners_O8.5", "corners_O9.5", "corners_O10.5", "corners_O11.5",
                 "corners_O12.5", "corners_local_O4.5", "corners_visita_O4.5", "mas_corners_local"]] + [d["corners_p10_p90"]])
story.append(tbl(rows, [3.9 * cm] + [1.1 * cm] * 6 + [1.4 * cm, 1.4 * cm, 1.6 * cm, 1.3 * cm], align_right_from=1))

story += [PageBreak(), P("Tarjetas", "h3")]
rows = [["Partido", "O2.5", "O3.5", "O4.5", "O5.5", "O6.5", "P(roja)", "Puntos (10/25)", "Más tarjetas local", "Árbitro"]]
for d in E.to_dict("records"):
    rows.append([Paragraph(d["nombre"], st["cell"])] + [pct(d[k]) for k in ["tarjetas_O2.5", "tarjetas_O3.5", "tarjetas_O4.5", "tarjetas_O5.5", "tarjetas_O6.5", "p_roja"]]
                + [f"{d['puntos_tarjeta']:.0f}", pct(d["mas_tarjetas_local"]), Paragraph(f"{d['arbitro']} (x{d['factor_arbitro']:.2f})", st["cell"])])
story.append(tbl(rows, [3.9 * cm] + [1.05 * cm] * 6 + [1.5 * cm, 1.6 * cm, 3.2 * cm], align_right_from=1))
story += [PageBreak(), P("Faltas, tiros a puerta y fueras de juego", "h3")]
rows = [["Partido", "Faltas O21.5", "Faltas O23.5", "A puerta O7.5", "A puerta O8.5", "A puerta O9.5", "F. de juego O2.5", "F. de juego O3.5"]]
for d in E.to_dict("records"):
    rows.append([Paragraph(d["nombre"], st["cell"])] + [pct(d[k]) for k in ["fouls_O21.5", "fouls_O23.5", "sot_O7.5", "sot_O8.5", "sot_O9.5", "offsides_O2.5", "offsides_O3.5"]])
story.append(tbl(rows, [4.2 * cm] + [1.85 * cm] * 7, align_right_from=1))
story.append(P("Fuera de juego: no hay datos libres por partido, así que es una estimación con el promedio de la Champions (3.1) repartido por volumen de tiros. No se pudo validar.", "small"))

story += [PageBreak(), P("Backtest de las estadísticas (misma regla 3 + 2)", "h2"),
          P("Entrenado en 2021-22 a 2023-24 y evaluado en 2024-25 y 2025-26, en las 11 ligas con estadísticas. La comparación es contra usar solo el promedio de la liga. Correlación = qué tanto se mueven juntos lo esperado y lo real (1 sería perfecto). No hay cuotas históricas de córners o tarjetas, así que no se pudo comparar contra el mercado.")]
rows = [["Estadística", "Línea", "Partidos", "Promedio real", "Error modelo", "Error promedio liga", "Correlación", "Acierto O/U modelo", "Acierto O/U liga"]]
for d in bte.to_dict("records"):
    rows.append([d["estadística"], f"{d['línea']}", f"{d['partidos']:,}", f"{d['promedio real']:.2f}", f"{d['error abs. modelo']:.2f}",
                 f"{d['error abs. promedio liga']:.2f}", f"{d['correlación']:.2f}", pct(d["acierto O/U modelo"]), pct(d["acierto O/U liga"])])
story.append(tbl(rows, [4.2 * cm, 1.1 * cm, 1.4 * cm, 1.7 * cm, 1.6 * cm, 1.9 * cm, 1.6 * cm, 1.7 * cm, 1.6 * cm], align_right_from=1))
story += [P("Error = diferencia absoluta media entre el total esperado y el real.", "small"),
          P("<b>Lectura.</b> Faltas y tiros sí tienen señal: el estilo de cada equipo pesa y el modelo le saca entre 2 y 4 puntos de acierto al promedio. Córners y tarjetas casi no: la correlación con lo real es de 0.17 y 0.25, y el acierto en la línea más común queda a 1 punto o menos del promedio. En un partido concreto un córner o una tarjeta depende de jugadas sueltas y del árbitro. Las casas ponen la línea cerca de la media y cobran margen, así que apostar córners o tarjetas con este modelo no tiene ventaja demostrada."),
          P("<b>Goles al descanso.</b> Se estiman como 46% de la tasa de gol del local y 45% de la del visitante (proporción medida en los datos). El acierto en over 0.5 y 1.5 al descanso es igual al de usar el promedio."),
          P("<b>Cómo se calcula.</b> Para cada estadística: promedio de la competición por perfil del equipo (lo que produce en su liga respecto al promedio de esa liga) por lo que permite el rival, ajustado por la diferencia de Elo. Los coeficientes salen de una regresión de Poisson en 11 ligas. La dispersión es binomial negativa con un factor común del partido, porque los córners y las tarjetas de ambos equipos suben y bajan juntos. El árbitro multiplica las tarjetas cuando hubo un promedio publicado: Michael Oliver 0.90 (Porto vs Napoli) y Chris Kavanagh 1.04 (Galatasaray vs Stuttgart).")]

# ------------------------------------------------------------------ parlays
story += [PageBreak(), P("Parlays sugeridos", "h2"),
          P("Cada parlay usa una pata por partido, así la probabilidad es el producto de las patas. La cuota justa es 1 entre la probabilidad: si la casa paga menos, el modelo espera perder dinero con esa apuesta. Pide 5% a 10% más que la cuota justa, porque el modelo también falla."),
          P("<b>Advertencias.</b> El margen de la casa se acumula con cada pata (cerca de 20% en un parlay de 4). En los moneylines el modelo usa sobre todo la probabilidad del mercado, así que a las cuotas actuales esos parlays tienen valor esperado negativo. En tiros y córners no hay cuotas históricas para comprobar si el modelo le gana a la casa. Varios parlays comparten partidos (Barcelona, Arsenal, PSG): si uno falla, fallan varios. Apuesta poco en cada uno, por ejemplo 0.5% a 1% de tu banca, y no juegues todos."),
          P("Viking vs Sabah queda fuera por falta de datos de Sabah, y PSV vs Club Brujas queda fuera de los parlays de goles.", "small")]
for nombre, g in par.groupby("parlay", sort=False):
    pr, cj, cmk = g.prob_parlay.iloc[0], g.cuota_justa_parlay.iloc[0], g.cuota_mercado_parlay.iloc[0]
    extra = f"; cuota de mercado ~{cmk:.2f}, valor esperado {pr * cmk - 1:+.0%}" if pd.notna(cmk) else ""
    rows = [["Partido", "Selección", "Prob.", "Cuota justa"]]
    for r in g.itertuples():
        rows.append([Paragraph(" vs ".join(N(t) for t in r.partido.split(" vs ")), st["cell"]),
                     Paragraph(r.seleccion, st["cell"]), pct(r.prob_pata), f"{r.cuota_justa_pata:.2f}"])
    story.append(KeepTogether([P(f"{nombre}: probabilidad {pr:.0%}, cuota justa {cj:.2f}{extra}", "h3"),
                               tbl(rows, [5.2 * cm, 7.6 * cm, 1.6 * cm, 2.0 * cm], align_right_from=2)]))

# ------------------------------------------------------------------ tendencias
story += [PageBreak(), P("Tendencias de la Champions 2026-27", "h2"),
          P("Las jornadas 1 a 3 dejaron 4.09 goles por partido, 74% de partidos con más de 2.5 goles, 67% con ambos anotando, 59% de victorias locales y solo 11% de empates. En 2024-25 y 2025-26 la media fue 3.36 goles, 65% over 2.5, 51% local y 16% empate. Con 54 partidos el promedio de goles todavía es inestable: espera que baje hacia 3.3 o 3.5 en las jornadas siguientes. El modelo ya da más peso a lo reciente, pero no todo."),
          ]
t = tabla.rename(columns={"over25_%": "over", "btts_%": "btts"})
rows = [["Equipo", "PJ", "G", "E", "P", "GF", "GC", "DG", "Pts", "Over 2.5", "BTTS"]]
for r in t.itertuples():
    rows.append([N(r.equipo), r.PJ, r.G, r.E, r.P, r.GF, r.GC, r.DG, r.Pts, f"{r.over:.0f}%", f"{r.btts:.0f}%"])
story.append(tbl(rows, [4.2 * cm] + [1.0 * cm] * 8 + [1.5 * cm, 1.3 * cm], align_right_from=1))

# ------------------------------------------------------------------ backtest
story += [PageBreak(), P("El método de tu amigo: entrenar con 3 años, probar con 2", "h2"),
          P("<b>Qué es.</b> Se llama validación fuera de muestra o backtest temporal. El modelo aprende con 2021-22, 2022-23 y 2023-24. Luego predice los partidos de 2024-25 y 2025-26 como si fueran futuros, y al final se comparan sus predicciones con los resultados reales. Es la única forma honesta de saber qué tan bien predice, porque si evalúas con los partidos que usó para aprender, el modelo ya conoce las respuestas y el acierto sale inflado."),
          P("<b>El orden importa.</b> No se puede mezclar al azar partidos de distintas temporadas, como se hace en otros problemas. Si el modelo ve partidos de 2025 al entrenar y luego predice 2024, usa información del futuro. Por eso el corte es por fecha."),
          P("<b>Dos versiones.</b> En la versión congelada (la literal) Elo, ataque y defensa se fijan el 1 de julio de 2024 y no cambian en dos años; un equipo que subió o bajó de nivel no se entera. En la versión walk-forward la estructura y los coeficientes se fijan con las 3 temporadas, pero antes de cada partido se usan los resultados ya jugados. Ningún resultado futuro entra, y es lo que harás cada semana en la vida real. Las dos versiones respetan la idea de tu amigo; la segunda mide mejor lo que vas a vivir."),
          P("<b>Por qué la tasa de acierto no basta.</b> Solo mira si el favorito ganó. Un modelo que dice 34% y otro que dice 80% cuentan igual si gana el local. Por eso se agregan log loss, Brier y RPS, que castigan estar muy seguro y fallar, y se compara contra las cuotas. Otro detalle: el empate ocurre en 25% de los partidos, pero casi nunca es la opción más probable, así que ningún modelo pasa de 55% a 60% de acierto en 1X2."),
          ]
rows = [["Modelo", "UCL WF", "UCL cong.", "Top 5 WF", "Top 5 cong.", "LL UCL WF", "LL top 5 WF"]]
for mod in ["Dixon-Coles", "Regresión logística (Elo)", "Regresión lineal (dif. goles)", "Regresión de Poisson (GLM)", "XGBoost", "Ensamble"]:
    rows.append([mod, pct(m("Champions League", mod, "walk-forward", "accuracy")) if True else "",
                 pct(m("Champions League", mod, "congelado", "accuracy")), pct(m("Top 5 ligas", mod, "walk-forward", "accuracy")),
                 pct(m("Top 5 ligas", mod, "congelado", "accuracy")), f'{m("Champions League", mod, "walk-forward", "log_loss"):.3f}',
                 f'{m("Top 5 ligas", mod, "walk-forward", "log_loss"):.3f}'])
fh = rep[rep.modelo == "Frecuencias históricas"]
rows.append(["Sin modelo (frecuencias)", pct(fh[fh.subconjunto == "Champions League"].accuracy.iloc[0]), "", pct(fh[fh.subconjunto == "Top 5 ligas"].accuracy.iloc[0]), "",
             f'{fh[fh.subconjunto == "Champions League"].log_loss.iloc[0]:.3f}', f'{fh[fh.subconjunto == "Top 5 ligas"].log_loss.iloc[0]:.3f}'])
rows.append(["Mercado Bet365 (ligas)", "", "", pct(acc_mk), "", "", f"{ll_mk:.3f}"])
story.append(tbl(rows, [4.8 * cm, 1.9 * cm, 2.0 * cm, 1.7 * cm, 1.8 * cm, 2.3 * cm, 2.0 * cm], align_right_from=1))
n_ucl = int(rep[(rep.subconjunto == "Champions League")].n.iloc[0])
n_top = int(rep[(rep.subconjunto == "Top 5 ligas")].n.iloc[0])
story += [P(f"Las primeras cuatro columnas son tasa de acierto. UCL = Champions; WF = walk-forward; cong. = congelado; LL = log loss (menor es mejor; azar = 1.099). Champions: {n_ucl} partidos; top 5 ligas: {n_top:,} partidos. La fila del mercado usa los partidos de liga con cuotas, que no son exactamente los mismos.", "small"),
          IMG(SAL / "acierto_champions.png", 15 * cm),
          IMG(SAL / "acierto_top.png", 15 * cm)]

story += [PageBreak(), P("Calibración y confianza", "h2"),
          P("Un modelo calibrado cumple lo que promete: cuando dice 70%, el favorito gana cerca de 70% de las veces. El ensamble está bien calibrado. La tabla sirve para leer las predicciones de esta jornada: un favorito al 55% pierde o empata casi la mitad de las veces.")]
rows = [["Confianza del favorito", "Partidos", "Acierto real", "Probabilidad media"]]
for r in conf.itertuples():
    rows.append([r._1, f"{r.partidos:,}", pct(r._3), pct(r._4)])
story.append(tbl(rows, [4.5 * cm, 2.5 * cm, 2.5 * cm, 3.2 * cm], align_right_from=1))
story += [Spacer(1, 6), IMG(SAL / "calibracion.png", 10.5 * cm),
          P("¿Sirve para over/under y ambos anotan?", "h3")]
rows = [["Mercado", "Partidos", "Acierto modelo", "Acierto Bet365"]]
for r in goles.itertuples():
    rows.append([r.mercado, f"{r.partidos:,}", pct(r._3), "" if pd.isna(r._4) else pct(r._4)])
story.append(tbl(rows, [5 * cm, 2.5 * cm, 3 * cm, 3 * cm], align_right_from=1))
story.append(P("En over 2.5 de ligas el modelo queda un punto por debajo del mercado. El 68% en Champions se explica sobre todo porque la mayoría de esos partidos tienen más de 2.5 goles.", "small"))

story += [PageBreak(), P("Apuestas simuladas contra Bet365", "h2"),
          P("Simulación en los partidos de liga de 2024-25 y 2025-26: 1 unidad cada vez que la probabilidad del modelo por la cuota supera 1 más la ventaja pedida. Se compara con apostar siempre al favorito del mercado.")]
rows = [["Estrategia", "Apuestas", "Aciertos", "Beneficio", "ROI", "Rango 90% del ROI"]]
for r in roi.itertuples():
    lo, hi = [float(v) for v in re.findall(r"-?\d+\.\d+(?:e-?\d+)?", str(r.roi_ic90))][:2]
    rows.append([r.estrategia, f"{r.apuestas:,}", f"{r.aciertos:,}", f"{r.beneficio_u:+.0f} u", f"{r.roi:.1%}", f"{lo:.1%} a {hi:.1%}"])
story.append(tbl(rows, [5 * cm, 1.8 * cm, 1.8 * cm, 2 * cm, 1.6 * cm, 3.2 * cm], align_right_from=1))
story += [Spacer(1, 6), IMG(SAL / "roi.png", 15 * cm),
          P("Las tres estrategias pierden. Las del modelo pierden más que apostar al favorito, porque cuando el modelo y la casa no coinciden, la casa suele tener razón: tiene información que el modelo no ve (alineaciones, lesiones de última hora, dinero de apostadores profesionales). El margen de la casa, entre 5% y 8%, se come cualquier ventaja pequeña.")]

# ------------------------------------------------------------------ modelos
story += [PageBreak(), P("Cómo funciona cada pieza", "h2")]
piezas = [
    ("Elo", "Cada equipo tiene un número de fuerza. Arranca con el Elo de ClubElo y después de cada partido sube o baja según el resultado esperado y el margen de goles. Los partidos europeos mueven más (K=30 contra 20) porque son los que conectan las ligas."),
    ("Dixon-Coles", "Supone que los goles de cada equipo siguen una distribución de Poisson cuya media depende de su ataque, la defensa rival y la localía. Corrige la frecuencia de marcadores bajos (0-0, 1-0, 0-1, 1-1). Los partidos viejos pesan menos: un partido de hace un año cuenta la mitad. Los equipos con pocos datos se acercan a lo que predice su Elo."),
    ("Regresión logística", "Convierte la diferencia de Elo, la localía y si el partido es europeo en probabilidades de 1, X y 2."),
    ("Regresión lineal", "Predice la diferencia de goles con Elo, forma de los últimos 5 partidos y días de descanso. Supone errores normales para pasar a 1X2. Es la más simple y terminó con peso cero en el ensamble porque no agrega nada a las otras."),
    ("Regresión de Poisson", "Dos regresiones, una para los goles del local y otra para los del visitante, con las mismas variables que la lineal."),
    ("XGBoost", "Cientos de árboles de decisión pequeños que combinan Elo, salidas de Dixon-Coles, forma y descanso. Puede captar relaciones no lineales, pero con datos de fútbol el beneficio sobre los modelos clásicos es pequeño."),
    ("Ensamble", "Promedio ponderado. Los pesos se eligieron con la temporada 2023-24, que ninguno de los modelos había visto: Dixon-Coles 23%, logística 33%, XGBoost 44%."),
    ("Monte Carlo", "Para cada partido se buscan las tasas de gol que reproducen la probabilidad final. Luego se simulan 100,000 partidos con ruido en esas tasas (10% a 12%) para reflejar que no se conocen con exactitud. De ahí salen marcadores, over/under y ambos anotan."),
]
for t, txt in piezas:
    story.append(P(f"<b>{t}.</b> {txt}"))

story += [P("Límites y críticas", "h2")]
limites = [
    "No le gana al mercado. Es la conclusión principal del backtest y no cambia por agregar más modelos.",
    "Datos con hueco. El espejo de GitHub tiene ligas hasta el 20 de septiembre de 2026 (Noruega y Austria solo hasta diciembre de 2024). Abierto en Colab, el notebook baja datos frescos de football-data.co.uk y el hueco desaparece.",
    "Sin xG ni alineaciones. El modelo solo usa goles y resultados. Los goles esperados (xG) y la alineación real explican mucho de lo que el mercado sabe y el modelo no.",
    "Equipos sin historial. Sabah, Slavia y Slovan dependen de un Elo por país más pocos partidos europeos.",
    "Bajas manuales y fuentes secundarias. Varias listas de lesionados salen de un solo medio y alguna mezcla jugadores de otros equipos. Si un titular juega, el ajuste sobra.",
    "Cuotas desiguales. Algunas son de Polymarket o Kalshi, otras de casas de EE. UU. y otras tienen 20 días. Antes de decidir revisa la cuota real del momento.",
    "Córners y tarjetas casi no se predicen mejor que con el promedio de la liga (ver backtest de estadísticas). Las estadísticas de Champions salen de perfiles de liga escalados al promedio de la Champions, porque no hay datos libres de córners o tarjetas por partido de Champions.",
    "Sin perfil de estadísticas para Bodø/Glimt, Viking, LASK, Shakhtar, Slavia, Slovan y Sabah: sus ligas no tienen esos datos en las fuentes libres. Fuera de juego: estimación sin validar.",
    "Muestra chica en Champions. 378 partidos de prueba dan un margen de error de unos 5 puntos en la tasa de acierto. La diferencia entre modelos en Champions no es significativa.",
]
for txt in limites:
    story.append(P(f"• {txt}"))

story += [P("Cómo usarlo cada semana", "h2"),
          P("1. Abre el notebook en Colab. 2. En la celda Configuración agrega los resultados nuevos de Champions a UCL_2026_27, cambia PARTIDOS (equipos, fecha, cuotas), AJUSTES_BAJAS y ARBITROS. 3. Ejecuta todo. Para partidos de liga del fin de semana usa la sección 6: baja el calendario y las cuotas de football-data.co.uk y predice todo con el mismo modelo."),
          P("Fuentes", "h2"),
          P("Datos históricos: football-data.co.uk (vía github.com/xgabora/Club-Football-Match-Data-2000-2025), ClubElo, openfootball (football.json y champions-league). Resultados, cuotas y bajas de la temporada 2026-27: uefa.com, nbcsports.com, sport-minute.com, covers.com, rotowire.com, squawka.com, rg.org, oddschecker.com, tips.gg, dimers.com, khelnow.com, thisisanfield.com, sportsgambler.com, starting11.com, vavel.com. Promedios de estadísticas: performanceodds.com, footystats.org. Árbitros: uefa.com, law5-theref.blogspot.com, foot-africa.com, playmakerstats.com. Todas consultadas el 3 de noviembre de 2026.", "small")]


def footer(c, d):
    c.saveState()
    c.setFont("DV", 7)
    c.setFillColor(MUTED)
    c.drawString(1.6 * cm, 1.0 * cm, "Modelo Champions jornada 4 · uso informativo, no es consejo de apuesta")
    c.drawRightString(A4[0] - 1.6 * cm, 1.0 * cm, f"{d.page}")
    c.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.5 * cm, bottomMargin=1.6 * cm,
                        title="Champions League jornada 4: predicciones y backtest", author="Modelo de predicción")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("PDF:", OUT)
