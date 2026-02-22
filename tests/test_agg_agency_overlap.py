from __future__ import annotations

from compgraph.aggregation.agency_overlap import BrandAgencyOverlapJob
from compgraph.aggregation.base import AggregationJob


class TestBrandAgencyOverlapJob:
    def test_table_name(self) -> None:
        assert BrandAgencyOverlapJob().table_name == "agg_brand_agency_overlap"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(BrandAgencyOverlapJob, AggregationJob)
