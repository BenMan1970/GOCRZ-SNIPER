"""Niveaux de référence (ouvertures) et classification de zone Premium/Discount."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from .indicators import is_valid_df
from .timeutil import midnight_ny, trading_week_start

# Tolérance entre l'ouverture théorique de la semaine et la 1re bougie disponible.
_WEEK_OPEN_GAP = timedelta(hours=2)


def midnight_open(df_m15: pd.DataFrame, now: datetime) -> float | None:
    """Open de la bougie M15 de 00:00 NY du jour courant (None si absente)."""
    if not is_valid_df(df_m15):
        return None
    target = pd.Timestamp(midnight_ny(now))
    if target not in df_m15.index:
        return None
    return float(df_m15.loc[target, "open"])


def weekly_open(df_m15: pd.DataFrame, now: datetime) -> float | None:
    """Open de la 1re bougie M15 après dimanche 17:00 NY (ouverture hebdomadaire).

    Calculée depuis le M15 : disponible dès l'ouverture de la semaine, alors que
    la bougie D du jour est incomplète (donc absente) dimanche soir et lundi.
    """
    if not is_valid_df(df_m15):
        return None
    start = pd.Timestamp(trading_week_start(now))
    bars = df_m15[df_m15.index >= start]
    if bars.empty or bars.index[0] - start > _WEEK_OPEN_GAP:
        return None
    return float(bars["open"].iloc[0])


@dataclass(frozen=True)
class Zone:
    label: str        # EXT HIGH | PREMIUM | EQUILIBRE | DISCOUNT | EXT LOW
    ref: str          # MO (midnight open) | D1 (milieu du range de la veille)
    premium: bool
    discount: bool

    def favorable(self, is_bull: bool) -> bool:
        """Zone favorable : on achète en discount, on vend en premium."""
        return self.discount if is_bull else self.premium


def classify_zone(
    price: float, mid_open: float | None, pdh: float, pdl: float
) -> Zone:
    """Zone du prix. Référence : midnight open ; repli : milieu du range D-1.

    EXT HIGH / EXT LOW ne sont attribués que si le prix est à la fois hors du
    range de la veille ET du bon côté de la référence (aucun cas contradictoire).
    """
    if mid_open is not None:
        ref, pivot = "MO", mid_open
    else:
        ref, pivot = "D1", (pdh + pdl) / 2.0

    if price > pdh and price > pivot:
        label = "EXT HIGH"
    elif price < pdl and price < pivot:
        label = "EXT LOW"
    elif price > pivot:
        label = "PREMIUM"
    elif price < pivot:
        label = "DISCOUNT"
    else:
        label = "EQUILIBRE"
    return Zone(
        label=label,
        ref=ref,
        premium=label in ("EXT HIGH", "PREMIUM"),
        discount=label in ("EXT LOW", "DISCOUNT"),
    )
