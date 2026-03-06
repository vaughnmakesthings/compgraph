"""Tests for embedding integration in _mark_pass2_complete."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_enrichment():
    """Create a mock PostingEnrichment with pass1 version."""
    enrichment = MagicMock()
    enrichment.enrichment_version = "v1"
    enrichment.entity_count = 0
    enrichment.title_normalized = "Field Marketing Representative"
    enrichment.content_role_specific = "Manage retail demos and events."
    enrichment.embedding = None
    return enrichment


@pytest.fixture
def mock_session(mock_enrichment):
    """Create a mock AsyncSession that returns the enrichment."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_enrichment
    session.execute.return_value = mock_result
    return session


class TestMarkPass2CompleteEmbedding:
    @patch("compgraph.enrichment.embeddings.generate_embedding", new_callable=AsyncMock)
    async def test_generates_embedding_on_pass2_complete(
        self, mock_generate: AsyncMock, mock_session: AsyncMock, mock_enrichment: MagicMock
    ):
        """Embedding should be generated when pass2 completes successfully."""
        from compgraph.enrichment.orchestrator import _mark_pass2_complete

        mock_generate.return_value = [0.1] * 384

        await _mark_pass2_complete(mock_session, uuid.uuid4(), entity_count=3)

        expected_text = "Field Marketing Representative Manage retail demos and events."
        mock_generate.assert_awaited_once_with(expected_text)
        assert mock_enrichment.embedding == [0.1] * 384

    @patch("compgraph.enrichment.embeddings.generate_embedding", new_callable=AsyncMock)
    async def test_embedding_failure_does_not_block_pass2(
        self, mock_generate: AsyncMock, mock_session: AsyncMock, mock_enrichment: MagicMock
    ):
        """Embedding failure should be logged but not prevent pass2 completion."""
        from compgraph.enrichment.orchestrator import _mark_pass2_complete

        mock_generate.side_effect = RuntimeError("model load failed")

        # Should not raise
        await _mark_pass2_complete(mock_session, uuid.uuid4(), entity_count=2)

        # Pass2 version should still be set despite embedding failure
        assert "pass2" in mock_enrichment.enrichment_version
        assert mock_enrichment.entity_count == 2
        # Embedding should remain None
        assert mock_enrichment.embedding is None

    @patch("compgraph.enrichment.embeddings.generate_embedding", new_callable=AsyncMock)
    async def test_empty_text_skips_embedding(
        self, mock_generate: AsyncMock, mock_session: AsyncMock, mock_enrichment: MagicMock
    ):
        """Empty title and content should skip embedding generation."""
        from compgraph.enrichment.orchestrator import _mark_pass2_complete

        mock_enrichment.title_normalized = ""
        mock_enrichment.content_role_specific = ""

        await _mark_pass2_complete(mock_session, uuid.uuid4(), entity_count=0)

        mock_generate.assert_not_awaited()
        assert mock_enrichment.embedding is None

    @patch("compgraph.enrichment.embeddings.generate_embedding", new_callable=AsyncMock)
    async def test_none_title_uses_content_only(
        self, mock_generate: AsyncMock, mock_session: AsyncMock, mock_enrichment: MagicMock
    ):
        """When title is None, only content should be used for embedding text."""
        from compgraph.enrichment.orchestrator import _mark_pass2_complete

        mock_enrichment.title_normalized = None
        mock_enrichment.content_role_specific = "Event coordinator role"
        mock_generate.return_value = [0.2] * 384

        await _mark_pass2_complete(mock_session, uuid.uuid4(), entity_count=1)

        mock_generate.assert_awaited_once_with("Event coordinator role")
