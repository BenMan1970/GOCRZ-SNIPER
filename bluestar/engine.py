"""Per-instrument analysis pipeline (read-only)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import pytz

from .clock import Clock
from .config import (
    FETCH_SPECS,
    INDICES,
    NY_TZ,
    STALENESS_LIMIT_MIN,
    STRENGTH_PAIRS,
)
from .data.oanda import AuthenticationError, CandleSource
from .indicators import (
    QuantEngine,
    compute_adr,
    compute_adr_consumed,
    is_valid_df,
    to_ny_times,
)
from .scoring import compute_score
from .signals import (
    compute_currency_strength,
    compute_momentum_score,
    compute_mtf_analysis,
    detect_fvg,
    find_last_hma_flip,
    get_daily_bias_v2,
    get_strength_delta,
)

logger = logging.getLogger("bluestar_sniper")


def _reject(
    ticker: str,
    reason: str,
    debug_log: list[tuple[str, str]] | None,
    lock: threading.Lock | None,
) -> None:
    if debug_log is None:
        return
    if lock:
        with lock:
            debug_log.append((ticker, reason))
    else:
        debug_log.append((ticker, reason))


def analyze_asset(
    source: CandleSource,
    ticker: str,
    clock: Clock,
    freshness_limit_min: int = 30,
    strength_scores: dict[str, float] | None = None,
    debug_log: list[tuple[str, str]] | None = None,
    _lock: threading.Lock | None = None,
) -> dict[str, object] | None:
    def reject(reason: str) -> None:
        _reject(ticker, reason, debug_log, _lock)

    try:
        fetch_results: dict[str, tuple[pd.DataFrame, str | None]] = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {
                ex.submit(source.fetch, ticker, gran, cnt): gran
                for gran, cnt in FETCH_SPECS
            }
            for fut in as_completed(futures):
                gran = futures[fut]
                try:
                    fetch_results[gran] = fut.result()
                except AuthenticationError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.error("[%s] fetch %s exception: %s", ticker, gran, exc)
                    fetch_results[gran] = (pd.DataFrame(), str(exc))

        df_m15, err_m15 = fetch_results.get("M15", (pd.DataFrame(), "missing"))
        df_h1, _ = fetch_results.get("H1", (pd.DataFrame(), None))
        df_d, err_d = fetch_results.get("D", (pd.DataFrame(), "missing"))
        df_4h, _ = fetch_results.get("H4", (pd.DataFrame(), None))
        df_w, _ = fetch_results.get("W", (pd.DataFrame(), None))
        df_mo, _ = fetch_results.get("M", (pd.DataFrame(), None))

        if not is_valid_df(df_m15):
            reject(f"FETCH_M15: {err_m15}")
            return None
        if not is_valid_df(df_d):
            reject(f"FETCH_D: {err_d}")
            return None

        try:
            last_candle_time = df_m15.index[-1]
            if last_candle_time.tz is None:
                last_candle_time = last_candle_time.tz_localize("UTC")
            now_utc = clock.now(pytz.UTC)
            staleness_minutes = (now_utc - last_candle_time).total_seconds() / 60
            if staleness_minutes > STALENESS_LIMIT_MIN:
                reject(f"STALE_DATA: {staleness_minutes:.0f}min")
                return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] staleness check error: %s", ticker, exc)

        price = float(df_m15["close"].iloc[-1])

        bias, _ = get_daily_bias_v2(df_d, current_price=price, clock=clock)
        bias_bull = bias in ("BULLISH", "STRONG BULLISH")
        bias_bear = bias in ("BEARISH", "STRONG BEARISH")

        dfs_mtf = {
            "M": df_mo if is_valid_df(df_mo) else None,
            "W": df_w if is_valid_df(df_w) else None,
            "D": df_d if is_valid_df(df_d) else None,
            "4H": df_4h if is_valid_df(df_4h) else None,
            "1H": df_h1 if is_valid_df(df_h1) else None,
            "15m": df_m15 if is_valid_df(df_m15) else None,
        }
        mtf_pct, mtf_dominant, _ = compute_mtf_analysis(dfs_mtf)

        hma = QuantEngine.hma(df_m15["close"], 20)
        if hma.isna().iloc[-5:].any():
            reject("HMA_NAN")
            return None

        flip_type, candles_ago, flip_idx = find_last_hma_flip(hma, max_lookback=20)
        if flip_type is None:
            reject("NO_HMA_FLIP")
            return None

        if bias == "NEUTRAL":
            reject("BIAS_NEUTRAL")
            return None

        if (flip_type == "BULL" and bias_bull) or (flip_type == "BEAR" and bias_bear):
            bias_alignment = "ALIGNED"
        else:
            bias_alignment = "COUNTER"

        if flip_idx is None:
            reject("NO_HMA_FLIP")
            return None
        try:
            flip_open_time = hma.index[flip_idx]
            if flip_open_time.tz is None:
                flip_open_time = flip_open_time.tz_localize("UTC")
            flip_close_time = flip_open_time + pd.Timedelta(minutes=15)
            mins_ago = max(
                0,
                int(
                    (clock.now(pytz.UTC) - flip_close_time).total_seconds() // 60
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] real freshness calc error: %s", ticker, exc)
            if candles_ago is None:
                reject("NO_HMA_FLIP")
                return None
            mins_ago = candles_ago * 15

        freshness_str = (
            f"⚡ {mins_ago} min" if mins_ago <= freshness_limit_min
            else f"⏳ {mins_ago} min"
        )
        signal_fresh = mins_ago <= freshness_limit_min

        hma_now = hma.iloc[-1]
        if flip_type == "BULL" and price <= hma_now:
            reject("PRICE_BELOW_HMA_ON_BULL")
            return None
        if flip_type == "BEAR" and price >= hma_now:
            reject("PRICE_ABOVE_HMA_ON_BEAR")
            return None

        atr_m15 = QuantEngine.atr(df_m15, 14)
        atr_val = float(atr_m15.iloc[-1])
        atr_mean = float(atr_m15.iloc[-50:].mean())

        in_bull_fvg, in_bear_fvg, nb_fvg, nr_fvg = detect_fvg(
            df_m15, price, lookback=80
        )
        fvg_near_bull = (
            nb_fvg is not None
            and abs(price - (nb_fvg[0] + nb_fvg[1]) / 2) < atr_val * 1.0
        )
        fvg_near_bear = (
            nr_fvg is not None
            and abs(price - (nr_fvg[0] + nr_fvg[1]) / 2) < atr_val * 1.0
        )

        midnight_open = None
        midnight_open_approximate = False
        try:
            ny_tz = pytz.timezone(NY_TZ)
            m15_times = to_ny_times(df_m15.index)
            today_ny = clock.now(ny_tz).date()
            mn_mask = (
                (np.array([t.date() for t in m15_times]) == today_ny)
                & (np.array([t.hour for t in m15_times]) == 0)
                & (np.array([t.minute for t in m15_times]) == 0)
            )
            mn_c = df_m15[mn_mask]
            if mn_c.empty:
                today_mask = np.array([t.date() for t in m15_times]) == today_ny
                today_c = df_m15[today_mask]
                if not today_c.empty:
                    first_time = m15_times[today_mask][0]
                    if first_time.hour != 0 or first_time.minute != 0:
                        midnight_open_approximate = True
                    midnight_open = float(today_c["open"].iloc[0])
            else:
                midnight_open = float(mn_c["open"].iloc[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] midnight_open error: %s", ticker, exc)

        pdh = float(df_d["high"].iloc[-1])
        pdl = float(df_d["low"].iloc[-1])

        if midnight_open is not None and not midnight_open_approximate:
            in_premium = (price > midnight_open) and (price <= pdh)
            in_discount = (price < midnight_open) and (price >= pdl)
            in_extended_high = price > pdh
            in_extended_low = price < pdl

            if in_extended_high:
                zone_label = "EXT HIGH"
            elif in_extended_low:
                zone_label = "EXT LOW"
            elif in_premium:
                zone_label = "PREMIUM"
            elif in_discount:
                zone_label = "DISCOUNT"
            else:
                zone_label = "EQUILIBRE"

            zone_premium = zone_label in ("EXT HIGH", "PREMIUM")
            zone_discount = zone_label in ("EXT LOW", "DISCOUNT")
            above_mid = zone_premium
            below_mid = zone_discount
        else:
            d1_mid = (pdh + pdl) / 2.0
            in_discount = price < d1_mid
            in_premium = price > d1_mid
            zone_discount = in_discount
            zone_premium = in_premium
            below_mid = in_discount
            above_mid = in_premium
            zone_label = (
                "DISCOUNT" if in_discount
                else "PREMIUM" if in_premium
                else "EQUILIBRE"
            )

        midnight_bonus = False
        if (
            midnight_open is not None
            and not midnight_open_approximate
            and (
                (flip_type == "BULL" and price < midnight_open)
                or (flip_type == "BEAR" and price > midnight_open)
            )
        ):
            midnight_bonus = True

        try:
            df_adx_src = df_h1 if is_valid_df(df_h1, 20) else df_m15
            adx_s, pdi_s, mdi_s = QuantEngine.adx(df_adx_src, 14)
            adx_val_score = round(float(adx_s.iloc[-1]), 1)
            pdi_val = round(float(pdi_s.iloc[-1]), 1)
            mdi_val = round(float(mdi_s.iloc[-1]), 1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] ADX score computation failed: %s", ticker, exc)
            adx_val_score, pdi_val, mdi_val = 0.0, 0.0, 0.0

        if ticker in INDICES:
            atr_d_raw = QuantEngine.atr(df_d, 14).iloc[-1]
            adr_display = round(float(atr_d_raw), 2) if not pd.isna(atr_d_raw) else None
            adr_label = "ATR"
            adr_consumed = None
        else:
            adr_raw = compute_adr(df_d, period=14)
            adr_display = round(float(adr_raw), 5) if not np.isnan(adr_raw) else None
            adr_label = "ADR"
            adr_consumed = compute_adr_consumed(
                df_m15,
                float(adr_raw) if not np.isnan(adr_raw) else None,
                clock,
            )
            if adr_consumed is not None and np.isnan(adr_consumed):
                adr_consumed = None

        score, grade, _ = compute_score(
            flip_type,
            mins_ago,
            mtf_pct,
            mtf_dominant,
            zone_discount,
            zone_premium,
            below_mid,
            above_mid,
            in_bull_fvg,
            in_bear_fvg,
            fvg_near_bull,
            fvg_near_bear,
            adx_val_score,
            pdi_val,
            mdi_val,
            atr_val,
            atr_mean,
            midnight_bonus=midnight_bonus,
            adr_consumed=adr_consumed,
            bias_alignment=bias_alignment,
        )

        strength_delta = None
        if strength_scores:
            strength_delta = get_strength_delta(ticker, strength_scores)

        signal_is_bull = flip_type == "BULL"
        df_h4 = df_4h if is_valid_df(df_4h) else None
        df_h1_ok = df_h1 if is_valid_df(df_h1) else None
        momentum = compute_momentum_score(df_h4, df_h1_ok, df_m15, signal_is_bull)

        sig = (
            ("▲ LONG" if flip_type == "BULL" else "▼ SHORT")
            if signal_fresh
            else ("LONG (expiré)" if flip_type == "BULL" else "SHORT (expiré)")
        )

        return {
            "Fraîcheur": freshness_str,
            "Actif + Note": ticker,
            "Signal": sig,
            "Biais Daily": bias,
            "Alignement": bias_alignment,
            "Zone": zone_label,
            "Score /100": score,
            "Grade": grade,
            "ADR": adr_display,
            "ADR Label": adr_label,
            "ADR Consumed": adr_consumed,
            "MTF Pct": mtf_pct,
            "Strength Δ": strength_delta,
            "Momentum": momentum,
            "signal_is_bull": signal_is_bull,
            "Midnight Bonus": midnight_bonus,
        }

    except AuthenticationError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] analyze_asset EXCEPTION: %s", ticker, exc, exc_info=True)
        reject(f"EXCEPTION: {exc}")
        return None


def fetch_strength_data(
    source: CandleSource,
    pairs: tuple[str, ...] = STRENGTH_PAIRS,
) -> dict[str, pd.DataFrame]:
    dfs: dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(source.fetch, pair, "H1", 100): pair
            for pair in pairs
        }
        for fut in as_completed(futures):
            pair = futures[fut]
            try:
                df, _ = fut.result()
                if not df.empty:
                    dfs[pair] = df
            except AuthenticationError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("fetch_strength_data %s: %s", pair, exc)
    return dfs


def analyze_assets(
    source: CandleSource,
    clock: Clock,
    assets: tuple[str, ...],
    freshness_limit_min: int,
    strength_scores: dict[str, float],
    progress: Callable[[int, int, str], None] | None = None,
    max_workers: int = 3,
) -> tuple[list[dict[str, object]], list[tuple[str, str]]]:
    results: list[dict[str, object]] = []
    debug_log: list[tuple[str, str]] = []
    lock = threading.Lock()
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {
            ex.submit(
                analyze_asset,
                source,
                ticker,
                clock,
                freshness_limit_min,
                strength_scores,
                debug_log,
                lock,
            ): ticker
            for ticker in assets
        }
        for fut in as_completed(future_map):
            ticker = future_map[fut]
            try:
                res = fut.result()
                if res:
                    with lock:
                        results.append(res)
            except AuthenticationError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Outer future %s: %s", ticker, exc)
            completed += 1
            if progress is not None:
                progress(completed, len(assets), ticker)
    return results, debug_log


def run_scan(
    source: CandleSource,
    clock: Clock,
    assets: tuple[str, ...],
    freshness_limit_min: int = 30,
    progress: Callable[[int, int, str], None] | None = None,
    max_workers: int = 3,
) -> tuple[list[dict[str, object]], list[tuple[str, str]], dict[str, float]]:
    """Fetch currency strength then analyse every asset.

    Returns (results, debug_log, strength_scores). Results are per-asset dicts;
    ordering is completion order and must not be relied upon.
    """
    dfs_h1 = fetch_strength_data(source)
    strength_scores = compute_currency_strength(dfs_h1)
    results, debug_log = analyze_assets(
        source,
        clock,
        assets,
        freshness_limit_min,
        strength_scores,
        progress,
        max_workers,
    )
    return results, debug_log, strength_scores
