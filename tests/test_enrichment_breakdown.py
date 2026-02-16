from __future__ import annotations

from unittest.mock import MagicMock


class TestGetEnrichmentPassBreakdown:
    def test_returns_pass_counts(self) -> None:
        from compgraph.dashboard.queries import get_enrichment_pass_breakdown

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalar_one=MagicMock(return_value=100)),
                MagicMock(scalar_one=MagicMock(return_value=60)),
                MagicMock(scalar_one=MagicMock(return_value=30)),
            ]
        )
        result = get_enrichment_pass_breakdown(session)
        assert result["total_active"] == 100
        assert result["unenriched"] == 10
        assert result["pass1_only"] == 60
        assert result["fully_enriched"] == 30

    def test_no_postings(self) -> None:
        from compgraph.dashboard.queries import get_enrichment_pass_breakdown

        session = MagicMock()
        session.execute = MagicMock(
            side_effect=[
                MagicMock(scalar_one=MagicMock(return_value=0)),
                MagicMock(scalar_one=MagicMock(return_value=0)),
                MagicMock(scalar_one=MagicMock(return_value=0)),
            ]
        )
        result = get_enrichment_pass_breakdown(session)
        assert result["total_active"] == 0
        assert result["unenriched"] == 0
