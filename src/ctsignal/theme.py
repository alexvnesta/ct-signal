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

from . import config

_ESC = html.escape

# ---------------------------------------------------------------- palette ---
# Dark editorial: ink navy background, warm orange mast accent, green answers,
# blue links. Verified AA+ on every surface (see CONTRAST note in CSS header).

CSS = """
/* Contrast (WCAG 2.2 AA, verified): ink #e9eef4/bg 15.9 · dim #93a7b9/bg 7.5
   faint #7d91a5/bg 5.7 on panel 5.2 · acc #f2a65a/bg 9.2 · blue #7fb4ff/bg 8.7
   ok #8fd6a9/panel 10.0 · badge #cfdcea/panel2 11.2 — all >= 4.5:1 normal text */
@font-face{font-family:"Newsreader";font-style:normal;font-weight:700;
  font-display:swap;src:url("/assets/fonts/newsreader-700-latin.woff2")
  format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,
  U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,
  U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
:root{
  --bg:#0e141b; --bg2:#0a0f14; --panel:#151d27; --panel2:#1a2531; --line:#28394a;
  --ink:#e9eef4; --dim:#93a7b9; --faint:#7d91a5;
  --acc:#f2a65a; --blue:#7fb4ff; --ok:#8fd6a9; --warn:#e5c07b;
  --serif:"Newsreader","Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
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
/* in-content links carry a non-color cue (WCAG 1.4.1); brand + nav opt out */
.meta a, .breadcrumb a, .provenance a, .footgrid a, .how a, .card a
{text-decoration:underline;text-underline-offset:3px;
  text-decoration-color:inherit}
::selection{background:#f2a65a44}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:3px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:1rem;top:.6rem;z-index:20;background:var(--acc);color:#0a0f14;
  padding:.5rem .9rem;border-radius:8px;font-weight:700;text-decoration:none}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:
  hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:
  none!important;scroll-behavior:auto!important}}
.wrap{max-width:var(--wrap);margin:0 auto;padding:0 1.2rem}
.col{max-width:var(--col)}
main{display:block}

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
  min-height:44px;display:inline-flex;align-items:center;
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
.more{font-weight:700;font-size:.9rem;display:inline-block;padding:10px 0;min-height:44px}
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
/* width:"container" measures the .vega-embed node, which vega-embed's own
   stylesheet makes inline-block; inside a flex tile that shrinks to the
   (0-wide) svg and collapses. Force the measure chain to fill the tile. */
.tile .viz,.tile .viz .vega-embed,.tile .viz .chart-wrapper{display:block;width:100%}
.chip{align-self:flex-start;background:var(--panel2);color:#cfdcea;border-radius:99px;
  padding:.1rem .65rem;font-size:.74rem}

.klink{color:inherit;text-decoration:none;border-bottom:1px dotted currentColor}
.klink:hover{border-bottom-style:solid}
.sponsor{display:flex;flex-wrap:wrap;gap:.6rem 1.2rem;align-items:center;
  justify-content:space-between;border:1px dashed var(--line);border-radius:10px;
  padding:.7rem 1rem;margin-top:1rem;background:var(--panel)}
.sponsor p{margin:0;color:var(--dim);font-size:.9rem}
.sponsor a{color:var(--acc);font-weight:700;font-size:.9rem}
details.embed{border:1px solid var(--line);border-radius:10px;background:var(--panel);
  padding:.6rem 1rem;margin:1rem 0}
details.embed summary{cursor:pointer;font-weight:700;font-size:.9rem;color:var(--dim)}
details.embed summary:hover{color:var(--ink)}
details.embed textarea{width:100%;box-sizing:border-box;background:var(--bg2);
  color:var(--ok);border:1px solid var(--line);border-radius:6px;padding:.5rem;
  font:.8rem/1.5 var(--mono);margin-top:.6rem}
.legend{color:var(--faint);font-size:.8rem;margin:1rem 0 0}

/* ------------------------------------------------------------- signals --- */
ol.signals{list-style:none;margin:0;padding:0}
li.sig{border-bottom:1px solid var(--line);padding:1.3rem 0}
li.sig:first-child{border-top:1px solid var(--line)}
li.sig h3{font:700 1.35rem/1.3 var(--serif);margin:.35rem 0 .4rem}
li.sig h2{font:700 1.35rem/1.3 var(--serif);margin:.35rem 0 .4rem}
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
figure.vizwrap{margin:0}
figure.vizwrap figcaption{color:var(--faint);font-size:.8rem;margin-top:.4rem;
  line-height:1.45}
.viz{overflow-x:auto}
.viz:focus-visible{outline:2px solid var(--acc);outline-offset:4px;border-radius:6px}
.viz .vega-embed .chart-wrapper{margin:0}
.viz .vega-embed details summary{color:var(--dim)}
code{background:var(--panel2);color:#cfdcea;padding:.1rem .35rem;border-radius:4px;
  font:.85em/1.5 var(--mono);word-break:break-all}
.provenance a{color:var(--blue)}

/* --------------------------------------------------------------- footer --- */
footer.site{border-top:1px solid var(--line);background:var(--bg2);margin-top:2.5rem;
  padding:1.8rem 0 2.2rem}
.footgrid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:1.5rem}
.footgrid h2{margin:.2rem 0 .6rem;color:var(--dim);font-size:.74rem;
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
        + f'</div><nav class="sitebar wrap" aria-label="Primary">{_NAV}</nav></header>'
    )


def footer() -> str:
    email = config.CONTACT_EMAIL
    year = dt.date.today().year
    return f"""<footer class="site"><div class="wrap footgrid">
<div><h2>CT&nbsp;<span style="color:var(--acc)">⚡</span>&nbsp;Signal</h3>
<p>An automated newsroom for Connecticut: the news cycle picks the question,
public data answers it — every number fetched from a named dataset, never typed
by hand.</p><p><a href="mailto:{email}">{email}</a></p></div>
<div><h2>Sections</h2><ul>
<li><a href="/">The board</a></li>
<li><a href="/#signals">Latest questions</a></li>
<li><a href="/feed.xml">RSS feed</a></li>
<li><a href="https://github.com/alexvnesta/ct-signal/tree/master/archive">Card archive</a></li></ul></div>
<div><h2>Newsroom</h2><ul>
<li><a href="/about">About</a></li>
<li><a href="/methodology">How we work</a></li>
<li><a href="/masthead">Masthead</a></li>
<li><a href="/corrections">Corrections</a></li>
<li><a href="https://github.com/alexvnesta/ct-signal">Source &amp; failure logs</a></li>
</ul></div></div>
<div class="wrap colophon"><span>© {year} CT Signal · Independent automated newsroom</span>
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
                        "cycle is already asking. Every number fetched, "
                        "never written.",
         "inLanguage": "en-US", "publisher": {"@id": f"{config.SITE_URL}/#org"}},
        {"@type": "Organization", "@id": f"{config.SITE_URL}/#org",
         "name": "CT Signal", "url": f"{config.SITE_URL}/",
         "email": config.CONTACT_EMAIL,
         "logo": dict(_ORG["logo"]),
         "sameAs": ["https://github.com/alexvnesta/ct-signal"]},
    ]}


def article_json_ld(*, card_id: str, headline: str, description: str,
                    published: str, section: str,
                    image: str | None = None) -> dict:
    url = f"{config.SITE_URL}/story/{card_id}"
    return {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "@id": f"{url}#article",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": headline, "description": description,
        "image": [image or f"{config.SITE_URL}/assets/og-cover.png"],
        "datePublished": published, "dateModified": published,
        "author": {"@type": "Organization", "name": "CT Signal",
                   "url": f"{config.SITE_URL}/"},
        "publisher": dict(_ORG),
        "articleSection": section, "inLanguage": "en-US",
        "isAccessibleForFree": True,
    }


def head(*, title: str, desc: str, path: str, og_type: str = "website", preload_font: bool = True,
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
              f'{blob.replace("</", "<\\/")}</script>')
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
<meta property="og:image:alt" content="{_ESC(img_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@ctsignal">
<meta name="twitter:title" content="{_ESC(og_title or title)}">
<meta name="twitter:description" content="{_ESC(og_desc or desc)}">
<meta name="twitter:image" content="{img}">
<meta name="twitter:image:alt" content="{_ESC(img_alt)}">
{art}<meta name="theme-color" content="#0e141b">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/assets/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="CT Signal"
 href="{config.SITE_URL}/feed.xml">
<link rel="alternate" type="application/feed+json" title="CT Signal (JSON)"
 href="{config.SITE_URL}/feed.json">
{"" if not preload_font else '<link rel="preload" href="/assets/fonts/newsreader-700-latin.woff2" as="font" type="font/woff2" crossorigin>'}
<link rel="stylesheet" href="/assets/site.css">
{ld}"""


def page(*, title: str, desc: str, path: str, body: str, **kw) -> str:
    h = head(title=title, desc=desc, path=path, **kw)
    return (f'<!doctype html>\n<html lang="en"><head>\n{h}\n</head>\n<body>\n'
            f'<a class="skip" href="#main">Skip to content</a>\n'
            f'{header()}\n<main id="main">\n{body}\n</main>\n{footer()}\n'
            f'{VEGA_LOAD}\n</body></html>\n')


# Inline JSON spec islands + one loader keep charts dependency-light and work
# identically on the board and story pages.
VEGA_LOAD = """<script defer src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script defer src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script defer src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
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
    safe = spec_json.replace("</", "<\\/")
    cap = f'<figcaption>{_ESC(caption)}</figcaption>' if caption else ''
    return (f'<figure class="vizwrap"><div class="viz" id="{el_id}" role="img" '
            f'tabindex="0" aria-label="{_ESC(label)}"{reserve}></div>{cap}</figure>'
            f'<script type="application/json" class="vs" '
            f'data-target="{el_id}">{safe}</script>')
