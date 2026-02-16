from __future__ import annotations

from compgraph.enrichment.orchestrator import (
    create_enrichment_run_record,
    get_latest_enrichment_run_from_db,
    increment_enrichment_counter,
    update_enrichment_run_record,
)


class TestDbPersistenceFunctions:
    def test_create_enrichment_run_record_callable(self):
        assert callable(create_enrichment_run_record)

    def test_get_latest_from_db_callable(self):
        assert callable(get_latest_enrichment_run_from_db)

    def test_increment_counter_callable(self):
        assert callable(increment_enrichment_counter)

    def test_update_record_callable(self):
        assert callable(update_enrichment_run_record)
