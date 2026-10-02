# Data & key validation log — 2026-09-30

Every source and key below was hit live before relying on it. Failures kept
on purpose: "what we ruled out" is research.

## Keys (all tested 2026-09-30, stored in `.env`, git-ignored, chmod 600)

| Key | Status | Notes |
|---|---|---|
| Data Commons | ✅ working | Used via official `datacommons-client` Python lib. Raw REST gotchas: key in `?key=` query param; short legacy DCIDs (401-era guesswork) are dead — see table below |
| Gemini | ✅ working | Model `gemini-3.8-flash` via `v1beta ...:generateContent`, `x-goog-api-key` header. `gemini-2.5-flash` retired for new users |
| data.ct.gov Socrata token | ❌ rejected | Tyler-hosted portal answers "Invalid app_token specified" for both the key ID and the secret (header and query param). Anonymous SODA works fine → we run keyless; token file kept in `.env` harmlessly |
| Data Commons NL API | ⚠️ unresolved | Key must go in `x-api-key` header; `/api/detect-intent` returns 405 (endpoint likely renamed). Unused by the pipeline; stat-var discovery done via `fetch_available_statistical_variables` instead |

## Validated Data Commons DCIDs (2024–2026 v2 naming; 52 peers each (50 states, DC, Puerto Rico))

| Indicator | DCID | CT latest (fetched) |
|---|---|---|
| Median gross rent | `Median_GrossRent_HousingUnit_WithCashRent_OccupiedHousingUnit_RenterOccupied` | $1,488 (2024) |
| Median household income | `Median_Income_Household` | $95,781 (2024) |
| Median home value | `Median_HomeValue_HousingUnit_OccupiedHousingUnit_OwnerOccupied` | $366,900 (2024) |
| Unemployment rate | `UnemploymentRate_Person` | 5.8% (2026-07) |
| Poverty (rate w/ `Count_Person` denom) | `Count_Person_BelowPovertyLevelInThePast12Months` | 9.6% (2024) |
| Violent crime (per-100k w/ `Count_Person`) | `Count_CriminalActivities_ViolentCrime` | 5,434 offenses (2023) |

NAEP average-scale-score has no plain all-student statvar (only demographic
slices / `Percent_NAEP_CumulativeAtAdvanced...`) → education stack-up will
use CT Socrata report-card datasets on event day.

DC response shape gotcha: observations nest under `byEntity[e].orderedFacets[].observations[]`
(with duplicates across facets — take max-date across facets, dedupe by facet).

## CT Open Data Portal — data.ct.gov (keyless)

- Catalog search is **network-wide**; filter on `metadata.domain == "data.ct.gov"`.
- Non-tabular datasets error on SODA ("no row or column access") — always
  SODA-test with `$limit=1` (`2cta-kxuv` "voter turnout" is a dashboard).
- Verified tabular, rows fetched live: `webp-fgt3` Net Grand List by Town
  (2025 data; full 169-town YoY comparison computed live),
  `8rr8-a322` Equalized Grand List, `xgef-f6jp` Municipal Fiscal Indicators.
- Caveat for grand-list cards: 2025 is a revaluation year in many towns —
  YoY growth mixes market moves with reassessment; cards must state this.

## Ruled out

- **BLS v1 API dead** (even `CES0000000000001` "does not exist").
- **FRED `fredgraph.csv`**: keyless + current (CTUR Aug 2026 = 5.1%) but
  blocks scripted retries → cross-check fallback only, never primary.
- **CT Examiner, ConnCATs feeds dead**; Courant/AP feeds absent/403.

## Feeds (200 + live titles on 2026-09-30)

CT Mirror `ctmirror.org/feed/`, Google News `?q=connecticut` (dedupe
syndicated titles), NYT U.S. RSS, NPR 1001, PBS NewsHour headlines.

## Design consequences

1. `datacommons-client` is the only sane way into DC (raw REST error
   messages underdocument the real schema).
2. Every DC card value is fetched (2026-09-30 live); fixtures exist purely
   as WiFi-death insurance and are labeled `cache` in the UI.
3. Dry-run validation (propose → discard if no data) proved itself during
   development: it silently caught dead DCIDs, non-tabular datasets, and
   keyword misses.
