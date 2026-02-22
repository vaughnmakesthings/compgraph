from __future__ import annotations

from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.coverage_gaps import MarketCoverageGapsJob


class TestMarketCoverageGapsJob:
    def test_table_name(self) -> None:
        assert MarketCoverageGapsJob().table_name == "agg_market_coverage_gaps"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(MarketCoverageGapsJob, AggregationJob)
