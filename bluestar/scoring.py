"""Signal scoring. Weights/thresholds are frozen pending human validation."""

from __future__ import annotations

from .config import GRADE_THRESHOLDS


def grade_for(score: int) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
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
    score = 0
    score_detail: dict[str, int] = {}

    if flip_type is not None and mins_ago is not None:
        mins = mins_ago
        if mins <= 15:
            pts = 30
        elif mins <= 30:
            pts = 20
        elif mins <= 45:
            pts = 10
        else:
            pts = 0
    else:
        pts = 0
    score += pts
    score_detail["Trigger"] = pts

    signal_is_bull = flip_type == "BULL"
    signal_is_bear = flip_type == "BEAR"

    mtf_aligned = (
        (signal_is_bull and mtf_dominant == "Bullish")
        or (signal_is_bear and mtf_dominant == "Bearish")
    )
    if mtf_aligned:
        if mtf_pct >= 80:
            pts = 25
        elif mtf_pct >= 65:
            pts = 18
        elif mtf_pct >= 50:
            pts = 10
        else:
            pts = 5
    else:
        pts = 0
    score += pts
    score_detail["MTF"] = pts

    if signal_is_bull:
        pts = 15 if zone_discount else (8 if below_mid else 0)
    elif signal_is_bear:
        pts = 15 if zone_premium else (8 if above_mid else 0)
    else:
        pts = 0
    score += pts
    score_detail["Zone"] = pts

    if midnight_bonus:
        score += 3
        score_detail["Midnight"] = 3
    else:
        score_detail["Midnight"] = 0

    if signal_is_bull:
        pts = 15 if in_bull_fvg else (7 if fvg_near_bull else 0)
    elif signal_is_bear:
        pts = 15 if in_bear_fvg else (7 if fvg_near_bear else 0)
    else:
        pts = 0
    score += pts
    score_detail["FVG"] = pts

    adx_dir_ok = (
        (signal_is_bull and pdi_val > mdi_val)
        or (signal_is_bear and mdi_val > pdi_val)
    )
    if adx_val > 25 and adx_dir_ok:
        pts = 10
    elif adx_val > 20 and adx_dir_ok:
        pts = 6
    elif adx_val > 20:
        pts = 3
    else:
        pts = 0
    score += pts
    score_detail["ADX"] = pts

    if atr_val >= atr_mean:
        pts = 5
    elif atr_val >= atr_mean * 0.5:
        pts = 3
    else:
        pts = 0
    score += pts
    score_detail["ATR"] = pts

    if adr_consumed is not None and adr_consumed > 70:
        score -= 5
        score_detail["ADR Malus"] = -5
    else:
        score_detail["ADR Malus"] = 0

    if bias_alignment == "COUNTER":
        score -= 20
        score_detail["Bias Malus"] = -20
    else:
        score_detail["Bias Malus"] = 0

    return score, grade_for(score), score_detail
