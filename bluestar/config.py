"""Single source of truth for universe, weights, thresholds and timeframes."""

from __future__ import annotations

from typing import Final

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

DISPLAY_NAMES: Final[dict[str, str]] = {"DE30_EUR": "DE40"}

INDICES: Final[frozenset[str]] = frozenset({"US30_USD", "NAS100_USD", "DE30_EUR"})

CURRENCIES: Final[tuple[str, ...]] = (
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF",
)

STRENGTH_PAIRS: Final[tuple[str, ...]] = (
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF",
    "AUD_USD", "USD_CAD", "NZD_USD",
    "EUR_GBP", "EUR_JPY", "EUR_CHF",
    "GBP_JPY", "AUD_JPY", "CAD_JPY", "NZD_JPY",
    "AUD_CAD", "AUD_CHF", "AUD_NZD", "CAD_CHF", "NZD_CAD", "NZD_CHF",
)

TF_WEIGHTS: Final[dict[str, float]] = {
    "M": 4.0, "W": 3.5, "D": 3.0, "4H": 2.5, "1H": 2.0, "15m": 1.5,
}
TOTAL_WEIGHT: Final[float] = sum(TF_WEIGHTS.values())

FETCH_SPECS: Final[tuple[tuple[str, int], ...]] = (
    ("M15", 400), ("H1", 200), ("D", 300),
    ("H4", 300), ("W", 250), ("M", 80),
)

FRESHNESS_CHOICES: Final[tuple[int, ...]] = (15, 30, 45, 60)
DEFAULT_FRESHNESS_MIN: Final[int] = 30
STALENESS_LIMIT_MIN: Final[int] = 45

SCORE_MAX: Final[int] = 103
SCORE_MIN: Final[int] = -25
GRADE_THRESHOLDS: Final[tuple[tuple[int, str], ...]] = (
    (85, "A+"), (70, "A"), (55, "B+"), (40, "B"),
)
GRADE_ORDER: Final[dict[str, int]] = {"A+": 5, "A": 4, "B+": 3, "B": 2, "C": 1}
MIN_GRADE_MAP: Final[dict[str, int]] = {"Tous": 0, "B": 2, "B+": 3, "A": 4, "A+": 5}

MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 1.5

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

NY_TZ: Final[str] = "America/New_York"

KILLZONES_NY_LOCAL: Final[dict[str, tuple[tuple[int, int], tuple[int, int]]]] = {
    "London": ((3, 0), (4, 30)),
    "NY AM": ((9, 30), (11, 0)),
}
KILLZONES_UTC_FIXED: Final[dict[str, tuple[tuple[int, int], tuple[int, int]]]] = {
    "Asia": ((0, 0), (2, 0)),
}
