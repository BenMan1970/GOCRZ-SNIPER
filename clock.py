"""Injectable clock - the single source of 'now'.

The monolith read datetime.now() in 7 places inside business logic, which made
replay, backtesting and deterministic tests impossible (AUDIT B-11). Every
time-dependent function now takes a Clock; the default is the real clock, and
tests/backtests pass a fixed one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

import pytz

from . import config


class Clock(Protocol):
    """Anything that can answer 'what time is it'."""

    def now(self) -> datetime:
        """Current instant, always tz-aware UTC."""
        ...


@dataclass(frozen=True)
class SystemClock:
    """Real wall clock. The production default."""

    def now(self) -> datetime:
        return datetime.now(pytz.UTC)


@dataclass(frozen=True)
class FixedClock:
    """A pinned instant, for replay and tests."""

    instant: datetime

    def __post_init__(self) -> None:
        if self.instant.tzinfo is None:
            raise ValueError("FixedClock requires a tz-aware instant")

    def now(self) -> datetime:
        return self.instant.astimezone(pytz.UTC)

    def advance(self, **kw: float) -> FixedClock:
        """Return a new clock moved forward. Keeps the original immutable."""
        return FixedClock(self.instant + timedelta(**kw))


DEFAULT_CLOCK: Clock = SystemClock()


def to_ny(ts: datetime) -> datetime:
    """Convert any aware datetime to New York local time."""
    return ts.astimezone(pytz.timezone(config.NY_TZ))


def ny_date(ts: datetime) -> date:
    """The NY calendar date of an instant - the 'midnight NY' day."""
    return to_ny(ts).date()


def minutes_in_day(ts: datetime) -> int:
    """Minutes since local midnight (NY for local windows, UTC for Tokyo)."""
    return ts.hour * 60 + ts.minute


def in_window(cur: int, start: tuple[int, int], end: tuple[int, int]) -> bool:
    """Inclusive window test on minutes-of-day, matching get_current_killzone()."""
    a = start[0] * 60 + start[1]
    b = end[0] * 60 + end[1]
    return a <= cur <= b


# Verbatim from the audited V16 table (audited golden pins badge/color strings).
KZ_STYLE: dict[str, tuple[str, str]] = {
    "London": ("LONDON", "#60a5fa"),
    "NY AM": ("NEW YORK AM", "#a78bfa"),
    "Asia": ("ASIA", "#5eead4"),
}


def current_killzone(clock: Clock = DEFAULT_CLOCK) -> str:
    """Name of the killzone containing 'now', or '' if none.

    NY-local windows are DST-correct via pytz; Asia stays pinned to UTC because
    Tokyo observes no DST (audited V16 semantics, inclusive bounds).
    """
    now = clock.now()
    t_ny = minutes_in_day(to_ny(now))
    for name, (start, end) in config.KILLZONES_NY_LOCAL.items():
        if in_window(t_ny, start, end):
            return name
    t_utc = minutes_in_day(now)
    for name, (start, end) in config.KILLZONES_UTC_FIXED.items():
        if in_window(t_utc, start, end):
            return name
    return ""


def killzone_badge(kz: str) -> str:
    return KZ_STYLE.get(kz, ("",))[0]


def killzone_color(kz: str) -> str:
    return KZ_STYLE.get(kz, ("", "#a8b2cc"))[1]


def minutes_since(ts: datetime, clock: Clock = DEFAULT_CLOCK) -> int:
    """Whole minutes elapsed between ts and now, never negative."""
    delta = clock.now() - ts
    return max(0, int(delta.total_seconds() // 60))
