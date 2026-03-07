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


# --- arq worker configuration tests ---


class TestArqWorkerSettings:
    def test_worker_settings_has_cron_jobs(self):
        from compgraph.scheduler.worker import WorkerSettings

        assert hasattr(WorkerSettings, "cron_jobs")
        assert len(WorkerSettings.cron_jobs) == 1

    def test_worker_settings_has_functions(self):
        from compgraph.scheduler.worker import WorkerSettings

        assert hasattr(WorkerSettings, "functions")
        assert len(WorkerSettings.functions) == 1

    def test_worker_max_jobs_is_one(self):
        from compgraph.scheduler.worker import WorkerSettings

        assert WorkerSettings.max_jobs == 1

    def test_cron_schedule_matches_expected(self):
        from compgraph.scheduler.worker import CRON_HOUR, CRON_MINUTE, CRON_WEEKDAYS

        assert CRON_HOUR == 2
        assert CRON_MINUTE == 0
        assert CRON_WEEKDAYS == {0, 2, 4}  # Mon, Wed, Fri

    def test_redis_settings_default(self):
        from compgraph.scheduler.worker import get_redis_settings

        with patch("compgraph.scheduler.worker.settings") as mock_settings:
            mock_settings.REDIS_URL = None
            rs = get_redis_settings()
            assert rs.host == "localhost"
            assert rs.port == 6379

    def test_redis_settings_from_url(self):
        from compgraph.scheduler.worker import get_redis_settings

        with patch("compgraph.scheduler.worker.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://myhost:6380/1"
            rs = get_redis_settings()
            assert rs.host == "myhost"
            assert rs.port == 6380
            assert rs.database == 1


class TestArqRunPipeline:
    async def test_run_pipeline_delegates_to_pipeline_job(self):
        from compgraph.scheduler.worker import run_pipeline

        with patch(
            "compgraph.scheduler.jobs.pipeline_job",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            await run_pipeline({})
            mock_pipeline.assert_called_once()


class TestArqPoolCreation:
    async def test_create_arq_pool_returns_pool(self):
        from compgraph.scheduler.app import create_arq_pool

        mock_pool = AsyncMock()
        with patch(
            "compgraph.scheduler.app.create_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            pool = await create_arq_pool()
            assert pool is mock_pool

    async def test_enqueue_pipeline_job_returns_job_id(self):
        from compgraph.scheduler.app import enqueue_pipeline_job

        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

        result = await enqueue_pipeline_job(mock_pool)
        assert result == "test-job-123"
        mock_pool.enqueue_job.assert_called_once_with(
            "run_pipeline", _job_id="manual_pipeline_trigger"
        )

    async def test_enqueue_pipeline_job_returns_none_on_duplicate(self):
        from compgraph.scheduler.app import enqueue_pipeline_job

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=None)

        result = await enqueue_pipeline_job(mock_pool)
        assert result is None


# --- API route tests ---


@pytest.fixture
def app_with_arq_pool():
    from compgraph.main import app

    mock_pool = AsyncMock()
    mock_pool.info = AsyncMock(return_value={})

    mock_job = MagicMock()
    mock_job.job_id = str(uuid.uuid4())
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

    app.state.arq_pool = mock_pool
    yield app
    if hasattr(app.state, "arq_pool"):
        del app.state.arq_pool


@pytest.fixture(autouse=True)
def _reset_paused_schedules():
    from compgraph.api.routes.scheduler import _paused_schedules

    _paused_schedules.clear()
    yield
    _paused_schedules.clear()


class TestSchedulerStatusAPI:
    async def test_status_returns_correct_structure(self, app_with_arq_pool):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/scheduler/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["schedule_id"] == "daily_pipeline"
        assert data["missed_run"] is False

    async def test_status_disabled_when_no_pool(self):
        from compgraph.main import app

        if hasattr(app.state, "arq_pool"):
            del app.state.arq_pool

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
    async def test_manual_trigger_works(self, app_with_arq_pool):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/trigger")

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert "triggered" in data["message"].lower()

    async def test_trigger_fails_when_disabled(self):
        from compgraph.main import app

        if hasattr(app.state, "arq_pool"):
            del app.state.arq_pool

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/trigger")

        assert resp.status_code == 503

    async def test_trigger_returns_409_on_duplicate(self, app_with_arq_pool):
        app_with_arq_pool.state.arq_pool.enqueue_job = AsyncMock(return_value=None)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/trigger")

        assert resp.status_code == 409


class TestSchedulerInvalidScheduleID:
    @pytest.mark.parametrize("action", ["trigger", "pause", "resume"])
    async def test_unknown_schedule_returns_404(self, app_with_arq_pool, action):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            resp = await client.post(f"/api/v1/scheduler/jobs/nonexistent/{action}")

        assert resp.status_code == 404


class TestSchedulerPauseResumeAPI:
    async def test_pause_works(self, app_with_arq_pool):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/pause")

        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is True

    async def test_resume_works(self, app_with_arq_pool):
        from compgraph.api.routes.scheduler import _paused_schedules

        _paused_schedules.add("daily_pipeline")

        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/scheduler/jobs/daily_pipeline/resume")

        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False

    async def test_pause_then_status_shows_paused(self, app_with_arq_pool):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_arq_pool),
            base_url="http://test",
        ) as client:
            await client.post("/api/v1/scheduler/jobs/daily_pipeline/pause")
            resp = await client.get("/api/v1/scheduler/status")

        data = resp.json()
        assert data["schedules"][0]["paused"] is True
