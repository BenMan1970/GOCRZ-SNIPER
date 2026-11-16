"""Score /100 transparent : chaque composante est tracée et explicable.

Composantes (poids dans config.SCORE_WEIGHTS) :
Trigger HMA 30 · MTF 25 · Zone 15 · Biais daily 10 · Force devise 10 · ADX 10.
Si la force devise est indisponible (métaux, indices), sa composante sort du
dénominateur : le score est renormalisé, l'instrument n'est jamais pénalisé.
ADX : non crédité si le signal est contraire au biais daily.
Malus : ADR > 70 % consommé (-5) · signal contraire au biais daily (-20).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import (
    ADR_MALUS,
    ADR_MALUS_THRESHOLD,
    ADX_POINTS,
    BIAS_POINTS,
    COUNTER_MALUS,
    FORCE_TIERS,
    GRADE_THRESHOLDS,
    MTF_ALIGNED_FLOOR,
    MTF_TIERS,
    SCORE_WEIGHTS,
    TRIGGER_TIERS,
)

ALIGNED = "ALIGNED"
NEUTRAL = "NEUTRAL"
COUNTER = "COUNTER"


@dataclass(frozen=True)
class ScoreResult:
    score: int
    grade: str
    earned: dict[str, int] = field(default_factory=dict)
    malus: dict[str, int] = field(default_factory=dict)
    max_available: int = 100

    def describe(self) -> str:
        parts = [f"{k} {v}/{SCORE_WEIGHTS[k]}" for k, v in self.earned.items()]
        if "Force" not in self.earned:
            parts.append("Force n/a")
        parts += [f"{k} {v}" for k, v in self.malus.items()]
        scale = "" if self.max_available == 100 else f" · renormalisé /{self.max_available}"
        return " · ".join(parts) + scale


def _tier(value: float, tiers: tuple[tuple[float, int], ...]) -> int:
    for threshold, points in tiers:
        if value >= threshold:
            return points
    return 0


def grade_for(score: int) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "C"


def compute_score(
    *,
    is_bull: bool,
    mins_ago: int | None,
    mtf_pct: int,
    mtf_aligned: bool,
    zone_favorable: bool,
    alignment: str,
    bias_strong: bool,
    strength_delta: float | None,
    adx_strong_count: int,
    adr_consumed: float | None,
) -> ScoreResult:
    earned: dict[str, int] = {}

    # Trigger : fraîcheur du flip HMA. Une continuation (mins_ago=None) vaut 0.
    if mins_ago is None:
        earned["Trigger"] = 0
    else:
        earned["Trigger"] = next((pts for lim, pts in TRIGGER_TIERS if mins_ago <= lim), 0)

    # MTF : n'est crédité que si le camp dominant est celui du signal.
    if not mtf_aligned:
        earned["MTF"] = 0
    else:
        earned["MTF"] = next((pts for lim, pts in MTF_TIERS if mtf_pct >= lim), MTF_ALIGNED_FLOOR)

    earned["Zone"] = SCORE_WEIGHTS["Zone"] if zone_favorable else 0

    if alignment == ALIGNED:
        earned["Bias"] = BIAS_POINTS["STRONG" if bias_strong else "NORMAL"]
    else:
        earned["Bias"] = 0

    available = sum(SCORE_WEIGHTS.values())
    if strength_delta is None:
        available -= SCORE_WEIGHTS["Force"]
    else:
        favorable = strength_delta if is_bull else -strength_delta
        earned["Force"] = _tier(favorable, FORCE_TIERS)

    # L'ADX (sans direction) mesure la force de la tendance en cours : pour un signal
    # COUNTER c'est la force de la tendance qu'il combat, donc aucun crédit.
    earned["ADX"] = 0 if alignment == COUNTER else ADX_POINTS[max(0, min(3, adx_strong_count))]

    base = round(sum(earned.values()) / available * 100)
    malus: dict[str, int] = {}
    if adr_consumed is not None and adr_consumed > ADR_MALUS_THRESHOLD:
        malus["ADR"] = -ADR_MALUS
    if alignment == COUNTER:
        malus["Contre-biais"] = -COUNTER_MALUS

    score = max(0, min(100, base + sum(malus.values())))
    return ScoreResult(
        score=score, grade=grade_for(score), earned=earned, malus=malus,
        max_available=available,
    )
