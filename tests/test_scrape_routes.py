"""Tests for scrape API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.orchestrator import (
    PipelineRun,
    PipelineStatus,
    _pipeline_runs,
    _store_run,
)


@pytest.fixture(autouse=True)
def clear_runs():
    _pipeline_runs.clear()
    yield
    _pipeline_runs.clear()


class TestScrapeStatusEndpoint:
    def test_status_no_runs_returns_404(self, client):
        resp = client.get("/api/scrape/status")
        assert resp.status_code == 404

    def test_status_returns_latest_run(self, client):
        run = PipelineRun(status=PipelineStatus.SUCCESS)
        run.finished_at = datetime.now(UTC)
        _store_run(run)

        resp = client.get("/api/scrape/status")
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

        resp = client.get("/api/scrape/status")
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

        resp = client.get(f"/api/scrape/status/{run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_status_by_id_not_found(self, client):
        resp = client.get(f"/api/scrape/status/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestScrapeTriggerEndpoint:
    def test_trigger_returns_run_id(self, client):
        resp = client.post("/api/scrape/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data
        assert "message" in data
        # Validate run_id is a valid UUID
        uuid.UUID(data["run_id"])

    def test_run_exists_after_trigger(self, client):
        resp = client.post("/api/scrape/trigger")
        run_id = resp.json()["run_id"]

        status_resp = client.get(f"/api/scrape/status/{run_id}")
        assert status_resp.status_code == 200
