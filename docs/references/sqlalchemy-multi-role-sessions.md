# Async SQLAlchemy Multi-Role Factory Patterns

> Reference doc for dual-connection strategy (user-scoped RLS vs service_role bypass) in async SQLAlchemy 2.0 + FastAPI.
> Researched: 2026-02-24. CompGraph auth implementation context.

## Quick Reference

| Approach | Use Case | RLS | Pool Count | Complexity |
|----------|----------|-----|------------|------------|
| **Separate engines** | Distinct connection strings per role | Per-engine | 2 | Low |
| **Single engine + SET LOCAL ROLE** | Same connection string, switch per-txn | Per-transaction | 1 | Medium |
| **Single engine + SET LOCAL claims** | Pass JWT claims into RLS policies | Per-transaction | 1 | Medium |

**Recommended for CompGraph:** Separate engines (approach 1). Service-role engine for background jobs (scraper, enrichment, aggregation). User-scoped engine for API requests with `SET LOCAL` JWT claims per transaction.

---

## Architecture

```
API Requests ──► user_engine (pooler, RLS enforced)
                   └─ SET LOCAL request.jwt.claims = '{...}'
                   └─ SET LOCAL ROLE authenticated

Background Jobs ──► service_engine (pooler, RLS bypassed)
  (scraper,          └─ connects as service_role / postgres
   enrichment,       └─ no SET LOCAL needed
   aggregation)
```

---

## Implementation

### 1. Dual Engine Setup (`db/session.py`)

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from compgraph.config import settings

_common_args = dict(
    pool_pre_ping=True,
    connect_args={"ssl": "require"},
)

# Service engine — used by background jobs, bypasses RLS
service_engine = create_async_engine(
    settings.database_url,  # service_role connection string
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    **_common_args,
)

# User engine — used by API, enforces RLS
user_engine = create_async_engine(
    settings.database_url_user,  # anon/authenticated role connection
    pool_size=5,        # smaller pool — API traffic only
    max_overflow=3,
    **_common_args,
)

service_session_factory = async_sessionmaker(
    service_engine, class_=AsyncSession, expire_on_commit=False,
)
user_session_factory = async_sessionmaker(
    user_engine, class_=AsyncSession, expire_on_commit=False,
)
```

### 2. JWT Claims Injection via Event Hook

```python
import json
from sqlalchemy import event, text
from sqlalchemy.orm import sessionmaker

# Create sync session class to attach events (required for async)
_sync_user_session_class = sessionmaker()
user_session_factory = async_sessionmaker(
    user_engine,
    class_=AsyncSession,
    sync_session_class=_sync_user_session_class,
    expire_on_commit=False,
)

@event.listens_for(_sync_user_session_class, "after_begin")
def _set_rls_context(session, transaction, connection):
    """Inject JWT claims into the Postgres session for RLS policies."""
    jwt_claims = getattr(session.info, "jwt_claims", None)
    if jwt_claims:
        # SET LOCAL scoped to current transaction only — auto-resets on COMMIT/ROLLBACK
        connection.execute(
            text("SET LOCAL request.jwt.claims = :claims"),
            {"claims": json.dumps(jwt_claims)},
        )
        connection.execute(text("SET LOCAL ROLE authenticated"))
```

### 3. FastAPI Dependencies (`api/deps.py`)

```python
from collections.abc import AsyncGenerator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from compgraph.db.session import service_session_factory, user_session_factory

async def get_service_db() -> AsyncGenerator[AsyncSession, None]:
    """Service-role session — background jobs only. Never use in API routes."""
    async with service_session_factory() as session:
        yield session

async def get_user_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """User-scoped session with RLS. Injects JWT claims from auth middleware."""
    async with user_session_factory() as session:
        # Attach JWT claims from auth middleware (set by verify_jwt dependency)
        jwt_claims = getattr(request.state, "jwt_claims", None)
        if jwt_claims:
            session.info["jwt_claims"] = jwt_claims
        yield session
```

### 4. Route Usage

```python
from fastapi import APIRouter, Depends
from compgraph.api.deps import get_user_db
from compgraph.api.auth import require_auth  # JWT verification dependency

router = APIRouter()

@router.get("/postings")
async def list_postings(
    user=Depends(require_auth),
    db: AsyncSession = Depends(get_user_db),
):
    # RLS automatically filters rows based on JWT claims
    result = await db.execute(select(Posting))
    return result.scalars().all()
```

### 5. Background Job Usage

```python
# In scraper/enrichment/aggregation orchestrators:
from compgraph.db.session import service_session_factory

async def run_enrichment_batch():
    async with service_session_factory() as session:
        # Full access — no RLS restrictions
        postings = await fetch_unenriched(session)
        ...
```

---

## Preventing Factory Leakage

| Rule | Enforcement |
|------|-------------|
| API routes never import `service_session_factory` | Ruff ban rule or code review |
| Background jobs never import `get_user_db` | Separate module boundaries |
| `get_service_db` is not registered as a FastAPI dependency on any router | Grep CI check |
| Type alias: `ServiceSession` vs `UserSession` | Distinct types prevent mixup |

```python
# Type aliases for clarity (db/session.py)
from typing import Annotated
from fastapi import Depends

ServiceSession = Annotated[AsyncSession, Depends(get_service_db)]
UserSession = Annotated[AsyncSession, Depends(get_user_db)]
```

Enforcement via ruff `ban-relative-imports` or a simple grep in CI:
```bash
# Fail if any API route file imports service_session_factory
rg "service_session_factory" src/compgraph/api/ && exit 1 || exit 0
```

---

## Pool Sizing

| Engine | pool_size | max_overflow | Rationale |
|--------|-----------|--------------|-----------|
| `service_engine` | 10 | 5 | Enrichment runs 5 concurrent tasks; scraper bursts |
| `user_engine` | 5 | 3 | API traffic is low (internal tool); grows with users |

Both engines share the Supabase pooler (PgBouncer in session mode). Total connections = `pool_size + max_overflow` per engine. Supabase free tier allows 60 pooled connections; Pro allows 200.

---

## Supabase-Specific Notes

- **service_role key** in connection string: bypasses RLS entirely. Use for the `service_engine`.
- **anon key** + `SET LOCAL ROLE authenticated`: enforces RLS. The `after_begin` hook sets `request.jwt.claims` so RLS policies can call `current_setting('request.jwt.claims', true)::json->>'sub'`.
- **`SET LOCAL` vs `SET`**: `SET LOCAL` is transaction-scoped (auto-resets on COMMIT/ROLLBACK). Safe for connection pooling — no checkin handler needed. `SET` (without LOCAL) leaks state across pooled connections.
- **Pooler mode**: Session mode (not transaction mode) required for `SET LOCAL` to work within a transaction boundary.

---

## Testing

```python
import pytest
from unittest.mock import patch

@pytest.fixture
async def user_session_with_claims(async_session):
    """Simulate authenticated user session for RLS tests."""
    async_session.info["jwt_claims"] = {
        "sub": "test-user-uuid",
        "role": "authenticated",
        "email": "test@example.com",
    }
    return async_session

@pytest.fixture
async def service_session(async_session):
    """Service-role session — no RLS context."""
    return async_session

async def test_rls_filters_by_user(user_session_with_claims):
    """Verify RLS policy restricts rows to the authenticated user."""
    # Insert rows owned by different users, assert only matching rows returned
    ...

async def test_service_session_sees_all(service_session):
    """Verify service session bypasses RLS."""
    ...
```

---

## Migration Path (CompGraph)

1. **Now:** Single `engine` + `async_session_factory` + `get_db()` (no RLS).
2. **M7 Auth:** Rename current engine to `service_engine`. Add `user_engine` + `user_session_factory`. Add `after_begin` hook. Update API deps.
3. **Gradual:** Keep `get_db()` as alias for `get_service_db()` during transition. Deprecate once all routes use `get_user_db()`.

---

## Gotchas & Limitations

- **Event hooks must attach to sync session class**, not `async_sessionmaker`. Use `sync_session_class=` parameter.
- **`SET LOCAL` requires a transaction**: Auto-commit mode skips the hook. Always use `async with session.begin():` or rely on the session's default transaction.
- **Connection pool state leak**: If using `SET` (not `SET LOCAL`), you MUST add a `@event.listens_for(engine.sync_engine, "checkin")` handler to `RESET ROLE`. Prefer `SET LOCAL` to avoid this entirely.
- **Two pools = double memory**: Each engine maintains its own connection pool. Size conservatively — CompGraph traffic doesn't justify large pools.
- **Supabase IPv6 DNS**: `user_engine` and `service_engine` should both use the session-mode pooler URL, not direct connection (same as current setup).

---

## Sources

- [SQLAlchemy 2.0 Async I/O docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy `after_begin` event discussion (#10469)](https://github.com/sqlalchemy/sqlalchemy/discussions/10469)
- [Supabase Row Level Security docs](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase Postgres Roles docs](https://supabase.com/docs/guides/database/postgres/roles)
- [SQLAlchemy connection pooling with multiple roles (Google Groups)](https://groups.google.com/g/sqlalchemy/c/ppFcBCu9Vy0)
- [PostgREST auth: SET LOCAL request.jwt.claims](https://docs.postgrest.org/en/v12/references/auth.html)
