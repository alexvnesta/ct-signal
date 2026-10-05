"""Standing source inventory.

Answers "are you current?" with a printed table, not a promise. Every
dataset we publish from or covet, its data-updated stamp at the portal,
and a live probe of which Census ACS releases exist yet — refreshed weekly
by the pipeline, committed as an artifact, rendered on /sources.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request

from . import config, util

STORED = config.ROOT / "data" / "inventory.json"
SCHEMA = 2   # bump when probe/field shape changes
SCHEMA = 2   # bump when probe/field shape changes
MAX_AGE_DAYS = 7

# Pinned by id. Roles: "consumed" (a card publishes from it) or "candidate"
# (credible future card, inventoried so a stale portal is visible anyway).
DATASETS = [
    ("webp-fgt3", "consumed", "Net grand list by town — the grand-list story"),
    ("8rr8-a322", "consumed", "Equalized net grand list — municipal finance"),
    ("xgef-f6jp", "candidate", "Municipal fiscal indicators — parked until "
                               "edition-aware filtering"),
    ("emyx-j53e", "candidate", "Mill rates FY2014–FY2027 — a tax-burden card "
                               "waits here"),
    ("he33-brru", "candidate", "Tax levy by municipality — the spending side"),
    ("ifrb-kp2b", "candidate", "Grand list components — commercial vs "
                               "residential split"),
]

ACS = {"acs5": "https://api.census.gov/data/{y}/acs/acs5/profile"
               "?get=NAME,DP05_0001E&for=state:09&key={k}",
       "acs1": "https://api.census.gov/data/{y}/acs/acs1/profile"
               "?get=NAME,DP05_0001E&for=state:09&key={k}"}


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def check(force: bool = False) -> dict | None:
    """Throttled to weekly; offline falls back to the committed artifact."""
    if STORED.exists() and not force:
        try:
            stored = json.loads(STORED.read_text())
            if int(stored.get("schema", 1)) < SCHEMA:
                return check(force=True)
            age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(
                stored["checked_at"])).days
            if age < MAX_AGE_DAYS:
                return stored
        except (ValueError, KeyError):
            pass
    year = dt.date.today().year
    acs = {}
    if config.CENSUS_API_KEY:
        for tag, tpl in ACS.items():
            for cand in range(year - 1, year - 4, -1):   # newest release wins
                if _get(tpl.format(y=cand, k=config.CENSUS_API_KEY)):
                    acs[tag] = str(cand)
                    break
    datasets = []
    for sid, role, note in DATASETS:
        d = _get(f"https://data.ct.gov/api/views/{sid}.json") or {}
        ru = d.get("rowsUpdatedAt")
        datasets.append({
            "id": sid, "role": role, "note": note, "name": d.get("name"),
            "updated": (dt.datetime.fromtimestamp(
                ru, dt.timezone.utc).isoformat(timespec="seconds")
                if ru else None)})
    out = {"schema": SCHEMA, "checked_at": dt.timezone and dt.datetime.now(
           dt.timezone.utc).isoformat(timespec="seconds"),
           "acs": acs, "datasets": datasets}
    util.atomic_write_text(STORED, json.dumps(out))
    return out


def table() -> str:
    """Freshness strip for /sources. Reads the artifact only — no network."""
    try:
        inv = json.loads(STORED.read_text())
    except (OSError, ValueError):
        return ""
    from html import escape as esc
    day = inv["checked_at"][:10]
    rows = ""
    for d in inv["datasets"]:
        stamp = d["updated"][:10] if d["updated"] else "unknown"
        rows += (f'<tr><td>{esc(d["name"] or d["id"])}'
                 f'<br><span class="dim">{esc(d["note"])}</span></td>'
                 f'<td>{"in use" if d["role"] == "consumed" else "inventoried"}</td>'
                 f'<td>{stamp}</td></tr>')
    acs = inv.get("acs") or {}
    year = int(day[:4])
    for tag, label, expected in (("acs1", "ACS 1-year (state board)", year - 2),
                                 ("acs5", "ACS 5-year (town desk)", year - 2)):
        latest = acs.get(tag)
        note = (f"probed {day}: latest release is {latest}" if latest
                else "probe unavailable this cycle")
        if latest and int(latest) < expected:
            note += (f" — {expected} is cataloged for release later this "
                     f"cycle and upgrades automatically")
        rows += (f'<tr><td>US Census Bureau — {label}'
                 f'<br><span class="dim">{note}</span></td>'
                 f'<td>in use</td><td>{latest or "?"}</td></tr>')
    return (f'<h2>Source freshness</h2><p class="sub">Portal-side "data '
            f'updated" stamps and live Census release probes, checked '
            f'{day} by the pipeline. Candidates are inventoried datasets '
            f'without a card yet — the backlog, visible.</p>'
            f'<table class="towntab"><thead><tr><th>Source</th><th>Status</th>'
            f'<th>Data updated</th></tr></thead><tbody>{rows}</tbody></table>')
