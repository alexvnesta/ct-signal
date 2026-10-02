# CT Signal

**Live → [ct-signal.vercel.app](https://ct-signal.vercel.app)** · Deck → [/slides](https://ct-signal.vercel.app/slides) · Hack for Humanity · Challenge 4: CTData.org, Made Conversational

News happens → CT data answers. A continual loop that makes CTData.org
conversational **in reverse**: it asks Connecticut the questions its news
cycle is already asking, and answers them only with fetched numbers.

- **The AI decides relevance, nothing else.** News arrives as language;
  Data Commons speaks DCIDs — summarizing intent and picking the query is
  the model's whole job. It never writes a number.
- **Every figure is fetched.** Each card's provenance drawer names the
  dataset, variable, data date, and the literal query that produced it.
- **Closed-set by design.** The model picks only from a curated catalog
  (`catalog/indicators.yaml`); an unmatched story produces no card, and
  cache fills are labeled `cache`. Degrades, never wrong.

- `docs/proposal.md` — problem, solution, rubric mapping, pitch
- `docs/use_cases.md` — six cards, each traced to a live test
- `docs/judge-qa.md` — adversarial Q&A drill, by judge, with tiebreaker doctrine
- `docs/data_sources.md` — validation log (incl. failures: BLS v1 dead,
  data.ct.gov search is network-wide, DC needs a free key)
- `docs/architecture.md` / `docs/plan-6h.md`

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # paste free key from apikeys.datacommons.org
```

## Run

```bash
python validate.py                    # validate catalog DCIDs (needs key)
python run.py --demo --once           # demo mode: fixtures fill Data Commons gaps
python run.py --interval-min 15       # continual loop for event day
python -m http.server -d output      # local preview: http://localhost:8000
```

`--demo` merges fixture headlines and serves Data Commons cards from
`fixtures/` (labeled `cache` in the UI) so the demo survives a missing key
or bad WiFi. The CT grand-list card runs live with no key.

**Status (2026-09-30):** live end-to-end. All 6 stack-up DCIDs validated
(52 states), feeds verified, keys in `.env` (git-ignored). Event-day
to-dos in `docs/plan-6h.md`.

## Layout

- `catalog/indicators.yaml` — the closed set the LLM/heuristics may pick from
- `src/ctsignal/` — feeds → questions → sources → cards → publish
- `output/feed.json`, `output/index.html` — deterministic published feed

## Vercel

Git-integrated static deploy (Vercel auto-builds on push to `master`;
`vercel.json` + `.vercelignore` keep the upload to just the built UI).

```bash
./deploy.sh --once    # one cycle, commit root index.html+feed.json, push → auto-deploy
./deploy.sh           # event-day loop: cycle + push every 15 min
./deploy.sh --pin     # judge-proof: snapshot feed to fixtures/, push
```

Live at https://ct-signal.vercel.app. `.env` (all API keys) is git- and
Vercel-ignored. Turn OFF Deployment Protection (project settings) so
judges can view without a Vercel login.
