"""Tests for force_stop / stop per-company state management (issue #362)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.orchestrator import (
    CompanyState,
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
    _pipeline_runs,
)


@pytest.fixture(autouse=True)
def clear_pipeline_runs():
    _pipeline_runs.clear()
    yield
    _pipeline_runs.clear()


def _make_company(slug: str = "bds", ats_platform: str = "icims") -> MagicMock:
    company = MagicMock()
    company.id = uuid.uuid4()
    company.slug = slug
    company.name = slug.replace("-", " ").title()
    company.ats_platform = ats_platform
    company.scraper_config = {}
    return company


def _patch_session_and_companies(companies: list[MagicMock]):
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = companies
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("compgraph.scrapers.orchestrator.async_session_factory", mock_factory)


class TestCompanyStateCancelledEnum:
    def test_cancelled_value_is_lowercase_string(self):
        assert CompanyState.CANCELLED == "cancelled"
        assert CompanyState.CANCELLED.value == "cancelled"

    def test_cancelled_serializes_in_dict(self):
        states: dict[str, CompanyState] = {"bds": CompanyState.CANCELLED}
        serialized = {k: v.value for k, v in states.items()}
        assert serialized == {"bds": "cancelled"}

    def test_all_enum_values_are_distinct(self):
        values = [s.value for s in CompanyState]
        assert len(values) == len(set(values))

    def test_cancelled_is_member_of_strenum(self):
        assert isinstance(CompanyState.CANCELLED, str)
        assert CompanyState("cancelled") is CompanyState.CANCELLED


class TestForceStopCompanyStates:
    def test_force_stop_sets_pending_to_cancelled(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.PENDING,
            "marketsource": CompanyState.PENDING,
            "2020": CompanyState.PENDING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.force_stop(run)

        assert run.status == PipelineStatus.CANCELLED
        for slug in run.company_states:
            assert run.company_states[slug] == CompanyState.CANCELLED

    def test_force_stop_sets_running_to_cancelled(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.RUNNING,
            "marketsource": CompanyState.RUNNING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.force_stop(run)

        for slug in run.company_states:
            assert run.company_states[slug] == CompanyState.CANCELLED

    def test_force_stop_preserves_terminal_states(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.COMPLETED,
            "marketsource": CompanyState.FAILED,
            "2020": CompanyState.SKIPPED,
            "troc": CompanyState.RUNNING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.force_stop(run)

        assert run.company_states["bds"] == CompanyState.COMPLETED
        assert run.company_states["marketsource"] == CompanyState.FAILED
        assert run.company_states["2020"] == CompanyState.SKIPPED
        assert run.company_states["troc"] == CompanyState.CANCELLED

    def test_force_stop_with_mixed_states(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.COMPLETED,
            "marketsource": CompanyState.RUNNING,
            "2020": CompanyState.PENDING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.force_stop(run)

        assert run.company_states["bds"] == CompanyState.COMPLETED
        assert run.company_states["marketsource"] == CompanyState.CANCELLED
        assert run.company_states["2020"] == CompanyState.CANCELLED
        assert run.status == PipelineStatus.CANCELLED

    def test_force_stop_with_empty_states(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.force_stop(run)

        assert run.status == PipelineStatus.CANCELLED
        assert run.company_states == {}

    def test_force_stop_cancels_tasks(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)

        mock_task_1 = MagicMock()
        mock_task_2 = MagicMock()
        orch._tasks = [mock_task_1, mock_task_2]

        orch.force_stop(run)

        mock_task_1.cancel.assert_called_once()
        mock_task_2.cancel.assert_called_once()

    def test_force_stop_sets_internal_flags(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.force_stop(run)

        assert orch._force_stop_requested is True
        assert orch._stop_requested is True


class TestStopCompanyStates:
    def test_stop_sets_pending_to_skipped(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.PENDING,
            "marketsource": CompanyState.PENDING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.stop(run)

        assert run.status == PipelineStatus.STOPPING
        assert run.company_states["bds"] == CompanyState.SKIPPED
        assert run.company_states["marketsource"] == CompanyState.SKIPPED

    def test_stop_leaves_running_untouched(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.RUNNING,
            "marketsource": CompanyState.PENDING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.stop(run)

        assert run.company_states["bds"] == CompanyState.RUNNING
        assert run.company_states["marketsource"] == CompanyState.SKIPPED

    def test_stop_preserves_terminal_states(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        run.company_states = {
            "bds": CompanyState.COMPLETED,
            "marketsource": CompanyState.FAILED,
            "2020": CompanyState.PENDING,
        }
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.stop(run)

        assert run.company_states["bds"] == CompanyState.COMPLETED
        assert run.company_states["marketsource"] == CompanyState.FAILED
        assert run.company_states["2020"] == CompanyState.SKIPPED

    def test_stop_sets_internal_flags(self):
        run = PipelineRun(status=PipelineStatus.RUNNING)
        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch.stop(run)

        assert orch._stop_requested is True
        assert orch._force_stop_requested is False


class TestCancelledErrorStateCleanup:
    async def test_cancelled_during_resume_wait_sets_cancelled(self):
        company = _make_company("bds")
        pipeline_run = PipelineRun(status=PipelineStatus.RUNNING)
        pipeline_run.company_states[company.slug] = CompanyState.PENDING

        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        orch._resume_event.clear()

        async def cancel_after_start():
            await asyncio.sleep(0.01)
            for task in orch._tasks:
                task.cancel()

        with _patch_session_and_companies([company]):
            task = asyncio.create_task(orch._scrape_company_with_isolation(company, pipeline_run))
            orch._tasks = [task]
            cancel_task = asyncio.create_task(cancel_after_start())

            with pytest.raises(asyncio.CancelledError):
                await task

            await cancel_task

        assert pipeline_run.company_states[company.slug] == CompanyState.CANCELLED

    async def test_force_stop_during_full_run_sets_all_cancelled(self):
        companies = [_make_company("bds"), _make_company("marketsource")]

        async def slow_scrape(c, s):
            await asyncio.sleep(10)
            return ScrapeResult(
                company_id=c.id,
                company_slug=c.slug,
                postings_found=10,
                snapshots_created=10,
                finished_at=datetime.now(UTC),
            )

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=slow_scrape)

        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        pipeline_run = PipelineRun()

        async def force_stop_after_start():
            await asyncio.sleep(0.05)
            orch.force_stop(pipeline_run)

        with (
            _patch_session_and_companies(companies),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            stop_task = asyncio.create_task(force_stop_after_start())
            run = await orch.run(pipeline_run)
            await stop_task

        assert run.status == PipelineStatus.CANCELLED
        for slug in run.company_states:
            assert run.company_states[slug] in (
                CompanyState.CANCELLED,
                CompanyState.SKIPPED,
            ), f"{slug} has unexpected state: {run.company_states[slug]}"

    async def test_post_gather_fixup_uses_cancelled_for_cancelled_tasks(self):
        companies = [_make_company("bds"), _make_company("marketsource")]

        call_count = 0

        async def slow_then_cancel_scrape(c, s):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(10)
            return ScrapeResult(
                company_id=c.id,
                company_slug=c.slug,
                postings_found=5,
                snapshots_created=5,
                finished_at=datetime.now(UTC),
            )

        mock_adapter = AsyncMock()
        mock_adapter.scrape = AsyncMock(side_effect=slow_then_cancel_scrape)

        orch = PipelineOrchestrator(max_retries=1, retry_base_delay=0.01)
        pipeline_run = PipelineRun()

        async def force_stop_soon():
            await asyncio.sleep(0.05)
            orch.force_stop(pipeline_run)

        with (
            _patch_session_and_companies(companies),
            patch(
                "compgraph.scrapers.orchestrator.get_adapter",
                return_value=mock_adapter,
            ),
        ):
            stop_task = asyncio.create_task(force_stop_soon())
            run = await orch.run(pipeline_run)
            await stop_task

        for slug, state in run.company_states.items():
            assert state != CompanyState.RUNNING, f"{slug} still RUNNING after force stop"
            assert state != CompanyState.PENDING, f"{slug} still PENDING after force stop"
