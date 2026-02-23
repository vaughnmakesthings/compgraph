from __future__ import annotations

from compgraph.aggregation.daily_velocity import _QUERY


class TestDailyVelocityQuery:
    def test_query_does_not_use_cross_join(self):
        """Query must not use CROSS JOIN (performance issue)."""
        assert "CROSS JOIN" not in _QUERY.upper()

    def test_query_does_not_use_exists_subquery(self):
        """Correlated EXISTS subquery must be eliminated."""
        assert "EXISTS" not in _QUERY.upper()

    def test_query_starts_from_posting_snapshots(self):
        """Query must use posting_snapshots as base table."""
        assert "posting_snapshots" in _QUERY

    def test_query_produces_required_columns(self):
        """Output must have all required columns."""
        for col in (
            "date",
            "company_id",
            "active_postings",
            "new_postings",
            "closed_postings",
            "net_change",
        ):
            assert col in _QUERY, f"Required column '{col}' missing from query"

    def test_net_change_computed_as_difference(self):
        """net_change = new_postings - closed_postings."""
        collapsed = "".join(_QUERY.split())
        assert "new_postings-closed_postings" in collapsed

    def test_query_joins_postings_table(self):
        """Must join postings table for company_id and post attributes."""
        assert "JOIN postings" in _QUERY

    def test_active_postings_counts_snapshot_rows(self):
        """active_postings must count from posting_snapshots (ps.posting_id)."""
        collapsed = "".join(_QUERY.split())
        assert "COUNT(DISTINCTps.posting_id)" in collapsed
