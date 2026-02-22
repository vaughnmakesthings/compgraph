from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.posting_lifecycle import PostingLifecycleJob


class TestPostingLifecycleJob:
    def test_table_name(self) -> None:
        assert PostingLifecycleJob().table_name == "agg_posting_lifecycle"

    def test_is_aggregation_job(self) -> None:
        assert issubclass(PostingLifecycleJob, AggregationJob)
