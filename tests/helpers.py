"""Shared test helpers for CompGraph enrichment tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


def make_mock_response(
    data: dict,
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Create a mock Anthropic API response with token usage."""
    content_block = MagicMock()
    content_block.text = json.dumps(data)
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = stop_reason
    response.usage = usage
    return response


def make_mock_client(
    response_data: dict,
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> AsyncMock:
    """Create a mock AsyncAnthropic client."""
    client = AsyncMock()
    client.messages.create = AsyncMock(
        return_value=make_mock_response(response_data, stop_reason, input_tokens, output_tokens)
    )
    return client
