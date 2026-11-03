# %% [config] Configuración de la jornada (EDITA ESTA CELDA ANTES DE CADA JORNADA)
# 1) Resultados de la Champions 2026-27 ya jugados. Agrega filas después de cada jornada.
#    Columnas: date, home, hc (país local), away, ac (país visita), hg, ag, home_factor (1 = localía normal)
UCL_2026_27 = """date,home,hc,away,ac,hg,ag,home_factor
2026-09-08,AEK,GRE,LASK,AUT,1,0,1
2026-09-08,Club Brugge,BEL,Aston Villa,ENG,2,3,1
2026-09-08,Dortmund,GER,Villarreal,ESP,3,2,1
2026-09-08,Porto,POR,Man City,ENG,0,2,1
2026-09-08,Lille,FRA,Betis,ESP,2,3,1
2026-09-08,Real Madrid,ESP,Inter,ITA,2,1,1
2026-09-09,Barcelona,ESP,Feyenoord,NED,5,1,1
2026-09-09,Stuttgart,GER,Viking,NOR,3,1,1
2026-09-09,Liverpool,ENG,Ath Madrid,ESP,2,1,1
2026-09-09,Paris SG,FRA,Slovan Bratislava,SVK,6,1,1
2026-09-09,Sp Lisbon,POR,Galatasaray,TUR,3,1,1
2026-09-09,Napoli,ITA,Arsenal,ENG,0,1,1
2026-09-10,Fenerbahce,TUR,Roma,ITA,1,1,1
2026-09-10,PSV Eindhoven,NED,Shakhtar Donetsk,UKR,1,1,1
2026-09-10,Como,ITA,RB Leipzig,GER,4,1,1
2026-09-10,Bayern Munich,GER,Bodo/Glimt,NOR,5,0,1
2026-09-10,Man United,ENG,Sabah,AZE,4,0,1
2026-09-10,Slavia Praha,CZE,Lens,FRA,2,3,1
2026-10-13,Lens,FRA,Sp Lisbon,POR,0,2,1
2026-10-13,Sabah,AZE,Slavia Praha,CZE,2,0,1
2026-10-13,Arsenal,ENG,Lille,FRA,3,0,1
2026-10-13,Ath Madrid,ESP,Man United,ENG,2,0,1
2026-10-13,Galatasaray,TUR,Barcelona,ESP,1,4,1
2026-10-13,Inter,ITA,Club Brugge,BEL,3,4,1
2026-10-13,RB Leipzig,GER,PSV Eindhoven,NED,1,0,1
2026-10-13,Viking,NOR,Bayern Munich,GER,3,3,1
2026-10-13,Villarreal,ESP,Napoli,ITA,3,1,1
2026-10-14,Feyenoord,NED,Como,ITA,3,2,1
2026-10-14,LASK,AUT,Liverpool,ENG,3,6,1
2026-10-14,Roma,ITA,Real Madrid,ESP,3,4,1
2026-10-14,Aston Villa,ENG,Fenerbahce,TUR,6,0,1
2026-10-14,Shakhtar Donetsk,UKR,AEK,GRE,3,1,0.4
2026-10-14,Bodo/Glimt,NOR,Dortmund,GER,1,0,1
2026-10-14,Man City,ENG,Paris SG,FRA,2,4,1
2026-10-14,Betis,ESP,Porto,POR,3,2,1
2026-10-14,Slovan Bratislava,SVK,Stuttgart,GER,0,3,1
2026-10-20,Fenerbahce,TUR,Slavia Praha,CZE,2,2,1
2026-10-20,Sabah,AZE,Dortmund,GER,1,2,1
2026-10-20,Roma,ITA,Slovan Bratislava,SVK,4,0,1
2026-10-20,Porto,POR,PSV Eindhoven,NED,0,1,1
2026-10-20,Liverpool,ENG,Villarreal,ESP,4,3,1
2026-10-20,Man City,ENG,AEK,GRE,5,1,1
2026-10-20,Napoli,ITA,Bodo/Glimt,NOR,4,3,1
2026-10-20,Paris SG,FRA,Barcelona,ESP,4,2,1
2026-10-20,Stuttgart,GER,Ath Madrid,ESP,1,1,1
2026-10-21,Como,ITA,Man United,ENG,4,1,1
2026-10-21,Lille,FRA,Galatasaray,TUR,2,4,1
2026-10-21,Aston Villa,ENG,Viking,NOR,3,1,1
2026-10-21,Club Brugge,BEL,Lens,FRA,3,0,1
2026-10-21,Bayern Munich,GER,Arsenal,ENG,2,2,1
2026-10-21,Inter,ITA,Shakhtar Donetsk,UKR,1,0,1
2026-10-21,Real Madrid,ESP,RB Leipzig,GER,4,1,1
2026-10-21,Betis,ESP,Feyenoord,NED,1,0,1
2026-10-21,Sp Lisbon,POR,LASK,AUT,2,3,1
"""

# 2) Partidos a predecir. Cuotas decimales (momios europeos). NaN = no encontrada.
#    factor_localia: 1 = estadio propio; 0.4 = Shakhtar juega lejos de Ucrania; 0 = cancha neutral.
#    fuente_cuotas: de dónde salió cada línea (revisa y actualiza antes del partido).
NaN = float("nan")
PARTIDOS = [
    # fecha, hora CET, local, visita, factor_localia, cuota 1, X, 2, fuente
    ("2026-11-03", "18:45", "Shakhtar Donetsk", "Sp Lisbon", 0.4, 3.60, 3.80, 2.05, "Oddschecker (hace ~20 días)"),
    ("2026-11-03", "18:45", "Galatasaray", "Stuttgart", 1.0, 2.20, 4.00, 3.00, "Oddschecker (hace ~20 días)"),
    ("2026-11-03", "21:00", "Ath Madrid", "Bayern Munich", 1.0, 3.33, 4.35, 2.00, "Polymarket 30/23/50 c"),
    ("2026-11-03", "21:00", "Barcelona", "Aston Villa", 1.0, 1.27, NaN, 10.50, "1xBet / LetsBetMD"),
    ("2026-11-03", "21:00", "Feyenoord", "Inter", 1.0, 4.51, 4.33, 1.75, "1xBet (rg.org) + Oddschecker"),
    ("2026-11-03", "21:00", "Bodo/Glimt", "Lille", 1.0, 1.92, 4.10, 4.00, "1xBet + Oddschecker"),
    ("2026-11-03", "21:00", "LASK", "Slovan Bratislava", 1.0, 1.43, 5.00, 6.67, "Oddschecker / rg.org"),
    ("2026-11-03", "21:00", "Man United", "Roma", 1.0, 2.375, 3.95, NaN, "bet365 (Squawka) + 1xBet"),
    ("2026-11-03", "21:00", "Villarreal", "Paris SG", 1.0, NaN, 4.88, 1.60, "RotoWire / 1xBet"),
    ("2026-11-04", "18:45", "Fenerbahce", "Liverpool", 1.0, 5.00, 4.60, 1.62, "Oddschecker / Covers"),
    ("2026-11-04", "18:45", "AEK", "Real Madrid", 1.0, 8.75, NaN, 1.30, "casas EE. UU. (-333/+775)"),
    ("2026-11-04", "21:00", "Dortmund", "Betis", 1.0, 1.75, NaN, 4.33, "Oddschecker"),
    ("2026-11-04", "21:00", "Porto", "Napoli", 1.0, 2.05, NaN, 3.70, "Oddschecker"),
    ("2026-11-04", "21:00", "PSV Eindhoven", "Club Brugge", 1.0, 2.10, NaN, 4.33, "Oddschecker"),
    ("2026-11-04", "21:00", "RB Leipzig", "Man City", 1.0, 5.25, NaN, 1.55, "BetRivers (-182/+425)"),
    ("2026-11-04", "21:00", "Lens", "Como", 1.0, 3.10, NaN, 2.20, "Oddschecker / bet365"),
    ("2026-11-04", "21:00", "Slavia Praha", "Arsenal", 1.0, NaN, NaN, 1.31, "DraftKings (-320)"),
    ("2026-11-04", "21:00", "Viking", "Sabah", 1.0, 1.52, 4.90, NaN, "Kalshi 66% + 1xBet"),
]

# 3) Ajuste por bajas, en puntos Elo (negativo = el equipo pierde fuerza).
#    Guía usada: delantero o mediocampista titular de élite -15 a -20; defensa titular -8 a -12;
#    portero titular -10 a -15; suplente -3 a -5. Se suman y se recortan a -60.
#    Fuente: previas del 2-3 nov 2026 (UEFA, Khelnow, RotoWire, This is Anfield). CONFIRMA CON LAS ALINEACIONES.
AJUSTES_BAJAS = {
    "Paris SG": -55,      # Dembélé, Kvaratskhelia, Marquinhos, Nuno Mendes fuera (confianza media)
    "Barcelona": -25,     # Koundé, Christensen, Eric García fuera; Olmo duda
    "Aston Villa": -12,   # Ruggeri, Wan-Bissaka fuera; Onana duda
    "Bayern Munich": -25, # Luis Díaz fuera; Olise y Neuer en duda
    "Ath Madrid": -5,     # Johnny Cardoso fuera
    "Inter": -25,         # Lautaro fuera, Bastoni sancionado (confianza baja, una sola fuente)
    "Liverpool": -25,     # Ekitiké, Frimpong, Bradley, Leoni fuera; Szoboszlai duda
    "Man City": -8,       # Stones fuera, Aké duda
    "RB Leipzig": -5,     # Marc Guiu fuera
    "Lens": -20,          # Edouard, Sima, Ganiou fuera
    "Napoli": -12,        # De Bruyne lesionado
    "Sp Lisbon": -12,     # Debast, Nuno Santos fuera; Zalazar duda
    "Shakhtar Donetsk": -4,  # Marlon fuera
    "Fenerbahce": -12,    # Asensio fuera; Oppong duda
    "Dortmund": -5,       # Emre Can fuera
}

# 4) Promedios por partido de la Champions (los dos equipos juntos). Se usan como nivel base de cada estadística.
#    Fuentes: PerformanceOdds 2025-26 (tiros 25.74, córners 9.43, faltas 23.24, fueras de juego 3.12, tarjetas 3.99),
#    FootyStats 2026-27 (córners 9.75). Tiros a puerta = 35% de los tiros (proporción de las ligas). Rojas: supuesto.
PROMEDIOS_UCL = {"corners": 9.6, "yellow": 3.87, "red": 0.12, "fouls": 23.2, "shots": 25.7, "sot": 9.0,
                 "offsides": 3.1, "offsides_liga": 3.5}

# 5) Árbitros de la jornada (UEFA y prensa, 2-3 nov 2026). factor_tarjetas multiplica amarillas y rojas
#    (y la mitad del efecto en faltas). Solo se movió de 1.0 cuando hubo un promedio publicado; se encoge 50% hacia 1.
ARBITROS = {
    "Shakhtar Donetsk vs Sp Lisbon": {"arbitro": "Ivan Kružliak (SVK)", "factor_tarjetas": 1.0},
    "Galatasaray vs Stuttgart": {"arbitro": "Chris Kavanagh (ENG)", "factor_tarjetas": 1.04},  # 4.07 amarillas/partido en Premier vs 3.79
    "Ath Madrid vs Bayern Munich": {"arbitro": "François Letexier (FRA)", "factor_tarjetas": 1.0},
    "Barcelona vs Aston Villa": {"arbitro": "Davide Massa (ITA)", "factor_tarjetas": 1.0},
    "Feyenoord vs Inter": {"arbitro": "Glenn Nyberg (SWE)", "factor_tarjetas": 1.0},
    "Bodo/Glimt vs Lille": {"arbitro": "João Pinheiro (POR)", "factor_tarjetas": 1.0},
    "LASK vs Slovan Bratislava": {"arbitro": "Donatas Rumšas (LTU)", "factor_tarjetas": 1.0},
    "Man United vs Roma": {"arbitro": "sin confirmar", "factor_tarjetas": 1.0},
    "Villarreal vs Paris SG": {"arbitro": "Felix Zwayer (GER)", "factor_tarjetas": 1.0},
    "Fenerbahce vs Liverpool": {"arbitro": "Clément Turpin (FRA)", "factor_tarjetas": 1.0},
    "AEK vs Real Madrid": {"arbitro": "Maurizio Mariani (ITA)", "factor_tarjetas": 1.0},
    "Dortmund vs Betis": {"arbitro": "Serdar Gözübüyük (NED)", "factor_tarjetas": 1.0},
    "Porto vs Napoli": {"arbitro": "Michael Oliver (ENG)", "factor_tarjetas": 0.90},  # 3.0-3.1 amarillas/partido en Premier vs 3.79
    "PSV Eindhoven vs Club Brugge": {"arbitro": "Irfan Peljto (BIH)", "factor_tarjetas": 1.0},
    "RB Leipzig vs Man City": {"arbitro": "Marco Guida (ITA)", "factor_tarjetas": 1.0},
    "Lens vs Como": {"arbitro": "Rohit Saggi (NOR)", "factor_tarjetas": 1.0},
    "Slavia Praha vs Arsenal": {"arbitro": "Tobias Stieler (GER)", "factor_tarjetas": 1.0},
    "Viking vs Sabah": {"arbitro": "Sander van der Eijk (NED)", "factor_tarjetas": 1.0},
}

# 6) Parlays. Partidos que no entran a ningún parlay y partidos que no entran a parlays de goles.
EXCLUIR_PARLAYS = ["Viking vs Sabah"]                  # Sabah sin historial: probabilidad poco confiable
EXCLUIR_GOLES = ["PSV Eindhoven vs Club Brugge"]       # Dixon-Coles espera casi 4 goles; el PSV lleva 2 en 3 partidos de Champions
#    Parlay armado a mano: (partido, selección). El texto debe ser igual al de la tabla de patas.
PARLAY_PERSONAL = [
    ("Slavia Praha vs Arsenal", "Gana Arsenal"),
    ("AEK vs Real Madrid", "Real Madrid más de 1.5 goles"),
    ("Ath Madrid vs Bayern Munich", "Bayern Munich más de 11.5 tiros"),
    ("Villarreal vs Paris SG", "Ambos anotan: sí"),
    ("Fenerbahce vs Liverpool", "Más de 2.5 goles"),
]

# 7) Parámetros generales
MODO_DATOS = "auto"          # "auto" intenta football-data.co.uk (fresco) y si falla usa el espejo de GitHub
TEMPORADAS_ENTRENAR = (2021, 2022, 2023)   # 2021-22, 2022-23, 2023-24
TEMPORADAS_PROBAR = (2024, 2025)           # 2024-25, 2025-26
N_SIMULACIONES = 100_000
