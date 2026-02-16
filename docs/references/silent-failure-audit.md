# Silent Failure Audit

**Date**: 2026-02-16
**Scope**: Full pipeline — scrapers, enrichment, aggregation, API, dashboard, database, scheduling

## Summary

19 silent failure modes identified across 7 pipeline stages. The system has good foundations (logging, error isolation, retry logic) but lacks **observability** — no alerting, no scheduling, and no baseline deviation detection. The highest-risk failures are broken scrapers returning 0 results marked as success, no scheduling mechanism for automated runs, and missing data freshness indicators.

## Priority Matrix

| ID | Stage | Description | Risk | Existing Safeguard |
|----|-------|-------------|------|--------------------|
| **SCHED-7.1** | Scheduling | No automated scheduling — pipelines require manual trigger | **P0** | None |
| **AF-3.1** | Aggregation | Module is placeholder — tables exist but never populated | **P0** | None |
| **SF-1.1** | Scraper | Zero results look like success (status=COMPLETED, jobs_found=0) | **P0** | None |
| **API-4.1** | API | Health endpoint returns 200 OK without checking database | **P1** | None |
| **SF-1.4** | Scraper | No "last successful scrape" timestamp — stale data looks current | **P1** | None |
| **DASH-5.1** | Dashboard | Cached data shows no freshness timestamp | **P1** | None |
| **EF-2.4** | Enrichment | No pay value sanity checks — outliers pollute benchmarks | **P1** | None |
| **SF-1.5** | Scraper | HTTP redirects silently followed — could scrape error page | **P2** | None |
| **API-4.2** | API | Run history in-memory only — lost on restart | **P2** | None |
| **DB-6.3** | Database | PostingEnrichment.posting_id not unique — risk of double-counting | **P2** | None |
| **EF-2.1** | Enrichment | Valid JSON, wrong content — no ground truth validation | **P2** | None |
| **SF-1.2** | Scraper | Partial results after circuit breaker looks like full success | **P2** | Circuit breaker logs |
| **SF-1.3** | Scraper | Malformed data (empty title/location) passes no validation | **P2** | None |
| **EF-2.2** | Enrichment | Empty entity extraction indistinguishable from extraction failure | **P3** | enrichment_version tracking |
| **EF-2.7** | Enrichment | Fuzzy match 70-85% logged but no review queue | **P3** | INFO logging |
| **DASH-5.2** | Dashboard | Query exceptions show generic error, details only in server logs | **P3** | logger.exception() |
| **DASH-5.4** | Dashboard | Pool exhaustion visible in diagnostics but no threshold warning | **P3** | Diagnostics sidebar |
| **DB-6.4** | Database | Missing indexes on is_active, enrichment_version | **P3** | None |
| **API-4.4** | API | Control endpoint race conditions on in-memory state | **P3** | None (single-user) |

## Detailed Findings

### 1. Scrapers

**SF-1.1: Zero results look like success**
- `icims.py:363-366`: When `job_entries` is empty, logs INFO and returns success with `jobs_found=0`
- A broken scraper (DNS failure, 404, redirect) returning 0 results is indistinguishable from a legitimately empty job board
- Known example: 4 scrapers currently broken (Advantage 301, Acosta/BDS DNS dead, MarketSource 404) — all would show as "completed" with 0 postings
- Fix: Compare against 7-day rolling average. >50% drop = warning, >90% drop = error

**SF-1.2: Partial results after circuit breaker**
- `icims.py:369-373`: Circuit breaker trips after 3 consecutive failures, remaining jobs silently skipped
- Scraper returns 50% of postings, marked as success with errors in array
- Orchestrator logs it as success if ANY postings were created
- Fix: Include `expected_count` vs `actual_count` in ScrapeRun, flag deviations

**SF-1.3: Malformed data passes through**
- `icims.py:126-166`: HTML fallback parsing returns empty strings for missing fields
- Postings with `title=""` or `location=""` get persisted and enriched
- Fix: Add minimum field validation before persist (title required, non-empty)

**SF-1.4: No staleness indicator**
- Deactivation uses 3-run grace period. If scraper breaks for 2 runs, data is stale but postings remain "active"
- No `last_successful_scrape` timestamp on Company table
- Fix: Add `last_scraped_at` to companies table, surface in dashboard

**SF-1.5: HTTP redirects silently followed**
- Both scrapers use `follow_redirects=True`. A 301 to an error page that returns 200 would be parsed as "0 jobs found"
- Known issue: Advantage redirects to `careers.youradv.com`
- Fix: Validate final response URL domain matches expected ATS domain

**Existing scraper safeguards**: Circuit breaker (3 failures), per-company isolation, 3-attempt retry with backoff, ScrapeRun persistence

### 2. Enrichment Pipeline

**EF-2.1: Valid JSON, wrong content (hallucination)**
- Haiku/Sonnet return valid JSON passing Pydantic validation but with incorrect classifications
- Example: `role_archetype="Ambassador"` for warehouse worker, or brand entities not in source text
- Documented in failure-patterns.md (EF-1, EF-2) but not yet observed
- Fix: Confidence thresholds, source-text verification for entity extraction

**EF-2.2: Empty entity extraction ambiguity**
- Pass 2 extracting zero entities is legitimate (not all postings mention brands)
- Cannot distinguish "no entities found" from "extraction failed to run properly"
- Mitigated by `enrichment_version` containing "pass2" regardless of entity count
- Fix: Add `entities_attempted: true` flag or count to distinguish outcomes

**EF-2.4: Pay extraction outliers**
- LLM extracts "$1M" from "manage $1M budget" as compensation
- No sanity checks: pay_min > pay_max accepted, $500/hr hourly rate accepted
- Documented in failure-patterns.md (EF-4) but no mitigation implemented
- Fix: Range validation (hourly: $5-$200, annual: $15K-$500K), min <= max check

**EF-2.7: Fuzzy match ambiguity**
- `resolver.py:74-79`: Matches between 70-85% logged at INFO as "accepted but flagged for review"
- No review queue, no confidence score persisted in PostingBrandMention
- Fix: Add `match_confidence` column to PostingBrandMention, review queue for <85%

**Existing enrichment safeguards**: `exclude_ids` prevents livelock, per-posting isolation, 3-attempt retry for rate limits, EnrichmentRun status tracking, markdown fence stripping (PR #62)

### 3. Aggregation

**AF-3.1: Module is placeholder**
- `src/compgraph/aggregation/__init__.py` is empty (1 line)
- 4 aggregation tables defined in models but never populated
- Dashboard or API queries against these tables would return empty results with no error
- Fix: M4 milestone — implement aggregation pipeline with completeness checks

### 4. API Layer

**API-4.1: Health endpoint doesn't check DB**
- `health.py:6-8`: Returns `{"status": "ok"}` unconditionally — no database ping
- External monitoring (Uptime Robot, etc.) would see 200 OK even when DB is unreachable
- Fix: Add `SELECT 1` ping, return `{"status": "degraded", "database": "error: ..."}` on failure

**API-4.2: In-memory run history**
- `scrape.py`: `_pipeline_runs` dict holds last 10 runs in memory
- All history lost on server restart — no audit trail
- EnrichmentRun similarly in-memory only
- Fix: Persist to database (mirror ScrapeRun pattern for enrichment)

**API-4.4: Control endpoint race conditions**
- Pause/resume/stop modify in-memory PipelineRun state without locking
- Low risk — single-user system, but could cause issues if dashboard sends rapid requests
- Fix: Add simple lock or compare-and-swap on state transitions

### 5. Dashboard

**DASH-5.1: No data freshness indicator**
- `@st.cache_data(ttl=60)` caches for 60 seconds — user sees data up to 1 minute stale
- No "as of {timestamp}" on any metric
- Fix: Add `last_scrape` / `last_enrichment` timestamps to every page header

**DASH-5.2: Generic error messages**
- `main.py:42-45`: `except Exception: st.error("Failed to load ...")` — logs full trace but user sees only generic message
- Fix: Show error category (connection, timeout, query) to help user self-diagnose

**DASH-5.4: Pool exhaustion not flagged**
- Diagnostics sidebar shows pool stats but no threshold warnings
- Pool 5/5 checked out = problem, but sidebar doesn't color-code or warn
- Fix: Add threshold coloring (>80% = yellow, 100% = red)

### 6. Database

**DB-6.3: PostingEnrichment not unique on posting_id**
- Multiple enrichment records per posting is intentional (versioning), but queries must handle it
- Aggregation queries that don't use DISTINCT or latest-only logic will double-count
- Fix: Add `ix_enrichment_latest` partial index or view for "latest enrichment per posting"

**DB-6.4: Missing query-performance indexes**
- No index on `Posting.is_active` (filtered on every dashboard query)
- No index on `PostingEnrichment.enrichment_version` (Pass 2 detection query)
- Fix: Add composite indexes for common query patterns

### 7. Scheduling

**SCHED-7.1: No automated scheduling**
- Pipelines only run when manually triggered via API or dashboard
- If no one triggers a scrape, data silently goes stale — no missed-run detection
- Fix: Implement scheduler (APScheduler, Celery Beat, or systemd timer) with missed-run alerts

## New Patterns Not in failure-patterns.md

These 9 patterns should be added to `docs/failure-patterns.md`:

1. SF-1.1 — Zero results without error (scraper)
2. SF-1.4 — Stale data without refresh indicator (scraper)
3. SF-1.5 — HTTP redirect without detection (scraper)
4. EF-2.2 — Empty entity extraction ambiguity (enrichment)
5. API-4.1 — Health endpoint no DB check (API)
6. API-4.2 — In-memory run history loss (API)
7. DASH-5.1 — Stale cached data (dashboard)
8. DB-6.3 — PostingEnrichment.posting_id not unique (database)
9. SCHED-7.1 — No scheduling mechanism (scheduling)

## Recommended Implementation Order

**When ready to address these**, the suggested sequence is:

1. **Health endpoint enhancement** (API-4.1) — smallest change, biggest monitoring impact
2. **Data freshness timestamps** (DASH-5.1, SF-1.4) — user-facing visibility
3. **Zero-result baseline alerts** (SF-1.1) — catches broken scrapers
4. **Pay value validation** (EF-2.4) — data quality guard
5. **Scheduling** (SCHED-7.1) — eliminates manual dependency
6. **Persistent run history** (API-4.2) — audit trail
7. **Remaining items** — indexes, redirect detection, race conditions
