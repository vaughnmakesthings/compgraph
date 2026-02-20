"""Shared retry logic for Anthropic API calls in the enrichment pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar, cast

import anthropic
from pydantic import BaseModel, ValidationError

from compgraph.enrichment.client import strip_markdown_fences

if TYPE_CHECKING:
    from anthropic.types import MessageParam

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Retry configuration
RATE_LIMIT_BASE_DELAY = 60.0
MAX_RETRIES = 3
PERMANENT_STATUS_CODES = frozenset({400, 401, 403, 422})

# Quota detection thresholds
_QUOTA_RETRY_AFTER_THRESHOLD = 300  # seconds — retry-after > 5min suggests quota
_QUOTA_KEYWORDS = ("usage limit", "spending limit", "quota exceeded", "billing")


class ErrorCategory(StrEnum):
    """Classification of API errors for circuit breaker decisions."""

    RATE_LIMIT = "rate_limit"
    QUOTA_EXHAUSTED = "quota_exhausted"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    PARSE_ERROR = "parse_error"


# Categories that indicate systemic API problems (vs per-posting issues)
API_FAILURE_CATEGORIES = frozenset(
    {ErrorCategory.RATE_LIMIT, ErrorCategory.QUOTA_EXHAUSTED, ErrorCategory.TRANSIENT}
)


class EnrichmentAPIError(Exception):
    """Wraps API errors with classification for circuit breaker decisions."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        original: Exception | None = None,
    ):
        super().__init__(message)
        self.category = category
        self.original = original


@dataclass
class LLMCallResult(Generic[T]):  # noqa: UP046
    """Result from an LLM call including token usage."""

    result: T
    input_tokens: int
    output_tokens: int


def _classify_rate_limit(error: anthropic.RateLimitError) -> ErrorCategory:
    """Distinguish rate-limit from quota exhaustion based on headers and message."""
    # Check retry-after header (> 5 min suggests quota, not transient rate limit)
    if hasattr(error, "response") and error.response is not None:
        retry_after_str = error.response.headers.get("retry-after", "")
        try:
            if int(retry_after_str) > _QUOTA_RETRY_AFTER_THRESHOLD:
                return ErrorCategory.QUOTA_EXHAUSTED
        except (ValueError, TypeError):
            pass

    # Check error message for quota keywords
    error_text = ""
    if hasattr(error, "message") and error.message:
        error_text = str(error.message).lower()
    if any(kw in error_text for kw in _QUOTA_KEYWORDS):
        return ErrorCategory.QUOTA_EXHAUSTED

    return ErrorCategory.RATE_LIMIT


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
) -> LLMCallResult[T]:
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
        LLMCallResult containing parsed result and token usage.

    Raises:
        EnrichmentAPIError: After exhausting retries or on permanent/parse errors.
    """
    typed_messages = cast("list[MessageParam]", messages)

    last_error: Exception | None = None
    last_category: ErrorCategory = ErrorCategory.TRANSIENT
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

            # Extract token usage
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "input_tokens", 0) or 0
                output_tokens = getattr(response.usage, "output_tokens", 0) or 0

            # Check for max_tokens truncation
            if response.stop_reason == "max_tokens":
                logger.warning(
                    "%s truncated for posting %s (max_tokens reached)",
                    pass_label,
                    posting_id,
                )

            # Extract text content from response (first block is always TextBlock)
            if not response.content:
                raise EnrichmentAPIError(
                    f"Empty content list in API response for posting {posting_id}",
                    category=ErrorCategory.PARSE_ERROR,
                )
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                raise EnrichmentAPIError(
                    f"Unexpected content block type for posting {posting_id}: "
                    f"{type(content_block).__name__}",
                    category=ErrorCategory.PARSE_ERROR,
                )
            text_content: str = content_block.text  # type: ignore[union-attr]

            # Parse JSON response into result type
            try:
                cleaned = strip_markdown_fences(text_content)
                data = json.loads(cleaned)
                parsed = result_type.model_validate(data)
                return LLMCallResult(
                    result=parsed,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except (json.JSONDecodeError, ValidationError) as parse_err:
                raise EnrichmentAPIError(
                    f"Failed to parse {pass_label} response for posting {posting_id}: {parse_err}",
                    category=ErrorCategory.PARSE_ERROR,
                    original=parse_err,
                ) from parse_err
            except Exception as unexpected_err:
                raise EnrichmentAPIError(
                    f"Unexpected error parsing {pass_label} response "
                    f"for posting {posting_id}: {unexpected_err}",
                    category=ErrorCategory.TRANSIENT,
                    original=unexpected_err,
                ) from unexpected_err

        except EnrichmentAPIError:
            raise  # Don't wrap our own errors

        except anthropic.RateLimitError as e:
            last_error = e
            last_category = _classify_rate_limit(e)
            if attempt < MAX_RETRIES - 1:
                delay = RATE_LIMIT_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited on posting %s (%s), retrying in %.0fs (attempt %d/%d)",
                    posting_id,
                    last_category,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await _retry_sleep(delay)
            else:
                logger.error("Rate limit exhausted for posting %s (%s)", posting_id, last_category)

        except anthropic.APIStatusError as e:
            last_error = e
            if e.status_code in PERMANENT_STATUS_CODES:
                logger.error(
                    "Permanent API error %d for posting %s, not retrying",
                    e.status_code,
                    posting_id,
                )
                raise EnrichmentAPIError(
                    f"Permanent API error {e.status_code} for posting {posting_id}",
                    category=ErrorCategory.PERMANENT,
                    original=e,
                ) from e
            last_category = ErrorCategory.TRANSIENT
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

    raise EnrichmentAPIError(
        f"{pass_label} failed after {MAX_RETRIES} retries for posting {posting_id}",
        category=last_category,
        original=last_error,
    )
