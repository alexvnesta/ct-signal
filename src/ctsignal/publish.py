"""Homepage export: the Connecticut board + the rolling feed of answered
questions, server-rendered so crawlers, RSS readers, and link previews all see
real content. Charts embed as JSON islands; the vega loader in theme upgrades
them to SVG progressively.
"""
from __future__ import annotations

import datetime as dt
import hashlib
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

    # Broadsheet front: lead story with its chart as the artwork, a column
    # of second stories, a dated rail of the rest. The grid is populated
    # top-down from the feed, so the layout can never disagree with it.
    lead = ""
    sec2 = ""
    rail = ""
    if cards:
        from . import newsroom
        c = cards[0]
        heroviz = ""
        if c.get("chart"):
            vdesc, vlabel = newsroom.chart_intro(c)
            heroviz = theme.viz(newsroom._spec_json(c["chart"]), "heroviz",
                                label=vlabel, caption=vdesc)
        lead = f"""<article class="lead">
<span class="kicker">Today's lead · {_ESC(c["topic"])} · {_ESC(c["stream"])} desk</span>
<h2><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h2>
<p class="lede">{_ESC(c["answer_text"])}</p>
{heroviz}
<div class="meta">{_trigger_line(c)}<span class="when">
{ago(c["generated_at"], now)}</span>
<a class="more" href="/story/{c["id"]}">Read the full story — with the chart
and the exact query →</a></div></article>"""

        for c in cards[1:5]:
            fig = ""
            tpath = newsroom._thumb_path(c)
            if tpath:
                v = hashlib.md5(tpath.read_bytes()).hexdigest()[:8]
                fig = (f'<a class="item-fig" href="/story/{c["id"]}" tabindex="-1" '
                       f'aria-hidden="true"><img class="item-thumb" '
                       f'src="/assets/story-{c["id"]}-thumb.png?v={v}" '
                       f'width="1200" height="480" loading="lazy" alt=""></a>')
            sec2 += f"""<div class="item">{fig}<div class="item-body">
<span class="kicker">{_ESC(c["topic"])}</span>
<h3><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h3>
<div class="meta">{ago(c["generated_at"], now)}</div>
</div></div>"""

        for c in cards[5:10]:
            rail += f"""<div class="item"><div class="item-body">
<span class="kicker">{_ESC(c["topic"])} · {_ESC(c["stream"])}</span>
<h3><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h3>
<div class="meta">{ago(c["generated_at"], now)}</div>
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

    # Trending only speaks when it has something to say: at least 3 votes
    # overall, a per-card score of its own. Until then, silence — a lone
    # badge on one card would advertise emptiness, not heat.
    _trend = board.get("trend") or []
    _votes = sum(t.get("votes", 0) for t in _trend)
    chip = '<span class="badge trend">trending</span> ' if _votes >= 3 else ""
    del chip  # trend badge stays available to story pages this cycle

    fixture = any("(fixture)" in (c["headline"].get("source") or "")
                  for c in cards)
    help_ = ("Every question here is raised by a headline first. These cards "
             "run on labeled demo fixtures; each fresh cycle replaces them "
             "with live receipts."
             if fixture else
             "Every question on this page was raised by a real headline first.")
    latest = f"""<section class="latest" id="signals"><div class="wrap">
<p class="sechelp" style="text-align:left;margin:0 0 .8rem">{help_}</p>
<div class="latest-grid">
{lead}
<div class="sec2"><h2 class="sec2-head">Also on the board</h2>{sec2}</div>
<aside class="rail"><h2 class="railhead">Latest questions</h2>{rail}</aside>
</div></div></section>"""

    body = f"""{latest}
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

<div class="wrap"><img class="tailpiece" src="/assets/skyline-light.png"
width="2340" height="875" loading="lazy" alt="Hartford skyline: the Soldiers
and Sailors arch, the stone-arch bridge, the State Capitol with its gilded
dome, City Place and the downtown towers"></div>"""

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
