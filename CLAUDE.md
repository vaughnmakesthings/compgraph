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

# Enrichment
op run --env-file=.env -- uv run python scripts/backfill_enrichment.py          # Run full backfill
op run --env-file=.env -- uv run python scripts/backfill_enrichment.py --dry-run  # Count only
op run --env-file=.env -- uv run python scripts/validate_enrichment.py          # Spot-check CSV

# Preflight
uv run preflight                                   # Validate environment before work

# Dashboard
op run --env-file=.env -- uv run streamlit run src/compgraph/dashboard/main.py  # Local (:8501)
```

**Secrets**: All secrets managed via 1Password. Use `op run --env-file=.env --` prefix for any command that needs DATABASE_PASSWORD or ANTHROPIC_API_KEY. See `docs/secrets-reference.md`.

## Stack

- **Python 3.12+** / **uv** — use Python 3.13 for venvs (not 3.14)
- **FastAPI** (async) — `src/compgraph/main.py`, module path: `compgraph.main:app`
- **SQLAlchemy 2.0** (async) + **asyncpg** — models in `src/compgraph/db/models.py`
- **Alembic** — migrations in `alembic/`, async engine, SSL required
- **Supabase** — managed Postgres 17, project ref `tkvxyxwfosworwqxesnz`
- **pydantic-settings** — config from `.env` via `src/compgraph/config.py`
- **anthropic** — AsyncAnthropic client for LLM enrichment (Haiku + Sonnet)
- **rapidfuzz** — fuzzy string matching for entity resolution
- **python-slugify** — slug generation for brand/retailer matching

## Architecture

```
Scrape (4 ATS) → Enrich (2-pass LLM) → Aggregate (materialized) → API (read-only)
```

- **Scrape**: 4 adapters (iCIMS×2, Workday CXS×2). Each isolated — one failing doesn't block others. Output: `postings` + `posting_snapshots` (append-only).
- **Enrich**: 2-pass — Haiku 4.5 for classification/pay extraction (Pass 1), Sonnet 4.5 for entity extraction (Pass 2). 3-tier entity resolution (exact/slug/fuzzy via rapidfuzz). Fingerprinting for repost detection. Output: `posting_enrichments` + `posting_brand_mentions`.
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
- Enrichment Pass 2 completion tracked via `enrichment_version` column containing "pass2" (not PostingBrandMention existence).
- Entity resolution uses savepoints (`begin_nested()`) for concurrent-safe creation.
- Anthropic SDK types (`MessageParam`) imported under `TYPE_CHECKING` guard, used via `cast()` at runtime.

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
- URL-encode special characters in `DATABASE_PASSWORD` (e.g., `@` → `%40`) — asyncpg will reject unencoded URLs.
- If direct connection DNS fails (IPv6 issues), use the session-mode pooler URL instead (`DATABASE_URL` vs `DATABASE_URL_DIRECT`).
- `DATABASE_URL_DIRECT` is for Alembic migrations only — all app traffic goes through the pooler.

## Common Pitfalls

- Don't mutate `posting_snapshots` — always INSERT new rows, never UPDATE.
- Don't load all of `docs/design.md` at once — use section references (§1-§10), see `docs/context-packs.md`.
- Don't hardcode iCIMS page sizes — they vary per company.
- Don't assume Workday CXS API is stable — it's undocumented.
- Don't skip the enrichment 2-pass pattern — Haiku alone misses edge cases, Sonnet alone is too expensive.
- Don't use `session.rollback()` in entity creation — use `session.begin_nested()` savepoints to preserve prior work.
- Don't check Pass 2 completion via `PostingBrandMention` existence — use `enrichment_version` containing "pass2".
- Don't add MCP servers to `.mcp.json` that are already provided by plugins — this causes ~10K tokens of context waste and auth warnings. Plugins are the authoritative source.
- Don't forget `exclude_ids` for failed postings in batch loops — prevents livelock on persistent failures.

## Platform Gotchas

- **macOS `find`**: Use `fd` or `Glob` tool instead — macOS `find` has different flag syntax than GNU `find` (e.g., `-regex` behavior differs).
- **Docker**: Requires OrbStack on macOS dev machines (not Docker Desktop). The GitHub MCP server is a Go-based Docker image, not an npm package.
- **`claude plugins uninstall`**: Unreliable — may silently fail. Verify removal by checking `~/.claude/plugins/` directly.
- **Ruff PostToolUse hook**: Strips imports it considers unused. After editing files with `TYPE_CHECKING` imports or `cast()` patterns, verify the imports survived.

## Deployment

Dev server runs on a Raspberry Pi (Debian 13 Trixie / DietPi, aarch64) at `192.168.1.69`.

- **SSH**: `ssh compgraph-dev` (alias in `~/.ssh/config`, uses 1Password SSH agent)
- **Service**: `systemctl {start|stop|restart|status} compgraph`
- **Logs**: `journalctl -u compgraph -f`
- **Health**: `http://192.168.1.69:8000/health`
- **Deploy**: `ssh compgraph-dev "cd /opt/compgraph && git pull && source /root/.local/bin/env && uv sync && systemctl restart compgraph"`

### Dashboard
- **URL**: `http://192.168.1.69:8501`
- **Service**: `systemctl {start|stop|restart|status} compgraph-dashboard`
- **Logs**: `journalctl -u compgraph-dashboard -f`

## Git Workflow

- Never merge a PR until ALL CI checks pass. Poll `gh pr checks <number>` if unsure.
- Git hooks: pre-commit (ruff check+format), pre-push (pytest). Install via `bash scripts/setup-hooks.sh`.
- Only use `--no-verify` for documentation-only pushes with explicit justification.

## Pre-Session Validation

Before starting work with external APIs, validate API keys with a lightweight test call. If invalid, stop immediately — do not retry in a loop.

## Hook Safety

All hooks MUST have a fallback/escape condition. If an external tool call fails 3 times, exit gracefully. The `.env` pattern in pre-tool hooks uses exact match to avoid blocking `.env.example`.

## Background Tasks & Sub-Agents

- Clean up stale background tasks before starting new orchestrator runs.
- When spawning sub-agents or orchestrator pipelines, check for duplicate/orphaned processes first.
- Do not improvise if a skill or resource is missing — ask the user or pull the latest from main before proceeding.
- If a background agent has not produced output in 10 minutes, consider it stale and report to the user.

## CodeSight (Semantic Code Search)

The project is indexed with CodeSight MCP for semantic search across code and docs.

**MANDATORY: Before ANY CodeSight search**, call `get_indexing_status(project="compgraph")`. If `is_stale: true`, reindex first:
```
index_codebase(project_path="/Users/vmud/Documents/dev/projects/compgraph", project_name="compgraph")
```
This is incremental (~2-4s) and skips unchanged files. Never search a stale index.

**Two-stage retrieval pattern:**
1. `search_code(query, project="compgraph")` — returns metadata only (~40 tokens/result)
2. `get_chunk_code(chunk_ids, include_context=True)` — expands relevant results with full source

**Useful filters:**
- `symbol_type="function"|"class"|"method"` — narrow to code symbols
- `file_pattern="src/compgraph/scrapers/"` — scope to directory
- `file_pattern="docs/"` — search design docs, research, and plans

**Indexed content:** All Python source, tests, and docs (design.md, product-spec, plans/, references/, failure-patterns, etc.). Research findings and architecture decisions are searchable alongside implementation code.

**When to use:** Prefer CodeSight over speculative file reads when exploring unfamiliar areas or when subagents need targeted context without loading entire files.

## Context Loading

Read `docs/changelog.md` (latest entry only) for session continuity. Load context packs from `docs/context-packs.md` based on task type. Never load all of `docs/design.md` at once (~5.5K tokens).

## Session Discipline

- Spend no more than 30% of session effort on codebase exploration before producing actionable output (plan, code, or specific questions).
- If the user interrupts or redirects, immediately pivot — do not continue the current exploration path.
- Every exploration phase must end with a concrete deliverable: a bullet-point summary, a proposed approach, or a direct question.

## Agent Crew

Project-level agents in `.claude/agents/` have deep CompGraph context:
- `python-backend-developer` — implementation (scrapers, enrichment, aggregation, API)
- `code-reviewer` — quality gate (plan alignment, async patterns, append-only rules)
- `pytest-validator` — test audit (hollow assertions, DB isolation)
- `spec-reviewer` — scope gate (goal achievement vs product spec)

Review sequence: implement → `code-reviewer` → `pytest-validator` → `spec-reviewer`

## Code Standards

When scaffolding new modules, create fully-implemented files — never empty stubs. Use TODO comments with specific descriptions for deferred work.

## Session Wrap-Up

Before ending a non-trivial session, write a structured summary instead of running parallel observer agents:
- Use `claude-mem save_memory` (if available) or append to `docs/changelog.md`
- Include: date, goal, files changed, key decisions, and open questions
- Keep summaries concise — 5-10 lines maximum
- This replaces the need for dedicated observer agent sessions
