from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from compgraph.enrichment.orchestrator import (
    EnrichmentRun,
    EnrichmentStatus,
)
from compgraph.enrichment.orchestrator import (
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
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
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
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert "system_state" in data
            assert "scrape" in data
            assert "enrich" in data
            assert "scheduler" in data

    def test_scrape_stage_includes_current_run_when_running(self, client):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        _store_run(run)
        with patch(
            "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert data["scrape"]["status"] == "running"
            assert data["scrape"]["current_run"] is not None
            assert data["scrape"]["current_run"]["run_id"] == str(run.run_id)

    def test_completed_scrape_has_no_current_run(self, client):
        run = PipelineRun(status=PipelineStatus.SUCCESS)
        run.finished_at = datetime.now(UTC)
        _store_run(run)
        with patch(
            "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert data["scrape"]["status"] == "success"
            assert data["scrape"]["current_run"] is None

    def test_scheduler_disabled_by_default(self, client):
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert data["scheduler"]["enabled"] is False
            assert data["scheduler"]["next_run_at"] is None

    def test_db_fallback_for_scrape_when_no_memory(self, client):
        db_scrape = {
            "run_id": "00000000-0000-0000-0000-000000000001",
            "status": "completed",
            "started_at": datetime.now(UTC),
            "finished_at": datetime.now(UTC),
            "jobs_found": 42,
            "snapshots_created": 10,
        }
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=db_scrape,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert data["scrape"]["status"] == "completed"
            assert data["system_state"] == "idle"

    def test_db_fallback_pending_scrape_shows_scraping(self, client):
        """DB 'pending' status should be normalized to 'running' so system_state is 'scraping'."""
        db_scrape = {
            "run_id": "00000000-0000-0000-0000-000000000002",
            "status": "pending",
            "started_at": datetime.now(UTC),
            "finished_at": None,
            "jobs_found": 0,
            "snapshots_created": 0,
        }
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=db_scrape,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = client.get("/api/pipeline/status")
            data = resp.json()
            assert data["scrape"]["status"] == "running"
            assert data["system_state"] == "scraping"

    def test_scraping_takes_priority_over_enriching(self, client):
        from compgraph.enrichment.orchestrator import _store_run as store_enrich

        scrape_run = PipelineRun(status=PipelineStatus.RUNNING)
        _store_run(scrape_run)
        enrich_run = EnrichmentRun(status=EnrichmentStatus.RUNNING)
        store_enrich(enrich_run)
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = client.get("/api/pipeline/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["system_state"] == "scraping"

    def test_enrich_db_fallback(self, client):
        db_enrich = {
            "run_id": str(uuid.uuid4()),
            "status": "completed",
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "pass1_total": 50,
            "pass1_succeeded": 48,
            "pass1_failed": 2,
            "pass1_skipped": 0,
            "pass2_total": 48,
            "pass2_succeeded": 45,
            "pass2_failed": 3,
            "pass2_skipped": 0,
            "error_summary": None,
        }
        with (
            patch(
                "compgraph.api.routes.pipeline.get_latest_scrape_run_from_db",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "compgraph.api.routes.pipeline.get_latest_enrichment_run_from_db",
                new_callable=AsyncMock,
                return_value=db_enrich,
            ),
        ):
            resp = client.get("/api/pipeline/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["enrich"]["status"] == "completed"
            assert data["enrich"]["last_completed_at"] is not None
