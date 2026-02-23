from __future__ import annotations

from compgraph.aggregation.coverage_gaps import _QUERY


class TestCoverageGapsQuery:
    def test_state_extraction_strips_zip_codes(self):
        collapsed = "".join(_QUERY.split())
        assert "SPLIT_PART(TRIM(SPLIT_PART(" in collapsed or "REGEXP_REPLACE" in collapsed, (
            "State extraction must strip trailing zip codes — use double SPLIT_PART or REGEXP_REPLACE"
        )

    def test_query_has_no_cross_join(self):
        assert "CROSS JOIN" not in _QUERY.upper()

    def test_query_filters_null_location(self):
        assert "location_raw IS NOT NULL" in _QUERY

    def test_query_groups_by_company_and_market(self):
        assert "GROUP BY pb.company_id, pb.market_id" in _QUERY

    def test_query_selects_required_output_columns(self):
        for col in (
            "company_id",
            "market_id",
            "total_active_postings",
            "brand_count",
            "brand_names",
        ):
            assert col in _QUERY, f"Missing required column: {col}"
