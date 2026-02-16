"""Tests for the pipeline orchestrator with mocked adapters."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.orchestrator import (
    BASELINE_DROP_THRESHOLD,
    BASELINE_LOOKBACK,
    MAX_STORED_RUNS,
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
    _pipeline_runs,
    _store_run,
    check_baseline_anomaly,
    get_latest_run,
    get_run,
)

# --- Fixtures ---


@pytest.fixture(autouse=True)
def clear_pipeline_runs():
    """Clear in-memory run store between tests."""
    _pipeline_runs.clear()
    yield
    _pipeline_runs.clear()


def _make_company(slug: str = "bds", ats_platform: str = "icims") -> MagicMock:
    """Create a mock Company object."""
    company = MagicMock()
    company.id = uuid.uuid4()
    company.slug = slug
    company.name = slug.replace("-", " ").title()
    company.ats_platform = ats_platform
    company.scraper_config = {}
    return company


def _make_success_result(
    company: MagicMock, postings: int = 10, snapshots: int = 10
) -> ScrapeResult:
    return ScrapeResult(
        company_id=company.id,
        company_slug=company.slug,
        postings_found=postings,
        snapshots_created=snapshots,
        finished_at=datetime.now(UTC),
    )


def _make_failure_result(company: MagicMock, error: str = "Connection timeout") -> ScrapeResult:
    return ScrapeResult(
        company_id=company.id,
        company_slug=company.slug,
        errors=[error],
        finished_at=datetime.now(UTC),
    )


def _patch_session_and_companies(companies: list[MagicMock]):
    """Return context managers to patch async_session_factory and company query."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = companies
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory)


# --- Orchestrator Tests ---


class TestPipelineOrchestratorAllSucceed:
    async def test_all_companies_succeed(self):
        """When all adapters succeed, pipeline status is SUCCESS."""
        companies = [_make_company("bds"), _make_company("marketsource")]

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(
            side_effect=lambda c, s: _make_success_result(c, postings=15, snapshots=15)
        )

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            _patch_session_and_companies(companies),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.SUCCESS
        assert run.companies_succeeded == 2
        assert run.companies_failed == 0
        assert run.total_postings_found == 30
        assert run.total_snapshots_created == 30
        assert run.finished_at is not None


class TestPipelineOrchestratorPartialFailure:
    async def test_partial_failure(self):
        """When some adapters fail, pipeline status is PARTIAL."""
        company_ok = _make_company("bds")
        company_fail = _make_company("marketsource")

        def _side_effect(company, session):
            if company.slug == "bds":
                return _make_success_result(company)
            raise ConnectionError("Timeout")

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=_side_effect)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            _patch_session_and_companies([company_ok, company_fail]),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.PARTIAL
        assert run.companies_succeeded == 1
        assert run.companies_failed == 1


class TestPipelineOrchestratorAllFail:
    async def test_all_companies_fail(self):
        """When all adapters fail, pipeline status is FAILED."""
        companies = [_make_company("bds"), _make_company("marketsource")]

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=ConnectionError("Timeout"))

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            _patch_session_and_companies(companies),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.FAILED
        assert run.companies_succeeded == 0
        assert run.companies_failed == 2


class TestPipelineOrchestratorRetry:
    async def test_retry_on_exception_succeeds(self):
        """Adapter exception triggers retry; succeeds on 3rd attempt."""
        company = _make_company("bds")
        call_count = 0

        async def flaky_scrape(c, s):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Timeout")
            return _make_success_result(c)

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=flaky_scrape)

        orchestrator = PipelineOrchestrator(max_retries=3, retry_base_delay=0.01)

        with (
            _patch_session_and_companies([company]),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.SUCCESS
        assert call_count == 3

    async def test_retry_exhausted_returns_error(self):
        """When retries exhausted, ScrapeResult has error message."""
        company = _make_company("bds")

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=ConnectionError("Always fails"))

        orchestrator = PipelineOrchestrator(max_retries=2, retry_base_delay=0.01)

        with (
            _patch_session_and_companies([company]),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.FAILED
        result = run.company_results["bds"]
        assert not result.success
        assert "Always fails" in result.errors[0]

    async def test_retry_on_error_result(self):
        """Adapter returning errors (not exception) also triggers retry."""
        company = _make_company("bds")
        call_count = 0

        async def flaky_scrape(c, s):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _make_failure_result(c, error="Rate limited")
            return _make_success_result(c)

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=flaky_scrape)

        orchestrator = PipelineOrchestrator(max_retries=3, retry_base_delay=0.01)

        with (
            _patch_session_and_companies([company]),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.SUCCESS
        assert call_count == 2


class TestPipelineOrchestratorEdgeCases:
    async def test_missing_adapter_skips_company(self):
        """Company with unregistered ats_platform is marked as error."""
        company = _make_company("unknown-co", ats_platform="lever")

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            _patch_session_and_companies([company]),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                side_effect=KeyError("lever"),
            ),
        ):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.FAILED
        result = run.company_results["unknown-co"]
        assert "No adapter registered" in result.errors[0]

    async def test_no_companies_returns_success(self):
        """Empty company list yields SUCCESS with no results."""
        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with _patch_session_and_companies([]):
            run = await orchestrator.run()

        assert run.status == PipelineStatus.SUCCESS
        assert len(run.company_results) == 0
        assert run.finished_at is not None

    async def test_accepts_precreated_run(self):
        """Orchestrator uses a pre-created PipelineRun when provided."""
        precreated = PipelineRun()
        original_id = precreated.run_id

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with _patch_session_and_companies([]):
            run = await orchestrator.run(pipeline_run=precreated)

        assert run.run_id == original_id
        assert run is precreated


# --- In-Memory Store Tests ---


class TestPipelineRunStore:
    def test_store_and_retrieve(self):
        run = PipelineRun()
        _store_run(run)
        assert get_run(run.run_id) is run

    def test_get_latest_run(self):
        run1 = PipelineRun()
        run2 = PipelineRun()
        _store_run(run1)
        _store_run(run2)
        assert get_latest_run() is run2

    def test_eviction_at_max(self):
        for _ in range(MAX_STORED_RUNS + 5):
            _store_run(PipelineRun())
        assert len(_pipeline_runs) == MAX_STORED_RUNS

    def test_get_latest_when_empty(self):
        assert get_latest_run() is None

    def test_get_nonexistent_run(self):
        assert get_run(uuid.uuid4()) is None


# --- _finalize_scrape_run Tests ---


def _mock_session_factory_for_finalize(
    scrape_run_obj: MagicMock, company_obj: MagicMock | None = None
):
    mock_session = AsyncMock()

    async def _get_side_effect(model_cls, pk):
        from compgraph.db.models import Company, ScrapeRun

        if model_cls is ScrapeRun:
            return scrape_run_obj
        if model_cls is Company:
            return company_obj
        return None

    mock_session.get = AsyncMock(side_effect=_get_side_effect)
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_factory, mock_session


class TestFinalizeUpdatesLastScrapedAt:
    async def test_success_updates_last_scraped_at(self):
        company = _make_company("bds")
        company_id = company.id

        mock_scrape_run = MagicMock()
        mock_scrape_run.id = uuid.uuid4()

        mock_company = MagicMock()
        mock_company.id = company_id
        mock_company.last_scraped_at = None

        mock_factory, _mock_session = _mock_session_factory_for_finalize(
            mock_scrape_run, mock_company
        )

        result = _make_success_result(company, postings=5, snapshots=5)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            await orchestrator._finalize_scrape_run(mock_scrape_run, result)

        assert mock_company.last_scraped_at is not None

    async def test_failure_does_not_update_last_scraped_at(self):
        company = _make_company("bds")
        company_id = company.id

        mock_scrape_run = MagicMock()
        mock_scrape_run.id = uuid.uuid4()

        mock_company = MagicMock()
        mock_company.id = company_id
        mock_company.last_scraped_at = None

        mock_factory, mock_session = _mock_session_factory_for_finalize(
            mock_scrape_run, mock_company
        )

        result = _make_failure_result(company, error="Connection timeout")

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            await orchestrator._finalize_scrape_run(mock_scrape_run, result)

        assert mock_company.last_scraped_at is None
        mock_session.get.assert_called_once()


# --- PipelineRun Property Tests ---


class TestPipelineRunProperties:
    def test_total_postings_found(self):
        run = PipelineRun()
        run.company_results["a"] = ScrapeResult(
            company_id=uuid.uuid4(), company_slug="a", postings_found=10
        )
        run.company_results["b"] = ScrapeResult(
            company_id=uuid.uuid4(), company_slug="b", postings_found=20
        )
        assert run.total_postings_found == 30

    def test_total_snapshots_created(self):
        run = PipelineRun()
        run.company_results["a"] = ScrapeResult(
            company_id=uuid.uuid4(), company_slug="a", snapshots_created=5
        )
        assert run.total_snapshots_created == 5

    def test_total_errors(self):
        run = PipelineRun()
        run.company_results["a"] = ScrapeResult(
            company_id=uuid.uuid4(), company_slug="a", errors=["e1", "e2"]
        )
        run.company_results["b"] = ScrapeResult(
            company_id=uuid.uuid4(), company_slug="b", errors=["e3"]
        )
        assert run.total_errors == 3

    def test_companies_succeeded_and_failed(self):
        run = PipelineRun()
        run.company_results["a"] = ScrapeResult(company_id=uuid.uuid4(), company_slug="a")
        run.company_results["b"] = ScrapeResult(
            company_id=uuid.uuid4(), company_slug="b", errors=["fail"]
        )
        assert run.companies_succeeded == 1
        assert run.companies_failed == 1

    def test_empty_run_properties(self):
        run = PipelineRun()
        assert run.total_postings_found == 0
        assert run.total_snapshots_created == 0
        assert run.total_errors == 0
        assert run.companies_succeeded == 0
        assert run.companies_failed == 0


# --- Baseline Anomaly Detection Tests ---


def _mock_session_with_historical(historical_counts: list[int]) -> AsyncMock:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = historical_counts
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


class TestCheckBaselineAnomaly:
    async def test_zero_results_with_baseline_triggers_warning(self):
        session = _mock_session_with_historical([50, 48, 52, 49, 51])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=0)

        assert len(warnings) == 1
        assert "Zero results detected" in warnings[0]
        assert "baseline average" in warnings[0]

    async def test_significant_drop_triggers_warning(self):
        session = _mock_session_with_historical([100, 100, 100, 100, 100])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=10)

        assert len(warnings) == 1
        assert "Significant drop detected" in warnings[0]
        assert str(BASELINE_DROP_THRESHOLD) in warnings[0] or "50%" in warnings[0]

    async def test_new_company_no_history_skips_check(self):
        session = _mock_session_with_historical([])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=0)

        assert warnings == []

    async def test_normal_run_no_warning(self):
        session = _mock_session_with_historical([50, 48, 52, 49, 51])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=45)

        assert warnings == []

    async def test_at_threshold_no_warning(self):
        session = _mock_session_with_historical([100, 100, 100])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=50)

        assert warnings == []

    async def test_just_below_threshold_triggers_warning(self):
        session = _mock_session_with_historical([100, 100, 100])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=49)

        assert len(warnings) == 1
        assert "Significant drop" in warnings[0]

    async def test_zero_baseline_zero_current_no_warning(self):
        session = _mock_session_with_historical([0, 0, 0])
        company_id = uuid.uuid4()

        warnings = await check_baseline_anomaly(session, company_id, current_jobs_found=0)

        assert warnings == []

    async def test_lookback_constant_matches_query(self):
        assert BASELINE_LOOKBACK == 7

    async def test_drop_threshold_constant(self):
        assert BASELINE_DROP_THRESHOLD == 0.50
