# CompGraph Master Gap Analysis Report

This report synthesizes findings from codebase scans, GitHub issues, documentation audits, silent failure analyses, and multidisciplinary swarm intelligence reviews.

## 1. 🏗️ Architecture & API Contracts
*Structural foundation, decoupling, state management, and API lifecycle.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **ARCH-01** | 🔴 CRITICAL | **Route-to-DB Coupling** | `api/routes/*.py` | Move SQLAlchemy query building out of route handlers. Create a dedicated `PostingService` layer for DB operations. | M4 | Medium |
| **ARCH-02** | 🟠 HIGH | **Fragile In-Memory State** | `orchestrator.py` | Eliminate global `_runs` dicts. Move pipeline and enrichment state tracking entirely to DB (`scrape_runs`, `enrichment_runs`). **Prereq:** Alembic migration to add `last_heartbeat_at` column to `scrape_runs` and `enrichment_runs` tables. | M4 | Medium |
| **ARCH-03** | 🟡 MEDIUM | **Unversioned API Contracts** | `api/routes/` | Implement strict API versioning (`/api/v1/postings`) to ensure backward compatibility for future UIs or mobile clients. | M4 | Small |
| **ARCH-04** | 🟡 MEDIUM | **Cross-Repo Schema Sync** | `web/types` & `db/models.py` | Automate generation of TypeScript interfaces from Python Pydantic models (e.g., using `pydantic-to-typescript` in CI). | M7 | Small |
| **ARCH-05** | 🔵 LOW | **Multi-Worker Unsafe** | Pipeline triggers | Move orchestrator locks to Redis or DB to support multi-worker (Gunicorn) scaling. (Issue #61) **Prereq:** OPS-06 (Redis). | M6 | Medium |

## 2. 🗄️ Data Models & Database Integrity
*Schemas, relationships, data fidelity, and migration safety.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **DATA-01** | 🔴 CRITICAL | **Double-Counting Enrichments** | Aggregation SQL | Versioned enrichments create multiple rows per posting. Create a `latest_enrichment` CTE/View and use it for all Agg queries. (Issue #70) | M4 | Small |
| **DATA-02** | 🟠 HIGH | **Missing FK Indexes** | `models.py` | 14 critical Foreign Key indexes are missing (e.g., on `posting_id`, `brand_id`), guaranteeing slow JOINs at scale. (Issue #45) | M4 | Small |
| **DATA-03** | 🟠 HIGH | **Brand Duplication** | `brands` table | Run consolidation migration for known duplicates ("LG" vs "LG Electronics", "Reliant"). | M4 | Small |
| **DATA-04** | 🟡 MEDIUM | **Empty Entity Ambiguity** | `schemas.py` | Add `entities_attempted: bool` to distinguish "LLM found 0 brands" from "Enrichment crashed/bypassed". (Issue #66) | M4 | Small |
| **DATA-05** | 🟡 MEDIUM | **Migration Idempotency** | `alembic/versions/` | Ensure `downgrade()` functions use `DROP IF EXISTS` (e.g., Issue #119 for triggers) and enforce `--dry-run` checks for data scripts. | M6 | Small |
| **DATA-06** | 🔵 LOW | **Squash Migrations** | `alembic/` | Condense initial prototype migrations into a single baseline once M3 schema is proven stable. (Issue #54) | M6 | Medium |

## 3. 🕸️ Scraping & Data Ingestion
*Resilience, anti-bot handling, and drift detection.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **SCRP-01** | 🔴 CRITICAL | **Silent Scraper Failures** | `scrapers/` | Scrapers return `SUCCESS` even if 0 jobs are found. Implement `check_baseline_anomaly` (alert if count drops >50% vs 7-day avg). | M4 | Small |
| **SCRP-02** | 🟠 HIGH | **Blind Redirect Following** | `scrapers/icims.py` | Scrapers follow 301/302s to unrelated error pages. Add `_validate_redirect()` to enforce expected ATS domains. | M4 | Small |
| **SCRP-03** | 🟡 MEDIUM | **Missing ATS Drift Detector** | Infrastructure | Companies change ATS providers silently. Build a meta-scraper to crawl corporate career roots and alert on ATS URL changes. | M7 | Medium |
| **SCRP-04** | 🔵 LOW | **Hardcoded Tuning Params** | `workday.py`, `icims.py` | Move `PAGE_SIZE`, `CONCURRENCY`, and `DELAY` to `config.py` `.env` variables for environment-specific tuning. | M6 | Trivial |

## 4. 🧠 LLM Enrichment & Data Science
*Data quality, prompts, extraction intelligence, and trust.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **LLM-01** | 🔴 CRITICAL | **Missing Pay Sanity Checks** | `schemas.py` | LLM extracts "$1M budget" as pay. Add Pydantic constraints (Hourly $10-$150, Annual $20k-$300k, `min <= max`). | M4 | Small |
| **LLM-02** | 🟠 HIGH | **Confidence Decay Engine** | `BrandTimeline` | Unmentioned relationships live forever. Implement a half-life algorithm moving relationships from "Active" → "Dormant". | M6 | Large |
| **LLM-03** | 🟠 HIGH | **Cross-Source Triangulation** | Schema Architecture | Decouple "Fact" from "Job Posting" to allow LinkedIn/Press Releases to feed an `IntelGraph` with composite confidence scoring. | M7 | Large |
| **LLM-04** | 🟡 MEDIUM | **Evaluation N+1 Queries** | `eval/router.py` | N+1 queries in leaderboard generation. (Issue #193). Use `selectinload`. | M6 | Small |
| **LLM-05** | 🟡 MEDIUM | **Batch Enrichment DB Load** | `orchestrator.py` | Current design triggers an individual DB update for every counter increment. Batch updates at the run/chunk level. (Issue #89) | M4 | Small |

## 5. ⚡ Performance & Scalability
*Speed, resource usage, and cost optimization.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **PERF-01** | 🔴 CRITICAL | **Sequential N+1 API Fetching**| `api/postings.py` | `GET /postings/{id}` issues 4 sequential DB queries. Use `joinedload` and `selectinload` to fetch the graph in 1 query. | M4 | Small |
| **PERF-02** | 🟠 HIGH | **Sequential Aggregations** | `aggregation/` | The 7 materialization jobs run sequentially. Refactor using `asyncio.gather` with a connection pool semaphore. | M4 | Small |
| **PERF-03** | 🟠 HIGH | **Anthropic Batch API Omission** | `enrichment/` | Non-urgent daily enrichments run synchronously. Integrate Anthropic Batch API to cut LLM costs by 50%. **Prereq:** Eval Tool (#128) for quality validation before switching enrichment path. | M6 | Medium |
| **PERF-04** | 🟡 MEDIUM | **API Aggregation Caching** | `api/routes/` | No caching layer for heavy aggregate reads. Integrate `fastapi-cache2` (Redis) with 60s TTLs. Depends on OPS-06 (Redis). | M8 | Medium |
| **PERF-05** | 🟡 MEDIUM | **Incorrect Aggregate Ordering**| `aggregation/` | `string_agg` with `.order_by()` on outer query is non-deterministic. Use Postgres `aggregate_order_by()`. | M4 | Trivial |

## 6. 🔒 Security & Access Control
*Auth, permissions, data protection, and injection prevention.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **SEC-01** | 🔴 CRITICAL | **Unauthenticated Controls** | `api/routes/scrape.py` | Anyone can hit `/trigger` or `/stop`. Implement Supabase Auth JWT middleware; enforce Admin RBAC roles. (Issue #59) **Prereqs:** (1) Supabase Auth project config (magic link provider, redirect URLs), (2) `get_current_user` FastAPI dependency for JWT validation, (3) migration to link `users.id` to Supabase `auth.users` via `auth_uid` column. | M4 | Medium |
| **SEC-02** | 🔴 CRITICAL | **SQL Wildcard Injection** | `api/postings.py` | `_escape_like` logic was removed during a refactor. Must restore escaping for `%` and `_` in search params. | M4 | Small |
| **SEC-03** | 🟠 HIGH | **Missing SSL Enforcement** | `alembic/env.py` | Migrations rely on `.env` strings for SSL mode. Hardcode `ssl=require` in Alembic's `create_async_engine`. | M4 | Trivial |
| **SEC-04** | 🟡 MEDIUM | **API Rate Limiting** | `api/main.py` | Missing abuse prevention. Implement `slowapi` or custom middleware to restrict req/min per authenticated user. Depends on SEC-01 (auth) + OPS-06 (Redis). | M7 S2 | Small |
| **SEC-05** | 🟡 MEDIUM | **Automated Secret Rotation** | Ops/Infra | No mechanism to rapidly cycle compromised Anthropic/Supabase/Logo.dev keys across environments. | M7 | Medium |

## 7. 🎨 Frontend & User Experience (UX)
*Usability, trust, workflow integration, and presentation.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **UX-01** | 🔴 CRITICAL | **Missing Evidence Trails** | `web/views/` | Without provenance, users won't trust the LLM. Implement deep-links highlighting the exact text span that triggered a brand match. **Prereqs:** (1) Alembic migration to add `matched_text` and `posting_section` columns to `posting_brand_mentions`, (2) Pass 2 enrichment prompt change to capture provenance metadata, (3) backfill script for existing mentions. | M7 | Large |
| **UX-02** | 🟠 HIGH | **Missing ConfirmDialogs** | `web/settings/` | Destructive/LLM-costing actions execute instantly. Wrap with Tremor ConfirmDialogs (Needs `confirmingLabel` fix: #194/#184). | M4 | Small |
| **UX-03** | 🟠 HIGH | **Server State Sync (React)** | `web/` | Manually polling via `useEffect`. Rip out `apiFetch` polling and adopt TanStack Query (React Query) or SWR. | M7 | Large |
| **UX-04** | 🟡 MEDIUM | **Empty States & FTUE** | `web/views/` | Add deliberate empty states ("Collecting baseline data...") to prevent confusion when stats are 0 or loading. | M5 | Medium |
| **UX-05** | 🟡 MEDIUM | **Skeleton Loaders** | `web/components/` | Replace layout-shifting generic spinners with dimension-accurate CSS skeleton loaders. | M7 | Small |
| **UX-06** | 🟡 MEDIUM | **In-App HITL Feedback** | `web/views/` | Add "Flag as Incorrect" button on intel chips. Feed flags directly into Eval Tool Ground Truth. **Prereq:** Eval Tool (#128) — needs ground truth storage and corpus infrastructure. | M7 | Medium |
| **UX-07** | 🔵 LOW | **"Push to Pipeline" (CRM)** | `web/` | Add Webhook/API buttons to push targeted competitor-brand pairings directly to Salesforce/HubSpot. | M7 | Medium |
| **UX-08** | 🔵 LOW | **Responsive Layout Audit** | `web/` | Verify complex AG Grid tables and Dashboards render correctly on iPads/tablets (Conference Room standard). | M7 | Small |

## 8. 🩺 Testing, QA & Observability
*Telemetry, test data, and system visibility.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **QA-01** | 🔴 CRITICAL | **Shallow Health Endpoint** | `api/routes/health.py` | `/health` returns 200 even if DB/Scheduler are dead. Add `SELECT 1` ping and APScheduler liveness check. | M4 | Small |
| **QA-02** | 🟠 HIGH | **LLM "Golden Set" Regressions**| `eval/` | Missing automated check to ensure prompt tweaks for Edge Case A don't break 50 established baseline cases. **Prereq:** Eval Tool (#128) — needs corpus, runner, and comparison engine. | M6 | Medium |
| **QA-03** | 🟠 HIGH | **Deterministic Data Factories**| `tests/` | Static fixtures are brittle. Implement `FactoryBoy` (Python) and `msw` (Frontend) for dynamic mock generation. | M6 | Medium |
| **QA-04** | 🟡 MEDIUM | **Structured LLM Telemetry** | `enrichment/` | Missing tracking of P95 latency and token-per-posting ratios. Stream to Grafana/Prometheus. **Prereq:** OPS-04 (monitoring stack — no Grafana/Prometheus currently provisioned on droplet). | M6 | Medium |
| **QA-05** | 🟡 MEDIUM | **Visual Regression Testing** | `web/tests/` | Implement Playwright `toHaveScreenshot()` to prevent Tailwind token updates from silently breaking layout. **Prereq:** `@playwright/test` npm dependency (not currently installed; excluded from tsconfig). | M7 | Medium |
| **QA-06** | 🔵 LOW | **Load/Concurrency Testing** | `tests/` | Run `k6` load scripts against `/velocity` to ensure FastAPI pool handles multiple dashboard users safely. | M7 | Small |

## 9. 🚀 DevOps, CI/CD & Infrastructure
*Provisioning, Disaster Recovery, and CI health.*

| ID | Severity | Issue | Affected Files / Area | Proposed Solution | Target | Effort |
|:---|:---|:---|:---|:---|:---|:---|
| **OPS-01** | 🟠 HIGH | **No Infrastructure as Code** | DO Droplet | Bash scripts are not reproducible. Migrate Droplet, Firewall, and Caddy provisioning to Terraform/Ansible. | M7 | Large |
| **OPS-02** | 🟠 HIGH | **Database DR Drills (PITR)** | Supabase | No runbook for Point-in-Time Recovery. If an agg script wipes a fact table, RTO is unknown. Document and drill. | M6 | Medium |
| **OPS-03** | 🟡 MEDIUM | **Log Retention & OOM Risks** | DO Droplet | Local `journalctl` will eventually fill disk. Implement `logrotate` and stream to centralized sink (Axiom/BetterStack). | M6 | Small |
| **OPS-04** | 🟡 MEDIUM | **System-Level Telemetry** | DO Droplet | Install `do-agent` (or NodeExporter) to trigger alerts on RAM > 90% or CPU > 85% before FastAPI crashes. | M6 | Small |
| **OPS-05** | 🔵 LOW | **Consolidate dev deps** | `pyproject.toml` | Resolve conflict between `[dependency-groups].dev` and `[project.optional-dependencies].dev`. (Issue #187) | M4 | Trivial |
| **OPS-06** | 🟡 MEDIUM | **Redis Infrastructure** | DO Droplet | No shared state store. Provision Redis on the DO droplet as a foundational service for caching (PERF-04), rate limiting (SEC-04), arq job queue (M6 roadmap), and multi-worker locks (ARCH-05). Install via `apt`, manage via systemd, bind to `127.0.0.1:6379`. | M7 | Small |

---

## 10. Dependency Map (2026-02-24)

*Prerequisite audit: items whose proposed solutions assume infrastructure, schema changes, or other items that don't yet exist. Added to prevent sprint planning surprises.*

### Critical Path: Eval Tool (#128) is the Hidden Keystone

The Eval Tool is upstream of 4 items but appears nowhere in Sections 1-9 as a tracked gap. It is the single largest untracked prerequisite in this plan.

```
Eval Tool (#128)
├── QA-02  (Golden Set Regressions — needs corpus + runner + comparison)
├── PERF-03 (Anthropic Batch API — needs quality validation before switching)
├── UX-06  (HITL Feedback — needs ground truth storage)
└── LiteLLM migration (phases.md M6 — needs quality baseline)
```

### Critical Path: Eval Tool (#128) Decomposition

**Target user:** Business admin with some technical knowledge — NOT engineers. The UI must abstract LLM internals into business-relevant concepts.

The eval tool currently has a **split-brain architecture** that must be consolidated before it can serve as a keystone:

**Standalone app** (`eval/`): Has a working LLM runner (`eval/eval/runner.py`) with LiteLLM/OpenRouter provider abstraction, aiosqlite storage, corpus management, and prompt loading. Deployed to a Raspberry Pi. This is the actual execution engine.

**Integrated module** (`src/compgraph/eval/`): Has Postgres models (`EvalRun`, `EvalResult`, `EvalCorpus`, `EvalComparison`, `EvalFieldReview`), API routes (`router.py`), and Elo scoring. The `POST /api/eval/runs` endpoint is a **stub** — it creates a DB record but the TODO at line 529 says: *"wire up the actual eval runner once litellm dependency is available (M6)"*. It calls zero LLMs.

**The frontend** (`web/src/app/eval/`): Has 5 pages (Runs, Review, Accuracy, Leaderboard, Prompt Diff) wired to the integrated module's API. The UI works for viewing results but cannot trigger actual evaluations.

```
Eval Tool Consolidation (#128)
├── Phase 0: Bootstrap (prereqs)
│   ├── Generate eval corpus: run scripts/generate_eval_corpus.py against live DB
│   │   (eval/data/ is currently EMPTY — no corpus.json exists)
│   ├── Delete standalone eval app (eval/) after Phase 1 merge
│   │   (includes Pi service compgraph-eval, Streamlit UI, aiosqlite store)
│   └── Ground truth labeling: admin user does this via the eval UI
│       (Review page already exists — needs ground truth editing capability)
│
├── Phase 1: Execution engine (merge runner)
│   ├── Port eval/eval/runner.py logic into src/compgraph/eval/logic.py
│   ├── Replace aiosqlite store calls with AsyncSession (Postgres)
│   ├── Wire POST /api/eval/runs to actually call LLMs via runner
│   ├── Add litellm to root pyproject.toml (already in eval/pyproject.toml)
│   ├── Use OpenRouter as provider (API credits available, OPENROUTER_API_KEY via 1Password)
│   └── Real-time progress tracking via GET /api/eval/runs/{id}/progress
│
├── Phase 2: Comparison engine
│   ├── Field-level diff view (e.g., "Model A: $15/hr, Model B: $18/hr") — not raw text
│   ├── Cost vs accuracy analysis per model ("Value for Money" ranking)
│   ├── Regression detection (did prompt V2 break cases V1 got right?)
│   └── Trust scoring per response (match rate against historical human corrections)
│
└── Phase 3: Guided UX (business admin focus)
    ├── Guided flow: Define → Run → Compare → Feedback → Analyze → Iterate
    ├── Simplify terminology for non-engineers:
    │   ├── "Tokens" → "Processing Volume"
    │   ├── "Latency" → "Thinking Time"
    │   └── "Temperature" → "Creativity Level"
    ├── Model selection: "Choose Intelligence Level" (Fast/Cheap vs Smart/Premium)
    │   instead of raw model ID strings
    ├── Scenario templates (e.g., "Test Pay Extraction Accuracy") to replace
    │   raw prompt version / pass number inputs
    └── Pre-fill suggested corrections from reference data in feedback step
```

**Remaining rejections from Gemini feedback:**
- `python-dotenv` — we use `pydantic-settings`. Wrong for our stack.
- "One-click Deploy to Production" for prompts — no prompt versioning/deployment system exists. Build the eval loop first, then consider deployment automation.
- Hard-locked stepper that prevents navigation — use a guided flow with recommended sequence, but don't lock users out of pages. Business admins with technical knowledge can handle non-linear navigation.

**What we accept:**
- The runner stub is the #1 blocker. Phase 1 consolidation is critical.
- OpenRouter as the LLM provider for evaluations (API credits available).
- Field-level diff view (not raw text comparison) is the right UX for the comparison page.
- Cost vs accuracy analysis is the core value proposition of the tool.
- Jargon simplification for business admin users — terminology should be accessible.
- Guided flow with scenario templates — appropriate for the target user.
- Model catalog with human-friendly labels instead of raw model ID strings.

---

### Critical Path: Auth Stack (SEC-01) Decomposition

SEC-01 is listed as a single "Medium" task but is actually 5-6 subtasks. Product decisions are locked:

**Auth flow (decided):**
- Admin creates invite via **in-app invite form** (not Supabase dashboard)
- Invited user receives a **magic link** email (no public signup URL exists)
- User clicks link → provisions their account (set name/password)
- All subsequent logins via **login page** (email + password)
- **Everything goes behind auth** — no public pages

**Roles:** `admin` (invite users, pipeline controls, eval tool, full access) and `viewer` (read-only dashboard)

```
SEC-01 (Auth & RBAC)
├── 1. Supabase Auth project config
│   ├── Enable magic link provider
│   ├── Configure redirect URLs (Vercel prod + localhost dev)
│   └── Disable public signup (invite-only)
│
├── 2. Backend auth middleware
│   ├── Alembic migration: add auth_uid column to users table, linking to Supabase auth.users
│   ├── get_current_user FastAPI dependency (decode Supabase JWT, lookup user record)
│   ├── Role-based route guards (admin vs viewer decorators)
│   └── POST /api/admin/invite endpoint (admin-only, sends magic link via Supabase)
│
├── 3. Frontend auth pages
│   ├── /login page (email + password form, Supabase Auth client)
│   ├── /setup page (magic link landing → set name/password)
│   ├── Auth context provider (wrap app layout, redirect unauthenticated to /login)
│   └── Admin invite form in Settings page
│
├── 4. RLS policies (SCOPED 2026-02-24)
│   │
│   ├── Design principle: 3-tier access (viewer / admin / service_role)
│   │   ├── viewer: SELECT only on dimension + aggregation + fact tables
│   │   ├── admin: SELECT + trigger actions (pipeline, aggregation, eval)
│   │   └── service_role: full INSERT/UPDATE/TRUNCATE — used by orchestrators + scheduler
│   │
│   ├── a. Dimension tables (companies, brands, retailers, markets, location_mappings)
│   │   ├── All authenticated users → SELECT
│   │   ├── service_role → INSERT/UPDATE (entity resolution, market seeding)
│   │   └── No user writes — reference data managed by pipeline
│   │
│   ├── b. Fact tables (postings, posting_snapshots, posting_enrichments, posting_brand_mentions)
│   │   ├── All authenticated users → SELECT
│   │   ├── service_role → INSERT (scrape + enrichment orchestrators)
│   │   ├── posting_snapshots: STRICT APPEND-ONLY — no UPDATE/DELETE even for service_role
│   │   └── posting_enrichments: service_role INSERT + UPDATE (Pass 2 overwrites allowed)
│   │
│   ├── c. Aggregation tables (7 agg_* tables)
│   │   ├── All authenticated users → SELECT
│   │   ├── service_role → TRUNCATE + INSERT (rebuild pattern)
│   │   └── No partial writes — aggregation is atomic truncate+insert
│   │
│   ├── d. Run tracking tables (scrape_runs, enrichment_runs)
│   │   ├── All authenticated users → SELECT (view run history)
│   │   └── service_role → INSERT/UPDATE (orchestrators track their own runs)
│   │
│   ├── e. Eval tables (eval_runs, eval_samples, eval_results, eval_prompts)
│   │   ├── All authenticated users → SELECT (view results)
│   │   ├── admin → INSERT/UPDATE (trigger runs, submit reviews)
│   │   └── service_role → INSERT/UPDATE (runner writes results)
│   │
│   ├── f. Users table
│   │   ├── Each user → SELECT own row only (auth.uid() = id)
│   │   ├── admin → SELECT all + UPDATE role + DELETE (manage team)
│   │   └── service_role → full access (invite flow creates user records)
│   │
│   ├── Implementation: single Alembic migration enabling RLS + creating policies
│   │   ├── Use Supabase service_role key for background jobs (bypasses RLS)
│   │   ├── API requests use user JWT → RLS filters apply automatically
│   │   └── Alembic can't auto-detect RLS — must write manual SQL migration
│   │
│   └── Key decision: orchestrators (scrape, enrich, aggregate, scheduler) use
│       service_role connection, NOT per-user JWT. This avoids RLS overhead
│       on high-throughput pipeline writes and sidesteps the "who triggered it"
│       attribution question (answer: the admin who clicked Trigger, but the
│       system service does the actual writes).
│
├── 5. Testing strategy (SCOPED 2026-02-24)
│   ├── Recommended: env-gated auth bypass + mock JWT for role testing
│   ├── Unit tests (pytest, no DB):
│   │   ├── Set AUTH_DISABLED=true in test settings → get_current_user returns a stub User
│   │   ├── For role-specific tests: mock get_current_user to return User(role="admin")
│   │   │   or User(role="viewer") to verify route guards
│   │   └── No Supabase dependency — fast, runs in CI without secrets
│   ├── Integration tests (live DB):
│   │   ├── Same AUTH_DISABLED=true approach (integration tests focus on DB, not auth)
│   │   └── Transaction rollback isolation already handles user records
│   ├── Auth flow E2E tests (future, M8):
│   │   └── Playwright against a test Supabase project (separate from prod)
│   └── Rejected: mock JWT with real Supabase validation in unit tests
│       (requires network calls to Supabase JWKS endpoint — too slow, flaky)
│
└── Unlocks:
    ├── SEC-04 (Rate limiting per authenticated user)
    ├── ARCH-02 (Admin-only pipeline controls after auth)
    └── All stakeholder-facing demos
```

### `/api/v1/` Cutover Strategy (SCOPED 2026-02-24)

The prefix change touches 3 independently-deployed systems. Deploying out of order breaks the frontend.

**Current state (verified):**
- Backend: 8 routers in `main.py` use `prefix="/api/<resource>"` (no version segment)
- Frontend: `api-client.ts` constructs paths like `/api/pipeline/status` from `NEXT_PUBLIC_API_URL`
- Vercel: `vercel.json` rewrites `/api/:path*` → `https://dev.compgraph.io/api/:path*` (wildcard — already handles `/api/v1/` without changes)
- Tests: ~30 Python test assertions + ~30 frontend test expectations hardcode `/api/` paths
- Deploy timing: Vercel finishes in ~30-60s, backend CD takes ~2-3 min → **Vercel deploys first**

**Recommended approach: Option C (Backend first with redirect)**

This is the safest approach with the smallest code footprint:

```
/api/v1/ Cutover (Option C)
│
├── Step 1: Backend PR (deploy first)
│   ├── main.py: change all 8 include_router() prefixes to /api/v1/
│   ├── Add catch-all redirect: /api/{path:path} → 308 redirect to /api/v1/{path}
│   │   (308 = Permanent Redirect, preserves method — POST stays POST)
│   ├── Update all Python test files: /api/ → /api/v1/ in assertions
│   ├── /health stays at /health (no version prefix for health checks)
│   └── Merge → CD deploys backend. Old frontend still works via 308 redirect.
│
├── Step 2: Frontend PR (deploy after backend is live)
│   ├── api-client.ts: update all paths from /api/ to /api/v1/
│   ├── Update frontend test expectations
│   ├── vercel.json: NO CHANGE (wildcard already works)
│   └── Merge → Vercel deploys. Frontend now calls /api/v1/ directly.
│
├── Step 3: Cleanup PR (after both are live)
│   └── Remove the /api/ → /api/v1/ catch-all redirect from backend
│       (once analytics confirm no traffic hitting old paths)
│
└── Why not the other options:
    ├── Option A (dual-mount): doubles the router registrations, harder to reason about
    └── Option B (atomic PR): a single PR touching both backend + web/ is fragile —
        backend CD and Vercel deploy from the same push but finish at different times,
        so the race condition still exists
```

**Files to change (exact list):**

| Step | File | Change |
|------|------|--------|
| 1 | `src/compgraph/main.py` | 8 `include_router()` prefix values: `/api/scrape` → `/api/v1/scrape`, etc. |
| 1 | `src/compgraph/main.py` | Add `@app.api_route("/api/{path:path}")` catch-all 308 redirect |
| 1 | `tests/test_postings_api.py` | ~10 path assertions |
| 1 | `tests/test_health_api.py` | 0 changes (health stays at /health) |
| 1 | `tests/test_*.py` (other) | ~20 path assertions across remaining test files |
| 2 | `web/src/lib/api-client.ts` | ~50 API method paths |
| 2 | `web/src/**/*.test.{ts,tsx}` | ~30 test expectations |
| 2 | `web/vercel.json` | No change needed |
| 3 | `src/compgraph/main.py` | Remove catch-all redirect |

**Effort:** Small (Steps 1+2 are mechanical find-and-replace, ~2 hours total)
**Risk:** Low (308 redirect provides backward compatibility during the transition window)

### Full Dependency Graph

| Item | Stated Prerequisites | **Missing Prerequisites (added by this audit)** |
|------|---------------------|------------------------------------------------|
| **ARCH-02** DB-backed runs | — | Alembic migration: `last_heartbeat_at` on `scrape_runs` + `enrichment_runs` |
| **ARCH-05** Multi-worker locks | — | OPS-06 (Redis) |
| **SEC-01** Auth & RBAC | Users table | Supabase Auth config, `auth_uid` migration, `get_current_user` dependency |
| **SEC-04** Rate limiting | — | SEC-01 (auth) + OPS-06 (Redis) *(now documented)* |
| **UX-01** Evidence Trails | — | Migration: `matched_text` + `posting_section` on `posting_brand_mentions`, Pass 2 prompt change, backfill script |
| **UX-03** SWR adoption | — | `swr` npm dependency (not in `web/package.json`) |
| **UX-06** HITL Feedback | — | Eval Tool (#128) ground truth infrastructure |
| **PERF-03** Batch API | — | Eval Tool (#128) quality validation |
| **PERF-04** API Caching | — | OPS-06 (Redis) *(now documented)* |
| **QA-02** Golden Set | — | Eval Tool (#128) corpus, runner, comparison engine |
| **QA-04** LLM Telemetry | — | OPS-04 (monitoring stack: Grafana/Prometheus not provisioned) |
| **QA-05** Visual Regression | — | `@playwright/test` npm dependency (excluded from tsconfig, not installed) |

### Topological Sprint Order (What Must Ship Before What)

Based on the dependency graph, the only valid build order for M7 is:

```
Sprint 1 (Foundation)
├── ARCH-03  /api/v1/ prefix          (no prereqs)
├── LLM-01   Pay bounds in Pydantic   (no prereqs)
├── SEC-01   Supabase Auth stack      (3-4 subtasks, see decomposition above)
├── ARCH-02  DB-backed run tracking   (needs heartbeat migration)
└── UX-02    ConfirmDialogs           (no prereqs)

Sprint 2 (Infrastructure)
├── OPS-06   Redis provisioning       (no prereqs)
├── SEC-04   Rate limiting            (needs SEC-01 + OPS-06)
├── ARCH-01  Service layer extraction (no prereqs, but benefits from v1 prefix)
└── OPS-02   DR drill                 (no prereqs, operational exercise)

Feature Sprint (requires Sprint 1 auth)
├── UX-01    Evidence Trails          (needs migration + prompt change + backfill)
└── UX-05    Skeleton loaders         (no prereqs)

Parallel Track (independent, can start Sprint 1)
└── Eval Tool (#128)
    ├── Phase 1: Runner consolidation   (port eval/eval/runner.py → src/compgraph/eval/logic.py,
    │                                     wire POST /runs, add litellm dep)
    ├── Phase 2: Comparison engine      (field-level diff, cost vs accuracy, regression detection)
    └── Phase 3: UX polish              (guided flow, model catalog dropdown)
    │
    └── Unlocks: QA-02, PERF-03, UX-06, LiteLLM migration
```

Items that **cannot start** until their prerequisites ship:
- SEC-04 is blocked by SEC-01 + OPS-06
- QA-02, PERF-03, UX-06 are blocked by Eval Tool (#128) Phase 2
- QA-04 is blocked by OPS-04 (monitoring stack)
- ARCH-05 is blocked by OPS-06 (Redis)
- PERF-04 is blocked by OPS-06 (Redis)

---

## 11. PM Disposition (2026-02-24)

*Ground-truth verification against codebase. See `strategic-roadmap-refined.md` Section 7 for full rationale.*

### Resolved — Remove from Active Tracking

| ID | Status | Evidence |
|----|--------|----------|
| **SEC-02** | FIXED | `_escape_like()` restored in `postings.py:92` (PR #196) |
| **DATA-01** | FIXED | `latest_enrichment` CTE in `pay_benchmarks.py` and `posting_lifecycle.py` |
| **DATA-02** | FIXED | Issue #45 closed; composite indexes on all major FK columns. Two minor gaps remain: `PostingBrandMention.resolved_brand_id` and `resolved_retailer_id` lack dedicated indexes — low urgency since they're only used in detail views. |
| **DATA-03** | FIXED | `dedup_brands.py` run in prod; 3 pairs consolidated |
| **SCRP-01** | FIXED | `check_baseline_anomaly()` in `orchestrator.py:122` with 7-run rolling avg |
| **QA-01** | FIXED | `health.py` has DB `SELECT 1` ping + scheduler liveness check, returns 503 on failure |
| **SEC-03** | FIXED | `alembic/env.py:69` hardcodes `ssl=require` |

### Accepted — Prioritized for M7

| ID | Revised Priority | Sprint |
|----|-----------------|--------|
| **SEC-01** | CRITICAL | M7 Sprint 1 (auth + RBAC) |
| **ARCH-02** | HIGH | M7 Sprint 1 (pairs with auth) |
| **LLM-01** | MEDIUM (partial fix exists) | M7 Quick Win (add upper bounds to Pydantic) |
| **ARCH-01** | MEDIUM | M7 Sprint 2 (incremental extraction) |
| **UX-01** | HIGH | M7 Feature Sprint |
| **UX-02** | MEDIUM | M7 Polish |
| **OPS-02** | MEDIUM | M7 Operational (half-day exercise) |
| **SCRP-02** | LOW | M7 or M8 |
| **ARCH-03** | MEDIUM | M7 Sprint 1 (prefix only, per engineering disagreement resolution) |
| **OPS-06** | MEDIUM | M7 Sprint 2 (Redis provisioning — unlocks PERF-04, SEC-04, arq, ARCH-05) |

### Rejected / Deferred

| ID | Disposition | Reason |
|----|------------|--------|
| ~~**ARCH-03**~~ | ~~REJECT~~ | *Reversed — see `2026-02-24-engineering-disagreements.md` Section 6A. Accepted as prefix-only change.* |
| **ARCH-04** | REJECT | Frontend types are view models, not DB mirrors. Manual sync is intentional |
| **ARCH-05** | DEFER M8+ | Single-worker is fine at current scale |
| **LLM-02** | DEFER M8+ | Product feature, not a bug. Needs user feedback first |
| **LLM-03** | DEFER INDEF | YAGNI — no second data source exists or is planned |
| **UX-03** | PARTIAL ACCEPT | SWR for new M7 components + Settings page polling. No blanket migration of existing pages. |
| **UX-06** | DEFER M8+ | HITL feedback requires Eval Tool (Issue #128) first |
| **UX-07** | DEFER M8+ | No user request for CRM integration |
| **OPS-01** | DEFER M8+ | 1 droplet doesn't justify Terraform overhead |
| **QA-03** | REJECT | 703 tests at 82% coverage — fixtures are working |
| **QA-05** | DEFER M8+ | Insufficient UI churn to justify visual regression infra |

### Not Covered by This Audit (Product Gaps)

- **Eval Tool** (Issue #128) — largest M7 deliverable, prerequisite for LLM provider migration
- **Company expansion** — 4 of 10+ competitors scraped; business impact of adding more
- **Export/Reporting** — stakeholders need Excel/PDF for leadership presentations
- **Sentry alerting** — configured but no systematic error triage workflow

### Milestone Correction

Both audit documents reference M4/M5/M6 as future milestones. **Actual state: M6 is complete, M7 is in progress.** Streamlit has been decommissioned and replaced by Next.js on Vercel. The `docs/phases.md` file is stale and needs updating to reflect this.
