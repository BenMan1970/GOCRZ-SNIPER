"""Design tokens + inline UI assets (V18 navy-premium theme).

All text/background pairs below are PROVEN WCAG contrast ratios (computed,
not assumed - see audit/probes/contrast_report.py):
  ink    #F2F6FF  15.9 over surface, 17.4 over bg
  ink-2  #C9D6F2  11.8
  muted  #93A1C7   6.7 / 7.3
  teal   #5EEAD4  11.6   blue  #60A5FA  6.8
  violet #A78BFA   6.3   magenta #F472B6 6.5
  gold   #E8C57A  10.4   amber #FBBF24 10.3
Every pair clears AA-normal (>=4.5); most clear AAA (>=7).
No raw layout color is allowed outside this module.
"""

from __future__ import annotations

# ---------------------------------------------------------------- palette
INK = "#F2F6FF"
INK_2 = "#C9D6F2"
MUTED = "#93A1C7"
FAINT = "#66739A"

BG0 = "#060B1A"
BG1 = "#0A1024"
SURFACE = "#111A33"
SURFACE_2 = "#16224A"
LINE = "rgba(126,146,196,.18)"
LINE_SOFT = "rgba(126,146,196,.10)"

TEAL = "#5EEAD4"
BLUE = "#60A5FA"
VIOLET = "#A78BFA"
MAGENTA = "#F472B6"
GOLD = "#E8C57A"
AMBER = "#FBBF24"

GRADE_COLORS = {
    "A+": {"color": "#E3D9FF", "line": VIOLET, "bg": "rgba(167,139,250,.14)"},
    "A": {"color": "#C9E2FF", "line": BLUE, "bg": "rgba(96,165,250,.10)"},
    "B+": {"color": "#BDF4E9", "line": TEAL, "bg": "rgba(94,234,212,.08)"},
    "B": {"color": "#C7D2E8", "line": "#8DA0C9", "bg": "transparent"},
    "C": {"color": "#A7B2CF", "line": "#64739D", "bg": "transparent"},
}
ZONE_COLORS = {
    "DISCOUNT": ("#8FC3FF", "rgba(96,165,250,.20)", "rgba(96,165,250,.72)"),
    "PREMIUM": ("#FFC4E4", "rgba(244,114,182,.20)", "rgba(244,114,182,.72)"),
    "EXT HIGH": ("#FF9FD2", "rgba(244,114,182,.26)", "rgba(244,114,182,.82)"),
    "EXT LOW": ("#8CF2DF", "rgba(94,234,212,.24)", "rgba(94,234,212,.82)"),
    "EQUILIBRE": ("#D8E1F5", "rgba(160,178,220,.18)", "rgba(160,178,220,.55)"),
}
# score-bar track text colors (pastels tuned for navy surfaces, AA-large)
SCORE_TEXT = {
    "A_PLUS": "#E3D9FF",
    "A": "#C9E2FF",
    "B_PLUS": "#BDF4E9",
    "B": "#DDE5F6",
    "C": "#C6D0E8",
}

BIAS_COLORS = {
    "STRONG BULLISH": ("Strong bull", TEAL, 2, True),
    "BULLISH": ("Bull", "#A9F3E6", 1, True),
    "STRONG BEARISH": ("Strong bear", MAGENTA, 2, False),
    "BEARISH": ("Bear", "#F9A8D4", 1, False),
}

FONT = (
    "'Inter','SF Pro Display','Segoe UI',system-ui,-apple-system,"
    "'Helvetica Neue',Arial,sans-serif"
)
FONT_MONO = (
    "'JetBrains Mono','Cascadia Mono','SF Mono',Consolas,'Courier New',monospace"
)

# ---------------------------------------------------------------- icons
ICON_ARROW_UP = (
    '<svg width="{sz}" height="{sz}" viewBox="0 0 14 14" '
    'style="vertical-align:-1px;display:inline-block">'
    '<path d="M7 2.4 11.7 9.6H2.3z" fill="currentColor"/></svg>'
)
ICON_ARROW_DOWN = (
    '<svg width="{sz}" height="{sz}" viewBox="0 0 14 14" '
    'style="vertical-align:-1px;display:inline-block">'
    '<path d="M7 11.6 2.3 4.4h9.4z" fill="currentColor"/></svg>'
)
ICON_BOLT = (
    '<svg width="11" height="11" viewBox="0 0 14 14" '
    'style="vertical-align:-1px;display:inline-block">'
    '<path d="M8.1 1 3.2 8.1h2.9L5.4 13l5.4-7.4H7.4L8.1 1z" '
    'fill="currentColor"/></svg>'
)
ICON_CLOCK = (
    '<svg width="11" height="11" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-1px;display:inline-block">'
    '<circle cx="7" cy="7" r="5.1" stroke="currentColor" stroke-width="1.25"/>'
    '<path d="M7 4.3V7.2l1.9 1.2" stroke="currentColor" stroke-width="1.25" '
    'stroke-linecap="round"/></svg>'
)
ICON_MOON = (
    '<svg width="11" height="11" viewBox="0 0 14 14" '
    'style="vertical-align:-1px;display:inline-block">'
    '<path d="M9.5 9A4.3 4.3 0 0 1 5.2 4.7c0-.8.2-1.6.6-2.2A5 5 0 1 0 '
    '11.7 8.4c-.6.4-1.4.6-2.2.6z" fill="currentColor"/></svg>'
)
ICON_TARGET = (
    '<svg width="11" height="11" viewBox="0 0 14 14" fill="none" '
    'style="vertical-align:-1px;display:inline-block">'
    '<circle cx="7" cy="7" r="5.1" stroke="currentColor" stroke-width="1.25"/>'
    '<circle cx="7" cy="7" r="1.6" fill="currentColor"/></svg>'
)
ICON_STAR = (
    '<svg width="11" height="11" viewBox="0 0 14 14" '
    'style="vertical-align:-1px;display:inline-block">'
    '<path d="M7 1.6l1.7 3.6 3.9.5-2.9 2.7.7 3.9L7 10.4 3.6 12.3l.7-3.9'
    'L1.4 5.7l3.9-.5L7 1.6z" fill="currentColor"/></svg>'
)


def icon_arrow(up: bool, size: int = 12) -> str:
    tmpl = ICON_ARROW_UP if up else ICON_ARROW_DOWN
    return tmpl.format(sz=size)


# ---------------------------------------------------------------- css
FONT_STACK = FONT[1:-1]  # strip quotes pair for CSS font-family list


BASE_CSS = f"""
<style>
  /* ---- typography & antialiasing ---------------------------------- */
  html, body, [class*="css"], .stApp {{
      font-family: {FONT_STACK};
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
      font-feature-settings: "tnum" 1, "cv05" 1;
  }}
  /* ---- navy background system -------------------------------------- */
  .stApp, [data-testid="stAppViewContainer"] {{
      background: radial-gradient(1200px 500px at 85% -8%,
                  rgba(96,165,250,.07), transparent 60%),
                  radial-gradient(900px 420px at -10% 108%,
                  rgba(244,114,182,.05), transparent 55%),
                  linear-gradient(180deg, {BG1} 0%, {BG0} 100%) fixed;
      color: {INK};
  }}
  [data-testid="stHeader"] {{
      background: transparent;
  }}
  [data-testid="stSidebar"] {{
      background: linear-gradient(180deg, {SURFACE} 0%, {BG1} 100%);
      border-right: 1px solid {LINE};
  }}
  [data-testid="stSidebar"] * {{
      color: {INK_2};
  }}
  /* ---- tables -------------------------------------------------------- */
  .bs-table {{width:100%; border-collapse:separate; border-spacing:0 7px;
      font-size:13.5px; line-height:1.35;}}
  .bs-table th {{color:{MUTED}; font-size:10.5px; letter-spacing:.14em;
      font-weight:700; text-transform:uppercase; text-align:left;
      padding:6px 12px; border-bottom:1px solid {LINE};}}
  .bs-table td {{background:{SURFACE}; padding:11px 12px;
      border-top:1px solid {LINE_SOFT}; border-bottom:1px solid {LINE_SOFT};
      color:{INK_2}; font-variant-numeric: tabular-nums;}}
  .bs-table td:first-child {{border-left:1px solid {LINE_SOFT};
      border-radius:12px 0 0 12px;}}
  .bs-table td:last-child {{border-right:1px solid {LINE_SOFT};
      border-radius:0 12px 12px 0;}}
  .bs-table tr:hover td {{background:{SURFACE_2};}}
  /* ---- KPI cards ------------------------------------------------------ */
  .kpi-grid {{display:grid; grid-template-columns:repeat(6,1fr);
      gap:12px; margin:8px 0 18px;}}
  .kpi {{border:1px solid {LINE}; border-radius:14px; padding:12px 14px;
      background: linear-gradient(180deg, {SURFACE}, {BG1});
      box-shadow: 0 1px 0 rgba(255,255,255,.03) inset,
                  0 8px 22px rgba(3,7,18,.35);}}
  .kpi-l {{color:{MUTED}; font-size:10px; letter-spacing:.16em; font-weight:700;
      display:inline-flex; gap:6px; align-items:center; text-transform:uppercase;}}
  .kpi-v {{color:{INK}; font-size:27px; font-weight:800; margin-top:3px;
      font-variant-numeric: tabular-nums; letter-spacing:.01em;}}
  .kpi-dim {{opacity:.42}}
  /* ---- expander / misc ------------------------------------------------ */
  [data-testid="stExpander"] {{border:1px solid {LINE};
      border-radius:12px; background:{SURFACE};}}
  .bs-dot {{display:inline-block}}
  a, .stButton button {{color:{INK_2}}}
  ::selection {{background: rgba(96,165,250,.35)}}
</style>
"""


def brand_header(badge: str, color: str) -> str:
    badge_html = (
        f'<span style="color:{color};border:1px solid {color};'
        f"padding:3px 10px;border-radius:20px;font-size:10.5px;"
        f'font-weight:700;letter-spacing:.12em">{badge or "HORS KZ"}'
        f"</span>"
    )
    return f"""
    <div style="display:flex;justify-content:space-between;
         align-items:center;padding:10px 4px 2px">
      <div>
        <div style="font-size:23px;font-weight:800;letter-spacing:.03em;
             font-family:{FONT_STACK}">
          <span style="color:{INK}">BLUE</span><span style="color:{GOLD}">STAR</span>
          <span style="background:linear-gradient(90deg,{TEAL},{BLUE},{VIOLET});
          -webkit-background-clip:text;background-clip:text;color:transparent;
          font-weight:900"> SNIPER</span>
          <span style="color:{MUTED};font-size:11px;font-weight:700;
          letter-spacing:.08em"> V18</span>
        </div>
        <div style="color:{MUTED};font-size:11px;letter-spacing:.08em;
             margin-top:2px">
          ICT MULTI-TIMEFRAME CONFLUENCE \u00b7 READ-ONLY</div>
      </div>
      <div style="text-align:right">{badge_html}</div>
    </div>
    """
