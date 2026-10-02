"""Newsroom site layer: story pages, archive, RSS, sitemap.

Durable, linkable objects — the atom of a news site — published beside the
rolling feed. Everything is static and committed, so git history doubles as
the audit trail. Absolute URLs (canonical, OG, RSS) use SITE_URL; on-site
navigation stays relative so the deploy preview works on any host.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import json

from . import config

_ESC = html.escape


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def _rfc822(ts: str) -> str:
    return email.utils.format_datetime(_parse(ts))


def _pretty(ts: str) -> str:
    d = _parse(ts)
    month = d.strftime("%B")
    return f"{month} {d.day}, {d.year}, {d:%H:%M} UTC"


def _day(ts: str) -> str:
    return ts[:10]


def permalink(card: dict) -> str:
    return f"{config.SITE_URL}/story/{card['id']}"


def _spec_json(obj) -> str:
    # Choropleth topo loads "us.json" relatively; story pages live deeper
    # than the site root, so pin it absolute.
    return json.dumps(obj, default=str).replace(
        '"us.json"', f'"{config.SITE_URL}/us.json"'
    )


_CSS = """
:root{--bg:#101418;--panel:#151c24;--line:#2b3a48;--ink:#eef2f5;--dim:#9fb0bf;
--acc:#f2a65a;--blue:#7fb4ff;--ok:#8fd6a9}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--ink);
max-width:820px;margin:0 auto;padding:1.2rem 1rem 3rem}
a{color:var(--blue)}
.home{font-weight:800;font-size:1.15rem;color:var(--ink);text-decoration:none;letter-spacing:.01em}
.home b{color:var(--acc)}
.sub{color:var(--dim);font-size:.85rem;margin-left:.6rem}
.kicker{margin-top:2.2rem;color:var(--acc);font-weight:700;font-size:.8rem;
letter-spacing:.18em;text-transform:uppercase}
h1{font-size:2.1rem;line-height:1.22;margin:.4rem 0 .8rem;letter-spacing:-.01em}
.answer{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--ok);
border-radius:10px;padding:1rem 1.2rem;font-size:1.35rem;font-weight:600;line-height:1.4}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:1rem 1.2rem;margin:1.2rem 0}
.label{color:var(--dim);font-weight:700;font-size:.72rem;letter-spacing:.16em;
text-transform:uppercase;margin-bottom:.5rem}
.meta{color:var(--dim);font-size:.85rem;line-height:1.5}
.badge{background:#243040;color:#cfdcea;border-radius:4px;padding:.05rem .4rem;font-size:.72rem}
code{background:#243040;color:#cfdcea;padding:.1rem .35rem;border-radius:4px;font-size:.85em;
word-break:break-all}
footer{border-top:1px solid var(--line);margin-top:2.5rem;padding-top:1rem}
"""

_VEGA = ('<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>\n'
         '<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>\n'
         '<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>')

_NAV = ('<a href="/about">About</a> · <a href="/methodology">Methodology</a> · '
        '<a href="/masthead">Masthead</a> · <a href="/corrections">Corrections</a> · '
        '<a href="/feed.xml">RSS</a>')


def _trigger_html(card: dict) -> str:
    h = card["headline"]
    title = _ESC(h["title"])
    if h.get("url"):
        title = f'<a href="{_ESC(h["url"])}" rel="noopener">{title}</a>'
    src = f'{_ESC(h["source"])} · ' if h.get("source") else ""
    return (f'<div class="card"><div class="label">Triggered by</div>'
            f'<div style="font-size:1.05rem;line-height:1.35">{src}{title}</div></div>')


def _provenance_html(card: dict) -> str:
    cites = "<br>".join(f'<a href="{_ESC(c)}">{_ESC(c)}</a>' for c in card["citations"])
    vals = card.get("answer_values") or {}
    data_date = f' · data as of <b>{_ESC(str(vals.get("date")))}</b>' if vals.get("date") else ""
    cache = ' <span class="badge">cache</span>' if card.get("cache") else ""
    return (f'<div class="card"><div class="label">Provenance · fetched, never written</div>'
            f'<div class="meta">dataset: {cites}<br>query: <code>{_ESC(str(card["query"]))}</code>'
            f'<br>published {_pretty(card["generated_at"])}{data_date}{cache}</div></div>')


def story_html(card: dict) -> str:
    q = _ESC(card["question"])
    a = _ESC(card["answer_text"])
    url = permalink(card)
    img = f'{config.SITE_URL}/shots/board.png'
    chart = (f'<div class="card"><div id="chart"></div>'
             f'<script>vegaEmbed("#chart", {_spec_json(card["chart"])}, {{actions:false}});</script></div>')
    chart2 = ""
    if card.get("chart2"):
        chart2 = (f'<div class="card"><div id="chart2"></div>'
                  f'<script>vegaEmbed("#chart2", {_spec_json(card["chart2"])}, {{actions:false}});</script></div>')
    cache_badge = ' <span class="badge">cache</span>' if card.get("cache") else ""
    kicker = f'{_ESC(card["topic"])} · {_ESC(card["stream"])} desk{cache_badge}'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{q} · CT Signal</title>
<link rel="canonical" href="{url}">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta property="og:type" content="article">
<meta property="og:site_name" content="CT Signal">
<meta property="og:title" content="{q}">
<meta property="og:description" content="{a}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="article:published_time" content="{card['generated_at']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#101418">
<style>{_CSS}</style></head><body>
<a class="home" href="/">CT&nbsp;<b>Signal</b></a><span class="sub">automated data desk</span>
<div class="kicker">{kicker}</div>
<h1>{q}</h1>
<div class="answer">{a}</div>
{chart}{chart2}
{_trigger_html(card)}
{_provenance_html(card)}
<footer><div class="meta">CT Signal is an automated newsroom: the news cycle picks
the question, public datasets answer it, no number was typed by a human.
{_NAV}<br><a href="mailto:{config.CONTACT_EMAIL}">{config.CONTACT_EMAIL}</a> · © {dt.date.today().year} CT Signal</div></footer>
</body></html>
"""


def rss_xml(cards: list[dict]) -> str:
    items = []
    for c in cards:
        h = c["headline"]
        trig = f'<a href="{_ESC(h["url"])}">{_ESC(h["title"])}</a>' if h.get("url") else _ESC(h["title"])
        desc = f'{_ESC(c["answer_text"])}<br/><br/>Triggered by: {trig}'
        items.append(
            f'<item><title>{_ESC(c["question"])}</title>'
            f'<link>{permalink(c)}</link><guid isPermaLink="true">{permalink(c)}</guid>'
            f'<pubDate>{_rfc822(c["generated_at"])}</pubDate>'
            f'<category>{_ESC(c["topic"])}</category>'
            f'<description>{desc}</description></item>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>CT Signal</title><link>{config.SITE_URL}</link>'
        f'<atom:link href="{config.SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
        '<description>Connecticut data answers to the questions its news cycle is '
        'already asking. Automated data desk — every number fetched, never written.'
        '</description><language>en-us</language>'
        f'<lastBuildDate>{_rfc822(cards[0]["generated_at"])}</lastBuildDate>'
        f'<webMaster>{config.CONTACT_EMAIL}</webMaster>'
        + "".join(items) + '</channel></rss>\n'
    )


def sitemap_xml(cards: list[dict]) -> str:
    now = _day(dt.datetime.now(dt.timezone.utc).isoformat())
    urls = [f'{config.SITE_URL}/']
    urls += [permalink(c) for c in cards]
    urls += [f'{config.SITE_URL}/{p}' for p in
             ("about", "methodology", "masthead", "corrections")]
    body = "".join(
        f'<url><loc>{u}</loc>{"<lastmod>" + now + "</lastmod>" if not u.startswith(config.SITE_URL + "/s") else ""}</url>'
        for u in urls
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + body + '</urlset>\n')


def write_all(cards: list[dict]) -> None:
    """Idempotent: rebuilds every story page, archive copy, RSS, sitemap."""
    for card in cards:
        arch = config.ARCHIVE_DIR / card["generated_at"][:7]
        arch.mkdir(parents=True, exist_ok=True)
        (arch / f"{card['id']}.json").write_text(
            json.dumps(card, indent=2, sort_keys=True, default=str))
        story = config.STORY_DIR / card["id"]
        story.mkdir(parents=True, exist_ok=True)
        (story / "index.html").write_text(story_html(card))
    if cards:
        (config.ROOT / "feed.xml").write_text(rss_xml(cards))
        (config.ROOT / "sitemap.xml").write_text(sitemap_xml(cards))
