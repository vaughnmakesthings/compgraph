"""Tests for _maybe_geocode_posting in persistence.py."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.scrapers.persistence import _maybe_geocode_posting


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


class TestMaybeGeocodePosting:
    async def test_skips_when_latitude_already_set(self, mock_session: AsyncMock):
        """Already-geocoded postings should be skipped immediately."""
        posting_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 40.7128
        mock_session.execute.return_value = mock_result

        await _maybe_geocode_posting(mock_session, posting_id, "New York, NY")

        # Only the latitude check query should be executed
        assert mock_session.execute.call_count == 1

    @patch("compgraph.geocoding.geocode_location", new_callable=AsyncMock)
    @patch("compgraph.geocoding.compute_h3_index")
    async def test_geocodes_and_updates_when_no_latitude(
        self, mock_h3: MagicMock, mock_geocode: AsyncMock, mock_session: AsyncMock
    ):
        """Postings without latitude should be geocoded and updated."""
        posting_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_geocode.return_value = (40.7128, -74.0060)
        mock_h3.return_value = "862a1072fffffff"

        await _maybe_geocode_posting(mock_session, posting_id, "New York, NY")

        mock_geocode.assert_awaited_once_with("New York, NY")
        mock_h3.assert_called_once_with(40.7128, -74.0060)
        # SELECT (latitude check) + UPDATE (set coords)
        assert mock_session.execute.call_count == 2

    @patch("compgraph.geocoding.geocode_location", new_callable=AsyncMock)
    async def test_no_update_when_geocode_returns_none(
        self, mock_geocode: AsyncMock, mock_session: AsyncMock
    ):
        """When geocoding finds no results, no UPDATE should be issued."""
        posting_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_geocode.return_value = None

        await _maybe_geocode_posting(mock_session, posting_id, "Remote")

        mock_geocode.assert_awaited_once_with("Remote")
        # Only the latitude check query, no UPDATE
        assert mock_session.execute.call_count == 1

    @patch("compgraph.geocoding.geocode_location", new_callable=AsyncMock)
    async def test_exception_is_caught_and_logged(
        self, mock_geocode: AsyncMock, mock_session: AsyncMock
    ):
        """Geocoding exceptions should be caught, not propagated."""
        posting_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_geocode.side_effect = Exception("network timeout")

        # Should not raise
        await _maybe_geocode_posting(mock_session, posting_id, "Error City")
