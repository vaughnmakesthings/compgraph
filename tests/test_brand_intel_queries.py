from __future__ import annotations

import os

os.environ.setdefault("DATABASE_PASSWORD", "test-placeholder")

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from compgraph.dashboard.queries import get_brand_intel, get_retailer_intel


def _make_row(name: str, active_postings: int, first_seen: datetime) -> SimpleNamespace:
    return SimpleNamespace(name=name, active_postings=active_postings, first_seen=first_seen)


class TestGetBrandIntel:
    def test_returns_correct_keys(self) -> None:
        ts = datetime(2026, 1, 10, tzinfo=UTC)
        session = MagicMock()
        session.execute.return_value = MagicMock(
            all=MagicMock(return_value=[_make_row("Acme Corp", 5, ts)])
        )

        result = get_brand_intel(session, uuid.uuid4())

        assert len(result) == 1
        assert set(result[0].keys()) == {"name", "active_postings", "first_seen"}

    def test_values_match_row(self) -> None:
        ts = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)
        session = MagicMock()
        session.execute.return_value = MagicMock(
            all=MagicMock(return_value=[_make_row("Samsung", 12, ts)])
        )

        result = get_brand_intel(session, uuid.uuid4())

        assert result[0]["name"] == "Samsung"
        assert result[0]["active_postings"] == 12
        assert result[0]["first_seen"] == ts

    def test_empty_result(self) -> None:
        session = MagicMock()
        session.execute.return_value = MagicMock(all=MagicMock(return_value=[]))

        result = get_brand_intel(session, uuid.uuid4())

        assert result == []

    def test_multiple_brands_preserve_order(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [
            _make_row("TopBrand", 20, ts),
            _make_row("MidBrand", 10, ts),
            _make_row("LowBrand", 2, ts),
        ]
        session = MagicMock()
        session.execute.return_value = MagicMock(all=MagicMock(return_value=rows))

        result = get_brand_intel(session, uuid.uuid4())

        assert len(result) == 3
        assert result[0]["name"] == "TopBrand"
        assert result[1]["name"] == "MidBrand"
        assert result[2]["name"] == "LowBrand"
        assert (
            result[0]["active_postings"]
            > result[1]["active_postings"]
            > result[2]["active_postings"]
        )


class TestGetRetailerIntel:
    def test_returns_correct_keys(self) -> None:
        ts = datetime(2026, 1, 15, tzinfo=UTC)
        session = MagicMock()
        session.execute.return_value = MagicMock(
            all=MagicMock(return_value=[_make_row("Walmart", 8, ts)])
        )

        result = get_retailer_intel(session, uuid.uuid4())

        assert len(result) == 1
        assert set(result[0].keys()) == {"name", "active_postings", "first_seen"}

    def test_values_match_row(self) -> None:
        ts = datetime(2026, 2, 10, 8, 0, 0, tzinfo=UTC)
        session = MagicMock()
        session.execute.return_value = MagicMock(
            all=MagicMock(return_value=[_make_row("Target", 6, ts)])
        )

        result = get_retailer_intel(session, uuid.uuid4())

        assert result[0]["name"] == "Target"
        assert result[0]["active_postings"] == 6
        assert result[0]["first_seen"] == ts

    def test_empty_result(self) -> None:
        session = MagicMock()
        session.execute.return_value = MagicMock(all=MagicMock(return_value=[]))

        result = get_retailer_intel(session, uuid.uuid4())

        assert result == []

    def test_multiple_retailers_preserve_order(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [
            _make_row("Costco", 15, ts),
            _make_row("Home Depot", 7, ts),
            _make_row("Best Buy", 3, ts),
        ]
        session = MagicMock()
        session.execute.return_value = MagicMock(all=MagicMock(return_value=rows))

        result = get_retailer_intel(session, uuid.uuid4())

        assert len(result) == 3
        assert result[0]["name"] == "Costco"
        assert result[2]["name"] == "Best Buy"
