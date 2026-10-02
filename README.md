# CT Signal

**Live → [ctsignal.org](https://ctsignal.org)** (DNS propagating; mirror:
[ct-signal.vercel.app](https://ct-signal.vercel.app)) · Deck → [/slides](https://ct-signal.vercel.app/slides) · Hack for Humanity · Challenge 4: CTData.org, Made Conversational

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
- `docs/newsroom.md` — the plan from demo → legit news site (decisions, ladder, ops)
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
- `story/<id>/` — permalink story pages; `archive/<YYYY-MM>/` — every card
  ever, as JSON; `feed.xml` + `sitemap.xml`; `/about` `/methodology`
  `/masthead` `/corrections` — the news site layer (`src/ctsignal/newsroom.py`)

## Deploy

Git-integrated static deploy to Vercel; **GitHub Actions (`pulse` workflow)
runs one cycle every 15 minutes** and pushes — the commit is the deploy and
the audit trail. Needs repo secrets `DC_API_KEY` + `GEMINI_API_KEY`; without
them pulses degrade to heuristics + keyless Socrata, never break the feed.

```bash
./deploy.sh --deploy   # publish current output/ (what CI does)
./deploy.sh --once     # manual cycle + push (laptop, optional now)
./deploy.sh --pin      # snapshot feed to fixtures/, push
```

Live at https://ctsignal.org (vercel.app until DNS finishes). `.env` (all API
keys) is git- and Vercel-ignored; `SITE_URL`/`CONTACT_EMAIL` override the
canonical URL/contact defaults. Deployment Protection is OFF (project
settings) so anyone can view.
