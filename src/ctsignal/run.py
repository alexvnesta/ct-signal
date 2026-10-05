from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time

from . import cards, charts, config, feeds, questions, util
from .sources import census1yr, datacommons, socrata


def build_board(catalog: dict) -> dict:
    tiles = []
    for indicator in catalog.get("stackup", []):
        fixture = config.FIXTURES_DIR / f"dc_{indicator['id']}.json"
        result = None
        if indicator.get("census1yr"):
            result = census1yr.stackup(
                indicator["census1yr"],
                fixture=config.FIXTURES_DIR / f"census1yr_{indicator['id']}.json")
        if result is None:
            try:
                result = datacommons.stackup(indicator, fixture=fixture)
            except Exception as exc:
                print(f"  board tile failed: {indicator['id']} "
                      f"({type(exc).__name__}: {exc})")
                result = None
        if not result:
            continue
        tiles.append({
            "id": indicator["id"],
            "title": indicator["title"],
            "topic": indicator["topic"],
            "value": cards.display(indicator, result["ct"]["value"]),
            "rank": result["ct"]["rank"],
            "rank_label": cards.human_rank(indicator, result["ct"]["rank"],
                                           result["n"]),
            "n": result["n"],
            "date": result["ct"]["date"],
            "strip": charts.shape_strip(result["rows"]),
        })
    return {"tiles": tiles}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _load_feed() -> dict:
    # Strict on purpose: output/cards.json (pipeline card state — NOT the
    # root feed.json, which is the JSON Feed spec file) is committed state.
    # Corrupt or wrong-shape must fail the cycle loudly; the old lenient
    # default let a truncated file silently republish an empty board.
    path = config.OUTPUT_DIR / "cards.json"
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {"cards": []}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"output/cards.json corrupt: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("cards"), list):
        raise RuntimeError("output/cards.json malformed (want dict with "
                           "'cards' list)")
    return data


def _asked_key(card: dict) -> str:
    # Key on the DATA date so a new vintage (ACS year roll, monthly BLS print)
    # refreshes the card, while re-proposals of the same vintage stay silent.
    vals = card.get("answer_values") or {}
    when = vals.get("date") or ""
    return f"{card['indicator']}:{card['question'][:80]}:{when}"


def _answer_stackup(proposal: dict, item: dict) -> dict | None:
    result = None
    if item.get("census1yr"):
        # ACS 1-year beats Data Commons' 5-year ceiling when reachable
        result = census1yr.stackup(
            item["census1yr"],
            fixture=config.FIXTURES_DIR / f"census1yr_{item['id']}.json")
    if result is None:
        fixture = config.FIXTURES_DIR / f"dc_{item['id']}.json"
        result = datacommons.stackup(item, fixture=fixture)
    if result is None:
        print(f"  discard (no data): {item['id']} <- {proposal['headline']['title'][:60]}")
        return None
    trend_rows = None
    if item.get("trend"):
        try:
            trend_rows = datacommons.trend(item)
        except Exception as exc:
            print(f"  trend failed ({exc}); rank strip only")
    return cards.from_stackup(item, proposal, result, trend_rows=trend_rows)


def _answer_local(proposal: dict, item: dict | None, demo: bool) -> dict | None:
    if (item is None
            or not (item.get("columns")
                    or proposal.get("indicator_id") in (None, "grand_list_growth"))):
        print(f"  skip (no answerer yet): {proposal.get('indicator_id')} <- {proposal['headline']['title'][:60]}")
        return None
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
        return None
    if proposal.get("indicator_id") is None:
        proposal = {**proposal, "question_override": None}
    return cards.from_local(item, proposal, result)


def _record_redirect(old_id: str, new_id: str) -> None:
    """A reworded question mints a new card id; the old permalink must 301 to
    the new one. Enforced by code now — the old hand-edit step was a rule
    nobody (including past me) reliably remembered."""
    path = config.ROOT / "vercel.json"
    cfg = json.loads(path.read_text())
    redirects = cfg.setdefault("redirects", [])
    entry = {"source": f"/story/{old_id}", "destination": f"/story/{new_id}",
             "permanent": True}
    if not any(r.get("source") == entry["source"] for r in redirects):
        redirects.append(entry)
        util.atomic_write_text(path, json.dumps(cfg, indent=2) + "\n")


def answer_proposals(proposals: list[dict], catalog: dict, demo: bool) -> list[dict]:
    stackup_by_id = {i["id"]: i for i in catalog.get("stackup", [])}
    local_by_id = {i["id"]: i for i in catalog.get("local", [])}
    built = []
    for proposal in proposals:
        indicator_id = proposal.get("indicator_id")
        try:
            if proposal["stream"] == "stackup" and indicator_id in stackup_by_id:
                card = _answer_stackup(proposal, stackup_by_id[indicator_id])
            elif proposal["stream"] == "local":
                card = _answer_local(proposal,
                                     local_by_id.get(indicator_id or "grand_list_growth"),
                                     demo)
            else:
                print(f"  skip (no answerer yet): {indicator_id or proposal['stream']} <- {proposal['headline']['title'][:60]}")
                continue
            if card:
                built.append(card)
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
    kept_ids = {c["id"] for c in kept}
    for card in new_cards:
        if card["id"] not in kept_ids:
            print(f"  balanced out (topic cap): {card['topic']} / {card['indicator']}")
    return kept


def _trend() -> list[dict]:
    """Attention with a week-long memory: per day, votes count twice the
    weight of views, downvotes subtract; a week of age halves the influence.
    Deterministic from a committed file — the trend table ships as an
    artifact like everything else here."""
    import json as _json
    import math
    import datetime as _dtd
    try:
        data = _json.loads((config.ROOT / "data" / "interactions.json")
                           .read_text())
    except (OSError, ValueError):
        return []
    today = _dtd.date.today()
    out = []
    for cid, days in (data or {}).items():
        if not isinstance(days, dict):
            continue
        score = votes = sees = 0
        for dk, e in days.items():
            try:
                age = (today - _dtd.date.fromisoformat(dk)).days
            except ValueError:
                continue
            u, dn, s = e.get("u", 0), e.get("d", 0), e.get("s", 0)
            votes += u + dn
            sees += s
            score += (u * 2 - dn * 1.5 + min(s, 50) * 0.1) * math.exp(-age / 7)
        if votes or sees:
            out.append({"id": cid, "score": round(score, 2),
                        "votes": votes, "sees": sees})
    out.sort(key=lambda t: -t["score"])
    return out


def _revalidate(cards_by_id: dict, by_id: dict) -> int:
    """Re-fetch every live stackup card; replace it when upstream printed a
    newer data date. Without this pass a fresh vintage only lands when a
    matching headline happens to trigger the same indicator — quiet news days
    would keep published numbers stale. Gated to one full pass every few
    hours to stay polite to the upstream rate limits (96 cycles/day must not
    mean 96 census probes). Local-stream cards (grand list rolls) are annual
    and skipped; their answers name the roll year in the text itself.
    """
    stamp_path = config.ASKED_LOG_PATH.parent / "revalidation.json"
    stamp = _load_json(stamp_path, {})
    now = dt.datetime.now(dt.timezone.utc)
    last = stamp.get("__last__")
    if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < 3 * 3600:
        return 0
    touched = 0
    for cid, card in list(cards_by_id.items()):
        ind = by_id.get(card.get("indicator"))
        if not ind or card.get("stream") != "stackup":
            continue
        result = None
        if ind.get("census1yr"):
            result = census1yr.stackup(
                ind["census1yr"],
                fixture=config.FIXTURES_DIR / f"census1yr_{ind['id']}.json")
        if result is None:
            try:
                result = datacommons.stackup(
                    ind, fixture=config.FIXTURES_DIR / f"dc_{ind['id']}.json")
            except Exception:
                continue
        new_date = (result.get("ct") or {}).get("date")
        old_date = (card.get("answer_values") or {}).get("date")
        # forward-only: upstream facets that flap backwards (DC serves several
        # facets per variable) must not bounce a published number or re-post it
        if not new_date or new_date <= old_date:
            continue
        trend_rows = None
        if ind.get("trend"):
            try:
                trend_rows = datacommons.trend(ind)
            except Exception:
                trend_rows = None
        proposal = {"headline": card["headline"],
                    "question_override": card["question"],
                    "indicator_id": ind["id"]}
        new = cards.from_stackup(ind, proposal, result, trend_rows=trend_rows)
        if new["id"] != cid:          # question drifted; not our business here
            continue
        new["generated_at"] = card["generated_at"]   # same story, newer number
        cards_by_id[cid] = new
        touched += 1
        print(f"  ~ revalidated [{card['stream']}/{card['topic']}] "
              f"{ind['id']}: {old_date} -> {new_date}")
    stamp["__last__"] = now.isoformat(timespec="seconds")
    stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True))
    return touched


def run_cycle(catalog: dict, demo: bool, use_llm: bool = True) -> int:
    existing = _load_feed()
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
        # one card per indicator: if the question text was reworded, the
        # regenerated card has a new id — drop the stale sibling so the
        # board never shows the same indicator twice (the superseded story
        # page stays committed on disk as audit trail).
        for oid, oc in list(cards_by_id.items()):
            if (oid != card["id"] and oc.get("indicator") == card.get("indicator")
                    and oc.get("stream") == card.get("stream")):
                del cards_by_id[oid]
                _record_redirect(oid, card["id"])
                print(f"  - superseded [{card['stream']}/{card['topic']}] {oid}")

    config.ASKED_LOG_PATH.parent.mkdir(exist_ok=True)
    config.ASKED_LOG_PATH.write_text(json.dumps(asked, indent=2, sort_keys=True))
    by_id = {i["id"]: i for s in ("stackup", "local") for i in catalog.get(s, [])}
    revalidated = _revalidate(cards_by_id, by_id)
    if revalidated:
        print(f"  revalidation: {revalidated} card(s) now carry newer numbers")
    ordered = sorted(cards_by_id.values(), key=lambda c: c["generated_at"], reverse=True)
    from . import publish

    from . import audit as _audit, inventory as _inv, towns as _towns
    _inv.check()              # portal stamps + ACS release probes
    broken = _audit.internal_links()
    if broken:                # visible where failure logs live
        with open(config.ROOT / "data" / "failures.log", "a") as fh:
            for b in broken[:10]:
                fh.write(f"linkcheck: {b}\n")
        print(f"  linkcheck: {len(broken)} broken internal link(s)")
    _towns.publish()          # ACS town snapshot + the town table page
    board = build_board(catalog)
    board["trend"] = _trend()
    publish.publish(ordered, board)
    print(f"  feed: {len(ordered)} cards (+{added} new)")
    return added


def main() -> None:
    parser = argparse.ArgumentParser(prog="ctsignal")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-min", type=float, default=15.0)
    parser.add_argument("--demo", action="store_true",
                        help="merge fixture headlines; live fetches still tried first, fixtures as fallback")
    parser.add_argument("--no-llm", action="store_true",
                        help="heuristic proposer only (deterministic demo fallback)")
    args = parser.parse_args()

    catalog = questions.load_catalog()
    while True:
        try:
            run_cycle(catalog, demo=args.demo, use_llm=not args.no_llm)
        except Exception as exc:
            # one named line, committed with the site: "our failure log is
            # public" is now a statement about this repo, not a hope
            msg = re.sub(r"https?://\S+", "<url>", str(exc))[:200]
            line = f"{_now()} cycle failed: {type(exc).__name__}: {msg}"
            config.ASKED_LOG_PATH.parent.mkdir(exist_ok=True)
            with open(config.ASKED_LOG_PATH.parent / "failures.log", "a") as fh:
                fh.write(line + "\n")
            print(line)
            raise SystemExit(1)
        if args.once:
            break
        time.sleep(args.interval_min * 60)


if __name__ == "__main__":
    main()
