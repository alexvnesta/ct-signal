from __future__ import annotations

import requests

from .. import config


def rows(dataset_id: str, **soql: str) -> list[dict]:
    resp = requests.get(
        f"{config.SOCRATA_PORTAL}/resource/{dataset_id}.json",
        params={"$limit": 400, **soql},
        headers=config.UA,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def town_metric_growth(cfg: dict, fixture: dict | None = None) -> dict | None:
    if fixture is not None:
        latest_year = int(fixture["latest_year"])
        prior_year = int(fixture["prior_year"])
        rows_in = fixture["rows"]
    else:
        year_col, town_col, value_col = cfg["year"], cfg["town"], cfg["value"]
        raw = rows(cfg["socrata_id"], **{"$order": f"{year_col} DESC, {town_col}"})
        by_town: dict[str, dict[int, float]] = {}
        for r in raw:
            try:
                year = int(r[year_col])
                value = float(r[value_col])
            except (KeyError, TypeError, ValueError):
                continue
            by_town.setdefault(r[town_col], {})[year] = value
        years = sorted({y for d in by_town.values() for y in d})
        if len(years) < 2:
            return None
        latest_year, prior_year = years[-1], years[-2]
        rows_in = [
            {"town": town, "latest": per_year[latest_year], "prior": per_year[prior_year]}
            for town, per_year in by_town.items()
            if latest_year in per_year and prior_year in per_year and per_year[prior_year] > 0
        ]
    scored = []
    for r in rows_in:
        latest, prior = float(r["latest"]), float(r["prior"])
        if prior <= 0:
            continue
        scored.append({
            "town": r["town"], "latest": latest, "prior": prior,
            "added": latest - prior, "pct": (latest - prior) / prior * 100,
        })
    if not scored:
        return None
    scored.sort(key=lambda s: s["pct"], reverse=True)
    top = scored[:10]
    return {
        "top": top,
        "latest_year": latest_year,
        "prior_year": prior_year,
        "n": len(scored),
        "rows": [
            {"state": s["town"], "value": round(s["pct"], 2), "rank": i + 1,
             "highlight": i == 0}
            for i, s in enumerate(top)
        ],
        "query": (
            f"GET /resource/{cfg.get('socrata_id', fixture and 'fixture')}.json "
            f"$order={cfg.get('year','year')} DESC ({len(scored)} places, last 2 years)"
        ),
    }


GRAND_LIST_CFG = {
    "socrata_id": "webp-fgt3",
    "year": "year",
    "town": "town_name",
    "value": "total_net_grand_list",
}


def grand_list_growth(fixture: dict | None = None) -> dict | None:
    return town_metric_growth(GRAND_LIST_CFG, fixture=fixture)
