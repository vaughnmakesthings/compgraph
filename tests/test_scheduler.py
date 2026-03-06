from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from compgraph.aggregation.orchestrator import AggregationResult
from compgraph.enrichment.orchestrator import EnrichmentRun, EnrichmentStatus
from compgraph.scheduler.jobs import pipeline_job
from compgraph.scrapers.orchestrator import PipelineRun, PipelineStatus

# --- Fixtures ---


@pytest.fixture(autouse=True)
def _reset_scheduler_state():
    import compgraph.scheduler.jobs as jobs_mod

    jobs_mod._last_pipeline_finished_at = None
    jobs_mod._last_pipeline_success = False
    yield
    jobs_mod._last_pipeline_finished_at = None
    jobs_mod._last_pipeline_success = False


@pytest.fixture(autouse=True)
def _mock_db_session():
    """Mock DB session factory to avoid DB connection in unit tests."""
    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch(
        "compgraph.db.session.async_session_factory",
        return_value=mock_cm,
    ):
        yield


def _mock_agg_orchestrator() -> MagicMock:
    mock_result = AggregationResult()
    mock_result.succeeded = {"agg_daily_velocity": 10}
    mock_agg_orch = MagicMock()
    mock_agg_orch.run = AsyncMock(return_value=mock_result)
    mock_agg_cls = MagicMock(return_value=mock_agg_orch)
    return mock_agg_cls


# --- pipeline_job tests ---


class TestPipelineJobScrapesThenEnriches:
    async def test_scrape_then_enrich_called_sequentially(self):
        call_order: list[str] = []

        async def mock_scrape_run(pipeline_run: PipelineRun | None = None) -> PipelineRun:
            call_order.append("scrape")
            if pipeline_run is not None:
                pipeline_run.status = PipelineStatus.SUCCESS
                pipeline_run.finished_at = datetime.now(UTC)
            return pipeline_run or PipelineRun()

        async def mock_enrich_run_full(
            run: EnrichmentRun, company_id=None
        ) -> tuple[MagicMock, MagicMock]:
            call_order.append("enrich")
            run.status = EnrichmentStatus.SUCCESS
            run.finished_at = datetime.now(UTC)
            return MagicMock(), MagicMock()

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=mock_scrape_run)

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock(side_effect=mock_enrich_run_full)

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
            patch(
                "compgraph.aggregation.orchestrator.AggregationOrchestrator",
                _mock_agg_orchestrator(),
            ),
            patch(
                "compgraph.aggregation.alerts.generate_alerts",
                new_callable=AsyncMock,
                return_value={"velocity_spike": 0, "new_brand": 0, "brand_lost": 0},
            ),
        ):
            await pipeline_job()

        assert call_order == ["scrape", "enrich"]
        mock_scrape_orch.run.assert_called_once()
        mock_enrich_orch.run_full.assert_called_once()


class TestPipelineJobSkipsEnrichOnFailure:
    async def test_skips_enrichment_when_scrape_fails(self):
        async def mock_scrape_run(pipeline_run: PipelineRun | None = None) -> PipelineRun:
            if pipeline_run is not None:
                pipeline_run.status = PipelineStatus.FAILED
                pipeline_run.finished_at = datetime.now(UTC)
            return pipeline_run or PipelineRun()

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=mock_scrape_run)

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock()

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
        ):
            await pipeline_job()

        mock_scrape_orch.run.assert_called_once()
        mock_enrich_orch.run_full.assert_not_called()


class TestPipelineJobScrapeException:
    async def test_exception_in_scrape_does_not_propagate(self):
        import compgraph.scheduler.jobs as jobs_mod

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=RuntimeError("connection lost"))

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock()

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
        ):
            await pipeline_job()  # should not raise

        mock_enrich_orch.run_full.assert_not_called()
        assert jobs_mod._last_pipeline_success is False
        assert jobs_mod._last_pipeline_finished_at is not None


class TestPipelineJobPartialTriggers:
    async def test_enrichment_runs_on_partial_scrape(self):
        async def mock_scrape_run(pipeline_run: PipelineRun | None = None) -> PipelineRun:
            if pipeline_run is not None:
                pipeline_run.status = PipelineStatus.PARTIAL
                pipeline_run.finished_at = datetime.now(UTC)
            return pipeline_run or PipelineRun()

        async def mock_enrich_run_full(
            run: EnrichmentRun, company_id=None
        ) -> tuple[MagicMock, MagicMock]:
            run.status = EnrichmentStatus.SUCCESS
            run.finished_at = datetime.now(UTC)
            return MagicMock(), MagicMock()

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=mock_scrape_run)

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock(side_effect=mock_enrich_run_full)

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
            patch(
                "compgraph.aggregation.orchestrator.AggregationOrchestrator",
                _mock_agg_orchestrator(),
            ),
            patch(
                "compgraph.aggregation.alerts.generate_alerts",
                new_callable=AsyncMock,
                return_value={"velocity_spike": 0, "new_brand": 0, "brand_lost": 0},
            ),
        ):
            await pipeline_job()

        mock_enrich_orch.run_full.assert_called_once()


class TestPipelineJobTracksState:
    async def test_updates_last_pipeline_state(self):
        import compgraph.scheduler.jobs as jobs_mod

        async def mock_scrape_run(pipeline_run: PipelineRun | None = None) -> PipelineRun:
            if pipeline_run is not None:
                pipeline_run.status = PipelineStatus.SUCCESS
                pipeline_run.finished_at = datetime.now(UTC)
            return pipeline_run or PipelineRun()

        async def mock_enrich_run_full(
            run: EnrichmentRun, company_id=None
        ) -> tuple[MagicMock, MagicMock]:
            run.status = EnrichmentStatus.SUCCESS
            run.finished_at = datetime.now(UTC)
            return MagicMock(), MagicMock()

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=mock_scrape_run)

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock(side_effect=mock_enrich_run_full)

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
            patch(
                "compgraph.aggregation.orchestrator.AggregationOrchestrator",
                _mock_agg_orchestrator(),
            ),
            patch(
                "compgraph.aggregation.alerts.generate_alerts",
                new_callable=AsyncMock,
                return_value={"velocity_spike": 0, "new_brand": 0, "brand_lost": 0},
            ),
        ):
            await pipeline_job()

        assert jobs_mod._last_pipeline_finished_at is not None
        assert jobs_mod._last_pipeline_success is True


class TestPipelineJobEnrichFailureTracked:
    async def test_enrichment_failure_sets_success_false(self):
        import compgraph.scheduler.jobs as jobs_mod

        async def mock_scrape_run(pipeline_run: PipelineRun | None = None) -> PipelineRun:
            if pipeline_run is not None:
                pipeline_run.status = PipelineStatus.SUCCESS
                pipeline_run.finished_at = datetime.now(UTC)
            return pipeline_run or PipelineRun()

        async def mock_enrich_run_full(
            run: EnrichmentRun, company_id=None
        ) -> tuple[MagicMock, MagicMock]:
            run.status = EnrichmentStatus.FAILED
            run.finished_at = datetime.now(UTC)
            return MagicMock(), MagicMock()

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=mock_scrape_run)

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock(side_effect=mock_enrich_run_full)

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
        ):
            await pipeline_job()

        assert jobs_mod._last_pipeline_finished_at is not None
        assert jobs_mod._last_pipeline_success is False


class TestPipelineJobPartialEnrichSucceeds:
    async def test_partial_enrichment_treated_as_success(self):
        import compgraph.scheduler.jobs as jobs_mod

        async def mock_scrape_run(pipeline_run: PipelineRun | None = None) -> PipelineRun:
            if pipeline_run is not None:
                pipeline_run.status = PipelineStatus.SUCCESS
                pipeline_run.finished_at = datetime.now(UTC)
            return pipeline_run or PipelineRun()

        async def mock_enrich_run_full(
            run: EnrichmentRun, company_id=None
        ) -> tuple[MagicMock, MagicMock]:
            run.status = EnrichmentStatus.PARTIAL
            run.finished_at = datetime.now(UTC)
            return MagicMock(), MagicMock()

        mock_scrape_orch = MagicMock()
        mock_scrape_orch.run = AsyncMock(side_effect=mock_scrape_run)

        mock_enrich_orch = MagicMock()
        mock_enrich_orch.run_full = AsyncMock(side_effect=mock_enrich_run_full)

        with (
            patch(
                "compgraph.scheduler.jobs.PipelineOrchestrator",
                return_value=mock_scrape_orch,
            ),
            patch(
                "compgraph.scheduler.jobs.EnrichmentOrchestrator",
                return_value=mock_enrich_orch,
            ),
            patch("compgraph.scheduler.jobs._store_scrape_run"),
            patch("compgraph.scheduler.jobs._store_enrichment_run"),
            patch(
                "compgraph.aggregation.orchestrator.AggregationOrchestrator",
                _mock_agg_orchestrator(),
            ),
            patch(
                "compgraph.aggregation.alerts.generate_alerts",
                new_callable=AsyncMock,
                return_value={"velocity_spike": 0, "new_brand": 0, "brand_lost": 0},
            ),
        ):
            await pipeline_job()

        assert jobs_mod._last_pipeline_finished_at is not None
        assert jobs_mod._last_pipeline_success is True


# --- Scheduler setup tests ---


class TestSchedulerSetup:
    async def test_registers_job_with_correct_cron(self):
        from compgraph.scheduler.app import SCHEDULE_ID, setup_scheduler

        scheduler = await setup_scheduler()
        try:
            schedules = await scheduler.get_schedules()
            assert len(schedules) == 1
            assert schedules[0].id == SCHEDULE_ID

            trigger = schedules[0].trigger
            assert trigger.timezone.key == "America/New_York"
            assert trigger.hour == "2"
            assert trigger.minute == "0"
            assert trigger.day_of_week == "1,3,5"
        finally:
            await scheduler.__aexit__(None, None, None)


# --- API route tests ---


@pytest.fixture
def app_with_scheduler():
    from compgraph.main import app

    mock_scheduler = AsyncMock()

    mock_schedule = MagicMock()
    mock_schedule.id = "daily_pipeline"
    mock_schedule.next_fire_time = datetime(2026, 2, 18, 7, 0, 0, tzinfo=UTC)
    mock_schedule.last_fire_time = datetime(2026, 2, 16, 7, 0, 0, tzinfo=UTC)
    mock_schedule.paused = False

    mock_scheduler.get_schedules = AsyncMock(return_value=[mock_schedule])
    mock_scheduler.add_job = AsyncMock(return_value=uuid.uuid4())
    mock_scheduler.pause_schedule = AsyncMock()
    mock_scheduler.unpause_schedule = AsyncMock()

    app.state.scheduler = mock_scheduler
    yield app
    if hasattr(app.state, "scheduler"):
        del app.state.scheduler


class TestSchedulerStatusAPI:
    async def test_status_returns_correct_structure(self, app_with_scheduler):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_scheduler),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/scheduler/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["schedule_id"] == "daily_pipeline"
        assert data["missed_run"] is False

    async def test_status_disabled_when_no_scheduler(self):
        from compgraph.main import app

        if hasattr(app.state, "scheduler"):
            del app.state.scheduler

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/scheduler/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["schedules"] == []


class TestSchedulerTriggerAPI:
    async def test_manual_trigger_works(self, app_with_scheduler):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_scheduler),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/trigger")

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert "triggered" in data["message"].lower()

    async def test_trigger_fails_when_disabled(self):
        from compgraph.main import app

        if hasattr(app.state, "scheduler"):
            del app.state.scheduler

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/trigger")

        assert resp.status_code == 503


class TestSchedulerInvalidScheduleID:
    @pytest.mark.parametrize("action", ["trigger", "pause", "resume"])
    async def test_unknown_schedule_returns_404(self, app_with_scheduler, action):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_scheduler),
            base_url="http://test",
        ) as client:
            resp = await client.post(f"/api/v1/scheduler/jobs/nonexistent/{action}")

        assert resp.status_code == 404


class TestSchedulerPauseResumeAPI:
    async def test_pause_works(self, app_with_scheduler):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_scheduler),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/pause")

        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is True

    async def test_resume_works(self, app_with_scheduler):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_scheduler),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/resume")

        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False
