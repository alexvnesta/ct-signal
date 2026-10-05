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


def _parse(text: str) -> list[dict]:
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 2 or not r[0][:4].isdigit() or r[1] in (".", ""):
            continue
        rows.append({"date": r[0][:7], "value": float(r[1])})
    rows.sort(key=lambda x: x["date"])
    return rows


def extreme_phrase(rows: list[dict], direction: str) -> str:
    """Deterministic superlative: compare the latest print to every earlier
    one. 'lowest on record' or 'lowest since <Month YYYY>' — always true of
    the series, never of a mood. No adjectives are invented here."""
    word = "lowest" if direction == "min" else "highest"
    better = (lambda v, m: v < m) if direction == "min" else (lambda v, m: v > m)
    latest, hist = rows[-1], rows[:-1]
    if not hist or not any(better(r["value"], latest["value"]) for r in hist):
        return f"{word} on record"
    for r in reversed(hist):
        if better(r["value"], latest["value"]) or r["value"] == latest["value"]:
            when = dt.date(int(r["date"][:4]), int(r["date"][5:7]), 1)
            return f"{word} since {when:%B %Y}"
    return f"{word} on record"


def observations(item: dict,
                 fixture: pathlib.Path | None = None) -> dict | None:
    """Latest print, full monthly history for the trend chart, and the
    honest extreme phrase — or None, and the cycle stays silent."""
    sid = item["fred"]["series"]
    rows, cached = None, False
    try:
        resp = requests.get(BASE, params={"id": sid}, timeout=30)
        resp.raise_for_status()
        rows = _parse(resp.text)
    except Exception:
        rows = None
    if not rows and fixture and fixture.exists():
        rows, cached = _parse(fixture.read_text()), True
    if not rows:
        return None
    latest = rows[-1]
    agency = item.get("agency", "US Bureau of Labor Statistics")
    return {
        "value": round(latest["value"], 3),
        "date": latest["date"],
        "rows": [{"date": r["date"], "series": "United States",
                  "value": round(r["value"], 2)} for r in rows[-360:]],
        "extreme": extreme_phrase(rows, item.get("extreme", "min")),
        "citation": f"https://fred.stlouisfed.org/series/{sid}",
        "query": f"FRED fredgraph.csv id={sid}; agency of record: {agency}",
        "cache": cached,
    }
