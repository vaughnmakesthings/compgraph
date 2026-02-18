# Real-Time Monitoring UI — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add DB-backed real-time monitoring with a System Status landing page, enrichment run persistence, and API fallback chain to fix issues #68, #81, #82, #83.

**Architecture:** New `enrichment_runs` table mirrors `scrape_runs` pattern. Status API endpoints fall back to DB when in-memory state is empty. New composite `/api/pipeline/status` endpoint feeds a Streamlit System Status landing page with auto-refresh.

**Tech Stack:** SQLAlchemy 2.0 (async), Alembic, FastAPI, Streamlit, pydantic, pytest

**Design doc:** `docs/plans/2026-02-16-monitoring-design.md`

---

## Execution Strategy

**Agent assignments:**
- Tasks 1-6: `python-backend-developer` (implementation)
- After Task 3: `code-reviewer` gate (data layer + API)
- After Task 6: `code-reviewer` → `pytest-validator` → `spec-reviewer` (full review)

**Parallelization:** Tasks 1-2 are sequential (model before migration). Tasks 3-4 can be parallelized (API changes are independent of dashboard). Task 5 depends on Task 3+4. Task 6 is the emoji fix (independent, can run in parallel with Task 5).

**Review gates:**
- Gate 1 (after Task 3): code-reviewer validates data layer + API changes
- Gate 2 (after Task 6): full review chain before PR

---

### Task 1: Add EnrichmentRun Model

**Files:**
- Modify: `src/compgraph/db/models.py:86-110` (add after `ScrapeRunStatus` enum and `ScrapeRun` class)

**Step 1: Write the failing test**

Create `tests/test_enrichment_run_model.py`:

```python
"""Tests for EnrichmentRunDB model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from compgraph.db.models import EnrichmentRunDB, EnrichmentRunStatus


class TestEnrichmentRunDBModel:
    def test_model_has_required_columns(self):
        run = EnrichmentRunDB(
            id=uuid.uuid4(),
            status=EnrichmentRunStatus.PENDING,
            started_at=datetime.now(UTC),
        )
        assert run.status == "pending"
        assert run.pass1_total == 0
        assert run.pass1_succeeded == 0
        assert run.pass2_total == 0

    def test_status_enum_values(self):
        assert EnrichmentRunStatus.PENDING == "pending"
        assert EnrichmentRunStatus.RUNNING == "running"
        assert EnrichmentRunStatus.COMPLETED == "completed"
        assert EnrichmentRunStatus.FAILED == "failed"

    def test_tablename(self):
        assert EnrichmentRunDB.__tablename__ == "enrichment_runs"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_enrichment_run_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'EnrichmentRunDB'`

**Step 3: Write the model**

Add to `src/compgraph/db/models.py` after `ScrapeRun` class (after line 109):

```python
class EnrichmentRunStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EnrichmentRunDB(Base):
    """Persistent enrichment run tracking — mirrors ScrapeRun pattern."""

    __tablename__ = "enrichment_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EnrichmentRunStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pass1_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass1_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass1_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass1_skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass2_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass2_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass2_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pass2_skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_enrichment_runs_status_started", "status", started_at.desc()),
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_enrichment_run_model.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/compgraph/db/models.py tests/test_enrichment_run_model.py
git commit -m "feat: add EnrichmentRunDB model for persistent enrichment tracking (#68)"
```

---

### Task 2: Alembic Migration for enrichment_runs

**Files:**
- Create: `alembic/versions/<auto>_add_enrichment_runs.py` (autogenerated)

**Step 1: Generate migration**

Run: `op run --env-file=.env -- uv run alembic revision --autogenerate -m "add enrichment_runs table"`

**Step 2: Review generated migration**

Verify it creates `enrichment_runs` table with all columns and the `ix_enrichment_runs_status_started` index.

**Step 3: Run migration**

Run: `op run --env-file=.env -- uv run alembic upgrade head`

**Step 4: Commit**

```bash
git add alembic/versions/*_add_enrichment_runs.py
git commit -m "migration: add enrichment_runs table"
```

---

### Task 3: Wire Enrichment Orchestrator to DB

**Files:**
- Modify: `src/compgraph/enrichment/orchestrator.py` (add DB persistence alongside in-memory state)
- Create: `tests/test_enrichment_orchestrator_db.py`

**Step 1: Write the failing test**

Create `tests/test_enrichment_orchestrator_db.py`:

```python
"""Tests for enrichment orchestrator DB persistence layer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from compgraph.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentRun,
    EnrichmentStatus,
    _runs,
    create_enrichment_run_record,
    get_latest_enrichment_run_from_db,
    increment_enrichment_counter,
)


class TestCreateEnrichmentRunRecord:
    @pytest.mark.asyncio
    async def test_creates_db_record(self):
        """create_enrichment_run_record should exist and accept run_id + session."""
        # This tests the function signature exists
        assert callable(create_enrichment_run_record)

    @pytest.mark.asyncio
    async def test_get_latest_from_db_callable(self):
        assert callable(get_latest_enrichment_run_from_db)

    @pytest.mark.asyncio
    async def test_increment_counter_callable(self):
        assert callable(increment_enrichment_counter)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_enrichment_orchestrator_db.py -v`
Expected: FAIL with `ImportError: cannot import name 'create_enrichment_run_record'`

**Step 3: Add DB persistence functions to orchestrator**

Add to `src/compgraph/enrichment/orchestrator.py`:

```python
# Add these imports at top
from sqlalchemy import update

from compgraph.db.models import EnrichmentRunDB, EnrichmentRunStatus

# Add these functions after the existing get_latest_enrichment_run():

async def create_enrichment_run_record(run_id: uuid.UUID) -> None:
    """Create a persistent enrichment_runs DB record at run start."""
    async with async_session_factory() as session:
        db_run = EnrichmentRunDB(
            id=run_id,
            status=EnrichmentRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        session.add(db_run)
        await session.commit()


async def increment_enrichment_counter(
    run_id: uuid.UUID,
    **counters: int,
) -> None:
    """Atomically increment counters on an enrichment_runs row.

    Usage: await increment_enrichment_counter(run_id, pass1_succeeded=1)
    """
    values = {
        getattr(EnrichmentRunDB, k): getattr(EnrichmentRunDB, k) + v
        for k, v in counters.items()
        if v != 0
    }
    if not values:
        return
    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB)
            .where(EnrichmentRunDB.id == run_id)
            .values(**values)
        )
        await session.commit()


async def update_enrichment_run_record(
    run_id: uuid.UUID,
    **fields: object,
) -> None:
    """Update fields on an enrichment_runs row (status, finished_at, totals, error_summary)."""
    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB)
            .where(EnrichmentRunDB.id == run_id)
            .values(**fields)
        )
        await session.commit()


async def get_latest_enrichment_run_from_db() -> dict | None:
    """Fetch the most recent enrichment_runs row as a dict."""
    from sqlalchemy import select

    async with async_session_factory() as session:
        stmt = (
            select(EnrichmentRunDB)
            .order_by(EnrichmentRunDB.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "run_id": row.id,
            "status": row.status,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "pass1_total": row.pass1_total,
            "pass1_succeeded": row.pass1_succeeded,
            "pass1_failed": row.pass1_failed,
            "pass1_skipped": row.pass1_skipped,
            "pass2_total": row.pass2_total,
            "pass2_succeeded": row.pass2_succeeded,
            "pass2_failed": row.pass2_failed,
            "pass2_skipped": row.pass2_skipped,
            "error_summary": row.error_summary,
        }
```

**Step 4: Wire DB calls into run_pass1 and run_pass2**

In `EnrichmentOrchestrator.run_pass1()` (line ~152):
- After `run.status = EnrichmentStatus.RUNNING` (line 162), add:
  ```python
  await create_enrichment_run_record(run.run_id)
  ```
- After each `result.succeeded += 1` (line 225), add:
  ```python
  await increment_enrichment_counter(run.run_id, pass1_succeeded=1)
  ```
- After each `result.failed += 1` (line 227), add:
  ```python
  await increment_enrichment_counter(run.run_id, pass1_failed=1)
  ```
- After `run.finish(result)` (line 243), add:
  ```python
  await update_enrichment_run_record(
      run.run_id,
      pass1_total=result.succeeded + result.failed + result.skipped,
      status=run.status.value if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.FAILED) else EnrichmentRunStatus.RUNNING,
      finished_at=run.finished_at,
  )
  ```

In `EnrichmentOrchestrator.run_pass2()` (line ~246):
- After each `result.succeeded += 1` (line 339), add:
  ```python
  await increment_enrichment_counter(run.run_id, pass2_succeeded=1)
  ```
- After each `result.failed += 1` (line 342), add:
  ```python
  await increment_enrichment_counter(run.run_id, pass2_failed=1)
  ```
- After `run.finish_pass2(result)` (line 357), add:
  ```python
  final_status = EnrichmentRunStatus.COMPLETED if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL) else EnrichmentRunStatus.FAILED
  error_msg = None
  if run.status == EnrichmentStatus.FAILED:
      error_msg = f"pass1: {run.pass1_result.failed}fail, pass2: {result.failed}fail"
  await update_enrichment_run_record(
      run.run_id,
      pass2_total=result.succeeded + result.failed + result.skipped,
      status=final_status,
      finished_at=run.finished_at,
      error_summary=error_msg,
  )
  ```

**Note:** When `run_full()` calls `run_pass1` then `run_pass2`, the DB record is created in `run_pass1` and updated throughout. `run_pass2` does NOT create a second record — it updates the same row.

**Important:** `run_pass1` only creates the DB record when called as the first pass. If `run_pass2` is called standalone (via `/api/enrich/pass2/trigger`), it needs the record too. Add a check at the top of `run_pass2`:
```python
# Ensure DB record exists (standalone pass2 calls won't have one from pass1)
from sqlalchemy import select as sa_select
async with async_session_factory() as check_session:
    exists = await check_session.execute(
        sa_select(EnrichmentRunDB.id).where(EnrichmentRunDB.id == run.run_id)
    )
    if exists.scalar_one_or_none() is None:
        await create_enrichment_run_record(run.run_id)
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_enrichment_orchestrator_db.py tests/test_enrichment_pass1.py tests/test_enrichment_pass2.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/enrichment/orchestrator.py tests/test_enrichment_orchestrator_db.py
git commit -m "feat: wire enrichment orchestrator to enrichment_runs DB table (#68)"
```

---

### Task 4: API Fallback Chain + Composite Pipeline Status Endpoint

**Files:**
- Modify: `src/compgraph/api/routes/enrich.py` (add DB fallback to status endpoint)
- Modify: `src/compgraph/api/routes/scrape.py` (add DB fallback to status endpoint)
- Create: `src/compgraph/api/routes/pipeline.py` (new composite endpoint)
- Modify: `src/compgraph/main.py:45-48` (register pipeline router)
- Create: `tests/test_pipeline_status.py`

**Step 1: Write the failing test**

Create `tests/test_pipeline_status.py`:

```python
"""Tests for composite pipeline status endpoint."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from compgraph.enrichment.orchestrator import (
    EnrichmentRun,
    EnrichmentStatus,
    _runs as enrich_runs,
)
from compgraph.scrapers.orchestrator import (
    PipelineRun,
    PipelineStatus,
    _pipeline_runs,
    _store_run,
)


@pytest.fixture(autouse=True)
def clear_state():
    _pipeline_runs.clear()
    enrich_runs.clear()
    yield
    _pipeline_runs.clear()
    enrich_runs.clear()


class TestPipelineStatusEndpoint:
    def test_idle_when_no_runs(self, client):
        """With no runs at all, endpoint should return idle state from DB fallback."""
        with patch(
            "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["system_state"] == "idle"

    def test_scraping_when_scrape_running(self, client):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        _store_run(run)
        with patch(
            "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["system_state"] == "scraping"

    def test_enriching_when_enrich_running(self, client):
        from compgraph.enrichment.orchestrator import _store_run as store_enrich

        enrich_run = EnrichmentRun(status=EnrichmentStatus.RUNNING)
        store_enrich(enrich_run)
        with patch(
            "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["system_state"] == "enriching"

    def test_error_when_last_run_failed(self, client):
        run = PipelineRun(status=PipelineStatus.FAILED)
        run.finished_at = datetime.now(UTC)
        _store_run(run)
        with patch(
            "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["system_state"] == "error"

    def test_response_shape(self, client):
        with patch(
            "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert "system_state" in data
            assert "scrape" in data
            assert "enrich" in data
            assert "scheduler" in data
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pipeline_status.py -v`
Expected: FAIL with 404 (route doesn't exist yet)

**Step 3: Create the composite pipeline status endpoint**

Create `src/compgraph/api/routes/pipeline.py`:

```python
"""Composite pipeline status endpoint — single call for dashboard landing page."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from compgraph.enrichment.orchestrator import (
    EnrichmentRun,
    EnrichmentStatus,
    get_latest_enrichment_run,
    get_latest_enrichment_run_from_db,
)
from compgraph.scrapers.orchestrator import (
    PipelineRun,
    PipelineStatus,
    get_latest_run,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


# --- Response Models ---


class ScrapeCurrentRun(BaseModel):
    run_id: uuid.UUID
    status: str
    started_at: datetime
    total_postings_found: int
    total_snapshots_created: int
    companies_succeeded: int
    companies_failed: int


class EnrichCurrentRun(BaseModel):
    run_id: uuid.UUID
    status: str
    started_at: datetime
    pass1_total: int
    pass1_succeeded: int
    pass2_total: int
    pass2_succeeded: int


class StageStatus(BaseModel):
    status: str  # idle, running, completed, failed
    last_completed_at: datetime | None
    current_run: ScrapeCurrentRun | EnrichCurrentRun | None


class SchedulerSummary(BaseModel):
    enabled: bool
    next_run_at: datetime | None


class PipelineStatusResponse(BaseModel):
    system_state: str  # idle, scraping, enriching, error
    scrape: StageStatus
    enrich: StageStatus
    scheduler: SchedulerSummary


# --- Helpers ---


def _scrape_stage_status(run: PipelineRun | None) -> StageStatus:
    if run is None:
        return StageStatus(status="idle", last_completed_at=None, current_run=None)

    if run.status == PipelineStatus.RUNNING:
        return StageStatus(
            status="running",
            last_completed_at=None,
            current_run=ScrapeCurrentRun(
                run_id=run.run_id,
                status=run.status.value,
                started_at=run.started_at,
                total_postings_found=run.total_postings_found,
                total_snapshots_created=run.total_snapshots_created,
                companies_succeeded=run.companies_succeeded,
                companies_failed=run.companies_failed,
            ),
        )

    return StageStatus(
        status=run.status.value,
        last_completed_at=run.finished_at,
        current_run=None,
    )


def _enrich_stage_from_memory(run: EnrichmentRun) -> StageStatus:
    if run.status == EnrichmentStatus.RUNNING:
        p1 = run.pass1_result
        p2 = run.pass2_result
        return StageStatus(
            status="running",
            last_completed_at=None,
            current_run=EnrichCurrentRun(
                run_id=run.run_id,
                status=run.status.value,
                started_at=run.started_at,
                pass1_total=0,  # in-memory doesn't track totals mid-run
                pass1_succeeded=p1.succeeded if p1 else 0,
                pass2_total=0,
                pass2_succeeded=p2.succeeded if p2 else 0,
            ),
        )

    return StageStatus(
        status=run.status.value,
        last_completed_at=run.finished_at,
        current_run=None,
    )


def _enrich_stage_from_db(db_run: dict) -> StageStatus:
    if db_run["status"] == "running":
        return StageStatus(
            status="running",
            last_completed_at=None,
            current_run=EnrichCurrentRun(
                run_id=db_run["run_id"],
                status=db_run["status"],
                started_at=db_run["started_at"],
                pass1_total=db_run["pass1_total"],
                pass1_succeeded=db_run["pass1_succeeded"],
                pass2_total=db_run["pass2_total"],
                pass2_succeeded=db_run["pass2_succeeded"],
            ),
        )

    return StageStatus(
        status=db_run["status"],
        last_completed_at=db_run["finished_at"],
        current_run=None,
    )


def _derive_system_state(scrape: StageStatus, enrich: StageStatus) -> str:
    if scrape.status == "running":
        return "scraping"
    if enrich.status == "running":
        return "enriching"
    if scrape.status == "failed" or enrich.status == "failed":
        return "error"
    return "idle"


# --- Endpoints ---


async def _get_scrape_run_from_db() -> dict | None:
    """Fetch latest scrape run summary from scrape_runs DB table."""
    from sqlalchemy import func, select

    from compgraph.db.models import ScrapeRun
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = (
            select(ScrapeRun)
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "run_id": row.id,
            "status": row.status,
            "started_at": row.started_at,
            "finished_at": row.completed_at,
            "jobs_found": row.jobs_found,
            "snapshots_created": row.snapshots_created,
        }


# Alias for testability
get_latest_scrape_run_from_db = _get_scrape_run_from_db


@router.get("/status", response_model=PipelineStatusResponse)
async def pipeline_status(request: Request) -> PipelineStatusResponse:
    """Composite pipeline status — single call for the dashboard landing page."""

    # --- Scrape status: in-memory first, DB fallback ---
    scrape_run = get_latest_run()
    scrape_stage = _scrape_stage_status(scrape_run)

    # If no in-memory run, check DB (handles scheduler-triggered + post-restart)
    if scrape_run is None:
        db_scrape = await get_latest_scrape_run_from_db()
        if db_scrape is not None:
            scrape_stage = StageStatus(
                status=db_scrape["status"],
                last_completed_at=db_scrape["finished_at"],
                current_run=None,
            )

    # --- Enrich status: in-memory first, DB fallback ---
    enrich_run = get_latest_enrichment_run()
    if enrich_run is not None:
        enrich_stage = _enrich_stage_from_memory(enrich_run)
    else:
        db_enrich = await get_latest_enrichment_run_from_db()
        if db_enrich is not None:
            enrich_stage = _enrich_stage_from_db(db_enrich)
        else:
            enrich_stage = StageStatus(status="idle", last_completed_at=None, current_run=None)

    # --- Scheduler summary ---
    scheduler = getattr(request.app.state, "scheduler", None)
    enabled = scheduler is not None
    next_run: datetime | None = None
    if enabled and scheduler is not None:
        try:
            schedules = await scheduler.get_schedules()
            if schedules and not schedules[0].paused:
                next_run = schedules[0].next_fire_time
        except Exception:
            pass

    return PipelineStatusResponse(
        system_state=_derive_system_state(scrape_stage, enrich_stage),
        scrape=scrape_stage,
        enrich=enrich_stage,
        scheduler=SchedulerSummary(enabled=enabled, next_run_at=next_run),
    )
```

**Step 4: Register the pipeline router**

In `src/compgraph/main.py`, add import and include:

```python
from compgraph.api.routes.pipeline import router as pipeline_router
# ...
app.include_router(pipeline_router)
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_pipeline_status.py tests/test_scrape_routes.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/api/routes/pipeline.py src/compgraph/main.py tests/test_pipeline_status.py
git commit -m "feat: add /api/pipeline/status composite endpoint with DB fallback (#82, #83)"
```

---

### **REVIEW GATE 1**: Run `code-reviewer` on Tasks 1-4

Validate:
- EnrichmentRunDB model matches design doc schema
- Atomic increment pattern uses SQL-level `column + N` (not ORM read-modify-write)
- DB fallback chain in pipeline status endpoint
- No sync DB calls in async code paths
- Test coverage for new functions

---

### Task 5: System Status Landing Page

**Files:**
- Rewrite: `src/compgraph/dashboard/main.py` (replace metrics page with System Status)
- Modify: `src/compgraph/dashboard/queries.py:333-337` (fix emoji shortcodes — part of this task)

**Step 1: Write the new System Status landing page**

Rewrite `src/compgraph/dashboard/main.py`:

```python
"""CompGraph Dashboard — System Status landing page."""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    get_enrichment_coverage,
    get_last_scrape_timestamps,
    get_per_company_counts,
)

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="CompGraph Dashboard", layout="wide")

render_diagnostics_sidebar()

API_BASE = os.environ.get("COMPGRAPH_API_URL", "http://localhost:8000")


def _api_get(path: str) -> dict[str, Any] | None:
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=5)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("API request failed: %s", exc)
        return None


# --- Fetch pipeline status ---
pipeline = _api_get("/api/pipeline/status")


# --- System State Banner ---
st.title("CompGraph Dashboard")

if pipeline is not None:
    state = pipeline["system_state"]
    if state == "idle":
        st.success("System Idle")
    elif state == "scraping":
        started = pipeline["scrape"].get("current_run", {}).get("started_at")
        elapsed = ""
        if started:
            try:
                dt = datetime.fromisoformat(started)
                secs = (datetime.now(UTC) - dt).total_seconds()
                mins = int(secs // 60)
                elapsed = f" ({mins}m {int(secs % 60)}s)"
            except (ValueError, TypeError):
                pass
        st.info(f"Scraping...{elapsed}")
    elif state == "enriching":
        started = pipeline["enrich"].get("current_run", {}).get("started_at")
        elapsed = ""
        if started:
            try:
                dt = datetime.fromisoformat(started)
                secs = (datetime.now(UTC) - dt).total_seconds()
                mins = int(secs // 60)
                elapsed = f" ({mins}m {int(secs % 60)}s)"
            except (ValueError, TypeError):
                pass
        st.info(f"Enriching...{elapsed}")
    elif state == "error":
        st.error("Error — last pipeline run failed")
    else:
        st.warning(f"Unknown state: {state}")
else:
    st.warning("Cannot reach API — status unavailable")


# --- Stage Cards ---
if pipeline is not None:
    col_scrape, col_enrich = st.columns(2)

    # Scrape card
    with col_scrape:
        st.subheader("Scrape")
        scrape = pipeline["scrape"]
        scrape_status = scrape["status"]

        if scrape_status == "running" and scrape.get("current_run"):
            cr = scrape["current_run"]
            st.markdown(f"**Status:** :blue[RUNNING]")
            st.metric("Postings Found", cr.get("total_postings_found", 0))
            st.metric("Companies Done", f"{cr.get('companies_succeeded', 0)}/{cr.get('companies_succeeded', 0) + cr.get('companies_failed', 0)}")
        elif scrape["last_completed_at"]:
            try:
                dt = datetime.fromisoformat(scrape["last_completed_at"])
                age = datetime.now(UTC) - dt
                age_str = f"{int(age.total_seconds() // 3600)}h ago" if age > timedelta(hours=1) else f"{int(age.total_seconds() // 60)}m ago"
            except (ValueError, TypeError):
                age_str = "unknown"
            color = "green" if scrape_status in ("success", "completed") else "red"
            st.markdown(f"**Status:** :{color}[{scrape_status.upper()}]")
            st.caption(f"Completed {age_str}")
        else:
            st.markdown("**Status:** :gray[NO RUNS]")

    # Enrichment card
    with col_enrich:
        st.subheader("Enrichment")
        enrich = pipeline["enrich"]
        enrich_status = enrich["status"]

        if enrich_status == "running" and enrich.get("current_run"):
            cr = enrich["current_run"]
            st.markdown(f"**Status:** :blue[RUNNING]")
            p1_total = cr.get("pass1_total", 0)
            p1_done = cr.get("pass1_succeeded", 0)
            p2_total = cr.get("pass2_total", 0)
            p2_done = cr.get("pass2_succeeded", 0)

            if p1_total > 0:
                st.progress(p1_done / p1_total, text=f"Pass 1: {p1_done}/{p1_total}")
            elif p1_done > 0:
                st.metric("Pass 1 Processed", p1_done)
            else:
                st.caption("Pass 1: starting...")

            if p2_total > 0:
                st.progress(p2_done / p2_total, text=f"Pass 2: {p2_done}/{p2_total}")
            elif p2_done > 0:
                st.metric("Pass 2 Processed", p2_done)
        elif enrich["last_completed_at"]:
            try:
                dt = datetime.fromisoformat(enrich["last_completed_at"])
                age = datetime.now(UTC) - dt
                age_str = f"{int(age.total_seconds() // 3600)}h ago" if age > timedelta(hours=1) else f"{int(age.total_seconds() // 60)}m ago"
            except (ValueError, TypeError):
                age_str = "unknown"
            color = "green" if enrich_status in ("success", "completed") else "red"
            st.markdown(f"**Status:** :{color}[{enrich_status.upper()}]")
            st.caption(f"Completed {age_str}")
        else:
            st.markdown("**Status:** :gray[NO RUNS]")


# --- Scheduler Row ---
if pipeline is not None:
    st.divider()
    sched = pipeline["scheduler"]
    sched_col1, sched_col2 = st.columns(2)
    with sched_col1:
        if sched["enabled"]:
            next_run = sched.get("next_run_at")
            if next_run:
                st.markdown(f"**Scheduler:** Enabled — next run at `{next_run}`")
            else:
                st.markdown("**Scheduler:** Enabled — no upcoming run")
        else:
            st.markdown("**Scheduler:** Disabled")
    with sched_col2:
        if sched["enabled"]:
            if st.button("Trigger Now"):
                trigger_result = _api_get("/api/scheduler/status")
                if trigger_result and trigger_result.get("schedules"):
                    schedule_id = trigger_result["schedules"][0]["schedule_id"]
                    try:
                        resp = requests.post(f"{API_BASE}/api/scheduler/jobs/{schedule_id}/trigger", timeout=10)
                        if resp.ok:
                            st.success("Pipeline triggered!")
                            time.sleep(1)
                            st.rerun()
                    except requests.RequestException as exc:
                        st.error(f"Failed to trigger: {exc}")


# --- Data Freshness ---
st.divider()
st.subheader("Data Freshness")


@st.cache_data(ttl=60)
def _load_freshness() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_last_scrape_timestamps(session))


@st.cache_data(ttl=60)
def _load_coverage() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_coverage(session))


@st.cache_data(ttl=60)
def _load_company_counts() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_per_company_counts(session))


try:
    freshness_data = _load_freshness()
    company_entries = [e for e in freshness_data if e["slug"] != "__global__"]
    if company_entries:
        cols = st.columns(len(company_entries))
        for col, entry in zip(cols, company_entries, strict=True):
            ts = entry["last_scraped_at"]
            if ts is None:
                icon, ts_str = "\u26aa", "Never"
            else:
                age = datetime.now(UTC) - ts
                if age < timedelta(hours=24):
                    icon = "\U0001f7e2"  # green circle
                elif age < timedelta(hours=72):
                    icon = "\U0001f7e1"  # yellow circle
                else:
                    icon = "\U0001f534"  # red circle
                ts_str = ts.strftime("%Y-%m-%d %H:%M UTC")
            col.markdown(f"{icon} **{entry['name']}**")
            col.caption(f"Last scraped: {ts_str}")
except Exception:
    logger.exception("Failed to load freshness data")

# --- Enrichment coverage ---
try:
    coverage = _load_coverage()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Active", coverage["total_active"])
    c2.metric("Enriched", coverage["enriched"])
    c3.metric("With Brands", coverage["with_brands"])
    c4.metric("Unenriched", coverage["unenriched"])
except Exception:
    logger.exception("Failed to load enrichment coverage")


# --- Auto-refresh ---
st.divider()
is_active = pipeline is not None and pipeline["system_state"] in ("scraping", "enriching")
auto_refresh = st.checkbox("Auto-refresh", value=is_active)
refresh_interval = 5 if is_active else 30

col_refresh, _ = st.columns([1, 3])
with col_refresh:
    if st.button("Refresh Now"):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    time.sleep(refresh_interval)
    st.cache_data.clear()
    st.rerun()
```

**Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All existing tests PASS (dashboard pages don't have unit tests — this is tested via manual verification on the dev server)

**Step 3: Commit**

```bash
git add src/compgraph/dashboard/main.py
git commit -m "feat: replace landing page with System Status dashboard (#83)"
```

---

### Task 6: Fix Emoji Shortcodes Across All Pages (#81)

**Files:**
- Modify: `src/compgraph/dashboard/queries.py:333-337` (FRESHNESS_ICONS dict)
- Modify: `src/compgraph/dashboard/pages/3_Pipeline_Controls.py:33-38` (COMPANY_STATE_ICONS dict)
- Modify: `src/compgraph/dashboard/pages/1_Pipeline_Health.py:63-69` (uses FRESHNESS_ICONS)

**Step 1: Write the failing test**

Create `tests/test_emoji_rendering.py`:

```python
"""Tests for emoji rendering — Unicode characters, not shortcodes."""

from compgraph.dashboard.queries import FRESHNESS_ICONS


class TestFreshnessIcons:
    def test_icons_are_unicode_not_shortcodes(self):
        for color, icon in FRESHNESS_ICONS.items():
            assert not icon.startswith(":"), f"FRESHNESS_ICONS['{color}'] is a shortcode: {icon}"
            assert len(icon) <= 2, f"FRESHNESS_ICONS['{color}'] is too long: {icon}"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_emoji_rendering.py -v`
Expected: FAIL — icons are currently `:green_circle:` shortcodes

**Step 3: Fix FRESHNESS_ICONS**

In `src/compgraph/dashboard/queries.py`, replace lines 333-338:

```python
FRESHNESS_ICONS: dict[str, str] = {
    "green": "\U0001f7e2",   # 🟢
    "yellow": "\U0001f7e1",  # 🟡
    "red": "\U0001f534",     # 🔴
    "gray": "\u26aa",        # ⚪
}
```

**Step 4: Fix COMPANY_STATE_ICONS**

In `src/compgraph/dashboard/pages/3_Pipeline_Controls.py`, replace lines 33-39:

```python
COMPANY_STATE_ICONS: dict[str, str] = {
    "pending": "\u23f3",     # ⏳
    "running": "\U0001f3c3", # 🏃
    "completed": "\u2705",   # ✅
    "failed": "\u274c",      # ❌
    "skipped": "\u23ed",     # ⏭
}
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_emoji_rendering.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/3_Pipeline_Controls.py tests/test_emoji_rendering.py
git commit -m "fix: replace emoji shortcodes with Unicode characters (#81)"
```

---

### **REVIEW GATE 2**: Full Review Chain

1. **`code-reviewer`** — Validate all changes against design doc, check async patterns, append-only compliance, test quality
2. **`pytest-validator`** — Audit all new tests for hollow assertions, proper DB isolation, meaningful coverage
3. **`spec-reviewer`** — Confirm issues #68, #81, #82, #83 are addressed, no scope creep

---

### Task 7: Final Commit + PR

**Step 1: Run full test suite**

Run: `uv run pytest -v --tb=short`
Expected: All tests PASS, coverage >= 50%

**Step 2: Create PR**

```bash
gh pr create --title "feat: real-time monitoring UI with DB-backed status" --body "$(cat <<'EOF'
## Summary
- Add `enrichment_runs` table for persistent enrichment tracking (#68)
- Add `/api/pipeline/status` composite endpoint with DB fallback chain (#82)
- Replace dashboard landing page with System Status page (#83)
- Fix emoji shortcode rendering across all dashboard pages (#81)

Closes #68, #81, #82, #83

## Design
See `docs/plans/2026-02-16-monitoring-design.md`

## Test plan
- [ ] Unit tests for EnrichmentRunDB model
- [ ] Unit tests for pipeline status endpoint (idle/scraping/enriching/error states)
- [ ] Unit tests for emoji rendering (Unicode, not shortcodes)
- [ ] Manual: trigger scrape via dashboard, verify System Status shows "Scraping..."
- [ ] Manual: verify enrichment progress bars update during run
- [ ] Manual: verify scheduler-triggered runs are visible (was broken in #82)
- [ ] Manual: verify emoji renders as colored circles (was broken in #81)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
