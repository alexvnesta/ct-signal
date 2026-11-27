# CT Signal — Agent & Maintainer Guide

CT Signal (`https://ctsignal.org`) is a static, automated civic data newsroom for Connecticut: news headlines raise questions from a closed catalog (`catalog/indicators.yaml`), public APIs (Census, Data Commons, CT Open Data Portal, FRED, ACIS) fetch the numbers, and static HTML + Vega-Lite charts + PNG/SVG/CSV receipts are committed and auto-deployed via Vercel.

**Canonical tagline & editorial voice:** `"Know where you live."` Lead with Connecticut and the finding, never with the pipeline. Never invent, estimate, or round a number outside code. See `docs/STYLE.md`.

---

## Quick Commands

Use the repo's `.venv` Python (`3.14` locally, `3.13` in GitHub Actions):

```bash
# Run the full test suite (~0.6s, offline, stdlib unittest)
.venv/bin/python -m unittest discover -s tests

# Rebuild every static HTML/SVG/PNG/CSV page from committed output/cards.json + data/towns.json (offline)
.venv/bin/python -c '
import json, pathlib, sys
sys.path.insert(0, "src")
from ctsignal import config, publish, towns
cards = json.loads((config.OUTPUT_DIR / "cards.json").read_text())["cards"]
board = json.loads((config.OUTPUT_DIR / "board.json").read_text())
publish.publish(cards, board)
towns.publish()
(config.ROOT / "index.html").write_text((config.OUTPUT_DIR / "index.html").read_text())
(config.ROOT / "board.json").write_text((config.OUTPUT_DIR / "board.json").read_text())
'

# Regenerate story OG covers and front-page card thumbnails (idempotent via assets/_art_manifest.json)
.venv/bin/python scripts/make_story_covers.py

# Run one live pipeline cycle (fetches feeds + APIs)
.venv/bin/python run.py --once

# Local static preview for visual QA
.venv/bin/python -m http.server 8765
```

---

## Single Sources of Truth (Never Edit Generated Artifacts Directly)

| Source file | What it generates / owns |
|---|---|
| `src/ctsignal/theme.py` | `assets/site.css` (auto-hashed via `CSS_HASH`), masthead/nav (`header()`), footer, JSON-LD, `viz()` chart island + `VEGA_LOAD`. **Never hand-edit `assets/site.css`.** |
| `src/ctsignal/publish.py` | `output/index.html` → `index.html`, `output/board.json` → `board.json` (front page + wire + Connecticut Board). |
| `src/ctsignal/newsroom.py` | `story/<id>/index.html`, `story/<id>/embed/index.html`, `indicator/<id>/{index.html,observations.csv}`, `indicators/index.html`, `topic/<desk>/index.html`, `town/<slug>/{index.html,feed.xml}`, `archive/index.html`, `feed.xml`, `feed.json`, `sitemap.xml`. |
| `src/ctsignal/towns.py` | `towns.html`, `towns.csv`, ACS table fragment `table_for()` embedded into town pages. |
| `src/ctsignal/pages.py` | `about.html`, `masthead.html`, `corrections.html`, `privacy.html`, `sources.html`, `404.html`. |
| `src/ctsignal/charts.py` | Altair / Vega-Lite v6 chart specs (`rank_strip`, `shape_strip`, `state_map`, `trend`). |
| `src/ctsignal/share.py` | Dark 2× share PNGs (`assets/share-<id>.png`) and paper-palette SSR SVGs (`assets/chart-<id>.svg`) via `vl-convert`. |
| `scripts/make_story_covers.py` | 1200×630 social covers (`assets/story-<id>.png`) and 480×192 front-page card thumbnails (`assets/story-<id>-thumb.png`). |
| `catalog/indicators.yaml` + `catalog/context.yaml` | Closed indicator catalog, answer templates, evergreen "Why it matters" & desk explainers. |

---

## Non-Negotiable UX, Visual & Data Invariants

These rules are enforced by `tests/test_ux_invariants.py`, `tests/test_smoke.py`, `tests/test_pure_parts.py`, and `tests/test_prose_slop.py`:

1. **Finding-first headlines everywhere:** Front page (`publish.py`), story pages, and archive all lead with `newsroom._finding(card)`, keeping the standing question as secondary context (`.lead-q` / `.storyq` / `.item-q`). Story and lead ledes use `newsroom._story_lede(card)` so they never echo the H1 sentence verbatim.
2. **Board KPI numbers stay neutral ink (`--ink`), never green (`--ok`):** Unemployment, poverty, and violent crime sit beside income and rent — coloring negative metrics green is misleading. Burnt orange (`--acc2` / `--acc`) highlights Connecticut in charts and active chrome.
3. **Top-N horizontal bar charts sort `#1` at the top:** `charts.rank_strip()` sorts `rows` ascending by `rank` so rank 1 sits at the top of the y-axis, keeps `data.values` at the top level of the Vega-Lite spec (even for layered bar+label charts so `make_story_covers.py`, `_place_line`, and `_chart_csv` keep working), adds right-side domain headroom, and uses unit-only x-axis titles (never triplicating the chart title).
4. **Instant zero-JS chart first paint:** `share.export_svg()` writes paper-palette SVGs (`assets/chart-<id>.svg`) that `theme.viz(..., preview_src=...)` renders immediately inside `.viz` before Vega-Embed hydrates interactivity after `window.load`. Keep `--viz-h` height reservation intact so CLS stays `0`.
5. **Thumbnail numbers always keep direction & units:** `scripts/make_story_covers.py:_thumb_value()` must format directional temperature anomalies (`+4.6°F`, `-2.4°F`), rates (`147/100k`), percents, and dollars cleanly — never falling back to a bare rounded integer like `5`. Bump the manifest salt (`|thumb-vN`) whenever thumbnail rendering changes.
6. **Wire hygiene:** `questions.wire_worthy()` filters sports, individual crime blotter, and unrelated non-CT national fluff out of `"On the wire"`. Keep `.wirelist` as a 2-column CSS Grid (not `column-count: 2`) with an even display count when ≥4 items exist.
7. **Consistent inner-page chrome & active nav:** Only `/` uses the tall illustrated skyline masthead (`compact=False`). Every inner page (`/story/*`, `/towns`, `/town/*`, `/indicators`, `/indicator/*`, `/topic/*`, `/archive`, `/about`, `/masthead`, `/corrections`, `/privacy`, `/sources`, `/404`) uses `compact=True` and automatically marks its active primary nav item with `aria-current="page"`.
8. **WCAG 2.2 AA & touch targets:** Every text color pair on `#faf8f3` meets ≥4.5:1 contrast; interactive controls (`.vote button`, `.chart-actions`, nav links, town controls) maintain ≥44px tap height on mobile.
9. **169 towns invariant:** Connecticut has exactly 169 municipalities. Never let aggregate rows (`Total`, `Connecticut`, `Statewide`) into town pages or `/towns.csv`.
10. **Archive immutability & secrets:** Never overwrite archived vintage JSON files (`archive/<YYYY-MM>/<id>-<date>.json`), never commit `.env` files, and never let credentials into `data/failures.log`.

---

## CI & Deployment

- `.github/workflows/pulse.yml` runs every 15 minutes (`run.py --once` → covers → `deploy.sh --deploy` → Bluesky).
- `deploy.sh --deploy` stages **only** generated paths listed in `GEN=(...)`, commits under `ct-signal-bot`, rebases onto `origin/master`, and pushes (Vercel auto-deploys `master`).
- When adding a new generated top-level file or directory, add it to `GEN=(...)` in `deploy.sh` and cover it in `tests/`.
- Always work in an isolated git worktree/branch for code or UI changes, run the full unittest suite, visually check desktop (`1440×900`) and mobile (`390×844`) renders on a local server, and keep generated site rebuilds in sync before pushing.
