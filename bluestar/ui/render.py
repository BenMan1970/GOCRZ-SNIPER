"""Rendu HTML pur (aucun import Streamlit) et préparation du tableau."""

from __future__ import annotations

import html
from datetime import datetime

import pandas as pd

from ..config import (
    ADX_TREND_MIN,
    DISPLAY_NAMES,
    FORCE_NEUTRAL_BAND,
    GRADE_ORDER,
    MIN_GRADE_MAP,
)

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
ICON_TREND = (
    '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-2px">'
    '<path d="M1.5 10.5 5 7l2.4 2.4L12.4 3.6M9 3.6h3.4V7" stroke="currentColor" '
    'stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>'
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


def _attr(text: str) -> str:
    return html.escape(str(text), quote=True)


def fresh_cell(signal_type: str, mins: float | None, is_fresh: bool) -> str:
    if signal_type == "CONTINUATION":
        col, bg, bd, ico, txt = "#67e8f9", "rgba(56,189,248,.09)", "rgba(56,189,248,.38)", ICON_TREND, "TENDANCE"
        dot = ""
    else:
        txt = f"{int(mins)} min" if mins is not None and not pd.isna(mins) else "—"
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
        f'white-space:nowrap">{dot}<span style="display:inline-flex">{ico}</span>{html.escape(txt)}</span>'
    )


def sig_cell(is_bull: bool, expired: bool) -> str:
    col = (("#34d399" if is_bull else "#fb7185") if not expired else "#91a4bf")
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


def bias_cell(b: str, tip: str = "") -> str:
    title = f' title="{_attr(tip)}"' if tip else ""
    if b not in BIAS_MAP:
        return (
            f'<span{title} style="color:#91a4bf;font-size:13px;letter-spacing:.02em">'
            "— Neutral</span>"
        )
    label, col, strength, up = BIAS_MAP[b]
    arrows = "".join(
        f'<span style="display:inline-flex">{icon_arrow(up, 9)}</span>'
        for _ in range(strength)
    )
    return (
        f'<span{title} style="display:inline-flex;align-items:center;gap:1px;color:{col};'
        f'font-size:13.5px;font-weight:600;letter-spacing:.01em">'
        f'{arrows}<span style="margin-left:5px">{html.escape(label)}</span></span>'
    )


def zone_cell(z: str, ref: str = "") -> str:
    col, bg, bd = ZONE_MAP.get(z, ZONE_MAP["EQUILIBRE"])
    tip = {"MO": "Référence : midnight open (00h00 NY)",
           "D1": "Référence : milieu du range D-1 (midnight open indisponible)"}.get(ref, "")
    return (
        f'<span title="{_attr(tip)}" style="color:{col};background:{bg};border:1px solid {bd};'
        f'padding:4px 8px;border-radius:4px;font-size:10.5px;font-weight:600;'
        f'letter-spacing:.1em;white-space:nowrap">{html.escape(z)}</span>'
    )


def score_bar(score: int, tip: str = "") -> str:
    if score >= 85:
        grad, col = "linear-gradient(90deg,#b78b2e,#f5c451)", "#f5c451"
    elif score >= 70:
        grad, col = "linear-gradient(90deg,#2457d6,#4f8dff)", "#8ab8ff"
    elif score >= 55:
        grad, col = "linear-gradient(90deg,#0e7490,#38bdf8)", "#67e8f9"
    elif score >= 40:
        grad, col = "linear-gradient(90deg,#3a4d68,#6f84a3)", "#c3d0e4"
    else:
        grad, col = "linear-gradient(90deg,#26364e,#4b5f7c)", "#93a6c2"
    width = max(3, min(score, 100))
    return (
        f'<div title="{_attr(tip)}" style="display:flex;align-items:center;gap:10px">'
        f'<span style="color:{col};font-weight:500;font-size:21px;'
        f"font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;"
        f'letter-spacing:-.04em;min-width:38px;text-align:right">{score}</span>'
        f'<div style="width:74px;height:5px;background:#16253b;'
        f'border-radius:2px;overflow:hidden">'
        f'<div style="width:{width}%;height:100%;background:{grad};border-radius:2px"></div>'
        f'</div></div>'
    )


def adr_cell(v: float | None, consumed: float | None = None) -> str:
    if v is None or pd.isna(v):
        return '<span style="color:#91a4bf">—</span>'
    formatted = f"{v:.5f}" if v < 0.1 else (f"{v:.3f}" if v < 10 else f"{v:.2f}")
    head = (
        f'<div style="display:flex;align-items:baseline;gap:7px">'
        f'<span style="color:#8ab8ff;font-size:9.5px;font-weight:600;letter-spacing:.11em;'
        f'background:#8ab8ff12;border:1px solid #8ab8ff3d;padding:1px 5px;'
        f'border-radius:3px">ADR</span>'
        f'<span style="color:var(--ink);font-weight:500;'
        f"font-family:'IBM Plex Mono',monospace;"
        f'font-size:14.5px;font-variant-numeric:tabular-nums;letter-spacing:-.02em">'
        f'{formatted}</span></div>'
    )
    if consumed is None or pd.isna(consumed):
        return head
    consumed = float(consumed)
    c = "#34d399" if consumed < 40 else ("#f5c451" if consumed < 70 else "#fb7185")
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


def force_cell(
    adx_values: dict[str, float | None], delta: float | None, is_bull: bool
) -> str:
    """Segments ADX (H4/H1/M15, allumés si ADX > seuil : force sans direction) + Δ devise."""
    seg, tips = [], []
    for name in ("H4", "H1", "M15"):
        v = adx_values.get(name) if adx_values else None
        on = v is not None and v > ADX_TREND_MIN
        seg.append(
            f'<div style="width:14px;height:8px;border-radius:2px;'
            f'background:{"#38bdf8" if on else "#16253b"}"></div>'
        )
        tips.append(f"{name} {v:.1f}" if v is not None else f"{name} n/a")
    bars = (
        f'<div style="display:flex;gap:4px;align-items:center" '
        f'title="ADX (force de tendance, sans direction) — {" · ".join(tips)}">{"".join(seg)}</div>'
    )
    if delta is None or pd.isna(delta):
        dh = (
            '<span style="color:#91a4bf;margin-left:9px;font-size:11.5px;'
            "font-family:'IBM Plex Mono',monospace\" "
            'title="Δ force devise non disponible pour cet instrument">n/a</span>'
        )
    else:
        if abs(delta) < FORCE_NEUTRAL_BAND:
            dc, rel = "#91a4bf", "neutre"
        elif (delta > 0) == is_bull:
            dc, rel = "#34d399", "favorable"
        else:
            dc, rel = "#fb7185", "contraire"
        side = "LONG" if is_bull else "SHORT"
        dh = (
            f'<span style="color:{dc};background:{dc}10;border:1px solid {dc}4d;'
            f'padding:2px 6px;border-radius:4px;font-weight:500;font-size:12px;'
            f"font-family:'IBM Plex Mono',monospace;margin-left:9px;"
            f'font-variant-numeric:tabular-nums" '
            f'title="Δ force devise {delta:+.2f} — {rel} au {side}">'
            f'{"+" if delta > 0 else ""}{delta:.1f}</span>'
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



# --------------------------------------------------------------------------- #
# Préparation du tableau (logique d'affichage pure, testable sans Streamlit)
# --------------------------------------------------------------------------- #
def build_frame(results: list[dict[str, object]], freshness: int) -> pd.DataFrame:
    """DataFrame d'affichage. `fresh` dépend du sélecteur : aucun rescan requis."""
    df = pd.DataFrame(results)
    if df.empty:
        return df
    flip = df["signal_type"] == "FLIP"
    df["fresh"] = flip & (df["mins_ago"].astype(float).fillna(1e9) <= freshness)
    df["expired"] = flip & ~df["fresh"]
    return df


def apply_filters(
    df: pd.DataFrame,
    min_grade: str,
    include_continuation: bool,
    hide_counter: bool,
    hide_expired: bool,
) -> pd.DataFrame:
    if df.empty:
        return df
    keep = df["grade"].map(GRADE_ORDER).fillna(0) >= MIN_GRADE_MAP[min_grade]
    if not include_continuation:
        keep &= df["signal_type"] != "CONTINUATION"
    if hide_counter:
        keep &= df["alignment"] != "COUNTER"
    if hide_expired:
        keep &= ~df["expired"]
    return df[keep]


def sort_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Ordre déterministe : frais, grade, score, ADX, MTF, ticker."""
    if df.empty:
        return df
    work = df.copy()
    work["_fresh"] = work["fresh"].astype(int)
    work["_grade"] = work["grade"].map(GRADE_ORDER).fillna(0).astype(int)
    work = work.sort_values(
        ["_fresh", "_grade", "score", "adx_strong", "mtf_pct", "ticker"],
        ascending=[False, False, False, False, False, True],
        kind="mergesort",
    )
    return work.drop(columns=["_fresh", "_grade"]).reset_index(drop=True)


def kpi_html(df: pd.DataFrame) -> str:
    active = df[~df["expired"]]
    kpis = [
        ("A+ PREMIUM", int((active["grade"] == "A+").sum()), "#f5c451", ICON_TARGET),
        ("GRADE A", int((active["grade"] == "A").sum()), "#4f8dff", ICON_TARGET),
        ("WATCHLIST", int(active["grade"].isin(["B+", "B"]).sum()), "#91a4bf", ICON_CLOCK),
        ("LONG ACTIFS", int(active["is_bull"].sum()), "#34d399", icon_arrow(True, 12)),
        ("SHORT ACTIFS", int((~active["is_bull"]).sum()), "#fb7185", icon_arrow(False, 12)),
        ("ADX 3/3", int((df["adx_strong"] == 3).sum()), "#38bdf8", ICON_BOLT),
    ]
    cards = "".join(
        f'<div class="kpi{"" if v else " kpi-dim"}" style="--acc:{c}">'
        f'<div class="kpi-l"><span style="color:{c};display:inline-flex">{ic}</span>{lbl}</div>'
        f'<div class="kpi-v">{v}</div></div>'
        for lbl, v, c, ic in kpis
    )
    return f'<div class="kpi-grid">{cards}</div>'


def _chip(text: str, col: str, icon: str = "") -> str:
    return (
        f'<span class="chip" style="background:{col}1f;border:1px solid {col}80;'
        f'color:{col}">{icon}{html.escape(text)}</span>'
    )


def table_html(df: pd.DataFrame) -> str:
    out = [TABLE_CSS]
    out.append(
        '<div class="sc-wrap"><table class="sc-tbl">\n<thead><tr>\n'
        '  <th style="width:132px">Fraîcheur</th>\n'
        "  <th>Actif</th>\n  <th>Signal</th>\n  <th>Biais daily</th>\n"
        '  <th>Zone</th>\n  <th style="width:140px">Score /100</th>\n'
        "  <th>ADR</th>\n  <th>ADX / Δ force</th>\n"
        "</tr></thead><tbody>\n"
    )
    for _, row in df.iterrows():
        grade = str(row["grade"])
        fresh, expired = bool(row["fresh"]), bool(row["expired"])
        is_bull = bool(row["is_bull"])
        gs = GRADE_STYLE.get(grade, GRADE_STYLE["C"])
        ticker = html.escape(DISPLAY_NAMES.get(row["ticker"], row["ticker"]))

        chips = ""
        if row["alignment"] == "COUNTER":
            chips += _chip("COUNTER", "#fb7185", ICON_ALERT)
        elif row["alignment"] == "NEUTRAL":
            chips += _chip("BIAIS NEUTRE", "#91a4bf")
        if row.get("hma_pullback"):
            gap_atr = row.get("hma_gap_atr")
            tip = f"Prix à {gap_atr} ATR du mauvais côté de la HMA (toléré)"
            chips += f'<span title="{_attr(tip)}">{_chip("PULLBACK HMA", "#38bdf8")}</span>'
        if row["data_issues"]:
            chips += (
                f'<span title="{_attr("Données dégradées : " + ", ".join(row["data_issues"]))}">'
                f'{_chip("DONNÉES", "#f5c451", ICON_ALERT)}</span>'
            )
        if row["killzone"]:
            kc = killzone_color(row["killzone"])
            chips += _chip(killzone_badge(row["killzone"]), kc)

        highlight = (fresh or not expired) and grade in ("A+", "A")
        row_style = f"background:{gs['bg'] if highlight else 'transparent'}"
        if highlight and grade == "A+":
            row_style += ";box-shadow:inset 0 0 36px -18px rgba(245,196,81,.18)"
        rail = ("rail-bull" if is_bull else "rail-bear") + (" stale" if expired else "")

        out.append(
            f'<tr class="{rail}" style="{row_style}">\n'
            f'  <td>{fresh_cell(row["signal_type"], row["mins_ago"], fresh)}</td>\n'
            f'  <td style="white-space:nowrap">\n'
            f'    <span class="ticker">{ticker}</span>\n'
            f"    <span class=\"grade-pill\" style=\"color:{gs['color']};background:{gs['line']}30;"
            f"border:1px solid {gs['line']}aa\">{gs['label']}</span>\n"
            f"    {chips}\n  </td>\n"
            f'  <td style="white-space:nowrap">{sig_cell(is_bull, expired)}</td>\n'
            f'  <td>{bias_cell(row["bias"], row["bias_detail"])}</td>\n'
            f'  <td>{zone_cell(row["zone"], row["zone_ref"])}</td>\n'
            f'  <td>{score_bar(int(row["score"]), row["score_detail"] + " | MTF " + row["mtf_detail"])}</td>\n'
            f'  <td>{adr_cell(row["adr"], row["adr_consumed"])}</td>\n'
            f'  <td>{force_cell(row["adx_values"], row["strength_delta"], is_bull)}</td>\n'
            "</tr>"
        )
    out.append("</tbody></table></div>")
    return "\n".join(out)


def footer_html(n: int, elapsed: float, scanned_at: datetime, kz_now: str) -> str:
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
      <span>{n} signal(s)</span>
      <span style="color:#2c4667">•</span>
      <span style="font-family:'IBM Plex Mono',monospace;text-transform:none;letter-spacing:.01em">
        {elapsed}s</span>
      <span style="color:#2c4667">•</span>
      <span style="font-family:'IBM Plex Mono',monospace;text-transform:none;letter-spacing:.01em">
        scan {scanned_at.strftime('%H:%M:%S')} UTC</span>
      <span style="color:#2c4667">•</span>
      {kz_foot}
    </div>
    """
    )
