"""Static editorial pages (About / Methodology / Masthead / Corrections).

Copy lives here as page bodies; theme provides the chrome, so these pages
always match the rest of the site and are regenerated (and diffable) with
every pipeline write.
"""
from __future__ import annotations

import html
import json

from . import config, theme

_PAGES: dict[str, tuple[str, str, str]] = {}  # slug -> (title, desc, body)


def _page(slug: str, title: str, desc: str, body: str) -> None:
    _PAGES[slug] = (title, desc, body)


_PAGE_CSS = """
<style>
article h1{font:700 clamp(1.7rem,4vw,2.3rem)/1.15 var(--serif);margin:.4rem 0 .3rem}
article .sub{color:var(--dim);font-size:.9rem;margin:0 0 1.6rem}
article h2{font:800 1rem/1.3 var(--sans);color:var(--acc);margin:2rem 0 .5rem;
  text-transform:uppercase;letter-spacing:.1em}
article p{margin:.5rem 0 1rem;color:#c8d4de}
article ul{margin:.5rem 0 1rem;padding-left:1.2rem}
article li{margin:.45rem 0;color:#c8d4de}
article strong{color:var(--ink)}
table{border-collapse:collapse;margin:.5rem 0}
td{padding:.45rem 1.4rem .45rem 0;vertical-align:top;color:#c8d4de}
td:first-child{color:var(--dim);font-size:.78rem;text-transform:uppercase;
  letter-spacing:.08em;white-space:nowrap;padding-top:.6rem}
</style>
"""

_page(
    "about",
    "About · CT Signal",
    "CT Signal is an automated data desk for Connecticut: real stories, real "
    "URLs, real receipts — every answer fetched from a named public dataset.",
    """<article class="wrap col">
<h1>About CT Signal</h1>
<p class="sub">An automated data desk for Connecticut.</p>
<p><strong>CT Signal is an automated data desk for Connecticut.</strong> When a story
breaks, we check what Connecticut's public data says about it — and publish the answer
within minutes, with the query attached.</p>

<h2>What we are</h2>
<p>A pipeline that behaves like a newsroom: real stories get real URLs, real timestamps,
real receipts. Every page on this site was produced the same way: a news story raised a
question, the closed catalog of validated indicators matched it, a public dataset answered
it. The ranking, the chart, the date — all fetched from source APIs.</p>

<h2>What we are not</h2>
<p>We don't have opinions, predictions, or sponsored posts. We don't accept stories we
can't verify against a named dataset. If we can't answer a question with fetched data,
we publish nothing — a missing card is our version of editorial restraint.</p>

<h2>Why it exists</h2>
<p>Connecticut has excellent public data and almost no way for a normal reader to meet it
at the moment they care. CTData Collaborative staffs a manual "Ask a Data Question"
helpline; the demand is real and the bottleneck is arrival time. CT Signal answers the
questions the news cycle is already asking, so the data shows up when the conversation does.</p>

<h2>How the numbers get here</h2>
<p>Headlines raise the question; a language model matches the moment to a
<strong>closed catalog</strong> of validated indicators; numbers come back from executed
queries against the US Census Bureau, Data Commons, and the Connecticut Open Data
Portal. <strong>No number on this site was written or rounded by a language model.</strong>
Every story page carries the dataset link and the literal query. If a fetch fails, the
card falls back to labeled cache or does not run:
<a href="https://github.com/alexvnesta/ct-signal">the failure log is public</a> and the
commits are the audit trail. We fail by absence, never by invention.</p>

<h2>Who runs it</h2>
<p>Built by <strong>Alex V. Nesta</strong> at Hack for Humanity (UConn School of Business,
Challenge 4: CTData.org, Made Conversational), and operating as an independent automated
newsroom since. The full pipeline, failure logs, and every card ever published are
<a href="https://github.com/alexvnesta/ct-signal">in public on GitHub</a>.</p>
</article>""")

_page(
    "corrections",
    "Corrections · CT Signal",
    "CT Signal corrects in public: how corrections work, and every correction to date.",
    """<article class="wrap col">
<h1>Corrections</h1>
<p class="sub">We are wrong in public, on this page, with receipts.</p>

<h2>How corrections work</h2>
<ul>
<li>Email <a href="mailto:hello@ctsignal.org">hello@ctsignal.org</a> with the story URL.
Any factual error — wrong question matched, wrong framing, stale data presented as new —
is a correction.</li>
<li>The story page is annotated and re-published; the original card JSON stays in the
<a href="https://github.com/alexvnesta/ct-signal">archive and commit history</a>,
so the correction is diffable like code — because it is.</li>
<li>If a whole indicator class proves unreliable, we retire it from the catalog and say
so here, not quietly.</li>
</ul>

<h2>How this differs from a normal newsroom</h2>
<p>Most errors here are mechanical (an upstream dataset revised, an endpoint changed
shape), so most fixes are automatic on the next fetch. What we list below are the ones
where a reader saw something we'd have kept serving.</p>

<h2>Corrections to date</h2>
<p>None yet. That is a small sample, not a claim of perfection —
<a href="https://github.com/alexvnesta/ct-signal">our failure log is public</a> and longer than our corrections
list on purpose: failures that stop a card from publishing never needed correcting.</p>
</article>""")


def write_pages() -> None:
    for slug, (title, desc, body) in _PAGES.items():
        page = theme.page(title=title, desc=desc, path=f"/{slug}",
                          body=_PAGE_CSS + body)
        (config.ROOT / f"{slug}.html").write_text(page)
    (config.ROOT / "404.html").write_text(theme.page(
        title="Page not found · CT Signal",
        desc="This page doesn't exist (yet). The board is always moving.",
        path="/404",
        body=_PAGE_CSS + """<article class="wrap col">
<h1>404 — off the board</h1>
<p class="sub">This page doesn't exist. Cards keep their permalinks for life,
so this link either predates or postdates the record.</p>
<p><a class="more" href="/">← Back to the Connecticut board</a></p>
</article>"""))


def _sources_body() -> str:
    from . import feeds, inventory as _inv, questions

    esc = html.escape
    try:
        report = json.loads((config.ROOT / "data" /
                             "validation_report.json").read_text())
    except (OSError, json.JSONDecodeError):
        report = {}

    def chip(status: str) -> str:
        if status.startswith("ok"):
            return f'<span style="color:var(--ok)">&#9679; verified</span>'
        if status.startswith("thin"):
            return f'<span style="color:var(--acc)">&#9679; {esc(status)}</span>'
        if status.startswith("error"):
            return f'<span style="color:#e5645f">&#9679; endpoint failing</span>'
        return '<span style="color:var(--dim)">&#9679; not checked yet</span>'

    rows = []
    for ind in questions.load_catalog().get("stackup", []):
        st = report.get(ind["id"], {}).get("status", "")
        if ind.get("census1yr"):
            src = (f'<a href="https://api.census.gov/data/2024/acs/acs1">'
                   f'US Census Bureau &middot; ACS 1-Year &middot; '
                   f'{esc(ind["census1yr"].get("table", ""))}</a>')
        else:
            src = (f'<a href="https://datacommons.org/data/commons/{ind["dcid"]}">'
                   f'Data Commons &middot; {esc(ind["dcid"])}</a>')
        rows.append(
            f'<tr><td>{esc(ind["title"])}<br><span class="meta">'
            f'{src}</span></td>'
            f'<td style="text-align:right">{chip(st)}</td></tr>')
    rows.append(
        '<tr><td>Grand list by town (property tax base)<br><span class="meta">'
        '<a href="https://data.ct.gov/d/webp-fgt3">CT Open Data Portal '
        '&middot; webp-fgt3</a></span></td>'
        '<td style="text-align:right">'
        '<span style="color:var(--dim)">&#9679; live every cycle</span></td></tr>')
    rows.append(
        '<tr><td>The national weather Connecticut lives in &mdash; hiring, '
        'quitting, layoffs, jobless duration, participation, labor’s share'
        '<br><span class="meta"><a href="https://fred.stlouisfed.org/series/JTSHIR">'
        'US Bureau of Labor Statistics, redistributed as FRED</a> '
        '&middot; keyless CSV, no account</span></td>'
        '<td style="text-align:right">'
        '<span style="color:var(--dim)">&#9679; fetched whenever a national '
        'card asks</span></td></tr>')

    trig = "".join(
        f'<li style="padding:.3rem 0">{esc(feeds._source_name(u))} &middot; '
        f'<span class="meta"><a href="{esc(u)}">{esc(u)}</a></span></li>'
        for u in list(config.CT_FEEDS) + list(config.NATIONAL_FEEDS))
    return f"""<article class="wrap col">
<div class="label">Data sources</div>
<h1 style="font:700 clamp(1.7rem,4vw,2.3rem)/1.15 var(--serif);margin:.4rem 0 .3rem">
What we watch</h1>
<p class="sub">Every dataset the desk queries, with its last endpoint check.
Status chips reflect the committed validation report &mdash; when an upstream
endpoint degrades, you see it here first, not in a silent gap.</p>
<table class="towntab"><tbody>{''.join(rows)}</tbody></table>
<h2 style="font:700 1.15rem/1.3 var(--serif);margin:1.4rem 0 .3rem">What triggers a question</h2>
<p class="sub">Live news feeds scanned every cycle; a question is only asked
when a tracked dataset can answer it.</p>
<ul style="list-style:none;padding:0">{trig}</ul>
<p class="meta">The endpoint check runs from the validate script and is
committed with the repo; a failing chip means the pipeline is answering from
labeled cached/fallback data until it recovers.</p>
{_inv.table()}
</article>"""


_page("sources", "Data sources · CT Signal",
      "Every dataset CT Signal queries, with live endpoint health.",
      _sources_body())
