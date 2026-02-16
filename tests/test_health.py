from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.main import app


@pytest.fixture
def _mock_db_success():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    app.dependency_overrides[get_db] = lambda: mock_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _mock_db_failure():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=ConnectionRefusedError("connection refused"))
    app.dependency_overrides[get_db] = lambda: mock_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _mock_db_timeout():
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(10)

    mock_session = AsyncMock()
    mock_session.execute = slow_execute
    app.dependency_overrides[get_db] = lambda: mock_session
    yield
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    def test_healthy_when_db_connected(self, _mock_db_success: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.1.0"
        assert body["database"] == "connected"

    def test_degraded_when_db_raises(self, _mock_db_failure: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["version"] == "0.1.0"
        assert "error:" in body["database"]
        assert "connection refused" in body["database"]

    def test_degraded_when_db_times_out(self, _mock_db_timeout: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["version"] == "0.1.0"
        assert "error:" in body["database"]
