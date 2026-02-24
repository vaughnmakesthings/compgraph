# CompGraph Code Review & Insights Log

This log tracks architectural improvements, security hardening, and performance optimizations identified during the CompGraph swarm reviews.

## Summary Table

*PM disposition added 2026-02-24. See `gap-analysis-consolidated.md` Section 10 and `strategic-roadmap-refined.md` Section 7 for full rationale.*

| ID | Domain | Severity | Status | Issue | Target |
|:---|:---|:---|:---|:---|:---|
| CG-ARCH-001 | Architecture | 🔴 CRITICAL | OPEN | Route-to-DB coupling (no Service Layer) | M7 S2 |
| CG-PERF-001 | Performance | 🟠 HIGH | OPEN | Sequential API data fetching (N+1 queries) | M7/M8 |
| CG-RELI-001 | Reliability | 🟠 HIGH | OPEN | Fragile in-memory run tracking (_runs dicts) | M7 S1 |
| CG-PERF-002 | Performance | 🟠 HIGH | DEFER | Sequential Aggregation Job execution | M8 |
| CG-OBS-001 | Observability | 🟡 MEDIUM | OPEN | Hybrid state fragmentation (Memory vs DB) | M7 S1 |
| CG-SEC-001 | Security | 🟡 MEDIUM | **RESOLVED** | Missing explicit SSL enforcement in Alembic | — |
| CG-SCALE-001| Scaling | 🔵 LOW | OPEN | Hardcoded scraper tuning parameters | M8 |
| CG-QUAL-001 | Quality | 🔵 LOW | OPEN | Timezone-naive datetime in preflight.py | M7 |
| CG-UX-184   | UX | 🟡 MEDIUM | OPEN | Missing ConfirmDialog for destructive actions (#184) | M7 |
| CG-DATA-070 | Data | 🟠 HIGH | **RESOLVED** | Double-counting in multiple enrichments (#70) | — |
| CG-SEC-059  | Security | 🟠 HIGH | OPEN | Lack of Auth on scrape control endpoints (#59) | M7 S1 |
| CG-PERF-089 | Performance| 🟡 MEDIUM | OPEN | Individual DB updates for counters (#89) | M7/M8 |
| CG-UX-001   | UX | 🔴 CRITICAL | OPEN | Missing Evidence Trails for trust | M7 |
| CG-RELI-002 | Reliability | 🟠 HIGH | **RESOLVED** | Silent Scraper Failures (Zero results) | — |
| CG-RELI-003 | Reliability | 🟠 HIGH | OPEN | Blind HTTP Redirect following in Scrapers | M7/M8 |
| CG-DATA-001 | Data | 🟠 HIGH | **RESOLVED** | Brand Deduplication (Reliant/LG/Virgin) | — |
| CG-OBS-002  | Observability | 🟡 MEDIUM | **RESOLVED** | Shallow Health Endpoint (no DB/Scheduler check) | — |
| CG-RELI-004 | Reliability | 🟡 MEDIUM | PARTIAL | Missing Pay Value Sanity Checks (bounds needed) | M7 |
| CG-PERF-003 | Performance | 🟡 MEDIUM | **N/A** | Incorrect SQL Aggregate Ordering (raw SQL, not ORM) | — |
| CG-SCALE-002| Scaling | 🔵 LOW | OPEN | Missing Anthropic Batch API integration | M8 |

---

## Detailed Findings

## CG-ARCH-001 — Route-to-DB Coupling
...
## CG-PERF-089 — Individual DB updates for counters
...
## CG-UX-001 — Missing Evidence Trails for Trust
- **Domain:** UX | **Severity:** 🔴 CRITICAL | **Status:** OPEN
- **Context:** `docs/COMPGRAPH_PROJECT_CONTEXT.md` §4
- **Issue:** Every inferred brand/retailer relationship MUST show evidence count, recency, and a clickable source trail to support leadership-level decisions.
- **Actionable Solution:**
  1. Audit `Opportunity Finder` and `Brand Intelligence` views.
  2. Implement `EvidenceBadge` and `SourcePostingLink` components.
  3. Ensure backend `brand_mentions` API provides the necessary metadata.
- **Target Milestone:** M7 | **Effort:** Medium

## CG-RELI-002 — Silent Scraper Failures (Zero Results)
- **Domain:** Reliability | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `docs/references/silent-failure-audit.md` SF-1.1
- **Issue:** Broken scrapers returning 0 results are currently marked as `SUCCESS`, causing data to go stale silently.
- **Actionable Solution:**
  1. Implement `check_baseline_anomaly` in `PipelineOrchestrator`.
  2. Compare job count to 7-day rolling average.
  3. Raise `WARNING` if >50% drop, `ERROR` if >90%.
- **Target Milestone:** M4 | **Effort:** Small

## CG-RELI-003 — Blind HTTP Redirect following in Scrapers
- **Domain:** Reliability | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `docs/references/silent-failure-audit.md` SF-1.5
- **Issue:** Scrapers follow redirects (301/302) blindly, potentially parsing error pages as empty successful scrapes.
- **Actionable Solution:**
  1. Add `_validate_redirect()` helper to `ICIMSFetcher`.
  2. Verify final response URL domain matches the expected ATS domain.
- **Target Milestone:** M4 | **Effort:** Small

## CG-DATA-001 — Brand Deduplication (Reliant/LG/Virgin)
- **Domain:** Data Integrity | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `docs/plans/2026-02-22-data-quality-aggregation-design.md` §4
- **Issue:** Duplicate brand entries (e.g., "LG" vs "LG Electronics") split timelines and inflate counts.
- **Actionable Solution:**
  1. Run `scripts/dedup_brands.py` to reparent mentions and delete duplicates.
  2. Update `entity_resolution` thresholds to prevent re-creation.
- **Target Milestone:** M4 | **Effort:** Small

## CG-OBS-002 — Shallow Health Endpoint
- **Domain:** Observability | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `docs/references/silent-failure-audit.md` API-4.1
- **Issue:** `/health` endpoint returns 200 OK even if the database is disconnected or the scheduler is dead.
- **Actionable Solution:**
  1. Add a database `SELECT 1` ping to the health check.
  2. Add APScheduler status check to the response body.
- **Target Milestone:** M4 | **Effort:** Small

## CG-RELI-004 — Missing Pay Value Sanity Checks
- **Domain:** Reliability | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `docs/references/silent-failure-audit.md` EF-2.4
- **Issue:** LLM can extract non-pay dollar amounts (e.g., "$1M budget") as compensation, polluting benchmarks.
- **Actionable Solution:**
  1. Add range validation to `PostingEnrichment` ($10-$150/hr, $20K-$300K/yr).
  2. Add `check_pay_range` constraint (min <= max).
- **Target Milestone:** M4 | **Effort:** Small

## CG-PERF-003 — Incorrect SQL Aggregate Ordering
- **Domain:** Performance | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `docs/context-packs.md` Pack C
- **Issue:** Aggregation queries using `string_agg` with `.order_by()` on the outer query produce non-deterministic results.
- **Actionable Solution:**
  1. Refactor all `string_agg` usages to use `aggregate_order_by()` from `sqlalchemy.dialects.postgresql`.
- **Target Milestone:** M4 | **Effort:** Trivial

## CG-SCALE-002 — Missing Anthropic Batch API integration
- **Domain:** Scaling | **Severity:** 🔵 LOW | **Status:** OPEN
- **Context:** `docs/references/llm-extraction-optimization.md` §5
- **Issue:** Non-urgent enrichment calls are made synchronously, missing the 50% "Batch API" discount.
- **Actionable Solution:**
  1. Refactor `EnrichmentOrchestrator` to support batch submission for daily runs.
- **Target Milestone:** M6 | **Effort:** Medium
...
## CG-UX-184 — Missing ConfirmDialog for Destructive Actions
- **Domain:** UX | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `web/src/components/ui/confirm-dialog.tsx` (Issue #184)
- **Issue:** Destructive actions (truncate tables, stop scrape) and LLM-costing actions (trigger enrichment) lack a confirmation gate.
- **Actionable Solution:**
  1. Implement a shared `ConfirmDialog` component using `@tremor/react`.
  2. Wrap all destructive buttons in `settings/page.tsx` and `eval/runs/page.tsx`.
- **Target Milestone:** M4 | **Effort:** Small

## CG-DATA-070 — Double-counting in multiple enrichments
- **Domain:** Data Integrity | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `docs/failure-patterns.md` -> DB-1 (Issue #70)
- **Issue:** Multiple enrichment versions per posting cause double-counting in dashboard metrics if not joined via the "latest" version.
- **Actionable Solution:**
  1. Create a `latest_enrichment` view or a standard CTE query pattern.
  2. Audit all aggregation jobs to ensure they join using the versioned latest record.
- **Target Milestone:** M4 | **Effort:** Small

## CG-SEC-059 — Lack of Auth on scrape control endpoints
- **Domain:** Security | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `src/compgraph/api/routes/scrape.py` (Issue #59)
- **Issue:** Scrape control endpoints (/trigger, /stop, etc.) are unauthenticated, allowing any client to disrupt pipeline runs.
- **Actionable Solution:**
  1. Integrate Supabase Auth middleware for all `/api/scrape/` and `/api/pipeline/` routes.
  2. Restrict trigger/stop actions to the `admin` role.
- **Target Milestone:** M4 | **Effort:** Medium

## CG-PERF-089 — Individual DB updates for counters
- **Domain:** Performance | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `src/compgraph/enrichment/orchestrator.py:L305-L313` (Issue #89)
- **Issue:** `increment_enrichment_counter` is called once per posting, creating excessive roundtrips for large batches.
- **Actionable Solution:**
  1. Collect success/failure counts at the batch level.
  2. Update the run record once per batch completion instead of once per item.
- **Target Milestone:** M4 | **Effort:** Small
- **Domain:** Architecture | **Severity:** 🔴 CRITICAL | **Status:** OPEN
- **Context:** `src/compgraph/api/routes/postings.py` (and all route files)
- **Issue:** Route handlers directly construct and execute complex SQLAlchemy queries, bypassing any abstraction layer.
- **Actionable Solution:**
  1. Create `src/compgraph/services/posting_service.py`.
  2. Encapsulate query building logic (filters, joins, subqueries) in service methods.
  3. Use FastAPI `Depends` to inject the service into routes.
- **Target Milestone:** M4 | **Effort:** Medium

## CG-PERF-001 — Sequential API Data Fetching
- **Domain:** Performance | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `src/compgraph/api/routes/postings.py:L227-L250`
- **Issue:** `GET /api/postings/{id}` performs 4 sequential DB queries to fetch a single detail view.
- **Actionable Solution:**
  1. Define missing relationships in `models.py` (latest_enrichment, brand_mentions).
  2. Refactor service layer to use `selectinload()` or `joinedload()` for a single-trip fetch.
- **Target Milestone:** M4 | **Effort:** Small

## CG-RELI-001 — Fragile In-Memory Run Tracking
- **Domain:** Reliability | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `src/compgraph/scrapers/orchestrator.py` & `src/compgraph/enrichment/orchestrator.py`
- **Issue:** Active run states are stored in global `_runs` dicts, which are lost on server restart.
- **Actionable Solution:**
  1. Eliminate in-memory tracking in orchestrators.
  2. Use DB tables (`scrape_runs`, `enrichment_runs`) as the exclusive source of truth.
  3. Implement a DB-backed heartbeat to detect and clean up "zombie" runs after restarts.
- **Target Milestone:** M4 | **Effort:** Medium

## CG-PERF-002 — Sequential Aggregation Job Execution
- **Domain:** Performance | **Severity:** 🟠 HIGH | **Status:** OPEN
- **Context:** `src/compgraph/aggregation/orchestrator.py`
- **Issue:** Aggregation jobs run one-by-one, leading to excessive nightly maintenance windows as data grows.
- **Actionable Solution:**
  1. Refactor `AggregationOrchestrator.run()` to use `asyncio.gather()`.
  2. Implement an `asyncio.Semaphore` (limit=3) to manage DB connection pressure.
- **Target Milestone:** M4 | **Effort:** Small

## CG-OBS-001 — Hybrid State Fragmentation
- **Domain:** Observability | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `src/compgraph/api/routes/pipeline.py`
- **Issue:** `/status` endpoint stitches state from both memory and DB, leading to inconsistent UI feedback.
- **Actionable Solution:**
  1. Refactor `/status` to query the database exclusively.
  2. Standardize enums between DB and logic layers.
- **Target Milestone:** M4 | **Effort:** Small

## CG-SEC-001 — Missing Explicit SSL Enforcement in Alembic
- **Domain:** Security | **Severity:** 🟡 MEDIUM | **Status:** OPEN
- **Context:** `alembic/env.py`
- **Issue:** Migration engine relies on `.env` strings for SSL, risking unencrypted connections if misconfigured.
- **Actionable Solution:**
  1. Hardcode `connect_args={"ssl": "require"}` in the `create_async_engine` call within `run_async_migrations()`.
- **Target Milestone:** M4 | **Effort:** Trivial

## CG-SCALE-001 — Hardcoded Scraper Tuning Parameters
- **Domain:** Scaling | **Severity:** 🔵 LOW | **Status:** OPEN
- **Context:** `src/compgraph/scrapers/workday.py`, `icims.py`
- **Issue:** Concurrency and page sizes are hardcoded module constants.
- **Actionable Solution:**
  1. Move `DETAIL_CONCURRENCY` and `PAGE_SIZE` to `Settings` in `config.py`.
  2. Allow environment-specific overrides via `.env`.
- **Target Milestone:** M6 | **Effort:** Small

## CG-QUAL-001 — Timezone-Naive Datetime usage
- **Domain:** Quality | **Severity:** 🔵 LOW | **Status:** OPEN
- **Context:** `src/compgraph/preflight.py:L1005`
- **Issue:** Usage of naive `datetime.now()` violates the project rule of "timezone-aware everywhere".
- **Actionable Solution:**
  1. Replace `datetime.now()` with `datetime.now(UTC)`.
- **Target Milestone:** M4 | **Effort:** Trivial
