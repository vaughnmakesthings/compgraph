# Session Changelog

Reverse-chronological log of what happened, what failed, and what's next. Read the latest entry at session start for continuity.

---

## 2026-02-12 (Session 3) — Dev Environment + Supabase Migrations

### Completed
- **Dev environment hardened** — Git hooks (pre-commit, pre-push), CI workflow (lint, typecheck, test, security), ruff rules, mypy config, pytest-cov with 50% threshold, CodeRabbit review config.
- **GitHub org migration** — Repo transferred to `vaughnmakesthings/compgraph` org, SSH remote configured, branch protection set via web UI.
- **Supabase migrations** — Alembic autogenerate connected to live Supabase (Postgres 17). Initial migration created all 13 tables. Migration applied successfully.
- **Seed data** — 4 target companies seeded: Advantage Solutions (Workday), Acosta Group (Workday), BDS Connected Solutions (iCIMS), MarketSource (iCIMS).
- **Custom skills** — Created worktree, pr, cleanup, merge-guardian, parallel-pipeline skills.
- **CLAUDE.md expanded** — Architecture overview, CI merge discipline, orchestrator process management, skills & artifacts sections.
- **Bug fix** — conftest.py seed data used wrong field name (`ats_type` → `ats_platform`) and was missing required `career_site_url`.

### Decisions
- SSH for git push (HTTPS via 1Password plugin too fragile with org tokens).
- CodeRabbit + Codecov + Snyk for CI. Skipped Gemini Code Assist, Cursor Bug Bot, CircleCI.
- GitHub Issues with milestones (M1-M7) for roadmap tracking.

### Blocked / Next
- **iCIMS scraper** — First scraper adapter (MarketSource + BDS). Primary implementation target.
- **Workday scraper** — Second priority (Advantage + Acosta).
- **CI secrets** — CODECOV_TOKEN and SNYK_TOKEN need adding to repo secrets.

---

## 2026-02-12 (Session 2) — Agent Crew Assembly + Context Management

### Completed
- **Agent crew assembled** — 4 project-level agents in `.claude/agents/`: `python-backend-developer`, `code-reviewer`, `pytest-validator`, `spec-reviewer`. Each has deep CompGraph context (schema, conventions, pipeline architecture).
- **Hooks configured** — PostToolUse: auto ruff format + auto pytest on Python file edits. PreToolUse: blocks `.env` (exact match), `.git/`, `credentials`. Notification: macOS osascript on permission/idle prompts.
- **Context management scaffolded** — `docs/` directory structure modeled after scraper-research-engine with token-optimized tiered loading.
- **Voltagent integration** — Identified high-value subagent types for specialist questions (python-pro, postgres-pro, prompt-engineer, data-engineer, backend-developer, debugger).

### Decisions
- Agent crew uses project-level agents for implementation/review, voltagent specialists for targeted questions. No overlap.
- Context packs designed around CompGraph's 5 task types: scrapers, enrichment, aggregation, API endpoints, database work.

### Blocked / Next
- **M1 Foundation**: Need Supabase connection to generate Alembic migrations. All 13 models defined but not migrated.
- **Scraper adapters**: iCIMS + Workday patterns documented in product spec Appendix B. Implementation is next priority.
- **Preflight validation**: Module designed (plan in `~/.claude/plans/`) but not yet implemented.

---

## 2026-02-11 (Session 1) — Initial Scaffold

### Completed
- **Project scaffold** — FastAPI app, SQLAlchemy 2.0 async models (13 tables), Alembic config, health endpoint, pydantic-settings config.
- **Database models** — 4 dimension tables (companies, brands, retailers, markets), 4 fact tables (postings, posting_snapshots, posting_enrichments, posting_brand_mentions), 4 aggregation tables (agg_daily_velocity, agg_brand_timeline, agg_pay_benchmarks, agg_posting_lifecycle), 1 auth table (users).
- **Product spec** — Full specification written: data architecture, pipeline design, API contracts, alert system, milestones M1-M7.
- **CLAUDE.md** — Project instructions configured.

### Decisions
- Python 3.12+ / FastAPI / SQLAlchemy 2.0 async / Supabase (managed Postgres) selected as stack.
- Append-only data model — never mutate historical records.
- UUIDs for all primary keys, timezone-aware timestamps.
- Two-pass enrichment: Haiku 4.5 (classification) + Sonnet 4.5 (entity extraction).

### Blocked / Next
- Need `.env` with Supabase DATABASE_URL to generate/run migrations.
- Need to implement first scraper adapter (iCIMS for MarketSource).
