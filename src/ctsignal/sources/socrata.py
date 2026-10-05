from __future__ import annotations

import requests

from .. import config


def _paginated(fetch, page: int = 1000, max_rows: int = 40000) -> list[dict]:
    """Loop $offset pages until a short page ends the dataset."""
    out, off = [], 0
    while True:
        batch = fetch(off)
        out += batch
        if len(batch) < page or len(out) >= max_rows:
            return out
        off += page


def rows(dataset_id: str, **soql: str) -> list[dict]:
    def fetch(offset: int) -> list[dict]:
        resp = requests.get(
            f"{config.SOCRATA_PORTAL}/resource/{dataset_id}.json",
            params={"$limit": 1000, "$offset": offset, **soql},
            headers={**config.UA,
                     **({"X-App-Token": config.SOCRATA_TOKEN}
                        if config.SOCRATA_TOKEN else {})},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    return _paginated(fetch)


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
        "all": [
            {"town": s["town"], "latest": round(s["latest"], 2),
             "prior": round(s["prior"], 2), "added": round(s["added"], 2),
             "pct": round(s["pct"], 2), "rank": i + 1}
            for i, s in enumerate(scored)
        ],
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


def _assess_ratio() -> float:
    """Connecticut assesses real property at 70% of actual value by statute
    (CGS §12-64); OPM audits towns against that line yearly. Not a computed
    proxy — a cited legal constant, because ODP's land-use columns measure
    what is assessed, not how far below market."""
    return 0.70


def mill_rates(cfg: dict, fixture: dict | None = None) -> dict | None:
    """Current-town mill rates, plus the figure a naive average would get wrong.

    An unweighted mean of 168 towns lets a village outweigh a city, so the
    state figure is weighted by each town's own net grand list: the rate a
    dollar of Connecticut property actually pays. District rows (a name with
    a dash) are excluded — they belong to a town, not beside it — and so are
    zero-rate rows, which mean 'not set yet', not 'free'.
    """
    import statistics
    fy_col = cfg.get("year", "fiscal_year")
    if fixture is not None:
        fy = int(fixture["fiscal_year"])
        pairs = [(r["town"], float(r["rate"]), float(r["grand_list"]))
                 for r in fixture["rows"]]
        rates = {t: r for t, r, _ in pairs}
        ratio = fixture.get("assess_ratio") or _assess_ratio()
    else:
        raw = rows(cfg["socrata_id"], **{fy_col: str(cfg["fiscal_year"])})
        rates = {}
        for r in raw:
            town = r.get(cfg.get("town", "municipality"), "")
            if "-" in town:
                continue
            try:
                rate = float(r.get("mill_rate_real_personal") or 0)
            except (TypeError, ValueError):
                continue
            if rate > 0:
                rates[town] = rate
        if not rates:
            return None
        fy = int(cfg["fiscal_year"])
        gl_year = cfg.get("grand_list_year")
        gl_rows = rows(cfg["grand_list_id"], **({"year": str(gl_year)}
                                                if gl_year else {}))
        gl = {r.get("town_name", ""): float(r.get("total_net_grand_list") or 0)
              for r in gl_rows}
        ratio = _assess_ratio()
        pairs = [(t, r, gl[t]) for t, r in rates.items() if gl.get(t, 0) > 0]
    if not pairs:
        return None
    state = sum(r * g for _, r, g in pairs) / sum(g for _, _, g in pairs)
    scored = sorted(pairs, key=lambda p: -p[1])
    if not fixture:
        top_g = max(g for _, _, g in pairs)
        scored = [(t, r, g / top_g) for t, r, g in scored]
    median = statistics.median(sorted(r for _, r, _ in pairs))
    top = scored[0]
    return {
        "fiscal_year": fy, "n": len(pairs),
        "state_rate": round(state, 2), "median_rate": round(median, 2),
        "assess_ratio": round(ratio, 4) if ratio else None,
        "top": {"town": top[0], "rate": round(top[1], 2),
                "multiple": round(top[1] / state, 2)},
        "rows": [{"state": t, "value": round(r, 2), "rank": i + 1,
                  # the orange bar is the card's own subject, not a
                  # name asserted in the catalog
                  "highlight": t == cfg.get("highlight", scored[0][0])}
                 for i, (t, r, _) in enumerate(scored[:10])],
        "all": [{"town": t, "rate": round(r, 2), "rank": i + 1,
                 "vs_state": round(r / state, 2)}
                for i, (t, r, _) in enumerate(scored)],
        "query": (f"GET /resource/{cfg.get('socrata_id', 'fixture')}.json"
                  f"?{fy_col}={fy} (municipal rows, split rates;"
                  f" weighted by {cfg.get('grand_list_id','grand list')}"
                  f" {cfg.get('grand_list_year', '')})"),
    }

GRAND_LIST_CFG = {
    "socrata_id": "webp-fgt3",
    "year": "year",
    "town": "town_name",
    "value": "total_net_grand_list",
}


def grand_list_growth(fixture: dict | None = None) -> dict | None:
    return town_metric_growth(GRAND_LIST_CFG, fixture=fixture)
