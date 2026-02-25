from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.auth.dependencies import (
    MOCK_ADMIN_ID,
    AuthUser,
    get_current_user,
    get_current_user_disabled,
    require_admin,
    require_viewer,
)

VIEWER_USER = AuthUser(
    id=uuid.uuid4(),
    email="viewer@compgraph.io",
    role="viewer",
    aal="aal1",
    session_id="test-viewer",
)

ADMIN_USER = AuthUser(
    id=uuid.uuid4(),
    email="admin@compgraph.io",
    role="admin",
    aal="aal1",
    session_id="test-admin",
)

ADMIN_ROUTES: list[tuple[str, str]] = [
    ("POST", "/api/v1/admin/invite"),
    ("GET", "/api/v1/admin/users"),
]

VIEWER_ROUTES: list[tuple[str, str]] = [
    ("GET", "/api/v1/aggregation/velocity"),
    ("GET", "/api/v1/aggregation/brand-timeline"),
    ("GET", "/api/v1/aggregation/pay-benchmarks"),
    ("GET", "/api/v1/aggregation/lifecycle"),
    ("GET", "/api/v1/companies"),
]


def _mock_db_session() -> AsyncMock:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    return mock_session


def _override_require_admin_for(user: AuthUser):
    def _dep() -> AuthUser:
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required",
            )
        return user

    return _dep


def _override_require_viewer_for(user: AuthUser):
    def _dep() -> AuthUser:
        if user.role not in ("admin", "viewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewer or admin role required",
            )
        return user

    return _dep


def _apply_overrides(user: AuthUser) -> dict:
    from compgraph.main import app

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = _override_require_admin_for(user)
    app.dependency_overrides[require_viewer] = _override_require_viewer_for(user)
    app.dependency_overrides[get_db] = lambda: _mock_db_session()
    return original


def _restore_overrides(original: dict) -> None:
    from compgraph.main import app

    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)


@pytest.fixture
def viewer_client() -> Generator[TestClient, None, None]:
    from compgraph.main import app

    original = _apply_overrides(VIEWER_USER)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    _restore_overrides(original)


@pytest.fixture
def admin_client() -> Generator[TestClient, None, None]:
    from compgraph.main import app

    original = _apply_overrides(ADMIN_USER)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    _restore_overrides(original)


@pytest.fixture
def bypass_client() -> Generator[TestClient, None, None]:
    from compgraph.auth.dependencies import (
        get_current_user_disabled,
        get_current_user_optional,
        require_admin_disabled,
    )
    from compgraph.main import app

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = get_current_user_disabled
    app.dependency_overrides[require_admin] = require_admin_disabled
    app.dependency_overrides[require_viewer] = require_admin_disabled
    app.dependency_overrides[get_current_user_optional] = get_current_user_disabled
    app.dependency_overrides[get_db] = lambda: _mock_db_session()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)


class TestAuthDisabledBypass:
    def test_auth_disabled_env_is_set_in_conftest(self):
        import os

        assert os.environ.get("AUTH_DISABLED") == "true"

    def test_auth_disabled_setting_is_true(self):
        from compgraph.config import settings

        assert settings.AUTH_DISABLED is True

    def test_auth_disabled_returns_mock_admin(self):
        user = get_current_user_disabled()
        assert user.role == "admin"
        assert user.id == MOCK_ADMIN_ID

    def test_health_no_auth_required(self, bypass_client: TestClient):
        resp = bypass_client.get("/health")
        assert resp.status_code in (200, 503)
        assert resp.status_code != 401

    def test_companies_no_auth_header(self, bypass_client: TestClient):
        resp = bypass_client.get("/api/v1/companies")
        assert resp.status_code != 401

    def test_aggregation_velocity_no_auth_header(self, bypass_client: TestClient):
        resp = bypass_client.get("/api/v1/aggregation/velocity")
        assert resp.status_code != 401

    def test_scrape_status_no_auth_header(self, bypass_client: TestClient):
        resp = bypass_client.get("/api/v1/scrape/status")
        assert resp.status_code in (200, 404)

    def test_admin_users_no_auth_header(self, bypass_client: TestClient):
        resp = bypass_client.get("/api/v1/admin/users")
        assert resp.status_code != 401


class TestAdminRoutesRejectViewer:
    def test_admin_invite_returns_403_for_viewer(self, viewer_client: TestClient):
        resp = viewer_client.post(
            "/api/v1/admin/invite",
            json={"email": "test@example.com", "role": "viewer"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin role required"

    def test_admin_users_returns_403_for_viewer(self, viewer_client: TestClient):
        resp = viewer_client.get("/api/v1/admin/users")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin role required"

    @pytest.mark.parametrize(
        "method,path",
        ADMIN_ROUTES,
        ids=[f"{m} {p}" for m, p in ADMIN_ROUTES],
    )
    def test_all_admin_routes_reject_viewer(
        self, viewer_client: TestClient, method: str, path: str
    ):
        kwargs: dict = {}
        if method == "POST" and "invite" in path:
            kwargs["json"] = {"email": "test@example.com", "role": "viewer"}
        resp = viewer_client.request(method, path, **kwargs)
        assert resp.status_code == 403


class TestAdminRoutesAcceptAdmin:
    def test_admin_users_succeeds_for_admin(self, admin_client: TestClient):
        resp = admin_client.get("/api/v1/admin/users")
        assert resp.status_code != 403
        assert resp.status_code != 401


class TestViewerRoutesAcceptViewer:
    @pytest.mark.parametrize(
        "method,path",
        VIEWER_ROUTES,
        ids=[f"{m} {p}" for m, p in VIEWER_ROUTES],
    )
    def test_viewer_routes_accept_viewer(self, viewer_client: TestClient, method: str, path: str):
        resp = viewer_client.request(method, path)
        assert resp.status_code != 401
        assert resp.status_code != 403


class TestViewerRoutesAcceptAdmin:
    @pytest.mark.parametrize(
        "method,path",
        VIEWER_ROUTES,
        ids=[f"{m} {p}" for m, p in VIEWER_ROUTES],
    )
    def test_viewer_routes_accept_admin(self, admin_client: TestClient, method: str, path: str):
        resp = admin_client.request(method, path)
        assert resp.status_code != 401
        assert resp.status_code != 403


class TestRoleEscalationPrevention:
    def test_viewer_can_read_scrape_status(self, viewer_client: TestClient):
        resp = viewer_client.get("/api/v1/scrape/status")
        assert resp.status_code != 401

    def test_viewer_can_trigger_scrape(self, viewer_client: TestClient):
        resp = viewer_client.post("/api/v1/scrape/trigger")
        assert resp.status_code != 401
