# M3 Dashboard Bug Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 dashboard visibility bugs discovered during first live pipeline run so operators can monitor scrape and enrichment activity.

**Architecture:** All fixes target the Streamlit dashboard layer (sync psycopg2 queries + page templates). No API or pipeline changes. New DB query functions follow existing `_timed_query` decorator pattern in `queries.py`. Pipeline Controls switches from in-memory API polling to direct DB queries for status.

**Tech Stack:** Python 3.12, Streamlit, SQLAlchemy (sync), pandas

**Branch:** `feat/first-run-fixes` (already exists with BUG-6/BUG-7 fixes)

---

## Task 1: BUG-1 — Emoji Shortcodes to Unicode

**Files:**
- Modify: `src/compgraph/dashboard/queries.py:333-338`
- Modify: `src/compgraph/dashboard/pages/3_Pipeline_Controls.py:33-39`
- Test: `tests/test_dashboard_queries.py`

**Step 1: Write failing test for FRESHNESS_ICONS Unicode values**

```python
# Add to tests/test_dashboard_queries.py
from compgraph.dashboard.queries import FRESHNESS_ICONS

class TestFreshnessIcons:
    def test_icons_are_unicode_not_shortcodes(self) -> None:
        for key, icon in FRESHNESS_ICONS.items():
            assert not icon.startswith(":"), f"FRESHNESS_ICONS['{key}'] is a shortcode: {icon}"

    def test_all_colors_present(self) -> None:
        assert set(FRESHNESS_ICONS.keys()) == {"green", "yellow", "red", "gray"}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_queries.py::TestFreshnessIcons -v`
Expected: FAIL — icons are currently shortcode strings like `:green_circle:`

**Step 3: Fix FRESHNESS_ICONS in queries.py**

Replace `queries.py:333-338`:
```python
FRESHNESS_ICONS: dict[str, str] = {
    "green": "\U0001f7e2",
    "yellow": "\U0001f7e1",
    "red": "\U0001f534",
    "gray": "\u26aa",
}
```

**Step 4: Fix COMPANY_STATE_ICONS in Pipeline Controls**

Replace `3_Pipeline_Controls.py:33-39`:
```python
COMPANY_STATE_ICONS: dict[str, str] = {
    "pending": "\u23f3",
    "running": "\U0001f3c3",
    "completed": "\u2705",
    "failed": "\u274c",
    "skipped": "\u23ed\ufe0f",
}
```

**Step 5: Run tests to verify pass**

Run: `uv run pytest tests/test_dashboard_queries.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/3_Pipeline_Controls.py tests/test_dashboard_queries.py
git commit -m "fix: replace emoji shortcodes with Unicode characters (BUG-1)"
```

---

## Task 2: BUG-5 — Rename "status" to "scrape_status"

**Files:**
- Modify: `src/compgraph/dashboard/queries.py:87` (dict key in `get_recent_scrape_runs`)
- Modify: `src/compgraph/dashboard/pages/1_Pipeline_Health.py:108` (`_style_row` check)
- Modify: `src/compgraph/dashboard/pages/1_Pipeline_Health.py:113` (add caption after table)
- Test: `tests/test_dashboard_queries.py`

**Step 1: Write failing test for renamed key**

```python
# Add to tests/test_dashboard_queries.py
from compgraph.dashboard.queries import get_recent_scrape_runs

class TestGetRecentScrapeRuns:
    def _make_scrape_run_row(
        self, company_name: str, status: str, started_at: datetime,
        completed_at: datetime | None = None,
    ) -> MagicMock:
        row = MagicMock()
        row.company_name = company_name
        row.ScrapeRun.started_at = started_at
        row.ScrapeRun.completed_at = completed_at
        row.ScrapeRun.status = status
        row.ScrapeRun.pages_scraped = 5
        row.ScrapeRun.jobs_found = 10
        row.ScrapeRun.snapshots_created = 10
        row.ScrapeRun.postings_closed = 0
        row.ScrapeRun.errors = None
        return row

    def test_returns_scrape_status_key(self) -> None:
        ts = datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC)
        rows = [self._make_scrape_run_row("T-ROC", "completed", ts, ts)]
        session = MagicMock()
        session.execute = MagicMock(return_value=MagicMock(all=MagicMock(return_value=rows)))

        result = get_recent_scrape_runs(session)

        assert "scrape_status" in result[0], "Expected 'scrape_status' key, not 'status'"
        assert "status" not in result[0], "Old 'status' key should be removed"
        assert result[0]["scrape_status"] == "completed"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_queries.py::TestGetRecentScrapeRuns::test_returns_scrape_status_key -v`
Expected: FAIL — key is currently `"status"`

**Step 3: Rename key in queries.py**

In `src/compgraph/dashboard/queries.py:87`, change:
```python
                "status": row.ScrapeRun.status,
```
to:
```python
                "scrape_status": row.ScrapeRun.status,
```

**Step 4: Update _style_row in Pipeline Health**

In `src/compgraph/dashboard/pages/1_Pipeline_Health.py:108`, change:
```python
        if row.get("status") == "completed":
```
to:
```python
        if row.get("scrape_status") == "completed":
```

**Step 5: Add clarifying caption after scrape runs table**

In `src/compgraph/dashboard/pages/1_Pipeline_Health.py`, after line 113 (`st.dataframe(styled, ...)`), add:
```python
    st.caption("Status shows scrape phase only. Enrichment runs separately after scrape completes.")
```

**Step 6: Run tests**

Run: `uv run pytest tests/test_dashboard_queries.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/1_Pipeline_Health.py tests/test_dashboard_queries.py
git commit -m "fix: rename status to scrape_status and add clarifying caption (BUG-5)"
```

---

## Task 3: BUG-4 — Elapsed Time for Running Scrapers

**Files:**
- Modify: `src/compgraph/dashboard/queries.py:86` (`completed_at` logic in `get_recent_scrape_runs`)
- Test: `tests/test_dashboard_queries.py`

**Step 1: Write failing test for elapsed time display**

```python
# Add to TestGetRecentScrapeRuns in tests/test_dashboard_queries.py
    def test_pending_run_shows_elapsed_time(self) -> None:
        started = datetime.now(UTC) - timedelta(minutes=12)
        rows = [self._make_scrape_run_row("2020 Companies", "pending", started)]
        session = MagicMock()
        session.execute = MagicMock(return_value=MagicMock(all=MagicMock(return_value=rows)))

        result = get_recent_scrape_runs(session)

        completed_at = result[0]["completed_at"]
        assert "12m" in str(completed_at), f"Expected elapsed minutes in '{completed_at}'"
        assert "elapsed" in str(completed_at).lower()

    def test_completed_run_shows_timestamp(self) -> None:
        ts = datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC)
        rows = [self._make_scrape_run_row("T-ROC", "completed", ts, ts)]
        session = MagicMock()
        session.execute = MagicMock(return_value=MagicMock(all=MagicMock(return_value=rows)))

        result = get_recent_scrape_runs(session)

        assert result[0]["completed_at"] == ts
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_queries.py::TestGetRecentScrapeRuns::test_pending_run_shows_elapsed_time -v`
Expected: FAIL — currently returns `"In Progress"` string

**Step 3: Add helper function and update get_recent_scrape_runs**

Add helper before `get_recent_scrape_runs` (after line 62 comment block) in `queries.py`:
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

Replace line 86 in `get_recent_scrape_runs`:
```python
                "completed_at": row.ScrapeRun.completed_at or "In Progress",
```
with:
```python
                "completed_at": _format_completed_at(row.ScrapeRun),
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_dashboard_queries.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/compgraph/dashboard/queries.py tests/test_dashboard_queries.py
git commit -m "feat: show elapsed time for running scrapers (BUG-4)"
```

---

## Review Gate 1

Run: `uv run pytest tests/ -x`

Dispatch `code-reviewer` agent on Tasks 1-3 changes. Focus areas:
- Unicode escape correctness
- `_format_completed_at` edge cases (null `started_at`?)
- `scrape_status` rename propagation — check no other files reference old key

---

## Task 4: BUG-2 — Pipeline Controls DB-Backed Status

**Files:**
- Modify: `src/compgraph/dashboard/queries.py` (add `get_latest_pipeline_status` function)
- Modify: `src/compgraph/dashboard/pages/3_Pipeline_Controls.py:68-76` (replace API call with DB query)
- Test: `tests/test_dashboard_queries.py`

**Why:** The API endpoint `/api/scrape/status` reads from in-memory `_pipeline_runs` dict. When the scheduler triggers a run via `pipeline_job()`, it creates a separate orchestrator instance that the API endpoint never sees. Querying `scrape_runs` DB table works regardless of trigger source.

**Step 1: Write failing test for new query function**

```python
# Add to tests/test_dashboard_queries.py
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
        assert result["total_snapshots_created"] == 802
        assert result["companies_succeeded"] == 2
        assert result["companies_failed"] == 0
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

    def test_all_failed_shows_failed(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        ts = datetime(2026, 2, 16, 14, 0, 0, tzinfo=UTC)
        runs = [
            self._make_run("BDS", "bds", "failed", ts, ts),
            self._make_run("MarketSource", "marketsource", "failed", ts, ts),
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
        assert result["status"] == "failed"
        assert result["companies_failed"] == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_queries.py::TestGetLatestPipelineStatus -v`
Expected: FAIL — `get_latest_pipeline_status` doesn't exist

**Step 3: Implement get_latest_pipeline_status**

Add after `get_recent_scrape_runs` in `src/compgraph/dashboard/queries.py` (around line 96):

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
    total_errors = 0
    succeeded = 0
    failed = 0
    company_states: dict[str, str] = {}
    company_results: dict[str, dict] = {}

    for row in rows:
        total_postings += row.jobs_found or 0
        total_snapshots += row.snapshots_created or 0
        if row.errors and isinstance(row.errors, dict):
            total_errors += len(row.errors.get("errors", []))

        company_states[row.slug] = row.status
        company_results[row.slug] = {
            "postings_found": row.jobs_found or 0,
            "snapshots_created": row.snapshots_created or 0,
        }

        if row.status == "completed":
            succeeded += 1
        elif row.status == "failed":
            failed += 1

    # Determine overall status
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
        "total_errors": total_errors,
        "companies_succeeded": succeeded,
        "companies_failed": failed,
        "company_states": company_states,
        "company_results": company_results,
    }
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_dashboard_queries.py::TestGetLatestPipelineStatus -v`
Expected: ALL PASS

**Step 5: Update Pipeline Controls to use DB query**

In `src/compgraph/dashboard/pages/3_Pipeline_Controls.py`:

Add imports at top:
```python
from compgraph.dashboard.db import get_session
from compgraph.dashboard.queries import get_latest_pipeline_status
```

Replace lines 68-76:
```python
# --- Fetch current status ---
status_data = _api_get("/api/scrape/status")

if status_data is None:
    st.info("No pipeline runs found. Start a scrape to begin.")
    pipeline_status: str | None = None
else:
    pipeline_status = str(status_data["status"])
```

With:
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

**Step 6: Run full test suite**

Run: `uv run pytest tests/ -x`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/3_Pipeline_Controls.py tests/test_dashboard_queries.py
git commit -m "feat: Pipeline Controls reads status from DB instead of in-memory API (BUG-2)"
```

---

## Task 5: BUG-3 — Enrichment Visibility on Pipeline Health

**Files:**
- Modify: `src/compgraph/dashboard/queries.py` (add `get_enrichment_pass_breakdown`)
- Modify: `src/compgraph/dashboard/pages/1_Pipeline_Health.py` (add enrichment sections)
- Test: `tests/test_dashboard_queries.py`

**Step 1: Write failing test for enrichment pass breakdown**

```python
# Add to tests/test_dashboard_queries.py
class TestGetEnrichmentPassBreakdown:
    def test_returns_pass_counts(self) -> None:
        from compgraph.dashboard.queries import get_enrichment_pass_breakdown

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalar_one=MagicMock(return_value=100)),   # total_active
                MagicMock(scalar_one=MagicMock(return_value=60)),    # pass1_only
                MagicMock(scalar_one=MagicMock(return_value=30)),    # fully_enriched
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

Run: `uv run pytest tests/test_dashboard_queries.py::TestGetEnrichmentPassBreakdown -v`
Expected: FAIL — function doesn't exist

**Step 3: Implement get_enrichment_pass_breakdown**

Add to `src/compgraph/dashboard/queries.py` after `get_enrichment_coverage` (around line 126):

```python
@_timed_query
def get_enrichment_pass_breakdown(session: Session) -> dict:
    """Enrichment pass completion breakdown for active postings."""
    active_ids = select(Posting.id).where(Posting.is_active.is_(True))

    total_active = session.execute(
        select(func.count()).select_from(Posting).where(Posting.is_active.is_(True))
    ).scalar_one()

    # Pass 1 only: has enrichment, version does NOT contain 'pass2'
    pass1_only = session.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id))).where(
            PostingEnrichment.posting_id.in_(active_ids),
            ~PostingEnrichment.enrichment_version.contains("pass2"),
        )
    ).scalar_one()

    # Fully enriched: version contains 'pass2'
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

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_dashboard_queries.py::TestGetEnrichmentPassBreakdown -v`
Expected: ALL PASS

**Step 5: Add enrichment sections to Pipeline Health page**

In `src/compgraph/dashboard/pages/1_Pipeline_Health.py`:

Update imports to add `get_enrichment_pass_breakdown`:
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

Add `import os` at top if not present.

Add cached loader after `_load_coverage`:
```python
@st.cache_data(ttl=60)
def _load_pass_breakdown() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_pass_breakdown(session))
```

After the existing enrichment coverage metrics (after line 89), add:

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

**Step 6: Run full test suite**

Run: `uv run pytest tests/ -x`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/compgraph/dashboard/queries.py src/compgraph/dashboard/pages/1_Pipeline_Health.py tests/test_dashboard_queries.py
git commit -m "feat: add enrichment pass breakdown and active run status to Pipeline Health (BUG-3)"
```

---

## Review Gate 2

Dispatch review agents in sequence:

1. **`code-reviewer`**: DB query correctness (SQL joins, aggregation logic), session lifecycle in Controls page, enrichment API error handling
2. **`pytest-validator`**: Test coverage for `get_latest_pipeline_status` and `get_enrichment_pass_breakdown` — hollow assertions, edge cases
3. **`spec-reviewer`**: Verify bugs #81, #82, #83 are addressed; flag scope creep

---

## Verification

1. **Automated**: `uv run pytest tests/ -x --tb=short` — all tests pass
2. **Manual dashboard walkthrough** (on Pi after deploy):
   - Pipeline Health: emoji icons render as Unicode (not `:green_circle:`)
   - Pipeline Health: column says `scrape_status`, caption explains scope
   - Pipeline Health: enrichment pass breakdown (4 metrics)
   - Pipeline Health: active enrichment run shows progress if running
   - Pipeline Controls: scheduler-triggered runs show real postings/snapshots from DB
   - Pipeline Controls: emoji icons render as Unicode (not `:runner:`)
   - Pipeline Controls: running scraper shows "Running (Xm elapsed)"
3. **Deploy**: `ssh compgraph-dev "cd /opt/compgraph && git pull && uv sync && systemctl restart compgraph-dashboard"`

---

## Agent Team & Execution Strategy

### Round 1 (parallel — no file conflicts):
| Agent | Type | Assignment |
|-------|------|------------|
| Agent A | `python-backend-developer` | Task 1 (BUG-1) + Task 2 (BUG-5) — bundle, same files |
| Agent B | `python-backend-developer` | Task 3 (BUG-4) — queries.py only, different section |

### Review Gate 1:
| Agent | Focus |
|-------|-------|
| `code-reviewer` | Unicode escapes, renamed key propagation, elapsed time edges |

### Round 2 (parallel — different pages):
| Agent | Type | Assignment |
|-------|------|------------|
| Agent C | `python-backend-developer` | Task 4 (BUG-2) — queries.py + Controls page |
| Agent D | `python-backend-developer` | Task 5 (BUG-3) — queries.py + Health page |

### Review Gate 2:
| Agent | Focus |
|-------|-------|
| `code-reviewer` | DB query patterns, session lifecycle, error handling |
| `pytest-validator` | Test coverage for new query functions |
| `spec-reviewer` | Bug closure verification, scope creep check |

### Conflict Avoidance
- **Round 1**: Agent A touches emoji dicts (queries.py:333-338) + status key rename (queries.py:87) + Health page styling. Agent B touches `_format_completed_at` helper (new, ~line 63) + `completed_at` value (queries.py:86). Different lines, no overlap.
- **Round 2**: Agent C adds `get_latest_pipeline_status()` to queries.py (~line 97) + modifies Controls page. Agent D adds `get_enrichment_pass_breakdown()` to queries.py (~line 127) + modifies Health page. Different functions appended to different sections, different pages.
