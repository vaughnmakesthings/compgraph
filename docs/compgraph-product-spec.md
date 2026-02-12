# CompGraph — Product Specification v1.0

## Competitive Intelligence Platform for Field Marketing Agencies

**Author:** Vaughn + Claude
**Date:** February 2026
**Status:** Design Phase

---

## 1. Product Vision

CompGraph is an internal competitive intelligence tool that transforms public job postings from competing field marketing agencies into actionable business intelligence. By scraping, enriching, and analyzing ATS data daily, CompGraph surfaces hiring velocity trends, client-brand relationships, pay benchmarking, and talent market pressure — giving Mosaic Sales Solutions a persistent information advantage.

The system is designed for **long-term data retention** as a core asset. Historical posting data becomes irreplaceable over time and constitutes the product's primary competitive moat.

---

## 2. Users & Access

### v1 (Internal)
- **Primary users:** Vaughn (daily driver), Mosaic leadership (meeting-ready views)
- **Access model:** Invite-only, authenticated web access
- **Deployment:** Open web, accessible to authorized users anywhere

### Future Expansion
- Additional Mosaic team members (BD, operations, regional directors)
- Architecture must support multi-user auth from day one

---

## 3. Target Companies

| Company | ATS Platform | Career Site | Scrape Method |
|---------|-------------|-------------|---------------|
| MarketSource | iCIMS | `applyatmarketsource-msc.icims.com` | iCIMS portal scraping |
| 2020 Companies | Workday | `2020companies.wd1.myworkdayjobs.com/External_Careers` | Workday CXS API |
| BDS Connected Solutions | iCIMS | `careers-bdssolutions.icims.com` | iCIMS portal scraping |
| T-ROC | Custom/TBD | `jobs.trocglobal.com` | Requires inspection |

**Design for extensibility** — adding a new competitor should require only a config entry and (if new ATS type) a scraper adapter.

---

## 4. Core Use Cases

### 4.1 Hiring Velocity Tracking
Monitor how aggressively each competitor is hiring over time. Surface trend lines, spikes (program launches), and declines (program losses). Enable comparison across competitors on the same time axis.

### 4.2 Client Brand Detection
Extract and classify every brand/company name mentioned in postings. Differentiate between:
- **Client Brand** — the brand being represented (e.g., Qualcomm, Samsung, Beats)
- **Retail Channel** — the store where reps deploy (e.g., Best Buy, Walmart, Target, Costco)

Track brand-to-agency relationships over time. Alert when new brands appear or existing brands disappear.

### 4.3 Pay Intelligence
Extract compensation data from postings: hourly rates, salary ranges, commission structures, benefits language. Benchmark by role type, geography, and competitor.

### 4.4 Posting Lifecycle Analysis
Track how long postings stay open, how often the same role is reposted (turnover signal), bulk posting events (program launches), and day-of-week posting patterns.

---

## 5. Data Architecture

### 5.1 Core Principles

1. **Append-only** — never mutate historical records. Every daily scrape creates snapshot records.
2. **Never delete** — when a posting disappears from the live site, mark `last_seen_at` but retain all data permanently.
3. **Store full, tag sections** — capture complete raw posting text, then use LLM enrichment to segment and classify. Dedup boilerplate at query time, not storage time.
4. **Fingerprint for identity** — link reposts of the same underlying role via fuzzy composite key (normalized title + location + brand).

### 5.2 Entity Model

```
┌─────────────────────────────────────────────────────────┐
│                    DIMENSION TABLES                      │
├──────────────┬──────────────┬───────────┬───────────────┤
│  companies   │   brands     │ retailers │   markets     │
│  (agencies)  │   (clients)  │ (stores)  │  (DMAs/metro) │
└──────┬───────┴──────┬───────┴─────┬─────┴───────┬───────┘
       │              │             │             │
       └──────────────┴─────────────┴─────────────┘
                          │
                ┌─────────┴──────────┐
                │   FACT TABLES      │
                ├────────────────────┤
                │  posting_snapshots │
                │  posting_enrichments│
                └─────────┬──────────┘
                          │
                ┌─────────┴──────────┐
                │  AGGREGATION TABLES │
                │  (materialized)     │
                ├─────────────────────┤
                │  daily_velocity     │
                │  brand_timelines    │
                │  pay_benchmarks     │
                │  lifecycle_metrics  │
                └─────────────────────┘
```

### 5.3 Table Definitions

#### `companies`
The four competitor agencies. Extensible.
```
id, name, slug, ats_platform, career_site_url, scraper_config (JSON), created_at
```

#### `brands`
Client brands extracted from postings. Grows organically.
```
id, name, slug, category (CE, wireless, appliance, etc.), first_seen_at, created_at
```

#### `retailers`
Retail channels where reps deploy.
```
id, name, slug, channel_type (big_box, carrier, club, grocery, etc.), created_at
```

#### `markets`
Geographic areas normalized to consistent granularity.
```
id, name, state, dma, latitude, longitude, created_at
```

#### `postings`
Canonical posting identity. One record per unique role (linked across reposts).
```
id, company_id, external_job_id, fingerprint_hash,
first_seen_at, last_seen_at, is_active (boolean),
times_reposted, created_at
```

#### `posting_snapshots`
Daily capture of every active posting. The append-only fact table.
```
id, posting_id, snapshot_date,
title_raw, location_raw, url,
full_text_raw, full_text_hash,
content_changed (boolean — did text change since last snapshot?),
created_at
```

#### `posting_enrichments`
LLM-extracted structured data. One record per posting (updated if raw text changes).
```
id, posting_id,
-- Classification
title_normalized, role_archetype, role_level (rep, lead, manager, director, etc.),
-- Entities
brand_id, retailer_id, market_id,
-- Compensation
pay_type (hourly, salary, commission, not_listed),
pay_min, pay_max, pay_currency,
pay_frequency (hourly, weekly, biweekly, annual),
commission_mentioned (boolean), commission_details,
benefits_mentioned (boolean), benefits_summary,
-- Content sections
content_role_specific (text — unique job content),
content_boilerplate (text — template/EEO/company description),
content_qualifications (text),
content_responsibilities (text),
-- Metadata
tools_mentioned (array), kpis_mentioned (array),
store_count_mentioned (integer, nullable),
travel_required (boolean),
employment_type (full_time, part_time, contract),
-- Enrichment tracking
enrichment_model, enrichment_version, enriched_at
```

#### `posting_brand_mentions`
Many-to-many: a single posting may mention multiple brands/retailers.
```
id, posting_id, entity_name, entity_type (brand, retailer, ambiguous),
confidence_score, resolved_brand_id, resolved_retailer_id
```

### 5.4 Materialized Aggregation Tables

Pre-computed on each daily scrape run. Dashboard queries hit these, not raw data.

#### `agg_daily_velocity`
```
date, company_id, brand_id, market_id,
active_postings, new_postings, closed_postings,
net_change
```

#### `agg_brand_timeline`
```
company_id, brand_id,
first_seen_at, last_seen_at, is_currently_active,
total_postings_all_time, current_active_postings,
peak_active_postings, peak_date
```

#### `agg_pay_benchmarks`
```
company_id, role_archetype, market_id, brand_id,
period (month),
avg_pay_min, avg_pay_max, median_pay_min, median_pay_max,
sample_size
```

#### `agg_posting_lifecycle`
```
company_id, role_archetype, brand_id, market_id,
period (month),
avg_days_open, median_days_open,
repost_rate (reposts / total postings),
avg_repost_gap_days
```

---

## 6. Data Pipeline

### 6.1 Daily Scrape Job

**Schedule:** Daily, overnight (2-4 AM ET)
**IP Mitigation:**
- Residential proxy rotation (one proxy per company domain per scrape)
- Randomized delays between requests (2-8 seconds)
- User-agent rotation
- Retry with backoff on rate limits
- Distribute scraping across a 2-hour window, not burst

**Process:**
1. For each company, fetch all active job listing URLs (list phase)
2. For each listing, fetch full detail page (detail phase — parallelized with rate limiting)
3. Compare `full_text_hash` against last snapshot — only flag `content_changed = true` if different
4. Write all snapshot records (even unchanged — supports lifecycle tracking)
5. Mark postings not seen today with `is_active = false`, set `last_seen_at`

### 6.2 LLM Enrichment Job

**Runs after:** Daily scrape completes
**Triggers on:** New postings OR postings where `content_changed = true`

**Two-pass enrichment:**

**Pass 1 — Section tagging + classification (Haiku 4.5)**
- Segment raw text into: role_specific, boilerplate, qualifications, responsibilities
- Classify: role_archetype, role_level, employment_type, travel_required
- Extract: pay data, benefits signals, tools/KPIs mentioned

**Pass 2 — Entity extraction (Sonnet 4.5)**
- Extract all company/brand/retailer names mentioned
- Classify each as: client_brand, retailer, or ambiguous
- Resolve against existing brands/retailers tables (fuzzy match)
- Create new brand/retailer records for first-time entities
- Assign confidence scores

**Cost estimate:**
- Backfill: ~$10-15 one-time (blended Haiku + Sonnet)
- Ongoing: ~$10-12/month

### 6.3 Aggregation Job

**Runs after:** Enrichment completes
**Process:** Rebuild all materialized aggregation tables from source data

---

## 7. Query Performance Strategy

### Fast Path (Dashboard)
All dashboard views query **materialized aggregation tables only**. These are small, pre-computed, and indexed. Response times should be <100ms regardless of total data volume.

Aggregation tables are rebuilt daily. For a tool refreshed once per day, this is sufficient — users always see current data instantly.

### Drill-Down Path (Detail Views)
When a user clicks into a specific posting or runs a custom filter, queries hit the enriched posting tables. These are indexed on the primary access patterns:
- `company_id + brand_id + snapshot_date`
- `company_id + market_id + snapshot_date`
- `brand_id + is_active`
- `fingerprint_hash` (for repost linkage)

### Deep Analysis Path (Ad-Hoc)
For custom queries or new analysis not covered by pre-built views, raw tables are available. May be slower on large date ranges but acceptable for exploratory use.

### Scaling Horizon
At ~1,275 postings/month with daily snapshots, you accumulate roughly:
- Year 1: ~460K snapshot rows
- Year 3: ~1.4M snapshot rows
- Year 5: ~2.3M snapshot rows

This is trivially small for any modern database. Performance won't be a concern for 5+ years even without optimization. Materialized views are a design choice for UX speed, not a necessity for data volume.

---

## 8. API Design (Backend-First, Frontend-Ready)

The backend exposes a RESTful API that serves all anticipated frontend views. Designing this contract now ensures zero rework when the frontend evolves from prototype to production.

### 8.1 Dashboard Endpoints

```
GET /api/velocity
  ?company_id=&brand_id=&market_id=&start_date=&end_date=&granularity=(day|week|month)
  Returns: time series of active/new/closed postings

GET /api/brands
  ?company_id=&status=(active|inactive|all)&sort=(first_seen|posting_count|last_seen)
  Returns: brand list with timeline metadata and current posting counts

GET /api/brands/:id/timeline
  ?start_date=&end_date=
  Returns: full history of a brand across all competitors

GET /api/pay
  ?role_archetype=&market_id=&company_id=&period=
  Returns: pay range benchmarks with comparison across competitors

GET /api/lifecycle
  ?company_id=&brand_id=&role_archetype=
  Returns: avg days open, repost rate, repost gap metrics

GET /api/alerts
  ?since=&type=(new_brand|brand_lost|volume_spike|volume_drop|pay_change)
  Returns: recent significant changes detected by the system
```

### 8.2 Detail Endpoints

```
GET /api/postings
  ?company_id=&brand_id=&market_id=&is_active=&page=&per_page=
  Returns: paginated posting list with enrichment summary

GET /api/postings/:id
  Returns: full posting detail — enrichment, all snapshots, lifecycle data

GET /api/postings/:id/history
  Returns: all snapshots for a posting, highlighting content changes

GET /api/companies
  Returns: competitor list with current aggregate stats

GET /api/companies/:id/summary
  Returns: full dashboard summary for one competitor
```

### 8.3 Auth Endpoints

```
POST /api/auth/login
POST /api/auth/invite
GET  /api/auth/me
POST /api/auth/logout
```

### 8.4 System Endpoints

```
GET /api/scrape/status
  Returns: last run time, success/failure per company, record counts

POST /api/scrape/trigger
  Manually trigger a scrape run (admin only)

GET /api/enrichment/status
  Returns: enrichment queue depth, last run stats
```

---

## 9. Alert System

Alerts are generated during the daily aggregation job by comparing today's aggregates against trailing averages and historical patterns.

### Alert Types

| Alert | Trigger Logic | Priority |
|-------|---------------|----------|
| **New Brand Detected** | Brand name appears in a competitor's postings for the first time | High |
| **Brand Lost** | Brand's active postings for a competitor drop to zero after being active 30+ days | High |
| **Volume Spike** | Competitor's new postings in a single day exceed 2x their 30-day daily average | Medium |
| **Volume Drop** | Competitor's active postings decline >25% week-over-week | Medium |
| **Pay Rate Change** | Average posted pay for a role/market shifts >10% vs. trailing 90 days | Medium |
| **Repost Surge** | A role is reposted 3+ times within 90 days (turnover signal) | Low |
| **New Market Entry** | Competitor posts in a DMA/state where they had no prior presence | Medium |

### Delivery
- v1: Alerts feed in dashboard (polling `/api/alerts`)
- v2: Email digest (daily or weekly summary)
- v3: Slack/webhook integration

---

## 10. Frontend Strategy

### Phase 1 — Streamlit Prototype
**Goal:** Validate data quality, enrichment accuracy, and dashboard views before investing in UI engineering.

- Connects directly to the same database the production API will use
- Implements the same views planned for the full app
- Deployed behind auth (Streamlit Cloud supports basic auth, or front with Cloudflare Access)
- Not throwaway — informs exactly what the production frontend needs

**Prototype Views:**
1. **Velocity Dashboard** — line charts of posting volume over time, filterable by competitor/brand/market
2. **Brand Radar** — table of all detected brands × competitors, with first/last seen and current count
3. **Posting Explorer** — searchable/filterable list of postings with enrichment data
4. **Alerts Feed** — chronological list of triggered alerts

### Phase 2 — Production Web App
**Goal:** Polished, presentation-ready UI accessible to invited users on the open web.

- Framework: React (Next.js) or similar — final choice deferred to stack selection
- Auth: Email invite + magic link or OAuth (no self-registration)
- Responsive but optimized for desktop/presentation (large screen conference room use case)
- Dark mode option for daily driver use
- Export: PDF snapshots of dashboard views for email/presentation distribution

**Production Views (building on prototype):**
1. **Executive Dashboard** — high-level KPIs across all competitors (total active postings, brand count, velocity trend)
2. **Competitor Deep Dive** — per-competitor view with brand mix, geographic footprint, pay distribution
3. **Brand Intelligence** — per-brand view across all competitors (who's hiring for this brand, where, at what pay)
4. **Market Map** — geographic visualization of competitor presence by DMA
5. **Pay Benchmarks** — side-by-side compensation comparison by role type and market
6. **Lifecycle Analysis** — time-to-fill and repost frequency heatmaps
7. **Alert Center** — filterable alert history with drill-down to underlying data
8. **Settings** — manage tracked companies, brand taxonomy, alert thresholds, user invites

---

## 11. Technology Considerations

**Stack selection is deferred** until this product spec is approved. The following are constraints and preferences to guide that decision:

### Backend Requirements
- Python preferred (scraping ecosystem, LLM SDKs, data processing)
- Must support scheduled jobs (cron-based scraping + enrichment + aggregation)
- Database must handle append-heavy write patterns efficiently
- Full-text search on posting content (for ad-hoc brand/keyword discovery)

### Database Requirements
- Strong time-series query performance (date-range aggregations are the primary access pattern)
- Materialized view or equivalent support
- Full-text search capability (native or via extension)
- Managed hosting preferred (minimal ops burden)
- Cost-effective at small scale, capable at large scale

### Auth Requirements
- Invite-only registration
- Session or token-based auth
- Role support (admin vs. viewer) for future multi-user scenarios

### Hosting Requirements
- Backend and scraper jobs can run on a single server/container initially
- Must support scheduled task execution
- Needs outbound internet access through residential proxies (scraping)

### LLM Requirements
- Anthropic API (Haiku 4.5 + Sonnet 4.5)
- Structured output (JSON mode) for enrichment extraction
- Must be callable from batch job context (not interactive)

---

## 12. Milestones

The milestone plan is structured around a **data-first validation loop**. We build the scraper and enrichment pipeline, let it collect real data for 1-2 weeks, then use that data to validate assumptions, test enrichment quality, and identify use cases before investing in API or UI layers.

### M1 — Foundation (Week 1-2)
Stack selection, project setup, and core data infrastructure.

- [ ] Finalize stack selection based on this spec
- [ ] Set up project repo, database, and development environment
- [ ] Implement data model (all tables, indexes, constraints)
- [ ] Build iCIMS scraper adapter (covers MarketSource + BDS)
- [ ] Build Workday CXS API scraper adapter (covers 2020 Companies)
- [ ] Inspect `jobs.trocglobal.com` and build T-ROC scraper adapter
- [ ] Implement daily scrape orchestrator with proxy rotation
- [ ] Build snapshot diffing logic (content change detection)

**Exit criteria:** All four scrapers run successfully and write raw snapshots to the database.

### M2 — Enrichment Pipeline (Week 3)
LLM enrichment that transforms raw postings into structured intelligence.

- [ ] Build LLM enrichment pipeline — Pass 1: Haiku (section tagging, classification, pay extraction)
- [ ] Build LLM enrichment pipeline — Pass 2: Sonnet (brand/retailer entity extraction and classification)
- [ ] Implement posting fingerprinting and repost linkage
- [ ] Run initial backfill enrichment on all captured postings
- [ ] Verify enrichment output with manual spot checks (~50 postings across all 4 competitors)

**Exit criteria:** Enrichment runs end-to-end. Spot checks confirm brand vs. retailer classification is directionally accurate. Known issues logged for tuning.

### 🔄 M3 — Data Collection Period (Week 4-5)
**The scraper and enrichment pipeline run daily on autopilot.** No new feature development. This phase exists to:

1. **Accumulate real data** — build a baseline of 10-14 daily snapshots across all competitors
2. **Validate reliability** — confirm scraper runs complete without failures, proxies hold, no rate limiting
3. **Assess enrichment quality** — review LLM output across a growing corpus; log misclassifications and edge cases
4. **Observe real patterns** — look at the data manually via SQL to see what's actually there:
   - How many postings include pay data? Is it enough to benchmark?
   - Are brand/retailer classifications clean or noisy?
   - What role archetypes are emerging? Do they need manual taxonomy tuning?
   - Are repost fingerprints linking correctly?
   - What changes day-over-day? How much churn is there?
5. **Identify use cases from real data** — let the data surface what's interesting rather than building views based on assumptions

**Activities during this phase:**
- [ ] Daily: monitor scrape logs, flag failures
- [ ] Day 3-4: first data quality review (SQL queries against enrichment tables)
- [ ] Day 7: comprehensive data quality audit — enrichment accuracy, entity resolution, fingerprint linkage
- [ ] Day 10-14: analysis session — what does the data actually tell us? What views matter most?
- [ ] Document findings: enrichment accuracy rates, data gaps, surprises, revised use case priorities
- [ ] Tune enrichment prompts based on observed errors
- [ ] Re-run enrichment on any postings affected by prompt changes

**Exit criteria:** 10+ days of clean daily snapshots. Enrichment accuracy validated. Revised use case priorities documented based on real data. Confidence that the foundation is solid.

### M4 — Aggregation & API (Week 6-7)
Build the query layer, informed by what the real data actually looks like.

- [ ] Build aggregation job (materialized tables) — scope refined by M3 findings
- [ ] Implement dashboard API endpoints (velocity, brands, pay, lifecycle)
- [ ] Implement detail API endpoints (postings, companies)
- [ ] Implement alert generation logic — thresholds informed by observed data patterns
- [ ] Implement auth endpoints (invite-only)
- [ ] API documentation

**Exit criteria:** All endpoints return real data. Alert logic generates meaningful signals (not noise).

### M5 — Prototype UI (Week 8-9)
Streamlit prototype connected to the live API. Validates that the views are useful before investing in a production frontend.

- [ ] Velocity dashboard — posting volume over time, filterable by competitor/brand/market
- [ ] Brand radar — all detected brands × competitors, with timelines
- [ ] Posting explorer — searchable/filterable list with enrichment data
- [ ] Alerts feed — triggered alerts with drill-down
- [ ] Deploy behind auth (Cloudflare Access or equivalent)

**Exit criteria:** Vaughn uses the prototype daily for 1+ week. Leadership can view it. Feedback captured on what works, what's missing, what to change.

### M6 — Tuning & Hardening (Week 10-11)
Fix what the prototype revealed. Harden for ongoing use.

- [ ] Refine enrichment prompts based on accumulated error patterns
- [ ] Tune alert thresholds to reduce noise
- [ ] Build brand/retailer taxonomy management (merge duplicates, correct misclassifications)
- [ ] Refine role archetype normalization
- [ ] Add monitoring/alerting for scraper failures
- [ ] Performance testing on dashboard queries

**Exit criteria:** System runs reliably with minimal manual intervention. Data quality is presentation-grade.

### M7 — Production UI (Week 12+)
Only after the prototype has proven the views and the data quality supports it.

- [ ] Frontend framework selection (informed by prototype experience)
- [ ] Implement production dashboard views
- [ ] Auth flow (invite + magic link)
- [ ] Export/PDF capability for leadership presentations
- [ ] Deploy to production
- [ ] Decommission Streamlit prototype

---

## 13. Open Questions

1. **T-ROC ATS identification** — Need to inspect `jobs.trocglobal.com` to determine scraping approach (may be Workday, custom CMS, or third-party platform).
2. **Brand taxonomy seeding** — Should we pre-seed the brands table with known CE/wireless brands, or let the system discover them purely from enrichment?
3. **Market normalization** — DMA, metro area, or state-level? DMA is most useful for field marketing but requires a mapping table.
4. **Historical backfill** — Can we get any historical posting data from Internet Archive/Wayback Machine for the target career sites, or do we start from scrape date zero?
5. **Proxy provider selection** — Need to evaluate residential proxy services (Bright Data, Oxylabs, SmartProxy, etc.) for reliability and cost.

---

## Appendix A: Estimated Ongoing Costs

| Item | Monthly Cost |
|------|-------------|
| LLM enrichment (Haiku + Sonnet blended) | ~$12 |
| Database hosting (managed Postgres or equivalent) | ~$15-50 |
| Compute (scraper + API server) | ~$10-30 |
| Residential proxies (4 domains, daily scrape) | ~$20-50 |
| Domain + SSL | ~$1 |
| **Total** | **~$60-145/month** |

## Appendix B: ATS Scraping Pattern Reference

### iCIMS (MarketSource, BDS Connected Solutions)
iCIMS career portals typically follow these patterns:
- **List endpoint:** `https://{subdomain}.icims.com/jobs/search` — often server-rendered HTML or AJAX fragments
- **Detail endpoint:** `https://{subdomain}.icims.com/jobs/{job_id}/{slug}/job` — full posting page
- Each company's portal may be configured differently — inspect network calls per target
- Less uniform than Workday's CXS API; may require per-company tuning
- Server-rendered pages can be scraped with plain HTTP + HTML parsing (no JS rendering needed in most cases)

### Workday (2020 Companies)
Workday career sites expose a structured CXS (Candidate Experience) API:
- **Search endpoint:** `https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` — returns JSON with pagination
- **Detail endpoint:** `https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs/{job_id}` — returns full posting as structured JSON
- Significantly easier to scrape than iCIMS — structured JSON responses, no HTML parsing needed
- Pagination via `offset` and `limit` parameters
- Supports filtering by location, job category, etc.

## Appendix C: Key Metrics Definitions

- **Hiring Velocity:** Count of net new postings per time period
- **Active Postings:** Postings currently live on the career site
- **Time-to-Fill:** Days between `first_seen_at` and `last_seen_at` for a posting
- **Repost Rate:** (Postings with 2+ appearances) / (Total unique postings) over trailing period
- **Repost Gap:** Average days between disappearance and reappearance of a reposted role
- **Brand Tenure:** Duration between first and last appearance of a brand in a competitor's postings
- **Market Density:** Number of active postings per DMA for a given competitor
