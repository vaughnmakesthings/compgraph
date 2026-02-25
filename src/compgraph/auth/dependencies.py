from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from compgraph.api.deps import get_settings
from compgraph.config import Settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

MOCK_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: uuid.UUID
    email: str
    role: str
    aal: str
    session_id: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),  # noqa: B008
    current_settings: Settings = Depends(get_settings),  # noqa: B008
) -> AuthUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            current_settings.SUPABASE_JWT_SECRET.get_secret_value(),
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, AttributeError):
        logger.warning("JWT sub claim is not a valid UUID: %s", sub)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    raw_app_metadata = payload.get("app_metadata", {})
    app_metadata = raw_app_metadata if isinstance(raw_app_metadata, dict) else {}
    role = app_metadata.get("role")
    if role is None:
        logger.warning("JWT missing app_metadata.role for sub=%s, defaulting to viewer", sub)
        role = "viewer"
    aal = payload.get("aal", "aal1")
    session_id = payload.get("session_id", "")

    return AuthUser(
        id=user_id,
        email=payload.get("email", ""),
        role=role,
        aal=aal,
        session_id=session_id,
    )


def require_admin(
    user: AuthUser = Depends(get_current_user),  # noqa: B008
) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


def require_viewer(
    user: AuthUser = Depends(get_current_user),  # noqa: B008
) -> AuthUser:
    if user.role not in ("admin", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer or admin role required",
        )
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),  # noqa: B008
    current_settings: Settings = Depends(get_settings),  # noqa: B008
) -> AuthUser | None:
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, current_settings)
    except HTTPException:
        return None


def get_current_user_disabled() -> AuthUser:
    return AuthUser(
        id=MOCK_ADMIN_ID,
        email="dev@compgraph.io",
        role="admin",
        aal="aal1",
        session_id="disabled",
    )


def require_admin_disabled() -> AuthUser:
    return get_current_user_disabled()
