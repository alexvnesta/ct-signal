from __future__ import annotations

import json
import re
import statistics

import requests

from .. import config

_CANON_TOWNS: dict[str, str] | None = None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")


def _canonical_town(name: str) -> str:
    """Normalize Socrata town names ('EAST HARTFORD', 'New Haven') to the
    canonical 169-town spelling from data/towns.json when available."""
    global _CANON_TOWNS
    if _CANON_TOWNS is None:
        _CANON_TOWNS = {}
        path = config.ROOT / "data" / "towns.json"
        if path.exists():
            try:
                snap = json.loads(path.read_text())
                _CANON_TOWNS = {
                    _slug(t["name"]): t["name"]
                    for t in snap.get("towns") or []
                    if t.get("name")
                }
            except (OSError, ValueError):
                _CANON_TOWNS = {}
    clean = str(name or "").strip()
    hit = _CANON_TOWNS.get(_slug(clean))
    if hit:
        return hit
    return clean.title() if clean.isupper() else clean


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


_PLACE_TOTALS = {"total", "connecticut", "statewide"}


def _is_municipality(name) -> bool:
    """Socrata town tables carry a statewide 'Total' row beside the 169 real
    municipalities. It is an aggregate, not a place: counting it inflates n
    and inserts a rank no town owns."""
    name = str(name or "").strip()
    return bool(name) and name.lower() not in _PLACE_TOTALS


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
        if not _is_municipality(r.get("town")):
            continue
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


def housing_permits(cfg: dict, fixture: dict | None = None) -> dict | None:
    """Annual housing units permitted by Connecticut town (DECD stm9-38x4)."""
    if fixture is not None:
        latest_year = int(fixture["latest_year"])
        prior_year = int(fixture.get("prior_year", latest_year - 1))
        scored = [
            {"town": _canonical_town(r["town"]), "value": int(r["value"]),
             "prior": int(r.get("prior", 0))}
            for r in fixture["rows"] if _is_municipality(r.get("town"))
        ]
    else:
        raw = rows(cfg["socrata_id"])
        if not raw:
            return None
        ycols = sorted(
            [k for k in raw[0] if re.fullmatch(r"_\d{4}", k)],
            key=lambda k: int(k[1:]),
        )
        if not ycols:
            return None
        latest_col = ycols[-1]
        prior_col = ycols[-2] if len(ycols) >= 2 else None
        latest_year = int(latest_col[1:])
        prior_year = int(prior_col[1:]) if prior_col else latest_year - 1
        scored = []
        for r in raw:
            town = str(r.get("towns") or r.get("town") or "").strip()
            if not _is_municipality(town) or not r.get("county"):
                continue
            try:
                val = int(float(r[latest_col]))
            except (KeyError, TypeError, ValueError):
                continue
            try:
                prev = int(float(r[prior_col])) if prior_col and r.get(prior_col) is not None else 0
            except (TypeError, ValueError):
                prev = 0
            scored.append({"town": _canonical_town(town), "value": val, "prior": prev})
    if not scored:
        return None
    scored.sort(key=lambda s: (-s["value"], s["town"]))
    state_total = sum(s["value"] for s in scored)
    top = scored[0]
    return {
        "latest_year": latest_year,
        "prior_year": prior_year,
        "n": len(scored),
        "state_value": state_total,
        "top": {"town": top["town"], "value": top["value"]},
        "rows": [
            {"state": s["town"], "value": s["value"], "rank": i + 1,
             "highlight": i == 0}
            for i, s in enumerate(scored[:10])
        ],
        "all": [
            {"town": s["town"], "value": s["value"], "prior": s["prior"],
             "rank": i + 1}
            for i, s in enumerate(scored)
        ],
        "query": (
            f"GET /resource/{cfg.get('socrata_id', 'fixture')}.json "
            f"(column _{latest_year}; {len(scored)} municipalities)"
        ),
    }


def home_sales(cfg: dict, fixture: dict | None = None) -> dict | None:
    """Median single-family home sale price by Connecticut town (OPM 5mzw-sjtu)."""
    min_sales = int(cfg.get("min_sales", 10))
    if fixture is not None:
        latest_year = int(fixture["latest_year"])
        state_med = round(float(fixture["state_value"]))
        total_sales = int(fixture.get("total_sales", 0))
        scored = [
            {"town": _canonical_town(r["town"]), "value": round(float(r["value"])),
             "sales": int(r.get("sales", min_sales))}
            for r in fixture["rows"]
            if _is_municipality(r.get("town")) and int(r.get("sales", min_sales)) >= min_sales
        ]
    else:
        sid = cfg["socrata_id"]
        yr_rows = rows(sid, **{
            "$select": "listyear,count(*) as n",
            "$group": "listyear",
            "$order": "listyear DESC",
            "$limit": "10",
        })
        yr_pick = next(
            (r["listyear"] for r in yr_rows
             if str(r.get("listyear", "")).isdigit() and int(r.get("n") or 0) >= 10000),
            None,
        )
        if not yr_pick:
            return None
        latest_year = int(yr_pick)
        resp = requests.get(
            f"{config.SOCRATA_PORTAL}/resource/{sid}.json",
            params={
                "$select": "town,saleamount",
                "$where": f"listyear='{latest_year}' AND residentialtype='Single Family' AND saleamount >= 50000",
                "$limit": 50000,
            },
            headers={**config.UA,
                     **({"X-App-Token": config.SOCRATA_TOKEN}
                        if config.SOCRATA_TOKEN else {})},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()
        by_town: dict[str, list[float]] = {}
        all_vals: list[float] = []
        for r in raw:
            t = str(r.get("town") or "").strip()
            if not _is_municipality(t):
                continue
            try:
                amt = float(r["saleamount"])
            except (KeyError, TypeError, ValueError):
                continue
            if amt < 50000:
                continue
            canon = _canonical_town(t)
            by_town.setdefault(canon, []).append(amt)
            all_vals.append(amt)
        if not all_vals:
            return None
        state_med = round(statistics.median(all_vals))
        total_sales = len(all_vals)
        scored = [
            {"town": t, "value": round(statistics.median(vs)), "sales": len(vs)}
            for t, vs in by_town.items() if len(vs) >= min_sales
        ]
    if not scored:
        return None
    scored.sort(key=lambda s: (-s["value"], s["town"]))
    top = scored[0]
    return {
        "latest_year": latest_year,
        "n": len(scored),
        "state_value": state_med,
        "total_sales": total_sales,
        "top": {"town": top["town"], "value": top["value"], "sales": top["sales"]},
        "rows": [
            {"state": s["town"], "value": s["value"], "rank": i + 1,
             "highlight": i == 0}
            for i, s in enumerate(scored[:10])
        ],
        "all": [
            {"town": s["town"], "value": s["value"], "sales": s["sales"],
             "rank": i + 1}
            for i, s in enumerate(scored)
        ],
        "query": (
            f"GET /resource/{cfg.get('socrata_id', 'fixture')}.json "
            f"$where=listyear='{latest_year}' AND residentialtype='Single Family' "
            f"AND saleamount>=50000 ({total_sales:,} sales; {len(scored)} towns with >={min_sales} sales)"
        ),
    }


def fiscal_metric(cfg: dict, fixture: dict | None = None) -> dict | None:
    """Edition-consistent OPM Municipal Fiscal Indicator by town (xgef-f6jp)."""
    metric = cfg["metric"]
    if fixture is not None:
        latest_year = int(fixture["latest_year"])
        edition = str(fixture.get("edition", ""))
        scored = [
            {"town": _canonical_town(r["town"]), "value": round(float(r["value"]))}
            for r in fixture["rows"]
            if _is_municipality(r.get("town")) and float(r.get("value") or 0) > 0
        ]
    else:
        sid = cfg["socrata_id"]
        ed_col = "municipal_fiscal_indicators_report_edition_"
        safe_metric = metric.replace("'", "''")
        ed_rows = rows(sid, **{
            "$select": f"{ed_col},year,count(*) as n",
            "$where": f"metric='{safe_metric}'",
            "$group": f"{ed_col},year",
            "$order": f"{ed_col} DESC, year DESC",
            "$limit": "12",
        })
        pick = next(
            (r for r in ed_rows
             if str(r.get("year", "")).isdigit() and int(r.get("n") or 0) >= 100),
            None,
        )
        if not pick:
            return None
        edition = str(pick[ed_col])
        latest_year = int(pick["year"])
        safe_ed = edition.replace("'", "''")
        raw = rows(sid, **{
            "$where": f"{ed_col}='{safe_ed}' AND metric='{safe_metric}' AND year='{latest_year}'",
        })
        scored = []
        for r in raw:
            t = str(r.get("town") or "").strip()
            if not _is_municipality(t) or "(" in t:
                continue
            try:
                val = float(r["value"])
            except (KeyError, TypeError, ValueError):
                continue
            if val <= 0:
                continue
            scored.append({"town": _canonical_town(t), "value": round(val)})
    if not scored:
        return None
    scored.sort(key=lambda s: (-s["value"], s["town"]))
    state_med = round(statistics.median(s["value"] for s in scored))
    top = scored[0]
    return {
        "latest_year": latest_year,
        "edition": edition,
        "n": len(scored),
        "state_value": state_med,
        "top": {"town": top["town"], "value": top["value"]},
        "rows": [
            {"state": s["town"], "value": s["value"], "rank": i + 1,
             "highlight": i == 0}
            for i, s in enumerate(scored[:10])
        ],
        "all": [
            {"town": s["town"], "value": s["value"], "rank": i + 1}
            for i, s in enumerate(scored)
        ],
        "query": (
            f"GET /resource/{cfg.get('socrata_id', 'fixture')}.json "
            f"$where=metric='{metric}' AND year='{latest_year}' ({edition}; {len(scored)} towns)"
        ),
    }
