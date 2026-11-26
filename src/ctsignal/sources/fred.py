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
import pathlib

import requests

BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"


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
