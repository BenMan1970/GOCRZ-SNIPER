"""Streamlit entry point. Thin: wiring + rendering only."""

from __future__ import annotations

import html
import os
import time
from collections import Counter
from datetime import UTC, datetime

import pandas as pd
import pytz
import streamlit as st

from ..clock import FixedClock, SystemClock
from ..config import (
    ASSETS,
    DEFAULT_FRESHNESS_MIN,
    DISPLAY_NAMES,
    FRESHNESS_CHOICES,
    GRADE_ORDER,
    MIN_GRADE_MAP,
)
from ..data.fixtures import FixtureSource
from ..data.oanda import (
    AuthenticationError,
    CandleSource,
    OandaSource,
    TokenBucket,
    redact,
)
from ..engine import analyze_assets, fetch_strength_data
from ..logging_utils import register_secret
from ..signals import compute_currency_strength
from ..status import SIGNAL, classify
from ..timeutil import get_current_killzone
from .render import (
    _html,
    footer_html,
    killzone_badge,
    killzone_color,
    kpi_html,
    sort_frame,
    table_html,
)
from .theme import theme_css

APP_VERSION = "V16"


def _secret(key: str, default: str | None = None) -> str | None:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # noqa: BLE001  # nosec B110
        pass
    return os.environ.get(key, default)


def _header_html(kz_now: str) -> str:
    if kz_now:
        kc = killzone_color(kz_now)
        kz_html = (
            f'<span class="bs-badge" style="border-color:{kc}4d;'
            f'background:{kc}0d;color:{kc}">'
            f'<span class="bs-dot" style="width:5px;height:5px;border-radius:50%;'
            f'background:{kc}"></span>'
            f'<span style="font-size:9.5px;font-weight:600;letter-spacing:.14em;'
            f'text-transform:uppercase;color:{kc}">{killzone_badge(kz_now)}</span></span>'
        )
    else:
        kz_html = (
            '<span class="bs-badge"><span class="bs-dot" '
            'style="width:5px;height:5px;border-radius:50%;background:#6f84a3"></span>'
            'HORS KILLZONE</span>'
        )
    return _html(
        f"""
    <div class="bs-header">
      <div class="bs-brand">
        <div style="width:52px;height:52px;flex-shrink:0;display:flex;align-items:center;
             justify-content:center;border:1px solid #2c4667;border-radius:10px;
             background:linear-gradient(180deg,#0d192b,#0a1322);
             box-shadow:inset 0 1px 0 rgba(255,255,255,.04)">
          <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
            <path d="M7 16V7h9M32 7h9v9M41 32v9h-9M16 41H7v-9"
                  stroke="#4f8dff" stroke-width="1.4" stroke-linecap="square" opacity=".5"/>
            <circle cx="24" cy="24" r="10.5" stroke="#4f8dff" stroke-width="1.2" opacity=".65"/>
            <path d="M24 8.5v7M24 32.5v7M8.5 24h7M32.5 24h7"
                  stroke="#8ab8ff" stroke-width="1.2" stroke-linecap="round"/>
            <circle cx="24" cy="24" r="2.6" fill="#f5c451"/>
          </svg>
        </div>
        <div>
          <div class="bs-overline">Tactical market scanner</div>
          <h1 class="bs-title">
            Bluestar <span class="bs-thin">Sniper</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;
                  font-weight:500;letter-spacing:.04em;color:var(--blue-2);
                  background:rgba(79,141,255,.07);border:1px solid #2c4667;
                  padding:3px 7px;border-radius:4px;margin-left:9px;vertical-align:middle">{APP_VERSION}</span>
          </h1>
          <p class="bs-sub">
            <span>HMA 20 · M15</span>
            <span class="bs-sep">/</span>
            <span>Multi-timeframe</span>
            <span class="bs-sep">/</span>
            <span>Zones ICT</span>
            <span class="bs-sep">/</span>
            <span>FVG &amp; force devise</span>
          </p>
        </div>
      </div>
      <div class="bs-badges">
        {kz_html}
        <span class="bs-badge">
          <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
            <rect x="3" y="6.2" width="8" height="5.8" rx="1.1"
                  stroke="currentColor" stroke-width="1.2"/>
            <path d="M5 6V4.5a2 2 0 0 1 4 0V6" stroke="currentColor" stroke-width="1.2"/>
          </svg>
          <strong>Read-only</strong> OANDA
        </span>
      </div>
    </div>
    <hr>
    """
    )


def _idle_html(n_assets: int) -> str:
    return _html(
        f"""
        <div style="max-width:720px;margin:0 auto;padding:54px 30px 48px;text-align:center;
             border:1px solid #1d2e47;border-radius:14px;
             background:linear-gradient(180deg,#0c1729,#0a1322);
             box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 30px 70px -56px #000">
          <div style="width:64px;height:64px;margin:0 auto 22px;display:flex;align-items:center;
               justify-content:center;border:1px solid #2c4667;border-radius:12px;
               background:#0d192b">
            <svg viewBox="0 0 48 48" width="38" height="38" fill="none">
              <circle cx="24" cy="24" r="14" stroke="#4f8dff" stroke-width="1.2" opacity=".55"/>
              <path d="M24 5v9M24 34v9M5 24h9M34 24h9"
                    stroke="#8ab8ff" stroke-width="1.2" stroke-linecap="round"/>
              <circle cx="24" cy="24" r="2.6" fill="#f5c451"/>
            </svg>
          </div>
          <div class="bs-overline" style="justify-content:center;margin-bottom:8px">Awaiting command</div>
          <div style="font-size:22px;color:var(--ink);font-weight:600;letter-spacing:-.02em">
            Scanner en veille
          </div>
          <div style="font-size:13px;color:var(--muted);margin-top:8px;letter-spacing:.01em">
            {n_assets} instruments · 6 timeframes · setups HMA / ICT
          </div>
          <div style="display:flex;justify-content:center;gap:7px;margin-top:22px;flex-wrap:wrap">
            <span class="bs-badge">Lecture seule</span>
            <span class="bs-badge"><strong>OANDA</strong> Practice</span>
            <span class="bs-badge">Données multi-TF</span>
          </div>
        </div>
        """
    )


def _safe_md(value: object) -> str:
    return html.escape(str(value)).replace("`", "\\`")


def _status_rows(
    assets: tuple[str, ...],
    results: list[dict[str, object]],
    debug_log: list[tuple[str, str]],
    now: datetime,
    token: str,
) -> list[dict[str, str]]:
    by_ticker = {str(r["Actif + Note"]): r for r in results}
    reasons = {ticker: reason for ticker, reason in debug_log}
    rows: list[dict[str, str]] = []
    for ticker in assets:
        display = DISPLAY_NAMES.get(ticker, ticker)
        if ticker in by_ticker:
            row = by_ticker[ticker]
            rows.append({
                "Actif": display,
                "Statut": SIGNAL,
                "Détail": (
                    f"{row['Signal']} · {row['Grade']} · "
                    f"{row['Score /100']}/103 · {row['Zone']}"
                ),
            })
            continue
        reason = reasons.get(ticker, "NO_RESULT")
        rows.append({
            "Actif": display,
            "Statut": classify(ticker, reason, now),
            "Détail": redact(reason, token),
        })
    return rows


def main() -> None:
    st.set_page_config(
        page_title="Bluestar Sniper · Market Intelligence",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(theme_css(), unsafe_allow_html=True)

    fixture_mode = os.environ.get("BLUESTAR_FIXTURE_MODE") == "1"
    fixed_now = os.environ.get("BLUESTAR_FIXED_NOW")
    clock = FixedClock(datetime.fromisoformat(fixed_now)) if fixed_now else SystemClock()

    token = _secret("OANDA_ACCESS_TOKEN")
    register_secret(token)
    if not fixture_mode and not token:
        st.error("🔑 **Secret manquant :** `OANDA_ACCESS_TOKEN`")
        st.stop()

    env = str(_secret("OANDA_ENVIRONMENT", "practice") or "practice").strip().lower()
    if env not in ("practice", "live"):
        st.error(f"⚠️ OANDA_ENVIRONMENT invalide : `{env}` — doit être `practice` ou `live`")
        st.stop()
    if env == "live" and not fixture_mode:
        st.warning("⚠️ **CONNEXION COMPTE RÉEL (live)** — opérations sur capital réel")

    source: CandleSource
    if fixture_mode:
        source = FixtureSource(when=clock.now(UTC))
        assets_env = os.environ.get("BLUESTAR_ASSETS", "")
        assets = (
            tuple(a.strip() for a in assets_env.split(",") if a.strip())
            if assets_env else source.instruments
        )
        token = "fixture-token"  # nosec B105
    else:
        source = OandaSource(
            token or "",
            env,
            limiter=TokenBucket(rate_per_s=25.0, burst=10.0),
        )
        assets = ASSETS

    kz_now = get_current_killzone(clock)
    st.markdown(_header_html(kz_now), unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        freshness = st.selectbox(
            "Fraîcheur max du signal (min)",
            list(FRESHNESS_CHOICES),
            index=list(FRESHNESS_CHOICES).index(DEFAULT_FRESHNESS_MIN),
        )
    with col2:
        min_grade = st.selectbox("Grade minimum", ["Tous", "B", "B+", "A", "A+"], index=0)
    with col3:
        show_debug = st.toggle("🐛 Debug", value=False)

    with st.expander("📘 Grille de notation V16"):
        st.markdown(
            """
| Critère | Max | Détail |
|---|---|---|
| **Trigger HMA flip** | 30 pts | ≤15 min = 30 · ≤30 min = 20 · ≤45 min = 10 · >45 min = 0 (fraîcheur = temps réel écoulé) |
| **MTF Alignment** | 25 pts | ≥80% = 25 · ≥65% = 18 · ≥50% = 10 · contre-MTF = 0 |
| **Zone D1** | 15 pts | Discount/Premium (EXT LOW/HIGH inclus) = 15 · sinon 0 |
| **Midnight Bonus** | 3 pts | Confluence directionnelle avec MO |
| **FVG M15** | 15 pts | Variante LuxAlgo (mitigation + seuil auto) |
| **ADX momentum** | 10 pts | ADX>25+DI ok = 10 · ADX>20+DI ok = 6 |
| **ATR actif** | 5 pts | ≥ moyenne = 5 · ≥ 50% = 3 |
| **ADR Malus** | -5 pts | Range journalier > 70% consommé depuis minuit NY (forex/métaux/crypto — non applicable aux indices, notés en ATR) |
| **Bias Malus** | -20 pts | Signal contraire (⚠ COUNTER) au biais journalier 5 facteurs |

Score max réel = **103** (échelle affichée « /103 », pas /100), plage possible [−25 ; 103].

| Colonne | Description |
|---|---|
| **Zone** | DISCOUNT = prix sous MO (00h00 NY) · PREMIUM = prix dessus · EXT HIGH/LOW = hors PDH/PDL |
| **ADR / ATR** | Valeur + jauge de consommation du range (🟢 <40% · 🟡 40–70% · 🔴 >70%) |
| **Momentum / Δ** | ■■■ = ADX H4·H1·M15 ≥ 25 alignés avec le signal · Δ = force devise base/quote, vert si favorable au signal, rouge si contraire (n/a indices, métaux et crypto) |

Le biais daily est neutralisé si la structure D1 est cassée (BOS) ou si une majorité 3-2 contredit la HMA20 daily sur 3 bougies.
            """
        )

    run = st.button("🚀  LANCER LE SCANNER", width="stretch")

    if not run:
        st.markdown(_idle_html(len(assets)), unsafe_allow_html=True)
        return

    t_start = time.time()
    progress = st.progress(0)
    status = st.empty()

    def on_progress(done: int, total: int, ticker: str) -> None:
        progress.progress(done / total)
        status.caption(
            f"⏳ {DISPLAY_NAMES.get(ticker, ticker)}… ({done}/{total})"
        )

    try:
        with st.spinner("Calcul Currency Strength H1…"):
            dfs_h1 = fetch_strength_data(source)
            strength_scores = compute_currency_strength(dfs_h1)

        with st.spinner("Analyse MTF en cours…"):
            results, debug_log = analyze_assets(
                source,
                clock,
                assets,
                freshness,
                strength_scores,
                progress=on_progress,
                max_workers=3,
            )
    except AuthenticationError:
        st.error(
            "🔑 **Token OANDA invalide ou expiré.** "
            "Vérifie `OANDA_ACCESS_TOKEN` puis relance le scanner."
        )
        st.stop()

    elapsed = round(time.time() - t_start, 1)
    status.empty()
    progress.empty()
    now_utc = clock.now(pytz.UTC)

    safe_debug = [(t, redact(r, token or "")) for t, r in debug_log]
    status_rows = _status_rows(assets, results, safe_debug, now_utc, token or "")

    if show_debug:
        with st.expander(f"🐛 Debug — {len(safe_debug)} rejetés en {elapsed}s"):
            if safe_debug:
                cols_d = st.columns(2)
                with cols_d[0]:
                    cats: Counter[str] = Counter()
                    for _, reason in safe_debug:
                        cats[reason.split(":")[0].strip()] += 1
                    st.markdown("**Raisons agrégées**")
                    for cat, n in cats.most_common():
                        st.markdown(f"- `{_safe_md(cat)}` → **{n}**")
                with cols_d[1]:
                    st.markdown("**Détail par actif**")
                    for ticker, reason in safe_debug[:30]:
                        st.markdown(
                            f"`{_safe_md(ticker)}` — {_safe_md(reason)}"
                        )

    counts: dict[str, int] = {}
    for row in status_rows:
        counts[row["Statut"]] = counts.get(row["Statut"], 0) + 1
    counts_txt = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    with st.expander(f"🩺 État du scan — {counts_txt}", expanded=not results):
        st.dataframe(
            pd.DataFrame(status_rows),
            hide_index=True,
            width="stretch",
        )

    if not results:
        st.warning("**Aucun signal valide détecté** sur cette session.")
        return

    kz_now = get_current_killzone(clock)
    df = pd.DataFrame(results)
    min_val = MIN_GRADE_MAP[min_grade]
    df = df[df["Grade"].map(GRADE_ORDER) >= min_val]
    if df.empty:
        st.info("Aucun signal avec ces filtres.")
        return

    df = sort_frame(df)
    st.markdown(kpi_html(df), unsafe_allow_html=True)
    st.markdown(
        _html(table_html(df, kz_now)),
        unsafe_allow_html=True,
    )
    st.markdown(
        footer_html(df, elapsed, now_utc, kz_now),
        unsafe_allow_html=True,
    )
