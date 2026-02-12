# CompGraph

Competitive intelligence platform for Mosaic Sales Solutions. Scrapes job postings from competing field marketing agencies, enriches with LLM, and surfaces hiring velocity, brand relationships, pay benchmarks, and posting lifecycle metrics.

## Pre-Session Validation

Before starting any work that uses external APIs, validate all API keys by making a lightweight test call. If any key is invalid, report it immediately and stop — do not attempt to proceed with broken credentials. Check API keys, database connections, and MCP server connectivity.

## Hook Safety

All stop hooks and pre-tool hooks MUST have a fallback/escape condition. Never create hooks that can infinite-loop on external API failures. If an external tool call fails 3 times, log the error and exit gracefully instead of retrying.

### Pre-tool Hook Patterns

The .env pattern match in pre-tool hooks should exclude .env.tpl and .env.example files. Use exact match for `.env` rather than substring matching to avoid blocking template files.

## Stack

- **Python 3.12+** with **uv** package manager
- **FastAPI** (async) — `src/compgraph/main.py`
- **SQLAlchemy 2.0** (async) + **asyncpg** — models in `src/compgraph/db/models.py`
- **Alembic** — migrations in `alembic/`
- **Supabase** — managed Postgres
- **pydantic-settings** — config from `.env`

## Key Files

- `docs/compgraph-product-spec.md` — full product specification
- `src/compgraph/main.py` — FastAPI app with lifespan
- `src/compgraph/config.py` — Settings class (DATABASE_URL, ANTHROPIC_API_KEY, etc.)
- `src/compgraph/db/models.py` — all SQLAlchemy models (dimension, fact, aggregation, auth)
- `src/compgraph/db/session.py` — async engine + session factory
- `src/compgraph/api/deps.py` — FastAPI dependency injection (get_db)
- `src/compgraph/api/routes/health.py` — health check endpoint

## Commands

```bash
uv sync                                          # Install dependencies
uv run compgraph                                 # Run dev server (0.0.0.0:8000)
uv run alembic upgrade head                      # Run migrations
uv run alembic revision --autogenerate -m "msg"  # Generate migration
uv run pytest                                    # Run tests
```

## Deployment

Dev server runs on a Linux server on the local network. Binds to `0.0.0.0:8000` by default (configurable via `HOST`/`PORT` env vars). Access from any machine on the LAN at `http://<linux-server-ip>:8000`.

## Conventions

- UUIDs for all primary keys
- Append-only data model — never mutate historical records
- All timestamps use timezone-aware datetime
- Async everywhere (engine, sessions, endpoints)
- Module path for uvicorn: `compgraph.main:app`

## Development Environment

### Python Environment

Use Python 3.13 for virtual environments (not 3.14). Always verify Python version compatibility with project dependencies (especially crewai) before creating venvs.

## Git Workflow

### Git Worktree Setup

When setting up git worktrees: 1) Create venv with Python 3.13, 2) Install all dependencies, 3) Run full test suite to verify baseline, 4) Ensure pre-push hooks have access to the worktree's venv. Use --no-verify for markdown-only pushes if hooks fail on missing deps.

## Code Standards

### Scaffolding Standards

When scaffolding a new project or module, always create fully-implemented files with real logic — never create empty stub files. If the full implementation isn't possible yet, add TODO comments with specific descriptions of what's needed.
