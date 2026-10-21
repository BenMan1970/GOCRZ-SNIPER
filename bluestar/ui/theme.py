"""Visual identity: premium navy dashboard with high-contrast accents."""

from __future__ import annotations

import os

WEB_FONTS_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Manrope:wght@400;500;600;700;800&"
    "family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');"
)

THEME_CSS = """
<style>
__FONTS__
:root{
  --bg:#050b18;
  --bg-2:#071126;
  --surface:#0a1730;
  --surface-2:#0e1d3a;
  --surface-3:#15294b;
  --line:#22385f;
  --line-2:#36527f;
  --ink:#f7f9ff;
  --ink-2:#dbe6fb;
  --muted:#a7b6d4;
  --muted-2:#8496b8;
  --azure:#7db7ff;
  --azure-2:#a8d1ff;
  --iris:#b7a4ff;
  --teal:#5eead4;
  --pink:#f7a6cf;
  --amber:#f7c66b;
  --shadow:0 30px 70px -44px #000;
  color-scheme:dark;
  accent-color:var(--azure);
}

html, body, .stApp, button, input, textarea, select,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stCaptionContainer"]{
  font-family:'Manrope',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
  font-feature-settings:'kern' 1,'liga' 1;
}
html, body{background:var(--bg);color:var(--ink)}
.stApp{
  background:
    radial-gradient(1100px 620px at 8% -12%, rgba(78,139,255,.18), transparent 60%),
    radial-gradient(880px 520px at 96% -6%, rgba(183,164,255,.13), transparent 62%),
    radial-gradient(820px 500px at 50% 112%, rgba(45,212,191,.08), transparent 60%),
    linear-gradient(180deg,#071126 0%,#050b18 46%,#040913 100%);
  background-attachment:fixed;
}
.stApp::before{
  content:"";position:fixed;top:0;left:0;right:0;height:1px;z-index:999;
  pointer-events:none;
  background:linear-gradient(90deg,transparent 4%,rgba(94,234,212,.55) 32%,
             rgba(125,183,255,.8) 52%,rgba(183,164,255,.55) 72%,transparent 96%);
}
[data-testid="stAppViewContainer"]{color:var(--ink)}
.block-container{padding-top:2.4rem;padding-bottom:4.5rem;max-width:1560px}
#MainMenu, footer, header[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4{font-family:'Manrope',sans-serif!important;font-weight:700!important;
  letter-spacing:-.028em!important;color:var(--ink)!important}
p, li{line-height:1.65}

.stButton>button{
  background:linear-gradient(135deg,#5eead4 0%,#7db7ff 48%,#b7a4ff 100%)!important;
  color:#04101f!important;border:1px solid rgba(255,255,255,.22)!important;
  font-family:'Manrope',sans-serif!important;font-weight:800!important;
  font-size:13.5px!important;letter-spacing:.18em!important;text-transform:uppercase!important;
  border-radius:13px!important;padding:15px 0!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.45),
             0 14px 34px -18px rgba(125,183,255,.75)!important;
  transition:transform .16s cubic-bezier(.2,.8,.2,1),box-shadow .18s ease,filter .18s ease!important;
}
.stButton>button:hover{
  transform:translateY(-1.5px)!important;filter:saturate(1.04) brightness(1.04)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.5),
             0 18px 40px -18px rgba(183,164,255,.7)!important;
}
.stButton>button:active{transform:translateY(0)!important}

.stSelectbox label, .stToggle label{
  color:var(--muted)!important;font-size:10.5px!important;font-weight:700!important;
  letter-spacing:.14em!important;text-transform:uppercase!important;
}
.stSelectbox div[data-baseweb="select"]>div{
  background:linear-gradient(180deg,#0c1b37,#09152b)!important;
  border:1px solid var(--line)!important;
  border-radius:12px!important;min-height:46px!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035);
  transition:border-color .16s ease, box-shadow .16s ease!important;
}
.stSelectbox div[data-baseweb="select"]>div:hover{border-color:var(--line-2)!important}
.stSelectbox div[data-baseweb="select"]>div:focus-within{
  border-color:rgba(125,183,255,.8)!important;
  box-shadow:0 0 0 3px rgba(125,183,255,.13)!important;
}
.stSelectbox div[data-baseweb="select"] *{color:var(--ink)!important;font-size:14.5px!important}
div[data-baseweb="popover"] ul{
  background:var(--surface-2)!important;border:1px solid var(--line)!important;
  border-radius:12px!important;box-shadow:var(--shadow)!important;
}
div[data-baseweb="popover"] li{color:var(--ink-2)!important;font-size:14px!important}
div[data-baseweb="popover"] li:hover{background:var(--surface-3)!important;color:var(--ink)!important}

[data-testid="stExpander"]{
  background:linear-gradient(180deg,rgba(14,29,58,.94),rgba(8,18,38,.94))!important;
  border:1px solid var(--line)!important;border-radius:15px!important;overflow:hidden!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 18px 44px -36px #000!important;
}
[data-testid="stExpander"] summary{
  color:var(--ink-2)!important;font-size:12px!important;font-weight:700!important;
  letter-spacing:.11em!important;text-transform:uppercase!important;
}
[data-testid="stExpander"] table{border-collapse:collapse!important;font-size:13.5px!important}
[data-testid="stExpander"] th{
  color:var(--muted)!important;font-size:10.5px!important;text-transform:uppercase!important;
  letter-spacing:.11em!important;border-bottom:1px solid var(--line)!important;
  background:rgba(21,41,75,.45)!important;padding:10px 13px!important;text-align:left!important;
}
[data-testid="stExpander"] td{
  color:var(--ink-2)!important;border-bottom:1px solid rgba(54,82,127,.55)!important;
  padding:10px 13px!important;
}
[data-testid="stExpander"] code{
  background:rgba(125,183,255,.1)!important;color:var(--azure-2)!important;
  font-family:'IBM Plex Mono',monospace!important;font-size:12px!important;
  border-radius:6px!important;padding:1px 6px!important;
}

[data-testid="stDataFrame"]{
  border:1px solid var(--line);border-radius:13px;overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 20px 46px -40px #000;
}
[data-testid="stCaptionContainer"]{color:var(--muted)!important}

hr{border:none!important;height:1px!important;
   background:linear-gradient(90deg,transparent,rgba(54,82,127,.85) 10%,
              rgba(125,183,255,.35) 50%,rgba(54,82,127,.85) 90%,transparent)!important;
   margin:22px 0!important}
::selection{background:rgba(183,164,255,.3);color:#fff}
::-webkit-scrollbar{height:9px;width:9px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--surface-3);border-radius:9px;border:2px solid var(--bg)}
::-webkit-scrollbar-thumb:hover{background:var(--line-2)}

.bs-header{display:flex;align-items:center;gap:18px;margin-bottom:22px;flex-wrap:wrap}
.bs-header .bs-brand{display:flex;align-items:center;gap:18px;min-width:0}
.bs-header .bs-badges{display:flex;align-items:center;gap:9px;margin-left:auto;flex-wrap:wrap}
.bs-overline{font-size:10px;font-weight:800;letter-spacing:.24em;
  text-transform:uppercase;color:var(--azure);margin-bottom:5px}
.bs-header .bs-title{margin:0;font-size:32px;line-height:1.08;color:var(--ink);
  font-weight:800;letter-spacing:-.03em}
.bs-header .bs-title .bs-thin{font-weight:500;color:var(--azure-2)}
.bs-header .bs-sub{margin:8px 0 0;display:flex;flex-wrap:wrap;align-items:center;gap:7px;
  color:var(--muted);font-size:12.5px;letter-spacing:.035em}
.bs-header .bs-sep{color:var(--line-2)}
.bs-badge{display:inline-flex;align-items:center;gap:7px;padding:7px 12px;border-radius:999px;
  border:1px solid var(--line);background:rgba(10,23,48,.72);color:var(--muted);
  font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;white-space:nowrap}
.bs-badge strong{color:var(--ink-2);font-weight:700}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));
          gap:13px;margin:8px 0 28px}
.kpi{position:relative;
  background:linear-gradient(158deg,rgba(16,32,64,.96),rgba(8,18,38,.96));
  border:1px solid rgba(125,183,255,.16);border-radius:16px;padding:16px 17px 15px;overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.045),0 22px 46px -38px #000;
  transition:border-color .18s ease,transform .18s cubic-bezier(.2,.8,.2,1),
             box-shadow .18s ease}
.kpi:hover{transform:translateY(-2px);border-color:rgba(125,183,255,.36);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 26px 50px -34px rgba(0,0,0,.9)}
.kpi::before{content:"";position:absolute;top:0;left:17px;right:17px;height:2px;
  background:linear-gradient(90deg,var(--acc),rgba(255,255,255,.05));
  border-radius:2px;opacity:.95}
.kpi::after{content:"";position:absolute;top:-48px;right:-48px;width:112px;height:112px;
  border-radius:50%;background:var(--acc);opacity:.06}
.kpi-l{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:10.5px;
  font-weight:800;letter-spacing:.15em;text-transform:uppercase}
.kpi-l>span:first-child{display:inline-flex;align-items:center;justify-content:center;
  width:25px;height:25px;border-radius:8px;background:rgba(125,183,255,.09);
  border:1px solid rgba(125,183,255,.15);color:var(--acc)}
.kpi-v{font-family:'IBM Plex Mono',monospace;font-size:33px;font-weight:600;
  color:var(--ink);line-height:1;margin-top:12px;letter-spacing:-.04em;
  font-variant-numeric:tabular-nums}
.kpi-dim .kpi-v{color:var(--muted-2)}

@keyframes bs-breathe{0%,100%{transform:scale(1);opacity:.28}50%{transform:scale(1.4);opacity:0}}
@keyframes bs-ping{0%,100%{opacity:1}50%{opacity:.45}}
.bs-pulse{animation:bs-breathe 2.4s cubic-bezier(.2,.6,.3,1) infinite}
.bs-dot{animation:bs-ping 1.9s ease-in-out infinite}

.stProgress div[role="progressbar"]>div>div>div{
  background:linear-gradient(90deg,#5eead4,#7db7ff 55%,#b7a4ff)!important;
}
.stSpinner>div{border-top-color:var(--azure)!important}

@media (max-width:900px){
  .stApp{background-attachment:scroll}
  .block-container{padding-top:1.5rem;padding-bottom:3rem}
  .bs-header .bs-title{font-size:27px}
  .bs-header .bs-badges{margin-left:0;width:100%}
  .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .kpi-v{font-size:29px}
}
</style>
"""


def theme_css(web_fonts: bool | None = None) -> str:
    if web_fonts is None:
        web_fonts = os.environ.get("BLUESTAR_WEB_FONTS", "1") != "0"
    return THEME_CSS.replace("__FONTS__", WEB_FONTS_IMPORT if web_fonts else "")
