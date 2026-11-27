"""Newsroom site layer: story pages, archive, RSS, JSON feed, sitemap.

Durable, linkable objects — the atom of a news site — published beside the
rolling feed. Everything is static and committed, so git history doubles as
the audit trail. Absolute URLs (canonical, OG, RSS) use SITE_URL; on-site
navigation stays root-relative so the deploy preview works on any host.
"""
from __future__ import annotations

import csv
import datetime as dt
import email.utils
import html
import io
import json
import re
import shutil

import yaml

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


def _short_date(ts: str) -> str:
    d = util.et(ts)
    return f"{d:%B} {d.day}, {d.year}"


def _data_date(value) -> str:
    """Human label for the observation date carried by a card. Annual
    vintage ('2025'), monthly ('2026-10'), daily ('2026-11-21'), and the
    local fiscal label ('FY2027') all stay honest instead of being forced
    into one timestamp shape."""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            d = dt.date.fromisoformat(text)
            return f"{d:%B} {d.day}, {d.year}"
        if re.fullmatch(r"\d{4}-\d{2}", text):
            d = dt.date.fromisoformat(text + "-01")
            return f"{d:%B} {d.year}"
        if re.fullmatch(r"\d{4}", text):
            return text
    except ValueError:
        pass
    return text


def _headline_date(value: str) -> str:
    """Compact month form for display type; the byline keeps the full date."""
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            d = dt.date.fromisoformat(value)
            return f"{d:%b} {d.day}, {d.year}"
        if re.fullmatch(r"\d{4}-\d{2}", value):
            d = dt.date.fromisoformat(value + "-01")
            return f"{d:%b} {d.year}"
    except ValueError:
        pass
    return value


def _display_prose(text: str) -> str:
    """Render prose dates the way people say them. The card JSON keeps ISO
    for machines; the page keeps months for readers."""
    return re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?\b",
                  lambda m: _data_date(m.group(0)), str(text))


def _finding(card: dict) -> str:
    """The headline is the finding, not the standing question. Derived from
    the answer so every page is reproducible from its own card JSON; the
    question survives as the deck, never as a duplicated H1."""
    raw = str(card.get("answer_text") or card.get("question") or "").strip()
    # The answer often carries a receipt tail after an em dash; the headline
    # needs the finding before it.
    raw = raw.split(" — ")[0]
    # First sentence only, so a reporting caveat does not become display type.
    raw = re.split(r"(?<=[.!?])\s+", raw)[0]
    # Peer-rank comparisons belong in the lede, not the headline.
    raw = re.sub(r",\s+(?:the\s+)?\d+(?:st|nd|rd|th)-[A-Za-z][A-Za-z-]*"
                 r"\s+of\s+\d+\s+peers\.?$", "", raw)
    raw = re.sub(r",\s+the fastest growth of \d+ towns\.?$", "", raw)
    raw = re.sub(r",\s+adding \$[\d.]+[BMK]\.?$", "", raw)
    raw = re.sub(r",\s+\d+(?:\.\d+)? times .*\.?$", "", raw)
    # A few indicators use a town-first preamble. This is a plain-language
    # compression of the same fact, not a second claim.
    raw = re.sub(r"\bled the \d+ towns measured in\b",
                 "led Connecticut towns in", raw)
    # Raw ISO dates belong in JSON, not display type.
    raw = re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?\b",
                 lambda m: _headline_date(m.group(0)), raw)
    # If a future template still produces a long line, fall back to the
    # first comma clause rather than letting the H1 run to four lines.
    if len(raw) > 95:
        cut = raw.find(", ")
        if cut >= 55:
            raw = raw[:cut]
    raw = raw.rstrip(" .")
    return raw or str(card.get("question") or "").strip()


def _story_lede(card: dict) -> str:
    """Continuation lede that avoids repeating the H1 finding word-for-word.
    Derived strictly from answer_text without inventing numbers or claims."""
    full = _display_prose(str(card.get("answer_text") or "")).strip()
    if not full:
        return ""
    finding = _finding(card)
    if finding and full.startswith(finding + ", "):
        tail = full[len(finding) + 2:].strip()
        if tail.startswith("the "):
            if "peer" in tail:
                return "That ranks " + tail[4:]
            return "That is " + tail
        return "That is " + tail
    if " — " in full:
        tail = full.split(" — ", 1)[1].strip()
        if tail:
            return tail[:1].upper() + tail[1:]
    if ", adding " in full:
        tail = full.split(", adding ", 1)[1].strip()
        if tail:
            return f"Across the towns measured, that added {tail}"
    return full


def _chart_svg_src(card: dict) -> str | None:
    """Cache-busted URL for a card's server-rendered paper SVG, or None."""
    svg = config.ROOT / "assets" / f"chart-{card['id']}.svg"
    if not svg.exists():
        return None
    stamp = svg.with_name(svg.name + ".ver")
    try:
        ver = f"?v={stamp.read_text().strip()[:12]}"
    except OSError:
        ver = ""
    return f"/assets/chart-{card['id']}.svg{ver}"


def permalink(card: dict) -> str:
    return f"{config.SITE_URL}/story/{card['id']}"


def _spec_json(obj) -> str:
    # Chart islands are JSON-in-HTML: neutralize both "</" and "<!--" so no
    # external string (town names, feed text inside altair data) can flip the
    # parser state; absolute us.json for deep story pages.
    blob = json.dumps(obj, sort_keys=True, default=str).replace("</", "<\\/")
    blob = blob.replace("<!--", "<\\u0021--")
    return blob.replace('"us.json"', f'"{_ESC(config.SITE_URL)}/us.json"')



def _trigger_html(card: dict) -> str:
    prefix, title = theme.trigger_parts(card)
    return (f'<div class="card"><h2 class="label">Source</h2>'
            f'<div style="font-size:1.05rem;line-height:1.35">{prefix}{title}</div></div>')


def _provenance_html(card: dict) -> str:
    cites = "<br>".join(f'<a href="{_ESC(c)}">{_ESC(c)}</a>' for c in card["citations"])
    vals = card.get("answer_values") or {}
    if vals.get("date"):
        data_date = f' · data as of <b>{_ESC(_data_date(str(vals.get("date"))))}</b>'
    else:
        data_date = ' · data vintage: see query above'
    cache = ' <span class="badge">cache</span>' if card.get("cache") else ""
    return (f'<div class="card provenance"><h2 class="label">'
            f'Provenance · fetched, never written</h2>'
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


def chart_intro(card: dict, *, on_home: bool = False) -> tuple[str, str]:
    """(caption, aria-label) for a card's primary chart — the honest artwork
    line, shared by the story page and the home hero so the lead's picture
    is never a different sentence from the story's picture."""
    kind = card.get("chart_kind", "rank_strip")
    src_tail = ("Source and query on the story page."
                if on_home else "Source and query below.")
    if card.get("stream") == "national":
        if card.get("series_freq") == "daily":
            chart = card.get("chart") or {}
            names = (((chart.get("encoding") or {}).get("color") or {})
                     .get("scale") or {}).get("domain") or []
            named = ("Bradley Intl (orange) and Danbury (gray)"
                     if names == ["Bradley Intl", "Danbury"]
                     else ", ".join(names) or "the stations")
            latest = (card.get("answer_values") or {}).get("date")
            tail = (f"the window ends {_display_prose(str(latest))}"
                    if latest else "the newest observation is at the right edge")
            desc = (f"Daily station readings, {named}, each measured against "
                    f"its own 1991–2020 normals; {tail}. {src_tail}")
            label = (f'Daily station trend chart for '
                     f'“{_display_prose(card["question"])}”. '
                     f'{_display_prose(card["answer_text"])}')
            return desc, label
        cadence = ("Quarterly" if card.get("series_freq") == "quarterly"
                   else "Monthly")
        desc = (f"{cadence} US series since the early 2000s; the newest "
                f"observation is at the right edge. {src_tail}")
        label = (f'US trend chart for “{_display_prose(card["question"])}”. '
                 f'{_display_prose(card["answer_text"])}')
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
                f". {src_tail}")
        label = (f'Town ranking chart for '
                 f'“{_display_prose(card["question"])}”. '
                 f'{_display_prose(card["answer_text"])}')
    elif kind == "trend":
        desc = ("Monthly series, Connecticut (orange) against the United "
                f"States average. {src_tail}")
        label = (f'Time-trend chart for '
                 f'“{_display_prose(card["question"])}”. '
                 f'{_display_prose(card["answer_text"])}')
    else:
        desc = ("Every peer ranked; Connecticut highlighted in orange. "
                f"{src_tail}")
        label = (f'Peer ranking chart for '
                 f'“{_display_prose(card["question"])}”. '
                 f'{_display_prose(card["answer_text"])}')
    return desc, label


def _vote_widget(card: dict) -> str:
    """First-party attention, no cookies: one beacon per page view, one vote
    per browser (localStorage). Counts are stored, never displayed — a young
    paper should not print its small numbers in public. Votes are explicit
    clicks only: an automatic page-view beacon records a reader’s presence
    without consent, and we removed ours (2026-10-06) rather than argue
    that first-party counts are not tracking."""
    vid = card["id"]
    return f"""<div class="vote"><span>Was this story useful?</span>
<button data-v="u" aria-label="yes, mark this story useful"><svg class="bolt" viewBox="0 0 12 18" aria-hidden="true" style="width:.72em;height:1em"><path fill="currentColor" d="M7.4 0 0 10.6h4.7L3.2 18l8.8-11.2H6.9L8.9 0z"/></svg> Yes</button>
<button data-v="d" aria-label="no, not useful yet">No</button></div>
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
                  f'<a href="/story/{c["id"]}">{_ESC(_finding(c))}</a></li>'
                  for c in sibs)
    return (f'<div class="card"><h2 class="label">Same headline, '
            f'more honest questions</h2>'
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
    desk_count = 0
    sib_url = (card.get("headline") or {}).get("url")
    sib_ids = {c["id"] for c in (cards or [])
               if c.get("id") != card["id"] and sib_url
               and (c.get("headline") or {}).get("url") == sib_url}
    for c in (cards or []):
        if (c.get("id") != card["id"] and c.get("topic") == card.get("topic")
                and c["id"] not in sib_ids):
            lis.append(f'<li style="padding:.15rem 0"><a href="/story/{c["id"]}">'
                       f'{esc(_finding(c))}</a></li>')
            desk_count += 1
            if desk_count == 3:
                break
    if not desk_count and card.get("topic"):
        lis.append(f'<li style="padding:.15rem 0"><a href="/topic/'
                   f'{esc(str(card["topic"]))}">{esc(_desk_label(card["topic"]))} '
                   'desk &rarr;</a></li>')
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
    return (f'<div class="card"><h2 class="label">Keep reading</h2>'
            f'<ul style="margin:.2rem 0 0;padding-left:1.1rem">{"".join(lis)}</ul>'
            f'{pn}</div>')


# --------------------------------------------------------- story context ---
# Phase 2 of the blog design: computed context, never generated filler. A
# "what changed" line is built only from two archived observations. "Why it
# matters" comes from an evergreen editorial file. "What to watch" appears
# only when the desk calendar actually carries a future event for the metric.
_CATALOG_CACHE: dict | None = None
_CONTEXT_CACHE: dict | None = None
_SEEDS_CACHE: list[dict] | None = None
_OBSERVATIONS_CACHE: dict | None = None

_TOWN_TABLE = {
    "mill_rates": ("rate", "Mill rate (mills per $1,000)", "rate"),
    "grand_list_growth": ("pct", "Net grand list growth (%)", "pct"),
    "equalized_grand_list": ("pct", "Equalized assessment growth (%)", "pct"),
}


def _catalog_index() -> dict:
    """Indicator metadata keyed by id, loaded once per render cycle."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        from . import questions
        try:
            catalog = questions.load_catalog()
        except (OSError, ValueError, yaml.YAMLError):
            catalog = {}
        _CATALOG_CACHE = {
            item["id"]: item
            for section in ("stackup", "local", "national")
            for item in catalog.get(section, [])
            if item.get("id")
        }
    return _CATALOG_CACHE


def _context_file() -> dict:
    """The editorial context file, loaded once per render cycle."""
    global _CONTEXT_CACHE
    if _CONTEXT_CACHE is None:
        path = config.ROOT / "catalog" / "context.yaml"
        try:
            data = yaml.safe_load(path.read_text())
        except (OSError, ValueError, yaml.YAMLError):
            data = {}
        _CONTEXT_CACHE = data or {}
    return _CONTEXT_CACHE


def _context_index() -> dict:
    """Evergreen editorial context, separate from the data catalog."""
    return _context_file().get("indicators", {}) or {}


def _desk_index() -> dict:
    """Evergreen desk explainers, keyed by topic id."""
    return _context_file().get("desks", {}) or {}


def _indicator_meta(card: dict) -> dict:
    return _catalog_index().get(str(card.get("indicator") or ""), {})


def _indicator_label(card: dict) -> str:
    meta = _indicator_meta(card)
    label = str(meta.get("title") or meta.get("chart_label") or "").strip()
    if not label:
        chart_title = (card.get("chart") or {}).get("title") or {}
        label = str(chart_title.get("text") if isinstance(chart_title, dict)
                    else chart_title or "").strip()
        label = re.sub(r"\s*\(top 10 towns\)\s*$", "", label, flags=re.I)
        label = re.sub(r",\s*(?:FY)?\d{4}\s*$", "", label)
    if not label:
        label = str(card.get("indicator") or "Indicator").replace("_", " ")
        label = label[:1].upper() + label[1:]
    return label


def _indicator_path(card: dict) -> str:
    return f"/indicator/{card.get('indicator') or 'unknown'}"


def _observation_key(value) -> int:
    """Comparable ordinal for every vintage label the cards carry: daily,
    monthly, annual, and the local fiscal year. Unknown labels stay at 0."""
    text = str(value or "").strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return int(dt.date.fromisoformat(text).strftime("%Y%m%d"))
        if re.fullmatch(r"\d{4}-\d{2}", text):
            return int(dt.date.fromisoformat(text + "-01").strftime("%Y%m%d"))
        if re.fullmatch(r"\d{4}", text):
            return int(text + "1231")
        fy = re.fullmatch(r"FY(\d{4})", text)
        if fy:
            return int(fy.group(1) + "0630")
    except ValueError:
        pass
    return 0


def _observation_records() -> dict:
    """Newest archived print per indicator per observation date. The raw
    archive is the audit trail; the rendered table never invents history."""
    global _OBSERVATIONS_CACHE
    if _OBSERVATIONS_CACHE is None:
        out: dict[str, dict[int, dict]] = {}
        for path in config.ARCHIVE_DIR.rglob("*.json"):
            try:
                rec = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            indicator = str(rec.get("indicator") or "")
            vals = rec.get("answer_values") or {}
            key = _observation_key(vals.get("date"))
            if not indicator or not key:
                continue
            slot = out.setdefault(indicator, {})
            prev = slot.get(key)
            if prev is None or str(rec.get("generated_at") or "") > \
                    str(prev.get("generated_at") or ""):
                slot[key] = rec
        _OBSERVATIONS_CACHE = out
    return _OBSERVATIONS_CACHE


def _prior_observation(card: dict) -> dict | None:
    """The newest archived observation strictly older than this card's data
    date. A newer archived print is not "prior" just because it has an older
    timestamp; only observation dates are compared."""
    vals = card.get("answer_values") or {}
    key = _observation_key(vals.get("date"))
    if not key or vals.get("value") is None:
        return None
    records = _observation_records().get(str(card.get("indicator") or ""), {})
    prior = [k for k in records if k < key]
    return records[max(prior)] if prior else None


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _value_text(meta: dict, value) -> str:
    from . import cards as _cards
    number = _num(value)
    if number is None:
        return _ESC(str(value))
    unit = str((meta or {}).get("unit") or "")
    try:
        if "precision" not in (meta or {}) and unit in ("index", "weeks"):
            base = f"{number:.1f}"
        else:
            base = _cards.display(meta or {}, number)
    except (KeyError, ValueError):
        base = f"{number:,.2f}".rstrip("0").rstrip(".")
    suffix = str((meta or {}).get("suffix") or "")
    if suffix:
        return base
    if unit == "%" or unit == "percent":
        return base + ("%" if not base.endswith("%") else "")
    if unit == "°F":
        return base + ("°F" if not base.endswith("°F") else "")
    if unit == "USD":
        return base if base.startswith("$") else "$" + base
    if unit == "index":
        return base
    if unit:
        return base + " " + unit
    return base


def _delta_text(meta: dict, delta: float) -> str:
    unit = str((meta or {}).get("unit") or "")
    size = abs(delta)
    if unit in ("percent", "%"):
        return f"{size:.1f} points"
    if unit == "USD":
        return f"${size:,.0f}"
    if unit == "°F":
        return f"{size:.1f}°F"
    if unit == "weeks":
        return f"{size:.1f} weeks"
    if unit == "claims":
        return f"{size:,.0f} claims"
    if unit == "index":
        return f"{size:.1f} points on the index"
    return f"{size:,.1f}"


def _what_changed_paragraph(card: dict) -> str:
    prior = _prior_observation(card)
    if not prior:
        return ""
    cur = card.get("answer_values") or {}
    pri = prior.get("answer_values") or {}
    current = _num(cur.get("value"))
    previous = _num(pri.get("value"))
    if current is None or previous is None:
        return ""
    meta = _indicator_meta(card)
    cur_date = _data_date(str(cur.get("date") or ""))
    pri_date = _data_date(str(pri.get("date") or ""))
    delta = current - previous
    cur_text = _value_text(meta, current)
    pri_text = _value_text(meta, previous)
    if abs(delta) < 1e-9:
        text = (f"The latest observation ({_ESC(cur_date)}) is "
                f"{cur_text}, unchanged from {pri_text} ({_ESC(pri_date)}).")
    else:
        direction = "up" if delta > 0 else "down"
        text = (f"The latest observation ({_ESC(cur_date)}) is {cur_text}, "
                f"{direction} {_delta_text(meta, delta)} from {pri_text} "
                f"({_ESC(pri_date)}).")
    if card.get("indicator") == "weather_anomaly":
        text += (" The anomaly is a trailing 30-day window, so this compares "
                 "consecutive daily vintages rather than two calendar months.")
    return f'<p>{text}</p>'


def _next_seed(card: dict) -> dict | None:
    """A future calendar hook for this indicator, if one exists. Past seeds
    are history and are not dressed up as a forecast."""
    global _SEEDS_CACHE
    if _SEEDS_CACHE is None:
        try:
            data = yaml.safe_load(config.SEEDS_PATH.read_text()) or {}
        except (OSError, ValueError, yaml.YAMLError):
            data = {}
        _SEEDS_CACHE = data.get("seeds", []) or []
    today = util.et(dt.datetime.now(dt.timezone.utc)).date()
    candidates = []
    for seed in _SEEDS_CACHE:
        if str(seed.get("indicator") or "") != str(card.get("indicator") or ""):
            continue
        try:
            when = dt.date.fromisoformat(str(seed.get("date") or ""))
        except ValueError:
            continue
        if today <= when <= today + dt.timedelta(days=90):
            candidates.append((when, seed))
    return min(candidates, key=lambda pair: pair[0])[1] if candidates else None


def _watch_paragraph(card: dict) -> str:
    seed = _next_seed(card)
    if not seed:
        return ""
    when = _data_date(str(seed["date"]))
    reason = str(seed.get("reason") or "").strip()
    if reason:
        return (f'<p>The next desk-calendar hook is {_ESC(reason)}, on '
                f'{_ESC(when)}. This page is rebuilt when the series prints '
                f'again.</p>')
    return (f'<p>The next desk-calendar hook is {_ESC(when)}. This page is '
            f'rebuilt when the series prints again.</p>')


def _context_html(card: dict) -> str:
    why = str((_context_index().get(str(card.get("indicator") or ""), {})
               or {}).get("why") or "").strip()
    changed = _what_changed_paragraph(card)
    watch = _watch_paragraph(card)
    parts = []
    if changed:
        parts.append(f'<h2 class="label">What changed</h2>{changed}')
    if why:
        parts.append(f'<h2 class="label">Why it matters</h2><p>{_ESC(why)}</p>')
    if watch:
        parts.append(f'<h2 class="label">What to watch</h2>{watch}')
    indicator = str(card.get("indicator") or "")
    if not indicator:
        return ""
    label = _ESC(_indicator_label(card))
    parts.append(
        f'<p class="meta"><a href="{_indicator_path(card)}">Read the '
        f'{label} indicator file →</a></p>')
    return f'<div class="card context">{"".join(parts)}</div>'


def _chart_values(card: dict) -> list[dict]:
    """Rows from a top-level data block or from each layer's nested data
    block. National trend charts put their series inside layer.data."""
    chart = card.get("chart") or {}
    rows = []
    for source in [chart] + list(chart.get("layer") or []):
        for block in (source.get("data"), source):
            vals = (block or {}).get("values")
            if isinstance(vals, list):
                rows.extend(r for r in vals if isinstance(r, dict))
    return rows


def _chart_csv(card: dict) -> str:
    """The chart's own rows as CSV. Same data the reader sees, no new
    fetch and no invented columns. Town charts store the place in `state`;
    the export names that column `town` so it reads correctly."""
    rows = _chart_values(card)
    if not rows:
        return ""
    town_rows = bool(card.get("towns"))

    def name(key: str) -> str:
        return "town" if town_rows and key == "state" else key

    skip = {"highlight", "short"}
    keys = []
    for key in ("date", "series", "town", "rank", "value"):
        if any(name(k) == key for row in rows for k in row):
            keys.append(key)
    for row in rows:
        for key in row:
            mapped = name(key)
            if (mapped not in keys and mapped not in skip
                    and not isinstance(row[key], (dict, list))):
                keys.append(mapped)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(keys)
    for row in rows:
        writer.writerow([
            row.get("state", "") if town_rows and key == "town"
            else row.get(key, "") for key in keys])
    return buf.getvalue()


def _table_cell(value, meta: dict, kind: str | None = None) -> str:
    number = _num(value)
    if number is None:
        return _ESC(str(value))
    if kind == "rate":
        return f"{number:,.2f}"
    if kind == "pct":
        return f"{number:.2f}%"
    unit = str((meta or {}).get("unit") or "")
    if unit == "USD":
        return f"${number:,.0f}"
    if unit in ("percent", "%"):
        return f"{number:.1f}%"
    if unit == "°F":
        return f"{number:.1f}°F"
    if unit == "per 100k":
        return f"{number:,.2f}"
    if unit == "index":
        return f"{number:.1f}"
    if unit in ("weeks", "claims"):
        return f"{number:,.1f}" if unit == "weeks" else f"{number:,.0f}"
    return f"{number:,.0f}" if abs(number) >= 100 else f"{number:.2f}"


def _table_shell(cols: list[tuple[str, str, bool]], rows: list[list[str]],
                 summary: str, note: str, caption: str) -> str:
    head = "".join(
        f'<th scope="col"{num_class}>{_ESC(label)}</th>'
        for label, _, numeric in cols
        for num_class in [' class="num"' if numeric else ""])
    body = "".join(
        '<tr>' + ''.join(
            f'<td{num_class}>{cell}</td>'
            for cell, (_, _, numeric) in zip(row, cols)
            for num_class in [' class="num"' if numeric else ""])
        + '</tr>'
        for row in rows)
    return (f'<details class="databox"><summary>{_ESC(summary)}</summary>'
            f'<div class="tablewrap"><table class="datatable">'
            f'<caption class="sr-only">{_ESC(caption)}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<p class="meta">{_ESC(note)}</p></details>')


def _data_table_html(card: dict) -> str:
    """A collapsed receipt for every chart with more than 12 rows. Town
    cards use the full 169-row snapshot; chart cards keep the complete short
    series and trim long series to the latest observations."""
    towns = [row for row in (card.get("towns") or []) if _is_town(row)]
    meta = _indicator_meta(card)
    if len(towns) > 12:
        indicator = str(card.get("indicator") or "")
        key, heading, kind = _TOWN_TABLE.get(
            indicator,
            ("value", _indicator_label(card), None),
        )
        if key == "value":
            first = towns[0]
            key = ("rate" if "rate" in first else
                   "pct" if "pct" in first else "value")
        rows = []
        for i, row in enumerate(towns):
            rank = row.get("rank", i + 1)
            rows.append([_ESC(str(rank)), _ESC(str(row.get("town") or "")),
                         _table_cell(row.get(key), meta, kind)])
        summary = f"See all {len(towns)} town rows behind the chart"
        note = ("The chart shows the ranked top 10; this table keeps every "
                "town row in the snapshot.")
        cols = [("Rank", "", False), ("Town", "", False),
                (heading, "", True)]
        return _table_shell(cols, rows, summary, note,
                            f"Town rows behind the chart: {heading}")

    chart_rows = _chart_values(card)
    if len(chart_rows) <= 12:
        return ""
    has_series = any(row.get("series") for row in chart_rows)
    has_rank = any(row.get("rank") is not None for row in chart_rows)
    truncated = False
    if len(chart_rows) > 60:
        truncated = True
        if has_series:
            groups: dict[str, list[dict]] = {}
            for row in chart_rows:
                groups.setdefault(str(row.get("series") or ""), []).append(row)
            chart_rows = [row for group in groups.values()
                          for row in group[-12:]]
        else:
            chart_rows = chart_rows[-24:]
    chart_rows = sorted(chart_rows,
                        key=lambda row: str(row.get("date") or ""))
    label = _indicator_label(card)
    unit = str(meta.get("unit") or "")
    if unit and unit not in label:
        label = f"{label} ({unit})"
    if has_series:
        cols = [("Date", "", False), ("Series", "", False),
                (label, "", True)]
        rows = [[_ESC(_data_date(str(row.get("date") or ""))),
                 _ESC(str(row.get("series") or "")),
                 _table_cell(row.get("value"), meta)] for row in chart_rows]
        count = len(rows)
        summary = (f"See all {count} observations behind the chart"
                   if not truncated
                   else f"See {count} recent observations behind the chart")
        note = ("Observations are listed by date; the chart holds the full "
                "series." if not truncated else
                "Latest 12 observations per series; the chart holds the full "
                "series.")
        answer_date = str((card.get("answer_values") or {}).get("date") or "")
        chart_date = max((str(row.get("date") or "") for row in chart_rows),
                         default="")
        if answer_date and chart_date and \
                _observation_key(answer_date) > _observation_key(chart_date):
            note += (f" Chart rows stop at {_ESC(_data_date(chart_date))}; "
                     f"the answer uses the {_ESC(_data_date(answer_date))} "
                     "vintage.")
    elif has_rank:
        townish = card.get("stream") == "local"
        cols = [("Rank", "", False),
                ("Town" if townish else "Peer", "", False),
                (label, "", True)]
        rows = [[_ESC(str(row.get("rank") or "")),
                 _ESC(str(row.get("state") or row.get("town") or "")),
                 _table_cell(row.get("value"), meta)] for row in chart_rows]
        count = len(rows)
        summary = f"See all {count} {'town' if townish else 'peer'} rows behind the chart"
        note = "Rank, peer, and value are carried straight from the chart data."
    else:
        cols = [("Date", "", False), (label, "", True)]
        rows = [[_ESC(_data_date(str(row.get("date") or ""))),
                 _table_cell(row.get("value"), meta)] for row in chart_rows]
        count = len(rows)
        summary = (f"See all {count} observations behind the chart"
                   if not truncated
                   else f"See the latest {count} observations behind the chart")
        note = ("The chart holds the complete series." if not truncated else
                "Latest 24 observations; the chart holds the complete series.")
    return _table_shell(cols, rows, summary, note,
                        f"Observations behind the chart: {label}")


def story_html(card: dict, siblings: list[dict] | None = None) -> str:
    q = _ESC(card["question"])
    a = _ESC(_story_lede(card))
    url = permalink(card)
    desc, label = chart_intro(card)
    desc, label = _display_prose(desc), _display_prose(label)
    chart = theme.viz(_spec_json(card["chart"]), "chart", label=label,
                      caption=desc, preview_src=_chart_svg_src(card))
    chart2 = ""
    if card.get("chart2"):
        chart2 = theme.viz(_spec_json(card["chart2"]), "chart2",
                           label=f'United States map, same data: '
                                 f'{_display_prose(card["answer_text"])}',
                           caption="Peer map; Connecticut outlined. "
                                   "AlbersUSA omits DC and Puerto Rico.")
    cache_badge = ' <span class="badge">cache</span>' if card.get("cache") else ""
    finding = _finding(card)
    vals = card.get("answer_values") or {}
    data_date = _data_date(vals.get("date"))
    actions: list[str] = []
    png = config.ROOT / "assets" / f"share-{card['id']}.png"
    if png.exists():
        stamp = png.with_name(png.name + ".ver")
        try:
            ver = f"?v={stamp.read_text().strip()[:12]}"
        except OSError:
            ver = ""
        actions.append(
            f'<a href="/assets/share-{card["id"]}.png{ver}">'
            'Download this chart (PNG, 2×)</a>')
    if _chart_csv(card):
        actions.append(
            f'<a href="{_indicator_path(card)}/observations.csv">'
            'Download the chart data (CSV)</a>')
    cite_text = (f'{finding}. CT Signal'
                 + (f' (data as of {data_date})' if data_date else '')
                 + f', {url}')
    actions.append(
        f'<button type="button" id="cite-btn" '
        f'data-cite="{_ESC(cite_text)}">Copy citation</button>')
    action_bar = (
        '<div class="chart-actions">' + "".join(actions) + '</div>'
        '<script>(function(){var b=document.getElementById("cite-btn");'
        'if(!b)return;function ok(){b.textContent="Citation copied";'
        'b.classList.add("cite-ok");setTimeout(function(){'
        'b.textContent="Copy citation";b.classList.remove("cite-ok");},2200);}'
        'function fb(t){var a=document.createElement("textarea");a.value=t;'
        'a.style.position="fixed";a.style.opacity="0";document.body.appendChild(a);'
        'a.select();try{document.execCommand("copy");ok();}catch(e){}a.remove();}'
        'b.onclick=function(){var t=b.dataset.cite||"";'
        'if(navigator.clipboard&&navigator.clipboard.writeText){'
        'navigator.clipboard.writeText(t).then(ok,function(){fb(t);});'
        '}else{fb(t);}};})();</script>'
    )
    kicker = (f'<a class="klink" href="/topic/{_ESC(card["topic"])}">'
              f'{_ESC(card["topic"])}</a> · {_ESC(card["stream"])} desk'
              f'{cache_badge}')
    og = _story_og(card)
    # The finding owns the H1; the standing question becomes the deck. The
    # 1200×630 social cover is kept out of the reading column so the page
    # opens with type, not a picture of type. It remains the OG artifact.
    meta = [f'Published {_pretty_time(card["generated_at"])}']
    rev = card.get("revalidated_at")
    if rev and str(rev) != str(card["generated_at"]):
        meta.append(f'Updated <time datetime="{rev}">{_ESC(_short_date(rev))}</time>')
    if data_date:
        meta.append(f'<b>Data as of {_ESC(_headline_date(str(vals.get("date"))))}</b>')
    meta.append('<a href="/masthead">Automated data desk</a>')
    story_meta = '<span class="sep">·</span>'.join(
        f'<span>{m}</span>' for m in meta)
    body = f"""<article class="wrap col story">
<div class="breadcrumb"><a href="/archive">← All stories</a></div>
<header class="storyhead">
<div class="kicker">{kicker}</div>
<h1 class="storyh1">{_ESC(finding)}</h1>
<p class="storyq">{q}</p>
<p class="storymeta">{story_meta}</p>
</header>
<p class="storylede">{a}</p>
{_place_line(card)}
<div class="card"><h2 class="label">The data</h2>{chart}{chart2}
{_data_table_html(card)}{action_bar}</div>
{_context_html(card)}
{_vote_widget(card)}
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
</article>"""
    return theme.page(
        title=f"{finding} · CT Signal",
        desc=card["answer_text"][:200],
        path=f"/story/{card['id']}",
        body=body, compact=True, og_type="article", og_title=finding,
        og_desc=card["answer_text"][:200], published=card["generated_at"],
        image=og,
        json_ld=theme.graph_json_ld(
            theme.article_json_ld(
                card_id=card["id"], headline=finding,
                description=card["answer_text"][:200],
                published=card["generated_at"], section=card["topic"],
                image=og,
                modified=card.get("revalidated_at")),
            theme.breadcrumb_json_ld([
                ("CT Signal", f"{config.SITE_URL}/"),
                ("Stories", f"{config.SITE_URL}/archive"),
                (finding, f"{config.SITE_URL}/story/{card['id']}"),
            ])))



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
<div class="answerbox" style="font-size:.95rem">{_ESC(_display_prose(card["answer_text"]))}</div>
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


def _observation_value(vals: dict) -> tuple[float, str] | None:
    """Comparable value for the vintage table: the card's direct value, or
    a local card's top-town growth when the card has no single statewide
    number."""
    if vals.get("value") is not None:
        number = _num(vals.get("value"))
        if number is not None:
            return number, "value"
    top = vals.get("top") or {}
    if top.get("pct") is not None:
        number = _num(top.get("pct"))
        if number is not None:
            return number, "top-growth"
    return None


def _indicator_vintages(card: dict) -> list[dict]:
    """Current and prior observation dates for one indicator. Only the
    newest archived print per observation date survives, because within a
    day repeated builds are deploy noise, not new data."""
    vals = card.get("answer_values") or {}
    key = _observation_key(vals.get("date"))
    current = _observation_value(vals)
    rows = []
    if key and current is not None:
        rows.append({"key": key, "date": vals.get("date"),
                     "value": current[0], "kind": current[1],
                     "published": card.get("generated_at")})
        records = _observation_records().get(str(card.get("indicator") or ""), {})
        for old_key in sorted((k for k in records if k < key), reverse=True)[:7]:
            old = records[old_key]
            value = _observation_value(old.get("answer_values") or {})
            if value is None:
                continue
            rows.append({"key": old_key,
                         "date": (old.get("answer_values") or {}).get("date"),
                         "value": value[0], "kind": value[1],
                         "published": old.get("generated_at")})
    return rows


def _indicator_vintages_html(card: dict) -> str:
    rows = _indicator_vintages(card)
    if len(rows) < 2:
        return ""
    meta = _indicator_meta(card)
    cells = []
    for row in rows:
        if row["kind"] == "top-growth":
            value = f"{row['value']:.1f}%"
        else:
            value = _value_text(meta, row["value"])
        published = (f'<time datetime="{_ESC(str(row["published"]))}">'
                     f'{_ESC(_short_date(str(row["published"])))}</time>'
                     if row.get("published") else "unknown")
        cells.append(
            f'<tr><td>{_ESC(_data_date(str(row["date"])))}</td>'
            f'<td class="num">{value}</td><td>{published}</td></tr>')
    return (f'<h2 class="label">Vintages on record</h2>'
            f'<div class="tablewrap"><table class="datatable vintages">'
            f'<thead><tr><th scope="col">Data as of</th>'
            f'<th scope="col" class="num">Value</th>'
            f'<th scope="col">Published</th></tr></thead><tbody>'
            + "".join(cells) + '</tbody></table></div>'
            f'<p class="meta">Each row is a different observation date. '
            f'Repeated builds of one vintage are not listed. The '
            f'<a href="/archive">public archive</a> keeps the raw JSON.</p>')


def indicator_html(card: dict) -> str:
    """A stable, evergreen URL for one measure: the current story, the
    computed change, why the measure matters, and every observation date on
    record. The page lives across cards and data refreshes."""
    label = _indicator_label(card)
    question = _ESC(card["question"])
    answer = _ESC(_display_prose(card["answer_text"]))
    finding = _ESC(_finding(card))
    vals = card.get("answer_values") or {}
    data_date = _data_date(str(vals.get("date") or ""))
    trail = []
    if data_date:
        trail.append(f'<b>Data as of {_ESC(data_date)}</b>')
    trail.append(f'Published {_ESC(_short_date(card["generated_at"]))}')
    meta = [f'Current story: <a href="/story/{card["id"]}">{finding}</a>',
            '<span class="sep">·</span> ' + ' &middot; '.join(trail)]
    desc, chart_label = chart_intro(card)
    chart = theme.viz(_spec_json(card["chart"]), "chart",
                      label=_display_prose(chart_label),
                      caption=_display_prose(desc),
                      preview_src=_chart_svg_src(card))
    why = str((_context_index().get(str(card.get("indicator") or ""), {})
               or {}).get("why") or "").strip()
    changed = _what_changed_paragraph(card)
    watch = _watch_paragraph(card)
    context = []
    if changed:
        context.append(f'<h2 class="label">What changed</h2>{changed}')
    if why:
        context.append(f'<h2 class="label">Why it matters</h2><p>{_ESC(why)}</p>')
    if watch:
        context.append(f'<h2 class="label">What to watch</h2>{watch}')
    context_html = ('<div class="card context">' + ''.join(context) +
                    '</div>') if context else ""
    vintages = _indicator_vintages_html(card)
    vintages_html = f'<div class="card">{vintages}</div>' if vintages else ""
    csv_link = (f'<p class="meta"><a href="{_indicator_path(card)}/observations.csv">'
                'Download the chart data (CSV)</a> · every row behind the chart.</p>'
                if _chart_csv(card) else "")
    body = f"""<article class="wrap col">
<div class="breadcrumb"><a href="/indicators">← All indicator files</a></div>
<header class="bloghead">
<div class="label">Indicator file</div>
<h1>{_ESC(label)}</h1>
<p class="blogdek">{question}</p>
<p class="storymeta">{''.join(f'<span class="long">{m}</span>' for m in meta)}</p>
</header>
<div class="card"><h2 class="label">Latest finding</h2>
<p class="indicator-finding">{answer}</p>
{chart}
{_data_table_html(card)}
{csv_link}
</div>
{context_html}
{vintages_html}
{_provenance_html(card)}
<p class="meta">Read <a href="/story/{card["id"]}">the full story</a> for the
news trigger and correction path. Every card on this site is reproducible
from its committed JSON.</p>
</article>"""
    url = f"{config.SITE_URL}{_indicator_path(card)}"
    ld = theme.graph_json_ld(
        {"@type": "WebPage",
         "@id": f"{url}#webpage",
         "url": url,
         "name": label,
         "description": (f"{card.get('question', '')} Latest finding: "
                         f"{card.get('answer_text', '')}")[:300],
         "isPartOf": {"@type": "WebSite", "@id": f"{config.SITE_URL}/#website"},
         "about": {"@type": "Thing", "name": label},
         "inLanguage": "en-US"},
        theme.breadcrumb_json_ld([
            ("CT Signal", f"{config.SITE_URL}/"),
            ("Indicator files", f"{config.SITE_URL}/indicators"),
            (label, url),
        ]))
    return theme.page(
        title=f"{label} · indicator file · CT Signal",
        desc=(f"{card.get('question', '')} Latest finding: "
              f"{card.get('answer_text', '')}")[:200],
        path=_indicator_path(card), body=body, compact=True,
        og_title=f"{label} — CT Signal", image=_story_og(card),
        json_ld=ld)


def indicators_html(cards: list[dict]) -> str:
    """Index of stable indicator pages, grouped by desk. This is a reading
    path into the measures themselves, not another feed."""
    current: dict[str, dict] = {}
    for card in sorted(cards, key=lambda c: c.get("generated_at", ""),
                       reverse=True):
        current.setdefault(str(card.get("indicator") or ""), card)
    groups: dict[str, list[dict]] = {}
    for card in current.values():
        groups.setdefault(str(card.get("topic") or ""), []).append(card)
    blocks = []
    for topic in sorted(groups):
        rows = sorted(groups[topic], key=lambda c: _indicator_label(c).lower())
        items = []
        for card in rows:
            vals = card.get("answer_values") or {}
            when = _data_date(str(vals.get("date") or ""))
            items.append(
                f'<li class="archive-item"><div class="archive-row">'
                f'<h3><a href="{_indicator_path(card)}">'
                f'{_ESC(_indicator_label(card))}</a></h3>'
                f'<span class="archive-meta">{_ESC(_desk_label(topic))} desk'
                + (f' · data as of {_ESC(when)}' if when else "") +
                f'</span></div>'
                f'<p class="archive-q">{_ESC(card["question"])}</p>'
                f'<p class="archive-q">Latest: '
                f'<a href="/story/{card["id"]}">{_ESC(_finding(card))}</a></p>'
                f'</li>')
        desk = _desk_index().get(topic) or {}
        blurb = str(desk.get("blurb") or "").strip()
        blocks.append(
            f'<h2 class="archive-month"><a href="/topic/{_ESC(topic)}">'
            f'{_ESC(_desk_label(topic))}</a></h2>'
            + (f'<p class="deskblurb">{_ESC(blurb)}</p>' if blurb else "")
            + f'<ul class="archive-list">{"".join(items)}</ul>')
    body = f"""<article class="wrap col">
<div class="breadcrumb"><a href="/">← The board</a></div>
<header class="bloghead">
<div class="label">Reference</div>
<h1>Indicator files</h1>
<p class="blogdek">{len(current)} stable pages, one for every measure the
desk currently answers. Each keeps the latest finding, the change from its
prior vintage, why the number matters, and the observation dates on record.</p>
</header>
{"".join(blocks)}
</article>"""
    ld = theme.graph_json_ld(
        {"@type": "CollectionPage",
         "@id": f"{config.SITE_URL}/indicators#webpage",
         "url": f"{config.SITE_URL}/indicators",
         "name": "CT Signal indicator files",
         "description": "Stable reference pages for every measure CT Signal "
                        "currently tracks.",
         "isPartOf": {"@type": "WebSite", "@id": f"{config.SITE_URL}/#website"},
         "inLanguage": "en-US"},
        theme.breadcrumb_json_ld([
            ("CT Signal", f"{config.SITE_URL}/"),
            ("Indicator files", f"{config.SITE_URL}/indicators"),
        ]))
    return theme.page(
        title="Indicator files · CT Signal",
        desc="Stable reference pages for every measure CT Signal tracks, "
             "with the current finding, prior vintage, and why it matters.",
        path="/indicators", body=body, compact=True,
        og_title="Indicator files — CT Signal", json_ld=ld)


def _topics(cards: list[dict]) -> dict:
    out: dict = {}
    for c in sorted(cards, key=lambda c: c["generated_at"], reverse=True):
        out.setdefault(c["topic"], []).append(c)
    return out


def _desk_label(topic: str) -> str:
    return topic.replace("-", " ").title()


def _desk_intro_html(topic: str) -> str:
    """Evergreen explainer for a desk, from catalog/context.yaml."""
    desk = _desk_index().get(topic) or {}
    blurb = str(desk.get("blurb") or "").strip()
    question = str(desk.get("question") or "").strip()
    if not blurb:
        return ""
    q = (f'<p class="meta">Standing question: {_ESC(question)}</p>'
         if question else "")
    return (f'<div class="card deskintro">'
            f'<h2 class="label">About this desk</h2>'
            f'<p>{_ESC(blurb)}</p>{q}</div>')


def _topic_chips(topics: list[str], active: str | None = None) -> str:
    links = ['<a href="/archive"%s>All</a>' % (
        ' aria-current="page"' if active is None else "")]
    for topic in topics:
        mark = ' aria-current="page"' if topic == active else ""
        links.append(f'<a href="/topic/{_ESC(topic)}"{mark}>'
                     f'{_ESC(_desk_label(topic))}</a>')
    return ('<nav class="topicchips" aria-label="Browse stories by desk">'
            + "".join(links) + "</nav>")


def _archive_item(card: dict) -> str:
    when = card.get("generated_at", "")
    date = _ESC(_short_date(when)) if when else "date unknown"
    topic = card.get("topic", "")
    return (
        f'<li class="archive-item">'
        f'<div class="archive-row">'
        f'<h3><a href="/story/{card["id"]}">{_ESC(_finding(card))}</a></h3>'
        f'<span class="archive-meta">'
        f'<a href="/topic/{_ESC(topic)}">{_ESC(_desk_label(topic))} desk</a> '
        f'&middot; {date}</span></div>'
        f'<p class="archive-q">{_ESC(card.get("question", ""))}</p></li>')


def _topic_files_html(topic: str, current: dict[str, dict] | None) -> str:
    """The stable reference files for one desk. These pages survive cards;
    the story list above them does not replace them."""
    entries = []
    for indicator, card in (current or {}).items():
        if indicator and str(card.get("topic") or "") == topic:
            entries.append((_indicator_label(card), indicator, card))
    if not entries:
        return ""
    entries.sort(key=lambda item: item[0].lower())
    rows = []
    for label, indicator, card in entries:
        when = str((card.get("answer_values") or {}).get("date") or "")
        date = _data_date(when) if when else ""
        rows.append(
            f'<li><a href="/indicator/{_ESC(indicator)}">{_ESC(label)}</a>'
            f'<span>{_ESC(date)}</span></li>' if date else
            f'<li><a href="/indicator/{_ESC(indicator)}">{_ESC(label)}</a>'
            f'<span>current</span></li>')
    return (f'<div class="card topicfiles"><h2 class="label">Indicator files'
            f'</h2><p class="meta">Stable reference pages for this desk: one '
            f'measure, its latest finding, and every vintage on record.</p>'
            f'<ul class="filelist">' + "".join(rows) + '</ul></div>')


def _archive_blocks(cards: list[dict]) -> str:
    months: dict[str, list[dict]] = {}
    for card in cards:
        months.setdefault(card.get("generated_at", "?")[:7], []).append(card)
    blocks = []
    for month in sorted(months, reverse=True):
        rows = sorted(months[month], key=lambda c: c.get("generated_at", ""),
                      reverse=True)
        try:
            label = f"{dt.date.fromisoformat(month + '-01'):%B %Y}"
        except ValueError:
            label = month
        blocks.append(
            f'<h2 class="archive-month">{_ESC(label)}</h2>'
            f'<ul class="archive-list">'
            + "".join(_archive_item(c) for c in rows) + "</ul>")
    return "".join(blocks)


def _item_list_json_ld(cards: list[dict]) -> dict:
    """The visible list, typed: search engines get the same order the page
    shows, with each finding as its own ListItem."""
    return {"@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i,
                 "url": f"{config.SITE_URL}/story/{c['id']}",
                 "name": _finding(c)}
                for i, c in enumerate(cards, start=1)]}


def topic_html(topic: str, cards: list[dict],
               topics: list[str] | None = None,
               current: dict[str, dict] | None = None) -> str:
    label = _ESC(_desk_label(topic))
    topics = topics or sorted({c.get("topic", "") for c in cards
                               if c.get("topic")})
    body = f"""<article class="wrap col">
<div class="breadcrumb"><a href="/archive">← All stories</a></div>
<header class="bloghead">
<div class="label">Topic desk</div>
<h1>{label}</h1>
<p class="blogdek">{len(cards)} finding{'s' if len(cards) != 1 else ''} from
this desk, newest first — each with its data vintage and the question behind
it.</p>
{_topic_chips(topics, topic)}
</header>
{_desk_intro_html(topic)}
{_archive_blocks(cards)}
{_topic_files_html(topic, current)}
</article>"""
    url = f"{config.SITE_URL}/topic/{topic}"
    ld = theme.graph_json_ld(
        {"@type": "CollectionPage",
         "@id": f"{url}#webpage", "url": url,
         "name": f"{_desk_label(topic)} stories — CT Signal",
         "description": f"All CT Signal findings on {_desk_label(topic)}: "
                        "charts, rankings, and the query behind every number.",
         "mainEntity": _item_list_json_ld(cards),
         "isPartOf": {"@type": "WebSite", "@id": f"{config.SITE_URL}/#website"},
         "inLanguage": "en-US"},
        theme.breadcrumb_json_ld([
            ("CT Signal", f"{config.SITE_URL}/"),
            ("Stories", f"{config.SITE_URL}/archive"),
            (_desk_label(topic), url),
        ]))
    return theme.page(
        title=f"{_desk_label(topic)} stories · CT Signal",
        desc=f"All CT Signal findings on {_desk_label(topic)}: charts, "
             "rankings, and the query behind every number.",
        path=f"/topic/{topic}", body=body, compact=True,
        og_title=f"{_desk_label(topic)} — CT Signal", json_ld=ld)



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
    parts.append(f'<url><loc>{config.SITE_URL}/indicators</loc>'
                 f'<lastmod>{now}</lastmod></url>')
    seen = set()
    for c in sorted(cards, key=lambda card: card.get("generated_at", ""),
                    reverse=True):
        indicator = str(c.get("indicator") or "")
        if not indicator or indicator in seen:
            continue
        seen.add(indicator)
        parts.append(f'<url><loc>{config.SITE_URL}{_indicator_path(c)}</loc>'
                     f'<lastmod>{_day(c["generated_at"])}</lastmod></url>')
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
            if not _is_town(row):
                continue
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
    global _OBSERVATIONS_CACHE
    from . import pages, share

    # Archive observations are written below. Start from disk, then refresh
    # after the loop so indicator pages see today's vintages too.
    _OBSERVATIONS_CACHE = None
    pages.write_pages()
    assets = config.ROOT / "assets"
    assets.mkdir(exist_ok=True)
    util.atomic_write_text(assets / "site.css", theme.CSS)
    for card in cards:
        share.export(card, assets)       # dark 2x PNG for social/download
        share.export_svg(card, assets)   # paper SVG for instant SSR paint
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
    history = _archive_index()
    _OBSERVATIONS_CACHE = None
    current_by_indicator: dict[str, dict] = {}
    for card in sorted(cards, key=lambda item: item.get("generated_at", ""),
                       reverse=True):
        current_by_indicator.setdefault(str(card.get("indicator") or ""),
                                        card)
    idir = config.ROOT / "indicator"
    idir.mkdir(parents=True, exist_ok=True)
    for indicator, card in sorted(current_by_indicator.items()):
        if not indicator:
            continue
        folder = idir / indicator
        folder.mkdir(parents=True, exist_ok=True)
        util.atomic_write_text(folder / "index.html", indicator_html(card))
        csv_text = _chart_csv(card)
        if csv_text:
            util.atomic_write_text(folder / "observations.csv", csv_text)
        else:
            stale_csv = folder / "observations.csv"
            if stale_csv.exists():
                stale_csv.unlink()
    live_indicators = set(current_by_indicator)
    for stale in idir.iterdir():
        if stale.is_dir() and stale.name not in live_indicators:
            shutil.rmtree(stale)
    root_ind = config.ROOT / "indicators"
    root_ind.mkdir(parents=True, exist_ok=True)
    util.atomic_write_text(root_ind / "index.html", indicators_html(cards))
    topics = sorted({c.get("topic", "") for c in history if c.get("topic")})
    tdir = config.ROOT / "topic"
    tdir.mkdir(exist_ok=True)
    for topic, tcards in _topics(history).items():
        hd = tdir / topic
        hd.mkdir(exist_ok=True)
        util.atomic_write_text(hd / "index.html",
                               topic_html(topic, tcards, topics,
                                          current_by_indicator))
    troot = config.ROOT / "town"
    # One page per town, every local fact that town has: two cards may
    # measure the same place (grand-list growth and the current tax rate),
    # and last-writer-wins would silently drop one of them.
    by_town: dict[str, dict[str, tuple[dict, dict]]] = {}
    for c in cards:
        for row in (c.get("towns") or []):
            if not _is_town(row):
                continue
            by_town.setdefault(row["town"], {})[c["indicator"]] = (row, c)
    for town, pieces in by_town.items():
        hd = troot / _slug(town)
        hd.mkdir(parents=True, exist_ok=True)
        util.atomic_write_text(hd / "index.html", town_html(town, pieces))
        util.atomic_write_text(hd / "feed.xml",
                               town_feed(town, _slug(town), cards))
    if troot.exists():
        live = {_slug(r["town"]) for c in cards
                for r in (c.get("towns") or []) if _is_town(r)}
        for stale in troot.iterdir():
            if stale.is_dir() and stale.name not in live:
                shutil.rmtree(stale)
    util.atomic_write_text(config.ARCHIVE_DIR / "index.html",
                           archive_html(cards, history))
    if cards:
        util.atomic_write_text(config.ROOT / "feed.xml", rss_xml(cards))
        util.write_json(config.ROOT / "feed.json", json.loads(json_feed(cards)))
        util.atomic_write_text(config.ROOT / "sitemap.xml", sitemap_xml(cards))


def _slug(name: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# A deck card can carry a statewide total alongside its 169 real town rows.
# That aggregate is a spreadsheet convenience, not a place page: rendering it
# produced a fake /town/total page (and sitemap entry) with no town identity.
_TOWN_AGGREGATES = {"total", "connecticut", "statewide"}


def _is_town(row: dict) -> bool:
    name = str(row.get("town") or "").strip().lower()
    return bool(name) and name not in _TOWN_AGGREGATES


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


def _town_lede(town: str, pieces: dict, rec: dict | None,
               snap: dict | None) -> str:
    """A short narrative top block built only from numbers on the page.

    Each sentence names its own dataset and vintage, so the lede never
    implies that a grand-list year, a mill-rate year and a Census five-year
    estimate came from one file.
    """
    from . import towns as _tw
    parts = []
    gl = pieces.get("grand_list_growth") or pieces.get("equalized_grand_list")
    if gl:
        row, card = gl
        n = card.get("answer_values", {}).get("n") or len(card.get("towns") or [])
        pct = row.get("pct")
        rank = row.get("rank")
        if pct is not None:
            verb = "grew" if pct >= 0 else "fell"
            s = (f"{_ESC(town)}'s net grand list {verb} {abs(pct):.1f}% "
                 "between the latest two assessment rolls")
            if rank and n:
                s += f", {_tw._ord(rank)}-highest of {n} Connecticut places"
            parts.append(s + ".")
    mr = pieces.get("mill_rates")
    if mr:
        row, card = mr
        av = card.get("answer_values", {})
        fy = str(av.get("date", "")).replace("FY", "")
        rate = row.get("rate")
        vs = row.get("vs_state")
        if rate is not None:
            s = (f"Its FY{fy} mill rate is {rate:.2f} mills per $1,000 of "
                 "taxable value")
            if vs is not None:
                s += f", {vs:.2f}× the statewide average"
            parts.append(s + ".")
    if rec:
        bits = []
        if rec.get("income") is not None:
            bits.append(f"median household income at ${rec['income']:,.0f}")
        if rec.get("poverty") is not None:
            bits.append(f"{rec['poverty']:.1f}% of residents below poverty")
        if bits:
            vintage = (snap or {}).get("vintage", "")
            parts.append(f"The Census Bureau's {vintage} estimate puts "
                         + " and ".join(bits) + ".")
    if not parts:
        return ""
    return f'<p class="townlede">{" ".join(parts)}</p>'


def _town_related_html(pieces: dict) -> str:
    """Cross-links from a town file to its indicator files and desks."""
    rows = []
    for indicator, (row, card) in sorted(pieces.items()):
        label = _indicator_label(card)
        date = str((card.get("answer_values") or {}).get("date") or "")
        if not date:
            date = _short_date(card.get("generated_at", ""))
        rows.append(
            f'<li><a href="/indicator/{_ESC(indicator)}">{_ESC(label)}</a>'
            f'<span>{_ESC(date)}</span></li>')
    topics = sorted({card.get("topic") for _, card in pieces.values()
                     if card.get("topic")})
    for topic in topics:
        rows.append(
            f'<li><a href="/topic/{_ESC(topic)}">{_ESC(_desk_label(topic))} '
            f'desk</a><span>desk</span></li>')
    rows.append('<li><a href="/towns">All 169 town files</a>'
                '<span>index</span></li>')
    return ('<div class="card related"><h2 class="label">Keep reading</h2>'
            '<ul class="filelist">' + "".join(rows) + '</ul></div>')


def _town_kpis_html(town: str, pieces: dict, rec: dict | None,
                    snap: dict | None) -> str:
    """Scannable 4-up summary strip at the top of every town page."""
    from . import towns as _tw
    cards: list[tuple[str, str, str]] = []
    mr = pieces.get("mill_rates")
    if mr:
        row, card = mr
        av = card.get("answer_values") or {}
        n = av.get("n") or len(card.get("towns") or [])
        fy = str(av.get("date", "")).replace("FY", "")
        cards.append((
            f"FY{fy} mill rate" if fy else "Mill rate",
            f'{row["rate"]:.2f}',
            f'{_tw._ord(row["rank"])}-highest of {n}',
        ))
        if av.get("state") and rec and rec.get("value") and av.get("assess_ratio"):
            est = rec["value"] * av["assess_ratio"] * row["rate"] / 1000
            cards.append((
                "Est. median home tax",
                f"${est:,.0f}/yr",
                f'70% of ${rec["value"]:,.0f}',
            ))
    if rec:
        n_acs = (snap or {}).get("n") or 169
        if rec.get("income") is not None:
            rk = rec.get("income_rank")
            cards.append((
                "Median income",
                f'${rec["income"]:,.0f}',
                f'{_tw._ord(rk)}-highest of {n_acs}' if rk else "ACS 5-yr",
            ))
        if rec.get("poverty") is not None:
            rk = rec.get("poverty_rank")
            cards.append((
                "Below poverty",
                f'{rec["poverty"]:.1f}%',
                f'{_tw._ord(rk)}-highest of {n_acs}' if rk else "ACS 5-yr",
            ))
    if len(cards) < 4:
        gl = pieces.get("grand_list_growth") or pieces.get("equalized_grand_list")
        if gl:
            row, card = gl
            n = card.get("answer_values", {}).get("n") or len(card.get("towns") or [])
            cards.append((
                "Grand list change",
                f'{row["pct"]:+.1f}%',
                f'{_tw._ord(row["rank"])}-highest of {n}',
            ))
    if not cards:
        return ""
    items = "".join(
        f'<div class="town-kpi"><div class="town-kpi-k">{_ESC(k)}</div>'
        f'<div class="town-kpi-v">{_ESC(v)}</div>'
        f'<div class="town-kpi-s">{_ESC(s)}</div></div>'
        for k, v, s in cards[:4]
    )
    return f'<div class="town-kpis" aria-label="{_ESC(town)} key figures">{items}</div>'


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
            f'<tr><td>Rank among {n} Connecticut places (1 = highest)</td>'
            f'<td>{_towns._ord(row["rank"])}-highest of {n}</td></tr>'
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
            f'<tr><td>Rank among {n} Connecticut places (1 = highest)</td>'
            f'<td>{_towns._ord(row["rank"])}-highest of {n}</td></tr>',
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
<div class="breadcrumb"><a href="/towns">← All 169 towns</a></div>
<div class="label">Connecticut town file</div>
<h1 style="font:700 clamp(1.85rem,4vw,2.5rem)/1.12 var(--serif);margin:.35rem 0 .3rem">{esc(town)}</h1>
<p class="sub">Every local number the desk holds for this town, each naming its
own source. Know where you live.</p>
{_town_kpis_html(town, pieces, rec, snap)}
{_town_lede(town, pieces, rec, snap)}
{''.join(sections)}
{acs}
{_town_related_html(pieces)}
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
    url = f"{config.SITE_URL}/town/{_slug(town)}"
    ld = theme.graph_json_ld(
        {"@type": "WebPage", "@id": f"{url}#webpage", "url": url,
         "name": title, "description": desc,
         "isPartOf": {"@type": "WebSite",
                      "@id": f"{config.SITE_URL}/#website"},
         "inLanguage": "en-US"},
        {"@type": "Place", "@id": f"{url}#place", "name": town,
         "containedInPlace": {"@type": "AdministrativeArea",
                              "name": "Connecticut"}},
        theme.breadcrumb_json_ld([
            ("CT Signal", f"{config.SITE_URL}/"),
            ("Towns", f"{config.SITE_URL}/towns"),
            (town, url),
        ]))
    page = theme.page(title=title, desc=esc(desc),
                      path=f'/town/{_slug(town)}', body=body, compact=True,
                      image=(timg if (config.ROOT / 'assets' /
                               f'town-{tslug}.png').exists() else None),
                      json_ld=ld)
    # Feed readers should find the town feed without a human clicking first.
    alt = (f'<link rel="alternate" type="application/atom+xml" '
           f'title="CT Signal \u2014 {esc(town)} (Atom)" '
           f'href="/town/{tslug}/feed.xml">')
    return page.replace("</head>", alt + "</head>", 1)


def _archive_index() -> list[dict]:
    """Newest surviving vintage per card, from the raw JSON audit trail."""
    seen: dict[str, tuple[str, dict]] = {}
    for path in config.ARCHIVE_DIR.rglob("*.json"):
        try:
            c = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        prev = seen.get(c["id"])
        if prev is None or c.get("generated_at", "") > prev[0]:
            seen[c["id"]] = (c.get("generated_at", ""), c)
    return [c for _, c in sorted(seen.values(),
                                key=lambda pair: pair[0], reverse=True)]


def archive_html(cards: list[dict], history: list[dict] | None = None) -> str:
    """Publication index: every card ever published, newest first, with the
    finding visible before the click. Raw JSON stays the audit trail."""
    history = history if history is not None else _archive_index()
    topics = sorted({c.get("topic", "") for c in history if c.get("topic")})
    body = f"""<article class="wrap col">
<header class="bloghead">
<div class="label">Stories</div>
<h1>Every story we&rsquo;ve published</h1>
<p class="blogdek">{len(history)} findings, kept forever &mdash; each with the
data vintage it was built from, and every vintage that superseded it. Raw
JSON lives in the repository; this page is the readable index.</p>
{_topic_chips(topics)}
</header>
{_archive_blocks(history)}
</article>"""
    url = f"{config.SITE_URL}/archive"
    ld = theme.graph_json_ld(
        {"@type": "CollectionPage",
         "@id": f"{url}#webpage", "url": url,
         "name": "Every story CT Signal has published",
         "description": "Every story CT Signal has published, with its finding, "
                        "desk and data vintage kept forever.",
         "mainEntity": _item_list_json_ld(history),
         "isPartOf": {"@type": "WebSite", "@id": f"{config.SITE_URL}/#website"},
         "inLanguage": "en-US"},
        theme.breadcrumb_json_ld([
            ("CT Signal", f"{config.SITE_URL}/"),
            ("Stories", url),
        ]))
    return theme.page(title="Stories · CT Signal",
                      desc="Every story CT Signal has published, with its "
                           "finding, desk and data vintage kept forever.",
                      path="/archive", body=body, compact=True, json_ld=ld)
