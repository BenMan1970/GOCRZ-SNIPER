"""Orchestration : téléchargement unique, analyse pure par actif, scan complet.

Flux : fetch_universe (1 requête par (actif, timeframe), jamais de doublon) ->
force devise (réutilise les H1 déjà chargés) -> analyze_asset (pur, sans I/O)
pour chaque actif -> ScanOutput.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import pandas as pd

from .clock import Clock
from .config import (
    ASSETS,
    CONTINUATION_ENABLED,
    FETCH_SPECS,
    FETCH_WORKERS,
    GRAN_TO_TF,
    HMA_FLIP_LOOKBACK,
    HMA_PERIOD,
    HMA_PRICE_TOLERANCE_ATR,
    MIN_BIAS_BARS,
    MIN_TREND_BARS,
    STALENESS_LIMIT_MIN,
    STRENGTH_PAIRS,
)
from .data.oanda import AuthenticationError, CandleSource
from .indicators import QuantEngine, compute_adr, compute_adr_consumed, is_valid_df
from .levels import classify_zone, midnight_open
from .logging_utils import LOGGER_NAME
from .scoring import ALIGNED, COUNTER, NEUTRAL, compute_score
from .signals import (
    compute_adx_levels,
    compute_currency_strength,
    compute_daily_bias,
    compute_mtf,
    hma_state,
    strength_delta,
)
from .timeutil import killzone_at

logger = logging.getLogger(LOGGER_NAME)

Frames = dict[str, pd.DataFrame | None]
Progress = Callable[[int, int, str], None]

FLIP = "FLIP"
CONTINUATION = "CONTINUATION"
_M15 = pd.Timedelta(minutes=15)


@dataclass
class ScanOutput:
    results: list[dict[str, object]] = field(default_factory=list)
    rejects: list[tuple[str, str]] = field(default_factory=list)
    strength: dict[str, float] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Téléchargement
# --------------------------------------------------------------------------- #
def fetch_universe(
    source: CandleSource,
    assets: Iterable[str],
    progress: Progress | None = None,
    max_workers: int = FETCH_WORKERS,
) -> tuple[dict[str, Frames], dict[str, dict[str, str]]]:
    """Charge chaque (actif, granularité) exactement une fois, en parallèle.

    Les paires de force devise absentes de `assets` sont chargées en H1 seulement.
    Lève AuthenticationError dès qu'un token est refusé.
    """
    counts = dict(FETCH_SPECS)
    tasks: list[tuple[str, str, int]] = [
        (a, gran, cnt) for a in assets for gran, cnt in FETCH_SPECS
    ]
    asset_set = {t[0] for t in tasks}
    tasks += [(p, "H1", counts["H1"]) for p in STRENGTH_PAIRS if p not in asset_set]

    frames: dict[str, Frames] = {}
    errors: dict[str, dict[str, str]] = {}
    total, done = len(tasks), 0

    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        futures = {pool.submit(source.fetch, t, g, c): (t, g) for t, g, c in tasks}
        for fut in as_completed(futures):
            ticker, gran = futures[fut]
            df, err = fut.result()          # AuthenticationError remonte ici
            frames.setdefault(ticker, {})[gran] = df if is_valid_df(df) else None
            if err:
                errors.setdefault(ticker, {})[gran] = err
            done += 1
            if progress:
                progress(done, total, ticker)
    except AuthenticationError:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    finally:
        pool.shutdown(wait=True)
    return frames, errors


# --------------------------------------------------------------------------- #
# Analyse d'un actif (pure : aucune I/O, aucune horloge globale)
# --------------------------------------------------------------------------- #
def analyze_asset(
    ticker: str,
    frames: Frames,
    fetch_errors: dict[str, str],
    clock: Clock,
    strength_scores: dict[str, float],
) -> tuple[dict[str, object] | None, str | None]:
    """Retourne (signal, None) ou (None, motif de rejet)."""
    df_m15, df_d = frames.get("M15"), frames.get("D")
    for gran, df in (("M15", df_m15), ("D", df_d)):
        if df is None:
            return None, f"FETCH_{gran}: {fetch_errors.get(gran, 'données absentes')}"

    now = clock.now()
    age_min = (now - df_m15.index[-1]).total_seconds() / 60.0
    if age_min > STALENESS_LIMIT_MIN:
        return None, f"STALE_DATA: dernière bougie M15 il y a {age_min:.0f} min"

    price = float(df_m15["close"].iloc[-1])
    bias = compute_daily_bias(df_d, df_m15, price, clock)
    if bias is None:
        return None, f"INSUFFICIENT_DATA: D = {len(df_d)} barres (< {MIN_BIAS_BARS})"

    hma = QuantEngine.hma(df_m15["close"], HMA_PERIOD)
    if hma.isna().iloc[-5:].any():
        return None, "HMA_NAN: historique M15 insuffisant"
    state = hma_state(hma)
    if state is None:
        return None, "HMA_NAN: pente indéterminée"

    is_bull = state.direction > 0
    hma_now = float(hma.iloc[-1])

    # Côté du prix vs HMA. gap > 0 : prix du MAUVAIS côté (distance en prix).
    gap = (hma_now - price) if is_bull else (price - hma_now)
    atr_m15 = float(QuantEngine.atr(df_m15, 14).iloc[-1])
    atr_ok = pd.notna(atr_m15) and atr_m15 > 0
    gap_atr = round(gap / atr_m15, 2) if atr_ok else None
    hma_pullback = False
    if gap >= 0:
        tolerance = HMA_PRICE_TOLERANCE_ATR * atr_m15 if atr_ok else 0.0
        if tolerance > 0 and gap <= tolerance:
            hma_pullback = True                  # pullback sur la HMA : accepté, signalé
        else:
            code = "PRICE_BELOW_HMA_ON_BULL" if is_bull else "PRICE_ABOVE_HMA_ON_BEAR"
            sign = "<=" if is_bull else ">="
            detail = f" (écart {gap_atr} ATR > {HMA_PRICE_TOLERANCE_ATR})" if atr_ok else ""
            return None, f"{code}: prix {price:.5g} {sign} HMA {hma_now:.5g}{detail}"

    if bias.direction == state.direction:
        alignment = ALIGNED
    elif bias.direction == 0:
        alignment = NEUTRAL
    else:
        alignment = COUNTER

    pdh, pdl = float(df_d["high"].iloc[-1]), float(df_d["low"].iloc[-1])
    zone = classify_zone(price, midnight_open(df_m15, now), pdh, pdl)

    is_flip = (
        state.bars_since_flip is not None and state.bars_since_flip <= HMA_FLIP_LOOKBACK
    )
    mins_ago: int | None = None
    flip_time: pd.Timestamp | None = None
    if is_flip:
        flip_time = df_m15.index[state.flip_pos]
        mins_ago = max(0, int((now - (flip_time + _M15)).total_seconds() // 60))
    elif not CONTINUATION_ENABLED:
        return None, f"NO_HMA_FLIP: aucun flip dans les {HMA_FLIP_LOOKBACK} dernières bougies"
    elif alignment != ALIGNED or not zone.favorable(is_bull):
        return None, (
            f"NO_HMA_FLIP: continuation non éligible "
            f"(biais {alignment}, zone {zone.label})"
        )

    mtf = compute_mtf({tf: frames.get(g) for g, tf in GRAN_TO_TF.items()})
    adx_count, adx_values = compute_adx_levels(
        frames.get("H4"), frames.get("H1"), df_m15
    )
    delta = strength_delta(ticker, strength_scores) if strength_scores else None
    adr = compute_adr(df_d)
    adr_value = None if pd.isna(adr) else adr
    adr_consumed = compute_adr_consumed(df_m15, adr_value, clock)

    scored = compute_score(
        is_bull=is_bull,
        mins_ago=mins_ago,
        mtf_pct=mtf.pct,
        mtf_aligned=mtf.dominant == state.direction,
        zone_favorable=zone.favorable(is_bull),
        alignment=alignment,
        bias_strong=bias.is_strong,
        strength_delta=delta,
        adx_strong_count=adx_count,
        adr_consumed=adr_consumed,
    )

    data_issues = [
        f"{tf} ({len(frames[g]) if frames.get(g) is not None else 0} barres)"
        for g, tf in GRAN_TO_TF.items()
        if not is_valid_df(frames.get(g), MIN_TREND_BARS)
    ]

    return {
        "ticker": ticker,
        "is_bull": is_bull,
        "signal_type": FLIP if is_flip else CONTINUATION,
        "mins_ago": mins_ago,
        "killzone": killzone_at(flip_time.to_pydatetime()) if flip_time is not None else "",
        "hma_pullback": hma_pullback,
        "hma_gap_atr": gap_atr,
        "bias": bias.label,
        "bias_detail": bias.describe(),
        "alignment": alignment,
        "zone": zone.label,
        "zone_ref": zone.ref,
        "score": scored.score,
        "grade": scored.grade,
        "score_detail": scored.describe(),
        "adr": None if adr_value is None else round(adr_value, 5),
        "adr_consumed": adr_consumed,
        "mtf_pct": mtf.pct,
        "mtf_detail": mtf.describe(),
        "strength_delta": delta,
        "adx_strong": adx_count,
        "adx_values": adx_values,
        "data_issues": data_issues,
    }, None


# --------------------------------------------------------------------------- #
# Scan complet
# --------------------------------------------------------------------------- #
def run_scan(
    source: CandleSource,
    clock: Clock,
    assets: Iterable[str] = ASSETS,
    progress: Progress | None = None,
    max_workers: int = FETCH_WORKERS,
) -> ScanOutput:
    assets = tuple(assets)
    n_fetch = len(assets) * len(FETCH_SPECS) + sum(1 for p in STRENGTH_PAIRS if p not in assets)
    total = n_fetch + len(assets)

    def fetch_progress(done: int, _total: int, ticker: str) -> None:
        if progress:
            progress(done, total, ticker)

    frames, errors = fetch_universe(source, assets, fetch_progress, max_workers)

    strength = compute_currency_strength(
        {p: frames.get(p, {}).get("H1") for p in STRENGTH_PAIRS}
    )

    out = ScanOutput(strength=strength)
    for i, ticker in enumerate(assets, start=1):
        try:
            signal, reason = analyze_asset(
                ticker, frames.get(ticker, {}), errors.get(ticker, {}), clock, strength
            )
        except Exception as exc:  # noqa: BLE001 - un actif ne doit jamais tuer le scan
            logger.exception("[%s] analyse en échec", ticker)
            signal, reason = None, f"EXCEPTION: {type(exc).__name__}: {exc}"
        if signal is not None:
            out.results.append(signal)
        else:
            out.rejects.append((ticker, reason or "NO_RESULT"))
        if progress:
            progress(n_fetch + i, total, ticker)
    return out
