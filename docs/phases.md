# Implementation Phases

## Current State (2026-02-12)

**Foundation ready.** All 13 tables live on Supabase (Postgres 17). 4 target companies seeded. Dev environment hardened (hooks, CI, coverage, mypy). Repo at `vaughnmakesthings/compgraph` with branch protection. Next: first scraper adapter (iCIMS).

See `docs/changelog.md` for session-by-session history.

---

### Phase 1: Foundation (M1) — IN PROGRESS

Goal: All four scrapers running, writing raw snapshots to the database.

| Task | Summary | Status |
|------|---------|--------|
| Project scaffold | FastAPI + SQLAlchemy models + Alembic + config | Done |
| Agent crew | 4 project agents + hooks + voltagent integration | Done |
| Context management | docs/ structure, context packs, tiered loading | Done |
| Supabase setup | Database provisioning, connection config, .env | Done |
| Alembic migrations | Generate from models, run against Supabase | Done |
| iCIMS scraper | MarketSource + BDS adapter (HTML parsing) | Not started |
| Workday scraper | 2020 Companies adapter (CXS API, JSON) | Not started |
| T-ROC scraper | Inspect site, determine ATS, build adapter | Not started |
| Snapshot diffing | Content hash comparison, change detection | Not started |
| Pipeline orchestrator | Daily scrape coordinator with error isolation | Not started |
| Proxy integration | Provider selection, rotation config | Not started |

**Exit criteria:** All four scrapers run successfully and write raw snapshots to the database.

---

### Phase 2: Enrichment Pipeline (M2)

Goal: LLM enrichment transforms raw postings into structured intelligence.

#### Step 2a: Pass 1 — Classification (Haiku)

- [ ] Section tagging prompt (role_specific, boilerplate, qualifications, responsibilities)
- [ ] Classification extraction (role_archetype, role_level, employment_type, travel)
- [ ] Pay data extraction (pay_type, pay_min, pay_max, frequency, commission, benefits)
- [ ] Structured output schema matching `posting_enrichments` model
- [ ] Unit tests with fixture postings from each ATS type

#### Step 2b: Pass 2 — Entity Extraction (Sonnet)

- [ ] Brand/retailer entity extraction prompt
- [ ] Entity classification (client_brand, retailer, ambiguous)
- [ ] Fuzzy matching against existing brands/retailers tables
- [ ] New entity creation for first-time names
- [ ] Confidence scoring
- [ ] Output schema matching `posting_brand_mentions` model

#### Step 2c: Fingerprinting & Repost Linkage

- [ ] Composite fingerprint: normalize(title) + normalize(location) + brand_slug
- [ ] Dedup logic: match fingerprint against existing postings
- [ ] `times_reposted` increment on canonical posting

#### Step 2d: Backfill & Validation

- [ ] Initial backfill enrichment on all captured postings
- [ ] Manual spot checks (~50 postings across all 4 competitors)
- [ ] Document enrichment accuracy, log misclassifications

**Exit criteria:** Enrichment runs end-to-end. Spot checks confirm brand vs retailer classification is directionally accurate.

---

### Phase 3: Data Collection Period (M3)

Goal: 10-14 days of daily pipeline runs on autopilot. No new features — validate reliability and data quality.

- [ ] Daily: monitor scrape logs, flag failures
- [ ] Day 3-4: first data quality review (SQL queries)
- [ ] Day 7: comprehensive audit — enrichment accuracy, entity resolution, fingerprints
- [ ] Day 10-14: analysis session — what does the data say? What views matter most?
- [ ] Tune enrichment prompts based on observed errors
- [ ] Re-enrich affected postings after prompt changes

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
Supabase setup + migrations         ← unblocks everything
  ↓
iCIMS + Workday scrapers            ← covers 3 of 4 companies
  ↓
Pipeline orchestrator + proxy       ← daily scraping operational
  ↓
Enrichment Pass 1 (Haiku)          ← structured data from raw text
  ↓
Enrichment Pass 2 (Sonnet)         ← entity extraction
  ↓
Data collection period (10-14 days) ← validate quality
  ↓
Aggregation + API                   ← dashboard-ready
```

T-ROC scraper and alert system are supporting tasks that can be parallelized alongside the critical path.
