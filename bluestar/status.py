"""Explicit per-instrument status for the UI (never a silent failure)."""

from __future__ import annotations

from datetime import datetime

import pytz

from .config import NY_TZ

SIGNAL = "SIGNAL"
FILTERED = "FILTRÉ"
STALE = "DONNÉES PÉRIMÉES"
CLOSED = "MARCHÉ FERMÉ"
UNAVAILABLE = "INDISPONIBLE"
ERROR = "ERREUR"

_FILTER_PREFIXES = (
    "NO_HMA_FLIP",
    "BIAS_NEUTRAL",
    "PRICE_BELOW_HMA_ON_BULL",
    "PRICE_ABOVE_HMA_ON_BEAR",
    "HMA_NAN",
)


def is_weekend_closed(ticker: str, now: datetime) -> bool:
    """FX/metals/indices close Friday 17:00 NY and reopen Sunday 17:00 NY.

    Holidays are not modelled yet (documented residual risk).
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=pytz.UTC)
    ny = now.astimezone(pytz.timezone(NY_TZ))
    weekday = ny.weekday()
    minutes = ny.hour * 60 + ny.minute
    if weekday == 5:
        return True
    if weekday == 4 and minutes >= 17 * 60:
        return True
    return weekday == 6 and minutes < 17 * 60


def classify(ticker: str, reason: str | None, now: datetime) -> str:
    if reason is None:
        return SIGNAL
    if reason == "NO_RESULT":
        return ERROR
    # Typed codes emitted by the data layer / engine may be wrapped as
    # "FETCH_M15: INSTRUMENT_UNAVAILABLE: ..." ; match by containment.
    if "INSTRUMENT_UNAVAILABLE" in reason:
        return UNAVAILABLE
    if "STALE_DATA" in reason:
        return CLOSED if is_weekend_closed(ticker, now) else STALE
    if "BAD_REQUEST" in reason:
        return ERROR
    if "TOKEN" in reason or reason.startswith("FETCH_"):
        return ERROR
    if "EXCEPTION" in reason:
        return ERROR
    if "RATE_LIMITED" in reason or "TIMEOUT" in reason or "NETWORK_ERROR" in reason:
        return ERROR
    if reason.startswith(_FILTER_PREFIXES):
        return FILTERED
    # Unknown motif -> explicit error, never silently "filtered".
    return ERROR
