"""The analysis engine: gates + scoring, fully injectable.

Corrects, with measured impact (see CHANGELOG):
  * B-11  clock is INJECTED - no wall-clock read inside the pipeline
  * B-13  late timeframes (H1/H4/W/M) are fetched LAZILY, only after the early
          gates pass (~41% of network calls avoided, outputs identical)
  * B-14  staleness measured from candle CLOSE (open + granularity), not open
  * B-7   ADR window over the last `period` CLOSED sessions
  * B-12  results are plain data (session_state handled in the UI layer)
"""

from __future__ import annotations

import threading
from datetime import tzinfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .analysis import (
    compute_adr,
    compute_adr_consumed,
    midnight_bonus_for,
    midnight_open_of,
    zone_state,
)
from .clock import Clock, DEFAULT_CLOCK
from .data import FetchError, OandaClient
from .indicators import atr as atr_series
from .indicators import hma as hma_series
from .signals import (
    compute_currency_strength,
    compute_momentum_score,
    compute_mtf_analysis,
    detect_fvg,
    find_last_hma_flip,
    get_daily_bias_v2,
    get_strength_delta,
    is_valid_df,
)
from .scoring import compute_score


@dataclass(frozen=True)
class Rejection:
    ticker: str
    reason: str


@dataclass(frozen=True)
class Signal:
    ticker: str
    payload: dict[str, object]


Result = Signal | Rejection

GRAN_MINUTES = {
    "M15": 15,
    "H1": 60,
    "H4": 240,
    "D": 24 * 60,
    "W": 7 * 24 * 60,
    "M": 30 * 24 * 60,
}


@dataclass
class Engine:
    """Configurable analysis engine."""

    client: OandaClient
    clock: Clock = DEFAULT_CLOCK
    freshness_limit_min: int = 30
    staleness_limit_min: int = config.STALENESS_LIMIT_MIN
    fvg_lookback: int = config.FVG_LOOKBACK
    flip_lookback: int = config.FLIP_LOOKBACK_BARS
    fetch_specs: tuple[tuple[str, int], ...] = config.FETCH_SPECS
    early_granularities: frozenset[str] = config.EARLY_GRANULARITIES
    lazy_fetch: bool = True
    staleness_basis: str = "close"  # "close" = B-14 fix; "open" = V16
    indices: frozenset[str] = config.INDICES
    debug_log: list[tuple[str, str]] | None = None
    debug_lock: threading.Lock | None = None

    # ------------------------------------------------------------ helpers
    def _reject(self, ticker: str, reason: str) -> Rejection:
        if self.debug_log is not None:
            entry = (ticker, reason)
            if self.debug_lock is not None:
                with self.debug_lock:
                    self.debug_log.append(entry)
            else:
                self.debug_log.append(entry)
        return Rejection(ticker, reason)

    def _staleness_minutes(self, df: pd.DataFrame, gran_key: str = "M15") -> float:
        minutes = GRAN_MINUTES.get(gran_key, GRAN_MINUTES["M15"])
        last_open = df.index[-1]
        basis = (
            last_open
            if self.staleness_basis == "open"
            else last_open + pd.Timedelta(minutes=minutes)
        )
        if basis.tz is None:
            basis = basis.tz_localize("UTC")
        delta = (self.clock.now().astimezone(basis.tz) - basis).total_seconds()
        return float(delta) / 60.0

    def _split_specs(self) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
        early = [(g, c) for g, c in self.fetch_specs if g in self.early_granularities]
        late = [
            (g, c) for g, c in self.fetch_specs if g not in self.early_granularities
        ]
        return early, late

    # ------------------------------------------------------------ pipeline
    def analyze(self, ticker: str) -> Result:
        """Full pipeline for one instrument. Never raises for domain reasons."""
        try:
            return self._analyze_inner(ticker)
        except FetchError as exc:
            return self._reject(ticker, f"{exc.kind}: {exc.detail}")
        except Exception as exc:
            return self._reject(ticker, f"EXCEPTION: {exc}")

    def _analyze_inner(self, ticker: str) -> Result:
        early_specs, late_specs = self._split_specs()
        frames: dict[str, pd.DataFrame] = {}
        errors: dict[str, str] = {}

        for gran, count in early_specs:
            df, err = self.client.fetch(ticker, gran, count)
            if err or df.empty:
                errors[gran] = err or "empty"
            else:
                frames[gran] = df

        df_m15 = frames.get("M15", pd.DataFrame())
        df_d = frames.get("D", pd.DataFrame())

        if not is_valid_df(df_m15):
            return self._reject(ticker, f"FETCH_M15: {errors.get('M15', 'missing')}")
        if not is_valid_df(df_d):
            return self._reject(ticker, f"FETCH_D: {errors.get('D', 'missing')}")

        staleness = self._staleness_minutes(df_m15)
        if staleness > self.staleness_limit_min:
            return self._reject(ticker, f"STALE_DATA: {staleness:.0f}min")

        price = float(df_m15["close"].iloc[-1])

        # ---- daily bias (early gate, needs D only)
        bias, _ = get_daily_bias_v2(df_d, clock=self.clock, current_price=price)
        bias_bull = bias in ("BULLISH", "STRONG BULLISH")
        bias_bear = bias in ("BEARISH", "STRONG BEARISH")

        # ---- HMA flip (M15 only)
        sig_hma = hma_series(df_m15["close"], config.HMA_PERIOD)
        if sig_hma.isna().iloc[-5:].any():
            return self._reject(ticker, "HMA_NAN")
        flip_type, candles_ago, flip_idx = find_last_hma_flip(
            sig_hma, max_lookback=self.flip_lookback
        )
        if flip_type is None:
            return self._reject(ticker, "NO_HMA_FLIP")
        if bias == "NEUTRAL":
            return self._reject(ticker, "BIAS_NEUTRAL")
        alignment = (
            "ALIGNED"
            if (
                (flip_type == "BULL" and bias_bull)
                or (flip_type == "BEAR" and bias_bear)
            )
            else "COUNTER"
        )

        # ---- real elapsed freshness (clock-injected; V16 - close of flip candle)
        try:
            flip_open_time = sig_hma.index[flip_idx]
            if flip_open_time.tz is None:
                flip_open_time = flip_open_time.tz_localize("UTC")
            flip_close_time = flip_open_time + pd.Timedelta(minutes=GRAN_MINUTES["M15"])
            mins_ago = max(
                0,
                int(
                    (
                        self.clock.now().astimezone(target_tz()) - flip_close_time
                    ).total_seconds()
                    // 60
                ),
            )
        except Exception:
            mins_ago = int(candles_ago or 0) * GRAN_MINUTES["M15"]

        sig_fresh = mins_ago <= self.freshness_limit_min

        hma_now = sig_hma.iloc[-1]
        if flip_type == "BULL" and price <= hma_now:
            return self._reject(ticker, "PRICE_BELOW_HMA_ON_BULL")
        if flip_type == "BEAR" and price >= hma_now:
            return self._reject(ticker, "PRICE_ABOVE_HMA_ON_BEAR")

        # ---- LAZY fetch of late timeframes (B-13): only for instruments that
        # survived every early gate. Outputs identical, network cost lower.
        late_frames: dict[str, pd.DataFrame | None] = {}
        if self.lazy_fetch:
            for gran, count in late_specs:
                df, err = self.client.fetch(ticker, gran, count)
                late_frames[gran] = (
                    df
                    if (df is not None and not df.empty and not err)
                    else pd.DataFrame()
                )
        else:
            for gran, _count in late_specs:
                late_frames[gran] = pd.DataFrame()

        df_h1 = late_frames.get("H1", pd.DataFrame())
        df_4h = late_frames.get("H4", pd.DataFrame())
        df_w = late_frames.get("W", pd.DataFrame())
        df_mo = late_frames.get("M", pd.DataFrame())

        dfs_mtf = {
            "M": df_mo if is_valid_df(df_mo) else None,
            "W": df_w if is_valid_df(df_w) else None,
            "D": df_d if is_valid_df(df_d) else None,
            "4H": df_4h if is_valid_df(df_4h) else None,
            "1H": df_h1 if is_valid_df(df_h1) else None,
            "15m": df_m15 if is_valid_df(df_m15) else None,
        }
        mtf_pct, mtf_dominant, _ = compute_mtf_analysis(dfs_mtf)

        # ---- ATR of M15 + FVG
        atr_m15 = atr_series(df_m15, config.ATR_PERIOD)
        atr_val = float(atr_m15.iloc[-1])
        atr_mean = float(atr_m15.iloc[-50:].mean())

        in_bull_fvg, in_bear_fvg, nb_fvg, nr_fvg = detect_fvg(
            df_m15, price, lookback=self.fvg_lookback
        )
        fvg_near_bull = (
            nb_fvg is not None and abs(price - (nb_fvg[0] + nb_fvg[1]) / 2) < atr_val
        )
        fvg_near_bear = (
            nr_fvg is not None and abs(price - (nr_fvg[0] + nr_fvg[1]) / 2) < atr_val
        )

        # ---- zones (clock-injected)
        mo, mo_approx = midnight_open_of(df_m15, clock=self.clock)
        pdh = float(df_d["high"].iloc[-1])
        pdl = float(df_d["low"].iloc[-1])
        zone = zone_state(price, mo, mo_approx, pdh, pdl)
        bonus = midnight_bonus_for(flip_type, price, mo, mo_approx)

        # ---- ADX for scoring (H1 preferred, M15 fallback - V16)
        try:
            adx_src = df_h1 if is_valid_df(df_h1, 20) else df_m15
            adx_s, pdi_s, mdi_s = data_adx(adx_src)
            adx_val_score = round(float(adx_s.iloc[-1]), 1)
            pdi_val = round(float(pdi_s.iloc[-1]), 1)
            mdi_val = round(float(mdi_s.iloc[-1]), 1)
        except Exception:
            adx_val_score, pdi_val, mdi_val = 0.0, 0.0, 0.0

        # ---- ADR / ATR display + consumed
        if ticker in self.indices:
            _atr_d = atr_series(df_d, config.ATR_PERIOD).iloc[-1]
            adr_display = round(float(_atr_d), 2) if not pd.isna(_atr_d) else None
            adr_label = "ATR"
            adr_consumed = None
        else:
            _adr = compute_adr(df_d, config.ADR_PERIOD)
            adr_display = round(float(_adr), 5) if not np.isnan(_adr) else None
            adr_label = "ADR"
            adr_consumed = compute_adr_consumed(
                df_m15, float(_adr) if not np.isnan(_adr) else None, clock=self.clock
            )
            if adr_consumed is not None and np.isnan(adr_consumed):
                adr_consumed = None

        score, grade, _detail = compute_score(
            flip_type,
            mins_ago,
            mtf_pct,
            mtf_dominant,
            bool(zone["zone_discount"]),
            bool(zone["zone_premium"]),
            bool(zone["below_mid"]),
            bool(zone["above_mid"]),
            in_bull_fvg,
            in_bear_fvg,
            fvg_near_bull,
            fvg_near_bear,
            adx_val_score,
            pdi_val,
            mdi_val,
            atr_val,
            atr_mean,
            midnight_bonus=bonus,
            adr_consumed=adr_consumed,
            bias_alignment=alignment,
        )

        signal_is_bull = flip_type == "BULL"
        momentum = compute_momentum_score(
            df_4h if is_valid_df(df_4h) else None,
            df_h1 if is_valid_df(df_h1) else None,
            df_m15,
            signal_is_bull,
        )

        label = (
            ("\u25b2 LONG" if flip_type == "BULL" else "\u25bc SHORT")
            if sig_fresh
            else ("LONG (expiré)" if flip_type == "BULL" else "SHORT (expiré)")
        )
        freshness = f"\u26a1 {mins_ago} min" if sig_fresh else f"\u23f3 {mins_ago} min"

        return Signal(
            ticker,
            {
                "Fraîcheur": freshness,
                "Actif + Note": ticker,
                "Signal": label,
                "Biais Daily": bias,
                "Alignement": alignment,
                "Zone": zone["label"],
                "Score /100": score,
                "Grade": grade,
                "ADR": adr_display,
                "ADR Label": adr_label,
                "ADR Consumed": adr_consumed,
                "MTF Pct": mtf_pct,
                "Strength Δ": None,
                "Momentum": momentum,
                "signal_is_bull": signal_is_bull,
                "Midnight Bonus": bonus,
            },
        )

    # ------------------------------------------------------------ parallel
    def scan(
        self,
        assets: list[str],
        strength_scores: dict[str, float] | None = None,
        parallel: bool = True,
        max_workers: int = 8,
    ) -> tuple[list[Signal], list[Rejection], list[tuple[str, str]]]:
        """Scan the universe; returns (signals, rejections, debug log)."""
        dbg: list[tuple[str, str]] = []
        self.debug_log = dbg
        self.debug_lock = threading.Lock()
        signals: list[Signal] = []
        rejects: list[Rejection] = []

        def run(t: str) -> Result:
            res = self.analyze(t)
            if isinstance(res, Signal) and strength_scores:
                res.payload["Strength Δ"] = get_strength_delta(t, strength_scores)
            return res

        if not parallel:
            for t in assets:
                res = run(t)
                (signals if isinstance(res, Signal) else rejects).append(res)  # type: ignore[arg-type]
            return signals, rejects, dbg

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(run, t): t for t in assets}
            for fut in as_completed(futures):
                res = fut.result()
                (signals if isinstance(res, Signal) else rejects).append(res)  # type: ignore[arg-type]
        return signals, rejects, dbg


def strength_from(
    client: OandaClient, pairs: tuple[str, ...] = config.STRENGTH_PAIRS
) -> dict[str, float]:
    """Fetch H1 close frames for the strength pairs and score currencies."""
    frames = {}
    for pair in pairs:
        df, err = client.fetch(pair, "H1", config.STRENGTH_COUNT)
        if not err and not df.empty:
            frames[pair] = df
    return compute_currency_strength(frames)


def target_tz() -> tzinfo:
    """tzinfo for clock conversions; kept as a function so tests can pin it."""
    import pytz

    return pytz.UTC


def pytz_utc() -> tzinfo:
    import pytz

    return pytz.UTC


def data_adx(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    from .indicators import adx

    return adx(df, config.ADX_PERIOD)
