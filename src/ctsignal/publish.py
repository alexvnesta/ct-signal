"""Homepage export: the Connecticut board + the rolling feed of answered
questions, server-rendered so crawlers, RSS readers, and link previews all see
real content. Charts embed as JSON islands; the vega loader in theme upgrades
them to SVG progressively.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import html
import json

from . import cards as _cards
from . import config, theme, util

_YOUR_TOWN_JS = r"""
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
function render(){var s=null;try{s=localStorage.getItem("ct-town");}catch(e){}
 if(!s||!b.towns[s]){pick();return;}
 var t=b.towns[s],v=t.v;
 document.getElementById("yourtown").innerHTML=
  '<span class="yt-line1">Your town \u00b7 '+t.n+
  ' \u00b7 <a href="/town/'+s+'">town file \u2192</a></span>'
  +'<span class="yt-facts">income '+fmt("income",v[2])
  +" \u00b7 poverty "+fmt("poverty",v[3])
  +" \u00b7 rent "+fmt("rent",v[4])
  +" \u00b7 home value "+fmt("value",v[5])
  +" \u00b7 median age "+fmt("age",v[1])
  +' \u00b7 <button id="yt-chg" class="yt-change">change town</button></span>';
 var c=document.getElementById("yt-chg"); if(c)c.onclick=function(){
  try{localStorage.removeItem("ct-town");}catch(e){} render();};}
function pick(){var e=document.getElementById("yourtown");
 e.innerHTML="Your town? <select id=\"yt-sel\" aria-label=\"Choose your town\">"
  +slugs.map(function(s){return '<option value="'+s+'">'+b.towns[s].n+
    '</option>';}).join("")
  +'</select> <button id="yt-set" class="ytbtn">Remember it</button>';
 document.getElementById("yt-set").onclick=function(){
  try{localStorage.setItem("ct-town",
    document.getElementById("yt-sel").value);}catch(e){} render();};}
render();})();
</script>"""


_ESC = html.escape


def _parse(ts: str) -> dt.datetime:
    return util.parse_ts(ts)


def ago(iso: str, now: dt.datetime) -> str:
    """Honest freshness as machine-readable <time>: relative while fresh,
    absolute date past a day, always the publish wall clock in ET. 'now' is
    the publish moment, never the card's own stamp — a lead that has not
    been replaced can never claim 'just now' hours later."""
    d = _parse(iso)
    s = max(0.0, (now - d).total_seconds())
    when = util.clock(util.et(d))
    if s < 90:
        label = when
    elif s < 5400:
        label = f"{round(s / 60)} min ago · {when}"
    elif s < 86400:
        label = f"{round(s / 3600)} h ago · {when}"
    else:
        label = f"{util.et(d):%b %-d} · {when}"
    return f'<time datetime="{iso}">{label}</time>'


def _trigger_line(card: dict) -> str:
    prefix, title = theme.trigger_parts(card)
    return (f'<span class="trig"><span class="srclabel">Source:</span> '
            f'{prefix}{title}</span>')


def _kicker(card: dict, when: str) -> str:
    cache = ' <span class="badge">cache</span>' if card.get("cache") else ""
    return (f'{_ESC(card["topic"])} · {_ESC(card["stream"])} desk'
            f'{cache} · {when}')


def home_html(cards: list[dict], board: dict) -> str:
    # Freshness is measured against the publish moment, never against the
    # lead's own stamp (an unreplaced lead must not claim 'just now' later).
    now = dt.datetime.now(dt.timezone.utc)
    if cards:
        now = max(now, _parse(cards[0]["generated_at"]))

    # Broadsheet front: lead story with its chart as the artwork, a column
    # of second stories, a dated rail of the rest. The grid is populated
    # top-down from the feed, so the layout can never disagree with it.
    lead = ""
    sec2 = ""
    rail = ""
    # The lead is the paper's opinion. A national headline alone does not
    # get to form one about Connecticut: the Connecticut stream must be in
    # on the trigger, or several independent CT newsrooms must be.
    def _ct_trigger(x):
        h = x.get("headline") or {}
        return (x.get("stream") == "ct" or h.get("stream") == "ct"
                or int(h.get("ct_hits") or 0) >= 2)
    if cards and not _ct_trigger(cards[0]):
        _i = next((i for i, x in enumerate(cards) if _ct_trigger(x)), None)
        if _i:
            cards = [cards[_i]] + cards[:_i] + cards[_i + 1:]
    if cards:
        from . import newsroom
        c = cards[0]
        lead_kick = ("Today's lead" if _ct_trigger(c)
                     else "From the data desk")
        heroviz = ""
        if c.get("chart"):
            vdesc, vlabel = newsroom.chart_intro(c)
            heroviz = theme.viz(newsroom._spec_json(c["chart"]), "heroviz",
                                label=vlabel, caption=vdesc)
        # A story published today can legitimately rest on an older print
        # (FBI crime is annual) — the kicker says which, so "today" never
        # quietly borrows freshness the dataset does not have.
        _m = re.search(r"\d{4}", str((c.get("answer_values") or {})
                                     .get("date", "")))
        # "latest print" claimed knowledge of the source’s release
        # inventory; the kicker states only the vintage answered.
        _vint = (f" · data through {_m.group()}"
                 if _m and int(_m.group()) < dt.datetime.now().year else "")
        lead = f"""<article class="lead">
<span class="kicker">{lead_kick} · {_ESC(c["topic"])} · {_ESC(c["stream"])} desk{_vint}</span>
<h2><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h2>
<p class="lede">{_ESC(c["answer_text"])}</p>
{heroviz}
<div class="meta">{_trigger_line(c)}<span class="when">
{ago(c["generated_at"], now)}</span>
<a class="more" href="/story/{c["id"]}">Read the full story — with the chart
and the exact query →</a></div></article>"""

        # One jobs release must not become five of nine visible cards:
        # max two cards per triggering headline, max three per topic.
        def _trig(x):
            return (x.get("headline") or {}).get("url") or x["id"]
        trig = {_trig(cards[0]): 1}
        topic = {cards[0]["topic"]: 1}
        sel = []
        for c in cards[1:]:
            if len(sel) >= 9:
                break
            if trig.get(_trig(c), 0) >= 2 or topic.get(c["topic"], 0) >= 3:
                continue
            trig[_trig(c)] = trig.get(_trig(c), 0) + 1
            topic[c["topic"]] = topic.get(c["topic"], 0) + 1
            sel.append(c)
        for c in sel[:4]:
            fig = ""
            tpath = newsroom._thumb_path(c)
            if tpath:
                v = hashlib.md5(tpath.read_bytes()).hexdigest()[:8]
                fig = (f'<a class="item-fig" href="/story/{c["id"]}" tabindex="-1" '
                       f'aria-hidden="true"><img class="item-thumb" '
                       f'src="/assets/story-{c["id"]}-thumb.png?v={v}" '
                       f'width="1200" height="480" loading="lazy" alt=""></a>')
            demo = (' · <span class="badge">DEMO TRIGGER</span>'
                    if _cards.is_demo_trigger(c) else "")
            sec2 += f"""<div class="item">{fig}<div class="item-body">
<span class="kicker">{_ESC(c["topic"])}{demo}</span>
<h3><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h3>
<div class="meta">{ago(c["generated_at"], now)}</div>
</div></div>"""

        for c in sel[4:9]:
            rail += f"""<div class="item"><div class="item-body">
<span class="kicker">{_ESC(c["topic"])} · {_ESC(c["stream"])}{' · <span class="badge">DEMO TRIGGER</span>' if _cards.is_demo_trigger(c) else ""}</span>
<h3><a href="/story/{c["id"]}">{_ESC(c["question"])}</a></h3>
<div class="meta">{ago(c["generated_at"], now)}</div>
</div></div>"""

    tiles = ""
    for i, t in enumerate(board.get("tiles", [])):
        pos = str(t.get("rank_label") or f'#{t["rank"]}')
        label = (f'{t["title"]}: Connecticut at {_ESC(str(t["value"]))} — '
                 f'{_ESC(pos)} of {t["n"]} peers')
        tiles += f"""<div class="tile">
<div class="tname">{_ESC(t["title"])}</div>
<div class="val">{_ESC(str(t["value"]))}</div>
{theme.viz(json.dumps(t["strip"], default=str), f"strip{i}", label=label)}
<span class="chip">{_ESC(pos)} of {_ESC(str(t["n"]))} peers · data {_ESC(str(t["date"]))}</span>
</div>"""

    # Trending only speaks when it has something to say: at least 3 votes
    # overall, a per-card score of its own. Until then, silence — a lone
    # badge on one card would advertise emptiness, not heat.
    _trend = board.get("trend") or []
    _votes = sum(t.get("votes", 0) for t in _trend)
    chip = '<span class="badge trend">trending</span> ' if _votes >= 3 else ""
    del chip  # trend badge stays available to story pages this cycle

    # The week's wire, mapped: which questions the news cycle itself pushed
    # at us, counted from the headline ledger — salience measured, not said.
    from . import questions as _q
    att = _q.attention(7)
    wire = ""
    if att.get("indicators"):
        _cat = _q.load_catalog()
        _titles = {it["id"]: it.get("title") or it["id"]
                   for sec in ("stackup", "local", "national")
                   for it in _cat.get(sec, [])}
        top = sorted(att["indicators"].items(),
                     key=lambda kv: (-kv[1]["hits"], kv[0]))[:3]
        parts = [f'{_ESC(_titles.get(iid, iid))} '
                 f'<span class="wire-n">\u00d7{n["hits"]}</span>'
                 for iid, n in top if n.get("hits")]
        if parts:
            wire = (f'<p class="wire">What Connecticut news is asking this week: '
                    + " \u00b7 ".join(parts)
                    + f' \u2014 from {_ESC(str(att["headlines"]))} headlines '
                    + 'ingested across the tracked newsrooms.</p>')

    # The wire block: yesterday-and-today's actual headlines from the
    # tracked newsrooms, links going out to them. The desk publishes only
    # what public data can answer — but it reads everything, and says so.
    from . import questions as _q2
    by_ind = {c.get("indicator"): c["id"] for c in cards if c.get("indicator")}
    wire_items = ""
    wire_rows: list[tuple] = []
    seen_titles: set[str] = set()
    for e in _q2.recent_wire(hours=30, limit=30):
        # Google News syndicates one story under five " - Outlet" titles;
        # exact-hash dedup catches none of them. Collapse on the first
        # clause with the publisher suffix stripped.
        key = re.split(r"\s+-\s+", e["title"])[0]
        key = re.sub(r"[^a-z0-9]+", " ", key.lower()).strip()[:60]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        if len(seen_titles) > 10:
            break
        age = ("new to the desk" if e.get("undated") else
               "just now" if e["age_h"] < 1 else
               f"{int(e['age_h'])}h ago" if e["age_h"] < 48 else
               f"{int(e['age_h'] // 24)}d ago")
        ans = next((f' <a class="wireans" href="/story/{by_ind[i]}">'
                    f'related data</a>' for i in e.get("hits", [])
                    if i in by_ind), "")
        wire_items += (
            f'<li><a href="{_ESC(e["url"])}" rel="noopener">'
            f'{_ESC(e["title"])}</a>'
            f'<span class="wiresrc"> &nbsp;{_ESC(e["src"])} · {age}'
            f'</span>{ans}</li>')
        wire_rows.append((bool(ans), e.get("stream") == "ct", age, e["title"],
                          f'<li><a href="{_ESC(e["url"])}" rel="noopener">'
                          f'{_ESC(e["title"])}</a>'
                          f'<span class="wiresrc"> &nbsp;{_ESC(e["src"])} · {age}'
                          f'</span>{ans}</li>'))
    any_ans = any(r[0] for r in wire_rows)
    # The wire block earns its place by connecting news to our numbers.
    # An unmapped block is someone else's news ticker; suppressed whole.
    wire_items = ""
    if any_ans:
        rows = sorted(wire_rows, key=lambda r: (not r[0],))
        wire_items = "".join(r[4] for r in rows[:10])
    wire_section = (f"""
<section class="wireblock"><div class="wrap">
<div class="sechead"><h2>On the wire</h2>
</div>
<ul class="wirelist">{wire_items}</ul>
</div></section>""" if wire_items else "")

    from . import towns as _towns
    tb = _towns.briefs()
    yt = ""
    if tb:
        yt = (f'<p class="yourtown" id="yourtown" aria-live="polite"></p>'
              '<script>window.__TB__='
              f'{json.dumps(tb, separators=(",", ":"))};</script>'
              + _YOUR_TOWN_JS)
    latest = f"""<section class="latest" id="signals"><div class="wrap">
<h1 class="vh">Today\u2019s Connecticut data board</h1>
{yt}
{wire}
<div class="latest-grid">
{lead}
<div class="sec2"><h2 class="sec2-head">More from Connecticut data</h2>{sec2}</div>
<aside class="rail"><h2 class="railhead">Latest questions</h2>{rail}<p class="allq"><a href="/archive">All published questions \u2192</a></p></aside>
</div></div></section>"""

    body = f"""{latest}
{wire_section}
<section><div class="wrap">
<div class="sechead"><h2>The Connecticut board</h2>
<p class="sechelp">Where we stand among our peers — refreshed with every data
vintage.</p></div>
<div class="tiles">{tiles}</div>
<p class="legend">Peer sets are the 50 states and Washington DC (plus Puerto
Rico where the source covers it); the count in each answer is that indicator's
own source. Charts plot every peer; rank 1 is the highest value, and chips say
“highest”, “lowest” or a plain-language superlative — never a bare number.
Each tile prints the vintage of its own dataset; older vintages are the honest
limit of annual surveys, not a lag in the pipeline.</p>
</div></section>

<div class="wrap"><img class="tailpiece" src="/assets/skyline-light.png"
width="2340" height="875" loading="lazy" alt="Hartford skyline: the Soldiers
and Sailors arch, the stone-arch bridge, the State Capitol with its gilded
dome, City Place and the downtown towers"></div>"""

    return theme.page(
        title="CT Signal — Connecticut's automated data desk",
        desc="Connecticut's automated newsroom: the news cycle picks the "
             "question, public data answers it. Charts, rankings, and the "
             "query behind every number.",
        path="/", body=body,
        og_title="CT Signal — Connecticut's automated data desk",
        json_ld=theme.site_json_ld())


def publish(cards: list[dict], board: dict | None = None) -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    feed = {
        "generated_at": cards[0]["generated_at"] if cards else None,
        "cards": cards,
    }
    util.write_json(config.OUTPUT_DIR / "cards.json", feed)
    if board is not None:
        util.write_json(config.OUTPUT_DIR / "board.json", board)
    util.atomic_write_text(config.OUTPUT_DIR / "index.html",
                           home_html(cards, board or {}))
    from . import newsroom

    newsroom.write_all(cards)
