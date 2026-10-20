"""Intraday context: midnight open, premium/discount zones, ADR consumption.

Semantics are V16-identical except clock INJECTION (B-11): 'today' derives from
the injected Clock, so replay reproduces exactly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .clock import Clock, DEFAULT_CLOCK, ny_date
from .indicators import adr as adr_of
from .signals import is_valid_df

import logging

log = logging.getLogger(__name__)



def compute_adr(df_d: pd.DataFrame, period: int = config.ADR_PERIOD) -> float:
    """Average daily range over the last `period` closed sessions.

    B-7 fix: the audited V16 read iloc[-(period+1):-1], which DROPPED the most
    recent closed session and lagged one day. fetch() keeps only complete
    candles, so iloc[-period:] is the correct window.
    """
    return adr_of(df_d, period)


def compute_adr_consumed(
    df_m15: pd.DataFrame, adr_value: float | None, clock: Clock = DEFAULT_CLOCK
) -> float | None:
    """Range consumed today since the NY-midnight session open, as % of ADR."""
    if not is_valid_df(df_m15) or adr_value is None or adr_value <= 0:
        return None
    try:
        idx = (
            df_m15.index
            if df_m15.index.tz is not None
            else df_m15.index.tz_localize("UTC")
        )
        today_ny = ny_date(clock.now())
        idx_ny = idx.tz_convert(config.NY_TZ)
        mask = np.array([t.date() for t in idx_ny]) == today_ny
        today_bars = df_m15[mask]
        if today_bars.empty:
            return None
        today_h = float(today_bars["high"].max())
        today_l = float(today_bars["low"].min())
        consumed = (today_h - today_l) / adr_value * 100.0
        return round(min(consumed, 100.0), 1)
    except Exception as exc:
        log.warning("ADR consumed unavailable (%s): %s", type(exc).__name__, exc)
        return None


def midnight_open_of(
    df_m15: pd.DataFrame, clock: Clock = DEFAULT_CLOCK
) -> tuple[float | None, bool]:
    """(midnight_open, approximate).

    Prefers the 00:00 NY candle open; falls back to the first candle of the NY
    day and flags the value as approximate (V16 semantics, clock-injected).
    """
    approximate = False
    try:
        idx = (
            df_m15.index
            if getattr(df_m15.index, "tz", None) is not None
            else df_m15.index.tz_localize("UTC")
        )
        idx_ny = idx.tz_convert(config.NY_TZ)
        today_ny = ny_date(clock.now())
        dates = np.array([t.date() for t in idx_ny])
        hours = np.array([t.hour for t in idx_ny])
        minutes = np.array([t.minute for t in idx_ny])
        mn_mask = (dates == today_ny) & (hours == 0) & (minutes == 0)
        exact = df_m15[mn_mask]
        if not exact.empty:
            return float(exact["open"].iloc[0]), False
        today_mask = dates == today_ny
        fallback = df_m15[today_mask]
        if fallback.empty:
            return None, False
        first = idx_ny[today_mask][0]
        approximate = bool(first.hour != 0 or first.minute != 0)
        return float(fallback["open"].iloc[0]), approximate
    except Exception as exc:
        log.warning("midnight open unavailable (%s): %s", type(exc).__name__, exc)
        return None, False


def zone_state(
    price: float,
    midnight_open: float | None,
    midnight_approximate: bool,
    pdh: float,
    pdl: float,
) -> dict[str, str | float | bool]:
    """Compute the zone label + scoring booleans (V16 mutual exclusivity fix)."""
    if midnight_open is not None and not midnight_approximate:
        in_premium = (price > midnight_open) and (price <= pdh)
        in_discount = (price < midnight_open) and (price >= pdl)
        in_extended_high = price > pdh
        in_extended_low = price < pdl
        if in_extended_high:
            label = "EXT HIGH"
        elif in_extended_low:
            label = "EXT LOW"
        elif in_premium:
            label = "PREMIUM"
        elif in_discount:
            label = "DISCOUNT"
        else:
            label = "EQUILIBRE"
        zone_premium = label in ("EXT HIGH", "PREMIUM")
        zone_discount = label in ("EXT LOW", "DISCOUNT")
    else:
        d1_mid = (pdh + pdl) / 2.0
        in_discount = price < d1_mid
        in_premium = price > d1_mid
        zone_discount = in_discount
        zone_premium = in_premium
        label = (
            "DISCOUNT" if in_discount else ("PREMIUM" if in_premium else "EQUILIBRE")
        )
    return {
        "label": label,
        "zone_premium": zone_premium,
        "zone_discount": zone_discount,
        "above_mid": zone_premium,
        "below_mid": zone_discount,
    }


def midnight_bonus_for(
    flip_type: str | None,
    price: float,
    midnight_open: float | None,
    midnight_approximate: bool,
) -> bool:
    """Bull below the midnight open / bear above it (V16)."""
    if midnight_open is None or midnight_approximate or flip_type is None:
        return False
    if flip_type == "BULL":
        return price < midnight_open
    if flip_type == "BEAR":
        return price > midnight_open
    return False
