"""Indicateurs techniques (purs, sans I/O).

L'ADX est exposé comme une COURBE unique (force de tendance, sans direction).
Ses composantes directionnelles internes (mouvements haussier/baissier lissés)
ne sont que des intermédiaires de calcul : elles ne sont ni retournées ni
utilisées ailleurs dans le projet.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from .clock import Clock
from .logging_utils import LOGGER_NAME
from .timeutil import trading_day_start

logger = logging.getLogger(LOGGER_NAME)


def is_valid_df(df: pd.DataFrame | None, min_rows: int = 1) -> bool:
    return isinstance(df, pd.DataFrame) and len(df) >= min_rows


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


class QuantEngine:
    @staticmethod
    def wma(series: pd.Series, period: int) -> pd.Series:
        """Moyenne pondérée linéaire, vectorisée (NaN dans la fenêtre => NaN)."""
        arr = series.to_numpy(dtype=np.float64)
        out = np.full(len(arr), np.nan)
        if len(arr) >= period:
            weights = np.arange(1, period + 1, dtype=np.float64)
            out[period - 1:] = sliding_window_view(arr, period) @ weights / weights.sum()
        return pd.Series(out, index=series.index)

    @staticmethod
    def hma(series: pd.Series, period: int = 20) -> pd.Series:
        half = int(period / 2)
        root = int(np.sqrt(period))
        raw = 2 * QuantEngine.wma(series, half) - QuantEngine.wma(series, period)
        if raw.isna().all():
            return pd.Series(np.nan, index=series.index)
        return QuantEngine.wma(raw, root)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        prev_close = df["close"].shift(1)
        true_range = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return true_range.ewm(alpha=1 / period, adjust=False).mean()

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Courbe ADX de Wilder (force de tendance 0-100, sans direction)."""
        up_move = df["high"].diff()
        down_move = -df["low"].diff()
        pos_move = pd.Series(
            np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
            index=df.index, dtype=np.float64,
        )
        neg_move = pd.Series(
            np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
            index=df.index, dtype=np.float64,
        )
        alpha = 1 / period
        safe_atr = QuantEngine.atr(df, period).replace(0, np.nan)
        pos_line = 100 * pos_move.ewm(alpha=alpha, adjust=False).mean() / safe_atr
        neg_line = 100 * neg_move.ewm(alpha=alpha, adjust=False).mean() / safe_atr
        spread = (pos_line - neg_line).abs()
        total = (pos_line + neg_line).replace(0, np.nan)
        return (100 * spread / total).ewm(alpha=alpha, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        out = pd.Series(np.nan, index=series.index, dtype=float)
        flat = avg_loss == 0
        out[flat] = 100.0
        valid = ~flat & avg_loss.notna() & avg_gain.notna()
        out[valid] = 100 - (100 / (1 + avg_gain[valid] / avg_loss[valid]))
        return out


def swing_points(series: pd.Series, wing: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Positions des pivots hauts/bas confirmés (`wing` bougies de chaque côté).

    Sur un plateau de valeurs égales, seul le premier point est retenu
    (pas de doublons adjacents). Les `wing` dernières bougies ne peuvent pas
    être confirmées : c'est voulu (pas de look-ahead).
    """
    arr = series.to_numpy(dtype=np.float64)
    if len(arr) < 2 * wing + 1:
        return np.array([], dtype=int), np.array([], dtype=int)
    win = sliding_window_view(arr, 2 * wing + 1)
    center, left, right = win[:, wing], win[:, :wing], win[:, wing + 1:]
    highs = (center > left.max(axis=1)) & (center >= right.max(axis=1))
    lows = (center < left.min(axis=1)) & (center <= right.min(axis=1))
    return np.flatnonzero(highs) + wing, np.flatnonzero(lows) + wing


def compute_adr(df_d: pd.DataFrame, period: int = 14) -> float:
    """Range journalier moyen sur les `period` dernières bougies D complètes."""
    if not is_valid_df(df_d, period):
        return float("nan")
    return float((df_d["high"] - df_d["low"]).iloc[-period:].mean())


def compute_adr_consumed(
    df_m15: pd.DataFrame, adr_value: float | None, clock: Clock
) -> float | None:
    """% du ADR déjà parcouru depuis l'ouverture du jour de trading (17:00 NY).

    Valeur non plafonnée : 130 % signifie que le range du jour dépasse l'ADR de 30 %.
    """
    if not is_valid_df(df_m15) or adr_value is None or not adr_value > 0:
        return None
    start = trading_day_start(clock.now())
    bars = df_m15[df_m15.index >= start]
    if bars.empty:
        return None
    day_range = float(bars["high"].max() - bars["low"].min())
    return round(day_range / adr_value * 100.0, 1)
