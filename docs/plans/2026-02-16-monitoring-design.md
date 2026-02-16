# Real-Time Monitoring UI Design

**Date**: 2026-02-16
**Status**: Approved
**Approach**: B — "Single Source of Truth" (DB-backed monitoring with dedicated status page)

## Problem

The first production run revealed that CompGraph's dashboard has critical monitoring gaps:
- No way to tell if the system is idle or active at a glance
- Enrichment pipeline has zero visibility (Issue #83)
- Scheduler-triggered runs invisible to Pipeline Controls (Issue #82 — in-memory state isolation)
- Enrichment run history lost on restart (Issue #68)
- Emoji shortcodes render as text instead of icons (Issue #81)

The pipeline infrastructure works correctly — all issues are visibility gaps.

## Design Decisions

1. **DB as source of truth** — status endpoints query `scrape_runs` and new `enrichment_runs` tables instead of relying solely on in-memory state
2. **Dedicated System Status landing page** — replaces current metrics-only landing, shows system state at a glance + drill-down per stage
3. **`enrichment_runs` table** — mirrors `scrape_runs` pattern, uses atomic increments for production-ready counter updates
4. **3-5s polling** — same pattern as existing Pipeline Controls auto-refresh, no SSE/WebSocket complexity
5. **Composite `/api/pipeline/status` endpoint** — single call feeds the entire landing page

## Section 1: `enrichment_runs` Table

```sql
CREATE TABLE enrichment_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    pass1_total     INTEGER NOT NULL DEFAULT 0,
    pass1_succeeded INTEGER NOT NULL DEFAULT 0,
    pass1_failed    INTEGER NOT NULL DEFAULT 0,
    pass1_skipped   INTEGER NOT NULL DEFAULT 0,
    pass2_total     INTEGER NOT NULL DEFAULT 0,
    pass2_succeeded INTEGER NOT NULL DEFAULT 0,
    pass2_failed    INTEGER NOT NULL DEFAULT 0,
    pass2_skipped   INTEGER NOT NULL DEFAULT 0,
    error_summary   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_enrichment_runs_status_started
    ON enrichment_runs (status, started_at DESC);
```

**Counter update pattern** — atomic increments for production safety:
```python
await session.execute(
    update(EnrichmentRun)
    .where(EnrichmentRun.id == run_id)
    .values(pass1_succeeded=EnrichmentRun.pass1_succeeded + 1)
)
```

**Orchestrator integration:**
- Run start: INSERT row with `status='running'`, `started_at=now()`
- During pass1: atomic increment `pass1_succeeded` / `pass1_failed` per posting
- Between passes: set `pass1_total` to final count, set `pass2_total`
- During pass2: atomic increment `pass2_succeeded` / `pass2_failed` per posting
- Run end: set `status='completed'|'failed'`, `finished_at=now()`, `error_summary` if failed

In-memory `_runs` dict stays as a fast cache. DB is the authoritative source.

## Section 2: Status API Changes

### Scrape Status — DB Fallback (`/api/scrape/status`)

**Current**: reads `_pipeline_runs` in-memory dict — broken for scheduler runs.

**New fallback chain:**
1. Check in-memory `_pipeline_runs` for active run (status=running)
2. If none, query `scrape_runs` for most recent run group (by `started_at DESC`), aggregate across companies
3. Return same `PipelineRunResponse` shape — no downstream changes

### Enrichment Status — DB Fallback (`/api/enrich/status`)

**Current**: reads `_runs` in-memory dict — no scheduler visibility, lost on restart.

**New fallback chain:**
1. Check in-memory `_runs` for active run
2. Fallback: query `enrichment_runs` for latest row
3. Return enrichment status with pass1/pass2 counters

### New: `/api/pipeline/status`

Single composite endpoint for the dashboard landing page.

```json
{
  "system_state": "idle | scraping | enriching | error",
  "scrape": {
    "status": "completed",
    "last_completed_at": "2026-02-16T20:15:00Z",
    "current_run": null
  },
  "enrich": {
    "status": "running",
    "last_completed_at": "2026-02-16T19:00:00Z",
    "current_run": {
      "run_id": "...",
      "pass1_succeeded": 250,
      "pass1_total": 705,
      "pass2_succeeded": 0,
      "pass2_total": 0,
      "started_at": "2026-02-16T20:16:00Z"
    }
  },
  "scheduler": {
    "enabled": true,
    "next_run_at": "2026-02-17T06:00:00Z"
  }
}
```

**`system_state` derivation**: running stage → active state name; most recent failed → `error`; otherwise `idle`.

## Section 3: System Status Landing Page

Replaces current `main.py` metrics-only landing page.

### Layout (top to bottom)

**1. System State Banner** — full-width colored bar:
- Green "System Idle" — nothing running, last runs succeeded
- Blue "Scraping..." / "Enriching..." — active stage with elapsed time
- Red "Error" — last run failed, one-line summary

**2. Stage Cards** — two columns:

| Scrape Card | Enrichment Card |
|-------------|-----------------|
| Status: Idle / Running / Failed | Status: Idle / Running / Failed |
| Last completed: relative time | Last completed: relative time |
| Result summary (companies, postings) | Result summary (pass1/pass2 counts) |
| If running: progress bar + per-company table | If running: progress bar + pass counters |

Progress bars derive from counters (e.g., `pass1_succeeded / pass1_total`).

**3. Scheduler Row** — next run time, last result, Trigger Now button

**4. Data Freshness** — per-company last-scraped timestamps + enrichment coverage (relocated from current landing page)

### Polling Strategy
- 5s interval when any stage is `running`
- 30s interval when all stages are `idle`
- Single `/api/pipeline/status` call feeds banner + both cards
- Same `st.empty()` + `time.sleep()` pattern as Pipeline Controls

### Other Page Changes
- Pipeline Health: no changes (keeps historical run table)
- Pipeline Controls: no changes (API fallback fixes #82 transparently)
- Scheduler: no changes (keeps schedule management)
- Posting Explorer: no changes

## Section 4: Bug Fixes Bundled

| Issue | Fix | Mechanism |
|-------|-----|-----------|
| #81 Emoji shortcodes | Replace `:green_circle:` with Unicode `🟢🔴🟡` | All dashboard pages |
| #82 Scheduler run visibility | API fallback to `scrape_runs` DB table | Scrape status endpoint |
| #83 No enrichment visibility | System Status page + enrichment stage card | New landing page |
| #68 Enrichment history lost | `enrichment_runs` DB table | Alembic migration |

## Out of Scope (YAGNI)

- SSE/WebSocket push — polling is sufficient at current scale
- Multi-worker shared state beyond DB (Issue #61)
- Concurrent run guards (Issue #60)
- Aggregation stage monitoring (no aggregation pipeline yet)
- Auth/permissions for dashboard controls
