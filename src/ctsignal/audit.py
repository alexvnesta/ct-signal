"""Self-audit: broken links, heartbeat age, live probes.

The watcher gets watched. The pulse audits links every cycle (cheap, no
network); a separate daily workflow (watchdog.yml) adds live probes and a
heartbeat check — because if the pulse itself dies, only something on a
different trigger can notice.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import urllib.request

from . import config, util

STORED = config.ROOT / "data" / "watchdog.json"
PAGES = {"about", "corrections", "masthead", "sources", "towns"}


def internal_links() -> list[str]:
    """Every href/src that points at our own site must resolve to a built
    artifact. This is the check that catches 'we deleted a page and left a
    hundred corpses behind'."""
    root = config.ROOT
    seen_files = {p for p in (root / "story").iterdir() if p.is_dir()} \
        if (root / "story").exists() else set()
    broken = []

    def resolve(href: str, page: str) -> bool:
        href = href.split("#", 1)[0].split("?", 1)[0]
        if not href.startswith("/") or href == "":
            return True                       # external or relative-ish
        if href in ("/", ""):
            return (root / "index.html").exists()
        parts = href.strip("/").split("/")
        if parts[0] == "story" and len(parts) == 2:
            return (root / "story" / parts[1] / "index.html").exists()
        if parts[0] == "town" and len(parts) == 2:
            return (root / "town" / parts[1] / "index.html").exists()
        if parts[0] == "topic" and len(parts) == 2:
            return (root / "topic" / parts[1] / "index.html").exists()
        if len(parts) == 1 and parts[0] in PAGES:
            return (root / f"{parts[0]}.html").exists()
        if len(parts) == 1 and parts[0] in ("archive",):
            return (config.ARCHIVE_DIR / "index.html").exists()
        if len(parts) == 1 and "." in parts[0]:
            return (root / parts[0]).exists() or (root / "output" / parts[0]).exists()
        return True                            # api/ and unknown: not file-mapped

    html_files = [root / "index.html", root / "towns.html", root / "sources.html",
                  config.ARCHIVE_DIR / "index.html"]
    for sub in ("story", "town", "topic"):
        base = root / sub
        if base.exists():
            html_files += list(base.glob("*/*.html"))
    pat = re.compile(r'(?:href|src)="(/[^"]*)"')
    for f in html_files:
        if not f.exists():
            broken.append(f"missing page: {f.relative_to(root)}")
            continue
        rel = "/" + str(f.relative_to(root)).replace("index.html", "").rstrip("/")
        for href in pat.findall(f.read_text()):
            if not resolve(href, rel):
                broken.append(f"{rel} -> {href}")
    return sorted(set(broken))[:50]


def sitemap_gaps() -> list[str]:
    """Every built page must appear in sitemap.xml. A page the sitemap
    forgot is a page search never meets; this drifts silently."""
    sm = config.ROOT / "sitemap.xml"
    if not sm.exists():
        return ["sitemap.xml missing"]
    urls = set(re.findall(r"<loc>([^<]+)</loc>", sm.read_text()))
    base = config.SITE_URL.rstrip("/")
    gaps = []
    for sub in ("story", "town", "topic"):
        base_dir = config.ROOT / sub
        if not base_dir.exists():
            continue
        for d in base_dir.iterdir():
            if d.is_dir() and (d / "index.html").exists():
                if f"{base}/{sub}/{d.name}" not in urls:
                    gaps.append(f"{sub}/{d.name} missing from sitemap")
    return gaps[:25]


def heartbeat_age_hours() -> float | None:
    """Hours since the newest machine commit (feed/attention/pulse)."""
    try:
        out = subprocess.run(
            ["git", "log", "--format=%ct %s", "-n", "20", "origin/master"],
            cwd=config.ROOT, capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        return None
    for line in out.splitlines():
        ts, _, msg = line.partition(" ")
        if re.match(r"(feed:|attention:|pulse|heartbe|inventory)", msg, re.I):
            return round((dt.datetime.now(dt.timezone.utc).timestamp()
                          - int(ts)) / 3600, 1)
    return None


def live_probes() -> dict:
    out = {}
    for path in ("/", "/board.json", "/towns", "/feed.xml"):
        try:
            with urllib.request.urlopen(config.SITE_URL + path, timeout=25) as r:
                out[path] = r.status
        except Exception as e:
            out[path] = type(e).__name__
    return out


def run(live: bool = True) -> dict:
    report = {"checked_at": dt.datetime.now(dt.timezone.utc)
              .isoformat(timespec="seconds"),
              "broken_links": internal_links(),
              "sitemap_gaps": sitemap_gaps(),
              "heartbeat_age_hours": heartbeat_age_hours()}
    if live:
        report["probes"] = live_probes()
    util.atomic_write_text(STORED, json.dumps(report))
    return report


def healthy(report: dict) -> bool:
    if report["broken_links"] or report.get("sitemap_gaps"):
        return False
    # 26h, not 6h: commits happen when data changes, and a healthy desk
    # can go a quiet day without one. Silence beyond a full day-plus is
    # the only honest death signal from out here.
    if report.get("heartbeat_age_hours") is None or \
            report["heartbeat_age_hours"] > 26:
        return False
    return all(str(v) == "200" for v in report.get("probes", {}).values())


if __name__ == "__main__":
    import sys
    rep = run(live="--live" in sys.argv)
    print(json.dumps(rep, indent=1))
    sys.exit(0 if healthy(rep) else 1)
