"""Offline fixture source for demos and UI tests (no network, no secrets)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from .oanda import EMPTY_DF, INSTRUMENT_UNAVAILABLE

ROOT = Path(__file__).resolve().parents[2]
DURATIONS = {
    "M15": timedelta(minutes=15),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D": timedelta(days=1),
    "W": timedelta(days=7),
    "M": timedelta(days=31),
}


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype("float64")
    return df


class FixtureSource:
    def __init__(self, root: Path | str | None = None, when: datetime | None = None):
        self.root = Path(root) if root else Path(
            os.environ.get("BLUESTAR_FIXTURES", ROOT / "fixtures")
        )
        self.when = when or datetime.now(UTC)
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}
        self.instruments = tuple(
            sorted(p.name.split("_M15")[0] for p in (self.root / "bulk").glob("*_M15.csv.gz"))
        )

    def frame(self, instrument: str, granularity: str) -> pd.DataFrame | None:
        key = (instrument, granularity)
        if key not in self._cache:
            path = self.root / "bulk" / f"{instrument}_{granularity}.csv.gz"
            if not path.exists():
                return None
            self._cache[key] = _read(path)
        return self._cache[key]

    def fetch(
        self, instrument: str, granularity: str, count: int
    ) -> tuple[pd.DataFrame, str | None]:
        if instrument not in self.instruments:
            return EMPTY_DF.copy(), INSTRUMENT_UNAVAILABLE
        full = self.frame(instrument, granularity)
        if full is None or full.empty:
            return EMPTY_DF.copy(), INSTRUMENT_UNAVAILABLE
        now = self.when.astimezone(UTC)
        closes = full.index.to_series().shift(-1)
        if len(full):
            closes.iloc[-1] = full.index[-1] + DURATIONS[granularity]
        complete = full[closes <= pd.Timestamp(now)]
        out = complete.tail(count)
        if out.empty:
            return EMPTY_DF.copy(), "Aucune bougie complète"
        return out.copy(), None
