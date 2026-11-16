"""Orchestration : téléchargement unique, analyse pure par actif, scan complet.

Flux : fetch_universe (1 requête par (actif, timeframe), jamais de doublon) ->
force devise (réutilise les H1 déjà chargés) -> analyze_asset (pur, sans I/O)
pour chaque actif -> ScanOutput.
"""

from __future__ import annotations

import logging
import time
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
from .data.oanda import AuthenticationError, CandleSource, is_access_refusal, is_retryable
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

# Refus d'accès consécutifs, sans aucune réponse valide, avant d'abandonner le scan.
AUTH_ABORT_THRESHOLD = 6

# Seconde passe pour les requêtes en erreur transitoire (refus 401/403 isolé, timeout, 429...) :
# pause puis faible concurrence, loin du burst initial.
RECOVERY_WORKERS = 2
RECOVERY_PAUSE_S = 2.0

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
Task = tuple[str, str, int]          # (actif, granularité OANDA, nombre de bougies)


@dataclass
class _Fetch:
    """État partagé du téléchargement : résultats, erreurs et compteurs de refus."""

    frames: dict[str, Frames]
    errors: dict[str, dict[str, str]]
    total: int
    progress: Progress | None
    done: int = 0
    answered: int = 0          # réponses du serveur autres qu'un refus d'accès
    refused: int = 0           # refus d'accès (401/403)
    first_refusal: str = ""

    def record(self, ticker: str, gran: str, df: pd.DataFrame, err: str | None, count: bool = True) -> None:
        self.frames.setdefault(ticker, {})[gran] = df if is_valid_df(df) else None
        if err:
            self.errors.setdefault(ticker, {})[gran] = err
        else:
            self.errors.get(ticker, {}).pop(gran, None)
        if is_access_refusal(err):
            self.refused += 1
            self.first_refusal = self.first_refusal or str(err)
        else:
            self.answered += 1
        if count:
            self.done += 1
            if self.progress:
                self.progress(self.done, self.total, ticker)


def _run(
    source: CandleSource, tasks: list[Task], workers: int, fetch: _Fetch, abort_after: int | None
) -> list[Task]:
    """Exécute `tasks` en parallèle. Retourne les tâches NON exécutées.

    Si `abort_after` refus d'accès s'accumulent sans aucune réponse valide, on interrompt
    (inutile de marteler l'API) et on rend les tâches restantes pour vérification.
    """
    if not tasks:
        return []
    pool = ThreadPoolExecutor(max_workers=min(workers, len(tasks)))
    leftover: list[Task] = []
    try:
        futures = {pool.submit(source.fetch, t, g, c): (t, g, c) for t, g, c in tasks}
        processed: set = set()
        for fut in as_completed(futures):
            ticker, gran, _ = futures[fut]
            df, err = fut.result()
            fetch.record(ticker, gran, df, err)
            processed.add(fut)
            if abort_after and fetch.answered == 0 and fetch.refused >= abort_after:
                pool.shutdown(wait=True, cancel_futures=True)
                for other, (t2, g2, c2) in futures.items():
                    if other in processed:
                        continue
                    if other.cancelled():
                        leftover.append((t2, g2, c2))
                    else:                                   # déjà en vol : on garde son résultat
                        df2, err2 = other.result()
                        fetch.record(t2, g2, df2, err2)
                break
    finally:
        pool.shutdown(wait=True)
    return leftover


def _confirm_or_raise(source: CandleSource, tasks: list[Task], fetch: _Fetch, pause: float) -> None:
    """Refus massif au démarrage : token faux, ou simple à-coup de l'API ?

    On attend, puis on rejoue séquentiellement quelques requêtes refusées. Si UNE passe, le
    token est valide : le scan continue. Sinon AuthenticationError (code HTTP + message OANDA).
    """
    refused = [t for t in tasks if is_access_refusal(fetch.errors.get(t[0], {}).get(t[1]))]
    time.sleep(pause)
    for ticker, gran, count in refused[:3]:
        df, err = source.fetch(ticker, gran, count)
        fetch.record(ticker, gran, df, err, count=False)
        if not is_access_refusal(err):
            return
    raise AuthenticationError(fetch.first_refusal)


def _recover(source: CandleSource, tasks: list[Task], fetch: _Fetch, pause: float) -> None:
    """Rejoue UNE fois les requêtes en erreur transitoire, à faible concurrence."""
    retry = [t for t in tasks if is_retryable(fetch.errors.get(t[0], {}).get(t[1]))]
    if not retry:
        return
    logger.info("passe de récupération : %d requête(s)", len(retry))
    time.sleep(pause)
    with ThreadPoolExecutor(max_workers=min(RECOVERY_WORKERS, len(retry))) as pool:
        futures = {pool.submit(source.fetch, t, g, c): (t, g) for t, g, c in retry}
        for fut in as_completed(futures):
            ticker, gran = futures[fut]
            df, err = fut.result()
            fetch.record(ticker, gran, df, err, count=False)


def fetch_universe(
    source: CandleSource,
    assets: Iterable[str],
    progress: Progress | None = None,
    max_workers: int = FETCH_WORKERS,
    recovery_pause: float = RECOVERY_PAUSE_S,
) -> tuple[dict[str, Frames], dict[str, dict[str, str]]]:
    """Charge chaque (actif, granularité) une fois, en parallèle, avec reprise sur erreur.

    1. Passe principale (burst parallèle).
    2. Si tout est refusé : vérification avant de conclure (voir `_confirm_or_raise`).
    3. Passe de récupération (faible concurrence) pour les erreurs transitoires.
    AuthenticationError n'est levée que si, même après pause, rien n'aboutit.
    Les paires de force devise absentes de `assets` sont chargées en H1 seulement.
    """
    counts = dict(FETCH_SPECS)
    tasks: list[Task] = [(a, gran, cnt) for a in assets for gran, cnt in FETCH_SPECS]
    asset_set = {t[0] for t in tasks}
    tasks += [(p, "H1", counts["H1"]) for p in STRENGTH_PAIRS if p not in asset_set]

    fetch = _Fetch({}, {}, len(tasks), progress)
    leftover = _run(source, tasks, max_workers, fetch, AUTH_ABORT_THRESHOLD)
    if leftover or (fetch.answered == 0 and fetch.refused):
        _confirm_or_raise(source, tasks, fetch, recovery_pause)
        _run(source, leftover, RECOVERY_WORKERS, fetch, None)
    _recover(source, tasks, fetch, recovery_pause)
    return fetch.frames, fetch.errors


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
    recovery_pause: float = RECOVERY_PAUSE_S,
) -> ScanOutput:
    assets = tuple(assets)
    n_fetch = len(assets) * len(FETCH_SPECS) + sum(1 for p in STRENGTH_PAIRS if p not in assets)
    total = n_fetch + len(assets)

    def fetch_progress(done: int, _total: int, ticker: str) -> None:
        if progress:
            progress(done, total, ticker)

    frames, errors = fetch_universe(source, assets, fetch_progress, max_workers, recovery_pause)

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
