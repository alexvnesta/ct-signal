# Real-world walkthroughs — CT Signal, 2026-11-27

Six personas walked the live site and the local build. The point was not to
grade the design in the abstract, but to answer three questions:

1. Where does a real person get value?
2. Where do they get stuck, suspicious, or bored?
3. What would make them come back — and is the site more than a fountain for
   social posts?

The short answer: **the site is already a strong reference desk, but it is not
yet a habit.** Social is currently the fountain; the site is the archive. The
next work is to invert that: social should point to distinct, durable pages,
and the site should give people a reason to return that is not “another
weather update.”

---

## What was walked

| Surface | Why it was walked |
|---|---|
| `/` | First contact; does a stranger know what this is? |
| `/story/<id>` | Reporter, student, skeptic; is the receipt legible? |
| `/towns` + `/town/<slug>` | Homeowner; is local value obvious? |
| `/indicators` + `/indicator/<id>` | Analyst; is the measure stable and reusable? |
| `/topic/<desk>` | Explorer; does a desk explain itself? |
| `/archive` | Returning reader; can they find the long tail? |
| `/about`, `/masthead`, `/corrections`, `/privacy` | Skeptic; who is responsible? |
| Bluesky feed | Social arrival; what does the post promise? |

Checks run after the walkthrough: 19 representative pages at 320 px and 1280 px
(no horizontal overflow, exactly one H1), Lighthouse mobile 100/100/100/100 on
home, a current story, an indicator file, `/towns`, a topic desk and a town
file, and 88 tests passing.

---

## Personas and scenarios

### 1. Dana, 42 — Old Lyme homeowner

**Scenario:** Her mill rate notice arrived. She wants to know whether her town
is high, what the number means, and what it costs on a median-value home.

**Path:** `/towns` → picker → Old Lyme → `/town/old-lyme`.

**Where she got value**
- The picker previews her town immediately: income, poverty, rent, home value,
  median age, each with a rank and denominator.
- The town file gives the mill rate, the rank among 169 towns, the statewide
  comparison, and an estimated tax on the median-value home.
- The narrative names each dataset and vintage separately, so the tax number
  and the ACS number do not blur together.
- The table now says “139th-highest of 169” and “Rank among towns (1 = highest),”
  which removes the old ambiguity about direction.
- “Keep reading” links the town back to the relevant indicator files and the
  town desk.

**What she liked**
- Local entry is fast; she does not have to read a story first.
- The page answers “is my town high?” before it explains methodology.
- The CSV link means she can take the table to a spreadsheet.

**What she did not like / concerns**
- The picker preview is long on a phone; it is useful but visually dense.
- The town file has no “compare with a neighboring town” control. She can read
  ranks, but she cannot put Old Lyme beside Lyme or Essex without opening
  another page.
- The Atom feed is the only “alert me when this changes” path; there is no
  saved-town email or notification.
- The page does not say “last changed since your last visit” — a returning
  homeowner has to reread the whole file.

**What we changed**
- Fixed map ordinals (`143rd`, not `143th`).
- Added rank direction labels.
- Added picker preview on selection.
- Added `/towns.csv` and linked it on `/towns`.

**Still open:** a two-town comparison view and a saved-town alert.

---

### 2. Marcus, 29 — local reporter on deadline

**Scenario:** A CT Mirror budget story lands. He needs a Connecticut number,
a chart he can reuse, the exact query, and a citation-ready URL.

**Path:** homepage lead → `/story/a3514b53fb39` (property tax) or the weather
story from the wire.

**Where he got value**
- The story H1 is the finding, not the question. He can lift it directly.
- The provenance card gives the dataset URL and the literal query.
- The chart is server-rendered and downloadable as PNG; the CSV link gives him
  the rows behind it.
- The “Same headline, more honest questions” block gives him sibling stories
  without duplicating the same link.
- The embed block gives him a copy-paste iframe.
- The corrections path is on the page, not buried in a footer.

**What he liked**
- “Fetched, never written” is a clean trust line.
- The page is reproducible from committed JSON; he can check the archive.
- The story meta now links “Automated data desk” to `/masthead`, so he can see
  who is responsible.

**What he did not like / concerns**
- There is no one-click “cite this story” copy action. He has to assemble the
  headline, URL, dataset and date himself.
- The story page does not show an author byline; “Automated data desk” is
  honest, but a reporter may want a named editor.
- The archive is a list of cards, not a searchable clips library. Finding the
  prior vintage means browsing or using git.
- The social post he arrived from used raw ISO dates (`2026-11-25`) and a long
  caveat; the page is cleaner than the post.

**What we changed**
- Added CSV download to story pages.
- Linked story meta to `/masthead`.
- Changed Bluesky copy to use the finding and display dates, not raw ISO.

**Still open:** a “cite this” action and a searchable archive.

---

### 3. Priya, 35 — policy analyst

**Scenario:** She needs the unemployment series, its definition, its vintage,
and a reusable file. She does not want a news story; she wants a measure.

**Path:** `/indicators` → `Unemployment rate vs. other states` →
`/indicator/unemployment`.

**Where she got value**
- The indicator index groups measures by desk and states the standing question.
- The indicator file gives the current story, latest finding, chart, “Why it
  matters,” provenance, and archived vintages.
- The unemployment labels are now distinct: “Unemployment rate vs. other
  states” (July 2026, 52 peers) versus “Connecticut unemployment rate
  (monthly)” (October 2026).
- The CSV link gives her the chart rows without scraping the table.
- The page is stable across refreshes; the URL is the measure, not the story.

**What she liked**
- The definition paragraph explains what the rate counts and what it misses.
- The provenance card is specific enough to reproduce the query.
- The page does not pretend a single vintage is a time series.

**What she did not like / concerns**
- There is no bulk download across indicators; she must open each file.
- There is no API or JSON endpoint advertised, even though the cards are JSON.
- The “What changed” block is absent on indicators with only one archived
  vintage; that is honest, but a first-time analyst may read it as a gap.
- The indicator page does not show a “last updated” changelog beyond the
  current story date and vintage table.
- The chart’s CSV uses chart rows, not a normalized long-form dataset; for
  some measures the columns are chart-specific.

**What we changed**
- Added `observations.csv` to every indicator file.
- Added the CSV link to the indicator page.

**Still open:** a bulk export and a documented JSON endpoint.

---

### 4. Eli, 17 — student arriving from social

**Scenario:** He sees a Bluesky post about Connecticut running warmer than
normal. He taps the link, wants a quick answer, and wants to know whether it
is a big deal.

**Path:** Bluesky post → `/story/0785479c5e31`.

**Where he got value**
- The H1 answers the question immediately.
- The lede gives the caveat: Bradley and Danbury, each against its own
  normals.
- “What changed” gives the prior day’s number.
- “Why it matters” explains that a 30-day anomaly is a seasonal signal, not a
  weather forecast.
- The chart is legible without reading the table.
- “Keep reading” now offers the Weather desk when there are no sibling
  stories.

**What he liked**
- The page is short enough to finish.
- The chart is the first visual, not a wall of text.
- The source and query are visible without a click.

**What he did not like / concerns**
- The H1 and lede repeat nearly the same sentence; the lede adds the caveat,
  but the repetition is noticeable.
- “What changed” can be a 0.1°F move, which feels like noise to a casual
  reader.
- The “Useful? yes / ▽ no” control is oddly worded.
- The social post itself was one of several near-identical weather posts; the
  feed feels like a ticker, not a newsroom.

**What we changed**
- Added the Weather desk link to “Keep reading.”
- Changed social copy to lead with the finding and use display dates.

**Still open:** a clearer “is this a big deal?” scale, and a less repetitive
social cadence.

---

### 5. Rosa, 58 — skeptical reader

**Scenario:** She likes the number but wants to know who made it, whether it
is automated, how errors are handled, and what data is collected about her.

**Path:** homepage → `/about` → `/masthead` → `/corrections` → `/privacy`.

**Where she got value**
- `/about` says what the site is and is not, and states that no number was
  written or rounded by a language model.
- `/masthead` names the publisher/editor and the reporting desk, and gives a
  contact address.
- `/corrections` lists real corrections with dates, including the 170-town
  error and the credential-in-log error.
- `/privacy` says no accounts, no cookies, no pageview tracking; Vercel request
  logs and Speed Insights are disclosed; Buttondown is disclosed.
- Story pages link “Automated data desk” to `/masthead`.

**What she liked**
- The trust furniture is specific, not generic.
- The corrections page admits a mistake in plain language.
- The privacy page is short and concrete.

**What she did not like / concerns**
- The site says “automated” but the about page also says “built by Alex”; the
  division of responsibility is clear on `/masthead`, but not on the story
  page until the new link.
- There is no visible “last reviewed” date on the about/masthead pages.
- The corrections page admits a credential was once written to a public log;
  that is honest, but a skeptical reader may want a short “what changed since”
  note.
- There is no pageview analytics, so the site cannot show audience evidence;
  that is a privacy choice, but it also means the team cannot see which
  personas arrive.

**What we changed**
- Linked story meta to `/masthead`.

**Still open:** a “last reviewed” stamp and a privacy-friendly audience
measurement decision.

---

### 6. Alex, 31 — civic organizer / social publisher

**Scenario:** He wants to share a chart, embed a story, and point people to a
local page without rewriting the copy.

**Path:** story → share PNG / embed → town page.

**Where he got value**
- The share PNG is generated from the same card, with the question, number,
  rank strip, source and brand.
- The embed block is copy-paste.
- The town page gives him a local link that is more useful than the story for
  a neighborhood audience.
- The CSV lets him build his own chart.

**What he liked**
- The assets are ready to post; he does not have to screenshot.
- The town file is a better landing page for a local group than the national
  story.

**What he did not like / concerns**
- The share PNG is a static image; there is no “copy link + suggested post”
  pair.
- The embed is an iframe; some newsletters and CMSes will strip it.
- The social feed is dominated by weather updates, so his audience sees the
  same story repeatedly.
- There is no “share this town file” asset; town pages have a share card, but
  the social workflow is story-centric.

**What we changed**
- Added CSV links and the homepage town entry.
- Changed Bluesky copy to finding-first.

**Still open:** town-specific share assets and a suggested-post field.

---

## What the walkthroughs found

### The site is stronger than the social feed

The durable surfaces are good:

- Story pages answer a question, show the receipt, and offer a chart, PNG, CSV,
  embed and correction path.
- Town pages answer a local question with a computed narrative, ranks,
  statewide comparison, ACS table and cross-links.
- Indicator pages are stable reference files with definitions, provenance and
  vintages.
- Topic desks explain their standing question and link their measures.
- The trust pages are specific and credible.

The social feed is weaker:

- The public Bluesky feed currently shows a run of near-identical weather
  posts linking the same story, with raw ISO dates in the text.
- The poster is keyed to card IDs and data-date changes, but weather refreshes
  daily, so the same story can be posted repeatedly.
- The post copy used the full answer, including caveats and ISO dates; the new
  copy uses the finding and display dates, which is better, but the cadence
  problem remains.

**So: is it just a fountain for social posts?** Not quite. The site is a real
reference desk. But right now the fountain is doing the distribution and the
site is doing the archiving. That is backwards. The site should be the place
people return to; social should be the place they discover it.

### The missing repeat-visit loop

A first-time visitor can get value. A returning visitor has few reasons to
come back:

- No weekly “what changed” page on the site (the digest is email-only).
- No saved-town alerts beyond the Atom feed.
- No “since your last visit” state.
- No comparison tool.
- No search.
- No newsletter archive on the site.
- No visible audience measurement, so the team cannot see which entry paths
  actually work.

### The missing distribution loop

- Social is weather-heavy and repetitive.
- There is no town-specific share asset.
- There is no “cite this” copy action.
- There is no bulk data export.
- There is no Reddit/Nextdoor pilot live yet.

---

## What we changed in this pass

These are live in the working tree and regenerated:

1. **Homepage deck.** A visible line explains the value proposition, with
   “Find your town →” and “Follow a measure →” links. The old H1 was visually
   hidden; a stranger now gets an orientation before the lead story.
2. **Story trust link.** “Automated data desk” in the story meta links to
   `/masthead`.
3. **Desk link in “Keep reading.”** When a story has no same-desk siblings,
   the block links its topic desk (e.g. Weather desk).
4. **CSV receipts.** Every indicator file serves `observations.csv` from its
   own chart rows; `/towns.csv` serves the 169-town table as raw values and
   ranks. Both are linked on the page that explains them.
5. **Social copy.** Bluesky posts now lead with the finding and use display
   dates; the link-card description also uses display prose.
6. **Earlier walkthrough fixes retained:** map ordinals, rank direction,
   picker preview, duplicate sibling links, clearer unemployment labels,
   focusable mobile peer toggle, indicator provenance, and the 169-town
   invariant.

Validation after these changes: 88 tests pass; 19 representative pages at
320 px and 1280 px have no horizontal overflow and exactly one H1; Lighthouse
mobile is 100/100/100/100 on home, a current story, an indicator file,
`/towns`, a topic desk and a town file.

---

## What to do if we want people to use and visit the site

### Priority 1 — Build a return hook

- **A weekly “What changed” page on the site.** The digest already computes
  the week’s board and top stories. Publish the same issue as `/week/<issue>`
  and link it from the homepage and footer. This is the simplest repeat-visit
  product: one URL that shows the week’s moves, not a feed of everything.
- **A newsletter archive.** If the digest is the retention product, its back
  issues should be readable on the site. That also gives search and social a
  durable destination.
- **Saved-town alerts.** Let a reader “follow” a town and get an email when its
  mill rate, rent, income or poverty vintage changes. The Atom feed is a
  developer path, not a normal-person path.

### Priority 2 — Make local utility obvious

- **Compare towns.** A two-town view (mill rate, median home value, estimated
  tax, income, rent) would turn the town file from a lookup into a tool.
- **A “what does this mean for my bill?” calculator.** The town page already
  estimates tax on a median-value home; let the reader enter an assessed value.
- **A town-specific share asset.** The story share PNG is good; a town share
  card would give local organizers a reason to post the town file.

### Priority 3 — Make social a discovery layer, not a mirror

- **Post on material change, not every refresh.** For weather, require a
  meaningful jump (e.g. ≥1°F from the last posted value) or a threshold cross,
  not just a new data date.
- **Rotate desks.** One weather post, one local-finance post, one economy post
  per cycle is a newsroom; four weather posts is a ticker.
- **Point to the durable page.** Link the town file or indicator file when the
  story is local or measure-specific, not only the story permalink.
- **Use a weekly thread.** A Sunday “what changed this week” thread with three
  distinct links is a better retention loop than daily near-duplicates.

### Priority 4 — Measure the paths

- **Choose a privacy-friendly pageview measurement.** The privacy page
  currently says no pageview tracking; that is a defensible choice, but it
  also means the team cannot see whether people arrive via town pages, story
  pages, social or search. Vercel Web Analytics is not enabled; Speed Insights
  only measures Core Web Vitals. Decide explicitly: either add a
  privacy-friendly counter and disclose it, or accept that audience evidence
  comes from Buttondown and social clicks only.
- **Track entry paths.** The most useful metric is not total pageviews; it is
  which persona path converts: social → story → town, search → indicator,
  newsletter → story.

### Priority 5 — Distribution pilots

- **Reddit/Nextdoor.** A town-specific post (“Old Lyme’s mill rate is 139th of
  169”) is more native to these venues than a national weather chart.
- **CTData / local newsletters.** The white-label digest is still unshipped;
  a co-branded weekly issue is a credible institutional distribution path.
- **Bluesky threads.** Use the chart image plus a short thread that links the
  town or indicator page.

---

## What still needs work

- No web weekly brief; the digest is email-only.
- No newsletter archive.
- No saved-town alerts.
- No comparison tool.
- No search.
- No bulk data export or documented JSON endpoint.
- No “cite this story” action.
- No town-specific share asset.
- Social cadence is still weather-heavy; the copy is better, the frequency is
  not.
- Pageview measurement is still undecided; the privacy page says none, and
  Vercel Web Analytics is not enabled.
- New desks (health, education, transportation, environment, civic government)
  are still waiting on sources.

---

## Bottom line

The site already earns trust and answers real questions. It is not merely a
social fountain. But it is optimized as a reference desk, not as a habit. The
next move is to give people a weekly reason to return, make local comparison a
tool rather than a lookup, and make social point to distinct durable pages
instead of repeating the same weather story.
