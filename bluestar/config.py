"""Source unique de vérité : univers, poids, seuils, timeframes.

Tout seuil métier vit ici. Aucun autre module ne doit coder un nombre magique
de scoring ou de filtrage.
"""

from __future__ import annotations

from typing import Final

# --------------------------------------------------------------------------- #
# Univers
# --------------------------------------------------------------------------- #
ASSETS: Final[tuple[str, ...]] = (
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF",
    "AUD_USD", "USD_CAD", "NZD_USD",
    "EUR_GBP", "EUR_JPY", "EUR_CHF",
    "EUR_AUD", "EUR_CAD", "EUR_NZD",
    "GBP_JPY", "GBP_CHF", "GBP_AUD",
    "GBP_CAD", "GBP_NZD",
    "AUD_JPY", "CAD_JPY", "CHF_JPY", "NZD_JPY",
    "AUD_CAD", "AUD_CHF", "AUD_NZD",
    "CAD_CHF", "NZD_CAD", "NZD_CHF",
    "XAU_USD",
    "US30_USD", "NAS100_USD", "DE30_EUR",
)

# Indices CFD : session avec fermeture quotidienne (ex. DAX : dernière bougie ~22h00 CET).
# Une dernière bougie ancienne y est NORMALE hors session : « marché fermé », pas une panne.
SESSION_BREAK_ASSETS: Final[tuple[str, ...]] = ("US30_USD", "NAS100_USD", "DE30_EUR")

DISPLAY_NAMES: Final[dict[str, str]] = {"DE30_EUR": "DE40"}

CURRENCIES: Final[tuple[str, ...]] = (
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF",
)

# Force devise : toutes les paires FX dont les deux jambes sont des devises
# suivies (28 paires => chaque devise apparaît exactement 7 fois, panier équilibré).
STRENGTH_PAIRS: Final[tuple[str, ...]] = tuple(
    a for a in ASSETS if all(leg in CURRENCIES for leg in a.split("_"))
)

# --------------------------------------------------------------------------- #
# Timeframes
# --------------------------------------------------------------------------- #
TF_WEIGHTS: Final[dict[str, float]] = {
    "M": 4.0, "W": 3.5, "D": 3.0, "4H": 2.5, "1H": 2.0, "15m": 1.5,
}
TOTAL_WEIGHT: Final[float] = sum(TF_WEIGHTS.values())

# Granularité OANDA -> clé de timeframe interne.
GRAN_TO_TF: Final[dict[str, str]] = {
    "M": "M", "W": "W", "D": "D", "H4": "4H", "H1": "1H", "M15": "15m",
}

# M15 = 600 bougies (~6,2 jours de trading) : couvre l'ouverture hebdomadaire
# (dimanche 17h NY) jusqu'au vendredi soir.
FETCH_SPECS: Final[tuple[tuple[str, int], ...]] = (
    ("M15", 600), ("H1", 200), ("D", 300),
    ("H4", 300), ("W", 250), ("M", 250),
)

MIN_TREND_BARS: Final[int] = 60     # historique minimal pour une tendance TF fiable
MIN_BIAS_BARS: Final[int] = 60      # historique daily minimal pour le biais
ADX_MIN_BARS: Final[int] = 50       # warm-up de l'ADX (EWM 14)

# --------------------------------------------------------------------------- #
# Trigger HMA
# --------------------------------------------------------------------------- #
HMA_PERIOD: Final[int] = 20
HMA_FLIP_LOOKBACK: Final[int] = 20          # un flip <= 20 bougies M15 = signal FLIP
CONTINUATION_ENABLED: Final[bool] = True    # setups sans flip récent (tendance)
# Tolérance (en ATR M15) quand le prix est du mauvais côté de la HMA : un prix à
# 2 pips d'une HMA descendante n'est pas un rejet, c'est un pullback sur la HMA.
HMA_PRICE_TOLERANCE_ATR: Final[float] = 0.25

FRESHNESS_CHOICES: Final[tuple[int, ...]] = (15, 30, 45)
DEFAULT_FRESHNESS_MIN: Final[int] = 30
STALENESS_LIMIT_MIN: Final[int] = 45        # dernière bougie M15 plus vieille => rejet

# --------------------------------------------------------------------------- #
# Force / ADX (courbe ADX uniquement, aucune notion de direction)
# --------------------------------------------------------------------------- #
ADX_PERIOD: Final[int] = 14
ADX_TREND_MIN: Final[float] = 25.0
FORCE_NEUTRAL_BAND: Final[float] = 1.5      # |Δ force devise| sous ce seuil = neutre

# --------------------------------------------------------------------------- #
# Score (/100). Les composantes indisponibles (Δ force devise n/a) sont
# retirées du dénominateur : le score est renormalisé, jamais pénalisé.
# --------------------------------------------------------------------------- #
SCORE_WEIGHTS: Final[dict[str, int]] = {
    "Trigger": 30, "MTF": 25, "Zone": 15, "Bias": 10, "Force": 10, "ADX": 10,
}
TRIGGER_TIERS: Final[tuple[tuple[int, int], ...]] = ((15, 30), (30, 20), (45, 10))
MTF_TIERS: Final[tuple[tuple[int, int], ...]] = ((80, 25), (65, 18), (50, 10))
MTF_ALIGNED_FLOOR: Final[int] = 5
BIAS_POINTS: Final[dict[str, int]] = {"STRONG": 10, "NORMAL": 7}
FORCE_TIERS: Final[tuple[tuple[float, int], ...]] = ((5.0, 10), (3.0, 7), (1.5, 4))
ADX_POINTS: Final[dict[int, int]] = {0: 0, 1: 4, 2: 7, 3: 10}

ADR_MALUS_THRESHOLD: Final[float] = 70.0    # % du range journalier consommé
ADR_MALUS: Final[int] = 5
COUNTER_MALUS: Final[int] = 20              # signal contraire au biais daily

GRADE_THRESHOLDS: Final[tuple[tuple[int, str], ...]] = (
    (85, "A+"), (70, "A"), (55, "B+"), (40, "B"),
)
GRADE_ORDER: Final[dict[str, int]] = {"A+": 5, "A": 4, "B+": 3, "B": 2, "C": 1}
MIN_GRADE_MAP: Final[dict[str, int]] = {"Tous": 0, "B": 2, "B+": 3, "A": 4, "A+": 5}

# --------------------------------------------------------------------------- #
# Réseau OANDA
# --------------------------------------------------------------------------- #
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 1.5
FETCH_WORKERS: Final[int] = 8
RATE_PER_S: Final[float] = 25.0
RATE_BURST: Final[float] = 10.0

OANDA_API_HOSTS: Final[dict[str, str]] = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}

API_CANDLE_PARAMS: Final[dict[str, str | int]] = {
    "price": "M",
    "alignmentTimezone": "America/New_York",
    "dailyAlignment": 17,
    "weeklyAlignment": "Friday",
}

# --------------------------------------------------------------------------- #
# Temps / killzones (bornes demi-ouvertes [début, fin[ )
# --------------------------------------------------------------------------- #
NY_TZ: Final[str] = "America/New_York"

KILLZONES_NY_LOCAL: Final[dict[str, tuple[tuple[int, int], tuple[int, int]]]] = {
    "London": ((3, 0), (4, 30)),
    "NY AM": ((9, 30), (11, 0)),
}
KILLZONES_UTC_FIXED: Final[dict[str, tuple[tuple[int, int], tuple[int, int]]]] = {
    "Asia": ((0, 0), (2, 0)),
}
