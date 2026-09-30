from __future__ import annotations

import datetime as dt
import hashlib

from . import charts


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _display(indicator: dict, value: float) -> str:
    prefix = indicator.get("prefix", "")
    suffix = indicator.get("suffix", "")
    precision = ".1f" if indicator.get("unit") == "percent" else ",.0f"
    return f"{prefix}{value:{precision}}{suffix}"


def _card_id(indicator_id: str, question: str) -> str:
    return hashlib.sha1(f"{indicator_id}:{question}".encode()).hexdigest()[:12]


def from_stackup(indicator: dict, proposal: dict, result: dict,
                 trend_rows: list[dict] | None = None) -> dict:
    question = proposal.get("question_override") or indicator["question"]
    display = _display(indicator, result["ct"]["value"])
    answer = indicator["answer"].format(
        value=display.strip("$") if indicator.get("prefix") else display,
        date=result["ct"]["date"][:4],
        rank=result["ct"]["rank"],
        n=result["n"],
    )
    if trend_rows:
        spec = charts.trend(
            trend_rows, title=indicator["title"], unit=indicator.get("unit", "")
        )
        kind = "trend"
    else:
        spec = charts.rank_strip(
            result["rows"], title=indicator["title"], unit=indicator.get("unit", "")
        )
        kind = "rank_strip"
    return {
        "id": _card_id(indicator["id"], question),
        "generated_at": _now(),
        "stream": "stackup",
        "topic": indicator["topic"],
        "indicator": indicator["id"],
        "headline": proposal["headline"],
        "question": question,
        "answer_text": answer,
        "answer_values": result["ct"],
        "chart_kind": kind,
        "chart": spec,
        "citations": [
            f"https://datacommons.org/data/commons/{indicator['dcid']}",
        ],
        "query": result["query"],
        "cache": result.get("cache", False),
    }


def from_local(item: dict, proposal: dict, result: dict) -> dict:
    question = proposal.get("question_override") or item["question"]
    top = result["top"][0]
    answer = item["answer"].format(
        top_town=top["town"],
        added=f"{top['added'] / 1e9:,.2f}B",
        pct=f"{top['pct']:.1f}",
        latest_year=result["latest_year"],
        n=result["n"],
    )
    spec = charts.rank_strip(
        result["rows"],
        title=f"{item.get('chart_label', 'Net grand list growth')}, {result['latest_year']} (top 10 towns)",
        unit="% change",
    )
    return {
        "id": _card_id(item["id"], question),
        "generated_at": _now(),
        "stream": "local",
        "topic": item["topic"],
        "indicator": item["id"],
        "headline": proposal["headline"],
        "question": question,
        "answer_text": answer,
        "answer_values": {"top": top, "n": result["n"]},
        "chart_kind": "rank_strip",
        "chart": spec,
        "citations": [
            f"https://data.ct.gov/d/{item['socrata_id']}",
        ],
        "query": result["query"],
        "cache": False,
    }
