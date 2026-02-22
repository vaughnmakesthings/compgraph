from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from compgraph.aggregation.base import AggregationJob


class FakeJob(AggregationJob):
    table_name = "agg_test"

    async def compute_rows(self, session):
        return [{"id": "test", "value": 1}]


class EmptyJob(AggregationJob):
    table_name = "agg_empty"

    async def compute_rows(self, session):
        return []


class TestAggregationJobBase:
    def test_subclass_requires_table_name(self):
        with pytest.raises(TypeError, match="must define table_name"):

            class BadJob(AggregationJob):
                async def compute_rows(self, session):
                    return []

            BadJob()

    def test_subclass_with_table_name(self):
        job = FakeJob()
        assert job.table_name == "agg_test"

    def test_is_abstract(self):
        with pytest.raises(TypeError):
            AggregationJob()

    @pytest.mark.asyncio
    async def test_run_truncates_then_inserts(self):
        job = FakeJob()
        mock_session = AsyncMock()

        result = await job.run(mock_session)

        # Should call execute at least twice (TRUNCATE + INSERT)
        assert mock_session.execute.call_count >= 2
        # Check the first call is TRUNCATE via the TextClause text
        first_arg = mock_session.execute.call_args_list[0][0][0]
        assert "TRUNCATE" in first_arg.text
        assert result == 1
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_run_with_empty_rows_still_commits(self):
        job = EmptyJob()
        mock_session = AsyncMock()

        result = await job.run(mock_session)

        assert result == 0
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_run_returns_row_count(self):
        job = FakeJob()
        job.compute_rows = AsyncMock(
            return_value=[
                {"id": "1", "value": 1},
                {"id": "2", "value": 2},
                {"id": "3", "value": 3},
            ]
        )
        mock_session = AsyncMock()

        result = await job.run(mock_session)

        assert result == 3
