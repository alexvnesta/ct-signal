"""Homepage export: the Connecticut board + the rolling feed of answered
questions, server-rendered so crawlers, RSS readers, and link previews all see
real content. Charts embed as JSON islands; the vega loader in theme upgrades
them to SVG progressively.
"""
from __future__ import annotations

import datetime as dt
import html
import json

from . import config, theme

_ESC = html.escape


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def ago(iso: str, now: dt.datetime) -> str:
    s = (now - _parse(iso)).total_seconds()
    stamp = iso[11:16] + " UTC"
    if s < 90:
        return f"just now · {stamp}"
    if s < 5400:
        return f"{round(s / 60)} min ago · {stamp}"
    if s < 86400:
        return f"{round(s / 3600)} h ago · {stamp}"
    return iso[:10]


def _trigger_line(card: dict) -> str:
    h = card["headline"]
    title = _ESC(h["title"])
    src = h.get("source") or ""
    # civic-calendar entries carry "[civic calendar] ..." in the title; don't
    # print the source label twice.
    if src and title.startswith(f"[{_ESC(src)}]"):
        title = title[len(f"[{_ESC(src)}]") + 1:].lstrip()
        src = ""
    if h.get("url"):
        title = (f'<a href="{_ESC(h["url"])}" rel="noopener">'
                 f'{title}</a>')
    src = f'{_ESC(src)} · ' if src else ""
    return f'Triggered by {src}{title}'


def _kicker(card: dict, when: str) -> str:
    cache = ' <span class="badge">cache</span>' if card.get("cache") else ""
    return (f'{_ESC(card["topic"])} · {_ESC(card["stream"])} desk'
            f'{cache} · {when}')


def home_html(cards: list[dict], board: dict) -> str:
    now = _parse(cards[0]["generated_at"]) if cards else (
        dt.datetime.now(dt.timezone.utc))

    hero = ""
    if cards:
        c = cards[0]
        hero = f"""<div class="wrap"><div class="hero">
<div class="kicker">Today's lead · {_ESC(c["topic"])} · {_ESC(c["stream"])} desk</div>
<h1><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h1>
<p class="lede">{_ESC(c["answer_text"])}</p>
<div class="meta">{_trigger_line(c)} · {ago(c["generated_at"], now)}</div>
<p><a class="more" href="/story/{c["id"]}">Read the full story with the chart
and the literal query →</a></p>
</div></div>"""

    tiles = ""
    for i, t in enumerate(board.get("tiles", [])):
        label = (f'{t["title"]}: Connecticut at {_ESC(str(t["value"]))}, '
                 f'rank {t["rank"]} of {t["n"]} peers')
        tiles += f"""<div class="tile">
<div class="tname">{_ESC(t["title"])}</div>
<div class="val">{_ESC(str(t["value"]))}</div>
{theme.viz(json.dumps(t["strip"], default=str), f"strip{i}", label=label)}
<span class="chip">#{_ESC(str(t["rank"]))} of {_ESC(str(t["n"]))} peers · data {_ESC(str(t["date"]))}</span>
</div>"""

    signals = ""
    for c in cards[1:] if cards else []:
        signals += f"""<li class="sig">
<div class="kicker">{_kicker(c, ago(c["generated_at"], now))}</div>
<h3><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h3>
<p class="answer">{_ESC(c["answer_text"])}</p>
<div class="meta">{_trigger_line(c)} ·
<a class="more" href="/story/{c["id"]}">the story with receipts →</a></div>
</li>"""

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
<p class="legend">“{n_peers} peers” = the 50 states, Washington DC, and Puerto
Rico. Each tile prints the vintage of its own dataset; older vintages are the
honest limit of annual surveys, not a lag in the pipeline.</p>
</div></section>

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
    (config.OUTPUT_DIR / "feed.json").write_text(
        json.dumps(feed, indent=2, sort_keys=True, default=str)
    )
    if board is not None:
        (config.OUTPUT_DIR / "board.json").write_text(
            json.dumps(board, indent=2, sort_keys=True, default=str)
        )
    (config.OUTPUT_DIR / "index.html").write_text(home_html(cards, board or {}))
    from . import newsroom

    newsroom.write_all(cards)
