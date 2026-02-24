# Implementation Phases

## Roadmap Summary

**Current milestone:** M6 complete. M7 in planning (roadmap approved 2026-02-24).
**Next milestone:** M7 — Production UI (auth, eval tool consolidation, infrastructure hardening)

### Pipeline

```
M1 (foundation) ✅ → M2 (enrichment) ✅ → M3 (data collection) ✅ → M4 (aggregation + API) ✅ → M5 (dashboard migration) ✅ → M6 (tuning + hardening) ✅ → M7 (production UI) ← NEXT
```

### Future Constraints — Do NOT Build Yet

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| arq (replace APScheduler) | M8 | Current scheduler works; needs Redis (OPS-06) first |
| Anthropic Batch API | M8 | Needs eval tool quality validation first |
| Multi-worker support (Gunicorn) | M8 | Single uvicorn worker is fine at current scale |
| Infrastructure as Code (Terraform) | M8+ | 1 droplet doesn't justify Terraform overhead |
| Scraper expansion (new companies) | M8+ | Current 5 companies validate pipeline |
| Cross-source triangulation (LinkedIn/Press) | Indefinite | YAGNI — no second data source planned |
| Custom JWT auth | Never | Using Supabase Auth |
| Prisma / second ORM | Never | Frontend is pure API consumer |

### Architecture Pre-Commitments

These decisions are already made. Do not revisit without explicit user approval:

- **Aggregation strategy:** truncate+insert rebuild (not incremental), transactional
- **API layer:** read-only queries against aggregation tables, no writes
- **Enrichment:** 2-pass stays (Haiku + Sonnet), model swap only after eval tool validates quality
- **Entity resolution:** 3-tier (exact/slug/fuzzy) stays, thresholds tunable via config
- **Auth:** Supabase Auth — invite-only via magic link, user provisions account with name/password, admin/viewer roles. No public sign-up, no custom JWT.
- **Frontend data access:** Pure API consumer — Next.js calls FastAPI, no direct DB, no Prisma
- **Database platform:** Supabase Postgres
- **Background jobs:** Use service_role connection (bypasses RLS) for all orchestrators
- **API versioning:** `/api/v1/` prefix (prefix only, no version negotiation middleware)

---

## Current State (2026-02-24)

**M6 COMPLETE.** Full pipeline operational: scrape (5 companies) → enrich (2-pass LLM) → aggregate (7 materialized tables) → API (read-only). Next.js 16 frontend deployed to Vercel with 7 dashboard pages + 5 eval pages. Streamlit decommissioned. Dev server on DO Droplet with CD auto-deploy. Backend: 703 tests, 82% coverage. Frontend: 174 tests, 52% coverage.

**M7 roadmap approved.** See `docs/plans/m7-implementation-roadmap.md` for the authoritative implementation plan with 5 phases, dependency graph, and sprint sequencing.

See `docs/changelog.md` for session-by-session history.

---

### Phase 1: Foundation (M1) — COMPLETE

Goal: All four scrapers running, writing raw snapshots to the database.

| Task | Summary | Status | PR |
|------|---------|--------|-----|
| Project scaffold | FastAPI + SQLAlchemy models + Alembic + config | Done | — |
| Supabase setup | Database provisioning, connection config, .env | Done | — |
| iCIMS scraper | MarketSource + BDS adapter (HTML parsing + JSON-LD) | Done | #33 |
| Workday scraper | 2020 Companies + T-ROC adapter (CXS API, JSON) | Done | #34, #36 |
| Pipeline orchestrator | Daily coordinator with error isolation | Done | #35 |
| Proxy integration | Optional proxy + UA rotation for all adapters | Done | #38 |

---

### Phase 2: Enrichment Pipeline (M2) — COMPLETE

Goal: LLM enrichment transforms raw postings into structured intelligence.

| Task | Summary | Status | PR |
|------|---------|--------|-----|
| Pass 1 — Classification | Haiku 4.5: role archetype, level, pay, content sections | Done | #39 |
| Pass 2 — Entity Extraction | Sonnet 4.5: brand/retailer extraction, 3-tier resolution | Done | #39 |
| Fingerprinting | SHA-256 composite hash, repost detection, canonical linking | Done | #39 |
| Backfill & Validation | CLI backfill script + CSV spot-check validation | Done | #39 |

---

### Phase 3: Data Collection Period (M3) — COMPLETE

Goal: 10-14 days of daily pipeline runs on autopilot. Validate reliability and data quality.

| Task | Summary | Status |
|------|---------|--------|
| Streamlit dashboard + diagnostics | Pipeline Health, Posting Explorer, diagnostics | Done (PRs #56-#58) |
| Scraper fixes | BDS + MarketSource URLs, Acosta + Advantage dropped (DNS dead) | Done (PRs #112, #115) |
| DB hardening | Server defaults, FK indexes, Alembic direct connection | Done (PRs #114, #116) |
| Brand Intel dashboard | Live SQL brand/retailer intel page | Done (PR #117) |
| Codebase audit + circuit breaker | Code simplification, enrichment circuit breaker | Done (PR #129) |
| Daily pipeline runs | 7+ consecutive days stable | Done |
| Data quality review | SQL queries on enrichment accuracy | Done |
| OSL onboarding | 5th company (OSL Retail Services) scraped via iCIMS adapter | Done |

---

### Phase 4: Aggregation & API (M4) — COMPLETE

Goal: Query layer serving dashboard views from pre-computed aggregation tables.

| Task | Summary | Status |
|------|---------|--------|
| 7 aggregation jobs | velocity, brand_timeline, pay_benchmarks, lifecycle, churn_signals, coverage_gaps, agency_overlap | Done |
| Aggregation orchestrator | Truncate+insert rebuild, transactional, error isolation | Done |
| Dashboard API endpoints | velocity, brand-timeline, pay-benchmarks, lifecycle, churn-signals, coverage-gaps, agency-overlap | Done |
| Detail API endpoints | GET /api/postings (list + detail), GET /api/companies | Done |
| Pipeline API endpoints | scrape trigger/status/pause/stop, enrichment trigger/status, scheduler status/trigger/pause/resume | Done |
| Pipeline runs history | GET /api/pipeline/runs (scrape + enrichment history) | Done |

---

### Phase 5: Dashboard Migration (M5) — COMPLETE

Goal: Migrate from Streamlit to Next.js. All views via API.

| Task | Summary | Status |
|------|---------|--------|
| DO dev server migration | Pi → DO Droplet (165.232.128.28), Caddy reverse proxy, systemd | Done (PR #143) |
| CD pipeline | GitHub Actions CI → SSH deploy → health check | Done (PR #146) |
| Streamlit decommission | Dashboard service stopped, code deleted | Done |

---

### Phase 6: Tuning & Hardening (M6) — COMPLETE

Goal: Production-grade frontend, data quality, and operational reliability.

| Task | Summary | Status |
|------|---------|--------|
| Next.js 16 frontend | 7 pages: Dashboard, Competitors (+ dossier), Market, Hiring, Settings, Eval (5 sub-pages) | Done (PR #161) |
| Vercel deployment | compgraph.vercel.app, API proxy via vercel.json rewrite | Done |
| Pipeline controls UI | Trigger/pause/resume/stop scrape, enrichment status, scheduler controls | Done (PR #167) |
| Data quality fixes | Latest-enrichment CTE, brand dedup, coverage gaps alignment | Done |
| Frontend tests | 174 tests, 52.3% coverage | Done |
| Backend tests | 703 tests, 82.27% coverage | Done |
| Eval tool scaffold | 5 pages (Runs, Review, Accuracy, Leaderboard, Prompt Diff) + 5 Postgres models | Done (PR #161) |
| Deployment security | deploy-ci.sh hardening, password encoding, sudo env quoting | Done |

---

### Phase 7: Production UI (M7) — IN PROGRESS

Goal: Auth, eval tool consolidation, infrastructure hardening, production-ready platform.

**Authoritative plan:** `docs/plans/m7-implementation-roadmap.md`

| Phase | Goal | Key Deliverables | Status |
|-------|------|-----------------|--------|
| **A** | API Versioning + Quick Wins | `/api/v1/` prefix, timezone fix, pay bounds, ConfirmDialogs | Planned |
| **B** | Eval Tool Consolidation | Merge runner, wire POST /runs, OpenRouter/LiteLLM, corpus bootstrap, delete standalone app | Planned |
| **C** | Supabase Auth & RBAC | JWT middleware, invite flow, login/setup pages, RLS on all tables, rate limiting | Planned |
| **D** | Infrastructure | Redis, DB-backed run tracking, service layer extraction | Planned |
| **E** | Feature Sprint | Evidence trails, skeleton loaders, SWR for new components | Planned |

**Locked decisions:** See roadmap Section 2 for full table (target user, auth flow, providers, rejections).

**Sprint sequence:**
```
Week 1-2:  Phase A + Phase B.0 (corpus bootstrap)
Week 2-4:  Phase B.1 (runner merge) + Phase C.1-C.3 (auth middleware)
Week 4-5:  Phase C.4-C.6 (frontend auth + RLS) + Phase B cleanup
Week 5-6:  Phase D (Redis, run tracking, service layer)
Week 6-8:  Phase E (evidence trails, UX) + Phase B.2 (comparison engine)
Week 8+:   Phase B.3 (guided UX for business admins)
```

---

## Critical Path

```
Supabase setup + migrations                ✅ M1
  ↓
iCIMS + Workday scrapers                   ✅ M1
  ↓
Enrichment 2-pass (Haiku + Sonnet)         ✅ M2
  ↓
Data collection period                     ✅ M3
  ↓
Aggregation + API endpoints                ✅ M4
  ↓
Next.js frontend + Vercel deploy           ✅ M5-M6
  ↓
/api/v1/ prefix + quick wins               ← Phase A (M7)
  ↓
Eval tool consolidation                    ← Phase B (parallel track)
  ↓
Supabase Auth + RBAC + RLS                 ← Phase C (M7)
  ↓
Redis + infra hardening                    ← Phase D (M7)
  ↓
Evidence trails + UX features              ← Phase E (M7)
```

---

## Supporting Documents

| Document | Purpose |
|----------|---------|
| `docs/plans/m7-implementation-roadmap.md` | Authoritative M7 plan (phases, dependencies, file lists, code snippets) |
| `docs/reports/gap-analysis-consolidated.md` | Master audit across 9 technical domains + dependency map |
| `docs/reports/strategic-roadmap-refined.md` | Strategic review with PM corrections |
| `docs/reports/code-review-log.md` | Detailed findings with resolution status |
| `docs/reports/2026-02-24-engineering-disagreements.md` | ARCH-03, UX-03, QA-03 resolutions |
| `docs/changelog.md` | Session-by-session development history |
