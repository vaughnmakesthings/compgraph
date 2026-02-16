# Session Changelog

Reverse-chronological log of what happened, what failed, and what's next. Read the latest entry at session start for continuity.

---

## 2026-02-15 (Session 8) — M2 PR Merged, All Review Bugs Fixed

### Completed
- **PR #39 merged** (Issues #8-#11) — Full M2 enrichment pipeline. 22 files, +3,649 LOC.
- **3 rounds of review fixes** — Addressed all 21 conversation threads from Cursor Bugbot + Gemini Code Assist.
- **304 tests passing**, 77% coverage.

### Review Fixes (Round 2 — Cursor Bugbot)
- Pass1 livelock: track `failed_ids` in-memory, pass `exclude_ids` to query.
- Canonical repost ordering: `ORDER BY first_seen_at ASC` on unfingerprinted batch.
- Run status aggregation: `_compute_final_status()` considers both pass1 + pass2 outcomes.
- Fingerprint failure visibility: downgrade status to PARTIAL on exception.
- Validation stale snapshots: latest-snapshot subquery (DISTINCT ON).
- Concurrent entity creation: `IntegrityError` catch + re-query on slug conflict.

### Review Fixes (Round 3 — Cursor Bugbot)
- Pass2 livelock: same `failed_ids` + `exclude_ids` pattern as Pass1.
- Backfill count: `enrichment_version` filter instead of `PostingBrandMention` existence.
- Entity rollback: `begin_nested()` savepoint instead of full `session.rollback()`.
- Validation duplicates: latest-enrichment subquery (DISTINCT ON `enriched_at`).

### Deferred (acknowledged in review)
- API authentication → M3
- pg_trgm fuzzy matching → M6 (dimension tables <500 rows)
- Prompt injection hardening → M6
- N+1 queries in fingerprinting/validation → M6 (bounded batch sizes)
- Concurrent run guard → M3 (single-operator deployment)

### Next
- **M3: Data Collection Period** — 10-14 days of daily pipeline runs, data quality monitoring

---

## 2026-02-15 (Session 7) — M2 Enrichment Pipeline Implementation

### Completed
- **PR #39 created** (Issues #8-#11) — Full M2 enrichment pipeline implementation
- **Pass 1** (Haiku 4.5) — Classification, pay extraction, content section tagging. 9 enrichment modules.
- **Pass 2** (Sonnet 4.5) — Entity extraction with 3-tier resolution (exact/slug/fuzzy via rapidfuzz). Auto-creates new Brand/Retailer records.
- **Fingerprinting** — SHA-256 composite hash detects reposted jobs, increments `times_reposted`.
- **Backfill scripts** — `scripts/backfill_enrichment.py` (CLI with --dry-run, --pass1-only, --pass2-only) and `scripts/validate_enrichment.py` (CSV spot-check).
- **304 tests passing**, 78% coverage. 108 new enrichment tests.

### Key Fixes During Initial Review
- Pass 2 infinite loop: empty entities caused re-processing. Fixed via `enrichment_version` tracking.
- mypy: `MessageParam` type via `TYPE_CHECKING` + `cast()`, content block `.text` via `hasattr` guard.
- Entity confidence sorting: primary brand/retailer now selected by highest confidence.

---

## 2026-02-15 (Session 6) — M1 Complete: Deactivation + Proxy PRs Merged

### Completed
- **PR #37 merged** (Issue #5) — Posting deactivation with 3-run grace period. Uses `completed_at` ordering with `started_at` cutoff. Added `postings_closed` to ScrapeRun. Fixed iCIMS `is_active` ON CONFLICT bug.
- **PR #38 merged** (Issue #7) — Proxy/UA integration. Optional `PROXY_URL` + credentials via `SecretStr`. RFC 3986 percent-encoding. IPv6 bracket preservation. UA rotation from 5 curated browser strings.
- **10 review threads resolved per PR** — Addressed Cursor Bugbot and Gemini code review feedback across 3 cycles each.
- **M1 milestone closed** — All 11 tasks complete. 196 tests passing, 87% coverage.

### Key Fixes During Review
- `postings_closed` nullable→non-nullable with `server_default="0"`
- `quote_plus()` → `quote(safe="")` for proxy userinfo (RFC 3986)
- Deactivation ordering: `completed_at` for recency, `started_at` for cutoff value
- Workday `httpx.AsyncClient` wrapped in try/except for malformed proxy URLs

### Next
- **M2: Enrichment Pipeline** — Haiku classification (Pass 1) → Sonnet entity extraction (Pass 2)
- Issues #8-#11 are the M2 implementation path

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
