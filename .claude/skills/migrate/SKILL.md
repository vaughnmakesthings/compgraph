---
name: migrate
description: Generate or apply Alembic migrations with safety checks for Supabase
disable-model-invocation: true
---

# Alembic Migration Workflow

Manages Alembic migrations against the Supabase database with built-in safety checks.

## Usage

- `/migrate generate <message>` — Generate a new migration
- `/migrate apply` — Apply all pending migrations
- `/migrate status` — Show current migration state

## Pre-flight Checks (ALL commands)

1. Verify `alembic/env.py` has `include_name` filter (prevents Supabase schema corruption)
2. Verify `op` CLI is available (1Password for secrets)
3. Verify connectivity to Supabase (direct connection for DDL)

```bash
# Check include_name filter
grep -q 'include_name' alembic/env.py || { echo "ABORT: include_name filter missing"; exit 1; }

# Check 1Password CLI
command -v op >/dev/null || { echo "ABORT: 1Password CLI (op) not found"; exit 1; }
```

## Generate (`/migrate generate <message>`)

1. Run pre-flight checks
2. Generate migration with autogenerate:
   ```bash
   op run --env-file=.env -- uv run alembic revision --autogenerate -m "<message>"
   ```
3. Read the generated migration file
4. Review for:
   - No operations on `auth`, `storage`, `realtime`, `extensions` schemas
   - All PKs use `sa.UUID(as_uuid=True)` with `default=uuid.uuid4`
   - All timestamps use `DateTime(timezone=True)`
   - Index names follow convention: `ix_<table>_<column>`
5. Present the migration diff for user approval before proceeding

## Apply (`/migrate apply`)

1. Run pre-flight checks
2. Show pending migrations:
   ```bash
   op run --env-file=.env -- uv run alembic history --verbose -r current:head
   ```
3. Ask for confirmation
4. Apply:
   ```bash
   op run --env-file=.env -- uv run alembic upgrade head
   ```
5. Verify by running `alembic current`

## Status (`/migrate status`)

```bash
op run --env-file=.env -- uv run alembic current
op run --env-file=.env -- uv run alembic history --verbose -r current:head
```

## Safety Rules

- **NEVER** run `alembic downgrade` — destructive on Supabase. Create a new forward migration to revert.
- **ALWAYS** use `op run --env-file=.env --` prefix — never hardcode credentials.
- **ALWAYS** use the direct connection URL (`DATABASE_URL_DIRECT`) for DDL — pooler doesn't support DDL.
- If DNS fails (IPv6), fall back to session-mode pooler URL with explicit warning.
- URL-encode special characters in `DATABASE_PASSWORD` (e.g., `@` -> `%40`).
