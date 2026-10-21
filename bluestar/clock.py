"""Injectable clock. Business logic must never call datetime.now() directly."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo
from typing import Protocol


class Clock(Protocol):
    def now(self, tz: tzinfo | None = None) -> datetime:
        ...


class SystemClock:
    def now(self, tz: tzinfo | None = None) -> datetime:
        return datetime.now(tz or UTC)


class FixedClock:
    def __init__(self, when: datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        self._when = when

    def now(self, tz: tzinfo | None = None) -> datetime:
        if tz is None:
            return self._when.astimezone(UTC).replace(tzinfo=None)
        return self._when.astimezone(tz)
