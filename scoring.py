"""Scoring - arithmetic IDENTICAL to V16, thresholds centralized in config.

Component maxima: Trigger 30 + MTF 25 + Zone 15 + Midnight 3 + FVG 15 +
ADX 10 + ATR 5 = 103. Maluses: ADR -5, Counter-bias -20 (floor -25).
"""

from __future__ import annotations

from . import config


def trigger_points(mins_ago: int | None, flip_type: str | None) -> int:
    """Points for flip freshness in real elapsed minutes (V16 tiers)."""
    if flip_type is None or mins_ago is None:
        return 0
    if mins_ago <= 15:
        return 30
    if mins_ago <= 30:
        return 20
    if mins_ago <= 45:
        return 10
    return 0


def mtf_points(mtf_pct: int, mtf_dominant: str, flip_type: str | None) -> int:
    """Points for multi-timeframe alignment with the signal direction."""
    aligned = (flip_type == "BULL" and mtf_dominant == "Bullish") or (
        flip_type == "BEAR" and mtf_dominant == "Bearish"
    )
    if not aligned:
        return 0
    if mtf_pct >= 80:
        return 25
    if mtf_pct >= 65:
        return 18
    if mtf_pct >= 50:
        return 10
    return 5


def zone_points(
    signal_is_bull: bool,
    zone_discount: bool,
    zone_premium: bool,
    below_mid: bool,
    above_mid: bool,
    signal_is_bear: bool = False,
) -> int:
    """V16 parity: with no flip side, the Zone component is 0."""
    if signal_is_bull:
        return (
            config.SCORE_ZONE_PERFECT
            if zone_discount
            else (config.SCORE_ZONE_PARTIAL if below_mid else 0)
        )
    if signal_is_bear:
        return (
            config.SCORE_ZONE_PERFECT
            if zone_premium
            else (config.SCORE_ZONE_PARTIAL if above_mid else 0)
        )
    return 0


def fvg_points(
    signal_is_bull: bool,
    in_bull_fvg: bool,
    in_bear_fvg: bool,
    fvg_near_bull: bool,
    fvg_near_bear: bool,
    signal_is_bear: bool = False,
) -> int:
    """V16 parity: with no explicit flip side, the FVG component is 0."""
    if signal_is_bull:
        return 15 if in_bull_fvg else (7 if fvg_near_bull else 0)
    if signal_is_bear:
        return 15 if in_bear_fvg else (7 if fvg_near_bear else 0)
    return 0


def adx_points(
    adx_val: float,
    pdi_val: float,
    mdi_val: float,
    signal_is_bull: bool,
    signal_is_bear: bool = False,
) -> int:
    """V16 parity: direction counts only with an EXPLICIT flip side. With no
    flip (None), dir_ok is False and a strong ADX yields the neutral 3 pts."""
    adx_dir_ok = (signal_is_bull and pdi_val > mdi_val) or (
        signal_is_bear and mdi_val > pdi_val
    )
    if adx_val > 25 and adx_dir_ok:
        return 10
    if adx_val > 20 and adx_dir_ok:
        return 6
    if adx_val > 20:
        return 3
    return 0


def atr_points(atr_val: float, atr_mean: float) -> int:
    if atr_val >= atr_mean:
        return 5
    if atr_val >= atr_mean * 0.5:
        return 3
    return 0


def grade_for(score: int) -> str:
    for name, threshold in config.GRADE_THRESHOLDS:
        if score >= threshold:
            return name
    return "C"


def compute_score(
    flip_type: str | None,
    mins_ago: int | None,
    mtf_pct: int,
    mtf_dominant: str,
    zone_discount: bool,
    zone_premium: bool,
    below_mid: bool,
    above_mid: bool,
    in_bull_fvg: bool,
    in_bear_fvg: bool,
    fvg_near_bull: bool,
    fvg_near_bear: bool,
    adx_val: float,
    pdi_val: float,
    mdi_val: float,
    atr_val: float,
    atr_mean: float,
    midnight_bonus: bool = False,
    adr_consumed: float | None = None,
    bias_alignment: str = "ALIGNED",
) -> tuple[int, str, dict[str, int]]:
    """V16 scoring. Returns (score, grade, component detail dict)."""
    score = 0
    score_detail: dict[str, int] = {}

    signal_is_bull = flip_type == "BULL"
    signal_is_bear = flip_type == "BEAR"

    pts = trigger_points(mins_ago, flip_type)
    score += pts
    score_detail["Trigger"] = pts

    pts = mtf_points(mtf_pct, mtf_dominant, flip_type)
    score += pts
    score_detail["MTF"] = pts

    pts = zone_points(
        signal_is_bull,
        zone_discount,
        zone_premium,
        below_mid,
        above_mid,
        signal_is_bear,
    )
    score += pts
    score_detail["Zone"] = pts

    mb = config.SCORE_MIDNIGHT_MAX if midnight_bonus else 0
    score += mb
    score_detail["Midnight"] = mb

    pts = fvg_points(
        signal_is_bull,
        in_bull_fvg,
        in_bear_fvg,
        fvg_near_bull,
        fvg_near_bear,
        signal_is_bear,
    )
    score += pts
    score_detail["FVG"] = pts

    pts = adx_points(adx_val, pdi_val, mdi_val, signal_is_bull, signal_is_bear)
    score += pts
    score_detail["ADX"] = pts

    pts = atr_points(atr_val, atr_mean)
    score += pts
    score_detail["ATR"] = pts

    if adr_consumed is not None and adr_consumed > config.ADR_MALUS_THRESHOLD:
        score -= config.SCORE_ADR_MALUS
        score_detail["ADR Malus"] = -config.SCORE_ADR_MALUS
    else:
        score_detail["ADR Malus"] = 0

    if bias_alignment == "COUNTER":
        score -= config.SCORE_BIAS_MALUS
        score_detail["Bias Malus"] = -config.SCORE_BIAS_MALUS
    else:
        score_detail["Bias Malus"] = 0

    return score, grade_for(score), score_detail
