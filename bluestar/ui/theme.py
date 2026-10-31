"""Visual identity: institutional navy terminal with sharp, restrained accents."""

from __future__ import annotations

import os

WEB_FONTS_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');"
)

THEME_CSS = """
<style>
__FONTS__
:root{
  --bg:#050a12;
  --bg-2:#070e1a;
  --surface:#0a1322;
  --surface-2:#0d192b;
  --surface-3:#12223a;
  --line:#1d2e47;
  --line-2:#2c4667;
  --ink:#f4f7fc;
  --ink-2:#d5e0ef;
  --muted:#91a4bf;
  --muted-2:#6f84a3;
  --blue:#4f8dff;
  --blue-2:#8ab8ff;
  --cyan:#38bdf8;
  --green:#34d399;
  --red:#fb7185;
  --gold:#f5c451;
  --shadow:0 28px 70px -46px #000;
  color-scheme:dark;
  accent-color:var(--blue);
}

html, body, .stApp, button, input, textarea, select,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stCaptionContainer"]{
  font-family:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
  font-feature-settings:'kern' 1,'liga' 1;
}
html, body{background:var(--bg);color:var(--ink)}
.stApp{
  background:
    radial-gradient(920px 500px at 50% -12%, rgba(79,141,255,.10), transparent 66%),
    linear-gradient(180deg,#070e1a 0%,#050a12 62%,#040810 100%);
  background-attachment:fixed;
}
.stApp::before{
  content:"";position:fixed;top:0;left:0;right:0;height:1px;z-index:999;
  pointer-events:none;background:rgba(79,141,255,.34);
}
[data-testid="stAppViewContainer"]{color:var(--ink)}
.block-container{padding-top:2.2rem;padding-bottom:4rem;max-width:1560px}
#MainMenu, footer, header[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4{font-family:'IBM Plex Sans',sans-serif!important;font-weight:600!important;
  letter-spacing:-.025em!important;color:var(--ink)!important}
p, li{line-height:1.6}

.stButton>button{
  background:#2f6bff!important;
  color:#ffffff!important;border:1px solid #5b91ff!important;
  font-family:'IBM Plex Sans',sans-serif!important;font-weight:600!important;
  font-size:12px!important;letter-spacing:.14em!important;text-transform:uppercase!important;
  border-radius:6px!important;padding:13px 0!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.16),
             0 10px 24px -20px rgba(47,107,255,.7)!important;
  transition:background .15s ease,border-color .15s ease!important;
}
.stButton>button:hover{background:#3d78ff!important;border-color:#8ab8ff!important}
.stButton>button:active{background:#2457d6!important}

.stSelectbox label, .stToggle label{
  color:var(--muted)!important;font-size:10.5px!important;font-weight:600!important;
  letter-spacing:.12em!important;text-transform:uppercase!important;
}
.stSelectbox div[data-baseweb="select"]>div{
  background:#0a1322!important;
  border:1px solid var(--line)!important;
  border-radius:6px!important;min-height:42px!important;
  transition:border-color .15s ease, box-shadow .15s ease!important;
}
.stSelectbox div[data-baseweb="select"]>div:hover{border-color:var(--line-2)!important}
.stSelectbox div[data-baseweb="select"]>div:focus-within{
  border-color:rgba(79,141,255,.8)!important;
  box-shadow:0 0 0 3px rgba(79,141,255,.12)!important;
}
.stSelectbox div[data-baseweb="select"] *{color:var(--ink)!important;font-size:14px!important}
div[data-baseweb="popover"] ul{
  background:var(--surface-2)!important;border:1px solid var(--line)!important;
  border-radius:8px!important;box-shadow:var(--shadow)!important;
}
div[data-baseweb="popover"] li{color:var(--ink-2)!important;font-size:14px!important}
div[data-baseweb="popover"] li:hover{background:var(--surface-3)!important;color:var(--ink)!important}

[data-testid="stExpander"]{
  background:#0a1322!important;
  border:1px solid var(--line)!important;border-radius:8px!important;overflow:hidden!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 18px 44px -38px #000!important;
}
[data-testid="stExpander"] summary{
  color:var(--ink-2)!important;font-size:11.5px!important;font-weight:600!important;
  letter-spacing:.1em!important;text-transform:uppercase!important;
}
[data-testid="stExpander"] table{border-collapse:collapse!important;font-size:13px!important}
[data-testid="stExpander"] th{
  color:var(--muted)!important;font-size:10px!important;text-transform:uppercase!important;
  letter-spacing:.1em!important;border-bottom:1px solid var(--line)!important;
  background:rgba(18,34,58,.48)!important;padding:9px 12px!important;text-align:left!important;
}
[data-testid="stExpander"] td{
  color:var(--ink-2)!important;border-bottom:1px solid rgba(44,70,103,.5)!important;
  padding:9px 12px!important;
}
[data-testid="stExpander"] code{
  background:rgba(79,141,255,.1)!important;color:var(--blue-2)!important;
  font-family:'IBM Plex Mono',monospace!important;font-size:11.5px!important;
  border-radius:4px!important;padding:1px 5px!important;
}

[data-testid="stDataFrame"]{
  border:1px solid var(--line);border-radius:9px;overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 20px 46px -40px #000;
}
[data-testid="stCaptionContainer"]{color:var(--muted)!important}

hr{border:none!important;height:1px!important;
   background:#1d2e47!important;margin:20px 0!important}
::selection{background:rgba(79,141,255,.3);color:#fff}
::-webkit-scrollbar{height:8px;width:8px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--surface-3);border-radius:8px;border:2px solid var(--bg)}
::-webkit-scrollbar-thumb:hover{background:var(--line-2)}

.bs-header{display:flex;align-items:center;gap:17px;margin-bottom:20px;flex-wrap:wrap}
.bs-header .bs-brand{display:flex;align-items:center;gap:16px;min-width:0}
.bs-header .bs-badges{display:flex;align-items:center;gap:7px;margin-left:auto;flex-wrap:wrap}
.bs-overline{display:flex;align-items:center;gap:8px;font-size:9.5px;font-weight:600;
  letter-spacing:.22em;text-transform:uppercase;color:var(--blue-2);margin-bottom:5px}
.bs-overline::before{content:"";width:18px;height:1px;background:var(--blue)}
.bs-header .bs-title{margin:0;font-size:30px;line-height:1.1;color:var(--ink);
  font-weight:700;letter-spacing:-.03em}
.bs-header .bs-title .bs-thin{font-weight:400;color:var(--blue-2)}
.bs-header .bs-sub{margin:7px 0 0;display:flex;flex-wrap:wrap;align-items:center;gap:7px;
  color:var(--muted);font-size:12px;letter-spacing:.02em}
.bs-header .bs-sep{color:var(--line-2)}
.bs-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:6px;
  border:1px solid var(--line);background:rgba(10,19,34,.72);color:var(--muted);
  font-size:9.5px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;white-space:nowrap}
.bs-badge strong{color:var(--ink-2);font-weight:600}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(154px,1fr));
          gap:10px;margin:8px 0 26px}
.kpi{position:relative;
  background:linear-gradient(180deg,#0c1729,#0a1322);
  border:1px solid rgba(79,141,255,.15);border-radius:10px;padding:14px 15px 13px;overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 22px 46px -40px #000;
  transition:border-color .16s ease,transform .16s ease,box-shadow .16s ease}
.kpi:hover{transform:translateY(-1px);border-color:rgba(79,141,255,.32);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 26px 50px -38px rgba(0,0,0,.9)}
.kpi::before{content:"";position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,var(--acc),transparent);opacity:.9}
.kpi::after{content:"";position:absolute;top:-46px;right:-46px;width:104px;height:104px;
  border-radius:50%;background:var(--acc);opacity:.045}
.kpi-l{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:10px;
  font-weight:600;letter-spacing:.13em;text-transform:uppercase}
.kpi-l>span:first-child{display:inline-flex;align-items:center;justify-content:center;
  width:24px;height:24px;border-radius:6px;background:rgba(79,141,255,.08);
  border:1px solid rgba(79,141,255,.14);color:var(--acc)}
.kpi-v{font-family:'IBM Plex Mono',monospace;font-size:30px;font-weight:600;
  color:var(--ink);line-height:1;margin-top:10px;letter-spacing:-.04em;
  font-variant-numeric:tabular-nums}
.kpi-dim .kpi-v{color:var(--muted-2)}

@keyframes bs-ping{0%,100%{opacity:1}50%{opacity:.4}}
.bs-dot{animation:bs-ping 2.6s ease-in-out infinite}

.stProgress div[role="progressbar"]>div>div>div{background:#4f8dff!important}
.stSpinner>div{border-top-color:var(--blue)!important}

@media (max-width:900px){
  .stApp{background-attachment:scroll}
  .block-container{padding-top:1.4rem;padding-bottom:3rem}
  .bs-header .bs-title{font-size:26px}
  .bs-header .bs-badges{margin-left:0;width:100%}
  .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .kpi-v{font-size:27px}
}
</style>
"""


def theme_css(web_fonts: bool | None = None) -> str:
    if web_fonts is None:
        web_fonts = os.environ.get("BLUESTAR_WEB_FONTS", "1") != "0"
    return THEME_CSS.replace("__FONTS__", WEB_FONTS_IMPORT if web_fonts else "")
