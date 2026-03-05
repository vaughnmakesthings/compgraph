"""Tests for scrape API endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from compgraph.api.deps import get_db
from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.orchestrator import (
    PipelineRun,
    PipelineStatus,
    _pipeline_runs,
    _store_run,
)


@pytest.fixture(autouse=True)
def clear_runs():
    from compgraph.scrapers.orchestrator import _pipeline_orchestrators

    _pipeline_runs.clear()
    _pipeline_orchestrators.clear()
    yield
    _pipeline_runs.clear()
    _pipeline_orchestrators.clear()


def _make_mock_db(
    scrape_run_row: object | None = None,
) -> AsyncGenerator:
    async def _override() -> AsyncGenerator:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = scrape_run_row
        mock_session.execute.return_value = mock_result
        yield mock_session

    return _override


@pytest.fixture
def client_with_db():
    import os

    os.environ.setdefault("DATABASE_PASSWORD", "test-placeholder")
    from fastapi.testclient import TestClient

    from compgraph.main import app

    def _factory(scrape_run_row: object | None = None):
        app.dependency_overrides[get_db] = _make_mock_db(scrape_run_row)
        return TestClient(app)

    yield _factory
    app.dependency_overrides.pop(get_db, None)


class TestScrapeStatusEndpoint:
    def test_status_no_runs_returns_404(self, client):
        resp = client.get("/api/v1/scrape/status")
        assert resp.status_code == 404

    def test_status_returns_latest_run(self, client):
        run = PipelineRun(status=PipelineStatus.SUCCESS)
        run.finished_at = datetime.now(UTC)
        _store_run(run)

        resp = client.get("/api/v1/scrape/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["run_id"] == str(run.run_id)
        assert data["total_postings_found"] == 0
        assert data["companies_succeeded"] == 0

    def test_status_with_company_results(self, client):
        run = PipelineRun(status=PipelineStatus.PARTIAL)
        run.finished_at = datetime.now(UTC)
        run.company_results["bds"] = ScrapeResult(
            company_id=uuid.uuid4(),
            company_slug="bds",
            postings_found=15,
            snapshots_created=15,
            finished_at=datetime.now(UTC),
        )
        run.company_results["marketsource"] = ScrapeResult(
            company_id=uuid.uuid4(),
            company_slug="marketsource",
            errors=["Timeout"],
            finished_at=datetime.now(UTC),
        )
        _store_run(run)

        resp = client.get("/api/v1/scrape/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert data["total_postings_found"] == 15
        assert data["companies_succeeded"] == 1
        assert data["companies_failed"] == 1
        assert data["company_results"]["bds"]["success"] is True
        assert data["company_results"]["marketsource"]["success"] is False


class TestScrapeStatusByIdEndpoint:
    def test_status_by_id(self, client):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        _store_run(run)

        resp = client.get(f"/api/v1/scrape/status/{run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_status_by_id_not_found(self, client):
        resp = client.get(f"/api/v1/scrape/status/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestScrapeTriggerEndpoint:
    def test_trigger_returns_run_id(self, client_with_db):
        c = client_with_db(scrape_run_row=None)
        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data
        assert "message" in data
        uuid.UUID(data["run_id"])

    def test_run_exists_after_trigger(self, client_with_db):
        c = client_with_db(scrape_run_row=None)
        resp = c.post("/api/v1/scrape/trigger")
        run_id = resp.json()["run_id"]

        status_resp = c.get(f"/api/v1/scrape/status/{run_id}")
        assert status_resp.status_code == 200


class TestScrapeTriggerConcurrencyGuard:
    def _make_active_scrape_run(self, status: str = "pending") -> MagicMock:
        row = MagicMock()
        row.id = uuid.uuid4()
        row.status = status
        return row

    def test_trigger_returns_409_when_db_has_pending_run(self, client_with_db):
        active = self._make_active_scrape_run("pending")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "already running" in detail["message"]
        assert detail["active_run_id"] == str(active.id)
        assert detail["active_status"] == "pending"

    def test_trigger_returns_409_when_db_has_running_run(self, client_with_db):
        active = self._make_active_scrape_run("running")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["active_status"] == "running"

    def test_trigger_returns_409_when_db_has_paused_run(self, client_with_db):
        active = self._make_active_scrape_run("paused")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["active_status"] == "paused"

    def test_trigger_returns_409_when_db_has_stopping_run(self, client_with_db):
        active = self._make_active_scrape_run("stopping")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["active_status"] == "stopping"

    def test_trigger_allowed_when_no_active_db_runs(self, client_with_db):
        c = client_with_db(scrape_run_row=None)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data

    def test_trigger_allowed_after_completed_run_in_db(self, client_with_db):
        c = client_with_db(scrape_run_row=None)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 200

    def test_trigger_409_detail_includes_run_id_and_status(self, client_with_db):
        active = self._make_active_scrape_run("pending")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "active_run_id" in detail
        assert "active_status" in detail
        assert "message" in detail
        uuid.UUID(detail["active_run_id"])

    def test_in_memory_guard_still_blocks_when_db_clear(self, client_with_db):
        c = client_with_db(scrape_run_row=None)
        _store_run(PipelineRun(status=PipelineStatus.RUNNING))

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert isinstance(detail, dict)
        assert "already running" in detail["message"]
        assert "active_run_id" in detail
        assert "active_status" in detail

    @pytest.mark.parametrize(
        "active_status",
        ["pending", "running", "paused", "stopping"],
    )
    def test_all_db_active_statuses_block_trigger(self, client_with_db, active_status):
        row = MagicMock()
        row.id = uuid.uuid4()
        row.status = active_status
        c = client_with_db(scrape_run_row=row)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409, f"DB status '{active_status}' should block trigger"
        detail = resp.json()["detail"]
        assert detail["active_status"] == active_status
        assert detail["active_run_id"] == str(row.id)

    @pytest.mark.parametrize(
        "terminal_status",
        [
            PipelineStatus.SUCCESS,
            PipelineStatus.PARTIAL,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        ],
    )
    def test_all_terminal_statuses_allow_trigger(self, client_with_db, terminal_status):
        c = client_with_db(scrape_run_row=None)
        run = PipelineRun(status=terminal_status)
        run.finished_at = datetime.now(UTC)
        _store_run(run)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 200, f"Status {terminal_status} should allow trigger"

    def test_active_statuses_frozenset_matches_db_list(self):
        from compgraph.api.routes.scrape import _ACTIVE_STATUSES, _DB_ACTIVE_STATUSES

        assert set(_DB_ACTIVE_STATUSES) == {s.value for s in _ACTIVE_STATUSES}

    def test_active_statuses_cover_all_non_terminal(self):
        from compgraph.api.routes.scrape import _ACTIVE_STATUSES

        terminal = {
            PipelineStatus.SUCCESS,
            PipelineStatus.PARTIAL,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        }
        all_statuses = set(PipelineStatus)
        assert _ACTIVE_STATUSES | terminal == all_statuses
        assert _ACTIVE_STATUSES & terminal == set()

    def test_db_guard_takes_precedence_over_in_memory(self, client_with_db):
        active = self._make_active_scrape_run("running")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert isinstance(detail, dict)
        assert "active_run_id" in detail

    def test_trigger_succeeds_when_no_runs_exist(self, client_with_db):
        assert len(_pipeline_runs) == 0
        c = client_with_db(scrape_run_row=None)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data
        uuid.UUID(data["run_id"])

    def test_in_memory_pending_run_blocks_trigger(self, client_with_db):
        c = client_with_db(scrape_run_row=None)
        _store_run(PipelineRun(status=PipelineStatus.PENDING))

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert isinstance(detail, dict)
        assert "already running" in detail["message"]

    def test_in_memory_stopping_run_blocks_trigger(self, client_with_db):
        c = client_with_db(scrape_run_row=None)
        _store_run(PipelineRun(status=PipelineStatus.STOPPING))

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert isinstance(detail, dict)
        assert "already running" in detail["message"]

    def test_409_detail_message_wording(self, client_with_db):
        active = self._make_active_scrape_run("pending")
        c = client_with_db(scrape_run_row=active)

        resp = c.post("/api/v1/scrape/trigger")
        detail = resp.json()["detail"]
        assert "Wait for completion or force-stop" in detail["message"]

    def test_latest_in_memory_run_determines_guard(self, client_with_db):
        c = client_with_db(scrape_run_row=None)

        old_run = PipelineRun(status=PipelineStatus.RUNNING)
        old_run.started_at = datetime(2024, 1, 1, tzinfo=UTC)
        _store_run(old_run)

        new_run = PipelineRun(status=PipelineStatus.SUCCESS)
        new_run.started_at = datetime(2024, 6, 1, tzinfo=UTC)
        new_run.finished_at = datetime(2024, 6, 1, tzinfo=UTC)
        _store_run(new_run)

        resp = c.post("/api/v1/scrape/trigger")
        assert resp.status_code == 200


class TestScrapeRunIdTargeting:
    """Tests for run_id targeting on control endpoints (issue #60)."""

    def _setup_running_run(self) -> tuple[PipelineRun, MagicMock]:
        from compgraph.scrapers.orchestrator import PipelineOrchestrator, _pipeline_orchestrators

        run = PipelineRun(status=PipelineStatus.RUNNING)
        _store_run(run)
        mock_orch = MagicMock(spec=PipelineOrchestrator)
        _pipeline_orchestrators[run.run_id] = mock_orch
        return run, mock_orch

    def _setup_paused_run(self) -> tuple[PipelineRun, MagicMock]:
        from compgraph.scrapers.orchestrator import PipelineOrchestrator, _pipeline_orchestrators

        run = PipelineRun(status=PipelineStatus.PAUSED)
        _store_run(run)
        mock_orch = MagicMock(spec=PipelineOrchestrator)
        _pipeline_orchestrators[run.run_id] = mock_orch
        return run, mock_orch

    def test_pause_with_run_id_targets_specific_run(self, client):
        run, mock_orch = self._setup_running_run()

        resp = client.post(f"/api/v1/scrape/pause?run_id={run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == str(run.run_id)
        mock_orch.pause.assert_called_once_with(run)

    def test_pause_with_invalid_run_id_returns_404(self, client):
        self._setup_running_run()
        fake_id = uuid.uuid4()

        resp = client.post(f"/api/v1/scrape/pause?run_id={fake_id}")
        assert resp.status_code == 404
        assert str(fake_id) in resp.json()["detail"]

    def test_resume_with_run_id_targets_specific_run(self, client):
        run, mock_orch = self._setup_paused_run()

        resp = client.post(f"/api/v1/scrape/resume?run_id={run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == str(run.run_id)
        mock_orch.resume.assert_called_once_with(run)

    def test_resume_with_invalid_run_id_returns_404(self, client):
        self._setup_paused_run()
        fake_id = uuid.uuid4()

        resp = client.post(f"/api/v1/scrape/resume?run_id={fake_id}")
        assert resp.status_code == 404

    def test_stop_with_run_id_targets_specific_run(self, client):
        run, mock_orch = self._setup_running_run()

        resp = client.post(f"/api/v1/scrape/stop?run_id={run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == str(run.run_id)
        mock_orch.stop.assert_called_once_with(run)

    def test_stop_with_invalid_run_id_returns_404(self, client):
        self._setup_running_run()
        fake_id = uuid.uuid4()

        resp = client.post(f"/api/v1/scrape/stop?run_id={fake_id}")
        assert resp.status_code == 404

    def test_force_stop_with_run_id_targets_specific_run(self, client):
        run, mock_orch = self._setup_running_run()

        resp = client.post(f"/api/v1/scrape/force-stop?run_id={run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == str(run.run_id)
        mock_orch.force_stop.assert_called_once_with(run)

    def test_force_stop_with_invalid_run_id_returns_404(self, client):
        self._setup_running_run()
        fake_id = uuid.uuid4()

        resp = client.post(f"/api/v1/scrape/force-stop?run_id={fake_id}")
        assert resp.status_code == 404

    def test_control_without_run_id_still_targets_latest(self, client):
        """Without run_id, endpoints still fall back to latest run (backwards compat)."""
        run, mock_orch = self._setup_running_run()

        resp = client.post("/api/v1/scrape/pause")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == str(run.run_id)
        mock_orch.pause.assert_called_once()

    def test_run_id_targets_non_latest_run(self, client):
        """run_id can target a run that is NOT the latest."""
        from compgraph.scrapers.orchestrator import PipelineOrchestrator, _pipeline_orchestrators

        older_run = PipelineRun(status=PipelineStatus.RUNNING)
        older_run.started_at = datetime(2024, 1, 1, tzinfo=UTC)
        _store_run(older_run)
        older_orch = MagicMock(spec=PipelineOrchestrator)
        _pipeline_orchestrators[older_run.run_id] = older_orch

        newer_run = PipelineRun(status=PipelineStatus.RUNNING)
        newer_run.started_at = datetime(2024, 6, 1, tzinfo=UTC)
        _store_run(newer_run)
        newer_orch = MagicMock(spec=PipelineOrchestrator)
        _pipeline_orchestrators[newer_run.run_id] = newer_orch

        resp = client.post(f"/api/v1/scrape/stop?run_id={older_run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == str(older_run.run_id)
        older_orch.stop.assert_called_once()
        newer_orch.stop.assert_not_called()

    def test_run_id_targeting_respects_status_check(self, client):
        """Targeting a completed run by run_id should return 409."""
        run = PipelineRun(status=PipelineStatus.SUCCESS)
        run.finished_at = datetime.now(UTC)
        _store_run(run)

        resp = client.post(f"/api/v1/scrape/pause?run_id={run.run_id}")
        assert resp.status_code == 409
        assert "not active" in resp.json()["detail"]


class TestScrapeRunsListing:
    """Tests for GET /scrape/runs endpoint (issue #60)."""

    def test_runs_empty(self, client):
        resp = client.get("/api/v1/scrape/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_runs_returns_single_run(self, client):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        _store_run(run)

        resp = client.get("/api/v1/scrape/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["runs"][0]["run_id"] == str(run.run_id)
        assert data["runs"][0]["status"] == "running"

    def test_runs_ordered_most_recent_first(self, client):
        old_run = PipelineRun(status=PipelineStatus.SUCCESS)
        old_run.started_at = datetime(2024, 1, 1, tzinfo=UTC)
        old_run.finished_at = datetime(2024, 1, 1, tzinfo=UTC)
        _store_run(old_run)

        new_run = PipelineRun(status=PipelineStatus.RUNNING)
        new_run.started_at = datetime(2024, 6, 1, tzinfo=UTC)
        _store_run(new_run)

        resp = client.get("/api/v1/scrape/runs")
        data = resp.json()
        assert data["total"] == 2
        assert data["runs"][0]["run_id"] == str(new_run.run_id)
        assert data["runs"][1]["run_id"] == str(old_run.run_id)

    def test_runs_includes_aggregated_fields(self, client):
        run = PipelineRun(status=PipelineStatus.PARTIAL)
        run.finished_at = datetime.now(UTC)
        run.company_results["bds"] = ScrapeResult(
            company_id=uuid.uuid4(),
            company_slug="bds",
            postings_found=15,
            snapshots_created=10,
            finished_at=datetime.now(UTC),
        )
        run.company_results["marketsource"] = ScrapeResult(
            company_id=uuid.uuid4(),
            company_slug="marketsource",
            errors=["Timeout"],
            finished_at=datetime.now(UTC),
        )
        _store_run(run)

        resp = client.get("/api/v1/scrape/runs")
        data = resp.json()
        summary = data["runs"][0]
        assert summary["total_postings_found"] == 15
        assert summary["total_snapshots_created"] == 10
        assert summary["companies_succeeded"] == 1
        assert summary["companies_failed"] == 1

    def test_runs_multiple(self, client):
        for i in range(5):
            run = PipelineRun(status=PipelineStatus.SUCCESS)
            run.started_at = datetime(2024, 1, i + 1, tzinfo=UTC)
            run.finished_at = datetime(2024, 1, i + 1, tzinfo=UTC)
            _store_run(run)

        resp = client.get("/api/v1/scrape/runs")
        data = resp.json()
        assert data["total"] == 5
        started_ats = [r["started_at"] for r in data["runs"]]
        assert started_ats == sorted(started_ats, reverse=True)


class TestGetAllRunsFunction:
    """Tests for get_all_runs() orchestrator function."""

    def test_get_all_runs_empty(self):
        from compgraph.scrapers.orchestrator import get_all_runs

        assert get_all_runs() == []

    def test_get_all_runs_returns_sorted(self):
        from compgraph.scrapers.orchestrator import get_all_runs

        old_run = PipelineRun(status=PipelineStatus.SUCCESS)
        old_run.started_at = datetime(2024, 1, 1, tzinfo=UTC)
        _store_run(old_run)

        new_run = PipelineRun(status=PipelineStatus.RUNNING)
        new_run.started_at = datetime(2024, 6, 1, tzinfo=UTC)
        _store_run(new_run)

        runs = get_all_runs()
        assert len(runs) == 2
        assert runs[0].run_id == new_run.run_id
        assert runs[1].run_id == old_run.run_id
