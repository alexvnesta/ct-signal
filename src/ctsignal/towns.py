"""Town desk: every Connecticut place at a glance.

One ACS five-year-profile call returns all 174 towns (five-year estimates
are how small towns get honest numbers, and the vintage says so). The table,
the town pages, and the state row are computed from that one fetch; nothing
here is invented. Suppressed cells come through as Census sentinels and stay
hidden as "—", never as a zero.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
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
STORY_FOR = {"income": "916a9da3173f", "poverty": "797faed5a836",
             "rent": "0125297ea839", "value": "517fafa716bc"}


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
        rk = f"{_ord(rank)}-highest of {data['n']}" if rank else "not published"
        sid = STORY_FOR.get(key)
        link = (f'<span class="state-link"><a href="/story/{sid}">'
                f'Statewide comparison &rarr;</a></span>' if sid else "")
        rows += (f'<tr><td>{esc(label)}{link}</td><td>{_fmt(t, key, kind)}</td>'
                 f'<td class="dim">{_fmt(ct, key, kind)}</td>'
                 f'<td>{_delta(t, ct, key, kind)}</td><td class="dim">{rk}</td></tr>')
    table = (f'<table class="townstats"><thead><tr><th>Measure</th>'
             f'<th>{esc(t["name"])}</th><th>Connecticut</th><th>Difference</th>'
             f'<th>Rank among towns (1 = highest)</th></tr></thead><tbody>{rows}</tbody></table>')
    return (f'<h2>Where {esc(t["name"])} sits</h2>'
            f'<p class="tablehint">On a phone, swipe the table sideways for the '
            f'difference and rank columns.</p>'
            f'<div class="tscroll" role="region" tabindex="0" '
            f'aria-label="Statistics for {esc(t["name"])}, scrolls sideways '
            f'on phones">{table}</div>'
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
.towns-page{padding-top:1.1rem}
.towns-head{display:flex;align-items:baseline;justify-content:space-between;
  flex-wrap:wrap;gap:.4rem 1.2rem;border-bottom:3px solid var(--ink);
  padding-bottom:.6rem;margin-bottom:1rem}
.towns-head h1{font:700 clamp(1.75rem,3.6vw,2.35rem)/1.12 var(--serif);
  margin:0;letter-spacing:-.012em}
.towns-head p{color:var(--dim);font-size:.9rem;margin:.25rem 0 0;max-width:68ch}
.towns-head-act{display:inline-flex;align-items:center;min-height:44px;
  padding:.35rem .8rem;border:1px solid var(--line);border-radius:6px;
  background:var(--panel);color:var(--ink);font:600 .82rem/1 var(--sans);
  text-decoration:none!important;white-space:nowrap}
.towns-head-act:hover{border-color:var(--acc);color:var(--acc)}
.towns-controls{display:flex;flex-wrap:wrap;align-items:center;
  justify-content:space-between;gap:.65rem 1rem;margin:0 0 1rem}
.filter{margin:0;background:var(--panel);border:1px solid var(--line);
  border-radius:6px;color:var(--ink);padding:.5rem .8rem;font:inherit;
  font-size:.92rem;min-height:44px;width:min(280px,100%)}
.filter:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
.mapchips{display:flex;flex-wrap:wrap;gap:.4rem;margin:0}
.mapchips button{background:var(--panel);border:1px solid var(--line);
  border-radius:999px;padding:.4rem .85rem;min-height:40px;
  font:.76rem/1.1 var(--sans);font-weight:600;color:var(--dim);cursor:pointer}
.mapchips button:hover{color:var(--ink);border-color:var(--acc)}
.mapchips button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.mapchips button:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.towns-stage{display:grid;grid-template-columns:minmax(0,1fr);
  gap:1.15rem 1.5rem;align-items:start;margin:0 0 1.4rem}
@media(min-width:920px){
  .towns-stage{grid-template-columns:minmax(0,1.55fr) minmax(0,1fr)}
}
.mapblock{margin:0}
.mapflex{display:block}
svg.townsmap{display:block;width:100%;height:auto;background:var(--panel);
  border:1px solid var(--rule);border-radius:8px;padding:8px}
svg.townsmap path{stroke:#fff;stroke-width:.55;transition:fill .25s;
  cursor:pointer}
svg.townsmap path:hover,svg.townsmap path.hl{stroke:var(--ink);stroke-width:1.4}
svg.townsmap path:focus-visible{stroke:var(--acc);stroke-width:2;outline:none}
.maplegend{display:flex;flex-wrap:wrap;gap:.35rem .85rem;
  font:.74rem/1.25 var(--sans);color:var(--dim);width:100%;margin-top:.65rem}
.maplegend .sw{display:inline-block;width:.85rem;height:.85rem;
  border:1px solid var(--line);margin-right:.4rem;vertical-align:-1px}
.mtip{position:fixed;pointer-events:none;background:var(--ink);color:#fff;
  padding:.45rem .7rem;border-radius:6px;font-size:.8rem;z-index:5;
  box-shadow:0 4px 14px rgba(20,30,40,.25);max-width:240px}
.mtip b{display:block;font-size:.86rem;margin-bottom:.15rem}
.mapnote{color:var(--faint);font-size:.76rem;margin:.45rem 0 0}
.town-spot{background:var(--panel);border:1px solid var(--rule);
  border-top:3px solid var(--acc2);padding:1rem 1.15rem}
.spot-k{font:800 .7rem/1 var(--sans);letter-spacing:.15em;
  text-transform:uppercase;color:var(--acc);margin:0 0 .45rem}
.spot-pick{display:flex;gap:.45rem;align-items:center;margin:0 0 .75rem}
.spot-pick select{flex:1;min-width:0;background:var(--bg);
  border:1px solid var(--line);border-radius:5px;color:var(--ink);
  padding:.45rem .65rem;font:600 .9rem/1.2 var(--sans);min-height:44px}
.spot-name{font:700 1.45rem/1.15 var(--serif);color:var(--ink);margin:0 0 .15rem}
.spot-sub{font-size:.8rem;color:var(--faint);margin:0 0 .65rem}
.spot-list{list-style:none;margin:0 0 .85rem;padding:0;border-top:1px solid var(--rule)}
.spot-list li{display:flex;justify-content:space-between;align-items:baseline;
  gap:.6rem;padding:.45rem 0;border-bottom:1px solid var(--rule);font-size:.86rem}
.spot-list .sk{color:var(--dim)}
.spot-list .sv{font-weight:700;color:var(--ink);text-align:right;
  font-variant-numeric:tabular-nums}
.spot-list .sr{display:block;font-weight:400;font-size:.74rem;color:var(--faint)}
.spot-actions{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
.spot-primary{display:inline-flex;align-items:center;min-height:44px;
  padding:.45rem .9rem;background:var(--ink);color:#fff!important;
  font:700 .84rem/1 var(--sans);border-radius:5px;text-decoration:none!important}
.spot-primary:hover{background:var(--acc)}
.spot-sec{display:inline-flex;align-items:center;min-height:44px;
  padding:.45rem .8rem;background:var(--bg);color:var(--ink);
  border:1px solid var(--line);border-radius:5px;font:600 .82rem/1 var(--sans);
  cursor:pointer}
.spot-sec:hover{border-color:var(--acc);color:var(--acc)}
.spot-sec[aria-pressed="true"]{background:var(--bg2);border-color:var(--acc);
  color:var(--acc)}
.spot-sug{margin:.7rem 0 0;padding-top:.65rem;border-top:1px solid var(--rule);
  font-size:.82rem;color:var(--dim);display:flex;flex-wrap:wrap;
  align-items:center;gap:.4rem}
.spot-sug button{background:none;border:0;color:var(--acc);font:700 .82rem var(--sans);
  text-decoration:underline;cursor:pointer;padding:.2rem 0;min-height:36px}
.spot-sug .yt-dismiss{color:var(--faint);font-weight:400}
.townstats{width:100%;border-collapse:collapse;margin:.6rem 0 1.2rem}
.tscroll{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;
  scrollbar-gutter:stable}
.tscroll:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.tablehint{color:var(--faint);font-size:.76rem;margin:.9rem 0 -.2rem}
@media(min-width:721px){.tablehint{display:none}}
.townstats th{text-align:left;font:700 .72rem/1.2 var(--sans);color:var(--dim);
  text-transform:uppercase;letter-spacing:.09em;padding:.45rem .9rem .6rem 0;
  border-bottom:2px solid var(--ink)}
.townstats td{padding:.6rem .9rem .6rem 0;border-bottom:1px solid var(--line);
  font-size:.94rem;font-variant-numeric:tabular-nums}
.townstats .dim{color:var(--dim)}
@media(max-width:720px){
.townstats th:first-child,.townstats td:first-child{position:sticky;left:0;
  z-index:1;background:var(--bg);box-shadow:1px 0 0 var(--line)}
.townstats thead th:first-child{z-index:2}
}
</style>"""


_MAP_JSON = config.ROOT / "assets" / "ct-towns.json"

_MAP_JS = """
<script>
const MT = __MT__;
const MMETA = __MMETA__;
window._n = __N__;
const RAMP = ["#f6f0e3","#ecd9bd","#dfb183","#c9722f","#a85408"];
const NOVAL = "#eae5da";
let metric = __DEFAULT_M__;
function fmtV(kind, v){ if (v===null||v===undefined) return "\\u2014";
  if (kind==="usd") return "$"+Math.round(v).toLocaleString("en-US");
  if (kind==="pct") return v.toFixed(1)+"%";
  if (kind==="mill") return Number(v).toFixed(2)+" mills";
  if (kind==="int") return Math.round(v).toLocaleString("en-US");
  return v.toLocaleString("en-US"); }
function ord(n){ if(!n) return null;
  const o = n%10===1&&n%100!==11?"st":n%10===2&&n%100!==12?"nd":
            n%10===3&&n%100!==13?"rd":"th";
  return n+o+"-highest"; }
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
  p.setAttribute("tabindex", "-1");
  p.setAttribute("role", "link");
  p.addEventListener("keydown",e=>{
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault(); location.href = p.dataset.h; return; }
    const i = paths.indexOf(p);
    let j = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i+1) % paths.length;
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") j = (i-1+paths.length) % paths.length;
    if (e.key === "Home") j = 0;
    if (e.key === "End") j = paths.length - 1;
    if (j !== null) { e.preventDefault();
      paths.forEach(x => x.setAttribute("tabindex", "-1"));
      paths[j].setAttribute("tabindex", "0"); paths[j].focus(); }});
  p.addEventListener("mousemove",e=>{
    const d=MT[p.dataset.n]||{}, v=d[metric];
    const r=(v!==null&&v!==undefined)?d[metric+"_r"]:null;
    tip.innerHTML = "<b>"+p.dataset.n+"</b>"+MMETA[metric].label+": "+
      fmtV(MMETA[metric].kind,v)+(r? " \\u00b7 "+ord(r)+" of "+
      window._n[metric] : " \\u00b7 not published");
    tip.style.display="block";
    tip.style.left=Math.min(e.clientX+14, innerWidth-260)+"px";
    tip.style.top=(e.clientY+16)+"px";
    if (window._spotTown && p.dataset.s) window._spotTown(p.dataset.s, false);
  });
  p.addEventListener("mouseleave",()=>{tip.style.display="none";});
  p.addEventListener("focus",()=>{
    const b=p.getBoundingClientRect();
    p.dispatchEvent(new MouseEvent("mousemove",
      {clientX:b.x+b.width/2, clientY:b.y+b.height/2}));});
  p.addEventListener("blur",()=>{tip.style.display="none";});
  p.addEventListener("click",()=>{location.href=p.dataset.h;});
});
// Roving focus: the map is one tab stop; arrows move between towns.
if (paths.length) paths[0].setAttribute("tabindex", "0");
function setMetric(b){
    document.querySelectorAll(".mapchips button").forEach(x=>{
      x.classList.toggle("on",x===b);
      x.setAttribute("aria-pressed",x===b);});
    metric=b.dataset.m; paint(); }
window._setMetric = k => { const b=document.querySelector(`.mapchips button[data-m="${k}"]`); if (b) setMetric(b); };
document.querySelectorAll(".mapchips button").forEach(b=>{
  b.addEventListener("click",()=>{ setMetric(b); });
});
paint();
</script>"""


def _load_local_cards(cards: list[dict] | None = None) -> list[dict]:
    if cards is not None:
        return cards
    path = config.OUTPUT_DIR / "cards.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text()).get("cards") or []
    except (OSError, ValueError):
        return []


def _local_town_extras(cards: list[dict] | None = None) -> tuple[dict[str, dict], dict]:
    """Extract FY2027 mill rate, car tax rate, 2024 median home sale, and
    per-pupil school spending per town slug from live local cards."""
    extras: dict[str, dict] = {}
    meta: dict = {}
    for c in _load_local_cards(cards):
        ind = c.get("indicator")
        av = c.get("answer_values") or {}
        trows = c.get("towns") or []
        if not trows:
            continue
        if ind == "mill_rates":
            meta["mill_fy"] = str(av.get("date") or "FY2027")
            meta["mill_n"] = av.get("n") or len(trows)
            meta["mill_rows"] = trows
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                slot = extras.setdefault(s, {})
                slot["mill"] = r.get("rate")
                slot["mill_r"] = r.get("rank")
                if r.get("mv_rate") is not None:
                    slot["mv_rate"] = r.get("mv_rate")
        elif ind == "home_sales_price":
            meta["sale_yr"] = str(av.get("date") or "2024")
            meta["sale_n"] = av.get("n") or len(trows)
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                slot = extras.setdefault(s, {})
                slot["sale"] = r.get("value")
                slot["sale_r"] = r.get("rank")
        elif ind == "school_spending_per_pupil":
            meta["school_yr"] = str(av.get("date") or "2023")
            meta["school_n"] = av.get("n") or len(trows)
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                slot = extras.setdefault(s, {})
                slot["school"] = r.get("value")
                slot["school_r"] = r.get("rank")
    return extras, meta


def _map_html(data: dict, extras: dict[str, dict] | None = None,
              meta: dict | None = None) -> tuple[str, str] | str:
    """The choropleth, baked: Census boundaries as inline SVG paths, town
    values embedded, vanilla JS doing quintile coloring. Includes FY2027 mill
    rate, 2024 single-family home sales, and school spending beside ACS data."""
    if not _MAP_JSON.exists():
        return ""
    try:
        geo = json.loads(_MAP_JSON.read_text())
    except ValueError:
        return ""
    extras = extras or {}
    meta = meta or {}
    has_mill = any(e.get("mill") is not None for e in extras.values())
    has_sale = any(e.get("sale") is not None for e in extras.values())
    has_school = any(e.get("school") is not None for e in extras.values())
    extra_defs: list[tuple[str, str, str]] = []
    if has_mill:
        extra_defs.append(("mill", f'{meta.get("mill_fy", "FY2027")} mill rate', "mill"))
    if has_sale:
        extra_defs.append(("sale", f'{meta.get("sale_yr", "2024")} home sale', "usd"))
    if has_school:
        extra_defs.append(("school", "School spending/pupil", "usd"))
    default_m = "mill" if has_mill else "income"
    all_chips = extra_defs + [(k, lab, kind) for k, lab, _, kind in LABELS[1:]]

    slug = {t["name"]: t["slug"] for t in data["towns"]}
    mt = {}
    for t in data["towns"]:
        if t["name"] not in slug:
            continue
        ex = extras.get(t["slug"], {})
        row_m = {
            **{k: t.get(k) for k, _, _, _ in LABELS},
            **{f"{k}_r": t.get(f"{k}_rank") for k, _, _, _ in LABELS},
        }
        for ek in ("mill", "sale", "school"):
            if ek in ex:
                row_m[ek] = ex[ek]
                row_m[f"{ek}_r"] = ex.get(f"{ek}_r")
        mt[t["name"]] = row_m
    paths = "".join(
        f'<path d="{g["d"]}" data-n="{_ESC(g["name"])}" '
        f'data-s="{slug[g["name"]]}" '
        f'data-h="/town/{slug[g["name"]]}"></path>'
        for g in geo["towns"] if g["name"] in slug)
    chips = "".join(
        f'<button type="button" data-m="{k}"'
        f' aria-pressed="{("true" if k == default_m else "false")}"'
        f' class="{("on" if k == default_m else "")}">{_ESC(lab)}</button>'
        for k, lab, _ in all_chips)
    mm = {k: {"label": lab, "kind": kind} for k, lab, _, kind in LABELS}
    for k, lab, kind in extra_defs:
        mm[k] = {"label": lab, "kind": kind}
    n = {k: sum(1 for t in data["towns"]
                if isinstance(t.get(f"{k}_rank"), int))
         for k, _, _, _ in LABELS}
    for ek, mk in (("mill", "mill_n"), ("sale", "sale_n"), ("school", "school_n")):
        n[ek] = meta.get(mk) or sum(1 for e in extras.values() if e.get(ek) is not None)
    js = (_MAP_JS.replace("__MT__", json.dumps(mt, separators=(",", ":")))
          .replace("__MMETA__", json.dumps(mm))
          .replace("__N__", json.dumps(n))
          .replace("__DEFAULT_M__", json.dumps(default_m)))
    chips_html = ('<div class="mapchips" role="group" '
                  'aria-label="Color the map by">\n' + chips + '</div>')
    default_label = mm[default_m]["label"].lower()
    map_body = ('<div class="mapblock">\n'
                '<div class="mapflex">\n<svg class="townsmap" viewBox="0 0 '
                + str(geo["width"]) + " " + str(geo["height"]) +
                '" role="group" aria-label="Connecticut mill rate and town data map">' + paths + '</svg>\n'
                '<div class="maplegend" id="ml"></div>\n</div>\n'
                '<p class="mapnote">Hover a town to preview on the right; click '
                'for its full file and tax calculator. Shading is a quintile split of '
                f'<span id="mlab">{_ESC(default_label)}</span> among towns '
                'with published values; boundaries: '
                + _ESC(geo["source"]) + '.</p>\n</div>\n' + js)
    return chips_html, map_body


def _mill_extremes_html(meta: dict) -> str:
    """Side-by-side 10 lowest and 10 highest Connecticut FY2027 mill rates."""
    rows = meta.get("mill_rows") or []
    if len(rows) < 20:
        return ""
    fy = _ESC(str(meta.get("mill_fy") or "FY2027"))
    highest = rows[:10]
    lowest = list(reversed(rows[-10:]))

    def _tbl(items: list[dict]) -> str:
        body = ""
        for r in items:
            s = re.sub(r"[^a-z0-9]+", "-", str(r["town"]).lower()).strip("-")
            mv = f'{r["mv_rate"]:.2f}' if r.get("mv_rate") is not None else "—"
            body += (
                f'<tr><td><a href="/town/{_ESC(s)}">{_ESC(r["town"])}</a></td>'
                f'<td class="num">{r["rate"]:.2f}</td>'
                f'<td class="num">{mv}</td></tr>'
            )
        return (
            '<table><thead><tr><th>Town</th>'
            '<th class="num">Real property</th>'
            '<th class="num">Car (MV)</th></tr></thead>'
            f'<tbody>{body}</tbody></table>'
        )

    return f"""<section class="extremes-grid" aria-label="Lowest and highest Connecticut mill rates">
<div class="extremes-card low">
<div class="spot-k">Lowest property tax rates · {fy}</div>
<h2>10 lowest mill rates in Connecticut</h2>
{_tbl(lowest)}
</div>
<div class="extremes-card high">
<div class="spot-k">Highest property tax rates · {fy}</div>
<h2>10 highest mill rates in Connecticut</h2>
{_tbl(highest)}
</div>
</section>"""


def briefs() -> dict:
    """Slug -> the five numbers a reader would share about their town, plus
    the rank denominators. Feeds the board's your-town strip and the per-town
    share cards; one source of truth for both."""
    data = snapshot()
    if not data:
        return {}
    counts = {k: sum(1 for t in data["towns"] if isinstance(t.get(f"{k}_rank"), int))
              for k, *_ in LABELS}
    out = {}
    for t in data["towns"]:
        row = [[t.get(k), t.get(f"{k}_rank")]
               for k, *_ in LABELS]
        out[t["slug"]] = {"n": t["name"], "v": row}
    return {"towns": out, "n": counts, "vintage": data["vintage"]}



_MY_TOWN_JS = r"""
<script>
(function(){var b=window.__TB__,slugs=Object.keys(b.towns).sort();
function fmt(i,p){var v=p[0],r=p[1],n=b.n[i];
 var s=v===null?"\u2014":i==="poverty"?v.toFixed(1)+"%":
  i==="age"?String(Math.round(v)):
  i==="pop"?Math.round(v).toLocaleString("en-US"):
  "$"+Math.round(v).toLocaleString("en-US");
 if(i==="pop"||r===null)return s;
 var o=r%10===1&&r%100!==11?"st":r%10===2&&r%100!==12?"nd":
       r%10===3&&r%100!==13?"rd":"th";
 return s+" ("+r+o+"-highest of "+n+")";}
function splitVal(full){var idx=full.indexOf(" (");
 if(idx<0)return [full,""];
 return [full.slice(0,idx),full.slice(idx+2,-1)];}
var el=document.getElementById("yourtown");
var saved=null,dismiss=null,sugSlug=null;
try{saved=localStorage.getItem("ct-town");
    dismiss=localStorage.getItem("ct-town-no");}catch(e){}
var active=saved&&b.towns[saved]?saved:(b.towns["hartford"]?"hartford":slugs[0]);
function highlightMap(s){
 document.querySelectorAll("svg.townsmap path.hl").forEach(function(p){p.classList.remove("hl");});
 var p=document.querySelector('svg.townsmap path[data-s="'+s+'"]');
 if(p)p.classList.add("hl");}
function row(label,txt){var parts=splitVal(txt);
 return '<li><span class="sk">'+label+'</span><span class="sv">'+parts[0]+
  (parts[1]?'<span class="sr">'+parts[1]+'</span>':'')+'</span></li>';}
function render(s,syncSelect){
 var t=b.towns[s]; if(!t)return; active=s; var v=t.v,isSaved=(saved===s);
 var selHtml='<div class="spot-pick"><label class="sr-only" for="yt-sel">Choose a town</label>'
  +'<select id="yt-sel" aria-label="Choose your town">'
  +slugs.map(function(k){return '<option value="'+k+'"'+(k===s?' selected':'')+'>'+b.towns[k].n+'</option>';}).join("")
  +'</select></div>';
 var millRow = t.m ? row((b.mill_fy||"FY2027")+" mill rate",
   Number(t.m[0]).toFixed(2)+" mills"+(t.m[1]?" ("+t.m[1]+(t.m[1]%10===1&&t.m[1]%100!==11?"st":t.m[1]%10===2&&t.m[1]%100!==12?"nd":t.m[1]%10===3&&t.m[1]%100!==13?"rd":"th")+"-highest of "+(b.mill_n||169)+")":"")) : "";
 var carRow = (t.m && t.m[2]!=null) ? row("Car (MV) mill rate", Number(t.m[2]).toFixed(2)+" mills") : "";
 var saleRow = t.s ? row("2024 median home sale", "$"+Math.round(t.s[0]).toLocaleString("en-US")) : "";
 var list='<ul class="spot-list">'
  +millRow+carRow+saleRow
  +row("Median income",fmt("income",v[2]))
  +row("Below poverty",fmt("poverty",v[3]))
  +row("Median gross rent",fmt("rent",v[4]))
  +row("Median home value",fmt("value",v[5]))
  +row("Median age",fmt("age",v[1]))
  +'</ul>';
 var sugHtml=(sugSlug&&sugSlug!==saved&&b.towns[sugSlug])
  ?'<div class="spot-sug"><span>Near <b>'+b.towns[sugSlug].n+'</b>?</span>'
   +'<button type="button" id="yt-yes">Switch to '+b.towns[sugSlug].n+'</button>'
   +'<button type="button" id="yt-no" class="yt-dismiss">dismiss</button></div>'
  :'';
 el.innerHTML='<div class="spot-k">'+(isSaved?'Your saved town':'Town spotlight')+'</div>'
  +selHtml
  +'<h2 class="spot-name">'+t.n+'</h2>'
  +'<p class="spot-sub">'+b.vintage+'</p>'
  +list
  +'<div class="spot-actions">'
  +'<a class="spot-primary" href="/town/'+s+'">Open '+t.n+' file \u2192</a>'
  +'<a class="spot-sec" href="/compare?a='+s+'">Compare</a>'
  +'<button type="button" id="yt-save" class="spot-sec" aria-pressed="'+(isSaved?'true':'false')+'">'
  +(isSaved?'\u2713 Saved':'Remember')+'</button>'
  +'</div>'+sugHtml;
 if(syncSelect!==false)highlightMap(s);
 var sel=document.getElementById("yt-sel");
 if(sel)sel.onchange=function(){render(this.value,true);};
 var btn=document.getElementById("yt-save");
 if(btn)btn.onclick=function(){
  if(saved===s){try{localStorage.removeItem("ct-town");}catch(e){} saved=null;}
  else{try{localStorage.setItem("ct-town",s);}catch(e){} saved=s;}
  render(s,true);};
 var yes=document.getElementById("yt-yes");
 if(yes)yes.onclick=function(){
  try{localStorage.setItem("ct-town",sugSlug);}catch(e){}
  saved=sugSlug; sugSlug=null; render(saved,true);};
 var no=document.getElementById("yt-no");
 if(no)no.onclick=function(){
  try{localStorage.setItem("ct-town-no","1");}catch(e){}
  sugSlug=null; render(active,false);};}
window._spotTown=function(s,sync){if(b.towns[s])render(s,sync);};
render(active,true);
var prod=/(^|\.)ctsignal\.org$/.test(location.hostname);
if(!saved&&!dismiss&&prod)fetch("/api/geo").then(function(r){return r.json();})
 .then(function(g){if(!g||g.region!=="CT"||!g.city)return;
  var s=g.city.toLowerCase().replace(/[^a-z]+/g,"-").replace(/^-|-$/g,"");
  if(b.towns[s]){sugSlug=s; render(active,false);}}).catch(function(){});
})();
</script>"""

def index_page(data: dict, cards: list[dict] | None = None) -> str:
    extras, meta = _local_town_extras(cards)
    map_parts = _map_html(data, extras=extras, meta=meta)
    chips_html, map_body = map_parts if isinstance(map_parts, tuple) else ("", map_parts)
    extremes_html = _mill_extremes_html(meta)
    has_mill = any(e.get("mill") is not None for e in extras.values())
    fy_lbl = _ESC(str(meta.get("mill_fy") or "FY2027"))
    rows = ""
    for t in data["towns"]:
        ex = extras.get(t["slug"], {})
        mill_cell = (f'<td>{ex["mill"]:.2f}</td>' if has_mill and ex.get("mill") is not None
                     else ('<td>—</td>' if has_mill else ''))
        cells = "".join(f"<td>{_fmt(t, k, kind)}</td>"
                        for k, _, _, kind in LABELS)
        rows += (f'<tr><td><a href="/town/{t["slug"]}">{_ESC(t["name"])}</a></td>'
                 f"{mill_cell}{cells}</tr>")
    mill_th = f"<th>{fy_lbl} Mill Rate</th>" if has_mill else ""
    body = f"""<div class="wrap towns-page">
<div class="towns-head">
<div><h1>Connecticut mill rates &amp; town data</h1>
<p>Interactive map and directory for all {data["n"]} Connecticut municipalities —
{fy_lbl} OPM property &amp; car mill rates, 2024 single-family home sales,
per-pupil school spending, and {data["vintage"]} Census benchmarks.</p></div>
<div style="display:flex;flex-wrap:wrap;gap:.5rem">
<a class="towns-head-act" href="/compare">Compare towns &rarr;</a>
<a class="towns-head-act" href="/towns.csv">Download all {data["n"]} towns (CSV)</a>
</div>
</div>
<div class="towns-controls">
<input class="filter" id="q" placeholder="Filter {data["n"]} towns…" aria-label="Filter towns"
 autocomplete="off">
{chips_html}
</div>
<div class="towns-stage">
{map_body}
<aside class="town-spot" id="yourtown" aria-label="Town spotlight">
<div class="spot-k">Town spotlight</div>
<p>Pick a town on the map or table to inspect its key municipal and Census figures.</p>
</aside>
</div>
{extremes_html}
<p class="tablehint">On a phone, swipe the table sideways for poverty, rent
and home value.</p>
<div class="tscroll" role="region" aria-label="Town statistics table, scrolls sideways on phones" tabindex="0">
<table class="townstats" id="tt"><thead><tr><th>Town</th>{mill_th}
{''.join(f"<th>{lab}</th>" for _, lab, _, _ in LABELS)}</tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="provenance">Sources: CT OPM ({fy_lbl} mill rates &amp; 2024 real-estate
sales), CSDE/OPM school spending, and US Census Bureau ({data["vintage"]},
county-subdivision level). Dashes are suppressed or unavailable cells, not zeros.
<a href="/sources">Sources &amp; failure logs</a>.</p>
</div>
<script>
const _m0 = (location.hash.match(/^#m=(\\w+)/) || [])[1];
  if (_m0 && window._setMetric) window._setMetric(_m0);
  document.getElementById("q").addEventListener("input", function () {{
  const v = this.value.toLowerCase();
  document.querySelectorAll("#tt tbody tr").forEach(r => {{
    r.hidden = !r.textContent.toLowerCase().includes(v); }});
}});
</script>"""
    return theme.page(
        title="Connecticut Mill Rates, Home Prices & Income by Town (All 169) · CT Signal",
        desc="Compare all 169 Connecticut towns: FY2027 mill rates, property tax "
             "calculator, 2024 home sales, school spending, income, rent & "
             "poverty from official CT data.",
        path="/towns", body=_PAGE_CSS + body, compact=True)


def _csv_text(data: dict, cards: list[dict] | None = None) -> str:
    """The town table as CSV: raw values, not formatted display strings, so
    a spreadsheet can sort and chart them without parsing dollar signs."""
    extras, _ = _local_town_extras(cards)
    cols = [("town", "name"), ("population", "pop"), ("median_age", "age"),
            ("median_household_income", "income"),
            ("below_poverty_pct", "poverty"),
            ("median_gross_rent", "rent"),
            ("median_home_value", "value")]
    ranks = [f"{key}_rank" for key, _, _, _ in LABELS[1:]]
    extra_cols = ["mill_rate_fy2027", "motor_vehicle_mill_rate",
                  "median_home_sale_2024", "school_spending_per_pupil"]
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([label for label, _ in cols] + ranks + extra_cols)
    for town in data["towns"]:
        row = [town.get(key, "") for _, key in cols]
        for key, _, _, _ in LABELS[1:]:
            rank = town.get(f"{key}_rank")
            row.append(rank if isinstance(rank, int) else "")
        ex = extras.get(town["slug"], {})
        row.extend([
            ex.get("mill", ""), ex.get("mv_rate", ""),
            ex.get("sale", ""), ex.get("school", ""),
        ])
        writer.writerow(row)
    return buf.getvalue()


def publish(cards: list[dict] | None = None) -> dict | None:
    """Write the town table page and refresh the snapshot file. Individual
    town pages are owned by newsroom (they are card-shaped) and fold in
    table_for(); two modules must not write the same file."""
    data = ensure()
    if not data:
        return None
    from . import towns as _self
    tb = _self.briefs() or {"towns": {}, "n": {}}
    extras, meta = _local_town_extras(cards)
    for slug, ex in extras.items():
        if slug in tb.get("towns", {}):
            if ex.get("mill") is not None:
                tb["towns"][slug]["m"] = [ex["mill"], ex.get("mill_r"), ex.get("mv_rate")]
            if ex.get("sale") is not None:
                tb["towns"][slug]["s"] = [ex["sale"], ex.get("sale_r")]
    tb["mill_fy"] = meta.get("mill_fy", "FY2027")
    tb["mill_n"] = meta.get("mill_n", 169)
    page = index_page(data, cards=cards)
    inject = (f'<script>window.__TB__='
              f'{json.dumps(tb, separators=(",", ":"))};</script>'
              + _MY_TOWN_JS)
    util.atomic_write_text(config.ROOT / "towns.html",
                           page.replace("</body>", inject + "</body>", 1))
    util.atomic_write_text(config.ROOT / "towns.csv", _csv_text(data, cards=cards))
    return data


_COMPARE_CSS = """<style>
.cmp-page{padding-top:1.1rem;padding-bottom:2rem}
.cmp-head{border-bottom:3px solid var(--ink);padding-bottom:.65rem;margin-bottom:1rem}
.cmp-head h1{font:700 clamp(1.75rem,3.6vw,2.35rem)/1.12 var(--serif);margin:0}
.cmp-head p{color:var(--dim);font-size:.92rem;margin:.3rem 0 0;max-width:72ch}
.cmp-presets{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin:0 0 .9rem}
.cmp-presets span{font:700 .72rem/1 var(--sans);text-transform:uppercase;
  letter-spacing:.12em;color:var(--dim);margin-right:.25rem}
.cmp-presets button{background:var(--panel);border:1px solid var(--line);
  border-radius:999px;padding:.35rem .75rem;min-height:38px;
  font:600 .78rem/1 var(--sans);color:var(--dim);cursor:pointer}
.cmp-presets button:hover{border-color:var(--acc);color:var(--ink)}
.cmp-controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
  gap:.65rem;margin:0 0 .95rem;background:var(--panel);
  border:1px solid var(--rule);border-radius:6px;padding:.85rem}
@media(max-width:860px){.cmp-controls{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:520px){.cmp-controls{grid-template-columns:1fr}}
.cmp-ctl label{display:block;font:700 .7rem/1.2 var(--sans);text-transform:uppercase;
  letter-spacing:.1em;color:var(--dim);margin:0 0 .3rem}
.cmp-ctl select,.cmp-ctl input{width:100%;min-height:44px;background:var(--bg);
  border:1px solid var(--line);border-radius:5px;color:var(--ink);
  padding:.45rem .65rem;font:600 .9rem/1.2 var(--sans)}
.cmp-actions{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1rem}
.cmp-table{width:100%;border-collapse:collapse;background:var(--panel);
  border:1px solid var(--rule)}
.cmp-table th{text-align:left;padding:.75rem .9rem;border-bottom:2px solid var(--ink);
  font:700 .76rem/1.25 var(--sans);text-transform:uppercase;letter-spacing:.08em;
  color:var(--dim);vertical-align:bottom}
.cmp-table th .ct-name{display:block;font:700 1.15rem/1.2 var(--serif);
  text-transform:none;letter-spacing:0;color:var(--ink);margin-bottom:.15rem}
.cmp-table th a{font:600 .76rem/1 var(--sans);text-transform:none;letter-spacing:0}
.cmp-table td{padding:.68rem .9rem;border-bottom:1px solid var(--rule);
  font-size:.92rem;font-variant-numeric:tabular-nums;vertical-align:top}
.cmp-table td:first-child{font-weight:600;color:var(--ink);min-width:190px}
.cmp-table .cm-sub{display:block;font-weight:400;font-size:.74rem;color:var(--faint);
  margin-top:.12rem}
.cmp-table .cm-val{font-weight:700;color:var(--ink);font-size:1rem}
.cmp-table .cm-rk{display:block;font-size:.75rem;color:var(--dim);margin-top:.12rem}
.cmp-table tr.cm-hi td{background:var(--bg2)}
.cmp-table td.ct-bench{color:var(--dim);background:var(--bg)}
</style>"""


def compare_data(data: dict, cards: list[dict] | None = None) -> dict:
    """Merge ACS town snapshot + live local Socrata card tables into one compact
    JSON payload for the zero-backend /compare tool."""
    by_slug: dict[str, dict] = {}
    for t in data.get("towns") or []:
        by_slug[t["slug"]] = {
            "n": t["name"],
            "pop": t.get("pop"),
            "age": t.get("age"),
            "income": t.get("income"), "income_r": t.get("income_rank"),
            "poverty": t.get("poverty"), "poverty_r": t.get("poverty_rank"),
            "rent": t.get("rent"), "rent_r": t.get("rent_rank"),
            "value": t.get("value"), "value_r": t.get("value_rank"),
        }
    meta: dict = {
        "vintage": data.get("vintage", ""),
        "n_acs": data.get("n", len(by_slug)),
        "ct": {
            "income": (data.get("ct") or {}).get("income"),
            "poverty": (data.get("ct") or {}).get("poverty"),
            "rent": (data.get("ct") or {}).get("rent"),
            "value": (data.get("ct") or {}).get("value"),
            "age": (data.get("ct") or {}).get("age"),
        },
        "assess_ratio": 0.70,
    }
    for c in (cards or []):
        ind = c.get("indicator")
        av = c.get("answer_values") or {}
        trows = c.get("towns") or []
        if not trows:
            continue
        if ind == "mill_rates":
            meta["mill_fy"] = str(av.get("date") or "")
            meta["state_mill"] = av.get("state")
            meta["mill_n"] = av.get("n") or len(trows)
            if av.get("assess_ratio"):
                meta["assess_ratio"] = av["assess_ratio"]
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                if s in by_slug:
                    by_slug[s]["mill"] = r.get("rate")
                    by_slug[s]["mill_r"] = r.get("rank")
                    if r.get("mv_rate") is not None:
                        by_slug[s]["mv_rate"] = r.get("mv_rate")
        elif ind == "home_sales_price":
            meta["sale_yr"] = str(av.get("date") or "")
            meta["state_sale"] = av.get("state")
            meta["sale_n"] = av.get("n") or len(trows)
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                if s in by_slug:
                    by_slug[s]["sale"] = r.get("value")
                    by_slug[s]["sale_c"] = r.get("sales")
                    by_slug[s]["sale_r"] = r.get("rank")
        elif ind == "housing_permits":
            meta["permits_yr"] = str(av.get("date") or "")
            meta["state_permits"] = av.get("state")
            meta["permits_n"] = av.get("n") or len(trows)
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                if s in by_slug:
                    by_slug[s]["permits"] = r.get("value")
                    by_slug[s]["permits_r"] = r.get("rank")
        elif ind == "school_spending_per_pupil":
            meta["school_yr"] = str(av.get("date") or "")
            meta["state_school"] = av.get("state")
            meta["school_n"] = av.get("n") or len(trows)
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                if s in by_slug:
                    by_slug[s]["school"] = r.get("value")
                    by_slug[s]["school_r"] = r.get("rank")
        elif ind == "grand_list_growth":
            meta["gl_yr"] = str(av.get("date") or "")
            meta["gl_n"] = av.get("n") or len(trows)
            for r in trows:
                s = re.sub(r"[^a-z0-9]+", "-", str(r.get("town") or "").lower()).strip("-")
                if s in by_slug:
                    by_slug[s]["gl_pct"] = r.get("pct")
                    by_slug[s]["gl_r"] = r.get("rank")
    return {"meta": meta, "towns": by_slug}


_COMPARE_JS = r"""<script>
(function(){
  var D = window.__CMP__;
  if (!D || !D.towns) return;
  var T = D.towns, M = D.meta || {};
  var slugs = Object.keys(T).sort(function(a,b){return T[a].n.localeCompare(T[b].n);});
  var selA = document.getElementById("cmp-a");
  var selB = document.getElementById("cmp-b");
  var selC = document.getElementById("cmp-c");
  var priceEl = document.getElementById("cmp-price");
  var out = document.getElementById("cmp-out");

  function fill(sel, allowNone){
    sel.innerHTML = (allowNone ? '<option value="">None (2-town view)</option>' : '')
      + slugs.map(function(s){return '<option value="'+s+'">'+T[s].n+'</option>';}).join("");
  }
  fill(selA, false); fill(selB, false); fill(selC, true);

  var qp = new URLSearchParams(location.search);
  var initA = qp.get("a"), initB = qp.get("b"), initC = qp.get("c");
  selA.value = T[initA] ? initA : (T["hartford"] ? "hartford" : slugs[0]);
  selB.value = T[initB] ? initB : (selA.value === "west-hartford" ? "new-haven" : (T["west-hartford"] ? "west-hartford" : slugs[1]));
  selC.value = T[initC] ? initC : "";
  if (qp.get("price") && !isNaN(Number(qp.get("price")))) priceEl.value = String(Math.max(50000, Number(qp.get("price"))));

  function ord(r){
    if (!r) return "";
    var o = r%10===1&&r%100!==11?"st":r%10===2&&r%100!==12?"nd":r%10===3&&r%100!==13?"rd":"th";
    return r+o;
  }
  function usd(v){ return v==null ? "\u2014" : "$"+Math.round(v).toLocaleString("en-US"); }
  function num(v){ return v==null ? "\u2014" : Math.round(v).toLocaleString("en-US"); }
  function pct(v){ return v==null ? "\u2014" : Number(v).toFixed(1)+"%"; }
  function mill(v){ return v==null ? "\u2014" : Number(v).toFixed(2)+" mills"; }
  function rk(r, n){ return (r && n) ? ord(r)+"-highest of "+n : ""; }
  function copyText(txt, btn, okLabel){
    var orig = btn.textContent;
    function done(){ btn.textContent = okLabel; btn.classList.add("copied");
      setTimeout(function(){ btn.textContent = orig; btn.classList.remove("copied"); }, 2200); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(done).catch(function(){ fallback(); });
    } else fallback();
    function fallback(){
      var ta=document.createElement("textarea"); ta.value=txt; ta.style.position="fixed"; ta.style.opacity="0";
      document.body.appendChild(ta); ta.select(); try{ document.execCommand("copy"); done(); }catch(e){}
      document.body.removeChild(ta);
    }
  }

  function currentPrice(){
    var v = Number(String(priceEl.value || "").replace(/[^0-9.]/g, ""));
    return (v && v >= 10000) ? v : 450000;
  }
  function currentSlugs(){
    return [selA.value, selB.value, selC.value].filter(function(s){ return s && T[s]; });
  }
  function syncUrl(){
    var p = new URLSearchParams();
    p.set("a", selA.value); p.set("b", selB.value);
    if (selC.value) p.set("c", selC.value);
    var pr = currentPrice();
    if (pr !== 450000) p.set("price", String(Math.round(pr)));
    try { history.replaceState(null, "", location.pathname + "?" + p.toString()); } catch(e){}
  }

  function render(){
    syncUrl();
    var chosen = currentSlugs();
    var pr = currentPrice();
    var ratio = M.assess_ratio || 0.70;
    var stateTax = M.state_mill ? Math.round(pr * ratio * M.state_mill / 1000) : null;

    var headCells = chosen.map(function(s){
      return '<th><span class="ct-name">'+T[s].n+'</span><a href="/town/'+s+'">Full town file \u2192</a></th>';
    }).join("");
    var rows = [
      {
        label: "Est. annual tax on a "+usd(pr)+" home",
        sub: "70% statutory assessment \u00d7 "+(M.mill_fy||"FY2027")+" mill rate",
        hi: true,
        bench: stateTax ? usd(stateTax)+"/yr ("+usd(stateTax/12)+"/mo)" : "\u2014",
        cell: function(t){
          if (t.mill == null) return '<span class="cm-val">\u2014</span>';
          var yr = Math.round(pr * ratio * t.mill / 1000);
          var diff = stateTax ? (yr - stateTax) : null;
          var ds = diff === null ? "" : (diff >= 0 ? "+"+usd(diff)+" vs. CT" : "-"+usd(Math.abs(diff))+" vs. CT");
          return '<span class="cm-val">'+usd(yr)+'/yr</span><span class="cm-rk">'+usd(yr/12)+'/mo'+(ds ? ' \u00b7 '+ds : '')+'</span>';
        }
      },
      {
        label: "Property tax rate ("+(M.mill_fy||"FY2027")+")",
        sub: "CT OPM municipal real-property mill rate",
        bench: M.state_mill ? mill(M.state_mill)+" (weighted)" : "\u2014",
        cell: function(t){ return '<span class="cm-val">'+mill(t.mill)+'</span><span class="cm-rk">'+rk(t.mill_r, M.mill_n)+'</span>'; }
      },
      {
        label: "Car tax rate (motor vehicle)",
        sub: "CT OPM motor-vehicle mill rate (32.46 statutory cap)",
        bench: "32.46 mills max cap",
        cell: function(t){
          if (t.mv_rate == null) return '<span class="cm-val">\u2014</span>';
          var note = t.mv_rate >= 32.45 ? "at CT statutory cap" : "town MV rate";
          return '<span class="cm-val">'+mill(t.mv_rate)+'</span><span class="cm-rk">'+note+'</span>';
        }
      },
      {
        label: "Median single-family sale ("+(M.sale_yr||"2024")+")",
        sub: "CT OPM recorded closings (\u226510 sales)",
        bench: M.state_sale ? usd(M.state_sale) : "\u2014",
        cell: function(t){ return '<span class="cm-val">'+usd(t.sale)+'</span><span class="cm-rk">'+(t.sale_c ? num(t.sale_c)+' sales \u00b7 '+rk(t.sale_r, M.sale_n) : 'under 10 sales or not reported')+'</span>'; }
      },
      {
        label: "School spending per pupil ("+(M.school_yr||"2023")+")",
        sub: "CSDE / OPM Municipal Fiscal Indicators",
        bench: M.state_school ? usd(M.state_school)+" (median)" : "\u2014",
        cell: function(t){ return '<span class="cm-val">'+usd(t.school)+'</span><span class="cm-rk">'+rk(t.school_r, M.school_n)+'</span>'; }
      },
      {
        label: "New housing permits ("+(M.permits_yr||"2025")+")",
        sub: "CT DECD annual units permitted",
        bench: M.state_permits ? num(M.state_permits)+" statewide" : "\u2014",
        cell: function(t){ return '<span class="cm-val">'+(t.permits!=null?num(t.permits)+" units":"\u2014")+'</span><span class="cm-rk">'+rk(t.permits_r, M.permits_n)+'</span>'; }
      },
      {
        label: "Grand list change ("+(M.gl_yr||"latest")+")",
        sub: "Net taxable property base growth",
        bench: "\u2014",
        cell: function(t){
          var s = t.gl_pct==null ? "\u2014" : (t.gl_pct>=0?"+":"")+Number(t.gl_pct).toFixed(1)+"%";
          return '<span class="cm-val">'+s+'</span><span class="cm-rk">'+rk(t.gl_r, M.gl_n)+'</span>';
        }
      },
      {
        label: "Median household income",
        sub: M.vintage || "ACS 5-year",
        bench: usd((M.ct||{}).income),
        cell: function(t){ return '<span class="cm-val">'+usd(t.income)+'</span><span class="cm-rk">'+rk(t.income_r, M.n_acs)+'</span>'; }
      },
      {
        label: "Median gross rent",
        sub: M.vintage || "ACS 5-year",
        bench: usd((M.ct||{}).rent),
        cell: function(t){ return '<span class="cm-val">'+usd(t.rent)+'</span><span class="cm-rk">'+rk(t.rent_r, M.n_acs)+'</span>'; }
      },
      {
        label: "Below poverty line",
        sub: M.vintage || "ACS 5-year",
        bench: pct((M.ct||{}).poverty),
        cell: function(t){ return '<span class="cm-val">'+pct(t.poverty)+'</span><span class="cm-rk">'+rk(t.poverty_r, M.n_acs)+'</span>'; }
      },
      {
        label: "Population",
        sub: M.vintage || "ACS 5-year",
        bench: "Connecticut",
        cell: function(t){ return '<span class="cm-val">'+num(t.pop)+'</span>'; }
      }
    ];

    var bodyHtml = rows.map(function(r){
      var cls = r.hi ? ' class="cm-hi"' : '';
      var tds = chosen.map(function(s){ return '<td>'+r.cell(T[s])+'</td>'; }).join("");
      return '<tr'+cls+'><td>'+r.label+'<span class="cm-sub">'+r.sub+'</span></td>'+tds+'<td class="ct-bench">'+r.bench+'</td></tr>';
    }).join("");

    out.innerHTML = '<div class="tscroll" role="region" tabindex="0" aria-label="Town comparison table">'
      + '<table class="cmp-table"><thead><tr><th>Measure</th>'+headCells+'<th>Connecticut</th></tr></thead>'
      + '<tbody>'+bodyHtml+'</tbody></table></div>';
  }

  [selA, selB, selC].forEach(function(el){ el.addEventListener("change", render); });
  priceEl.addEventListener("input", render);
  document.querySelectorAll(".cmp-presets button").forEach(function(b){
    b.addEventListener("click", function(){
      selA.value = b.dataset.a; selB.value = b.dataset.b; selC.value = b.dataset.c || "";
      render();
    });
  });
  document.getElementById("cmp-copy-link").addEventListener("click", function(){
    var url = "https://ctsignal.org/compare" + location.search;
    copyText(url, this, "\u2713 Link copied");
  });
  document.getElementById("cmp-copy-sum").addEventListener("click", function(){
    var chosen = currentSlugs(), pr = currentPrice(), ratio = M.assess_ratio || 0.70;
    var lines = ["Connecticut town comparison ("+chosen.map(function(s){return T[s].n;}).join(" vs. ")+"):"];
    chosen.forEach(function(s){
      var t = T[s];
      var tax = t.mill!=null ? usd(Math.round(pr * ratio * t.mill / 1000))+"/yr on "+usd(pr)+" home" : "mill rate n/a";
      var sale = t.sale!=null ? ", 2024 median home sale "+usd(t.sale) : "";
      var sch = t.school!=null ? ", school spending "+usd(t.school)+"/pupil" : "";
      lines.push("- "+t.n+": "+(t.mill!=null?t.mill.toFixed(2)+" mills":"n/a")+" ("+tax+")"+sale+sch+".");
    });
    lines.push("Official CT OPM, DECD & Census receipts: https://ctsignal.org/compare"+location.search);
    copyText(lines.join("\n"), this, "\u2713 Summary copied");
  });
  render();
})();
</script>"""


def compare_page(data: dict, cards: list[dict] | None = None) -> str:
    payload = compare_data(data, cards)
    body = f"""<div class="wrap cmp-page">
<div class="breadcrumb"><a href="/towns">&larr; All 169 towns</a></div>
<div class="cmp-head">
<h1>Compare Connecticut towns</h1>
<p>Put two or three municipalities side by side — FY2027 property tax rates and
estimated tax bills, 2024 recorded single-family home sales, per-pupil school
spending, 2025 housing permits, and Census benchmarks. Every figure comes from
a named public dataset.</p>
</div>
<div class="cmp-presets" role="group" aria-label="Popular comparisons">
<span>Quick picks</span>
<button type="button" data-a="hartford" data-b="west-hartford">Hartford vs. West Hartford</button>
<button type="button" data-a="greenwich" data-b="stamford">Greenwich vs. Stamford</button>
<button type="button" data-a="new-haven" data-b="hamden">New Haven vs. Hamden</button>
<button type="button" data-a="bridgeport" data-b="fairfield">Bridgeport vs. Fairfield</button>
</div>
<div class="cmp-controls">
<div class="cmp-ctl"><label for="cmp-a">Town 1</label><select id="cmp-a"></select></div>
<div class="cmp-ctl"><label for="cmp-b">Town 2</label><select id="cmp-b"></select></div>
<div class="cmp-ctl"><label for="cmp-c">Town 3 (optional)</label><select id="cmp-c"></select></div>
<div class="cmp-ctl"><label for="cmp-price">Compare tax on home value ($)</label>
<input id="cmp-price" type="number" min="50000" step="25000" value="450000" inputmode="numeric"></div>
</div>
<div class="cmp-actions">
<button type="button" id="cmp-copy-sum" class="town-act-pri">Copy summary to share</button>
<button type="button" id="cmp-copy-link" class="town-act-btn">Copy comparison link</button>
</div>
<div id="cmp-out"><p class="meta">Loading town comparison&hellip;</p></div>
<p class="provenance">Tax estimates apply Connecticut\u2019s statutory 70%
assessment ratio (CGS &sect;12-64) to municipal real-property mill rates; fire,
water, and sewer districts are separate. Sources: CT OPM, CT DECD, CSDE, and
US Census Bureau ({_ESC(data.get("vintage", ""))}). <a href="/sources">Sources &amp; failure logs</a>.</p>
</div>"""
    page = theme.page(
        title="Compare Connecticut Towns: Mill Rates, Property Tax & Home Sales · CT Signal",
        desc="Compare any 2 or 3 Connecticut towns side by side: FY2027 property "
             "tax rates, estimated tax bills, 2024 home sale prices, school "
             "spending & Census income.",
        path="/compare", body=_COMPARE_CSS + body, compact=True,
    )
    inject = (f'<script>window.__CMP__='
              f'{json.dumps(payload, separators=(",", ":"))};</script>'
              + _COMPARE_JS)
    return page.replace("</body>", inject + "</body>", 1)


def write_compare(cards: list[dict] | None = None) -> None:
    data = snapshot() or ensure()
    if not data:
        return
    util.atomic_write_text(config.ROOT / "compare.html",
                           compare_page(data, cards))
