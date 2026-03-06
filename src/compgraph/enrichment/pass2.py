"""Pass 2 enrichment — Sonnet entity extraction."""

from __future__ import annotations

import uuid

import anthropic

from compgraph.config import settings
from compgraph.enrichment.prompts import PASS2_SYSTEM_PROMPT, build_pass2_messages
from compgraph.enrichment.retry import LLMCallResult, call_llm
from compgraph.enrichment.schemas import Pass2Result


async def enrich_posting_pass2(
    client: anthropic.AsyncAnthropic,
    posting_id: uuid.UUID,
    title: str,
    location: str,
    content_role_specific: str | None,
    full_text: str,
) -> LLMCallResult[Pass2Result]:
    """Run Pass 2 enrichment on a single posting.

    Calls Sonnet to extract brand and retailer entities.
    Uses content_role_specific from Pass 1 as primary input.
    Routes through the feature-flagged call_llm dispatcher which selects
    between Instructor (structured output) and manual JSON parsing paths.

    Args:
        client: AsyncAnthropic client instance.
        posting_id: UUID of the posting (for logging).
        title: Raw title from the posting snapshot.
        location: Raw location from the posting snapshot.
        content_role_specific: Role-specific text from Pass 1 (preferred input).
        full_text: Full text content from the posting snapshot (fallback).

    Returns:
        LLMCallResult wrapping Pass2Result with token usage.

    Raises:
        EnrichmentAPIError: After exhausting retries or on permanent/parse errors.
    """
    messages = build_pass2_messages(title, location, content_role_specific, full_text)

    return await call_llm(
        client,
        posting_id=posting_id,
        model=settings.ENRICHMENT_MODEL_PASS2,
        max_tokens=1024,
        system_prompt=PASS2_SYSTEM_PROMPT,
        messages=messages,
        result_type=Pass2Result,
        pass_label="Pass 2",  # noqa: S106
    )
