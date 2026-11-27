"""Weekly distribution draft pack for human 30-second approval.

    python3 scripts/weekly_social_draft.py        # -> output/weekly-draft.md

Reads only committed local data (output/cards.json, board.json, data/towns.json)
with zero paid API calls. Produces ready-to-approve, non-spammy drafts for:
  1. LinkedIn (data-led Connecticut post)
  2. r/Connecticut (receipts-first title + compact table)
  3. Local Facebook Town Group / Nextdoor snippet (neighborly, zero hype;
     strictly for human posting — never bot-scraped or auto-posted)
  4. Bluesky weekly 3-post thread (rotated across distinct non-weather desks)
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ctsignal import config, newsroom  # noqa: E402

SITE = config.SITE_URL.rstrip("/")


def _pick_town_spotlight(cards: list[dict]) -> dict | None:
    """Pick a high-interest town comparison for neighborly local sharing."""
    by_ind = {c.get("indicator"): c for c in cards if c.get("indicator")}
    mr = by_ind.get("mill_rates")
    hs = by_ind.get("home_sales_price")
    hp = by_ind.get("housing_permits")
    sc = by_ind.get("school_spending_per_pupil")
    if not mr:
        return None
    top_mr = (mr.get("towns") or [None])[0]
    top_hp = (hp.get("towns") or [None])[0] if hp else None
    top_hs = (hs.get("towns") or [None])[0] if hs else None
    top_sc = (sc.get("towns") or [None])[0] if sc else None
    return {
        "mill_top": top_mr,
        "mill_state": (mr.get("answer_values") or {}).get("state"),
        "mill_fy": (mr.get("answer_values") or {}).get("date", "FY2027"),
        "permits_top": top_hp,
        "permits_state": (hp.get("answer_values") or {}).get("state") if hp else None,
        "sales_top": top_hs,
        "sales_state": (hs.get("answer_values") or {}).get("state") if hs else None,
        "school_top": top_sc,
        "school_state": (sc.get("answer_values") or {}).get("state") if sc else None,
    }


def render_draft(cards: list[dict], board: dict) -> str:
    if not cards:
        return "# Weekly draft\n\nNo cards available.\n"
    week = dt.date.fromisoformat(
        max(c["generated_at"] for c in cards)[:10]).isocalendar()
    issue = f"{week.year}-W{week.week:02d}"

    # Select distinct non-weather Connecticut stories first.
    ct_local = [c for c in cards if c.get("stream") == "local"]
    ct_stack = [c for c in cards if c.get("stream") == "stackup"]
    ct_other = [c for c in cards if c.get("indicator") in (
        "ct_unemployment", "northeast_electricity")]
    pool = ct_local + ct_stack + ct_other
    picked: list[dict] = []
    seen_ind: set[str] = set()
    for c in pool:
        ind = str(c.get("indicator") or c["id"])
        if ind in seen_ind:
            continue
        seen_ind.add(ind)
        picked.append(c)
        if len(picked) >= 4:
            break

    lead = picked[0] if picked else cards[0]
    lead_finding = newsroom._finding(lead) or lead["answer_text"]
    spot = _pick_town_spotlight(cards) or {}

    bullets = "\n".join(
        f"- **{newsroom._finding(c)}** ({SITE}/story/{c['id']})"
        for c in picked[:3]
    )

    # 1. LinkedIn draft
    linkedin = (
        f"What official Connecticut public data shows this week ({issue}):\n\n"
        f"{bullets}\n\n"
        f"Every figure on CT Signal comes straight from CT OPM, DECD, CSDE, BLS, or US Census APIs "
        f"with the exact query attached — no LLM-written numbers.\n\n"
        f"Full weekly brief: {SITE}/week/{issue}\n"
        f"Compare any 2–3 CT towns side by side (mill rate, est. tax bill, 2024 home sales, school spending): "
        f"{SITE}/compare"
    )

    # 2. r/Connecticut draft
    reddit_title = f"Connecticut by the numbers ({issue}): {lead_finding}"
    reddit_rows = "\n".join(
        f"| {c['question']} | {newsroom._finding(c)} | [Chart & query]({SITE}/story/{c['id']}) |"
        for c in picked[:4]
    )
    reddit = (
        f"**Title:** `{reddit_title}`\n\n"
        f"Compiled from live CT Open Data Portal (OPM / DECD / CSDE), BLS, and Census releases:\n\n"
        f"| Question | Official finding | Receipts |\n"
        f"|---|---|---|\n"
        f"{reddit_rows}\n\n"
        f"You can also look up your own town's property tax estimator at {SITE}/towns or put two "
        f"towns side by side at {SITE}/compare."
    )

    # 3. Local Facebook Town Group / Nextdoor snippet (human-posted, zero hype)
    mt = spot.get("mill_top") or {}
    st_mill = spot.get("mill_state")
    st_sale = spot.get("sales_state")
    st_school = spot.get("school_state")
    fb_bits = []
    if mt and st_mill:
        fb_bits.append(
            f"CT OPM's {spot.get('mill_fy', 'FY2027')} municipal mill rates average "
            f"{st_mill:.2f} mills statewide (weighted by grand list), with "
            f"{mt['town']} highest at {mt['rate']:.2f} mills."
        )
    if st_sale:
        fb_bits.append(f"2024 recorded single-family homes sold for a statewide median of ${st_sale:,.0f}.")
    if st_school:
        fb_bits.append(f"Public school spending sits at a town median of ${st_school:,.0f} per pupil.")
    fb_snippet = (
        "Sharing a free public-data tool in case folks here are comparing property taxes or home sales "
        "ahead of budget season:\n\n"
        + " ".join(fb_bits) + "\n\n"
        f"You can check your town's numbers + run the property tax estimator here: {SITE}/towns\n"
        f"Or compare neighboring towns side by side: {SITE}/compare\n"
        "(All numbers come directly from CT OPM, DECD, CSDE, and the US Census — no ads or sign-up.)"
    )

    # 4. Bluesky 3-post thread (strictly <= 300 chars each, distinct desks)
    bsky_posts = []
    p1 = (f"CT Signal weekly brief ({issue}): {lead_finding}\n\n"
          f"Full board + receipts: {SITE}/week/{issue}")
    bsky_posts.append(p1[:299])
    for c in picked[1:3]:
        p = f"{newsroom._finding(c)}\n\nChart & query: {SITE}/story/{c['id']}"
        bsky_posts.append(p[:299])
    bsky_md = "\n\n".join(
        f"**Post {i} ({len(txt)} chars):**\n> {txt.replace(chr(10), chr(10) + '> ')}"
        for i, txt in enumerate(bsky_posts, 1)
    )

    return (
        f"# CT Signal — Weekly Distribution Draft ({issue})\n\n"
        f"_Generated from committed public datasets with zero LLM copywriting. "
        f"Review in 30 seconds before posting; never auto-post to Reddit or Facebook groups._\n\n"
        f"## 1. LinkedIn\n\n{linkedin}\n\n"
        f"## 2. r/Connecticut\n\n{reddit}\n\n"
        f"## 3. Local Facebook Town Group / Nextdoor\n\n{fb_snippet}\n\n"
        f"## 4. Bluesky Weekly Thread\n\n{bsky_md}\n"
    )


def main() -> None:
    cards = json.loads((ROOT / "output" / "cards.json").read_text())["cards"]
    board = json.loads((ROOT / "board.json").read_text())
    out = ROOT / "output" / "weekly-draft.md"
    text = render_draft(cards, board)
    out.write_text(text)
    print(f"weekly draft -> {out.relative_to(ROOT)} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
