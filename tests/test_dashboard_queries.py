from __future__ import annotations

import os

os.environ.setdefault("DATABASE_PASSWORD", "test-placeholder")

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from compgraph.dashboard.queries import freshness_color, get_last_scrape_timestamps


class TestFreshnessColor:
    def test_none_returns_gray(self) -> None:
        assert freshness_color(None) == "gray"

    def test_recent_returns_green(self) -> None:
        ts = datetime.now(UTC) - timedelta(hours=1)
        assert freshness_color(ts) == "green"

    def test_boundary_24h_returns_green(self) -> None:
        ts = datetime.now(UTC) - timedelta(hours=23, minutes=59)
        assert freshness_color(ts) == "green"

    def test_24h_returns_yellow(self) -> None:
        ts = datetime.now(UTC) - timedelta(hours=25)
        assert freshness_color(ts) == "yellow"

    def test_boundary_72h_returns_yellow(self) -> None:
        ts = datetime.now(UTC) - timedelta(hours=71, minutes=59)
        assert freshness_color(ts) == "yellow"

    def test_old_returns_red(self) -> None:
        ts = datetime.now(UTC) - timedelta(hours=73)
        assert freshness_color(ts) == "red"

    def test_very_old_returns_red(self) -> None:
        ts = datetime.now(UTC) - timedelta(days=30)
        assert freshness_color(ts) == "red"


class TestGetLastScrapeTimestamps:
    def _make_company_row(
        self, name: str, slug: str, last_scraped_at: datetime | None
    ) -> MagicMock:
        row = MagicMock()
        row.name = name
        row.slug = slug
        row.last_scraped_at = last_scraped_at
        return row

    def test_returns_companies_and_global(self) -> None:
        ts = datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC)
        company_rows = [self._make_company_row("T-ROC", "t-roc", ts)]
        global_ts = datetime(2026, 2, 15, 14, 0, 0, tzinfo=UTC)

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(all=MagicMock(return_value=company_rows)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=global_ts)),
            ]
        )

        result = get_last_scrape_timestamps(session)

        assert len(result) == 2
        assert result[0]["name"] == "T-ROC"
        assert result[0]["slug"] == "t-roc"
        assert result[0]["last_scraped_at"] == ts
        assert result[1]["name"] == "__global__"
        assert result[1]["last_scraped_at"] == global_ts

    def test_no_companies_still_has_global(self) -> None:
        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(all=MagicMock(return_value=[])),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            ]
        )

        result = get_last_scrape_timestamps(session)

        assert len(result) == 1
        assert result[0]["name"] == "__global__"
        assert result[0]["last_scraped_at"] is None

    def test_multiple_companies(self) -> None:
        ts1 = datetime(2026, 2, 14, 10, 0, 0, tzinfo=UTC)
        ts2 = datetime(2026, 2, 15, 8, 0, 0, tzinfo=UTC)
        company_rows = [
            self._make_company_row("BDS", "bds", ts1),
            self._make_company_row("T-ROC", "t-roc", ts2),
        ]

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(all=MagicMock(return_value=company_rows)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=ts2)),
            ]
        )

        result = get_last_scrape_timestamps(session)

        assert len(result) == 3
        assert result[0]["name"] == "BDS"
        assert result[1]["name"] == "T-ROC"
        assert result[2]["name"] == "__global__"

    def test_null_last_scraped_at(self) -> None:
        company_rows = [self._make_company_row("NewCo", "newco", None)]

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(all=MagicMock(return_value=company_rows)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            ]
        )

        result = get_last_scrape_timestamps(session)

        assert result[0]["last_scraped_at"] is None
