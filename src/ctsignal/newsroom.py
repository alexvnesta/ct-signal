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
import shutil

from . import config, theme, util

_ESC = html.escape


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def _rfc822(ts: str) -> str:
    return email.utils.format_datetime(_parse(ts))


def _pretty(ts: str) -> str:
    d = util.et(ts)
    return f"{d:%B} {d.day}, {d.year}, {util.clock(d)}"


def _day(ts: str) -> str:
    return ts[:10]


def permalink(card: dict) -> str:
    return f"{config.SITE_URL}/story/{card['id']}"


def _spec_json(obj) -> str:
    # Chart islands are JSON-in-HTML: neutralize both "</" and "<!--" so no
    # external string (town names, feed text inside altair data) can flip the
    # parser state; absolute us.json for deep story pages.
    blob = json.dumps(obj, default=str).replace("</", "<\\/")
    blob = blob.replace("<!--", "<\\u0021--")
    return blob.replace('"us.json"', f'"{_ESC(config.SITE_URL)}/us.json"')



def _trigger_html(card: dict) -> str:
    prefix, title = theme.trigger_parts(card)
    return (f'<div class="card"><div class="label">Triggered by</div>'
            f'<div style="font-size:1.05rem;line-height:1.35">{prefix}{title}</div></div>')


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
    p = _cover_path(card)
    return f"{config.SITE_URL}/assets/story-{card['id']}.png" if p else None


def _cover_path(card: dict):
    """The story's OG card on disk, or None (generic og-cover fallback)."""
    p = config.ROOT / "assets" / f"story-{card['id']}.png"
    return p if p.exists() else None


def story_html(card: dict) -> str:
    q = _ESC(card["question"])
    a = _ESC(card["answer_text"])
    url = permalink(card)
    kind = card.get("chart_kind", "rank_strip")
    local = card.get("stream") == "local"
    if local:
        desc = ("Top 10 Connecticut towns by net grand list growth; the "
                "fastest town highlighted in orange. Source and query below.")
        label = (f'Town ranking chart for “{card["question"]}”. '
                 f'{card["answer_text"]}')
    elif kind == "trend":
        desc = ("Monthly series, Connecticut (orange) against the United "
                "States average. Source and query below.")
        label = (f'Time-trend chart for “{card["question"]}”. '
                 f'{card["answer_text"]}')
    else:
        desc = ("Every peer ranked; Connecticut highlighted in orange. "
                "Source and query below.")
        label = (f'Peer ranking chart for “{card["question"]}”. '
                 f'{card["answer_text"]}')
    chart = theme.viz(_spec_json(card["chart"]), "chart", label=label,
                      caption=desc)
    chart2 = ""
    if card.get("chart2"):
        chart2 = theme.viz(_spec_json(card["chart2"]), "chart2",
                           label=f'United States map, same data: '
                                 f'{card["answer_text"]}',
                           caption="Peer map; Connecticut outlined. "
                                   "AlbersUSA omits DC and Puerto Rico.")
    cache_badge = ' <span class="badge">cache</span>' if card.get("cache") else ""
    kicker = (f'<a class="klink" href="/topic/{_ESC(card["topic"])}">'
              f'{_ESC(card["topic"])}</a> · {_ESC(card["stream"])} desk'
              f'{cache_badge}')
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
{_freshness_html(card)}
<details class="embed"><summary>Embed this story</summary>
<p class="meta">Free to embed with attribution — the embed stays updated as
the underlying data refreshes.</p>
<textarea id="embed-snippet" name="embed-snippet" aria-label="Embed code for this story" readonly rows="2" onclick="this.select()">&lt;iframe src="{_ESC(config.SITE_URL)}/story/{card["id"]}/embed" width="100%" height="540" style="border:0;border-radius:10px" loading="lazy" title="{_ESC(card["question"])}"&gt;&lt;/iframe&gt;</textarea>
</details>
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



def embed_html(card: dict) -> str:
    """Chromeless story card for iframes. Canonical points at the story so
    embeds consolidate link equity instead of duplicating it."""
    label = f'{card["question"]}. {card["answer_text"]}'
    chart = theme.viz(_spec_json(card["chart"]), "chart", label=label,
                      caption=None)
    body = f"""<div style="background:var(--bg);color:var(--ink);
font:16px/1.6 var(--sans);padding:1rem 1.2rem;min-height:100vh;box-sizing:border-box">
<div class="kicker"><a class="klink" href="/story/{card["id"]}" target="_blank"
rel="noopener">{_ESC(card["topic"])}</a> · CT Signal</div>
<h1 style="font:700 1.25rem/1.3 var(--serif);margin:.4rem 0">{_ESC(card["question"])}</h1>
<div class="answerbox" style="font-size:.95rem">{_ESC(card["answer_text"])}</div>
{chart}
<p class="meta" style="margin:.8rem 0 0">Data refreshes automatically ·
<a href="/story/{card["id"]}" target="_blank" rel="noopener">full story with
provenance →</a></p>
</div>"""
    head = theme.head(title=f'{card["question"]} · embedded on CT Signal',
                      desc=card["answer_text"][:200],
                      path=f'/story/{card["id"]}', og_type="article")
    return f'<!doctype html><html lang="en">{head}<body>{body}' \
           f'{theme.VEGA_LOAD}</body></html>\n'


def _topics(cards: list[dict]) -> dict:
    out: dict = {}
    for c in sorted(cards, key=lambda c: c["generated_at"], reverse=True):
        out.setdefault(c["topic"], []).append(c)
    return out


def topic_html(topic: str, cards: list[dict]) -> str:
    items = "".join(
        f"""<li class="sig">
<div class="kicker"><span class="badge">{_ESC(c["stream"])} desk</span> ·
{_pretty(c["generated_at"])}</div>
<h2><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h2>
<p class="answer">{_ESC(c["answer_text"])}</p>
</li>""" for c in cards)
    body = f"""<div class="wrap col">
<div class="breadcrumb"><a href="/">← The board</a></div>
<div class="kicker">Topic desk</div>
<h1 style="font:700 clamp(1.6rem,4vw,2.3rem)/1.2 var(--serif);margin:.4rem 0 .3rem">{_ESC(topic).replace("-", " ").capitalize()}</h1>
<p class="meta">Every question this desk has answered, newest first. Know
where you live.</p>
<ol class="signals">{items}</ol>
</div>"""
    return theme.page(
        title=f"{topic.capitalize()} stories · CT Signal",
        desc=f"All CT Signal answers on {topic}: charts, rankings, and the "
             "query behind every number.",
        path=f"/topic/{topic}", body=body,
        og_title=f"{topic.capitalize()} — CT Signal")



def rss_xml(cards: list[dict]) -> str:
    items = []
    for c in cards:
        h = c["headline"]
        trig = (f'<a href="{_ESC(h["url"])}">{_ESC(h["title"])}</a>'
                if h.get("url") else _ESC(h["title"]))
        story = permalink(c)
        art = ""
        png = _cover_path(c)
        if png:
            art = (f'<enclosure url="{config.SITE_URL}/assets/story-{c["id"]}.png"'
                   f' length="{png.stat().st_size}" type="image/png"/>')
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
        'already asking. Automated data desk — know where you live.'
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
            "content_text": c["answer_text"] + trig,
            "date_published": c["generated_at"],
            "_tags": [c["topic"]],
        }
        png = _cover_path(c)
        if png:
            it["image"] = f"{config.SITE_URL}/assets/story-{c['id']}.png"
            it["attachments"] = [{
                "url": f"{config.SITE_URL}/assets/story-{c['id']}.png",
                "mime_type": "image/png",
                "size_in_bytes": png.stat().st_size,
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
    from . import pages
    now = _day(dt.datetime.now(dt.timezone.utc).isoformat())
    parts = [f'<url><loc>{config.SITE_URL}/</loc><lastmod>{now}</lastmod></url>']
    for c in cards:
        parts.append(f'<url><loc>{permalink(c)}</loc>'
                     f'<lastmod>{_day(c["generated_at"])}</lastmod></url>')
    for topic, tcards in _topics(cards).items():
        newest = max(_day(c["generated_at"]) for c in tcards)
        parts.append(f'<url><loc>{config.SITE_URL}/topic/{topic}</loc>'
                     f'<lastmod>{newest}</lastmod></url>')
    for p in sorted(pages._PAGES):
        parts.append(f'<url><loc>{config.SITE_URL}/{p}</loc>'
                     f'<lastmod>{now}</lastmod></url>')
    parts.append(f'<url><loc>{config.SITE_URL}/archive</loc>'
                 f'<lastmod>{now}</lastmod></url>')
    for c in cards:
        for row in (c.get("towns") or [])[:200]:
            parts.append(
                f'<url><loc>{config.SITE_URL}/town/{_slug(row["town"])}</loc>'
                f'<lastmod>{_day(c["generated_at"])}</lastmod></url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(parts) + '</urlset>\n')


def write_all(cards: list[dict]) -> None:
    """Idempotent: rebuilds every story page, archive copy, feeds, sitemap."""
    from . import pages

    pages.write_pages()
    assets = config.ROOT / "assets"
    assets.mkdir(exist_ok=True)
    util.atomic_write_text(assets / "site.css", theme.CSS)
    for card in cards:
        arch = config.ARCHIVE_DIR / card["generated_at"][:7]
        arch.mkdir(parents=True, exist_ok=True)
        (arch / f"{card['id']}.json").write_text(
            json.dumps(card, indent=2, sort_keys=True, default=str))
        story = config.STORY_DIR / card["id"]
        story.mkdir(parents=True, exist_ok=True)
        util.atomic_write_text(story / "index.html", story_html(card))
        emb = story / "embed"
        emb.mkdir(exist_ok=True)
        util.atomic_write_text(emb / "index.html", embed_html(card))
    tdir = config.ROOT / "topic"
    tdir.mkdir(exist_ok=True)
    for topic, tcards in _topics(cards).items():
        hd = tdir / topic
        hd.mkdir(exist_ok=True)
        (hd / "index.html").write_text(topic_html(topic, tcards))
    troot = config.ROOT / "town"
    for c in cards:
        for row in (c.get("towns") or []):
            hd = troot / _slug(row["town"])
            hd.mkdir(parents=True, exist_ok=True)
            util.atomic_write_text(hd / "index.html", town_html(row, c))
    if troot.exists():
        live = {_slug(r["town"]) for c in cards for r in (c.get("towns") or [])}
        for stale in troot.iterdir():
            if stale.is_dir() and stale.name not in live:
                shutil.rmtree(stale)
    util.atomic_write_text(config.ARCHIVE_DIR / "index.html",
                           archive_html(cards))
    if cards:
        util.atomic_write_text(config.ROOT / "feed.xml", rss_xml(cards))
        util.write_json(config.ROOT / "feed.json", json.loads(json_feed(cards)))
        util.atomic_write_text(config.ROOT / "sitemap.xml", sitemap_xml(cards))


def _slug(name: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _freshness_html(card: dict) -> str:
    """Honesty strip: how many archived vintages exist for this card."""
    vers = sorted(set(config.ARCHIVE_DIR.glob(f"*/{card['id']}.json")))
    if len(vers) < 2:
        return ""
    return (f'<p class="meta">This story refreshes automatically with its '
            f'dataset &mdash; {len(vers)} archived vintages on record in '
            f'<a href="/archive">the public archive</a>.</p>')


def town_html(row: dict, card: dict) -> str:
    esc = html.escape
    n = card.get("answer_values", {}).get("n") or len(card.get("towns") or [])
    b = card.get("answer_values", {}).get("top") or {}
    med = sorted(r["pct"] for r in card.get("towns") or [])
    median = med[len(med) // 2] if med else 0.0
    body = f"""<article class="wrap col">
<div class="label">Connecticut town file</div>
<h1 style="font:700 clamp(1.7rem,4vw,2.4rem)/1.15 var(--serif);margin:.4rem 0 .3rem">{esc(row["town"])}</h1>
<p class="sub">Property tax base (net grand list), from the Connecticut Open
Data Portal. Know where you live. This is one row of
<a href="/story/{card["id"]}">the full story</a> with the chart and the query.</p>
<table class="towntab"><tbody>
<tr><td>Net grand list, {esc(str(card["answer_values"].get("date", "")))}</td><td>${row["latest"]:,.0f}</td></tr>
<tr><td>Net grand list, prior vintage</td><td>${row["prior"]:,.0f}</td></tr>
<tr><td>Change in two years</td><td>${row["added"]:,.0f} ({row["pct"]:+.1f}%)</td></tr>
<tr><td>Rank among {n} Connecticut places</td><td>{row["rank"]} of {n}</td></tr>
<tr><td>Statewide median change (for context)</td><td>{median:+.1f}%</td></tr>
</tbody></table>
<p class="meta">Fastest-growing place this vintage: {esc(b.get("town", ""))}.
Dataset citation and the literal query live on
<a href="/story/{card["id"]}">the source story</a>; errors are corrected publicly.</p>
</article>"""
    title = f'{row["town"]} property tax base · CT Signal town file'
    desc = (f'{row["town"]}\'s net taxable property: ${row["latest"]:,.0f}, '
            f'{row["pct"]:+.1f}% over two years, rank {row["rank"]} of {n}.')
    return theme.page(title=title, desc=esc(desc), path=f'/town/{_slug(row["town"])}',
                      body=body)


def archive_html(cards: list[dict]) -> str:
    """On-site index of every card ever published (the audit trail, browsable)."""
    esc = html.escape
    seen: dict[str, tuple[str, dict]] = {}
    for path in config.ARCHIVE_DIR.rglob("*.json"):
        try:
            c = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        prev = seen.get(c["id"])
        if prev is None or c.get("generated_at", "") > prev[0]:
            seen[c["id"]] = (c.get("generated_at", ""), c)
    months: dict[str, list[dict]] = {}
    for _, c in seen.values():
        months.setdefault(c.get("generated_at", "?")[:7], []).append(c)
    blocks = []
    for month in sorted(months, reverse=True):
        rows = sorted(months[month], key=lambda c: c.get("generated_at", ""),
                      reverse=True)
        lis = "".join(
            f'<li style="padding:.5rem 0;border-bottom:1px solid var(--line)">'
            f'<a href="/story/{c["id"]}">{esc(c["question"])}</a> '
            f'<span class="meta">&middot; {esc(c.get("topic", ""))} &middot; '
            f'{esc(c.get("generated_at", ""))[:10]}</span></li>'
            for c in rows)
        blocks.append(
            f'<h2 style="font:700 1.15rem/1.3 var(--serif);margin:1.4rem 0 .2rem">'
            f'{esc(month)}</h2><ul style="list-style:none;padding:0">{lis}</ul>')
    total = len(seen)
    body = f"""<article class="wrap col">
<div class="label">Public archive</div>
<h1 style="font:700 clamp(1.7rem,4vw,2.3rem)/1.15 var(--serif);margin:.4rem 0 .3rem">
Every question we have answered</h1>
<p class="sub">{total} published cards, kept forever &mdash; including every
story whose data vintage was superseded. Raw JSON lives in the repository,
one file per card per month; this page is the human-readable index.</p>
{''.join(blocks)}
</article>"""
    return theme.page(title="Card archive · CT Signal",
                      desc="Every question CT Signal has answered, kept "
                           "forever with its data vintage.",
                      path="/archive", body=body)
