"""Tests for Pass 1 enrichment pipeline (Haiku classification)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from helpers import make_mock_client as _make_mock_client
from helpers import make_mock_response as _make_mock_response

from compgraph.enrichment.pass1 import enrich_posting_pass1
from compgraph.enrichment.prompts import (
    PASS1_SYSTEM_PROMPT,
    build_pass1_messages,
    build_pass1_user_message,
)
from compgraph.enrichment.retry import (
    EnrichmentAPIError,
    ErrorCategory,
    LLMCallResult,
    _classify_rate_limit,
)
from compgraph.enrichment.schemas import Pass1Result

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_FIELD_REP_RESPONSE = {
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
    "content_role_specific": "Visit 10-15 Best Buy stores weekly to demonstrate Samsung products.",
    "content_boilerplate": "We are an equal opportunity employer.",
    "content_qualifications": "Must have reliable transportation and smartphone.",
    "content_responsibilities": "Travel to retail stores, set up displays, engage customers.",
    "tools_mentioned": ["Salesforce", "Repsly"],
    "kpis_mentioned": ["sales targets", "store visits per day"],
    "store_count": 15,
}

SAMPLE_MERCHANDISER_RESPONSE = {
    "role_archetype": "merchandiser",
    "role_level": "entry",
    "employment_type": "part_time",
    "travel_required": True,
    "pay_type": None,
    "pay_min": None,
    "pay_max": None,
    "pay_frequency": None,
    "has_commission": None,
    "has_benefits": None,
    "content_role_specific": "Reset displays and stock shelves at Target and Walmart.",
    "content_boilerplate": "Equal opportunity employer.",
    "content_qualifications": "No experience needed.",
    "content_responsibilities": "Stock shelves, set up displays, ensure planogram compliance.",
    "tools_mentioned": [],
    "kpis_mentioned": [],
    "store_count": None,
}

SAMPLE_MANAGER_RESPONSE = {
    "role_archetype": "manager",
    "role_level": "manager",
    "employment_type": "full_time",
    "travel_required": True,
    "pay_type": "salary",
    "pay_min": 55000.0,
    "pay_max": 65000.0,
    "pay_frequency": "year",
    "has_commission": True,
    "has_benefits": True,
    "content_role_specific": "Manage team of 20+ field reps across the Southeast region.",
    "content_boilerplate": "About Us: We are a leading field marketing agency.",
    "content_qualifications": "3+ years management experience in retail or field marketing.",
    "content_responsibilities": "Hire, train, and manage field reps. Report on KPIs.",
    "tools_mentioned": ["Excel", "Tableau"],
    "kpis_mentioned": ["team retention", "territory coverage"],
    "store_count": None,
}


# ---------------------------------------------------------------------------
# Pass1Result schema validation
# ---------------------------------------------------------------------------


class TestPass1ResultSchema:
    def test_valid_full_response(self):
        result = Pass1Result.model_validate(SAMPLE_FIELD_REP_RESPONSE)
        assert result.role_archetype == "field_rep"
        assert result.pay_min == 20.0
        assert result.pay_max == 25.0
        assert result.tools_mentioned == ["Salesforce", "Repsly"]
        assert result.store_count == 15

    def test_all_null_fields(self):
        data = {
            "role_archetype": None,
            "role_level": None,
            "employment_type": None,
            "travel_required": None,
            "pay_type": None,
            "pay_min": None,
            "pay_max": None,
            "pay_frequency": None,
            "has_commission": None,
            "has_benefits": None,
            "content_role_specific": None,
            "content_boilerplate": None,
            "content_qualifications": None,
            "content_responsibilities": None,
            "tools_mentioned": [],
            "kpis_mentioned": [],
            "store_count": None,
        }
        result = Pass1Result.model_validate(data)
        assert result.role_archetype is None
        assert result.tools_mentioned == []

    def test_minimal_response(self):
        """Only role_archetype provided, everything else defaults."""
        result = Pass1Result.model_validate({"role_archetype": "merchandiser"})
        assert result.role_archetype == "merchandiser"
        assert result.pay_min is None
        assert result.tools_mentioned == []
        assert result.kpis_mentioned == []

    def test_empty_object(self):
        result = Pass1Result.model_validate({})
        assert result.role_archetype is None
        assert result.tools_mentioned == []

    def test_extra_fields_ignored(self):
        data = {**SAMPLE_FIELD_REP_RESPONSE, "unexpected_field": "value"}
        result = Pass1Result.model_validate(data)
        assert result.role_archetype == "field_rep"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


class TestPromptConstruction:
    def test_system_prompt_not_empty(self):
        assert len(PASS1_SYSTEM_PROMPT) > 500

    def test_system_prompt_contains_taxonomy(self):
        assert "field_rep" in PASS1_SYSTEM_PROMPT
        assert "merchandiser" in PASS1_SYSTEM_PROMPT
        assert "brand_ambassador" in PASS1_SYSTEM_PROMPT

    def test_build_user_message(self):
        msg = build_pass1_user_message("Field Rep", "Chicago, IL", "Job description here")
        assert "<title>Field Rep</title>" in msg
        assert "<location>Chicago, IL</location>" in msg
        assert "Job description here" in msg

    def test_build_messages_returns_user_message(self):
        messages = build_pass1_messages("Title", "Location", "Body text")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Title" in messages[0]["content"]


# ---------------------------------------------------------------------------
# enrich_posting_pass1()
# ---------------------------------------------------------------------------


class TestEnrichPostingPass1:
    @pytest.mark.asyncio
    async def test_successful_field_rep_classification(self):
        client = _make_mock_client(SAMPLE_FIELD_REP_RESPONSE)
        posting_id = uuid.uuid4()

        llm_result = await enrich_posting_pass1(
            client, posting_id, "Field Sales Rep - Samsung", "Chicago, IL", "Visit Best Buy stores."
        )

        assert isinstance(llm_result, LLMCallResult)
        assert llm_result.result.role_archetype == "field_rep"
        assert llm_result.result.pay_type == "hourly"
        assert llm_result.result.pay_min == 20.0
        assert llm_result.result.has_commission is True
        assert llm_result.input_tokens == 100
        assert llm_result.output_tokens == 50
        client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_successful_merchandiser_classification(self):
        client = _make_mock_client(SAMPLE_MERCHANDISER_RESPONSE)
        posting_id = uuid.uuid4()

        llm_result = await enrich_posting_pass1(
            client, posting_id, "Retail Merchandiser", "Dallas, TX", "Stock shelves."
        )

        assert llm_result.result.role_archetype == "merchandiser"
        assert llm_result.result.employment_type == "part_time"
        assert llm_result.result.pay_type is None

    @pytest.mark.asyncio
    async def test_successful_manager_classification(self):
        client = _make_mock_client(SAMPLE_MANAGER_RESPONSE)
        posting_id = uuid.uuid4()

        llm_result = await enrich_posting_pass1(
            client, posting_id, "Territory Manager", "Atlanta, GA", "Manage team of 20."
        )

        assert llm_result.result.role_archetype == "manager"
        assert llm_result.result.pay_type == "salary"
        assert llm_result.result.pay_min == 55000.0

    @pytest.mark.asyncio
    async def test_token_tracking(self):
        """Token counts from the API response should be propagated."""
        client = _make_mock_client(SAMPLE_FIELD_REP_RESPONSE, input_tokens=250, output_tokens=120)

        llm_result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert llm_result.input_tokens == 250
        assert llm_result.output_tokens == 120

    @pytest.mark.asyncio
    async def test_max_tokens_truncation_warns(self, caplog):
        """When response is truncated, should log warning but still return partial result."""
        client = _make_mock_client(SAMPLE_FIELD_REP_RESPONSE, stop_reason="max_tokens")
        posting_id = uuid.uuid4()

        import logging

        with caplog.at_level(logging.WARNING):
            llm_result = await enrich_posting_pass1(client, posting_id, "Title", "Loc", "Body")

        assert llm_result.result.role_archetype == "field_rep"
        assert "truncated" in caplog.text.lower() or "max_tokens" in caplog.text

    @pytest.mark.asyncio
    async def test_parse_failure_raises_enrichment_api_error(self):
        """Invalid JSON response should raise EnrichmentAPIError with PARSE_ERROR category."""
        client = AsyncMock()
        content_block = MagicMock()
        content_block.text = "This is not JSON"
        response = MagicMock()
        response.content = [content_block]
        response.stop_reason = "end_turn"
        response.usage = MagicMock(input_tokens=100, output_tokens=50)
        client.messages.create = AsyncMock(return_value=response)

        with pytest.raises(EnrichmentAPIError) as exc_info:
            await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert exc_info.value.category == ErrorCategory.PARSE_ERROR

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """Should retry on RateLimitError with exponential backoff."""
        import anthropic

        client = AsyncMock()
        # First call: rate limit, second call: success
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(
            side_effect=[
                rate_limit_error,
                _make_mock_response(SAMPLE_FIELD_REP_RESPONSE),
            ]
        )

        with patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock):
            llm_result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert llm_result.result.role_archetype == "field_rep"
        assert client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self):
        """Should raise EnrichmentAPIError after exhausting retries on RateLimitError."""
        import anthropic

        client = AsyncMock()
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(side_effect=rate_limit_error)

        with (
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
            pytest.raises(EnrichmentAPIError) as exc_info,
        ):
            await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert exc_info.value.category == ErrorCategory.RATE_LIMIT
        assert client.messages.create.await_count == 3

    @pytest.mark.asyncio
    async def test_api_status_error_retry(self):
        """Should retry on APIStatusError (5xx)."""
        import anthropic

        client = AsyncMock()
        api_error = anthropic.APIStatusError(
            message="Server error",
            response=MagicMock(status_code=500, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(
            side_effect=[
                api_error,
                _make_mock_response(SAMPLE_FIELD_REP_RESPONSE),
            ]
        )

        with patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock):
            llm_result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert llm_result.result.role_archetype == "field_rep"
        assert client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        """Should NOT retry on permanent errors (400, 401, 403, 422)."""
        import anthropic

        for status_code in (400, 401, 403, 422):
            client = AsyncMock()
            api_error = anthropic.APIStatusError(
                message=f"Error {status_code}",
                response=MagicMock(status_code=status_code, headers={}),
                body=None,
            )
            client.messages.create = AsyncMock(side_effect=api_error)

            with (
                patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
                pytest.raises(EnrichmentAPIError) as exc_info,
            ):
                await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

            assert exc_info.value.category == ErrorCategory.PERMANENT
            # Only 1 attempt — no retries for permanent errors
            assert client.messages.create.await_count == 1, f"Status {status_code} should not retry"

    @pytest.mark.asyncio
    async def test_transient_500_still_retries(self):
        """500 errors should still retry (not permanent)."""
        import anthropic

        client = AsyncMock()
        api_error = anthropic.APIStatusError(
            message="Internal Server Error",
            response=MagicMock(status_code=500, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(side_effect=api_error)

        with (
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
            pytest.raises(EnrichmentAPIError) as exc_info,
        ):
            await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert exc_info.value.category == ErrorCategory.TRANSIENT
        # All 3 retry attempts for transient 500
        assert client.messages.create.await_count == 3


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


class TestErrorClassification:
    def test_standard_rate_limit(self):
        """Standard 429 without quota indicators → RATE_LIMIT."""
        import anthropic

        error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.RATE_LIMIT

    def test_quota_from_retry_after_header(self):
        """retry-after > 300s suggests quota exhaustion."""
        import anthropic

        error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={"retry-after": "600"}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.QUOTA_EXHAUSTED

    def test_short_retry_after_is_rate_limit(self):
        """retry-after <= 300s is normal rate limiting."""
        import anthropic

        error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={"retry-after": "60"}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.RATE_LIMIT

    def test_quota_from_usage_limit_message(self):
        """Error message containing 'usage limit' → QUOTA_EXHAUSTED."""
        import anthropic

        error = anthropic.RateLimitError(
            message="Your usage limit has been exceeded",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.QUOTA_EXHAUSTED

    def test_quota_from_spending_limit_message(self):
        """Error message containing 'spending limit' → QUOTA_EXHAUSTED."""
        import anthropic

        error = anthropic.RateLimitError(
            message="Your spending limit has been reached",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.QUOTA_EXHAUSTED

    def test_quota_from_billing_message(self):
        """Error message containing 'billing' → QUOTA_EXHAUSTED."""
        import anthropic

        error = anthropic.RateLimitError(
            message="Billing issue: please check your account",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.QUOTA_EXHAUSTED


# ---------------------------------------------------------------------------
# 429-as-APIStatusError (#107)
# ---------------------------------------------------------------------------


class TestAPIStatusError429:
    def test_classify_429_api_status_error(self):
        import anthropic

        from compgraph.enrichment.retry import _classify_rate_limit

        error = anthropic.APIStatusError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.RATE_LIMIT

    def test_classify_429_api_status_error_quota(self):
        import anthropic

        from compgraph.enrichment.retry import _classify_rate_limit

        error = anthropic.APIStatusError(
            message="Your usage limit has been exceeded",
            response=MagicMock(status_code=429, headers={"retry-after": "600"}),
            body=None,
        )
        assert _classify_rate_limit(error) == ErrorCategory.QUOTA_EXHAUSTED

    @pytest.mark.asyncio
    async def test_429_api_status_error_uses_rate_limit_delay(self):
        import anthropic

        from compgraph.enrichment.retry import RATE_LIMIT_BASE_DELAY

        client = AsyncMock()
        api_error = anthropic.APIStatusError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(
            side_effect=[
                api_error,
                _make_mock_response(SAMPLE_FIELD_REP_RESPONSE),
            ]
        )

        sleep_mock = AsyncMock()
        with patch("compgraph.enrichment.retry._retry_sleep", sleep_mock):
            llm_result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert llm_result.result.role_archetype == "field_rep"
        assert client.messages.create.await_count == 2
        sleep_mock.assert_awaited_once()
        actual_delay = sleep_mock.call_args[0][0]
        assert actual_delay == RATE_LIMIT_BASE_DELAY * (2**0)  # 60s on first retry

    @pytest.mark.asyncio
    async def test_429_api_status_error_exhausted(self):
        import anthropic

        client = AsyncMock()
        api_error = anthropic.APIStatusError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(side_effect=api_error)

        with (
            patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock),
            pytest.raises(EnrichmentAPIError) as exc_info,
        ):
            await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert exc_info.value.category == ErrorCategory.RATE_LIMIT
        assert client.messages.create.await_count == 3

    @pytest.mark.asyncio
    async def test_500_still_uses_transient_delay(self):
        import anthropic

        client = AsyncMock()
        api_error = anthropic.APIStatusError(
            message="Internal Server Error",
            response=MagicMock(status_code=500, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(
            side_effect=[
                api_error,
                _make_mock_response(SAMPLE_FIELD_REP_RESPONSE),
            ]
        )

        sleep_mock = AsyncMock()
        with patch("compgraph.enrichment.retry._retry_sleep", sleep_mock):
            llm_result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert llm_result.result.role_archetype == "field_rep"
        sleep_mock.assert_awaited_once()
        actual_delay = sleep_mock.call_args[0][0]
        assert actual_delay == 2.0 * (2**0)  # 2s transient delay, not 60s


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_trips_after_threshold(self):
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=3)
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        assert not breaker.tripped
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        assert not breaker.tripped
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        assert breaker.tripped
        assert breaker.trip_reason is not None
        assert "3 consecutive" in breaker.trip_reason

    def test_resets_on_success(self):
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=3)
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        breaker.record_success()
        assert breaker.consecutive_failures == 0
        # Need 3 more failures now, not just 1
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        assert not breaker.tripped

    def test_ignores_parse_errors(self):
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=3)
        for _ in range(5):
            breaker.record_api_failure(ErrorCategory.PARSE_ERROR)
        assert not breaker.tripped

    def test_ignores_permanent_errors(self):
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=3)
        for _ in range(5):
            breaker.record_api_failure(ErrorCategory.PERMANENT)
        assert not breaker.tripped

    def test_trips_on_quota_exhausted(self):
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=2)
        breaker.record_api_failure(ErrorCategory.QUOTA_EXHAUSTED)
        breaker.record_api_failure(ErrorCategory.QUOTA_EXHAUSTED)
        assert breaker.tripped
        assert "quota_exhausted" in breaker.trip_reason

    def test_trips_on_transient_errors(self):
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=2)
        breaker.record_api_failure(ErrorCategory.TRANSIENT)
        breaker.record_api_failure(ErrorCategory.TRANSIENT)
        assert breaker.tripped

    def test_mixed_api_errors_accumulate(self):
        """Different API error categories still count toward the threshold."""
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=3)
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        breaker.record_api_failure(ErrorCategory.QUOTA_EXHAUSTED)
        breaker.record_api_failure(ErrorCategory.TRANSIENT)
        assert breaker.tripped

    def test_tripped_stays_tripped_after_success(self):
        """Once tripped, the breaker stays tripped even if API recovers."""
        from compgraph.enrichment.orchestrator import CircuitBreaker

        breaker = CircuitBreaker(threshold=2)
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        breaker.record_api_failure(ErrorCategory.RATE_LIMIT)
        assert breaker.tripped
        breaker.record_success()
        assert breaker.tripped  # Conservative: stays tripped for rest of run


# ---------------------------------------------------------------------------
# LLMCallResult
# ---------------------------------------------------------------------------


class TestLLMCallResult:
    def test_wraps_result_with_tokens(self):
        result = Pass1Result.model_validate(SAMPLE_FIELD_REP_RESPONSE)
        llm_result = LLMCallResult(result=result, input_tokens=200, output_tokens=80)
        assert llm_result.result.role_archetype == "field_rep"
        assert llm_result.input_tokens == 200
        assert llm_result.output_tokens == 80


# ---------------------------------------------------------------------------
# Pay extraction edge cases (schema-level)
# ---------------------------------------------------------------------------


class TestPayExtraction:
    def test_up_to_pay(self):
        """'Up to $25/hr' → pay_min=None, pay_max=25."""
        data = {**SAMPLE_FIELD_REP_RESPONSE, "pay_min": None, "pay_max": 25.0}
        result = Pass1Result.model_validate(data)
        assert result.pay_min is None
        assert result.pay_max == 25.0

    def test_single_pay_value(self):
        """'$20/hr' → both min and max are 20."""
        data = {**SAMPLE_FIELD_REP_RESPONSE, "pay_min": 20.0, "pay_max": 20.0}
        result = Pass1Result.model_validate(data)
        assert result.pay_min == 20.0
        assert result.pay_max == 20.0

    def test_salary_range(self):
        """'$55,000-65,000/year'."""
        data = {
            **SAMPLE_FIELD_REP_RESPONSE,
            "pay_type": "salary",
            "pay_min": 55000.0,
            "pay_max": 65000.0,
            "pay_frequency": "year",
        }
        result = Pass1Result.model_validate(data)
        assert result.pay_type == "salary"
        assert result.pay_frequency == "year"

    def test_no_pay_mentioned(self):
        result = Pass1Result.model_validate(SAMPLE_MERCHANDISER_RESPONSE)
        assert result.pay_type is None
        assert result.pay_min is None
        assert result.pay_max is None


# ---------------------------------------------------------------------------
# Content section tagging
# ---------------------------------------------------------------------------


class TestContentSections:
    def test_role_specific_extracted(self):
        result = Pass1Result.model_validate(SAMPLE_FIELD_REP_RESPONSE)
        assert "Best Buy" in result.content_role_specific

    def test_boilerplate_extracted(self):
        result = Pass1Result.model_validate(SAMPLE_FIELD_REP_RESPONSE)
        assert "equal opportunity" in result.content_boilerplate.lower()

    def test_qualifications_extracted(self):
        result = Pass1Result.model_validate(SAMPLE_FIELD_REP_RESPONSE)
        assert "transportation" in result.content_qualifications


# ---------------------------------------------------------------------------
# Enrich API routes
# ---------------------------------------------------------------------------


class TestEnrichAPIRoutes:
    def test_trigger_pass1(self, client):
        with patch("compgraph.api.routes.enrich.EnrichmentOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            response = client.post("/api/enrich/pass1/trigger")
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "message" in data

    def test_status_no_runs(self, client):
        """Status endpoint should 404 when no runs exist."""
        from compgraph.enrichment.orchestrator import _runs

        _runs.clear()
        response = client.get("/api/enrich/status")
        assert response.status_code == 404

    def test_status_with_run(self, client):
        """After triggering, status should return the run."""
        with patch("compgraph.api.routes.enrich.EnrichmentOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            response = client.post("/api/enrich/pass1/trigger")
        run_id = response.json()["run_id"]
        status_response = client.get("/api/enrich/status")
        assert status_response.status_code == 200
        assert status_response.json()["run_id"] == run_id

    def test_status_by_id(self, client):
        with patch("compgraph.api.routes.enrich.EnrichmentOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            response = client.post("/api/enrich/pass1/trigger")
        run_id = response.json()["run_id"]
        status_response = client.get(f"/api/enrich/status/{run_id}")
        assert status_response.status_code == 200
        assert status_response.json()["run_id"] == run_id

    def test_status_by_id_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/enrich/status/{fake_id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Orchestrator unit tests
# ---------------------------------------------------------------------------


class TestEnrichmentOrchestrator:
    def test_enrich_result_defaults(self):
        from compgraph.enrichment.orchestrator import EnrichResult

        result = EnrichResult()
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0

    def test_enrichment_run_finish_success(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=10, failed=0)
        run.finish(result)
        assert run.status == EnrichmentStatus.SUCCESS
        assert run.finished_at is not None

    def test_enrichment_run_finish_partial(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=8, failed=2)
        run.finish(result)
        assert run.status == EnrichmentStatus.PARTIAL

    def test_enrichment_run_finish_failed(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=0, failed=5)
        run.finish(result)
        assert run.status == EnrichmentStatus.FAILED

    def test_enrichment_run_finish_nothing_to_process(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=0, failed=0)
        run.finish(result)
        assert run.status == EnrichmentStatus.SUCCESS

    def test_run_storage(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            _runs,
            _store_run,
            get_enrichment_run,
            get_latest_enrichment_run,
        )

        _runs.clear()
        run1 = EnrichmentRun()
        run2 = EnrichmentRun()
        _store_run(run1)
        _store_run(run2)

        assert get_enrichment_run(run1.run_id) is run1
        assert get_enrichment_run(run2.run_id) is run2
        assert get_latest_enrichment_run() is run2
        assert get_enrichment_run(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


class TestStripMarkdownFences:
    def test_strips_json_fence(self):
        from compgraph.enrichment.client import strip_markdown_fences

        text = '```json\n{"key": "value"}\n```'
        assert strip_markdown_fences(text) == '{"key": "value"}'

    def test_strips_plain_fence(self):
        from compgraph.enrichment.client import strip_markdown_fences

        text = '```\n{"key": "value"}\n```'
        assert strip_markdown_fences(text) == '{"key": "value"}'

    def test_passes_through_raw_json(self):
        from compgraph.enrichment.client import strip_markdown_fences

        text = '{"key": "value"}'
        assert strip_markdown_fences(text) == '{"key": "value"}'

    def test_strips_with_surrounding_whitespace(self):
        from compgraph.enrichment.client import strip_markdown_fences

        text = '  \n```json\n{"key": "value"}\n```\n  '
        assert strip_markdown_fences(text) == '{"key": "value"}'

    def test_preserves_multiline_json(self):
        from compgraph.enrichment.client import strip_markdown_fences

        text = '```json\n{\n  "role": "merchandiser",\n  "pay": 19.0\n}\n```'
        result = strip_markdown_fences(text)
        assert '"role": "merchandiser"' in result
        assert '"pay": 19.0' in result


class TestClientFactory:
    def test_singleton_returns_same_client(self):
        from compgraph.enrichment.client import get_anthropic_client, reset_client

        reset_client()
        client1 = get_anthropic_client()
        client2 = get_anthropic_client()
        assert client1 is client2
        reset_client()

    def test_reset_creates_new_client(self):
        from compgraph.enrichment.client import get_anthropic_client, reset_client

        reset_client()
        client1 = get_anthropic_client()
        reset_client()
        client2 = get_anthropic_client()
        assert client1 is not client2
        reset_client()


# ---------------------------------------------------------------------------
# Config enrichment settings
# ---------------------------------------------------------------------------


class TestEnrichmentConfig:
    def test_enrichment_defaults(self):
        from compgraph.config import settings

        assert settings.ENRICHMENT_BATCH_SIZE == 50
        assert settings.ENRICHMENT_CONCURRENCY == 5
        assert settings.ENRICHMENT_MODEL_PASS1 == "claude-haiku-4-5-20251001"

    def test_circuit_breaker_threshold_default(self):
        from compgraph.config import settings

        assert settings.ENRICHMENT_CIRCUIT_BREAKER_THRESHOLD == 3


# ---------------------------------------------------------------------------
# Observability fields
# ---------------------------------------------------------------------------


class TestObservabilityFields:
    def test_enrichment_run_defaults(self):
        from compgraph.enrichment.orchestrator import EnrichmentRun

        run = EnrichmentRun()
        assert run.circuit_breaker_tripped is False
        assert run.error_summary is None

    def test_enrich_result_includes_api_and_dedup(self):
        from compgraph.enrichment.orchestrator import EnrichResult

        result = EnrichResult()
        assert result.total_api_calls == 0
        assert result.total_dedup_saved == 0

    def test_status_includes_token_fields(self, client):
        from unittest.mock import AsyncMock, patch

        with patch("compgraph.api.routes.enrich.EnrichmentOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            client.post("/api/enrich/pass1/trigger")

        response = client.get("/api/enrich/status")
        assert response.status_code == 200
        data = response.json()
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "total_api_calls" in data
        assert "total_dedup_saved" in data
        assert "circuit_breaker_tripped" in data
        assert "error_summary" in data

    def test_status_with_token_data(self, client):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichResult,
            _store_run,
        )

        run = EnrichmentRun()
        result = EnrichResult(
            succeeded=5,
            total_input_tokens=1000,
            total_output_tokens=500,
            total_api_calls=5,
            total_dedup_saved=3,
        )
        run.finish(result)
        _store_run(run)

        response = client.get(f"/api/enrich/status/{run.run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_input_tokens"] == 1000
        assert data["total_output_tokens"] == 500
        assert data["total_api_calls"] == 5
        assert data["total_dedup_saved"] == 3

    def test_status_circuit_breaker_flag(self, client):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichResult,
            _store_run,
        )

        run = EnrichmentRun()
        run.circuit_breaker_tripped = True
        run.error_summary = "circuit breaker triggered: 3 consecutive API failures"
        result = EnrichResult(succeeded=2, failed=3)
        run.finish(result)
        _store_run(run)

        response = client.get(f"/api/enrich/status/{run.run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["circuit_breaker_tripped"] is True
        assert "circuit breaker" in data["error_summary"]
