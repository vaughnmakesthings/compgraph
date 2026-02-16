# Context Loading Plan

This document defines exactly which files Claude Code (or an orchestrated agent) should read for each development task. Stay within context budget while having everything needed to produce correct code on the first pass.

---

## How This Works

Context loading is **tiered**. Every session starts with Tier 0 (automatic). Then load the Tier 1 pack for your current task. Load Tier 2 only when you hit a wall or need reference material.

```
Tier 0: Always loaded (CLAUDE.md)                         ~2K tokens
Tier 1: Task-specific context pack                        ~3–8K tokens
Tier 2: Reference docs (load on demand)                   ~2–5K tokens each
───────────────────────────────────────────────────────────
Budget target: ≤15K tokens of project context per session
```

**Rule: Never load all of `docs/design.md` at once.** It's ~5.5K tokens. Read only the section relevant to your current task using the section index at the top of that file.

---

## Tier 0: Always Loaded

Claude Code reads `CLAUDE.md` automatically. It contains:
- Project structure and key files
- Stack and conventions
- How to run and test
- Agent crew selection pattern
- Quick-reference context loading table

**Session startup:** Also read `docs/changelog.md` (latest entry only) for continuity — what happened last session, what failed, and what's next.

---

## Tier 1: Task-Specific Context Packs

### Pack A: Building a Scraper Adapter

Use when implementing any file in `src/compgraph/scrapers/`.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §3 Scraper Adapters | Adapter protocol, ATS patterns | ~700 |
| `docs/design.md` → §9 Proxy & IP Strategy | Rate limiting, proxy rotation | ~400 |
| `docs/design.md` → §8 Error Handling | Retry strategy, failure isolation | ~400 |
| `src/compgraph/db/models.py` → Company, Posting, PostingSnapshot models | Target schema | ~600 |
| The specific scraper file being built/modified | Current state | ~200–500 |

**ATS-specific additions:**

| ATS Type | Also load | Why |
|----------|-----------|-----|
| iCIMS | `docs/references/icims-scraping.md` → **UC section first**, then §1–§2 + §6 | **3 unresolved conflicts** — validate with curl before coding. iframe bypass, JSON-LD, selectors |
| Workday | `docs/compgraph-product-spec.md` → Appendix B (Workday section) | CXS API endpoints, JSON structure |
| T-ROC | Notes from site inspection (when available) | Custom ATS discovery |

**Anti-bot risk note:** [JobFunnel](https://github.com/PaulMcInnis/JobFunnel) (2.1K stars) was **archived Dec 2025** specifically because aggressive anti-automation measures made lightweight scraping infeasible. Proxy rotation and rate limiting are mandatory, not optional. If iCIMS starts requiring full browser rendering, evaluate [Crawl4AI](https://github.com/unclecode/crawl4ai) (60K stars) as a fallback engine — it handles JS rendering, crash recovery, and structured CSS extraction. See `docs/references/similar-projects-research.md` for full analysis.

**Total: ~2.5K–3.5K tokens**

**Recommended agent:** `python-backend-developer` (project-level) for implementation, `voltagent-core-dev:backend-developer` for async patterns.

---

### Pack B: Enrichment Pipeline (Modifying/Debugging)

Use when modifying or debugging any file in `src/compgraph/enrichment/`.

**M2 implemented the full pipeline (PR #39).** This pack is now for modifications, prompt tuning, and debugging.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §4 LLM Enrichment Pipeline | Two-pass architecture, prompt principles | ~800 |
| `src/compgraph/enrichment/schemas.py` | Pass1Result, Pass2Result, EntityMention schemas | ~400 |
| `src/compgraph/enrichment/orchestrator.py` | Batch processing, concurrency, status tracking | ~500 |
| The enrichment module being modified | Current state | ~200–500 |

**Module-specific additions:**

| Module | Also load | Why |
|--------|-----------|-----|
| `pass1.py` | `prompts.py` (PASS1_SYSTEM_PROMPT) | Haiku classification prompt |
| `pass2.py` | `prompts.py` (PASS2_SYSTEM_PROMPT) | Sonnet entity extraction prompt |
| `resolver.py` | `db/models.py` → Brand, Retailer | Entity resolution targets, slug matching |
| `fingerprint.py` | `db/models.py` → Posting (fingerprint_hash, times_reposted) | Repost detection schema |
| `queries.py` | `db/models.py` → PostingEnrichment, PostingSnapshot | Query join patterns |

**Key implementation patterns (from M2 review):**
- Pass 2 completion tracked via `enrichment_version` containing "pass2" (NOT PostingBrandMention existence)
- Failed postings tracked via `exclude_ids` set to prevent batch livelock
- Entity creation uses `begin_nested()` savepoints for concurrent safety
- Anthropic SDK types use `TYPE_CHECKING` guard + `cast()` (ruff strips unused imports)
- Run status uses `_compute_final_status()` aggregating both pass results

**Tier 2 escalation (load if hitting quality/cost issues):**

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/references/llm-extraction-optimization.md` → §2 Structured Output API | `messages.parse()` pattern, cache control, `stop_reason` handling | ~500 |
| `docs/references/llm-extraction-optimization.md` → §4 Haiku vs Sonnet Quality | Failure modes, hallucination risks, quality cliff | ~600 |
| `docs/references/llm-extraction-optimization.md` → §6 Pipeline Architecture | 5-layer validation, retry strategy, monitoring metrics | ~700 |

**Total: ~2K–3K tokens (core) + ~1.8K (Tier 2 if needed)**

**Recommended agent:** `python-backend-developer` for implementation, `voltagent-data-ai:prompt-engineer` for prompt tuning, `voltagent-lang:python-pro` for async patterns.

---

### Pack C: Building Aggregation Jobs

Use when implementing any file in `src/compgraph/aggregation/`.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §5 Aggregation Engine | Rebuild strategy, table definitions | ~500 |
| `src/compgraph/db/models.py` → all 4 agg_* models | Target schema | ~400 |
| `src/compgraph/db/models.py` → source models (postings, enrichments) | Input schema | ~400 |
| The aggregation module being built/modified | Current state | ~200–500 |

**Total: ~1.5K–2K tokens**

**Recommended agent:** `python-backend-developer` for implementation, `voltagent-data-ai:postgres-pro` for query optimization.

---

### Pack D: Building API Endpoints

Use when implementing any file in `src/compgraph/api/`.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §6 API Surface | Endpoint contracts, query patterns | ~600 |
| `src/compgraph/api/deps.py` | Dependency injection (get_db) | ~200 |
| `src/compgraph/db/models.py` → models queried by this endpoint | Target tables | ~300–600 |
| `src/compgraph/api/routes/health.py` | Existing pattern reference | ~200 |
| The route file being built/modified | Current state | ~200–500 |

**Endpoint-type additions:**

| Type | Also load | Why |
|------|-----------|-----|
| Dashboard endpoints | agg_* models | Query aggregation tables |
| Detail endpoints | fact + enrichment models | Query source tables |
| Auth endpoints | User model, config (JWT settings) | Auth implementation |
| System endpoints | Pipeline status tracking (when exists) | Scrape/enrichment status |

**Total: ~2K–3K tokens**

**Recommended agent:** `python-backend-developer` for implementation, `voltagent-core-dev:backend-developer` for FastAPI patterns, `voltagent-core-dev:api-designer` for REST design.

---

### Pack E: Database & Migrations

Use when modifying models in `src/compgraph/db/models.py` or working with Alembic.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §7 Database Schema Notes | Indexes, fingerprinting, partitioning | ~500 |
| `src/compgraph/db/models.py` | Current schema (full file) | ~1.5K |
| `src/compgraph/db/session.py` | Engine configuration | ~300 |
| `alembic/env.py` | Migration environment | ~300 |
| Latest migration file in `alembic/versions/` | Current DB state | ~300 |

**Tier 2 escalation (load for Supabase-specific issues):**

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/references/supabase-alembic-migrations.md` → §1 Connection Strings | Direct vs pooled, asyncpg crash fix, two-URL pattern | ~600 |
| `docs/references/supabase-alembic-migrations.md` → §2 Schema Isolation | `include_name` filter, auth.users FK, RLS in migrations | ~500 |
| `docs/references/supabase-alembic-migrations.md` → §3 Pool Configuration | Free tier limits (15 conn), pool_size tuning | ~400 |

**Total: ~3K tokens (core) + ~1.5K (Tier 2 if needed)**

**Recommended agent:** `python-backend-developer` for implementation, `voltagent-data-ai:postgres-pro` for Postgres-specific features.

---

### Pack F: Debugging Pipeline Failures

Use when a pipeline stage produces incorrect output or crashes.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/failure-patterns.md` | Known failure modes, cascades, mitigations | ~1K+ |
| `docs/design.md` → §8 Error Handling | Retry strategy, isolation patterns | ~400 |
| The failing module | Current implementation | ~500 |
| Its input/output models | Expected data shapes | ~300–600 |
| `docs/changelog.md` (latest entry) | What changed recently? | ~500 |

**Stage-specific additions:**

| Stage | Also load | Why |
|-------|-----------|-----|
| Scraper | `docs/design.md` → §3 + §9 | Adapter patterns, proxy config |
| Enrichment | `docs/design.md` → §4 | Prompt patterns, LLM failure modes |
| Aggregation | `docs/design.md` → §5 | Rebuild strategy, SQL patterns |
| API | `docs/design.md` → §6 | Response contracts, query patterns |

**Total: ~3K–5K tokens**

**Recommended agent:** `voltagent-qa-sec:debugger` for diagnosis, then `python-backend-developer` for fix.

---

### Pack G: Pipeline Orchestration

Use when modifying the daily pipeline coordinator or scheduling infrastructure.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §2 Data Pipeline | Pipeline sequencing, orchestrator pattern | ~800 |
| `docs/design.md` → §8 Error Handling | Stage isolation, partial failure handling | ~400 |
| `docs/workflow.md` | Development workflow, agent handoffs | ~1K |
| The pipeline orchestrator module | Current implementation | ~500 |

**Total: ~2.5K–3K tokens**

**Recommended agent:** `python-backend-developer` for implementation, `voltagent-data-ai:data-engineer` for pipeline architecture.

---

### Pack H: Alert System

Use when implementing alert generation or delivery.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §10 Alert Generation | Alert types, trigger logic, priorities | ~400 |
| `docs/compgraph-product-spec.md` → §9 Alert System | Full alert specification | ~500 |
| `src/compgraph/db/models.py` → agg_* models | Source data for alert comparisons | ~400 |

**Total: ~1.5K tokens**

---

## Tier 2: Reference Documents (Load On Demand)

These are NOT loaded by default. Pull them in only when needed.

### Internal Project References

| Document | When to load | Tokens (est.) |
|----------|-------------|:---:|
| `docs/compgraph-product-spec.md` | Full product spec — requirements, milestones, API contracts, data architecture | ~8K |
| `docs/design.md` (full) | Cross-cutting architecture changes ONLY | ~5.5K |
| `docs/phases.md` | Implementation roadmap, milestone tracking, current progress | ~2K |
| `docs/failure-patterns.md` | Known failure modes — load when debugging any pipeline issue | ~1K+ |
| `docs/workflow.md` | Development workflow, agent crew integration, review gates | ~2K |
| `docs/secrets-reference.md` | 1Password references, env var setup | ~500 |

### External Research (load by section)

| Document | When to load | For |
|----------|-------------|-----|
| `docs/references/llm-extraction-optimization.md` | Pricing, prompt patterns, Haiku vs Sonnet quality cliff, Batch API, validation stack | Enrichment pipeline, cost decisions |
| `docs/references/supabase-alembic-migrations.md` | Connection strings, schema isolation, pool config, migration safety | Database setup, Alembic config |
| `docs/references/icims-scraping.md` | iframe bypass, JSON-LD extraction, pagination, anti-scraping, portal types | iCIMS scraper (BDS, MarketSource) |
| `docs/references/workday-cxs-api.md` | CXS API endpoints, search/detail schemas, pagination, rate limits, tenant variations | Workday scraper (2020 Companies) |
| `docs/references/proxy-provider-comparison.md` | Provider evaluation, pricing, feature comparison | Proxy infrastructure |
| `docs/references/similar-projects-research.md` | Open-source project patterns, tooling decisions, anti-bot signals | Scraper design, enrichment tooling, pipeline architecture |

#### `docs/references/supabase-alembic-migrations.md` (~2K tokens total)

| Section | When to load | For |
|---------|-------------|-----|
| §1 Connection Strings | Setting up DATABASE_URL, configuring alembic/env.py | Connection type selection, asyncpg compatibility |
| §2 Schema Isolation | First autogenerate, auth.users FK decisions | `include_name` filter, RLS policy migrations |
| §3 Pool Configuration | Tuning pool for free tier, latency issues | Pool sizing, `pool_pre_ping`, avoiding NullPool for app |
| §4 Migration Safety | Setting up AI agent guardrails | Hooks, stairway tests, CI linting |

#### `docs/references/llm-extraction-optimization.md` (~3K tokens total)

| Section | When to load | For |
|---------|-------------|-----|
| §1 Pricing & Cost Math | Estimating enrichment costs, choosing model tier | Cost projections, batch sizing |
| §2 Structured Output API | Implementing extraction calls | `messages.parse()` + `output_config` pattern, cache control |
| §3 Prompt Patterns | Writing enrichment prompts | XML tags, few-shot design, temperature, CoT decisions |
| §4 Haiku vs Sonnet Quality | Understanding failure modes per model | Routing decisions, hallucination risks, quality cliff |
| §5 Cost Optimization Stack | Optimizing pipeline costs | Pre-filter, caching, Batch API, schema design |
| §6 Pipeline Architecture | Routing, validation, retry logic | 5-layer validation, escalation chain, monitoring metrics |

#### `docs/references/icims-scraping.md` (~2.5K tokens total)

| Section | When to load | For |
|---------|-------------|-----|
| §1 Portal Architecture | Understanding iframe bypass, portal types | Classic vs Modern, URL patterns, `?in_iframe=1` |
| §2 Search & Pagination | Implementing search page crawling | `pr=` parameter, page detection, CSS selectors, filter params |
| §3 Detail & JSON-LD | Extracting structured job data | Schema.org JobPosting, field mapping to CompGraph schema |
| §4 Anti-Scraping & Rate Limits | Configuring request parameters | Safe delays, CDN behavior, no-auth requirement |
| §5 Gotchas & Edge Cases | Debugging iCIMS scraper issues | Portal decommissioning, CSS fragility, entity encoding |
| §6 Code Pattern | Implementation reference | Two-phase scraper, search parser, JSON-LD extractor |

#### `docs/references/workday-cxs-api.md` (~3K tokens total)

| Section | When to load | For |
|---------|-------------|-----|
| §1 Endpoints & URL Pattern | Deriving API URLs from career page URL | Workday adapter setup |
| §2 Search API | Request body, pagination, facet filtering, response schema | Pagination implementation |
| §3 Detail API | Full field reference with reliability indicators | Detail parsing, field mapping |
| §4 Rate Limiting | Safe delays, concurrency limits | Scraper config |
| §5 Tenant Variations | What's consistent vs varies across companies | Multi-tenant adapter design |
| §6 Gotchas | Pagination traps, date handling, HTML parsing | Debugging scraper issues |
| §7 Code Pattern | Daily delta strategy, date parser, API call patterns | Implementation reference |

> **Note:** Reference docs are created as research is conducted. Not all may exist yet. Check `docs/references/` before loading.

---

## Agent Crew Context Loading

When launching a project-level agent via the orchestrator or manually, inject the relevant context pack into the agent's prompt:

| Agent | Default Pack | Always Include |
|-------|-------------|----------------|
| `python-backend-developer` | Pack matching current task (A-H) | Tier 0 (CLAUDE.md auto-loaded) |
| `code-reviewer` | Pack matching reviewed code + full `docs/design.md` section | changelog latest entry |
| `pytest-validator` | Test files + source files under test | Models for type checking |
| `spec-reviewer` | `docs/compgraph-product-spec.md` (relevant sections) | changelog latest entry |

### Voltagent Specialist Injection

Voltagent agents have NO project context. When launching them, include:
1. The specific question/task (not the whole project)
2. Relevant code snippets (paste, don't reference files)
3. Constraints and conventions that apply

Keep voltagent prompts under 3K tokens. They're specialists, not project owners.
