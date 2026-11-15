"""Fuseaux, killzones et bornes de session (jour/semaine de trading OANDA)."""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytz

from .clock import Clock
from .config import KILLZONES_NY_LOCAL, KILLZONES_UTC_FIXED, NY_TZ

_NY = pytz.timezone(NY_TZ)
_UTC = pytz.UTC


def _aware_utc(moment: datetime) -> datetime:
    return moment.replace(tzinfo=_UTC) if moment.tzinfo is None else moment


def to_ny(moment: datetime) -> datetime:
    return _aware_utc(moment).astimezone(_NY)


def killzone_at(moment: datetime) -> str:
    """Killzone active à `moment` ('' si aucune). Bornes [début, fin[."""
    ny_t = to_ny(moment).time()
    utc_t = _aware_utc(moment).astimezone(_UTC).time()
    for name, ((sh, sm), (eh, em)) in KILLZONES_NY_LOCAL.items():
        if time(sh, sm) <= ny_t < time(eh, em):
            return name
    for name, ((sh, sm), (eh, em)) in KILLZONES_UTC_FIXED.items():
        if time(sh, sm) <= utc_t < time(eh, em):
            return name
    return ""


def get_current_killzone(clock: Clock) -> str:
    return killzone_at(clock.now(_UTC))


def _ny_at(day, hour: int) -> datetime:
    return _NY.localize(datetime(day.year, day.month, day.day, hour, 0))


def trading_day_start(now: datetime) -> datetime:
    """Début (17:00 NY) du jour de trading contenant `now`."""
    ny = to_ny(now)
    day = ny.date()
    if ny.time() < time(17, 0):
        day -= timedelta(days=1)
    return _ny_at(day, 17)


def trading_week_start(now: datetime) -> datetime:
    """Dimanche 17:00 NY de la semaine de trading contenant `now`."""
    ny = to_ny(now)
    day = ny.date() - timedelta(days=(ny.weekday() + 1) % 7)
    start = _ny_at(day, 17)
    if start > ny:
        start = _ny_at(day - timedelta(days=7), 17)
    return start


def midnight_ny(now: datetime) -> datetime:
    """00:00 NY du jour calendaire courant (ouverture « midnight open » ICT)."""
    return _ny_at(to_ny(now).date(), 0)


def is_weekend_closed(now: datetime) -> bool:
    """FX/métaux/indices : fermés vendredi 17:00 NY -> dimanche 17:00 NY.

    Les jours fériés ne sont pas modélisés (risque résiduel documenté).
    """
    ny = to_ny(now)
    minutes = ny.hour * 60 + ny.minute
    wd = ny.weekday()
    return wd == 5 or (wd == 4 and minutes >= 17 * 60) or (wd == 6 and minutes < 17 * 60)
