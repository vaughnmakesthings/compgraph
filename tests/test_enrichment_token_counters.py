"""Tests for enrichment run token/API call counter wiring (Issue #447)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.enrichment.retry import LLMCallResult
from compgraph.enrichment.schemas import Pass1Result, Pass2Result

SAMPLE_PASS1 = Pass1Result.model_validate(
    {
        "role_archetype": "field_rep",
        "role_level": "entry",
        "employment_type": "full_time",
        "travel_required": True,
        "pay_type": "hourly",
        "pay_min": 20.0,
        "pay_max": 25.0,
        "pay_frequency": "hour",
        "has_commission": False,
        "has_benefits": True,
        "content_role_specific": "Demo Samsung products at Best Buy.",
        "content_boilerplate": "EOE.",
        "content_qualifications": "Reliable transportation.",
        "content_responsibilities": "Travel to stores.",
        "tools_mentioned": [],
        "kpis_mentioned": [],
        "store_count": None,
    }
)

SAMPLE_PASS2 = Pass2Result.model_validate(
    {
        "entities": [
            {"entity_name": "Samsung", "entity_type": "brand", "confidence": 0.95},
        ],
    }
)


def _make_posting_snapshot_pair(
    posting_id: uuid.UUID | None = None,
    snapshot_id: uuid.UUID | None = None,
    title: str = "Field Rep",
    location: str = "Dallas, TX",
    full_text: str = "Demo Samsung products at Best Buy.",
) -> tuple[MagicMock, MagicMock]:
    posting = MagicMock()
    posting.id = posting_id or uuid.uuid4()
    snapshot = MagicMock()
    snapshot.id = snapshot_id or uuid.uuid4()
    snapshot.title_raw = title
    snapshot.location_raw = location
    snapshot.full_text_raw = full_text
    return posting, snapshot


def _make_pass2_triple(
    posting_id: uuid.UUID | None = None,
    enrichment_id: uuid.UUID | None = None,
    title: str = "Field Rep",
    location: str = "Dallas, TX",
    full_text: str = "Demo Samsung products at Best Buy.",
    content_role_specific: str | None = "Demo Samsung products at Best Buy.",
) -> tuple[MagicMock, MagicMock, MagicMock]:
    posting = MagicMock()
    posting.id = posting_id or uuid.uuid4()
    snapshot = MagicMock()
    snapshot.id = uuid.uuid4()
    snapshot.title_raw = title
    snapshot.location_raw = location
    snapshot.full_text_raw = full_text
    enrichment = MagicMock()
    enrichment.id = enrichment_id or uuid.uuid4()
    enrichment.content_role_specific = content_role_specific
    enrichment.enrichment_version = "pass1-v1"
    enrichment.title_normalized = title
    enrichment.entity_count = None
    return posting, snapshot, enrichment


class TestPass1TokenCounterWiring:
    @pytest.mark.asyncio
    async def test_pass1_increments_token_counters_on_success(self):
        mock_increment = AsyncMock()
        mock_pass1 = AsyncMock(
            return_value=LLMCallResult(result=SAMPLE_PASS1, input_tokens=150, output_tokens=75)
        )

        batch = [_make_posting_snapshot_pair()]
        mock_fetch = AsyncMock(side_effect=[batch, []])
        mock_save = AsyncMock()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_pass1),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.enrichment.orchestrator.update_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.create_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.increment_enrichment_counter", mock_increment),
            patch("compgraph.enrichment.orchestrator.compute_content_hash", return_value="abc123"),
            patch("compgraph.main.shutdown_event") as mock_shutdown,
        ):
            mock_shutdown.is_set.return_value = False

            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=1)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        assert result.total_input_tokens == 150
        assert result.total_output_tokens == 75
        assert result.total_api_calls == 1

        token_calls = [
            c
            for c in mock_increment.call_args_list
            if "total_input_tokens" in c.kwargs
            or (len(c.args) > 1 and "total_input_tokens" in str(c))
        ]
        assert len(token_calls) >= 1
        tc = token_calls[0]
        assert tc.kwargs["total_input_tokens"] == 150
        assert tc.kwargs["total_output_tokens"] == 75
        assert tc.kwargs["total_api_calls"] == 1

    @pytest.mark.asyncio
    async def test_pass1_no_token_increment_on_failure(self):
        mock_increment = AsyncMock()

        from compgraph.enrichment.retry import EnrichmentAPIError, ErrorCategory

        mock_pass1 = AsyncMock(
            side_effect=EnrichmentAPIError("test error", ErrorCategory.PARSE_ERROR)
        )

        batch = [_make_posting_snapshot_pair()]
        mock_fetch = AsyncMock(side_effect=[batch, []])
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_pass1),
            patch("compgraph.enrichment.orchestrator.save_enrichment", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.enrichment.orchestrator.update_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.create_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.increment_enrichment_counter", mock_increment),
            patch("compgraph.enrichment.orchestrator.compute_content_hash", return_value="abc123"),
            patch("compgraph.main.shutdown_event") as mock_shutdown,
        ):
            mock_shutdown.is_set.return_value = False

            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=1)
            run = EnrichmentRun()
            await orch.run_pass1(run)

        token_calls = [c for c in mock_increment.call_args_list if "total_input_tokens" in c.kwargs]
        assert len(token_calls) == 0


class TestPass2TokenCounterWiring:
    @pytest.mark.asyncio
    async def test_pass2_increments_token_counters_on_success(self):
        mock_increment = AsyncMock()
        mock_pass2 = AsyncMock(
            return_value=LLMCallResult(result=SAMPLE_PASS2, input_tokens=200, output_tokens=100)
        )

        batch = [_make_pass2_triple()]
        mock_fetch = AsyncMock(side_effect=[batch, []])
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=MagicMock(id=uuid.uuid4()))
            )
        )
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass2", mock_pass2),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.enrichment.orchestrator.update_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.create_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.increment_enrichment_counter", mock_increment),
            patch("compgraph.enrichment.orchestrator.compute_content_hash", return_value="def456"),
            patch(
                "compgraph.enrichment.orchestrator.resolve_entity",
                AsyncMock(return_value=MagicMock()),
            ),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", AsyncMock()),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", AsyncMock()),
            patch("compgraph.main.shutdown_event") as mock_shutdown,
        ):
            mock_shutdown.is_set.return_value = False

            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=1)
            run = EnrichmentRun()
            from compgraph.enrichment.orchestrator import EnrichResult

            run.pass1_result = EnrichResult(
                succeeded=1,
                failed=0,
                skipped=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_api_calls=0,
                total_dedup_saved=0,
            )
            result = await orch.run_pass2(run)

        assert result.total_input_tokens == 200
        assert result.total_output_tokens == 100
        assert result.total_api_calls == 1

        token_calls = [c for c in mock_increment.call_args_list if "total_input_tokens" in c.kwargs]
        assert len(token_calls) >= 1
        tc = token_calls[0]
        assert tc.kwargs["total_input_tokens"] == 200
        assert tc.kwargs["total_output_tokens"] == 100
        assert tc.kwargs["total_api_calls"] == 1


class TestTokenCounterAccumulation:
    @pytest.mark.asyncio
    async def test_multiple_postings_accumulate_tokens(self):
        mock_increment = AsyncMock()
        call_count = 0

        async def mock_pass1_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return LLMCallResult(
                result=SAMPLE_PASS1,
                input_tokens=100 * call_count,
                output_tokens=50 * call_count,
            )

        mock_pass1 = AsyncMock(side_effect=mock_pass1_side_effect)

        p1, s1 = _make_posting_snapshot_pair(title="Job A", full_text="Content A")
        p2, s2 = _make_posting_snapshot_pair(title="Job B", full_text="Content B")
        batch = [(p1, s1), (p2, s2)]
        mock_fetch = AsyncMock(side_effect=[batch, []])
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        hash_counter = 0

        def unique_hash(*args, **kwargs):
            nonlocal hash_counter
            hash_counter += 1
            return f"hash{hash_counter}"

        with (
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_pass1),
            patch("compgraph.enrichment.orchestrator.save_enrichment", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.async_session_factory", mock_factory),
            patch("compgraph.enrichment.orchestrator.update_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.create_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.increment_enrichment_counter", mock_increment),
            patch(
                "compgraph.enrichment.orchestrator.compute_content_hash", side_effect=unique_hash
            ),
            patch("compgraph.main.shutdown_event") as mock_shutdown,
        ):
            mock_shutdown.is_set.return_value = False

            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=2)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        assert result.total_input_tokens == 300
        assert result.total_output_tokens == 150
        assert result.total_api_calls == 2

        token_calls = [c for c in mock_increment.call_args_list if "total_input_tokens" in c.kwargs]
        assert len(token_calls) == 2
        total_input = sum(c.kwargs["total_input_tokens"] for c in token_calls)
        total_output = sum(c.kwargs["total_output_tokens"] for c in token_calls)
        assert total_input == 300
        assert total_output == 150
