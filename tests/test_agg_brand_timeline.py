from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.brand_timeline import BrandTimelineJob


class TestBrandTimelineJob:
    def test_table_name(self) -> None:
        assert BrandTimelineJob().table_name == "agg_brand_timeline"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(BrandTimelineJob, AggregationJob)
