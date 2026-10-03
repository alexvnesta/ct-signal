"""One-shot refresh: re-answer census1yr indicators with ACS 1-year data.

Run after wiring or changing the census1yr catalog blocks. Cards keep their
ids (hash of indicator + question), so permalinks and Bluesky cards stay
valid; only values, dates, ranks, charts and citations are replaced. The
archive copy is updated too, since the archive is the card store that the
next publish rebuilds pages from.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from ctsignal import cards, config  # noqa: E402
from ctsignal.sources import census1yr  # noqa: E402

catalog = yaml.safe_load((ROOT / "catalog" / "indicators.yaml").read_text())
by_id = {i["id"]: i for s in ("stackup", "local") for i in catalog.get(s, [])}

feed = json.loads((ROOT / "output" / "cards.json").read_text())
done = []
for idx, card in enumerate(feed["cards"]):
    ind = by_id.get(card["indicator"])
    if not ind or "census1yr" not in ind:
        continue
    result = census1yr.stackup(
        ind["census1yr"],
        fixture=config.FIXTURES_DIR / f"census1yr_{ind['id']}.json")
    if result is None:
        print(f"skip {ind['id']}: census source unavailable")
        continue
    new = cards.from_stackup(
        ind, {"headline": card["headline"], "question_override": card["question"]},
        result, trend_rows=None)
    assert new["id"] == card["id"], f"id drift {card['id']} -> {new['id']}"
    new["generated_at"] = card["generated_at"]   # keep original first-publish stamp
    feed["cards"][idx] = new
    arch = ROOT / "archive" / "2026-10" / f"{card['id']}.json"
    if arch.exists():
        arch.write_text(json.dumps(new, indent=2, sort_keys=True))
    done.append((ind["id"], result["ct"]["date"], result["ct"]["rank"], result["n"]))

(ROOT / "output" / "cards.json").write_text(json.dumps(feed, indent=2, sort_keys=True))
for row in done:
    print("refreshed", *row)
print(len(done), "cards refreshed")
