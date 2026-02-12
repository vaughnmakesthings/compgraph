# Research Prompts for Context Pack References

Generated 2026-02-12. Each prompt is designed for Anthropic Compass. After generation, compress to ~2K tokens and place in `docs/references/`.

---

## Tier 1: Phase 1 Blockers

### 1. iCIMS Portal Scraping

> Target file: `docs/references/icims-scraping.md`
> Context pack: Pack A (Scraper Adapters)
> Unblocks: MarketSource + BDS Connected Solutions scrapers (2 of 4 companies)

```
Scraping iCIMS career portals programmatically with Python: a practitioner's guide

I'm building a competitive intelligence system (CompGraph) that scrapes job postings daily from two companies using iCIMS career portals:
- MarketSource: applyatmarketsource-msc.icims.com
- BDS Connected Solutions: careers-bdssolutions.icims.com

Stack: Python 3.12+, httpx (async), BeautifulSoup/lxml for HTML parsing. No Selenium/Playwright unless absolutely required — prefer plain HTTP.

I need practitioner-validated answers to:

1. **iCIMS portal architecture**: How are iCIMS career sites structured? Is the job list server-rendered HTML or loaded via AJAX/API? Do they use consistent URL patterns across different company portals, or does each company's configuration vary? What are the actual endpoints for listing jobs and fetching detail pages?

2. **Pagination**: How does pagination work on iCIMS portals? Is it query parameter based (page=, offset=), infinite scroll via AJAX, or something else? What are the typical page sizes? How do you detect the last page?

3. **Job detail extraction**: What HTML structure do iCIMS job detail pages use? Are there consistent CSS selectors or element IDs for title, location, description, requirements, and compensation? Do different portal configurations change the HTML layout significantly?

4. **Anti-scraping measures**: Do iCIMS portals implement rate limiting, bot detection, CAPTCHAs, or IP blocking? What request headers are needed to avoid blocks? Do they check referrer, user-agent, or cookies? What request rates are safe for daily scraping?

5. **Hidden APIs**: Do iCIMS portals expose any JSON API endpoints (for search, filtering, or detail fetches) that are more reliable than HTML scraping? Some career platforms have undocumented APIs used by their search/filter UI — does iCIMS have these?

6. **Common pitfalls**: What breaks in practice? Encoding issues, JavaScript-dependent content, session/cookie requirements, geolocation redirects, portal downtime patterns?

7. **Practitioner code patterns**: What does a minimal working scraper look like? Include request headers, pagination loop, and detail page parsing. Focus on httpx async patterns.

Ground answers in real practitioner experience from GitHub repos, blog posts, Stack Overflow, or Reddit. Include specific URL patterns, HTTP methods, and response formats observed from live iCIMS portals.
```

---

### 2. Workday CXS API

> Target file: `docs/references/workday-cxs-api.md`
> Context pack: Pack A (Scraper Adapters)
> Unblocks: 2020 Companies scraper

```
Workday CXS (Candidate Experience) API for job posting extraction: complete technical reference

I'm building a daily job posting scraper targeting 2020 Companies, whose career site runs on Workday:
- URL: 2020companies.wd1.myworkdayjobs.com/External_Careers

Stack: Python 3.12+, httpx (async). The Workday CXS API returns structured JSON, so no HTML parsing needed.

I need a comprehensive technical reference covering:

1. **API endpoint structure**: What are the exact endpoints for job search and job detail on Workday CXS sites? Document the URL pattern with tenant/site variables. What HTTP methods are used (GET vs POST for search)? What Content-Type headers are required?

2. **Search API**: What is the request body schema for the search endpoint? How do pagination parameters work (offset, limit)? What is the maximum page size? What filtering parameters are available (location, job category, posted date)? What does the response JSON schema look like — specifically the job listing objects and pagination metadata?

3. **Detail API**: What does the job detail endpoint return? Document the full JSON response schema including: job title, location, description (HTML or plain text?), requirements, compensation data, posting date, job ID, and any other structured fields. How is rich text/HTML formatted in the response?

4. **Rate limiting and anti-scraping**: Does the Workday CXS API enforce rate limits? What are safe request intervals for daily scraping? Are there authentication requirements, API keys, or session tokens? Do they block by IP, user-agent, or request pattern?

5. **Tenant variations**: How much does the CXS API vary between different Workday tenants? Are the endpoints, response schemas, and pagination consistent, or do companies customize them? What fields are reliably present vs. optional?

6. **Edge cases and gotchas**: What breaks in practice? Empty results vs. end of pagination, job postings that exist on the site but don't appear in API results, encoding issues in job descriptions, date format variations, timezone handling.

7. **Working code pattern**: Show a minimal async Python scraper that paginates through all jobs, fetches details, and extracts structured data. Use httpx.

Ground answers in real practitioner experience — GitHub repos scraping Workday sites, blog posts, reverse engineering documentation. Include actual request/response examples from live Workday CXS endpoints.
```

---

### 3. Residential Proxy Providers

> Target file: `docs/references/proxy-provider-comparison.md`
> Context pack: Pack A (Scraper Adapters), design.md §9
> Unblocks: All scrapers (proxy rotation required for daily scraping)

```
Residential proxy providers for daily web scraping: a 2025-2026 comparison for small-scale career site monitoring

I'm building a competitive intelligence system that scrapes 4 career sites daily (iCIMS portals and Workday CXS API). The scraping volume is low — approximately 200-500 requests per day, distributed across a 2-hour window (2-4 AM ET). I need residential proxies to avoid IP blocks on career sites.

Requirements:
- US residential IPs (not datacenter — career sites block datacenter IPs)
- Async rotation: one proxy per target domain per scrape session
- Python integration via httpx (async HTTP client)
- Budget: $20-50/month
- Must work reliably for iCIMS and Workday domains

Compare the following providers with practitioner-validated data:

1. **Bright Data (formerly Luminati)**: Pricing model (per GB, per request, or flat?), residential pool size, US coverage, Python SDK or proxy endpoint format, minimum commitment, actual practitioner experience scraping career sites or similar low-volume monitoring use cases.

2. **Oxylabs**: Same dimensions. How does their residential proxy product compare to their Web Scraper API for this use case? Is the scraper API overkill for simple HTML/JSON fetching?

3. **SmartProxy**: Same dimensions. Often cited as the budget option — is the quality/reliability adequate for daily monitoring?

4. **Smaller alternatives**: Are there providers better suited for this specific use case (low volume, daily schedule, US residential IPs)? Consider: ScraperAPI, Zyte (formerly Scrapy Cloud), IPRoyal, SOAX.

For each provider, I need:
- Exact pricing for my volume (~500 requests/day, ~10 MB/day)
- Connection format (HTTP proxy URL with auth, or API endpoint?)
- Python/httpx integration pattern (how to configure proxy rotation)
- Reliability for career site scraping specifically
- Gotchas: minimum spend, bandwidth accounting tricks, IP quality issues, support responsiveness

Also cover:
- **Self-hosted alternative**: Is running your own proxy rotation (e.g., via Tor, free proxy lists, or VPN rotation) viable for this scale, or is a paid provider the clear winner?
- **The "do I even need proxies" question**: At 200-500 requests/day with 2-8 second delays across 4 domains, will career sites actually block me? What's the real-world threshold where proxies become necessary vs. nice-to-have?

Ground in practitioner experience. Include actual monthly costs from real users, not just listed pricing.
```

---

## Tier 2: Phase 1 Supporting

### 4. Async Pipeline Orchestration

> Target file: `docs/references/async-pipeline-orchestration.md`
> Context pack: Pack G (Pipeline Orchestration)
> Unblocks: Daily pipeline coordinator

```
Building async ETL pipeline orchestrators in Python with asyncio: patterns for daily scheduled jobs

I'm building a daily pipeline coordinator for a competitive intelligence system. The pipeline has three sequential stages that run nightly:

1. **Scrape** (4 concurrent scrapers, one per company) → writes to posting_snapshots table
2. **Enrich** (LLM API calls, ~40 postings/batch) → writes to posting_enrichments table
3. **Aggregate** (rebuild 4 materialized summary tables) → writes to agg_* tables

Stack: Python 3.12+, asyncio, SQLAlchemy 2.0 async, FastAPI (the pipeline runs as a background task or CLI command, not an HTTP endpoint).

Key constraints:
- Stages are sequential (scrape must finish before enrich, enrich before aggregate)
- Within each stage, work is parallel (4 scrapers concurrent, multiple enrichments concurrent)
- Partial failures within a stage should NOT block the next stage (if 1 of 4 scrapers fails, enrich the other 3)
- The system must track per-company success/failure and report status
- Target runtime: <30 minutes for the full pipeline

I need practitioner-validated patterns for:

1. **Orchestrator architecture**: What's the right abstraction for a sequential-stages-with-parallel-tasks pipeline in pure asyncio? Compare: simple async functions with gather(), a Stage/Pipeline class hierarchy, or using a lightweight framework (Prefect, Dagster, APScheduler). What do practitioners at this scale actually use vs. what's overengineered?

2. **Error isolation**: How do you implement "one company fails, others continue" cleanly with asyncio.gather()? The return_exceptions=True pattern — what are its gotchas? How do you distinguish between "scraper returned empty results" (maybe the site is down) vs "scraper raised an exception" (bug)?

3. **Stage handoff**: How do you pass results between sequential stages? Direct return values, database queries, or an intermediate data structure? What's the pattern for "enrich only what was successfully scraped"?

4. **Scheduling**: For a nightly job triggered at 2 AM ET — APScheduler inside the FastAPI process, a separate CLI entry point invoked by cron/systemd timer, or Celery/RQ? What do small teams actually use for single-server Python deployments?

5. **Observability**: Logging, timing, and status reporting for a multi-stage pipeline. How do you structure logs so you can see per-company, per-stage progress? What metrics matter?

6. **Concurrency control**: Semaphores for rate limiting within a stage (e.g., max 2 concurrent scrapers). Connection pool budgeting across stages. How to prevent database connection exhaustion when scraping and enriching overlap.

7. **Failure recovery**: If the pipeline crashes mid-enrichment, how do you resume without re-scraping? Idempotency patterns for each stage. Checkpoint strategies that aren't overkill for a nightly batch.

Focus on asyncio-native patterns. Avoid Airflow/Luigi/heavyweight frameworks — this is a single-server nightly job, not a distributed DAG. Ground in practitioner experience from similar small-scale ETL systems.
```

---

### 5. Unknown ATS Identification

> Target file: `docs/references/ats-identification-patterns.md`
> Context pack: Pack A (Scraper Adapters)
> Unblocks: T-ROC scraper + future competitor additions

```
Identifying and fingerprinting Applicant Tracking Systems (ATS) from career site URLs: a reverse engineering guide

I'm building scrapers for competing field marketing agencies' career sites. Three of four targets use known ATS platforms (iCIMS, Workday), but the fourth — jobs.trocglobal.com — uses an unknown platform. Future competitor additions will also require ATS identification.

I need a systematic methodology for determining what ATS platform powers a career site, and how to build a scraper for it. Specifically:

1. **ATS fingerprinting techniques**: How do you identify which ATS platform powers a career site? What HTML signatures, URL patterns, meta tags, JavaScript includes, cookie names, API endpoints, or HTTP headers are diagnostic? Document fingerprints for the major ATS platforms used by mid-market companies: iCIMS, Workday, Greenhouse, Lever, BambooHR, JazzHR, Paycom, ADP, UKG (UltiPro), Jobvite, SmartRecruiters, Ashby.

2. **Network traffic analysis**: When inspecting an unknown career site, what should you look for in browser DevTools Network tab? Common API endpoint patterns for job search/listing/detail across different ATS platforms. How to identify whether the site is server-rendered, SPA, or hybrid.

3. **Common ATS API patterns**: For the most popular ATS platforms (beyond iCIMS and Workday which I already have), document the typical API endpoint structure, authentication requirements, and response formats. Which platforms have well-documented APIs vs. which require reverse engineering?

4. **The custom CMS case**: When a career site doesn't use a recognizable ATS platform (custom WordPress plugin, embedded iframe from a niche provider, static HTML pages), what's the fallback scraping strategy? How do you build a reliable scraper for a one-off custom site?

5. **Scraper portability**: Once you've identified the ATS, how reusable is the scraper across different companies using the same platform? What's typically the same vs. what varies per-company (URL structure, field names, pagination, available fields)?

6. **ATS market share data**: What percentage of mid-market US companies (500-5000 employees) use each major ATS? This helps prioritize which platform adapters to build for future competitor additions.

Ground in practitioner experience. Include specific HTML/URL fingerprints that can be checked programmatically, not just manual inspection steps.
```

---

## Tier 3: Phase 2 Prep

### 6. Entity Resolution & Fuzzy Matching

> Target file: `docs/references/entity-resolution-fuzzy-matching.md`
> Context pack: Pack B (Enrichment Pipeline)
> Unblocks: Phase 2b — brand/retailer entity extraction

```
Entity resolution and fuzzy matching for company/brand names in Python: production patterns for competitive intelligence

I'm building an LLM enrichment pipeline that extracts brand and retailer names from job postings. After extraction, I need to resolve entities against existing database tables (brands, retailers) to avoid duplicates. The challenge: the same entity appears in many forms across different postings.

Examples of the matching problem:
- "Samsung" vs "Samsung Electronics" vs "SAMSUNG" vs "Samsung Mobile"
- "Best Buy" vs "BestBuy" vs "Best Buy Co." vs "Best Buy Mobile"
- "T-Mobile" vs "TMobile" vs "T Mobile" vs "Metro by T-Mobile"

Stack: Python 3.12+, PostgreSQL (Supabase), SQLAlchemy 2.0 async. The brands and retailers tables start empty and grow organically as new entities are discovered.

I need practitioner-validated patterns for:

1. **String similarity algorithms**: Compare approaches for company/brand name matching: Levenshtein distance, Jaro-Winkler, token sort ratio (fuzzywuzzy/rapidfuzz), TF-IDF + cosine similarity, phonetic matching (Soundex, Metaphone). Which works best for company names specifically? What similarity thresholds produce good results in practice?

2. **Python libraries**: rapidfuzz vs. thefuzz (fuzzywuzzy) vs. jellyfish vs. polyfuzz — which is the production standard for 2025? Performance characteristics at scale (matching against 500-1000 known entities). Async-friendly?

3. **Canonical name management**: When the same entity appears in multiple forms, how do you pick the canonical name? Longest form? Most frequent form? Manual curation? How do you handle legitimate distinct entities with similar names (e.g., "Samsung Electronics" vs "Samsung SDS")?

4. **Database-side matching**: PostgreSQL pg_trgm extension for trigram similarity, ts_vector for full-text search, or ILIKE with patterns — which approach works at this scale? Can Supabase's Postgres handle trigram indexes? Should matching happen in Python or SQL?

5. **The LLM + fuzzy hybrid**: Since I'm already calling an LLM for entity extraction, should I have the LLM also resolve entities against a provided list of known names? How does this compare to post-extraction fuzzy matching? What are the accuracy and cost trade-offs?

6. **Alias tables**: The pattern of maintaining an alias/synonym table that maps variant names to canonical entities. Schema design, population strategies (manual seeding, auto-discovery, LLM-assisted), and lookup patterns.

7. **Confidence scoring**: How to produce meaningful confidence scores for entity matches. What score ranges map to "auto-accept" vs "human review" vs "treat as new entity"?

Focus on the specific problem of company/brand name resolution in a competitive intelligence context. I care about precision over recall — a false match (merging two distinct brands) is worse than a false split (creating a duplicate entry that gets manually merged later).
```

---

### 7. Posting Fingerprinting & Repost Detection

> Target file: `docs/references/posting-fingerprinting-repost-detection.md`
> Context pack: Pack B (Enrichment Pipeline)
> Unblocks: Phase 2c — fingerprinting & repost linkage

```
Detecting reposted job listings across daily scrapes: fingerprinting, deduplication, and lifecycle tracking

I'm building a competitive intelligence system that scrapes job postings daily from 4 career sites. A core use case is detecting when the same role is reposted — this is a turnover signal (the position wasn't filled, or the hire didn't work out). I also need to track posting lifecycle: how long postings stay open, and detect bulk posting events (program launches).

The data model:
- `postings` table: canonical posting identity, linked across reposts via `fingerprint_hash`
- `posting_snapshots` table: daily capture of every active posting (append-only)
- Each snapshot has `full_text_raw`, `full_text_hash`, and `content_changed` boolean

Current fingerprinting approach (from design doc):
fingerprint = sha256(normalize(title) + "|" + normalize(location) + "|" + brand_slug)

I need practitioner-validated answers for:

1. **Fingerprint design**: Is title + location + brand sufficient to link reposts? What about: slight title variations ("Sales Rep" vs "Sales Representative"), location format differences ("New York, NY" vs "NYC" vs "New York"), or brand name variations? What normalization steps improve matching? Should the fingerprint include or exclude the company (since we're tracking competitors, company is already a dimension)?

2. **Normalization techniques**: For job titles — lowercasing, removing punctuation, standardizing abbreviations (Sr. → Senior, Mgr → Manager), removing level indicators? For locations — standardizing to city/state, handling "Remote" and "Multiple Locations"? What normalization produces the best dedup results for field marketing job postings specifically?

3. **Content change detection**: I store `full_text_hash` to detect when a posting's content changes between daily snapshots. What hashing approach handles minor formatting changes (whitespace, HTML artifacts) without generating false positives? Should I hash the raw text or a normalized version?

4. **Repost detection vs. content update**: How do you distinguish between "this is a repost of a closed position" (disappeared for N days, then reappeared) vs. "this posting was updated" (content changed but it never disappeared)? What gap duration signals a true repost vs. a scraping hiccup?

5. **Bulk posting detection**: How to detect program launches — when a competitor posts 10+ similar roles in a single day. Clustering approaches for grouping related postings. What patterns indicate a new client program vs. routine hiring?

6. **Lifecycle metrics**: Calculating time-to-fill (first_seen to last_seen), repost rate, and repost gap. Handling edge cases: postings that never close, postings with multiple gaps, postings that change significantly mid-lifecycle.

7. **Scale considerations**: At ~1,275 postings/month with daily snapshots, do I need anything beyond simple hash comparison? At what scale do more sophisticated dedup approaches (LSH, MinHash, embedding similarity) become necessary?

Ground in practitioner experience from job board aggregators, competitive intelligence tools, or HR tech platforms that deal with posting deduplication at scale.
```

---

## Usage Notes

- Process each Compass output through the same compression pipeline: identify signal, cut narrative, preserve tables/code/numbers, target ~2K tokens
- After compression, place in `docs/references/` and update `docs/context-packs.md` Tier 2 table + relevant Pack escalation sections
- Add any new failure patterns discovered to `docs/failure-patterns.md`
- Priority order: run Tier 1 prompts first (unblock Phase 1 critical path), Tier 2 during early implementation, Tier 3 before starting Phase 2
