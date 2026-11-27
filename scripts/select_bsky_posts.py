"""Pure, unit-tested selector for automated Bluesky card posts.

Prevents the social feed from turning into a repetitive weather ticker:
  1. Weather cards require BOTH a large anomaly (>= 5.0°F) AND a material
     shift from the prior snapshot (>= 1.5°F) — plus a 48h cooldown if
     weather was already posted recently.
  2. Desk rotation: Connecticut local/stackup stories rank ahead of US macro,
     and at most one card per topic is selected per cycle; if the newest recent
     post on the feed was from a given topic, other topics rotate ahead.
"""
from __future__ import annotations

import json
import sys


def _is_ct_card(c: dict) -> bool:
    h = c.get("headline") or {}
    return (
        c.get("stream") in ("local", "stackup", "ct")
        or h.get("stream") == "ct"
        or int(h.get("ct_hits") or 0) >= 2
        or c.get("indicator") in ("ct_unemployment", "northeast_electricity")
    )


def _weather_material(card: dict, prev_card: dict | None,
                      recent_weather_posted: bool = False) -> bool:
    if card.get("topic") != "weather":
        return True
    if recent_weather_posted:
        return False
    try:
        cur_val = float((card.get("answer_values") or {}).get("value"))
    except (TypeError, ValueError):
        return False
    if abs(cur_val) < 5.0:
        return False
    if prev_card is not None:
        try:
            prev_val = float((prev_card.get("answer_values") or {}).get("value"))
            if abs(cur_val - prev_val) < 1.5:
                return False
        except (TypeError, ValueError):
            pass
    return True


def select_candidates(
    cur_cards: list[dict],
    prev_cards: list[dict],
    *,
    recent_ids: set[str] | None = None,
    last_topic: str | None = None,
    recent_weather: bool = False,
    limit: int = 2,
) -> list[dict]:
    """Return up to `limit` cards worth posting, ordered CT-first with desk
    rotation and a strict material-change gate on daily weather refreshes."""
    recent_ids = recent_ids or set()
    prev_by_id = {c["id"]: c for c in prev_cards}
    changed = []
    for c in cur_cards:
        cid = c["id"]
        if cid in recent_ids:
            continue
        prev = prev_by_id.get(cid)
        cur_date = (c.get("answer_values") or {}).get("date")
        prev_date = (prev.get("answer_values") or {}).get("date") if prev else None
        if prev is not None and prev_date == cur_date:
            continue
        if not _weather_material(c, prev, recent_weather_posted=recent_weather):
            continue
        changed.append(c)

    def sort_key(c: dict) -> tuple:
        same_as_last = 1 if (last_topic and c.get("topic") == last_topic) else 0
        is_weather = 1 if c.get("topic") == "weather" else 0
        ct_rank = 0 if _is_ct_card(c) else 1
        return (is_weather, same_as_last, ct_rank)

    changed.sort(key=sort_key)
    picked: list[dict] = []
    seen_topics: set[str] = set()
    for c in changed:
        t = str(c.get("topic") or "")
        if t and t in seen_topics:
            continue
        picked.append(c)
        if t:
            seen_topics.add(t)
        if len(picked) >= limit:
            break
    return picked


def main() -> None:
    payload = json.load(sys.stdin)
    picked = select_candidates(
        payload.get("cur_cards") or [],
        payload.get("prev_cards") or [],
        recent_ids=set(payload.get("recent_ids") or []),
        last_topic=payload.get("last_topic") or None,
        recent_weather=bool(payload.get("recent_weather")),
        limit=int(payload.get("limit", 2)),
    )
    print(" ".join(c["id"] for c in picked))


if __name__ == "__main__":
    main()
