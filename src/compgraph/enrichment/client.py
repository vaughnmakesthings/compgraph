"""Anthropic API client factory — singleton AsyncAnthropic for enrichment pipeline."""

from __future__ import annotations

import re

import anthropic

from compgraph.config import settings

_client: anthropic.AsyncAnthropic | None = None

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*?)```\s*$", re.DOTALL)


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM response text.

    Models sometimes wrap JSON in ```json ... ``` despite instructions not to.
    """
    m = _FENCE_RE.match(text.strip())
    return m.group(1).strip() if m else text


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
