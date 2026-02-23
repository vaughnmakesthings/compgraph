# Implementation Phases

## Roadmap Summary

**Current milestone:** M3 — Data Collection Period (~95% complete)
**Next milestone:** M4 — Aggregation & API

### Pipeline

```
M3 (data collection) → M4 (aggregation + API) → M5 (dashboard via API) → M6 (tuning + hardening) → M7 (production UI)
```

### Future Constraints — Do NOT Build Yet

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| Auth (Supabase Auth, invite via magic link + password login) | M4 (Step 4d) | API must exist first |
| arq (replace APScheduler) | M6 | Current scheduler works; migration is operational hardening |
| LiteLLM (provider abstraction) | M6 | Needs Prompt Evaluation Tool (Issue #128) to validate quality first |
| Frontend framework (Next.js) | M7 | Streamlit validates views cheaply before committing to framework |
| Digital Ocean production deploy | M7 | Production infra only after production UI |
| Digital Ocean dev migration | ~~M5~~ DONE | DO Droplet live + CD auto-deploy on merge to main |
| Scraper expansion (new companies) | M4+ | Current 4 companies validate pipeline; add more after agg+API layer exists |
| Custom JWT auth | Never | Using Supabase Auth instead |
| Prisma / second ORM | Never | FastAPI + SQLAlchemy is the single data layer; frontend is pure API consumer |

### Architecture Pre-Commitments

These decisions are already made. Do not revisit without explicit user approval:

- **Aggregation strategy:** truncate+insert rebuild (not incremental), transactional
- **API layer:** read-only queries against aggregation tables, no writes
- **Dashboard migration (M5):** Streamlit pages migrate from direct DB queries to API calls
- **Enrichment:** 2-pass stays (Haiku + Sonnet), model swap only after Prompt Evaluation Tool validates quality
- **Entity resolution:** 3-tier (exact/slug/fuzzy) stays, thresholds tunable via config
- **Auth:** Supabase Auth — invite via magic link, user sets up username/password during profile setup. Admin/user roles. No public sign-up, no custom JWT.
- **Frontend data access:** Pure API consumer — Next.js calls FastAPI endpoints, no direct DB access, no Prisma
- **Database platform:** Supabase Postgres through M6. Evaluate DO Managed Postgres for M7 if needed.

---

## Current State (2026-02-22)

**M3 ~95% complete.** All 4 scrapers operational (T-ROC, 2020 Companies, BDS, MarketSource). 1,025 postings scraped, enrichment pipeline running. Brand Intel dashboard shipped (PR #117). Posting Explorer polished with brand/retailer columns, pay formatting, human-readable headers (PRs #123, #124). All tests passing (CI enforced). Dev server + dashboard running at dev.compgraph.io / dashboard.dev.compgraph.io (Digital Ocean). **CD pipeline live** — auto-deploys to dev server on merge to main (PR #146). Remaining: data quality review, prompt tuning.

See `docs/changelog.md` for session-by-session history.

---

### Phase 1: Foundation (M1) — COMPLETE

Goal: All four scrapers running, writing raw snapshots to the database.

| Task | Summary | Status | PR |
|------|---------|--------|-----|
| Project scaffold | FastAPI + SQLAlchemy models + Alembic + config | Done | — |
| Agent crew | 4 project agents + hooks + voltagent integration | Done | — |
| Context management | docs/ structure, context packs, tiered loading | Done | — |
| Supabase setup | Database provisioning, connection config, .env | Done | — |
| Alembic migrations | Generate from models, run against Supabase | Done | — |
| iCIMS scraper | MarketSource + BDS adapter (HTML parsing + JSON-LD) | Done | #33 |
| Workday scraper | Advantage + Acosta adapter (CXS API, JSON) | Done | #34 |
| T-ROC scraper | Workday CXS adapter (reused workday module) | Done | #36 |
| Snapshot diffing | Content hash, change detection, deactivation | Done | #37 |
| Pipeline orchestrator | Daily coordinator with error isolation | Done | #35 |
| Proxy integration | Optional proxy + UA rotation for all adapters | Done | #38 |

**Exit criteria met:** All four scrapers run successfully and write raw snapshots to the database.

---

### Phase 2: Enrichment Pipeline (M2) — COMPLETE

Goal: LLM enrichment transforms raw postings into structured intelligence.

| Task | Summary | Status | PR |
|------|---------|--------|-----|
| Pass 1 — Classification | Haiku 4.5: role archetype, level, pay, content sections | Done | #39 |
| Pass 2 — Entity Extraction | Sonnet 4.5: brand/retailer extraction, 3-tier resolution | Done | #39 |
| Fingerprinting | SHA-256 composite hash, repost detection, canonical linking | Done | #39 |
| Backfill & Validation | CLI backfill script + CSV spot-check validation | Done | #39 |
| Enrichment API routes | /api/enrich/trigger, /status, /pass1/trigger, /pass2/trigger | Done | #39 |
| Review bug fixes | 3 rounds: 12 bugs fixed across orchestrator, resolver, queries | Done | #39 |

**Exit criteria met:** Enrichment runs end-to-end. 304 tests passing, 77% coverage.

---

### Phase 3: Data Collection Period (M3) — IN PROGRESS

Goal: 10-14 days of daily pipeline runs on autopilot. No new features — validate reliability and data quality.

| Task | Summary | Status |
|------|---------|--------|
| Dashboard + diagnostics | Streamlit app, Pipeline Health, Posting Explorer, diagnostics sidebar | Done (PRs #56-#57) |
| Scrape controls | Pause/stop/force-stop API + dashboard page | Done (PR #58) |
| Enrichment fence fix | `strip_markdown_fences()` for Haiku JSON responses | Done (PR #62) |
| Fix broken scraper URLs | BDS + MarketSource fixed; Acosta + Advantage dropped (DNS dead) | Done (PRs #112, #115) |
| DB hardening | Server defaults, FK indexes, Alembic direct connection | Done (PRs #114, #116) |
| Drop enrichments trigger | Append-only trigger causing iCIMS conflicts | Done (PR #118) |
| Brand Intel dashboard | Live SQL brand/retailer intel page | Done (PR #117) |
| Posting Explorer improvements | Brand/retailer columns, pay formatting, column ordering | Done (PRs #123, #124) |
| Codebase audit + circuit breaker | Code simplification, enrichment circuit breaker | Done (PR #129) |
| Daily pipeline runs | Monitor scrape + enrichment, flag failures | In progress |
| Data quality review | SQL queries on enrichment accuracy | Pending |
| Initial prompt fixes from observed errors | Fix obvious extraction failures from pipeline monitoring | Pending |
| Prompt injection mitigation (Pass 1) | Sanitize/validate LLM input to prevent injection (Issue #130) | Pending |
| Prompt injection mitigation (Pass 2) | Sanitize/validate LLM input to prevent injection (Issue #131) | Pending |

**Exit criteria (all must be met):**
- 7+ consecutive days with 0 unhandled pipeline failures
- Enrichment Pass 1 success rate >95% across all companies
- Enrichment Pass 2 success rate >90% across all companies
- At least 1 data quality SQL review completed with findings documented
- Security issues #130 and #131 (prompt injection) addressed or risk-accepted

---

### Phase 4: Aggregation & API (M4)

Goal: Query layer serving dashboard views from pre-computed aggregation tables, plus auth.

#### Step 4a: Aggregation Jobs

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| `agg_daily_velocity` job | Posting counts per company per day | M3 complete (clean enrichment data) | Pending |
| `agg_brand_timeline` job | Brand mention timelines per company | M3 complete | Pending |
| `agg_pay_benchmarks` job | Pay range aggregation by role/company | M3 complete | Pending |
| `agg_posting_lifecycle` job | Days-open, repost rates per company | M3 complete | Pending |
| Aggregation orchestrator | Truncate+insert rebuild, transactional, error isolation | All 4 agg jobs | Pending |

#### Step 4b: Dashboard API Endpoints

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| `GET /api/velocity` | Time series of posting volume | `agg_daily_velocity` job | Pending |
| `GET /api/brands` | Brand list with timeline metadata | `agg_brand_timeline` job | Pending |
| `GET /api/brands/:id/timeline` | Single brand history | `agg_brand_timeline` job | Pending |
| `GET /api/pay` | Pay range benchmarks | `agg_pay_benchmarks` job | Pending |
| `GET /api/lifecycle` | Days open, repost metrics | `agg_posting_lifecycle` job | Pending |
| `GET /api/alerts` | Recent significant changes | All agg jobs | Pending |

#### Step 4c: Detail API Endpoints

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| `GET /api/postings` | Paginated posting list with filters | None (queries fact tables) | Pending |
| `GET /api/postings/:id` | Full posting detail with enrichment | None | Pending |
| `GET /api/postings/:id/history` | Snapshot timeline for a posting | None | Pending |
| `GET /api/companies` | Competitor list with summary stats | Agg jobs for stats | Pending |
| `GET /api/companies/:id/summary` | Single competitor dashboard view | Agg jobs for stats | Pending |

#### Step 4d: Auth & System

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| Supabase Auth integration | Invite via magic link, profile setup with username/password, admin/user roles, JWT verification middleware (Issue #59) | Users table exists | Pending |
| Role-based access control | Admin: invite, pipeline control, full access. User: read-only dashboard, export | Supabase Auth | Pending |
| `GET /api/scrape/status` | Pipeline status | — | Done (PR #58) |
| `POST /api/scrape/trigger` | Manual trigger (admin) | — | Done (PR #58) |
| Alert generation logic | Detect significant changes, create alert records | All agg jobs | Pending |

#### Step 4e: Pipeline Infrastructure

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| `scrape_runs` table | Per-company health tracking: status, duration, error counts per run | Schema migration | Pending |
| Scraper expansion (first wave) | Onboard 2-4 additional companies using existing adapters | Agg jobs validate pipeline | Pending |
| Missing indexes | Add indexes on large fact/aggregation tables (Issue #110) | — | Pending |

**Exit criteria:** All endpoints return real data. Auth gates dashboard access. Alerts generate meaningful signals.

---

### Phase 5: Dashboard via API (M5)

Goal: Migrate existing Streamlit pages from direct DB queries to API calls. Add velocity and alerts views.

**Context:** 5 dashboard pages already exist and query the database directly:
1. Pipeline Health — pipeline run status, failure rates
2. Posting Explorer — searchable posting list with enrichment data
3. Pipeline Controls — scrape trigger, pause/stop
4. Scheduler — APScheduler job status
5. Brand Intel — brand/retailer relationships, mention counts

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| API client module | Shared httpx client for Streamlit → API calls | M4 API endpoints | Pending |
| Migrate Pipeline Health | Replace direct DB queries with API calls | API client + system endpoints | Pending |
| Migrate Posting Explorer | Replace direct DB queries with posting API | API client + detail endpoints | Pending |
| Migrate Pipeline Controls | Already uses API routes; verify and clean up | API client | Pending |
| Migrate Brand Intel | Replace direct DB queries with brand API | API client + brand endpoints | Pending |
| Velocity dashboard | New page: line charts of posting volume, filterable | `GET /api/velocity` | Pending |
| Alerts feed | New page: triggered alerts with drill-down | `GET /api/alerts` | Pending |
| Migrate Scheduler page | Replace direct APScheduler queries with API calls (design for arq compatibility in M6) | API client + system endpoints | Pending |
| DO dev environment migration | Move FastAPI + Streamlit + scheduler from Pi to DO Droplet | DO account provisioned | **Complete** (PR #143) |
| Deploy behind auth | Dashboard requires login | Auth endpoints (M4) | Pending |

**Exit criteria:** All dashboard pages use API exclusively (no direct DB). Velocity and alerts views functional. Daily use for 1+ week. Leadership can view.

---

### Phase 6: Tuning & Hardening (M6)

Goal: Production-grade data quality, operational reliability, and cost-optimized LLM pipeline.

#### Step 6a: Data Quality

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| Systematic prompt refinement with Prompt Evaluation Tool | Refine enrichment prompts using Prompt Evaluation Tool Elo ranking | M3 data quality review + Prompt Evaluation Tool | Pending |
| Enrichment pass refactor | Merge run_pass1/run_pass2 into generic _run_pass (Issue #90) | — | Pending |
| Brand/retailer taxonomy | Merge duplicate entities, correct misclassifications | Enrichment data available | Pending |
| Role archetype normalization | Standardize role categories across companies | Enrichment data available | Pending |
| Alert threshold tuning | Reduce noise from velocity/brand/lifecycle alerts | Alert system (M4) | Pending |

#### Step 6b: Operational Hardening

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| Pipeline monitoring | Structured logging, health metrics, failure alerting | Dashboard via API (M5) | Pending |
| Concurrent run guard | Prevent overlapping pipeline runs (Issue #60) | — | Pending |
| Multi-worker support | Safe concurrent API + scheduler (Issue #61) | Concurrent run guard | Pending |
| Query performance | Index tuning, slow query identification | Production-like data volume | Pending |
| Supabase RLS policies | Row-level security hardening (Issue #52) | Auth (M4) | Pending |
| Scraper redirect validation | Validate HTTP redirect targets (Issue #65) | — | Pending |

#### Step 6c: Scaling Prep

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| Prompt Evaluation Tool | Standalone app for prompt/model testing with Elo ranking (Issue #128) | — | Pending |
| Haiku Pass 2 test | Evaluate Haiku for Pass 2 (5x savings if quality holds) | Prompt Evaluation Tool | Pending |
| LiteLLM integration | Provider-agnostic LLM calls (~half day, drop-in) | Prompt Evaluation Tool validates quality | Pending |
| Anthropic Batch API | 50% cost discount for non-urgent enrichment | LiteLLM (or direct integration) | Pending |
| arq migration | Replace APScheduler with arq for Redis-backed job queue | Multi-worker support | Pending |

**Exit criteria:** Enrichment accuracy >90%. No false-positive alerts for 7 days. Pipeline runs unattended for 2+ weeks. LLM cost path to <$30/mo validated.

---

### Phase 7: Production UI (M7)

Goal: Production-ready frontend with auth, export, and deployment on Digital Ocean.

**Architecture note:** Frontend is a pure API consumer. Next.js calls FastAPI endpoints directly. No BFF layer, no Prisma, no direct DB access.

| Task | Summary | Dependencies | Status |
|------|---------|-------------|--------|
| Frontend stack finalization | Confirm leading candidate: Next.js App Router + AG Grid + shadcn/ui + Recharts | M5 validates view requirements | Pending |
| Project scaffold | Next.js app, AG Grid integration, API client, auth middleware | Stack confirmed | Pending |
| Dashboard views | Rebuild Streamlit views: velocity, brand intel, posting explorer, alerts | Scaffold | Pending |
| Data tables (AG Grid) | Sorting, filtering, column grouping for posting/brand/company views | Scaffold | Pending |
| Charts (Recharts) | Velocity line charts, brand timeline, pay distribution | Scaffold | Pending |
| Auth flow | Next.js middleware + Supabase Auth, password login, role-based route protection | Supabase Auth (M4) | Pending |
| Export/PDF capability | Download reports, charts, filtered data | Production views | Pending |
| DO production deploy | Droplet provisioning, Caddy reverse proxy, CI/CD, domain, SSL | All above | Pending |
| Scraper expansion (full) | Scale to 50 companies using proven adapters | Pipeline validated at 10+ companies | Pending |

**Consideration:** Evaluate Metabase OSS as a complementary exploration layer alongside the custom frontend. Could serve ad-hoc data exploration needs without custom development. See `docs/references/metabase-oss-evaluation.md`. Decision at M7 planning time.

**Exit criteria:** Production URL accessible. Auth working. All views from M5 replicated. PDF export functional. CI/CD pipeline green.

---

## Critical Path

```
Supabase setup + migrations                ✅ M1
  ↓
iCIMS + Workday scrapers                   ✅ M1
  ↓
Pipeline orchestrator + proxy              ✅ M1
  ↓
Enrichment Pass 1 (Haiku)                  ✅ M2
  ↓
Enrichment Pass 2 (Sonnet)                 ✅ M2
  ↓
Data collection period (10-14 days)        ← YOU ARE HERE (M3, ~95%)
  ↓
Aggregation jobs (4 tables)                ← next (M4a)
  ↓
Dashboard + Detail API endpoints           ← M4b-c
  ↓
Auth endpoints                             ← M4d
  ↓
Dashboard via API migration                ← M5
  ↓
DO dev environment migration               ← M5 (parallel)
  ↓
Data quality + operational hardening       ← M6a-b
  ↓
LLM eval → Haiku test → LiteLLM → Batch   ← M6c (scaling prep)
  ↓
Frontend framework → views → deploy        ← M7
```

---

## Open Issue Mapping

All open GitHub issues assigned to milestones. Last triaged: 2026-02-22.

### Close as stale/done (verify first)

| Issue | Title | Rationale |
|-------|-------|-----------|
| #46 | Fix Alembic connection routing | Fixed in PRs #114, #116 (direct connection support) |
| #47 | Add append-only triggers on fact tables | Trigger deliberately dropped in PR #118 by design |
| #108 | Migrations use pooled database URL | Duplicate of #46, same fix |

### M3 (must-fix before graduation)

| Issue | Title | Category |
|-------|-------|----------|
| #130 | Prompt injection risk in Pass 1 enrichment | Security |
| #131 | Prompt injection risk in Pass 2 enrichment | Security |
| #109 | Enrichment runs stuck as RUNNING | Pipeline reliability |
| #102 | Duplicate brand mentions from Pass 2 reruns | Data quality |
| #105 | Fingerprinting before brand resolution | Data quality |

### M4

| Issue | Title | Category |
|-------|-------|----------|
| #59 | Auth endpoints (now Supabase Auth) | Auth |
| #110 | Missing indexes on fact/aggregation tables | Performance |
| #70 | Multiple PostingEnrichment records per posting | Data integrity |
| #107 | Enrichment retry logic (transient vs permanent errors) | Pipeline reliability |

### M5

| Issue | Title | Category |
|-------|-------|----------|
| #55 | Dashboard UX polish | Dashboard |
| #97 | Dashboard shows "pending" for running companies | Dashboard bug |
| #99 | Dashboard auto-refresh doesn't activate externally | Dashboard bug |
| #100 | Scheduler page shows "No pipeline runs" | Dashboard bug |
| #91 | Enrichment progress shows zeros during runs | Dashboard bug |

### M6

| Issue | Title | Category |
|-------|-------|----------|
| #52 | RLS policies for Supabase security | Security |
| #60 | Concurrent run control | Operational |
| #61 | Multi-worker support | Operational |
| #65 | Scraper redirect validation | Security |
| #90 | Enrichment pass refactor (_run_pass) | Refactor |
| #49 | Connection pool tuning | Performance |
| #50 | CHECK constraints on pay ranges | Schema |
| #51 | FK cascade rules | Schema |
| #53 | CI migration drift detection | CI |
| #54 | Squash Alembic migrations | Maintenance |
| #48 | CREATE INDEX CONCURRENTLY | Performance |
| #128 | Prompt Evaluation Tool (Elo ranking) | Scaling prep (M6c) |

### Low-priority / review feedback (triage individually)

| Issue | Title | Category |
|-------|-------|----------|
| #87 | Batch ID for scrape run grouping | Pipeline improvement |
| #88 | Server default for enrichment_runs.status | Migration cleanup |
| #89 | Batch enrichment counter increments | Performance |
| #95, #96 | Extract pass1/pass2 save helpers | Related to #90 refactor |
| #101 | Scraper deactivation overlap bug | Pipeline edge case |
| #103 | Fuzzy resolution loads entire tables | Performance |
| #104 | Scrape API orphans concurrent runs | Pipeline edge case |
| #106 | Pipeline leaks PENDING scrape runs | Pipeline edge case |
| #119 | Make downgrade() idempotent in migration | Migration cleanup |
| #120 | Improve retailer intel test thoroughness | Test quality |
| #121, #122 | Explicit column rename in Brand Intel | Dashboard cleanup |
| #132-138 | Code quality from latest review | Code quality |
| #66 | Distinguish empty extraction from failure | Enrichment design |
