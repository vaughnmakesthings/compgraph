from __future__ import annotations

import uuid
from datetime import UTC, datetime

from compgraph.db.models import EnrichmentRunDB, EnrichmentRunStatus


class TestEnrichmentRunDBModel:
    def test_model_has_required_columns(self):
        expected_id = uuid.uuid4()
        expected_time = datetime.now(UTC)
        run = EnrichmentRunDB(
            id=expected_id,
            status=EnrichmentRunStatus.PENDING,
            started_at=expected_time,
        )
        assert run.status == "pending"
        assert run.id == expected_id
        assert run.started_at == expected_time

    def test_circuit_breaker_tripped_column_exists(self):
        table = EnrichmentRunDB.__table__
        assert "circuit_breaker_tripped" in table.c
        col = table.c["circuit_breaker_tripped"]
        assert not col.nullable
        assert col.default.arg is False

    def test_circuit_breaker_tripped_can_be_set_true(self):
        run = EnrichmentRunDB(
            id=uuid.uuid4(),
            status=EnrichmentRunStatus.FAILED,
            started_at=datetime.now(UTC),
            circuit_breaker_tripped=True,
        )
        assert run.circuit_breaker_tripped is True

    def test_circuit_breaker_tripped_has_server_default(self):
        table = EnrichmentRunDB.__table__
        col = table.c["circuit_breaker_tripped"]
        assert col.server_default is not None
        assert str(col.server_default.arg) == "false"

    def test_integer_columns_have_server_defaults(self):
        table = EnrichmentRunDB.__table__
        int_cols = [
            "pass1_total",
            "pass1_succeeded",
            "pass1_failed",
            "pass1_skipped",
            "pass2_total",
            "pass2_succeeded",
            "pass2_failed",
            "pass2_skipped",
        ]
        for col_name in int_cols:
            col = table.c[col_name]
            assert col.server_default is not None, f"{col_name} missing server_default"
            assert str(col.server_default.arg) == "0", f"{col_name} server_default != '0'"

    def test_status_enum_values(self):
        assert EnrichmentRunStatus.PENDING == "pending"
        assert EnrichmentRunStatus.RUNNING == "running"
        assert EnrichmentRunStatus.COMPLETED == "completed"
        assert EnrichmentRunStatus.FAILED == "failed"

    def test_tablename(self):
        assert EnrichmentRunDB.__tablename__ == "enrichment_runs"
