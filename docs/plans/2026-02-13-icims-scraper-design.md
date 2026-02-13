# iCIMS Scraper Adapter Design

**Issue:** #2 — iCIMS scraper adapter (MarketSource + BDS)
**Date:** 2026-02-13
**Status:** Approved

## Context

First scraper on the critical path. Covers 2 of 4 target companies (MarketSource, BDS Connected Solutions). Both use iCIMS-hosted career portals with consistent URL patterns and JSON-LD structured data.

## Approach: JSON-LD Extraction (Approach A)

Single `ICIMSAdapter` class implementing `ScraperAdapter` protocol. Paginates listing pages via HTML table, fetches detail pages, extracts `JobPosting` JSON-LD schema.

## Architecture

```
PipelineOrchestrator
  → ICIMSAdapter.scrape(company, session)
    → 1. Paginate listing pages (GET /jobs/search?pr=N&in_iframe=1)
         Parse .iCIMS_JobListingRow hrefs → [(job_id, slug)]
    → 2. Fetch detail pages (GET /jobs/{id}/{slug}/job?in_iframe=1)
         Parse <script type="application/ld+json"> → JobPosting
         Fallback: HTML selectors if JSON-LD missing
    → 3. Persist to DB
         Upsert Posting by (company_id, external_job_id)
         INSERT PostingSnapshot (always, append-only)
```

## Target Sites (from product spec + live probing)

| Company | iCIMS Subdomain | Jobs/page | Est. total |
|---------|----------------|-----------|------------|
| MarketSource | `applyatmarketsource-msc.icims.com` | ~20 | ~380 |
| BDS Connected Solutions | `careers-bdssolutions.icims.com` | 50 | ~200 |

## Data Source: JSON-LD JobPosting Schema

Both sites embed `<script type="application/ld+json">` on detail pages with:
- `title` → `PostingSnapshot.title_raw`
- `description` (raw HTML) → `PostingSnapshot.full_text_raw`
- `jobLocation` → `PostingSnapshot.location_raw`
- `datePosted`, `validThrough` → metadata
- `baseSalary.minValue/maxValue` → metadata (BDS only)
- `employmentType` → metadata
- Job ID from URL → `Posting.external_job_id`
- Full URL → `PostingSnapshot.url`

## Data Flow & Persistence

1. **Paginate:** GET listing pages, extract job hrefs from `.iCIMS_JobListingRow`
2. **Fetch:** For each job, GET detail page via Semaphore(5) with 2-8s random delay
3. **Parse:** Extract JSON-LD `JobPosting`, fall back to HTML selectors
4. **Persist per job:**
   - SELECT Posting WHERE company_id + external_job_id
   - If not found → INSERT Posting (first_seen_at=now)
   - If found → UPDATE last_seen_at only
   - INSERT PostingSnapshot (always)
   - full_text_hash = SHA-256 of raw HTML description
   - content_changed = (hash != last snapshot's hash)
5. **Idempotency:** UNIQUE(posting_id, snapshot_date) with ON CONFLICT DO UPDATE

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Listing page failure | Return ScrapeResult with errors; orchestrator retries |
| Detail page failure (single job) | Log, skip job, continue |
| 3 consecutive detail failures | Circuit breaker trips, stop fetching, return partial result |
| HTTP 429/403 | Retriable; orchestrator backoff handles it |
| JSON-LD missing | HTML fallback selectors; if both fail, skip job |
| DB persistence failure (single job) | Log, skip, continue |

**Rate limiting:** Randomized 2-8s delay, configurable via `company.scraper_config`:
```json
{"delay_min": 2.0, "delay_max": 8.0, "max_concurrency": 5}
```

## Module Structure

**New files:**
- `src/compgraph/scrapers/icims.py` — ICIMSAdapter class
- `tests/test_icims_adapter.py` — Unit tests with mocked httpx

**Modified files:**
- `src/compgraph/scrapers/__init__.py` — Register adapter
- `pyproject.toml` — Add httpx + beautifulsoup4 deps

**Schema migration:**
- UNIQUE constraint on `posting_snapshots(posting_id, snapshot_date)`

## What This Issue Does NOT Do

| Deferred Item | Deferred To | Rationale |
|---|---|---|
| `is_active` management | #5 | Unsafe without scrape completeness tracking; needs 3-miss grace period + scrape_runs table (#32) |
| `scrape_runs` table | #32 | Schema addition serving #5, #12, #24; orthogonal to scraper logic |
| Fingerprint repost detection | #10 | Needs enrichment (#8/#9) for brand_slug; premature without real data |
| Posting count assertion | #12 | Needs baseline from 2+ completed runs + scrape_runs table |

## Testing Strategy

- Mock httpx responses with captured HTML fixtures
- Pagination: single page, multi-page, empty results
- JSON-LD parsing: valid, missing, malformed
- HTML fallback when JSON-LD absent
- Persistence: new posting, existing posting, content changed/unchanged
- Circuit breaker: 3 consecutive failures
- Idempotency: same job scraped twice same day
- No live HTTP calls in unit tests
