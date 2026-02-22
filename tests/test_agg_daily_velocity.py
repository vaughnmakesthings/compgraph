from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.daily_velocity import DailyVelocityJob


class TestDailyVelocityJob:
    def test_table_name(self) -> None:
        assert DailyVelocityJob().table_name == "agg_daily_velocity"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(DailyVelocityJob, AggregationJob)
