"""Town desk: every Connecticut place at a glance.

One ACS five-year-profile call returns all 174 towns (five-year estimates
are how small towns get honest numbers, and the vintage says so). The table,
the town pages, and the state row are computed from that one fetch; nothing
here is invented. Suppressed cells come through as Census sentinels and stay
hidden as "—", never as a zero.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.request
from html import escape as _ESC

from . import config, theme, util

PROFILE = ("https://api.census.gov/data/{year}/acs/acs5/profile"
           "?get=NAME,DP05_0001E,DP05_0018E,DP03_0062E,"
           "DP04_0134E,DP04_0089E&for={geo}&key={key}")
# Poverty as a headcount ratio over the B17020 people universe — the same
# table the board cards fetch, so a town page and the state story can never
# disagree about what poverty means. (B17010 counts families; it is not this.)
DETAIL = ("https://api.census.gov/data/{year}/acs/acs5"
          "?get=B17020_001E,B17020_002E&for={geo}&key={key}")
LABELS = [("pop", "Population", "DP05_0001E", "int"),
          ("age", "Median age", "DP05_0018E", "num"),
          ("income", "Median household income", "DP03_0062E", "usd"),
          ("poverty", "Below poverty line", "B17020", "pct"),
          ("rent", "Median gross rent", "DP04_0134E", "usd"),
          ("value", "Median home value", "DP04_0089E", "usd")]
STORED = config.ROOT / "data" / "towns.json"
STORY_FOR = {"income": None, "poverty": "797faed5a836", "rent": "0125297ea839"}


def _clean(raw: str, kind: str, field: str = "") -> float | int | None:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v <= -6e8:                       # Census "not published" sentinels
        return None
    if kind == "int":
        return int(v)
    if kind == "num":
        return round(v, 1)
    if kind == "usd":
        floor = {"rent": 200, "value": 50000}.get(field, 10000)
        return None if v < floor else int(v)
    return int(v)


def _fetch(url: str) -> list[list[str]] | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _rows(payload: list[list[str]]) -> list[dict]:
    head = payload[0]
    out = []
    for row in payload[1:]:
        d = dict(zip(head, row))
        name = re.sub(r"\s+(town|city)\s*,.*Connecticut\s*$", "", d["NAME"])
        rec = {"name": name,
               "slug": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
               "geoid": d["state"] + d.get("county", "")
               + d.get("county subdivision", "")}
        for key, _, var, k in LABELS:
            rec[key] = _clean(d.get(var, ""), k, key)
        out.append(rec)
    return out


def ensure() -> dict | None:
    """Refresh annually; offline or keyless falls back to the committed file."""
    age_days = 0
    if STORED.exists():
        try:
            stored = json.loads(STORED.read_text())
            age_days = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(
                stored["fetched_at"])).days
            if age_days < 300:
                return stored
        except (ValueError, KeyError):
            stored = None
    key = config.CENSUS_API_KEY
    this = dt.date.today().year
    for year in (str(this - 2), str(this - 3)):   # newest ACS5 first
        if not key:
            break
        geo_t = "county+subdivision:*&in=state:09"
        got = _fetch(PROFILE.format(year=year, geo=geo_t, key=key))
        det = _fetch(DETAIL.format(year=year, geo=geo_t, key=key))
        state = _fetch(PROFILE.format(year=year, geo="state:09", key=key))
        sdet = _fetch(DETAIL.format(year=year, geo="state:09", key=key))
        if got and det and state and sdet:
            towns = sorted(_rows(got), key=lambda t: -(t["pop"] or 0))
            _poverty(towns, det)
            st = _rows(state)[0]
            _poverty([st], sdet)
            data = {"vintage": f"{year} ACS 5-year ({int(year) - 4}–{year})",
                    "fetched_at": dt.datetime.now(dt.timezone.utc)
                    .isoformat(timespec="seconds"),
                    "ct": st, "towns": towns}
            _rank(data)
            util.atomic_write_text(STORED, json.dumps(data))
            return data
    return json.loads(STORED.read_text()) if STORED.exists() else None


def _poverty(recs: list[dict], payload: list[list[str]]) -> None:
    head = payload[0]
    by_geo = {}
    for row in payload[1:]:
        d = dict(zip(head, row))
        gid = d["state"] + d.get("county", "") + d.get("county subdivision", "")
        try:
            uni, poor = int(d["B17020_001E"]), int(d["B17020_002E"])
        except (KeyError, ValueError):
            uni = poor = -1
        rec_by_slug = None
        for r in recs:
            if r.get("geoid") == gid:
                rec_by_slug = r
                break
        if rec_by_slug is not None:
            rec_by_slug["poverty"] = (round(poor / uni * 100, 1)
                                      if uni > 0 and poor >= 0 else None)


def _rank(data: dict) -> None:
    n = len(data["towns"])
    for key, _, _, _ in LABELS:
        vals = [t for t in data["towns"] if isinstance(t.get(key), (int, float))]
        vals.sort(key=lambda t: -t[key])
        for i, t in enumerate(vals, 1):
            t[f"{key}_rank"] = i
    data["n"] = n


def _ord(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _fmt(rec: dict, key: str, kind: str) -> str:
    v = rec.get(key)
    if v is None:
        return "—"
    if kind == "int":
        return f"{v:,}"
    if kind == "num":
        return f"{v}"
    if kind == "pct":
        return f"{v}%"
    return f"${v:,}"


def _delta(town: dict, ct: dict, key: str, kind: str) -> str:
    a, b = town.get(key), ct.get(key)
    if a is None or b is None or not b:
        return "—"
    pct = (a - b) / abs(b) * 100
    word = "above" if pct >= 0 else "below"
    if kind == "pct":
        return f"{abs(a - b):.1f} points {word} CT"
    return f"{abs(pct):.0f}% {word} CT"


def snapshot() -> dict | None:
    """The ACS fetch, for newsroom to fold into its town pages."""
    if not STORED.exists():
        return None
    try:
        return json.loads(STORED.read_text())
    except ValueError:
        return None


def table_for(t: dict, data: dict, esc) -> str:
    """The ACS table for one town, as HTML. Ranks are across the places the
    Census publishes, and every cell that is suppressed stays a dash."""
    ct = data["ct"]
    rows = ""
    for key, label, _var, kind in LABELS[1:]:
        rank = t.get(f"{key}_rank")
        rk = f"{_ord(rank)} of {data['n']}" if rank else "not published"
        sid = STORY_FOR.get(key)
        link = (f' <a href="/story/{sid}">the state answer &rarr;</a>' if sid else "")
        rows += (f'<tr><td>{esc(label)}{link}</td><td>{_fmt(t, key, kind)}</td>'
                 f'<td class="dim">{_fmt(ct, key, kind)}</td>'
                 f'<td>{_delta(t, ct, key, kind)}</td><td class="dim">{rk}</td></tr>')
    return (f'<h2>Where {esc(t["name"])} sits</h2>'
            f'<table class="townstats"><thead><tr><th>Measure</th>'
            f'<th>{esc(t["name"])}</th><th>Connecticut</th><th>Difference</th>'
            f'<th>Rank among towns</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="provenance">US Census Bureau, {data["vintage"]}, county-subdivision '
            f'level — the estimates built for places this size. Ranks run across the '
            f'{data["n"]} places with published values. Suppressed cells are dashes, '
            f'not zeros. Poverty is the same table the state story uses, so the two '
            f'pages cannot tell different stories.</p>')


def lookup(data: dict, name: str) -> dict | None:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    for t in data["towns"]:
        if t["slug"] == slug:
            return t
    return None


_PAGE_CSS = """<style>
.townstats{width:100%;border-collapse:collapse;margin:1.2rem 0}
.townstats th{text-align:left;font:700 .72rem/1 var(--sans);color:var(--dim);
  text-transform:uppercase;letter-spacing:.1em;padding:0 .9rem .6rem 0;
  border-bottom:1px solid var(--acc)}
.townstats td{padding:.6rem .9rem .6rem 0;border-bottom:1px solid var(--line);
  font-size:.95rem}
.townstats .dim{color:var(--dim)}
.filter{margin:1rem 0;background:var(--panel);border:1px solid var(--line);
  border-radius:8px;color:var(--ink);padding:.55rem .8rem;font:inherit;width:min(280px,100%)}
</style>"""


def index_page(data: dict) -> str:
    rows = ""
    for t in data["towns"]:
        cells = "".join(f"<td>{_fmt(t, k, kind)}</td>"
                        for k, _, _, kind in LABELS)
        rows += (f'<tr><td><a href="/town/{t["slug"]}">{_ESC(t["name"])}</a></td>'
                 f"{cells}</tr>")
    body = f"""<div class="wrap col">
<div class="sechead"><h2>Every Connecticut town, one table</h2>
<p class="sechelp">{data["vintage"]} — five-year estimates, because that is what
makes a town of 800 readable. Sort is by population; type to find your town.</p></div>
<input class="filter" id="q" placeholder="Filter towns…" aria-label="Filter towns"
 autocomplete="off">
<table class="townstats" id="tt"><thead><tr><th>Town</th>
{''.join(f"<th>{lab}</th>" for _, lab, _, _ in LABELS)}</tr></thead>
<tbody>{rows}</tbody></table>
<p class="provenance">US Census Bureau, {data["vintage"]}, county-subdivision
level. Ranks run across the {data["n"]} places the Census publishes for
Connecticut. Dashes are Census-suppressed cells, not zeros — the same honesty
rule as the board. <a href="/sources">Sources &amp; failure logs</a>.</p>
</div>
<script>
document.getElementById("q").addEventListener("input", function () {{
  const v = this.value.toLowerCase();
  document.querySelectorAll("#tt tbody tr").forEach(r => {{
    r.hidden = !r.textContent.toLowerCase().includes(v); }});
}});
</script>"""
    return theme.page(title="Connecticut towns · CT Signal",
                      desc="Every Connecticut town's income, poverty, rent, and "
                           f"home value against the state — {data['vintage']}.",
                      path="/towns", body=_PAGE_CSS + body)


def publish() -> dict | None:
    """Write the town table page and refresh the snapshot file. Individual
    town pages are owned by newsroom (they are card-shaped) and fold in
    table_for(); two modules must not write the same file."""
    data = ensure()
    if not data:
        return None
    util.atomic_write_text(config.ROOT / "towns.html", index_page(data))
    return data
