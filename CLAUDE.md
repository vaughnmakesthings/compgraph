# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CompGraph — competitive intelligence platform for Mosaic Sales Solutions. Scrapes job postings from 4 competing field marketing agencies, enriches with LLM, and surfaces hiring velocity, brand relationships, pay benchmarks, and posting lifecycle metrics.

## Commands

```bash
# Setup
uv sync                                           # Install dependencies
bash scripts/setup-hooks.sh                        # Install git hooks

# Dev server
uv run compgraph                                   # Run dev server (0.0.0.0:8000)
op run --env-file=.env -- uv run compgraph         # Run with 1Password secrets

# Database
op run --env-file=.env -- uv run alembic upgrade head                      # Run migrations
op run --env-file=.env -- uv run alembic revision --autogenerate -m "msg"  # Generate migration

# Tests
uv run pytest                                      # All unit tests (no DB required)
uv run pytest tests/test_preflight.py              # Single test file
uv run pytest -k "test_health"                     # Single test by name
uv run pytest -m integration                       # Integration tests (needs DB)
uv run pytest --no-cov                             # Skip coverage enforcement

# Lint & typecheck
uv run ruff check src/ tests/                      # Lint
uv run ruff format src/ tests/                     # Format
uv run mypy src/compgraph/                         # Typecheck

# Preflight
uv run preflight                                   # Validate environment before work
```

**Secrets**: All secrets managed via 1Password. Use `op run --env-file=.env --` prefix for any command that needs DATABASE_PASSWORD or ANTHROPIC_API_KEY. See `docs/secrets-reference.md`.

## Stack

- **Python 3.12+** / **uv** — use Python 3.13 for venvs (not 3.14)
- **FastAPI** (async) — `src/compgraph/main.py`, module path: `compgraph.main:app`
- **SQLAlchemy 2.0** (async) + **asyncpg** — models in `src/compgraph/db/models.py`
- **Alembic** — migrations in `alembic/`, async engine, SSL required
- **Supabase** — managed Postgres 17, project ref `tkvxyxwfosworwqxesnz`
- **pydantic-settings** — config from `.env` via `src/compgraph/config.py`

## Architecture

```
Scrape (4 ATS) → Enrich (2-pass LLM) → Aggregate (materialized) → API (read-only)
```

- **Scrape**: 4 adapters (iCIMS×2, Workday CXS×2). Each isolated — one failing doesn't block others. Output: `postings` + `posting_snapshots` (append-only).
- **Enrich**: 2-pass — Haiku for classification/pay extraction, Sonnet for entity extraction. Output: `posting_enrichments` + `posting_brand_mentions`.
- **Aggregate**: Rebuilds 4 tables (`agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle`) from source data via truncate+insert.
- **API**: Async FastAPI, read-only queries against aggregation tables. No writes from API layer.

### Database Schema (13 tables)

| Tier | Tables | Purpose |
|------|--------|---------|
| **Dimension** | `companies`, `brands`, `retailers`, `markets` | Reference data, slowly changing |
| **Fact** | `postings`, `posting_snapshots`, `posting_enrichments`, `posting_brand_mentions` | Append-only event data |
| **Aggregation** | `agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle` | Pre-computed dashboard metrics |
| **Auth** | `users` | Invite-only access control |

### Key Design Decisions

- **Append-only** — never UPDATE/DELETE fact tables. Snapshots accumulate. Enrichments are versioned.
- **Per-company adapter isolation** — scrapers share an interface but run independently.
- **Sequential pipeline stages** — scrape completes before enrichment starts. Parallelism is WITHIN stages, not between.
- **UUID PKs everywhere** — no serial IDs.
- **Session mode pooler** for app traffic (IPv4-safe), direct connection for Alembic migrations only.

## Conventions

- All database operations must be async. No sync SQLAlchemy calls anywhere.
- No mutable operations on `posting_snapshots` or `posting_enrichments` — append-only.
- All timestamps use timezone-aware datetime (`DateTime(timezone=True)`).
- UUIDs for all primary keys (`UUID(as_uuid=True)`, `default=uuid.uuid4`).
- FastAPI dependency injection via `get_db()` in `src/compgraph/api/deps.py`.

## Tests

Two tiers in `tests/conftest.py`:
- **Unit fixtures** (`client`, `settings_override`): no DB, run everywhere. `DATABASE_PASSWORD` gets a placeholder.
- **Integration fixtures** (`async_session`, `seeded_db`): require live Supabase. Marked `@pytest.mark.integration`, skipped by default.

Integration tests use transaction rollback isolation — each test gets a fresh session that rolls back after completion.

Coverage threshold: 50% minimum enforced via `--cov-fail-under=50`.

## Alembic

- Only manages `public` schema — `include_name` filter in `alembic/env.py` excludes Supabase-managed schemas (`auth`, `storage`, `realtime`, `extensions`).
- Always requires `ssl=require` in connection args.
- Autogenerated migrations go to `alembic/versions/` — exempt from strict ruff rules via `pyproject.toml` per-file-ignores.
- Needs live DB connection: use `op run --env-file=.env --` prefix.

## Common Pitfalls

- Don't mutate `posting_snapshots` — always INSERT new rows, never UPDATE.
- Don't load all of `docs/design.md` at once — use section references (§1-§10), see `docs/context-packs.md`.
- Don't hardcode iCIMS page sizes — they vary per company.
- Don't assume Workday CXS API is stable — it's undocumented.
- Don't skip the enrichment 2-pass pattern — Haiku alone misses edge cases, Sonnet alone is too expensive.

## Deployment

Dev server runs on a Raspberry Pi (Debian 13 Trixie / DietPi, aarch64) at `192.168.1.69`.

- **SSH**: `ssh compgraph-dev` (alias in `~/.ssh/config`, uses 1Password SSH agent)
- **Service**: `systemctl {start|stop|restart|status} compgraph`
- **Logs**: `journalctl -u compgraph -f`
- **Health**: `http://192.168.1.69:8000/health`
- **Deploy**: `ssh compgraph-dev "cd /opt/compgraph && git pull && source /root/.local/bin/env && uv sync && systemctl restart compgraph"`

## Git Workflow

- Never merge a PR until ALL CI checks pass. Poll `gh pr checks <number>` if unsure.
- Git hooks: pre-commit (ruff check+format), pre-push (pytest). Install via `bash scripts/setup-hooks.sh`.
- Only use `--no-verify` for documentation-only pushes with explicit justification.

## Pre-Session Validation

Before starting work with external APIs, validate API keys with a lightweight test call. If invalid, stop immediately — do not retry in a loop.

## Hook Safety

All hooks MUST have a fallback/escape condition. If an external tool call fails 3 times, exit gracefully. The `.env` pattern in pre-tool hooks uses exact match to avoid blocking `.env.example`.

## Context Loading

Read `docs/changelog.md` (latest entry only) for session continuity. Load context packs from `docs/context-packs.md` based on task type. Never load all of `docs/design.md` at once (~5.5K tokens).

## Agent Crew

Project-level agents in `.claude/agents/` have deep CompGraph context:
- `python-backend-developer` — implementation (scrapers, enrichment, aggregation, API)
- `code-reviewer` — quality gate (plan alignment, async patterns, append-only rules)
- `pytest-validator` — test audit (hollow assertions, DB isolation)
- `spec-reviewer` — scope gate (goal achievement vs product spec)

Review sequence: implement → `code-reviewer` → `pytest-validator` → `spec-reviewer`

## Code Standards

When scaffolding new modules, create fully-implemented files — never empty stubs. Use TODO comments with specific descriptions for deferred work.
