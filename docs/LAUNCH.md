# Launch checklist — the five remaining keys (all yours, all ~5 minutes)

The site runs itself; the repo is public; distribution is pre-wired and
dark until each secret exists. Nothing here needs code from me first —
each item lights up an already-merged path.

## 1. Search Console + Bing Webmaster (biggest lever, zero cost)

- <https://search.google.com/search-console> → add property
  `https://ctsignal.org` → verification method **HTML file** is easiest:
  download the file, commit it to the repo root, done (Vercel serves it).
  DNS TXT also fine — apex is at Porkbun.
- Then **Sitemaps → add** `https://ctsignal.org/sitemap.xml` (186 URLs).
- Bing Webmaster Tools ("Import from Search Console" is one click).
- Optional while you're in there: Request Indexing on the homepage and
  the five live stories.

## 2. Buttondown (weekly digest, drafts mode)

- Free plan: <https://buttondown.com> → create account → create list
  "weekly" → API key.
- Repo → Settings → Secrets → Actions → new secret `BUTTONDOWN_KEY`.
- Behavior from then on: the cycle that bumps `output/digest/<week>.html`
  files a **draft** with Buttondown automatically. A human (you) presses
  send — no accidental mail. Subscribe widget in the footer is a
  follow-up 10-minute step once the list exists.

## 3. Bluesky (cards auto-post)

- bsky.app → Settings → App passwords → "ct-signal bot" (handles posting).
- Two secrets: `BSKY_HANDLE` (e.g. `ctsignal.bsky.social`) and
  `BSKY_APP_PASSWORD`.
- Behavior: any cycle that publishes a **new** card id posts one update
  (question, answer, link card, "sources on the page"). Rewords and data
  refreshes don't double-post. No hashtags, no emoji, receipts voice.

## 4. Porkbun (mail + handles)

- Email forwarding: Porkbun → your domain → "Email Forwarding" → create
  `hello@ctsignal.org` → forwards to your inbox. (Site already links
  `mailto:hello@ctsignal.org`; this makes the address real.)
- Reserve `@ctsignal` on Bluesky/X while you're logging in anyway.

## 5. Google News Publisher Center

- <https://publishercenter.google.com> → publication "CT Signal" →
  add website `ctsignal.org` → RSS: `https://ctsignal.org/feed.xml` →
  category News. Reviewers check for About/Methodology/Masthead/Contact —
  all four exist and are linked from every page's footer.
- Acceptance typically takes days; the feed keeps it fresh on its own.

## Then

Watch the Actions tab for a day: green schedule ticks (every ~15 min,
public repos are no longer throttled), occasional `ct-signal-bot`
"feed: HH:MM card refresh" commits = real data movement. After ~2 weeks
of baseline traffic the Phase C drafts (HN meta-story, Nieman Lab pitch,
sponsor one-pager) become writable with numbers in hand.
