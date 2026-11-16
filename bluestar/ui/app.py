"""Point d'entrée Streamlit. Mince : câblage + rendu uniquement."""

from __future__ import annotations

import html
import os
import time
from collections import Counter
from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from .. import __version__
from ..clock import SystemClock
from ..config import (
    ADR_MALUS,
    ADR_MALUS_THRESHOLD,
    ADX_POINTS,
    ADX_TREND_MIN,
    ASSETS,
    BIAS_POINTS,
    COUNTER_MALUS,
    DEFAULT_FRESHNESS_MIN,
    DISPLAY_NAMES,
    FRESHNESS_CHOICES,
    HMA_FLIP_LOOKBACK,
    HMA_PRICE_TOLERANCE_ATR,
    OANDA_API_HOSTS,
    RATE_BURST,
    RATE_PER_S,
    SCORE_WEIGHTS,
)
from ..data.oanda import AuthenticationError, OandaSource, TokenBucket, redact
from ..engine import ScanOutput, run_scan
from ..logging_utils import register_secret
from ..status import SIGNAL, classify
from ..timeutil import get_current_killzone
from .render import (
    _html,
    apply_filters,
    build_frame,
    footer_html,
    killzone_badge,
    killzone_color,
    kpi_html,
    sort_frame,
    table_html,
)
from .theme import theme_css

APP_VERSION = "V" + ".".join(__version__.split(".")[:2])
SCAN_KEY = "bluestar_scan"
STALE_SCAN_MIN = 10          # au-delà, on avertit que les résultats ont vieilli
MIN_GRADE_CHOICES = ["Tous", "B", "B+", "A", "A+"]


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
            <span>Force devise &amp; ADX</span>
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
            {n_assets} instruments · 6 timeframes · flips HMA &amp; continuations ICT
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


def _grid_markdown() -> str:
    w = SCORE_WEIGHTS
    return f"""
| Critère | Max | Détail |
|---|---|---|
| **Trigger HMA** | {w['Trigger']} pts | flip ≤15 min = 30 · ≤30 min = 20 · ≤45 min = 10 · plus ancien ou continuation = 0 |
| **MTF** | {w['MTF']} pts | ≥80 % = 25 · ≥65 % = 18 · ≥50 % = 10 · aligné <50 % = 5 · contre-MTF = 0 |
| **Zone** | {w['Zone']} pts | LONG en DISCOUNT/EXT LOW, SHORT en PREMIUM/EXT HIGH = {w['Zone']} · sinon 0 |
| **Biais daily** | {w['Bias']} pts | aligné fort = {BIAS_POINTS['STRONG']} · aligné = {BIAS_POINTS['NORMAL']} · neutre ou contraire = 0 |
| **Force devise** | {w['Force']} pts | Δ favorable ≥5 = 10 · ≥3 = 7 · ≥1,5 = 4 (indisponible pour métaux/indices : score renormalisé) |
| **ADX** | {w['ADX']} pts | nb de TF (H4·H1·M15) avec ADX > {ADX_TREND_MIN:g} : 3 = {ADX_POINTS[3]} · 2 = {ADX_POINTS[2]} · 1 = {ADX_POINTS[1]} · non crédité si COUNTER |
| **Malus ADR** | -{ADR_MALUS} | range du jour de trading (depuis 17h NY) > {ADR_MALUS_THRESHOLD:g} % de l'ADR |
| **Malus contre-biais** | -{COUNTER_MALUS} | signal contraire au biais daily (⚠ COUNTER) |

Score sur **100**, borné à [0 ; 100]. Grades : A+ ≥85 · A ≥70 · B+ ≥55 · B ≥40 · C.

**Types de signal.** *Flip* : la HMA 20 (M15) vient de changer de couleur (≤{HMA_FLIP_LOOKBACK} bougies). *Tendance* : pas de flip récent, mais biais daily aligné **et** zone favorable ; le Trigger vaut alors 0 (score max 70).

**Côté de la HMA.** Le prix doit être du bon côté de la HMA 20. Un écart ≤ {HMA_PRICE_TOLERANCE_ATR:g} ATR M15 est toléré (chip PULLBACK HMA) ; au-delà, rejet avec l'écart en ATR.

**Biais daily** : 7 votes (structure ±2, EMA 21/50, Weekly Open, clôture J-1, pente EMA50, pente HMA20). Directionnel à ≥3 votes et majorité stricte ; STRONG à ≥5. Une structure cassée interdit seulement de continuer dans le sens cassé.

**Tendance MTF** : une seule définition pour M, W, D, 4H, 1H, 15m (vote de 5 critères : close/EMA50, EMA21/50, EMA9/21, RSI, MACD).
"""


def _status_rows(
    assets: tuple[str, ...], scan: ScanOutput, now: datetime, token: str
) -> list[dict[str, str]]:
    by_ticker = {r["ticker"]: r for r in scan.results}
    reasons = dict(scan.rejects)
    rows: list[dict[str, str]] = []
    for ticker in assets:
        display = DISPLAY_NAMES.get(ticker, ticker)
        if ticker in by_ticker:
            r = by_ticker[ticker]
            kind = "tendance" if r["signal_type"] == "CONTINUATION" else "flip"
            rows.append({
                "Actif": display,
                "Statut": SIGNAL,
                "Détail": (
                    f"{'LONG' if r['is_bull'] else 'SHORT'} ({kind}) · {r['grade']} · "
                    f"{r['score']}/100 · {r['zone']}"
                ),
            })
        else:
            reason = reasons.get(ticker, "NO_RESULT")
            rows.append({
                "Actif": display,
                "Statut": classify(reason, now),
                "Détail": redact(reason, token),
            })
    return rows


def _debug_frame(results: list[dict[str, object]]) -> pd.DataFrame:
    """Tout ce qui explique un signal, sans rien à déduire."""
    def adx_text(values: dict[str, float | None]) -> str:
        return " · ".join(f"{k} {'n/a' if v is None else v}" for k, v in values.items())

    df = pd.DataFrame(results)
    df["adx"] = df["adx_values"].map(adx_text)
    df["pullback_hma"] = df["hma_pullback"].map({True: "oui", False: ""})
    return df[
        ["ticker", "signal_type", "alignment", "zone", "bias", "bias_detail",
         "strength_delta", "adx", "hma_gap_atr", "pullback_hma",
         "score", "score_detail", "mtf_detail"]
    ].rename(columns={"strength_delta": "Δ force", "hma_gap_atr": "écart HMA (ATR)"})


def _run_scan(token: str, env: str, clock: SystemClock) -> dict[str, object]:
    t_start = time.time()
    progress = st.progress(0)
    status = st.empty()

    def on_progress(done: int, total: int, ticker: str) -> None:
        progress.progress(min(done / total, 1.0))
        status.caption(f"⏳ {DISPLAY_NAMES.get(ticker, ticker)}… ({done}/{total})")

    source = OandaSource(
        token, env, limiter=TokenBucket(rate_per_s=RATE_PER_S, burst=RATE_BURST)
    )
    try:
        output = run_scan(source, clock, ASSETS, progress=on_progress)
    finally:
        source.close()
        progress.empty()
        status.empty()
    return {
        "output": output,
        "elapsed": round(time.time() - t_start, 1),
        "at": clock.now(UTC),
    }


def main() -> None:
    st.set_page_config(
        page_title="Bluestar Sniper · Market Intelligence",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(theme_css(), unsafe_allow_html=True)

    clock = SystemClock()
    token = _secret("OANDA_ACCESS_TOKEN")
    register_secret(token)
    if not token:
        st.error("🔑 **Secret manquant :** `OANDA_ACCESS_TOKEN`")
        st.stop()

    env = str(_secret("OANDA_ENVIRONMENT", "practice") or "practice").strip().lower()
    if env not in OANDA_API_HOSTS:
        st.error(f"⚠️ OANDA_ENVIRONMENT invalide : `{env}` — doit être `practice` ou `live`")
        st.stop()
    if env == "live":
        st.warning("⚠️ **CONNEXION COMPTE RÉEL (live)** — lecture seule, mais données du compte réel")

    st.markdown(_header_html(get_current_killzone(clock)), unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns([1.3, 1, 1.15, 1.15, 1.15, 0.8])
    with c1:
        freshness = st.selectbox(
            "Fraîcheur max du flip (min)",
            list(FRESHNESS_CHOICES),
            index=list(FRESHNESS_CHOICES).index(DEFAULT_FRESHNESS_MIN),
        )
    with c2:
        min_grade = st.selectbox("Grade minimum", MIN_GRADE_CHOICES, index=0)
    with c3:
        include_cont = st.toggle("Inclure les tendances", value=True)
    with c4:
        hide_counter = st.toggle("Masquer COUNTER", value=True)
    with c5:
        hide_expired = st.toggle("Masquer expirés", value=False)
    with c6:
        show_debug = st.toggle("🐛 Debug", value=False)

    with st.expander("📘 Grille de notation V17"):
        st.markdown(_grid_markdown())

    if st.button("🚀  LANCER LE SCANNER", width="stretch"):
        try:
            st.session_state[SCAN_KEY] = _run_scan(token, env, clock)
        except AuthenticationError:
            st.error(
                "🔑 **Token OANDA invalide ou expiré.** "
                "Vérifie `OANDA_ACCESS_TOKEN` puis relance le scanner."
            )
            st.stop()

    scan = st.session_state.get(SCAN_KEY)
    if scan is None:
        st.markdown(_idle_html(len(ASSETS)), unsafe_allow_html=True)
        return

    # ----- Résultats : persistants, les filtres ci-dessus n'imposent AUCUN rescan -----
    output: ScanOutput = scan["output"]
    scanned_at: datetime = scan["at"]
    now = clock.now(UTC)
    age_min = (now - scanned_at).total_seconds() / 60.0
    if age_min > STALE_SCAN_MIN:
        st.warning(
            f"⏱ Scan vieux de {age_min:.0f} min : fraîcheurs et prix ne sont plus à jour. "
            "Relance le scanner."
        )

    safe_rejects = [(t, redact(r, token)) for t, r in output.rejects]
    status_rows = _status_rows(ASSETS, output, now, token)

    if show_debug:
        with st.expander(f"🐛 Debug — {len(safe_rejects)} rejetés en {scan['elapsed']}s", expanded=True):
            left, right = st.columns(2)
            with left:
                cats = Counter(r.split(":")[0].strip() for _, r in safe_rejects)
                st.markdown("**Raisons agrégées**")
                for cat, n in cats.most_common():
                    st.markdown(f"- `{_safe_md(cat)}` → **{n}**")
            with right:
                st.markdown("**Détail par actif**")
                for ticker, reason in safe_rejects:
                    st.markdown(f"`{_safe_md(ticker)}` — {_safe_md(reason)}")
            if output.results:
                st.markdown("**Pourquoi ce biais / ce score (signaux retenus)**")
                st.dataframe(_debug_frame(output.results), hide_index=True, width="stretch")

    counts = Counter(row["Statut"] for row in status_rows)
    counts_txt = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    with st.expander(f"🩺 État du scan — {counts_txt}", expanded=not output.results):
        st.dataframe(pd.DataFrame(status_rows), hide_index=True, width="stretch")

    if not output.results:
        st.warning("**Aucun signal valide détecté** sur cette session.")
        return

    frame = build_frame(output.results, freshness)
    n_counter = int((frame["alignment"] == "COUNTER").sum())
    frame = apply_filters(frame, min_grade, include_cont, hide_counter, hide_expired)
    if hide_counter and n_counter:
        st.caption(f"{n_counter} signal(s) COUNTER masqué(s) — désactive « Masquer COUNTER » pour les voir.")
    if frame.empty:
        st.info("Aucun signal avec ces filtres.")
        return

    frame = sort_frame(frame)
    kz_now = get_current_killzone(clock)
    st.markdown(kpi_html(frame), unsafe_allow_html=True)
    st.markdown(_html(table_html(frame)), unsafe_allow_html=True)
    st.markdown(
        footer_html(len(frame), scan["elapsed"], scanned_at, kz_now),
        unsafe_allow_html=True,
    )
