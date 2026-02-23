from __future__ import annotations

from compgraph.aggregation.posting_lifecycle import _QUERY


class TestPostingLifecycleQuery:
    def test_days_open_guarded_against_negative(self):
        """days_open must use GREATEST(0, ...) to handle data anomalies."""
        collapsed = "".join(_QUERY.split())
        assert "GREATEST(0," in collapsed, (
            "days_open must be wrapped in GREATEST(0, ...) to prevent negative durations"
        )

    def test_avg_repost_gap_uses_division_by_times_reposted(self):
        """avg_repost_gap_days must divide days_open by times_reposted."""
        collapsed = "".join(_QUERY.split())
        assert "NULLIF(times_reposted,0)" in collapsed, (
            "avg_repost_gap_days must use NULLIF(times_reposted, 0) division to avoid divide-by-zero"
        )

    def test_query_uses_coalesce_for_active_postings(self):
        """days_open should use COALESCE(last_seen_at, NOW()) for active postings."""
        assert "COALESCE" in _QUERY and "last_seen_at" in _QUERY and "NOW()" in _QUERY

    def test_query_groups_by_required_dimensions(self):
        """GROUP BY must include company_id, role_archetype, period."""
        collapsed = "".join(_QUERY.split())
        assert "GROUPBYcompany_id,role_archetype,period" in collapsed

    def test_query_joins_posting_enrichments(self):
        """Query must join posting_enrichments for role_archetype."""
        assert "posting_enrichments" in _QUERY

    def test_query_has_repost_rate_calculation(self):
        """repost_rate must be computed as fraction of reposted postings."""
        assert "times_reposted" in _QUERY
        assert "repost_rate" in _QUERY
