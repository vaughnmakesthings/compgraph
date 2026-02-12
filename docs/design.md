# CompGraph — Technical Design

> Competitive intelligence platform. Scrapes job postings from 4 competing field marketing agencies, enriches via LLM, surfaces hiring velocity, brand relationships, pay benchmarks, and posting lifecycle metrics.

## Section Index

Use this index to load specific sections by line range. **Never load the entire file at once.**

| Section | Lines | Tokens (est.) | Load when |
|---------|-------|:---:|-----------|
| Architecture Overview | §1 | ~400 | Cross-cutting changes, onboarding |
| Data Pipeline | §2 | ~800 | Scraper, enrichment, or aggregation work |
| Scraper Adapters | §3 | ~700 | Building/modifying any scraper |
| LLM Enrichment Pipeline | §4 | ~800 | Enrichment prompts, entity extraction |
| Aggregation Engine | §5 | ~500 | Materialized table rebuilds |
| API Surface | §6 | ~600 | Endpoint implementation |
| Database Schema Notes | §7 | ~500 | Model changes, migration work |
| Error Handling & Retries | §8 | ~400 | Pipeline resilience |
| Proxy & IP Strategy | §9 | ~400 | Scraping infrastructure |
| Alert Generation | §10 | ~400 | Alert logic implementation |

**Total: ~5.5K tokens** — budget is ≤2K per session via selective loading.

---

## §1 Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                      DAILY PIPELINE                            │
│                                                                │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐     │
│  │ Scrape   │───▶│ Enrich (LLM) │───▶│ Aggregate        │     │
│  │ (4 ATS)  │    │ (2-pass)     │    │ (materialized)   │     │
│  └──────────┘    └──────────────┘    └──────────────────┘     │
│       │                │                      │                │
│       ▼                ▼                      ▼                │
│  posting_snapshots  posting_enrichments  agg_* tables          │
│                     posting_brand_mentions                      │
└───────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │    FastAPI API      │
                    │  (async, read-only) │
                    └────────────────────┘
```

**Key constraint:** Pipeline stages are sequential within a run (scrape must complete before enrichment, enrichment before aggregation). Parallelism is WITHIN each stage — 4 scrapers run concurrently, enrichment processes multiple postings concurrently.

**Data model:** Append-only. Never mutate historical records. Snapshots accumulate daily. Enrichments are versioned. Aggregation tables are rebuilt from source data each run.

---

## §2 Data Pipeline

### Schedule
- **Scrape:** Daily 2-4 AM ET, staggered across companies (not burst)
- **Enrich:** Triggered after scrape completes. Processes new postings + postings with `content_changed = true`
- **Aggregate:** Triggered after enrichment completes. Rebuilds all 4 materialized tables

### Pipeline Orchestrator

The orchestrator runs the 3 stages sequentially. Each stage reports success/failure per company. Partial failures in scraping (e.g., one company's site is down) should NOT block enrichment of already-captured data.

```python
async def run_daily_pipeline():
    # Stage 1: Scrape all companies concurrently
    scrape_results = await asyncio.gather(
        *[scrape_company(c) for c in companies],
        return_exceptions=True
    )
    # Stage 2: Enrich new/changed postings
    await enrich_pending_postings()
    # Stage 3: Rebuild aggregation tables
    await rebuild_aggregations()
```

### Snapshot Diffing

Each scrape captures ALL active postings. Compare `full_text_hash` against the last snapshot:
- Same hash → `content_changed = false` (still write the snapshot for lifecycle tracking)
- Different hash → `content_changed = true` (triggers re-enrichment)
- Posting absent → set `is_active = false`, update `last_seen_at` on the canonical posting

---

## §3 Scraper Adapters

### Architecture

Each ATS platform gets a scraper adapter that implements a common interface:

```python
class ScraperAdapter(Protocol):
    async def list_postings(self, company: Company) -> list[RawPosting]:
        """Fetch all active posting URLs/IDs from the career site."""
        ...

    async def fetch_detail(self, posting_url: str) -> PostingDetail:
        """Fetch full posting content from a detail page."""
        ...
```

### iCIMS Adapter (MarketSource, BDS Connected Solutions)

- **List:** `GET https://{subdomain}.icims.com/jobs/search` — server-rendered HTML, paginated
- **Detail:** `GET https://{subdomain}.icims.com/jobs/{id}/{slug}/job` — full posting page
- **Parsing:** HTML extraction (no JS rendering needed in most cases)
- **Quirks:** Each company's portal may be configured differently. Inspect network calls per target.
- **Rate limiting:** 2-8 second random delays between requests

### Workday CXS Adapter (2020 Companies)

- **List:** `POST https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` — returns JSON with pagination (`offset` + `limit`)
- **Detail:** `GET .../{job_id}` — returns structured JSON (no HTML parsing needed)
- **Advantages:** Structured JSON responses, built-in filtering (location, category)
- **Pagination:** Standard offset/limit, iterate until empty results

### T-ROC Adapter (TBD)

- **Site:** `jobs.trocglobal.com`
- **Status:** Requires inspection to determine ATS platform
- **Approach:** Inspect network traffic, identify API endpoints or HTML structure

### Custom Adapter Pattern

For new ATS types, create a new adapter module in `src/compgraph/scrapers/`:
1. Implement `ScraperAdapter` protocol
2. Add company entry to `companies` table with `ats_platform` and `scraper_config` JSON
3. Register in scraper factory/registry

---

## §4 LLM Enrichment Pipeline

### Two-Pass Architecture

Each posting goes through two sequential LLM passes. Separation keeps costs low (Haiku is ~10x cheaper) and allows different models for different tasks.

**Pass 1 — Classification & Extraction (Haiku 4.5)**
- Input: `full_text_raw` from `posting_snapshots`
- Tasks:
  - Segment raw text into sections: `role_specific`, `boilerplate`, `qualifications`, `responsibilities`
  - Classify: `role_archetype`, `role_level`, `employment_type`, `travel_required`
  - Extract pay data: `pay_type`, `pay_min`, `pay_max`, `pay_frequency`, commission/benefits signals
  - Extract: `tools_mentioned[]`, `kpis_mentioned[]`, `store_count_mentioned`
  - Normalize title: `title_normalized`
- Output: Structured JSON matching `posting_enrichments` schema
- Model: `claude-haiku-4-5-20251001`
- Temperature: 0.1 (factual extraction)

**Pass 2 — Entity Extraction (Sonnet 4.5)**
- Input: `full_text_raw` + Pass 1 sections (role_specific is most signal-dense)
- Tasks:
  - Extract ALL company/brand/retailer names mentioned
  - Classify each as: `client_brand`, `retailer`, or `ambiguous`
  - Fuzzy-match against existing `brands` and `retailers` tables
  - Create new records for first-time entities
  - Assign confidence scores (0.0-1.0)
- Output: Array of `posting_brand_mentions` records
- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.1 (entity extraction)

### Enrichment Triggers

- New posting (no prior enrichment record)
- Content changed (`content_changed = true` on latest snapshot)
- Manual re-enrichment (after prompt tuning)

### Prompt Design Principles

- System prompt restricts to provided context only — "Only extract entities that appear verbatim in the text"
- Include `reasoning` field positioned BEFORE answer fields in structured output schema
- Use `Literal` types for enum fields (role_level, pay_type, entity_type)
- Structured output via `client.messages.parse(output_format=Model)` (Anthropic native, GA — NOT Instructor; constrained decoding guarantees schema compliance)

### Cost Estimates

- Per posting: ~$0.002 (Haiku) + ~$0.01 (Sonnet) = ~$0.012
- Daily batch (~40 new postings): ~$0.50
- Monthly: ~$10-12
- Initial backfill (~1000 postings): ~$12

---

## §5 Aggregation Engine

### Materialized Tables

Four pre-computed tables rebuilt after each enrichment run. Dashboard queries hit ONLY these tables for <100ms response times.

**Rebuild Strategy:** Full rebuild from source data (not incremental). At projected volumes (460K snapshots/year), this remains fast. Switch to incremental only if rebuild time exceeds 60 seconds.

#### `agg_daily_velocity`
```sql
-- Active, new, and closed postings per day per dimension
INSERT INTO agg_daily_velocity (date, company_id, brand_id, market_id, ...)
SELECT snapshot_date, company_id, brand_id, market_id,
       COUNT(*) FILTER (WHERE is_active) as active_postings,
       COUNT(*) FILTER (WHERE first_seen_at = snapshot_date) as new_postings,
       COUNT(*) FILTER (WHERE last_seen_at = snapshot_date AND NOT is_active) as closed_postings
FROM postings JOIN posting_enrichments ...
GROUP BY snapshot_date, company_id, brand_id, market_id;
```

#### `agg_brand_timeline`
- Tracks brand-to-agency relationships over time
- `first_seen_at`, `last_seen_at`, `is_currently_active`
- `peak_active_postings` + `peak_date` for historical high-water mark

#### `agg_pay_benchmarks`
- Monthly pay ranges by `role_archetype` × `market` × `company` × `brand`
- avg/median for `pay_min` and `pay_max`
- `sample_size` for statistical significance

#### `agg_posting_lifecycle`
- Monthly metrics: `avg_days_open`, `median_days_open`, `repost_rate`, `avg_repost_gap_days`
- Segmented by `company` × `role_archetype` × `brand` × `market`

---

## §6 API Surface

### Design Principles
- Async FastAPI endpoints, all read-only against aggregation tables for dashboard
- Drill-down endpoints query enriched posting tables directly
- Standard pagination: `?page=&per_page=` with `Link` headers
- Filter parameters: `company_id`, `brand_id`, `market_id`, `start_date`, `end_date`
- All responses use Pydantic response models

### Dashboard Endpoints (aggregate tables)
| Endpoint | Table | Purpose |
|----------|-------|---------|
| `GET /api/velocity` | `agg_daily_velocity` | Time series of posting volume |
| `GET /api/brands` | `agg_brand_timeline` | Brand list with timeline metadata |
| `GET /api/brands/:id/timeline` | `agg_brand_timeline` | Single brand history across competitors |
| `GET /api/pay` | `agg_pay_benchmarks` | Pay range benchmarks |
| `GET /api/lifecycle` | `agg_posting_lifecycle` | Days open, repost rate metrics |
| `GET /api/alerts` | alerts (derived) | Recent significant changes |

### Detail Endpoints (enriched tables)
| Endpoint | Table(s) | Purpose |
|----------|----------|---------|
| `GET /api/postings` | postings + enrichments | Paginated posting list |
| `GET /api/postings/:id` | postings + enrichments + snapshots | Full posting detail |
| `GET /api/postings/:id/history` | posting_snapshots | Snapshot timeline |
| `GET /api/companies` | companies + aggregates | Competitor list with stats |
| `GET /api/companies/:id/summary` | multiple | Full competitor dashboard |

### System Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Liveness check (exists) |
| `GET /api/scrape/status` | Last run time, per-company results |
| `POST /api/scrape/trigger` | Manual scrape trigger (admin) |
| `GET /api/enrichment/status` | Enrichment queue depth |

---

## §7 Database Schema Notes

### Key Indexes
```sql
-- Primary access patterns
CREATE INDEX ix_snapshots_posting_date ON posting_snapshots(posting_id, snapshot_date);
CREATE INDEX ix_enrichments_company_brand ON posting_enrichments(company_id, brand_id);
CREATE INDEX ix_enrichments_company_market ON posting_enrichments(company_id, market_id);
CREATE INDEX ix_postings_fingerprint ON postings(fingerprint_hash);
CREATE INDEX ix_postings_active ON postings(is_active) WHERE is_active = true;
CREATE INDEX ix_brand_mentions_posting ON posting_brand_mentions(posting_id);

-- Aggregation table indexes (primary query dimensions)
CREATE INDEX ix_velocity_date_company ON agg_daily_velocity(date, company_id);
CREATE INDEX ix_brand_timeline_company ON agg_brand_timeline(company_id, brand_id);
CREATE INDEX ix_pay_benchmarks_period ON agg_pay_benchmarks(period, company_id);
CREATE INDEX ix_lifecycle_period ON agg_posting_lifecycle(period, company_id);
```

### Fingerprinting

Repost detection via composite fingerprint:
```python
fingerprint = hashlib.sha256(
    f"{normalize(title)}|{normalize(location)}|{brand_slug}".encode()
).hexdigest()
```

Postings with the same fingerprint are linked. `times_reposted` incremented on the canonical posting.

### Partitioning (Future)

At 460K rows/year, partitioning is unnecessary. Consider AFTER Year 3 (~1.4M rows):
- `posting_snapshots` — partition by `snapshot_date` (monthly)
- `agg_daily_velocity` — partition by `date` (yearly)

---

## §8 Error Handling & Retries

### Scraper Failures
- Per-company isolation: one company's failure doesn't block others
- Retry with exponential backoff: 3 attempts, base 30s
- On total failure: log error, mark company's scrape as failed, continue pipeline
- Enrichment processes whatever was successfully scraped

### Enrichment Failures
- Per-posting isolation: one posting's enrichment failure doesn't block batch
- LLM timeout: 60s per call, retry once
- Validation error (structured output): retry with same prompt (LLM non-determinism may fix)
- After 2 failures: skip posting, log for manual review
- Never block aggregation for enrichment failures

### Aggregation Failures
- Full rebuild is idempotent — safe to retry
- TRUNCATE + INSERT within transaction
- On failure: old aggregation data remains (stale but available)

---

## §9 Proxy & IP Strategy

### Residential Proxy Rotation
- One proxy per company domain per scrape session
- Randomized delays: 2-8 seconds between requests
- User-agent rotation from curated pool
- Distribute scraping across 2-hour window (2-4 AM ET)

### Rate Limit Response
- 429/rate limit → backoff 60s, retry with new proxy
- 403/blocked → rotate proxy + user-agent, retry
- 3 consecutive failures → skip company for this run, alert

### Provider Selection
Evaluate: Bright Data, Oxylabs, SmartProxy. Key criteria:
- Residential IP pool size
- Geographic targeting (US, metro-level)
- Concurrent session limits
- Cost per GB

---

## §10 Alert Generation

Alerts are generated during the daily aggregation job by comparing today's aggregates against trailing averages.

| Alert Type | Trigger | Priority |
|------------|---------|----------|
| New Brand Detected | Brand first appears in a competitor's postings | High |
| Brand Lost | Brand's active count drops to 0 after 30+ days active | High |
| Volume Spike | Day's new postings > 2x 30-day daily average | Medium |
| Volume Drop | Active postings decline >25% week-over-week | Medium |
| Pay Rate Change | Average pay shifts >10% vs 90-day trailing | Medium |
| Repost Surge | Same role reposted 3+ times in 90 days | Low |
| New Market Entry | Competitor posts in a DMA with no prior presence | Medium |

### Implementation
```python
async def generate_alerts(session: AsyncSession, run_date: date):
    alerts = []
    alerts.extend(await detect_new_brands(session, run_date))
    alerts.extend(await detect_brand_losses(session, run_date))
    alerts.extend(await detect_volume_spikes(session, run_date))
    # ... etc
    await session.execute(insert(Alert).values(alerts))
```

Delivery: v1 = API feed, v2 = email digest, v3 = Slack webhook.
