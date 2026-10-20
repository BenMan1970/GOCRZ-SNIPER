"""Signal detection: per-TF trends, MTF alignment, daily bias, FVG, HMA flips.

Behavior: arithmetic copied EXACTLY from the audited V16 implementation and
pinned by tests/golden (tf_trends, mtf_real, daily_bias, fvg, flips digests).
The only semantic change is clock INJECTION (AUDIT B-11): get_daily_bias_v2 now
receives a Clock instead of reading the wall clock, so the same instant always
reproduces the same bias.
"""

from __future__ import annotations

import numpy as np
import pytz
import pandas as pd

from . import config
from .clock import Clock, DEFAULT_CLOCK
from .indicators import adx, rsi, zlema


def is_valid_df(df: pd.DataFrame, min_rows: int = 1) -> bool:
    """True if df is a non-None DataFrame with at least min_rows rows."""
    return df is not None and isinstance(df, pd.DataFrame) and len(df) >= min_rows


# ---------------------------------------------------------------- tf trend
def trend_monthly_weekly(close: pd.Series, tf_type: str) -> tuple[int, float, str]:
    """M/W trend: SMA(min(200, n)) vs EMA50. Identical to V16 (SMA80 for M,
    SMA200 for W given fetch counts 120/300)."""
    min_bars = 52 if tf_type == "M" else 200
    if len(close) < min_bars:
        return 0, 40.0, "NEUT"
    sma_long = close.rolling(min(200, len(close))).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    if pd.isna(sma_long) or pd.isna(ema50):
        return 0, 40.0, "NEUT"
    if ema50 > sma_long:
        return 1, 75.0, "BULL"
    if ema50 < sma_long:
        return -1, 75.0, "BEAR"
    return 0, 40.0, "NEUT"


def trend_4h(df: pd.DataFrame, close: pd.Series) -> tuple[int, float, str]:
    """4H trend: EMA50 + DI dominance + UTC-date open vote (V16 semantics)."""
    score = 0
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    score += 1 if close.iloc[-1] > ema50 else -1
    _adx_s, pdi_s, mdi_s = adx(df, 14)
    score += 1 if pdi_s.iloc[-1] > mdi_s.iloc[-1] else -1
    # UTC-date grouping (audited: degenerate on 22.8% of instants; B-5).
    # Kept for behavior parity - the NY-session fix is a strategy decision.
    today = df.index[-1].date()
    mask = pd.Series([ts.date() for ts in df.index], index=df.index) == today
    day_rows = df[mask]
    if not day_rows.empty:
        score += 1 if close.iloc[-1] > day_rows["open"].iloc[0] else -1
    trend = 1 if score > 0 else (-1 if score < 0 else 0)
    strength = 90.0 if abs(score) == 3 else (70.0 if abs(score) >= 1 else 40.0)
    label = "BULL" if trend == 1 else ("BEAR" if trend == -1 else "NEUT")
    return trend, strength, label


def trend_intraday(close: pd.Series) -> tuple[int, float, str]:
    """D/1H/15m trend stack: EMA ladder + ZLEMA + RSI + MACD (V16)."""
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema9 = close.ewm(span=9, adjust=False).mean()
    zl = zlema(close, 50, 17)
    rsi_v = rsi(close, 14)
    macd_line = (
        close.ewm(span=12, adjust=False).mean()
        - close.ewm(span=26, adjust=False).mean()
    )
    sig = macd_line.ewm(span=9, adjust=False).mean()
    c = close.iloc[-1]
    bullish = (
        c > zl.iloc[-1]
        and ema9.iloc[-1] > ema21.iloc[-1]
        and ema21.iloc[-1] > ema50.iloc[-1]
        and not pd.isna(rsi_v.iloc[-1])
        and rsi_v.iloc[-1] > 50
        and macd_line.iloc[-1] > sig.iloc[-1]
    )
    bearish = (
        c < zl.iloc[-1]
        and ema9.iloc[-1] < ema21.iloc[-1]
        and ema21.iloc[-1] < ema50.iloc[-1]
        and not pd.isna(rsi_v.iloc[-1])
        and rsi_v.iloc[-1] < 50
        and macd_line.iloc[-1] < sig.iloc[-1]
    )
    base_str = min(80.0, abs(c - zl.iloc[-1]) / max(c, 1e-9) * 1000)
    strength = base_str if (bullish or bearish) else 30.0
    trend = 1 if bullish else (-1 if bearish else 0)
    label = "BULL" if trend == 1 else ("BEAR" if trend == -1 else "NEUT")
    return trend, strength, label


def get_tf_trend(df: pd.DataFrame, tf_type: str) -> tuple[int, float, str]:
    """Dispatch a timeframe to its trend stack - V16-identical."""
    if not is_valid_df(df, 50):
        return 0, 40.0, "NEUT"
    close = df["close"]
    if tf_type in ("M", "W"):
        return trend_monthly_weekly(close, tf_type)
    if tf_type == "4H":
        return trend_4h(df, close)
    return trend_intraday(close)


def compute_mtf_analysis(
    dfs: dict[str, pd.DataFrame],
) -> tuple[int, str, dict[str, dict[str, object]]]:
    """(alignment_pct, dominant, per-TF results) from raw TF trends (V16)."""
    results: dict[str, dict[str, object]] = {}
    for tf, df in dfs.items():
        t, s, lbl = get_tf_trend(df, tf)
        results[tf] = {"trend": t, "strength": s, "label": lbl}
    raw_bull = sum(
        config.TF_WEIGHTS[tf]
        for tf in config.TF_WEIGHTS
        if results.get(tf, {}).get("trend", 0) == 1
    )
    raw_bear = sum(
        config.TF_WEIGHTS[tf]
        for tf in config.TF_WEIGHTS
        if results.get(tf, {}).get("trend", 0) == -1
    )
    alignment_pct = round(max(raw_bull, raw_bear) / config.TOTAL_WEIGHT * 100)
    if raw_bull > raw_bear:
        dominant = "Bullish"
    elif raw_bear > raw_bull:
        dominant = "Bearish"
    else:
        dominant = "Neutral"
    return alignment_pct, dominant, results


# ---------------------------------------------------------------- daily bias
def _swing_points(
    values: np.ndarray, wing: int = config.SWING_WING
) -> tuple[list[int], list[int]]:
    """Indices of swing highs/lows with a +-wing plateau tolerance (V16)."""
    highs: list[int] = []
    lows: list[int] = []
    n = len(values)
    for i in range(wing, n - wing):
        window = values[i - wing : i + wing + 1]
        if abs(values[i] - window.max()) < 1e-9:
            highs.append(i)
        if abs(values[i] - window.min()) < 1e-9:
            lows.append(i)
    return highs, lows


def get_daily_bias_v2(
    df_d: pd.DataFrame, clock: Clock = DEFAULT_CLOCK, current_price: float | None = None
) -> tuple[str, dict[str, str | int | bool]]:
    """5-factor daily bias. Votes: Structure(2), EMA21/50, Weekly Open, Close
    J-1, EMA50 Slope. Max single side = 6 (audited). Majority camp needs >=3
    votes to be non-NEUTRAL; ANY (<=2, <=2) outcome is NEUTRAL."""
    if not is_valid_df(df_d, 60):
        return "NEUTRAL", {}

    close = df_d["close"]
    high = df_d["high"]
    low = df_d["low"]
    cur = current_price if current_price is not None else float(close.iloc[-1])

    votes_bull = 0
    votes_bear = 0
    detail: dict[str, str | int] = {}

    sh_idx, _ = _swing_points(high.to_numpy(dtype=np.float64))
    _, sl_idx = _swing_points(low.to_numpy(dtype=np.float64))

    struct_vote = "NEUTRAL"
    if len(sh_idx) >= 2 and len(sl_idx) >= 2:
        hh = high.iloc[sh_idx[-1]] > high.iloc[sh_idx[-2]]
        hl = low.iloc[sl_idx[-1]] > low.iloc[sl_idx[-2]]
        lh = high.iloc[sh_idx[-1]] < high.iloc[sh_idx[-2]]
        ll = low.iloc[sl_idx[-1]] < low.iloc[sl_idx[-2]]
        if hh and hl:
            struct_vote = "BULLISH"
            votes_bull += 2
        elif lh and ll:
            struct_vote = "BEARISH"
            votes_bear += 2
    detail["Structure"] = struct_vote

    ema50_series = close.ewm(span=50, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
    ema50 = ema50_series.iloc[-1]
    if cur > ema21 > ema50:
        detail["EMA 21/50"] = "BULLISH"
        votes_bull += 1
    elif cur < ema21 < ema50:
        detail["EMA 21/50"] = "BEARISH"
        votes_bear += 1
    else:
        detail["EMA 21/50"] = "NEUTRAL"

    # Weekly Open: OANDA D candles open Sunday 17:00 NY, so the current week's
    # Monday session starts Sunday 17:00 NY -> shift NY wall time by +7h so that
    # candle lands on Monday 00:00 (V16 convention, clock-injected).
    wo_vote = "NEUTRAL"
    try:
        idx_ny = (
            df_d.index.tz_convert(config.NY_TZ)
            if df_d.index.tz is not None
            else df_d.index.tz_localize("UTC").tz_convert(config.NY_TZ)
        )
        shifted_idx = idx_ny.tz_localize(None) + pd.Timedelta(hours=7)
        now_shifted = clock.now().astimezone(pytz.timezone(config.NY_TZ)).replace(
            tzinfo=None
        ) + pd.Timedelta(hours=7)
        monday_date = (now_shifted - pd.Timedelta(days=now_shifted.weekday())).date()
        mondays_mask = np.array([t.date() for t in shifted_idx]) == monday_date
        current_week_mondays = df_d[mondays_mask]
        if not current_week_mondays.empty:
            weekly_open = float(current_week_mondays["open"].iloc[0])
            wo_vote = "BULLISH" if cur > weekly_open else "BEARISH"
            if wo_vote == "BULLISH":
                votes_bull += 1
            else:
                votes_bear += 1
        detail["Weekly Open"] = wo_vote
    except Exception:
        detail["Weekly Open"] = "NEUTRAL"

    # df_d holds only COMPLETE candles, so iloc[-1] is yesterday - same
    # convention as PDH/PDL below (V16 fix, iloc[-2] removed).
    if is_valid_df(df_d, 1):
        midpoint = (float(high.iloc[-1]) + float(low.iloc[-1])) / 2
        if float(close.iloc[-1]) > midpoint:
            detail["Close J-1"] = "BULLISH"
            votes_bull += 1
        else:
            detail["Close J-1"] = "BEARISH"
            votes_bear += 1
    else:
        detail["Close J-1"] = "NEUTRAL"

    slope_vote = "NEUTRAL"
    slope_norm = 0.0
    try:
        if len(ema50_series) >= 6:
            atr_d_val = float(
                pd.concat(
                    [
                        high - low,
                        (high - close.shift()).abs(),
                        (low - close.shift()).abs(),
                    ],
                    axis=1,
                )
                .max(axis=1)
                .ewm(alpha=1 / 14, adjust=False)
                .mean()
                .iloc[-1]
            )
            slope_5d = float(ema50_series.iloc[-1] - ema50_series.iloc[-6])
            if atr_d_val > 0:
                slope_norm = slope_5d / atr_d_val
                if slope_norm > 0.05:
                    slope_vote = "BULLISH"
                    votes_bull += 1
                elif slope_norm < -0.05:
                    slope_vote = "BEARISH"
                    votes_bear += 1
        detail["EMA50 Slope"] = f"{slope_vote} ({slope_norm:+.3f})"
    except Exception:
        detail["EMA50 Slope"] = "NEUTRAL"

    detail["Votes"] = f"{votes_bull}B / {votes_bear}S"

    if votes_bull > votes_bear:
        bias = (
            "STRONG BULLISH"
            if votes_bull >= 5
            else ("BULLISH" if votes_bull >= 3 else "NEUTRAL")
        )
    elif votes_bear > votes_bull:
        bias = (
            "STRONG BEARISH"
            if votes_bear >= 5
            else ("BEARISH" if votes_bear >= 3 else "NEUTRAL")
        )
    else:
        bias = "NEUTRAL"
    return bias, detail


# ---------------------------------------------------------------- FVG
def detect_fvg(
    df: pd.DataFrame, price: float, lookback: int = config.FVG_LOOKBACK
) -> tuple[bool, bool, tuple[float, float] | None, tuple[float, float] | None]:
    """Fair value gaps with the V16 auto-threshold (mean bar range pct over the
    lookback+3 slice, x2). Returns (in_bull, in_bear, nearest_bull, nearest_bear)."""
    sub = df.iloc[-(lookback + 3) :].reset_index(drop=True)
    n = len(sub)
    if n < 3:
        return False, False, None, None

    denom = sub["low"].replace(0, 1e-9)
    range_pct = (sub["high"] - sub["low"]) / denom
    auto_thr = float(range_pct.expanding().mean().iloc[-1]) * config.FVG_THRESHOLD_K

    active_bulls: list[tuple[float, float]] = []
    active_bears: list[tuple[float, float]] = []

    for i in range(2, n):
        h0 = float(sub["high"].iloc[i])
        l0 = float(sub["low"].iloc[i])
        c0 = float(sub["close"].iloc[i])
        c1 = float(sub["close"].iloc[i - 1])
        h2 = float(sub["high"].iloc[i - 2])
        l2 = float(sub["low"].iloc[i - 2])

        # invalidation on close through the far edge
        active_bulls = [(b, t) for b, t in active_bulls if c0 >= b]
        active_bears = [(b, t) for b, t in active_bears if c0 <= t]

        if l0 > h2 and c1 > h2:
            size_pct = (l0 - h2) / max(h2, 1e-9)
            if size_pct >= auto_thr:
                active_bulls.insert(0, (h2, l0))
        elif h0 < l2 and c1 < l2:
            size_pct = (l2 - h0) / max(h0, 1e-9)
            if size_pct >= auto_thr:
                active_bears.insert(0, (h0, l2))

    in_bull = any(b <= price <= t for b, t in active_bulls)
    in_bear = any(b <= price <= t for b, t in active_bears)

    def _nearest(lst: list[tuple[float, float]]) -> tuple[float, float] | None:
        if not lst:
            return None
        return min(lst, key=lambda r: abs(price - (r[0] + r[1]) / 2))

    return in_bull, in_bear, _nearest(active_bulls), _nearest(active_bears)


# ---------------------------------------------------------------- HMA flip
def find_last_hma_flip(
    hma_series: pd.Series, max_lookback: int = config.FLIP_LOOKBACK_BARS
) -> tuple[str | None, int | None, int | None]:
    """Most recent HMA color FLIP within the lookback. Flat candles are ignored
    (neither GREEN nor RED). Returns (BULL|BEAR, candles_ago, idx) or (None,)*3."""
    colors: list[tuple[int, str]] = []
    n = len(hma_series)
    for i in range(n - 1, max(n - max_lookback - 2, 1), -1):
        v_curr = hma_series.iloc[i]
        v_prev = hma_series.iloc[i - 1]
        if pd.isna(v_curr) or pd.isna(v_prev):
            continue
        if v_curr == v_prev:
            continue
        colors.append((i, "GREEN" if v_curr > v_prev else "RED"))

    for j in range(len(colors) - 1):
        idx_curr, col_curr = colors[j]
        _, col_prev = colors[j + 1]
        if col_curr != col_prev:
            candles_ago = max(0, (n - 1) - idx_curr)
            return ("BULL" if col_curr == "GREEN" else "BEAR"), candles_ago, idx_curr
    return None, None, None


# ---------------------------------------------------------------- strength
def compute_currency_strength(dfs_h1: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Per-currency 0-10 score from EMA ladder + RSI votes on H1 closes (V16)."""
    raw = dict.fromkeys(config.CURRENCIES, 0.0)
    counts = dict.fromkeys(config.CURRENCIES, 0)

    for pair, df in dfs_h1.items():
        if not is_valid_df(df, 60):
            continue
        parts = pair.split("_")
        if len(parts) != 2:
            continue
        base, quote = parts[0], parts[1]
        if base not in config.CURRENCIES or quote not in config.CURRENCIES:
            continue
        close = df["close"]
        ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
        ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        rsi_v = rsi(close, 14).iloc[-1]
        rsi_ok = not pd.isna(rsi_v)
        bullish = ema9 > ema21 > ema50 and rsi_ok and rsi_v > 50
        bearish = ema9 < ema21 < ema50 and rsi_ok and rsi_v < 50
        contrib = 1.0 if bullish else (-1.0 if bearish else 0.0)
        raw[base] += contrib
        raw[quote] -= contrib
        counts[base] += 1
        counts[quote] += 1

    scores = {}
    for c in config.CURRENCIES:
        scores[c] = raw[c] / counts[c] if counts[c] > 0 else 0.0
    vals = list(scores.values())
    s_min, s_max = min(vals), max(vals)
    spread = s_max - s_min
    if spread < 1e-8:
        return dict.fromkeys(config.CURRENCIES, 5.0)
    return {c: round((v - s_min) / spread * 10, 2) for c, v in scores.items()}


def get_strength_delta(
    ticker: str,
    strength_scores: dict[str, float] | None,
) -> float | None:
    parts = ticker.split("_")
    if len(parts) != 2:
        return None
    if not strength_scores:
        return None
    base, quote = parts[0], parts[1]
    sb = strength_scores.get(base)
    sq = strength_scores.get(quote)
    if sb is None or sq is None:
        return None
    return round(sb - sq, 2)


# ---------------------------------------------------------------- momentum
def compute_momentum_score(
    df_h4: pd.DataFrame, df_h1: pd.DataFrame, df_m15: pd.DataFrame, signal_is_bull: bool
) -> int:
    """Count of timeframes with ADX>=25 and DI agreement (V16)."""
    score = 0
    for df_src in (df_h4, df_h1, df_m15):
        if not is_valid_df(df_src, 20):
            continue
        adx_s, pdi_s, mdi_s = adx(df_src, 14)
        adx_v = float(adx_s.iloc[-1])
        di_ok = (
            (pdi_s.iloc[-1] > mdi_s.iloc[-1])
            if signal_is_bull
            else (mdi_s.iloc[-1] > pdi_s.iloc[-1])
        )
        if adx_v >= 25 and di_ok:
            score += 1
    return score


__all__ = [
    "compute_currency_strength",
    "compute_momentum_score",
    "compute_mtf_analysis",
    "detect_fvg",
    "find_last_hma_flip",
    "get_daily_bias_v2",
    "get_strength_delta",
    "get_tf_trend",
    "is_valid_df",
]
