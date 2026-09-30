# Roadmap to 100% — ordered, with acceptance tests

Everything is one of seven tasks. T1–T5 are pre-event-safe (no event-day
dependency); T6–T7 are event-day. Ordering = demo payoff per hour.

## T1 — LLM question generator (Gemini) · ~45 min · pre-event
Replace heuristics with the model heuristics can't be: semantic matching.
- `questions.propose_with_llm`: one batched call per cycle — send the
  headline list + a compact catalog (id, title, topic) + system rule
  "reply ONLY a JSON array of {indicator_id, headline_id}; propose only if
  the story is genuinely about that indicator; fewer is better".
- Model `gemini-3.8-flash`, `responseMimeType: application/json`, 20s timeout.
- Every proposal passes `validate_proposal` (closed-set id check) — then
  the existing dry-run discards. Fallback chain: LLM → heuristics → discard.
- **Accept:** against today's ~58 live headlines, hand-audit: ≥8/10 proposals
  defensible, 0 unknown ids survive, LLM timeout still yields the heuristic cards.

## T2 — Unemployment trend card (uses existing `charts.trend`) · ~30 min · pre-event
- Same DC call pattern, but `date` = 5-year range (client accepts range);
  entities: CT + `country/USA`. Rows: `{date, series, value}`.
- Card gains `chart_kind: trend` (index.html already renders whatever spec
  ships); answer text keeps the rank sentence, chart becomes CT-vs-US over time.
- **Accept:** ≥12 monthly points, both series, spec asserts like rank_strip
  (inline values, pinned schema).

## T3 — Election seed card · ~45 min · pre-event attempt, event-day finish
- Hunt SOTUS tabulars NOW (15 min): catalog queries "2024 general",
  "registration list", "absentee 2026" filtered `metadata.domain`, then
  SODA `$limit=1`. Best-known candidates from earlier logs are non-tabular.
- If found: answerer = ballots cast ÷ registered, latest governor's year vs
  presidential year → CT trend card on Nov 3 seed.
- If not found: seed card becomes "CT towns' taxable base going into the
  election" (reuses the proven grand-list answerer) — still timely, honest,
  zero new code.
- **Accept:** Nov-3 seed produces a card (either path).

## T4 — Generic local answerer (equalized GL + municipal fiscal) · ~30 min · pre-event, optional
- Generalize `grand_list_growth(dataset_cfg)`: config supplies socrata_id,
  value column, town column, year column → both remaining catalog entries
  get answerers without new functions.
- **Accept:** a "school aid / municipal finance" keyword headline yields a
  third local card type.

## T5 — Topic balance + freshness ranking · ~20 min · pre-event
- In `run_cycle`: max 1 new card per topic per cycle; when several
  candidates share a topic, keep the freshest headline `published`.
- Relative age ("12 min ago") in index.html card meta.
- **Accept:** feed after a housing-heavy news hour shows one housing card,
  tagged, chosen for recency.

## T6 — Soak + demo hardening · event-day, runs itself mostly
- 10:45: `python run.py --interval-min 15 &`; hourly glance at card count.
- 15:30: copy feed to `fixtures/last_feed.json`; kill WiFi; verify
  `--demo --once` still renders from cache, cards labeled `cache`.
- Screenshot set: live feed, provenance drawer (open), validation_report,
  data_sources failure table, asked-log.
- **Accept:** at 16:00 the feed's newest timestamp is < 15 min old.

## T7 — Presentation kit · ~45 min · event-day
- 3-min script (in proposal.md) rehearsed twice with the actual morning's
  freshest card; one slide of evidence (validation log incl. failures —
  this is our "Research and evidence" criterion, say that out loud).
- Q&A one-liners: hallucination (values are fetched, LLM never writes a
  number) / junk questions (closed set + dry-run discard, show discard log) /
  durability (cron + yaml catalog, no framework).
- **Accept:** pitch under 3:00 with the live feed visible the whole time.

## Definition of 100%
Feed shows, every cycle: ≥2 topic-balanced cards from live national + CT
news (LLM-proposed, dry-run validated), an unemployment trend card, an
election-cycle card, all specs rendering, cache fallback rehearsed, pitch
timed. Nice-to-have beyond 100%: T4's third card type, newsletter digest
export (one template — could mention on the roadmap slide).

## Status (2026-09-30, same day)
- **T1 ✅** Gemini live: closed-set JSON proposals via fallback chain
  (`gemini-3.1-flash-lite` → … → `gemini-3.8-flash`; 3.8-flash intermittently
  503s "high demand" on free tier — chain + heuristics make it moot).
  `--no-llm` flag for deterministic demo runs.
- **T2 ✅** Unemployment trend card live: `ObservationDate.ALL` full monthly
  history (CT from 1976), 48-month slice, CT-vs-US, card now shows trend +
  rank sentence ("#3 of 52").
- **T3 ✅ (by fallback)** Portal has NO tabular CT election data —
  `2cta-kxuv` is an `href` asset (link to SOTUS website). Election seed card
  uses the grand-list answerer with its own honest question; seed question
  override dropped on fallback. SOTUS press-release CSV ingest = beyond 100%.
- **T4 ✅** `town_metric_growth(cfg)` generic answerer; equalized assessment
  card live (170 towns, Old Lyme +57.4%). Municipal fiscal (long format)
  still needs a long-format answerer = beyond 100%.
- **T5 ✅** Topic cap + recency tie-break verified ("balanced out" lines in
  run log); relative age ("12 min ago") in feed UI.
- Remaining for event day: T6 soak + cache drill, T7 pitch kit.
