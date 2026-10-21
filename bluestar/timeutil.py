"""Time, killzones and session helpers. All now() calls go through a Clock."""

from __future__ import annotations

from datetime import datetime

import pytz

from .clock import Clock
from .config import KILLZONES_NY_LOCAL, KILLZONES_UTC_FIXED, NY_TZ


def get_current_killzone(clock: Clock) -> str:
    ny_tz = pytz.timezone(NY_TZ)
    now_ny = clock.now(ny_tz)
    t_ny = now_ny.hour * 60 + now_ny.minute
    for name, (start, end) in KILLZONES_NY_LOCAL.items():
        s = start[0] * 60 + start[1]
        e = end[0] * 60 + end[1]
        if s <= t_ny <= e:
            return name
    now_utc = clock.now(pytz.UTC)
    t_utc = now_utc.hour * 60 + now_utc.minute
    for name, (start, end) in KILLZONES_UTC_FIXED.items():
        s = start[0] * 60 + start[1]
        e = end[0] * 60 + end[1]
        if s <= t_utc <= e:
            return name
    return ""


def ny_date(value: datetime) -> object:
    if value.tzinfo is None:
        value = value.replace(tzinfo=pytz.UTC)
    return value.astimezone(pytz.timezone(NY_TZ)).date()
