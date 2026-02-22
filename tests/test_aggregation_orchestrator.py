from compgraph.aggregation.orchestrator import AggregationOrchestrator, AggregationResult


class TestAggregationOrchestrator:
    def test_job_count(self) -> None:
        orch = AggregationOrchestrator()
        assert len(orch.jobs) == 7

    def test_job_order_velocity_before_pay(self) -> None:
        orch = AggregationOrchestrator()
        names = [j.table_name for j in orch.jobs]
        assert names.index("agg_daily_velocity") < names.index("agg_pay_benchmarks")

    def test_job_order_velocity_before_coverage(self) -> None:
        orch = AggregationOrchestrator()
        names = [j.table_name for j in orch.jobs]
        assert names.index("agg_daily_velocity") < names.index("agg_market_coverage_gaps")

    def test_all_table_names_unique(self) -> None:
        orch = AggregationOrchestrator()
        names = [j.table_name for j in orch.jobs]
        assert len(names) == len(set(names))

    def test_result_ok_property(self) -> None:
        result = AggregationResult()
        assert result.ok is True
        result.failed["test"] = "error"
        assert result.ok is False
