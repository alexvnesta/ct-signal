# Stories and the story index — design plan

Adopted 2026-11-26. This is the working plan for turning CT Signal's dated
answers into readable, findable stories — and for making `/archive` behave
like a publication index rather than a list of timestamps.

The diagnosis is simple: the pipeline is good at producing one accurate
answer, but the site still reads like a stream of snapshots. A reader who
arrives from search gets a chart, a sentence and a source; a reader who wants
the backstory, the direction of travel or the next thing to watch has to
reconstruct it themselves. The fix is not a new framework. It is an article
shell that puts the finding first, an index that exposes findings, and a small
amount of computed prose around the data we already have.

**Ship status (2026-11-27).** Phase 1 — the article shell, topic desks and
finding-first archive — and Phase 2 — computed context, collapsed chart
receipts and 18 stable indicator files — are implemented and verified.
Phases 3–4 remain the plan of record. Evidence is recorded in §9.

## 1. The product shape

Four content types, each with a different job:

| Type | Job | Length | Cadence |
|---|---|---|---|
| **Signal story** | One current finding, one chart, one source | 250–450 words | Every publish |
| **Weekly brief** | The strongest few changes, linked to stories | 600–900 words | Sunday/Monday digest |
| **Explainer** | Evergreen answer to a standing question | 800–1,500 words | When a topic earns it |
| **Town note** | A place's numbers, compared honestly | 300–600 words | With ACS/town updates |

Signal stories are the base layer. They need a durable article URL, a finding
headline, and enough context to stand alone. Explainers are the reference
layer and should eventually live on stable per-indicator pages. The weekly
brief is distribution, not a substitute for either.

## 2. Story page anatomy

The order below is deliberately reader-first. Nothing decorative comes before
the finding.

1. **Compact header** — brand and primary navigation only. No nameplate
   skyline on article pages; the story is the artwork.
2. **Breadcrumb** — `← All stories`.
3. **Kicker** — topic desk, stream, cache badge if applicable.
4. **Finding as H1** — one sentence, derived from the answer, stripped of the
   peer-ranking tail. Example: “Connecticut ran 4.7°F warmer than normal over
   the 30 days ending Nov 26, 2026.”
5. **Question deck** — the standing question in smaller type directly below
   the headline. It tells the reader what was asked without taking the H1.
6. **Byline line** — published date, last revalidated date when different,
   compact data vintage, desk attribution. One line, tabular numerals, no fake
   precision.
7. **Opening explanation** — the full answer as normal prose, not a boxed
   callout. The headline is the short version; this is the receipt-bearing
   version. ISO dates become long-form prose dates here.
8. **Key chart** — one accessible chart, source/caption underneath, download
   link. The chart is not the hero image. Its container reserves height before
   Vega mounts, including on mobile.
9. **Quick vote** — one quiet control after the chart, never before the
   finding; counts are stored but not displayed.
10. **Source and method box** — dataset, query, retrieval time, caveats.
11. **Freshness strip** — what was checked, when, and what the vintage is not.
12. **Embed and correction** — one copyable chart spec and a visible
    correction path.
13. **Related stories** — same topic or same town, not random.
14. **Newsletter link** — the footer subscription, never a modal.

Phase 2 now inserts **“What changed”**, **“Why it matters”**, **“What to
watch”** and a collapsed data table between the chart and the source box. Each
claim is computed from the card, the observation history, or the evergreen
context catalog — never invented by the renderer. “What to watch” appears only
when the civic calendar supplies a real upcoming release.

The current page already has most of the receipts: chart caption, provenance,
freshness strip, embed snippet, correction policy. The redesign keeps those
and removes the duplicated social cover from the reading column. The
1200×630 cover remains the OG/social artifact only.

### Headline rule

The H1 must be the finding, not the question. A deterministic `finding`
helper extracts the first sentence of `answer_text`, drops the trailing
“Nth-highest/lowest of 52 peers” comparison, drops “adding $X” tails, and
shortens a few known long forms. If the result is still too long, the question
becomes the fallback headline. No LLM rewrite at render time: the page must
be reproducible from the same card JSON.

### Metadata rule

Show three clocks, not one:

- **Published** — when the story first appeared.
- **Updated** — when the current card was last revalidated, if later.
- **Data as of** — the observation date inside `answer_values.date`.

A reader should never have to guess whether “Nov 26” means the story date or
the data date.

## 3. Index anatomy

`/archive` becomes the publication index. Blog-index conventions that apply
here:

1. **Header** — one H1 (“Every story we've published”), one explanatory
   sentence, total count.
2. **Topic filters** — links to `/topic/<topic>`; filters must work without
   JavaScript because the topic pages already exist.
3. **Reverse-chronological list** — month H2 headings, one row per story,
   finding H3. No skipped heading levels.
4. **Finding headline** — the same `finding` used on the story page.
5. **Question line** — the standing question as a one-line deck.
6. **Date and desk** — topic + publication date, not raw ISO timestamps.
7. **Topic desks** — `/topic/<topic>` reuse the same rows and all seven topic
   chips, with the active desk marked; they are not a second card grid.
8. **Pagination later** — unnecessary at 20 cards; add when the archive is
   over ~60 and measure first.

No identical card grid. No infinite scroll. No “featured” module until there
is enough publishing volume to justify one. The list is the product.

The board's rail can keep “Latest questions”; the global nav should point to
`/archive` as **Stories**, because “Latest questions” currently points at the
lead section, not a list.

## 4. Typography and reading measure

- Body text: 18–20px, line-height 1.55–1.65, 60–75 characters per line.
- H1: `clamp(1.85rem, 4vw, 2.45rem)`, balanced wrapping, no more than
  three lines on desktop.
- H2 section labels: sans, uppercase, small, with a clear top rule.
- Chart labels and captions: sans; narrative and headline: Newsreader.
- One typeface download on article pages remains acceptable; no new font
  request for prose.
- Keep the column at 760px, but let prose run slightly narrower than the
  chart card when the chart needs full width.

## 5. Accessibility and performance

- WCAG 2.2 AA: 4.5:1 text contrast, visible `:focus-visible`, 44px targets
  for primary controls and topic chips, 24px minimum for inline links,
  semantic headings, one H1.
- Charts: `role="img"` + descriptive `aria-label`; caption below; keyboard
  focus; data table fallback when the chart carries more than a summary.
- No autoplay, no scroll hijacking, no newsletter modal.
- Static HTML, minimal JS. Vega only where a chart exists. On the Lighthouse
  mobile profile, article and board FCP is 1.1s and CLS is 0; the 833 KB chart
  renderer is loaded after the page's own load event, then injects into a
  reserved container, so the finding does not wait behind chart JavaScript.
  The peer map below the fold mounts only when 20% visible, so map compile
  stays off the first paint.
- The town choropleth ships integer, relative-coordinate SVG paths (about
  60 KiB instead of 126 KiB). The town picker still uses the production
  `api/geo` location hint, but only on ctsignal.org: previews and the local
  static harness must not request a route their host does not serve.
- Respect `prefers-reduced-motion`; no entrance animations on article chrome.

## 6. SEO, schema and trust

- Title: finding + ` · CT Signal`; meta description: answer, trimmed.
- One H1, semantic section H2s, canonical URL, article schema with
  `datePublished`, `dateModified`, Organization author, breadcrumbs.
- RSS and JSON feed keep the question as the item title until the finding
  helper is stable; do not ship two different headline systems silently.
- Trust markers on-page: byline/desk, source list, query, data date,
  correction policy, “automated data desk” disclosure.
- Internal links: topic desk, related stories, town page, methodology.
- Avoid promising “live” data when the vintage is annual. Say “data as of”.

## 7. Editorial rubric for every story

A story passes when:

1. The headline states the finding, not the topic.
2. The opening sentence includes a number, its unit, the geography, the data
   date, and the comparison.
3. The second sentence adds movement, a benchmark, or a consequence.
4. The caveat is explicit and close to the number it qualifies.
5. Receipts are visible: source, query, retrieval time, vintage.
6. The chart, caption and answer tell the same story; no orphaned annotation.
7. The prose passes the house style tests (`tests/test_prose_slop.py`).
8. There is one clear next action: read the source, open the town page,
   subscribe, or embed.
9. The page is readable at 320px and keyboard-operable.
10. The story can be understood without the homepage.

## 8. Implementation phases

### Phase 1 — article shell and index (shipped 2026-11-26)

- [x] Compact article header in `theme.py`; no full nameplate on story pages.
- [x] Hide the social cover from the article body; keep it as OG image.
- [x] Add `_finding()` in `newsroom.py`; H1 is the finding, question becomes
      deck.
- [x] Replace the boxed answer with a prose lede; humanize display dates
      without changing card JSON.
- [x] Add published/updated/data-date metadata as atomic spans.
- [x] Promote card labels to semantic H2s; month H2, finding H3 in indexes.
- [x] Rebuild `/archive` as a finding-first index with all topic links.
- [x] Rebuild topic desks from the same archive rows; singular/plural counts.
- [x] Point global nav at `/archive` as Stories.
- [x] Move the vote control below the chart.
- [x] Reserve chart height on mobile (`--viz-h`, capped at 340px), fixing the
      0.26 CLS regression.
- [x] Refresh archived story pages with the same shell, so every archive link
      opens the current article contract rather than an older template.
- [x] Lazy-mount the below-fold peer map (20% visibility); preserve its
      `role="img"` wrapper and label after Vega replaces the target.
- [x] Exclude the statewide `Total` aggregate from town lists and pages:
      the equalized-assessment card now says 169 towns, the fake
      `/town/total` page is gone, and the fix is logged on `/corrections`.
- [x] Load the pinned Vega stack after page load; charts still mount in the
      reserved container, and the first paint no longer shares a critical
      path with an 833 KB renderer.
- [x] Compact the town map's SVG geometry to integer relative coordinates;
      `/towns` now clears 100/100/100/100 on the same mobile profile. Keep the
      production-only location hint, but gate it by host so previews never
      log a 404.
- [x] Underline inline prose, table and label links (WCAG 1.4.1 contrast cue),
      bringing `/about` and individual town pages to 100 accessibility.

### Phase 2 — computed context and stable files (shipped 2026-11-27)

- [x] Add a “What changed” module from observation history: latest value,
      prior value, direction, magnitude, and observation dates. Annual values
      stay annual; monthly and daily dates keep their own precision.
- [x] Add an evergreen “Why it matters” line from `catalog/context.yaml` for
      every current indicator, with no claim that the number is new.
- [x] Add “What to watch” only where a release calendar supplies a real
      upcoming seed; suppress it during a quiet week.
- [x] Add a collapsed data table to every chart. Tables keep all local town
      rows and every peer row; long national series show the latest 12 rows
      per series and say so.
- [x] Add 18 stable `/indicator/<id>` files and a grouped `/indicators` index.
      Each file keeps one H1, the standing question, the current finding, the
      chart receipt, computed context, vintages on record, provenance, and a
      link to the current story.
- [x] Add `/indicators` to the footer and both index and per-indicator URLs to
      the sitemap. Stale indicator directories are removed on each build.
- [x] Link each topic desk to its own indicator files, so a reader who arrives
      through a story can reach the standing reference page without guessing.
- [x] Make the mobile chart summary keyboard-operable: the checkbox stays in
      the tab order, the label gains a focus ring, and Space reveals the chart.
- [x] Rebuild archived story pages with the Phase 2 context modules so old
      links share the current page contract.

### Phase 3 — durable reference

- Evergreen explainers for the six existing topics; add health, education,
  transportation, environment and civic government when sources are ready.
- Town pages gain a narrative top block and cross-links to related stories.
- A weekly brief that links the best stories rather than duplicating them.

### Phase 4 — measurement and distribution

- Privacy-respecting page analytics and Search Console verification.
- Track article entry paths, not just homepage visits.
- Digest cadence and Bluesky posts measured against story clicks.
- Reddit/Nextdoor pilot only after the article pages can hold their own.

## 9. QA gates

- `.venv/bin/python -m unittest discover -s tests` — 82 tests, OK.
- Crawl every page at 320 and 1280; no horizontal overflow. Last crawl:
  221 sitemap paths — 18 indicator files, `/indicators`, 169 real town pages;
  no aggregate `/town/total`.
- Keyboard pass on article header, chart focus, vote controls, embed details.
- Check one story per stream/topic shape (rank, trend, local, weather).
- Lighthouse mobile on home, one current story, `/archive`, one archived
  story, `/towns`, `/about`, a topic desk and a town page; keep the
  100/100/100/100 bar. Last run (2026-11-26): home, current story, growth
  story, archive and archived story all 100/100/100/100 with FCP 1.1s and
  TBT 0; `/towns` 100/100/100/100 (FCP 1.5s, CLS 0.012); `/about`, topic desk
  and town page 100/100/100/100.
- Stable indicator pages, `/indicators` and topic desks hold 100/100/100/100
  on mobile (last run 2026-11-27; FCP 0.9s, CLS 0, TBT 0).
- Keyboard pass includes the mobile chart toggle: tab to the checkbox, Space
  expands the full chart and shows its caption.
- Live byte-check after Vercel deploy: title, H1, canonical, JSON-LD, OG.
- Regenerate story covers only after template changes settle; then rerun
  `publish.publish` so cache tokens match.

## 10. Non-goals

No SPA, no CMS, no ad network, no comments, no cookie banner, no modal
newsletter popup, no infinite scroll, no template swap. The site stays
server-rendered and cheap to operate.

## References

- [Data Journalism Handbook](https://datajournalism.com/read/handbook/one)
- [AP News Values and Principles](https://www.ap.org/about/news-values-and-principles/)
- [SPJ Code of Ethics](https://www.spj.org/ethics/)
- [Trust Project indicators](https://trustproject.org/trust-indicators/)
- [Datawrapper chart-type guide](https://www.datawrapper.de/blog/chart-types-guide)
- [FT Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary)
- [NN/g: how users read on the web](https://www.nngroup.com/articles/how-users-read-on-the-web/)
- [Baymard: line length and readability](https://baymard.com/research-articles/line-length-readability)
- [Practical Typography: line length](https://practicaltypography.com/line-length.html)
- [WebAIM contrast checker](https://webaim.org/resources/contrastchecker/)
- [WCAG 2.2 quick reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [Google Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals?hl=en)
