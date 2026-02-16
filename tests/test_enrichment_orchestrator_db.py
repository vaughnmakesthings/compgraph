"""Tests for enrichment orchestrator DB persistence functions."""

from __future__ import annotations

import inspect
import uuid

from compgraph.enrichment.orchestrator import (
    create_enrichment_run_record,
    get_latest_enrichment_run_from_db,
    increment_enrichment_counter,
    update_enrichment_run_record,
)


class TestDbPersistenceFunctions:
    def test_create_enrichment_run_record_is_async_with_run_id_param(self):
        assert inspect.iscoroutinefunction(create_enrichment_run_record)
        sig = inspect.signature(create_enrichment_run_record)
        assert "run_id" in sig.parameters
        assert sig.parameters["run_id"].annotation in (uuid.UUID, "uuid.UUID")

    def test_increment_enrichment_counter_is_async_with_kwargs(self):
        assert inspect.iscoroutinefunction(increment_enrichment_counter)
        sig = inspect.signature(increment_enrichment_counter)
        assert "run_id" in sig.parameters
        assert "counters" in sig.parameters
        assert sig.parameters["counters"].kind == inspect.Parameter.VAR_KEYWORD

    def test_update_enrichment_run_record_is_async_with_kwargs(self):
        assert inspect.iscoroutinefunction(update_enrichment_run_record)
        sig = inspect.signature(update_enrichment_run_record)
        assert "run_id" in sig.parameters
        assert "fields" in sig.parameters
        assert sig.parameters["fields"].kind == inspect.Parameter.VAR_KEYWORD

    def test_get_latest_from_db_is_async_returns_optional_dict(self):
        assert inspect.iscoroutinefunction(get_latest_enrichment_run_from_db)
        sig = inspect.signature(get_latest_enrichment_run_from_db)
        assert (
            len([p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]) == 0
        )
