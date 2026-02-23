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
```

**Secrets**: All secrets managed via 1Password. Use `op run --env-file=.env --` prefix for any command that needs DATABASE_PASSWORD or ANTHROPIC_API_KEY. See `docs/secrets-reference.md`.

### Frontend (compgraph-eval)

When working in `compgraph-eval`:

```bash
cd compgraph-eval/web
npm run lint             # ESLint strict (--max-warnings 0)
npm run typecheck        # TypeScript --noEmit
npm test                 # Vitest run
npm run test:coverage    # Vitest with v8 coverage (50% threshold)
npm run build            # Production build
```

See `compgraph-eval/CLAUDE.md` for full frontend conventions.

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
- **httpx** + **beautifulsoup4** — HTTP client + HTML parsing for scrapers
- **apscheduler** (v4 alpha) — scheduled pipeline jobs

## Architecture

```
Scrape (4 ATS) → Enrich (2-pass LLM) → Aggregate (materialized) → API (read-only)
```

- **Scrape**: 4 adapters (iCIMS×2, Workday CXS×2). Each isolated — one failing doesn't block others. Output: `postings` + `posting_snapshots` (append-only).
- **Enrich**: 2-pass — Haiku 4.5 for classification/pay extraction (Pass 1), Sonnet 4.5 for entity extraction (Pass 2). 3-tier entity resolution (exact/slug/fuzzy via rapidfuzz). Fingerprinting for repost detection. Output: `posting_enrichments` + `posting_brand_mentions`.
- **Aggregate**: Rebuilds 4 tables (`agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle`) from source data via truncate+insert.
- **Scheduler**: APScheduler v4 cron jobs trigger scrape→enrich→aggregate pipeline. Config in `src/compgraph/scheduler/`.
- **Frontend**: Next.js 16 at `web/` — Pipeline Health, Posting Explorer, Brand Intel, and Scheduler views. Deployed to Vercel.
- **API**: Async FastAPI, read-only queries against aggregation tables. No writes from API layer.

### Database Schema (13 tables)

| Tier | Tables | Purpose |
|------|--------|---------|
| **Dimension** | `companies`, `brands`, `retailers`, `markets` | Reference data, slowly changing |
| **Fact** | `postings`, `posting_snapshots`, `posting_enrichments`, `posting_brand_mentions` | Append-only event data |
| **Aggregation** | `agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle` | Pre-computed dashboard metrics |
| **Auth** | `users` | Invite-only access control |

## Roadmap

**Current:** M3 — Data Collection (~95%). Remaining: data quality review, prompt fixes, security (#130/#131).
**Next:** M4 — Aggregation & API (4 agg rebuild jobs → dashboard/detail endpoints → Supabase Auth).

**Do NOT build yet:**
- Auth (Supabase Auth, invite via magic link, password login) → M4d. Custom JWT → never.
- arq (replace APScheduler) → M6
- LiteLLM (provider abstraction) → M6 (needs LLM eval tool first)
- Digital Ocean production deploy → M7 (dev migration in M5)
- Prisma / second ORM → never (frontend is pure API consumer)

**Pre-commitments:** Aggregation = truncate+insert. API = read-only. Dashboard migration (M5) = Streamlit → API calls. Enrichment 2-pass stays. Entity resolution 3-tier stays. Auth = Supabase Auth (invite via magic link, password login, admin/user roles). Frontend = pure API consumer (Next.js calls FastAPI, no direct DB). Database = Supabase Postgres through M6.

See `docs/phases.md` for full roadmap with task tables. Load Pack R from `docs/context-packs.md` for planning sessions.

### Key Design Decisions

- **Append-only snapshots** — never UPDATE/DELETE `posting_snapshots`. Enrichments are versioned (append-only trigger removed in PR #118; prefer INSERT but UPDATEs allowed).
- **Per-company adapter isolation** — scrapers share an interface but run independently.
- **Sequential pipeline stages** — scrape completes before enrichment starts. Parallelism is WITHIN stages, not between.
- **UUID PKs everywhere** — no serial IDs.
- **Session mode pooler** for app traffic (IPv4-safe), direct connection for Alembic migrations only.

## Conventions

### Frontend Design Antipatterns

When generating or reviewing frontend code (Next.js, React, CSS), reject these AI-default patterns on sight:

**Color:**
- Don't use purple, indigo, or violet as primary/accent colors. The `bg-indigo-500` / `violet-600` / cyan palette is the #1 AI-generation tell. Use the project's defined brand palette instead.
- Don't accept gradient hero sections (especially purple→blue or purple→pink). If a gradient is needed, it must use brand colors with intentional direction and purpose.
- Don't default to Tailwind's color names without mapping them to design tokens first.

**Components & Layout:**
- Don't use the SaaS landing page template (centered hero → 3-column feature grid → CTA → footer). CompGraph is a B2B intelligence platform — use data-dense layouts.
- Don't apply uniform large border-radius (`rounded-xl`, `rounded-2xl`) to everything. Vary radius by component role: inputs, cards, buttons, and containers should have distinct radii.
- Don't add glassmorphism (backdrop-blur + transparency) to cards. Use solid backgrounds with subtle borders.
- Don't use decorative icons (Lucide/Heroicons scattered for visual filler). Every icon must communicate meaning.

**Typography & Spacing:**
- Don't default to Inter. Choose a specific font pairing with rationale (display + body).
- Don't use metronomic spacing (identical gaps everywhere). Create visual rhythm with intentional density variation — tight data sections vs. airy navigation.
- Don't use the same shadow depth on every elevated element. Define a shadow scale (sm/md/lg) and assign by component importance.

**Animation & Polish:**
- Don't add fade-in-on-scroll to every section or hover-scale to every card. Animations must serve a UX purpose (state change feedback, progressive disclosure, loading indication).
- Don't use `transition-all` — specify exact properties (`transition-colors`, `transition-opacity`).
- Don't add the ✨ sparkle icon or "AI-powered" badges. These are negative trust signals.

**Process:**
- Never accept the first AI-generated color scheme. Always override with project design tokens.
- Treat AI-generated components as wireframes, then apply intentional design decisions.
- When prompting AI tools for UI, provide: hex colors, font family, spacing scale values, border-radius values. Never say "make it modern."

Reference: `docs/references/ai-generated-design-complaints.md` for the full research behind these rules.

### Backend Conventions

- All database operations must be async. No sync SQLAlchemy calls anywhere.
- No mutable operations on `posting_snapshots` — strict append-only. `posting_enrichments` allows updates (trigger dropped in PR #118 due to iCIMS conflicts).
- All timestamps use timezone-aware datetime (`DateTime(timezone=True)`).
- UUIDs for all primary keys (`UUID(as_uuid=True)`, `default=uuid.uuid4`).
- FastAPI dependency injection via `get_db()` in `src/compgraph/api/deps.py`.
- Enrichment Pass 2 completion tracked via `enrichment_version` column containing "pass2" (not PostingBrandMention existence).
- Entity resolution uses savepoints (`begin_nested()`) for concurrent-safe creation.
- Anthropic SDK types (`MessageParam`) imported under `TYPE_CHECKING` guard, used via `cast()` at runtime.
- SQL `string_agg()` subqueries must include `ORDER BY` for deterministic results.

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
- Don't test mock behavior — test real behavior. Don't add test-only methods to production classes. Mock minimally and only after understanding the dependency chain.
- Don't create GitHub issues or TaskCreate entries without checking for duplicates first. Search existing open issues (`gh issue list`) and the current task list (`TaskList`) before creating. Never create the same task twice.

## Platform Gotchas

- **`grep` vs `rg`**: Always use the Grep tool or `rg` directly — never `grep --include` flags. The Grep tool uses ripgrep which doesn't support GNU grep flags and will silently return wrong results.
- **macOS `find`**: Use `fd` or `Glob` tool instead — macOS `find` has different flag syntax than GNU `find` (e.g., `-regex` behavior differs).
- **Docker**: Requires OrbStack on macOS dev machines (not Docker Desktop). The GitHub MCP server is a Go-based Docker image, not an npm package.
- **`claude plugins uninstall`**: Verify removal by checking `~/.claude/plugins/installed_plugins.json` directly.
- **Ruff PostToolUse hook**: Strips imports it considers unused. After editing files with `TYPE_CHECKING` imports or `cast()` patterns, verify the imports survived.
- **Skills format**: Must use `.claude/skills/<name>/SKILL.md` (directory-based, not flat files).

## Deployment

### Infrastructure Platform: Digital Ocean
- **Platform**: Digital Ocean for all production and dev infrastructure
- **CLI**: `doctl` (v1.150.0) — installed, authenticated via 1Password plugin (`op plugin run -- doctl`)
- **Management**: Use `doctl` CLI for all infrastructure operations (droplets, databases, networking, firewalls)

### Dev Server (Digital Ocean Droplet)
Dev server runs on a DO Droplet (`s-1vcpu-2gb`, sfo3, Ubuntu 24.04) at `165.232.128.28`.

- **SSH**: `ssh compgraph-do` (alias in `~/.ssh/config`, uses 1Password SSH agent)
- **Health**: `https://dev.compgraph.io/health`
- **Auto-deploy**: Merging to `main` triggers CD workflow → CI passes → SSH deploy → migrate → restart → health check
- **Manual deploy**: `bash infra/deploy.sh` (or `bash infra/deploy.sh --env-update` to push fresh secrets)
- **Service**: `systemctl {start|stop|restart|status} compgraph`
- **Logs**: `journalctl -u compgraph -f`
- **Reverse proxy**: Caddy — automatic HTTPS via Let's Encrypt, config at `/etc/caddy/Caddyfile`
- **Infra files**: `infra/` directory (systemd units, Caddyfile, setup + deploy scripts, `deploy-ci.sh` for CD)

### CD Pipeline (Auto-Deploy)
Every merge to `main` auto-deploys to the dev server via GitHub Actions:

1. CI workflow runs (lint, typecheck, test, security scan)
2. CI passes → CD workflow triggers via `workflow_run`
3. SSH to droplet → `git pull` → `uv sync` → `alembic upgrade head` → restart services → health check

- **Workflow**: `.github/workflows/cd.yml`
- **Deploy script**: `infra/deploy-ci.sh` (runs on droplet)
- **Secrets**: `DEPLOY_SSH_KEY` + `DEPLOY_SSH_KNOWN_HOSTS` (GitHub repo secrets, dedicated ED25519 key)
- **Migrations**: Auto-run via pooler URL (avoids IPv6 direct connection DNS issue)
- **Concurrency**: Only one deploy at a time — new merges cancel in-progress deploys

## SSH & Remote Commands

When running commands on the dev server via SSH:
- **Never build complex one-liner SSH commands** with f-string dictionary access, nested quotes, or multi-level escaping. They break reliably.
- **For multi-line commands**: Write a temporary script file on the remote, execute it, then clean up:
  ```bash
  ssh compgraph-do 'cat > /tmp/task.sh << "SCRIPT"
  cd /opt/compgraph
  uv run python -c "from compgraph.config import Settings; print(Settings().database_url)"
  SCRIPT
  bash /tmp/task.sh && rm /tmp/task.sh'
  ```
- **For database queries**: Use `psql` or write a Python script rather than embedding SQL in SSH commands.
- **For simple commands**: Single operations like `systemctl restart compgraph` are fine as one-liners.

## Git Workflow

- **NEVER merge to main without explicit user approval.** Poll the user, don't assume.
- **NEVER leave unactioned code review feedback before merge.** Fix, defer to issue, or explicitly reject with rationale.
- Never merge a PR until ALL CI checks pass. Poll `gh pr checks <number>` if unsure.
- 4 review bots active on PRs: Gemini, Cursor, Copilot, AND Cubic. Wait for all before merging.
- Git hooks: pre-commit (ruff check+format+mypy), pre-push (pytest). Install via `bash scripts/setup-hooks.sh`.
- Only use `--no-verify` for documentation-only pushes with explicit justification.

### PR Workflow

Before pushing any branch with Python changes:
1. Run `uv run ruff check src/ tests/ --fix && uv run ruff format src/ tests/` — fix lint issues locally
2. Run `uv run mypy src/compgraph/` — catch type errors before CI does
3. Run `uv run pytest -x -q --tb=short -m "not integration"` — full unit test pass
4. Only push after all three pass. Do NOT push hoping CI will catch issues — it wastes a round-trip.

After squash-merging a PR to main:
- CD auto-deploys to dev server (no manual action needed)
- Sync local main: `git checkout main && git pull origin main`
- Rebase any open feature branches: `git checkout feat/xxx && git rebase main`
- This prevents branch divergence on subsequent PRs.

SQL aggregate pattern reminder: Use `aggregate_order_by()` from `sqlalchemy.dialects.postgresql` for ordered aggregates. SELECT-level `.order_by()` is a no-op for scalar aggregate functions.

## Pre-Session Validation

Before starting work with external APIs, validate API keys with a lightweight test call. If invalid, stop immediately — do not retry in a loop.

## Hook Safety

All hooks MUST have a fallback/escape condition. If an external tool call fails 3 times, exit gracefully. The `.env` pattern in pre-tool hooks uses exact match to avoid blocking `.env.example`.

## Background Tasks & Sub-Agents

- Clean up stale background tasks before starting new orchestrator runs.
- When spawning sub-agents or orchestrator pipelines, check for duplicate/orphaned processes first.
- Do not improvise if a skill or resource is missing — ask the user or pull the latest from main before proceeding.
- If a background agent has not produced output in 10 minutes, consider it stale and report to the user.
- **Observer agents must always record.** Never skip an observation claiming it is "routine" or "no observation needed." Record every meaningful event — git operations, file edits, test results, decisions, errors. If in doubt, record it. The session-end summary is the fallback, not the primary mechanism.

## CodeSight (Semantic Code Search)

The project is indexed with CodeSight MCP for semantic search across code and docs.

**MANDATORY SESSION START:** Always reindex at the beginning of every session — no exceptions, no conditional check:
```
index_codebase(project_path="/Users/vmud/Documents/dev/projects/compgraph", project_name="compgraph")
```
This is incremental (~2-4s for no changes, ~15s for many). Do it once at session start, then search freely.

**Two-stage retrieval pattern:**
1. `search_code(query, project="compgraph")` — returns metadata only (~40 tokens/result)
2. `get_chunk_code(chunk_ids, include_context=True)` — expands relevant results with full source

**Useful filters:**
- `symbol_type="function"|"class"|"method"` — narrow to code symbols
- `file_pattern="src/compgraph/scrapers/"` — scope to directory
- `file_pattern="docs/"` — search design docs, research, and plans

**Indexed content:** All Python source, tests, and docs (design.md, product-spec, plans/, references/, failure-patterns, etc.). Research findings and architecture decisions are searchable alongside implementation code.

**When to use:** CodeSight is the **default** exploration tool — use it BEFORE Read/Glob/Grep when exploring unfamiliar code. Only fall back to direct file reads for exact line-level content that CodeSight already pointed you to.

## Context Loading

**Exploration hierarchy (follow this order — do NOT skip to step 3):**
1. **Claude-Mem** — search persistent memory for prior research and decisions: `search(query="<topic>", project="compgraph")` → `get_observations(ids=[...])` for details. If memory answers the question, stop here.
2. **CodeSight** — semantic search across code and docs: `search_code(query="<topic>", project="compgraph")` → `get_chunk_code(chunk_ids)` for source. If CodeSight locates the relevant code, read only that file.
3. **Targeted reads** — Glob/Grep/Read for specific files identified by steps 1-2. Do NOT speculatively read files hoping to find something — that's what steps 1-2 are for.

**Anti-pattern:** Opening 5+ files with Read/Glob before trying Claude-Mem or CodeSight. If you catch yourself doing this, stop and use the tools above first.

Read `docs/changelog.md` (latest entry only) for session continuity. The Roadmap section above provides milestone awareness at Tier 0. Load context packs from `docs/context-packs.md` based on task type — use Pack R for planning sessions. Never load all of `docs/design.md` at once (~5.5K tokens).

## Session Discipline

**Hard limits on exploration before producing output:**
- **Max 5 tool calls** for initial exploration (claude-mem + CodeSight + targeted reads). After 5 calls, you MUST produce a deliverable: a summary, a proposed approach, or a specific question.
- **If you need more exploration**, tell the user what you've found so far and ask if you should continue. Do NOT silently keep reading files.
- **Never open more than 3 files** in a single exploration pass without producing intermediate output.

**Behavioral rules:**
- If the user interrupts or redirects, immediately pivot — do not continue the current exploration path.
- Every exploration phase must end with a concrete deliverable, even if incomplete.
- When the user says "implement", start writing code within your first 5 tool calls. Use claude-mem and CodeSight to get oriented, then produce code — not a 10-call research phase.

## Agent Crew

Project-level agents in `.claude/agents/` have deep CompGraph context:
- `python-backend-developer` — implementation (scrapers, enrichment, aggregation, API)
- `react-frontend-developer` — Next.js pages, Recharts charts, AG Grid tables, Supabase Auth, Vitest tests
- `nextjs-deploy-ops` — DO deployment, Caddy, systemd, Supabase RLS, CI/CD
- `code-reviewer` — quality gate (plan alignment, async patterns, append-only rules)
- `pytest-validator` — test audit (hollow assertions, DB isolation)
- `spec-reviewer` — scope gate (goal achievement vs product spec)
- `database-optimizer` — query/index/schema optimization
- `python-pro` — Python 3.12+ async patterns and idioms
- `dx-optimizer` — developer experience and tooling improvements
- `enrichment-monitor` — enrichment pipeline health checks
- `agent-organizer` — multi-agent orchestration and delegation

Review sequence: implement → `code-reviewer` → `pytest-validator` → `spec-reviewer`

## Skills

Custom skills in `.claude/skills/` (invoke via `/skillname`):
- `/commit` — lint, test, diff review, commit, push
- `/pr` — create PR with validation and CI awareness
- `/deploy` — deploy main to Digital Ocean dev server
- `/merge-guardian` — enforce CI pass + review before merge
- `/pr-feedback-cycle` — triage and resolve bot review comments
- `/research` — structured codebase/web research with scope boundaries
- `/worktree` — isolated git worktree for issue work
- `/parallel-pipeline` — decompose issue into parallel agent subtasks
- `/cleanup` — clean up merged branches and worktrees
- `/enrich-status` — check enrichment pipeline status on dev server
- `/migrate` — generate/run Alembic migrations
- `/docs-audit` — validate doc freshness, cross-doc consistency, and research gaps
- `/frontend-design` — enforce CompGraph design language, reject AI-default patterns

## Code Standards

When scaffolding new modules, create fully-implemented files — never empty stubs. Use TODO comments with specific descriptions for deferred work.

## Session Wrap-Up

Before ending a non-trivial session, write a structured summary instead of running parallel observer agents:
- Save key decisions and findings to claude-mem: `save_memory(text="...", project="compgraph")` — this is the primary persistence method
- Also append to `docs/changelog.md` for file-based continuity
- Include: date, goal, files changed, key decisions, and open questions
- Keep summaries concise — 5-10 lines maximum
- **Roadmap checkpoint:** If milestone progress changed, update `docs/phases.md` Current State line and the Roadmap section above
- This replaces the need for dedicated observer agent sessions
