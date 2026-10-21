"""Technical indicators. Behaviour is frozen by tests/golden."""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from .clock import Clock
from .config import NY_TZ

logger = logging.getLogger("bluestar_sniper")


def is_valid_df(df: pd.DataFrame | None, min_rows: int = 1) -> bool:
    return df is not None and isinstance(df, pd.DataFrame) and len(df) >= min_rows


class QuantEngine:
    @staticmethod
    def wma(series: pd.Series, period: int) -> pd.Series:
        weights = np.arange(1, period + 1, dtype=np.float64)
        w_sum = weights.sum()
        arr = series.to_numpy(dtype=np.float64)
        n = len(arr)
        out = np.full(n, np.nan)
        for i in range(period - 1, n):
            out[i] = np.dot(arr[i - period + 1: i + 1], weights) / w_sum
        return pd.Series(out, index=series.index)

    @staticmethod
    def hma(series: pd.Series, period: int = 20) -> pd.Series:
        half = int(period / 2)
        sqrt_p = int(np.sqrt(period))
        raw = 2 * QuantEngine.wma(series, half) - QuantEngine.wma(series, period)
        if raw.isna().all():
            return pd.Series(np.nan, index=series.index)
        return QuantEngine.wma(raw, sqrt_p)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        c = df["close"].shift(1)
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - c).abs(),
                (df["low"] - c).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.ewm(alpha=1 / period, adjust=False).mean()

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
        high = df["high"]
        low = df["low"]
        prev_high = high.shift(1)
        prev_low = low.shift(1)

        up_move = high - prev_high
        down_move = prev_low - low

        pdm = pd.Series(
            np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
            index=df.index,
            dtype=np.float64,
        )
        mdm = pd.Series(
            np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
            index=df.index,
            dtype=np.float64,
        )

        atr_v = QuantEngine.atr(df, period)
        pdm_s = pdm.ewm(alpha=1 / period, adjust=False).mean()
        mdm_s = mdm.ewm(alpha=1 / period, adjust=False).mean()

        safe_atr = atr_v.replace(0, np.nan)
        pdi = 100 * pdm_s / safe_atr
        mdi = 100 * mdm_s / safe_atr
        dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()
        return adx, pdi, mdi

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rsi_out = pd.Series(np.nan, index=series.index, dtype=float)
        mask_zero = avg_loss == 0
        rsi_out[mask_zero] = 100.0
        mask_nz = ~mask_zero & avg_loss.notna() & avg_gain.notna()
        rsi_out[mask_nz] = 100 - (100 / (1 + avg_gain[mask_nz] / avg_loss[mask_nz]))
        return rsi_out

    @staticmethod
    def zlema(series: pd.Series, period: int = 50, lag: int = 17) -> pd.Series:
        src = series + (series - series.shift(lag))
        return src.ewm(span=period, adjust=False).mean()


def compute_adr(df_d: pd.DataFrame, period: int = 14) -> float:
    if not is_valid_df(df_d, period):
        return float("nan")
    ranges = (df_d["high"] - df_d["low"]).iloc[-period:]
    return float(ranges.mean()) if not ranges.empty else float("nan")


def compute_adr_consumed(
    df_m15: pd.DataFrame,
    adr_value: float | None,
    clock: Clock,
) -> float | None:
    if not is_valid_df(df_m15) or adr_value is None or adr_value <= 0:
        return None
    try:
        ny_tz = pytz.timezone(NY_TZ)
        idx = pd.DatetimeIndex(df_m15.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        idx_ny = idx.tz_convert(ny_tz)
        today_ny = clock.now(ny_tz).date()

        mask = idx_ny.date == today_ny
        today_bars = df_m15[mask]
        if today_bars.empty:
            return None

        today_h = float(today_bars["high"].max())
        today_l = float(today_bars["low"].min())
        consumed = (today_h - today_l) / adr_value * 100.0
        return round(min(consumed, 100.0), 1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("compute_adr_consumed error: %s", exc)
        return None


def swing_points(series: pd.Series, wing: int = 5) -> tuple[list[int], list[int]]:
    highs: list[int] = []
    lows: list[int] = []
    arr = series.to_numpy(dtype=np.float64)
    n = len(arr)
    for i in range(wing, n - wing):
        window = arr[i - wing: i + wing + 1]
        if abs(arr[i] - window.max()) < 1e-9:
            highs.append(i)
        if abs(arr[i] - window.min()) < 1e-9:
            lows.append(i)
    return highs, lows


def daily_atr(df_d: pd.DataFrame, period: int = 14) -> float:
    high = df_d["high"]
    low = df_d["low"]
    close = df_d["close"]
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    return float(tr.ewm(alpha=1 / period, adjust=False).mean().iloc[-1])


def to_ny_times(index: pd.Index) -> pd.DatetimeIndex:
    idx = pd.to_datetime(index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    return idx.tz_convert(pytz.timezone(NY_TZ))


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=pytz.UTC)
    return value.astimezone(pytz.UTC)
