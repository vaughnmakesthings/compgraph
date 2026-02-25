from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from compgraph.api.deps import get_settings
from compgraph.auth.dependencies import (
    AuthUser,
    get_current_user,
    get_current_user_disabled,
    get_current_user_optional,
    require_admin,
    require_admin_disabled,
    require_viewer,
)

TEST_SECRET = "test-jwt-secret-for-unit-tests-minimum-32-bytes"
TEST_USER_ID = str(uuid.uuid4())
TEST_EMAIL = "user@compgraph.io"


def _make_token(
    *,
    sub: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    role: str = "viewer",
    aal: str = "aal1",
    session_id: str = "sess-123",
    exp: int | None = None,
    secret: str = TEST_SECRET,
    audience: str = "authenticated",
) -> str:
    now = int(time.time())
    payload: dict = {
        "sub": sub,
        "email": email,
        "aal": aal,
        "session_id": session_id,
        "role": "authenticated",
        "app_metadata": {"role": role},
        "aud": audience,
        "iat": now,
        "exp": exp if exp is not None else now + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _mock_settings(secret: str = TEST_SECRET) -> MagicMock:
    mock = MagicMock()
    mock.SUPABASE_JWT_SECRET.get_secret_value.return_value = secret
    return mock


def _build_app() -> FastAPI:

    test_app = FastAPI()

    @test_app.get("/protected")
    def protected(user: AuthUser = Depends(get_current_user)):  # noqa: B008
        return {"id": str(user.id), "email": user.email, "role": user.role}

    @test_app.get("/admin-only")
    def admin_only(user: AuthUser = Depends(require_admin)):  # noqa: B008
        return {"id": str(user.id), "role": user.role}

    @test_app.get("/viewer-only")
    def viewer_only(user: AuthUser = Depends(require_viewer)):  # noqa: B008
        return {"id": str(user.id), "role": user.role}

    @test_app.get("/optional")
    def optional_auth(user: AuthUser | None = Depends(get_current_user_optional)):  # noqa: B008
        if user is None:
            return {"authenticated": False}
        return {"authenticated": True, "email": user.email}

    test_app.dependency_overrides[get_settings] = lambda: _mock_settings()
    return test_app


@pytest.fixture
def auth_app() -> FastAPI:
    return _build_app()


@pytest.fixture
def auth_client(auth_app: FastAPI) -> TestClient:
    return TestClient(auth_app)


class TestAuthDisabledBypass:
    def test_returns_mock_admin_user(self):
        user = get_current_user_disabled()
        assert isinstance(user, AuthUser)
        assert user.role == "admin"
        assert user.email == "dev@compgraph.io"
        assert user.session_id == "disabled"

    def test_require_admin_disabled_returns_mock(self):
        user = require_admin_disabled()
        assert isinstance(user, AuthUser)
        assert user.role == "admin"

    def test_dependency_override_bypasses_auth(self):

        app = FastAPI()

        @app.get("/protected")
        def protected(user: AuthUser = Depends(get_current_user)):  # noqa: B008
            return {"role": user.role}

        app.dependency_overrides[get_current_user] = get_current_user_disabled
        app.dependency_overrides[get_settings] = lambda: _mock_settings()

        with TestClient(app) as client:
            resp = client.get("/protected")
            assert resp.status_code == 200
            assert resp.json()["role"] == "admin"


class TestValidToken:
    def test_decodes_correctly(self, auth_client: TestClient):
        token = _make_token(role="viewer")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == TEST_USER_ID
        assert data["email"] == TEST_EMAIL
        assert data["role"] == "viewer"

    def test_admin_token(self, auth_client: TestClient):
        token = _make_token(role="admin")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_extracts_app_metadata_role_not_top_level(self, auth_client: TestClient):
        token = _make_token(role="admin")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        data = resp.json()
        assert data["role"] == "admin"
        assert data["role"] != "authenticated"


class TestExpiredToken:
    def test_raises_401(self, auth_client: TestClient):
        token = _make_token(exp=int(time.time()) - 3600)
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Token has expired"


class TestInvalidSignature:
    def test_raises_401(self, auth_client: TestClient):
        token = _make_token(secret="wrong-secret")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"


class TestMissingHeader:
    def test_raises_401(self, auth_client: TestClient):
        resp = auth_client.get("/protected")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Missing authorization header"


class TestRequireAdmin:
    def test_viewer_gets_403(self, auth_client: TestClient):
        token = _make_token(role="viewer")
        resp = auth_client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin role required"

    def test_admin_passes(self, auth_client: TestClient):
        token = _make_token(role="admin")
        resp = auth_client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"


class TestRequireViewer:
    def test_viewer_passes(self, auth_client: TestClient):
        token = _make_token(role="viewer")
        resp = auth_client.get("/viewer-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

    def test_admin_passes(self, auth_client: TestClient):
        token = _make_token(role="admin")
        resp = auth_client.get("/viewer-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_unknown_role_gets_403(self, auth_client: TestClient):
        token = _make_token(role="unknown")
        resp = auth_client.get("/viewer-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestOptionalAuth:
    def test_no_token_returns_none(self, auth_client: TestClient):
        resp = auth_client.get("/optional")
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is False

    def test_valid_token_returns_user(self, auth_client: TestClient):
        token = _make_token()
        resp = auth_client.get("/optional", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["email"] == TEST_EMAIL

    def test_invalid_token_returns_none(self, auth_client: TestClient):
        resp = auth_client.get("/optional", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is False


class TestWWWAuthenticateHeader:
    def test_401_includes_header(self, auth_client: TestClient):
        resp = auth_client.get("/protected")
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate") == "Bearer"

    def test_expired_token_includes_header(self, auth_client: TestClient):
        token = _make_token(exp=int(time.time()) - 3600)
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate") == "Bearer"


class TestMissingSubClaim:
    def test_raises_401(self, auth_client: TestClient):

        now = int(time.time())
        payload = {
            "email": "test@test.com",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
            "app_metadata": {"role": "viewer"},
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Token missing subject claim"


class TestAdminInviteEndpoint:
    @pytest.fixture
    def admin_app(self):
        from compgraph.api.deps import get_db
        from compgraph.api.routes.admin import router as admin_router

        app = FastAPI()
        app.include_router(admin_router)

        mock_admin = AuthUser(
            id=uuid.UUID(TEST_USER_ID),
            email="admin@test.com",
            role="admin",
            aal="aal1",
            session_id="test-session",
        )
        app.dependency_overrides[require_admin] = lambda: mock_admin

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        mock_settings = _mock_settings()
        mock_settings.SUPABASE_PROJECT_REF = "testproject"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value.return_value = "test-service-key"
        app.dependency_overrides[get_settings] = lambda: mock_settings

        app._mock_session = mock_session  # type: ignore[attr-defined]
        return app

    @pytest.fixture
    def admin_client(self, admin_app: FastAPI) -> TestClient:
        return TestClient(admin_app)

    def test_non_admin_gets_403(self):
        from compgraph.api.deps import get_db
        from compgraph.api.routes.admin import router as admin_router

        app = FastAPI()
        app.include_router(admin_router)

        mock_settings = _mock_settings()
        mock_settings.SUPABASE_PROJECT_REF = "testproject"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value.return_value = "test-service-key"
        app.dependency_overrides[get_settings] = lambda: mock_settings

        async def override_get_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            token = _make_token(role="viewer")
            resp = client.post(
                "/api/v1/admin/invite",
                json={"email": "new@test.com", "role": "viewer"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
            assert resp.json()["detail"] == "Admin role required"

    def test_admin_can_invite(self, admin_client: TestClient, admin_app: FastAPI):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": str(uuid.uuid4())}

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("compgraph.api.routes.admin.httpx.AsyncClient", return_value=mock_http_client):
            resp = admin_client.post(
                "/api/v1/admin/invite",
                json={"email": "newuser@example.com", "role": "viewer"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["email"] == "newuser@example.com"
            assert data["role"] == "viewer"
            assert data["invited"] is True

    def test_duplicate_email_returns_409(self, admin_client: TestClient, admin_app: FastAPI):
        mock_session = admin_app._mock_session  # type: ignore[attr-defined]
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(email="existing@test.com")
        mock_session.execute.return_value = mock_result

        resp = admin_client.post(
            "/api/v1/admin/invite",
            json={"email": "existing@test.com", "role": "viewer"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_invalid_email_returns_422(self, admin_client: TestClient):
        resp = admin_client.post(
            "/api/v1/admin/invite",
            json={"email": "not-an-email", "role": "viewer"},
        )
        assert resp.status_code == 422

    def test_invalid_role_returns_422(self, admin_client: TestClient):
        resp = admin_client.post(
            "/api/v1/admin/invite",
            json={"email": "valid@test.com", "role": "superadmin"},
        )
        assert resp.status_code == 422

    def test_supabase_failure_returns_502(self, admin_client: TestClient, admin_app: FastAPI):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("compgraph.api.routes.admin.httpx.AsyncClient", return_value=mock_http_client):
            resp = admin_client.post(
                "/api/v1/admin/invite",
                json={"email": "newuser@example.com", "role": "viewer"},
            )
            assert resp.status_code == 502
            assert resp.json()["detail"] == "Failed to send invite via Supabase Auth"


class TestAuthUserDataclass:
    def test_frozen(self):
        user = AuthUser(
            id=uuid.uuid4(),
            email="test@test.com",
            role="viewer",
            aal="aal1",
            session_id="s1",
        )
        with pytest.raises(AttributeError):
            user.role = "admin"  # type: ignore[misc]

    def test_slots(self):
        user = AuthUser(
            id=uuid.uuid4(),
            email="test@test.com",
            role="viewer",
            aal="aal1",
            session_id="s1",
        )
        assert set(user.__slots__) == {"id", "email", "role", "aal", "session_id"}


class TestAudienceValidation:
    def test_wrong_audience_rejected(self, auth_client: TestClient):
        token = _make_token(audience="wrong-audience")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"


class TestMissingAppMetadata:
    def _make_token_raw(self, payload_overrides: dict) -> str:
        now = int(time.time())
        payload: dict = {
            "sub": TEST_USER_ID,
            "email": TEST_EMAIL,
            "aal": "aal1",
            "session_id": "sess-123",
            "role": "authenticated",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        }
        payload.update(payload_overrides)
        return jwt.encode(payload, TEST_SECRET, algorithm="HS256")

    def test_no_app_metadata_defaults_to_viewer(self, auth_client: TestClient):
        token = self._make_token_raw({})
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

    def test_empty_app_metadata_defaults_to_viewer(self, auth_client: TestClient):
        token = self._make_token_raw({"app_metadata": {}})
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"


class TestMalformedToken:
    def test_non_jwt_string_raises_401(self, auth_client: TestClient):
        resp = auth_client.get("/protected", headers={"Authorization": "Bearer not-a-jwt"})
        assert resp.status_code == 401

    def test_garbage_base64_raises_401(self, auth_client: TestClient):
        resp = auth_client.get("/protected", headers={"Authorization": "Bearer aaa.bbb.ccc"})
        assert resp.status_code == 401


class TestInvalidSubFormat:
    def test_non_uuid_sub_raises_401(self, auth_client: TestClient):
        now = int(time.time())
        payload: dict = {
            "sub": "not-a-uuid",
            "email": TEST_EMAIL,
            "aal": "aal1",
            "session_id": "sess-123",
            "role": "authenticated",
            "app_metadata": {"role": "viewer"},
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"


class TestAlgorithmConfusion:
    def test_none_algorithm_rejected(self, auth_client: TestClient):
        import base64
        import json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        payload_data = {
            "sub": TEST_USER_ID,
            "email": TEST_EMAIL,
            "aud": "authenticated",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "app_metadata": {"role": "admin"},
        }
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=")
        token = f"{header.decode()}.{payload.decode()}."
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestTopLevelRoleIgnored:
    def test_top_level_admin_role_ignored(self, auth_client: TestClient):
        now = int(time.time())
        payload: dict = {
            "sub": TEST_USER_ID,
            "email": TEST_EMAIL,
            "aal": "aal1",
            "session_id": "sess-123",
            "role": "admin",
            "app_metadata": {"role": "viewer"},
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"
