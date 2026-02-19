"""Shared retry logic for Anthropic API calls in the enrichment pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import TYPE_CHECKING, TypeVar, cast

import anthropic
from pydantic import BaseModel

from compgraph.enrichment.client import strip_markdown_fences

if TYPE_CHECKING:
    from anthropic.types import MessageParam

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Retry configuration
RATE_LIMIT_BASE_DELAY = 60.0
MAX_RETRIES = 3
PERMANENT_STATUS_CODES = frozenset({400, 401, 403, 422})


async def _retry_sleep(delay: float) -> None:
    """Sleep wrapper for retry backoff. Extracted for testability."""
    await asyncio.sleep(delay)


async def call_llm_with_retry(  # noqa: UP047
    client: anthropic.AsyncAnthropic,
    *,
    posting_id: uuid.UUID,
    model: str,
    max_tokens: int,
    system_prompt: str,
    messages: list[dict],
    result_type: type[T],
    pass_label: str,
) -> T:
    """Call Anthropic API with retry logic for rate limits and transient errors.

    Shared by both Pass 1 and Pass 2 enrichment functions.

    Args:
        client: AsyncAnthropic client instance.
        posting_id: UUID of the posting (for logging).
        model: Model ID to use.
        max_tokens: Maximum tokens in response.
        system_prompt: System prompt text.
        messages: Message list for the API call.
        result_type: Pydantic model class to parse the response into.
        pass_label: Human-readable label for log messages (e.g. "Pass 1").

    Returns:
        Parsed result of type T.

    Raises:
        anthropic.APIError: After exhausting retries.
        ValueError: If response cannot be parsed.
    """
    typed_messages = cast("list[MessageParam]", messages)

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=typed_messages,
            )

            # Check for max_tokens truncation
            if response.stop_reason == "max_tokens":
                logger.warning(
                    "%s truncated for posting %s (max_tokens reached)",
                    pass_label,
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

            # Parse JSON response into result type
            try:
                cleaned = strip_markdown_fences(text_content)
                data = json.loads(cleaned)
                return result_type.model_validate(data)
            except Exception as parse_err:
                raise ValueError(
                    f"Failed to parse {pass_label} response for posting {posting_id}: {parse_err}"
                ) from parse_err

        except anthropic.RateLimitError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RATE_LIMIT_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited on posting %s, retrying in %.0fs (attempt %d/%d)",
                    posting_id,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await _retry_sleep(delay)
            else:
                logger.error("Rate limit exhausted for posting %s", posting_id)

        except anthropic.APIStatusError as e:
            last_error = e
            if e.status_code in PERMANENT_STATUS_CODES:
                logger.error(
                    "Permanent API error %d for posting %s, not retrying",
                    e.status_code,
                    posting_id,
                )
                break
            if attempt < MAX_RETRIES - 1:
                delay = 2.0 * (2**attempt)
                logger.warning(
                    "API error on posting %s: %s, retrying in %.0fs (attempt %d/%d)",
                    posting_id,
                    e.status_code,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await _retry_sleep(delay)
            else:
                logger.error("API error exhausted for posting %s: %s", posting_id, e.status_code)

    raise last_error  # type: ignore[misc]
