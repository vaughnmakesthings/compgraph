from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.pay_benchmarks import PayBenchmarksJob


class TestPayBenchmarksJob:
    def test_table_name(self) -> None:
        assert PayBenchmarksJob().table_name == "agg_pay_benchmarks"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(PayBenchmarksJob, AggregationJob)
