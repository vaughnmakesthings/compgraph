# Failure Pattern Catalog

Observed and anticipated failure modes from pipeline development, E2E runs, and architecture analysis. Add new patterns as they're discovered. Each entry has: trigger, symptoms, blast radius, and mitigation status.

---

## Scraper Failures

### SF-1: iCIMS Portal Structure Variation

**Trigger**: iCIMS portals are configured differently per company. Page sizes vary (BDS=50, MarketSource=20). Available metadata fields differ. Companies can run Classic (server-rendered) or Modern Career Sites (React SPA) — the latter requires Playwright, not plain HTTP.

**Blast radius**: One company's scraper fails silently — returns 0 or partial postings. Other companies unaffected (per-company isolation).

**Symptoms**: Empty `posting_snapshots` for a specific company on a given day. Or unusually low count compared to prior days.

**Mitigation**: Use JSON-LD extraction (survives redesigns) over CSS selectors. Parse "Page X of Y" dynamically — never hardcode page size. Detect portal type on first scrape. Add assertion: if today's count is <50% of yesterday's, flag as potential failure. See `docs/references/icims-scraping.md` §1, §5.

**Status**: Anticipated, not yet observed.

---

### SF-1b: iCIMS Portal Decommissioning

**Trigger**: A target company migrates from iCIMS Classic to Modern Career Sites, BrassRing, or another ATS without notice. MarketSource (`applyatmarketsource-msc.icims.com`) may already be decommissioned — conflicting reports (Feb 2026).

**Blast radius**: Entire company's data collection stops. HTTP 410 (Gone) on all pages. No fallback without discovering the new URL.

**Symptoms**: All detail page fetches return 410. Search pages return empty or redirect. `posting_snapshots` drops to 0 for that company.

**Mitigation**: Monitor for HTTP 410 responses — iCIMS returns 410 (not 404) for expired/decommissioned content. Maintain alternative URL candidates per company. Alert on 0-posting days. Verify MarketSource portal status before building adapter. See `docs/references/icims-scraping.md` §5.

**Status**: Anticipated. MarketSource status conflicting — **verify before implementation.** See `docs/references/icims-scraping.md` → UC-3 for validation steps.

---

### SF-2: Workday CXS API Schema Change

**Trigger**: Workday updates their CXS API response format (field names, pagination, nesting).

**Blast radius**: 2020 Companies scraper breaks entirely. Returns malformed data or errors.

**Symptoms**: JSON parse errors, missing expected fields, empty results despite postings existing on the site.

**Mitigation**: Schema validation on CXS response before processing. Compare response structure against expected shape. Alert on structural changes.

**Status**: Anticipated, not yet observed.

---

### SF-3: Rate Limiting / IP Block

**Trigger**: Too many requests too fast, or residential proxy flagged.

**Blast radius**: Per-company. Proxy rotation should isolate companies from each other.

**Symptoms**: 429 responses, 403 blocks, CAPTCHAs, empty responses.

**Mitigation**: Randomized delays (2-8s), proxy rotation, user-agent rotation, 2-hour scrape window. Retry with backoff (3 attempts). Skip company after 3 consecutive failures.

**Status**: Anticipated, not yet observed.

---

## Enrichment Failures

### EF-1: Haiku Section Misclassification

**Trigger**: Pass 1 (Haiku) incorrectly classifies boilerplate as role-specific content, or vice versa.

**Blast radius**: Moderate. Downstream entity extraction (Pass 2) gets noisy input. Pay data extraction may capture boilerplate numbers. Role archetype may be wrong.

**Symptoms**: `content_boilerplate` contains job-specific details. `content_role_specific` contains EEO language or company description.

**Mitigation**: Include clear examples in the system prompt. Add `reasoning` field before classification fields. Post-enrichment spot checks.

**Status**: Anticipated, not yet observed.

---

### EF-2: Entity Extraction Hallucination

**Trigger**: Pass 2 (Sonnet) extracts brand/retailer names not present in the text, or misclassifies entity type.

**Blast radius**: `posting_brand_mentions` contains phantom entities. Brand/retailer tables grow with incorrect entries. Aggregation tables show false relationships.

**Symptoms**: Brands appearing in `agg_brand_timeline` that don't match any real relationship. Confidence scores may be low but still above threshold.

**Mitigation**: System prompt: "Only extract entities that appear verbatim in the text." Confidence threshold for entity creation (e.g., >0.7 for auto-create, 0.4-0.7 for manual review, <0.4 discard). Spot checks during data collection period.

**Status**: Anticipated, not yet observed.

---

### EF-3: Structured Output Validation Failure

**Trigger**: Anthropic SDK's `messages.parse()` returns data that violates Pydantic constraints (`ge`/`le` validators, enum values).

**Blast radius**: Per-posting. One enrichment fails, others continue.

**Symptoms**: `ValidationError` on Pydantic model. Known SDK behavior: constraints in field descriptions are hints, not enforced by grammar.

**Mitigation**: Catch `ValidationError`, retry once (LLM non-determinism may fix). After 2 failures, skip posting and log for manual review. Use `Literal` types for enum fields (more reliable than `ge`/`le`).

**Status**: Anticipated. Known Anthropic SDK behavior documented in their GitHub issues.

---

### EF-4: Pay Data Extraction Noise

**Trigger**: Postings mention dollar amounts in non-compensation context (e.g., "manage $1M budget", "save customers $500").

**Blast radius**: `pay_min`/`pay_max` contain wrong values. `agg_pay_benchmarks` skewed.

**Symptoms**: Outlier pay values. `pay_min` > `pay_max`. Unreasonable hourly rates (e.g., $1000/hr).

**Mitigation**: Constrain extraction to compensation section only (after Pass 1 segmentation). Add sanity checks: hourly $8-$100, salary $20K-$300K. Flag outliers for manual review.

**Status**: Anticipated, not yet observed.

---

## Aggregation Failures

### AF-1: Stale Aggregation After Partial Enrichment

**Trigger**: Enrichment processes only 60% of postings (some failed). Aggregation runs on incomplete data.

**Blast radius**: Dashboard shows artificially low numbers. `agg_daily_velocity` undercounts.

**Symptoms**: Sudden drop in active postings that doesn't match reality. Drop correlates with enrichment failure logs.

**Mitigation**: Track enrichment completion rate. If <90% processed, flag aggregation as "partial" — still run but annotate. Display data quality indicator in API responses.

**Status**: Anticipated, not yet observed.

---

## Pipeline Failures

### PF-1: Supabase Connection Pool Exhaustion

**Trigger**: Too many concurrent database connections from parallel scraper/enrichment tasks.

**Blast radius**: All pipeline stages fail. Connection timeouts cascade.

**Symptoms**: `asyncpg.exceptions.TooManyConnectionsError`, connection timeouts, "remaining connection slots are reserved" errors.

**Mitigation**: SQLAlchemy pool config: `pool_size=15, max_overflow=10, pool_recycle=300, pool_pre_ping=True`. Supabase Pro (Micro compute): **60 direct connections**, **200 pooler connections**. Budget: Alembic=NullPool (1), app=25, background jobs=share app pool. Avoid `NullPool` for app traffic (26x latency penalty). See `docs/references/supabase-alembic-migrations.md` §3.

**Status**: Anticipated, not yet observed.

---

### PF-1a: Database Password Breaks URL Parsing

**Trigger**: Supabase-generated passwords containing `@`, `/`, `#`, or `?` characters embedded directly in a `postgresql+asyncpg://user:pass@host` connection string.

**Blast radius**: All database connections fail. SQLAlchemy parses the `@` in the password as the user:password@host delimiter, producing a malformed hostname.

**Symptoms**: `socket.gaierror` with a hostname containing password fragments (e.g., host becomes `cek3wvf-vtm@aws-0-...`). URL parsing silently succeeds but produces wrong components.

**Mitigation**: Store password in a separate `DATABASE_PASSWORD` env var. Construct URLs in `config.py` using `urllib.parse.quote_plus()`. Never embed raw passwords in URLs.

**Status**: **Observed and fixed.** Hit during initial setup (Feb 12 2026). Fixed by separating `DATABASE_PASSWORD` from URL construction in `config.py`.

---

### PF-1b: Supabase Direct Connection IPv6-Only Resolution

**Trigger**: Using `db.[PROJECT].supabase.co` (direct connection) on a network without IPv6 support.

**Blast radius**: All direct connections fail — Alembic migrations, any code using `DATABASE_URL_DIRECT`.

**Symptoms**: `socket.gaierror: [Errno 8] nodename nor servname provided, or not known`. DNS resolves but asyncpg can't connect.

**Mitigation**: Use session mode pooler (`aws-0-[REGION].pooler.supabase.com:5432`) for all connections. Session mode is asyncpg-safe (unlike transaction mode on port 6543). Direct URL is only needed if you require IPv6-only features or have IPv6 network support.

**Status**: **Observed.** Hit during initial setup (Feb 12 2026). Resolved by using pooler for both app and Alembic.

---

### PF-2: Supavisor Transaction Mode Breaks asyncpg

**Trigger**: Using Supabase's default pooled connection (port 6543, transaction mode) with asyncpg.

**Blast radius**: All database operations fail with cryptic errors. Both app and migration paths affected.

**Symptoms**: `DuplicatePreparedStatementError`, prepared statement cache errors. Logs show errors on connection reuse.

**Mitigation**: Use two connection strings: `DATABASE_URL` (session mode pooler, port 5432) for app, `DATABASE_URL_DIRECT` (direct, port 5432 on `db.[PROJECT].supabase.co`) for Alembic. Never use port 6543 with asyncpg. See `docs/references/supabase-alembic-migrations.md` §1.

**Status**: Anticipated. Documented in Supabase GitHub issues #35684, #39227.

---

### PF-3: Alembic Autogenerate Touches Supabase-Managed Schemas

**Trigger**: Running `alembic revision --autogenerate` without schema filtering. Alembic detects `auth`, `storage`, `realtime`, `extensions` schemas and generates migrations for them.

**Blast radius**: Critical. Generated migrations change object ownership from Supabase service accounts. After applying, those schemas become permanently inaccessible (April 2025 lockout).

**Symptoms**: Migration file contains `CREATE TABLE auth.*`, `ALTER TABLE storage.*`, or similar. After running, Supabase dashboard shows permission errors on auth/storage features.

**Mitigation**: Add `include_name` filter to `alembic/env.py` — only manage `public` schema. Currently missing from our env.py. See `docs/references/supabase-alembic-migrations.md` §2.

**Status**: **Mitigated.** `include_name` filter added to `alembic/env.py`. PreToolUse hook in `.claude/settings.json` blocks `--autogenerate` if filter is ever removed. Documented in Supabase GitHub discussion #34270 (100+ comments).

---

### SF-4: Zero Results Without Error

**Trigger**: Scraper target returns HTTP 200 but with empty job listings (error page, redesigned portal, empty search results). Scraper logs INFO and returns `jobs_found=0` with `status=COMPLETED`.

**Blast radius**: Entire company's data collection silently stops. Existing postings never deactivated (grace period prevents it for 2 runs). Dashboard shows stale data as current.

**Symptoms**: `ScrapeRun` with `status=COMPLETED, jobs_found=0`. No errors logged. Indistinguishable from a legitimately empty job board.

**Mitigation**: Compare result count against 7-day rolling average. >50% drop = WARNING, >90% drop = ERROR. Add `expected_count` field to `ScrapeRun` for baseline tracking. Alert on 0-result completions for companies with historical postings.

**Status**: Anticipated. Currently observable with 4 broken scrapers (Advantage 301, Acosta/BDS DNS dead, MarketSource 404) — all would report as "completed" with 0 postings.

---

### SF-5: Stale Data Without Refresh Indicator

**Trigger**: Scraper fails for multiple runs but deactivation grace period (3 runs) hasn't elapsed. Or scraper simply hasn't been triggered (no scheduling). Active postings remain marked `is_active=True` indefinitely.

**Blast radius**: Dashboard shows outdated posting counts as current. Users make decisions on stale data.

**Symptoms**: No visible symptom — data looks current. Only discoverable by checking `last ScrapeRun.started_at` per company.

**Mitigation**: Add `last_scraped_at` timestamp to `companies` table, update on each successful scrape. Surface in dashboard header as "Data as of: {timestamp}". Warn if >24h stale.

**Status**: Anticipated, not yet observed.

---

### SF-6: HTTP Redirect Without Detection

**Trigger**: Target ATS URL returns 301/302 redirect. Both scrapers use `follow_redirects=True`, so redirect is silently followed. Final page may be an error page, login page, or different site entirely that returns HTTP 200.

**Blast radius**: Per-company. Scraper parses wrong page, finds 0 jobs, returns success.

**Symptoms**: `jobs_found=0` with no errors. Only discoverable by inspecting redirect chain or comparing final URL to expected domain.

**Mitigation**: After HTTP response, validate that final URL domain matches expected ATS domain. Log WARNING if redirect detected. Block scraping if final domain doesn't match.

**Status**: Anticipated. Known example: Advantage Solutions redirects from original URL to `careers.youradv.com`.

---

## Enrichment Failures (continued)

### EF-5: Empty Entity Extraction Ambiguity

**Trigger**: Pass 2 extracts zero entities from a posting. This is a legitimate outcome (not all postings mention brands), but it's indistinguishable from an extraction that silently failed to find real entities.

**Blast radius**: Low per-posting. At scale, systematic misses would mean brand analytics undercount relationships.

**Symptoms**: `PostingBrandMention` has no rows for posting. `enrichment_version` contains "pass2" (extraction ran, just found nothing). No error logged.

**Mitigation**: Add `entities_attempted` boolean or `entity_count` to `PostingEnrichment` to distinguish "ran and found nothing" from "didn't run." Periodic spot-check: sample postings with 0 entities, verify manually that no brands appear in text.

**Status**: Anticipated, not yet observed.

---

## API Failures

### API-1: Health Endpoint Does Not Check Database

**Trigger**: `/health` endpoint returns `{"status": "ok"}` without performing any database connectivity check.

**Blast radius**: External uptime monitors (Uptime Robot, Pingdom, etc.) see 200 OK even when database is unreachable. False positive on health status.

**Symptoms**: Health check passes while all data-serving endpoints fail with connection errors.

**Mitigation**: Add `SELECT 1` database ping to health endpoint. Return `{"status": "degraded", "database": "error: ..."}` on failure with HTTP 503. Keep response fast (<500ms timeout on DB check).

**Status**: Anticipated. Current health endpoint at `src/compgraph/api/routes/health.py` has no DB check.

---

### API-2: In-Memory Run History Lost on Restart

**Trigger**: Server restart (deployment, crash, systemd restart). `_pipeline_runs` dict in `scrape.py` and `EnrichmentRun` objects are stored in process memory only.

**Blast radius**: All pipeline run history lost. `/api/scrape/status` returns 404 for previously tracked runs. No audit trail of past runs.

**Symptoms**: After restart, status endpoints show no history. Users cannot review outcomes of recent pipeline executions.

**Mitigation**: Persist `EnrichmentRun` to database (mirror existing `ScrapeRun` pattern which is already DB-persisted). For scrape pipeline status, add a `pipeline_runs` table or extend `scrape_runs` with pipeline-level metadata.

**Status**: Anticipated, not yet observed. `ScrapeRun` is DB-persisted but pipeline orchestration state and enrichment runs are memory-only.

---

## Dashboard Failures

### DASH-1: Stale Cached Data Without Freshness Indicator

**Trigger**: Streamlit `@st.cache_data(ttl=60)` serves cached query results for up to 60 seconds. No timestamp shown indicating when data was last fetched.

**Blast radius**: User sees metrics that are up to 60 seconds old without knowing it. Combined with SF-5 (no scrape freshness), could show data that is days old with no indication.

**Symptoms**: No visible symptom. Metrics appear current but may reflect old state.

**Mitigation**: Display "Last refreshed: {timestamp}" on each cached section. Show "Data as of last scrape: {timestamp}" using most recent `ScrapeRun.started_at`. Color-code: green (<1h), yellow (1-24h), red (>24h).

**Status**: Anticipated, not yet observed.

---

## Database Failures

### DB-1: PostingEnrichment Allows Multiple Records Per Posting

**Trigger**: Re-enrichment of a posting creates a new `PostingEnrichment` row (by design — versioning). Queries that join `postings` to `posting_enrichments` without filtering to latest version will return multiple rows per posting.

**Blast radius**: Aggregation queries double-count postings. Dashboard metrics inflated.

**Symptoms**: Posting counts higher than expected. Metrics change after re-enrichment even though underlying data hasn't changed.

**Mitigation**: Create a SQL view or query pattern that selects only the latest enrichment per posting (by `created_at` or `enrichment_version`). Use this view consistently in aggregation and dashboard queries. Consider a partial unique index on `(posting_id)` for the latest record.

**Status**: Anticipated. Current dashboard queries use outer join without deduplication.

---

## Scheduling Failures

### SCHED-1: No Automated Pipeline Scheduling

**Trigger**: No cron, scheduler, or automated trigger exists. Pipelines only run when a user manually triggers them via API (`/api/scrape/trigger`) or dashboard button.

**Blast radius**: Entire system. If no one triggers a scrape for days, all data goes stale silently. No missed-run detection exists.

**Symptoms**: `ScrapeRun` table shows no recent entries. Dashboard shows old data. No alert or notification that scrapes haven't run.

**Mitigation**: Implement automated scheduling (APScheduler, Celery Beat, or systemd timer). Daily scrape at 2am, enrichment at 3am, aggregation at 4am. Add missed-run detection: if expected run hasn't started within 2x its normal interval, alert via webhook/email.

**Status**: Anticipated. System is currently manual-only. M3 phase includes pipeline automation.

---

### DASH-2: Streamlit sprintf Format Incompatibility

**Trigger**: Using `%,` comma thousands separator in `st.column_config.NumberColumn(format=...)`. Streamlit's internal sprintf library doesn't support this modifier.

**Blast radius**: Per-column. Affected columns show raw unformatted numbers with a console error tooltip.

**Symptoms**: Dashboard shows tooltip "Failed to format the number based on the provided format configuration: ($%,.2f). Error: SyntaxError: [sprintf] unexpected placeholder". Numbers display without formatting.

**Mitigation**: Use `$ %.2f` (no comma) or implement custom string formatting on the DataFrame before display. Trade-off: string formatting breaks numeric column sorting.

**Status**: **Observed and fixed.** Hit Feb 19 2026 after PR #123 followed bot review suggestion to use `$%,.2f`. Fixed in PR #124 by reverting to `$ %.2f`.

---

## Code Quality Failures

### CQ-1: Sequential Async Operations Where Concurrency Is Safe

**Trigger**: Writing multiple independent `await` calls in sequence without considering `asyncio.gather()`.

**Blast radius**: Latency multiplied by number of sequential calls. For N independent DB queries at 50ms each, total = N*50ms instead of ~50ms.

**Symptoms**: Endpoint response times linearly proportional to number of sub-queries. Aggregation jobs take sum-of-all-jobs time instead of max-single-job time.

**Mitigation**: Before writing sequential `await` calls, ask: "Are these independent?" If yes, use `asyncio.gather()` with per-operation sessions. Each gathered coroutine must have its own session to avoid shared-session conflicts.

**Status**: Observed (Mar 7 2026). Found in posting_service.py (4 sequential queries), aggregation orchestrator (7 sequential jobs), enrichment dedup saves.

---

### CQ-2: Copy-Paste Across Adapter Implementations

**Trigger**: Implementing a new scraper/adapter by copying an existing one and modifying. Shared infrastructure (circuit breaker, HTTP client setup, retry logic) gets duplicated instead of extracted.

**Blast radius**: Bug fixes must be applied to N files. Behavior diverges silently. New adapters inherit stale patterns.

**Symptoms**: Identical methods (same name, same body) in 3+ files. `grep -c` for a function name returns multiple files.

**Mitigation**: Before implementing shared behavior in an adapter, check if it exists in `scrapers/base.py` or a shared module. If 2+ adapters share identical logic (>10 lines), extract to a shared module immediately — do not defer. The "extract after 3 copies" rule applies.

**Status**: Observed (Mar 7 2026). Circuit breaker (~40 lines) and HTTP client init (~7 lines) duplicated across all 3 scrapers.

---

### CQ-3: Status Enum Proliferation

**Trigger**: Each subsystem (scraper, enrichment, scheduler) defines its own status enum without checking for existing ones. Similar values get different names (`SUCCESS` vs `COMPLETED`).

**Blast radius**: String-to-enum mapping code proliferates in API routes. Status comparisons become fragile. Frontend must handle multiple status vocabularies.

**Symptoms**: `grep -r "class.*Status.*Enum" src/` returns 3+ distinct enums with overlapping values. API routes contain `_STATUS_MAP` dicts.

**Mitigation**: Before creating a new status enum, search for existing ones. If a subsystem needs additional states, extend the canonical enum or create a subsystem-specific enum that clearly documents why it differs.

**Status**: Observed (Mar 7 2026). 3 separate status enums with overlapping values; `_STATUS_MAP` in enrich routes maps "completed" to SUCCESS.

---

### CQ-4: Frontend Design Token Drift

**Trigger**: Using raw hex color values (e.g., `#8C2C23`, `#4F5D75`) directly in JSX className strings instead of referencing design tokens from `lib/constants.ts` or CSS variables.

**Blast radius**: Design changes require find-and-replace across dozens of files. Inconsistencies between components using slightly different hex values for the same semantic color.

**Symptoms**: `grep -r '#[0-9A-Fa-f]{6}' web/src/` returns 50+ matches. Same color used in multiple files with no shared constant.

**Mitigation**: Define all brand colors in `lib/constants.ts` (for JS access) and CSS variables (for Tailwind). Reference by semantic name, never by hex value in component code.

**Status**: Observed (Mar 7 2026). 6+ hex colors inlined across settings and hiring pages.

---

### CQ-5: Type Safety Erosion via `as any`

**Trigger**: API response types from code generators don't match runtime shape. Developer casts to `any` with eslint-disable instead of fixing the type definition or adding a proper type assertion.

**Blast radius**: Runtime errors not caught at compile time. TypeScript's value proposition eroded. Each `any` cast is a hole in the type system.

**Symptoms**: `grep -r 'as any' web/src/` returns matches with `eslint-disable` comments. Generated API types exist but aren't used.

**Mitigation**: Never use `as any`. If generated types are wrong, fix the generator input or add a proper type assertion with `as SomeSpecificType`. If the type is truly unknown, use `unknown` + type guard.

**Status**: Observed (Mar 7 2026). 3 `as any` casts in settings page with eslint-disable comments.

---

## Template for New Patterns

```markdown
### XX-N: Short Name

**Trigger**: What causes this failure.

**Blast radius**: What breaks, how far does damage spread.

**Symptoms**: What you observe when this happens.

**Mitigation**: How to prevent or recover. Status: designed / implemented / observed.

**Observed**: Date, context, details.
```
