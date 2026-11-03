# -*- coding: utf-8 -*-
"""
Modelo de predicción de partidos de fútbol (Champions League y ligas europeas).

Componentes:
  1. Carga de datos con respaldo (football-data.co.uk -> espejo en GitHub -> openfootball)
  2. Elo propio (sembrado con ClubElo) que se actualiza partido a partido
  3. Dixon-Coles con decaimiento temporal y prior Elo para equipos con pocos datos
  4. Regresión logística (Elo), regresión lineal (diferencia de goles) y regresión de Poisson
  5. XGBoost multiclase
  6. Ensamble con pesos optimizados fuera de muestra y mezcla con el mercado
  7. Monte Carlo de marcadores con incertidumbre de parámetros
  8. Backtest: entrenar 3 temporadas, probar 2 (modo congelado y modo walk-forward)

Cada bloque "# %%" se convierte en una celda del notebook.
"""

# %% [codigo] Librerías y configuración general
import os, re, io, json, math, time, warnings, difflib, unicodedata, urllib.request
from datetime import timedelta
import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar, least_squares
from scipy.stats import poisson, norm

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

CACHE_DIR = os.environ.get("FM_CACHE", "datos_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Ligas domésticas usadas (código football-data -> país)
DIVS_MAIN = ["E0", "SP1", "I1", "D1", "F1", "P1", "N1", "B1", "T1", "G1", "SC0"]
DIVS_EXTRA = {"AUT": "AUT", "NOR": "NOR", "SUI": "SWZ", "DEN": "DNK"}  # código interno -> archivo /new/
DIV_COUNTRY = {"E0": "ENG", "SP1": "ESP", "I1": "ITA", "D1": "GER", "F1": "FRA", "P1": "POR",
               "N1": "NED", "B1": "BEL", "T1": "TUR", "G1": "GRE", "SC0": "SCO", "AUT": "AUT",
               "NOR": "NOR", "SUI": "SUI", "DEN": "DEN"}
OF_LEAGUES = {"en.1": "E0", "es.1": "SP1", "de.1": "D1", "it.1": "I1", "fr.1": "F1", "pt.1": "P1", "nl.1": "N1"}

# Elo inicial por país para clubes sin historial (solo se usa si no hay semilla ClubElo)
COUNTRY_DEFAULT_ELO = {"CZE": 1620, "UKR": 1600, "SVK": 1470, "AZE": 1520, "KAZ": 1450, "CYP": 1520,
                       "CRO": 1590, "SRB": 1580, "SUI": 1600, "HUN": 1550, "ISR": 1520, "BUL": 1520,
                       "MDA": 1450, "LVA": 1420, "FIN": 1420, "IRL": 1350, "SWE": 1520, "POL": 1520,
                       "ROU": 1500, "RUS": 1650, "KOS": 1400, "SVN": 1450, "NOR": 1550, "DEN": 1580,
                       "AUT": 1580, "BEL": 1620, "SCO": 1600, "GRE": 1600, "TUR": 1620, "NED": 1650,
                       "POR": 1680, "FRA": 1680, "GER": 1700, "ITA": 1700, "ESP": 1720, "ENG": 1740}

XG_BASE = "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/"
OF_BASE = "https://raw.githubusercontent.com/openfootball/football.json/master/"
OFCL_BASE = "https://raw.githubusercontent.com/openfootball/champions-league/master/"
FD_BASE = "https://www.football-data.co.uk/"


def http_get(url, timeout=40, cache=True):
    """Descarga con caché en disco."""
    fn = os.path.join(CACHE_DIR, re.sub(r"[^A-Za-z0-9._-]", "_", url)[-150:])
    if cache and os.path.exists(fn) and os.path.getsize(fn) > 0:
        with open(fn, "rb") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (modelo-futbol)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if cache:
        with open(fn, "wb") as f:
            f.write(data)
    return data


# %% [codigo] Normalización de nombres de equipos
_TRANS = str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "ı": "i", "İ": "I", "æ": "ae", "ß": "ss",
                        "đ": "d", "Đ": "D", "ð": "d", "þ": "th"})
STOP = {"fc", "cf", "afc", "sc", "sk", "sl", "ssc", "ac", "kv", "bc", "pae", "sfp", "fk", "cp", "sv",
        "tsg", "ogc", "osc", "bsc", "gnk", "pfc", "bk", "kaa", "krc", "rsc", "club", "de", "futbol",
        "calcio", "1907", "1909", "1899", "1846", "04", "29", "sad", "the", "cfc", "as", "rc", "hnk", "nk",
        "ff", "if", "65", "1963"}

ALIAS = {
    "Bayern München": "Bayern Munich", "FC Bayern München": "Bayern Munich",
    "Club Atlético de Madrid": "Ath Madrid", "Atlético Madrid": "Ath Madrid", "Athletic Club": "Ath Bilbao",
    "Sporting Clube de Portugal": "Sp Lisbon", "Sporting CP": "Sp Lisbon",
    "Sporting Braga": "Sp Braga", "Sporting Clube de Braga": "Sp Braga", "SC Braga": "Sp Braga",
    "Sport Lisboa e Benfica": "Benfica", "SL Benfica": "Benfica",
    "FC Internazionale Milano": "Inter", "AC Milan": "Milan",
    "Paris Saint-Germain": "Paris SG", "Paris Saint-Germain FC": "Paris SG",
    "Manchester City": "Man City", "Manchester City FC": "Man City",
    "Manchester United": "Man United", "Manchester United FC": "Man United",
    "PSV": "PSV Eindhoven", "Feyenoord Rotterdam": "Feyenoord", "Club Brugge KV": "Club Brugge",
    "Royale Union Saint-Gilloise": "St. Gilloise", "Union Saint-Gilloise": "St. Gilloise",
    "FK Bodø/Glimt": "Bodo/Glimt", "Bodoe Glimt": "Bodo/Glimt",
    "Olympiakos Piraeus": "Olympiakos", "PAE Olympiakos SFP": "Olympiakos", "Olympiacos": "Olympiakos",
    "AEK Athen": "AEK", "AEK Athens": "AEK", "PAOK Saloniki": "PAOK",
    "Eintracht Frankfurt": "Ein Frankfurt", "Bayer 04 Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen",
    "Bor. Mönchengladbach": "M'gladbach", "Borussia Mönchengladbach": "M'gladbach",
    "1899 Hoffenheim": "Hoffenheim", "TSG 1899 Hoffenheim": "Hoffenheim", "1. FC Union Berlin": "Union Berlin",
    "Real Sociedad de Fútbol": "Sociedad", "Real Sociedad": "Sociedad", "Real Betis": "Betis",
    "Real Betis Balompié": "Betis", "Real Madrid CF": "Real Madrid", "Deportivo Alavés": "Alaves",
    "Lazio Roma": "Lazio", "SS Lazio": "Lazio", "AS Roma": "Roma", "Olympique Lyonnais": "Lyon",
    "Olympique Marseille": "Marseille", "Olympique de Marseille": "Marseille", "Stade Rennais": "Rennes",
    "Stade Rennais FC 1901": "Rennes", "Stade Brestois 29": "Brest", "Racing Club de Lens": "Lens",
    "Tottenham Hotspur": "Tottenham", "Tottenham Hotspur FC": "Tottenham", "Newcastle United FC": "Newcastle",
    "Newcastle United": "Newcastle", "West Ham United": "West Ham", "West Ham United FC": "West Ham",
    "Leicester City": "Leicester", "Brighton & Hove Albion": "Brighton", "Brighton & Hove Albion FC": "Brighton",
    "Wolverhampton Wanderers": "Wolves", "Wolverhampton Wanderers FC": "Wolves", "Nottingham Forest": "Nott'm Forest",
    "Nottingham Forest FC": "Nott'm Forest", "AFC Ajax": "Ajax", "FC Twente": "Twente",
    "FC Red Bull Salzburg": "Salzburg", "RB Salzburg": "Salzburg", "SK Sturm Graz": "Sturm Graz",
    "Rapid Wien": "SK Rapid", "SK Rapid Wien": "SK Rapid", "Wolfsberger AC": "Wolfsberger AC",
    "FC København": "FC Copenhagen", "Brøndby IF": "Brondby", "İstanbul Başakşehir": "Buyuksehyr",
    "Beşiktaş": "Besiktas", "Fenerbahçe": "Fenerbahce", "Galatasaray SK": "Galatasaray",
    "Qarabağ Ağdam FK": "Qarabag", "Qarabağ FK": "Qarabag", "Dinamo Kiev": "Dynamo Kyiv",
    "FK Shakhtar Donetsk": "Shakhtar Donetsk", "SK Slavia Praha": "Slavia Praha",
    "ŠK Slovan Bratislava": "Slovan Bratislava", "GNK Dinamo Zagreb": "Dinamo Zagreb",
    "FK Crvena Zvezda": "Crvena Zvezda", "Red Star Belgrade": "Crvena Zvezda", "AC Sparta Praha": "Sparta Praha",
    "Viktoria Plzeň": "Plzen", "Ferencvárosi TC": "Ferencvaros", "PFC Ludogorets Razgrad": "Ludogorets",
    "FC Sheriff": "Sheriff", "FK Kairat": "Kairat", "Paphos FC": "Paphos",
    "Girona FC": "Girona", "Villarreal CF": "Villarreal", "Sevilla FC": "Sevilla", "Valencia CF": "Valencia",
    "Granada CF": "Granada", "Celtic FC": "Celtic", "Rangers FC": "Rangers", "Molde FK": "Molde",
    "LASK Linz": "LASK", "Slavia Prague": "Slavia Praha", "Slovan": "Slovan Bratislava", "Shakhtar": "Shakhtar Donetsk",
    "Sabah FK": "Sabah", "Sabah FC": "Sabah", "NEC": "Nijmegen", "NEC Nijmegen": "Nijmegen",
}


def _strip_accents(s):
    s = str(s).translate(_TRANS)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_name(s):
    s = _strip_accents(s).lower().replace("&", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = s.replace("oe", "o").replace("ae", "a").replace("ue", "u")  # Malmoe = Malmö = Malmo
    toks = [t for t in s.split() if t not in STOP]
    return " ".join(toks) if toks else s.strip()


def pretty_name(s):
    s = _strip_accents(s)
    toks = s.replace("-", " - ").split()
    while toks and toks[0].lower().strip(".") in STOP:
        toks = toks[1:]
    while toks and toks[-1].lower().strip(".") in STOP:
        toks = toks[:-1]
    return " ".join(toks).replace(" - ", "-") if toks else s


class NameResolver:
    """Convierte nombres de distintas fuentes a un nombre canónico (estilo football-data)."""

    def __init__(self):
        self.pool = {}   # país -> set de nombres canónicos
        self.cache = {}

    def add_pool(self, country, names):
        self.pool.setdefault(country, set()).update([n for n in names if isinstance(n, str)])

    def resolve(self, name, country=None):
        key = (name, country)
        if key in self.cache:
            return self.cache[key]
        out = self._resolve(name, country)
        self.cache[key] = out
        return out

    def _match_in(self, name, cands):
        if not cands:
            return None
        n = norm_name(name)
        nm = {c: norm_name(c) for c in cands}
        exact = [c for c, v in nm.items() if v == n]
        if exact:
            return exact[0]
        nt = set(n.split())
        sub = [c for c, v in nm.items() if v and (set(v.split()) <= nt or nt <= set(v.split()))]
        if len(sub) == 1:
            return sub[0]
        best = difflib.get_close_matches(n, list(nm.values()), n=1, cutoff=0.78)
        if best:
            return [c for c, v in nm.items() if v == best[0]][0]
        return None

    def _resolve(self, name, country):
        if country == "MCO":
            country = "FRA"
        if name in ALIAS:
            a = ALIAS[name]
            return a
        cands = self.pool.get(country, set()) if country else set().union(*self.pool.values()) if self.pool else set()
        m = self._match_in(name, cands)
        if m:
            return m
        return pretty_name(name)


RESOLVER = NameResolver()


# %% [codigo] Carga de datos domésticos (football-data.co.uk con respaldo en GitHub)
STAT_COLS_FD = {"ht_hg": "HTHG", "ht_ag": "HTAG", "h_shots": "HS", "a_shots": "AS", "h_sot": "HST", "a_sot": "AST",
                "h_fouls": "HF", "a_fouls": "AF", "h_corners": "HC", "a_corners": "AC", "h_yellow": "HY",
                "a_yellow": "AY", "h_red": "HR", "a_red": "AR", "h_off": "HO", "a_off": "AO"}
STAT_COLS_XG = {"ht_hg": "HTHome", "ht_ag": "HTAway", "h_shots": "HomeShots", "a_shots": "AwayShots",
                "h_sot": "HomeTarget", "a_sot": "AwayTarget", "h_fouls": "HomeFouls", "a_fouls": "AwayFouls",
                "h_corners": "HomeCorners", "a_corners": "AwayCorners", "h_yellow": "HomeYellow",
                "a_yellow": "AwayYellow", "h_red": "HomeRed", "a_red": "AwayRed"}
EXTRA_COLS = list(STAT_COLS_FD) + ["referee"]


def _std_cols(df, div, country):
    """Normaliza un CSV de football-data al esquema interno."""
    c = df.columns
    home = "HomeTeam" if "HomeTeam" in c else "Home"
    away = "AwayTeam" if "AwayTeam" in c else "Away"
    hg = "FTHG" if "FTHG" in c else "HG"
    ag = "FTAG" if "FTAG" in c else "AG"
    out = pd.DataFrame({
        "date": pd.to_datetime(df["Date"], dayfirst=True, errors="coerce"),
        "div": div, "country": country,
        "home": df[home].astype(str).str.strip(), "away": df[away].astype(str).str.strip(),
        "hg": pd.to_numeric(df[hg], errors="coerce"), "ag": pd.to_numeric(df[ag], errors="coerce"),
    })
    for tgt, opts in {"oh": ["B365H", "B365CH", "AvgH", "AvgCH", "PSH", "PSCH"],
                      "od": ["B365D", "B365CD", "AvgD", "AvgCD", "PSD", "PSCD"],
                      "oa": ["B365A", "B365CA", "AvgA", "AvgCA", "PSA", "PSCA"],
                      "o25": ["B365>2.5", "Avg>2.5"], "u25": ["B365<2.5", "Avg<2.5"]}.items():
        col = next((o for o in opts if o in c), None)
        out[tgt] = pd.to_numeric(df[col], errors="coerce") if col else np.nan
    for tgt, col in STAT_COLS_FD.items():
        out[tgt] = pd.to_numeric(df[col], errors="coerce") if col in c else np.nan
    out["referee"] = df["Referee"].astype(str) if "Referee" in c else np.nan
    return out


def load_footballdata(seasons=("1819", "1920", "2021", "2122", "2223", "2324", "2425", "2526", "2627"),
                      verbose=True):
    frames = []
    for s in seasons:
        for d in DIVS_MAIN:
            url = f"{FD_BASE}mmz4281/{s}/{d}.csv"
            try:
                raw = http_get(url, cache=(s != seasons[-1]))
                df = pd.read_csv(io.BytesIO(raw), encoding="latin-1", on_bad_lines="skip")
                if len(df):
                    frames.append(_std_cols(df, d, DIV_COUNTRY[d]))
            except Exception as e:
                if verbose:
                    print("  aviso:", url, e)
    for code, fn in DIVS_EXTRA.items():
        try:
            raw = http_get(f"{FD_BASE}new/{fn}.csv", cache=False)
            df = pd.read_csv(io.BytesIO(raw), encoding="latin-1", on_bad_lines="skip")
            frames.append(_std_cols(df, code, DIV_COUNTRY[code]))
        except Exception as e:
            if verbose:
                print("  aviso extra:", fn, e)
    out = pd.concat(frames, ignore_index=True)
    return out.dropna(subset=["date", "hg", "ag"])


def load_xgabora():
    raw = http_get(XG_BASE + "Matches.csv")
    m = pd.read_csv(io.BytesIO(raw), low_memory=False)
    divs = DIVS_MAIN + list(DIVS_EXTRA)
    m = m[m.Division.isin(divs)]
    out = pd.DataFrame({
        "date": pd.to_datetime(m.MatchDate), "div": m.Division, "country": m.Division.map(DIV_COUNTRY),
        "home": m.HomeTeam, "away": m.AwayTeam, "hg": m.FTHome, "ag": m.FTAway,
        "oh": m.OddHome, "od": m.OddDraw, "oa": m.OddAway, "o25": m.Over25, "u25": m.Under25})
    for tgt, col in STAT_COLS_XG.items():
        out[tgt] = pd.to_numeric(m[col], errors="coerce")
    return out.dropna(subset=["hg", "ag"])


def load_elo_seeds():
    raw = http_get(XG_BASE + "EloRatings.csv")
    e = pd.read_csv(io.BytesIO(raw))
    e["date"] = pd.to_datetime(e["date"])
    return e.rename(columns={"club": "team"})


def load_openfootball_league(season="2026-27"):
    """Resultados (y calendario) de la temporada actual en 7 ligas, respaldo si no hay football-data."""
    rows = []
    for code, div in OF_LEAGUES.items():
        try:
            d = json.loads(http_get(f"{OF_BASE}{season}/{code}.json", cache=False))
        except Exception as e:
            print("  aviso openfootball:", code, e)
            continue
        for mt in d.get("matches", []):
            sc = mt.get("score") if isinstance(mt.get("score"), dict) else {}
            ft = sc.get("ft")
            rows.append({"date": pd.to_datetime(mt["date"]), "div": div, "country": DIV_COUNTRY[div],
                         "home_raw": mt["team1"], "away_raw": mt["team2"],
                         "hg": ft[0] if ft else np.nan, "ag": ft[1] if ft else np.nan,
                         "ht_hg": sc.get("ht", [np.nan, np.nan])[0], "ht_ag": sc.get("ht", [np.nan, np.nan])[1],
                         "time": mt.get("time")})
    return pd.DataFrame(rows)


# %% [codigo] Carga de partidos europeos (Champions y Europa League, formato football.txt)
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                                      "Sep", "Oct", "Nov", "Dec"], 1)}
RE_DATE = re.compile(r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
RE_MATCH = re.compile(r"^\s*(?:\d{1,2}[:.]\d{2}\s+)?(.+?)\s+\((\w{3})\)\s+v\s+(.+?)\s+\((\w{3})\)\s+(.*)$")


def parse_football_txt(text, season, comp):
    start = int(season[:4])
    rows, cur_date, rnd = [], None, ""
    for line in text.splitlines():
        if line.strip().startswith("▪"):
            rnd = line.strip().lstrip("▪").strip()
            continue
        md = RE_DATE.match(line)
        if md:
            mon, day = MONTHS[md.group(2)], int(md.group(3))
            yr = start if mon >= 7 else start + 1
            cur_date = pd.Timestamp(yr, mon, day)
            continue
        mm = RE_MATCH.match(line)
        if not mm or cur_date is None:
            continue
        rest = mm.group(5)
        pares = re.findall(r"\((\d+)-(\d+)(?:,\s*(\d+)-(\d+))?\)", rest)
        if "a.e.t" in rest:
            par = re.search(r"\((\d+)-(\d+)", rest)
            if not par:
                continue
            hg, ag = int(par.group(1)), int(par.group(2))
            ht = (pares[0][2], pares[0][3]) if pares and pares[0][2] else (np.nan, np.nan)
        else:
            sc = re.match(r"\s*(\d+)-(\d+)", rest)
            if not sc:
                continue
            hg, ag = int(sc.group(1)), int(sc.group(2))
            ht = (pares[0][0], pares[0][1]) if pares else (np.nan, np.nan)
        neutral = rnd.lower() == "final"
        rows.append({"date": cur_date, "div": comp, "home_raw": mm.group(1).strip(), "hc": mm.group(2),
                     "away_raw": mm.group(3).strip(), "ac": mm.group(4), "hg": hg, "ag": ag,
                     "ht_hg": float(ht[0]), "ht_ag": float(ht[1]),
                     "home_factor": 0.0 if neutral else 1.0, "round": rnd})
    return pd.DataFrame(rows)


def load_european(seasons=("2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26")):
    frames = []
    for s in seasons:
        for comp, fn in [("UCL", "cl.txt"), ("UEL", "el.txt")]:
            try:
                txt = http_get(f"{OFCL_BASE}{s}/{fn}").decode("utf-8")
                if txt.strip().startswith("404"):
                    continue
                df = parse_football_txt(txt, s, comp)
                if len(df):
                    frames.append(df)
            except Exception:
                pass
    return pd.concat(frames, ignore_index=True)


# %% [codigo] Construcción del dataset unificado
def build_dataset(ucl_actual_csv, source="auto", verbose=True):
    """Devuelve (partidos, semillas_elo). partidos: date, div, home, away, hg, ag, odds, home_factor, is_euro."""
    t0 = time.time()
    dom = None
    if source in ("auto", "footballdata"):
        try:
            http_get(f"{FD_BASE}mmz4281/2526/E0.csv", timeout=15)
            if verbose:
                print("Fuente doméstica: football-data.co.uk (datos frescos)")
            dom = load_footballdata(verbose=verbose)
        except Exception as e:
            if verbose:
                print("football-data.co.uk no disponible:", str(e)[:80])
    fresh = dom is not None
    if dom is None:
        if verbose:
            print("Fuente doméstica: espejo GitHub (xgabora) + openfootball para 2026-27")
        dom = load_xgabora()
    dom = dom[dom.date >= "2018-07-01"].copy()
    for (div, country), g in dom.groupby(["div", "country"]):
        RESOLVER.add_pool(country, set(g.home) | set(g.away))

    seeds = load_elo_seeds()
    for country, g in seeds.groupby("country"):
        if country not in set(DIV_COUNTRY.values()):
            RESOLVER.add_pool(country, set(g.team))
    seeds["team"] = [RESOLVER.resolve(t, c) for t, c in zip(seeds.team, seeds.country)]

    if not fresh:
        of = load_openfootball_league("2026-27")
        if len(of):
            of["home"] = [RESOLVER.resolve(n, c) for n, c in zip(of.home_raw, of.country)]
            of["away"] = [RESOLVER.resolve(n, c) for n, c in zip(of.away_raw, of.country)]
            last = dom.groupby("div").date.max()
            of_played = of.dropna(subset=["hg"])
            of_played = of_played[of_played.apply(lambda r: r.date > last.get(r["div"], pd.Timestamp("1900")), axis=1)]
            dom = pd.concat([dom, of_played[["date", "div", "country", "home", "away", "hg", "ag", "ht_hg", "ht_ag"]]], ignore_index=True)
            if verbose:
                print(f"  openfootball 2026-27: +{len(of_played)} partidos domésticos (hasta {of_played.date.max().date() if len(of_played) else '-'})")

    eur = load_european()
    cur = pd.read_csv(io.StringIO(ucl_actual_csv))
    cur["date"] = pd.to_datetime(cur["date"])
    cur["div"] = "UCL"
    cur = cur.rename(columns={"home": "home_raw", "away": "away_raw"})
    cur["home_factor"] = cur.get("home_factor", 1.0)
    eur = pd.concat([eur, cur], ignore_index=True)
    eur["home"] = [RESOLVER.resolve(n, c if isinstance(c, str) else None) for n, c in zip(eur.home_raw, eur.get("hc", pd.Series([None] * len(eur))))]
    eur["away"] = [RESOLVER.resolve(n, c if isinstance(c, str) else None) for n, c in zip(eur.away_raw, eur.get("ac", pd.Series([None] * len(eur))))]
    eur["country"] = "EUR"

    dom["home_factor"] = 1.0
    dom["is_euro"] = 0
    eur["is_euro"] = 1
    cols = ["date", "div", "country", "home", "away", "hg", "ag", "home_factor", "is_euro", "oh", "od", "oa", "o25", "u25"] + EXTRA_COLS
    for c in cols:
        if c not in eur:
            eur[c] = np.nan
        if c not in dom:
            dom[c] = np.nan
    df = pd.concat([dom[cols], eur[cols]], ignore_index=True)
    df = df.dropna(subset=["hg", "ag"]).sort_values(["date", "is_euro"]).reset_index(drop=True)
    df["hg"] = df.hg.astype(int)
    df["ag"] = df.ag.astype(int)
    df["res"] = np.where(df.hg > df.ag, 0, np.where(df.hg == df.ag, 1, 2))  # 0=local 1=empate 2=visita
    df["season"] = np.where(df.date.dt.month >= 7, df.date.dt.year, df.date.dt.year - 1)
    # país de cada equipo (para semillas por defecto)
    tc = {}
    for _, r in dom[["home", "country"]].drop_duplicates().iterrows():
        tc[r.home] = r.country
    for _, r in eur.iterrows():
        for t, c in ((r.home, r.get("hc")), (r.away, r.get("ac"))):
            if t not in tc and isinstance(c, str):
                tc[t] = "FRA" if c == "MCO" else c
    df.attrs["team_country"] = tc
    df.attrs["fresh"] = fresh
    if verbose:
        print(f"Partidos cargados: {len(df):,} | europeos: {df.is_euro.sum():,} | último: {df.date.max().date()} | {time.time()-t0:.0f}s")
    return df, seeds


# %% [codigo] Elo propio (sembrado con ClubElo, actualizado partido a partido)
class Elo:
    def __init__(self, seeds, team_country, k_dom=20, k_euro=30, hfa=65, reseed_days=180):
        self.k_dom, self.k_euro, self.hfa, self.reseed_days = k_dom, k_euro, hfa, reseed_days
        self.r, self.last = {}, {}
        self.team_country = team_country
        self.seed_idx = {t: (g.date.values, g.elo.values) for t, g in seeds.sort_values("date").groupby("team")}

    def _seed(self, team, date):
        if team in self.seed_idx:
            d, e = self.seed_idx[team]
            i = np.searchsorted(d, np.datetime64(date), side="right") - 1
            if i >= 0 and (np.datetime64(date) - d[i]) < np.timedelta64(60, "D"):
                return float(e[i])
        return None

    def get(self, team, date):
        if team not in self.r:
            s = self._seed(team, date)
            self.r[team] = s if s is not None else COUNTRY_DEFAULT_ELO.get(self.team_country.get(team), 1500)
        elif (date - self.last.get(team, date)).days > self.reseed_days:
            s = self._seed(team, date)
            if s is not None:
                self.r[team] = s
        return self.r[team]

    def update(self, h, a, hg, ag, date, hf=1.0, euro=0):
        rh, ra = self.get(h, date), self.get(a, date)
        dr = rh + self.hfa * hf - ra
        we = 1.0 / (10 ** (-dr / 400.0) + 1.0)
        w = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        gd = abs(hg - ag)
        g = 1.0 if gd <= 1 else 1.5 if gd == 2 else (11.0 + gd) / 8.0
        k = self.k_euro if euro else self.k_dom
        delta = k * g * (w - we)
        self.r[h] = rh + delta
        self.r[a] = ra - delta
        self.last[h] = self.last[a] = date
        return rh, ra


def run_elo(df, seeds, until=None):
    """Elo previo a cada partido (sin fuga de información). Si until, congela después de esa fecha."""
    elo = Elo(seeds, df.attrs.get("team_country", {}))
    eh, ea = np.zeros(len(df)), np.zeros(len(df))
    for i, r in enumerate(df.itertuples(index=False)):
        if until is not None and r.date >= until:
            eh[i], ea[i] = elo.get(r.home, until), elo.get(r.away, until)
            continue
        eh[i], ea[i] = elo.update(r.home, r.away, r.hg, r.ag, r.date, r.home_factor, r.is_euro)
    return eh, ea, elo


# %% [codigo] Dixon-Coles con decaimiento temporal y prior Elo
class DixonColes:
    """log(lambda_local) = mu + home*hf + att[local] + dfn[visita];  log(lambda_visita) = mu + att[visita] + dfn[local].
    Penalización (att - a0*z)^2 + (dfn - d0*z)^2 con z = (Elo-1700)/100: equipos con pocos datos caen hacia su Elo."""

    def __init__(self, xi=0.0019, window_days=1095, lam_prior=4.0, max_goals=10):
        self.xi, self.window, self.lam, self.G = xi, window_days, lam_prior, max_goals

    def fit(self, df, ref_date, elo_now, init=None):
        d = df[(df.date < ref_date) & (df.date >= ref_date - pd.Timedelta(days=self.window))]
        teams = sorted(set(d.home) | set(d.away))
        self.teams = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        hi, ai = d.home.map(self.teams).values, d.away.map(self.teams).values
        yh, ya, hf = d.hg.values.astype(float), d.ag.values.astype(float), d.home_factor.values.astype(float)
        w = np.exp(-self.xi * (ref_date - d.date).dt.days.values)
        z = np.array([(elo_now.get(t, 1600) - 1700) / 100.0 for t in teams])
        lam = self.lam

        def unpack(p):
            return p[0], p[1], p[2:2 + n], p[2 + n:2 + 2 * n], p[-2], p[-1]

        def f(p):
            mu, home, att, dfn, a0, d0 = unpack(p)
            lh = mu + home * hf + att[hi] + dfn[ai]
            la = mu + att[ai] + dfn[hi]
            Lh, La = np.exp(lh), np.exp(la)
            nll = np.sum(w * (Lh - yh * lh)) + np.sum(w * (La - ya * la))
            ra, rd = att - a0 * z, dfn - d0 * z
            nll += lam * (ra @ ra + rd @ rd)
            gh, ga = w * (Lh - yh), w * (La - ya)
            g = np.zeros_like(p)
            g[0] = gh.sum() + ga.sum()
            g[1] = (gh * hf).sum()
            g_att = np.bincount(hi, gh, n) + np.bincount(ai, ga, n) + 2 * lam * ra
            g_dfn = np.bincount(ai, gh, n) + np.bincount(hi, ga, n) + 2 * lam * rd
            g[2:2 + n], g[2 + n:2 + 2 * n] = g_att, g_dfn
            g[-2] = -2 * lam * (ra @ z)
            g[-1] = -2 * lam * (rd @ z)
            return nll, g

        p0 = np.zeros(2 * n + 4)
        p0[0], p0[1], p0[-2], p0[-1] = 0.25, 0.25, 0.12, -0.12
        if init is not None:
            for t, i in self.teams.items():
                if t in init["teams"]:
                    j = init["teams"][t]
                    p0[2 + i], p0[2 + n + i] = init["att"][j], init["dfn"][j]
            p0[0], p0[1], p0[-2], p0[-1] = init["mu"], init["home"], init["a0"], init["d0"]
        res = minimize(f, p0, jac=True, method="L-BFGS-B", options={"maxiter": 500})
        self.mu, self.home, self.att, self.dfn, self.a0, self.d0 = unpack(res.x)
        # rho por máxima verosimilitud dada la parte Poisson
        lh = np.exp(self.mu + self.home * hf + self.att[hi] + self.dfn[ai])
        la = np.exp(self.mu + self.att[ai] + self.dfn[hi])
        m00, m01, m10, m11 = (yh == 0) & (ya == 0), (yh == 0) & (ya == 1), (yh == 1) & (ya == 0), (yh == 1) & (ya == 1)

        def nll_rho(r):
            t = np.ones_like(lh)
            t[m00] = 1 - lh[m00] * la[m00] * r
            t[m01] = 1 + lh[m01] * r
            t[m10] = 1 + la[m10] * r
            t[m11] = 1 - r
            return -np.sum(w * np.log(np.clip(t, 1e-9, None)))

        self.rho = minimize_scalar(nll_rho, bounds=(-0.25, 0.25), method="bounded").x
        self.n_obs = pd.Series(np.bincount(hi, w, n) + np.bincount(ai, w, n), index=teams)
        self.ref_date = ref_date
        return self

    def state(self):
        return {"teams": self.teams, "att": self.att, "dfn": self.dfn, "mu": self.mu, "home": self.home,
                "a0": self.a0, "d0": self.d0}

    def team_params(self, team, elo_now):
        if team in self.teams:
            i = self.teams[team]
            return self.att[i], self.dfn[i]
        z = (elo_now.get(team, 1600) - 1700) / 100.0
        return self.a0 * z, self.d0 * z

    def lambdas(self, home, away, hf, elo_now):
        ah, dh = self.team_params(home, elo_now)
        aa, da = self.team_params(away, elo_now)
        return math.exp(self.mu + self.home * hf + ah + da), math.exp(self.mu + aa + dh)


def score_matrix(lh, la, rho, G=10):
    """Matriz de probabilidades de marcador (Poisson + corrección Dixon-Coles). Vectorizada."""
    lh, la = np.atleast_1d(lh), np.atleast_1d(la)
    k = np.arange(G + 1)
    ph = poisson.pmf(k[None, :], lh[:, None])
    pa = poisson.pmf(k[None, :], la[:, None])
    M = ph[:, :, None] * pa[:, None, :]
    rho = np.broadcast_to(np.atleast_1d(rho), lh.shape)
    M[:, 0, 0] *= 1 - lh * la * rho
    M[:, 0, 1] *= 1 + lh * rho
    M[:, 1, 0] *= 1 + la * rho
    M[:, 1, 1] *= 1 - rho
    M = np.clip(M, 0, None)
    M /= M.sum(axis=(1, 2), keepdims=True)
    return M


def probs_1x2(M):
    tri_l = np.tril(np.ones(M.shape[1:]), -1).astype(bool)
    ph = M[:, tri_l].sum(axis=1)
    pd_ = np.einsum("nii->n", M)
    return np.c_[ph, pd_, 1 - ph - pd_]


def dc_walk_forward(df, elo_pre, start, end, step_days=14, dc_kwargs=None, frozen_at=None, verbose=True):
    """Predicciones Dixon-Coles fuera de muestra para partidos en [start, end).
    Reajusta cada step_days usando solo partidos anteriores. Si frozen_at, ajusta una sola vez en esa fecha."""
    dc_kwargs = dc_kwargs or {}
    out = np.full((len(df), 4), np.nan)
    rhos = np.full(len(df), np.nan)
    elo_hist = pd.DataFrame({"date": np.r_[df.date.values, df.date.values],
                             "team": np.r_[df.home.values, df.away.values],
                             "elo": np.r_[elo_pre[0], elo_pre[1]]}).sort_values("date")
    t, init, fits = pd.Timestamp(start), None, 0
    dates = [pd.Timestamp(frozen_at)] if frozen_at is not None else []
    if frozen_at is None:
        while t < pd.Timestamp(end):
            dates.append(t)
            t += pd.Timedelta(days=step_days)
    t0 = time.time()
    for j, t in enumerate(dates):
        t_next = pd.Timestamp(end) if frozen_at is not None else (dates[j + 1] if j + 1 < len(dates) else pd.Timestamp(end))
        mask = (df.date >= (t if frozen_at is None else pd.Timestamp(start))) & (df.date < t_next)
        if not mask.any():
            continue
        elo_now = elo_hist[elo_hist.date < t].groupby("team").elo.last().to_dict()
        dc = DixonColes(**dc_kwargs).fit(df, t, elo_now, init=init)
        init = dc.state()
        fits += 1
        sub = df[mask]
        lam = np.array([dc.lambdas(h, a, hf, elo_now) for h, a, hf in zip(sub.home, sub.away, sub.home_factor)])
        P = probs_1x2(score_matrix(lam[:, 0], lam[:, 1], dc.rho))
        idx = np.where(mask.values)[0]
        out[idx, 0], out[idx, 1] = lam[:, 0], lam[:, 1]
        out[idx, 2], out[idx, 3] = P[:, 0], P[:, 2]
        rhos[idx] = dc.rho
    if verbose:
        print(f"  Dixon-Coles: {fits} ajustes en {time.time()-t0:.0f}s")
    return out, rhos


# %% [codigo] Variables de forma (últimos 5 partidos) y descanso
def form_features(df, n=5, frozen_at=None):
    long = pd.concat([
        pd.DataFrame({"i": df.index, "date": df.date, "team": df.home, "gf": df.hg, "ga": df.ag,
                      "pts": np.select([df.hg > df.ag, df.hg == df.ag], [3, 1], 0), "side": "h"}),
        pd.DataFrame({"i": df.index, "date": df.date, "team": df.away, "gf": df.ag, "ga": df.hg,
                      "pts": np.select([df.ag > df.hg, df.ag == df.hg], [3, 1], 0), "side": "a"})
    ]).sort_values(["team", "date", "i"])
    g = long.groupby("team")
    if frozen_at is None:
        for c in ["gf", "ga", "pts"]:
            long[c + "5"] = g[c].transform(lambda s: s.shift(1).rolling(n, min_periods=1).mean())
    else:
        pre = long[long.date < frozen_at]
        snap = pre.groupby("team").tail(n).groupby("team")[["gf", "ga", "pts"]].mean()
        for c in ["gf", "ga", "pts"]:
            roll = g[c].transform(lambda s: s.shift(1).rolling(n, min_periods=1).mean())
            long[c + "5"] = np.where(long.date < frozen_at, roll, long.team.map(snap[c]))
    long["rest"] = g.date.diff().dt.days.clip(upper=21)
    h = long[long.side == "h"].set_index("i")
    a = long[long.side == "a"].set_index("i")
    f = pd.DataFrame(index=df.index)
    for c in ["gf5", "ga5", "pts5", "rest"]:
        f["h_" + c] = h[c]
        f["a_" + c] = a[c]
    return f.fillna({"h_gf5": 1.35, "a_gf5": 1.35, "h_ga5": 1.35, "a_ga5": 1.35, "h_pts5": 1.35,
                     "a_pts5": 1.35, "h_rest": 7, "a_rest": 7})


def assemble_features(df, eh, ea, dc_out, form):
    X = pd.DataFrame(index=df.index)
    X["elo_h"], X["elo_a"] = eh, ea
    X["elo_diff"] = eh - ea
    X["hf"] = df.home_factor.values
    X["is_euro"] = df.is_euro.values
    X["dc_lh"], X["dc_la"] = dc_out[:, 0], dc_out[:, 1]
    X["dc_ph"], X["dc_pa"] = dc_out[:, 2], dc_out[:, 3]
    X["dc_pd"] = 1 - X.dc_ph - X.dc_pa
    X = pd.concat([X, form], axis=1)
    X["pts5_diff"] = X.h_pts5 - X.a_pts5
    X["gd5_diff"] = (X.h_gf5 - X.h_ga5) - (X.a_gf5 - X.a_ga5)
    X["rest_diff"] = X.h_rest - X.a_rest
    return X


FEATS_XGB = ["elo_h", "elo_a", "elo_diff", "hf", "is_euro", "dc_lh", "dc_la", "dc_ph", "dc_pd", "dc_pa",
             "h_gf5", "h_ga5", "h_pts5", "a_gf5", "a_ga5", "a_pts5", "h_rest", "a_rest", "pts5_diff", "gd5_diff"]
FEATS_LIN = ["elo_diff", "hf", "is_euro", "pts5_diff", "gd5_diff", "rest_diff"]


# %% [codigo] Modelos: regresión logística, regresión lineal, regresión de Poisson y XGBoost
from sklearn.linear_model import LogisticRegression, LinearRegression, PoissonRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import xgboost as xgb


class EloLogit:
    nombre = "Regresión logística (Elo)"

    def fit(self, X, y, w=None):
        Z = self._z(X)
        self.m = LogisticRegression(C=1.0, max_iter=2000).fit(Z, y, sample_weight=w)
        return self

    def _z(self, X):
        d = X.elo_diff.values / 100.0
        return np.c_[d, X.hf.values, X.is_euro.values, d * X.is_euro.values]

    def predict(self, X):
        return self.m.predict_proba(self._z(X))


class LinearGD:
    """Regresión lineal sobre la diferencia de goles; 1X2 con distribución normal de residuos."""
    nombre = "Regresión lineal (dif. goles)"

    def fit(self, X, y_gd, w=None):
        self.m = make_pipeline(StandardScaler(), LinearRegression()).fit(X[FEATS_LIN], y_gd, linearregression__sample_weight=w)
        res = y_gd - self.m.predict(X[FEATS_LIN])
        self.sigma = float(np.sqrt(np.average(res ** 2, weights=w)))
        return self

    def mean(self, X):
        return self.m.predict(X[FEATS_LIN])

    def predict(self, X):
        mu = self.mean(X)
        pa = norm.cdf((-0.5 - mu) / self.sigma)
        ph = 1 - norm.cdf((0.5 - mu) / self.sigma)
        return np.c_[ph, 1 - ph - pa, pa]


class PoissonGLM:
    """Dos regresiones de Poisson (goles local y visita) con Elo y forma; 1X2 por matriz de marcadores."""
    nombre = "Regresión de Poisson (GLM)"

    def fit(self, X, hg, ag, w=None, rho=-0.05):
        F = FEATS_LIN
        self.mh = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=500)).fit(X[F], hg, poissonregressor__sample_weight=w)
        self.ma = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=500)).fit(X[F], ag, poissonregressor__sample_weight=w)
        self.rho = rho
        return self

    def lambdas(self, X):
        return self.mh.predict(X[FEATS_LIN]), self.ma.predict(X[FEATS_LIN])

    def predict(self, X):
        lh, la = self.lambdas(X)
        return probs_1x2(score_matrix(lh, la, self.rho))


class XGBModel:
    nombre = "XGBoost"

    def __init__(self, n_estimators=400, **kw):
        self.params = dict(n_estimators=n_estimators, max_depth=3, learning_rate=0.03, subsample=0.8,
                           colsample_bytree=0.8, min_child_weight=20, reg_lambda=5.0,
                           objective="multi:softprob", num_class=3, eval_metric="mlogloss", n_jobs=4)
        self.params.update(kw)

    def fit(self, X, y, w=None, X_val=None, y_val=None):
        if X_val is not None:
            m = xgb.XGBClassifier(**{**self.params, "n_estimators": 1500, "early_stopping_rounds": 50})
            m.fit(X[FEATS_XGB], y, sample_weight=w, eval_set=[(X_val[FEATS_XGB], y_val)], verbose=False)
            self.best_n = int(m.best_iteration) + 1
            self.params["n_estimators"] = self.best_n
        self.m = xgb.XGBClassifier(**self.params).fit(X[FEATS_XGB], y, sample_weight=w)
        return self

    def predict(self, X):
        return self.m.predict_proba(X[FEATS_XGB])


# %% [codigo] Métricas, ensamble y mezcla con el mercado
def metrics(P, y, name=""):
    P = np.clip(np.asarray(P, float), 1e-12, 1)
    P = P / P.sum(1, keepdims=True)
    y = np.asarray(y)
    Y = np.eye(3)[y]
    acc = (P.argmax(1) == y).mean()
    ll = -np.mean(np.log(P[np.arange(len(y)), y]))
    brier = np.mean(np.sum((P - Y) ** 2, 1))
    cP, cY = np.cumsum(P, 1)[:, :2], np.cumsum(Y, 1)[:, :2]
    rps = np.mean(np.sum((cP - cY) ** 2, 1) / 2)
    return {"modelo": name, "n": len(y), "accuracy": acc, "log_loss": ll, "brier": brier, "rps": rps}


def market_probs(oh, od, oa):
    inv = np.c_[1 / np.asarray(oh, float), 1 / np.asarray(od, float), 1 / np.asarray(oa, float)]
    return inv / inv.sum(1, keepdims=True)


def fit_weights(P_list, y):
    """Pesos del ensamble (simplex) que minimizan log loss en datos fuera de muestra."""
    k = len(P_list)
    Ps = np.stack(P_list)

    def loss(v):
        w = np.exp(v) / np.exp(v).sum()
        P = np.tensordot(w, Ps, 1)
        return -np.mean(np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)))

    r = minimize(loss, np.zeros(k), method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-4})
    return np.exp(r.x) / np.exp(r.x).sum()


def fit_blend(P_model, P_mkt, y):
    """Peso w del modelo en la mezcla lineal w*modelo + (1-w)*mercado."""
    def loss(w):
        P = w * P_model + (1 - w) * P_mkt
        return -np.mean(np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)))
    return minimize_scalar(loss, bounds=(0, 1), method="bounded").x


def calibration_table(P, y, bins=10):
    rows = []
    for k, lab in enumerate(["local", "empate", "visita"]):
        p = P[:, k]
        hit = (np.asarray(y) == k).astype(float)
        cut = pd.cut(p, np.linspace(0, 1, bins + 1), include_lowest=True)
        t = pd.DataFrame({"p": p, "hit": hit, "bin": cut}).groupby("bin", observed=True).agg(p_media=("p", "mean"), frecuencia=("hit", "mean"), n=("hit", "size"))
        t["resultado"] = lab
        rows.append(t.reset_index())
    return pd.concat(rows)


def value_bets_sim(P, oh, od, oa, y, edge=0.05, kelly_frac=0.25):
    """Simula apostar 1 unidad cuando prob_modelo * cuota > 1 + edge. Devuelve resumen y serie de beneficio."""
    O = np.c_[oh, od, oa].astype(float)
    ok = np.isfinite(O).all(1)
    P, O, y = np.asarray(P)[ok], O[ok], np.asarray(y)[ok]
    ev = P * O - 1
    pick = ev.argmax(1)
    bet = ev[np.arange(len(pick)), pick] > edge
    win = (pick == y) & bet
    profit = np.where(bet, np.where(win, O[np.arange(len(pick)), pick] - 1, -1), 0.0)
    n = int(bet.sum())
    roi = profit.sum() / n if n else np.nan
    rng = np.random.default_rng(0)
    pb = profit[bet]
    boots = [rng.choice(pb, len(pb)).mean() for _ in range(2000)] if n > 10 else [np.nan]
    return {"apuestas": n, "aciertos": int(win.sum()), "beneficio_u": profit.sum(), "roi": roi,
            "roi_ic90": (np.nanpercentile(boots, 5), np.nanpercentile(boots, 95))}, np.cumsum(profit)


# %% [codigo] Monte Carlo de marcadores
def implied_lambdas(p_target, rho=-0.05, init=(1.4, 1.1), total_anchor=None, w_anchor=0.15):
    """Busca (lambda_local, lambda_visita) cuya matriz Dixon-Coles reproduce P(local) y P(visita).
    Si total_anchor, agrega un ancla suave hacia los goles totales de Dixon-Coles para que un empate
    poco probable entre equipos parejos no dispare el total de goles."""
    def f(x):
        lh, la = np.exp(x)
        P = probs_1x2(score_matrix(lh, la, rho))[0]
        r = [P[0] - p_target[0], P[2] - p_target[2]]
        if total_anchor:
            r.append(w_anchor * (math.log(lh + la) - math.log(total_anchor)))
        return r
    r = least_squares(f, np.log(init), bounds=([-3, -3], [2, 2]))
    return tuple(np.exp(r.x))


def monte_carlo(lh, la, rho=-0.05, n_sims=100_000, sigma=0.10, seed=42):
    """Simula n_sims partidos. Cada simulación sortea lambdas con ruido lognormal (incertidumbre del modelo)
    y después un marcador de la matriz Dixon-Coles correspondiente."""
    rng = np.random.default_rng(seed)
    G = 10
    eps = rng.normal(0, sigma, (n_sims, 2))
    LH, LA = lh * np.exp(eps[:, 0] - sigma ** 2 / 2), la * np.exp(eps[:, 1] - sigma ** 2 / 2)
    out_h, out_a = np.empty(n_sims, int), np.empty(n_sims, int)
    chunk = 20_000
    for s in range(0, n_sims, chunk):
        M = score_matrix(LH[s:s + chunk], LA[s:s + chunk], rho, G).reshape(-1, (G + 1) ** 2)
        c = M.cumsum(1)
        u = rng.random((len(M), 1))
        k = (c < u).sum(1).clip(max=(G + 1) ** 2 - 1)
        out_h[s:s + chunk], out_a[s:s + chunk] = k // (G + 1), k % (G + 1)
    tot = out_h + out_a
    sc = pd.Series([f"{h}-{a}" for h, a in zip(out_h[:20000], out_a[:20000])]).value_counts(normalize=True)
    return {"p_local": (out_h > out_a).mean(), "p_empate": (out_h == out_a).mean(), "p_visita": (out_h < out_a).mean(),
            "over15": (tot > 1.5).mean(), "over25": (tot > 2.5).mean(), "over35": (tot > 3.5).mean(),
            "btts": ((out_h > 0) & (out_a > 0)).mean(), "goles_esp": tot.mean(),
            "goles_p5_p95": (int(np.percentile(tot, 5)), int(np.percentile(tot, 95))),
            "top_marcadores": sc.head(5).round(3).to_dict(), "sims_h": out_h, "sims_a": out_a}


# %% [codigo] Pipeline completo: características walk-forward para todas las temporadas
TEMPORADAS = {2021: "2021-22", 2022: "2022-23", 2023: "2023-24", 2024: "2024-25", 2025: "2025-26", 2026: "2026-27"}
TOP5 = ["E0", "SP1", "I1", "D1", "F1"]


def build_features(df, seeds, start="2021-07-01", step_days=14, dc_kwargs=None, verbose=True):
    t0 = time.time()
    eh, ea, elo = run_elo(df, seeds)
    if verbose:
        print(f"  Elo walk-forward listo ({time.time()-t0:.0f}s)")
    end = df.date.max() + pd.Timedelta(days=1)
    dc_out, rhos = dc_walk_forward(df, (eh, ea), start, end, step_days=step_days, dc_kwargs=dc_kwargs, verbose=verbose)
    form = form_features(df)
    X = assemble_features(df, eh, ea, dc_out, form)
    X["rho"] = rhos
    return X, elo


def frozen_features(df, seeds, cutoff, dc_kwargs=None, verbose=True):
    """Versión estricta: nada de lo ocurrido desde cutoff entra al modelo (Elo, Dixon-Coles y forma congelados)."""
    cutoff = pd.Timestamp(cutoff)
    eh, ea, _ = run_elo(df, seeds, until=cutoff)
    dc_out, rhos = dc_walk_forward(df, (eh, ea), cutoff, df.date.max() + pd.Timedelta(days=1),
                                   dc_kwargs=dc_kwargs, frozen_at=cutoff, verbose=verbose)
    form = form_features(df, frozen_at=cutoff)
    X = assemble_features(df, eh, ea, dc_out, form)
    X["rho"] = rhos
    return X


def train_models(X, df, idx_train, idx_val=None):
    """Entrena los 4 modelos estadísticos. Si idx_val, usa validación para el número de árboles de XGBoost."""
    Xt, yt = X.loc[idx_train], df.loc[idx_train, "res"].values
    gd = (df.loc[idx_train, "hg"] - df.loc[idx_train, "ag"]).values
    models = {
        "logit": EloLogit().fit(Xt, yt),
        "lineal": LinearGD().fit(Xt, gd),
        "poisson": PoissonGLM().fit(Xt, df.loc[idx_train, "hg"].values, df.loc[idx_train, "ag"].values,
                                    rho=float(np.nanmedian(X.loc[idx_train, "rho"]))),
    }
    xm = XGBModel()
    if idx_val is not None:
        xm.fit(Xt, yt, X_val=X.loc[idx_val], y_val=df.loc[idx_val, "res"].values)
    else:
        xm.fit(Xt, yt)
    models["xgboost"] = xm
    return models


NOMBRES = {"dc": "Dixon-Coles", "logit": "Regresión logística (Elo)", "lineal": "Regresión lineal (dif. goles)",
           "poisson": "Regresión de Poisson (GLM)", "xgboost": "XGBoost", "ensamble": "Ensamble",
           "mercado": "Mercado (Bet365)", "mezcla": "Ensamble + mercado"}


def predict_all(models, X):
    P = {"dc": np.c_[X.dc_ph, X.dc_pd, X.dc_pa]}
    for k, m in models.items():
        P[k] = m.predict(X)
    return P


def run_backtest(df, X, seeds, train_seasons=(2021, 2022, 2023), test_seasons=(2024, 2025), dc_kwargs=None,
                 X_frozen=None, verbose=True):
    """Backtest con la regla 3 + 2: entrena con 3 temporadas, evalúa en las 2 siguientes sin verlas."""
    ok = X[["dc_ph", "dc_pa"]].notna().all(1)
    s = df.season
    tr = df.index[ok & s.isin(train_seasons[:-1])]
    va = df.index[ok & (s == train_seasons[-1])]
    te = df.index[ok & s.isin(test_seasons)]
    keys = ["dc", "logit", "lineal", "poisson", "xgboost"]

    # 1) entrenar en temporadas 1-2, validar en la 3 (pesos del ensamble, árboles XGBoost y mezcla con mercado)
    m12 = train_models(X, df, tr, va)
    Pv = predict_all(m12, X.loc[va])
    yv = df.loc[va, "res"].values
    w = fit_weights([Pv[k] for k in keys], yv)
    Pv["ensamble"] = np.tensordot(w, np.stack([Pv[k] for k in keys]), 1)
    has_odds_v = df.loc[va, ["oh", "od", "oa"]].notna().all(1).values & (df.loc[va, "is_euro"] == 0).values
    Mv = market_probs(*df.loc[va, ["oh", "od", "oa"]].values[has_odds_v].T)
    w_blend = fit_blend(Pv["ensamble"][has_odds_v], Mv, yv[has_odds_v])

    # 2) reentrenar con las 3 temporadas y predecir las 2 de prueba
    models = train_models(X, df, tr.union(va))
    models["xgboost"].params["n_estimators"] = m12["xgboost"].params["n_estimators"]
    models["xgboost"].fit(X.loc[tr.union(va)], df.loc[tr.union(va), "res"].values)
    res = {}
    for modo, XX in [("walk-forward", X), ("congelado", X_frozen)]:
        if XX is None:
            continue
        P = predict_all(models, XX.loc[te])
        P["ensamble"] = np.tensordot(w, np.stack([P[k] for k in keys]), 1)
        res[modo] = P
    return {"models": models, "weights": dict(zip(keys, w)), "w_blend": w_blend, "idx_test": te,
            "idx_train": tr.union(va), "preds": res, "freq_train": np.bincount(df.loc[tr.union(va), "res"], minlength=3) / len(tr.union(va))}


def backtest_report(df, bt):
    te = bt["idx_test"]
    y = df.loc[te, "res"].values
    sub = {"Todos los partidos": np.ones(len(te), bool),
           "Top 5 ligas": df.loc[te, "div"].isin(TOP5).values,
           "Champions League": (df.loc[te, "div"] == "UCL").values}
    odds = df.loc[te, ["oh", "od", "oa"]].values.astype(float)
    has_odds = np.isfinite(odds).all(1) & (df.loc[te, "is_euro"] == 0).values
    tablas = []
    for modo, P in bt["preds"].items():
        Pm = np.full((len(te), 3), np.nan)
        Pm[has_odds] = market_probs(*odds[has_odds].T)
        P = dict(P)
        P["mezcla"] = np.where(has_odds[:, None], bt["w_blend"] * P["ensamble"] + (1 - bt["w_blend"]) * np.nan_to_num(Pm), np.nan)
        for sname, mask in sub.items():
            for k in ["dc", "logit", "lineal", "poisson", "xgboost", "ensamble"]:
                r = metrics(P[k][mask], y[mask], NOMBRES[k])
                r.update({"modo": modo, "subconjunto": sname})
                tablas.append(r)
            if modo == "walk-forward":
                r = metrics(np.tile(bt["freq_train"], (mask.sum(), 1)), y[mask], "Frecuencias históricas")
                r.update({"modo": "referencia", "subconjunto": sname})
                tablas.append(r)
        if modo == "walk-forward":
            mk = has_odds
            for k, PP in [("mercado", Pm), ("mezcla", P["mezcla"]), ("ensamble", P["ensamble"])]:
                r = metrics(PP[mk], y[mk], NOMBRES[k] + " (solo partidos con cuotas)")
                r.update({"modo": "walk-forward", "subconjunto": "Ligas con cuotas"})
                tablas.append(r)
    return pd.DataFrame(tablas)


# %% [codigo] Predicción de partidos nuevos (cualquier jornada o fin de semana)
def impute_market(row, p_model, margin=0.05):
    """Probabilidades del mercado sin margen.
    Faltan 0 cuotas: se normalizan.
    Falta 1 cuota: esa probabilidad se toma del modelo y las otras dos conservan la proporción del mercado.
    Faltan 2 cuotas: la conocida se descuenta con un margen típico de 5% y el resto se reparte según el modelo."""
    o = np.array([row.get("cuota_local", np.nan), row.get("cuota_empate", np.nan), row.get("cuota_visita", np.nan)], float)
    known = np.isfinite(o)
    pm = np.asarray(p_model, float)
    if known.sum() == 0:
        return None, "sin cuotas"
    p = np.where(known, 1 / np.where(known, o, 1), np.nan)
    if known.sum() == 3:
        return p / p.sum(), "completo"
    if known.sum() == 2:
        k = ~known
        p[k] = pm[k]
        p[known] = p[known] / p[known].sum() * (1 - pm[k].sum())
        return p, "imputado (1 cuota)"
    p[known] = p[known] / (1 + margin)
    rest = 1 - p[known].sum()
    p[~known] = rest * pm[~known] / pm[~known].sum()
    return p, "imputado (2 cuotas)"


def current_state(df, seeds, dc_kwargs=None, ref_date=None):
    ref_date = pd.Timestamp(ref_date) if ref_date is not None else df.date.max() + pd.Timedelta(days=1)
    eh, ea, elo = run_elo(df, seeds)
    elo_now = dict(elo.r)
    dc = DixonColes(**(dc_kwargs or {})).fit(df, ref_date, elo_now)
    long = pd.concat([pd.DataFrame({"date": df.date, "team": df.home, "gf": df.hg, "ga": df.ag,
                                    "pts": np.select([df.hg > df.ag, df.hg == df.ag], [3, 1], 0)}),
                      pd.DataFrame({"date": df.date, "team": df.away, "gf": df.ag, "ga": df.hg,
                                    "pts": np.select([df.ag > df.hg, df.ag == df.hg], [3, 1], 0)})]).sort_values("date")
    form = long.groupby("team").tail(5).groupby("team")[["gf", "ga", "pts"]].mean()
    last = long.groupby("team").date.max()
    return {"elo": elo, "dc": dc, "form": form, "last": last, "ref_date": ref_date}


def fixture_features(fx, st, ajustes=None):
    """Construye las variables de cada partido a predecir. ajustes: dict equipo -> puntos Elo (bajas)."""
    ajustes = ajustes or {}
    dc, elo = st["dc"], st["elo"]
    rows = []
    for r in fx.itertuples(index=False):
        d = pd.Timestamp(r.fecha)
        h, a, hf = r.local, r.visita, float(getattr(r, "factor_localia", 1.0))
        dh, da = ajustes.get(h, 0.0), ajustes.get(a, 0.0)
        eh0, ea0 = elo.get(h, d), elo.get(a, d)
        lh, la = dc.lambdas(h, a, hf, elo.r)
        lh *= math.exp(dc.a0 * dh / 100 + dc.d0 * da / 100)
        la *= math.exp(dc.a0 * da / 100 + dc.d0 * dh / 100)
        P = probs_1x2(score_matrix(lh, la, dc.rho))[0]
        f = st["form"]
        g = lambda t, c, dflt: float(f.loc[t, c]) if t in f.index else dflt
        rest = lambda t: min((d - st["last"][t]).days, 21) if t in st["last"].index else 7
        rows.append({"elo_h": eh0 + dh, "elo_a": ea0 + da, "elo_diff": eh0 + dh - ea0 - da, "hf": hf,
                     "is_euro": int(getattr(r, "competicion", "UCL") in ("UCL", "UEL", "UECL")),
                     "dc_lh": lh, "dc_la": la, "dc_ph": P[0], "dc_pd": P[1], "dc_pa": P[2],
                     "h_gf5": g(h, "gf", 1.35), "h_ga5": g(h, "ga", 1.35), "h_pts5": g(h, "pts", 1.35),
                     "a_gf5": g(a, "gf", 1.35), "a_ga5": g(a, "ga", 1.35), "a_pts5": g(a, "pts", 1.35),
                     "h_rest": rest(h), "a_rest": rest(a), "dc_known_h": h in dc.teams, "dc_known_a": a in dc.teams})
    X = pd.DataFrame(rows)
    X["pts5_diff"] = X.h_pts5 - X.a_pts5
    X["gd5_diff"] = (X.h_gf5 - X.h_ga5) - (X.a_gf5 - X.a_ga5)
    X["rest_diff"] = X.h_rest - X.a_rest
    return X


def predict_fixtures(fx, st, prod_models, weights, w_blend, ajustes=None, n_sims=100_000, sigma=0.12, verbose=True):
    X = fixture_features(fx, st, ajustes)
    keys = ["dc", "logit", "lineal", "poisson", "xgboost"]
    P = predict_all(prod_models, X)
    Wv = np.array([weights[k] for k in keys])
    P["ensamble"] = np.tensordot(Wv, np.stack([P[k] for k in keys]), 1)
    rho = st["dc"].rho
    out, sims = [], {}
    for i, r in enumerate(fx.reset_index(drop=True).itertuples(index=False)):
        pe = P["ensamble"][i]
        pm, estado = impute_market(r._asdict(), pe)
        pf = w_blend * pe + (1 - w_blend) * pm if pm is not None else pe
        lh, la = implied_lambdas(pf, rho, init=(X.dc_lh[i], X.dc_la[i]), total_anchor=X.dc_lh[i] + X.dc_la[i])
        mc = monte_carlo(lh, la, rho, n_sims=n_sims, sigma=sigma, seed=i)
        sims[f"{r.local} vs {r.visita}"] = mc
        row = {"fecha": r.fecha, "hora_CET": getattr(r, "hora_CET", ""), "local": r.local, "visita": r.visita,
               "elo_local": round(X.elo_h[i]), "elo_visita": round(X.elo_a[i])}
        for k in keys + ["ensamble"]:
            row.update({f"{k}_1": P[k][i][0], f"{k}_X": P[k][i][1], f"{k}_2": P[k][i][2]})
        row.update({"mercado_1": pm[0] if pm is not None else np.nan, "mercado_X": pm[1] if pm is not None else np.nan,
                    "mercado_2": pm[2] if pm is not None else np.nan, "cuotas": estado,
                    "final_1": pf[0], "final_X": pf[1], "final_2": pf[2],
                    "lambda_local": lh, "lambda_visita": la, "goles_dc": X.dc_lh[i] + X.dc_la[i], "goles_esp": mc["goles_esp"],
                    "over25": mc["over25"], "btts": mc["btts"],
                    "marcador_probable": max(mc["top_marcadores"], key=mc["top_marcadores"].get),
                    "top_marcadores": mc["top_marcadores"]})
        # valor esperado contra cuotas reales (no imputadas)
        best = None
        for j, lab in enumerate(["local", "empate", "visita"]):
            o = getattr(r, ["cuota_local", "cuota_empate", "cuota_visita"][j], np.nan)
            if o is not None and np.isfinite(o):
                ev = pe[j] * o - 1
                row[f"ev_{lab}"] = ev
                if best is None or ev > best[1]:
                    best = (lab, ev, o, pe[j])
        if best and best[1] > 0.05:
            kelly = max((best[3] * best[2] - 1) / (best[2] - 1), 0) * 0.25
            row["posible_valor"] = f"{best[0]} @ {best[2]:.2f} (EV {best[1]:+.0%}, Kelly/4 {kelly:.1%})"
        else:
            row["posible_valor"] = "-"
        out.append(row)
    return pd.DataFrame(out), sims, X


def standings(df_cur):
    rows = []
    for r in df_cur.itertuples(index=False):
        for t, gf, ga in ((r.home, r.hg, r.ag), (r.away, r.ag, r.hg)):
            rows.append({"equipo": t, "PJ": 1, "G": int(gf > ga), "E": int(gf == ga), "P": int(gf < ga), "GF": gf, "GC": ga,
                         "Pts": 3 * (gf > ga) + (gf == ga), "over25": int(r.hg + r.ag > 2), "btts": int(r.hg > 0 and r.ag > 0)})
    t = pd.DataFrame(rows).groupby("equipo").sum()
    t["DG"] = t.GF - t.GC
    t["over25_%"] = (100 * t.over25 / t.PJ).round(0)
    t["btts_%"] = (100 * t.btts / t.PJ).round(0)
    return t.drop(columns=["over25", "btts"]).sort_values(["Pts", "DG", "GF"], ascending=False)


def fixtures_df(partidos):
    fx = pd.DataFrame(partidos, columns=["fecha", "hora_CET", "local", "visita", "factor_localia",
                                         "cuota_local", "cuota_empate", "cuota_visita", "fuente_cuotas"])
    fx["competicion"] = "UCL"
    return fx


def train_production(df, X, bt, upto=None):
    """Modelos finales: se entrenan con TODAS las temporadas disponibles (características fuera de muestra)."""
    ok = X[["dc_ph", "dc_pa"]].notna().all(1)
    idx = df.index[ok]
    models = train_models(X, df, idx)
    models["xgboost"].params["n_estimators"] = bt["models"]["xgboost"].params["n_estimators"]
    models["xgboost"].fit(X.loc[idx], df.loc[idx, "res"].values)
    keys = ["dc", "logit", "lineal", "poisson", "xgboost"]
    P = bt["preds"]["walk-forward"]
    y = df.loc[bt["idx_test"], "res"].values
    w = fit_weights([P[k] for k in keys], y)
    return models, dict(zip(keys, w))


def proximos_partidos_ligas(dias=7, desde=None, divisiones=("E0", "SP1", "I1", "D1", "F1", "P1", "N1")):
    """Partidos de liga de los próximos días (modo fin de semana).
    1) football-data.co.uk/fixtures.csv (trae cuotas Bet365); 2) respaldo: calendario de openfootball (sin cuotas)."""
    desde = pd.Timestamp(desde) if desde is not None else pd.Timestamp.today().normalize()
    hasta = desde + pd.Timedelta(days=dias)
    try:
        raw = http_get(FD_BASE + "fixtures.csv", cache=False, timeout=20)
        f = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
        f["fecha"] = pd.to_datetime(f["Date"], dayfirst=True, errors="coerce")
        f = f[f.Div.isin(divisiones) & (f.fecha >= desde) & (f.fecha < hasta)]
        out = pd.DataFrame({"fecha": f.fecha.dt.strftime("%Y-%m-%d"), "hora_CET": f.get("Time", ""),
                            "local": f.HomeTeam, "visita": f.AwayTeam, "factor_localia": 1.0,
                            "cuota_local": f.get("B365H"), "cuota_empate": f.get("B365D"), "cuota_visita": f.get("B365A"),
                            "fuente_cuotas": "football-data (Bet365)", "competicion": f.Div})
        print(f"football-data fixtures.csv: {len(out)} partidos")
        return out.reset_index(drop=True)
    except Exception as e:
        print("fixtures.csv no disponible:", str(e)[:60], "-> calendario openfootball (sin cuotas)")
    of = load_openfootball_league("2026-27")
    of = of[of.hg.isna() & (of.date >= desde) & (of.date < hasta) & of["div"].isin(divisiones)]
    out = pd.DataFrame({"fecha": of.date.dt.strftime("%Y-%m-%d"), "hora_CET": of.time.fillna(""),
                        "local": [RESOLVER.resolve(n, c) for n, c in zip(of.home_raw, of.country)],
                        "visita": [RESOLVER.resolve(n, c) for n, c in zip(of.away_raw, of.country)],
                        "factor_localia": 1.0, "cuota_local": np.nan, "cuota_empate": np.nan, "cuota_visita": np.nan,
                        "fuente_cuotas": "sin cuotas", "competicion": of["div"].values})
    return out.reset_index(drop=True)


# %% [codigo] Gráficos
import matplotlib
import matplotlib.pyplot as plt

C_LOCAL, C_EMPATE, C_VISITA = "#2a78d6", "#c3c2b7", "#e34948"
C_S1, C_S2, C_S3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def _style(ax):
    ax.set_facecolor(SURF)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def plot_partidos(pred, titulo="Probabilidades finales 1X2", col="final", fn=None):
    n = len(pred)
    fig, ax = plt.subplots(figsize=(9, 0.42 * n + 1.2), facecolor=SURF)
    _style(ax)
    labels = [f"{r.local} vs {r.visita}" for r in pred.itertuples()]
    y = np.arange(n)[::-1]
    p1, px, p2 = pred[f"{col}_1"].values, pred[f"{col}_X"].values, pred[f"{col}_2"].values
    gap = 0.004
    ax.barh(y, p1 - gap, color=C_LOCAL, height=0.62, label="Gana local")
    ax.barh(y, px - gap, left=p1 + gap, color=C_EMPATE, height=0.62, label="Empate")
    ax.barh(y, p2 - gap, left=p1 + px + gap, color=C_VISITA, height=0.62, label="Gana visita")
    for yy, a, b, c in zip(y, p1, px, p2):
        for x0, w, txt_c in [(0, a, "white"), (a, b, INK), (a + b, c, "white")]:
            if w > 0.07:
                ax.text(x0 + w / 2, yy, f"{w:.0%}", ha="center", va="center", fontsize=8, color=txt_c)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9, color=INK)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title(titulo, loc="left", fontsize=12, color=INK)
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=9, borderaxespad=1.6)
    fig.tight_layout()
    if fn:
        fig.savefig(fn, dpi=160, facecolor=SURF)
    return fig


def plot_metricas(rep, metrica="accuracy", subconjunto="Champions League", fn=None):
    d = rep[(rep.subconjunto == subconjunto) & rep.modo.isin(["walk-forward", "congelado"])]
    modelos = [m for m in d.modelo.unique()]
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURF)
    _style(ax)
    yy = np.arange(len(modelos))[::-1]
    for k, (modo, c) in enumerate([("walk-forward", C_S1), ("congelado", C_S2)]):
        v = [d[(d.modelo == m) & (d.modo == modo)][metrica].mean() for m in modelos]
        ax.barh(yy + (0.2 if k == 0 else -0.2), v, height=0.36, color=c, label=modo)
        for y0, val in zip(yy + (0.2 if k == 0 else -0.2), v):
            ax.text(val, y0, f" {val:.1%}" if metrica == "accuracy" else f" {val:.3f}", va="center", fontsize=8, color=INK2)
    base = rep[(rep.subconjunto == subconjunto) & (rep.modo == "referencia")][metrica]
    if len(base):
        ax.axvline(base.iloc[0], color=MUTED, lw=1, ls="--")
        ax.text(base.iloc[0], yy[0] + 0.55, " sin modelo", color=MUTED, fontsize=8)
    ax.set_yticks(yy)
    ax.set_yticklabels(modelos, fontsize=9, color=INK)
    lo = d[metrica].min()
    ax.set_xlim(lo * 0.85 if metrica == "accuracy" else lo * 0.95, d[metrica].max() * 1.08)
    if metrica == "accuracy":
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    nom = {"accuracy": "Tasa de acierto", "log_loss": "Log loss (menor es mejor)", "rps": "RPS (menor es mejor)"}[metrica]
    ax.set_title(f"{nom}: {subconjunto}, temporadas de prueba 2024-25 y 2025-26", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    if fn:
        fig.savefig(fn, dpi=160, facecolor=SURF)
    return fig


def plot_calibracion(P, y, fn=None):
    t = calibration_table(P, y, bins=10)
    fig, ax = plt.subplots(figsize=(5.6, 4.6), facecolor=SURF)
    _style(ax)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--")
    for lab, c in [("local", C_LOCAL), ("empate", "#52514e"), ("visita", C_VISITA)]:
        d = t[(t.resultado == lab) & (t.n >= 30)]
        ax.plot(d.p_media, d.frecuencia, color=c, lw=2, marker="o", ms=5, label=lab)
    ax.set_xlabel("Probabilidad que dio el modelo", color=INK2, fontsize=9)
    ax.set_ylabel("Frecuencia real", color=INK2, fontsize=9)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Calibración del ensamble (2024-25 y 2025-26)", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    if fn:
        fig.savefig(fn, dpi=160, facecolor=SURF)
    return fig


def plot_roi(curvas, fn=None):
    fig, ax = plt.subplots(figsize=(8, 3.4), facecolor=SURF)
    _style(ax)
    ax.grid(axis="y", color=GRID, lw=0.6)
    for (lab, cur), c in zip(curvas.items(), [C_S1, C_S2, C_S3]):
        ax.plot(np.arange(len(cur)), cur, color=c, lw=2, label=lab)
        ax.text(len(cur) - 1, cur[-1], f" {cur[-1]:+.0f} u", color=INK2, fontsize=8, va="center")
    ax.axhline(0, color="#c3c2b7", lw=1)
    ax.set_xlabel("Partidos de liga en orden cronológico (2024-25 y 2025-26)", color=INK2, fontsize=9)
    ax.set_ylabel("Beneficio acumulado (unidades)", color=INK2, fontsize=9)
    ax.set_title("Apostar 1 unidad cuando el modelo ve valor contra Bet365", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.tight_layout()
    if fn:
        fig.savefig(fn, dpi=160, facecolor=SURF)
    return fig


# %% [codigo] Estadísticas del partido: córners, tarjetas, faltas, tiros y fueras de juego
from scipy.stats import nbinom

STATS = {"corners": ("h_corners", "a_corners", "Córners"), "yellow": ("h_yellow", "a_yellow", "Amarillas"),
         "red": ("h_red", "a_red", "Rojas"), "fouls": ("h_fouls", "a_fouls", "Faltas"),
         "shots": ("h_shots", "a_shots", "Tiros"), "sot": ("h_sot", "a_sot", "Tiros a puerta"),
         "offsides": ("h_off", "a_off", "Fueras de juego")}
LINEAS = {"goles": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5], "corners": [7.5, 8.5, 9.5, 10.5, 11.5, 12.5],
          "tarjetas": [2.5, 3.5, 4.5, 5.5, 6.5], "fouls": [19.5, 21.5, 23.5, 25.5],
          "shots": [21.5, 23.5, 25.5, 27.5], "sot": [6.5, 7.5, 8.5, 9.5, 10.5], "offsides": [1.5, 2.5, 3.5, 4.5]}


def stat_baselines(df, s, window=300):
    """Promedio de la liga por lado (local/visita) en los 300 partidos anteriores. Sin fuga de información."""
    h, a, _ = STATS[s]
    bh, ba = pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index)
    if h not in df or df[h].notna().sum() == 0:
        return bh, ba, {}
    dom = df[(df.is_euro == 0) & df[h].notna() & df[a].notna()].sort_values("date")
    last = {}
    for div, g in dom.groupby("div"):
        bh[g.index] = g[h].shift(1).rolling(window, min_periods=30).mean().values
        ba[g.index] = g[a].shift(1).rolling(window, min_periods=30).mean().values
        last[div] = (g[h].tail(window).mean(), g[a].tail(window).mean())
    return bh, ba, last


def stat_team_ratios(df, s, bh, ba, n=20, k=5.0):
    """Cuánto produce (fr) y cuánto permite (ar) cada equipo respecto al promedio de su liga.
    Media de los últimos n partidos, encogida hacia 1 con k partidos ficticios."""
    h, a, _ = STATS[s]
    ok = df[h].notna() & df[a].notna() & bh.notna() & ba.notna() & (bh > 0) & (ba > 0)
    d = df[ok]
    long = pd.concat([
        pd.DataFrame({"i": d.index, "date": d.date, "team": d.home, "side": "h", "fr": d[h] / bh[ok], "ar": d[a] / ba[ok]}),
        pd.DataFrame({"i": d.index, "date": d.date, "team": d.away, "side": "a", "fr": d[a] / ba[ok], "ar": d[h] / bh[ok]})
    ]).sort_values(["team", "date", "i"])
    g = long.groupby("team")
    for c in ["fr", "ar"]:
        sm = g[c].transform(lambda x: x.shift(1).rolling(n, min_periods=1).sum()).fillna(0)
        ct = g[c].transform(lambda x: x.shift(1).rolling(n, min_periods=1).count()).fillna(0)
        long[c + "_r"] = (sm + k) / (ct + k)
    tail = long.groupby("team").tail(n).groupby("team").agg(fr=("fr", "sum"), ar=("ar", "sum"), n=("fr", "size"),
                                                         ultimo=("date", "max"))
    tail["fr"], tail["ar"] = (tail.fr + k) / (tail.n + k), (tail.ar + k) / (tail.n + k)
    H, A = long[long.side == "h"].set_index("i"), long[long.side == "a"].set_index("i")
    feats = pd.DataFrame({"fr_h": H.fr_r, "ar_h": H.ar_r, "fr_a": A.fr_r, "ar_a": A.ar_r})
    return feats, tail


def _design(fr_self, ar_opp, elo_self_minus_opp, is_home):
    return np.c_[np.ones(len(fr_self)), np.log(fr_self), np.log(ar_opp), elo_self_minus_opp / 100.0, is_home]


def fit_poisson_offset(F, y, offset, l2=1e-2):
    def f(b):
        eta = F @ b + offset
        mu = np.exp(eta)
        return np.sum(mu - y * eta) + l2 * b @ b, F.T @ (mu - y) + 2 * l2 * b
    return minimize(f, np.zeros(F.shape[1]), jac=True, method="L-BFGS-B").x


class StatModel:
    """Para cada estadística: media = promedio de la competición x (producción propia)^b1 x (lo que permite el rival)^b2
    x exp(b3 * diferencia Elo). Dispersión binomial negativa con un factor común del partido (ritmo, árbitro)."""

    def fit(self, df, eh, ea, s, train_mask, ratios=None):
        h, a, _ = STATS[s]
        self.s = s
        bh, ba, self.last_base = stat_baselines(df, s)
        if not self.last_base:
            self.ok = False
            return self
        feats, self.tail = stat_team_ratios(df, s, bh, ba)
        idx = feats.index[train_mask[feats.index]]
        if len(idx) < 500:
            self.ok = False
            return self
        e_d = (eh - ea)[idx] if isinstance(eh, np.ndarray) else (eh[idx] - ea[idx])
        fh, fa = feats.loc[idx], df.loc[idx]
        F = np.r_[_design(fh.fr_h.values, fh.ar_a.values, e_d, np.ones(len(idx))),
                  _design(fh.fr_a.values, fh.ar_h.values, -e_d, np.zeros(len(idx)))]
        y = np.r_[fa[h].values, fa[a].values]
        off = np.log(np.r_[bh[idx].values, ba[idx].values])
        self.beta = fit_poisson_offset(F, y, off)
        mu = np.exp(F @ self.beta + off)
        n = len(idx)
        mh, ma, yh, ya = mu[:n], mu[n:], y[:n], y[n:]
        self.phi = max(np.sum((yh - mh) * (ya - ma)) / np.sum(mh * ma), 0.0)
        alpha_team = max(np.sum((y - mu) ** 2 - mu) / np.sum(mu ** 2), 0.0)
        self.alpha = max(alpha_team - self.phi, 0.0)
        self.home_share = float(np.mean(yh) / (np.mean(yh) + np.mean(ya)))
        self.feats, self.bh, self.ba, self.ok = feats, bh, ba, True
        return self

    def mu(self, fr_h, ar_h, fr_a, ar_a, elo_d, base_h, base_a):
        fr_h, ar_h, fr_a, ar_a = (np.atleast_1d(np.asarray(v, float)) for v in (fr_h, ar_h, fr_a, ar_a))
        elo_d = np.atleast_1d(np.asarray(elo_d, float))
        mh = np.exp(_design(fr_h, ar_a, elo_d, np.ones(len(fr_h))) @ self.beta) * base_h
        ma = np.exp(_design(fr_a, ar_h, -elo_d, np.zeros(len(fr_h))) @ self.beta) * base_a
        return mh, ma

    def total_dist(self, mh, ma):
        """Aproximación binomial negativa del total (media y varianza exactas del modelo)."""
        mt = mh + ma
        var = mt + self.alpha * (1 + self.phi) * (mh ** 2 + ma ** 2) + self.phi * mt ** 2
        a_t = np.clip((var - mt) / mt ** 2, 1e-6, None)
        nn = 1 / a_t
        return nn, nn / (nn + mt)

    def team(self, t):
        if t in self.tail.index:
            return float(self.tail.loc[t, "fr"]), float(self.tail.loc[t, "ar"]), int(self.tail.loc[t, "n"])
        return 1.0, 1.0, 0


def sim_counts(mh, ma, alpha, phi, n, rng):
    G = rng.gamma(1 / phi, phi, n) if phi > 1e-6 else np.ones(n)
    gh = rng.gamma(1 / alpha, alpha, n) if alpha > 1e-6 else np.ones(n)
    ga = rng.gamma(1 / alpha, alpha, n) if alpha > 1e-6 else np.ones(n)
    return rng.poisson(mh * G * gh), rng.poisson(ma * G * ga)


def fit_stat_models(df, eh, ea, train_mask):
    out = {}
    for s in STATS:
        m = StatModel().fit(df, eh, ea, s, train_mask)
        if m.ok:
            out[s] = m
    return out


def fit_halftime(df, X, train_mask):
    """Goles al descanso = fracción k de la tasa de gol del partido (Poisson). k se estima con datos."""
    ok = train_mask & df.ht_hg.notna() & X.dc_lh.notna()
    return float(df.loc[ok, "ht_hg"].sum() / X.loc[ok, "dc_lh"].sum()), float(df.loc[ok, "ht_ag"].sum() / X.loc[ok, "dc_la"].sum())


def stats_backtest(df, eh, ea, X, train_seasons, test_seasons):
    """Regla 3 + 2 para estadísticas: se entrena con 3 temporadas y se evalúa en las 2 siguientes (ligas con datos)."""
    train = df.season.isin(train_seasons).values
    models = fit_stat_models(df, eh, ea, pd.Series(train, index=df.index))
    filas = []
    test = df.season.isin(test_seasons)
    combos = {"Córners": ["corners"], "Tarjetas (amarillas + rojas)": ["yellow", "red"], "Faltas": ["fouls"],
              "Tiros": ["shots"], "Tiros a puerta": ["sot"]}
    linea = {"Córners": 9.5, "Tarjetas (amarillas + rojas)": 4.5, "Faltas": 23.5, "Tiros": 24.5, "Tiros a puerta": 8.5}
    for nombre, parts in combos.items():
        if not all(p in models for p in parts):
            continue
        m0 = models[parts[0]]
        idx = m0.feats.index[test[m0.feats.index]]
        y = sum(df.loc[idx, STATS[p][0]].values + df.loc[idx, STATS[p][1]].values for p in parts)
        mt, var_m, bt, var_b = 0, 0, 0, 0
        for p in parts:
            m = models[p]
            f = m.feats.loc[idx]
            mh, ma = m.mu(f.fr_h, f.ar_h, f.fr_a, f.ar_a, eh[idx] - ea[idx], m.bh[idx].values, m.ba[idx].values)
            bh_, ba_ = m.bh[idx].values, m.ba[idx].values
            for (h_, a_), acc in (((mh, ma), "m"), ((bh_, ba_), "b")):
                t = h_ + a_
                v = t + m.alpha * (1 + m.phi) * (h_ ** 2 + a_ ** 2) + m.phi * t ** 2
                if acc == "m":
                    mt, var_m = mt + t, var_m + v
                else:
                    bt, var_b = bt + t, var_b + v
        L = linea[nombre]
        res = {"estadística": nombre, "partidos": len(idx), "promedio real": y.mean(),
               "error abs. modelo": np.mean(np.abs(y - mt)), "error abs. promedio liga": np.mean(np.abs(y - bt)),
               "correlación": np.corrcoef(y, mt)[0, 1], "línea": L}
        for lab, mu_, var_ in (("modelo", mt, var_m), ("liga", bt, var_b)):
            a_t = np.clip((var_ - mu_) / mu_ ** 2, 1e-6, None)
            p_over = nbinom.sf(np.floor(L), 1 / a_t, (1 / a_t) / (1 / a_t + mu_))
            hit = (y > L)
            res[f"acierto O/U {lab}"] = ((p_over > 0.5) == hit).mean()
            res[f"log loss O/U {lab}"] = -np.mean(hit * np.log(np.clip(p_over, 1e-9, 1)) + (~hit) * np.log(np.clip(1 - p_over, 1e-9, 1)))
        filas.append(res)
    # goles al descanso
    k = fit_halftime(df, X, pd.Series(train, index=df.index))
    ok = test & df.ht_hg.notna() & X.dc_lh.notna()
    ok_tr = pd.Series(train, index=df.index) & df.ht_hg.notna()
    lht = k[0] * X.loc[ok, "dc_lh"].values + k[1] * X.loc[ok, "dc_la"].values
    yht = (df.loc[ok, "ht_hg"] + df.loc[ok, "ht_ag"]).values
    ytr = (df.loc[ok_tr, "ht_hg"] + df.loc[ok_tr, "ht_ag"]).values
    for L in (0.5, 1.5):
        p = poisson.sf(np.floor(L), lht)
        pb = (ytr > L).mean()
        hit = yht > L
        filas.append({"estadística": "Goles 1er tiempo", "partidos": int(ok.sum()), "promedio real": yht.mean(),
                      "error abs. modelo": np.mean(np.abs(yht - lht)), "error abs. promedio liga": np.mean(np.abs(yht - ytr.mean())),
                      "correlación": np.corrcoef(yht, lht)[0, 1], "línea": L,
                      "acierto O/U modelo": ((p > .5) == hit).mean(), "acierto O/U liga": ((pb > .5) == hit).mean(),
                      "log loss O/U modelo": -np.mean(hit * np.log(p) + (~hit) * np.log(1 - p)),
                      "log loss O/U liga": -np.mean(hit * np.log(pb) + (~hit) * np.log(1 - pb))})
    t = pd.DataFrame(filas)
    return t, models, k


def predict_stats(fx, pred, sims, X_fx, models, k_ht, promedios, arbitros=None, n_sims=100_000, seed=7):
    """Monte Carlo de goles extendidos, córners, tarjetas, faltas, tiros, tiros a puerta y fueras de juego."""
    arbitros = arbitros or {}
    rng = np.random.default_rng(seed)
    filas, lineas = [], []
    for i, r in enumerate(fx.reset_index(drop=True).itertuples(index=False)):
        key = f"{r.local} vs {r.visita}"
        comp = getattr(r, "competicion", "UCL")
        arb = arbitros.get(key, {})
        f_tar = float(arb.get("factor_tarjetas", 1.0))
        elo_d = X_fx.elo_h[i] - X_fx.elo_a[i]
        row = {"partido": key, "arbitro": arb.get("arbitro", "sin dato"), "factor_arbitro": f_tar}
        cobertura = []
        sim = {}
        for s, m in models.items():
            frh, arh, nh = m.team(r.local)
            fra, ara, na = m.team(r.visita)
            if comp in ("UCL", "UEL", "UECL"):
                tot = promedios[s]
                bh, ba = tot * m.home_share, tot * (1 - m.home_share)
            else:
                bh, ba = m.last_base.get(comp, (np.nan, np.nan))
            mh, ma = m.mu(frh, arh, fra, ara, elo_d, bh, ba)
            mh, ma = float(mh[0]), float(ma[0])
            if s in ("yellow", "red"):
                mh, ma = mh * f_tar, ma * f_tar
            if s == "fouls":
                mh, ma = mh * (1 + (f_tar - 1) / 2), ma * (1 + (f_tar - 1) / 2)
            sim[s] = sim_counts(mh, ma, m.alpha, m.phi, n_sims, rng)
            if s == "corners":
                cobertura = [nh, na]
        if "offsides" not in models and "shots" in sim:
            # sin datos de fuera de juego: proxy proporcional a la raíz del volumen de tiros esperado
            ms = models["shots"]
            sh = sim["shots"]
            base = promedios["offsides"] if comp in ("UCL", "UEL", "UECL") else promedios.get("offsides_liga", 3.6)
            esp_h, esp_a = sh[0].mean(), sh[1].mean()
            ref = promedios["shots"] if comp in ("UCL", "UEL", "UECL") else sum(ms.last_base.get(comp, (12.5, 10.5)))
            moh = base * 0.52 * (esp_h / (ref * 0.55)) ** 0.5
            moa = base * 0.48 * (esp_a / (ref * 0.45)) ** 0.5
            sim["offsides"] = sim_counts(moh, moa, 0.20, 0.05, n_sims, rng)
        g = sims[key]
        gh, ga = g["sims_h"], g["sims_a"]
        tg = gh + ga
        row.update({"goles_local": gh.mean(), "goles_visita": ga.mean(), "goles_total": tg.mean(),
                    "doble_1X": pred.final_1[i] + pred.final_X[i], "doble_X2": pred.final_X[i] + pred.final_2[i],
                    "doble_12": pred.final_1[i] + pred.final_2[i],
                    "dnb_local": pred.final_1[i] / (pred.final_1[i] + pred.final_2[i]),
                    "btts": ((gh > 0) & (ga > 0)).mean(), "cero_local": (ga == 0).mean(), "cero_visita": (gh == 0).mean()})
        for L in LINEAS["goles"]:
            row[f"goles_O{L}"] = (tg > L).mean()
        for L in (0.5, 1.5, 2.5):
            row[f"local_O{L}"], row[f"visita_O{L}"] = (gh > L).mean(), (ga > L).mean()
        lh_ht, la_ht = k_ht[0] * pred.lambda_local[i], k_ht[1] * pred.lambda_visita[i]
        row["ht_O0.5"] = 1 - poisson.pmf(0, lh_ht + la_ht)
        row["ht_O1.5"] = poisson.sf(1, lh_ht + la_ht)
        Mht = score_matrix(lh_ht, la_ht, 0.0)
        row["ht_1"], row["ht_X"], row["ht_2"] = probs_1x2(Mht)[0]
        for s, (yh, ya) in sim.items():
            row[f"{s}_local"], row[f"{s}_visita"], row[f"{s}_total"] = yh.mean(), ya.mean(), (yh + ya).mean()
            row[f"{s}_p10_p90"] = f"{int(np.percentile(yh + ya, 10))}-{int(np.percentile(yh + ya, 90))}"
        if "yellow" in sim and "red" in sim:
            th, ta = sim["yellow"][0] + sim["red"][0], sim["yellow"][1] + sim["red"][1]
            tt = th + ta
            row.update({"tarjetas_local": th.mean(), "tarjetas_visita": ta.mean(), "tarjetas_total": tt.mean(),
                        "p_roja": ((sim["red"][0] + sim["red"][1]) > 0).mean(),
                        "puntos_tarjeta": (10 * (sim["yellow"][0] + sim["yellow"][1]) + 25 * (sim["red"][0] + sim["red"][1])).mean(),
                        "mas_tarjetas_local": (th > ta).mean()})
            for L in LINEAS["tarjetas"]:
                row[f"tarjetas_O{L}"] = (tt > L).mean()
        for s in ("corners", "fouls", "shots", "sot", "offsides"):
            if s in sim:
                tt = sim[s][0] + sim[s][1]
                for L in LINEAS[s]:
                    row[f"{s}_O{L}"] = (tt > L).mean()
        if "corners" in sim:
            row["mas_corners_local"] = (sim["corners"][0] > sim["corners"][1]).mean()
            row["corners_local_O4.5"] = (sim["corners"][0] > 4.5).mean()
            row["corners_visita_O4.5"] = (sim["corners"][1] > 4.5).mean()
        row["partidos_con_estadisticas"] = f"{cobertura[0]}/{cobertura[1]}" if cobertura else "-"
        row["offsides_fuente"] = "modelo" if "offsides" in models else "proxy (promedio UCL x volumen de tiros)"
        filas.append(row)
    return pd.DataFrame(filas)


def plot_stats(est, fn=None):
    n = len(est)
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.36 * n + 1.4), facecolor=SURF, sharey=True)
    y = np.arange(n)[::-1]
    labels = est.partido.str.replace(" vs ", " - ")
    for ax, (pref, titulo) in zip(axes, [("corners", "Córners esperados"), ("tarjetas", "Tarjetas esperadas")]):
        _style(ax)
        l, v = est[f"{pref}_local"].values, est[f"{pref}_visita"].values
        ax.barh(y, l - 0.03, color=C_LOCAL, height=0.62, label="Local")
        ax.barh(y, v - 0.03, left=l + 0.03, color=C_VISITA, height=0.62, label="Visita")
        for yy, a, b in zip(y, l, v):
            ax.text(a + b + 0.15, yy, f"{a + b:.1f}", va="center", fontsize=8, color=INK2)
        ax.set_title(titulo, loc="left", fontsize=11, color=INK)
        ax.set_xlim(0, max(l + v) * 1.15)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(labels, fontsize=8.5, color=INK)
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.tight_layout()
    if fn:
        fig.savefig(fn, dpi=160, facecolor=SURF)
    return fig
