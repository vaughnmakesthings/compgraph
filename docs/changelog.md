# Session Changelog

Reverse-chronological log of what happened, what failed, and what's next. Read the latest entry at session start for continuity.

---

## 2026-02-19 — Posting Explorer UI Polish + Hotfix

**Goal:** Merge Posting Explorer improvements, resolve bot review feedback, deploy.

**What happened:**
- PR #123 merged — Posting Explorer UI: brand/retailer columns via `string_agg` subqueries, `column_config` for pay formatting, human-readable headers, explicit column ordering
- PR #124 merged — Hotfix: `$%,.2f` sprintf comma format unsupported by Streamlit on dev server, reverted to `$ %.2f`
- 5 bot review comments resolved across 3 cycles (Gemini, Cubic, Cursor):
  - Explicit `column_map` for rename+reorder (Gemini)
  - `aggregate_order_by()` for deterministic `string_agg` ordering (Cursor — caught that SELECT-level ORDER BY is a no-op for aggregates)
  - `column_config.NumberColumn` to preserve numeric sorting (Cubic)
  - Comma thousands separator format (Cubic — worked in theory, not in practice)
- Both PRs deployed to dev server

**Key decisions:**
- `aggregate_order_by` from `sqlalchemy.dialects.postgresql` is the correct way to order within `string_agg` — `.order_by()` on the select is a no-op for scalar aggregate subqueries
- Streamlit `column_config.NumberColumn` preferred over string formatting for pay columns — preserves sorting

**Lessons learned:**
- Streamlit's sprintf doesn't support `%,` comma separator (at least not the version on the Pi). Stick to `$ %.2f` or implement a custom formatter
- Ruff PostToolUse hook strips imports before code references them — edit function bodies first, then add imports

**State:** M3 ~95% complete. 458 tests, all green. All dashboard pages operational. Next: data quality review, remaining M3 items.

---

## 2026-02-18 — Brand Intel Dashboard + Posting Explorer Improvements

**Goal:** Ship Brand Intel dashboard page, resolve enrichment trigger issue, improve Posting Explorer UI.

**What happened:**
- PR #117 merged — Brand Intel dashboard page (live SQL brand/retailer intel, company relationships, active posting counts)
- PR #118 merged — Dropped append-only trigger from `posting_enrichments` (was causing iCIMS snapshot conflicts and mass deactivation)
- PR #123 created — Posting Explorer UI improvements (readability, pay formatting via `column_config`, explicit column ordering, deterministic `string_agg` ordering)
- Bot review feedback cycles completed for all 3 PRs (Cursor, Gemini, Copilot)
- Deployed Brand Intel + trigger fix to dev server

**Key decisions:**
- Brand Intel uses live SQL queries against fact tables (not aggregation tables) — acceptable for current data volume
- `posting_enrichments` no longer strictly append-only at DB level — trigger dropped, application convention relaxed

**State:** M3 ~90% complete. 458 tests, all green. PR #123 open for Posting Explorer polish. Next: data quality review, remaining M3 items.

---

## 2026-02-17 — M3 Parallel Sprint: 5 PRs Merged + Deployed

**Goal:** Complete all unblocked M3 tasks via parallel agent pipeline.

**What happened:**
- Dispatched 4 parallel agents to isolated git worktrees (WS1–WS4)
- All 4 produced passing code (450 tests total on combined main)
- PRs #112–#116 created, CI passed, merged to main in order
- Deployed to dev server (Pi via Tailscale), health check green
- Ran 4 pending Alembic migrations on live Supabase DB

**PRs merged:**
- **#112** — BDS location parsing + category-specific iCIMS URLs (#98, #111)
- **#113** — Dashboard state fixes: pending→running, auto-refresh, scheduler DB fallback (#97, #99, #100, #91, #55)
- **#114** — DB hardening: enrichment_runs default, append-only triggers, FK indexes (#88, #47, #45)
- **#115** — iCIMS redirect domain validation (#65)
- **#116** — Alembic direct DB connection + env override (#46)

**Issues resolved:** #45, #46, #47, #55, #65, #88, #91, #97, #98, #99, #100, #111

**Key discovery:** `db.*.supabase.co` direct host doesn't resolve from Pi (IPv6) OR macOS (DNS). Added `ALEMBIC_DATABASE_URL` env override to server `.env` pointing at the session-mode pooler. Documented in `docs/secrets-reference.md`.

**State:** M3 ~80% complete. 450 tests, all green. 12 issues closed this session. Next: data quality review, remaining open issues.

---

## 2026-02-15 (Session 9) — Dashboard, Scrape Controls, Enrichment Fix, M3 Kickoff

### Completed
- **PR #56 merged** — Dashboard UX fixes: pay value `0.0` falsy bug, error message sanitization (no raw exceptions to UI), empty JSON falsy check in error summary.
- **PR #57 merged** — Dashboard diagnostics: `configure_logging()`, `_timed_query` decorator, session timing, diagnostics sidebar, typed return annotations.
- **PR #58 merged** — Scrape pipeline controls: pause/resume/stop/force-stop API endpoints, `asyncio.Event` for pause, per-company state tracking, Pipeline Controls dashboard page.
- **PR #62 merged** — Enrichment JSON fence fix: Haiku wraps JSON in ` ```json ``` ` markdown fences. Added `strip_markdown_fences()` to client.py, applied in pass1 + pass2.
- **23 code review comments** triaged across PRs #56/#57/#58 — fixed, deferred (3 issues created: #59 auth, #60 concurrent runs, #61 multi-worker), or resolved.
- **Merge conflicts** resolved across 5 dashboard files when merging PRs #56 and #57 (both modified same files).
- **T-ROC scrape** — 98 postings successfully scraped. First M3 data collection run.
- **Full enrichment** — 98/98 postings enriched (Pass 1 + Pass 2, 0 failures). 4 role archetypes detected, 19 postings with brand mentions.
- **Branch cleanup** — Deleted 11 stale branches (local + remote + dev server). Only `main` + `feat/issue-6` remain.
- **309 tests passing**, 69% coverage.

### Scraper Status (M3 Day 1)
- T-ROC: operational (98 postings)
- Advantage Solutions: broken (301 redirect to `careers.youradv.com`)
- Acosta Group: broken (DNS failure — domain gone)
- BDS Connected Solutions: broken (DNS failure — domain gone)
- MarketSource: broken (404 on careers search URL)

### Key Bug Fixes
- `strip_markdown_fences()` — regex strips ` ```json ``` ` fences before `json.loads()` in enrichment pass1/pass2
- Pay value display: `if pay_min or pay_max` → `if pay_min is not None or pay_max is not None` (0.0 is falsy)
- Error sanitization: `st.error(f"...{exc}")` → generic message + `logger.exception()`
- Empty JSON check: `if row.ScrapeRun.errors` → `if row.ScrapeRun.errors is not None` (empty `{}` is falsy)
- Misleading success: "No errors" shown even when error load failed → track `errors_loaded` flag

### Next
- **Fix broken scraper URLs** for Advantage, Acosta, BDS, MarketSource (career sites changed)
- **M3 continues** — daily pipeline runs with T-ROC data while investigating other scrapers
- **Issues #59-#61** — auth, concurrent run guard, multi-worker state (deferred from reviews)

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
