# Similar Projects Research — GitHub Scan (Feb 12, 2026)

Searched for open-source projects updated in the last 6 months with code patterns reusable in CompGraph. Organized by CompGraph component.

---

## 1. Scraper Layer

### Crawl4AI — LLM-Friendly Web Crawler
- **Repo:** [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai)
- **Stars:** 60K+ | **Last Updated:** Active (v0.8.0)
- **Relevance:** HIGH — iCIMS HTML scraping, Workday dynamic page rendering
- **What it does:** Open-source web crawler optimized for LLM pipelines. Generates clean markdown. Supports JS execution, structured extraction via CSS/XPath schemas, and LLM-based extraction.
- **Reusable patterns:**
  - `JsonCssExtractionStrategy` — define schema with `baseSelector` + `fields[]` to extract structured data from HTML. Could replace manual BeautifulSoup parsing for iCIMS job cards.
  - `js_code` parameter — execute JavaScript to trigger dynamic content loading (useful for iCIMS pagination and Workday SPA rendering).
  - `prefetch=True` mode — 5-10x faster URL discovery for bulk job listing pages.
  - Crash recovery with `resume_state` callbacks — good pattern for long-running scrape sessions.
- **How to adopt:** Use as the scraping engine underneath our adapter layer. Each company adapter defines a `JsonCssExtractionStrategy` schema specific to that ATS. Crawl4AI handles rendering, JS execution, and structured output.

### chuchro3/WebCrawler — Workday Job Posting Crawler
- **Repo:** [chuchro3/WebCrawler](https://github.com/chuchro3/WebCrawler)
- **Stars:** Low | **Last Updated:** Older, but still relevant patterns
- **Relevance:** MEDIUM — Workday CXS scraping approach
- **What it does:** Crawls Workday `*.wd1.myworkdayjobs.com` sites. Intercepts the async API calls that Workday's SPA makes, extracts JSON directly.
- **Reusable patterns:**
  - **Intercept Workday's internal API** rather than parsing rendered HTML — the crawler reads the landing page's async API call to get structured JSON directly. This is exactly the CXS API approach described in our design doc.
  - Parallel detail fetching — once all job URLs are found on page 1, detail pages are fetched in parallel.
  - Output format: `{company: [{title, description, url}]}` — simple, clean per-company JSON.
- **Limitation:** Uses PhantomJS (deprecated). We'd use Playwright or httpx instead.

### iamgeorgelee/workday — Workday Parser
- **Repo:** [iamgeorgelee/workday](https://github.com/iamgeorgelee/workday)
- **Stars:** 1 | **Relevance:** LOW-MEDIUM
- **What it does:** 7-step methodology: Google search → find career page → intercept async API → extract URLs → paginate → parse JSON → store.
- **Reusable pattern:** The `WorkdayCrawler().get_by_company()` interface is clean. The approach of intercepting Workday's async API rather than scraping HTML confirms our CXS API strategy.

### nicobrenner/commandjobs — AI Job Search Tool
- **Repo:** [nicobrenner/commandjobs](https://github.com/nicobrenner/commandjobs)
- **Stars:** 169 | **Last Updated:** Oct 2025
- **Relevance:** MEDIUM — Has a Workday scraper module
- **What it does:** Multi-source job scraper with AI analysis. Recently added Workday scraper (NVIDIA, CrowdStrike, Red Hat, Salesforce). Uses SQLite + GPT for job-resume matching.
- **Reusable patterns:**
  - Modular scraper architecture in `job_scraper/` directory — each source is a separate module.
  - `gpt_interactions` table storing LLM analysis results as JSON — similar to our `posting_enrichments` pattern.
  - Country/date filtering for Workday scrapes.

### JobFunnel (ARCHIVED)
- **Repo:** [PaulMcInnis/JobFunnel](https://github.com/PaulMcInnis/JobFunnel)
- **Stars:** 2.1K | **Archived:** Dec 2025
- **Relevance:** MEDIUM — Adapter pattern, dedup strategy
- **What it does:** Multi-site job aggregator with dedup. Archived because modern job boards use aggressive anti-automation.
- **Reusable patterns:**
  - **Base Scraper abstract class** — standardized interface that all site-specific scrapers implement. Directly maps to our adapter pattern.
  - **Block list / status tracking** — jobs tracked as interested/applied/interview/offer/archive/rejected. Similar concept to our posting lifecycle tracking.
  - **Cache folder pattern** — raw scrape data cached locally for recovery, separate from processed DB.
- **Warning:** Archived due to anti-bot measures. Confirms we need proxy rotation and careful rate limiting.

---

## 2. Enrichment Layer

### Instructor — Structured LLM Outputs
- **Repo:** [567-labs/instructor](https://github.com/567-labs/instructor)
- **Stars:** 12.4K | **Last Updated:** Jan 2026 (v1.14.5)
- **Relevance:** VERY HIGH — Our enrichment pipeline's core extraction pattern
- **What it does:** Pydantic-based structured extraction from LLMs. Works with Anthropic Claude (Haiku + Sonnet). Automatic validation, retries, and streaming.
- **Reusable patterns:**
  - **Define Pydantic model → get validated extraction:** `client.chat.completions.create(response_model=PostingEnrichment, ...)` returns a validated Pydantic object. This is exactly our 2-pass enrichment pattern.
  - **Automatic retry on validation failure** — `max_retries=3` with error message feedback to LLM for self-correction. Eliminates manual retry logic.
  - **Provider abstraction** — `instructor.from_provider("anthropic/claude-3-5-haiku")` for Pass 1, switch to Sonnet for Pass 2. Same API, different model.
  - **Streaming partial responses** — useful for long job posting enrichments where you want incremental output.
- **How to adopt:** Use as the extraction layer in our enrichment pipeline. Define `PostingClassification` (Pass 1/Haiku) and `BrandEntityExtraction` (Pass 2/Sonnet) as Pydantic models matching our DB schema. Instructor handles validation, retries, and structured output.

### Google LangExtract
- **Repo:** [google/langextract](https://github.com/google/langextract)
- **Stars:** 31.3K | **Last Updated:** Active
- **Relevance:** MEDIUM — Alternative extraction approach
- **What it does:** Extract structured info from unstructured text with source grounding. Each extraction maps back to exact text location.
- **Reusable patterns:**
  - **Source grounding** — every extracted entity links to the exact span in the source text. Useful for our brand mention extraction where we want to know WHERE in the posting a brand was mentioned.
  - **Multi-pass extraction** — sequential passes improve recall on longer documents. Validates our 2-pass design.
  - **Text chunking strategies** — handles long documents by chunking and parallel processing.
- **Limitation:** Optimized for Gemini. Would need adapter work for Claude. Instructor is more practical for us.

### LLM-IE — Information Extraction Toolkit
- **Repo:** [daviden1013/llm-ie](https://github.com/daviden1013/llm-ie)
- **Stars:** 51 | **Last Updated:** Dec 2025 (v1.4.0)
- **Relevance:** MEDIUM — Entity extraction pipeline patterns
- **What it does:** Full IE pipeline: text chunking → context addition → LLM extraction → frame management. Supports async extraction (v1.4.0).
- **Reusable patterns:**
  - **Sentence-by-sentence extraction** outperforms whole-document extraction — validates our approach of structured section-by-section processing.
  - **PromptEditor class** — interactive prompt refinement before deployment. Good pattern for designing our enrichment prompts.
  - **Frame-based output** — extracted entities have `entity_text`, `start`, `end`, `attr{}`. Maps to our `posting_brand_mentions` with confidence scores.
  - **Async extract methods** (v1.4.0) — matches our async-everything architecture.

### spacy-llm
- **Repo:** [explosion/spacy-llm](https://github.com/explosion/spacy-llm)
- **Stars:** High | **Relevance:** LOW-MEDIUM
- **What it does:** Mix LLM-powered and traditional NLP components in spaCy pipelines. Few-shot entity recognition.
- **Reusable pattern:** Hybrid approach — use LLM for ambiguous entities, rule-based for obvious ones (e.g., known brand names). Could optimize our Pass 2 costs.

---

## 3. Pipeline / Architecture Layer

### benavlabs/FastAPI-boilerplate
- **Repo:** [benavlabs/FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate)
- **Stars:** 1.8K | **Last Updated:** Nov 2025 (v0.16.0)
- **Relevance:** HIGH — Production FastAPI + SQLAlchemy 2.0 async patterns
- **What it does:** Production-ready async FastAPI + SQLAlchemy 2.0 + Pydantic V2 + Alembic + Redis.
- **Reusable patterns:**
  - **FastCRUD library** — standardized CRUD operations with pagination. Could adopt for our read-only API against aggregation tables.
  - **JWT auth with access/refresh tokens** — maps to our `users` table auth requirements.
  - **ARQ for Redis-backed background jobs** — pattern for scheduling scrape/enrich/aggregate jobs.
  - **Tier-based rate limiting** — useful for API access control.
  - **Three-stage Docker deployment** — dev (Uvicorn), staging (Gunicorn+Uvicorn), prod (NGINX+Gunicorn).
  - **Decorator-based caching** — useful for aggregation query results that don't change between pipeline runs.

### modern-python/fastapi-sqlalchemy-template
- **Repo:** [modern-python/fastapi-sqlalchemy-template](https://github.com/modern-python/fastapi-sqlalchemy-template)
- **Stars:** 187 | **Relevance:** MEDIUM
- **What it does:** Dockerized async FastAPI + SQLAlchemy 2 with DI container.
- **Reusable patterns:**
  - **IOC container pattern** — dependency injection via `modern-di` library. Alternative to our current `get_db()` approach.
  - **Pytest with automatic transaction rollback** — test isolation without manual cleanup. Adopt for our test suite.
  - **ruff + mypy enforcement** — already using ruff, could add mypy.

### wynnemlo/scraping_jobsdb — Job Posting ETL Pipeline
- **Repo:** [wynnemlo/scraping_jobsdb](https://github.com/wynnemlo/scraping_jobsdb)
- **Stars:** Low | **Relevance:** MEDIUM — ETL architecture patterns
- **What it does:** Daily ETL pipeline: scrape JobsDB → data lake (raw HTML) → Spark transform → Postgres warehouse.
- **Reusable patterns:**
  - **Schema layering:** `raw.*` → `staging.*` → final tables. Maps to our scrape → enrich → aggregate flow.
  - **Idempotent DAGs** — every task designed for safe re-runs. Critical for our daily pipeline.
  - **Salary range dedup strategy** — cross-referencing the same job across salary filters to impute actual pay range. Creative approach we could adapt for cross-source dedup.
  - **SQL sanity checks** between pipeline stages.

### benpmeredith/jobspy — FastAPI Job Scraper
- **Repo:** [benpmeredith/jobspy](https://github.com/benpmeredith/jobspy)
- **Stars:** 3 | **Relevance:** LOW-MEDIUM
- **What it does:** FastAPI job scraper for LinkedIn/Indeed/ZipRecruiter with Supabase auth.
- **Reusable pattern:** Uses **Supabase for auth** with `users` table + RLS + JWT. Directly matches our auth setup.

---

## 4. Competitive Intelligence

### Procycons/Comperator
- **Repo:** [Procycons/Comperator](https://github.com/Procycons/Comperator)
- **Stars:** 11 | **Last Updated:** Jul 2024 (older)
- **Relevance:** LOW — General competitive intel patterns
- **What it does:** LLM-powered competitor analysis: crawl → classify → summarize → visualize (Streamlit).
- **Reusable patterns:**
  - **Config-driven competitor list** — `config.yaml` specifies companies + URLs. Maps to our company dimension table.
  - **Singleton LLM wrapper** for consistent API interactions.
  - **Modular pipeline:** `crawler.py` → `llm.py` → `analyzer.py` → `app.py`.

---

## Priority Adoption Recommendations

### Must-Evaluate (High Impact, Low Effort)

| Project | Pattern | CompGraph Component | Effort |
|---------|---------|-------------------|--------|
| **Instructor** | Pydantic-based structured extraction with Claude | Enrichment pipeline | Low — pip install, define models |
| **Crawl4AI** | JS-capable scraping with CSS schema extraction | Scraper adapters | Medium — replace manual parsing |
| **benavlabs/FastAPI-boilerplate** | Background jobs, caching, rate limiting patterns | API + Pipeline orchestration | Low — cherry-pick patterns |

### Should-Review (Good Patterns to Study)

| Project | Pattern | CompGraph Component |
|---------|---------|-------------------|
| **chuchro3/WebCrawler** | Workday CXS API interception approach | Workday scraper |
| **LLM-IE** | Sentence-level extraction, async extract, frame model | Enrichment pipeline |
| **scraping_jobsdb** | Schema layering (raw → staging → final), idempotent DAGs | Pipeline architecture |
| **JobFunnel** | Base Scraper abstract class, lifecycle status tracking | Adapter pattern |

### Nice-to-Know (Reference Only)

| Project | Insight |
|---------|---------|
| **LangExtract** | Source grounding (link extraction to exact text span) — future enhancement |
| **commandjobs** | Workday scraper module for 4 companies — validate our approach |
| **Comperator** | Config-driven competitor list pattern |

---

## Key Takeaways

1. **No direct competitor exists** — no open-source project combines ATS scraping + LLM enrichment + competitive intelligence analytics. CompGraph is novel in this combination.

2. **Instructor is the obvious choice** for our enrichment layer — 12K+ stars, active development, native Anthropic Claude support, Pydantic models map directly to our SQLAlchemy schemas.

3. **Crawl4AI could simplify our scraper layer** — instead of raw httpx/BeautifulSoup, use Crawl4AI's structured extraction with per-adapter CSS schemas. Handles JS rendering, pagination, crash recovery.

4. **The Workday CXS API interception pattern is validated** — multiple projects (WebCrawler, workday, commandjobs) all intercept Workday's internal async API rather than scraping rendered HTML.

5. **Our append-only / schema-layering design is industry-standard** — scraping_jobsdb uses the same raw → staging → final pattern. Idempotent pipeline tasks are a proven approach.

6. **Anti-bot is a real concern** — JobFunnel (2.1K stars) was archived specifically because of aggressive anti-automation. Proxy rotation and rate limiting are not optional.
