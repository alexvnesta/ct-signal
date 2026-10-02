"""Static editorial pages (About / Methodology / Masthead / Corrections).

Copy lives here as page bodies; theme provides the chrome, so these pages
always match the rest of the site and are regenerated (and diffable) with
every pipeline write.
"""
from __future__ import annotations

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

<h2>Who runs it</h2>
<p>Built by <strong>Alex V. Nesta</strong> at Hack for Humanity (UConn School of Business,
Challenge 4: CTData.org, Made Conversational), and operating as an independent automated
newsroom since. The full pipeline, failure logs, and every card ever published are
<a href="https://github.com/alexvnesta/ct-signal">in public on GitHub</a>.</p>
</article>""")

_page(
    "methodology",
    "Methodology · CT Signal",
    "How CT Signal works: listen, choose from a closed catalog, fetch numbers from "
    "named public APIs, publish every 15 minutes — and the honesty rules in between.",
    """<article class="wrap col">
<h1>How CT Signal works</h1>
<p class="sub">The whole system in four steps — and the rules that keep us honest.</p>

<h2>1 · Listen</h2>
<p>We watch Connecticut feeds (CT Mirror, Google News CT) and national feeds (NYT, NPR,
PBS), plus a civic calendar (school year, tax deadlines, census releases). Headlines are
deduplicated and tracked by age.</p>

<h2>2 · Choose the question</h2>
<p>A language model reads the headlines against our <strong>closed catalog</strong> of
validated indicators and proposes only questions the catalog can actually answer.
News arrives as language; data speaks in dataset codes — reading intent is the AI's
entire job. An unmatched story produces nothing. If the model is unavailable, a
keyword heuristic falls back; the catalog is the same either way.</p>

<h2>3 · Fetch, never write</h2>
<p><strong>No number on this site was written or rounded by a language model.</strong>
Answers come from executed queries against Data Commons and the Connecticut Open Data
Portal (Socrata), dry-run validated before publication. Every story page shows the
dataset link and the literal query.</p>

<h2>4 · Publish</h2>
<p>Cards land on the board, get their own permalink story page, the RSS feed, and the
archive — every 15 minutes, via a scheduled job whose commits are the audit trail.
If a fetch fails, the card falls back to labeled <code>cache</code> or doesn't run.
We fail by absence, never by invention.</p>

<h2>The honesty rules</h2>
<ul>
<li><strong>Ranks use all 52 peers</strong> (50 states + DC + PR) and are phrased human-first:
"3rd safest", "10th lowest poverty" — never a bare "#50 of 52".</li>
<li><strong>Data dates are printed on every card.</strong> ACS is annual, employment is
monthly; the card tells you which vintage you're reading. The card answers the news
question; the date tells you how current the answer is.</li>
<li><strong>Unflattering cards publish too</strong> — including ones with caveats printed
on the card (e.g., revaluation-driven grand-list jumps).</li>
<li><strong>Our failure log is public:</strong> endpoint failures, dead APIs, and portal
quirks are documented in the repo, not hidden.</li>
</ul>

<h2>Corrections</h2>
<p>Found something wrong? <a href="mailto:hello@ctsignal.org">Email us</a> — we annotate
the story, re-publish, and the change is visible in the commit history. See
<a href="/corrections">the corrections policy</a>.</p>
</article>""")

_page(
    "masthead",
    "Masthead · CT Signal",
    "Who runs CT Signal: publisher, reporting desk, independence policy, and "
    "republication terms.",
    """<article class="wrap col">
<h1>Masthead</h1>
<table>
<tr><td>Publisher &amp; editor</td><td>Alex V. Nesta — final word on corrections,
catalog changes, and anything with a decimal point.</td></tr>
<tr><td>Reporting desk</td><td>The pipeline. It picks questions from the news cycle and
fetches answers from Data Commons and the Connecticut Open Data Portal. It has no
access to press releases, vibes, or ad buyers.</td></tr>
<tr><td>Contact</td><td><a href="mailto:hello@ctsignal.org">hello@ctsignal.org</a>
— corrections, tips, and republication requests.</td></tr>
<tr><td>Independence</td><td>CT Signal runs on free-tier public infrastructure and takes
no paid placement. No dataset, card, or position is influenced by sponsorship.</td></tr>
<tr><td>Republication</td><td>Story pages and charts may be republished free with
attribution and a link to the original permalink. Credit the underlying dataset too —
it did the work.</td></tr>
<tr><td>Origin</td><td>Built at Hack for Humanity (UConn School of Business),
Challenge 4: CTData.org, Made Conversational. Code, logs, and history:
<a href="https://github.com/alexvnesta/ct-signal">github.com/alexvnesta/ct-signal</a>.</td></tr>
</table>
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
<a href="/methodology">our failure log is public</a> and longer than our corrections
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
