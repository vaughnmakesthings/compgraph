# Supabase Auth + FastAPI Integration

> Reference doc for CompGraph M4d auth implementation.
> Researched: 2026-02-21. Sources listed at bottom.

## Table of Contents

- [S1 Architecture Overview](#s1-architecture-overview)
- [S2 JWT Verification Middleware](#s2-jwt-verification-middleware)
- [S3 Magic Link Invite Flow](#s3-magic-link-invite-flow)
- [S4 Role-Based Access Control](#s4-role-based-access-control)
- [S5 Password Login Flow](#s5-password-login-flow)
- [S6 Implementation Checklist](#s6-implementation-checklist)

---

## S1 Architecture Overview

### How Supabase Auth Works

Supabase Auth is a standalone authentication server (GoTrue) that issues JWTs. The FastAPI
backend never manages passwords or sessions directly — it only **verifies** tokens that
Supabase issued.

```
                         ┌──────────────┐
                         │  Supabase    │
                         │  Auth Server │
                         └──────┬───────┘
                                │ issues JWT
                                ▼
┌──────────┐  login    ┌──────────────┐  Bearer JWT   ┌──────────────┐
│  Next.js │ ────────► │  Supabase JS │ ────────────► │   FastAPI    │
│ Frontend │           │   Client     │               │   Backend    │
└──────────┘           └──────────────┘               └──────┬───────┘
                                                             │ verify JWT
                                                             │ (local or JWKS)
                                                             ▼
                                                      ┌──────────────┐
                                                      │  Supabase    │
                                                      │  Postgres    │
                                                      └──────────────┘
```

### Token Flow

1. **Frontend** calls `supabase.auth.signInWithPassword()` or clicks a magic link.
2. **Supabase Auth** validates credentials and returns an `access_token` (JWT) + `refresh_token`.
3. **Frontend** stores the JWT (HttpOnly cookie recommended) and sends it as `Authorization: Bearer <token>` on every API request to FastAPI.
4. **FastAPI** verifies the JWT signature, extracts `sub` (user ID), `role`, and `app_metadata` claims.
5. **FastAPI** uses the user ID to look up the CompGraph `users` table for app-level role enforcement.

### JWT Structure

A Supabase-issued JWT contains these claims:

```json
{
  "sub": "a1b2c3d4-uuid",
  "email": "user@example.com",
  "role": "authenticated",
  "aud": "authenticated",
  "iss": "https://tkvxyxwfosworwqxesnz.supabase.co/auth/v1",
  "exp": 1678886400,
  "iat": 1678882800,
  "aal": "aal1",
  "session_id": "...",
  "app_metadata": {
    "provider": "email",
    "compgraph_role": "admin"
  },
  "user_metadata": {
    "name": "Jane Admin"
  }
}
```

Key claims for CompGraph:
- `sub` — Supabase user UUID (maps to auth identity, not necessarily CompGraph `users.id`)
- `email` — user's email address
- `app_metadata.compgraph_role` — custom claim injected via Auth Hook (see S4)
- `role` — always `"authenticated"` for logged-in users (Postgres role, not app role)

### Signing Key Transition (2025-2026)

Supabase is migrating from **symmetric** (HS256 with a shared `JWT_SECRET`) to **asymmetric**
(ES256/RS256 via JWKS). Timeline:

- **Oct 2025**: New projects default to asymmetric JWTs.
- **Late 2026**: All projects expected to complete migration.
- **JWKS endpoint**: `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`

**Recommendation for CompGraph**: Implement JWKS-based verification from the start with
HS256 fallback, since the project was created before Oct 2025. Rotate to asymmetric keys
before late 2026.

---

## S2 JWT Verification Middleware

### Dependencies

```
# pyproject.toml — add to [project.dependencies]
python-jose[cryptography]>=3.3.0
httpx>=0.27.0  # already in project
```

`python-jose` handles both HS256 (symmetric) and ES256/RS256 (asymmetric) verification.
For JWKS-only verification, `PyJWT` with `PyJWKClient` is an alternative, but `python-jose`
is more commonly used with FastAPI.

### Config Additions

```python
# src/compgraph/config.py — new fields

class Settings(BaseSettings):
    # ... existing fields ...

    # Supabase Auth
    SUPABASE_JWT_SECRET: str = ""          # HS256 fallback (Dashboard > Settings > API > JWT Secret)
    SUPABASE_JWKS_URL: str = ""            # Auto-derived if empty
    SUPABASE_SERVICE_ROLE_KEY: str = ""    # For admin API calls (invite, create user)

    @property
    def supabase_jwks_url(self) -> str:
        if self.SUPABASE_JWKS_URL:
            return self.SUPABASE_JWKS_URL
        return f"https://{self.SUPABASE_PROJECT_REF}.supabase.co/auth/v1/.well-known/jwks.json"

    @property
    def supabase_issuer(self) -> str:
        return f"https://{self.SUPABASE_PROJECT_REF}.supabase.co/auth/v1"
```

### JWKS Cache

```python
# src/compgraph/auth/jwks.py
"""JWKS fetcher with TTL cache for Supabase JWT verification."""

import time
from dataclasses import dataclass, field

import httpx
from jose import jwk
from jose.utils import base64url_decode


@dataclass
class JWKSCache:
    """Caches JWKS keys with a configurable TTL (default: 1 hour)."""

    jwks_url: str
    ttl_seconds: int = 3600
    _keys: dict[str, dict] = field(default_factory=dict)
    _fetched_at: float = 0.0

    def _is_expired(self) -> bool:
        return time.monotonic() - self._fetched_at > self.ttl_seconds

    async def get_signing_key(self, kid: str) -> dict:
        """Return the JWK matching the given key ID, fetching if cache is stale."""
        if self._is_expired() or kid not in self._keys:
            await self._refresh()
        if kid not in self._keys:
            raise ValueError(f"No signing key found for kid={kid}")
        return self._keys[kid]

    async def _refresh(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.jwks_url, timeout=10.0)
            resp.raise_for_status()
            jwks_data = resp.json()

        self._keys = {}
        for key_data in jwks_data.get("keys", []):
            kid = key_data.get("kid")
            if kid:
                self._keys[kid] = key_data
        self._fetched_at = time.monotonic()
```

### Auth Dependency

```python
# src/compgraph/auth/dependencies.py
"""FastAPI dependencies for Supabase JWT verification."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.auth.jwks import JWKSCache
from compgraph.config import settings
from compgraph.db.models import User

if TYPE_CHECKING:
    pass

# --- Module-level singletons ---

_bearer_scheme = HTTPBearer(
    scheme_name="Supabase JWT",
    description="Supabase-issued access token",
)

_jwks_cache = JWKSCache(jwks_url=settings.supabase_jwks_url)

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class AuthenticatedUser:
    """Resolved user from JWT + database lookup."""

    supabase_user_id: str      # JWT 'sub' claim
    email: str
    compgraph_role: str         # From CompGraph users table ('admin' | 'viewer')
    user_id: uuid.UUID          # CompGraph users.id


async def _verify_jwt(token: str) -> dict:
    """Verify a Supabase JWT and return its payload.

    Tries JWKS (asymmetric) first, falls back to HS256 (symmetric).
    """
    # --- Attempt 1: Asymmetric via JWKS ---
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if kid:
            key_data = await _jwks_cache.get_signing_key(kid)
            payload = jwt.decode(
                token,
                key_data,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
                issuer=settings.supabase_issuer,
            )
            return payload
    except (JWTError, ValueError, KeyError):
        pass  # Fall through to symmetric

    # --- Attempt 2: Symmetric HS256 with JWT secret ---
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload
        except JWTError:
            pass

    raise _credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """Extract and verify the Supabase JWT, then resolve the CompGraph user.

    Usage:
        @app.get("/protected")
        async def protected(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    payload = await _verify_jwt(credentials.credentials)

    supabase_uid = payload.get("sub")
    email = payload.get("email")
    if not supabase_uid or not email:
        raise _credentials_exception

    # Look up CompGraph user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not registered in CompGraph. Contact an admin for an invite.",
        )

    return AuthenticatedUser(
        supabase_user_id=supabase_uid,
        email=email,
        compgraph_role=user.role,
        user_id=user.id,
    )


# Import at module level would be circular; use late import in function
def get_db():
    """Re-export to avoid circular imports. Overridden at module init."""
    from compgraph.api.deps import get_db as _get_db

    return _get_db()
```

### Important: The `get_db` Dependency

The auth module needs the database session. To avoid circular imports, it re-exports
`get_db` from `compgraph.api.deps`. An alternative is to pass it via `Depends()` chain
(shown above).

### Verification Strategy Decision

| Approach | Pros | Cons |
|----------|------|------|
| **Local JWT decode** (recommended) | Fast (~0.1ms), no network call, works offline | Must handle key rotation, cache JWKS |
| **Supabase `auth.get_user(token)`** | Always current, simple | Network call per request (~50-200ms), rate limits |
| **Supabase `/auth/v1/user` endpoint** | No SDK needed | Network call, region-dependent latency |

**CompGraph choice**: Local JWT decode with JWKS + HS256 fallback. The `get_user()` round-trip
is unacceptable for a high-frequency API.

---

## S3 Magic Link Invite Flow

### Overview

CompGraph uses an **invite-only** model. Admins invite users; users cannot self-register.

```
Admin (FastAPI)                 Supabase Auth              New User
     │                               │                        │
     │  invite_user_by_email()       │                        │
     │──────────────────────────────►│                        │
     │                               │   email with link      │
     │                               │───────────────────────►│
     │                               │                        │
     │                               │  user clicks link      │
     │                               │◄───────────────────────│
     │                               │                        │
     │                               │  redirect to frontend  │
     │                               │───────────────────────►│
     │                               │                        │
     │                               │  set password (optional)│
     │                               │◄───────────────────────│
     │                               │                        │
     │                               │  JWT issued            │
     │                               │───────────────────────►│
```

### Admin Client Setup

```python
# src/compgraph/auth/admin.py
"""Supabase Admin auth client for user management."""

from supabase import create_client
from supabase.lib.client_options import ClientOptions

from compgraph.config import settings


def get_supabase_admin_client():
    """Create a Supabase client with service_role key for admin operations.

    IMPORTANT: Never expose the service_role key to the frontend.
    This client must only be used in server-side (FastAPI) code.
    """
    supabase_url = f"https://{settings.SUPABASE_PROJECT_REF}.supabase.co"
    return create_client(
        supabase_url,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        ),
    )
```

### Invite Endpoint

```python
# src/compgraph/api/routes/auth.py
"""Auth management endpoints (admin-only)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.auth.admin import get_supabase_admin_client
from compgraph.auth.dependencies import AuthenticatedUser, get_current_user
from compgraph.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"  # "admin" or "viewer"
    name: str | None = None


class InviteResponse(BaseModel):
    message: str
    email: str
    role: str


@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    body: InviteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteResponse:
    """Invite a new user via magic link email.

    Only admins can invite. Creates a CompGraph user record and triggers
    a Supabase invite email.
    """
    # Enforce admin-only
    if current_user.compgraph_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate role
    if body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=422, detail="Role must be 'admin' or 'viewer'")

    # Check if user already exists in CompGraph
    from sqlalchemy import select

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already exists")

    # 1. Create CompGraph user record
    new_user = User(
        email=body.email,
        name=body.name,
        role=body.role,
        invited_by=current_user.user_id,
    )
    db.add(new_user)
    await db.flush()  # Get the ID before commit

    # 2. Send Supabase invite email
    admin_client = get_supabase_admin_client()
    try:
        admin_client.auth.admin.invite_user_by_email(
            body.email,
            {
                "data": {
                    "compgraph_role": body.role,
                    "name": body.name,
                },
                "redirect_to": f"https://compgraph.io/auth/callback",
            },
        )
    except Exception as e:
        # Roll back CompGraph user if Supabase invite fails
        await db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send invite email: {e}",
        )

    await db.commit()

    return InviteResponse(
        message=f"Invite sent to {body.email}",
        email=body.email,
        role=body.role,
    )
```

### Alternative: `create_user` + Manual Password Set

If you need to create a user with a pre-set password (e.g., for testing or seeding):

```python
# Server-side only — requires service_role key
admin_client = get_supabase_admin_client()

response = admin_client.auth.admin.create_user(
    {
        "email": "testuser@example.com",
        "password": "initial-password-123",
        "email_confirm": True,  # Skip email verification
        "app_metadata": {"compgraph_role": "viewer"},
        "user_metadata": {"name": "Test User"},
    }
)
```

### Frontend Callback Handling

After the user clicks the magic link, Supabase redirects to the frontend callback URL
with auth tokens in the URL fragment:

```
https://compgraph.io/auth/callback#access_token=eyJ...&refresh_token=...&type=invite
```

The Next.js frontend extracts these tokens via `supabase.auth.exchangeCodeForSession()`
(if using PKCE) or reads them from the URL hash. The invite flow does NOT support PKCE,
so tokens arrive in the fragment.

---

## S4 Role-Based Access Control

### Role Storage: Dual-Layer Approach

CompGraph uses **two layers** for role enforcement:

| Layer | Where | Purpose |
|-------|-------|---------|
| **CompGraph `users` table** | `users.role` column | Server-side role lookup, source of truth |
| **Supabase `app_metadata`** | JWT `app_metadata.compgraph_role` | Optional fast-path from JWT claims |

The CompGraph `users` table is the **authoritative** source. The JWT `app_metadata` claim
is a convenience for lightweight checks but can become stale if a role is changed without
re-issuing the JWT.

### Why Not Just `app_metadata`?

- `app_metadata` requires a Custom Access Token Hook (Postgres function) to inject into the JWT.
- Role changes via `update_user_by_id` only take effect on the next token refresh.
- The CompGraph `users.role` column is checked on every request via the database lookup in `get_current_user`.

### Custom Access Token Hook (Optional Enhancement)

To embed `compgraph_role` directly in the JWT (avoids DB lookup for role on every request):

```sql
-- Run via Supabase SQL Editor or migration
-- This function runs before every JWT is issued

CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    claims jsonb;
    user_role text;
BEGIN
    -- Extract current claims from the event
    claims := event->'claims';

    -- Look up the user's CompGraph role
    SELECT role INTO user_role
    FROM public.users
    WHERE email = (claims->>'email');

    -- If user exists in CompGraph, inject their role
    IF user_role IS NOT NULL THEN
        claims := jsonb_set(
            claims,
            '{app_metadata, compgraph_role}',
            to_jsonb(user_role)
        );
    END IF;

    -- Return the modified event
    RETURN jsonb_set(event, '{claims}', claims);
END;
$$;

-- Grant execute to supabase_auth_admin (required for Auth hooks)
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO supabase_auth_admin;

-- Revoke from public for security
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM anon;
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM authenticated;
```

Then enable it in the Supabase Dashboard: **Authentication > Hooks > Custom Access Token Hook** and select the `custom_access_token_hook` function.

### FastAPI Role Dependencies

```python
# src/compgraph/auth/dependencies.py — additional dependencies

async def require_auth(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require any authenticated CompGraph user. Alias for clarity."""
    return user


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require an admin user. Returns 403 if not admin."""
    if user.compgraph_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def require_role(
    *allowed_roles: str,
):
    """Factory for role-based dependencies.

    Usage:
        @app.get("/reports", dependencies=[Depends(require_role("admin", "analyst"))])
    """
    async def _check(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.compgraph_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(allowed_roles)}",
            )
        return user
    return _check
```

### Usage in Routes

```python
from compgraph.auth.dependencies import require_admin, require_auth

# Any authenticated user
@router.get("/postings")
async def list_postings(
    user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    ...

# Admin only
@router.delete("/postings/{posting_id}")
async def delete_posting(
    posting_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ...

# Router-level protection (all routes in router require auth)
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
```

### Updating a User's Role

```python
# Server-side admin operation
async def update_user_role(
    user_email: str,
    new_role: str,
    db: AsyncSession,
):
    """Update a user's role in both CompGraph DB and Supabase app_metadata."""
    from sqlalchemy import select, update

    # 1. Update CompGraph users table
    await db.execute(
        update(User).where(User.email == user_email).values(role=new_role)
    )
    await db.commit()

    # 2. Update Supabase app_metadata (takes effect on next token refresh)
    admin_client = get_supabase_admin_client()
    # First, find the Supabase user ID
    users_response = admin_client.auth.admin.list_users()
    supabase_user = next(
        (u for u in users_response if u.email == user_email), None
    )
    if supabase_user:
        admin_client.auth.admin.update_user_by_id(
            supabase_user.id,
            {"app_metadata": {"compgraph_role": new_role}},
        )
```

---

## S5 Password Login Flow

### Frontend Login (Next.js)

Users who accepted an invite and set a password can log in directly:

```typescript
// Next.js frontend — login page
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

async function login(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) throw error;

  // data.session.access_token — JWT to send to FastAPI
  // data.session.refresh_token — for token refresh
  return data.session;
}
```

### Token Refresh

Supabase access tokens expire (default: 1 hour). The frontend must handle refresh:

```typescript
// Automatic refresh via Supabase client
supabase.auth.onAuthStateChange((event, session) => {
  if (event === "TOKEN_REFRESHED" && session) {
    // Update stored access token
    setAccessToken(session.access_token);
  }
});

// Manual refresh
const { data, error } = await supabase.auth.refreshSession();
```

### FastAPI Receives the Token

The FastAPI backend does not handle login or token refresh — it only verifies tokens.
The frontend includes the JWT in every request:

```typescript
// API client wrapper
async function apiCall(path: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    throw new Error("Not authenticated");
  }

  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${session.access_token}`,
      "Content-Type": "application/json",
    },
  });
}
```

### Session Management Considerations

| Concern | Approach |
|---------|----------|
| Token storage | HttpOnly cookie or in-memory (NOT localStorage) |
| Token refresh | Supabase JS client handles automatically |
| Logout | `supabase.auth.signOut()` — invalidates refresh token server-side |
| Expired token hitting FastAPI | Returns 401; frontend intercepts and refreshes |
| Multiple tabs | Supabase JS uses BroadcastChannel for cross-tab sync |

### FastAPI Does NOT Need:

- A `/login` endpoint — login happens on the frontend via Supabase JS.
- A `/refresh` endpoint — refresh happens on the frontend via Supabase JS.
- A `/logout` endpoint — logout is client-side (optionally, add one to clear server-side state).
- Session storage — JWTs are stateless. No server-side session table needed.

---

## S6 Implementation Checklist

### Prerequisites

- [ ] Get `SUPABASE_JWT_SECRET` from Supabase Dashboard > Settings > API > JWT Secret
- [ ] Get `SUPABASE_SERVICE_ROLE_KEY` from Supabase Dashboard > Settings > API > `service_role` key
- [ ] Add both to 1Password and `.env` template
- [ ] Determine if project uses asymmetric JWTs (check Dashboard > Settings > API > JWT Signing Keys)

### Dependencies

- [ ] Add `python-jose[cryptography]` to `pyproject.toml`
- [ ] Add `supabase` (supabase-py) to `pyproject.toml` for admin client
- [ ] Run `uv sync`

### Config

- [ ] Add `SUPABASE_JWT_SECRET`, `SUPABASE_JWKS_URL`, `SUPABASE_SERVICE_ROLE_KEY` to `Settings`
- [ ] Add `supabase_jwks_url` and `supabase_issuer` properties
- [ ] Update `.env.example` with new vars
- [ ] Add secrets to 1Password and `op` env file

### Auth Module

- [ ] Create `src/compgraph/auth/__init__.py`
- [ ] Create `src/compgraph/auth/jwks.py` — JWKS cache
- [ ] Create `src/compgraph/auth/dependencies.py` — `get_current_user`, `require_auth`, `require_admin`
- [ ] Create `src/compgraph/auth/admin.py` — Supabase admin client wrapper

### API Routes

- [ ] Create `src/compgraph/api/routes/auth.py` — invite endpoint
- [ ] Add auth router to FastAPI app in `main.py`
- [ ] Add `Depends(require_auth)` to existing read-only endpoints
- [ ] Add `Depends(require_admin)` to pipeline control endpoints

### Database

- [ ] Verify `users` table schema matches auth needs (has `role`, `email`, `invited_by`)
- [ ] Migration: add Supabase user UUID column if needed for cross-referencing
- [ ] Optional: Create Custom Access Token Hook function in Supabase SQL Editor
- [ ] Optional: Enable hook in Dashboard > Authentication > Hooks

### Frontend (Next.js — M7)

- [ ] Install `@supabase/supabase-js`
- [ ] Create auth context/provider with session management
- [ ] Create login page (email + password)
- [ ] Create invite acceptance/callback page
- [ ] Add Authorization header to all API calls
- [ ] Handle 401 responses with automatic token refresh

### Testing

- [ ] Unit tests for `_verify_jwt` with mocked JWKS and HS256 keys
- [ ] Unit tests for `get_current_user` with mocked DB
- [ ] Unit tests for `require_admin` / `require_auth` dependencies
- [ ] Integration test: invite flow end-to-end (requires Supabase test project)
- [ ] Test expired token returns 401
- [ ] Test invalid token returns 401
- [ ] Test non-admin calling admin endpoint returns 403

### Security

- [ ] Never expose `SUPABASE_SERVICE_ROLE_KEY` to frontend
- [ ] Never log JWT tokens
- [ ] Set CORS to allow only the Next.js frontend origin (not `*`)
- [ ] Ensure JWKS cache TTL is reasonable (1 hour default; 10 min minimum during key rotation)
- [ ] Rate-limit the invite endpoint

---

## Sources

- [Supabase JWT Documentation](https://supabase.com/docs/guides/auth/jwts)
- [Supabase JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys)
- [Supabase Python Admin API](https://supabase.com/docs/reference/python/admin-api)
- [Supabase Python: invite_user_by_email](https://supabase.com/docs/reference/python/auth-admin-inviteuserbyemail)
- [Supabase Python: create_user](https://supabase.com/docs/reference/python/auth-admin-createuser)
- [Supabase Python: update_user_by_id](https://supabase.com/docs/reference/python/auth-admin-updateuserbyid)
- [Supabase Custom Claims & RBAC](https://supabase.com/docs/guides/database/postgres/custom-claims-and-role-based-access-control-rbac)
- [Supabase Custom Access Token Hook](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook)
- [Supabase Auth + FastAPI Integration (Grokipedia)](https://grokipedia.com/page/Supabase_Auth_and_FastAPI_Integration)
- [Migrating from Static JWT Secrets to JWKS in Supabase (ObjectGraph)](https://objectgraph.com/blog/migrating-supabase-jwt-jwks/)
- [Supabase Auth + Next.js + FastAPI (Medium)](https://medium.com/@ojasskapre/implementing-supabase-authentication-with-next-js-and-fastapi-5656881f449b)
- [Implementing Supabase Auth in FastAPI (Medium)](https://phillyharper.medium.com/implementing-supabase-auth-in-fastapi-63d9d8272c7b)
- [Verifying Supabase JWT Discussion](https://github.com/orgs/supabase/discussions/20763)
- [FastAPI Security/JWT Tutorial](https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/security/oauth2-jwt.md)
- [Supabase OAuth 2.1 Flows (JWKS verification example)](https://supabase.com/docs/guides/auth/oauth-server/oauth-flows)
- [FastAPI + Supabase Template (Substack)](https://euclideanai.substack.com/p/fastapi-supabase-template-for-llm)
