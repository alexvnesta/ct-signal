# 6-hour build plan (10:30–4:00 + 5:00 judging)

## 10:30–11:15 — Key + catalog validation — ✅ DONE 2026-09-30 (pre-event)
- [x] Free Data Commons key → `.env` (`validate.py`: all 6 DCIDs ok, 52 states)
- [x] Gemini key ok (`gemini-3.8-flash`); Socrata token dead on Tyler portal
      → keyless; NL API detect-intent moved on — discovery done via
      `fetch_available_statistical_variables`
- [x] 3 CT tabular datasets row-verified (webp-fgt3 fully exercised:
      169-town live comparison)
- [ ] Event-day leftovers: wire Gemini into `propose_with_llm`; find a
      tabular SOTUS turnout table for the election seed card

## 10:45–1:30 — Parallel tracks
- **Track 1 (data):** sources/datacommons.py + sources/socrata.py +
  charts.py (rank strip, trend). Verify: 1 card per stream, hand-triggered.
- **Track 2 (pipeline):** feeds.py + questions.py heuristics + asked-log +
  dry-run validation. Verify: proposals from live CT Mirror feed.
- **Track 3 (surface):** cards.py templates + publish.py (feed.json,
  index.html w/ vega-embed, provenance drawer) + README screenshots.

## 1:30–2:30 — Integration
- run.py single cycle end-to-end; feed grows with every run; dedupe proves itself.
- Election calendar seed live (Nov 3, 2026) — deterministic card regardless
  of news quality.

## 2:30–3:15 — Research evidence pass
- Hardest-question pass: 10 hand-picked headlines; record accept/reject
  rates (the reject rate is a *feature* to show).
- Cross-check 2 card values against the source site manually (one slide's
  worth of screenshots).

## 3:15–4:00 — Demo hardening
- Run the loop live all afternoon so `feed.json` timestamps show ~6 hours
  of continuous generation.
- Cache pin: `run.py --once` snapshot copied to `fixtures/last_feed.json` —
  if WiFi dies, judge sees the feed, labeled `cache`.
- Pitch rehearsal x2 with timer; demo card = freshest national card.

## Judging posture
- Show, don't claim: provenance drawer open on one card, asked-log file,
  validation log (this repo's data_sources.md) offered as evidence.
- Tiebreakers favor us: Impact (newsletter/homepipe/SMS path, CTData
  mission language), AI Effectiveness (closed-set + dry-run = intentionality
  with receipts).
