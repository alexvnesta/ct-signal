from __future__ import annotations

import calendar
import hashlib
import html
import re

import feedparser
import requests

from . import config


def _source_name(url: str) -> str:
    for host, name in [
        ("ctmirror.org", "CT Mirror"),
        ("news.google.com", "Google News (CT)"),
        ("nytimes.com", "NYT U.S."),
        ("npr.org", "NPR"),
        ("pbs.org", "PBS NewsHour"),
    ]:
        if host in url:
            return name
    return url


def _clean(title: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(title)).strip()


def _safe_link(u) -> str:
    # feeds are third-party input: only http/https may become a clickable
    # href on our pages (a javascript:/data: link executes in our origin)
    return u if isinstance(u, str) and u.lower().startswith(
        ("http://", "https://")) else "" 


def fetch_feed(url: str) -> list[dict]:
    stream = "ct" if url in config.CT_FEEDS else "national"
    try:
        resp = requests.get(url, headers=config.UA, timeout=12)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  feed fetch failed ({url}): {type(exc).__name__}")
        return []
    parsed = feedparser.parse(resp.content)
    out: list[dict] = []
    for entry in parsed.entries[:12]:
        title = _clean(entry.get("title", ""))
        if not title:
            continue
        out.append(
            {
                "id": hashlib.sha1(title.lower().encode()).hexdigest()[:12],
                "title": title,
                "url": _safe_link(entry.get("link", "")),
                "source": _source_name(url),
                "published": str(entry.get("published", "") or entry.get("updated", "")),
                "published_sort": (
                    calendar.timegm(entry.published_parsed)
                    if entry.get("published_parsed") else 0
                ),
                "stream": stream,
            }
        )
    return out


def gather() -> list[dict]:
    seen: set[str] = set()
    headlines: list[dict] = []
    for url in [*config.CT_FEEDS, *config.NATIONAL_FEEDS]:
        for h in fetch_feed(url):
            if h["id"] in seen:
                continue
            seen.add(h["id"])
            headlines.append(h)
    return headlines
