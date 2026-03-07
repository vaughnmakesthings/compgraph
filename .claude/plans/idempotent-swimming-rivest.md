# CompGraph Simplification Opportunities Audit

**Date:** 2026-03-07
**Scope:** Entire main branch — backend, frontend, tests
**Purpose:** Document simplification opportunities without implementing changes

---

## Summary

3 review agents audited the full codebase across 3 dimensions: code reuse, code quality, and efficiency. **25 findings** total, categorized by priority.

| Priority | Count | Estimated Lines Saved / Impact |
|----------|-------|-------------------------------|
| HIGH | 4 | ~200 lines saved, 150ms+ per-request savings |
| MEDIUM | 12 | ~100 lines saved, consistency improvements |
| LOW | 9 | Polish-level, minimal risk |

---

## HIGH Priority

### H1. N+1 Query in `get_posting()` — Sequential DB Queries
- **File:** `src/compgraph/services/posting_service.py:157-184`
- **Issue:** 4 sequential `await db.execute()` calls (posting, enrichment, snapshot, brand mentions) when 3 are independent
- **Fix:** `asyncio.gather()` the 3 independent queries after the initial posting fetch
- **Impact:** ~150ms saved per posting detail request (high-frequency endpoint)

### H2. Circuit Breaker Copy-Paste Across Scrapers
- **Files:** `src/compgraph/scrapers/icims.py`, `workday.py`, `jobsync.py`
- **Issue:** Identical circuit breaker state machine (~40 lines) duplicated in all 3 adapters: `_consecutive_failures`, `_circuit_open`, `_record_success()`, `_record_failure()`, `_check_circuit()`
- **Fix:** Extract `CircuitBreakerMixin` or utility class. Also move `CircuitBreakerOpen` exception to a shared module (currently defined locally in workday.py)
- **Impact:** ~120 lines eliminated, single source of truth for circuit breaker semantics

### H3. Enrichment Status Logic Duplication
- **File:** `src/compgraph/enrichment/orchestrator.py:88-114`
- **Issue:** `_update_status()` and `_compute_final_status()` implement near-identical status determination logic that could diverge
- **Fix:** Unify into a single `_compute_status(pass1_result, pass2_result)` method
- **Impact:** Eliminates risk of status logic divergence between passes

### H4. Sequential Aggregation Jobs
- **File:** `src/compgraph/aggregation/orchestrator.py:44-64`
- **Issue:** 7 independent aggregation jobs run sequentially in a `for` loop. Each `await job.run(session)` blocks the next
- **Fix:** `asyncio.gather()` with per-job sessions
- **Impact:** Aggregation time reduced from ~150-300s to ~50s (max single job duration)

---

## MEDIUM Priority

### M1. Aggregation Row Transformation Boilerplate
- **Files:** All 7 modules in `src/compgraph/aggregation/`
- **Issue:** Every `compute_rows()` repeats: `str(uuid.uuid4())` for IDs, `str(row.company_id)`, nullable UUID/float coercion (`str(x) if x is not None else None`)
- **Fix:** Create `safe_uuid_str()`, `safe_float()` helpers or a row transformation utility
- **Impact:** ~70 lines eliminated, consistent null handling

### M2. Inconsistent Status Enums
- **Files:** `enrichment/orchestrator.py:43-48`, `scrapers/orchestrator.py:27-48`, `db/models.py:108,134-137`
- **Issue:** 3+ separate enums with overlapping values (`PENDING`, `RUNNING`, `SUCCESS`/`COMPLETED`/`FAILED`). The `_STATUS_MAP` in `routes/enrich.py:23-28` maps `"completed"` to `EnrichmentStatus.SUCCESS` — a naming mismatch
- **Fix:** Create canonical `PipelineStatus` enum in a shared module

### M3. Stringly-Typed Status Values in API Routes
- **File:** `src/compgraph/api/routes/enrich.py:23-28, 111`
- **Issue:** Hardcoded string-to-enum maps and trigger method strings (`"run_pass1"`, `"run_pass2"`)
- **Fix:** Use enum `.value` for mapping; create an enum for trigger methods

### M4. Sequential Enrichment Saves for Deduped Postings
- **File:** `src/compgraph/enrichment/orchestrator.py:514-541`
- **Issue:** When content hash matches cache, each posting in the group is saved sequentially with separate sessions/commits
- **Fix:** `asyncio.gather()` the save operations
- **Impact:** ~10-20s saved per enrichment run

### M5. Correlated Subqueries in `search_postings()`
- **File:** `src/compgraph/dashboard/queries.py:285-368`
- **Issue:** Two correlated `string_agg()` subqueries (brands + retailers) per row — effectively N+2 queries
- **Fix:** Use `FILTER (WHERE entity_type = 'client_brand')` in a single joined aggregation
- **Impact:** ~50-100ms saved per dashboard page load

### M6. Parameter Sprawl in LLM Call Functions
- **Files:** `enrichment/retry.py:108-118`, `pass1.py:15-21`, `pass2.py:15-22`
- **Issue:** `call_llm_with_retry()` takes 8 parameters
- **Fix:** Create `LLMCallConfig` dataclass to bundle model, max_tokens, system_prompt, result_type

### M7. Scraper HTTP Client Initialization Duplication
- **Files:** `scrapers/icims.py`, `workday.py`, `jobsync.py`
- **Issue:** All 3 adapters repeat identical `httpx.AsyncClient` setup (headers, User-Agent, proxy kwargs, timeout, follow_redirects)
- **Fix:** Factory function `create_scraper_client(domain, timeout=30.0)`
- **Impact:** ~15-20 lines eliminated

### M8. Complex Nested Status Finalization
- **File:** `src/compgraph/enrichment/orchestrator.py:460-495`
- **Issue:** After `run_pass1()`, deeply nested conditionals handle shutdown/circuit-breaker/normal completion. `error_summary` gets overwritten multiple times
- **Fix:** Extract `_finalize_run(shutdown_interrupted, breaker_tripped)` method

### M9. Frontend Inline Color Hex Values
- **File:** `web/src/app/(app)/settings/page.tsx:56, 81, 210`
- **Issue:** Design token colors (`#8C2C23`, `#EF8354`, `#4F5D75`, etc.) inlined in multiple components
- **Fix:** Extract to `lib/constants.ts` or CSS variables

### M10. Frontend Type Safety Gaps — `any` Casts
- **File:** `web/src/app/(app)/settings/page.tsx:206, 316, 326`
- **Issue:** `eslint-disable @typescript-eslint/no-explicit-any` with `as any` casts on API response data
- **Fix:** Use generated API types (`ScrapeStatusResponse`, `EnrichStatusResponse`) instead

### M11. Frontend Filter State Could Use `useMemo`
- **File:** `web/src/app/(app)/hiring/page.tsx:115-120`
- **Issue:** `hasActiveFilters` is derived from 5 state variables but computed inline on every render
- **Fix:** Wrap in `useMemo` with proper deps

### M12. Triple-Nested JSX Map in Settings Page
- **File:** `web/src/app/(app)/settings/page.tsx:253-276`
- **Issue:** Pass result rendering has 3 levels of `.map()` with conditional rendering
- **Fix:** Extract `<PassResultDetail />` component

---

## LOW Priority

### L1. Cache-Control Header Repetition
- **File:** `src/compgraph/api/routes/aggregation.py:29-97`
- **Issue:** 7 identical GET endpoints all set `response.headers["Cache-Control"] = CACHE_CONTROL_5MIN`
- **Fix:** Decorator or middleware for cache headers

### L2. Dead Code — `CircuitBreaker.record_success()`
- **File:** `src/compgraph/enrichment/orchestrator.py:172-174`
- **Issue:** Method defined but never called; failures reset inline instead
- **Fix:** Remove or wire up properly

### L3. Magic Advisory Lock Key
- **File:** `src/compgraph/enrichment/orchestrator.py:123`
- **Issue:** Hardcoded integer with comment explaining derivation. Scraper module computes differently
- **Fix:** Standardize derivation approach; add verification test

### L4. Pipeline Totals Recomputed on Every Access
- **File:** `src/compgraph/scrapers/orchestrator.py:62-81`
- **Issue:** `@property` methods sum results on every call
- **Fix:** Cache after results are finalized

### L5. Query Result Iteration Inconsistency
- **Files:** Various aggregation modules
- **Issue:** Some use `.mappings().all()`, others iterate directly
- **Fix:** Standardize on one pattern

### L6. `datetime.now(UTC).date()` Repeated
- **Files:** `aggregation/brand_churn.py`, `agency_overlap.py`, `coverage_gaps.py`
- **Issue:** Same 1-liner in 3 files
- **Fix:** Utility function (minimal value)

### L7. Count Query Subquery Wrapper
- **File:** `src/compgraph/services/posting_service.py:92-128`
- **Issue:** Count wraps filtered result in subquery unnecessarily
- **Fix:** Direct `COUNT(*)` without subquery

### L8. Frontend Dropdown SVG Inlined 4 Times
- **File:** `web/src/app/(app)/hiring/page.tsx:171, 189, 204, 222`
- **Issue:** Same SVG data URI repeated for all select elements
- **Fix:** Extract to constant

### L9. Frontend Multi-Pass Velocity Loop
- **File:** `web/src/app/(app)/page.tsx:88-143`
- **Issue:** Velocity data iterated 4 separate times for different derived values
- **Fix:** Single-pass computation

---

## Implementation Strategy

**Batch 1 — Backend Performance (H1, H4, M4, M5):**
- All `asyncio.gather()` opportunities
- Highest ROI, minimal risk
- Assign: python-backend-developer agent

**Batch 2 — Scraper DRY (H2, M7):**
- Circuit breaker mixin + HTTP client factory
- Touches all 3 scraper files
- Assign: scraper-developer agent

**Batch 3 — Enrichment Quality (H3, M2, M3, M6, M8, L2):**
- Status enum consolidation + orchestrator cleanup
- All enrichment-related
- Assign: python-backend-developer agent

**Batch 4 — Aggregation DRY (M1, L1, L5, L6):**
- Row transformation helpers + consistency
- All aggregation-related
- Assign: python-backend-developer agent

**Batch 5 — Frontend Polish (M9, M10, M11, M12, L8, L9):**
- Type safety, component extraction, constants
- All web/ changes
- Assign: react-frontend-developer agent

**Review gates:** code-reviewer after each batch, pytest-validator for batches 1-4

---

## Sprint 9 Merge-Wave Plan

| Wave | Issue | Rationale |
|------|-------|-----------|
| 1 | Issue 1 (Performance) | No file overlap with others; highest ROI |
| 1 | Issue 5 (Frontend) | Zero overlap with backend issues; parallel-safe |
| 2 | Issue 2 (Scrapers) | Isolated to scrapers/; no enrichment overlap |
| 2 | Issue 4 (Aggregation) | Isolated to aggregation/; no scraper overlap |
| 3 | Issue 3 (Enrichment) | Touches orchestrator.py which may conflict with Issue 1's M4; must go last |

Waves 1+2 can run in parallel worktrees. Wave 3 after merge.

---

## Root Causes

| Root Cause | Findings | Prevention |
|------------|----------|------------|
| RC-1: No async concurrency convention | H1, H4, M4 | CLAUDE.md convention + agent definitions |
| RC-2: No shared abstraction mandate | H2, M7, M1 | CLAUDE.md convention + code-reviewer checklist |
| RC-3: Status enum proliferation | M2, M3, H3 | failure-patterns.md CQ-3 |
| RC-4: Frontend design token drift | M9, L8 | react-frontend-developer antipattern |
| RC-5: Type safety erosion | M10 | react-frontend-developer antipattern |
