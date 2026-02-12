# Alembic Migrations on Supabase: Practitioner Patterns

> Source: Compass research report (Feb 2026). Covers connection pitfalls, schema isolation, pool config, and AI agent safety for Alembic + async SQLAlchemy + asyncpg on Supabase Postgres.

## Section Index

| Section | Load when |
|---------|-----------|
| §1 Connection Strings | Setting up DATABASE_URL, configuring alembic/env.py |
| §2 Schema Isolation | Configuring autogenerate, auth.users FK, RLS policies |
| §3 Pool Configuration | Tuning SQLAlchemy pool for free tier limits |
| §4 Migration Safety | Hooks, linting, stairway tests for AI-assisted migrations |

---

## §1 Connection Strings

### Supabase's Three Connection Types

| Type | Port | Host | Use For | asyncpg Safe? |
|------|------|------|---------|:---:|
| **Direct** | 5432 | `db.[PROJECT].supabase.co` | Migrations, DDL | Yes |
| **Supavisor transaction mode** | 6543 | `aws-0-[region].pooler.supabase.com` | **NEVER for migrations** | No — breaks prepared statements |
| **Supavisor session mode** | 5432 | `aws-0-[region].pooler.supabase.com` | App traffic (IPv4-friendly) | Yes |

### The asyncpg + Transaction Mode Crash

Supavisor transaction mode causes `DuplicatePreparedStatementError` with asyncpg. The pooler doesn't support prepared statements. If forced to use it, disable caching:

```python
# ONLY if you must use transaction mode (port 6543) — avoid for migrations
engine = create_async_engine(
    url,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)
```

### Two Environment Variables Pattern (recommended)

```bash
# .env
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres  # session mode, for app
DATABASE_URL_DIRECT=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres  # direct, for migrations
```

**Direct connections resolve IPv6 only (since Jan 2024)** — breaks most CI/CD. Use session mode pooler for CI, direct for local dev.

### alembic/env.py Connection Override

```python
from compgraph.config import settings

def run_migrations_online():
    # Prefer direct connection for migrations, fall back to pooled
    url = getattr(settings, "DATABASE_URL_DIRECT", None) or settings.DATABASE_URL
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    # ...
```

---

## §2 Schema Isolation

### The April 2025 Schema Lockout

Supabase restricted access to `auth`, `storage`, `realtime` schemas. Alembic autogenerate detects these schemas and generates migrations that change object ownership — permanently locking you out.

### Required: `include_name` Filter in env.py

```python
def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in ["public"]  # ONLY manage public schema
    return True

# In run_migrations_online():
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_name=include_name,
    # ...
)
```

### Foreign Keys to auth.users

Three approaches for the `users` table FK to Supabase auth:

1. **Reflect auth schema** — use `sqlacodegen` to generate the auth.users model, import it
2. **Dashboard-only FK** — define the FK in Supabase dashboard, not in SQLAlchemy models (CompGraph approach: users table is standalone, no FK to auth.users in ORM)
3. **Raw SQL migration** — add FK via `op.execute()` in Alembic migration, not in model definition

### RLS Policies, Triggers, Functions

Alembic autogenerate **cannot detect** RLS policies, triggers, or database functions. Handle via raw SQL in migrations:

```python
def upgrade():
    op.execute("""
        ALTER TABLE postings ENABLE ROW LEVEL SECURITY;
        CREATE POLICY "postings_read" ON postings
            FOR SELECT USING (true);
    """)
```

Supabase guideline: enable RLS on every table, even public ones. Use granular per-operation, per-role policies.

---

## §3 Pool Configuration

### Free Tier Limits

Supabase free tier: **15 concurrent connections**. Budget across:
- Alembic migrations: `pool_size=1, max_overflow=0` (runs sequentially)
- App (FastAPI): `pool_size=5, max_overflow=5` (10 max)
- Background jobs (scraper/enrichment): share app pool or separate with `pool_size=2`

### Alembic Pool Config

```python
# alembic/env.py — use NullPool for migrations (one-shot connection)
connectable = create_async_engine(url, poolclass=pool.NullPool)
```

### App Pool Config (avoid NullPool)

NullPool for app traffic causes **26x latency penalty** (benchmarked: 0.15s PostgREST vs 3.97s NullPool). Use:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,      # Recycle connections every 5 min
    pool_pre_ping=True,    # Verify connection health before use
)
```

---

## §4 Migration Safety

### Hooks > CLAUDE.md Rules

CLAUDE.md rules are advisory — agents can override them. **Hooks are enforced constraints.** For migration protection:

```json
// .claude/settings.json — PreToolUse hook
{
  "type": "command",
  "command": "echo 'Review migration before applying'",
  "event": "PreToolUse",
  "pattern": "alembic/versions"
}
```

### Stairway Test Pattern

Test every migration is reversible: `upgrade → downgrade → upgrade`. Catches orphaned types and irreversible operations.

```python
def test_stairway(alembic_runner):
    """Ensure all migrations can upgrade and downgrade cleanly."""
    alembic_runner.migrate_up_to("head")
    alembic_runner.migrate_down_to("base")
    alembic_runner.migrate_up_to("head")
```

### CI Linting

**Squawk** (Rust-based PostgreSQL migration linter) detects:
- Non-concurrent index creation (locks table)
- Missing `NOT VALID` on constraint additions
- Dangerous column drops

Available as GitHub Action, posts results as PR comments.

### AI Agent Safety Checklist

1. Never give agents unsupervised write access to production DB
2. Use `NullPool` + direct connection for migration runs (isolated, single-use)
3. Filter schemas in autogenerate (`include_name`)
4. Review generated migrations before `alembic upgrade head`
5. Add nullable columns first, populate, then add constraints (safe migration pattern)
6. Never delete columns in the same migration that removes code using them
