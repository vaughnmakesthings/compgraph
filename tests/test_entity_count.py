"""Tests for entity_count field behavior in Pass 2 enrichment."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.db.models import PostingEnrichment
from compgraph.enrichment.orchestrator import EnrichmentOrchestrator, _mark_pass2_complete
from compgraph.enrichment.schemas import EntityMention, Pass2Result

# ---------------------------------------------------------------------------
# _mark_pass2_complete — entity_count assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_pass2_complete_sets_entity_count():
    enrichment = MagicMock()
    enrichment.enrichment_version = "v1"
    enrichment.entity_count = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = enrichment

    session = AsyncMock()
    session.execute.return_value = mock_result

    await _mark_pass2_complete(session, uuid.uuid4(), entity_count=3)

    assert enrichment.entity_count == 3


@pytest.mark.asyncio
async def test_mark_pass2_complete_defaults_entity_count_zero():
    enrichment = MagicMock()
    enrichment.enrichment_version = "v1"
    enrichment.entity_count = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = enrichment

    session = AsyncMock()
    session.execute.return_value = mock_result

    await _mark_pass2_complete(session, uuid.uuid4())

    assert enrichment.entity_count == 0


@pytest.mark.asyncio
async def test_mark_pass2_complete_already_pass2_still_sets_count():
    """entity_count is set even if enrichment_version already contains pass2."""
    enrichment = MagicMock()
    enrichment.enrichment_version = "v1+pass2"
    enrichment.entity_count = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = enrichment

    session = AsyncMock()
    session.execute.return_value = mock_result

    await _mark_pass2_complete(session, uuid.uuid4(), entity_count=2)

    # Version should NOT be doubled
    assert enrichment.enrichment_version == "v1+pass2"
    # But entity_count should still be set
    assert enrichment.entity_count == 2


# ---------------------------------------------------------------------------
# _resolve_and_save_pass2 — entity_count propagation
# ---------------------------------------------------------------------------


def _make_entities(count: int) -> list[EntityMention]:
    return [
        EntityMention(
            entity_name=f"Brand_{i}",
            entity_type="client_brand",
            confidence=0.9,
        )
        for i in range(count)
    ]


@pytest.mark.asyncio
@patch(
    "compgraph.enrichment.orchestrator._mark_pass2_complete",
    new_callable=AsyncMock,
)
@patch(
    "compgraph.enrichment.orchestrator.save_brand_mentions",
    new_callable=AsyncMock,
)
@patch(
    "compgraph.enrichment.orchestrator.resolve_entity",
    new_callable=AsyncMock,
)
async def test_resolve_and_save_pass2_with_entities(
    mock_resolve: AsyncMock,
    mock_save: AsyncMock,
    mock_mark: AsyncMock,
):
    mock_resolve.return_value = MagicMock()
    session = AsyncMock()
    posting_id = uuid.uuid4()
    enrichment_id = uuid.uuid4()
    pass2_result = Pass2Result(entities=_make_entities(3))

    await EnrichmentOrchestrator._resolve_and_save_pass2(
        session, posting_id, enrichment_id, pass2_result
    )

    mock_mark.assert_awaited_once_with(session, enrichment_id, entity_count=3)


@pytest.mark.asyncio
@patch(
    "compgraph.enrichment.orchestrator._mark_pass2_complete",
    new_callable=AsyncMock,
)
@patch(
    "compgraph.enrichment.orchestrator.save_brand_mentions",
    new_callable=AsyncMock,
)
async def test_resolve_and_save_pass2_empty_entities(
    mock_save: AsyncMock,
    mock_mark: AsyncMock,
):
    session = AsyncMock()
    posting_id = uuid.uuid4()
    enrichment_id = uuid.uuid4()
    pass2_result = Pass2Result(entities=[])

    await EnrichmentOrchestrator._resolve_and_save_pass2(
        session, posting_id, enrichment_id, pass2_result
    )

    mock_mark.assert_awaited_once_with(session, enrichment_id, entity_count=0)
    mock_save.assert_not_awaited()


@pytest.mark.asyncio
@patch(
    "compgraph.enrichment.orchestrator._mark_pass2_complete",
    new_callable=AsyncMock,
)
@patch(
    "compgraph.enrichment.orchestrator.save_brand_mentions",
    new_callable=AsyncMock,
)
async def test_resolve_and_save_pass2_none_entities(
    mock_save: AsyncMock,
    mock_mark: AsyncMock,
):
    session = AsyncMock()
    posting_id = uuid.uuid4()
    enrichment_id = uuid.uuid4()
    pass2_result = Pass2Result.model_validate({})

    await EnrichmentOrchestrator._resolve_and_save_pass2(
        session, posting_id, enrichment_id, pass2_result
    )

    mock_mark.assert_awaited_once_with(session, enrichment_id, entity_count=0)
    mock_save.assert_not_awaited()


# ---------------------------------------------------------------------------
# Model field existence
# ---------------------------------------------------------------------------


def test_entity_count_model_field_exists():
    columns = PostingEnrichment.__table__.columns
    assert "entity_count" in columns
