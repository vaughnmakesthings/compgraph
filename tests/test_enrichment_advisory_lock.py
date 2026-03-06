from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.enrichment.orchestrator import (
    ENRICHMENT_ADVISORY_LOCK_KEY,
    EnrichmentOrchestrator,
    EnrichmentRun,
    EnrichmentStatus,
    EnrichResult,
)


@pytest.fixture
def orchestrator() -> EnrichmentOrchestrator:
    with patch("compgraph.enrichment.orchestrator.get_anthropic_client"):
        return EnrichmentOrchestrator(batch_size=10, concurrency=2)


@pytest.fixture
def enrichment_run() -> EnrichmentRun:
    return EnrichmentRun()


def _make_lock_session(acquired: bool) -> AsyncMock:
    scalar_result = MagicMock()
    scalar_result.scalar.return_value = acquired
    session = AsyncMock()
    session.execute.return_value = scalar_result
    return session


def _make_session_ctx(session: AsyncMock) -> AsyncMock:
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestAdvisoryLockAcquired:
    @pytest.mark.asyncio
    async def test_run_full_acquires_lock_and_runs_pipeline(
        self, orchestrator: EnrichmentOrchestrator, enrichment_run: EnrichmentRun
    ) -> None:
        lock_session = _make_lock_session(acquired=True)
        fingerprint_session = AsyncMock()

        call_count = 0

        def factory_side_effect() -> AsyncMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_session_ctx(lock_session)
            return _make_session_ctx(fingerprint_session)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                side_effect=factory_side_effect,
            ),
            patch(
                "compgraph.enrichment.fingerprint.detect_reposts",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch.object(orchestrator, "run_pass1", new_callable=AsyncMock) as mock_pass1,
            patch.object(orchestrator, "run_pass2", new_callable=AsyncMock) as mock_pass2,
        ):
            mock_pass1.return_value = EnrichResult(succeeded=5)
            mock_pass2.return_value = EnrichResult(succeeded=3)

            p1, p2 = await orchestrator.run_full(enrichment_run)

            assert p1.succeeded == 5
            assert p2.succeeded == 3
            mock_pass1.assert_awaited_once()
            mock_pass2.assert_awaited_once()

            lock_session.execute.assert_awaited_once()
            call_args = lock_session.execute.call_args
            assert str(call_args[0][0]) == "SELECT pg_try_advisory_lock(:key)"
            assert call_args[0][1]["key"] == ENRICHMENT_ADVISORY_LOCK_KEY


class TestAdvisoryLockBlocked:
    @pytest.mark.asyncio
    async def test_run_full_returns_early_when_lock_not_acquired(
        self, orchestrator: EnrichmentOrchestrator, enrichment_run: EnrichmentRun
    ) -> None:
        lock_session = _make_lock_session(acquired=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=_make_session_ctx(lock_session),
            ),
            patch.object(orchestrator, "run_pass1", new_callable=AsyncMock) as mock_pass1,
            patch.object(orchestrator, "run_pass2", new_callable=AsyncMock) as mock_pass2,
        ):
            p1, p2 = await orchestrator.run_full(enrichment_run)

            assert p1.succeeded == 0
            assert p2.succeeded == 0
            assert enrichment_run.status == EnrichmentStatus.FAILED
            assert enrichment_run.finished_at is not None
            assert "concurrent" in (enrichment_run.error_summary or "")
            mock_pass1.assert_not_awaited()
            mock_pass2.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_lock_key_is_stable_bigint(self) -> None:
        assert isinstance(ENRICHMENT_ADVISORY_LOCK_KEY, int)
        assert -(2**63) <= ENRICHMENT_ADVISORY_LOCK_KEY < 2**63
