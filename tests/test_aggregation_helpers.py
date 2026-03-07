from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import patch

from compgraph.aggregation.helpers import new_row_id, safe_float, safe_uuid_str, today_utc


class TestNewRowId:
    def test_returns_string(self) -> None:
        result = new_row_id()
        assert isinstance(result, str)

    def test_returns_valid_uuid(self) -> None:
        result = new_row_id()
        parsed = uuid.UUID(result)
        assert parsed.version == 4

    def test_returns_unique_values(self) -> None:
        ids = {new_row_id() for _ in range(100)}
        assert len(ids) == 100


class TestSafeUuidStr:
    def test_none_returns_none(self) -> None:
        assert safe_uuid_str(None) is None

    def test_uuid_returns_string(self) -> None:
        val = uuid.uuid4()
        result = safe_uuid_str(val)
        assert result == str(val)
        assert isinstance(result, str)

    def test_string_passes_through(self) -> None:
        val = "abc-123"
        assert safe_uuid_str(val) == "abc-123"


class TestSafeFloat:
    def test_none_returns_none(self) -> None:
        assert safe_float(None) is None

    def test_int_returns_float(self) -> None:
        result = safe_float(42)
        assert result == 42.0
        assert isinstance(result, float)

    def test_float_passes_through(self) -> None:
        assert safe_float(3.14) == 3.14

    def test_decimal_like_string(self) -> None:
        assert safe_float("99.5") == 99.5

    def test_zero(self) -> None:
        result = safe_float(0)
        assert result == 0.0
        assert isinstance(result, float)


class TestTodayUtc:
    def test_returns_date(self) -> None:
        result = today_utc()
        assert isinstance(result, date)

    def test_matches_utc_date(self) -> None:
        expected = datetime.now(UTC).date()
        assert today_utc() == expected

    def test_uses_utc_timezone(self) -> None:
        fake_utc = datetime(2026, 1, 15, 23, 59, 59, tzinfo=UTC)
        with patch("compgraph.aggregation.helpers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = today_utc()
            assert result == date(2026, 1, 15)
            mock_dt.now.assert_called_once_with(UTC)
