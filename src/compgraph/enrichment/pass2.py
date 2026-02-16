"""Pass 2 enrichment — Sonnet entity extraction."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

import anthropic

from compgraph.config import settings
from compgraph.enrichment.prompts import PASS2_SYSTEM_PROMPT, build_pass2_messages
from compgraph.enrichment.schemas import Pass2Result

logger = logging.getLogger(__name__)

# Retry configuration
_RATE_LIMIT_BASE_DELAY = 60.0
_MAX_RETRIES = 3


async def _retry_sleep(delay: float) -> None:
    """Sleep wrapper for retry backoff. Extracted for testability."""
    await asyncio.sleep(delay)


async def enrich_posting_pass2(
    client: anthropic.AsyncAnthropic,
    posting_id: uuid.UUID,
    title: str,
    location: str,
    content_role_specific: str | None,
    full_text: str,
) -> Pass2Result:
    """Run Pass 2 enrichment on a single posting.

    Calls Sonnet to extract brand and retailer entities.
    Uses content_role_specific from Pass 1 as primary input.
    Retries on rate limits and transient API errors.

    Args:
        client: AsyncAnthropic client instance.
        posting_id: UUID of the posting (for logging).
        title: Raw title from the posting snapshot.
        location: Raw location from the posting snapshot.
        content_role_specific: Role-specific text from Pass 1 (preferred input).
        full_text: Full text content from the posting snapshot (fallback).

    Returns:
        Pass2Result with extracted entities.

    Raises:
        anthropic.APIError: After exhausting retries.
        ValueError: If response cannot be parsed into Pass2Result.
    """
    messages = build_pass2_messages(title, location, content_role_specific, full_text)

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.messages.create(
                model=settings.ENRICHMENT_MODEL_PASS2,
                max_tokens=1024,
                temperature=0.1,
                system=[
                    {
                        "type": "text",
                        "text": PASS2_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            )

            if response.stop_reason == "max_tokens":
                logger.warning(
                    "Pass 2 truncated for posting %s (max_tokens reached)",
                    posting_id,
                )

            text_content = response.content[0].text

            try:
                data = json.loads(text_content)
                return Pass2Result.model_validate(data)
            except (json.JSONDecodeError, Exception) as parse_err:
                raise ValueError(
                    f"Failed to parse Pass 2 response for posting {posting_id}: {parse_err}"
                ) from parse_err

        except anthropic.RateLimitError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                delay = _RATE_LIMIT_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited on posting %s, retrying in %.0fs (attempt %d/%d)",
                    posting_id,
                    delay,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                await _retry_sleep(delay)
            else:
                logger.error("Rate limit exhausted for posting %s", posting_id)

        except anthropic.APIStatusError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                delay = 2.0 * (2**attempt)
                logger.warning(
                    "API error on posting %s: %s, retrying in %.0fs (attempt %d/%d)",
                    posting_id,
                    e.status_code,
                    delay,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                await _retry_sleep(delay)
            else:
                logger.error("API error exhausted for posting %s: %s", posting_id, e.status_code)

    raise last_error  # type: ignore[misc]
