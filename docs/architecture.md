# Architecture

Single Python process, cron-shaped (`run.py --interval`), no framework.
Stages are plain functions so every stage is inspectable and re-runnable —
that inspectability is a judging feature, not just good hygiene.

```
feeds.py        questions.py        sources/            cards.py       publish.py
RSS x5    ──▶   headline→catalog ──▶ Data Commons  ──▶   answer card ──▶ output/feed.json
civic calendar  (closed-set JSON,   CT Socrata          + provenance     index.html
                dry-run validated)  FRED fallback       + Altair spec    (vega-embed)
                          │
                     asked_log.json (dedupe, sha1 of question+indicator)
```

## Module map

| Module | Responsibility |
|---|---|
| `config.py` | env (DC key), feed list, entities, topic allowlist, paths |
| `feeds.py` | fetch+parse RSS, normalize, dedupe by title hash |
| `questions.py` | propose questions: closed-set keyword heuristics; `propose_with_llm` stub (Gemini/GPT at event); calendar seeds |
| `sources/datacommons.py` | v2 observation for all 52 peers (50 states, DC, Puerto Rico); rank computation |
| `sources/socrata.py` | SoQL row fetch on data.ct.gov (portal-scoped datasets only) |
| `charts.py` | Altair → Vega-Lite spec (rank strip, trend); spec is data, shipped inline |
| `cards.py` | assemble card with provenance chain; answer templates from catalog |
| `publish.py` | feed.json + static index.html |
| `run.py` | cycle loop, asked-log, fixtures fallback, `--once`, `--demo` |

## Invariants (the pitch rests on these)

1. **No LLM number.** Card values come from `sources/` responses only.
2. **Closed-set generation.** Proposals reference a catalog `indicator_id`;
   unknown ids are rejected before any API call.
3. **Dry-run or discard.** A proposal that doesn't fetch a value produces
   no card — the feed can be sparse, never wrong.
4. **Provenance is a first-class field.** Every card serializes its chain:
   headline URL/id, dataset, query, fetched timestamp, data vintage.
5. **Deterministic output.** Chart specs: inline `data.values`
   (no consolidated `datasets` map), pinned schema major version, no
   random ids. Same input → byte-identical feed.json.

## Altair usage (spec-factory mode)

- Altair constructs specs only; the frontend embeds the spec with
  vega-embed. `alt.data_transformers.disable_max_rows()` and
  `consolidate_datasets = False` at import (we own the data budget:
  ≤ 51 rows per card).
- `chart.to_dict(validate=False)` + pinned `$schema` major.
- Conditional highlight color uses raw-dict encoding passthrough
  (single-dict `condition`, `legend: None` preserved) — typed constructors
  would elide or list-wrap it.

## Failure posture

- Feeds: per-feed try/except; 5 sources, one dying is a warning line.
- Data Commons 401/no key: national stream falls back to `fixtures/*.json`
  (cards labeled `"cache": true` — honest in the UI).
- FRED: one retry + 24h on-disk cache (it blocks scripted callers sometimes).
- Socrata non-tabular 404s: caught by dry-run; dataset stays out of catalog.
