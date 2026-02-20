"""Tests for Pass 2 enrichment pipeline (Sonnet entity extraction)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from helpers import make_mock_client as _make_mock_client
from helpers import make_mock_response as _make_mock_response

from compgraph.enrichment.pass2 import enrich_posting_pass2
from compgraph.enrichment.prompts import (
    PASS2_SYSTEM_PROMPT,
    build_pass2_messages,
    build_pass2_user_message,
)
from compgraph.enrichment.retry import (
    EnrichmentAPIError,
    ErrorCategory,
    LLMCallResult,
)
from compgraph.enrichment.schemas import EntityMention, Pass2Result

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES_RESPONSE = {
    "entities": [
        {
            "entity_name": "Samsung",
            "entity_type": "client_brand",
            "confidence": 0.95,
        },
        {
            "entity_name": "Best Buy",
            "entity_type": "retailer",
            "confidence": 0.95,
        },
        {
            "entity_name": "Walmart",
            "entity_type": "retailer",
            "confidence": 0.9,
        },
    ]
}

SAMPLE_EMPTY_ENTITIES = {"entities": []}

SAMPLE_AMBIGUOUS_ENTITY = {
    "entities": [
        {
            "entity_name": "Apple",
            "entity_type": "ambiguous",
            "confidence": 0.7,
        },
    ]
}


# ---------------------------------------------------------------------------
# Pass2Result schema validation
# ---------------------------------------------------------------------------


class TestPass2ResultSchema:
    def test_valid_entities(self):
        result = Pass2Result.model_validate(SAMPLE_ENTITIES_RESPONSE)
        assert len(result.entities) == 3
        assert result.entities[0].entity_name == "Samsung"
        assert result.entities[0].entity_type == "client_brand"
        assert result.entities[0].confidence == 0.95

    def test_empty_entities(self):
        result = Pass2Result.model_validate(SAMPLE_EMPTY_ENTITIES)
        assert len(result.entities) == 0

    def test_empty_object_defaults(self):
        result = Pass2Result.model_validate({})
        assert result.entities == []

    def test_ambiguous_entity(self):
        result = Pass2Result.model_validate(SAMPLE_AMBIGUOUS_ENTITY)
        assert len(result.entities) == 1
        assert result.entities[0].entity_type == "ambiguous"
        assert result.entities[0].confidence == 0.7


class TestEntityMention:
    def test_valid_brand(self):
        entity = EntityMention(
            entity_name="Samsung",
            entity_type="client_brand",
            confidence=0.95,
        )
        assert entity.entity_name == "Samsung"

    def test_confidence_bounds(self):
        """Confidence must be 0.0-1.0."""
        entity = EntityMention(entity_name="Test", entity_type="retailer", confidence=0.0)
        assert entity.confidence == 0.0

        entity = EntityMention(entity_name="Test", entity_type="retailer", confidence=1.0)
        assert entity.confidence == 1.0

    def test_confidence_negative_rejected(self):
        """Negative confidence should be rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EntityMention(entity_name="Test", entity_type="retailer", confidence=-0.1)

    def test_confidence_out_of_range(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EntityMention(entity_name="Test", entity_type="retailer", confidence=1.5)


# ---------------------------------------------------------------------------
# Pass 2 prompt construction
# ---------------------------------------------------------------------------


class TestPass2PromptConstruction:
    def test_system_prompt_not_empty(self):
        assert len(PASS2_SYSTEM_PROMPT) > 500

    def test_system_prompt_contains_classification_rules(self):
        assert "client_brand" in PASS2_SYSTEM_PROMPT
        assert "retailer" in PASS2_SYSTEM_PROMPT
        assert "ambiguous" in PASS2_SYSTEM_PROMPT

    def test_build_user_message_with_role_specific(self):
        msg = build_pass2_user_message(
            "Field Rep", "Chicago", "Samsung products at Best Buy", "Full text here"
        )
        assert "Samsung products at Best Buy" in msg
        assert "Full text here" not in msg  # uses role_specific, not full_text

    def test_build_user_message_fallback_to_full_text(self):
        msg = build_pass2_user_message("Field Rep", "Chicago", None, "Full text with entities")
        assert "Full text with entities" in msg

    def test_build_messages(self):
        messages = build_pass2_messages("Title", "Loc", "Role specific", "Full text")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"


# ---------------------------------------------------------------------------
# enrich_posting_pass2()
# ---------------------------------------------------------------------------


class TestEnrichPostingPass2:
    @pytest.mark.asyncio
    async def test_successful_entity_extraction(self):
        client = _make_mock_client(SAMPLE_ENTITIES_RESPONSE)
        posting_id = uuid.uuid4()

        llm_result = await enrich_posting_pass2(
            client,
            posting_id,
            "Samsung Brand Ambassador",
            "Chicago, IL",
            "Represent Samsung at Best Buy and Walmart",
            "Full text here",
        )

        assert isinstance(llm_result, LLMCallResult)
        assert len(llm_result.result.entities) == 3
        assert llm_result.result.entities[0].entity_name == "Samsung"
        assert llm_result.input_tokens == 100
        assert llm_result.output_tokens == 50
        client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_entity_extraction(self):
        client = _make_mock_client(SAMPLE_EMPTY_ENTITIES)

        llm_result = await enrich_posting_pass2(
            client,
            uuid.uuid4(),
            "Warehouse Coordinator",
            "Dallas, TX",
            None,
            "Process incoming shipments and manage inventory.",
        )

        assert len(llm_result.result.entities) == 0

    @pytest.mark.asyncio
    async def test_token_tracking(self):
        """Token counts from the API response should be propagated."""
        client = _make_mock_client(SAMPLE_ENTITIES_RESPONSE, input_tokens=300, output_tokens=150)

        llm_result = await enrich_posting_pass2(client, uuid.uuid4(), "Title", "Loc", None, "Body")

        assert llm_result.input_tokens == 300
        assert llm_result.output_tokens == 150

    @pytest.mark.asyncio
    async def test_parse_failure_raises_enrichment_api_error(self):
        """Invalid JSON should raise EnrichmentAPIError with PARSE_ERROR category."""
        client = AsyncMock()
        content_block = MagicMock()
        content_block.text = "Not JSON"
        response = MagicMock()
        response.content = [content_block]
        response.stop_reason = "end_turn"
        response.usage = MagicMock(input_tokens=100, output_tokens=50)
        client.messages.create = AsyncMock(return_value=response)

        with pytest.raises(EnrichmentAPIError) as exc_info:
            await enrich_posting_pass2(client, uuid.uuid4(), "Title", "Loc", None, "Body")

        assert exc_info.value.category == ErrorCategory.PARSE_ERROR

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        import anthropic

        client = AsyncMock()
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.messages.create = AsyncMock(
            side_effect=[
                rate_limit_error,
                _make_mock_response(SAMPLE_ENTITIES_RESPONSE),
            ]
        )

        with patch("compgraph.enrichment.retry._retry_sleep", new_callable=AsyncMock):
            llm_result = await enrich_posting_pass2(
                client, uuid.uuid4(), "Title", "Loc", None, "Body"
            )

        assert len(llm_result.result.entities) == 3
        assert client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self):
        """Should raise EnrichmentAPIError after exhausting retries."""
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
            await enrich_posting_pass2(client, uuid.uuid4(), "Title", "Loc", None, "Body")

        assert exc_info.value.category == ErrorCategory.RATE_LIMIT
        assert client.messages.create.await_count == 3

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
                await enrich_posting_pass2(client, uuid.uuid4(), "Title", "Loc", None, "Body")

            assert exc_info.value.category == ErrorCategory.PERMANENT
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
            await enrich_posting_pass2(client, uuid.uuid4(), "Title", "Loc", None, "Body")

        assert exc_info.value.category == ErrorCategory.TRANSIENT
        assert client.messages.create.await_count == 3


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestPass2APIRoutes:
    def test_trigger_pass2(self, client):
        with patch("compgraph.api.routes.enrich.EnrichmentOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            response = client.post("/api/enrich/pass2/trigger")
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "Pass 2" in data["message"]

    def test_trigger_full_pipeline(self, client):
        with patch("compgraph.api.routes.enrich.EnrichmentOrchestrator") as mock_orch_cls:
            mock_orch = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            response = client.post("/api/enrich/trigger")
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "Full" in data["message"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestPass2Config:
    def test_enrichment_model_pass2(self):
        from compgraph.config import settings

        assert settings.ENRICHMENT_MODEL_PASS2 == "claude-sonnet-4-5-20250929"
