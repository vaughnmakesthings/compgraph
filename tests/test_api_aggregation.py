from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.main import app


@pytest.fixture
def _mock_db() -> None:  # type: ignore[return]
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    app.dependency_overrides[get_db] = lambda: mock_session
    yield
    app.dependency_overrides.pop(get_db, None)


class TestAggregationEndpoints:
    def test_velocity_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/velocity")
        assert r.status_code == 200

    def test_brand_timeline_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/brand-timeline")
        assert r.status_code == 200

    def test_pay_benchmarks_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/pay-benchmarks")
        assert r.status_code == 200

    def test_lifecycle_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/lifecycle")
        assert r.status_code == 200

    def test_churn_signals_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/churn-signals")
        assert r.status_code == 200

    def test_coverage_gaps_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/coverage-gaps")
        assert r.status_code == 200

    def test_agency_overlap_endpoint_exists(self, _mock_db: None) -> None:
        with TestClient(app) as client:
            r = client.get("/api/v1/aggregation/agency-overlap")
        assert r.status_code == 200

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/aggregation/velocity",
            "/api/v1/aggregation/brand-timeline",
            "/api/v1/aggregation/pay-benchmarks",
            "/api/v1/aggregation/lifecycle",
            "/api/v1/aggregation/churn-signals",
            "/api/v1/aggregation/coverage-gaps",
            "/api/v1/aggregation/agency-overlap",
        ],
    )
    def test_cache_control_header_on_get_endpoints(self, _mock_db: None, path: str) -> None:
        with TestClient(app) as client:
            r = client.get(path)
        assert r.status_code == 200
        assert r.headers.get("cache-control") == "public, max-age=300"

    def test_trigger_no_cache_control_header(self, client) -> None:  # type: ignore[no-untyped-def]
        r = client.post("/api/v1/aggregation/trigger")
        assert "cache-control" not in r.headers

    def test_trigger_endpoint_exists(self, client) -> None:  # type: ignore[no-untyped-def]
        r = client.post("/api/v1/aggregation/trigger")
        assert r.status_code != 404
