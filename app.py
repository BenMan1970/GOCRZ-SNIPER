"""BLUESTAR SNIPER V18 - Streamlit UI (navy-premium theme).

Mechanical corrections vs V16 (documented in CHANGELOG):
  * B-12  results persist in st.session_state - changing a filter no longer
          destroys a finished scan and forces a ~51s re-run
  * B-13  the engine fetches late timeframes lazily (~41% fewer calls)
  * token is NEVER rendered, logged, or embedded in error strings
  * strength fetch is cached (TTL 300s) - it changes at most intraday
Layout, KPI semantics, grade palette, sort order, and the killzone badge are
V16-faithful (V16 table pinned by tests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import time
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from bluestar.data import RawTransport

from bluestar import config
from bluestar.config import GRADE_ORDER
from bluestar.clock import current_killzone, killzone_badge, killzone_color
from bluestar.data import OandaClient, TokenBucket
from bluestar.engine import Engine, strength_from
from bluestar.ui_css import (
    AMBER,
    BASE_CSS,
    BLUE,
    BIAS_COLORS,
    GOLD,
    GRADE_COLORS,
    MAGENTA,
    MUTED,
    TEAL,
    VIOLET,
    ZONE_COLORS,
    brand_header,
    icon_arrow,
)

# Grade-minimum slider: label -> numeric order (aligned with GRADE_ORDER:
# filtering keeps grade k and everything ranked above it).
MIN_MAP = {"A+": 5, "A": 4, "B+": 3, "B": 2, "C": 1}


def _html(s: str) -> str:
    """Strip per-line indentation so markdown cannot read attributes as code."""
    return "\n".join(line.lstrip() for line in s.strip("\n").split("\n"))


def load_env() -> tuple[str, str]:
    """Read OANDA credentials from .env / streamlit secrets / environment.

    Priority: .env file (local dev) > st.secrets (Streamlit Cloud) >
    process environment. The token value is never rendered or logged.
    """
    import os
    from pathlib import Path

    values: dict[str, str] = {}
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    try:
        if "OANDA_ACCESS_TOKEN" in st.secrets:
            values.setdefault(
                "OANDA_ACCESS_TOKEN", str(st.secrets["OANDA_ACCESS_TOKEN"])
            )
            values.setdefault(
                "OANDA_ENVIRONMENT",
                str(st.secrets.get("OANDA_ENVIRONMENT", "practice")),
            )
    except Exception:
        pass  # no secrets backend (plain local run) - .env / env vars suffice
    values.setdefault("OANDA_ACCESS_TOKEN", os.environ.get("OANDA_ACCESS_TOKEN", ""))
    values.setdefault(
        "OANDA_ENVIRONMENT", os.environ.get("OANDA_ENVIRONMENT", "practice")
    )
    token = values.get("OANDA_ACCESS_TOKEN", "")
    env = values.get("OANDA_ENVIRONMENT", "practice")
    if not token:
        st.error("Credentials OANDA manquantes (.env / secrets / variables).")
        st.stop()
    return token, env


@st.cache_data(ttl=300, show_spinner=False)
def cached_strength(token: str, env: str) -> dict[str, float]:
    """Currency strength, cached 5 min (token used as cache key is NOT shown)."""
    client = OandaClient(RawTransportFor(token, env))
    return strength_from(client)


def RawTransportFor(token: str, env: str) -> "RawTransport":
    from bluestar.data import RawTransport

    return RawTransport(token, env, bucket=TokenBucket())


def build_engine(token: str, env: str, freshness: int = 30) -> Engine:
    client = OandaClient(RawTransportFor(token, env))
    return Engine(client=client, freshness_limit_min=freshness)


def fresh_cell(fresh_str: str, is_fresh: bool) -> str:
    from bluestar.ui_css import ICON_BOLT, ICON_CLOCK

    txt = fresh_str.replace("\u26a1", "").replace("\u23f3", "").strip()
    col = TEAL if is_fresh else MUTED
    ico = ICON_BOLT if is_fresh else ICON_CLOCK
    dot = (
        f'<span style="width:4px;height:4px;border-radius:50%;background:{col};'
        f'box-shadow:0 0 3px {col};display:inline-block"></span>'
        if is_fresh
        else ""
    )
    bg = "rgba(94,234,212,.16)" if is_fresh else "rgba(135,145,174,.14)"
    bd = "rgba(94,234,212,.6)" if is_fresh else "rgba(135,145,174,.4)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;color:{col};'
        f"background:{bg};border:1px solid {bd};padding:4px 10px;border-radius:30px;"
        f'font-size:12.5px;font-weight:600;white-space:nowrap">{dot}{ico}{txt}</span>'
    )


def sig_cell(sig: str, is_bull: bool) -> str:
    expired = "xp" in sig or "EXPIR" in sig.upper()
    col = (TEAL if is_bull else MAGENTA) if not expired else MUTED
    word = "LONG" if is_bull else "SHORT"
    if expired:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:6px;color:{col};'
            f'font-size:11.5px;letter-spacing:.1em;font-weight:600">'
            f"{icon_arrow(is_bull, 10)}{word} \u00b7 EXPIRE</span>"
        )
    return (
        f'<span style="display:inline-flex;align-items:center;gap:7px;color:{col};'
        f"background:{col}26;border:1px solid {col}99;padding:5px 12px 5px 10px;"
        f'border-radius:9px;font-size:14px;font-weight:700;letter-spacing:.09em">'
        f"{icon_arrow(is_bull, 12)}{word}</span>"
    )


def bias_cell(b: str) -> str:
    if b not in BIAS_COLORS:
        return '<span style="color:' + MUTED + ';font-size:14px">\u2014 Neutral</span>'
    label, col, strength, up = BIAS_COLORS[b]
    arrows = "".join(icon_arrow(up, 10) for _ in range(strength))
    return (
        f'<span style="display:inline-flex;align-items:center;gap:2px;color:{col};'
        f'font-size:14.5px;font-weight:700">{arrows}'
        f'<span style="margin-left:5px">{label}</span></span>'
    )


def zone_cell(z: str, mn_bonus: bool) -> str:
    from bluestar.ui_css import ICON_MOON

    col, bg, bd = ZONE_COLORS.get(z, ZONE_COLORS["EQUILIBRE"])
    moon = (
        f'<span style="color:{VIOLET};margin-left:7px" '
        f'title="Confluence midnight open">{ICON_MOON}</span>'
        if mn_bonus
        else ""
    )
    return (
        f'<span style="display:inline-flex;align-items:center">'
        f'<span style="color:{col};background:{bg};border:1px solid {bd};'
        f"padding:5px 11px;border-radius:7px;font-size:11px;font-weight:700;"
        f'letter-spacing:.11em;white-space:nowrap">{z}</span>{moon}</span>'
    )


def score_bar(score: int) -> str:
    if score >= 85:
        grad, col = (f"linear-gradient(90deg,{BLUE},{VIOLET} 55%,{MAGENTA})", "#E3D9FF")
    elif score >= 70:
        grad, col = f"linear-gradient(90deg,{TEAL},{BLUE})", "#C9E2FF"
    elif score >= 55:
        grad, col = "linear-gradient(90deg,#2E6E8E,#5EEAD4)", "#BDF4E9"
    elif score >= 40:
        grad, col = "linear-gradient(90deg,#54639B,#B9C6E4)", "#DDE5F6"
    else:
        grad, col = "linear-gradient(90deg,#39446C,#7E8CB6)", "#C6D0E8"
    width = (
        max(3, min(score, config.SCORE_MAX) / config.SCORE_MAX * 100)
        if score >= 0
        else 3
    )
    return (
        f'<div style="display:flex;align-items:center;gap:11px">'
        f'<span style="color:{col};font-weight:700;font-size:22px;'
        f'min-width:40px;text-align:right">{score}</span>'
        f'<div style="width:72px;height:6px;background:rgba(90,104,150,.55);'
        f'border-radius:3px;overflow:hidden">'
        f'<div style="width:{width}%;height:100%;background:{grad};'
        f'border-radius:3px"></div></div></div>'
    )


def adr_cell(v: float | None, label: str = "ADR", consumed: float | None = None) -> str:
    if v is None:
        return '<span style="color:' + MUTED + '">\u2014</span>'
    formatted = f"{v:.5f}" if v < 1.0 else f"{v:.2f}"
    tag_color = BLUE if label == "ADR" else GOLD
    head = (
        f'<span style="color:{tag_color};font-size:10px;font-weight:700;'
        f"background:{tag_color}12;border:1px solid {tag_color}40;padding:2px 6px;"
        f'border-radius:5px">{label}</span>'
        f'<span style="font-weight:600;font-size:15px">{formatted}</span>'
    )
    head = f'<div style="display:flex;align-items:baseline;gap:7px">{head}</div>'
    if consumed is None or (isinstance(consumed, float) and np.isnan(consumed)):
        return head
    consumed = float(consumed)
    c = TEAL if consumed < 40 else (AMBER if consumed < 70 else MAGENTA)
    fill = int(min(max(consumed, 0), 100))
    gauge = (
        f'<div style="display:flex;align-items:center;gap:7px;margin-top:6px">'
        f'<div style="width:60px;height:4px;background:rgba(90,104,150,.55);'
        f'border-radius:2px;overflow:hidden">'
        f'<div style="width:{fill}%;height:100%;background:{c};'
        f'border-radius:2px"></div></div>'
        f'<span style="color:{c};font-size:11px;font-weight:700">'
        f"{consumed:.0f}%</span></div>"
    )
    return f"<div>{head}{gauge}</div>"


def force_cell(momentum: int, delta: float, is_bull: bool) -> str:
    col = TEAL if is_bull else MAGENTA
    seg = "".join(
        (
            f'<div style="width:16px;height:9px;border-radius:2px;background:{col};'
            f'box-shadow:0 0 4px -1px {col}"></div>'
            if i < momentum
            else '<div style="width:16px;height:9px;border-radius:2px;'
            'background:rgba(90,104,150,.35)"></div>'
        )
        for i in range(3)
    )
    dtxt = (
        ""
        if delta is None
        else (f'<span style="color:{col};font-weight:700">{delta:+.2f}</span>')
    )
    return (
        f'<div style="display:flex;flex-direction:column;gap:4px">'
        f'<div style="display:flex;gap:3px">{seg}</div>{dtxt}</div>'
    )


def grade_chip(grade: str) -> str:
    s = GRADE_COLORS[grade]
    return (
        f'<span style="color:{s["color"]};border:1.5px solid {s["line"]};'
        f"background:{s['bg']};padding:5px 12px;border-radius:9px;"
        f'font-weight:800;font-size:14px;letter-spacing:.06em">{grade}</span>'
    )


def sort_key(row: pd.Series) -> tuple[int, int, int, int, int]:
    """V16 order: fresh first, then grade, score, momentum, MTF."""
    fresh = 1 if "\u26a1" in str(row["Fra\u00eecheur"]) else 0
    g = GRADE_ORDER.get(row["Grade"], 0)
    s = row["Score /100"]
    m = row["MTF Pct"]
    mom = row.get("Momentum", 0)
    return (-fresh, -g, -s, -mom, -m)


def main() -> None:
    st.set_page_config(
        page_title=config.APP_NAME,
        page_icon="\U0001f3af",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_html(BASE_CSS), unsafe_allow_html=True)

    token, env = load_env()
    kz_now = current_killzone()

    with st.sidebar:
        st.markdown(
            _html(brand_header(killzone_badge(kz_now), killzone_color(kz_now))),
            unsafe_allow_html=True,
        )
        freshness = st.slider(
            "Fraicheur max du signal (min)", 15, 60, 30, step=5
        )  # wired into Engine freshness
        min_grade = st.select_slider("Grade minimum", list(MIN_MAP), "B")
        show_debug = st.checkbox("Afficher le debug", False)
        st.caption("Mode lecture seule \u2014 aucun ordre n'est passe")
        st.caption(f"Environnement: {env} \u00b7 token **masque**")
        run = st.button("\U0001f680 LANCER LE SCANNER", use_container_width=True)

    results = st.session_state.get("results", None)
    if run:
        engine = build_engine(token, env, freshness=freshness)
        progress = st.progress(0)
        status = st.empty()
        t0 = time.perf_counter()

        strength_scores = {}
        with st.spinner("Currency Strength H1..."):
            try:
                strength_scores = cached_strength(token, env)
            except Exception:
                strength_scores = {}

        signals, rejects, _ = engine.scan(
            list(config.ASSETS),
            strength_scores=strength_scores,
            parallel=True,
            max_workers=3,
        )
        progress.progress(1.0)
        status.empty()
        elapsed = round(time.perf_counter() - t0, 1)
        rows = [s.payload | {"_ticker": s.ticker} for s in signals]
        st.session_state["results"] = {
            "rows": rows,
            "rejects": rejects,
            "elapsed": elapsed,
            "at": str(datetime.now()),
        }
        results = st.session_state["results"]

    if not results:
        st.markdown(
            _html(f"""
        <div style="text-align:center;padding:86px 0 74px;color:#C9D6F2">
          <div style="font-size:15px;font-weight:500">Scanner en veille</div>
          <div style="font-size:12.5px;opacity:.7;margin-top:7px;
               letter-spacing:.04em">{len(config.ASSETS)} instruments \u00b7
               6 timeframes \u00b7 lance l'analyse pour r\u00e9v\u00e9ler "
               "les setups actifs</div>
        </div>"""),
            unsafe_allow_html=True,
        )
        return

    reject_log = [(r.ticker, r.reason) for r in results.get("rejects", [])]
    if show_debug and reject_log:
        with st.expander(
            f"\U0001f41b Debug \u2014 {len(reject_log)} rejet\u00e9s "
            f"en {results.get('elapsed')}s"
        ):
            cats = Counter(reason.split(":")[0].strip() for _, reason in reject_log)
            st.markdown("**Raisons agr\u00e9g\u00e9es**")
            for cat, n in cats.most_common():
                st.markdown(f"- `{cat}` \u2192 **{n}**")

    df = pd.DataFrame(results["rows"])
    if df.empty:
        st.warning("**Aucun signal valide d\u00e9tect\u00e9** sur cette session.")
        return

    df = df[df["Grade"].map(GRADE_ORDER) >= MIN_MAP[min_grade]]
    if df.empty:
        st.info("Aucun signal avec ces filtres.")
        return
    df["_sk"] = df.apply(sort_key, axis=1)
    df = df.sort_values("_sk").drop(columns=["_sk"]).reset_index(drop=True)

    a_plus = len(
        df[
            (df["Grade"] == "A+")
            & df["Fra\u00eecheur"].str.contains("\u26a1", na=False)
        ]
    )
    a_grade = len(
        df[(df["Grade"] == "A") & df["Fra\u00eecheur"].str.contains("\u26a1", na=False)]
    )
    b_watch = len(
        df[
            df["Grade"].isin(["B+", "B"])
            & df["Fra\u00eecheur"].str.contains("\u26a1", na=False)
        ]
    )
    longs = len(
        df[
            df["Signal"].str.contains("LONG", na=False)
            & ~df["Signal"].str.contains("xp")
        ]
    )
    shorts = len(
        df[
            df["Signal"].str.contains("SHORT", na=False)
            & ~df["Signal"].str.contains("xp")
        ]
    )
    max_mom = len(df[df.get("Momentum", 0) == 3]) if "Momentum" in df.columns else 0

    from bluestar.ui_css import ICON_CLOCK, ICON_STAR, ICON_TARGET

    kpis = [
        ("A+ PREMIUM", a_plus, VIOLET, ICON_TARGET),
        ("GRADE A", a_grade, BLUE, ICON_TARGET),
        ("WATCHLIST", b_watch, GOLD, ICON_CLOCK),
        ("LONG ACTIFS", longs, TEAL, icon_arrow(True, 12)),
        ("SHORT ACTIFS", shorts, MAGENTA, icon_arrow(False, 12)),
        ("FORCE MAX", max_mom, AMBER, ICON_STAR),
    ]
    cards = "".join(
        f'<div class="kpi{"" if v else " kpi-dim"}" style="--acc:{c}">'
        f'<div class="kpi-l"><span style="color:{c}">{ic}</span>{lbl}</div>'
        f'<div class="kpi-v">{v}</div></div>'
        for lbl, v, c, ic in kpis
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)

    header = (
        "<tr><th>Signal</th><th>Actif</th><th>Fra\u00eecheur</th>"
        "<th>Score</th><th>Grade</th><th>Biais Daily</th><th>Zone</th>"
        "<th>ADR (consomm\u00e9)</th><th>MTF</th><th>Force</th>"
        "<th>Alignement</th></tr>"
    )
    rows_html = [header]
    for _, r in df.iterrows():
        is_fresh = "\u26a1" in str(r["Fra\u00eecheur"])
        display = config.DISPLAY_NAMES.get(r["_ticker"], r["_ticker"])
        rows_html.append(
            "<tr><td>" + sig_cell(r["Signal"], bool(r["signal_is_bull"])) + "</td>"
            f'<td style="font-weight:700">{display}</td>'
            "<td>" + fresh_cell(str(r["Fra\u00eecheur"]), is_fresh) + "</td>"
            "<td>" + score_bar(int(r["Score /100"])) + "</td>"
            "<td>" + grade_chip(r["Grade"]) + "</td>"
            "<td>" + bias_cell(r["Biais Daily"]) + "</td>"
            "<td>" + zone_cell(r["Zone"], bool(r["Midnight Bonus"])) + "</td>"
            "<td>" + adr_cell(r["ADR"], r["ADR Label"], r["ADR Consumed"]) + "</td>"
            f"<td>{r['MTF Pct']}%</td>"
            "<td>"
            + force_cell(
                int(r["Momentum"]), r["Strength \u0394"], bool(r["signal_is_bull"])
            )
            + "</td>"
            f"<td>{r['Alignement']}</td></tr>"
        )
    table = (
        '<div style="overflow-x:auto"><table class="bs-table">'
        + "".join(rows_html)
        + "</table></div>"
    )
    st.markdown(_html(table), unsafe_allow_html=True)

    kz_badge = killzone_badge(kz_now)
    kz_col = killzone_color(kz_now)
    st.markdown(
        _html(f"""
    <div style="display:flex;justify-content:space-between;padding:14px 4px 24px;
         color:#93A1C7;font-size:12px">
      <span>Killzone: <b style="color:{kz_col}">{kz_badge or "HORS KZ"}</b>
        \u00b7 A+ \u2265 85 \u00b7 A \u2265 70 \u00b7 B+ \u2265 55 "
        "\u00b7 B \u2265 40</span>
      <span>Scan de {results.get("elapsed")}s \u00b7
        {datetime.now().strftime("%H:%M:%S")}</span>
    </div>"""),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
