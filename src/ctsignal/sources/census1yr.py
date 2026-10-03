"""US Census Bureau direct: ACS 1-year state estimates.

Data Commons is our default source, but its ACS named variables ride the
5-year releases, which run ~2 years stale for state totals. The Census API
itself publishes 1-year estimates for every state within months of the
reference year, so the four housing/income/poverty comparisons fetch here.

Two live-verified quirks drive the design:
  - The API intermittently serves an HTML error page with HTTP 200, so every
    fetch retries until the body parses as a JSON array.
  - The 2024 redesign renumbered tables (median gross rent moved from
    B25107 to B25113, the poverty universe is B17020). Codes are pinned in
    the catalog; a missing column returns no data rather than silently
    ranking the wrong series, and the fixture takes over.
"""
from __future__ import annotations

import json
import pathlib
import time
import urllib.error
import urllib.request

from .. import config
from .datacommons import STATE_NAMES

CT = "09"

API = "https://api.census.gov/data/{vintage}/acs/acs1?get=NAME,{cols}&for=state:*&key={key}"


class CensusError(RuntimeError):
    pass


def _get_json(url: str, tries: int = 6, pause: float = 2.0) -> list:
    last = "no attempt"
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                body = resp.read().decode("utf-8", "replace")
            rows = json.loads(body)
            if isinstance(rows, list) and rows and isinstance(rows[0], list):
                return rows
            last = "body is not a data array"       # flaky HTML-200 page
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):
                raise CensusError(f"vintage missing at {exc.code}") from None
            last = f"HTTP {exc.code}"
        except (json.JSONDecodeError, OSError) as exc:
            last = str(exc)[:120]
        time.sleep(pause)
    raise CensusError(f"census fetch failed: {last}")


def _values(rows: list, spec: dict) -> dict[str, float]:
    """Map state FIPS -> indicator value from a Census tabular response."""
    hdr = rows[0]
    num_col = spec.get("value") or spec["num"]
    want = [c for c in (num_col, spec.get("den")) if c]
    if any(c not in hdr for c in want) or "state" not in hdr:
        return {}                        # this vintage uses other codes
    vi, ni = hdr.index(num_col), hdr.index(num_col)
    di = hdr.index(spec["den"]) if spec.get("den") else -1
    gi = hdr.index("state")
    out: dict[str, float] = {}
    for row in rows[1:]:
        try:
            if di > 0:
                num, den = float(row[ni]), float(row[di])
                if den:
                    out[row[gi]] = round(num / den * float(spec.get("per", 100)), 2)
            else:
                out[row[gi]] = float(row[vi])
        except (ValueError, TypeError):
            continue
    return out


def _rank(values: dict[str, float], vintage: str, spec: dict) -> dict:
    ranked = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
    rows, ct_block = [], None
    for rank, (fips, value) in enumerate(ranked, start=1):
        if fips == CT:
            ct_block = {"value": value, "date": vintage, "rank": rank}
        rows.append({"state": STATE_NAMES.get(f"geoId/{fips}", fips),
                     "value": value, "rank": rank, "highlight": fips == CT})
    table = spec.get("table", "")
    return {
        "rows": rows, "ct": ct_block, "n": len(rows), "cache": False,
        "query": (f"api.census.gov ACS 1-Year {vintage}: "
                  f"get=NAME,{table or spec.get('value') or spec['num']}&for=state:*"),
        "citation": (f"https://data.census.gov/table/ACSDT1Y{vintage}.{table}"
                     "?g=040XX00US$0400000" if table else
                     "https://www.census.gov/programs-surveys/acs"),
    }


def stackup(spec: dict, fixture: pathlib.Path | None = None) -> dict | None:
    """ACS 1-year state comparison, same shape as datacommons.stackup().

    spec (catalog census1yr block): vintages [2025, 2024]; a `value` column,
    or a `num`/`den` ratio scaled by `per`; `table` for the citation link.
    """
    if config.CENSUS_API_KEY:
        cols = [c for c in (spec.get("value") or spec["num"], spec.get("den")) if c]
        for vintage in spec["vintages"]:
            url = API.format(vintage=vintage, cols=",".join(cols),
                             key=config.CENSUS_API_KEY)
            try:
                values = _values(_get_json(url), spec)
            except CensusError:
                # vintage not shipped (404 fast) or API hiccup (retries
                # exhausted): try the next vintage, then fall to fixtures
                continue
            if CT in values and len(values) >= 40:
                return _rank(values, str(vintage), spec)
    if fixture and fixture.exists():
        blob = json.loads(fixture.read_text())
        return _rank(blob["values"], blob["vintage"], spec)
    return None
