from __future__ import annotations

import json

from . import config

_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>CT Signal</title>
<script src="https://cdn.jsdelivr.net/npm/vega@7"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@6"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@7"></script>
<style>
body{font-family:system-ui;margin:2rem auto;max-width:760px;color:#222}
article{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}
.meta{color:#777;font-size:0.85rem}
.answer{font-size:1.15rem;font-weight:600;margin:.4rem 0}
details{margin-top:.5rem;font-size:.85rem;color:#444}
code{background:#f4f4f4;padding:0 .25rem}
.badge{background:#eee;border-radius:4px;padding:0 .35rem;font-size:.75rem}
</style></head><body>
<h1>CT Signal</h1><p class="meta">Questions generated from live news + civic calendar,
answered only with fetched numbers.</p><div id="feed"></div>
<script>
fetch("feed.json").then(r=>r.json()).then(feed=>{
  const ago=iso=>{const s=(Date.now()-new Date(iso))/1000;
    if(s<90)return"just now";if(s<5400)return Math.round(s/60)+" min ago";
    if(s<86400)return Math.round(s/3600)+" h ago";return iso.slice(0,10);};
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
      <details><summary>provenance</summary>
      dataset: <code>${c.citations.join(", ")}</code><br>
      query: <code>${c.query}</code></details>`;
    root.prepend(a);
    vegaEmbed(`.chart-${c.id}`, c.chart, {actions:false});
  }
});
</script></body></html>
"""


def publish(cards: list[dict]) -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    feed = {
        "generated_at": cards[0]["generated_at"] if cards else None,
        "cards": cards,
    }
    (config.OUTPUT_DIR / "feed.json").write_text(
        json.dumps(feed, indent=2, sort_keys=True, default=str)
    )
    (config.OUTPUT_DIR / "index.html").write_text(_TEMPLATE)
