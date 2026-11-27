# CT Signal — Autonomous Agent Backlog & Growth Runbook

This backlog is structured so a weekly local maintenance agent (DeepSeek Harness
on `local-vllm/deepseek-v4.1-flash`, \$0 API spend) can steadily grow CT Signal's
Connecticut depth, search footprint, and reliability with **at most one clean,
tested PR per week** for ~2 minutes of human review.

---

## Weekly Maintainer Loop (DeepSeek Harness)

1. **Read** `AGENTS.md` first (all UX, chart, copy, and deploy invariants apply).
2. **Triage health:** inspect `data/failures.log` and `data/watchdog.json`. Fix
   any broken upstream schema, failing endpoint, or linkcheck warning *before*
   starting a feature item.
3. **Pick ONE unchecked item** from the highest priority section below.
4. **Work in an isolated git worktree** (`git worktree add -b feat/<slug> ...`).
   Never edit directly in a dirty primary checkout.
5. **Live-verify before committing:** probe any new API/Socrata endpoint live
   first, verify row counts and town canonicalization against `data/towns.json`,
   and verify `test_prose_slop.py` passes on all new templates.
6. **Rebuild & verify everything:**
   - Run full site rebuild (`publish.publish(...)` + `scripts/make_story_covers.py` + `scripts/make_digest.py`)
   - Run full test suite (`python -m unittest discover -s tests`)
   - Run `audit.internal_links()` and `audit.sitemap_gaps()` (both must return `[]`)
7. **Open 1 clean PR** summarizing the verified live numbers, changed files, and
   test counts. Never merge directly to `master` without human review when
   adding new datasets or UI surfaces.

---

## Weekly Distribution Loop (Sunday Evening, ~30s Human Approval)

1. Run `python3 scripts/weekly_social_draft.py` to refresh `output/weekly-draft.md`.
2. Present the four channel drafts (LinkedIn, `r/Connecticut`, Local Facebook
   Town Group / Nextdoor, Bluesky weekly thread) to Alex for 30-second approval.
3. **Community & Platform Guardrails (Non-Negotiable):**
   - **Never scrape private Facebook groups or Nextdoor.** Personal community
     threads are not public datasets and scraping violates platform ToS and
     reader trust.
   - **Never auto-post with bots to Reddit, Facebook groups, or Nextdoor.**
     Human-posted neighborly receipts only; organic sharing is driven by the
     1-click *"Copy town summary to share"* buttons on `/town/*` and `/compare`.
   - Automated posting is restricted to official API channels (Buttondown weekly
     digest + Bluesky via `scripts/ci_post_bsky.sh` with material-change gating).

---

## Prioritized Backlog

### P1 — High-Impact Connecticut Datasets (Keyless / Public APIs)

- [ ] **Municipal Long-Term Debt per Capita (`xgef-f6jp`, OPM Municipal Fiscal Indicators)**
  - *Why:* Reuses the existing `answerer: fiscal_metric` adapter with ~15 lines
    of YAML in `catalog/indicators.yaml` + `catalog/context.yaml` + a row on
    every `/town/*` page and `/compare`.
  - *Acceptance:* Probe exact metric string in `xgef-f6jp` (`Report Edition: 2019-2023`),
    verify 169 towns, add fixture unit test, pass `test_prose_slop.py`.
- [ ] **Tax-Exempt Property Share by Town (`xgef-f6jp`, `Tax exempt property as a percent of total`)**
  - *Why:* Major CT civic debate (especially Hartford, New Haven, college towns
    and PILOT funding). Reuses `fiscal_metric` with percent formatting.
- [ ] **CT Electric Vehicle Registrations by Town (`y7ky-5wcz`, `data.ct.gov`)**
  - *Why:* Live-updated Nov 2026 on `data.ct.gov`; high engagement for CT
    clean-energy & auto/credit-union underwriting prospects.
- [ ] **CT Residential Solar Installations by Town (`fvw8-89kt`, RSIP on `data.ct.gov`)**
  - *Why:* Pairs naturally with Eversource / Northeast electricity rate coverage
    and CT solar/heat-pump underwriting prospects.
- [ ] **CT EdSight / School Chronic Absenteeism or Graduation Rate by District**
  - *Why:* High-search-intent parent & homebuyer data alongside per-pupil
    spending on `/town/*` and `/compare`. Verify official CSDE open-data endpoint.

### P2 — Town Utility, Retention & SEO Polish

- [ ] **Upgrade per-town share cards (`scripts/make_town_covers.py`)**
  - *Why:* Include FY2027 mill rate + 2024 median single-family home sale price
    on `/assets/town-<slug>.png` so pasting `/town/<slug>` into Facebook town
    groups, Nextdoor, or X shows crisp local numbers in the link preview.
- [ ] **Add Mill Rate + 2024 Home Sale Price to `/towns` choropleth map pills**
  - *Why:* Let readers shade the 169-town map on `/towns` by mill rate, 2024
    home sale price, school spending, and 2025 housing permits in addition to
    the 5 ACS Census measures.
- [ ] **Interactive "Download town dossier (CSV / Print-friendly PDF view)" on `/town/*`**
  - *Why:* Gives realtors, town finance boards, and reporters a clean `@media print`
    1-page town sheet with zero backend cost.
- [ ] **Saved-town annual change alerts (Buttondown tag flow)**
  - *Why:* Optional tag-based subscribe (`town:west-hartford`) so readers get an
    email when their specific town's mill rate, home sales, or grand list updates.

### P3 — Monetization & Partnership Milestones (Human-Led)

- [x] **Flip Vercel Web Analytics toggle ON in Vercel Dashboard** (enabled 2026-11-27 on free Hobby tier; triggers fresh edge mount of `/_vercel/insights/script.js`)
  - Code (`/_vercel/insights/script.js`) and `/privacy` disclosure are live; aggregate cookieless path/referrer counts are active.
- [ ] **60-day baseline review (Search Console + Vercel Analytics + Buttondown)**
  - Identify top 20 landing `/town/*` and `/compare` queries and subscriber count.
- [ ] **Outreach wave 1 (once >= 500–1,000 CT digest subscribers or steady `/town/*` search traffic)**
  - Send 10 short, proof-backed outreach notes pointing to `/partner` and
    `/week` to CT credit unions, regional real estate brokerages, clean-energy
    installers, and CTData / local newsrooms.
