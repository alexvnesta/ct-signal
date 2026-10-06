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
import hashlib
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


def _pretty_time(ts: str) -> str:
    """Same Eastern wall clock, machine-readable."""
    return f'<time datetime="{ts}">{_pretty(ts)}</time>'


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
    return (f'<div class="card"><div class="label">Source</div>'
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
            f'<br>published {_pretty_time(card["generated_at"])}{data_date}{cache}</div></div>')


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


def _thumb_path(card: dict):
    """Sentence-free board thumbnail (same generator), or None — a missing
    PNG never yields a broken img on the board."""
    p = config.ROOT / "assets" / f"story-{card['id']}-thumb.png"
    return p if p.exists() else None


def _place_line(card: dict) -> str:
    """One derived sentence about where the middle of the pack sits, computed
    from the chart rows the card already carries. Nothing is invented: the
    only number is the median of the peers being shown. Percent indicators
    say points, because a difference of two percents is not two percent."""
    if card.get("stream") != "stackup":
        return ""
    values = (card.get("chart") or {}).get("data", {}).get("values") or []
    peers = [float(v["value"]) for v in values if "value" in v]
    if len(peers) < 40:
        return ""
    ours = [float(v["value"]) for v in values if v.get("highlight") and "value" in v]
    if not ours:
        return ""
    peers.sort()
    mid = len(peers) // 2
    median = (peers[mid] if len(peers) % 2
              else (peers[mid - 1] + peers[mid]) / 2)
    gap = ours[0] - median
    money = card["answer_text"].count("$") > 0
    if money:
        med_txt = f"${abs(median):,.0f}"
        gap_txt = f"${abs(gap):,.0f}"
    elif card["answer_text"].count("%") > 0:
        med_txt = f"{abs(median):.1f}%"
        step = 0.1
        gap_txt = f"{abs(gap):.1f} points"
        if abs(gap) < step:
            gap_txt = f"{abs(gap):.2f} points"
    else:
        dec = 0 if abs(median) >= 10 else 1
        fmt = f"{{:,.{dec}f}}"
        med_txt = fmt.format(abs(median))
        gap_txt = fmt.format(abs(gap))
        if "100k" in card["answer_text"]:
            med_txt, gap_txt = f"{med_txt} crimes", f"{gap_txt} crimes"
    if abs(gap) < 1e-9:
        return ""
    side = "above" if gap > 0 else "below"
    title = card.get("chart", {}).get("title", {}).get("text", "").lower()
    cadence = " a month" if "rent" in title else ""
    return (f'<p class="meta" style="margin:.7rem 0 0">Half the peer group '
            f'sits under {med_txt}{cadence}. Connecticut is {gap_txt} {side} '
            f'the middle.</p>')


def chart_intro(card: dict) -> tuple[str, str]:
    """(caption, aria-label) for a card's primary chart — the honest artwork
    line, shared by the story page and the home hero so the lead's picture
    is never a different sentence from the story's picture."""
    kind = card.get("chart_kind", "rank_strip")
    if card.get("stream") == "national":
        cadence = ("Quarterly" if card.get("series_freq") == "quarterly"
                   else "Monthly")
        desc = (f"{cadence} US series since the early 2000s; the latest "
                "print is labelled on the chart. Source and query below.")
        label = (f'US trend chart for “{card["question"]}”. '
                 f'{card["answer_text"]}')
        return desc, label
    if card.get("stream") == "local":
        # Derived from the chart's own data: a memorized sentence fitted
        # one dataset and lied about the next (it claimed grand-list
        # growth under a mill-rate chart for exactly one commit).
        chart = card.get("chart") or {}
        ct = chart.get("title") or {}
        what = ct.get("text") if isinstance(ct, dict) else str(ct)
        cd = (chart.get("data") or {}).get("values", [])
        hl = next((r.get("state") for r in cd if r.get("highlight")), None)
        desc = (f'{what or "Connecticut towns ranked"}; '
                f'{f"{hl} highlighted in orange" if hl else "ranked first to last"}'
                ". Source and query below.")
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
    return desc, label


def _vote_widget(card: dict) -> str:
    """First-party attention, no cookies: one beacon per page view, one vote
    per browser (localStorage). Counts are stored, never displayed — a young
    paper should not print its small numbers in public. Votes are explicit
    clicks only: an automatic page-view beacon records a reader’s presence
    without consent, and we removed ours (2026-10-06) rather than argue
    that first-party counts are not tracking."""
    vid = card["id"]
    return f"""<div class="vote"><span>Useful?</span>
<button data-v="u" aria-label="yes, mark this story useful"><svg class="bolt" viewBox="0 0 12 18" aria-hidden="true" style="width:.72em;height:1em;vertical-align:-.1em"><path fill="currentColor" d="M7.4 0 0 10.6h4.7L3.2 18l8.8-11.2H6.9L8.9 0z"/></svg> yes</button>
<button data-v="d" aria-label="no, not useful yet">&#9661; no</button></div>
<script>
(() => {{
  const k = "ctv:{vid}", id = "{vid}";
  const bs = document.querySelectorAll(".vote button");
  const lock = (d) => bs.forEach((b) => {{ b.disabled = true;
    if (b.dataset.v === d) b.setAttribute("data-chosen", ""); }});
  const done = localStorage.getItem(k);
  if (done) lock(done);
  else bs.forEach((b) => b.onclick = () => {{
    localStorage.setItem(k, b.dataset.v); lock(b.dataset.v);
    fetch("/api/vote", {{ method: "POST",
      body: JSON.stringify({{ id, dir: b.dataset.v === "u" ? "up" : "down" }}) }})
      .catch(() => {{}});
  }});
}})();
</script>"""


def _siblings_html(card: dict, cards: list[dict]) -> str:
    """Trigger-grouping: one headline can open several honest questions;
    the story pages point at each other instead of pretending to be alone."""
    url = (card.get("headline") or {}).get("url")
    if not url:
        return ""
    sibs = [c for c in (cards or [])
            if c.get("id") != card["id"]
            and (c.get("headline") or {}).get("url") == url]
    if not sibs:
        return ""
    lis = "".join(f'<li style="padding:.2rem 0">'
                  f'<a href="/story/{c["id"]}">{_ESC(c["question"])}</a></li>'
                  for c in sibs)
    return (f'<div class="card"><div class="label">Same headline, '
            f'more honest questions</div>'
            f'<ul style="list-style:none;margin:.2rem 0 0;padding:0">{lis}'
            f'</ul></div>')


_TOWN_METRIC = {"household_income": ("income", "income"),
                "poverty": ("poverty", "poverty"),
                "median_rent": ("rent", "gross rent"),
                "median_home_value": ("value", "home value")}


def _related_html(card: dict, cards: list[dict]) -> str:
    """Recirculation the desk can do honestly: same-desk links that exist,
    the town bridge that serves the tagline, and the board's own order for
    prev/next — no fabricated "related" guesses."""
    esc = html.escape
    lis = []
    for c in (cards or []):
        if c.get("id") != card["id"] and c.get("topic") == card.get("topic"):
            lis.append(f'<li style="padding:.15rem 0"><a href="/story/{c["id"]}">'
                       f'{esc(c["question"])}</a></li>')
            if len(lis) == 3:
                break
    town = _TOWN_METRIC.get(card.get("indicator"))
    if town:
        lis.append(f'<li style="padding:.15rem 0"><a href="/towns#m={town[0]}">'
                   f'Compare all 169 Connecticut towns by {town[1]} →</a></li>')
    else:
        lis.append('<li style="padding:.15rem 0"><a href="/towns">'
                   'See these measures for every Connecticut town →</a></li>')
    order = sorted((c for c in (cards or []) if c.get("generated_at")),
                   key=lambda c: c["generated_at"], reverse=True)
    ids = [c["id"] for c in order]
    pn = ""
    if card["id"] in ids:
        i = ids.index(card["id"])
        older = (f'<a href="/story/{ids[i + 1]}">Previous story →</a>'
                 if i + 1 < len(ids) else "")
        newer = (f'<a href="/story/{ids[i - 1]}">← Newer story</a>'
                 if i > 0 else "")
        pn = (f'<p class="meta" style="display:flex;justify-content:space-between;'
              f'gap:1rem;margin:.5rem 0 0">{newer}{older}</p>')
    return (f'<div class="card"><div class="label">Keep reading</div>'
            f'<ul style="margin:.2rem 0 0;padding-left:1.1rem">{"".join(lis)}</ul>'
            f'{pn}</div>')


def story_html(card: dict, siblings: list[dict] | None = None) -> str:
    q = _ESC(card["question"])
    a = _ESC(card["answer_text"])
    url = permalink(card)
    desc, label = chart_intro(card)
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
    shareline = ""
    if (config.ROOT / "assets" / f"share-{card['id']}.png").exists():
        shareline = ('<p class="meta" style="margin:.5rem 0 0">'
                     f'<a href="/assets/share-{card["id"]}.png">'
                     "Download this chart (PNG, 2×)</a>"
                     " &middot; rendered server-side from the same spec "
                     "you see above.</p>")
    kicker = (f'<a class="klink" href="/topic/{_ESC(card["topic"])}">'
              f'{_ESC(card["topic"])}</a> · {_ESC(card["stream"])} desk'
              f'{cache_badge}')
    og = _story_og(card)
    # On a story page the social cover IS the headline treatment: same words,
    # one voice, so the page matches its own preview instead of printing the
    # question twice.
    # The cover art repeats the question and answer inside pixels; the
    # real h1 and lede sit under it, visible, so text scales, selects
    # and survives reader modes. The art is decoration on top.
    hero_art, h1 = "", f'<h1 class="storyh1">{q}</h1>'
    cover = config.ROOT / "assets" / f"story-{card['id']}.png"
    if cover.exists():
        cv = hashlib.md5(cover.read_bytes()).hexdigest()[:8]
        hero_art = (f'<img class="storyhero" src="/assets/story-{card["id"]}.png?v={cv}"'
                    f' width="1200" height="630" alt="" role="presentation">')
    else:
        h1 = ('<h1 style="font:700 clamp(1.6rem,4vw,2.3rem)/1.2 '
              'var(--serif);margin:.4rem 0 .3rem">' + q + '</h1>')
    lede = f'<div class="answerbox">{a}</div>'
    body = f"""<div class="wrap col">
<div class="breadcrumb"><a href="/">← The board</a></div>
<div class="kicker">{kicker}</div>
{hero_art}{h1}
<div class="meta">Published {_pretty_time(card["generated_at"])} · CT Signal
automated data desk</div>
{lede}{_place_line(card)}{_vote_widget(card)}
<div class="card"><div class="label">The data</div>{chart}{chart2}{shareline}</div>
{_trigger_html(card)}
{_siblings_html(card, siblings)}
{_related_html(card, siblings)}
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
            image=og,
            modified=card.get("revalidated_at")))



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
{_pretty_time(c["generated_at"])}</div>
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
        src_prefix, trig = theme.trigger_parts(c)
        story = permalink(c)
        art = ""
        png = _cover_path(c)
        if png:
            art = (f'<enclosure url="{config.SITE_URL}/assets/story-{c["id"]}.png"'
                   f' length="{png.stat().st_size}" type="image/png"/>')
        desc = (f'{_ESC(c["answer_text"])}<br/><br/>'
                f'<a href="{story}">Read the full story with the chart and '
                f'the query</a><br/><br/>Source: {src_prefix}{trig}')
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
        h = c.get("headline") or {}
        src = f'{h["source"]} — ' if h.get("source") else ""
        trig = f' Source: {src}{h["title"]}' if h.get("title") else ""
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
    archive = []
    story_dir = config.ROOT / "story"
    live_ids = {c["id"] for c in cards}
    if story_dir.exists():
        for d in story_dir.iterdir():
            if d.is_dir() and (d / "index.html").exists() \
                    and d.name not in live_ids:
                archive.append(f'<url><loc>{config.SITE_URL}/story/{d.name}'
                               f'</loc><lastmod>{now}</lastmod></url>')
    parts.extend(archive)
    for topic, tcards in _topics(cards).items():
        newest = max(_day(c["generated_at"]) for c in tcards)
        parts.append(f'<url><loc>{config.SITE_URL}/topic/{topic}</loc>'
                     f'<lastmod>{newest}</lastmod></url>')
    for p in sorted(pages._PAGES):
        parts.append(f'<url><loc>{config.SITE_URL}/{p}</loc>'
                     f'<lastmod>{now}</lastmod></url>')
    parts.append(f'<url><loc>{config.SITE_URL}/towns</loc>'
                 f'<lastmod>{now}</lastmod></url>')
    parts.append(f'<url><loc>{config.SITE_URL}/archive</loc>'
                 f'<lastmod>{now}</lastmod></url>')
    # Town pages come from the desk's own snapshot, not from which cards
    # happen to name towns today: every built town page is a real page, and
    # the desk is the site's largest section. Cards may cite towns too —
    # those lastmods follow the card that cited them.
    built_towns = {d.name for d in (config.ROOT / "town").iterdir()
                   if d.is_dir() and (d / "index.html").exists()} \
        if (config.ROOT / "town").exists() else set()
    cited, card_day = set(), {}
    for c in cards:
        for row in (c.get("towns") or [])[:200]:
            slug = _slug(row["town"])
            cited.add(slug)
            card_day[slug] = max(card_day.get(slug, ""),
                                 _day(c["generated_at"]))
    for slug in sorted(built_towns):
        when = card_day.get(slug, now)
        parts.append(f'<url><loc>{config.SITE_URL}/town/{slug}</loc>'
                     f'<lastmod>{when}</lastmod></url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(parts) + '</urlset>\n')


def write_all(cards: list[dict]) -> None:
    """Idempotent: rebuilds every story page, archive copy, feeds, sitemap."""
    from . import pages, share

    pages.write_pages()
    assets = config.ROOT / "assets"
    assets.mkdir(exist_ok=True)
    util.atomic_write_text(assets / "site.css", theme.CSS)
    for card in cards:
        share.export(card, assets)   # before the story renders its link
        arch = config.ARCHIVE_DIR / card["generated_at"][:7]
        arch.mkdir(parents=True, exist_ok=True)
        # The archive page promises superseded vintages are "kept
        # forever" — an id-only filename silently overwrote the prior
        # version within the same month. Data date makes every print
        # of every card a durable, diffable artifact.
        stamp = str(card.get("answer_values", {}).get("date")
                    or card["generated_at"][:10]).replace(":", "-")
        (arch / f"{card['id']}-{stamp}.json").write_text(
            json.dumps(card, indent=2, sort_keys=True, default=str))
        story = config.STORY_DIR / card["id"]
        story.mkdir(parents=True, exist_ok=True)
        util.atomic_write_text(story / "index.html", story_html(card, cards))
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
    # One page per town, every local fact that town has: two cards may
    # measure the same place (grand-list growth and the current tax rate),
    # and last-writer-wins would silently drop one of them.
    by_town: dict[str, dict[str, tuple[dict, dict]]] = {}
    for c in cards:
        for row in (c.get("towns") or []):
            by_town.setdefault(row["town"], {})[c["indicator"]] = (row, c)
    for town, pieces in by_town.items():
        hd = troot / _slug(town)
        hd.mkdir(parents=True, exist_ok=True)
        util.atomic_write_text(hd / "index.html", town_html(town, pieces))
        util.atomic_write_text(hd / "feed.xml",
                               town_feed(town, _slug(town), cards))
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
    vers = sorted(set(config.ARCHIVE_DIR.glob(f"*/{card['id']}-*.json"))
                | set(config.ARCHIVE_DIR.glob(f"*/{card['id']}.json")))
    if len(vers) < 2:
        return ""
    return (f'<p class="meta">This story refreshes automatically with its '
            f'dataset &mdash; {len(vers)} archived vintages on record in '
            f'<a href="/archive">the public archive</a>.</p>')


_MY_TOWN_BTN = r"""
<span id="mt-wrap"></span>
<script>(function(){var s="%s",w=document.getElementById("mt-wrap"),cur=null;
try{cur=localStorage.getItem("ct-town");}catch(e){}
if(cur===s){w.innerHTML=' <button id="mt-b" class="ytbtn">\u2713 your town</button>'
 +' \u00b7 <a href="/towns">change</a>';
 w.querySelector("#mt-b").onclick=function(){try{localStorage.removeItem("ct-town");}catch(e){}
  w.innerHTML=' <a href="/towns">not that? pick on the towns page</a>';};}
else{w.innerHTML=' <button id="mt-b" class="ytbtn">Make this my town</button>';
 w.querySelector("#mt-b").onclick=function(){try{localStorage.setItem("ct-town",s);}catch(e){}
  w.innerHTML=' \u2713 saved \u00b7 <a href="/towns">view your numbers</a>';};}})();</script>"""


def town_feed(town: str, slug: str, cards: list[dict]) -> str:
    """A per-town Atom feed: the return channel a remembered town still
    lacks. Static, honest entries only — the stories that measure this town
    and the vintage of its data file. No database, no new service."""
    from . import towns as _tw
    snap = _tw.snapshot()
    fetched = (snap or {}).get("fetched_at", "")
    esc = html.escape
    base = f"{config.SITE_URL}/town/{slug}"
    bridge = set(_tw.STORY_FOR.values())          # stories every town file leans on
    entries, stamps = [], []
    def _rfc3339(iso: str) -> str:
        try:
            return util.parse_ts(iso).isoformat()
        except Exception:
            return ""
    for c in (cards or []):
        local = any((r.get("town") or "").lower() == town.lower()
                    for r in (c.get("towns") or []))
        if local or c["id"] in bridge:
            stamp = _rfc3339(c["generated_at"])
            stamps.append(stamp)
            href = f"{config.SITE_URL}/story/{c['id']}"
            entries.append(
                f"<entry><title>{esc(c['question'])}</title>"
                f'<link href="{href}"/><id>{href}</id>'
                f"<updated>{stamp}</updated>"
                f"<summary>{esc(c['answer_text'][:160])}</summary></entry>")
    if fetched:
        stamps.append(_rfc3339(fetched))
        entries.append(
            f"<entry><title>{esc(town)} data file current through "
            f"{esc((snap or {}).get('vintage', ''))}</title>"
            f'<link href="{base}"/>'
            f"<id>{base}?v={esc(fetched[:10])}</id>"
            f"<updated>{_rfc3339(fetched)}</updated>"
            "<summary>Every number on the town file, with its source "
            "and vintage.</summary></entry>")
    # <updated> must reflect the newest entry, not the snapshot date.
    updated = max((t for t in stamps if t), default=_rfc3339(
        dt.datetime.now(dt.timezone.utc).isoformat()))
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            f'<title>CT Signal \u2014 {esc(town)}</title>'
            f'<link href="{base}"/><link rel="self" '
            f'href="{base}/feed.xml"/>'
            f'<updated>{updated}</updated>'
            f'<id>{base}/feed.xml</id>{"".join(entries)}</feed>')


def town_html(town: str, pieces: dict) -> str:
    """A town file is assembled from every local card that measures it.

    Each section names its own dataset and links its own story, so the page
    can hold two numbers from two files without implying they came from one.
    """
    esc = html.escape
    from . import towns as _towns
    snap = _towns.snapshot()
    rec = _towns.lookup(snap, town) if snap else None
    acs = _towns.table_for(rec, snap, esc) if rec else ""
    acs_css = _towns._PAGE_CSS if rec else ""

    sections, facts = [], []
    gl = pieces.get("grand_list_growth") or pieces.get("equalized_grand_list")
    if gl:
        row, card = gl
        n = card.get("answer_values", {}).get("n") or len(card.get("towns") or [])
        med = sorted(r["pct"] for r in card.get("towns") or [])
        median = med[len(med) // 2] if med else 0.0
        sections.append(
            f'<h2>Property tax base</h2>'
            f'<p class="sub">Net grand list from the CT Open Data Portal, via '
            f'<a href="/story/{card["id"]}">this story</a>.</p>'
            f'<table class="towntab"><tbody>'
            f'<tr><td>Net grand list, {esc(str(card["answer_values"].get("date", "")))}</td>'
            f'<td>${row["latest"]:,.0f}</td></tr>'
            f'<tr><td>Net grand list, prior vintage</td><td>${row["prior"]:,.0f}</td></tr>'
            f'<tr><td>Change between the latest two assessment rolls</td>'
            f'<td>${row["added"]:,.0f} ({row["pct"]:+.1f}%)</td></tr>'
            f'<tr><td>Rank among {n} Connecticut places</td>'
            f'<td>{row["rank"]} of {n}</td></tr>'
            f'<tr><td>Statewide median change (for context)</td>'
            f'<td>{median:+.1f}%</td></tr>'
            f'</tbody></table>')
        facts.append(f'grand list ${row["latest"]:,.0f} ({row["pct"]:+.1f}%)')
    mr = pieces.get("mill_rates")
    if mr:
        row, card = mr
        av = card.get("answer_values", {})
        n = av.get("n") or len(card.get("towns") or [])
        fy = str(av.get("date", "")).replace("FY", "")
        rows = [
            f'<tr><td>Mill rate, FY{esc(fy)}</td>'
            f'<td>{row["rate"]:.2f} mills per $1,000</td></tr>',
            f'<tr><td>Rank among {n} Connecticut places</td>'
            f'<td>{row["rank"]} of {n}</td></tr>',
            f'<tr><td>Compared with the statewide rate</td>'
            f'<td>{row["vs_state"]:.2f}× the statewide average</td></tr>']
        if av.get("state"):
            rows.append('<tr><td>Statewide rate, weighted by taxable value'
                        f'</td><td>{av["state"]:.2f} mills</td></tr>')
        # mill rates are levied on ASSESSMENT, not market value; the card's
        # assess_ratio (from ODP's ten-mill land share) converts ACS value
        # into an honest estimate, labeled as one.
        if av.get("state") and rec and rec.get("value") and av.get("assess_ratio"):
            est = rec["value"] * av["assess_ratio"] * row["rate"] / 1000
            rows.append('<tr><td>Estimated tax on a median-value home'
                        f' (assessment {av["assess_ratio"] * 100:.0f}% of market '
                        f'per state law)</td>'
                        f'<td>${est:,.0f} a year</td></tr>')
        sections.append(
            '<h2>Property tax rate</h2>'
            '<p class="sub">Municipal mill rate for real property, fiscal year '
            f'{esc(fy)}, from the CT Open Data Portal via '
            '<a href="/story/' + card["id"] + '">this story</a>. '
            'Service-district rates are separate and not shown here.</p>'
            '<table class="towntab"><tbody>' + ''.join(rows) + '</tbody></table>')
        facts.append(f'mill rate {row["rate"]:.2f} ({row["vs_state"]:.2f}× state)')
    if not sections:
        return ""
    body = f"""{acs_css}<article class="wrap col">
<div class="label">Connecticut town file · <a href="/towns">all towns</a></div>
<h1 style="font:700 clamp(1.7rem,4vw,2.4rem)/1.15 var(--serif);margin:.4rem 0 .3rem">{esc(town)}</h1>
<p class="sub">Every local number the desk holds for this town, each naming its
own source. Know where you live.</p>
{''.join(sections)}
{acs}
<p class="meta">Dataset citations and the literal queries live on the linked
stories; errors are corrected publicly.</p>
</article>"""
    tslug = _slug(town)
    timg = f"{config.SITE_URL}/assets/town-{tslug}.png"
    if (config.ROOT / "assets" / f"town-{tslug}.png").exists():
        body = body.replace(
            '<p class="meta">Dataset citations',
            f'<p class="meta" style="margin:.5rem 0 0"><a href="{timg}">'
            'Share card for ' + esc(town) + ' (PNG, 1200×630)</a>'
            ' — generated from the numbers on this page. '
            f'<a href="/town/{tslug}/feed.xml">Subscribe</a>'
            ' to updates for this town (Atom).'
            + (_MY_TOWN_BTN % tslug) + '</p>'
            '<p class="meta">Dataset citations')
    title = f"{town} town file · CT Signal"
    # The og:description must match the share card the preview shows:
    # the same five numbers, the same vintage, no mill-rate surprise.
    from . import towns as _tw
    _b = _tw.briefs()
    _r = _b.get("towns", {}).get(_slug(town))
    if _r:
        _v = _r["v"]
        def _f(i, k):
            v = _v[i][0]
            if v is None:
                return "not published"
            if k == "poverty":
                return f"{v:.1f}%"
            if k == "age":
                return str(round(v))
            return (f"${v/1e6:.2f}M" if v >= 1_000_000
                    else f"${v:,.0f}")
        desc = (f"{town}, {_b['vintage']}: median household "
                f"income {_f(2, 'income')}, {_f(3, 'poverty')} "
                f"below poverty, median rent {_f(4, 'rent')}, "
                f"median home value {_f(5, 'value')}, median age "
                f"{_f(1, 'age')}.")
        desc = desc + " Ranks, sources and the town file: "
        desc += f"{config.SITE_URL}/town/{_slug(town)}"
    else:
        desc = f"{town}: " + "; ".join(facts) + "."
    page = theme.page(title=title, desc=esc(desc),
                      path=f'/town/{_slug(town)}', body=body,
                      image=(timg if (config.ROOT / 'assets' /
                               f'town-{tslug}.png').exists() else None))
    # Feed readers should find the town feed without a human clicking first.
    alt = (f'<link rel="alternate" type="application/atom+xml" '
           f'title="CT Signal \u2014 {esc(town)} (Atom)" '
           f'href="/town/{tslug}/feed.xml">')
    return page.replace("</head>", alt + "</head>", 1)


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
