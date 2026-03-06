"""Tests for the Instructor-based enrichment path."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from compgraph.enrichment.retry import (
    EnrichmentAPIError,
    ErrorCategory,
    LLMCallResult,
    call_llm,
    call_llm_with_instructor,
)
from compgraph.enrichment.schemas import Pass1Result, Pass2Result

# ---------------------------------------------------------------------------
# Sample data (reused from pass1/pass2 tests)
# ---------------------------------------------------------------------------

SAMPLE_PASS1 = {
    "role_archetype": "field_rep",
    "role_level": "entry",
    "employment_type": "full_time",
    "travel_required": True,
    "pay_type": "hourly",
    "pay_min": 20.0,
    "pay_max": 25.0,
    "pay_frequency": "hour",
    "has_commission": True,
    "has_benefits": True,
    "content_role_specific": "Visit Best Buy stores.",
    "content_boilerplate": "We are an equal opportunity employer.",
    "content_qualifications": "Must have transportation.",
    "content_responsibilities": "Travel to retail stores.",
    "tools_mentioned": ["Salesforce"],
    "kpis_mentioned": ["sales targets"],
    "store_count": 15,
}

SAMPLE_PASS2 = {
    "entities": [
        {"entity_name": "Samsung", "entity_type": "client_brand", "confidence": 0.95},
        {"entity_name": "Best Buy", "entity_type": "retailer", "confidence": 0.9},
    ]
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_raw_response(input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    raw = MagicMock()
    raw.usage = usage
    return raw


# ---------------------------------------------------------------------------
# get_instructor_client()
# ---------------------------------------------------------------------------


class TestGetInstructorClient:
    def test_returns_async_instructor(self):
        import instructor

        from compgraph.enrichment.client import get_instructor_client, reset_client

        reset_client()
        client = get_instructor_client()
        assert isinstance(client, instructor.AsyncInstructor)
        reset_client()

    def test_singleton_returns_same_instance(self):
        from compgraph.enrichment.client import get_instructor_client, reset_client

        reset_client()
        c1 = get_instructor_client()
        c2 = get_instructor_client()
        assert c1 is c2
        reset_client()

    def test_reset_clears_instructor_client(self):
        from compgraph.enrichment.client import get_instructor_client, reset_client

        reset_client()
        c1 = get_instructor_client()
        reset_client()
        c2 = get_instructor_client()
        assert c1 is not c2
        reset_client()


# ---------------------------------------------------------------------------
# call_llm_with_instructor() — Pass 1
# ---------------------------------------------------------------------------


class TestCallLLMWithInstructorPass1:
    @pytest.mark.asyncio
    async def test_returns_validated_pass1_result(self):
        parsed = Pass1Result.model_validate(SAMPLE_PASS1)
        raw = _mock_raw_response(input_tokens=200, output_tokens=80)

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(return_value=(parsed, raw))

        with patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client):
            result = await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert isinstance(result, LLMCallResult)
        assert result.result.role_archetype == "field_rep"
        assert result.result.pay_min == 20.0
        assert result.input_tokens == 200
        assert result.output_tokens == 80

    @pytest.mark.asyncio
    async def test_token_tracking(self):
        parsed = Pass1Result.model_validate(SAMPLE_PASS1)
        raw = _mock_raw_response(input_tokens=500, output_tokens=250)

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(return_value=(parsed, raw))

        with patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client):
            result = await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert result.input_tokens == 500
        assert result.output_tokens == 250


# ---------------------------------------------------------------------------
# call_llm_with_instructor() — Pass 2
# ---------------------------------------------------------------------------


class TestCallLLMWithInstructorPass2:
    @pytest.mark.asyncio
    async def test_returns_validated_pass2_result(self):
        parsed = Pass2Result.model_validate(SAMPLE_PASS2)
        raw = _mock_raw_response()

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(return_value=(parsed, raw))

        with patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client):
            result = await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass2Result,
                pass_label="Pass 2",
            )

        assert isinstance(result, LLMCallResult)
        assert len(result.result.entities) == 2
        assert result.result.entities[0].entity_name == "Samsung"


# ---------------------------------------------------------------------------
# Error handling in Instructor path
# ---------------------------------------------------------------------------


class TestInstructorErrorHandling:
    @pytest.mark.asyncio
    async def test_rate_limit_retries(self):
        parsed = Pass1Result.model_validate(SAMPLE_PASS1)
        raw = _mock_raw_response()

        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(
            side_effect=[rate_limit_error, (parsed, raw)]
        )

        with (
            patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client),
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
        ):
            result = await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert result.result.role_archetype == "field_rep"
        assert mock_client.create_with_completion.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self):
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(side_effect=rate_limit_error)

        with (
            patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client),
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
            pytest.raises(EnrichmentAPIError) as exc_info,
        ):
            await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert exc_info.value.category == ErrorCategory.RATE_LIMIT
        assert mock_client.create_with_completion.await_count == 3

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        for status_code in (400, 401, 403, 422):
            api_error = anthropic.APIStatusError(
                message=f"Error {status_code}",
                response=MagicMock(status_code=status_code, headers={}),
                body=None,
            )

            mock_client = AsyncMock()
            mock_client.create_with_completion = AsyncMock(side_effect=api_error)

            with (
                patch(
                    "compgraph.enrichment.retry.get_instructor_client",
                    return_value=mock_client,
                ),
                patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
                pytest.raises(EnrichmentAPIError) as exc_info,
            ):
                await call_llm_with_instructor(
                    posting_id=uuid.uuid4(),
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system_prompt="Test prompt",
                    messages=[{"role": "user", "content": "test"}],
                    result_type=Pass1Result,
                    pass_label="Pass 1",
                )

            assert exc_info.value.category == ErrorCategory.PERMANENT
            assert mock_client.create_with_completion.await_count == 1

    @pytest.mark.asyncio
    async def test_transient_500_retries(self):
        parsed = Pass1Result.model_validate(SAMPLE_PASS1)
        raw = _mock_raw_response()

        api_error = anthropic.APIStatusError(
            message="Internal Server Error",
            response=MagicMock(status_code=500, headers={}),
            body=None,
        )

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(side_effect=[api_error, (parsed, raw)])

        with (
            patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client),
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
        ):
            result = await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert result.result.role_archetype == "field_rep"
        assert mock_client.create_with_completion.await_count == 2

    @pytest.mark.asyncio
    async def test_quota_exhausted_detection(self):
        rate_limit_error = anthropic.RateLimitError(
            message="Your usage limit has been exceeded",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        mock_client = AsyncMock()
        mock_client.create_with_completion = AsyncMock(side_effect=rate_limit_error)

        with (
            patch("compgraph.enrichment.retry.get_instructor_client", return_value=mock_client),
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
            pytest.raises(EnrichmentAPIError) as exc_info,
        ):
            await call_llm_with_instructor(
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert exc_info.value.category == ErrorCategory.QUOTA_EXHAUSTED


# ---------------------------------------------------------------------------
# Feature flag routing — call_llm()
# ---------------------------------------------------------------------------


class TestCallLLMRouter:
    @pytest.mark.asyncio
    async def test_routes_to_old_path_when_flag_disabled(self):
        from helpers import make_mock_client

        from compgraph.config import settings as real_settings

        client = make_mock_client(SAMPLE_PASS1)

        with patch.object(real_settings, "USE_INSTRUCTOR", False):
            result = await call_llm(
                client,
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": json.dumps(SAMPLE_PASS1)}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert isinstance(result, LLMCallResult)
        assert result.result.role_archetype == "field_rep"
        client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_routes_to_instructor_path_when_flag_enabled(self):
        from compgraph.config import settings as real_settings

        parsed = Pass1Result.model_validate(SAMPLE_PASS1)
        raw = _mock_raw_response()

        mock_instructor_client = AsyncMock()
        mock_instructor_client.create_with_completion = AsyncMock(return_value=(parsed, raw))

        with (
            patch(
                "compgraph.enrichment.retry.get_instructor_client",
                return_value=mock_instructor_client,
            ),
            patch.object(real_settings, "USE_INSTRUCTOR", True),
        ):
            result = await call_llm(
                AsyncMock(),  # client unused in instructor path
                posting_id=uuid.uuid4(),
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system_prompt="Test prompt",
                messages=[{"role": "user", "content": "test"}],
                result_type=Pass1Result,
                pass_label="Pass 1",
            )

        assert isinstance(result, LLMCallResult)
        assert result.result.role_archetype == "field_rep"
        mock_instructor_client.create_with_completion.assert_awaited_once()


# ---------------------------------------------------------------------------
# USE_INSTRUCTOR config flag
# ---------------------------------------------------------------------------


class TestUseInstructorConfig:
    def test_default_is_false(self):
        from compgraph.config import settings

        assert settings.USE_INSTRUCTOR is False
