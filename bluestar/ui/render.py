"""Pure HTML rendering helpers (no Streamlit imports)."""

from __future__ import annotations

import html
from datetime import datetime

import numpy as np
import pandas as pd

from ..config import DISPLAY_NAMES, GRADE_ORDER

KZ_STYLE = {
    "London": ("LONDON", "#7db7ff"),
    "NY AM": ("NEW YORK AM", "#b7a4ff"),
    "Asia": ("ASIA", "#5eead4"),
}


def killzone_badge(kz: str) -> str:
    return KZ_STYLE.get(kz, ("", ""))[0]


def killzone_color(kz: str) -> str:
    return KZ_STYLE.get(kz, ("", "#a7b6d4"))[1]


def icon_arrow(up: bool, size: int = 12) -> str:
    d = "M7 2.4 11.7 9.6H2.3z" if up else "M7 11.6 2.3 4.4h9.4z"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 14 14" '
        f'style="vertical-align:-1px"><path d="{d}" fill="currentColor"/></svg>'
    )


ICON_BOLT = (
    '<svg width="11" height="11" viewBox="0 0 14 14" style="vertical-align:-1px">'
    '<path d="M8.1 1 3.2 8.1h2.9L5.4 13l5.4-7.4H7.4L8.1 1z" fill="currentColor"/></svg>'
)
ICON_CLOCK = (
    '<svg width="11" height="11" viewBox="0 0 14 14" fill="none" style="vertical-align:-1px">'
    '<circle cx="7" cy="7" r="5.1" stroke="currentColor" stroke-width="1.25"/>'
    '<path d="M7 4.3V7.2l1.9 1.2" stroke="currentColor" stroke-width="1.25" '
    'stroke-linecap="round"/></svg>'
)
ICON_MOON = (
    '<svg width="11" height="11" viewBox="0 0 14 14" style="vertical-align:-1px">'
    '<path d="M9.5 9A4.3 4.3 0 0 1 5.2 4.7c0-.8.2-1.6.6-2.2A5 5 0 1 0 11.7 8.4c-.6.4-1.4.6-2.2.6z" '
    'fill="currentColor"/></svg>'
)
ICON_ALERT = (
    '<svg width="11" height="11" viewBox="0 0 14 14" fill="none" style="vertical-align:-1px">'
    '<path d="M7 2 12.4 11.4H1.6L7 2z" stroke="currentColor" stroke-width="1.15"/>'
    '<path d="M7 5.6v2.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'
    '<circle cx="7" cy="10" r=".72" fill="currentColor"/></svg>'
)
ICON_TARGET = (
    '<svg width="13" height="13" viewBox="0 0 16 16" fill="none">'
    '<circle cx="8" cy="8" r="6.2" stroke="currentColor" stroke-width="1.2" opacity=".45"/>'
    '<circle cx="8" cy="8" r="2.6" stroke="currentColor" stroke-width="1.2"/>'
    '<circle cx="8" cy="8" r="1" fill="currentColor"/></svg>'
)


def _html(s: str) -> str:
    return "\n".join(line.lstrip() for line in s.strip("\n").split("\n"))


GRADE_STYLE = {
    "A+": {"color": "#d6ccff", "line": "#b7a4ff", "bg": "rgba(183,164,255,.10)", "label": "A+"},
    "A":  {"color": "#b9dbff", "line": "#7db7ff", "bg": "rgba(125,183,255,.08)", "label": "A"},
    "B+": {"color": "#b8f5ea", "line": "#5eead4", "bg": "rgba(94,234,212,.055)", "label": "B+"},
    "B":  {"color": "#c3cfe6", "line": "#8496b8", "bg": "transparent", "label": "B"},
    "C":  {"color": "#aebbd6", "line": "#5d6a92", "bg": "transparent", "label": "C"},
}

BIAS_MAP = {
    "STRONG BULLISH": ("Strong bull", "#5eead4", 2, True),
    "BULLISH":        ("Bull",        "#a9f3e6", 1, True),
    "STRONG BEARISH": ("Strong bear", "#f7a6cf", 2, False),
    "BEARISH":        ("Bear",        "#f9c3de", 1, False),
}

ZONE_MAP = {
    "DISCOUNT":  ("#8ec5ff", "rgba(125,183,255,.14)", "rgba(125,183,255,.55)"),
    "PREMIUM":   ("#f9b8dc", "rgba(247,166,207,.14)", "rgba(247,166,207,.55)"),
    "EXT HIGH":  ("#f78ec4", "rgba(247,142,196,.18)", "rgba(247,142,196,.7)"),
    "EXT LOW":   ("#7ff0dc", "rgba(94,234,212,.16)",  "rgba(94,234,212,.7)"),
    "EQUILIBRE": ("#cbd6ea", "rgba(167,182,212,.14)", "rgba(167,182,212,.45)"),
}


def fresh_cell(fresh_str: str, is_fresh: bool) -> str:
    txt = html.escape(fresh_str.replace("⚡", "").replace("⏳", "").strip())
    col = "#5eead4" if is_fresh else "#a7b6d4"
    ico = ICON_BOLT if is_fresh else ICON_CLOCK
    dot = (
        f'<span class="bs-dot" style="width:5px;height:5px;border-radius:50%;'
        f'background:{col};box-shadow:0 0 0 2px {col}22"></span>' if is_fresh else ""
    )
    bg = "linear-gradient(180deg,rgba(94,234,212,.18),rgba(94,234,212,.1))" if is_fresh \
        else "linear-gradient(180deg,rgba(167,182,212,.13),rgba(167,182,212,.07))"
    bd = "rgba(94,234,212,.55)" if is_fresh else "rgba(167,182,212,.34)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:7px;color:{col};'
        f'background:{bg};border:1px solid {bd};padding:5px 11px;border-radius:999px;'
        f"font-family:'IBM Plex Mono',monospace;font-size:12.5px;font-weight:600;"
        f'letter-spacing:-.01em;white-space:nowrap;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)">'
        f'{dot}<span style="display:inline-flex">{ico}</span>{txt}</span>'
    )


def sig_cell(sig: str, is_bull: bool) -> str:
    expired = "expiré" in sig
    col = ("#5eead4" if is_bull else "#f7a6cf") if not expired else "#a7b6d4"
    word = "LONG" if is_bull else "SHORT"
    if expired:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:7px;color:{col};'
            f'font-size:12px;letter-spacing:.12em;font-weight:700">'
            f'<span style="display:inline-flex;opacity:.8">{icon_arrow(is_bull, 10)}</span>'
            f'{word} · EXPIRÉ</span>'
        )
    return (
        f'<span style="display:inline-flex;align-items:center;gap:8px;color:{col};'
        f'background:linear-gradient(180deg,{col}2e,{col}18);border:1px solid {col}8c;'
        f'padding:6px 13px 6px 11px;border-radius:10px;font-size:14.5px;font-weight:800;'
        f'letter-spacing:.1em;box-shadow:inset 0 1px 0 rgba(255,255,255,.06)">'
        f'<span style="display:inline-flex">{icon_arrow(is_bull, 12)}</span>{word}</span>'
    )


def bias_cell(b: str) -> str:
    if b not in BIAS_MAP:
        return (
            '<span style="color:#a7b6d4;font-size:14px;letter-spacing:.04em">'
            "— Neutral</span>"
        )
    label, col, strength, up = BIAS_MAP[b]
    arrows = "".join(
        f'<span style="display:inline-flex">{icon_arrow(up, 10)}</span>'
        for _ in range(strength)
    )
    return (
        f'<span style="display:inline-flex;align-items:center;gap:2px;color:{col};'
        f'font-size:14.5px;font-weight:700;letter-spacing:.01em">'
        f'{arrows}<span style="margin-left:5px">{html.escape(label)}</span></span>'
    )


def zone_cell(z: str, mn_bonus: bool) -> str:
    col, bg, bd = ZONE_MAP.get(z, ZONE_MAP["EQUILIBRE"])
    moon = (
        f'<span style="color:#d6ccff;display:inline-flex;margin-left:7px" '
        f'title="Confluence midnight open">{ICON_MOON}</span>' if mn_bonus else ""
    )
    return (
        f'<span style="display:inline-flex;align-items:center">'
        f'<span style="color:{col};background:{bg};border:1px solid {bd};'
        f'padding:5px 12px;border-radius:8px;font-size:11.5px;font-weight:800;'
        f'letter-spacing:.12em;white-space:nowrap;box-shadow:inset 0 1px 0 rgba(255,255,255,.045)">'
        f'{html.escape(z)}</span>{moon}</span>'
    )


def score_bar(score: int) -> str:
    if score >= 85:
        grad, col = (
            "linear-gradient(90deg,#7db7ff,#b7a4ff 55%,#f7a6cf)",
            "#ece6ff",
        )
    elif score >= 70:
        grad, col = (
            "linear-gradient(90deg,#5eead4,#7db7ff)",
            "#dcecff",
        )
    elif score >= 55:
        grad, col = (
            "linear-gradient(90deg,#3f7fa0,#5eead4)", "#d9fbf5",
        )
    elif score >= 40:
        grad, col = (
            "linear-gradient(90deg,#5d6a92,#a7b6d4)", "#e1e7f5",
        )
    else:
        grad, col = (
            "linear-gradient(90deg,#334266,#8496b8)", "#c3cfe6",
        )
    width = max(3, min(score, 103) / 103 * 100) if score >= 0 else 3
    return (
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<span style="color:{col};font-weight:600;font-size:23px;'
        f"font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;"
        f'letter-spacing:-.04em;min-width:42px;text-align:right">{score}</span>'
        f'<div style="width:84px;height:7px;background:rgba(54,82,127,.55);'
        f'border-radius:4px;overflow:hidden;box-shadow:inset 0 1px 2px rgba(0,0,0,.35)">'
        f'<div style="width:{width}%;height:100%;background:{grad};'
        f'border-radius:4px;box-shadow:0 0 10px -3px rgba(125,183,255,.55)"></div></div></div>'
    )


def adr_cell(v: float | None, label: str = "ADR", consumed: float | None = None) -> str:
    if v is None:
        return '<span style="color:#a7b6d4">—</span>'
    formatted = f"{v:.5f}" if v < 1.0 else f"{v:.2f}"
    tag_color = "#7db7ff" if label == "ADR" else "#c4b5fd"
    head = (
        f'<div style="display:flex;align-items:baseline;gap:8px">'
        f'<span style="color:{tag_color};font-size:10px;font-weight:800;letter-spacing:.13em;'
        f'background:{tag_color}14;border:1px solid {tag_color}45;padding:2px 7px;'
        f'border-radius:6px">{html.escape(label)}</span>'
        f'<span style="color:var(--ink);font-weight:600;'
        f"font-family:'IBM Plex Mono',monospace;"
        f'font-size:15.5px;font-variant-numeric:tabular-nums;letter-spacing:-.02em">'
        f'{formatted}</span></div>'
    )
    if consumed is None or (isinstance(consumed, float) and np.isnan(consumed)):
        return head
    consumed = float(consumed)
    if consumed < 40:
        c = "#5eead4"
    elif consumed < 70:
        c = "#f7c66b"
    else:
        c = "#f7a6cf"
    fill = int(min(max(consumed, 0), 100))
    gauge = (
        f'<div style="display:flex;align-items:center;gap:8px;margin-top:7px">'
        f'<div style="width:66px;height:5px;background:rgba(54,82,127,.55);'
        f'border-radius:3px;overflow:hidden;box-shadow:inset 0 1px 2px rgba(0,0,0,.35)">'
        f'<div style="width:{fill}%;height:100%;background:{c};border-radius:3px">'
        f'</div></div>'
        f"<span style=\"color:{c};font-size:11.5px;font-family:'IBM Plex Mono',monospace;"
        f'font-weight:600;font-variant-numeric:tabular-nums">{consumed:.0f}%</span></div>'
    )
    return f"<div>{head}{gauge}</div>"


def force_cell(momentum_score: int, delta: float | None, is_bull: bool) -> str:
    col = "#5eead4" if is_bull else "#f7a6cf"
    seg = "".join(
        (
            f'<div style="width:17px;height:10px;border-radius:3px;background:{col};'
            f'box-shadow:0 0 8px -4px {col}"></div>'
        ) if i < momentum_score else
        '<div style="width:17px;height:10px;border-radius:3px;background:rgba(54,82,127,.55);'
        'box-shadow:inset 0 1px 2px rgba(0,0,0,.35)"></div>'
        for i in range(3)
    )
    bars = f'<div style="display:flex;gap:5px;align-items:center">{seg}</div>'
    if delta is not None:
        dc = "#5eead4" if delta >= 1.5 else "#f7a6cf" if delta <= -1.5 else "#a7b6d4"
        sign = "+" if delta > 0 else ""
        dh = (
            f'<span style="color:{dc};background:{dc}18;border:1px solid {dc}66;'
            f'padding:3px 8px;border-radius:7px;font-weight:600;font-size:13px;'
            f"font-family:'IBM Plex Mono',monospace;margin-left:11px;"
            f'font-variant-numeric:tabular-nums">{sign}{delta:.1f}</span>'
        )
    else:
        dh = (
            '<span style="color:#a7b6d4;margin-left:11px;font-size:12px;'
            "font-family:'IBM Plex Mono',monospace\">n/a</span>"
        )
    return f'<div style="display:flex;align-items:center">{bars}{dh}</div>'


TABLE_CSS = """
<style>
.sc-wrap{overflow-x:auto;border:1px solid #28406c;border-radius:19px;
  background:linear-gradient(180deg,#0b1934,#081228);
  box-shadow:0 34px 80px -52px #000,inset 0 1px 0 rgba(255,255,255,.045)}
.sc-tbl{width:100%;border-collapse:separate;border-spacing:0;
  font-family:'Manrope',sans-serif;font-size:15px;font-weight:500;color:var(--ink)}
.sc-tbl thead th{
  padding:15px 20px;text-align:left;white-space:nowrap;
  color:#c3d3ee;font-size:10.5px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
  background:#0e1f3f;border-bottom:1px solid #2f4b7b;
  position:sticky;top:0;z-index:2}
.sc-tbl td{padding:16px 20px;border-bottom:1px solid rgba(54,82,127,.42);vertical-align:middle}
.sc-tbl th+th,.sc-tbl td+td{border-left:1px solid rgba(54,82,127,.18)}
.sc-tbl tbody tr:nth-child(even) td{background:rgba(125,183,255,.032)}
.sc-tbl tbody tr{transition:background .14s ease}
.sc-tbl tbody tr:hover td{background:rgba(125,183,255,.085)}
.sc-tbl tbody tr:last-child td{border-bottom:none}
.sc-tbl td:first-child{position:relative;padding-left:22px}
.sc-tbl td:first-child::before{content:"";position:absolute;left:0;top:9px;bottom:9px;width:3px;
  border-radius:0 3px 3px 0}
.rail-bull td:first-child::before{background:linear-gradient(180deg,#5eead4,rgba(94,234,212,.12))}
.rail-bear td:first-child::before{background:linear-gradient(180deg,#f7a6cf,rgba(247,166,207,.12))}
.ticker{font-family:'IBM Plex Mono',monospace;font-size:19.5px;font-weight:600;color:var(--ink);
  white-space:nowrap;letter-spacing:-.035em;font-variant-numeric:tabular-nums}
.stale .ticker{color:#b9c9e6}
.grade-pill{display:inline-block;padding:3px 9px;border-radius:7px;font-size:12px;font-weight:700;
  letter-spacing:.02em;margin-left:11px;vertical-align:middle;
  font-family:'IBM Plex Mono',monospace;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
.chip{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;
  font-size:10.5px;font-weight:800;letter-spacing:.12em;margin-left:9px;vertical-align:middle}
@media (max-width:900px){
  .sc-tbl{font-size:14px}
  .sc-tbl thead th{padding:12px 14px}
  .sc-tbl td{padding:13px 14px}
  .sc-tbl td:first-child{padding-left:16px}
  .ticker{font-size:17.5px}
}
</style>
"""


def kpi_html(df: pd.DataFrame) -> str:
    a_plus = len(df[(df["Grade"] == "A+") & df["Fraîcheur"].str.contains("⚡", na=False)])
    a_grade = len(df[(df["Grade"] == "A") & df["Fraîcheur"].str.contains("⚡", na=False)])
    b_watch = len(
        df[df["Grade"].isin(["B+", "B"]) & df["Fraîcheur"].str.contains("⚡", na=False)]
    )
    longs = len(
        df[df["Signal"].str.contains("LONG", na=False) & ~df["Signal"].str.contains("expiré")]
    )
    shorts = len(
        df[df["Signal"].str.contains("SHORT", na=False) & ~df["Signal"].str.contains("expiré")]
    )
    max_mom = len(df[df.get("Momentum", 0) == 3]) if "Momentum" in df.columns else 0

    kpis = [
        ("A+ PREMIUM", a_plus, "#b7a4ff", ICON_TARGET),
        ("GRADE A", a_grade, "#7db7ff", ICON_TARGET),
        ("WATCHLIST", b_watch, "#c3cfe6", ICON_CLOCK),
        ("LONG ACTIFS", longs, "#5eead4", icon_arrow(True, 12)),
        ("SHORT ACTIFS", shorts, "#f7a6cf", icon_arrow(False, 12)),
        ("FORCE MAX", max_mom, "#f7c66b", ICON_BOLT),
    ]
    cards = "".join(
        f'<div class="kpi{"" if v else " kpi-dim"}" style="--acc:{c}">'
        f'<div class="kpi-l"><span style="color:{c};display:inline-flex">{ic}</span>{lbl}</div>'
        f'<div class="kpi-v">{v}</div></div>'
        for lbl, v, c, ic in kpis
    )
    return f'<div class="kpi-grid">{cards}</div>'


def table_html(df: pd.DataFrame, kz_now: str) -> str:
    out = [TABLE_CSS]
    out.append(
        '<div class="sc-wrap"><table class="sc-tbl">\n<thead><tr>\n'
        '  <th style="width:132px">Fraîcheur</th>\n'
        "  <th>Actif</th>\n  <th>Signal</th>\n  <th>Biais daily</th>\n"
        "  <th>Zone</th>\n  <th style=\"width:140px\">Score /103</th>\n"
        "  <th>ADR / ATR</th>\n  <th>Force</th>\n"
        "</tr></thead><tbody>\n"
    )
    for _, row in df.iterrows():
        grade = str(row.get("Grade", "C"))
        fresh = "⚡" in str(row.get("Fraîcheur", ""))
        gs = GRADE_STYLE.get(grade, GRADE_STYLE["C"])
        score = int(row.get("Score /100", 0))
        ticker_raw = str(row.get("Actif + Note", "")).split("  ")[0].strip()
        ticker = html.escape(DISPLAY_NAMES.get(ticker_raw, ticker_raw))
        sig_value = str(row.get("Signal", "—"))
        adr_v = row.get("ADR")
        adr_lbl = str(row.get("ADR Label", "ADR"))
        adr_cons = row.get("ADR Consumed")
        bias = str(row.get("Biais Daily", "—"))
        alignment = str(row.get("Alignement", "ALIGNED"))
        zone = str(row.get("Zone", "—"))
        fresh_str = str(row.get("Fraîcheur", "—"))
        sdelta = row.get("Strength Δ")
        momentum = int(row.get("Momentum", 0))
        is_bull = bool(row.get("signal_is_bull", True))
        mn_bonus = bool(row.get("Midnight Bonus", False))

        align_tag = (
            f'<span class="chip" style="background:rgba(247,166,207,.14);'
            f'border:1px solid rgba(247,166,207,.6);color:#f7a6cf">'
            f"{ICON_ALERT}COUNTER</span>" if alignment == "COUNTER" else ""
        )

        if kz_now and fresh:
            kc = killzone_color(kz_now)
            kz_tag = (
                f'<span class="chip" style="background:{kc}22;border:1px solid {kc}80;'
                f'color:{kc}">{killzone_badge(kz_now)}</span>'
            )
        else:
            kz_tag = ""

        row_bg = gs["bg"] if fresh and grade in ("A+", "A") else "transparent"
        rail = ("rail-bull" if is_bull else "rail-bear") + ("" if fresh else " stale")
        row_style = f"background:{row_bg}"
        if fresh and grade == "A+":
            row_style += ";box-shadow:inset 0 0 36px -16px rgba(183,164,255,.20)"

        out.append(
            f'<tr class="{rail}" style="{row_style}">\n'
            f"  <td>{fresh_cell(fresh_str, fresh)}</td>\n"
            f'  <td style="white-space:nowrap">\n'
            f'    <span class="ticker">{ticker}</span>\n'
            f"    <span class=\"grade-pill\" style=\"color:{gs['color']};background:{gs['line']}30;"
            f"          border:1px solid {gs['line']}aa\">{gs['label']}</span>\n"
            f"    {align_tag}\n"
            f"  </td>\n"
            f'  <td style="white-space:nowrap">{sig_cell(sig_value, is_bull)}{kz_tag}</td>\n'
            f"  <td>{bias_cell(bias)}</td>\n"
            f"  <td>{zone_cell(zone, mn_bonus)}</td>\n"
            f"  <td>{score_bar(score)}</td>\n"
            f"  <td>{adr_cell(adr_v, adr_lbl, consumed=adr_cons)}</td>\n"
            f"  <td>{force_cell(momentum, sdelta, is_bull)}</td>\n"
            "</tr>"
        )
    out.append("</tbody></table></div>")
    return "\n".join(out)


def sort_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic ordering: fresh, grade, score, momentum, MTF, ticker."""
    if df.empty:
        return df
    work = df.copy()
    work["_fresh"] = work["Fraîcheur"].astype(str).str.contains("⚡").astype(int)
    work["_grade"] = work["Grade"].map(GRADE_ORDER).fillna(0).astype(int)
    work["_score"] = work["Score /100"].fillna(0).astype(float)
    work["_mom"] = work.get("Momentum", pd.Series(0, index=work.index)).fillna(0).astype(int)
    work["_mtf"] = work["MTF Pct"].fillna(0).astype(int)
    work["_ticker"] = work["Actif + Note"].astype(str)
    work = work.sort_values(
        ["_fresh", "_grade", "_score", "_mom", "_mtf", "_ticker"],
        ascending=[False, False, False, False, False, True],
        kind="mergesort",
    )
    return work.drop(
        columns=["_fresh", "_grade", "_score", "_mom", "_mtf", "_ticker"]
    ).reset_index(drop=True)


def footer_html(df: pd.DataFrame, elapsed: float, now: datetime, kz_now: str) -> str:
    kz_foot = (
        f'<span style="color:{killzone_color(kz_now)}">'
        f"killzone {killzone_badge(kz_now)} active</span>" if kz_now
        else '<span style="color:#8496b8">hors killzone</span>'
    )
    return _html(
        f"""
    <div style="display:flex;align-items:center;justify-content:flex-end;gap:14px;
                margin-top:14px;font-size:10.5px;letter-spacing:.1em;font-weight:600;
                text-transform:uppercase;color:var(--muted)">
      <span>{len(df)} signal(s)</span>
      <span style="color:#36527f">•</span>
      <span style="font-family:'IBM Plex Mono',monospace;text-transform:none;letter-spacing:.02em">
        {elapsed}s</span>
      <span style="color:#36527f">•</span>
      <span style="font-family:'IBM Plex Mono',monospace;text-transform:none;letter-spacing:.02em">
        {now.strftime('%H:%M:%S')} UTC</span>
      <span style="color:#36527f">•</span>
      {kz_foot}
    </div>
    """
    )
