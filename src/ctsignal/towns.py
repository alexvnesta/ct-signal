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
SCHEMA = 2   # bump when parsing/cleaning rules change; older
             # stored snapshots are refetched regardless of age
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
        if d["NAME"].startswith("County subdivisions not defined"):
            continue        # Census pseudo-places for unorganized land
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
            if int(stored.get("schema", 1)) < SCHEMA:
                raise ValueError("schema")
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
            data = {"schema": SCHEMA, "vintage": f"{year} ACS 5-year ({int(year) - 4}–{year})",
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
.mapblock{margin:1.2rem 0 .4rem}
.mapchips{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:.7rem}
.mapchips button{background:var(--panel);border:1px solid var(--line);
  border-radius:999px;padding:.32rem .8rem;font:.72rem/1.1 var(--mono);
  color:var(--dim);cursor:pointer;letter-spacing:.04em}
.mapchips button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.mapchips button:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.mapflex{display:flex;gap:1.2rem;align-items:flex-start;flex-wrap:wrap}
svg.townsmap{width:min(100%,560px);height:auto;background:var(--panel);
  border:1px solid var(--line);border-radius:8px;padding:6px}
svg.townsmap path{stroke:#fff;stroke-width:.5;transition:fill .3s;
  cursor:pointer}
svg.townsmap path:hover{stroke:var(--ink);stroke-width:1.2}
svg.townsmap path:focus-visible{stroke:var(--acc);stroke-width:2;
  outline:none}
.maplegend{display:flex;flex-direction:column;gap:.3rem;
  font:.74rem/1.2 var(--sans);color:var(--dim);min-width:150px}
.maplegend .sw{display:inline-block;width:.9rem;height:.9rem;
  border:1px solid var(--line);margin-right:.45rem;vertical-align:-1px}
.mtip{position:fixed;pointer-events:none;background:var(--ink);color:#fff;
  padding:.45rem .7rem;border-radius:6px;font-size:.8rem;z-index:5;
  box-shadow:0 4px 14px rgba(20,30,40,.25);max-width:240px}
.mtip b{display:block;font-size:.86rem;margin-bottom:.15rem}
.mapnote{color:var(--faint);font-size:.76rem;margin:.5rem 0 1.1rem}
</style>"""


_MAP_JSON = config.ROOT / "assets" / "ct-towns.json"

_MAP_JS = """
<script>
const MT = __MT__;
const MMETA = __MMETA__;
window._n = __N__;
const RAMP = ["#f6f0e3","#ecd9bd","#dfb183","#c9722f","#a85408"];
const NOVAL = "#eae5da";
let metric = "income";
function fmtV(kind, v){ if (v===null||v===undefined) return "\\u2014";
  if (kind==="usd") return "$"+Math.round(v).toLocaleString("en-US");
  if (kind==="pct") return v.toFixed(1)+"%";
  if (kind==="int") return Math.round(v).toLocaleString("en-US");
  return v.toLocaleString("en-US"); }
function ord(n){ if(!n) return null; const s=["th","st","nd","rd"],
  v=n%100; return n+(s[v-20]||s[v]||s[0])+"-highest"; }
function quantiles(vals){ const v=vals.slice().sort((a,b)=>a-b), q=[];
  for (let i=1;i<5;i++) q.push(v[Math.floor(v.length*i/5)]); return q; }
function bucket(v, qs){ for (let i=0;i<4;i++) if (v<=qs[i]) return i;
  return 4; }
const tip = document.createElement("div"); tip.className="mtip";
tip.style.display="none"; document.body.appendChild(tip);
const paths = Array.from(
  document.querySelectorAll("svg.townsmap path"));
function paint(){
  const meta = MMETA[metric];
  const vals = paths.map(p=>((MT[p.dataset.n]||{})[metric])).filter(
    v=>v!==null&&v!==undefined);
  const qs = quantiles(vals);
  paths.forEach(p=>{
    const v=(MT[p.dataset.n]||{})[metric];
    p.style.fill = (v===null||v===undefined) ? NOVAL : RAMP[bucket(v,qs)];
    const r=(MT[p.dataset.n]||{})[metric+"_r"];
    p.setAttribute("aria-label", p.dataset.n+": "+fmtV(meta.kind,v)+
      (r? " \\u2014 "+ord(r)+" of "+window._n[metric] : ""));
  });
  let h = '<span class="dim" style="font-weight:700">shade = '+
    meta.label+' (quintiles)</span>';
  const edges=[null,...qs,null];
  for (let i=0;i<5;i++){
    const lo=edges[i], hi=edges[i+1];
    const rng = lo===null ? "under "+fmtV(meta.kind,hi) :
      hi===null ? fmtV(meta.kind,lo)+" and up" :
      fmtV(meta.kind,lo)+" \\u2013 "+fmtV(meta.kind,hi);
    h += '<span><i class="sw" style="background:'+RAMP[i]+'"></i>'+rng+
      '</span>';
  }
  h += '<span><i class="sw" style="background:'+NOVAL+
    '"></i>Census-suppressed</span>';
  document.getElementById("ml").innerHTML=h;
  document.getElementById("mlab").textContent=meta.label.toLowerCase();
}
paths.forEach(p=>{
  p.setAttribute("aria-label", p.dataset.n);
  p.setAttribute("tabindex", "0");
  p.setAttribute("role", "link");
  p.addEventListener("keydown",e=>{
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault(); location.href = p.dataset.h; }});
  p.addEventListener("mousemove",e=>{
    const d=MT[p.dataset.n]||{}, v=d[metric];
    const r=(v!==null&&v!==undefined)?d[metric+"_r"]:null;
    tip.innerHTML = "<b>"+p.dataset.n+"</b>"+MMETA[metric].label+": "+
      fmtV(MMETA[metric].kind,v)+(r? " \\u00b7 "+ord(r)+" of "+
      window._n[metric] : " \\u00b7 not published");
    tip.style.display="block";
    tip.style.left=Math.min(e.clientX+14, innerWidth-260)+"px";
    tip.style.top=(e.clientY+16)+"px";
  });
  p.addEventListener("mouseleave",()=>{tip.style.display="none";});
  p.addEventListener("focus",()=>{
    const b=p.getBoundingClientRect();
    p.dispatchEvent(new MouseEvent("mousemove",
      {clientX:b.x+b.width/2, clientY:b.y+b.height/2}));});
  p.addEventListener("blur",()=>{tip.style.display="none";});
  p.addEventListener("click",()=>{location.href=p.dataset.h;});
});
document.querySelectorAll(".mapchips button").forEach(b=>{
  b.addEventListener("click",()=>{
    metric=b.dataset.m;
    document.querySelectorAll(".mapchips button").forEach(x=>{
      x.classList.toggle("on",x===b);
      x.setAttribute("aria-pressed",x===b);});
    paint();
  });
});
paint();
</script>"""


def _map_html(data: dict) -> str:
    """The choropleth, baked: Census boundaries as inline SVG paths, town
    values embedded, five lines of vanilla JS doing quintile coloring. No
    tile provider, no scripts phoning home — the map is the data."""
    if not _MAP_JSON.exists():
        return ""
    try:
        geo = json.loads(_MAP_JSON.read_text())
    except ValueError:
        return ""
    slug = {t["name"]: t["slug"] for t in data["towns"]}
    mt = {t["name"]: {**{k: t.get(k) for k, _, _, _ in LABELS},
                      **{f"{k}_r": t.get(f"{k}_rank")
                         for k, _, _, _ in LABELS}}
          for t in data["towns"] if t["name"] in slug}
    paths = "".join(
        f'<path d="{g["d"]}" data-n="{_ESC(g["name"])}" '
        f'data-h="/town/{slug[g["name"]]}"></path>'
        for g in geo["towns"] if g["name"] in slug)
    chips = "".join(
        f'<button type="button" data-m="{k}"'
        f' aria-pressed="{("true" if k == "income" else "false")}"'
        f' class="{("on" if k == "income" else "")}">{_ESC(lab)}</button>'
        for k, lab, _, _ in LABELS[1:])
    mm = {k: {"label": lab, "kind": kind} for k, lab, _, kind in LABELS}
    # "of 169" was a lie for any suppressed measure: a rank can only
    # run across the towns that actually have a published value.
    n = {k: sum(1 for t in data["towns"]
                if isinstance(t.get(f"{k}_rank"), int))
         for k, _, _, _ in LABELS}
    js = (_MAP_JS.replace("__MT__", json.dumps(mt, separators=(",", ":")))
          .replace("__MMETA__", json.dumps(mm))
          .replace("__N__", json.dumps(n)))
    return ('<div class="mapblock">\n<div class="mapchips" role="group" '
            'aria-label="Color the map by">\n' + chips + '</div>\n'
            '<div class="mapflex">\n<svg class="townsmap" viewBox="0 0 '
            + str(geo["width"]) + " " + str(geo["height"]) +
            '" role="img" aria-label="Map of Connecticut towns shaded by '
            'the chosen measure">' + paths + '</svg>\n'
            '<div class="maplegend" id="ml"></div>\n</div>\n'
            '<p class="mapnote">Click a town for its full page. Shading '
            'is a quintile split of <span id="mlab">median household '
            'income</span> among towns with published values; boundaries: '
            + _ESC(geo["source"]) + '.</p>\n</div>\n' + js)


def index_page(data: dict) -> str:
    map_html = _map_html(data)
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
{map_html}
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
