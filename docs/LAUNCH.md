# Launch status — shipped the night of Oct 2, 2026

Everything that was "pre-wired and dark" is now lit. Each item below was
verified against the live service, not assumed.

## 1. Search Console + Bing — DONE

- Property `https://ctsignal.org` verified via HTML file
  (`google581efe0b3bcbbb99.html`, committed — do not delete; `cleanUrls`
  stayed OFF because it 308'd the verification path).
- Sitemap `https://ctsignal.org/sitemap.xml` submitted.
- Bing imported the property via "Import from Search Console"; Sitemaps
  page shows the feed Imported/Processing.

## 2. Buttondown — DONE

- Account `buttondown.com/ctsignal`, branded (name, bio, `#f2a65a` tint).
- Scoped CI key (Emails RW, Sending disabled) lives as `BUTTONDOWN_KEY`.
- API pinned to `2026-04-01`: the digest step files a **draft** with
  `{subject, body}` — verified 201 against production; a human presses
  send. Remaining 10-minute follow-up: footer subscribe widget (the list
  exists now).

## 3. Bluesky — DONE (handle is the domain)

- Account **@ctsignal.org** (did:plc:pwesbwayfxnpvnfpvf7xj6cl), email
  `social@ctsignal.org` confirmed, avatar/bio set via XRPC, launch card
  posted (link card renders with ctsignal.org attribution).
- `@ctsignal.org` works because Porkbun DNS serves
  `_atproto TXT "did=did:plc:..."` (exact value:
  `did=did:plc:pwesbwayfxnpvnfpvf7xj6cl`). Keep that TXT record.
- Secrets: `BSKY_HANDLE=ctsignal.org`, `BSKY_APP_PASSWORD` (label
  "ct-signal-ci", no DM access). createSession verified live.
- Poster fix shipped same night: session token lives at `accessJwt`, not
  `access_token`; first run after the secrets land posts nothing rather
  than dumping the whole card backlog.

## 4. Porkbun — DONE

- Email forwarding (free, MX → fwd1.porkbun.com): `social@ctsignal.org`
  (account-notification sink) and `hello@ctsignal.org` (public contact)
  both forward to the personal inbox. Bluesky's verification email rode
  this path end-to-end — forwarding proven by real mail, not by hope.
- A hosted-email free trial sits unconfigured on the domain; it expires
  Oct 17 harmlessly. Don't configure it unless a real inbox is wanted —
  hosted mail and forwarding share one MX story.

## 5. Publisher Center — DONE

- Publication "CT Signal" claimed (id `CAowg-_hCw`), US/English. The
  March-2025 Publisher Center auto-builds the Google News page from the
  sitemap + feed once claimed; no feed-section wizard remains to click.

## Watching

- Actions tab: green scheduled ticks; `ct-signal-bot` "feed: HH:MM card
  refresh" commits mean data moved (heartbeat restored when repo
  privileges were flipped — see commit `256f7f9`).
- Search Console coverage reports over the next week; index request on
  homepage + live stories is worth one click once content looks settled.
- After ~2 weeks of baseline the Phase C drafts (HN meta-story, Nieman
  pitch, sponsor one-pager) become writable with numbers in hand.
