from __future__ import annotations

import json

from . import config

_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>CT Signal</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<style>
body{font-family:system-ui;margin:2rem auto;max-width:880px;color:#eef2f5;
  background:#101418;padding:0 1rem}
h1{margin-bottom:.2rem}
a{color:#7fb4ff}
.meta{color:#9fb0bf;font-size:.85rem}
#board{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.8rem;
  margin:1.2rem 0 2rem}
.tile{background:#1a2129;border:1px solid #2b3a48;border-radius:12px;padding:1rem 1.1rem;color:#eef2f5}
.tname{color:#9fb0bf;font-size:.85rem}
.val{font-size:1.9rem;font-weight:700;color:#8fd6a9;margin:.15rem 0}
.chip{background:#243040;border-radius:99px;padding:.1rem .6rem;font-size:.75rem;color:#cfdcea}
article{background:#151c24;border:1px solid #2b3a48;border-radius:8px;padding:1rem;margin:1rem 0}
.answer{font-size:1.15rem;font-weight:600;margin:.4rem 0}
details{margin-top:.5rem;font-size:.85rem;color:#9fb0bf}
code{background:#243040;color:#cfdcea;padding:0 .25rem;border-radius:4px}
.badge{background:#243040;color:#cfdcea;border-radius:4px;padding:0 .35rem;font-size:.75rem}
</style></head><body>
<h1>CT Signal</h1>
<p class="meta">Questions generated from live news + civic calendar,
answered only with fetched numbers.</p>
<div id="board"></div><div id="feed"></div>
<script>
Promise.all([
  fetch("feed.json").then(r=>r.json()),
  fetch("board.json").then(r=>r.json()).catch(()=>({tiles:[]}))
]).then(([feed,board])=>{
  const ago=iso=>{const s=(Date.now()-new Date(iso))/1000;
    if(s<90)return"just now";if(s<5400)return Math.round(s/60)+" min ago";
    if(s<86400)return Math.round(s/3600)+" h ago";return iso.slice(0,10);};
  const broot=document.getElementById("board");
  for(const t of board.tiles){
    const d=document.createElement("div");d.className="tile";
    d.innerHTML=`<div class="tname">${t.title}</div>
      <div class="val">${t.value}</div>
      <span class="chip">#${t.rank} of ${t.n} states · data ${t.date}</span>
      <div class="strip-${t.id}"></div>`;
    broot.appendChild(d);
    vegaEmbed(`.strip-${t.id}`,t.strip,{actions:false});
  }
  const root=document.getElementById("feed");
  for(const c of feed.cards){
    const a=document.createElement("article");
    a.innerHTML=`<div class="meta"><span class="badge">${c.stream} · ${c.topic}</span>
      ${c.cache?'<span class="badge">cache</span>':''}
      ${c.headline.url?`<a href="${c.headline.url}">${c.headline.title}</a>`:c.headline.title}
      · ${ago(c.generated_at)}</div>
      <div><em>${c.question}</em></div>
      <div class="answer">${c.answer_text}</div>
      <div class="chart-${c.id}"></div>
      <div class="chart2-${c.id}"></div>
      <details><summary>provenance</summary>
      dataset: <code>${c.citations.join(", ")}</code><br>
      query: <code>${c.query}</code></details>`;
    root.prepend(a);
    vegaEmbed(`.chart-${c.id}`, c.chart, {actions:false});
    if(c.chart2) vegaEmbed(`.chart2-${c.id}`, c.chart2, {actions:false});
  }
});
</script></body></html>
"""


def publish(cards: list[dict], board: dict | None = None) -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    feed = {
        "generated_at": cards[0]["generated_at"] if cards else None,
        "cards": cards,
    }
    (config.OUTPUT_DIR / "feed.json").write_text(
        json.dumps(feed, indent=2, sort_keys=True, default=str)
    )
    if board is not None:
        (config.OUTPUT_DIR / "board.json").write_text(
            json.dumps(board, indent=2, sort_keys=True, default=str)
        )
    (config.OUTPUT_DIR / "index.html").write_text(_TEMPLATE)
