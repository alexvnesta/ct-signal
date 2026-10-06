from __future__ import annotations

import datetime as dt
import hashlib

from . import charts


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def display(indicator: dict, value: float) -> str:
    prefix = indicator.get("prefix", "")
    suffix = indicator.get("suffix", "")
    if "precision" in indicator:      # explicit decimals (weeks, indices)
        precision = f".{indicator['precision']}f"
    else:
        precision = ".1f" if indicator.get("unit") == "percent" else ",.0f"
    return f"{prefix}{value:{precision}}{suffix}"


_display = display


def is_demo_trigger(card: dict) -> bool:
    """True when a card's trigger headline is a labeled demo. The label
    style has drifted before ('jobs-report fixture' vs 'PBS NewsHour
    (fixture)'), so we test for the word, in any casing, not one exact
    spelling — a card that quietly stops admitting it is a demo is the
    worst kind of lie this site can tell."""
    src = (card.get("headline") or {}).get("source") or ""
    return "fixture" in src.lower()


def _card_id(indicator_id: str, question: str) -> str:
    return hashlib.sha1(f"{indicator_id}:{question}".encode()).hexdigest()[:12]


def _ordinal(n: int) -> str:
    """3 -> '3rd'. Used so low-is-better indicators phrase honestly:
    '3rd safest', not '#50 of 52'. Deterministic — no LLM in the sentence."""
    if 10 <= n % 100 <= 20:
        sfx = "th"
    else:
        sfx = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{sfx}"


def human_rank(indicator: dict, rank: int, n: int) -> str:
    """Direction-honest rank phrase for board chips: never a bare '#50 of 52'.
    Needs indicator['direction'] ('high'|'low') and optional
    indicator['superlative'] (e.g. 'safe' -> '3rd-safest')."""
    direction = indicator.get("direction", "high")
    sup = indicator.get("superlative")
    if direction == "low":
        word = _ordinal(n - rank + 1)
        return f"{word}-{sup or 'lowest'}"
    return f"{_ordinal(rank)}-highest"


def from_stackup(indicator: dict, proposal: dict, result: dict,
                 trend_rows: list[dict] | None = None) -> dict:
    question = proposal.get("question_override") or indicator["question"]
    display = _display(indicator, result["ct"]["value"])
    answer = indicator["answer"].format(
        value=display.strip("$") if indicator.get("prefix") else display,
        date=result["ct"]["date"][:4],
        rank=result["ct"]["rank"],
        n=result["n"],
        rank_word=_ordinal(result["ct"]["rank"]),
        low_word=_ordinal(result["n"] - result["ct"]["rank"] + 1),
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
        "chart2": (charts.state_map(result["rows"],
                                    title=indicator["title"],
                                    unit=indicator.get("unit", ""))
                   if kind == "rank_strip" else None),
        "citations": [
            result.get("citation")
            or f"https://datacommons.org/data/commons/{indicator['dcid']}",
        ],
        "query": result["query"],
        "cache": result.get("cache", False),
    }


def from_national(item: dict, proposal: dict, result: dict) -> dict:
    """A card about the national context, from a series with no state
    breakdown. No fake Connecticut angle, no invented peers: the answer
    says US, the trend chart is the picture, and the extreme phrase is
    computed, not written."""
    question = proposal.get("question_override") or item["question"]
    disp = _display(item, result["value"])
    answer = item["answer"].format(
        value=disp.strip("$") if item.get("prefix") else disp,
        date=result["date"],
        extreme=result["extreme"],
    )
    return {
        "id": _card_id(item["id"], question),
        "generated_at": _now(),
        "stream": "national",
        "topic": item["topic"],
        "indicator": item["id"],
        "headline": proposal["headline"],
        "question": question,
        "answer_text": answer,
        "answer_values": {"value": result["value"], "date": result["date"]},
        "series_freq": item.get("fred", {}).get("freq", "monthly"),
        "chart_kind": "trend",
        "chart": charts.trend(result["rows"], title=item["title"],
                              unit=item.get("unit", ""),
                              highlight_series=item.get("geo",
                                                        "United States")),
        "chart2": None,
        "citations": [result["citation"]],
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
        unit="% change", peer_word="Town",
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
        "answer_values": {"top": top, "n": result["n"],
                         "date": str(result["latest_year"])},
        "chart_kind": "rank_strip",
        "chart": spec,
        "citations": [
            f"https://data.ct.gov/d/{item['socrata_id']}",
        ],
        "query": result["query"],
        "towns": result.get("all"),
        "cache": False,
    }


def from_mill_rates(item: dict, proposal: dict, result: dict) -> dict:
    question = proposal.get("question_override") or item["question"]
    t = result["top"]
    answer = item["answer"].format(
        top_town=t["town"], rate=f"{t['rate']:.2f}",
        state=result["state_rate"], multiple=f"{t['multiple']:.1f}",
        n=result["n"], fiscal_year=result["fiscal_year"])
    spec = charts.rank_strip(
        result["rows"],
        title=f"{item.get('chart_label', 'Property tax rate')}, FY{result['fiscal_year']} (top 10 towns)",
        unit="mills per $1,000", peer_word="Town",
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
        "answer_values": {"top": t, "n": result["n"],
                          "state": result["state_rate"],
                          "assess_ratio": result.get("assess_ratio"),
                          "date": f"FY{result['fiscal_year']}"},
        "chart_kind": "rank_strip",
        "chart": spec,
        "citations": [f"https://data.ct.gov/d/{item['socrata_id']}"],
        "query": result["query"],
        "towns": result.get("all"),
        "cache": False,
    }
