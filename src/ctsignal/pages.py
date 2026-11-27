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
article p{margin:.5rem 0 1rem;color:var(--dim)}
article ul{margin:.5rem 0 1rem;padding-left:1.2rem}
article li{margin:.45rem 0;color:var(--dim)}
article strong{color:var(--ink)}
table{width:100%;border-collapse:collapse;margin:.5rem 0}
td{padding:.45rem 1rem .45rem 0;vertical-align:top;color:var(--dim);
  overflow-wrap:anywhere}
td:first-child{color:var(--dim);font-size:.78rem;text-transform:uppercase;
  letter-spacing:.08em;white-space:normal;padding-top:.6rem}
.masttab{table-layout:fixed}
.masttab td:first-child{width:34%;white-space:normal}
@media(max-width:720px){.masttab td:first-child{width:38%;font-size:.7rem;
  letter-spacing:.06em}}
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
    "masthead",
    "Masthead · CT Signal",
    "Who runs CT Signal: publisher, reporting desk, independence policy, and "
    "republication terms.",
    """<article class="wrap col">
<h1>Masthead</h1>
<p class="sub">One human, one pipeline, and the rules both follow.</p>
<table class="masttab">
<tr><td>Publisher &amp; editor</td><td>Alex V. Nesta — final word on corrections,
catalog changes, and anything with a decimal point.</td></tr>
<tr><td>Reporting desk</td><td>The pipeline. It picks questions from the news cycle and
fetches answers from the US Census Bureau, Data Commons, and the Connecticut Open Data
Portal. It has no access to press releases, vibes, or ad buyers.</td></tr>
<tr><td>Contact</td><td><a href="mailto:hello@ctsignal.org">hello@ctsignal.org</a>
— corrections, tips, and republication requests. Every message is read and logged.</td></tr>
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
<ol>
<li><strong>2026-10-06 — the unemployment answer contradicted itself.</strong>
The story card showed 5.1% (August, "2nd-highest of 9 peers", cached) while the
board tile showed 5.8% (July, 3rd-highest of 52). A partial upstream cohort had
outranked a complete print. The fix is in the code: cohort-consistent dates at
the source and a completeness rule in revalidation — a nine-peer answer can no
longer beat a 52-peer one. What readers saw for the day: two defensible numbers
and no explanation, which is exactly the kind of thing this page exists to
admit.</li>
<li><strong>2026-10-06 — we published a credential in our own failure log.</strong>
A bug in our Data Commons adapter on October 3 wrote a failed request URL —
API key attached — into <code>data/failures.log</code>, which the pipeline
commits publicly. The key was rotated the moment we caught it; the log is
scrubbed, and failure lines are now redacted before they are ever written. The
old key's value is a dead credential; the lesson is printed where you can
check it.</li>
<li><strong>2026-11-26 — a statewide total was counted as a town.</strong>
The equalized-assessment growth card said 170 towns; Connecticut has 169. The
source table's “Total” row is a statewide aggregate, not a municipality, and
one card had admitted it into the town list at rank 37. We now exclude
aggregate rows before ranking, so the card says 169 towns and the fake
<code>/town/total</code> page is gone. The finding is unchanged: Old Lyme still
led at +57.4%.</li>
</ol>
<p>That is a small list, not a claim of perfection —
<a href="https://github.com/alexvnesta/ct-signal">our failure log is public</a>
and longer than our corrections list on purpose: failures that stop a card
from publishing never needed correcting.</p>
</article>""")


_page(
    "privacy",
    "Privacy · CT Signal",
    "What CT Signal collects: no accounts, no cookies, no ad trackers; "
    "cookieless aggregate page counts and email only when you subscribe.",
    """<article class="wrap col">
<h1>Privacy</h1>
<p class="sub">No accounts, no cookies, no ad trackers.</p>

<h2>What we collect</h2>
<p>Nothing that identifies you personally. CT Signal has no login, no ad
network, no third-party tracking pixel, and no cross-site cookies. Reading
the site does not create a profile.</p>

<h2>Server logs</h2>
<p>Our host, Vercel, keeps ordinary request logs for security and reliability.
They are not joined to a reader identity and are not used to build an audience
profile.</p>

<h2>Cookieless measurement</h2>
<p>On production (<code>ctsignal.org</code>), we load two first-party Vercel
scripts: <strong>Vercel Speed Insights</strong> (Core Web Vitals: load speed,
layout stability, interaction latency) and <strong>Vercel Web Analytics</strong>
(aggregate, cookieless page-path counts and referrers so we know which town
and story pages readers actually use). Neither sets cookies, fingerprints
browsers, or tracks you across sites.</p>

<h2>The weekly email</h2>
<p>If you subscribe, Buttondown stores the email address you type and the
delivery record for the digest. You can unsubscribe in one click from any
issue. We do not sell, rent, or trade the list, and we do not add you to any
other list.</p>

<h2>What we do not do</h2>
<ul>
<li>No advertising trackers, retargeting pixels, or data brokers.</li>
<li>No cross-site profiling or fingerprinting.</li>
<li>No paid placement that changes a number or a ranking.</li>
</ul>

<h2>Contact</h2>
<p>Questions about this page, or a request to remove an email address:
<a href="mailto:hello@ctsignal.org">hello@ctsignal.org</a>. Corrections and
republication requests go to the same address.</p>
</article>""")

_page(
    "partner",
    "Partner & underwrite · CT Signal",
    "Underwrite CT Signal's Monday digest and 169-town desk, or license "
    "automated Connecticut town briefs and live chart embeds.",
    """<article class="wrap col">
<h1>Partner &amp; underwrite</h1>
<p class="sub">Clean local underwriting and automated Connecticut data tools —
strictly separated from the numbers.</p>

<p><strong>CT Signal</strong> publishes live, verifiable public data for all
169 Connecticut municipalities — property tax rates, recorded home sales,
housing permits, school spending, and Census benchmarks — with zero LLM-written
numbers and zero ad-tech trackers.</p>

<h2>1. Underwrite the Monday brief &amp; town desk</h2>
<p>Flat-rate quarterly underwriting (NPR / public-media style) for Connecticut
credit unions, regional lenders, real estate brokerages, clean-energy providers,
universities, and civic organizations who want to reach engaged Connecticut
homeowners, relocators, and municipal leaders.</p>
<ul>
<li><strong>What you get:</strong> A clearly labeled &ldquo;Underwritten by&rdquo;
acknowledgment in the <a href="/week">Monday weekly brief</a> and across our
<a href="/towns">169-town reference desk</a> and <a href="/compare">Compare towns</a>
tool.</li>
<li><strong>Zero ad tech:</strong> Plain text and link — no tracking pixels,
no programmatic banners, no third-party cookies.</li>
</ul>

<h2>2. Newsroom embeds &amp; co-branded town briefs</h2>
<p>Built for Connecticut newsrooms, hyperlocal newsletters, regional Councils
of Governments, civic nonprofits, and real estate relocation teams:</p>
<ul>
<li><strong>Live story embeds &amp; CSVs:</strong> Every story and indicator
file offers copy-paste chart embeds, 2&times; PNG graphics, and raw CSV receipts.
Free for non-commercial republication with attribution.</li>
<li><strong>White-label briefs &amp; custom feeds:</strong> Automated weekly
briefs, custom multi-town packets, or scheduled data feeds tailored to your
region or readership.</li>
</ul>

<h2>Editorial firewall</h2>
<p>Underwriting pays for infrastructure and coverage depth — never outcomes.
<strong>No partner or sponsor can add, remove, round, or influence any dataset,
ranking, chart, or correction.</strong> Every methodology rule and
<a href="/corrections">correction log</a> stays public on GitHub.</p>

<h2>Start a conversation</h2>
<p>Write to <a href="mailto:hello@ctsignal.org?subject=CT%20Signal%20partnership">hello@ctsignal.org</a>
with a sentence about what you are looking for — underwriting, a newsroom
reprint, or a custom town data brief.</p>
</article>""")

def write_pages() -> None:
    for slug, (title, desc, body) in _PAGES.items():
        page = theme.page(title=title, desc=desc, path=f"/{slug}",
                          body=_PAGE_CSS + body, compact=True)
        (config.ROOT / f"{slug}.html").write_text(page)
    (config.ROOT / "404.html").write_text(theme.page(
        title="Page not found · CT Signal",
        desc="This page doesn't exist (yet). The board is always moving.",
        path="/404", compact=True,
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

    # What the wire asked that no tracked dataset can answer — measured,
    # not written: the desk reads everything, and admits what it cannot
    # yet cover. Five lines, counts only, refreshed every publish.
    try:
        import datetime as _dt
        _ledger = json.loads((config.ROOT / "data" /
                              "ledger.json").read_text()).get("entries", {})
        _cut = (_dt.datetime.now(_dt.timezone.utc)
                - _dt.timedelta(days=7)).timestamp()
        _recent = [h for h in _ledger.values()
                   if (h.get("pub") or 0) > _cut]
        _kw_sets = [i.get("keywords") or []
                    for sec in ("stackup", "local", "national")
                    for i in questions.load_catalog().get(sec, [])]
        _buckets = {}
        for _h in _recent:
            _t = _h["title"].lower()
            # Strong must be per-indicator: two weak phrases from two
            # different cards do not together make one answerable question.
            if any(questions._strong_enough(
                       questions._keyword_hits(_t, kws)) for kws in _kw_sets):
                continue
            for _name, _terms in (
                    ("politics & elections", ("trump", "senate", "election",
                     "midterm", "governor", "campaign", "debate")),
                    ("justice & courts", ("police", "court", "trial",
                     "charged", "arrest", "prison", "execut")),
                    ("weather & utilities", ("hurricane", "storm", "outage",
                     "power", "flood", "weather")),
                    ("schools & education", ("school", "district",
                     "student", "teacher", "education"))):
                if any(w in _t for w in _terms):
                    _buckets[_name] = _buckets.get(_name, 0) + 1
                    break
        _top = sorted(_buckets.items(), key=lambda kv: -kv[1])[:3]
        if _top:
            _gap = " \u00b7 ".join(f"{esc(k)} ({v})" for k, v in _top)
            _gapline = (
                f'<p class="sub">This week the wire also asked about '
                f'{_gap} \u2014 {len(_recent)} headlines read in 7 days, '
                f'and no tracked dataset answers those yet. When one '
                f'arrives, the desk covers it.</p>')
        else:
            _gapline = ""
    except (OSError, json.JSONDecodeError, KeyError):
        _gapline = ""

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
{_gapline}
<p class="meta">The endpoint check runs from the validate script and is
committed with the repo; a failing chip means the pipeline is answering from
labeled cached/fallback data until it recovers.</p>
{_inv.table()}
</article>"""


_page("sources", "Data sources · CT Signal",
      "Every dataset CT Signal queries, with live endpoint health.",
      _sources_body())
