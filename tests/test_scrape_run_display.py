"""Tests for scrape run display formatting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from compgraph.dashboard.queries import _format_completed_at


class TestFormatCompletedAt:
    def test_completed_run_returns_timestamp(self):
        run = MagicMock()
        run.completed_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC)
        run.status = "completed"
        run.started_at = datetime(2026, 2, 16, 11, 50, 0, tzinfo=UTC)
        assert _format_completed_at(run) == run.completed_at

    def test_pending_run_shows_elapsed(self):
        run = MagicMock()
        run.completed_at = None
        run.status = "pending"
        run.started_at = datetime.now(UTC) - timedelta(minutes=12)
        result = str(_format_completed_at(run))
        assert "12m" in result
        assert "elapsed" in result.lower()

    def test_in_progress_fallback(self):
        run = MagicMock()
        run.completed_at = None
        run.status = "failed"
        run.started_at = datetime.now(UTC) - timedelta(minutes=5)
        assert _format_completed_at(run) == "In Progress"
