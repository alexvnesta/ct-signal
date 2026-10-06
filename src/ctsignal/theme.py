"""Shared design system for every generated page: one stylesheet, one masthead,
one footer. Pages stay dumb; taste lives here.

Everything links /assets/site.css (absolute) so story pages, the board, and the
static pages share one cached stylesheet. Internal navigation is root-relative;
canonical/OG URLs use config.SITE_URL so previews can render anywhere.

Accessibility contract (WCAG 2.2 AA): every color pair used for meaningful text
passes 4.5:1; in-content links carry an underline, not just color; charts carry
aria-labels + captions; there is a skip link and a main landmark; :focus-visible
is always visible on the dark theme.
"""
from __future__ import annotations

import datetime as dt
import html
import json

import hashlib

from . import config

_ESC = html.escape

# ---------------------------------------------------------------- palette ---
# Dark editorial: ink navy background, warm orange mast accent, green answers,
# blue links. Verified AA+ on every surface (see CONTRAST note in CSS header).

CSS_HASH = ''  # patched at import end
CSS = """
/* Contrast (WCAG 2.2 AA, verified on paper #faf8f3): ink #1c2733 13.8 ·
   dim #4c5a68 6.6 · faint #66717e 4.6 · acc #a85408 4.9 · blue #2b62b8 5.2
   ok #1a6e41 5.3 · badge #4c5a68/#eee9df 6.0 — all >= 4.5:1 normal text */
@font-face{font-family:"Newsreader";font-style:normal;font-weight:700;
  font-display:swap;src:url("/assets/fonts/newsreader-700-latin.woff2")
  format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,
  U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,
  U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
:root{
  --bg:#faf8f3; --bg2:#f4f1e9; --panel:#ffffff; --panel2:#efece3; --line:#d9d3c6;
  --rule:#e4dfd3; --ink:#1c2733; --dim:#4c5a68; --faint:#66717e;
  --acc:#a85408; --acc2:#d9772b; --blue:#2b62b8; --ok:#1a6e41; --warn:#8a6d1f;
  --serif:"Newsreader","Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --wrap:1140px; --col:760px;
}
*{box-sizing:border-box}
html{color-scheme:light}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans);
  min-height:100vh;display:flex;flex-direction:column;
  -webkit-smoothing:antialiased;-webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
/* in-content links carry a non-color cue (WCAG 1.4.1); brand + nav opt out */
.meta a, .breadcrumb a, .provenance a, .footgrid a, .card a, .item a.r
{text-decoration:underline;text-underline-offset:3px}
::selection{background:#d9772b33}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:2px}
.skip{position:absolute;left:-9999px;top:0;z-index:20;background:var(--acc);color:#fff;
  padding:8px 14px;font-weight:700}
.skip:focus{left:0}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:
  hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:
  none!important;scroll-behavior:auto!important}}
.wrap{max-width:var(--wrap);margin:0 auto;padding:0 1.2rem}
.col{max-width:var(--col)}
main{display:block;flex:1 0 auto}

/* ------------------------------------------------- masthead (broadsheet) --- */
/* The nameplate is typographic and centered — the broadsheet convention:
   rules above and below the folio line, sections on a double-ruled line.
   The drawn skyline lives where a paper puts its tailpiece: page bottom. */
header.site{background:var(--bg)}
/* The nameplate carries the house drawing itself: the light skyline sits
   behind the wordmark like a printer's ornament, at quarter strength — a
   background, not a banner; it never steals clicks from the brand. */
.nameplate{position:relative;text-align:center;padding:1.5rem 1.2rem 0;
  overflow:hidden}
.plate-art{position:absolute;left:50%;bottom:-8px;transform:translateX(-50%);
  height:clamp(84px,13vw,148px);width:auto;max-width:96%;opacity:.4;
  pointer-events:none}
.brand{position:relative;display:inline-block;padding-bottom:2.4rem;
  font:700 clamp(2.1rem,6vw,3.3rem)/1.05 var(--serif);color:var(--ink);
  letter-spacing:.05em;text-decoration:none!important}
.boltwrap{display:inline-block;font-style:normal}
.boltwrap svg{display:inline-block;width:.6em;height:.92em;vertical-align:-.06em;
  margin:0 .08em;color:var(--acc2)}
.brand .boltwrap svg{width:.66em;height:1em}
.dateline{text-align:center;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);
  border-width:3px 0 1px;padding:.4rem 1.2rem;color:var(--dim);font-size:.78rem;
  letter-spacing:.14em;text-transform:uppercase}
nav.sitebar{display:flex;flex-wrap:wrap;justify-content:center;gap:.1rem;
  border-bottom:3px double var(--ink);margin-bottom:.2rem}
nav.sitebar a{color:var(--dim);font:600 .8rem/1 var(--sans);padding:.65rem .85rem;
  min-height:44px;display:inline-flex;align-items:center;text-transform:uppercase;
  letter-spacing:.09em;text-decoration:none!important;border-bottom:2px solid transparent}
nav.sitebar a:hover{color:var(--acc)}
nav.sitebar a.rss{color:var(--acc)}

/* ------------------------------------------------------ Latest (broadsheet) */
.latest{padding:1.4rem 0 .6rem}
.latest-grid{display:grid;grid-template-columns:minmax(0,6.5fr) minmax(0,4.5fr);
  gap:0 2rem}
.lead .kicker{color:var(--acc);font-weight:800;font-size:.76rem;letter-spacing:.16em;
  text-transform:uppercase}
.lead h2{font:700 clamp(1.6rem,3.4vw,2.3rem)/1.15 var(--serif);margin:.45rem 0 .55rem;
  text-wrap:balance}
.lead h2 a{color:var(--ink)}
.lead h2 a:hover{color:var(--acc);text-decoration:none}
.lead .lede{font:400 1.12rem/1.55 var(--serif);color:var(--dim);margin:0 0 .8rem}
.lead .vizwrap{margin:.2rem 0 .6rem;background:var(--panel);border:1px solid var(--rule);
  padding:.6rem .5rem .3rem}
.sec2 .item,.rail .item{border-top:1px solid var(--rule);padding:.85rem 0}
.sec2 .item:first-child,.rail .item:first-child{border-top:3px solid var(--ink)}
.item-fig{flex:0 0 216px}
.item-fig img{width:216px;height:auto;display:block;border:1px solid var(--rule)}
.item-body{min-width:0}
.sec2 h3,.rail h3{font:700 1.08rem/1.3 var(--serif);margin:.1rem 0 .3rem}
.sec2 h3 a,.rail h3 a{color:var(--ink)}
.sec2 h3 a:hover,.rail h3 a:hover{color:var(--acc);text-decoration:none}
.item .meta{color:var(--faint);font-size:.8rem;line-height:1.5}
.item .kicker{display:block;color:var(--acc);font-weight:700;font-size:.68rem;
  letter-spacing:.14em;text-transform:uppercase;margin-bottom:.15rem}
.sec2{align-self:start}
.rail{margin-top:1.6rem;border-top:0}
.railhead,.lead-head,.sec2-head{font:800 .8rem/1 var(--sans);letter-spacing:.18em;
  text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
  padding-bottom:.5rem;margin:0 0 .2rem}
@media(min-width:1000px){.latest-grid{grid-template-columns:minmax(0,6fr) minmax(0,3.6fr) minmax(0,3fr)}}

/* --------------------------------------------------------------- board ---- */
section{padding:1.6rem 0}
.sechead{display:flex;align-items:baseline;justify-content:space-between;
  flex-wrap:wrap;gap:.2rem 1rem;border-bottom:3px solid var(--ink);
  padding-bottom:.45rem;margin-bottom:1.2rem}
.sechead h2{font:800 1.15rem/1.2 var(--sans);margin:0;text-transform:uppercase;
  letter-spacing:.1em;text-wrap:balance}
.sechelp{color:var(--faint);font-size:.84rem;margin:0;text-align:right}
.storyh1{font:700 clamp(1.6rem,4vw,2.3rem)/1.2 var(--serif);
  margin:.9rem 0 .3rem}
.allq{margin:.8rem 0 0;font-size:.84rem}
.allq a{color:var(--dim);text-decoration:underline}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}
.tile{background:var(--panel);border:1px solid var(--rule);border-top:3px solid var(--acc2);
  padding:1rem 1.15rem;display:flex;flex-direction:column;gap:.15rem}
.tile:hover{border-color:var(--acc2)}
.tname{color:var(--dim);font-size:.82rem;font-weight:600}
.val{font:800 2rem/1.15 var(--sans);color:var(--ok);letter-spacing:-.01em}
.tile .viz{min-height:58px;margin:.15rem 0 .2rem}
.tile .viz,.tile .viz .vega-embed,.tile .viz .chart-wrapper{display:block;width:100%}
.vote{display:flex;align-items:center;gap:.6rem;margin-top:.85rem;
  color:var(--dim);font-size:.9rem}
.vote button{background:var(--panel2);color:var(--dim);border:1px solid var(--line);
  border-radius:99px;padding:.25rem .85rem;font:inherit;font-size:.85rem;cursor:pointer}
.vote button:hover{color:var(--ink);border-color:var(--acc)}
.vote button[data-chosen]{color:#fff;background:var(--acc);border-color:var(--acc)}
.vote button:disabled{cursor:default}
.badge{background:#eee9df;color:var(--dim);border-radius:3px;
  padding:.05rem .4rem;font-size:.72rem;white-space:nowrap}
.badge.trend{background:var(--acc);color:#fff;border:0}
.chip{align-self:flex-start;background:var(--panel2);color:var(--dim);border-radius:99px;
  padding:.1rem .65rem;font-size:.74rem}

.sub a,.meta a{text-decoration:underline}
.klink{color:inherit;text-decoration:none;border-bottom:1px dotted currentColor}
.klink:hover{border-bottom-style:solid}
.towntab{width:100%;border-collapse:collapse;margin:.8rem 0}
.towntab td{padding:.45rem .6rem;border-bottom:1px solid var(--rule);font-variant-numeric:tabular-nums}
.towntab td:first-child{color:var(--dim)}
.towntab td:last-child{text-align:right;font-weight:700}
/* .footgrid a out-ranks .subbtn for the color property — the button needs
   the footer-scoped rule or it renders gray-on-rust, which reads as broken */
a.subbtn{display:inline-block;background:var(--acc);color:#fff;padding:.4rem .9rem;
  font-size:.84rem;font-weight:700;letter-spacing:.04em}
a.subbtn:hover,a.subbtn:focus-visible{background:#8f4706;color:#fff;
  text-decoration:none}
.footgrid a.subbtn{color:#fff}
.footgrid a.subbtn:hover{color:#fff}
details.embed{border:1px solid var(--rule);border-radius:6px;background:var(--panel);
  padding:.6rem 1rem;margin:1rem 0}
details.embed summary{cursor:pointer;font-weight:700;font-size:.9rem;color:var(--dim)}
details.embed summary:hover{color:var(--ink)}
details.embed textarea{width:100%;box-sizing:border-box;background:var(--bg2);
  color:var(--ok);border:1px solid var(--line);border-radius:4px;padding:.5rem;
  font:.8rem/1.5 var(--mono);margin-top:.6rem}
.legend{color:var(--faint);font-size:.8rem;margin:1rem 0 0}
.wire{color:var(--faint);font-size:.8rem;margin:.2rem 0 .9rem}
.wireblock{border-top:3px double var(--ink);margin-top:2.2rem;padding-top:.2rem}
.wirelist{list-style:none;padding:0;margin:.4rem 0 0;column-count:2;
  column-gap:2.4rem}
.wirelist li{padding:.5rem 0;border-bottom:1px solid var(--rule);
  break-inside:avoid;list-style:none}
.wirelist{padding-left:0}
.wirelist li a{font-weight:600;font-size:.95rem}
.wiresrc{display:block;color:var(--faint);font:.7rem/1.4 var(--mono);
  margin-top:.1rem;text-transform:uppercase;letter-spacing:.06em}
.wireans{display:inline-block;background:#eee9df;color:#6e3705;
  font:700 .68rem/1 var(--mono);letter-spacing:.06em;padding:.18rem .45rem;
  border-radius:3px;text-transform:uppercase;margin-top:.25rem}
.wireans:hover{background:var(--acc);color:#fff}
.wire-n{background:#eee9df;color:var(--dim);padding:.02rem .35rem;
  border-radius:3px;font:700 .72rem var(--mono)}

/* ------------------------------------------------------------- signals ---- */
/* kept: town/story index lists reuse .sig on paper */
ol.signals{list-style:none;margin:0;padding:0;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:1rem}
li.sig{border:1px solid var(--rule);background:var(--panel);
  overflow:hidden;display:flex;flex-direction:column}
.sigart{display:block;width:100%;height:auto;border-bottom:1px solid var(--rule)}
li.sig .sigpad{padding:.9rem 1.1rem 1.05rem;display:flex;flex-direction:column}
li.sig h3{font:700 1.35rem/1.3 var(--serif);margin:.35rem 0 .4rem}
li.sig h2{font:700 1.35rem/1.3 var(--serif);margin:.35rem 0 .4rem}
li.sig h3 a{color:var(--ink)}
li.sig h3 a:hover{color:var(--acc);text-decoration:none}
li.sig .answer{font-size:1.02rem;color:var(--dim);margin:0 0 .5rem}
li.sig .meta{font-size:.88rem}

/* ---------------------------------------------------------------- cards --- */
.card{background:var(--panel);border:1px solid var(--rule);
  padding:1rem 1.2rem;margin:1.2rem 0}
.card .label{color:var(--dim);font-weight:700;font-size:.72rem;letter-spacing:.16em;
  text-transform:uppercase;margin-bottom:.5rem}
.answerbox{background:var(--bg2);border:1px solid var(--rule);
  border-left:4px solid var(--ok);padding:1rem 1.2rem;
  font:600 1.3rem/1.4 var(--sans);margin:.9rem 0 1.2rem}
figure.vizwrap{margin:0}
figure.vizwrap figcaption{color:var(--faint);font-size:.8rem;margin-top:.4rem;
  line-height:1.45}
.viz{overflow-x:auto}
.viz:focus-visible{outline:2px solid var(--acc);outline-offset:4px}
.viz .vega-embed .chart-wrapper{margin:0}
.viz .vega-embed details summary{color:var(--dim)}
/* charts carry baked dark-palette config from altair; vega paints text and
   rules with presentation attributes, which any CSS rule outranks — one
   override keeps every chart on the paper without regenerating specs */
.viz text{fill:#4c5a68}
.viz .role-axis path,.viz .role-axis line,
.viz .role-legend path,.viz .role-legend line{stroke:#b8b2a6}
.viz .role-grid path,.viz .role-grid line{stroke:#e4dfd3}
.viz .role-title text{fill:#1c2733}
.viz .role-legend-label text{fill:#4c5a68}
code{background:var(--panel2);color:var(--ink);padding:.1rem .35rem;
  font:.85em/1.5 var(--mono);word-break:break-all}
.provenance a{color:var(--blue);overflow-wrap:anywhere}

/* --------------------------------------------------------- story / hero --- */
.hero{padding:2.2rem 0 .6rem;max-width:var(--col)}
.storyhero{display:block;width:100%;height:auto;border:1px solid var(--rule);
  margin:.6rem 0 0}
.kicker{color:var(--acc);font-weight:800;font-size:.78rem;letter-spacing:.18em;
  text-transform:uppercase;text-wrap:balance}
.hero h1{font:700 clamp(1.7rem,4.5vw,2.5rem)/1.18 var(--serif);margin:.5rem 0 .8rem;
  letter-spacing:-.01em;text-wrap:balance}
.hero h1 a{color:var(--ink)}
.hero h1 a:hover{color:var(--acc);text-decoration:none}
.lede{font-size:1.25rem;line-height:1.5;color:var(--dim);margin:0 0 1rem}
.hero .vizwrap{margin:1.2rem 0 .3rem;background:var(--panel);
  border:1px solid var(--rule);padding:.6rem .5rem .3rem}
.hero .meta, .meta{color:var(--dim);font-size:.9rem;line-height:1.55}
.meta .trig{display:block}
.meta .when,.meta .more{display:block;margin-top:.2rem}
.meta time{font-variant-numeric:tabular-nums}
.srclabel{color:var(--faint)}
.more{color:var(--acc);font-weight:700;font-size:.9rem;display:inline-block;
  padding:10px 0;min-height:44px}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
white-space:nowrap;border:0;padding:0;margin:-1px;clip-path:inset(50%)}

/* ------------------------------------------------------------ tailpiece --- */
/* our Hartford skyline as a printer's tailpiece — the drawing that matches
   the paper, at the foot of the board (see assets-src/README.md) */
.tailwrap{padding:1.2rem 1.2rem 0}
.tailpiece{display:block;width:100%;height:auto;max-width:1140px;margin:0 auto}

/* ---------------------------------------------------------------- footer -- */
footer.site{border-top:3px double var(--ink);background:var(--bg2);margin-top:2.5rem;
  padding:1.8rem 0 2.2rem}
.footgrid{display:grid;grid-template-columns:2fr 1fr 1fr 1.3fr;gap:1.5rem}
.footgrid form{display:flex;gap:.4rem;margin-top:.4rem}
.footgrid input{flex:1;min-width:0;background:var(--panel);border:1px solid var(--line);
color:var(--ink);padding:.45rem .6rem;font:inherit;font-size:.87rem}
.footgrid input:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
.footgrid form button{background:var(--acc);color:#fff;border:0;padding:.45rem .8rem;
font:inherit;font-size:.87rem;font-weight:700;cursor:pointer}
@media(max-width:880px){.footgrid{grid-template-columns:1fr 1fr}}
.footgrid h2{margin:.2rem 0 .6rem;color:var(--dim);font-size:.74rem;
  letter-spacing:.16em;text-transform:uppercase}
.footgrid p{color:var(--dim);font-size:.87rem;margin:.3rem 0}
.footgrid ul{list-style:none;margin:0;padding:0}
.footgrid li{margin:.3rem 0}
.footgrid a{color:var(--dim);font-size:.87rem}
.footgrid a:hover{color:var(--ink)}
.colophon{border-top:1px solid var(--rule);margin-top:1.6rem;padding-top:1rem;
  color:var(--dim);font-size:.78rem;
  display:flex;justify-content:space-between;
  flex-wrap:wrap;gap:.4rem}
.colophon a{text-decoration:underline}
.breadcrumb{margin:1.4rem 0 .2rem;font-size:.82rem}
.breadcrumb a{color:var(--faint);display:inline-block;padding:.35rem .15em}
@media (max-width:999px){.latest-grid{grid-template-columns:1fr}}
.peersum,.peershow,.peersum-t{display:none}
.peersum{list-style:none;margin:.4rem 0 0;padding:0}
.peersum li{display:flex;align-items:center;gap:.45rem;margin:.18rem 0;font-size:.8rem}
.peersum .pl{flex:0 0 7.2rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--dim)}
.peersum .pb{height:.68rem;background:#b8b2a6;min-width:2px}
.peersum li.ct .pl{color:var(--ink);font-weight:700}
.peersum li.ct .pb{background:var(--acc)}
.peersum .pv{font:600 .78rem var(--sans);color:var(--ink)}
.peersum-t{font-size:.78rem;color:var(--dim);text-decoration:underline;cursor:pointer;margin-top:.3rem}
.yourtown{background:var(--panel);padding:.55rem .7rem;
  border-left:3px solid var(--acc)}
.yt-line1{display:block;font:700 1.05rem/1.25 var(--serif);color:var(--ink)}
.yourtown a{text-decoration:underline}
.yt-facts{display:block;margin-top:.25rem;color:var(--ink)}
.yt-change{background:none;border:0;color:var(--dim);font-size:.78rem;
  text-decoration:underline;cursor:pointer;padding:0;vertical-align:baseline}
.ytbtn{background:var(--acc);color:#fff;border:0;padding:.3rem .6rem;
  font:600 .8rem var(--sans);cursor:pointer}
@media (max-width:720px){.footgrid{grid-template-columns:1fr}
  .val{font-size:1.7rem}.hero .lede{font-size:1.1rem}
  nav.sitebar{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;
    overscroll-behavior-x:contain;justify-content:flex-start}
  nav.sitebar::-webkit-scrollbar{display:none}
  nav.sitebar a{white-space:nowrap;padding:.5rem .65rem;font-size:.74rem}
  .kicker{letter-spacing:.1em;font-size:.74rem}
  nav.sitebar a.rss{display:none}
  .nameplate{padding:.9rem .8rem 0}
  .brand{font-size:1.85rem;padding-bottom:1.7rem}
  .plate-art{height:70px}
  .dateline{font-size:.62rem;letter-spacing:.08em;padding:.3rem .8rem}
  .vizwrap .viz{min-height:0!important;max-height:340px;
    overflow-y:auto;scrollbar-width:none;overscroll-behavior-x:contain}
  .vizwrap .viz::-webkit-scrollbar{display:none}
  .peershow~.viz,.peershow~.viz.vega-embed{display:none}
  .peershow:checked~.viz,.peershow:checked~.viz.vega-embed{display:block}
  .peershow:checked~.peersum{display:none}
  .peershow~figcaption{display:none}
  .peershow:checked~figcaption{display:block}
  .peersum{display:block}
  .peersum-t{display:inline-block}

  .sechead h2{letter-spacing:.06em}
  .item-fig{flex:0 0 132px}.item-fig img{width:132px}
  footer.site{padding-bottom:calc(2.2rem + 4.5rem +
    env(safe-area-inset-bottom,0px))}}
"""

# ------------------------------------------------------------- components ---

_BOLT_SVG = ('<svg class="bolt" viewBox="0 0 12 18" aria-hidden="true">'
             '<path fill="currentColor" d="M7.4 0 0 10.6h4.7L3.2 18l8.8-11.2H6.9'
             'L8.9 0z"/></svg>')
# The bolt is our mark — so it is drawn, not typed: one path, currentColor,
# sized in em. The ⚡ text emoji rendered as clip art; this renders as type.
_BOLT = ('<i class="boltwrap" aria-hidden="true">' + _BOLT_SVG + '</i>')
_BRAND = f'<a class="brand" href="/">CT{_BOLT}Signal</a>'
_RSS_BOLT = _BOLT_SVG

_NAV = (
    '<a href="/">The board</a>'
    '<a href="/#signals">Latest questions</a>'
    '<a href="/towns">Towns</a>'
    '<a href="/about">About</a>'
    f'<a class="rss" href="/feed.xml">RSS {_RSS_BOLT}</a>'
)


def dateline(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    # nbsp glues the separator to the date: balanced wraps must never leave
    # a leading "·" on the tagline's second line.
    return now.strftime("%A, %B %-d, %Y") + "\u00a0\u00b7 automated data desk"


def header() -> str:
    # The nameplate carries the house drawing itself: the light skyline sits
    # behind the wordmark like a printer's ornament, at quarter strength.
    # (The full-strength copy stays as the page's tailpiece at the bottom.)
    return (
        '<a class="skip" href="#main">Skip to content</a>'
        '<header class="site">'
        '<div class="wrap nameplate">'
        '<img class="plate-art" src="/assets/skyline-light.png" '
        'width="2340" height="875" alt="" aria-hidden="true">'
        + _BRAND + '</div>'
        f'<div class="dateline">{dateline()}</div>'
        f'<nav class="sitebar" aria-label="Primary">{_NAV}</nav></header>'
    )


def trigger_parts(card: dict) -> tuple[str, str]:
    """The 'Source' attribution, rendered once for home and stories.
    Returns (source-prefix, title-html); both already HTML-escaped.
    Demo-triggered cards are labeled here, per card, so a reader
    never has to scroll to a global disclaimer to learn a card
    ran on a stand-in headline."""
    from . import cards as _c
    h = card.get("headline") or {}
    if not h.get("title"):
        return ('<span class="badge">DATA DESK</span> ',
                _ESC("Question raised by the data itself; no news "
                     "headline claims credit for it."))
    title = _ESC(h["title"])
    src = h.get("source") or ""
    # civic-calendar entries carry "[civic calendar] ..." in the title;
    # don't print the source label twice.
    if src and title.startswith(f"[{_ESC(src)}]"):
        title = title[len(f"[{_ESC(src)}]") + 1:].lstrip()
    if h.get("url"):
        title = f'<a href="{_ESC(h["url"])}" rel="noopener">{title}</a>'
    prefix = f'{_ESC(src)} \u2014 ' if src else ""
    if _c.is_demo_trigger(card):
        prefix = '<span class="badge">DEMO TRIGGER</span> ' + prefix
    return prefix, title


def footer() -> str:
    email = config.CONTACT_EMAIL
    year = dt.date.today().year
    return f"""<footer class="site"><div class="wrap footgrid">
<div><h2>CT&nbsp;<span class="boltwrap" aria-hidden="true"><svg class="bolt" viewBox="0 0 12 18" aria-hidden="true"><path fill="currentColor" d="M7.4 0 0 10.6h4.7L3.2 18l8.8-11.2H6.9L8.9 0z"/></svg></span>&nbsp;Signal</h2>
<p>An automated newsroom for Connecticut: the news cycle picks the question,
public data answers it. Know where you live.</p>
<p><a class="subbtn" href="mailto:{email}?subject=Board%20sponsorship">Sponsor the board</a></p>
<p><a href="mailto:{email}">{email}</a></p>
<p><a href="mailto:{email}?subject=Question%20for%20the%20desk&amp;body=Town%3A%20%0AQuestion%20(one%20sentence)%3A%20">Ask the desk a question</a> — every message is read and logged.</p></div>
<div><h2>Sections</h2><ul>
<li><a href="/">The board</a></li>
<li><a href="/#signals">Latest questions</a></li>
<li><a href="/archive">Card archive</a></li>
<li><a href="/towns">Towns</a></li>
<li><a href="/sources">Data sources</a></li>
<li><a href="/feed.xml">RSS feed</a></li></ul></div>
<div><h2>Newsroom</h2><ul>
<li><a href="/about">About</a></li>
<li><a href="/masthead">Who runs this</a></li>
<li><a href="/corrections">Corrections</a></li>
</ul></div>
<div><h2>Weekly digest</h2>
<p>The strongest signal of the week, one email, filed weekly and sent by a human.
Unsubscribe in one click — we sell no data.</p>
<form action="https://buttondown.com/api/emails/embed-subscribe/ctsignal"
method="post" target="_blank" rel="noopener">
<label class="sr-only" for="foot-sub-email">Email address</label>
<input id="foot-sub-email" type="email" name="email" placeholder="you@example.com" required>
<button type="submit">Subscribe</button></form></div></div>
<div class="wrap colophon"><span>© {year} CT Signal · Independent automated newsroom ·
<a href="https://github.com/alexvnesta/ct-signal">Source &amp; failure logs</a></span>
<span>Built at Hack for Humanity · Runs on free-tier public infrastructure</span></div>
</footer>"""


_ORG = {"@type": "Organization", "name": "CT Signal",
        "url": f"{config.SITE_URL}/",
        "logo": {"@type": "ImageObject",
                 "url": f"{config.SITE_URL}/assets/og-cover.png",
                 "width": 1200, "height": 630}}


def site_json_ld() -> dict:
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{config.SITE_URL}/#website",
         "url": f"{config.SITE_URL}/", "name": "CT Signal",
         "description": "Connecticut data answers to the questions its news "
                        "cycle is already asking. Know where you live.",
         "inLanguage": "en-US", "publisher": {"@id": f"{config.SITE_URL}/#org"}},
        {"@type": "Organization", "@id": f"{config.SITE_URL}/#org",
         "name": "CT Signal", "url": f"{config.SITE_URL}/",
         "email": config.CONTACT_EMAIL,
         "logo": dict(_ORG["logo"]),
         "sameAs": ["https://github.com/alexvnesta/ct-signal"]},
    ]}


def article_json_ld(*, card_id: str, headline: str, description: str,
                    published: str, section: str,
                    image: str | None = None,
                    modified: str | None = None) -> dict:
    url = f"{config.SITE_URL}/story/{card_id}"
    return {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "@id": f"{url}#article",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": headline, "description": description,
        "image": [image or f"{config.SITE_URL}/assets/og-cover.png"],
        # dateModified only moves when the pipeline actually re-checked
        # the number, so "modified" means modified, not "deployed".
        "datePublished": published,
        "dateModified": modified or published,
        "author": {"@type": "Organization", "name": "CT Signal",
                   "url": f"{config.SITE_URL}/"},
        "publisher": dict(_ORG),
        "articleSection": section, "inLanguage": "en-US",
        "isAccessibleForFree": True,
    }


def head(*, title: str, desc: str, path: str, og_type: str = "website",
         og_title: str | None = None, og_desc: str | None = None,
         image: str | None = None, published: str | None = None,
         json_ld: dict | list | None = None) -> str:
    url = f"{config.SITE_URL}{path}"
    img = image or f"{config.SITE_URL}/assets/og-cover.png"
    img_alt = og_title or title
    art = (f'<meta property="article:published_time" content="{published}">'
           if published else "")
    ld = ""
    if json_ld is not None:
        blob = json.dumps(json_ld, ensure_ascii=False, separators=(",", ":"))
        ld = (f'<script type="application/ld+json">'
              f'{blob.replace("</", "<\\/").replace("<!--", "<\\u0021--")}</script>')
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
<meta property="og:image:alt" content="{_ESC(img_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@ctsignal">
<meta name="twitter:title" content="{_ESC(og_title or title)}">
<meta name="twitter:description" content="{_ESC(og_desc or desc)}">
<meta name="twitter:image" content="{img}">
<meta name="twitter:image:alt" content="{_ESC(img_alt)}">
{art}<meta name="theme-color" content="#faf8f3">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/assets/favicon-32.png" type="image/png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/icon-192.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="CT Signal"
 href="{config.SITE_URL}/feed.xml">
<link rel="alternate" type="application/feed+json" title="CT Signal (JSON)"
 href="{config.SITE_URL}/feed.json">
<link rel="stylesheet" href="/assets/site.css?v={CSS_HASH}">
{ld}"""


def page(*, title: str, desc: str, path: str, body: str, **kw) -> str:
    h = head(title=title, desc=desc, path=path, **kw)
    # The vendored Vega stack is ~280 KB compressed: it loads only on pages
    # that actually contain a chart island (class="vs"), not on prose.
    vega = VEGA_LOAD if 'class="vs"' in body else ""
    return (f'<!doctype html>\n<html lang="en"><head>\n{h}\n</head>\n<body>\n'
            f'{header()}\n<main id="main">\n{body}\n</main>\n{footer()}\n'
            f'{vega}\n</body></html>\n')


# Inline JSON spec islands + one loader keep charts dependency-light and work
# identically on the board and story pages.
# Charts are the one piece of JavaScript the board cannot generate as
# markup, and the review found the honest way to keep the promise: ship
# the renderer ourselves. Pinned copies in assets/vendor/ — same bytes
# every visitor gets, no CDN request that leaks a page view to a
# third party, and the CSP shrinks to this origin.
VEGA_LOAD = """<script defer src="/assets/vendor/vega.min.js?v=6-6-7"></script>
<script defer src="/assets/vendor/vega-lite.min.js?v=6-6-7"></script>
<script defer src="/assets/vendor/vega-embed.min.js?v=6-6-7"></script>
<script>window.addEventListener("DOMContentLoaded",()=>{
// vega-embed replaces the target div, so re-assert the accessible wrapper
// (role=img + label + tabindex) on the node that ends up in the DOM, and make
// the injected SVG presentational — its nested graphics-symbol roles would
// otherwise be flagged as img-role nodes without alt text.
const tidy=root=>{const svg=root&&root.querySelector("svg");if(!svg)return;
  svg.setAttribute("aria-hidden","true");svg.setAttribute("focusable","false");
  svg.querySelectorAll("[role],[aria-roledescription]").forEach(n=>{
    n.removeAttribute("role");n.removeAttribute("aria-roledescription");});};
const views=[];let rt;
window.addEventListener("resize",()=>{clearTimeout(rt);rt=setTimeout(()=>{
  views.forEach(v=>{try{v.resize().run()}catch(e){}});},150);});
const go=()=>{
document.querySelectorAll("script.vs").forEach(s=>{const el=document.getElementById(
  s.dataset.target); if(!el) return; const holder=el.parentElement,
  label=el.getAttribute("aria-label"); try{ vegaEmbed(el, JSON.parse(
  s.textContent), {actions:false,renderer:"svg",
  config:{background:"transparent"}}).then(r=>{ views.push(r.view);
    const node=holder.querySelector(".vega-embed")||holder;
    node.setAttribute("role","img");node.setAttribute("aria-label",label);
    node.setAttribute("tabindex","0");tidy(node);})
  .catch(e=>console.warn("chart:",e));
  }catch(e){console.warn("spec:",e);}});};
  if(window.vegaEmbed) go(); else window.addEventListener("load",go);});</script>"""


def _peer_summary(spec: dict) -> tuple[str, int] | None:
    """A chart form designed for the phone: the ranked peers a reader can
    actually hold in mind — Connecticut, its immediate neighbours, and the
    extremes — with an explicit route to the full field. Returns (html,
    count) when the spec is a ranked peer chart; None for anything else
    (those keep the scroll-cropped desktop chart)."""
    try:
        rows = spec["data"]["values"]
    except (KeyError, TypeError):
        return None
    if (not isinstance(rows, list) or len(rows) < 12
            or not all(isinstance(r, dict) and isinstance(r.get("value"),
                        (int, float)) and isinstance(r.get("rank"), int)
                       for r in rows)):
        return None
    hi = [r for r in rows if r.get("highlight")]
    if len(hi) != 1 or min(r["value"] for r in rows) < 0:
        return None
    label_key = next((k for k in rows[0]
                      if k not in ("value", "rank", "highlight", "color")
                      and isinstance(rows[0][k], str)), None)
    if not label_key:
        return None
    rows = sorted(rows, key=lambda r: r["rank"])
    n = len(rows)
    ct = hi[0]["rank"]
    keep = sorted({1, n, ct} | {ct - 2, ct - 1, ct + 1, ct + 2})
    keep = [k for k in keep if 1 <= k <= n]
    biggest = max(r["value"] for r in rows)
    def _fmt(v: float) -> str:
        return f"{v:,.0f}" if abs(v) >= 1000 else f"{round(v, 1):g}"
    lis = []
    for r in rows:
        if r["rank"] not in keep:
            continue
        w = max(2, round(r["value"] / biggest * 100))
        cls = ' class="ct"' if r.get("highlight") else ""
        lis.append(
            f'<li{cls}><span class="pl">{_ESC(str(r[label_key]))}</span>'
            f'<span class="pb" style="width:{w}%"></span>'
            f'<span class="pv">{_fmt(r["value"])}</span></li>')
    return ('<ul class="peersum">' + "".join(lis) + '</ul>'), n


def viz(spec_json: str, el_id: str, *, label: str,
        caption: str | None = None) -> str:
    """Chart island with a text alternative (WCAG 1.1.1): the container carries
    role=img + aria-label and is keyboard-scrollable; an optional visible
    figcaption doubles as the takeaway line. The spec is normalized here —
    transparent background, no vega-internal ARIA (the wrapper already speaks),
    and a reserved min-height so SVG injection never shifts layout."""
    try:
        spec = json.loads(spec_json)
    except ValueError:
        spec = {}
    if spec:
        spec.setdefault("background", "transparent")
        spec["aria"] = False
        reserve = ""
        h = spec.get("height")
        if isinstance(h, (int, float)):
            pad = 58 if spec.get("title") else 16
            reserve = f' style="min-height:{int(h) + pad}px"'
        spec_json = json.dumps(spec, default=str)
    else:
        reserve = ' style="min-height:120px"'
    safe = (spec_json.replace("</", "<\\/")
            .replace("<!--", "<\\u0021--"))
    cap = f'<figcaption>{_ESC(caption)}</figcaption>' if caption else ''
    summary, n = (None, 0)
    if spec:
        built = _peer_summary(spec)
        if built:
            summary, n = built
    ctl = ""
    if summary:
        ctl = (f'<input type="checkbox" id="{el_id}-pp" class="peershow">'
               f'<label class="peersum-t" for="{el_id}-pp">'
               f'Show all {n} peers</label>')
    return (f'<figure class="vizwrap">{ctl}<div class="viz" id="{el_id}" role="img" '
            f'tabindex="0" aria-label="{_ESC(label)}"{reserve}></div>'
            f'{summary or ""}{cap}</figure>'
            f'<script type="application/json" class="vs" '
            f'data-target="{el_id}">{safe}</script>')


CSS_HASH = hashlib.sha1(CSS.encode()).hexdigest()[:8]
