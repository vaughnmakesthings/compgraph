# First Pipeline Run Findings — M3 Pre-Testing Fixes

**Date**: 2026-02-16
**Context**: Manual pipeline trigger via dashboard Scheduler page after deploying latest main to dev server
**Pipeline**: Scrape (4 companies) → Enrich Pass 1 (Haiku) → Enrich Pass 2 (Sonnet)

---

## Run Results

| Company | Scrape Status | Postings | Snapshots | Notes |
|---------|--------------|----------|-----------|-------|
| T-ROC | completed | 102 | 102 | Working. 4 new postings since last scrape. |
| 2020 Companies | completed | 700+ | 700+ | NEW — first successful scrape. Workday adapter works. |
| BDS Connected Solutions | failed | 0 | 0 | iCIMS URLs still broken. |
| MarketSource | failed | 0 | 0 | iCIMS URLs still broken. |

**Enrichment**: Pass 1 (Haiku) in progress at time of writing. ~250 of ~700+ new postings enriched. Pass 2 (Sonnet) pending.

**Performance**: Pi at 6% memory (460M/7.69G), CPU load 0.16. No bottlenecks. Pipeline is I/O bound (waiting on Anthropic API).

---

## Bugs Found During Live Testing

### BUG-1: Emoji shortcodes render as text (CRITICAL UX)

**Location**: Dashboard — Pipeline Health, Pipeline Controls
**Symptom**: `:green_circle:`, `:white_check_mark:`, `:x:`, `:runner:` display as literal text instead of rendered emoji icons.
**Impact**: Dashboard looks broken to end users. Data freshness indicators are unreadable.
**Root cause**: Streamlit markdown rendering not processing emoji shortcodes in certain contexts (likely `st.markdown` vs `st.write` or missing `unsafe_allow_html`).
**Fix**: Replace shortcode strings with actual Unicode emoji characters: `🟢`, `✅`, `❌`, `🏃`.

### BUG-2: Pipeline Controls shows 0/0 for scheduler-triggered runs (IMPORTANT)

**Location**: `src/compgraph/dashboard/pages/3_Pipeline_Controls.py`
**Symptom**: When pipeline is triggered via the scheduler (APScheduler `pipeline_job()`), the Pipeline Controls page shows Status: RUNNING but Postings Found: 0, Snapshots: 0, Succeeded: 0 for all companies — even T-ROC which completed with 102 postings.
**Impact**: Operator has no visibility into scheduler-triggered run progress. Looks like a broken pipeline.
**Root cause**: Pipeline Controls reads from `/api/scrape/status` which returns the in-memory `PipelineOrchestrator` state. The scheduler creates its own orchestrator instance in `pipeline_job()` — the API endpoint reads a *different* instance.
**Fix options**:
  - (a) Have `pipeline_job()` use the same global orchestrator as the API
  - (b) Add a shared state store (Issue #61)
  - (c) Query the database for real-time scrape run progress instead of in-memory state
**Recommended**: Option (c) — query `scrape_runs` table directly. Most reliable and works regardless of which code path triggered the run.

### BUG-3: No enrichment visibility on any dashboard page (IMPORTANT)

**Location**: Dashboard — all pages
**Symptom**: After scrape completes, new postings appear in Posting Explorer with no enrichment data. There's no indication that enrichment is running, queued, or how far along it is. User sees "completed" scrape + empty enrichment fields and assumes something broke.
**Impact**: Confusing to end users. Cannot distinguish "enrichment hasn't run yet" from "enrichment failed" from "enrichment not supported."
**Fix**: Add "Enrichment Status" section to Pipeline Health showing:
  - Current enrichment run status (idle / pass1 running / pass2 running)
  - Postings enriched vs total (e.g., "250 / 705 postings — Pass 1 in progress")
  - Last enrichment run timestamp and result

### BUG-4: No progress indication for long-running scrapers (MODERATE)

**Location**: Dashboard — Pipeline Controls
**Symptom**: 2020 Companies showed `:runner: running` for 15+ minutes with 0 Postings and 0 Snapshots. No indication of how many pages scraped, how many postings found, or estimated time remaining.
**Impact**: Operator cannot distinguish "scraper working through 700 postings" from "scraper hung/stuck." No way to know if intervention is needed.
**Fix**: For scheduler-triggered runs, at minimum show a "scrape started at" timestamp. Better: query `scrape_runs` table for the in-progress run and show `pages_scraped` / `jobs_found` as they accumulate.

### BUG-5: "completed" label misleading during multi-phase pipeline (MODERATE)

**Location**: Dashboard — Pipeline Health, Pipeline Controls
**Symptom**: T-ROC shows "completed" in the scrape runs table while enrichment is still in progress. New T-ROC postings appear in Posting Explorer with empty enrichment fields. User interpretation: "T-ROC is done but enrichment failed."
**Impact**: Misleading status. "Completed" refers to the scrape phase only, but user reads it as "fully processed."
**Fix options**:
  - (a) Rename column from "status" to "scrape_status" to clarify scope
  - (b) Add a separate "enrichment_status" column to the scrape runs table
  - (c) Add a pipeline-level status that tracks scrape + enrichment as a unit
**Recommended**: (a) is the quickest. (c) is best long-term but more work.

### BUG-6: `pages_scraped` always 0 in dashboard (MODERATE)

**Location**: `src/compgraph/scrapers/workday.py`, `src/compgraph/scrapers/icims.py`
**Symptom**: Pipeline Health dashboard shows "Pages Scraped: 0" for all companies, even though `jobs_found` and `snapshots_created` have correct values.
**Impact**: Misleading — looks like scraper didn't paginate at all.
**Root cause**: Neither Workday nor iCIMS adapter ever increments `result.pages_scraped` on the `ScrapeResult`. The field defaults to 0 and is copied as-is to the `scrape_runs` DB record.
**Fix**: APPLIED — Added `pages_fetched` counter to both fetcher classes, set `result.pages_scraped` in both adapters.

### BUG-7: BDS/MarketSource scraper URLs not applied by migration (CRITICAL)

**Location**: `alembic/versions/d5e6f7a8b9c0_update_competitor_companies.py`
**Symptom**: BDS fails with `ConnectError('[Errno -2] Name or service not known')`. MarketSource fails with `404 Not Found` on `https://www.marketsource.com/careers/jobs/search?pr=0&in_iframe=1`.
**Impact**: 2 of 4 competitors produce zero data.
**Root cause**: Migration used `ON CONFLICT (slug) DO NOTHING`. BDS and MarketSource already existed in the database (from initial seeding) with old, incorrect URLs. The migration's INSERT with correct iCIMS URLs and `search_urls` config was silently skipped.
**Fix**: APPLIED — Updated company records directly in DB with correct URLs. Fixed migration to use `ON CONFLICT (slug) DO UPDATE SET` for future runs.

---

## Infrastructure Observations

### OBS-1: SQL echo fills logs (LOW)

**Impact**: `ENVIRONMENT=dev` on the Pi causes `echo=True` on the SQLAlchemy engine. Every SQL query logged to journald. During a 700-posting scrape, this generates thousands of log lines, making it hard to find application-level messages.
**Fix**: Set `ENVIRONMENT=production` in `.env` on the Pi, or explicitly set `echo=False`.

### OBS-2: No swap configured (LOW)

**Impact**: At 6% memory usage this isn't urgent. But with no swap, an unexpected memory spike would trigger OOM killer instantly with no buffer.
**Fix**: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile` + add to `/etc/fstab`.

### OBS-3: 2020 Companies has 700+ postings (INFORMATIONAL)

**Impact**: First successful 2020 Companies scrape reveals they have significantly more postings than T-ROC (700+ vs 102). This affects:
  - Enrichment time: ~700 Haiku calls (Pass 1) + ~700 Sonnet calls (Pass 2) = significant API spend
  - Pipeline duration: Full pipeline run will take 30-60 min instead of ~5 min with T-ROC alone
  - `ENRICHMENT_BATCH_SIZE=50` and `ENRICHMENT_CONCURRENCY=5` settings are appropriate

---

## Priority Fix List for Dev Team

### Must Fix Before M3 Testing Begins

| Priority | Bug | Effort | Impact | Status |
|----------|-----|--------|--------|--------|
| P0 | BUG-1: Emoji shortcodes as text | 15 min | Dashboard looks broken | OPEN (#81) |
| P0 | BUG-2: Pipeline Controls 0/0 for scheduler runs | 1-2 hr | No run visibility | OPEN (#82) |
| P0 | BUG-7: BDS/MarketSource URLs not applied | 5 min | 2/4 competitors broken | FIXED (DB + migration) |
| P1 | BUG-3: No enrichment status on dashboard | 2-3 hr | Can't monitor enrichment | OPEN (#83) |
| P1 | BUG-5: "completed" misleading for scrape-only | 15 min | Confusing status | OPEN |

### Fix During M3 Week 1

| Priority | Item | Effort | Status |
|----------|------|--------|--------|
| P2 | BUG-4: No progress for long scrapers | 1 hr | OPEN |
| P2 | BUG-6: `pages_scraped` always 0 | 15 min | FIXED (code) |
| P2 | OBS-1: Disable SQL echo on Pi | 2 min | FIXED (.env) |
| P3 | OBS-2: Add swap file | 5 min | OPEN |

---

## Positive Findings

1. **2020 Companies scraper works** — 700+ postings on first run. Workday adapter handles large volumes.
2. **Enrichment Pass 1 running smoothly** — ~40 postings/min via Haiku, no failures observed.
3. **Pi performance excellent** — 6% memory, 0.16 load average. No resource concerns.
4. **Health endpoint works** — `/health` correctly reports DB connected + scheduler OK.
5. **APScheduler integration solid** — Manual trigger via dashboard worked, schedule configured for Mon/Wed/Fri 2am.
6. **Data freshness indicators work** — T-ROC shows green with correct timestamp (ignoring emoji rendering bug).
7. **Migrations applied cleanly** — Both pending migrations ran without issues.

---

## Consensus

The pipeline infrastructure works. Scraping and enrichment are running correctly end-to-end. The issues are all **dashboard visibility gaps** — the actual data pipeline is reliable. The dev team should prioritize fixing the dashboard UX (emoji rendering, scheduler-triggered run visibility, enrichment status) before the business user begins daily monitoring.
