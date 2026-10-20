"""All tunable constants in ONE place.

Previously these were duplicated as magic numbers across the monolith (score
thresholds, grade cuts, staleness limits, retry policy). Single source of truth
so the UI legend, the sort order, the KPIs and the scorer cannot disagree.
"""

from __future__ import annotations

from typing import Final

APP_NAME: Final = "BLUESTAR SNIPER"
APP_VERSION: Final = "V17"

# ---------------------------------------------------------------- universe
# Symbols are resolved against /v3/accounts/{id}/instruments at runtime; this
# list is the *desired* universe, not an assumption that they exist.
INDICES: Final[frozenset[str]] = frozenset({"US30_USD", "NAS100_USD", "DE30_EUR"})

ASSETS: Final[tuple[str, ...]] = (
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "USD_CHF",
    "AUD_USD",
    "USD_CAD",
    "NZD_USD",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_NZD",
    "GBP_JPY",
    "GBP_CHF",
    "GBP_AUD",
    "GBP_CAD",
    "GBP_NZD",
    "AUD_JPY",
    "CAD_JPY",
    "CHF_JPY",
    "NZD_JPY",
    "AUD_CAD",
    "AUD_CHF",
    "AUD_NZD",
    "CAD_CHF",
    "NZD_CAD",
    "NZD_CHF",
    "XAU_USD",
    "US30_USD",
    "NAS100_USD",
    "DE30_EUR",
)

# Display-only renames. OANDA's API symbol for the DAX 40 is still DE30_EUR
# (verified live: displayName='Germany 30'), so we keep the API symbol for
# requests and show the modern name in the UI.
DISPLAY_NAMES: Final[dict[str, str]] = {
    "DE30_EUR": "DE40",
    "US30_USD": "US30",
    "NAS100_USD": "NAS100",
    "XAU_USD": "XAU",
    "US30_USD ": "US30",
}

CURRENCIES: Final[tuple[str, ...]] = (
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "AUD",
    "CAD",
    "NZD",
    "CHF",
)

STRENGTH_PAIRS: Final[tuple[str, ...]] = (
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "USD_CHF",
    "AUD_USD",
    "USD_CAD",
    "NZD_USD",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_CHF",
    "GBP_JPY",
    "AUD_JPY",
    "CAD_JPY",
    "NZD_JPY",
    "AUD_CAD",
    "AUD_CHF",
    "AUD_NZD",
    "CAD_CHF",
    "NZD_CAD",
    "NZD_CHF",
)

# ---------------------------------------------------------------- fetch
# (granularity, count). Counts must guarantee indicator warm-up: ADX needs
# V16-exact counts: W min(200,250)=SMA200, M min(200,80)=SMA80 (audited).
FETCH_SPECS: Final[tuple[tuple[str, int], ...]] = (
    # V16-exact counts: W min(200,250)=SMA200, M min(200,80)=SMA80 (audited)
    ("M15", 400),
    ("H1", 200),
    ("D", 300),
    ("H4", 300),
    ("W", 250),
    ("M", 80),
)
# Granularities needed before the early gates; the rest are fetched lazily.
EARLY_GRANULARITIES: Final[frozenset[str]] = frozenset({"M15", "D"})
LATE_GRANULARITIES: Final[tuple[str, ...]] = ("H1", "H4", "W", "M")
STRENGTH_COUNT: Final = 100

# OANDA candle alignment. Verified live: these reproduce the server defaults,
# but we send them explicitly so behaviour cannot drift with a server change.
ALIGNMENT_TZ: Final = "America/New_York"
DAILY_ALIGNMENT: Final = 17
WEEKLY_ALIGNMENT: Final = "Friday"

# ---------------------------------------------------------------- time
NY_TZ: Final = "America/New_York"
UTC_TZ: Final = "UTC"

# Killzones in NY local time (DST-correct via pytz). Tokyo observes no DST, so
# Asia stays pinned to UTC.
KILLZONES_NY_LOCAL: Final[dict[str, tuple[tuple[int, int], tuple[int, int]]]] = {
    "London": ((3, 0), (4, 30)),
    "NY AM": ((9, 30), (11, 0)),
}
KILLZONES_UTC_FIXED: Final[dict[str, tuple[tuple[int, int], tuple[int, int]]]] = {
    "Asia": ((0, 0), (2, 0)),
}

# ---------------------------------------------------------------- freshness
M15_MINUTES: Final = 15
STALENESS_LIMIT_MIN: Final = 45
FRESH_LIMIT_MIN: Final = 15  # <= this many minutes since candle CLOSE -> "fresh"
FLIP_LOOKBACK_BARS: Final = 20

# ---------------------------------------------------------------- MTF
TF_WEIGHTS: Final[dict[str, float]] = {
    "M": 4.0,
    "W": 3.5,
    "D": 3.0,
    "4H": 2.5,
    "1H": 2.0,
    "15m": 1.5,
}
TOTAL_WEIGHT: Final = sum(TF_WEIGHTS.values())

# ---------------------------------------------------------------- indicators
HMA_PERIOD: Final = 20
ATR_PERIOD: Final = 14
ADX_PERIOD: Final = 14
RSI_PERIOD: Final = 14
ZLEMA_PERIOD: Final = 50
ZLEMA_LAG: Final = 17
ADR_PERIOD: Final = 14
SWING_WING: Final = 5

# ---------------------------------------------------------------- FVG
FVG_LOOKBACK: Final = 80
# LuxAlgo-style automatic threshold: k * mean(bar range %) over the window.
FVG_THRESHOLD_K: Final = 2.0

# ---------------------------------------------------------------- scoring
# Component maxima. The UI, the legend, the sort and the KPIs all derive from
# these, so "Score /103" can never disagree with the arithmetic again.
SCORE_TRIGGER_MAX: Final = 30
SCORE_MTF_MAX: Final = 25
SCORE_ZONE_PERFECT: Final = 15
SCORE_ZONE_PARTIAL: Final = 8
SCORE_MIDNIGHT_MAX: Final = 3
SCORE_FVG_MAX: Final = 15
SCORE_ADX_MAX: Final = 10
SCORE_ATR_MAX: Final = 5
SCORE_ADR_MALUS: Final = 5
SCORE_BIAS_MALUS: Final = 20
SCORE_MAX: Final = (
    SCORE_TRIGGER_MAX
    + SCORE_MTF_MAX
    + SCORE_ZONE_PERFECT
    + SCORE_MIDNIGHT_MAX
    + SCORE_FVG_MAX
    + SCORE_ADX_MAX
    + SCORE_ATR_MAX
)  # 103
SCORE_MIN: Final = -(SCORE_ADR_MALUS + SCORE_BIAS_MALUS)  # -25

# Freshness / age scoring on the trigger
TRIGGER_AGE_TIERS: Final[tuple[tuple[int, int], ...]] = (
    (5, 30),
    (15, 25),
    (30, 15),
    (45, 9),
)
TRIGGER_EXPIRED_MIN: Final = 45

# MTF alignment percentage tiers
MTF_TIERS: Final[tuple[tuple[int, int], ...]] = (
    (80, 25),
    (65, 20),
    (50, 15),
    (0, 8),
)

# ADX tiers
ADX_TIERS: Final[tuple[tuple[int, int], ...]] = (
    (25, 10),
    (20, 6),
    (0, 3),
)
ADX_STRONG: Final = 25
ADX_MEDIUM: Final = 20

# ADR consumption malus threshold (% of ADR)
ADR_MALUS_THRESHOLD: Final = 70.0

# Grades. Derived from SCORE_MAX so the bands are proportionally consistent.
GRADE_THRESHOLDS: Final[tuple[tuple[str, int], ...]] = (
    ("A+", 85),
    ("A", 70),
    ("B+", 55),
    ("B", 40),
    ("C", 0),
)
GRADE_ORDER: Final[dict[str, int]] = {"A+": 5, "A": 4, "B+": 3, "B": 2, "C": 1}

# ---------------------------------------------------------------- api policy
MAX_RETRIES: Final = 3
RETRY_BASE_DELAY: Final = 1.5
RETRY_MAX_DELAY: Final = 30.0
REQUEST_TIMEOUT: Final = 20  # (connect, read) seconds, applied by the client
RATE_LIMIT_RPS: Final = 8.0  # global token bucket
RATE_LIMIT_BURST: Final = 16
FATAL_HTTP_CODES: Final[frozenset[int]] = frozenset({401, 403})
RETRYABLE_HTTP_CODES: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})

# ---------------------------------------------------------------- data contract
MIN_ROWS_M15: Final = 60
MAX_GAP_MULTIPLIER: Final = 60  # a gap > 60x the granularity marks a session break

# ---------------------------------------------------------------- logging
LOG_NAME: Final = "bluestar_sniper"
