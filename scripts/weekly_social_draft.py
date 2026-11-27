"""Weekly distribution draft pack for human 30-second approval.

    python3 scripts/weekly_social_draft.py        # -> output/weekly-draft.md

Reads only committed local data (output/cards.json, board.json, data/towns.json)
with zero paid API calls. Leads with computed concentration, neighbor spreads,
and concrete dollar contrasts rather than predictable "#1 town" trivia.
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


def _town_lookup(card: dict | None) -> dict[str, dict]:
    if not card:
        return {}
    return {str(r.get("town") or "").lower(): r for r in (card.get("towns") or [])}


def _computed_angles(cards: list[dict]) -> list[tuple[str, str, str]]:
    """Build deterministic, receipt-backed narrative angles (hook, label, url)
    directly from live card numbers — spreads, shares, and neighbor contrasts
    instead of static "#1 town" superlatives."""
    by_ind = {c.get("indicator"): c for c in cards if c.get("indicator")}
    angles: list[tuple[str, str, str]] = []

    hp = by_ind.get("housing_permits")
    if hp and hp.get("towns"):
        top = hp["towns"][0]
        av = hp.get("answer_values") or {}
        total = int(av.get("state") or 0)
        yr = av.get("date", "2025")
        n = av.get("n") or len(hp["towns"])
        if total > 0:
            share = top["value"] / total * 100
            top3 = sum(r["value"] for r in hp["towns"][:3])
            top3_pct = top3 / total * 100
            hook = (
                f"{top['town']} alone permitted {share:.1f}% of all new housing "
                f"in Connecticut in {yr} ({top['value']:,} of {total:,} units "
                f"across {n} towns; top 3 towns accounted for {top3_pct:.0f}%)."
            )
            angles.append((hook, f"New housing permits ({yr})", f"{SITE}/story/{hp['id']}"))

    mr = by_ind.get("mill_rates")
    if mr and mr.get("towns"):
        tmap = _town_lookup(mr)
        av = mr.get("answer_values") or {}
        fy = str(av.get("date") or "FY2027")
        ratio = float(av.get("assess_ratio") or 0.70)
        gw = tmap.get("greenwich")
        st = tmap.get("stamford")
        ht = tmap.get("hartford")
        if gw and st and ht:
            home = 750_000
            tax_gw = round(home * ratio * gw["rate"] / 1000)
            tax_st = round(home * ratio * st["rate"] / 1000)
            tax_ht = round(home * ratio * ht["rate"] / 1000)
            hook = (
                f"On a $750,000 home, {fy} municipal property taxes jump from "
                f"${tax_gw:,}/yr in Greenwich ({gw['rate']:.2f} mills) to "
                f"${tax_st:,}/yr next door in Stamford ({st['rate']:.2f} mills) "
                f"— and ${tax_ht:,}/yr in Hartford ({ht['rate']:.2f} mills)."
            )
            angles.append((hook, f"Property tax spread ({fy})", f"{SITE}/compare?a=greenwich&b=stamford&c=hartford&price=750000"))

    hs = by_ind.get("home_sales_price")
    if hs and hs.get("towns"):
        tlist = hs["towns"]
        av = hs.get("answer_values") or {}
        yr = av.get("date", "2024")
        med = av.get("state")
        tot_sales = av.get("total_sales")
        hi, lo = tlist[0], tlist[-1]
        if med:
            sales_bit = f"Across {int(tot_sales):,} recorded single-family closings in {yr}" if tot_sales else f"In {yr}"
            hook = (
                f"{sales_bit}, Connecticut's median sale price was ${int(med):,} "
                f"— spanning ${int(lo['value']):,} in {lo['town']} to "
                f"${int(hi['value']):,} in {hi['town']}."
            )
            angles.append((hook, f"Single-family home sales ({yr})", f"{SITE}/story/{hs['id']}"))

    sc = by_ind.get("school_spending_per_pupil")
    if sc and sc.get("towns"):
        tlist = sc["towns"]
        av = sc.get("answer_values") or {}
        yr = av.get("date", "2023")
        med = av.get("state")
        hi, lo = tlist[0], tlist[-1]
        if med and lo["value"] > 0:
            mult = hi["value"] / lo["value"]
            hook = (
                f"Public school spending spans a {mult:.1f}× range across "
                f"Connecticut's {len(tlist)} towns ({yr}) — from ${int(lo['value']):,}/pupil "
                f"in {lo['town']} to ${int(hi['value']):,} in small-enrollment "
                f"{hi['town']} (town median: ${int(med):,})."
            )
            angles.append((hook, f"School spending per pupil ({yr})", f"{SITE}/story/{sc['id']}"))

    return angles


def render_draft(cards: list[dict], board: dict) -> str:
    if not cards:
        return "# Weekly draft\n\nNo cards available.\n"
    week = dt.date.fromisoformat(
        max(c["generated_at"] for c in cards)[:10]).isocalendar()
    issue = f"{week.year}-W{week.week:02d}"

    angles = _computed_angles(cards)
    if not angles:
        lead = cards[0]
        angles = [(newsroom._finding(lead) or lead["answer_text"],
                   lead["question"], f"{SITE}/story/{lead['id']}")]

    lead_hook, _, _ = angles[0]
    bullets = "\n".join(f"- **{hook}** ({url})" for hook, _, url in angles[:3])

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
    reddit_title = f"Connecticut by the numbers ({issue}): {lead_hook.split(' (')[0]}"
    reddit_rows = "\n".join(
        f"| {label} | {hook} | [Receipts]({url}) |"
        for hook, label, url in angles[:4]
    )
    reddit = (
        f"**Title:** `{reddit_title}`\n\n"
        f"Compiled directly from live CT Open Data Portal (OPM / DECD / CSDE), BLS, and Census releases:\n\n"
        f"| Measure | What the official data shows | Source & chart |\n"
        f"|---|---|---|\n"
        f"{reddit_rows}\n\n"
        f"You can run the FY2027 property tax estimator for your town at {SITE}/towns or put two "
        f"neighboring towns side by side at {SITE}/compare."
    )

    # 3. Local Facebook Town Group / Nextdoor snippet (human-posted, zero hype)
    fb_lead = angles[1][0] if len(angles) > 1 else lead_hook
    fb_extra = angles[2][0] if len(angles) > 2 else ""
    fb_snippet = (
        "Sharing a free public-data tool in case folks here are comparing property taxes or home sales "
        "ahead of town budget season:\n\n"
        + fb_lead + (f" {fb_extra}" if fb_extra else "") + "\n\n"
        f"Check your town's FY2027 mill rate + property tax estimator here: {SITE}/towns\n"
        f"Or compare neighboring towns side by side: {SITE}/compare\n"
        "(All numbers pull directly from CT OPM, DECD, CSDE, and the US Census — no ads, no sign-up.)"
    )

    # 4. Bluesky 3-post thread (strictly <= 300 chars each, distinct angles)
    bsky_posts = []
    for idx, (hook, _, url) in enumerate(angles[:3], 1):
        prefix = f"CT Signal ({issue}): " if idx == 1 else ""
        tail = f"\n\n{SITE}/week/{issue}" if idx == 1 else f"\n\nReceipts: {url}"
        room = 299 - len(prefix) - len(tail)
        body_txt = hook if len(hook) <= room else hook[:room - 1].rsplit(" ", 1)[0] + "…"
        bsky_posts.append(f"{prefix}{body_txt}{tail}")
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
