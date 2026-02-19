"""Shared test helpers for CompGraph enrichment tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


def make_mock_response(data: dict, stop_reason: str = "end_turn") -> MagicMock:
    """Create a mock Anthropic API response."""
    content_block = MagicMock()
    content_block.text = json.dumps(data)
    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = stop_reason
    return response


def make_mock_client(response_data: dict, stop_reason: str = "end_turn") -> AsyncMock:
    """Create a mock AsyncAnthropic client."""
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=make_mock_response(response_data, stop_reason))
    return client
