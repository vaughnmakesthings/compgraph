"""Pass 1 enrichment — Haiku classification and pay extraction."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import TYPE_CHECKING, cast

import anthropic

from compgraph.config import settings
from compgraph.enrichment.client import strip_markdown_fences
from compgraph.enrichment.prompts import PASS1_SYSTEM_PROMPT, build_pass1_messages
from compgraph.enrichment.schemas import Pass1Result

if TYPE_CHECKING:
    from anthropic.types import MessageParam

logger = logging.getLogger(__name__)

# Retry configuration
_RATE_LIMIT_BASE_DELAY = 60.0
_MAX_RETRIES = 3
_PERMANENT_STATUS_CODES = frozenset({400, 401, 403, 422})
_PERMANENT_STATUS_CODES = frozenset({400, 401, 403, 422})


async def _retry_sleep(delay: float) -> None:
    """Sleep wrapper for retry backoff. Extracted for testability."""
    await asyncio.sleep(delay)


async def enrich_posting_pass1(
    client: anthropic.AsyncAnthropic,
    posting_id: uuid.UUID,
    title: str,
    location: str,
    full_text: str,
) -> Pass1Result:
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
        Pass1Result with extracted classification data.

    Raises:
        anthropic.APIError: After exhausting retries.
        ValueError: If response cannot be parsed into Pass1Result.
    """
    messages = cast("list[MessageParam]", build_pass1_messages(title, location, full_text))

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.messages.create(
                model=settings.ENRICHMENT_MODEL_PASS1,
                max_tokens=2048,
                temperature=0.1,
                system=[
                    {
                        "type": "text",
                        "text": PASS1_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            )

            # Check for max_tokens truncation
            if response.stop_reason == "max_tokens":
                logger.warning(
                    "Pass 1 truncated for posting %s (max_tokens reached)",
                    posting_id,
                )

            # Extract text content from response (first block is always TextBlock)
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                raise ValueError(
                    f"Unexpected content block type for posting {posting_id}: "
                    f"{type(content_block).__name__}"
                )
            text_content: str = content_block.text  # type: ignore[union-attr]

            # Parse JSON response into Pass1Result
            try:
                cleaned = strip_markdown_fences(text_content)
                data = json.loads(cleaned)
                return Pass1Result.model_validate(data)
            except (json.JSONDecodeError, Exception) as parse_err:
                raise ValueError(
                    f"Failed to parse Pass 1 response for posting {posting_id}: {parse_err}"
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
            if e.status_code in _PERMANENT_STATUS_CODES:
                logger.error(
                    "Permanent API error %d for posting %s, not retrying",
                    e.status_code,
                    posting_id,
                )
                break
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
