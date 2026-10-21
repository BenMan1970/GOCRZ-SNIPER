"""Trend, bias, liquidity and currency-strength signals."""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from .clock import Clock
from .config import (
    CURRENCIES,
    NY_TZ,
    TF_WEIGHTS,
    TOTAL_WEIGHT,
)
from .indicators import QuantEngine, is_valid_df, swing_points

logger = logging.getLogger("bluestar_sniper")


def get_tf_trend(df: pd.DataFrame, tf_type: str) -> tuple[int, float, str]:
    if not is_valid_df(df, 50):
        return 0, 40.0, "NEUT"
    close = df["close"]

    if tf_type in ("M", "W"):
        min_bars = 52 if tf_type == "M" else 200
        if len(df) < min_bars:
            return 0, 40.0, "NEUT"
        sma200 = close.rolling(min(200, len(df))).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        if pd.isna(sma200) or pd.isna(ema50):
            return 0, 40.0, "NEUT"
        trend = 1 if ema50 > sma200 else (-1 if ema50 < sma200 else 0)
        strength = 75.0 if ema50 != sma200 else 40.0
        label = "BULL" if trend == 1 else ("BEAR" if trend == -1 else "NEUT")
        return trend, strength, label

    if tf_type == "4H":
        score = 0
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        score += 1 if close.iloc[-1] > ema50 else -1
        try:
            adx_s, pdi_s, mdi_s = QuantEngine.adx(df, 14)
            score += 1 if pdi_s.iloc[-1] > mdi_s.iloc[-1] else -1
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_tf_trend 4H ADX error: %s", exc)

        try:
            df_tz = df.copy()
            index = pd.DatetimeIndex(df_tz.index)
            if index.tz is None:
                index = index.tz_localize("UTC")
            df_tz.index = index
            ny_index = index.tz_convert(pytz.timezone(NY_TZ))
            today = ny_index[-1].date()
            mask = np.array([ts.date() for ts in ny_index]) == today
            day_rows = df_tz[mask]
            if not day_rows.empty:
                daily_open = day_rows["open"].iloc[0]
                score += 1 if close.iloc[-1] > daily_open else -1
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_tf_trend 4H daily_open error: %s", exc)

        trend = 1 if score > 0 else (-1 if score < 0 else 0)
        strength = 90.0 if abs(score) == 3 else (70.0 if abs(score) >= 1 else 40.0)
        label = "BULL" if trend == 1 else ("BEAR" if trend == -1 else "NEUT")
        return trend, strength, label

    ema50 = close.ewm(span=50, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema9 = close.ewm(span=9, adjust=False).mean()
    zl = QuantEngine.zlema(close, 50, 17)
    rsi_v = QuantEngine.rsi(close, 14)
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    c = close.iloc[-1]
    bullish = (
        c > zl.iloc[-1]
        and ema9.iloc[-1] > ema21.iloc[-1]
        and ema21.iloc[-1] > ema50.iloc[-1]
        and not pd.isna(rsi_v.iloc[-1])
        and rsi_v.iloc[-1] > 50
        and macd.iloc[-1] > sig.iloc[-1]
    )
    bearish = (
        c < zl.iloc[-1]
        and ema9.iloc[-1] < ema21.iloc[-1]
        and ema21.iloc[-1] < ema50.iloc[-1]
        and not pd.isna(rsi_v.iloc[-1])
        and rsi_v.iloc[-1] < 50
        and macd.iloc[-1] < sig.iloc[-1]
    )
    base_str = min(80.0, abs(c - zl.iloc[-1]) / max(c, 1e-9) * 1000)
    strength = base_str if (bullish or bearish) else 30.0
    trend = 1 if bullish else (-1 if bearish else 0)
    label = "BULL" if trend == 1 else ("BEAR" if trend == -1 else "NEUT")
    return trend, strength, label


def compute_mtf_analysis(
    dfs: dict[str, pd.DataFrame | None],
) -> tuple[int, str, dict[str, dict[str, object]]]:
    results: dict[str, dict[str, object]] = {}
    for tf, df in dfs.items():
        if df is None:
            trend, strength, label = 0, 40.0, "NEUT"
        else:
            trend, strength, label = get_tf_trend(df, tf)
        results[tf] = {"trend": trend, "strength": strength, "label": label}

    raw_bull = sum(
        TF_WEIGHTS[tf] for tf in TF_WEIGHTS
        if results.get(tf, {}).get("trend", 0) == 1
    )
    raw_bear = sum(
        TF_WEIGHTS[tf] for tf in TF_WEIGHTS
        if results.get(tf, {}).get("trend", 0) == -1
    )
    alignment_pct = round(max(raw_bull, raw_bear) / TOTAL_WEIGHT * 100)
    dominant = (
        "Bullish" if raw_bull > raw_bear
        else "Bearish" if raw_bear > raw_bull
        else "Neutral"
    )
    return alignment_pct, dominant, results


def get_daily_bias_v2(
    df_d: pd.DataFrame,
    current_price: float | None,
    clock: Clock,
) -> tuple[str, dict[str, str]]:
    if not is_valid_df(df_d, 60):
        return "NEUTRAL", {}

    close = df_d["close"]
    high = df_d["high"]
    low = df_d["low"]

    cur = current_price if current_price is not None else float(close.iloc[-1])

    votes_bull = 0
    votes_bear = 0
    detail: dict[str, str] = {}

    sh_idx, _ = swing_points(high)
    _, sl_idx = swing_points(low)

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

    wo_vote = "NEUTRAL"
    try:
        df_copy = df_d.copy()
        index = pd.DatetimeIndex(df_copy.index)
        if index.tz is None:
            index = index.tz_localize("UTC")
        df_copy.index = index
        ny_tz_wo = pytz.timezone(NY_TZ)
        shifted_idx = (
            index.tz_convert(ny_tz_wo).tz_localize(None)
            + pd.Timedelta(hours=7)
        )
        now_shifted = (
            clock.now(ny_tz_wo).replace(tzinfo=None) + pd.Timedelta(hours=7)
        )
        monday_date = (
            now_shifted - pd.Timedelta(days=now_shifted.weekday())
        ).date()
        current_week_mondays = df_copy[
            np.array([t.date() for t in shifted_idx]) == monday_date
        ]
        if not current_week_mondays.empty:
            weekly_open = float(current_week_mondays["open"].iloc[0])
            wo_vote = "BULLISH" if cur > weekly_open else "BEARISH"
            if wo_vote == "BULLISH":
                votes_bull += 1
            else:
                votes_bear += 1
        detail["Weekly Open"] = wo_vote
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_daily_bias_v2 Weekly Open error: %s", exc)
        detail["Weekly Open"] = "NEUTRAL"

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
                ).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_daily_bias_v2 EMA50 Slope error: %s", exc)
        detail["EMA50 Slope"] = "NEUTRAL"

    detail["Votes"] = f"{votes_bull}B / {votes_bear}S"

    if votes_bull > votes_bear:
        bias = (
            "STRONG BULLISH" if votes_bull >= 5
            else ("BULLISH" if votes_bull >= 3 else "NEUTRAL")
        )
    elif votes_bear > votes_bull:
        bias = (
            "STRONG BEARISH" if votes_bear >= 5
            else ("BEARISH" if votes_bear >= 3 else "NEUTRAL")
        )
    else:
        bias = "NEUTRAL"

    return bias, detail


def detect_fvg(
    df: pd.DataFrame,
    price: float,
    lookback: int = 80,
) -> tuple[bool, bool, tuple[float, float] | None, tuple[float, float] | None]:
    sub = df.iloc[-(lookback + 3):].reset_index(drop=True)
    n = len(sub)
    if n < 3:
        return False, False, None, None

    denom = sub["low"].replace(0, 1e-9)
    range_pct = (sub["high"] - sub["low"]) / denom
    auto_thr = float(range_pct.expanding().mean().iloc[-1]) * 2.0

    active_bulls: list[tuple[float, float]] = []
    active_bears: list[tuple[float, float]] = []

    for i in range(2, n):
        h0 = float(sub["high"].iloc[i])
        l0 = float(sub["low"].iloc[i])
        c0 = float(sub["close"].iloc[i])
        c1 = float(sub["close"].iloc[i - 1])
        h2 = float(sub["high"].iloc[i - 2])
        l2 = float(sub["low"].iloc[i - 2])

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

    def _nearest(
        lst: list[tuple[float, float]],
    ) -> tuple[float, float] | None:
        if not lst:
            return None
        return min(lst, key=lambda r: abs(price - (r[0] + r[1]) / 2))

    return in_bull, in_bear, _nearest(active_bulls), _nearest(active_bears)


def compute_currency_strength(dfs_h1: dict[str, pd.DataFrame]) -> dict[str, float]:
    raw = {c: 0.0 for c in CURRENCIES}
    counts = {c: 0 for c in CURRENCIES}

    for pair, df in dfs_h1.items():
        if not is_valid_df(df, 60):
            continue
        parts = pair.split("_")
        if len(parts) != 2:
            continue
        base, quote = parts[0], parts[1]
        if base not in CURRENCIES or quote not in CURRENCIES:
            continue

        close = df["close"]
        ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
        ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        rsi_v = QuantEngine.rsi(close, 14).iloc[-1]

        rsi_ok = not pd.isna(rsi_v)
        bullish = ema9 > ema21 > ema50 and rsi_ok and rsi_v > 50
        bearish = ema9 < ema21 < ema50 and rsi_ok and rsi_v < 50
        contrib = 1.0 if bullish else (-1.0 if bearish else 0.0)

        raw[base] += contrib
        raw[quote] -= contrib
        counts[base] += 1
        counts[quote] += 1

    scores = {}
    for c in CURRENCIES:
        scores[c] = raw[c] / counts[c] if counts[c] > 0 else 0.0

    vals = list(scores.values())
    s_min, s_max = min(vals), max(vals)
    spread = s_max - s_min
    if spread < 1e-8:
        return {c: 5.0 for c in CURRENCIES}
    return {c: round((v - s_min) / spread * 10, 2) for c, v in scores.items()}


def get_strength_delta(ticker: str, strength_scores: dict[str, float]) -> float | None:
    parts = ticker.split("_")
    if len(parts) != 2:
        return None
    base, quote = parts[0], parts[1]
    sb = strength_scores.get(base)
    sq = strength_scores.get(quote)
    if sb is None or sq is None:
        return None
    return round(sb - sq, 2)


def compute_momentum_score(
    df_h4: pd.DataFrame | None,
    df_h1: pd.DataFrame | None,
    df_m15: pd.DataFrame,
    signal_is_bull: bool,
) -> int:
    score = 0
    for df_src in (df_h4, df_h1, df_m15):
        if df_src is None or not is_valid_df(df_src, 20):
            continue
        try:
            adx_s, pdi_s, mdi_s = QuantEngine.adx(df_src, 14)
            adx_v = float(adx_s.iloc[-1])
            di_ok = (
                (pdi_s.iloc[-1] > mdi_s.iloc[-1]) if signal_is_bull
                else (mdi_s.iloc[-1] > pdi_s.iloc[-1])
            )
            if adx_v >= 25 and di_ok:
                score += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("compute_momentum_score error: %s", exc)
    return score


def find_last_hma_flip(
    hma_series: pd.Series,
    max_lookback: int = 20,
) -> tuple[str | None, int | None, int | None]:
    colors: list[tuple[int, str]] = []
    n = len(hma_series)
    for i in range(n - 1, max(n - max_lookback - 3, 1), -1):
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


def hourly_ny_bucket(value: datetime) -> datetime:
    """Kept for calendar tests; converts to NY wall time."""
    return value.astimezone(pytz.timezone(NY_TZ))
