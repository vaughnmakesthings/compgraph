"""Dedicated tests for the scrape completeness gate in the pipeline orchestrator.

The completeness gate in _finalize_scrape_run prevents false deactivation when a
partial scrape returns fewer results than the existing active posting baseline.
When triggered, it skips deactivate_stale_postings and appends a warning.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.orchestrator import PipelineOrchestrator, _count_active_postings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    postings_found: int = 50,
    snapshots_created: int = 50,
    errors: list[str] | None = None,
    company_id: uuid.UUID | None = None,
    company_slug: str = "bds",
) -> ScrapeResult:
    return ScrapeResult(
        company_id=company_id or uuid.uuid4(),
        company_slug=company_slug,
        postings_found=postings_found,
        snapshots_created=snapshots_created,
        errors=errors or [],
    )


def _make_scrape_run() -> MagicMock:
    run = MagicMock()
    run.id = uuid.uuid4()
    return run


def _mock_finalize_session(baseline_count: int) -> tuple[MagicMock, AsyncMock]:
    """Return (mock_factory, mock_session) with _count_active_postings stubbed.

    The mock session handles session.get() for both ScrapeRun and Company,
    and patches execute() to return the provided baseline_count.
    """
    mock_scrape_run_db = MagicMock()
    mock_scrape_run_db.id = uuid.uuid4()
    mock_scrape_run_db.completed_at = None
    mock_scrape_run_db.jobs_found = None
    mock_scrape_run_db.snapshots_created = None
    mock_scrape_run_db.pages_scraped = None
    mock_scrape_run_db.status = None
    mock_scrape_run_db.errors = None
    mock_scrape_run_db.postings_closed = None

    mock_company_db = MagicMock()
    mock_company_db.last_scraped_at = None

    mock_session = AsyncMock()

    async def _get(model_cls, pk):
        from compgraph.db.models import Company, ScrapeRun

        if model_cls is ScrapeRun:
            return mock_scrape_run_db
        if model_cls is Company:
            return mock_company_db
        return None

    mock_session.get = AsyncMock(side_effect=_get)
    mock_session.commit = AsyncMock()

    # execute() is used by both _count_active_postings and check_baseline_anomaly.
    # First call returns the baseline count; subsequent calls return empty history
    # (so check_baseline_anomaly produces no additional warnings).
    count_result = MagicMock()
    count_result.scalar_one.return_value = baseline_count

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[count_result, history_result])

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_factory, mock_session


# ---------------------------------------------------------------------------
# _count_active_postings unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCountActivePostings:
    async def test_returns_correct_count(self) -> None:
        """_count_active_postings returns the scalar result from the DB query."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await _count_active_postings(mock_session, uuid.uuid4())

        assert count == 42
        mock_session.execute.assert_called_once()

    async def test_returns_zero_for_new_company(self) -> None:
        """Returns 0 when the company has no active postings."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await _count_active_postings(mock_session, uuid.uuid4())

        assert count == 0


# ---------------------------------------------------------------------------
# Completeness gate — trigger behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCompletenessGateTriggered:
    async def test_gate_skips_deactivation_when_triggered(self) -> None:
        """When postings_found < baseline * threshold, deactivate_stale_postings is NOT called."""
        # baseline=100, found=10 — far below the default 0.7 threshold
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=100)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=10)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        deactivate_mock = AsyncMock(return_value=0)
        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.scrapers.orchestrator.deactivate_stale_postings", deactivate_mock),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        deactivate_mock.assert_not_called()

    async def test_gate_appends_warning_when_triggered(self) -> None:
        """When gate triggers, a warning message is appended to result.warnings."""
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=100)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=10, company_slug="marketsource")

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        assert len(result.warnings) >= 1
        gate_warnings = [w for w in result.warnings if "completeness gate" in w.lower()]
        assert gate_warnings, f"Expected a completeness gate warning, got: {result.warnings}"
        assert "marketsource" in gate_warnings[0]
        assert "skipping deactivation" in gate_warnings[0].lower()

    async def test_gate_reports_percentage_in_warning(self) -> None:
        """The warning message includes the percentage of baseline found."""
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=100)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=10)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        gate_warnings = [w for w in result.warnings if "completeness gate" in w.lower()]
        assert gate_warnings
        # 10/100 = 10.0% — below the 0.2 threshold (20 jobs)
        assert "10.0%" in gate_warnings[0]


# ---------------------------------------------------------------------------
# Completeness gate — pass behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCompletenessGatePasses:
    async def test_gate_calls_deactivation_when_passing(self) -> None:
        """When postings_found >= baseline * threshold, deactivate_stale_postings IS called."""
        # baseline=100, found=80 — above the default 0.7 threshold (70)
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=100)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=80)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        deactivate_mock = AsyncMock(return_value=5)
        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.scrapers.orchestrator.deactivate_stale_postings", deactivate_mock),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        deactivate_mock.assert_called_once()

    async def test_gate_passes_at_exact_threshold(self) -> None:
        """When postings_found == baseline * threshold exactly, gate does not trigger."""
        # baseline=100, threshold=0.2, found=20 — exactly at threshold (not below), gate passes
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=100)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=20)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        deactivate_mock = AsyncMock(return_value=0)
        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.scrapers.orchestrator.deactivate_stale_postings", deactivate_mock),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        deactivate_mock.assert_called_once()

    async def test_gate_no_warning_when_passing(self) -> None:
        """No completeness-gate warning appears when gate does not trigger."""
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=100)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=80)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        gate_warnings = [w for w in result.warnings if "completeness gate" in w.lower()]
        assert not gate_warnings


# ---------------------------------------------------------------------------
# Completeness gate — zero baseline (first scrape)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCompletenessGateZeroBaseline:
    async def test_zero_baseline_deactivation_proceeds(self) -> None:
        """When baseline is 0 (first scrape), gate does not trigger and deactivation proceeds."""
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=0)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=50)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        deactivate_mock = AsyncMock(return_value=0)
        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.scrapers.orchestrator.deactivate_stale_postings", deactivate_mock),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        deactivate_mock.assert_called_once()

    async def test_zero_baseline_zero_found_no_division_error(self) -> None:
        """baseline=0 and found=0 does not raise a ZeroDivisionError."""
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=0)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=0)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            # Should not raise
            await orchestrator._finalize_scrape_run(scrape_run, result)

    async def test_zero_baseline_no_gate_warning(self) -> None:
        """No completeness-gate warning when baseline is 0."""
        mock_factory, _mock_session = _mock_finalize_session(baseline_count=0)
        scrape_run = _make_scrape_run()
        result = _make_result(postings_found=50)

        orchestrator = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        with (
            patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory),
            patch(
                "compgraph.scrapers.orchestrator.deactivate_stale_postings",
                AsyncMock(return_value=0),
            ),
        ):
            await orchestrator._finalize_scrape_run(scrape_run, result)

        gate_warnings = [w for w in result.warnings if "completeness gate" in w.lower()]
        assert not gate_warnings
