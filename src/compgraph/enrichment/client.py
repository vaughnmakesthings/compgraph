"""Anthropic API client factory — singleton AsyncAnthropic for enrichment pipeline."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import anthropic

from compgraph.config import settings

if TYPE_CHECKING:
    import instructor

_client: anthropic.AsyncAnthropic | None = None
_instructor_client: instructor.AsyncInstructor | None = None

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*?)```\s*$", re.DOTALL)


# TODO: Remove after USE_INSTRUCTOR flag is permanently enabled
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


def get_instructor_client() -> instructor.AsyncInstructor:
    import instructor as _instructor

    global _instructor_client
    if _instructor_client is None:
        _instructor_client = _instructor.from_anthropic(get_anthropic_client())
    return _instructor_client


def reset_client() -> None:
    """Reset the singleton clients. Used in tests."""
    global _client, _instructor_client
    _client = None
    _instructor_client = None
