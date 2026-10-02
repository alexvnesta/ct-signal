# Judge Q&A drill — attack angles, by judge

Companion to `demo-script.md` (which owns the 3-min script and base one-liners).
This file is the adversarial pass: the hard version of each question, a
≤3-sentence answer, and the artifact you point at if they want proof.

**Tiebreaker doctrine:** the rubric breaks ties on Impact Potential → AI
Effectiveness. If an answer is going nowhere, land it on one of those two:
*"CTData could send this Monday"* (impact) or *"the AI's entire job is
relevance"* (effectiveness). Never end on architecture.

---

## Final round

### Sen. James Maroney — policy, optics, constituents
**"Who decides what gets asked? Today it's rent — tomorrow it embarrasses a district."**
> Nobody editorially. The trigger is the published news cycle, and every card
> shows the article that provoked it. The candidate set is a public,
> version-controlled YAML — the git history is our editorial log. Point: no
> human chose these numbers; the news did.

**"Nice demo. Who keeps this alive in six months?"**
> One cron loop, static hosting, free-tier APIs — the maintenance is an hour a
> month. And the alternative is the status quo: CTData already staffs an
> "Ask a Data Question" helpline by hand; this automates answering questions
> people are already asking them. Point: newsletter mock (slide 5).

**"What does this do for Hartford specifically?"**
> The local cards are municipal (grand-list/revaluation covers all 169 towns),
> and the digest format is exactly what HDC and Hartford orgs republish. The
> catalog is topic-keyed, so a Hartford slice is a filter, not a rebuild.

**Trap to avoid:** getting pulled into CT politics trivia. Redirect to the
pipeline's neutrality — it produces unflattering cards too (Bridgeport +59.9%,
and the rent card shows CT isn't cheap).

### Michelle Riordan-Nold — CTData's own turf; data authority
**"We already have the dashboards. Why do I need this?"**
> Your dashboards are pull; engagement is push. Her own service proves demand —
> the helpline. We don't replace the portals; every card routes readers back to
> the source. Point: slide 2 quote + the source links in each card.

**"Where exactly does '3rd safest' come from? Defensible?"**
> Data Commons `Count_CriminalActivities_ViolentCrime`, 147 per 100k, ranked
> across 52 (50 states + DC + PR — the denominator is defined in the catalog).
> Every DCID was validated live and logged 2026-09-30. Point:
> `docs/data_sources.md` — including the failures ("this is our research slide").

**"ACS lags a year. How do you not present stale data as news?"**
> The card answers the news question, but the data date is printed on the card
> itself — unemployment says July 2026, poverty says 2024. A dated card is a
> receipt; an undated number is a vibe.

**"What would you need from CTData to take this over?"**
> Three things: your topic taxonomy as the catalog, a Socrata app token, and an
> inbox to send the digest from. Election cards need the SOTUS CSV — your
> portal links election results but has no dataset (verified today; it's
> roadmap item #1).

**Trap to avoid:** acting like CTData's problem is data. Their problem is
*arrival*. Concede their data is excellent; you built the last mile.

### Russell Goldenbroit — Google architect; will poke the seam
**"Gemini's the only smart component and it's on a free tier. Single point of failure?"**
> The failure mode is designed: Gemini down → heuristic matcher over the same
> closed catalog, cards degrade to cache, visibly labeled. The system can
> produce a missing card, never a wrong card. Point: the `cache` labels on the
> live board. (Also: this is Gemini free-tier doing real production-shaped
> work — a good story for everyone in the room.)

**"Why a static export instead of a server?"**
> The feed *is* the database. `feed.json` is deterministic given inputs, gets
> committed, and every deploy is an auditable version of the news→data join.
> No server, no state, no cost, no incident.

**"Reproducibility — rerun yesterday, get yesterday?"**
> Inputs are archived (headlines fixture, committed us.json), so a rerun
> renders byte-identical. The git log *is* the replay. Point: commit history's
> "feed: HH:MM card refresh" commits — a timestamped audit trail for free.

**"Scale it 100× — what breaks?"**
> Nothing in the match: it's headlines × a fixed catalog, stateless. The budget
> that breaks first is Data Commons rate limits — already measured and logged
> in `docs/data_sources.md`. The answer to scale is more cache, not more AI.

**"Why vega combo pinned to v5?"** (if he noticed)
> Pinning makes chart rendering deterministic across deploys — same principle
> as the static export: no surprise diffs.

## Semi-final panel (Challenge 4)

### Kelsey Rogers & Cheryl Tokarski — STEM education lens
**"Could a classroom actually use this?"**
> Every card is a complete data-literacy lesson: real trigger article →
> question → data → chart → source. Teachers get a weekly set of them by
> default — it's the same feed the digest uses. No prompting required, which
> is the point: students shouldn't have to invent a query to find out their
> state is 3rd safest on violent crime.

**"How do I know a kid reads this and trusts it?"**
> The card states its own limits — Bridgeport's revaluation caveat is printed
> on the card. Honest cards are the teachable ones.

### Michael Heiser — venture/ops lens
**"What's the ongoing cost, and who pays?"**
> Free Data Commons tier + static hosting + one cron ≈ $0/yr. The buyer is
> CTData, and the pitch is cost *reduction*: they already answer these
> questions manually. Point: the helpline quote on slide 2.

**"What's defensible here — you could be rebuilt in a weekend?"**
> The code, yes — deliberately. The asset is the validated catalog plus the
> public failure log, and being the thing sitting in CTData's inbox Monday.
> Distribution beats moat for civic tools.

---

## Admitted-weakness list (say these before they find them)
1. **Six indicators.** Depth over breadth in 6 hours; adding one is 8 lines of YAML through a validator that already caught real endpoint failures.
2. **No election cards.** CT's portal has no results dataset (we checked; it's a hyperlink). SOTUS ingest is roadmap #1 — the civic-calendar hook already exists.
3. **Free-tier Gemini 503s.** Handled: heuristics + labeled cache.
4. **The 52 denominator.** 50 states + DC + PR, defined in the catalog; framed as "3rd safest" / "10th-lowest poverty," never a raw "#50".
5. **Bridgeport +59.9% is real but needs context** — the revaluation caveat is shown on the card, and we keep it that way.

## Numbers cold (today's board — verify at `./deploy.sh --once` before the slot)
- Rent $1,488 — #17/52 (national headline trigger)
- Unemployment 5.8% — #3/52 highest, trend chart, Jul 2026
- Bridgeport grand list +59.9% — all 169 towns, GL 2025, caveat on card
- Violent crime 147/100k — **3rd safest** in the country (#50/52 by rate; never say "#50")
- Poverty 9.6% — #43/52 *highest* = **10th lowest** (2024 ACS)
