# Newsroom plan — from hackathon demo to legit CT data newsroom

Decisions locked 2026-10-02: fully automated publishing (transparency is the
editorial stance), domain **ctsignal.org** (Porkbun/Cloudflare), social on all
four platforms in order Bluesky → X → LinkedIn (weekly) → Instagram,
newsletter: **EmailOctopus for sending + a Substack column for reach**.

## The ladder

**Phase 1 — A real site ✅ (this push)**
- Story permalinks: every card → `/story/<id>` with canonical, OG, publish
  date, trigger, provenance. Durable URLs are the atom; everything else
  (social, citations, RSS) compounds on these.
- Archive: every card ever, as JSON, at `/archive/<YYYY-MM>/<id>.json` —
  corrections are diffable because the archive is git.
- RSS (`/feed.xml`) + `sitemap.xml` + newsroom pages: `/about`,
  `/methodology`, `/masthead`, `/corrections` — the trust furniture a
  generated newsroom should advertise, not apologize for.
- GitHub Actions `pulse` workflow replaces the laptop loop: 15-min cron,
  `python run.py --once` → `deploy.sh --deploy`. The commit is still the
  deploy and the audit trail (now bot-authored, timestamped, reviewable).

**Phase 2 — Presence**
- Share-image generator: per-story PNG (question top, big number, rank strip,
  source line, brand colors) rendered from data already in the card.
- Idempotent social poster keyed on card IDs (`.posted.json` state): Bluesky
  → X → weekly LinkedIn digest post. OG tags from Phase 1 make even manual
  shares look produced.
- Accounts: @ctsignal everywhere available; one branded avatar; bio = the
  methodology one-liner + link.

**Phase 3 — Newsroom muscle**
- SOTUS election ingest (the vertical local news must notice).
- Town pages from the archive (169 grand-list pages = SEO long tail, free).
- Newsletter sending: EmailOctopus (SES, free ≤2,500 contacts) via API —
  the digest HTML is already generated; Substack column for human voice.
- Topic sections + "for teachers" view (the challenge judges' audience).

**Phase 4 — Institution**
- CTData white-label digest (their logo, our pipeline — slide 5, executed).
- Reprints with CT Mirror / ConnectCT orbit; fiscal sponsorship when grants appear.

## Ops runbook (Phase 1, one-time)
1. **Repo secrets**: Settings → Secrets and variables → Actions →
   `DC_API_KEY`, `GEMINI_API_KEY`. Until set, pulses run heuristics +
   keyless Socrata only (feed never breaks — cards just stop growing).
2. **DNS** (Cloudflare, both *DNS only / grey cloud*):
   `A @ → 76.76.21.21` and `CNAME www → cname.vercel-dns.com`; remove the
   Porkbun parking records. Then add `ctsignal.org` + `www.ctsignal.org` in
   Vercel → project → Settings → Domains.
3. **Retire the laptop loop** — no more `./deploy.sh` on the Mac; the
   workflow owns the heartbeat now (`--pin` still exists for snapshots).
4. Stop Deployment Protection (already done), and keep `hello@ctsignal.org`
   forwarding somewhere real — corrections promises are load-bearing.

## Notes
- `data/asked_log.json` is now committed: the "already asked" memory persists
  across CI runs, so free-tier quotas aren't re-burned on old headlines.
- Story pages reference charts via absolute `SITE_URL` paths; the board keeps
  relative ones so the Vercel preview works pre-domain.
- If GitHub Actions pulses look stale after ~60 days of zero pushes, re-run
  the workflow manually (Actions → pulse → Run workflow); scheduled runs park
  on inactive repos.
