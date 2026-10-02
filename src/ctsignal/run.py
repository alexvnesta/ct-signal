from __future__ import annotations

import argparse
import datetime as dt
import json
import time

from . import cards, charts, config, feeds, questions
from .sources import datacommons, socrata


def build_board(catalog: dict) -> dict:
    tiles = []
    for indicator in catalog.get("stackup", []):
        fixture = config.FIXTURES_DIR / f"dc_{indicator['id']}.json"
        try:
            result = datacommons.stackup(indicator, fixture=fixture)
        except Exception:
            result = None
        if not result:
            continue
        tiles.append({
            "id": indicator["id"],
            "title": indicator["title"],
            "topic": indicator["topic"],
            "value": cards.display(indicator, result["ct"]["value"]),
            "rank": result["ct"]["rank"],
            "n": result["n"],
            "date": result["ct"]["date"],
            "strip": charts.dot_strip(result["rows"], title="rank across the 52 peers"),
        })
    return {"tiles": tiles}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _asked_key(card: dict) -> str:
    # Key on the DATA date so a new vintage (ACS year roll, monthly BLS print)
    # refreshes the card, while re-proposals of the same vintage stay silent.
    vals = card.get("answer_values") or {}
    when = vals.get("date") or ""
    return f"{card['indicator']}:{card['question'][:80]}:{when}"


def answer_proposals(proposals: list[dict], catalog: dict, demo: bool) -> list[dict]:
    stackup_by_id = {i["id"]: i for i in catalog.get("stackup", [])}
    local_by_id = {i["id"]: i for i in catalog.get("local", [])}
    built = []
    for proposal in proposals:
        indicator_id = proposal.get("indicator_id")
        try:
            if proposal["stream"] == "stackup" and indicator_id in stackup_by_id:
                indicator = stackup_by_id[indicator_id]
                fixture = config.FIXTURES_DIR / f"dc_{indicator_id}.json"
                result = datacommons.stackup(indicator, fixture=fixture)
                if result is None:
                    print(f"  discard (no data): {indicator_id} <- {proposal['headline']['title'][:60]}")
                    continue
                trend_rows = None
                if indicator.get("trend"):
                    try:
                        trend_rows = datacommons.trend(indicator)
                    except Exception as exc:
                        print(f"  trend failed ({exc}); rank strip only")
                built.append(cards.from_stackup(indicator, proposal, result, trend_rows=trend_rows))
            elif proposal["stream"] == "local":
                item = local_by_id.get(indicator_id or "grand_list_growth")
                if item is None or not (item.get("columns") or indicator_id in (None, "grand_list_growth")):
                    print(f"  skip (no answerer yet): {indicator_id} <- {proposal['headline']['title'][:60]}")
                    continue
                cfg = item.get("columns") or socrata.GRAND_LIST_CFG
                fixture = None
                fx_path = config.FIXTURES_DIR / "grand_list.json"
                if demo and item["id"] == "grand_list_growth" and fx_path.exists():
                    fixture = json.loads(fx_path.read_text())
                try:
                    result = socrata.town_metric_growth(cfg)
                except Exception:
                    result = socrata.town_metric_growth(cfg, fixture=fixture) if fixture else None
                if result is None:
                    print(f"  discard (no data): {item['id']}")
                    continue
                if indicator_id is None:
                    proposal = {**proposal, "question_override": None}
                built.append(cards.from_local(item, proposal, result))
            else:
                print(f"  skip (no answerer yet): {indicator_id or proposal['stream']} <- {proposal['headline']['title'][:60]}")
        except Exception as exc:
            print(f"  error: {indicator_id}: {exc}")
    return built


def load_fixture_headlines() -> list[dict]:
    path = config.FIXTURES_DIR / "headlines.json"
    return _load_json(path, [])


def balance_by_topic(new_cards: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for card in new_cards:
        topic = card["topic"]
        score = card["headline"].get("published_sort") or 0
        current = best.get(topic)
        if current is None or score > (current["headline"].get("published_sort") or 0):
            best[topic] = card
    kept = list(best.values())
    for card in new_cards:
        if card not in kept:
            print(f"  balanced out (topic cap): {card['topic']} / {card['indicator']}")
    return kept


def run_cycle(catalog: dict, demo: bool, use_llm: bool = True) -> int:
    existing = _load_json(config.OUTPUT_DIR / "feed.json", {"cards": []})
    cards_by_id = {c["id"]: c for c in existing.get("cards", [])}
    asked = _load_json(config.ASKED_LOG_PATH, {})

    headlines = feeds.gather()
    if demo:
        seen = {h["id"] for h in headlines}
        headlines += [h for h in load_fixture_headlines() if h["id"] not in seen]
    print(f"[{_now()}] headlines={len(headlines)}")

    heuristic = questions.propose(headlines, catalog)
    proposals = heuristic
    if use_llm:
        try:
            llm = questions.propose_with_llm(headlines, catalog)
            llm_pairs = {(p["indicator_id"], p["headline"]["id"]) for p in llm}
            proposals = llm + [p for p in heuristic
                               if (p["indicator_id"], p["headline"]["id"]) not in llm_pairs]
            print(f"  proposals: {len(llm)} llm + {len(proposals) - len(llm)} heuristic")
        except Exception as exc:
            print(f"  llm skipped ({type(exc).__name__}: {exc}); heuristics only")

    new_cards = balance_by_topic(answer_proposals(proposals, catalog, demo))

    added = 0
    for card in new_cards:
        key = _asked_key(card)
        if key in asked:
            continue
        asked[key] = card["generated_at"]
        if card["id"] not in cards_by_id:
            added += 1
            print(f"  + card [{card['stream']}/{card['topic']}] {card['answer_text'][:90]}")
        else:
            print(f"  ~ refreshed [{card['stream']}/{card['topic']}] {card['answer_text'][:90]}")
        cards_by_id[card["id"]] = card

    config.ASKED_LOG_PATH.parent.mkdir(exist_ok=True)
    config.ASKED_LOG_PATH.write_text(json.dumps(asked, indent=2, sort_keys=True))
    ordered = sorted(cards_by_id.values(), key=lambda c: c["generated_at"], reverse=True)
    from . import publish

    publish.publish(ordered, build_board(catalog))
    print(f"  feed: {len(ordered)} cards (+{added} new)")
    return added


def main() -> None:
    parser = argparse.ArgumentParser(prog="ctsignal")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-min", type=float, default=15.0)
    parser.add_argument("--demo", action="store_true",
                        help="merge fixture headlines + fixture-backed answers")
    parser.add_argument("--no-llm", action="store_true",
                        help="heuristic proposer only (deterministic demo fallback)")
    args = parser.parse_args()

    catalog = questions.load_catalog()
    while True:
        run_cycle(catalog, demo=args.demo, use_llm=not args.no_llm)
        if args.once:
            break
        time.sleep(args.interval_min * 60)


if __name__ == "__main__":
    main()
