# M3 Parallel Pipeline — Research Findings

**Date:** 2026-02-18
**Sources:** CodeSight (codebase), Context7 (library docs), web research (practitioner patterns), Supabase (live DB)
**Purpose:** Feed implementation agents with validated patterns and codebase state for M3 issue resolution

---

## Database State (Live Supabase Query Results)

### Table Sizes
| Table | Rows | Size |
|-------|------|------|
| posting_snapshots | 2,031 | 9.5 MB |
| postings | 1,056 | 760 KB |
| posting_enrichments | 932 | 4.8 MB |
| posting_brand_mentions | 727 | 336 KB |
| scrape_runs | 15 | 48 KB |
| enrichment_runs | 1 | 48 KB |
| brands | 16 | 48 KB |
| retailers | 5 | 48 KB |
| companies | 4 | 48 KB |
| Aggregation tables | 0 | 8-16 KB each |

### Missing FK Indexes (Issue #45)
**14 FK columns missing indexes.** Critical ones for dashboard query performance:

| Table | FK Column | Status |
|-------|-----------|--------|
| posting_enrichments | posting_id | **MISSING** (critical — used in 5+ dashboard queries) |
| posting_enrichments | brand_id | **MISSING** |
| posting_enrichments | retailer_id | **MISSING** |
| posting_enrichments | market_id | **MISSING** |
| posting_brand_mentions | posting_id | **MISSING** (critical — used in JOINs) |
| posting_brand_mentions | resolved_brand_id | **MISSING** |
| posting_brand_mentions | resolved_retailer_id | **MISSING** |
| agg_daily_velocity | brand_id, market_id | **MISSING** |
| agg_pay_benchmarks | company_id, brand_id, market_id | **MISSING** |
| agg_posting_lifecycle | company_id, brand_id, market_id | **MISSING** |
| users | invited_by | **MISSING** |
| posting_snapshots | posting_id | HAS INDEX (composite: posting_id, snapshot_date) |
| postings | company_id | HAS INDEX |
| scrape_runs | company_id | HAS INDEX |

### Existing Indexes on Fact Tables
- `posting_snapshots`: PK, `ix_snapshots_company_brand_date(posting_id, snapshot_date)`, `uq_snapshots_posting_date`
- `postings`: PK, `ix_postings_brand_active(company_id, is_active)`, `ix_postings_fingerprint_hash`, `uq_postings_company_external(company_id, external_job_id)`
- `posting_enrichments`: PK only — **no FK indexes**
- `posting_brand_mentions`: PK only — **no FK indexes**
- `scrape_runs`: PK, `ix_scrape_runs_company_started(company_id, started_at DESC)`

### Append-Only Triggers (Issue #47)
**No triggers exist** on any fact tables. Append-only is convention-only, not DB-enforced.

### Scrape Run History (Issues #97, #100)
- All 15 scrape_runs have status `completed` or `failed` (never `pending` at rest)
- BDS + MarketSource failed on Feb 16 runs (before URL fix), succeeded on Feb 18
- ScrapeRunStatus enum: `PENDING`, `COMPLETED`, `FAILED` (no `RUNNING` state in DB)
- Root cause of #97: orchestrator creates ScrapeRun with `status='pending'`, updates to `completed`/`failed` when done. No intermediate `running` state in DB.

### Enrichment Run State (Issue #91)
- Only 1 enrichment_run exists: `pass1_total=26, pass1_succeeded=23, pass2_total=31, pass2_succeeded=23`
- `pass1_skipped=0, pass2_skipped=0` — skipped counts not yet populated
- Enrichment progress shows zeros because `_enrich_stage_from_memory()` uses in-memory `run.pass1_result` which is `None` until pass completes

### Alembic State
- **Single head on main:** `b52ab5ef6cf1` (no two-head problem)
- `feat/issue-98-111` branch adds `f8a9b0c1d2e3` chaining off `b52ab5ef6cf1`
- New DB migrations must chain off `f8a9b0c1d2e3` after merge

---

## WS1: Dashboard State + UX (#97, #99, #100, #55, #91)

### Issue #97 — "Pending" for Running Companies

**Root cause:** `get_latest_pipeline_status()` in `dashboard/queries.py:109-177` reads `ScrapeRun.status` from DB. The orchestrator creates runs with `status='pending'` (via model default) and only updates to `completed`/`failed` when a company finishes. There is no `running` state in the `ScrapeRunStatus` enum.

**The pipeline API** (`/api/pipeline/status`) correctly reads from in-memory `PipelineRun` which has real-time `company_states` with `running` state. But the dashboard pages (`Pipeline Controls`, `Pipeline Health`) read from DB via `get_latest_pipeline_status()`.

**Fix approach:** Make dashboard pages use the pipeline API (`/api/pipeline/status`) as primary source with DB as fallback, not the other way around. The Pipeline Controls page already has `_api_get()` but doesn't use it for company-level states.

**Implementation:**
- `dashboard/queries.py` — `get_latest_pipeline_status()` line 157-159: the `if "pending" in statuses: overall = "running"` logic is correct for the overall status but individual company states still show "pending"
- Fix: either (a) add API-sourced company states to the dashboard, or (b) update `company_states` dict to map `"pending"` → `"running"` when the overall run is active

**Recommended:** Option (b) — simpler, no new API calls needed. In `get_latest_pipeline_status()`, after building `company_states`, if any company is still "pending" and the run `completed_at IS NULL`, remap to "running":
```python
# After building company_states dict
if any(s == "pending" for s in company_states.values()):
    for slug, status in company_states.items():
        if status == "pending":
            company_states[slug] = "running"
```

### Issue #99 — Auto-Refresh Not Activating on External Scrape

**Root cause:** `dashboard/main.py:245-258` — auto-refresh checkbox default computed once at page load:
```python
is_active = pipeline is not None and pipeline["system_state"] in ("scraping", "enriching")
auto_refresh = st.checkbox("Auto-refresh", value=is_active)
```
If the page loads while idle, `is_active=False` and the checkbox stays unchecked.

**Streamlit patterns (from Context7 + research):**

1. **`@st.fragment(run_every=N)`** — the modern solution. Wraps the status-polling block in a fragment that reruns independently every N seconds without full page rerun.

2. **`st.rerun(scope="fragment")`** — reruns only the fragment from which it's called.

3. **Session state initialization guard** — never pass both `value=` and `key=` to a checkbox:
```python
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = is_active
auto_refresh = st.checkbox("Auto-refresh", key="auto_refresh")
```

**Recommended fix:** Use `@st.fragment(run_every=30)` for a lightweight status-checking fragment that activates auto-refresh when it detects active state. This replaces the current `time.sleep() + st.rerun()` pattern which blocks the Streamlit thread.

```python
@st.fragment(run_every=30)  # 30s background poll
def _status_monitor():
    status = _api_get("/api/pipeline/status")
    if status and status["system_state"] in ("scraping", "enriching"):
        st.session_state.auto_refresh = True
        st.rerun(scope="app")  # Full rerun to activate fast polling

# Main page — fast polling when active
if st.session_state.get("auto_refresh"):
    @st.fragment(run_every=5)
    def _live_status():
        # Render live metrics
        ...
```

**Caveat:** `st.fragment` cannot call `st.sidebar`. Sidebar elements must be rendered outside fragments.

### Issue #100 — Scheduler "No Pipeline Runs"

**Root cause:** `scheduler/jobs.py:28-33` — module-level `_last_pipeline_finished_at = None`. Only updated by `pipeline_job()` which is called by the scheduler cron, not by manual `POST /api/scrape/trigger`.

**Scheduler API** (`/api/scheduler/status`) at `api/routes/scheduler.py:66-101` returns `last_pipeline_finished_at` from `get_last_pipeline_finished_at()` which reads the module-level variable.

**Fix approach:** Query the `scrape_runs` table for the most recent completed run instead of relying on in-memory state. This shows ALL pipeline runs regardless of trigger source.

```python
# In scheduler/jobs.py or a shared query function
async def get_last_pipeline_run_from_db() -> dict | None:
    async with async_session_factory() as session:
        stmt = (
            select(ScrapeRun)
            .where(ScrapeRun.status.in_(["completed", "failed"]))
            .order_by(ScrapeRun.completed_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            return {"finished_at": row.completed_at, "success": row.status == "completed"}
    return None
```

Then update `scheduler_status()` to use DB as fallback when `get_last_pipeline_finished_at()` returns `None`.

### Issue #91 — Enrichment Progress Zeros

**Root cause:** `api/routes/pipeline.py:101-119` — `_enrich_stage_from_memory()` sets `pass1_total=0` and `pass2_total=0` because `run.pass1_result` is `None` until the pass completes. The DB fallback (`_enrich_stage_from_db()`) has correct counters from `increment_enrichment_counter()` but is never reached when an in-memory run exists.

**Fix approach — hybrid read:** When in-memory run exists AND is `RUNNING`, read live counters from DB:
```python
def _enrich_stage_from_memory(run: EnrichmentRun) -> StageStatus:
    if run.status == EnrichmentStatus.RUNNING:
        # Read live counters from DB (updated by increment_enrichment_counter)
        db_run = await get_latest_enrichment_run_from_db()
        if db_run and db_run["status"] == "running":
            return _enrich_stage_from_db(db_run)
        # Fallback to in-memory with zero totals
        ...
```

**Key insight:** `increment_enrichment_counter()` at `enrichment/orchestrator.py:140-156` uses atomic DB updates (`SET pass1_succeeded = pass1_succeeded + 1`), so the DB always has the freshest counters during active runs.

### Issue #55 — Dashboard UX Polish

From the issue body, remaining items:
- [ ] No "last refreshed" timestamp on any page
- [ ] Timestamps display with microseconds and UTC offset (verbose)
- [ ] Cache TTL (60s) may confuse during active runs
- [ ] No pagination for scrape runs (hard limit 20)
- [ ] Metric cards could use delta indicators

**Fix approach:** These are small, independent changes across dashboard pages. Key patterns:
- Add `st.caption(f"Last refreshed: {datetime.now(UTC).strftime('%H:%M:%S UTC')}")` to each page
- Format timestamps via a shared helper: `ts.strftime("%Y-%m-%d %H:%M UTC")` (drop microseconds)
- Cache TTL: use 5s during active runs, 60s when idle (already partially done in main.py)

---

## WS2: Database Hardening (#88, #47, #45)

### Issue #88 — Server Default for enrichment_runs.status

**Current state:** `enrichment_runs.status` column has no `server_default`. Model has `default=EnrichmentRunStatus.PENDING` (Python-side only).

**Fix:** Simple `ALTER COLUMN SET DEFAULT`:
```python
def upgrade() -> None:
    op.alter_column('enrichment_runs', 'status',
        server_default='pending')

def downgrade() -> None:
    op.alter_column('enrichment_runs', 'status',
        server_default=None)
```

### Issue #47 — Append-Only Triggers

**Current state:** No triggers exist. Pattern from research:
```sql
CREATE OR REPLACE FUNCTION enforce_append_only()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only. UPDATE and DELETE are not permitted.',
        TG_TABLE_NAME USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

Apply to: `posting_snapshots`, `posting_enrichments`, `posting_brand_mentions`

**Caveat:** These triggers will block the `postings.is_active` UPDATE from deactivation logic. Verify that deactivation only updates `postings`, not the fact tables.

### Issue #45 — FK Indexes

**Priority indexes based on query analysis:**

1. **`posting_enrichments(posting_id)`** — HIGH: used in 5+ dashboard queries and enrichment queries
2. **`posting_brand_mentions(posting_id)`** — HIGH: used in JOINs for brand analysis
3. **`posting_enrichments(brand_id)`** — MEDIUM: used in enrichment coverage queries
4. **`posting_brand_mentions(resolved_brand_id)`** — MEDIUM: used in brand timeline
5. Aggregation table indexes — LOW priority (tables are empty, truncate+insert pattern)

**Pattern for non-concurrent index creation:**
```python
def upgrade() -> None:
    op.create_index('ix_posting_enrichments_posting_id', 'posting_enrichments', ['posting_id'])
    op.create_index('ix_posting_brand_mentions_posting_id', 'posting_brand_mentions', ['posting_id'])
    ...
```

**Note on CONCURRENTLY:** asyncpg + `CREATE INDEX CONCURRENTLY` has a known incompatibility (SQLAlchemy issue #11299). For our small table sizes (< 3K rows), regular `CREATE INDEX` is fast enough. Use `CONCURRENTLY` only when tables exceed 100K+ rows.

**Migration chain:** All three migrations (#88, #47, #45) must chain sequentially off the current head. Order: #88 (tiny) → #47 (triggers) → #45 (indexes).

---

## WS3: Scraper Hardening (#65)

### Issue #65 — Validate HTTP Redirect Targets

**Current state:**
- iCIMS scraper (`icims.py:377`): `follow_redirects=True` — NO validation
- Workday scraper: does NOT set `follow_redirects` (httpx default=False) — inherently safe

**Only iCIMS needs the fix.** Workday uses JSON API (POST requests), not HTML page scraping.

**Known failure case:** Advantage Solutions redirected from original URL to `careers.youradv.com` — different domain, 200 response, 0 jobs parsed, scraper reported success.

**Recommended approach — domain allowlist validation:**

```python
def _validate_redirect(response: httpx.Response, expected_domain: str) -> None:
    """Validate redirect didn't leave the expected domain."""
    final_domain = urlparse(str(response.url)).netloc.lower().split(":")[0]
    expected = urlparse(expected_domain).netloc.lower().split(":")[0]
    if final_domain != expected:
        raise ValueError(
            f"Redirected to unexpected domain '{final_domain}' "
            f"(expected '{expected}'). Chain: "
            + " -> ".join(str(r.url) for r in response.history)
            + f" -> {response.url}"
        )
```

**Insertion points:**
1. `ICIMSFetcher.fetch_all_listings()` — after `response = await self.client.get(url)` at line 214
2. `ICIMSFetcher.fetch_detail()` — after `response = await self.client.get(url)` at line 237

**For multi-URL fetching**, each search URL has its own expected domain derived from the URL itself. The `_base_url_from_search_url()` helper already exists for this.

**httpx patterns (from Context7):**
- `response.history` — list of intermediate Response objects (one per redirect hop)
- `response.url` — final URL after all redirects
- `response.is_redirect` — True if response is a redirect (before following)
- Event hooks: `event_hooks={"response": [validator_fn]}` for client-wide validation

---

## WS4: Alembic Config (#46)

### Issue #46 — Direct Connection for Migrations

**Current state:** `alembic/env.py:26` returns `settings.database_url` (session-mode pooler).

**Fix:** Change to `settings.database_url_direct`:
```python
def get_url() -> str:
    """Get migration connection URL. Uses direct connection for DDL safety."""
    try:
        from compgraph.config import settings
        return settings.database_url_direct
    except Exception:
        return os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
```

**`settings.database_url_direct`** at `config.py:53-60` constructs:
```
postgresql+asyncpg://postgres:{pw}@db.{ref}.supabase.co:5432/postgres
```

**Risk:** Direct connection requires IPv6 on the host running migrations. Both macOS dev and the Pi should have IPv6. If not, keep pooler URL as fallback with an env var override.

**Safer approach — prefer direct, fallback to pooler:**
```python
def get_url() -> str:
    try:
        from compgraph.config import settings
        url = os.environ.get("ALEMBIC_DATABASE_URL")
        if url:
            return url
        return settings.database_url_direct
    except Exception:
        return os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
```

---

## Cross-Cutting Concerns

### Alembic Migration Chain
After merging `feat/issue-98-111`, the head will be `f8a9b0c1d2e3`. All new migrations must chain:
```
b52ab5ef6cf1 → f8a9b0c1d2e3 → [#88] → [#47] → [#45]
```

### Test Strategy
- Dashboard fixes (#97, #99, #100, #91, #55): primarily manual testing via dashboard observation. Unit tests for query functions.
- DB migrations (#88, #47, #45): test single-head constraint. Trigger tests via integration tests.
- Scraper hardening (#65): unit tests with mocked httpx responses containing redirect chains.
- Alembic config (#46): verify migration runs against live DB.

### Deployment Sequence
1. Merge `feat/issue-98-111` → main (scraper fixes)
2. Deploy to dev server (runs migration `f8a9b0c1d2e3`)
3. Merge parallel workstream PRs → main
4. Deploy again (runs chained migrations)
5. Trigger full scrape to verify all 4 scrapers + enrichment
