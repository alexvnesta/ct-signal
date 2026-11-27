"""Keyless FRED adapter: the national context layer.

CT Signal answers Connecticut against the country. Some of the country's
own series — JOLTS churn, jobless duration, labor's share of output — have
no state breakdown at all: they are the weather Connecticut lives in. Cards
built here carry stream "national" and say "US" in the answer, so the
Connecticut frame is never quietly abandoned; the question is honestly a
national one.

FRED is a redistribution layer, not a source of record: every citation
pairs the series with the agency the catalog names. The CSV endpoint needs
no key and no account: fredgraph.csv?id=SERIES.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import pathlib

import requests

BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"),
    ("DE", "Delaware"), ("DC", "District of Columbia"), ("FL", "Florida"),
    ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"), ("IL", "Illinois"),
    ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"), ("KY", "Kentucky"),
    ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"),
    ("MS", "Mississippi"), ("MO", "Missouri"), ("MT", "Montana"),
    ("NE", "Nebraska"), ("NV", "Nevada"), ("NH", "New Hampshire"),
    ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"),
    ("OK", "Oklahoma"), ("OR", "Oregon"), ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"), ("SC", "South Carolina"), ("SD", "South Dakota"),
    ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"), ("VT", "Vermont"),
    ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"),
]


def _parse(text: str, weekly: bool = False) -> list[dict]:
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 2 or not r[0][:4].isdigit() or r[1] in (".", ""):
            continue
        # Monthly series keep YYYY-MM; weekly ones (jobless claims) must
        # keep the full day or every print collapses into its month.
        rows.append({"date": r[0][:10] if weekly else r[0][:7],
                     "value": float(r[1])})
    rows.sort(key=lambda x: x["date"])
    return rows


def _period_label(row: dict, weekly: bool) -> str:
    when = dt.date.fromisoformat(
        row["date"] if len(row["date"]) == 10 else row["date"] + "-01")
    # A weekly series naming only the month reads as nonsense when
    # the print itself is inside that month — weeks say the day.
    return f"{when:%B %-d, %Y}" if weekly else f"{when:%B %Y}"


def extreme_phrase(rows: list[dict], direction: str,
                   weekly: bool = False) -> str:
    """Deterministic superlative: compare the latest print to every earlier
    one. 'lowest on record' or 'lowest since <Month YYYY>' — always true of
    the series, never of a mood. No adjectives are invented here."""
    word = "lowest" if direction == "min" else "highest"
    better = (lambda v, m: v < m) if direction == "min" else (lambda v, m: v > m)
    latest, hist = rows[-1], rows[:-1]
    if not hist:
        return f"{word} on record"
    prev = hist[-1]
    # Adjacent prints are a transition, not a superlative. Saying
    # "highest since September" when September itself was higher (or the
    # same) reads as a contradiction; name the move instead.
    if latest["value"] == prev["value"]:
        return f"unchanged from {_period_label(prev, weekly)}"
    if better(prev["value"], latest["value"]):
        return (f"down from {_period_label(prev, weekly)}"
                if direction == "max"
                else f"up from {_period_label(prev, weekly)}")
    if not any(better(r["value"], latest["value"]) for r in hist):
        return f"{word} on record"
    for r in reversed(hist):
        if better(r["value"], latest["value"]):
            return f"{word} since {_period_label(r, weekly)}"
    return f"{word} on record"


def observations(item: dict,
                 fixture: pathlib.Path | None = None) -> dict | None:
    """Latest print, full monthly history for the trend chart, and the
    honest extreme phrase — or None, and the cycle stays silent."""
    sid = item["fred"]["series"]
    weekly = item.get("fred", {}).get("freq") == "weekly"
    keep = 1040 if weekly else 360   # ~20 years of weeks, ~30 of months
    rows, cached = None, False
    try:
        resp = requests.get(BASE, params={"id": sid}, timeout=30)
        resp.raise_for_status()
        rows = _parse(resp.text, weekly=weekly)
    except Exception:
        rows = None
    if not rows and fixture and fixture.exists():
        rows, cached = _parse(fixture.read_text(), weekly=weekly), True
    if not rows:
        return None
    latest = rows[-1]
    agency = item.get("agency", "US Bureau of Labor Statistics")
    return {
        "value": round(latest["value"], 3),
        "date": latest["date"],
        "rows": [{"date": r["date"], "series": item.get("geo", "United States"),
                  "value": round(r["value"], 2)} for r in rows[-keep:]],
        "extreme": extreme_phrase(rows, item.get("extreme", "min"),
                                weekly=weekly),
        "citation": f"https://fred.stlouisfed.org/series/{sid}",
        "query": f"FRED fredgraph.csv id={sid}; agency of record: {agency}",
        "cache": cached,
    }


def state_stackup(
    cfg: dict,
    *,
    cache_path: pathlib.Path | None = None,
    max_age_hours: float = 6.0,
) -> dict | None:
    """50-state + DC monthly BLS LAUS seasonally adjusted comparison via FRED.

    Unifies the Connecticut board tile and story with the state CTUR series so
    the site never displays a lagging unadjusted Data Commons rate beside a
    fresh seasonally adjusted BLS rate. Cached on disk for `max_age_hours` so
    15-minute pulses stay polite to FRED and deterministic offline.
    """
    suffix = str(cfg.get("suffix") or "UR")
    agency = str(cfg.get("agency") or "US Bureau of Labor Statistics, Local Area Unemployment Statistics (seasonally adjusted)")
    if cache_path and cache_path.exists():
        try:
            saved = json.loads(cache_path.read_text())
            ts = saved.get("fetched_at")
            if ts:
                age_h = (dt.datetime.now(dt.timezone.utc)
                         - dt.datetime.fromisoformat(ts)).total_seconds() / 3600
                if age_h < max_age_hours and saved.get("rows") and saved.get("ct"):
                    return saved
        except (OSError, ValueError):
            pass

    name_by_id = {f"{code}{suffix}": name for code, name in US_STATES}
    since = (dt.date.today() - dt.timedelta(days=540)).isoformat()
    by_date: dict[str, dict[str, float]] = {}
    try:
        for i in range(0, len(US_STATES), 10):
            chunk = [f"{code}{suffix}" for code, _ in US_STATES[i:i + 10]]
            resp = requests.get(
                BASE, params={"id": ",".join(chunk), "cosd": since}, timeout=25)
            resp.raise_for_status()
            parsed = list(csv.reader(io.StringIO(resp.text)))
            if len(parsed) < 2:
                continue
            head = parsed[0]
            for row in parsed[1:]:
                if not row or not row[0][:4].isdigit():
                    continue
                d = row[0][:7]
                for h, v in zip(head[1:], row[1:]):
                    if h in name_by_id and v not in ("", "."):
                        try:
                            by_date.setdefault(d, {})[name_by_id[h]] = float(v)
                        except ValueError:
                            continue
    except Exception:
        if cache_path and cache_path.exists():
            try:
                saved = json.loads(cache_path.read_text())
                if saved.get("rows") and saved.get("ct"):
                    return {**saved, "cache": True}
            except (OSError, ValueError):
                pass
        return None

    target = next(
        (d for d in sorted(by_date, reverse=True) if len(by_date[d]) >= len(US_STATES)),
        None,
    )
    if not target or "Connecticut" not in by_date[target]:
        return None
    pairs = sorted(by_date[target].items(), key=lambda kv: (-kv[1], kv[0]))
    rows = [
        {"state": name, "value": round(val, 2), "rank": idx,
         "highlight": name == "Connecticut"}
        for idx, (name, val) in enumerate(pairs, 1)
    ]
    ct_row = next(r for r in rows if r["highlight"])
    result = {
        "ct": {"value": ct_row["value"], "rank": ct_row["rank"], "date": target},
        "n": len(rows),
        "rows": rows,
        "citation": f"https://fred.stlouisfed.org/series/CT{suffix}",
        "query": f"FRED fredgraph.csv 50 states + DC (<ST>{suffix}, {target}); agency of record: {agency}",
        "cache": False,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def state_trend(cfg: dict, months: int = 48) -> list[dict] | None:
    """Monthly Connecticut vs. United States seasonally adjusted trend via FRED."""
    ct_sid = f"CT{cfg.get('suffix', 'UR')}"
    us_sid = str(cfg.get("us_series") or "UNRATE")
    try:
        r_ct = requests.get(BASE, params={"id": ct_sid}, timeout=25)
        r_us = requests.get(BASE, params={"id": us_sid}, timeout=25)
        r_ct.raise_for_status()
        r_us.raise_for_status()
        ct_rows = _parse(r_ct.text)
        us_rows = _parse(r_us.text)
    except Exception:
        return None
    if len(ct_rows) < 12 or len(us_rows) < 12:
        return None
    out = [{"date": r["date"], "series": "Connecticut", "value": round(r["value"], 2)}
           for r in ct_rows[-months:]]
    out += [{"date": r["date"], "series": "United States", "value": round(r["value"], 2)}
            for r in us_rows[-months:]]
    return out
