"""Technical indicators - arithmetic IDENTICAL to the audited V16 implementation.

Warm-up semantics are preserved exactly (including the documented asymmetry:
ATR/ADX emit from bar 0 with no min_periods, RSI/ADR are seeded). The golden
master pins every output, so any change here is caught by CI.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted moving average, linearly weighted 1..period."""
    weights = np.arange(1, period + 1)
    denom = float(weights.sum())
    out = series.rolling(period).apply(
        lambda x: float(np.dot(x, weights) / denom), raw=True
    )
    return pd.Series(out, index=series.index, dtype=float)


def hma(series: pd.Series, period: int | None = None) -> pd.Series:
    """Hull moving average: WMA(2*WMA(n/2) - WMA(n), sqrt(n))."""
    p = config.HMA_PERIOD if period is None else period
    raw = 2 * wma(series, int(p / 2)) - wma(series, p)
    return wma(raw, round(np.sqrt(p)))


def true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder true range: max(H-L, |H-Cprev|, |L-Cprev|)."""
    prev = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev).abs(),
            (df["low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(df: pd.DataFrame, period: int = config.ATR_PERIOD) -> pd.Series:
    """Average true range.

    NOTE (documented behaviour, preserved): no `min_periods`, so the series is
    populated from bar 0 with a heavily seeded EWM. Measured warm-up bias is
    ~+-7.8 ADX points at bar 27, decaying below 1e-4 by bar ~300. Fetch counts
    in config are sized to keep this out of the decision window.
    """
    return true_range(df).ewm(alpha=1 / period, adjust=False).mean()


def adx(
    df: pd.DataFrame, period: int = config.ADX_PERIOD
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder ADX with +DI/-DI.

    Directional movement is EWM-smoothed with the same alpha as the ATR; this is
    algebraically the Wilder recursion. Convergence to an independent Wilder
    implementation is <1e-6 after ~200 bars (tests/reference/).
    """
    high, low = df["high"], df["low"]
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
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

    alpha = 1 / period
    safe_atr = atr(df, period).replace(0, np.nan)
    pdi = 100 * pdm.ewm(alpha=alpha, adjust=False).mean() / safe_atr
    mdi = 100 * mdm.ewm(alpha=alpha, adjust=False).mean() / safe_atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=alpha, adjust=False).mean(), pdi, mdi


def rsi(series: pd.Series, period: int = config.RSI_PERIOD) -> pd.Series:
    """Wilder RSI in [0, 100]; a zero average loss maps to 100."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    out = pd.Series(np.nan, index=series.index, dtype=float)
    zero_loss = avg_loss == 0
    out[zero_loss] = 100.0
    nz = ~zero_loss & avg_loss.notna() & avg_gain.notna()
    out[nz] = 100 - (100 / (1 + avg_gain[nz] / avg_loss[nz]))
    return out


def zlema(
    series: pd.Series, period: int = config.ZLEMA_PERIOD, lag: int = config.ZLEMA_LAG
) -> pd.Series:
    """Zero-lag EMA: EMA(span=period) of the de-lagged series."""
    return (series + (series - series.shift(lag))).ewm(span=period, adjust=False).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram."""
    line = ema(series, fast) - ema(series, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def adr(df_daily: pd.DataFrame, period: int = config.ADR_PERIOD) -> float:
    """Average daily range over the last `period` CLOSED sessions.

    Mean of (high - low) over the final `period` rows - which, because fetch()
    keeps only complete candles, is exactly the last `period` closed sessions.
    (The audited V16 used iloc[-(period+1):-1], lagging one session; AUDIT B-7.)
    """
    if df_daily is None or len(df_daily) < 2:
        return float("nan")
    ranges = (df_daily["high"] - df_daily["low"]).iloc[-period:]
    if ranges.empty:
        return float("nan")
    return float(ranges.mean())
