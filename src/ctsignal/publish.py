"""Homepage export: the Connecticut board + the rolling feed of answered
questions, server-rendered so crawlers, RSS readers, and link previews all see
real content. Charts embed as JSON islands; the vega loader in theme upgrades
them to SVG progressively.
"""
from __future__ import annotations

import datetime as dt
import html
import json

from . import config, theme, util

_ESC = html.escape


def _parse(ts: str) -> dt.datetime:
    return util.parse_ts(ts)


def ago(iso: str, now: dt.datetime) -> str:
    """Honest freshness as machine-readable <time>: relative while fresh,
    absolute date past a day, always the publish wall clock in ET. 'now' is
    the publish moment, never the card's own stamp — a lead that has not
    been replaced can never claim 'just now' hours later."""
    d = _parse(iso)
    s = max(0.0, (now - d).total_seconds())
    when = util.clock(util.et(d))
    if s < 90:
        label = when
    elif s < 5400:
        label = f"{round(s / 60)} min ago · {when}"
    elif s < 86400:
        label = f"{round(s / 3600)} h ago · {when}"
    else:
        label = f"{util.et(d):%b %-d} · {when}"
    return f'<time datetime="{iso}">{label}</time>'


def _trigger_line(card: dict) -> str:
    prefix, title = theme.trigger_parts(card)
    return (f'<span class="trig"><span class="srclabel">Source:</span> '
            f'{prefix}{title}</span>')


def _kicker(card: dict, when: str) -> str:
    cache = ' <span class="badge">cache</span>' if card.get("cache") else ""
    return (f'{_ESC(card["topic"])} · {_ESC(card["stream"])} desk'
            f'{cache} · {when}')


def home_html(cards: list[dict], board: dict) -> str:
    # Freshness is measured against the publish moment, never against the
    # lead's own stamp (an unreplaced lead must not claim 'just now' later).
    now = dt.datetime.now(dt.timezone.utc)
    if cards:
        now = max(now, _parse(cards[0]["generated_at"]))

    hero = ""
    if cards:
        c = cards[0]
        # The lead's artwork is its own chart — receipts as art, one shared
        # caption with the story page. Cards without a chart keep a text hero.
        heroviz = ""
        if c.get("chart"):
            from . import newsroom
            vdesc, vlabel = newsroom.chart_intro(c)
            heroviz = theme.viz(newsroom._spec_json(c["chart"]), "heroviz",
                                label=vlabel, caption=vdesc)
        hero = f"""<div class="wrap"><div class="hero">
<div class="kicker">Today's lead · {_ESC(c["topic"])} · {_ESC(c["stream"])} desk</div>
<h1><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h1>
<p class="lede">{_ESC(c["answer_text"])}</p>
{heroviz}
<div class="meta">{_trigger_line(c)}<span class="when">
{ago(c["generated_at"], now)}</span></div>
<p><a class="more" href="/story/{c["id"]}">Read the full story — with the chart
and the exact query →</a></p>
</div></div>"""

    tiles = ""
    for i, t in enumerate(board.get("tiles", [])):
        pos = str(t.get("rank_label") or f'#{t["rank"]}')
        label = (f'{t["title"]}: Connecticut at {_ESC(str(t["value"]))} — '
                 f'{_ESC(pos)} of {t["n"]} peers')
        tiles += f"""<div class="tile">
<div class="tname">{_ESC(t["title"])}</div>
<div class="val">{_ESC(str(t["value"]))}</div>
{theme.viz(json.dumps(t["strip"], default=str), f"strip{i}", label=label)}
<span class="chip">{_ESC(pos)} of {_ESC(str(t["n"]))} peers · data {_ESC(str(t["date"]))}</span>
</div>"""

    from . import newsroom
    signals = ""
    for c in cards[1:] if cards else []:
        # The story's own cover art is the card's picture: it regenerates
        # with the card, so the picture can never disagree with the answer
        # (an image of yesterday's number is the classic news-site lie).
        cover = ""
        if newsroom._cover_path(c):
            cover = (f'<a href="/story/{c["id"]}" tabindex="-1" aria-hidden="true">'
                     f'<img class="sigart" src="/assets/story-{c["id"]}.png" '
                     f'width="1200" height="630" loading="lazy" alt=""></a>')
        signals += f"""<li class="sig">{cover}<div class="sigpad">
<div class="kicker">{_kicker(c, ago(c["generated_at"], now))}</div>
<h3><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h3>
<p class="answer">{_ESC(c["answer_text"])}</p>
<div class="meta">{_trigger_line(c)}
<a class="more" href="/story/{c["id"]}">the story with receipts →</a></div>
</div></li>"""

    fixture = any("(fixture)" in (c["headline"].get("source") or "")
                  for c in cards)
    help_ = ("Every question here is raised by a headline first. These cards "
             "run on labeled demo fixtures; each fresh cycle replaces them "
             "with live receipts."
             if fixture else
             "Every question below was raised by a real headline first.")
    signals_html = f"""<section id="signals"><div class="wrap col">
<div class="sechead"><h2>Latest questions</h2>
<p class="sechelp">{help_}</p></div>
<ol class="signals">{signals}</ol>
</div></section>"""

    n_peers = (board.get("tiles") or [{}])[0].get("n", "52")
    body = f"""{hero}
<section><div class="wrap">
<div class="sechead"><h2>The Connecticut board</h2>
<p class="sechelp">Where we stand among our peers — refreshed with every data
vintage.</p></div>
<div class="tiles">{tiles}</div>
<p class="legend">Peer sets are the 50 states and Washington DC (plus Puerto
Rico where the source covers it); the count in each answer is that indicator's
own source. Charts plot every peer; rank 1 is the highest value, and chips say
“highest”, “lowest” or a plain-language superlative — never a bare number.
Each tile prints the vintage of its own dataset; older vintages are the honest
limit of annual surveys, not a lag in the pipeline.</p>
</div></section>

<div class="wrap"><aside class="sponsor">
<p><strong>Independent · automated · reader-supported.</strong> No trackers,
no ads, no cookies — public data with the receipts attached.</p>
<p><a href="mailto:{config.CONTACT_EMAIL}?subject=Board%20sponsorship">Sponsor the board &rarr;</a></p>
</aside></div>

{signals_html}

<section><div class="wrap">
<div class="sechead"><h2>How this newsroom works</h2>
<p class="sechelp">Four steps, every 15 minutes, in public.</p></div>
<div class="how">
<div class="step"><b>1 · Listen</b><p>CT and national feeds plus a civic
calendar. <strong>Headlines pick the topic.</strong> An unmatched story
produces nothing.</p></div>
<div class="step"><b>2 · Choose</b><p>A language model matches the moment to a
<strong>closed catalog</strong> of validated indicators — questions it can
actually answer.</p></div>
<div class="step"><b>3 · Fetch</b><p><strong>No number here was written by a
language model.</strong> Ranks come from executed queries against Data Commons
and data.ct.gov.</p></div>
<div class="step"><b>4 · Publish</b><p>Board, story page, RSS, archive —
every 15 minutes. <strong>The git history is the audit trail</strong>, and the
failure log ships with it.</p></div>
</div>
</div></section>"""

    return theme.page(
        title="CT Signal — Connecticut's automated data desk",
        desc="Connecticut's automated newsroom: the news cycle picks the "
             "question, public data answers it. Charts, rankings, and the "
             "query behind every number.",
        path="/", body=body,
        og_title="CT Signal — Connecticut's automated data desk",
        json_ld=theme.site_json_ld())


def publish(cards: list[dict], board: dict | None = None) -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    feed = {
        "generated_at": cards[0]["generated_at"] if cards else None,
        "cards": cards,
    }
    util.write_json(config.OUTPUT_DIR / "cards.json", feed)
    if board is not None:
        util.write_json(config.OUTPUT_DIR / "board.json", board)
    util.atomic_write_text(config.OUTPUT_DIR / "index.html",
                           home_html(cards, board or {}))
    from . import newsroom

    newsroom.write_all(cards)
