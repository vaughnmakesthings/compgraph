"""Pass 1 enrichment — Haiku classification and pay extraction."""

from __future__ import annotations

import uuid

import anthropic

from compgraph.config import settings
from compgraph.enrichment.prompts import PASS1_SYSTEM_PROMPT, build_pass1_messages
from compgraph.enrichment.retry import LLMCallResult, call_llm_with_retry
from compgraph.enrichment.schemas import Pass1Result


async def enrich_posting_pass1(
    client: anthropic.AsyncAnthropic,
    posting_id: uuid.UUID,
    title: str,
    location: str,
    full_text: str,
) -> LLMCallResult[Pass1Result]:
    """Run Pass 1 enrichment on a single posting.

    Calls Haiku to classify the posting and extract structured fields.
    Retries on rate limits and transient API errors.

    Args:
        client: AsyncAnthropic client instance.
        posting_id: UUID of the posting (for logging).
        title: Raw title from the posting snapshot.
        location: Raw location from the posting snapshot.
        full_text: Full text content from the posting snapshot.

    Returns:
        LLMCallResult wrapping Pass1Result with token usage.

    Raises:
        EnrichmentAPIError: After exhausting retries or on permanent/parse errors.
    """
    messages = build_pass1_messages(title, location, full_text)

    return await call_llm_with_retry(
        client,
        posting_id=posting_id,
        model=settings.ENRICHMENT_MODEL_PASS1,
        max_tokens=2048,
        system_prompt=PASS1_SYSTEM_PROMPT,
        messages=messages,
        result_type=Pass1Result,
        pass_label="Pass 1",  # noqa: S106
    )
