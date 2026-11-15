"""Signaux : tendance par timeframe, MTF, biais daily, force devise, ADX, HMA."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .clock import Clock
from .config import (
    ADX_MIN_BARS,
    ADX_PERIOD,
    ADX_TREND_MIN,
    CURRENCIES,
    MIN_BIAS_BARS,
    MIN_TREND_BARS,
    STRENGTH_PAIRS,
    TF_WEIGHTS,
    TOTAL_WEIGHT,
)
from .indicators import QuantEngine, ema, is_valid_df, swing_points
from .levels import weekly_open
from .logging_utils import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


# --------------------------------------------------------------------------- #
# Tendance d'un timeframe (définition UNIQUE pour M, W, D, 4H, 1H, 15m)
# --------------------------------------------------------------------------- #
def tf_trend(df: pd.DataFrame | None) -> int:
    """+1 haussier, -1 baissier, 0 neutre. Vote de 5 critères, majorité >= 3.

    1. close vs EMA50   2. EMA21 vs EMA50   3. EMA9 vs EMA21
    4. RSI14 vs 50      5. MACD(12,26) vs signal(9)
    """
    if not is_valid_df(df, MIN_TREND_BARS):
        return 0
    close = df["close"]
    ema9, ema21, ema50 = ema(close, 9), ema(close, 21), ema(close, 50)
    macd = ema(close, 12) - ema(close, 26)
    macd_signal = ema(macd, 9)
    rsi = QuantEngine.rsi(close, 14).iloc[-1]
    rsi_vote = 0.0 if pd.isna(rsi) else float(np.sign(rsi - 50.0))
    score = (
        np.sign(close.iloc[-1] - ema50.iloc[-1])
        + np.sign(ema21.iloc[-1] - ema50.iloc[-1])
        + np.sign(ema9.iloc[-1] - ema21.iloc[-1])
        + rsi_vote
        + np.sign(macd.iloc[-1] - macd_signal.iloc[-1])
    )
    if score >= 3:
        return 1
    if score <= -3:
        return -1
    return 0


@dataclass(frozen=True)
class MtfResult:
    pct: int                  # poids du camp dominant / poids total (0-100)
    dominant: int             # +1, -1, 0
    trends: dict[str, int]    # tendance par TF

    def describe(self) -> str:
        arrows = {1: "▲", -1: "▼", 0: "–"}
        return " ".join(f"{tf}{arrows[self.trends.get(tf, 0)]}" for tf in TF_WEIGHTS)


def compute_mtf(frames_by_tf: dict[str, pd.DataFrame | None]) -> MtfResult:
    trends = {tf: tf_trend(frames_by_tf.get(tf)) for tf in TF_WEIGHTS}
    bull_w = sum(w for tf, w in TF_WEIGHTS.items() if trends[tf] > 0)
    bear_w = sum(w for tf, w in TF_WEIGHTS.items() if trends[tf] < 0)
    if bull_w == bear_w:
        dominant = 0
    else:
        dominant = 1 if bull_w > bear_w else -1
    pct = int(round(max(bull_w, bear_w) / TOTAL_WEIGHT * 100))
    return MtfResult(pct=pct, dominant=dominant, trends=trends)


# --------------------------------------------------------------------------- #
# Biais daily : 7 votes, aucun garde-fou caché
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Bias:
    label: str                 # STRONG BULLISH | BULLISH | NEUTRAL | BEARISH | STRONG BEARISH
    bull: int
    bear: int
    detail: dict[str, str]

    @property
    def direction(self) -> int:
        if "BULLISH" in self.label:
            return 1
        if "BEARISH" in self.label:
            return -1
        return 0

    @property
    def is_strong(self) -> bool:
        return self.label.startswith("STRONG")

    def describe(self) -> str:
        return " · ".join(f"{k}: {v}" for k, v in self.detail.items())


def _structure(high: pd.Series, low: pd.Series, price: float) -> str:
    """BULLISH | BEARISH | BROKEN_BULL | BROKEN_BEAR | NEUTRAL (pivots wing=5)."""
    sh_idx, _ = swing_points(high)
    _, sl_idx = swing_points(low)
    if len(sh_idx) < 2 or len(sl_idx) < 2:
        return "NEUTRAL"
    h1, h0 = float(high.iloc[sh_idx[-1]]), float(high.iloc[sh_idx[-2]])
    l1, l0 = float(low.iloc[sl_idx[-1]]), float(low.iloc[sl_idx[-2]])
    if h1 > h0 and l1 > l0:                       # HH + HL
        return "BULLISH" if price >= l1 else "BROKEN_BULL"
    if h1 < h0 and l1 < l0:                       # LH + LL
        return "BEARISH" if price <= h1 else "BROKEN_BEAR"
    return "NEUTRAL"


def compute_daily_bias(
    df_d: pd.DataFrame, df_m15: pd.DataFrame, price: float, clock: Clock
) -> Bias | None:
    """Biais daily sur 7 votes (max 7). None si l'historique D est insuffisant.

    Votes : Structure (±2) · EMA 21/50 · Weekly Open · Clôture J-1 vs milieu de
    range · pente EMA50/ATR · pente HMA20 daily (±1 chacun).
    Seuils : directionnel si le camp gagnant a >= 3 votes ET plus que l'autre ;
    STRONG à partir de 5. Une structure D1 cassée interdit UNIQUEMENT de
    continuer dans le sens cassé : elle n'annule plus un retournement confirmé.
    """
    if not is_valid_df(df_d, MIN_BIAS_BARS):
        return None
    close, high, low = df_d["close"], df_d["high"], df_d["low"]
    bull = bear = 0
    detail: dict[str, str] = {}

    # 1. Structure (±2)
    structure = _structure(high, low, price)
    if structure == "BULLISH":
        bull += 2
    elif structure == "BEARISH":
        bear += 2
    detail["Structure"] = structure

    # 2. EMA 21/50
    ema21, ema50 = ema(close, 21), ema(close, 50)
    if price > ema21.iloc[-1] > ema50.iloc[-1]:
        bull += 1
        detail["EMA"] = "BULLISH"
    elif price < ema21.iloc[-1] < ema50.iloc[-1]:
        bear += 1
        detail["EMA"] = "BEARISH"
    else:
        detail["EMA"] = "NEUTRAL"

    # 3. Weekly Open (depuis le M15 : dispo dès dimanche soir)
    wo = weekly_open(df_m15, clock.now())
    if wo is None:
        detail["Weekly Open"] = "N/A"
    elif price > wo:
        bull += 1
        detail["Weekly Open"] = "BULLISH"
    elif price < wo:
        bear += 1
        detail["Weekly Open"] = "BEARISH"
    else:
        detail["Weekly Open"] = "NEUTRAL"

    # 4. Clôture de la veille vs milieu de son range
    mid = (float(high.iloc[-1]) + float(low.iloc[-1])) / 2.0
    last_close = float(close.iloc[-1])
    if last_close > mid:
        bull += 1
        detail["Close J-1"] = "BULLISH"
    elif last_close < mid:
        bear += 1
        detail["Close J-1"] = "BEARISH"
    else:
        detail["Close J-1"] = "NEUTRAL"

    # 5. Pente EMA50 sur 5 jours, normalisée par l'ATR daily
    atr_d = float(QuantEngine.atr(df_d, 14).iloc[-1])
    slope = (float(ema50.iloc[-1]) - float(ema50.iloc[-6])) / atr_d if atr_d > 0 else 0.0
    if slope > 0.05:
        bull += 1
        detail["Pente EMA50"] = "BULLISH"
    elif slope < -0.05:
        bear += 1
        detail["Pente EMA50"] = "BEARISH"
    else:
        detail["Pente EMA50"] = "NEUTRAL"

    # 6. Pente HMA20 daily (3 bougies)
    hma = QuantEngine.hma(close, 20).dropna()
    if len(hma) >= 4 and hma.iloc[-1] != hma.iloc[-4]:
        if hma.iloc[-1] > hma.iloc[-4]:
            bull += 1
            detail["HMA20"] = "BULLISH"
        else:
            bear += 1
            detail["HMA20"] = "BEARISH"
    else:
        detail["HMA20"] = "NEUTRAL"

    if bull > bear and bull >= 3:
        label = "STRONG BULLISH" if bull >= 5 else "BULLISH"
    elif bear > bull and bear >= 3:
        label = "STRONG BEARISH" if bear >= 5 else "BEARISH"
    else:
        label = "NEUTRAL"

    if (label.endswith("BULLISH") and structure == "BROKEN_BULL") or (
        label.endswith("BEARISH") and structure == "BROKEN_BEAR"
    ):
        label = "NEUTRAL"
        detail["Veto"] = f"structure {structure} : continuation interdite"
    elif structure in ("BROKEN_BULL", "BROKEN_BEAR"):
        detail["Structure"] = f"{structure} (retournement)"

    detail["Votes"] = f"{bull}B / {bear}S"
    return Bias(label=label, bull=bull, bear=bear, detail=detail)


# --------------------------------------------------------------------------- #
# Force devise
# --------------------------------------------------------------------------- #
def compute_currency_strength(
    frames_h1: dict[str, pd.DataFrame | None],
) -> dict[str, float]:
    """Score 0-10 par devise : tendance H1 de chaque paire (même définition que le MTF)."""
    totals = {c: 0.0 for c in CURRENCIES}
    counts = {c: 0 for c in CURRENCIES}
    for pair in STRENGTH_PAIRS:
        df = frames_h1.get(pair)
        if not is_valid_df(df, MIN_TREND_BARS):
            continue
        base, quote = pair.split("_")
        trend = tf_trend(df)
        totals[base] += trend
        totals[quote] -= trend
        counts[base] += 1
        counts[quote] += 1
    raw = {c: totals[c] / counts[c] for c in CURRENCIES if counts[c] > 0}
    if not raw:
        return {}
    lo, hi = min(raw.values()), max(raw.values())
    if hi - lo < 1e-9:
        return {c: 5.0 for c in raw}
    return {c: round((v - lo) / (hi - lo) * 10.0, 2) for c, v in raw.items()}


def strength_delta(ticker: str, scores: dict[str, float]) -> float | None:
    """Δ = force(base) - force(quote) ; None pour métaux et indices."""
    base, _, quote = ticker.partition("_")
    if base in scores and quote in scores:
        return round(scores[base] - scores[quote], 2)
    return None


# --------------------------------------------------------------------------- #
# ADX (courbe uniquement)
# --------------------------------------------------------------------------- #
def compute_adx_levels(
    df_h4: pd.DataFrame | None, df_h1: pd.DataFrame | None, df_m15: pd.DataFrame | None
) -> tuple[int, dict[str, float | None]]:
    """Nombre de TF (H4/H1/M15) dont l'ADX dépasse le seuil, et valeurs ADX."""
    values: dict[str, float | None] = {}
    for name, df in (("H4", df_h4), ("H1", df_h1), ("M15", df_m15)):
        if not is_valid_df(df, ADX_MIN_BARS):
            values[name] = None
            continue
        v = QuantEngine.adx(df, ADX_PERIOD).iloc[-1]
        values[name] = None if pd.isna(v) else round(float(v), 1)
    strong = sum(1 for v in values.values() if v is not None and v > ADX_TREND_MIN)
    return strong, values


# --------------------------------------------------------------------------- #
# HMA : direction courante et ancienneté du dernier flip
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HmaState:
    direction: int                 # +1 (montante) / -1 (descendante)
    bars_since_flip: int | None    # None : aucune bascule dans l'historique disponible
    flip_pos: int | None           # position de la 1re bougie de la couleur courante


def hma_state(hma: pd.Series) -> HmaState | None:
    """Couleur courante de la HMA et nombre de bougies depuis sa dernière bascule.

    Les pentes nulles prolongent la couleur précédente. `bars_since_flip = 0`
    signifie que la dernière bougie est la première de la nouvelle couleur.
    """
    values = hma.to_numpy(dtype=np.float64)
    valid = np.flatnonzero(~np.isnan(values))
    if len(valid) < 3:
        return None
    start = int(valid[0])
    slope = np.sign(np.diff(values[start:]))
    colour = pd.Series(slope).replace(0.0, np.nan).ffill().to_numpy()
    current = colour[-1]
    if np.isnan(current):
        return None
    other = np.flatnonzero(colour != current)       # NaN != current -> True
    if other.size == 0:
        return HmaState(int(current), None, None)
    # colour[k] est la couleur de la bougie (start + k + 1)
    flip_pos = start + int(other[-1]) + 2
    return HmaState(int(current), len(values) - 1 - flip_pos, flip_pos)
