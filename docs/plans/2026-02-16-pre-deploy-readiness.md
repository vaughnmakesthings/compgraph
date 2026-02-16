# Pre-Deployment Readiness Review — M3 Data Collection

**Date**: 2026-02-16
**Target**: Deploy latest main to dev server (192.168.1.69), enable APScheduler for automated daily pipeline runs
**Verdict**: CONDITIONAL GO (3 blockers, ~30 min total effort)

---

## Agent Team

| Agent | Focus | Verdict |
|-------|-------|---------|
| Code Quality | Async safety, error handling, test gaps | DEPLOY READY (4 caveats) |
| Database | Schema, migrations, pool config, indexes | BLOCKERS FOUND (1 critical) |
| Pipeline Reliability | Failure isolation, LLM resilience, scheduler | BLOCKERS FOUND (1 critical) |
| DevOps/Infra | Systemd, health checks, monitoring, disk | BLOCKERS FOUND (2 critical) |
| Business User (Dana) | Value delivery, dashboard UX, monitoring | NOT READY (3 requests) |
| CTO (Arbiter) | Blocker vs defer classification | CONDITIONAL GO |

---

## BLOCKERS (Must Fix Before Deploy)

### 1. DB-3: Pending Alembic Migrations
**Source**: Database Agent
**Effort**: 2 minutes

Two migrations not applied to Supabase (`d5e6f7a8b9c0` — competitor companies update, `e6f7a8b9c0d1` — `last_scraped_at` column). App will fail at startup if models expect columns that don't exist.

**Fix**:
```bash
ssh compgraph-dev "cd /opt/compgraph && op run --env-file=.env -- uv run alembic upgrade head"
```

### 2. DO-2: Health Endpoint Doesn't Check Scheduler
**Source**: DevOps Agent
**Effort**: 15-20 minutes

`/health` checks DB connectivity but ignores APScheduler. If scheduler dies silently, health says "OK" while no data is collected. This is the **silent failure** scenario — the single biggest risk for unattended operation.

**Fix**: Add scheduler liveness to `/health` response when `SCHEDULER_ENABLED=true`.

### 3. PR-2: Broken Scrapers Waste 3.5 Min on Retries
**Source**: Pipeline Reliability Agent
**Effort**: 5-10 minutes

3 of 4 scrapers have dead URLs. Each gets 3 retry attempts with exponential backoff (30s, 60s, 120s) every pipeline run. This produces noisy logs and wastes time.

**Fix**: Disable the 3 broken scrapers in company config or skip known-broken adapters.

---

## DEFER-M3 (Fix During Data Collection Period)

| ID | Finding | Agent | Rationale |
|----|---------|-------|-----------|
| CQ-1/PR-4 | No concurrent run guard (API vs scheduler) | Code Quality + Pipeline | Single operator won't trigger during scheduled windows. Issue #60. |
| CQ-2 | Enrichment run store unbounded memory | Code Quality | 14 entries over 2 weeks = negligible. Add `MAX_STORED_RUNS` cap. |
| CQ-3 | `setup_scheduler` missing `__aexit__` on failure | Code Quality | One-shot leak on startup failure. Systemd restarts. |
| PR-1 | Enrichment gated on scrape success | Pipeline | Transient T-ROC failure delays enrichment by 1 day, not data loss. |
| PR-3 | No explicit Anthropic API timeout | Pipeline | Default SDK timeout is 10 min — long but not infinite. Add 60s timeout. |
| DO-1 | Systemd service files not version-controlled | DevOps | Services exist on Pi and work. Copy to repo for hygiene. |
| DO-3 | No log rotation config | DevOps | journald has default limits. 59GB won't fill in 2 weeks. |
| DO-4 | No alerting on silent failures | DevOps | With DO-2 fixed, can poll `/health`. Add cron-based alert. |
| DO-5 | Graceful shutdown may orphan enrichment | DevOps | Set `TimeoutStopSec=90` on Pi. Restarts are rare and manual. |
| DO-6 | No memory monitoring | DevOps | SSH access available. Add metric to `/health`. |
| DB-1 | Pool size oversized for Pi | Database | Works, just suboptimal. Monitor and tune. |
| BU-1 | Only 1 of 4 competitors scraped | Business User | Known constraint. Fix scrapers as URLs are reverse-engineered. |
| BU-2 | No time-series chart | Business User | Build after 3-5 days of data exist. |
| BU-3 | No brands rollup page | Business User | Build during M3 once enrichment data accumulates. |
| BU-6 | Scraper status health table | Business User | Build alongside DO-2 health improvements. |

## DEFER-M4+ (Future Milestones)

| ID | Finding | Agent |
|----|---------|-------|
| CQ-4 | Missing enrichment exception test | Code Quality |
| DB-2 | Missing index on `enrichment_version` | Database |
| PR-5 | In-memory scheduler state lost on restart | Pipeline (Issue #61) |
| PR-6 | Workday single-transaction commit | Pipeline |
| BU-4 | Pay benchmarks summary page | Business User |
| BU-5 | CSV export from Posting Explorer | Business User |

---

## Deploy Sequence

1. Fix PR-2 — Disable broken scrapers in config
2. Fix DO-2 — Add scheduler state to `/health` endpoint
3. Run tests — Confirm 360+ pass, CI green
4. Merge to main
5. Deploy to Pi — `git pull && uv sync && systemctl restart compgraph`
6. Fix DB-3 — Run `alembic upgrade head` on Supabase
7. Verify — `/health` returns scheduler status, T-ROC scrape completes, enrichment triggers
8. Monitor — Check logs after first scheduled run

## M3 Priority Queue (First Week Post-Deploy)

1. CQ-1/PR-4 — Concurrent run guard (Issue #60)
2. PR-3 — Anthropic API explicit timeout
3. DO-5 — Systemd stop timeout
4. CQ-2 — Enrichment run store eviction
5. DO-1 — Version-control systemd units
6. BU-2/BU-3 — Dashboard time-series + brands pages

---

## Consensus Statement

CompGraph is ready to deploy with three small fixes totaling ~30 minutes: apply pending database migrations, add scheduler liveness to the health endpoint, and disable the three known-broken scrapers. All other findings are either low-risk for a single-operator dev server or addressable during M3 without jeopardizing data integrity. The priority is to start the pipeline — every day without collection is lost competitive intelligence data.

---

## Full Agent Reports

### Code Quality Agent — DEPLOY READY

**Strengths observed**: Pipeline phase isolation, Pydantic v2 schemas, timezone-aware datetimes, `max_concurrent_jobs=1`.

| # | Severity | Finding | File |
|---|----------|---------|------|
| CQ-1 | IMPORTANT | No concurrent run guard for manual trigger vs scheduled run | `scheduler.py:111` |
| CQ-2 | IMPORTANT | Enrichment run store unbounded memory (no eviction like scrape has) | `enrichment/orchestrator.py:101` |
| CQ-3 | IMPORTANT | `__aenter__` without `__aexit__` on setup failure | `scheduler/app.py:23` |
| CQ-4 | IMPORTANT | Missing test for enrichment exception in `pipeline_job` | `tests/test_scheduler.py` |
| CQ-5 | NOTE | `_get_scheduler` missing return type annotation | `scheduler.py:48` |
| CQ-6 | NOTE | `_validate_schedule_id` parameter named `job_id` but validates schedules | `scheduler.py:58` |
| CQ-7 | NOTE | Singleton Anthropic client never closed | `enrichment/client.py:25` |
| CQ-8 | NOTE | In-process state lost on restart (known, deferred to M6) | `scheduler/jobs.py:26` |

### Database Agent — BLOCKERS FOUND

**Strengths observed**: Append-only enforced on fact tables, session lifecycle correct, transaction boundaries proper, savepoint handling correct, pool pre-ping enabled.

| # | Severity | Finding | File |
|---|----------|---------|------|
| DB-1 | IMPORTANT | Pool size oversized for Pi (5+5 vs recommended 3+2) | `db/session.py:8` |
| DB-2 | IMPORTANT | Missing index on `enrichment_version` (matters at 10K+ rows) | `db/models.py:203` |
| DB-3 | CRITICAL | 2 pending Alembic migrations not applied | Migration system |
| DB-4 | NOTE | `deactivate_stale_postings` UPDATEs `postings.is_active` (acceptable exception) | `scrapers/deactivation.py:56` |
| DB-5 | NOTE | Migration `d5e6f7a8b9c0` uses manual cascading DELETEs (fragile but works) | `alembic/versions/` |

### Pipeline Reliability Agent — BLOCKERS FOUND

**Strengths observed**: `asyncio.shield` for finalization, crash-resilient enrichment pattern, idempotent re-scraping.

| # | Severity | Finding | File |
|---|----------|---------|------|
| PR-1 | IMPORTANT | Enrichment gated on scrape success — T-ROC transient failure skips backlog | `scheduler/jobs.py:74` |
| PR-2 | IMPORTANT | 3 broken scrapers waste 3.5 min/run on retries + log noise | `scrapers/orchestrator.py:457` |
| PR-3 | IMPORTANT | No timeout on Anthropic API calls (default 10 min) | `enrichment/pass1.py:64` |
| PR-4 | CRITICAL | No concurrent run guard between scheduler and API triggers | `scheduler/jobs.py:40` |
| PR-5 | IMPORTANT | In-memory scheduler state lost on restart (Issue #61) | `scheduler/jobs.py:26` |
| PR-6 | IMPORTANT | Workday single-transaction commit — crash loses full scrape | `scrapers/workday.py:406` |

### DevOps Agent — BLOCKERS FOUND

**Strengths observed**: Application code is production-quality. Dependencies well managed.

| # | Severity | Finding | File |
|---|----------|---------|------|
| DO-1 | CRITICAL | No systemd service files in repo (exist on Pi, not version-controlled) | Infrastructure |
| DO-2 | CRITICAL | Health endpoint doesn't check APScheduler state | `api/routes/health.py:16` |
| DO-3 | IMPORTANT | No log rotation configured | Infrastructure |
| DO-4 | IMPORTANT | No alerting on silent pipeline failures | `scheduler/jobs.py:40` |
| DO-5 | IMPORTANT | Graceful shutdown may orphan enrichment (default 30s systemd timeout) | `main.py:23` |
| DO-6 | IMPORTANT | No memory monitoring on 8GB Pi | Infrastructure |

### Business User Agent (Dana) — NOT READY

**Strengths observed**: Enrichment quality excellent (98/98, 100% success). Dashboard UX clean and non-technical. Data freshness indicators work well. Pipeline Controls give user autonomy.

| # | Type | Request |
|---|------|---------|
| BU-1 | BLOCKING | Fix 3 broken scrapers — can't do competitive intelligence with 1 company |
| BU-2 | BLOCKING | Add time-series posting volume chart |
| BU-3 | BLOCKING | Add brands rollup page with posting counts |
| BU-4 | REQUEST | Pay benchmarks summary page |
| BU-5 | REQUEST | CSV export from Posting Explorer |
| BU-6 | REQUEST | Scraper status health table on Pipeline Health |
| BU-7 | REQUEST | In-app feedback/flagging mechanism |
| BU-8 | REQUEST | Enrichment accuracy rollup metrics |
| BU-9 | REQUEST | Plain-English error summaries |

**CTO override on BU-1/BU-2/BU-3**: These are classified as DEFER-M3, not blockers. T-ROC data alone has value for validating the pipeline. Competitive analysis requires fixing scraper URLs, which is substantial reverse-engineering work. Dashboard enhancements need data to exist first. Deploy now, enhance during M3.
