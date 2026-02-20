from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.main import app


def _make_db_fixture(execute_behavior):
    """Factory for DB mock fixtures with shared setup/teardown."""

    @pytest.fixture
    def _fixture():
        mock_session = AsyncMock()
        if callable(execute_behavior) and not isinstance(execute_behavior, (AsyncMock, MagicMock)):
            mock_session.execute = execute_behavior
        elif isinstance(execute_behavior, Exception):
            mock_session.execute = AsyncMock(side_effect=execute_behavior)
        else:
            mock_session.execute = AsyncMock(return_value=execute_behavior)
        app.dependency_overrides[get_db] = lambda: mock_session
        yield
        app.dependency_overrides.clear()

    return _fixture


async def _slow_execute(*args, **kwargs):
    await asyncio.sleep(10)


_mock_db_success = _make_db_fixture(MagicMock())
_mock_db_failure = _make_db_fixture(ConnectionRefusedError("connection refused"))
_mock_db_timeout = _make_db_fixture(_slow_execute)


@pytest.fixture(autouse=False)
def _cleanup_scheduler_state():
    yield
    if hasattr(app.state, "scheduler"):
        del app.state.scheduler


class TestHealthEndpoint:
    def test_healthy_when_db_connected(self, _mock_db_success: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.1.0"
        assert body["checks"]["database"] == "connected"

    def test_degraded_when_db_raises(self, _mock_db_failure: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["version"] == "0.1.0"
        assert "error:" in body["checks"]["database"]
        assert "connection refused" in body["checks"]["database"]

    def test_degraded_when_db_times_out(self, _mock_db_timeout: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["version"] == "0.1.0"
        assert "error:" in body["checks"]["database"]

    def test_scheduler_disabled_shown(self, _mock_db_success: None) -> None:
        with TestClient(app) as client:
            resp = client.get("/health")
        body = resp.json()
        assert body["checks"]["scheduler"] == "disabled"

    def test_scheduler_enabled_and_healthy(
        self, _mock_db_success: None, _cleanup_scheduler_state: None
    ) -> None:
        mock_scheduler = AsyncMock()
        mock_scheduler.get_schedules = AsyncMock(return_value=[MagicMock()])
        with (
            patch("compgraph.api.routes.health.settings") as mock_settings,
            TestClient(app) as client,
        ):
            mock_settings.SCHEDULER_ENABLED = True
            app.state.scheduler = mock_scheduler
            resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["checks"]["scheduler"] == "ok (1 schedule(s))"

    def test_scheduler_enabled_but_not_initialized(
        self, _mock_db_success: None, _cleanup_scheduler_state: None
    ) -> None:
        with (
            patch("compgraph.api.routes.health.settings") as mock_settings,
            TestClient(app) as client,
        ):
            mock_settings.SCHEDULER_ENABLED = True
            resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["scheduler"] == "error: not initialized"

    def test_scheduler_check_failure(
        self, _mock_db_success: None, _cleanup_scheduler_state: None
    ) -> None:
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedules = AsyncMock(side_effect=RuntimeError("scheduler crashed"))
        with (
            patch("compgraph.api.routes.health.settings") as mock_settings,
            TestClient(app) as client,
        ):
            mock_settings.SCHEDULER_ENABLED = True
            app.state.scheduler = mock_scheduler
            resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["scheduler"] == "error: RuntimeError"
