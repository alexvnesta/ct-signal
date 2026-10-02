# Roadmap — distribution & monetization plan

Adopted 2026-10-02 after the review board signed off (see REVIEW_BOARD.md).
Rule inherited from the board: **nothing ships that breaks the 100/100/100/100
bar** — every phase below ends with the same verification loop we already
have (Lighthouse mobile on home + a story, a11y spot-check, live byte
verification after push).

## Phase A — in-repo only, no accounts needed — **SHIPPED 2026-10-02**

| # | Item | What it is | Done when |
|---|------|-----------|-----------|
| A1 ✅ | Design craft pass | Self-host Newsreader/Source Serif 4 for story headlines (`font-display: swap` + `size-adjust`, CLS must stay 0); FT/Datawrapper-style chart upgrades: direct labels on trend endpoints, one annotation on the highlighted peer, cleaner axis units. Branch + before/after screenshots, pick together. | Chosen upgrades live, all Lighthouse categories still 100 |
| A2 ✅ | Sponsor slot | One honest, designed-in slot under the board: default state = "Independent · automated · reader-supported", swaps to "Board brought to you by …". No ad networks, no layout shift. | Slot ships in "vacant" state |
| A3 ✅ | Embed widget | `/story/<id>/embed` — chromeless answer + chart + attribution link; "Embed" button on stories reveals a copy-paste iframe snippet. Every embed = distribution + backlink. | Embed renders, snippet copies, attribution required |
| A4 ✅ | Topic hub pages | `/topic/housing`, `/topic/jobs` etc., listing all stories per topic. Interlinking = the SEO long game; titles target "connecticut X vs national" queries. | Hubs live, in nav, in sitemap |
| A5 ✅ | Weekly digest generator | `scripts/make_digest.py` renders one email HTML from feed.json + board.json (what changed on the board this week, top 3 stories, links). Output committed under `output/digest/`. Sending wired in Phase B. | Digest renders for the current week |

## Phase B — one-time accounts (human: ~20 min each; agent wires the rest)

| # | Account | Unlocks | Agent wires |
|---|---------|---------|-------------|
| B1 | Bluesky app token | Auto-post story cards (we already generate the 1200×630 covers + alt text) on publish | GH Action step in pulse: post on feed diff |
| B2 | Buttondown (free ≤100 subs) | Weekly digest delivery + subscribe UI link | Digest posted via API; subscribe page in footer |
| B3 | Google News Publisher Center | Feed already ready (RSS + masthead + automation disclosure) | Submission checklist + byline/schema fixes if asked |
| B4 | Existing backlog | `DC_API_KEY` + `GEMINI_API_KEY` GH secrets (LLM matching, signed DC fetches); Porkbun email forwarding for hello@ (matters once sponsors/newsletter replies are real) | Verify first LLM-matched cycle end-to-end |

## Phase C — outreach (human posts, agent drafts; sequenced after A+B1/B2)

1. **Meta-story launch**: "An autonomous newsroom that won't let an LLM write
   the numbers" — HN Show + Indie Hackers (agent drafts; human posts). Best
   single source of first backlinks.
2. **Nieman Lab pitch** (~250 words, agent drafts) — working systems with
   honest automation disclosure get covered.
3. **r/Connecticut + Nextdoor**: every digest issue carries a "ready to post"
   snippet per notable stat (generated in A5).
4. **Syndication email**: template to CT newsletters/outlets offering free
   republication + the A3 embed. The ask is a link back, nothing else.
5. **Sponsor one-pager**: after 2–4 weeks of traffic baseline — credit
   unions, insurers, law firms buy local-data attention; slot A2 is the
   product. Agent drafts; human makes the calls.

## Phase D — the franchise (only after traction evidence)

- **NY / NJ / MA Signal**: the repo is already state-parameterized; audit
  catalog indicators for state-agnostic equivalents; each edition = config +
  catalog + cron. Sell to partner newsletters as white-label data blocks.
- **Paid feed tier**: `board.json`/`feed.json` are already public; the paid
  product is schema stability + SLA + CSV exports, not hosting.
- **Grants**: CT local-news funders (Democracy Fund ecosystem, IFNI associate)
  — evidence = digest, citations, traffic baseline.

## Explicit non-goals

No ad networks (kills the perf scores at our scale), no comment systems, no
SPA frameworks, no cookie banners (nothing set), no design-template swaps —
templates inform, we build.

## Verification protocol (every ship, forever)

Lighthouse mobile (home + one story) → all 100s; contrast spot-check on new
UI; redirects/headers sweep; live byte-check after Vercel deploy. Machine
cycles inherit the audited generators, so the bar can't rot between reviews.

## Phase A ship notes (verification evidence)

- Newsreader 700 latin subset (24 KB) self-hosted + preloaded: computed
  h1 font verified in browser; story trace LCP 136 ms, **CLS 0.00** with
  the swap; Lighthouse mobile home 100/100/100/100.
- Trend charts: CT/US direct endpoint labels verified in live SVG; axis
  uses labelOverlap after two labelExpr signal failures on the real
  renderer (caught only because we checked the live console, not the
  local spec).
- `/story/<id>/embed`: renders standalone, canonical consolidates to the
  story, console clean (preload skipped on embed pages).
- `/topic/<x>` hubs: 5 live, in sitemap with per-topic lastmod,
  trailing-slash 308 rule added; Lighthouse 100/100/100/100 after an
  h1→h3 heading-skip fix.
- Digest issue 2026-W40 frozen at output/digest/2026-W40.html.
- Sponsor strip verified on mobile 390 px: no overflow, contrast from
  the audited palette.


## HARDENING BACKLOG (from 2026-10-02 three-auditor review: SRE/health/security)

Shipped in the hardening pass: rebase-retry push, publish-only-on-success,
asked-log-after-publish, atomic writes, strict feed.json, failures.log in-repo,
token confinement, link scheme allowlist, island `<!--` hardening, CI no
longer masks failures (red = red), first smoke-test suite (tests/).

Deliberately deferred (each is a tidy refactor, none is load-bearing):
- Shared `trigger_fragment()` (publish/newsroom render the same trigger line).
- `scripts/_brand.py` (palette + fonts + SITE currently triplicated across
  the three scripts/ files).
- Split `run.answer_proposals` into `_answer_stackup/_answer_local`,
  data-driven local answerers (grand_list hardcoded four times).
- Socrata `$limit: 400` → paginate or detect truncation.
- Rename pipeline state `output/feed.json` → `output/cards.json`
  (name collides with the JSON Feed spec file at root).
- Generate vercel redirect fragments when a card id is superseded.
- Feed display names belong in config next to each URL, not a host map.
