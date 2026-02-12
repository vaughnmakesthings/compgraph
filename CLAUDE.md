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

## Context Loading (Quick Reference)

**Session startup:** Read `docs/changelog.md` (latest entry only) for continuity. Then load the context pack for your task from `docs/context-packs.md`.

| Task | Context Pack | Key Files | Tokens |
|------|-------------|-----------|:---:|
| Scraper adapter | Pack A | design.md §3 + §9, models.py (Posting/Snapshot) | ~3K |
| Enrichment pipeline | Pack B | design.md §4, models.py (Enrichment/BrandMention) | ~3K |
| Aggregation jobs | Pack C | design.md §5, models.py (agg_* models) | ~2K |
| API endpoints | Pack D | design.md §6, deps.py, route files | ~3K |
| Database/migrations | Pack E | design.md §7, models.py (full), session.py, alembic/ | ~3K |
| Debug pipeline | Pack F | failure-patterns.md, design.md §8, failing module | ~4K |
| Pipeline orchestration | Pack G | design.md §2 + §8, workflow.md | ~3K |
| Alert system | Pack H | design.md §10, product-spec §9 | ~1.5K |

**Rule:** Never load all of `docs/design.md` at once (~5.5K tokens). Load sections by number (§1-§10).

**Full details:** `docs/context-packs.md`

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

### CI Merge Discipline

Never merge a PR until ALL CI checks have completed and passed — including external checks (e.g., Cursor bugbot). If any check is still `pending` or `queued`, wait and poll `gh pr checks <number>` before merging. Only use `--no-verify` for documentation-only changes (markdown, comments) with explicit justification.

### Git Worktree Setup

When setting up git worktrees: 1) Create venv with Python 3.13, 2) Install all dependencies, 3) Run full test suite to verify baseline, 4) Ensure pre-push hooks have access to the worktree's venv. Use --no-verify for markdown-only pushes if hooks fail on missing deps.

## Orchestrator Process Management

Before starting a new orchestrator run or spawning background agents:
1. Check for existing orchestrator processes: `ps aux | grep claude` — kill stale ones
2. Clean up orphaned subagent sessions and stale status files in `work/`
3. Never run duplicate orchestrator instances against the same worktree
4. After completion, verify no background tasks are still running before starting new work

## Skills & Artifacts

Before improvising a workflow, check if a skill already exists:
1. Run `ls .claude/skills/` to see project-specific skills
2. Check available plugin skills via `/help` or the skill list in system context
3. Pull latest from the working branch before claiming a skill or file doesn't exist
4. If a matching skill exists, use it — don't recreate the logic inline

## Agent Crew

### Project-Level Agents (`.claude/agents/`)

These have deep CompGraph context (schema, conventions, pipeline architecture). Use for implementation and review work.

| Agent | Role | Use When |
|-------|------|----------|
| `python-backend-developer` | Implementation | Writing scrapers, enrichment, aggregation, API routes, models |
| `code-reviewer` | Quality gate | After completing a major step — checks plan alignment, async patterns, append-only rules |
| `pytest-validator` | Test audit | After code review — catches hollow assertions, missing edge cases, DB isolation issues |
| `spec-reviewer` | Scope gate | Before merge — validates goal achievement vs scope creep against product spec |

### Voltagent Subagents (via Task tool)

These are generic specialists with broad expertise but no project context. Use for targeted specialist questions.

**High-value** (use these):

| Subagent Type | Use When |
|---------------|----------|
| `voltagent-lang:python-pro` | Python 3.12+ async patterns, type system questions |
| `voltagent-data-ai:postgres-pro` | Supabase query optimization, indexing, Postgres-specific features |
| `voltagent-data-ai:prompt-engineer` | Designing 2-pass enrichment prompts (Haiku + Sonnet) |
| `voltagent-data-ai:data-engineer` | Pipeline architecture for scrape → enrich → aggregate flow |
| `voltagent-core-dev:backend-developer` | FastAPI patterns, middleware, dependency injection |
| `voltagent-qa-sec:debugger` | Diagnosing async/DB issues |

**Use sparingly** (only when specifically needed):

| Subagent Type | Use When |
|---------------|----------|
| `voltagent-data-ai:database-optimizer` | Query performance tuning |
| `voltagent-qa-sec:performance-engineer` | Bottleneck profiling |
| `voltagent-infra:deployment-engineer` | CI/CD setup |
| `voltagent-core-dev:api-designer` | REST API surface design |

**Skip**: `voltagent-domains:*`, `voltagent-biz:*`, `voltagent-meta:*`, frontend/mobile agents — not relevant to this project.

### Agent Selection Pattern

- **Implementation work** → project-level `python-backend-developer` (knows schema, conventions, pipeline)
- **Specialist questions** → voltagent agents (e.g., `postgres-pro` for index strategy, `prompt-engineer` for enrichment prompts)
- **Review gates** → project-level `code-reviewer` → `pytest-validator` → `spec-reviewer`

## Architecture Overview

### Pipeline Architecture

```
Scrape (4 ATS) → Enrich (2-pass LLM) → Aggregate (materialized) → API (read-only)
```

- **Scrape**: 4 concurrent adapters (iCIMS×2, Workday CXS×2). Each adapter is isolated — one failing doesn't block others. Output: `postings` + `posting_snapshots` (append-only).
- **Enrich**: 2-pass — Haiku for fast entity extraction, Sonnet for ambiguous cases. Output: `posting_enrichments` + `posting_brand_mentions`.
- **Aggregate**: Rebuilds 4 materialized tables (`agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle`) from source data each run.
- **API**: Async FastAPI, read-only queries against aggregation tables. No writes from API layer.

### Key Design Decisions

- **Append-only data model** — never UPDATE/DELETE historical records. Snapshots accumulate. Enrichments are versioned.
- **Per-company adapter isolation** — scrapers share an interface but run independently. A BDS failure doesn't affect Advantage.
- **Sequential pipeline stages** — scrape completes before enrichment starts. Parallelism is WITHIN stages, not between.
- **UUID PKs everywhere** — no serial IDs, enables distributed inserts.

### Common Pitfalls (avoid these)

- Don't mutate `posting_snapshots` — always INSERT new rows, never UPDATE
- Don't load all of `docs/design.md` at once — use section references (§1-§10)
- Don't hardcode iCIMS page sizes — they vary per company (BDS=50, MarketSource=20)
- Don't assume Workday CXS API is stable — it's undocumented and changes without notice
- Don't use sync SQLAlchemy — everything is async (engine, sessions, endpoints)
- Don't skip the enrichment 2-pass pattern — Haiku alone misses edge cases, Sonnet alone is too expensive

## Code Standards

### Scaffolding Standards

When scaffolding a new project or module, always create fully-implemented files with real logic — never create empty stub files. If the full implementation isn't possible yet, add TODO comments with specific descriptions of what's needed.
