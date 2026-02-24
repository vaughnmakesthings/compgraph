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

**Recommended agent:** `python-backend-developer` for implementation, `python-pro` for async patterns.

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

**Recommended agent:** `python-backend-developer` for implementation, `python-pro` for async patterns.

---

### Pack C: Building Aggregation Jobs

Use when implementing any file in `src/compgraph/aggregation/`.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/design.md` → §5 Aggregation Engine | Rebuild strategy, table definitions | ~500 |
| `src/compgraph/db/models.py` → all 4 agg_* models | Target schema | ~400 |
| `src/compgraph/db/models.py` → source models (postings, enrichments) | Input schema | ~400 |
| Existing aggregation module (e.g. `daily_velocity.py`) | SQL query patterns as reference | ~500 |
| The aggregation module being built/modified | Current state | ~200–500 |

**Key patterns:**
- Aggregation strategy is truncate+insert (never incremental update) — see CLAUDE.md pre-commitments
- Use `aggregate_order_by()` from `sqlalchemy.dialects.postgresql` for ordered aggregates — SELECT-level `.order_by()` is a no-op for scalar aggregate functions
- Each job rebuilds one table inside a single transaction with error isolation

**Agg table → source mapping:**

| Agg Table | Source Tables | Key Columns |
|-----------|-------------|-------------|
| `agg_daily_velocity` | `postings`, `posting_snapshots` | company_id, snapshot date, counts |
| `agg_brand_timeline` | `posting_brand_mentions`, `postings` | brand_id, company_id, date range |
| `agg_pay_benchmarks` | `posting_enrichments`, `postings` | company_id, pay_range_min/max, role_type |
| `agg_posting_lifecycle` | `postings`, `posting_snapshots` | days_open, repost count, company_id |

**Total: ~2K–2.5K tokens**

**Recommended agent:** `python-backend-developer` for implementation, `database-optimizer` for query optimization.

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
| Aggregation endpoints (`/api/v1/aggregation/*`) | agg_* models | Query aggregation tables |
| Detail endpoints (`/api/v1/postings`, `/api/v1/companies`) | fact + enrichment models | Query source tables, pagination patterns |
| Auth endpoints | Use **Pack I** instead | Supabase Auth is complex enough for dedicated pack |
| Eval endpoints | Use **Pack J** instead | Eval tool consolidation has its own pack |
| System endpoints (`/api/v1/pipeline/*`, `/api/v1/scrape/*`) | Orchestrator state | Pipeline status, run history |

**Endpoint → agg table mapping:**

| Endpoint | Agg Table | Notes |
|----------|-----------|-------|
| `GET /api/v1/aggregation/velocity` | `agg_daily_velocity` | Time series, filter by company |
| `GET /api/v1/aggregation/brand-timeline` | `agg_brand_timeline` | Brand timeline + agency overlap |
| `GET /api/v1/aggregation/pay-benchmarks` | `agg_pay_benchmarks` | Filter by role/company |
| `GET /api/v1/aggregation/lifecycle` | `agg_posting_lifecycle` | Days open, repost metrics |

**Total: ~2K–3K tokens**

**Recommended agent:** `python-backend-developer` for implementation, `python-pro` for FastAPI patterns.

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

**Recommended agent:** `python-backend-developer` for implementation, `database-optimizer` for Postgres-specific features.

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

**Recommended agent:** `python-backend-developer` for diagnosis and fix.

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

**Recommended agent:** `python-backend-developer` for implementation.

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

### Pack I: Auth & Access Control (M7 Phase C)

Use when implementing Supabase Auth integration, JWT middleware, RLS policies, or role-based access.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/plans/m7-implementation-roadmap.md` → Section 6 (Phase C) | Full auth implementation plan with code snippets, route matrix, RLS tiers | ~2K |
| `src/compgraph/db/models.py` → User model | Existing schema: id, email, name, role, invited_by, created_at | ~200 |
| `src/compgraph/config.py` | Settings class — add SUPABASE_JWT_SECRET, AUTH_DISABLED | ~300 |
| `src/compgraph/api/deps.py` | Current get_db() dependency — add get_current_user, require_admin | ~200 |
| `docs/references/supabase-auth-fastapi.md` | Supabase Auth patterns (JWT verification, magic link, RBAC) | ~800 |

**Locked decisions (from roadmap Section 2):**
- Auth = Supabase Auth (invite-only via magic link, password login)
- No public signup — admin creates invite via in-app form
- Frontend SDK: `@supabase/supabase-js` only (no `@supabase/auth-ui-react`)
- Background jobs use service_role connection (bypass RLS)
- Test strategy: AUTH_DISABLED=true for unit/integration tests

**Roles:**

| Role | Access |
|------|--------|
| Admin | Invite users, pipeline control, eval tool, full access |
| Viewer | Read-only dashboard |

**New files to create:**
- `src/compgraph/api/auth.py` — JWT middleware, get_current_user, require_admin
- `web/src/app/login/page.tsx` — Login page
- `web/src/app/setup/page.tsx` — Account provisioning (magic link landing)
- `web/src/lib/auth-context.tsx` — Auth context provider + route protection
- `alembic/versions/xxxx_add_auth_uid.py` — Add auth_uid to users table
- `alembic/versions/xxxx_enable_rls.py` — Enable RLS + policies on all tables

**Total: ~3.5K tokens**

**Recommended agents:** `python-backend-developer` (backend middleware + migration), `react-frontend-developer` (login/setup pages + auth context), `security-reviewer` (RLS policy audit).

---

### Pack J: Eval Tool Consolidation (M7 Phase B)

Use when merging the standalone eval runner into the integrated Postgres-backed system.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/plans/m7-implementation-roadmap.md` → Section 5 (Phase B) | Full consolidation plan with file mapping, code snippets, phase breakdown | ~2K |
| `eval/eval/runner.py` | Source: working LLM runner to port | ~500 |
| `eval/eval/providers.py` | Source: LiteLLM wrapper with OpenRouter | ~400 |
| `eval/eval/config.py` | Source: 16-model catalog, concurrency, max_tokens | ~200 |
| `src/compgraph/eval/router.py` → line 529 area | Target: the stub TODO to replace | ~500 |
| `src/compgraph/eval/models.py` | Target: EvalRun, EvalResult, EvalCorpus, EvalComparison, EvalFieldReview models | ~600 |

**Key context:**
- The standalone `eval/` app has a working runner with LiteLLM/OpenRouter — this is the execution engine to port
- The integrated `src/compgraph/eval/` has Postgres models + API routes — this is the target
- `POST /api/eval/runs` is a stub at router.py:529 — it creates a DB record but calls zero LLMs
- OpenRouter is the provider (API credits available, `OPENROUTER_API_KEY` via 1Password)
- Target user is a business admin with some technical knowledge

**File mapping:**

| Source (eval/eval/) | Destination (src/compgraph/eval/) | Action |
|---------------------|----------------------------------|--------|
| runner.py | logic.py (new) | Port, replace EvalStore with AsyncSession |
| providers.py | providers.py (new) | Keep LiteLLM wrapper, use Settings |
| config.py | Merge into config.py | OPENROUTER_API_KEY, EVAL_MODELS dict |
| schemas.py | schemas.py (existing) | Align Pydantic models |
| prompts/*.py | prompts/*.py (new dir) | Copy, fix imports |
| store.py | DELETE | Replaced by Postgres |
| ui/ | DELETE | Replaced by Next.js |

**Total: ~4K tokens**

**Recommended agents:** `python-backend-developer` (runner port + router wiring), `react-frontend-developer` (eval UX improvements).

---

### Pack K: API Versioning (M7 Phase A)

Use when implementing the `/api/v1/` prefix cutover.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/plans/m7-implementation-roadmap.md` → Section 4 (Phase A) | Full cutover plan with code snippets, 3-step approach | ~1.5K |
| `src/compgraph/main.py` | Current router registration — 8 include_router() calls | ~300 |
| `web/src/lib/api-client.ts` | Frontend API paths to update | ~500 |
| `web/src/lib/constants.ts` | API_BASE definition | ~100 |
| `web/vercel.json` | Vercel rewrite rules (no change needed) | ~100 |

**Approach:** Option C — backend first with 308 redirect, then frontend, then cleanup. See roadmap Section 4.1 for exact file list and code snippets.

**Total: ~2.5K tokens**

**Recommended agents:** `python-backend-developer` (backend prefix), `react-frontend-developer` (frontend paths).

---

### Pack R: Roadmap & Phase Planning

Use when planning work, assessing scope, transitioning milestones, or delegating multi-agent tasks.

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/phases.md` → Roadmap Summary + M7 section | Current milestone, constraints, pre-commitments, sprint sequence | ~1K |
| `docs/plans/m7-implementation-roadmap.md` → Sections 1-2, 9-12 | Locked decisions, sprint sequence, dependencies, definition of done | ~2K |
| `docs/compgraph-product-spec.md` → milestones section | Original requirements per milestone | ~800 |
| `docs/changelog.md` (latest entry) | What happened last session | ~500 |

**Tier 2 escalation (load for dependency/audit analysis):**

| Load | Why | Tokens (est.) |
|------|-----|:---:|
| `docs/reports/gap-analysis-consolidated.md` → Section 10 (Dependency Map) | Prereq chains, topological sprint order | ~1K |
| `docs/reports/gap-analysis-consolidated.md` → Section 11 (PM Disposition) | Accepted/rejected/deferred items | ~500 |

**Total: ~4K core + ~1.5K Tier 2**

**Recommended agents:** `agent-organizer` (always loads Pack R), `spec-reviewer` (loads Roadmap Summary for scope checks).

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
| `docs/ci.md` | CI jobs (lint, type, test, security), CD auto-deploy pipeline, local hooks, review bots | ~1K |
| `docs/secrets-reference.md` | 1Password references, env var setup | ~500 |

### External Research (load by section)

| Document | When to load | For |
|----------|-------------|-----|
| `docs/references/llm-extraction-optimization.md` | Pricing, prompt patterns, Haiku vs Sonnet quality cliff, Batch API, validation stack | Enrichment pipeline, cost decisions |
| `docs/references/supabase-alembic-migrations.md` | Connection strings, schema isolation, pool config, migration safety | Database setup, Alembic config |
| `docs/references/icims-scraping.md` | iframe bypass, JSON-LD extraction, pagination, anti-scraping, portal types | iCIMS scraper (BDS, MarketSource) |
| `docs/references/workday-cxs-api.md` | CXS API endpoints, search/detail schemas, pagination, rate limits, tenant variations | Workday scraper (2020 Companies) |
| `docs/references/similar-projects-research.md` | Open-source project patterns, tooling decisions, anti-bot signals | Scraper design, enrichment tooling, pipeline architecture |
| `docs/references/canadian-portals-research.md` | Canadian job portal research | Scraper expansion |
| `docs/references/logo-dev-api.md` | Logo CDN endpoint, publishable vs secret keys, Brand Search/Describe, rate limits, CompGraph integration patterns | Brand enrichment, frontend logos, map markers |
| `docs/references/multi-component-scraper-patterns.md` | Multi-component scraper architecture | Scraper design patterns |
| `docs/references/osl-careers-research.md` | OSL careers site analysis | Competitor integration |
| `docs/references/silent-failure-audit.md` | Silent failure identification and mitigation | Pipeline debugging |
| `docs/references/troc-ats-research.md` | T-ROC ATS platform analysis | Workday scraper |
| `docs/references/metabase-oss-evaluation.md` | Metabase OSS evaluation for complementary data exploration | Deferred — evaluate post-M7 |
| `docs/references/openrouter-model-candidates.md` | OpenRouter model pricing, 16 candidate models for eval, cost projections | Enrichment pipeline, Prompt Evaluation Tool |
| `docs/references/llm-eval-best-practices.md` | Eval frameworks, scoring, statistical rigor, prompt optimization from human feedback, error taxonomy, cost optimization | Prompt Evaluation Tool, prompt improvement |
| `docs/references/vitest-infrastructure-best-practices.md` | Vitest 4 setup, practitioner pain points, Jest migration, CI config | Frontend testing (Next.js) |
| `docs/references/nextjs-15-vitest-testing-patterns.md` | Next.js 15 App Router testing pyramid, RSC limitations, mocking patterns | Frontend testing (Next.js) |
| `docs/references/ai-generated-design-complaints.md` | AI design visual tells, purple problem, practitioner complaints, antidotes | Frontend design (Next.js) |
| `docs/UI/compgraph-design-handoff/compgraph-handoff/specs/map-visualizations.md` | Mapbox GL JS heatmap (H3 hex) + pin map patterns, color ramp, zoom-adaptive resolution, Supabase storage strategy | Frontend maps, geographic intel |
| `docs/UI/compgraph-design-handoff/compgraph-handoff/specs/logo-dev-integration.md` | Logo.dev CDN + Brand Search API, CompetitorLogo component, presets by context, greyscale grid, caching, attribution | Frontend logos, competitor profiles |
| `docs/references/supabase-auth-fastapi.md`  | Supabase Auth JWT verification, magic link flow, role-based middleware | Auth (M4d) |
| `docs/references/truncate-insert-patterns.md`  | PostgreSQL truncate+insert rebuild patterns, transaction isolation, concurrent reads | Aggregation (M4a) |
| `docs/references/fastapi-pagination-patterns.md`  | Cursor vs offset pagination, filter parameters, SQLAlchemy query builders | Detail API (M4c) |
| `docs/references/mcp-server-capabilities.md` | Tool catalog for Supabase, Vercel, next-devtools, Sentry, Playwright — tool tables, project IDs, composed workflows | Deployment, Frontend, Database, Debugging |
| `docs/references/automation-setup.md` | MCP servers (Playwright, Sentry), hooks, skills, agents — setup reference for Claude Code and Cursor | Automation, DX |
| `docs/references/operating-budget.md` | Infrastructure, LLM, and data enrichment cost line items with optimization levers and scaling plan | Cost planning, M6 planning |

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
| `python-backend-developer` | Pack matching current task (A-H) | Tier 0 (CLAUDE.md auto-loaded, includes Roadmap) |
| `code-reviewer` | Pack matching reviewed code + full `docs/design.md` section | changelog latest entry |
| `pytest-validator` | Test files + source files under test | Models for type checking |
| `spec-reviewer` | `docs/compgraph-product-spec.md` (relevant sections) | Roadmap Summary from `phases.md` |
| `agent-organizer` | Pack R (Roadmap & Phase Planning) | Tier 0 + changelog latest entry |

### Subagent Prompting

When launching a project-level agent, include:
1. The specific task (not the whole project)
2. Relevant context pack reference
3. Constraints and conventions that apply
