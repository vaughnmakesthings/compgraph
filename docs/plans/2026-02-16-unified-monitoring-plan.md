# Unified Monitoring & Dashboard Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all first-run dashboard visibility bugs (#68, #81, #82, #83, BUG-4, BUG-5) and add real-time monitoring via DB-backed status, a composite API endpoint, and a System Status landing page.

**Architecture:** New `enrichment_runs` table mirrors `scrape_runs`. Enrichment orchestrator writes atomic counter increments to DB during runs. New composite `/api/pipeline/status` endpoint aggregates in-memory + DB state. System Status replaces current landing page. Pipeline Controls switches from broken in-memory API to direct DB queries. All dashboard emoji shortcodes replaced with Unicode.

**Tech Stack:** SQLAlchemy 2.0 (async + sync), Alembic, FastAPI, Streamlit, pydantic, pytest

**Branch:** `feat/first-run-fixes` (exists — has design + plan docs committed)

**Design doc:** `docs/plans/2026-02-16-monitoring-design.md`

**Supersedes:** `docs/plans/2026-02-16-monitoring-implementation.md` and `docs/plans/2026-02-16-dashboard-bug-fixes.md`

---

## Execution Strategy

**Agent assignments:**
- Tasks 1-9: `python-backend-developer` (implementation)
- Review Gate 1 (after Task 3): `code-reviewer` — data layer validation
- Review Gate 2 (after Task 7): `code-reviewer` — dashboard fixes
- Review Gate 3 (after Task 9): `code-reviewer` → `pytest-validator` → `spec-reviewer` — full chain

**Parallelization:**
- Tasks 1-3: **Sequential** (model → migration → orchestrator wiring)
- Tasks 4-7: **Parallel** (independent dashboard fixes touching different files/sections)
- Tasks 8-9: **Sequential** (API endpoint → landing page that consumes it)

**Conflict avoidance for parallel Tasks 4-7:**
- Task 4: `queries.py:333-338` (FRESHNESS_ICONS dict) + `3_Pipeline_Controls.py:33-39` (COMPANY_STATE_ICONS dict)
- Task 5: `queries.py:86-87` (get_recent_scrape_runs dict keys) + `1_Pipeline_Health.py:108` (_style_row)
- Task 6: `queries.py` new function ~line 97 + `3_Pipeline_Controls.py:68-76` (status fetch)
- Task 7: `queries.py` new function ~line 127 + `1_Pipeline_Health.py:89+` (new section)
- **No overlapping line ranges** — safe to parallelize

---

## Phase 1: Data Layer (Sequential)

### Task 1: Add EnrichmentRunDB Model

**Files:**
- Modify: `src/compgraph/db/models.py:86-109` (add after ScrapeRun class)
- Create: `tests/test_enrichment_run_model.py`

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

Verify it creates `enrichment_runs` table with all 14 columns and the `ix_enrichment_runs_status_started` index.

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
- Modify: `src/compgraph/enrichment/orchestrator.py`
- Create: `tests/test_enrichment_orchestrator_db.py`

**Step 1: Write the failing test**

Create `tests/test_enrichment_orchestrator_db.py`:

```python
"""Tests for enrichment orchestrator DB persistence functions."""

from __future__ import annotations

from compgraph.enrichment.orchestrator import (
    create_enrichment_run_record,
    get_latest_enrichment_run_from_db,
    increment_enrichment_counter,
    update_enrichment_run_record,
)


class TestDbPersistenceFunctions:
    def test_create_enrichment_run_record_callable(self):
        assert callable(create_enrichment_run_record)

    def test_get_latest_from_db_callable(self):
        assert callable(get_latest_enrichment_run_from_db)

    def test_increment_counter_callable(self):
        assert callable(increment_enrichment_counter)

    def test_update_record_callable(self):
        assert callable(update_enrichment_run_record)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_enrichment_orchestrator_db.py -v`
Expected: FAIL with `ImportError: cannot import name 'create_enrichment_run_record'`

**Step 3: Add DB persistence functions**

Add to `src/compgraph/enrichment/orchestrator.py` after `get_latest_enrichment_run()` (after line 115):

```python
# ---------------------------------------------------------------------------
# DB persistence (enrichment_runs table) — supplements in-memory state
# ---------------------------------------------------------------------------

async def create_enrichment_run_record(run_id: uuid.UUID) -> None:
    """Create a persistent enrichment_runs DB record at run start."""
    from compgraph.db.models import EnrichmentRunDB, EnrichmentRunStatus as DBStatus

    async with async_session_factory() as session:
        db_run = EnrichmentRunDB(
            id=run_id,
            status=DBStatus.RUNNING,
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
    from sqlalchemy import update

    from compgraph.db.models import EnrichmentRunDB

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
    from sqlalchemy import update

    from compgraph.db.models import EnrichmentRunDB

    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB)
            .where(EnrichmentRunDB.id == run_id)
            .values(**fields)
        )
        await session.commit()


async def get_latest_enrichment_run_from_db() -> dict | None:
    """Fetch the most recent enrichment_runs row as a dict."""
    from sqlalchemy import select as sa_select

    from compgraph.db.models import EnrichmentRunDB

    async with async_session_factory() as session:
        stmt = (
            sa_select(EnrichmentRunDB)
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

**Step 4: Wire DB calls into run_pass1**

In `EnrichmentOrchestrator.run_pass1()`:

After line 162 (`run.status = EnrichmentStatus.RUNNING`), add:
```python
        await create_enrichment_run_record(run.run_id)
```

After line 225 (`result.succeeded += 1`), add:
```python
                        await increment_enrichment_counter(run.run_id, pass1_succeeded=1)
```

After line 227 (`result.failed += 1`), add:
```python
                        await increment_enrichment_counter(run.run_id, pass1_failed=1)
```

After line 243 (`run.finish(result)`), add:
```python
        await update_enrichment_run_record(
            run.run_id,
            pass1_total=result.succeeded + result.failed + result.skipped,
            status="running",  # pass1 done but pass2 may follow
            finished_at=None,  # not finished until pass2 or standalone pass1
        )
```

**Step 5: Wire DB calls into run_pass2**

In `EnrichmentOrchestrator.run_pass2()`:

After line 256 (`run.status = EnrichmentStatus.RUNNING`), add:
```python
        # Ensure DB record exists (standalone pass2 calls won't have one from pass1)
        from sqlalchemy import select as sa_select
        from compgraph.db.models import EnrichmentRunDB
        async with async_session_factory() as _check_session:
            _exists = await _check_session.execute(
                sa_select(EnrichmentRunDB.id).where(EnrichmentRunDB.id == run.run_id)
            )
            if _exists.scalar_one_or_none() is None:
                await create_enrichment_run_record(run.run_id)
```

After line 340 (`result.succeeded += 1`), add:
```python
                        await increment_enrichment_counter(run.run_id, pass2_succeeded=1)
```

After line 342 (`result.failed += 1`), add:
```python
                        await increment_enrichment_counter(run.run_id, pass2_failed=1)
```

After line 357 (`run.finish_pass2(result)`), add:
```python
        from compgraph.db.models import EnrichmentRunStatus as DBStatus
        final_status = DBStatus.COMPLETED if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL) else DBStatus.FAILED
        error_msg = None
        if run.status == EnrichmentStatus.FAILED:
            error_msg = f"pass1: {run.pass1_result.failed if run.pass1_result else 0}fail, pass2: {result.failed}fail"
        await update_enrichment_run_record(
            run.run_id,
            pass2_total=result.succeeded + result.failed + result.skipped,
            status=final_status,
            finished_at=run.finished_at,
            error_summary=error_msg,
        )
```

**Step 6: Handle standalone pass1 finalization**

When `run_pass1` is called without a subsequent `run_pass2` (e.g., via `/api/enrich/pass1/trigger`), the DB record should be finalized. Add to the end of `run_pass1` (after the `update_enrichment_run_record` call added in Step 4), this comment block for the implementer:

```python
        # NOTE: When called via run_full(), status stays "running" here because
        # run_pass2 will finalize it. When called standalone, the API route or
        # caller should call update_enrichment_run_record() to set final status.
```

**Step 7: Run tests**

Run: `uv run pytest tests/test_enrichment_orchestrator_db.py tests/test_enrichment_pass1.py tests/test_enrichment_pass2.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add src/compgraph/enrichment/orchestrator.py tests/test_enrichment_orchestrator_db.py
git commit -m "feat: wire enrichment orchestrator to enrichment_runs DB table (#68)"
```

---

### REVIEW GATE 1: Data Layer

Run `code-reviewer` on Tasks 1-3. Validate:
- EnrichmentRunDB matches design doc schema exactly
- Atomic increment uses SQL-level `column + N` (not ORM read-modify-write)
- No sync DB calls in async code
- Imports use `TYPE_CHECKING` guard or function-local imports (ruff safety)
- Test coverage for new functions

---

## Phase 2: Dashboard Quick Fixes (Parallel)

Tasks 4-7 touch different files/sections. Run in parallel.

### Task 4: Fix Emoji Shortcodes (#81)

**Files:**
- Modify: `src/compgraph/dashboard/queries.py:333-338`
- Modify: `src/compgraph/dashboard/pages/3_Pipeline_Controls.py:33-39`
- Create: `tests/test_emoji_rendering.py`

**Step 1: Write the failing test**

Create `tests/test_emoji_rendering.py`:

```python
"""Tests for emoji rendering — Unicode characters, not shortcodes."""

from compgraph.dashboard.queries import FRESHNESS_ICONS


class TestFreshnessIcons:
    def test_icons_are_unicode_not_shortcodes(self):
        for key, icon in FRESHNESS_ICONS.items():
            assert not icon.startswith(":"), f"FRESHNESS_ICONS['{key}'] is a shortcode: {icon}"

    def test_all_colors_present(self):
        assert set(FRESHNESS_ICONS.keys()) == {"green", "yellow", "red", "gray"}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_emoji_rendering.py -v`
Expected: FAIL — icons are `:green_circle:` shortcodes

**Step 3: Fix FRESHNESS_ICONS**

In `src/compgraph/dashboard/queries.py:333-338`, replace:

```python
FRESHNESS_ICONS: dict[str, str] = {
    "green": "\U0001f7e2",   # 🟢
    "yellow": "\U0001f7e1",  # 🟡
    "red": "\U0001f534",     # 🔴
    "gray": "\u26aa",        # ⚪
}
```

**Step 4: Fix COMPANY_STATE_ICONS**

In `src/compgraph/dashboard/pages/3_Pipeline_Controls.py:33-39`, replace:

```python
COMPANY_STATE_ICONS: dict[str, str] = {
    "pending": "\u23f3",      # ⏳
    "running": "\U0001f3c3",  # 🏃
    "completed": "\u2705",    # ✅
    "failed": "\u274c",       # ❌
    "skipped": "\u23ed\ufe0f",  # ⏭️
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

### Task 5: Rename "status" to "scrape_status" + Elapsed Time (BUG-4, BUG-5)

**Files:**
- Modify: `src/compgraph/dashboard/queries.py:86-87` (key rename + elapsed time helper)
- Modify: `src/compgraph/dashboard/pages/1_Pipeline_Health.py:108,113` (column name + caption)
- Create: `tests/test_scrape_run_display.py`

**Step 1: Write the failing test**

Create `tests/test_scrape_run_display.py`:

```python
"""Tests for scrape run display formatting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from compgraph.dashboard.queries import _format_completed_at


class TestFormatCompletedAt:
    def test_completed_run_returns_timestamp(self):
        run = MagicMock()
        run.completed_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC)
        run.status = "completed"
        run.started_at = datetime(2026, 2, 16, 11, 50, 0, tzinfo=UTC)
        assert _format_completed_at(run) == run.completed_at

    def test_pending_run_shows_elapsed(self):
        run = MagicMock()
        run.completed_at = None
        run.status = "pending"
        run.started_at = datetime.now(UTC) - timedelta(minutes=12)
        result = str(_format_completed_at(run))
        assert "12m" in result
        assert "elapsed" in result.lower()

    def test_in_progress_fallback(self):
        run = MagicMock()
        run.completed_at = None
        run.status = "failed"
        run.started_at = datetime.now(UTC) - timedelta(minutes=5)
        assert _format_completed_at(run) == "In Progress"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scrape_run_display.py -v`
Expected: FAIL with `ImportError: cannot import name '_format_completed_at'`

**Step 3: Add helper and update get_recent_scrape_runs**

In `src/compgraph/dashboard/queries.py`, add before `get_recent_scrape_runs` (before line 64):

```python
def _format_completed_at(run: Any) -> Any:
    """Format completed_at: show elapsed time for pending runs, timestamp for completed."""
    if run.completed_at:
        return run.completed_at
    if run.status == "pending":
        elapsed = datetime.now(UTC) - run.started_at
        minutes = int(elapsed.total_seconds() / 60)
        return f"Running ({minutes}m elapsed)"
    return "In Progress"
```

In `get_recent_scrape_runs`, replace line 86-87:
```python
                "completed_at": _format_completed_at(row.ScrapeRun),
                "scrape_status": row.ScrapeRun.status,
```

**Step 4: Update Pipeline Health page**

In `src/compgraph/dashboard/pages/1_Pipeline_Health.py:108`, change:
```python
        if row.get("scrape_status") == "completed":
```

After line 113 (`st.dataframe(styled, ...)`), add:
```python
    st.caption("Status shows scrape phase only. Enrichment runs separately after scrape completes.")
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_scrape_run_display.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/1_Pipeline_Health.py tests/test_scrape_run_display.py
git commit -m "fix: rename status to scrape_status and show elapsed time for running scrapers (BUG-4, BUG-5)"
```

---

### Task 6: Pipeline Controls DB-Backed Status (#82)

**Files:**
- Modify: `src/compgraph/dashboard/queries.py` (add `get_latest_pipeline_status` function ~line 97)
- Modify: `src/compgraph/dashboard/pages/3_Pipeline_Controls.py:68-76`
- Create: `tests/test_pipeline_controls_db.py`

**Why:** `/api/scrape/status` reads the in-memory `_pipeline_runs` dict. The scheduler's `pipeline_job()` creates a separate orchestrator instance the API never sees. Querying `scrape_runs` DB table directly works regardless of trigger source.

**Step 1: Write the failing test**

Create `tests/test_pipeline_controls_db.py`:

```python
"""Tests for DB-backed pipeline status query."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock


class TestGetLatestPipelineStatus:
    def _make_run(
        self, company_name: str, slug: str, status: str,
        started_at: datetime, completed_at: datetime | None = None,
        jobs_found: int = 0, snapshots_created: int = 0,
    ) -> MagicMock:
        row = MagicMock()
        row.company_name = company_name
        row.slug = slug
        row.status = status
        row.started_at = started_at
        row.completed_at = completed_at
        row.jobs_found = jobs_found
        row.snapshots_created = snapshots_created
        row.errors = None
        return row

    def test_returns_none_when_no_runs(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        session = MagicMock()
        session.execute = MagicMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=None))
                )
            )
        )
        result = get_latest_pipeline_status(session)
        assert result is None

    def test_aggregates_company_results(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        ts = datetime(2026, 2, 16, 14, 0, 0, tzinfo=UTC)
        runs = [
            self._make_run("T-ROC", "t-roc", "completed", ts, ts, 102, 102),
            self._make_run("2020 Companies", "2020", "completed", ts, ts, 700, 700),
        ]
        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=ts)))),
                MagicMock(all=MagicMock(return_value=runs)),
            ]
        )
        result = get_latest_pipeline_status(session)
        assert result is not None
        assert result["total_postings_found"] == 802
        assert result["companies_succeeded"] == 2
        assert result["status"] == "success"

    def test_mixed_status_shows_running(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        ts = datetime(2026, 2, 16, 14, 0, 0, tzinfo=UTC)
        runs = [
            self._make_run("T-ROC", "t-roc", "completed", ts, ts, 102, 102),
            self._make_run("2020 Companies", "2020", "pending", ts, None, 0, 0),
        ]
        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=ts)))),
                MagicMock(all=MagicMock(return_value=runs)),
            ]
        )
        result = get_latest_pipeline_status(session)
        assert result is not None
        assert result["status"] == "running"
        assert result["company_states"]["t-roc"] == "completed"
        assert result["company_states"]["2020"] == "pending"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pipeline_controls_db.py -v`
Expected: FAIL — `get_latest_pipeline_status` doesn't exist

**Step 3: Implement get_latest_pipeline_status**

Add to `src/compgraph/dashboard/queries.py` after `get_recent_scrape_runs` (~line 97):

```python
@_timed_query
def get_latest_pipeline_status(session: Session) -> dict | None:
    """Aggregated status of the most recent pipeline batch from DB.

    Finds the latest started_at across scrape_runs, fetches all runs with
    that timestamp (= same batch), and aggregates into the shape Pipeline
    Controls expects.
    """
    latest_started = session.execute(
        select(func.max(ScrapeRun.started_at))
    ).scalars().first()

    if latest_started is None:
        return None

    stmt = (
        select(
            ScrapeRun.status,
            ScrapeRun.started_at,
            ScrapeRun.completed_at,
            ScrapeRun.jobs_found,
            ScrapeRun.snapshots_created,
            ScrapeRun.errors,
            Company.name.label("company_name"),
            Company.slug,
        )
        .join(Company, ScrapeRun.company_id == Company.id)
        .where(ScrapeRun.started_at == latest_started)
    )
    rows = session.execute(stmt).all()

    if not rows:
        return None

    total_postings = 0
    total_snapshots = 0
    succeeded = 0
    failed = 0
    company_states: dict[str, str] = {}
    company_results: dict[str, dict] = {}

    for row in rows:
        total_postings += row.jobs_found or 0
        total_snapshots += row.snapshots_created or 0
        company_states[row.slug] = row.status
        company_results[row.slug] = {
            "postings_found": row.jobs_found or 0,
            "snapshots_created": row.snapshots_created or 0,
        }
        if row.status == "completed":
            succeeded += 1
        elif row.status == "failed":
            failed += 1

    statuses = set(company_states.values())
    if "pending" in statuses:
        overall = "running"
    elif failed == len(rows):
        overall = "failed"
    elif failed > 0:
        overall = "partial"
    else:
        overall = "success"

    return {
        "status": overall,
        "started_at": latest_started,
        "total_postings_found": total_postings,
        "total_snapshots_created": total_snapshots,
        "companies_succeeded": succeeded,
        "companies_failed": failed,
        "company_states": company_states,
        "company_results": company_results,
    }
```

**Step 4: Update Pipeline Controls to use DB query**

In `src/compgraph/dashboard/pages/3_Pipeline_Controls.py`, add imports:
```python
from compgraph.dashboard.db import get_session
from compgraph.dashboard.queries import get_latest_pipeline_status
```

Replace lines 68-75 (the `_api_get("/api/scrape/status")` block):
```python
# --- Fetch current status from DB (works for both API and scheduler triggers) ---
with get_session() as _db_session:
    status_data = get_latest_pipeline_status(_db_session)

if status_data is None:
    st.info("No pipeline runs found. Start a scrape to begin.")
    pipeline_status: str | None = None
else:
    pipeline_status = str(status_data["status"])
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_pipeline_controls_db.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/3_Pipeline_Controls.py tests/test_pipeline_controls_db.py
git commit -m "feat: Pipeline Controls reads status from DB instead of in-memory API (#82)"
```

---

### Task 7: Enrichment Pass Breakdown on Pipeline Health (#83 partial)

**Files:**
- Modify: `src/compgraph/dashboard/queries.py` (add `get_enrichment_pass_breakdown` ~line 127)
- Modify: `src/compgraph/dashboard/pages/1_Pipeline_Health.py:89+`
- Create: `tests/test_enrichment_breakdown.py`

**Step 1: Write the failing test**

Create `tests/test_enrichment_breakdown.py`:

```python
"""Tests for enrichment pass breakdown query."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestGetEnrichmentPassBreakdown:
    def test_returns_pass_counts(self) -> None:
        from compgraph.dashboard.queries import get_enrichment_pass_breakdown

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalar_one=MagicMock(return_value=100)),  # total_active
                MagicMock(scalar_one=MagicMock(return_value=60)),   # pass1_only
                MagicMock(scalar_one=MagicMock(return_value=30)),   # fully_enriched
            ]
        )
        result = get_enrichment_pass_breakdown(session)
        assert result["total_active"] == 100
        assert result["unenriched"] == 10
        assert result["pass1_only"] == 60
        assert result["fully_enriched"] == 30

    def test_no_postings(self) -> None:
        from compgraph.dashboard.queries import get_enrichment_pass_breakdown

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalar_one=MagicMock(return_value=0)),
                MagicMock(scalar_one=MagicMock(return_value=0)),
                MagicMock(scalar_one=MagicMock(return_value=0)),
            ]
        )
        result = get_enrichment_pass_breakdown(session)
        assert result["total_active"] == 0
        assert result["unenriched"] == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_enrichment_breakdown.py -v`
Expected: FAIL — function doesn't exist

**Step 3: Implement get_enrichment_pass_breakdown**

Add to `src/compgraph/dashboard/queries.py` after `get_enrichment_coverage` (~line 127):

```python
@_timed_query
def get_enrichment_pass_breakdown(session: Session) -> dict:
    """Enrichment pass completion breakdown for active postings."""
    active_ids = select(Posting.id).where(Posting.is_active.is_(True))

    total_active = session.execute(
        select(func.count()).select_from(Posting).where(Posting.is_active.is_(True))
    ).scalar_one()

    pass1_only = session.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id))).where(
            PostingEnrichment.posting_id.in_(active_ids),
            ~PostingEnrichment.enrichment_version.contains("pass2"),
        )
    ).scalar_one()

    fully_enriched = session.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id))).where(
            PostingEnrichment.posting_id.in_(active_ids),
            PostingEnrichment.enrichment_version.contains("pass2"),
        )
    ).scalar_one()

    return {
        "total_active": total_active,
        "unenriched": total_active - pass1_only - fully_enriched,
        "pass1_only": pass1_only,
        "fully_enriched": fully_enriched,
    }
```

**Step 4: Add enrichment section to Pipeline Health**

In `src/compgraph/dashboard/pages/1_Pipeline_Health.py`:

Add `import os` at top. Update imports:
```python
from compgraph.dashboard.queries import (
    FRESHNESS_ICONS,
    freshness_color,
    get_enrichment_coverage,
    get_enrichment_pass_breakdown,
    get_error_summary,
    get_last_scrape_timestamps,
    get_recent_scrape_runs,
)
```

Add cached loader after `_load_coverage`:
```python
@st.cache_data(ttl=60)
def _load_pass_breakdown() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_pass_breakdown(session))
```

After line 89 (enrichment coverage metrics), add:
```python
# --- Enrichment pass breakdown ---
try:
    breakdown = _load_pass_breakdown()
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Total Active", breakdown["total_active"])
    p2.metric("Unenriched", breakdown["unenriched"])
    p3.metric("Pass 1 Only", breakdown["pass1_only"])
    p4.metric("Pass 1 + 2 (Complete)", breakdown["fully_enriched"])
except Exception:
    logger.exception("Failed to load enrichment pass breakdown")

# --- Active enrichment run (best-effort API call) ---
try:
    import requests as _req
    _api_base = os.environ.get("COMPGRAPH_API_URL", "http://localhost:8000")
    _enrich_resp = _req.get(f"{_api_base}/api/enrich/status", timeout=3)
    if _enrich_resp.status_code == 200:
        _enrich_data = _enrich_resp.json()
        _enrich_status = _enrich_data.get("status", "idle")
        if _enrich_status not in ("idle", "completed", "failed"):
            st.info(
                f"Enrichment: **{_enrich_status.upper()}** "
                f"(started {_enrich_data.get('started_at', 'unknown')})"
            )
            if _enrich_data.get("pass1_result"):
                _p1r = _enrich_data["pass1_result"]
                st.caption(
                    f"Pass 1: {_p1r['succeeded']} succeeded, "
                    f"{_p1r['failed']} failed, {_p1r['skipped']} skipped"
                )
            if _enrich_data.get("pass2_result"):
                _p2r = _enrich_data["pass2_result"]
                st.caption(
                    f"Pass 2: {_p2r['succeeded']} succeeded, "
                    f"{_p2r['failed']} failed, {_p2r['skipped']} skipped"
                )
except Exception:
    pass  # API unavailable is fine — enrichment status is best-effort
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_enrichment_breakdown.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/1_Pipeline_Health.py tests/test_enrichment_breakdown.py
git commit -m "feat: add enrichment pass breakdown and active run status to Pipeline Health (#83)"
```

---

### REVIEW GATE 2: Dashboard Fixes

Run `code-reviewer` on Tasks 4-7. Validate:
- Unicode escape correctness (verify characters render)
- `scrape_status` rename propagated to all consumers (grep for old `"status"` key usage in Health page)
- `get_latest_pipeline_status` SQL join + aggregation logic
- `get_enrichment_pass_breakdown` subquery correctness
- Session lifecycle in Pipeline Controls (context manager properly closes)
- No sync DB calls in async code paths (all dashboard queries are sync — correct for Streamlit)

---

## Phase 3: Real-Time Monitoring (Sequential)

### Task 8: Composite `/api/pipeline/status` Endpoint

**Files:**
- Create: `src/compgraph/api/routes/pipeline.py`
- Modify: `src/compgraph/main.py:45-48` (register router)
- Create: `tests/test_pipeline_status.py`

**Step 1: Write the failing test**

Create `tests/test_pipeline_status.py`:

```python
"""Tests for composite pipeline status endpoint."""

from __future__ import annotations

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
                pass1_total=0,
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


# --- DB Fallback ---


async def get_latest_scrape_run_from_db() -> dict | None:
    """Fetch latest scrape run summary from scrape_runs DB table."""
    from sqlalchemy import select

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


# --- Endpoint ---


@router.get("/status", response_model=PipelineStatusResponse)
async def pipeline_status(request: Request) -> PipelineStatusResponse:
    """Composite pipeline status — single call for the dashboard landing page."""

    # --- Scrape status: in-memory first, DB fallback ---
    scrape_run = get_latest_run()
    scrape_stage = _scrape_stage_status(scrape_run)

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

In `src/compgraph/main.py`, add:
```python
from compgraph.api.routes.pipeline import router as pipeline_router
```
And after the existing `app.include_router` calls:
```python
app.include_router(pipeline_router)
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_pipeline_status.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/api/routes/pipeline.py src/compgraph/main.py tests/test_pipeline_status.py
git commit -m "feat: add /api/pipeline/status composite endpoint with DB fallback (#82, #83)"
```

---

### Task 9: System Status Landing Page

**Files:**
- Rewrite: `src/compgraph/dashboard/main.py`

**Step 1: Write the new System Status landing page**

Rewrite `src/compgraph/dashboard/main.py` with the full implementation from the monitoring design doc:

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

    with col_scrape:
        st.subheader("Scrape")
        scrape = pipeline["scrape"]
        scrape_status = scrape["status"]

        if scrape_status == "running" and scrape.get("current_run"):
            cr = scrape["current_run"]
            st.markdown("**Status:** :blue[RUNNING]")
            st.metric("Postings Found", cr.get("total_postings_found", 0))
            co_done = cr.get("companies_succeeded", 0)
            co_fail = cr.get("companies_failed", 0)
            st.metric("Companies Done", f"{co_done}/{co_done + co_fail}")
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

    with col_enrich:
        st.subheader("Enrichment")
        enrich = pipeline["enrich"]
        enrich_status = enrich["status"]

        if enrich_status == "running" and enrich.get("current_run"):
            cr = enrich["current_run"]
            st.markdown("**Status:** :blue[RUNNING]")
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
Expected: All tests PASS

**Step 3: Commit**

```bash
git add src/compgraph/dashboard/main.py
git commit -m "feat: replace landing page with System Status dashboard (#83)"
```

---

### REVIEW GATE 3: Full Review Chain

1. **`code-reviewer`** — All changes against design doc, async patterns, append-only compliance, test quality
2. **`pytest-validator`** — All new tests for hollow assertions, proper mocking, meaningful coverage
3. **`spec-reviewer`** — Confirm #68, #81, #82, #83 addressed, BUG-4/BUG-5 fixed, no scope creep

---

### Task 10: Final Verification + PR

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
- Add enrichment pass breakdown to Pipeline Health page
- Pipeline Controls now reads from DB (fixes scheduler-triggered run visibility)
- Show elapsed time for running scrapers (BUG-4)
- Rename `status` to `scrape_status` with clarifying caption (BUG-5)

Closes #68, #81, #82, #83

## Design
See `docs/plans/2026-02-16-monitoring-design.md`

## Test plan
- [ ] Unit tests for EnrichmentRunDB model
- [ ] Unit tests for pipeline status endpoint (idle/scraping/enriching/error states)
- [ ] Unit tests for emoji rendering (Unicode, not shortcodes)
- [ ] Unit tests for elapsed time formatting
- [ ] Unit tests for DB-backed pipeline status query
- [ ] Unit tests for enrichment pass breakdown query
- [ ] Manual: trigger scrape via dashboard, verify System Status shows "Scraping..."
- [ ] Manual: verify enrichment progress bars update during run
- [ ] Manual: verify scheduler-triggered runs visible (was broken in #82)
- [ ] Manual: verify emoji renders as colored circles (was broken in #81)
- [ ] Manual: Pipeline Controls shows real data for scheduler runs
- [ ] Manual: Pipeline Health shows enrichment pass breakdown

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Verification Checklist

**Automated**: `uv run pytest tests/ -x --tb=short` — all tests pass

**Manual dashboard walkthrough** (on Pi after deploy):
1. System Status: banner shows "Idle" / "Scraping..." / "Enriching..." with elapsed time
2. System Status: scrape card shows real-time postings/companies during run
3. System Status: enrichment card shows pass1/pass2 progress bars during run
4. System Status: scheduler row shows next run time + "Trigger Now" button
5. System Status: data freshness uses Unicode emoji (not shortcodes)
6. Pipeline Health: emoji icons render as Unicode
7. Pipeline Health: column says `scrape_status`, caption explains scope
8. Pipeline Health: enrichment pass breakdown (4 metrics)
9. Pipeline Health: active enrichment run shows progress if running
10. Pipeline Controls: scheduler-triggered runs show real postings from DB
11. Pipeline Controls: emoji icons render as Unicode
12. Pipeline Controls: running scraper shows "Running (Xm elapsed)"

**Deploy**:
```bash
ssh compgraph-dev "cd /opt/compgraph && git pull && source /root/.local/bin/env && uv sync && systemctl restart compgraph && systemctl restart compgraph-dashboard"
```
