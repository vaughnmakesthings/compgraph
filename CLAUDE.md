# CompGraph

Competitive intelligence platform for Mosaic Sales Solutions. Scrapes job postings from competing field marketing agencies, enriches with LLM, and surfaces hiring velocity, brand relationships, pay benchmarks, and posting lifecycle metrics.

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
