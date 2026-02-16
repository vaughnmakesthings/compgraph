"""Tests for Pass 1 enrichment pipeline (Haiku classification)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.enrichment.pass1 import enrich_posting_pass1
from compgraph.enrichment.prompts import (
    PASS1_SYSTEM_PROMPT,
    build_pass1_messages,
    build_pass1_user_message,
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


def _make_mock_response(data: dict, stop_reason: str = "end_turn") -> MagicMock:
    """Create a mock Anthropic API response."""
    content_block = MagicMock()
    content_block.text = json.dumps(data)
    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = stop_reason
    return response


def _make_mock_client(response_data: dict, stop_reason: str = "end_turn") -> AsyncMock:
    """Create a mock AsyncAnthropic client."""
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=_make_mock_response(response_data, stop_reason))
    return client


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

        result = await enrich_posting_pass1(
            client, posting_id, "Field Sales Rep - Samsung", "Chicago, IL", "Visit Best Buy stores."
        )

        assert result.role_archetype == "field_rep"
        assert result.pay_type == "hourly"
        assert result.pay_min == 20.0
        assert result.has_commission is True
        client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_successful_merchandiser_classification(self):
        client = _make_mock_client(SAMPLE_MERCHANDISER_RESPONSE)
        posting_id = uuid.uuid4()

        result = await enrich_posting_pass1(
            client, posting_id, "Retail Merchandiser", "Dallas, TX", "Stock shelves."
        )

        assert result.role_archetype == "merchandiser"
        assert result.employment_type == "part_time"
        assert result.pay_type is None

    @pytest.mark.asyncio
    async def test_successful_manager_classification(self):
        client = _make_mock_client(SAMPLE_MANAGER_RESPONSE)
        posting_id = uuid.uuid4()

        result = await enrich_posting_pass1(
            client, posting_id, "Territory Manager", "Atlanta, GA", "Manage team of 20."
        )

        assert result.role_archetype == "manager"
        assert result.pay_type == "salary"
        assert result.pay_min == 55000.0

    @pytest.mark.asyncio
    async def test_max_tokens_truncation_warns(self, caplog):
        """When response is truncated, should log warning but still return partial result."""
        client = _make_mock_client(SAMPLE_FIELD_REP_RESPONSE, stop_reason="max_tokens")
        posting_id = uuid.uuid4()

        import logging

        with caplog.at_level(logging.WARNING):
            result = await enrich_posting_pass1(client, posting_id, "Title", "Loc", "Body")

        assert result.role_archetype == "field_rep"
        assert "truncated" in caplog.text.lower() or "max_tokens" in caplog.text

    @pytest.mark.asyncio
    async def test_parse_failure_raises_value_error(self):
        """Invalid JSON response should raise ValueError."""
        client = AsyncMock()
        content_block = MagicMock()
        content_block.text = "This is not JSON"
        response = MagicMock()
        response.content = [content_block]
        response.stop_reason = "end_turn"
        client.messages.create = AsyncMock(return_value=response)

        with pytest.raises(ValueError, match="Failed to parse"):
            await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

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

        with patch("compgraph.enrichment.pass1._retry_sleep", new_callable=AsyncMock):
            result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert result.role_archetype == "field_rep"
        assert client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self):
        """Should raise after exhausting retries on RateLimitError."""
        import anthropic

        client = AsyncMock()
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(side_effect=rate_limit_error)

        with (
            patch("compgraph.enrichment.pass1._retry_sleep", new_callable=AsyncMock),
            pytest.raises(anthropic.RateLimitError),
        ):
            await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert client.messages.create.await_count == 3

    @pytest.mark.asyncio
    async def test_api_status_error_retry(self):
        """Should retry on APIStatusError."""
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

        with patch("compgraph.enrichment.pass1._retry_sleep", new_callable=AsyncMock):
            result = await enrich_posting_pass1(client, uuid.uuid4(), "Title", "Loc", "Body")

        assert result.role_archetype == "field_rep"
        assert client.messages.create.await_count == 2


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
