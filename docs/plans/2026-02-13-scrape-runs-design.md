# scrape_runs Tracking Table — Design

**Issue:** #32
**Date:** 2026-02-13

## Purpose

Track pipeline run completeness per company. Enables safe `is_active` management (issue #5), daily monitoring (issue #12), and failure alerting (issue #24).

## Schema

```python
class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID]           # PK, uuid4
    company_id: Mapped[uuid.UUID]   # FK -> companies.id
    started_at: Mapped[datetime]    # timezone-aware
    completed_at: Mapped[datetime | None]
    status: Mapped[str]             # pending | completed | failed | partial
    pages_scraped: Mapped[int]      # default 0
    jobs_found: Mapped[int]         # default 0
    snapshots_created: Mapped[int]  # default 0
    errors: Mapped[dict | None]     # JSON column, nullable
    created_at: Mapped[datetime]    # server_default=func.now()
```

**Index:** `(company_id, started_at DESC)` for latest-run queries.

## Orchestrator Integration

1. Before calling `adapter.scrape()`, create a `ScrapeRun` row with `status=pending`
2. After `adapter.scrape()` returns, update the row with results from `ScrapeResult`
3. Map `ScrapeResult.success` -> `status=completed`, errors -> `status=failed`, partial -> `status=partial`

## Deferred

- `scrape_run_id` FK on `PostingSnapshot` — adds coupling, not needed yet
- `pages_expected` column — iCIMS doesn't know total pages upfront

## Files

- `src/compgraph/db/models.py` — add ScrapeRun model
- `alembic/versions/` — new migration
- `src/compgraph/scrapers/orchestrator.py` — create/update ScrapeRun per company
- `src/compgraph/scrapers/base.py` — add `pages_scraped` to ScrapeResult
- `tests/test_scrape_runs.py` — model lifecycle tests
- `tests/test_orchestrator.py` — update existing tests for ScrapeRun creation
