"""Newsroom site layer: story pages, archive, RSS, JSON feed, sitemap.

Durable, linkable objects — the atom of a news site — published beside the
rolling feed. Everything is static and committed, so git history doubles as
the audit trail. Absolute URLs (canonical, OG, RSS) use SITE_URL; on-site
navigation stays root-relative so the deploy preview works on any host.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import json

from . import config, theme

_ESC = html.escape


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def _rfc822(ts: str) -> str:
    return email.utils.format_datetime(_parse(ts))


def _pretty(ts: str) -> str:
    d = _parse(ts)
    return f"{d:%B} {d.day}, {d.year}, {d:%H:%M} UTC"


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


def _trigger_html(card: dict) -> str:
    h = card["headline"]
    title = _ESC(h["title"])
    src = h.get("source") or ""
    if src and title.startswith(f"[{_ESC(src)}]"):  # don't print label twice
        title = title[len(f"[{_ESC(src)}]") + 1:].lstrip()
        src = ""
    if h.get("url"):
        title = f'<a href="{_ESC(h["url"])}" rel="noopener">{title}</a>'
    src = f'{_ESC(src)} · ' if src else ""
    return (f'<div class="card"><div class="label">Triggered by</div>'
            f'<div style="font-size:1.05rem;line-height:1.35">{src}{title}</div></div>')


def _provenance_html(card: dict) -> str:
    cites = "<br>".join(f'<a href="{_ESC(c)}">{_ESC(c)}</a>' for c in card["citations"])
    vals = card.get("answer_values") or {}
    if vals.get("date"):
        data_date = f' · data as of <b>{_ESC(str(vals.get("date")))}</b>'
    else:
        data_date = ' · data vintage: see query above'
    cache = ' <span class="badge">cache</span>' if card.get("cache") else ""
    return (f'<div class="card provenance"><div class="label">'
            f'Provenance · fetched, never written</div>'
            f'<div class="meta">dataset: {cites}<br>query: <code>{_ESC(str(card["query"]))}</code>'
            f'<br>published {_pretty(card["generated_at"])}{data_date}{cache}</div></div>')


def _story_og(card: dict) -> str | None:
    """Per-story cover if generated (scripts/make_story_covers.py); the
    generic cover otherwise. Checked at build time so a missing PNG never
    yields a 404 og:image."""
    p = config.ROOT / "assets" / f"story-{card['id']}.png"
    return f"{config.SITE_URL}/assets/story-{card['id']}.png" if p.exists() else None


def story_html(card: dict) -> str:
    q = _ESC(card["question"])
    a = _ESC(card["answer_text"])
    url = permalink(card)
    label = f'Peer ranking chart for “{card["question"]}”. {card["answer_text"]}'
    chart = theme.viz(_spec_json(card["chart"]), "chart", label=label,
                      caption="Every peer ranked; Connecticut highlighted in "
                              "orange. Source and query below.")
    chart2 = ""
    if card.get("chart2"):
        chart2 = theme.viz(_spec_json(card["chart2"]), "chart2",
                           label=f'United States map, same data: '
                                 f'{card["answer_text"]}',
                           caption="Peer map; Connecticut outlined. "
                                   "AlbersUSA omits DC and Puerto Rico.")
    cache_badge = ' <span class="badge">cache</span>' if card.get("cache") else ""
    kicker = f'{_ESC(card["topic"])} · {_ESC(card["stream"])} desk{cache_badge}'
    og = _story_og(card)
    body = f"""<div class="wrap col">
<div class="breadcrumb"><a href="/">← The board</a></div>
<div class="kicker">{kicker}</div>
<h1 style="font:700 clamp(1.6rem,4vw,2.3rem)/1.2 var(--serif);margin:.4rem 0 .3rem">{q}</h1>
<div class="meta">Published {_pretty(card["generated_at"])} · CT Signal
automated data desk</div>
<div class="answerbox">{a}</div>
<div class="card"><div class="label">The data</div>{chart}{chart2}</div>
{_trigger_html(card)}
{_provenance_html(card)}
<p class="meta">Found an error? Corrections are public, annotated, and diffable —
see <a href="/corrections">the corrections policy</a>.</p>
</div>"""
    return theme.page(
        title=f"{card['question']} · CT Signal",
        desc=card["answer_text"][:200],
        path=f"/story/{card['id']}",
        body=body, og_type="article", og_title=card["question"],
        og_desc=card["answer_text"][:200], published=card["generated_at"],
        image=og,
        json_ld=theme.article_json_ld(
            card_id=card["id"], headline=card["question"],
            description=card["answer_text"][:200],
            published=card["generated_at"], section=card["topic"],
            image=og))


def rss_xml(cards: list[dict]) -> str:
    items = []
    for c in cards:
        h = c["headline"]
        trig = (f'<a href="{_ESC(h["url"])}">{_ESC(h["title"])}</a>'
                if h.get("url") else _ESC(h["title"]))
        story = permalink(c)
        art = ""
        if (config.ROOT / "assets" / f"story-{c['id']}.png").exists():
            art = (f'<enclosure url="{config.SITE_URL}/assets/story-{c["id"]}.png"'
                   f' length="0" type="image/png"/>')
        desc = (f'{_ESC(c["answer_text"])}<br/><br/>'
                f'<a href="{story}">Read the full story with the chart and '
                f'the query</a><br/><br/>Triggered by: {trig}')
        items.append(
            f'<item><title>{_ESC(c["question"])}</title>{art}'
            f'<link>{story}</link><guid isPermaLink="true">{story}</guid>'
            f'<pubDate>{_rfc822(c["generated_at"])}</pubDate>'
            f'<category>{_ESC(c["topic"])}</category>'
            f'<description>{desc}</description></item>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>CT Signal</title><link>{config.SITE_URL}/</link>'
        f'<atom:link href="{config.SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
        '<description>Connecticut data answers to the questions its news cycle is '
        'already asking. Automated data desk — every number fetched, never written.'
        '</description><language>en-us</language>'
        '<docs>https://www.rssboard.org/rss-specification</docs>'
        '<generator>CT Signal pipeline</generator>'
        '<ttl>15</ttl>'
        f'<managingEditor>{config.CONTACT_EMAIL} (CT Signal)</managingEditor>'
        f'<webMaster>{config.CONTACT_EMAIL} (CT Signal)</webMaster>'
        f'<lastBuildDate>{_rfc822(cards[0]["generated_at"])}</lastBuildDate>'
        + "".join(items) + '</channel></rss>\n'
    )


def json_feed(cards: list[dict]) -> str:
    items = []
    for c in cards:
        h = c["headline"]
        trig = f' Triggered by: {h["title"]}' if h.get("title") else ""
        it = {
            "id": permalink(c),
            "url": permalink(c),
            "title": c["question"],
            "content_text": c["answer_text"] + "." + trig,
            "date_published": c["generated_at"],
            "_tags": [c["topic"]],
        }
        if (config.ROOT / "assets" / f"story-{c['id']}.png").exists():
            it["image"] = f"{config.SITE_URL}/assets/story-{c['id']}.png"
            it["attachments"] = [{
                "url": f"{config.SITE_URL}/assets/story-{c['id']}.png",
                "mime_type": "image/png",
            }]
        items.append(it)
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "CT Signal",
        "home_page_url": config.SITE_URL + "/",
        "feed_url": config.SITE_URL + "/feed.json",
        "description": "Connecticut data answers to the questions its news "
                       "cycle is already asking. Every number fetched, never "
                       "written.",
        "favicon": f"{config.SITE_URL}/assets/favicon.svg",
        "items": items,
    }
    return json.dumps(feed, indent=2, ensure_ascii=False) + "\n"


def sitemap_xml(cards: list[dict]) -> str:
    now = _day(dt.datetime.now(dt.timezone.utc).isoformat())
    parts = [f'<url><loc>{config.SITE_URL}/</loc><lastmod>{now}</lastmod></url>']
    for c in cards:
        parts.append(f'<url><loc>{permalink(c)}</loc>'
                     f'<lastmod>{_day(c["generated_at"])}</lastmod></url>')
    for p in ("about", "methodology", "masthead", "corrections"):
        parts.append(f'<url><loc>{config.SITE_URL}/{p}</loc>'
                     f'<lastmod>{now}</lastmod></url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(parts) + '</urlset>\n')


def write_all(cards: list[dict]) -> None:
    """Idempotent: rebuilds every story page, archive copy, feeds, sitemap."""
    from . import pages

    pages.write_pages()
    assets = config.ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "site.css").write_text(theme.CSS)
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
        (config.ROOT / "feed.json").write_text(json_feed(cards))
        (config.ROOT / "sitemap.xml").write_text(sitemap_xml(cards))
