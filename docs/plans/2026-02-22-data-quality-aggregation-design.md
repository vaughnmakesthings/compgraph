# Data Quality & Aggregation Design

**Date:** 2026-02-22
**Milestone:** M4 — Aggregation & API
**Status:** Design approved, pending implementation plan

## 1. Data Quality Assessment

Live database inspection of 2,575 postings (Feb 15-20, 2026) across 4 competitors. 2,548 enriched (99% coverage).

### Critical (blocks aggregation)

| Issue | Impact | Fix |
|-------|--------|-----|
| `title_normalized` at 0% fill rate | Cannot group similar roles for aggregation | Deterministic normalization function (Section 5) |
| `markets` table empty, 0 rows | No geographic dimension for agg_pay_benchmarks or coverage gaps | Market normalization pipeline (Section 3) |
| 3 duplicate brand pairs | Inflates brand counts, splits brand timelines | One-time merge script (Section 4) |

### Medium (degrades quality)

| Issue | Impact |
|-------|--------|
| 1,763 distinct locations with 250+ format duplicates | Same city split across multiple entries (case, suffix, zip variations) |
| 70 enrichments with pay_type but NULL amounts | Known pattern — LLM identified structure without dollar figures |
| 188 Canadian locations (7%) need CMA grouping | Separate normalization from US MSA logic |

### Low (monitor)

| Issue | Impact |
|-------|--------|
| 27 unenriched postings (1%) | Negligible — likely malformed source HTML |
| 6-day snapshot window | Narrow for trend detection; resolves with continued collection |

## 2. Approach: Clean-Then-Aggregate

Three approaches were evaluated:

- **A: Clean-Then-Aggregate** — fix data quality issues first, then build aggregation jobs on clean data
- **B: Aggregate-First, Clean in Parallel** — build agg jobs tolerating dirty data, clean alongside
- **C: LLM Enhancement Pass + Clean + Aggregate** — add new LLM fields first, then clean and aggregate

**Selected: Approach A** — clean data first, aggregate second. Rationale:
- Aggregation queries are simpler when source data is clean
- Market normalization is a hard dependency for pay benchmarks and coverage gaps
- Brand dedup is surgical (3 updates) and should not be deferred
- LLM enhancements (Approach C) deferred to M5+ after enrichment pipeline stabilizes

## 3. Market Normalization

### Problem

1,763 distinct `location_raw` values in `posting_snapshots` representing ~900 unique cities across ~200 metro markets. Three categories of inconsistency:

- **Format duplicates** (~250 entries): `Dallas, TX` vs `DALLAS, TX, US` vs `Dallas, TX, US`
- **Suburb fragmentation**: Dallas, Richardson, Plano, Frisco, Arlington all map to Dallas-Fort Worth metro
- **Cross-border**: US locations use state codes, Canadian locations use province codes (ON, BC, AB)

### Solution: 3-Layer Normalization

**Layer 1 — Deterministic regex (at ingest time):**
```
1. Strip trailing ", US" suffix
2. Normalize case → title case
3. Remove embedded ZIP codes
4. Collapse whitespace
```
Reduces 1,763 → ~900 unique city strings.

**Layer 2 — `location_mappings` table (LLM-seeded):**
```sql
CREATE TABLE location_mappings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_normalized TEXT NOT NULL,       -- "Richardson"
    state           TEXT NOT NULL,       -- "TX"
    country         TEXT NOT NULL DEFAULT 'US',  -- "US" or "CA"
    metro_name      TEXT NOT NULL,       -- "Dallas-Fort Worth"
    metro_state     TEXT NOT NULL,       -- "TX"
    metro_country   TEXT NOT NULL DEFAULT 'US',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (city_normalized, state, country)
);
```

One-time seeding process:
1. Extract distinct (city, state, country) triples after Layer 1 normalization
2. Batch 50 cities per Haiku 4.5 call with prompt: "Map each city to its US Census MSA or Canadian CMA metropolitan area"
3. ~18 batches at ~$0.005/batch = ~$0.10 total
4. Manual review of ambiguous mappings before INSERT

**Layer 3 — `markets` table:**
```sql
CREATE TABLE markets (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name    TEXT NOT NULL UNIQUE,  -- "Dallas-Fort Worth, TX"
    state   TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'US'
);
```

Populated by `SELECT DISTINCT metro_name, metro_state, metro_country FROM location_mappings`.

**Ongoing flow (new postings):**
1. Scraper writes `location_raw` to `posting_snapshots` (unchanged)
2. Enrichment pipeline applies Layer 1 regex → looks up `location_mappings`
3. If city not found → queue for LLM mapping (batch daily, same Haiku prompt)
4. Aggregation jobs JOIN through `location_mappings` → `markets`

## 4. Brand Deduplication

Three duplicate brand pairs identified:

| Current Entries | Canonical Name |
|----------------|---------------|
| "Reliant" + "Reliant Energy" | Reliant Energy |
| "LG" + "LG Electronics" | LG Electronics |
| "Virgin Mobile" + "Virgin Plus" | Virgin Plus |

**Fix:** One-time migration script:
1. UPDATE `posting_brand_mentions.resolved_brand_id` → canonical brand ID
2. DELETE duplicate brand rows
3. Add normalized aliases to entity resolution pipeline to prevent re-creation

Wrapped in a single transaction. 3 UPDATE + 3 DELETE statements.

## 5. Title Normalization

`title_normalized` is at 0% fill rate despite being in the enrichment schema.

**Selected: Deterministic normalization (no LLM):**
- Lowercase
- Strip trailing location/company boilerplate (e.g., "- Dallas, TX", "| 2020 Companies")
- Collapse whitespace and special characters
- Backfillable: run once across all 2,548 enrichments

If quality proves insufficient for role grouping, upgrade to LLM-based normalization later.

## 6. Pay Data: No Cleanup Needed

70 enrichments have `pay_type` set but `pay_min`/`pay_max` are NULL. This is correct behavior — the LLM identified the compensation structure ("commission role") but the posting text didn't include dollar amounts.

Aggregation queries filter with `WHERE pay_min IS NOT NULL`. Documented as known pattern, not a data quality issue.

## 7. Aggregation Job Execution Order

All jobs use **truncate+insert** pattern (pre-committed architecture decision).

| Order | Table | Depends On |
|-------|-------|------------|
| 1 | `agg_daily_velocity` | postings, posting_snapshots |
| 2 | `agg_brand_timeline` | posting_brand_mentions, brands, postings |
| 3 | `agg_posting_lifecycle` | postings, posting_snapshots |
| 4 | `agg_pay_benchmarks` | posting_enrichments, markets, location_mappings |

Jobs 1-3 can run independently. Job 4 depends on market normalization (Section 3) being complete.

## 8. New Aggregation Tables

Beyond the existing 4 empty tables, add 3 high-value tables for business development:

### P0 — `agg_brand_churn_signals`
**Question:** Which competitor-brand relationships are deteriorating?

Per (company_id, brand_id) per rolling 7-day window:
- `active_posting_count`, `velocity_delta` (% change vs prior period)
- `avg_days_active` for open postings, `repost_rate`
- `churn_signal_score` — composite: declining volume + aging postings + rising reposts

**Action:** BD team proactively pitches brands where a competitor shows churn signals.

### P0 — `agg_market_coverage_gaps`
**Question:** Where are competitors absent or thin?

Per (company_id, market_id):
- `total_active_postings`, `brand_count`, `brand_list` (array)
- `coverage_density` (postings per market, normalized)
- Cross-reference: brands a competitor serves nationally but not in specific markets

**Depends on:** market normalization complete (Section 3).
**Action:** "Your current agency has no presence in these top-20 DMAs."

### P1 — `agg_brand_agency_overlap`
**Question:** Which brands use multiple agencies (easier to win)?

Per (brand_id):
- `agency_count`, `agency_list`, `primary_agency`, `primary_share`
- `is_exclusive` (single agency), `is_contested` (no agency >60% share)

**Action:** Target multi-agency brands first — they already accept multi-vendor model.

### Deferred (M5+)
- Hiring surge detection → event-driven alerts, not periodic agg
- Market concentration index (HHI) → useful after 90+ days of data
- Seasonal patterns → needs 3+ months of collection
- Role architecture comparison → extends existing agg tables
- Posting quality score → internal benchmarking

## 9. New LLM-Derived Fields (Deferred to M5+)

Do NOT add to enrichment pipeline now. Defer until Pass 1/Pass 2 are stable and Prompt Evaluation Tool (#128) exists.

| Signal | Value | Target |
|--------|-------|--------|
| `program_name` (e.g., "Samsung Experience Zone") | Track specific programs over time | M5 |
| `urgency_signals` ("immediately", "ASAP") | Detect turnover / struggling to fill | M5 |
| `predecessor_mentions` ("replacing", "taking over") | Competitive displacement evidence | M5 |
| `contract_duration_hints` ("long-term", "6-month") | Estimate contract value | M6 |
| `turnover_signals` (low qualification bar) | Vulnerability detection | M6 |

## 10. Dashboard Pages (Deferred)

No further Streamlit development. Dashboard pages for BD users will be built in Next.js/React (M7):

- **Competitive Radar** — brand churn signals + surge detection
- **Market Map** — geographic coverage gaps by competitor and brand
- **Comp Benchmarks** — pay vulnerability index by market/role
- **Brand Profiles** — per-brand view of competing agencies, program sizes, pay ranges

## Implementation Sequence

```
Phase 1: Data Cleanup (no schema changes needed)
  ├── Brand deduplication (Section 4) — one-time migration
  ├── Title normalization backfill (Section 5) — deterministic function
  └── Location regex normalization (Section 3, Layer 1)

Phase 2: Schema + Seeding
  ├── location_mappings table + LLM seeding (Section 3, Layer 2)
  ├── markets table population (Section 3, Layer 3)
  └── agg table schema additions (Section 8) — 3 new tables

Phase 3: Aggregation Jobs
  ├── agg_daily_velocity rebuild job
  ├── agg_brand_timeline rebuild job
  ├── agg_posting_lifecycle rebuild job
  ├── agg_pay_benchmarks rebuild job (depends on Phase 2)
  ├── agg_brand_churn_signals rebuild job
  ├── agg_market_coverage_gaps rebuild job (depends on Phase 2)
  └── agg_brand_agency_overlap rebuild job

Phase 4: API Endpoints (read-only)
  └── FastAPI endpoints exposing aggregation data for dashboard consumption
```
