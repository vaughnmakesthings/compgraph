"""Tests for posting deactivation logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from compgraph.scrapers.deactivation import GRACE_PERIOD_RUNS, deactivate_stale_postings


class TestDeactivateStalePostings:
    """Unit tests for deactivate_stale_postings."""

    @pytest.mark.asyncio
    async def test_skip_when_fewer_than_grace_period_runs(self) -> None:
        """Should return 0 when fewer than 3 completed runs exist."""
        from unittest.mock import MagicMock

        session = AsyncMock()
        # First execute returns no cutoff (fewer than 3 runs)
        cutoff_result = MagicMock()
        cutoff_result.scalar_one_or_none.return_value = None
        session.execute.return_value = cutoff_result

        company_id = uuid.uuid4()
        scrape_run_id = uuid.uuid4()

        count = await deactivate_stale_postings(session, company_id, scrape_run_id)
        assert count == 0
        # Should only have been called once (the cutoff query)
        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_deactivate_postings_older_than_cutoff(self) -> None:
        """Should deactivate postings with last_seen_at before the 3rd run cutoff."""
        from unittest.mock import MagicMock

        session = AsyncMock()
        cutoff_time = datetime.now(UTC) - timedelta(days=3)

        cutoff_result = MagicMock()
        cutoff_result.scalar_one_or_none.return_value = cutoff_time

        update_result = MagicMock()
        update_result.rowcount = 5

        session.execute.side_effect = [cutoff_result, update_result]

        company_id = uuid.uuid4()
        scrape_run_id = uuid.uuid4()

        count = await deactivate_stale_postings(session, company_id, scrape_run_id)
        assert count == 5
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_zero_deactivations_within_grace_period(self) -> None:
        """Should return 0 when all postings are within the grace period."""
        from unittest.mock import MagicMock

        session = AsyncMock()
        cutoff_time = datetime.now(UTC) - timedelta(days=3)

        cutoff_result = MagicMock()
        cutoff_result.scalar_one_or_none.return_value = cutoff_time

        update_result = MagicMock()
        update_result.rowcount = 0

        session.execute.side_effect = [cutoff_result, update_result]

        company_id = uuid.uuid4()
        scrape_run_id = uuid.uuid4()

        count = await deactivate_stale_postings(session, company_id, scrape_run_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_deactivation_uses_correct_company_filter(self) -> None:
        """Should only deactivate postings for the specified company."""
        from unittest.mock import MagicMock

        session = AsyncMock()
        cutoff_time = datetime.now(UTC) - timedelta(days=3)

        cutoff_result = MagicMock()
        cutoff_result.scalar_one_or_none.return_value = cutoff_time

        update_result = MagicMock()
        update_result.rowcount = 2

        session.execute.side_effect = [cutoff_result, update_result]

        company_id = uuid.uuid4()
        scrape_run_id = uuid.uuid4()

        count = await deactivate_stale_postings(session, company_id, scrape_run_id)
        assert count == 2

        # Verify the update statement was called (second execute call)
        update_call = session.execute.call_args_list[1]
        stmt = update_call[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "postings" in compiled.lower()
        assert "is_active" in compiled.lower()
        assert company_id.hex in compiled

    def test_grace_period_constant(self) -> None:
        """Grace period should be 3 runs."""
        assert GRACE_PERIOD_RUNS == 3


class TestScrapeResultPostingsClosed:
    """Tests for postings_closed field on ScrapeResult."""

    def test_default_postings_closed_is_zero(self) -> None:
        from compgraph.scrapers.base import ScrapeResult

        result = ScrapeResult(company_id=uuid.uuid4(), company_slug="test")
        assert result.postings_closed == 0

    def test_postings_closed_can_be_set(self) -> None:
        from compgraph.scrapers.base import ScrapeResult

        result = ScrapeResult(company_id=uuid.uuid4(), company_slug="test")
        result.postings_closed = 10
        assert result.postings_closed == 10


class TestScrapeRunPostingsClosedColumn:
    """Tests for postings_closed column on ScrapeRun model."""

    def test_scrape_run_has_postings_closed_column(self) -> None:
        from compgraph.db.models import ScrapeRun

        assert hasattr(ScrapeRun, "postings_closed")
        col = ScrapeRun.__table__.columns["postings_closed"]
        assert col.nullable is False
        assert str(col.server_default.arg) == "0"  # type: ignore[union-attr]


class TestICIMSIsActiveOnConflict:
    """Tests that iCIMS persist_posting sets is_active=True on conflict."""

    def test_icims_persist_posting_sets_is_active_on_conflict(self) -> None:
        """Verify the ON CONFLICT clause includes is_active=True."""
        import inspect

        from compgraph.scrapers.icims import persist_posting

        source = inspect.getsource(persist_posting)
        # The ON CONFLICT SET should include is_active
        assert '"is_active": True' in source or "'is_active': True" in source
