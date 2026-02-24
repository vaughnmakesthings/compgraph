# CompGraph: Competitive Intelligence Platform

CompGraph is a high-performance intelligence platform built for field marketing agencies. It monitors competitor hiring activity by scraping job postings, enriching them with LLMs (Anthropic Haiku & Sonnet), and surfacing insights via a Next.js dashboard.

## Project Overview

- **Purpose**: Track competitor hiring velocity, brand relationships, pay benchmarks, and posting lifecycles.
- **Architecture**: `Scrape → Enrich (2-pass LLM) → Aggregate (Materialized) → API (Read-only)`
- **Core Stack**: 
  - **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (Async), Alembic, APScheduler v4.
  - **Frontend**: Next.js 15+, Tailwind CSS, TypeScript, Recharts, AG Grid.
  - **Database**: Supabase (Postgres 17).
  - **LLM**: Anthropic (Haiku for classification, Sonnet for entity resolution).

## Getting Started

### Backend Setup
```bash
uv sync                                 # Install dependencies
bash scripts/setup-hooks.sh             # Install git hooks
uv run compgraph                        # Start dev server (0.0.0.0:8000)
uv run preflight                        # Validate environment
```

### Database Management
```bash
# Requires 1Password for secrets (op run)
op run --env-file=.env -- uv run alembic upgrade head                      # Run migrations
op run --env-file=.env -- uv run alembic revision --autogenerate -m "msg"  # New migration
```

### Frontend Setup
```bash
cd web
npm install
npm run dev                             # Start Next.js dev server
```

### Testing
```bash
uv run pytest                           # Run all unit tests (DB-free)
uv run pytest -m integration            # Run integration tests (Live DB required)
cd web && npm test                      # Run frontend Vitest suite
```

## Project Structure

- `src/compgraph/`: Core backend logic.
  - `api/`: FastAPI routes and dependencies.
  - `db/`: SQLAlchemy models and session management.
  - `scrapers/`: ATS-specific adapters (iCIMS, Workday).
  - `enrichment/`: 2-pass LLM enrichment logic and entity resolution.
  - `aggregation/`: Logic for rebuilding materialized aggregation tables.
- `web/`: Next.js frontend application.
- `scripts/`: Data maintenance, backfills, and market normalization.
- `docs/`: Comprehensive project documentation (design, roadmap, secrets).
- `infra/`: Deployment configurations for Digital Ocean and Caddy.
- `alembic/`: Database migration history.

## Development Conventions

- **Async First**: All database and network I/O in Python must be asynchronous.
- **Data Integrity**: 
  - `postings` and `posting_snapshots` are strictly **append-only**.
  - UUIDs (v4) are used for all primary keys.
  - Aggregation tables use a **truncate-and-insert** pattern for daily updates.
- **UI/UX Guidelines**: 
  - Adhere to the brand palette; avoid AI-default colors (purple/indigo/cyan).
  - Use data-dense layouts instead of generic SaaS templates.
  - Icons must serve a functional purpose, not just visual filler.
- **Security**: 
  - Secrets are managed via 1Password. Use the `op run` prefix for sensitive commands.
  - Supabase Auth is used for user management and access control.
- **Git Workflow**: 
  - Never merge to `main` without passing CI (Ruff, MyPy, Pytest).
  - Squash-merge PRs and rebase feature branches frequently.

## Key Design Patterns

- **Adapter Pattern**: Scrapers share a common interface but are isolated by company to prevent cross-contamination.
- **Two-Pass Enrichment**: Pass 1 (Haiku) handles cost-effective classification; Pass 2 (Sonnet) handles complex entity extraction and fuzzy matching.
- **Three-Tier Entity Resolution**: Exact slug matching → Normalized name matching → Fuzzy matching (RapidFuzz).
- **Session-Mode Pooler**: Use the Supabase pooler for application traffic; use direct connections only for migrations.

## Code Search Protocol

This project is indexed by **codesight** (semantic code search). When exploring the codebase:
1.  **Semantic Queries**: For behavioral queries (e.g., "how is auth handled?") use `search_code` first.
2.  **Keyword Search**: For exact names or keywords, use standard Grep.
3.  **Two-Stage Retrieval**: Always call `search_code` first, then expand the top 2-3 results with `get_chunk_code` to save context tokens.
4.  **Index Staleness**: If `get_indexing_status` shows `is_stale: true`, run `index_codebase` to refresh the semantic index.

For detailed design specifications, refer to `docs/design.md`. For the current development status, see `docs/phases.md`.
