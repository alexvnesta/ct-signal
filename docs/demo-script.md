# Demo script (3-min slot + Q&A)

Deck: `slides.html` (also at ct-signal.vercel.app/slides.html). ←/→ to advance.

## Set-up before your slot
1. Terminal A: `./deploy.sh --once` ran within the last hour (feed is fresh + pushed).
2. Browser tab 1: https://ct-signal.vercel.app (scroll so two cards are visible).
3. Browser tab 2: slides.html (fullscreen). Terminal A visible in the dock.
4. Fallback if news pool is dry for national stories: run with `--demo`
   (fixture headlines like "Renters battered by record shelter costs" reliably
   trigger Gemini matches — verified 3/3).

## The 3 minutes
- :00 Slide 2 (problem), 20s. Point at CTData's own helpline.
- :20 Slide 3 (loop), 40s. Key line: "The LLM never writes a number."
- :60 **Live feed.** Walk three cards, contrasting the streams:
  1. Rent #17/52 — national headline → stack-up. "This answered itself minutes
     after the story ran."
  2. Unemployment trend #3/52 — the trend chart, data from July 2026.
  3. Bridgeport +59.9% — local card, all 169 towns, revaluation caveat shown
     because honest cards age better than flattering ones.
- 2:15 Open a **provenance drawer**: dataset + the literal query. "Ask me anything
  about these numbers; they're fetched."
- 2:30 **Fresh cycle live**: `./deploy.sh --once`, refresh: "the loop is the
  product — every 15 minutes, forever." If Gemini 503s (free tier is flaky),
  shrug: "closed-set + heuristics — degraded, never wrong" (true, it still runs).
- 2:50 Slide 5: newsletter fit + the failure log ("this slide is our research
  slide") + one-liner close.

## Q&A one-liners
- Hallucinations? Numbers come from executed API calls; LLM output is filtered
  through a closed catalog and dry-run execution.
- Why closed set? 6 indicators × 52 states beat an agent that can silently
  wrong-answer; adding an indicator is 8 lines of YAML.
- Why not a chatbot? Their audience won't prompt; the news cycle tells us what
  people are already asking. Chat is a UI layer we could add on this backend.
- Socrata/DU limits? Anonymous SODA + hourly-scale volume; token wiring exists.
- Election data? CT's portal has none (verified — 'Election Results and Voter
  Turnout' is literally a hyperlink); SOTUS CSV ingest is first roadmap item.
- Maintenance? One cron loop + one YAML catalog; every failure mode is a
  missing card, labeled cache when it's from cache.

## Cards to know cold (today's real values)
rent $1,488 #17/52 · unemployment 5.8% #3/52 (Jul 2026) · Bridgeport +59.9%
(169 towns, GL 2025) · crime 147/100k = 3rd LOWEST in the country (#50 of 52
by rate — say "3rd safest", never "#50") · poverty 9.6% #43/52 (2024;
#43 of 52 highest = 10th-lowest poverty in the country — frame accordingly).
