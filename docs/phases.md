# Implementation Phases

## Current State (2026-02-15)

**M3 in progress (Day 1).** Dashboard (PRs #56-#58), scrape controls (pause/stop/force-stop), and enrichment JSON fence fix (PR #62) all merged. First T-ROC scrape: 98 postings, 98/98 enriched. 4 of 5 scrapers have broken URLs (career site changes). 309 tests passing, 69% coverage. Dev server + dashboard running at 192.168.1.69:8000/:8501.

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
| Fix broken scraper URLs | Advantage, Acosta, BDS, MarketSource career sites changed | TODO |
| Daily pipeline runs | Monitor scrape + enrichment, flag failures | In progress (Day 1) |
| Day 3-4: data quality review | SQL queries on enrichment accuracy | Pending |
| Day 7: comprehensive audit | Entity resolution, fingerprints, archetype distribution | Pending |
| Day 10-14: analysis session | What views matter most? Revise use case priorities | Pending |
| Tune enrichment prompts | Based on observed errors | Pending |

**Exit criteria:** 10+ days of clean snapshots. Enrichment accuracy validated. Use case priorities revised from real data.

---

### Phase 4: Aggregation & API (M4)

Goal: Query layer serving dashboard views from pre-computed aggregation tables.

#### Step 4a: Aggregation Jobs

- [ ] `agg_daily_velocity` rebuild job
- [ ] `agg_brand_timeline` rebuild job
- [ ] `agg_pay_benchmarks` rebuild job
- [ ] `agg_posting_lifecycle` rebuild job
- [ ] Full rebuild orchestrator (truncate + insert, transactional)

#### Step 4b: Dashboard API Endpoints

- [ ] `GET /api/velocity` — time series of posting volume
- [ ] `GET /api/brands` — brand list with timeline metadata
- [ ] `GET /api/brands/:id/timeline` — single brand history
- [ ] `GET /api/pay` — pay range benchmarks
- [ ] `GET /api/lifecycle` — days open, repost metrics
- [ ] `GET /api/alerts` — recent significant changes

#### Step 4c: Detail API Endpoints

- [ ] `GET /api/postings` — paginated posting list
- [ ] `GET /api/postings/:id` — full posting detail
- [ ] `GET /api/postings/:id/history` — snapshot timeline
- [ ] `GET /api/companies` — competitor list with stats
- [ ] `GET /api/companies/:id/summary` — competitor dashboard

#### Step 4d: Auth & System

- [ ] Auth endpoints (login, invite, me, logout)
- [ ] `GET /api/scrape/status` — pipeline status
- [ ] `POST /api/scrape/trigger` — manual trigger (admin)
- [ ] Alert generation logic

**Exit criteria:** All endpoints return real data. Alerts generate meaningful signals.

---

### Phase 5: Prototype UI (M5)

Goal: Streamlit prototype connected to live API. Validates views before production frontend.

- [ ] Velocity dashboard — line charts, filterable
- [ ] Brand radar — brands × competitors table
- [ ] Posting explorer — searchable list with enrichment
- [ ] Alerts feed — triggered alerts with drill-down
- [ ] Deploy behind auth

**Exit criteria:** Daily use for 1+ week. Leadership can view. Feedback captured.

---

### Phase 6: Tuning & Hardening (M6)

- [ ] Refine enrichment prompts from accumulated error patterns
- [ ] Tune alert thresholds to reduce noise
- [ ] Brand/retailer taxonomy management (merge dupes, correct misclassifications)
- [ ] Role archetype normalization
- [ ] Scraper failure monitoring/alerting
- [ ] Dashboard query performance testing

---

### Phase 7: Production UI (M7)

- [ ] Frontend framework selection
- [ ] Production dashboard views
- [ ] Auth flow (invite + magic link)
- [ ] Export/PDF capability
- [ ] Deploy to production

---

## Critical Path

```
Supabase setup + migrations         ✅ M1
  ↓
iCIMS + Workday scrapers            ✅ M1
  ↓
Pipeline orchestrator + proxy       ✅ M1
  ↓
Enrichment Pass 1 (Haiku)          ✅ M2
  ↓
Enrichment Pass 2 (Sonnet)         ✅ M2
  ↓
Data collection period (10-14 days) ← YOU ARE HERE (M3)
  ↓
Aggregation + API                   ← dashboard-ready (M4)
```
