"""Pure HTML rendering helpers (no Streamlit imports)."""

from __future__ import annotations

import html
from datetime import datetime

import numpy as np
import pandas as pd

from ..config import DISPLAY_NAMES, GRADE_ORDER

KZ_STYLE = {
    "London": ("LONDON", "#4f8dff"),
    "NY AM": ("NEW YORK AM", "#8ab8ff"),
    "Asia": ("ASIA", "#38bdf8"),
}


def killzone_badge(kz: str) -> str:
    return KZ_STYLE.get(kz, ("", ""))[0]


def killzone_color(kz: str) -> str:
    return KZ_STYLE.get(kz, ("", "#91a4bf"))[1]


def icon_arrow(up: bool, size: int = 12) -> str:
    d = "M7 12V2.4M3.3 6.1 7 2.4l3.7 3.7" if up else "M7 2v9.6M3.3 7.9 7 11.6l3.7-3.7"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 14 14" fill="none" '
        f'style="vertical-align:-2px"><path d="{d}" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


ICON_BOLT = (
    '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-2px">'
    '<path d="M7.8 1.6 3.4 7.9h2.8L6.1 12.4l4.7-6.6H7.9l-.1-4.2z" '
    'stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>'
)
ICON_CLOCK = (
    '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-2px">'
    '<circle cx="7" cy="7" r="5.2" stroke="currentColor" stroke-width="1.25"/>'
    '<path d="M7 4.2V7.2l2 1.2" stroke="currentColor" stroke-width="1.25" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
ICON_MOON = (
    '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-2px">'
    '<path d="M11.1 8.6A4.7 4.7 0 0 1 5.4 2.9 4.7 4.7 0 1 0 11.1 8.6z" '
    'stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>'
)
ICON_ALERT = (
    '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-2px">'
    '<path d="M7 2.1 12.4 11.4H1.6L7 2.1z" stroke="currentColor" stroke-width="1.15" '
    'stroke-linejoin="round"/>'
    '<path d="M7 5.6v2.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'
    '<circle cx="7" cy="10" r=".7" fill="currentColor"/></svg>'
)
ICON_TARGET = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none">'
    '<circle cx="8" cy="8" r="5.4" stroke="currentColor" stroke-width="1.2"/>'
    '<path d="M8 1.2v2.2M8 12.6v2.2M1.2 8h2.2M12.6 8h2.2" '
    'stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>'
    '<circle cx="8" cy="8" r="1.1" fill="currentColor"/></svg>'
)


def _html(s: str) -> str:
    return "\n".join(line.lstrip() for line in s.strip("\n").split("\n"))


GRADE_STYLE = {
    "A+": {"color": "#f5c451", "line": "#b78b2e", "bg": "rgba(245,196,81,.065)", "label": "A+"},
    "A":  {"color": "#8ab8ff", "line": "#4f8dff", "bg": "rgba(79,141,255,.055)", "label": "A"},
    "B+": {"color": "#67e8f9", "line": "#38bdf8", "bg": "rgba(56,189,248,.045)", "label": "B+"},
    "B":  {"color": "#c3d0e4", "line": "#6f84a3", "bg": "transparent", "label": "B"},
    "C":  {"color": "#93a6c2", "line": "#4b5f7c", "bg": "transparent", "label": "C"},
}

BIAS_MAP = {
    "STRONG BULLISH": ("Strong bull", "#34d399", 2, True),
    "BULLISH":        ("Bull",        "#6ee7b7", 1, True),
    "STRONG BEARISH": ("Strong bear", "#fb7185", 2, False),
    "BEARISH":        ("Bear",        "#fda4af", 1, False),
}

ZONE_MAP = {
    "DISCOUNT":  ("#8ab8ff", "rgba(79,141,255,.12)",  "rgba(79,141,255,.48)"),
    "PREMIUM":   ("#fda4af", "rgba(251,113,133,.12)", "rgba(251,113,133,.45)"),
    "EXT HIGH":  ("#fb7185", "rgba(251,113,133,.15)", "rgba(251,113,133,.6)"),
    "EXT LOW":   ("#34d399", "rgba(52,211,153,.13)",  "rgba(52,211,153,.55)"),
    "EQUILIBRE": ("#c3d0e4", "rgba(145,164,191,.12)", "rgba(145,164,191,.4)"),
}


def fresh_cell(fresh_str: str, is_fresh: bool) -> str:
    txt = html.escape(fresh_str.replace("⚡", "").replace("⏳", "").strip())
    col = "#34d399" if is_fresh else "#91a4bf"
    ico = ICON_BOLT if is_fresh else ICON_CLOCK
    dot = (
        f'<span class="bs-dot" style="width:4px;height:4px;border-radius:50%;'
        f'background:{col}"></span>' if is_fresh else ""
    )
    bg = "rgba(52,211,153,.09)" if is_fresh else "rgba(145,164,191,.08)"
    bd = "rgba(52,211,153,.38)" if is_fresh else "rgba(145,164,191,.26)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;color:{col};'
        f'background:{bg};border:1px solid {bd};padding:4px 9px;border-radius:4px;'
        f"font-family:'IBM Plex Mono',monospace;font-size:11.5px;font-weight:500;"
        f'white-space:nowrap">{dot}<span style="display:inline-flex">{ico}</span>{txt}</span>'
    )


def sig_cell(sig: str, is_bull: bool) -> str:
    expired = "expiré" in sig
    col = ("#34d399" if is_bull else "#fb7185") if not expired else "#91a4bf"
    word = "LONG" if is_bull else "SHORT"
    if expired:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:6px;color:{col};'
            f'font-size:11.5px;letter-spacing:.1em;font-weight:600">'
            f'<span style="display:inline-flex;opacity:.75">{icon_arrow(is_bull, 11)}</span>'
            f'{word} · EXPIRÉ</span>'
        )
    return (
        f'<span style="display:inline-flex;align-items:center;gap:7px;color:{col};'
        f'background:{col}12;border:1px solid {col}66;'
        f'padding:5px 10px 5px 9px;border-radius:5px;font-size:13.5px;font-weight:600;'
        f'letter-spacing:.08em">'
        f'<span style="display:inline-flex">{icon_arrow(is_bull, 12)}</span>{word}</span>'
    )


def bias_cell(b: str) -> str:
    if b not in BIAS_MAP:
        return (
            '<span style="color:#91a4bf;font-size:13px;letter-spacing:.02em">'
            "— Neutral</span>"
        )
    label, col, strength, up = BIAS_MAP[b]
    arrows = "".join(
        f'<span style="display:inline-flex">{icon_arrow(up, 9)}</span>'
        for _ in range(strength)
    )
    return (
        f'<span style="display:inline-flex;align-items:center;gap:1px;color:{col};'
        f'font-size:13.5px;font-weight:600;letter-spacing:.01em">'
        f'{arrows}<span style="margin-left:5px">{html.escape(label)}</span></span>'
    )


def zone_cell(z: str, mn_bonus: bool) -> str:
    col, bg, bd = ZONE_MAP.get(z, ZONE_MAP["EQUILIBRE"])
    moon = (
        f'<span style="color:#f5c451;display:inline-flex;margin-left:6px" '
        f'title="Confluence midnight open">{ICON_MOON}</span>' if mn_bonus else ""
    )
    return (
        f'<span style="display:inline-flex;align-items:center">'
        f'<span style="color:{col};background:{bg};border:1px solid {bd};'
        f'padding:4px 8px;border-radius:4px;font-size:10.5px;font-weight:600;'
        f'letter-spacing:.1em;white-space:nowrap">{html.escape(z)}</span>{moon}</span>'
    )


def score_bar(score: int) -> str:
    if score >= 85:
        grad, col = (
            "linear-gradient(90deg,#b78b2e,#f5c451)",
            "#f5c451",
        )
    elif score >= 70:
        grad, col = (
            "linear-gradient(90deg,#2457d6,#4f8dff)",
            "#8ab8ff",
        )
    elif score >= 55:
        grad, col = (
            "linear-gradient(90deg,#0e7490,#38bdf8)",
            "#67e8f9",
        )
    elif score >= 40:
        grad, col = (
            "linear-gradient(90deg,#3a4d68,#6f84a3)",
            "#c3d0e4",
        )
    else:
        grad, col = (
            "linear-gradient(90deg,#26364e,#4b5f7c)",
            "#93a6c2",
        )
    width = max(3, min(score, 103) / 103 * 100) if score >= 0 else 3
    return (
        f'<div style="display:flex;align-items:center;gap:10px">'
        f'<span style="color:{col};font-weight:500;font-size:21px;'
        f"font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;"
        f'letter-spacing:-.04em;min-width:38px;text-align:right">{score}</span>'
        f'<div style="width:74px;height:5px;background:#16253b;'
        f'border-radius:2px;overflow:hidden">'
        f'<div style="width:{width}%;height:100%;background:{grad};border-radius:2px"></div>'
        f'</div></div>'
    )


def adr_cell(v: float | None, label: str = "ADR", consumed: float | None = None) -> str:
    if v is None:
        return '<span style="color:#91a4bf">—</span>'
    formatted = f"{v:.5f}" if v < 1.0 else f"{v:.2f}"
    tag_color = "#8ab8ff" if label == "ADR" else "#67e8f9"
    head = (
        f'<div style="display:flex;align-items:baseline;gap:7px">'
        f'<span style="color:{tag_color};font-size:9.5px;font-weight:600;letter-spacing:.11em;'
        f'background:{tag_color}12;border:1px solid {tag_color}3d;padding:1px 5px;'
        f'border-radius:3px">{html.escape(label)}</span>'
        f'<span style="color:var(--ink);font-weight:500;'
        f"font-family:'IBM Plex Mono',monospace;"
        f'font-size:14.5px;font-variant-numeric:tabular-nums;letter-spacing:-.02em">'
        f'{formatted}</span></div>'
    )
    if consumed is None or (isinstance(consumed, float) and np.isnan(consumed)):
        return head
    consumed = float(consumed)
    if consumed < 40:
        c = "#34d399"
    elif consumed < 70:
        c = "#f5c451"
    else:
        c = "#fb7185"
    fill = int(min(max(consumed, 0), 100))
    gauge = (
        f'<div style="display:flex;align-items:center;gap:7px;margin-top:6px">'
        f'<div style="width:58px;height:4px;background:#16253b;'
        f'border-radius:2px;overflow:hidden">'
        f'<div style="width:{fill}%;height:100%;background:{c};border-radius:2px">'
        f'</div></div>'
        f"<span style=\"color:{c};font-size:10.5px;font-family:'IBM Plex Mono',monospace;"
        f'font-weight:500;font-variant-numeric:tabular-nums">{consumed:.0f}%</span></div>'
    )
    return f"<div>{head}{gauge}</div>"


def force_cell(momentum_score: int, delta: float | None, is_bull: bool) -> str:
    col = "#34d399" if is_bull else "#fb7185"
    seg = "".join(
        (
            f'<div style="width:14px;height:8px;border-radius:2px;background:{col}"></div>'
        ) if i < momentum_score else
        '<div style="width:14px;height:8px;border-radius:2px;background:#16253b"></div>'
        for i in range(3)
    )
    bars = (
        f'<div style="display:flex;gap:4px;align-items:center" '
        f'title="ADX H4/H1/M15 alignés avec le signal : {momentum_score}/3">{seg}</div>'
    )
    if delta is not None:
        if abs(delta) < 1.5:
            dc, rel = "#91a4bf", "neutre"
        elif (delta > 0) == is_bull:
            dc, rel = "#34d399", "favorable"
        else:
            dc, rel = "#fb7185", "contraire"
        sign = "+" if delta > 0 else ""
        side = "LONG" if is_bull else "SHORT"
        dh = (
            f'<span style="color:{dc};background:{dc}10;border:1px solid {dc}4d;'
            f'padding:2px 6px;border-radius:4px;font-weight:500;font-size:12px;'
            f"font-family:'IBM Plex Mono',monospace;margin-left:9px;"
            f'font-variant-numeric:tabular-nums" '
            f'title="Δ force devise {delta:+.2f} — {rel} au {side}">'
            f"{sign}{delta:.1f}</span>"
        )
    else:
        dh = (
            '<span style="color:#91a4bf;margin-left:9px;font-size:11.5px;'
            "font-family:'IBM Plex Mono',monospace\" "
            'title="Δ force devise non disponible pour cet instrument">n/a</span>'
        )
    return f'<div style="display:flex;align-items:center">{bars}{dh}</div>'


TABLE_CSS = """
<style>
.sc-wrap{overflow-x:auto;border:1px solid #1d2e47;border-radius:12px;
  background:#0a1322;
  box-shadow:0 30px 70px -52px #000,inset 0 1px 0 rgba(255,255,255,.035)}
.sc-tbl{width:100%;border-collapse:separate;border-spacing:0;
  font-family:'IBM Plex Sans',sans-serif;font-size:14px;font-weight:400;color:var(--ink)}
.sc-tbl thead th{
  padding:12px 18px;text-align:left;white-space:nowrap;
  color:#91a4bf;font-size:9.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;
  background:#0d192b;border-bottom:1px solid #243854;
  position:sticky;top:0;z-index:2}
.sc-tbl td{padding:13px 18px;border-bottom:1px solid rgba(36,56,84,.6);vertical-align:middle}
.sc-tbl tbody tr:nth-child(even) td{background:rgba(79,141,255,.022)}
.sc-tbl tbody tr{transition:background .13s ease}
.sc-tbl tbody tr:hover td{background:rgba(79,141,255,.06)}
.sc-tbl tbody tr:last-child td{border-bottom:none}
.sc-tbl td:first-child{position:relative;padding-left:18px}
.sc-tbl td:first-child::before{content:"";position:absolute;left:0;top:8px;bottom:8px;width:2px;
  border-radius:0 2px 2px 0}
.rail-bull td:first-child::before{background:#34d399}
.rail-bear td:first-child::before{background:#fb7185}
.ticker{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:500;color:var(--ink);
  white-space:nowrap;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.stale .ticker{color:#c3d0e4}
.grade-pill{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10.5px;font-weight:600;
  letter-spacing:.02em;margin-left:9px;vertical-align:middle;
  font-family:'IBM Plex Mono',monospace}
.chip{display:inline-flex;align-items:center;gap:4px;padding:2px 7px;border-radius:3px;
  font-size:9.5px;font-weight:600;letter-spacing:.1em;margin-left:8px;vertical-align:middle}
@media (max-width:900px){
  .sc-tbl{font-size:13.5px}
  .sc-tbl thead th{padding:11px 13px}
  .sc-tbl td{padding:12px 13px}
  .sc-tbl td:first-child{padding-left:14px}
  .ticker{font-size:16.5px}
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
        ("A+ PREMIUM", a_plus, "#f5c451", ICON_TARGET),
        ("GRADE A", a_grade, "#4f8dff", ICON_TARGET),
        ("WATCHLIST", b_watch, "#91a4bf", ICON_CLOCK),
        ("LONG ACTIFS", longs, "#34d399", icon_arrow(True, 12)),
        ("SHORT ACTIFS", shorts, "#fb7185", icon_arrow(False, 12)),
        ("ADX 3/3", max_mom, "#38bdf8", ICON_BOLT),
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
        "  <th>ADR / ATR</th>\n  <th>Momentum / Δ</th>\n"
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
            f'<span class="chip" style="background:rgba(251,113,133,.12);'
            f'border:1px solid rgba(251,113,133,.5);color:#fb7185">'
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
            row_style += ";box-shadow:inset 0 0 36px -18px rgba(245,196,81,.18)"

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
        else '<span style="color:#6f84a3">hors killzone</span>'
    )
    return _html(
        f"""
    <div style="display:flex;align-items:center;justify-content:flex-end;gap:13px;
                margin-top:12px;font-size:10px;letter-spacing:.09em;font-weight:500;
                text-transform:uppercase;color:var(--muted)">
      <span>{len(df)} signal(s)</span>
      <span style="color:#2c4667">•</span>
      <span style="font-family:'IBM Plex Mono',monospace;text-transform:none;letter-spacing:.01em">
        {elapsed}s</span>
      <span style="color:#2c4667">•</span>
      <span style="font-family:'IBM Plex Mono',monospace;text-transform:none;letter-spacing:.01em">
        {now.strftime('%H:%M:%S')} UTC</span>
      <span style="color:#2c4667">•</span>
      {kz_foot}
    </div>
    """
    )
