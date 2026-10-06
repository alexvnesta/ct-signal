from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time

from . import cards, charts, config, feeds, questions, util
from .sources import census1yr, datacommons, fred, socrata


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


def _scrub_failure(msg: str) -> str:
    """Failure lines are published with the site (sources.html points
    at the log), so an exception string must never carry a credential:
    an upstream URL that failed validation once leaked a live API key
    through here. Scrub scheme-less URLs and any key-like parameter
    before the string gets a public home."""
    msg = re.sub(r"https?://\S+", "<url>", msg)
    msg = re.sub(r"[?&]((?:api_)?[Kk]ey|[Tt]oken|[Ss]ecret|[Pp]assword)"
                 r"=[^&\s,]+", lambda m: "<redacted " + m.group(1)
                 + ">", msg)
    msg = re.sub(r"[A-Za-z0-9_-]{32,}", "<redacted>", msg)
    return msg[:200]


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
    # Key on the data date plus the answer's content and field set: a new
    # vintage (ACS year roll, monthly BLS print) must refresh the card, a
    # re-proposal of the same vintage must stay silent, and a card whose
    # SHAPE changed (template edit, new provenance field) must refresh too
    # — otherwise the town pages render the old fields forever and quietly
    # contradict the card's own story.
    import hashlib
    vals = card.get("answer_values") or {}
    when = vals.get("date") or ""
    shape = json.dumps({"t": card.get("answer_text", ""), "v": vals,
                        "c": card.get("chart")},
                       sort_keys=True, default=str)
    sig = hashlib.sha1(shape.encode()).hexdigest()[:10]
    return f"{card['indicator']}:{card['question'][:80]}:{when}:{sig}"


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


def _answer_national(proposal: dict, item: dict) -> dict | None:
    fixture = config.FIXTURES_DIR / f"fred_{item['id']}.csv"
    result = fred.observations(item, fixture=fixture if fixture.exists()
                               else None)
    if result is None:
        print(f"  discard (no data): {item['id']} <- {proposal['headline']['title'][:60]}")
        return None
    return cards.from_national(item, proposal, result)


def _answer_local(proposal: dict, item: dict | None, demo: bool) -> dict | None:
    if (item is None
            or not (item.get("columns")
                    or proposal.get("indicator_id") in (None, "grand_list_growth"))):
        print(f"  skip (no answerer yet): {proposal.get('indicator_id')} <- {proposal['headline']['title'][:60]}")
        return None
    cfg = item.get("columns") or socrata.GRAND_LIST_CFG
    answerer = item.get("answerer", "town_metric_growth")
    if answerer == "mill_rates":
        # Fiscal years advance every July; a hardcoded year would quietly
        # freeze the card on last year's tax rate.
        cfg = {**cfg, "fiscal_year": max(dt.date.today().year, cfg["fiscal_year"])}
        result = socrata.mill_rates(cfg)
        build = cards.from_mill_rates
    else:
        fixture = None
        fx_path = config.FIXTURES_DIR / "grand_list.json"
        if demo and item["id"] == "grand_list_growth" and fx_path.exists():
            fixture = json.loads(fx_path.read_text())
        try:
            result = socrata.town_metric_growth(cfg)
        except Exception:
            result = socrata.town_metric_growth(cfg, fixture=fixture) if fixture else None
        build = cards.from_local
    if result is None:
        print(f"  discard (no data): {item['id']}")
        return None
    if proposal.get("indicator_id") is None:
        proposal = {**proposal, "question_override": None}
    return build(item, proposal, result)


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
    national_by_id = {i["id"]: i for i in catalog.get("national", [])}
    built = []
    for proposal in proposals:
        indicator_id = proposal.get("indicator_id")
        try:
            if indicator_id in national_by_id:
                # routing follows the catalog section, not the proposal's
                # label: a seed or LLM may call a national card "stackup"
                card = _answer_national(proposal, national_by_id[indicator_id])
            elif proposal["stream"] == "stackup" and indicator_id in stackup_by_id:
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
    """One fresh card per (topic, indicator) per cycle. The cap used to be
    per topic, which meant one jobs-report headline could only ever publish
    one labor question — the deck effect needs every honest angle on the
    same day, while never two vintages of the same indicator."""
    best: dict[tuple, dict] = {}
    for card in new_cards:
        key = (card["topic"], card.get("indicator"))
        score = card["headline"].get("published_sort") or 0
        current = best.get(key)
        if current is None or score > (current["headline"].get("published_sort") or 0):
            best[key] = card
    kept = list(best.values())
    kept_ids = {c["id"] for c in kept}
    for card in new_cards:
        if card["id"] not in kept_ids:
            print(f"  balanced out (one per topic+indicator): {card['topic']} / {card['indicator']}")
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


def _migrate_fixtures(cards_by_id: dict, by_id: dict,
                      headlines: list[dict],
                      proposals: list[dict]) -> int:
    """Demo triggers retire themselves — two ways, both honest.

    Promotion: every cycle we check the wire for a real headline that
    would raise the same question. When one exists the card is rebuilt
    on that trigger — same question, same URL, real receipt.

    Filing: when a demo card finds no real trigger, the synthetic one is
    deleted rather than displayed. The card keeps its live numbers and
    becomes a data desk filing: a question the desk raised from the
    series itself, claiming no news hook it cannot show. The fixture
    disclaimer deletes itself when the last demo trigger goes one way or
    the other; nothing else needed."""
    touched = 0
    for cid, card in list(cards_by_id.items()):
        demo = cards.is_demo_trigger(card)
        if not (demo or cards.is_data_filed(card)):
            continue
        ind = by_id.get(card.get("indicator"))
        if not ind or not ind.get("fred"):
            continue          # the current data-filed set is all national series
        # A live proposal for this indicator is the strongest candidate:
        # it may have come from the LLM proposer and would otherwise be
        # swallowed by the asked-log dedup gate, since the numbers it
        # answers with are already on record.
        cands = [p["headline"] for p in proposals
                 if p.get("indicator_id") == ind["id"]
                 and not cards.is_demo_trigger(p)]
        cands += [h for h in headlines if questions._keyword_hits(
            h["title"], ind.get("keywords") or [])]
        for h in cands:
            res = fred.observations(
                ind, fixture=config.FIXTURES_DIR / f"fred_{ind['id']}.csv")
            if not res:
                break
            new = cards.from_national(ind, {"headline": h}, res)
            if new["id"] != cid:
                break         # reworded question: leave the card as is
            cards_by_id[cid] = new
            touched += 1
            print(f"  \u2192 promoted [{card['stream']}/{card['topic']}] "
                  f"{ind['id']} <- {h['title'][:64]}")
            break
        else:
            if demo:
                card.pop("headline", None)
                card["origin"] = "data desk"
                touched += 1
                print(f"  \u2192 data-filed (no real trigger to claim) "
                      f"[{card['stream']}/{card['topic']}] {ind['id']}")
            elif cards.is_data_filed(card):
                # A filed card is a standing question: its numbers must
                # not fossilize just because no headline reopens it.
                res = fred.observations(
                    ind,
                    fixture=config.FIXTURES_DIR / f"fred_{ind['id']}.csv")
                if not res:
                    continue
                rebuilt = cards.from_national(
                    ind, {"question_override": card["question"],
                          "headline": None}, res)
                if rebuilt["id"] != cid or \
                        rebuilt["answer_text"] == card.get("answer_text"):
                    continue
                rebuilt["origin"] = "data desk"
                rebuilt["generated_at"] = card["generated_at"]
                rebuilt["revalidated_at"] = dt.datetime.now(
                    dt.timezone.utc).isoformat(timespec="seconds")
                cards_by_id[cid] = rebuilt
                touched += 1
                print(f"  ~ data-filed numbers revalidated [{ind['id']}] "
                      f"-> {res['date']}")
    return touched


def _revalidate(cards_by_id: dict, by_id: dict) -> int:
    """Re-fetch every live stackup card; replace it when upstream printed a
    newer data date. Without this pass a fresh vintage only lands when a
    matching headline happens to trigger the same indicator — quiet news days
    would keep published numbers stale. Gated to one full pass every few
    hours to stay polite to the upstream rate limits (96 cycles/day must not
    mean 96 census probes). Local-stream cards (grand list rolls) are annual
    and skipped; their answers name the roll year in the text itself.

    Cards that readers are actually reading get probed first: attention
    scores (the same trend the board publishes) order the loop, so if an
    upstream rate limit truncates a pass it truncates the cards nobody
    opened, not the ones people came back to.
    """
    stamp_path = config.ASKED_LOG_PATH.parent / "revalidation.json"
    stamp = _load_json(stamp_path, {})
    now = dt.datetime.now(dt.timezone.utc)
    last = stamp.get("__last__")
    if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < 3 * 3600:
        return 0
    touched = 0
    order = {t["id"]: t["score"] for t in _trend()}
    for cid, card in sorted(list(cards_by_id.items()),
                            key=lambda kv: -order.get(kv[0], 0)):
        ind = by_id.get(card.get("indicator"))
        if not ind or card.get("stream") not in ("stackup", "national"):
            continue
        if ind.get("fred"):
            res = fred.observations(
                ind, fixture=config.FIXTURES_DIR / f"fred_{ind['id']}.csv")
            new_date = (res or {}).get("date")
            old_date = (card.get("answer_values") or {}).get("date")
            if not new_date or new_date <= old_date:
                continue
            proposal = {"headline": card["headline"],
                        "question_override": card["question"],
                        "indicator_id": ind["id"]}
            new = cards.from_national(ind, proposal, res)
            if new["id"] != cid:
                continue
            # Completeness beats nominal recency: a 9-peer partial
            # cache must not keep outranking a full 52-state print
            # just because its date label is newer (a 5.1%/9-peers
            # answer once sat beside 5.8%/52 on the same site).
            old_n = int((card.get("answer_values") or {}).get("n") or 0)
            new_n = int((new.get("answer_values") or {}).get("n") or 0)
            if old_n and new_n < old_n and new_date == old_date:
                continue
            if new_date <= old_date and new_n <= old_n:
                continue
            new["generated_at"] = card["generated_at"]
            new["revalidated_at"] = now.isoformat(timespec="seconds")
            cards_by_id[cid] = new
            touched += 1
            print(f"  ~ revalidated [national/{card['topic']}] "
                  f"{ind['id']}: {old_date}/{old_n} -> "
                  f"{new_date}/{new_n}")
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
        new_n = int(result.get("n") or 0)
        old_n = int((card.get("answer_values") or {}).get("n") or 0)
        # Forward-only by default: facets that flap backwards (DC serves
        # several per variable) must not bounce a published number. But
        # a published answer built on a partial cohort is always fair
        # game for a complete one, at any date — completeness is a
        # stronger claim to truth than a newer date label (this rule
        # replaced the 5.1%-of-9-peers answer; see corrections).
        if not new_date:
            continue
        if new_date <= old_date:
            if old_n >= datacommons.MIN_PEERS or new_n <= old_n:
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
        new["revalidated_at"] = now.isoformat(timespec="seconds")
        cards_by_id[cid] = new
        touched += 1
        print(f"  ~ revalidated [{card['stream']}/{card['topic']}] "
              f"{ind['id']}: {old_date}/{old_n} -> "
              f"{new_date}/{new_n}")
    stamp["__last__"] = now.isoformat(timespec="seconds")
    stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True))
    return touched


def run_cycle(catalog: dict, demo: bool, use_llm: bool = True) -> int:
    existing = _load_feed()
    cards_by_id = {c["id"]: c for c in existing.get("cards", [])}
    asked = _load_json(config.ASKED_LOG_PATH, {})

    headlines = feeds.gather()
    questions.update_ledger(headlines, catalog)
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
    by_id = {i["id"]: i for s in ("stackup", "local", "national")
             for i in catalog.get(s, [])}
    revalidated = _revalidate(cards_by_id, by_id)
    if revalidated:
        print(f"  revalidation: {revalidated} card(s) now carry newer numbers")
    migrated = _migrate_fixtures(cards_by_id, by_id, headlines, proposals)
    if migrated:
        print(f"  fixtures: {migrated} card(s) now triggered by real "
              "headlines")
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
            msg = _scrub_failure(str(exc))
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
