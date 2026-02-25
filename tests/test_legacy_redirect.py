from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.main import app


@pytest.fixture
def _mock_db() -> None:  # type: ignore[return]
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    app.dependency_overrides[get_db] = lambda: mock_session
    yield
    app.dependency_overrides.clear()


class TestLegacyApiRedirect:
    def test_get_redirects_to_v1(self, client: TestClient) -> None:
        resp = client.get("/api/pipeline/status", follow_redirects=False)
        assert resp.status_code == 308
        assert resp.headers["location"] == "/api/v1/pipeline/status"

    def test_preserves_query_string(self, client: TestClient) -> None:
        resp = client.get("/api/postings?limit=10", follow_redirects=False)
        assert resp.status_code == 308
        assert resp.headers["location"] == "/api/v1/postings?limit=10"

    def test_health_not_redirected(self, _mock_db: None) -> None:
        with TestClient(app) as tc:
            resp = tc.get("/health", follow_redirects=False)
        assert resp.status_code != 308
