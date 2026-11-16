"""Statut explicite par instrument pour l'UI (jamais d'échec silencieux)."""

from __future__ import annotations

from datetime import datetime

from .timeutil import is_weekend_closed

SIGNAL = "SIGNAL"
FILTERED = "FILTRÉ"
STALE = "DONNÉES PÉRIMÉES"
CLOSED = "MARCHÉ FERMÉ"
UNAVAILABLE = "INDISPONIBLE"
DENIED = "ACCÈS REFUSÉ"
INSUFFICIENT = "DONNÉES INSUFFISANTES"
ERROR = "ERREUR"

# Rejets métier (le scanner a fonctionné, le setup ne qualifie pas).
FILTER_PREFIXES = (
    "NO_HMA_FLIP",
    "PRICE_BELOW_HMA_ON_BULL",
    "PRICE_ABOVE_HMA_ON_BEAR",
    "HMA_NAN",
)


def classify(reason: str | None, now: datetime) -> str:
    if reason is None:
        return SIGNAL
    if reason == "NO_RESULT":
        return ERROR
    # Codes typés possiblement enveloppés ("FETCH_M15: INSTRUMENT_UNAVAILABLE: ...").
    if "INSTRUMENT_UNAVAILABLE" in reason:
        return UNAVAILABLE
    if "ACCESS_DENIED" in reason:
        return DENIED
    if reason.startswith("INSUFFICIENT_DATA"):
        return INSUFFICIENT
    if "STALE_DATA" in reason:
        return CLOSED if is_weekend_closed(now) else STALE
    if reason.startswith(FILTER_PREFIXES):
        return FILTERED
    # Tout le reste (BAD_REQUEST, TOKEN, FETCH_*, EXCEPTION, réseau...) = erreur
    # explicite, jamais « filtré » en silence.
    return ERROR
