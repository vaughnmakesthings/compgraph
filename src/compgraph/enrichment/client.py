"""Anthropic API client factory — singleton AsyncAnthropic for enrichment pipeline."""

from __future__ import annotations

import anthropic

from compgraph.config import settings

_client: anthropic.AsyncAnthropic | None = None


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    """Return a shared AsyncAnthropic client (singleton).

    Reuses the same connection pool across all enrichment calls.
    """
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def reset_client() -> None:
    """Reset the singleton client. Used in tests."""
    global _client
    _client = None
