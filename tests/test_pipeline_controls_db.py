from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock


class TestGetLatestPipelineStatus:
    def _make_run(
        self,
        company_name: str,
        slug: str,
        status: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        jobs_found: int = 0,
        snapshots_created: int = 0,
    ) -> MagicMock:
        row = MagicMock()
        row.company_name = company_name
        row.slug = slug
        row.status = status
        row.started_at = started_at
        row.completed_at = completed_at
        row.jobs_found = jobs_found
        row.snapshots_created = snapshots_created
        row.errors = None
        return row

    def test_returns_none_when_no_runs(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        session = MagicMock()
        session.execute = MagicMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            )
        )
        result = get_latest_pipeline_status(session)
        assert result is None

    def test_aggregates_company_results(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        ts = datetime(2026, 2, 16, 14, 0, 0, tzinfo=UTC)
        runs = [
            self._make_run("T-ROC", "t-roc", "completed", ts, ts, 102, 102),
            self._make_run("2020 Companies", "2020", "completed", ts, ts, 700, 700),
        ]
        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(
                    scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=ts)))
                ),
                MagicMock(all=MagicMock(return_value=runs)),
            ]
        )
        result = get_latest_pipeline_status(session)
        assert result is not None
        assert result["total_postings_found"] == 802
        assert result["companies_succeeded"] == 2
        assert result["status"] == "success"

    def test_mixed_status_shows_running(self) -> None:
        from compgraph.dashboard.queries import get_latest_pipeline_status

        ts = datetime(2026, 2, 16, 14, 0, 0, tzinfo=UTC)
        runs = [
            self._make_run("T-ROC", "t-roc", "completed", ts, ts, 102, 102),
            self._make_run("2020 Companies", "2020", "pending", ts, None, 0, 0),
        ]
        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(
                    scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=ts)))
                ),
                MagicMock(all=MagicMock(return_value=runs)),
            ]
        )
        result = get_latest_pipeline_status(session)
        assert result is not None
        assert result["status"] == "running"
        assert result["company_states"]["t-roc"] == "completed"
        assert result["company_states"]["2020"] == "pending"
