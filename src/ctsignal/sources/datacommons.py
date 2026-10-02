from __future__ import annotations

import json
import pathlib

from .. import config

STATE_NAMES = {
    "geoId/01": "Alabama", "geoId/02": "Alaska", "geoId/04": "Arizona",
    "geoId/05": "Arkansas", "geoId/06": "California", "geoId/08": "Colorado",
    "geoId/09": "Connecticut", "geoId/10": "Delaware", "geoId/11": "District of Columbia",
    "geoId/12": "Florida", "geoId/13": "Georgia", "geoId/15": "Hawaii",
    "geoId/16": "Idaho", "geoId/17": "Illinois", "geoId/18": "Indiana",
    "geoId/19": "Iowa", "geoId/20": "Kansas", "geoId/21": "Kentucky",
    "geoId/22": "Louisiana", "geoId/23": "Maine", "geoId/24": "Maryland",
    "geoId/25": "Massachusetts", "geoId/26": "Michigan", "geoId/27": "Minnesota",
    "geoId/28": "Mississippi", "geoId/29": "Missouri", "geoId/30": "Montana",
    "geoId/31": "Nebraska", "geoId/32": "Nevada", "geoId/33": "New Hampshire",
    "geoId/34": "New Jersey", "geoId/35": "New Mexico", "geoId/36": "New York",
    "geoId/37": "North Carolina", "geoId/38": "North Dakota", "geoId/39": "Ohio",
    "geoId/40": "Oklahoma", "geoId/41": "Oregon", "geoId/42": "Pennsylvania",
    "geoId/44": "Rhode Island", "geoId/45": "South Carolina", "geoId/46": "South Dakota",
    "geoId/47": "Tennessee", "geoId/48": "Texas", "geoId/49": "Utah",
    "geoId/50": "Vermont", "geoId/51": "Virginia", "geoId/53": "Washington",
    "geoId/54": "West Virginia", "geoId/55": "Wisconsin", "geoId/56": "Wyoming",
    # PR joins the 52-peer set and prints with a real name (DC is mapped above).
    "geoId/72": "Puerto Rico",
}

CT = "geoId/09"
_CLIENT = None


class DataCommonsAuthError(RuntimeError):
    pass


def client():
    global _CLIENT
    if _CLIENT is None:
        from datacommons_client import DataCommonsClient

        _CLIENT = DataCommonsClient(api_key=config.DC_API_KEY)
    return _CLIENT


def _latest_by_entity(payload: dict, variable: str) -> dict[str, tuple[str, float]]:
    out: dict[str, tuple[str, float]] = {}
    by_var = payload.get("byVariable", {}).get(variable, {})
    for entity, blob in by_var.get("byEntity", {}).items():
        obs = blob.get("observations")
        if obs is None:
            obs = [o for f in blob.get("orderedFacets", []) for o in f.get("observations", [])]
        if not obs:
            continue
        latest = max(obs, key=lambda o: o.get("date", ""))
        if latest.get("value") is None:
            continue
        out[entity] = (latest.get("date", ""), float(latest["value"]))
    return out


def observations(variables: list[str]) -> dict:
    if not config.DC_API_KEY:
        raise DataCommonsAuthError("Data Commons key missing (set DC_API_KEY)")
    resp = client().observation.fetch_observations_by_entity_type(
        date="LATEST", parent_entity="country/USA",
        entity_type="State", variable_dcids=variables,
    )
    return resp.model_dump()


MONTH_RE = __import__("re").compile(r"^\d{4}-\d{2}$")


def trend(indicator: dict, months: int = 48) -> list[dict] | None:
    from datacommons_client.models.observation import ObservationDate

    resp = client().observation.fetch(
        variable_dcids=indicator["dcid"],
        date=ObservationDate.ALL,
        entity_dcids=[CT, "country/USA"],
    )
    by_entity = resp.model_dump()["byVariable"].get(indicator["dcid"], {}).get("byEntity", {})
    rows: list[dict] = []
    seen_series = set()
    for entity, label in [(CT, "Connecticut"), ("country/USA", "United States")]:
        blob = by_entity.get(entity)
        if not blob:
            continue
        best: dict[str, float] = {}
        for facet in blob.get("orderedFacets", []):
            monthly = {
                o["date"]: float(o["value"])
                for o in facet.get("observations", [])
                if o.get("value") is not None and MONTH_RE.match(o.get("date", ""))
            }
            if len(monthly) > len(best):
                best = monthly
        if not best:
            continue
        for date in sorted(best)[-months:]:
            rows.append({"date": date, "series": label, "value": round(best[date], 2)})
        seen_series.add(label)
    if len(seen_series) < 2 or len(rows) < 12:
        return None
    return rows


def stackup(indicator: dict, fixture: pathlib.Path | None = None) -> dict | None:
    payload, cached = None, False
    try:
        variables = [indicator["dcid"]]
        if indicator.get("denominator"):
            variables.append(indicator["denominator"])
        payload = observations(variables)
    except Exception:
        if fixture and fixture.exists():
            payload, cached = json.loads(fixture.read_text()), True
        else:
            return None
    num = _latest_by_entity(payload, indicator["dcid"])
    den = _latest_by_entity(payload, indicator["denominator"]) if indicator.get("denominator") else None
    if den is not None and indicator.get("per"):
        num = {
            e: (d, v / den[e][1] * indicator["per"])
            for e, (d, v) in num.items() if den.get(e) and den[e][1]
        }
    if CT not in num or not num:
        return None
    ranked = sorted(num.items(), key=lambda kv: kv[1][1], reverse=True)
    rows, ct_block = [], None
    for rank, (entity, (date, value)) in enumerate(ranked, start=1):
        if entity == CT:
            ct_block = {"value": round(value, 2), "date": date, "rank": rank}
        rows.append({"state": STATE_NAMES.get(entity, entity),
                     "value": round(value, 2), "rank": rank,
                     "highlight": entity == CT})
    if ct_block is None:
        return None
    return {"rows": rows, "ct": ct_block, "n": len(rows), "cache": cached,
            "query": f"DC v2 observations variable={indicator['dcid']} parent=country/USA type=State"}
