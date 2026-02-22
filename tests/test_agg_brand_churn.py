from __future__ import annotations

from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.brand_churn import BrandChurnSignalsJob


class TestBrandChurnSignalsJob:
    def test_table_name(self) -> None:
        assert BrandChurnSignalsJob().table_name == "agg_brand_churn_signals"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(BrandChurnSignalsJob, AggregationJob)
