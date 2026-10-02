"""Shared design system for every generated page: one stylesheet, one masthead,
one footer. Pages stay dumb; taste lives here.

Everything links /assets/site.css (absolute) so story pages, the board, and the
static pages share one cached stylesheet. Internal navigation is root-relative;
canonical/OG URLs use config.SITE_URL so previews can render anywhere.
"""
from __future__ import annotations

import datetime as dt
import html

from . import config

_ESC = html.escape

# ---------------------------------------------------------------- palette ---
# Dark editorial: ink navy background, warm orange mast accent, green answers,
# blue links. Contrast: ink on bg = 13.9:1, dim on bg = 7.4:1 (AA+ everywhere).

CSS = """
:root{
  --bg:#0e141b; --bg2:#0a0f14; --panel:#151d27; --panel2:#1a2531; --line:#28394a;
  --ink:#e9eef4; --dim:#93a7b9; --faint:#5f7387;
  --acc:#f2a65a; --blue:#7fb4ff; --ok:#8fd6a9; --warn:#e5c07b;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --wrap:1080px; --col:760px;
}
*{box-sizing:border-box}
html{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
::selection{background:#f2a65a44}
.wrap{max-width:var(--wrap);margin:0 auto;padding:0 1.2rem}
.col{max-width:var(--col)}

/* ------------------------------------------------------------ masthead --- */
header.site{background:var(--bg2);border-bottom:1px solid var(--line);
  box-shadow:0 1px 0 #f2a65a22}
.mast{display:flex;align-items:baseline;justify-content:space-between;
  flex-wrap:wrap;gap:.4rem 1rem;padding-top:1.1rem;padding-bottom:.7rem}
.brand{font:800 1.55rem/1 var(--sans);color:var(--ink);letter-spacing:-.02em;
  text-decoration:none!important}
.brand .bolt{color:var(--acc)}
.tagline{color:var(--dim);font-size:.8rem;letter-spacing:.14em;text-transform:uppercase}
nav.sitebar{display:flex;flex-wrap:wrap;gap:.15rem;border-top:1px solid var(--line);
  margin-top:.15rem}
nav.sitebar a{color:var(--dim);font-size:.84rem;font-weight:600;padding:.55rem .8rem;
  border-bottom:2px solid transparent;text-transform:uppercase;letter-spacing:.06em;
  text-decoration:none!important}
nav.sitebar a:hover{color:var(--ink);border-bottom-color:var(--acc)}
nav.sitebar a.rss{margin-left:auto;color:var(--acc)}

/* ---------------------------------------------------------------- hero --- */
.hero{padding:2.4rem 0 .6rem;max-width:var(--col)}
.kicker{color:var(--acc);font-weight:800;font-size:.78rem;letter-spacing:.18em;
  text-transform:uppercase}
.hero h1{font:700 clamp(1.7rem,4.5vw,2.5rem)/1.18 var(--serif);margin:.5rem 0 .8rem;
  letter-spacing:-.01em}
.hero h1 a{color:var(--ink)}
.hero h1 a:hover{color:var(--acc);text-decoration:none}
.lede{font-size:1.25rem;line-height:1.5;color:var(--ink);margin:0 0 1rem}
.hero .meta, .meta{color:var(--dim);font-size:.85rem;line-height:1.55}
.more{font-weight:700;font-size:.9rem}
.badge{background:var(--panel2);color:#cfdcea;border-radius:4px;
  padding:.05rem .4rem;font-size:.72rem;white-space:nowrap}

/* --------------------------------------------------------------- board --- */
section{padding:1.6rem 0}
.sechead{display:flex;align-items:baseline;justify-content:space-between;
  flex-wrap:wrap;gap:.2rem 1rem;border-bottom:2px solid var(--acc);
  padding-bottom:.45rem;margin-bottom:1.2rem}
.sechead h2{font:800 1.15rem/1.2 var(--sans);margin:0;text-transform:uppercase;
  letter-spacing:.1em}
.sechelp{color:var(--dim);font-size:.84rem;margin:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:.9rem}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:1rem 1.15rem;display:flex;flex-direction:column;gap:.15rem}
.tname{color:var(--dim);font-size:.82rem;font-weight:600}
.val{font:800 2rem/1.15 var(--sans);color:var(--ok);letter-spacing:-.01em}
.tile .viz{min-height:58px;margin:.15rem 0 .2rem}
.chip{align-self:flex-start;background:var(--panel2);color:#cfdcea;border-radius:99px;
  padding:.1rem .65rem;font-size:.74rem}
.legend{color:var(--faint);font-size:.78rem;margin:1rem 0 0}

/* ------------------------------------------------------------- signals --- */
ol.signals{list-style:none;margin:0;padding:0}
li.sig{border-bottom:1px solid var(--line);padding:1.3rem 0}
li.sig:first-child{border-top:1px solid var(--line)}
li.sig h3{font:700 1.35rem/1.3 var(--serif);margin:.35rem 0 .4rem}
li.sig h3 a{color:var(--ink)}
li.sig h3 a:hover{color:var(--acc);text-decoration:none}
li.sig .answer{font-size:1.02rem;color:var(--ink);margin:0 0 .5rem}
li.sig .meta{font-size:.82rem}

/* ------------------------------------------------------------------ how --- */
.how{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:.9rem}
.step{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:1rem 1.15rem}
.step b{display:block;color:var(--acc);font-size:.76rem;letter-spacing:.16em;
  text-transform:uppercase;margin-bottom:.35rem}
.step p{margin:0;font-size:.9rem;color:var(--dim)}
.step p strong{color:var(--ink)}

/* ---------------------------------------------------------------- cards ---- */
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:1rem 1.2rem;margin:1.2rem 0}
.card .label{color:var(--dim);font-weight:700;font-size:.72rem;letter-spacing:.16em;
  text-transform:uppercase;margin-bottom:.5rem}
.answerbox{background:var(--panel);border:1px solid var(--line);
  border-left:4px solid var(--ok);border-radius:10px;padding:1rem 1.2rem;
  font:600 1.3rem/1.4 var(--sans);margin:.9rem 0 1.2rem}
.viz{overflow-x:auto}
.viz .vega-embed .chart-wrapper{margin:0}
.viz .vega-embed details summary{color:var(--dim)}
code{background:var(--panel2);color:#cfdcea;padding:.1rem .35rem;border-radius:4px;
  font:.85em/1.5 var(--mono);word-break:break-all}
footer .meta a, .provenance a{color:var(--blue)}

/* --------------------------------------------------------------- footer --- */
footer.site{border-top:1px solid var(--line);background:var(--bg2);margin-top:2.5rem;
  padding:1.8rem 0 2.2rem}
.footgrid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:1.5rem}
.footgrid h4{margin:.2rem 0 .6rem;color:var(--dim);font-size:.74rem;
  letter-spacing:.16em;text-transform:uppercase}
.footgrid p{color:var(--dim);font-size:.87rem;margin:.3rem 0}
.footgrid ul{list-style:none;margin:0;padding:0}
.footgrid li{margin:.3rem 0}
.footgrid a{color:var(--dim);font-size:.87rem}
.footgrid a:hover{color:var(--ink)}
.colophon{border-top:1px solid var(--line);margin-top:1.6rem;padding-top:1rem;
  color:var(--faint);font-size:.78rem;display:flex;justify-content:space-between;
  flex-wrap:wrap;gap:.4rem}
.breadcrumb{margin:1.4rem 0 .2rem;font-size:.82rem}
.breadcrumb a{color:var(--faint)}
@media (max-width:720px){.footgrid{grid-template-columns:1fr}
  .val{font-size:1.7rem}.hero .lede{font-size:1.1rem}}
"""

# ------------------------------------------------------------- components ---

_BRAND = ('<a class="brand" href="/">CT<span class="bolt">⚡</span>Signal</a>')

_NAV = (
    '<a href="/">The board</a>'
    '<a href="/#signals">Latest questions</a>'
    '<a href="/methodology">Methodology</a>'
    '<a href="/about">About</a>'
    '<a href="/masthead">Masthead</a>'
    '<a href="/corrections">Corrections</a>'
    '<a class="rss" href="/feed.xml">RSS ⚡</a>'
)


def dateline(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    return now.strftime("%A, %B %-d, %Y") + " · automated data desk"


def header() -> str:
    return (
        '<header class="site"><div class="wrap mast">'
        + _BRAND
        + f'<span class="tagline">{dateline()}</span>'
        + f'</div><nav class="sitebar wrap">{_NAV}</nav></header>'
    )


def footer() -> str:
    email = config.CONTACT_EMAIL
    year = dt.date.today().year
    return f"""<footer class="site"><div class="wrap footgrid">
<div><h4>CT&nbsp;<span style="color:var(--acc)">⚡</span>&nbsp;Signal</h4>
<p>An automated newsroom for Connecticut: the news cycle picks the question,
public data answers it — every number fetched from a named dataset, never typed
by hand.</p><p><a href="mailto:{email}">{email}</a></p></div>
<div><h4>Sections</h4><ul>
<li><a href="/">The board</a></li>
<li><a href="/#signals">Latest questions</a></li>
<li><a href="/feed.xml">RSS feed</a></li>
<li><a href="https://github.com/alexvnesta/ct-signal/tree/master/archive">Card archive</a></li></ul></div>
<div><h4>Newsroom</h4><ul>
<li><a href="/about">About</a></li>
<li><a href="/methodology">How we work</a></li>
<li><a href="/masthead">Masthead</a></li>
<li><a href="/corrections">Corrections</a></li>
<li><a href="https://github.com/alexvnesta/ct-signal">Source &amp; failure logs</a></li>
</ul></div></div>
<div class="wrap colophon"><span>© {year} CT Signal · Independent automated newsroom</span>
<span>Built at Hack for Humanity · Runs on free-tier public infrastructure</span></div>
</footer>"""


def head(*, title: str, desc: str, path: str, og_type: str = "website",
         og_title: str | None = None, og_desc: str | None = None,
         image: str | None = None, published: str | None = None) -> str:
    url = f"{config.SITE_URL}{path}"
    img = image or f"{config.SITE_URL}/assets/og-cover.png"
    art = (f'<meta property="article:published_time" content="{published}">'
           if published else "")
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_ESC(title)}</title>
<meta name="description" content="{_ESC(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="CT Signal">
<meta property="og:title" content="{_ESC(og_title or title)}">
<meta property="og:description" content="{_ESC(og_desc or desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@ctsignal">
{art}<meta name="theme-color" content="#0e141b">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/assets/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="CT Signal"
 href="{config.SITE_URL}/feed.xml">
<link rel="stylesheet" href="/assets/site.css">"""


def page(*, title: str, desc: str, path: str, body: str, **kw) -> str:
    h = head(title=title, desc=desc, path=path, **kw)
    return (f'<!doctype html>\n<html lang="en"><head>\n{h}\n</head>\n<body>\n'
            f'{header()}\n{body}\n{footer()}\n{VEGA_LOAD}\n</body></html>\n')


# Inline JSON spec islands + one loader keep charts dependency-light and work
# identically on the board and story pages.
VEGA_LOAD = """<script defer src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script defer src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script defer src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<script>window.addEventListener("DOMContentLoaded",()=>{const go=()=>{
document.querySelectorAll("script.vs").forEach(s=>{const el=document.getElementById(
  s.dataset.target); if(!el) return; try{ vegaEmbed(el, JSON.parse(
  s.textContent), {actions:false,renderer:"svg",
  config:{background:"transparent"}}).catch(e=>console.warn("chart:",e));
  }catch(e){console.warn("spec:",e);}});};
  if(window.vegaEmbed) go(); else window.addEventListener("load",go);});</script>"""


def viz(spec_json: str, el_id: str) -> str:
    safe = spec_json.replace("</", "<\\/")
    return (f'<div class="viz" id="{el_id}"></div>'
            f'<script type="application/json" class="vs" '
            f'data-target="{el_id}">{safe}</script>')
