# CompGraph Refined Audit & Strategic Roadmap

This report provides human-readable definitions of identified problems, their associated business risks, and the specific architectural solutions required to achieve an enterprise-grade platform.

---

## 1. 🏗️ Architecture & API Contracts
*Foundational structural requirements and system "plumbing".*

### ARCH-01: Route-to-DB Coupling (🔴 CRITICAL)
*   **The Problem:** API route handlers are currently doing "manual labor"—they construct complex database queries, handle joins, and manage SQL logic directly. This makes the code hard to read, impossible to test without a live database, and prevents us from reusing query logic in other parts of the system.
*   **The Solution:** Implement a **Service Layer** (`src/compgraph/services/`). Create a `PostingService` that accepts a database session and returns Pydantic models. The API routes should only handle HTTP status codes and call the service.
*   **Target:** M4 | **Effort:** Medium

### ARCH-02: Fragile In-Memory Run Tracking (🟠 HIGH)
*   **The Problem:** Currently, the "pulse" of the system (active scrapes and enrichment runs) is stored in a Python dictionary. If the server restarts or crashes, that pulse is lost. The system won't know it was in the middle of a run, and the UI will show "Idle" while background tasks might still be zombie-ing along.
*   **The Solution:** Eliminate the `_runs` in-memory dictionaries. Use the **Database as the Source of Truth**. Implement a "Heartbeat" column in the `scrape_runs` and `enrichment_runs` tables that orchestrators update every 30 seconds.
*   **Target:** M4 | **Effort:** Medium

### ARCH-03: Unversioned API Contracts (🟡 MEDIUM)
*   **The Problem:** Our API URLs look like `/api/postings`. If we change the data shape for the web app, we might break future mobile apps or third-party integrations.
*   **The Solution:** Move to **Explicit Versioning** (`/api/v1/postings`). Use FastAPI router prefixing to ensure we can host V1 and V2 side-by-side during transitions.
*   **Target:** M4 | **Effort:** Small

---

## 2. 🗄️ Data Models & Database Integrity
*The integrity of the "Intel" depends on the cleanliness of the schema.*

### DATA-01: Enrichment Double-Counting (🔴 CRITICAL)
*   **The Problem:** We version our AI enrichments (good for history), but standard SQL joins see *every version*. This causes "Postings Found" to double or triple in reports every time we re-run the AI on existing data.
*   **The Solution:** Create a **`latest_enrichment` View or CTE** logic. All aggregation and dashboard queries must filter to only the most recent `enrichment_version` per posting ID.
*   **Target:** M4 | **Effort:** Small

### DATA-02: Missing Foreign Key Indexes (🟠 HIGH)
*   **The Problem:** We have relationships between Postings, Brands, and Retailers, but 14 of those links don't have "lookup shortcuts" (indexes). As the database grows from 1,000 to 100,000 rows, the dashboard will slow down to a crawl.
*   **The Solution:** Add **explicit indexes** to all Foreign Key columns, specifically `posting_id`, `brand_id`, and `retailer_id` in the fact and aggregation tables.
*   **Target:** M4 | **Effort:** Small

---

## 3. 🕸️ Scraping & Data Ingestion
*Ensuring the pipeline is resilient to changes in competitor websites.*

### SCRP-01: Silent Scraper Success (🔴 CRITICAL)
*   **The Problem:** If a competitor's website breaks and returns an empty list, the scraper currently says "SUCCESS: Found 0 jobs." This is a "silent death" where data goes stale without any alert firing.
*   **The Solution:** Implement **Baseline Anomaly Detection**. Compare the "Jobs Found" count to a 7-day rolling average. If it drops by >50%, mark the run as `DEGRADED` and fire an alert.
*   **Target:** M4 | **Effort:** Small

### SCRP-02: Blind Redirect Following (🟠 HIGH)
*   **The Problem:** If an iCIMS portal is decommissioned, it might redirect to a generic "Thank you" page. Our scraper follows that redirect and tries to parse it as job data, failing to find anything but reporting success.
*   **The Solution:** Add a **Domain Validator** to the HTTP client. If the final URL doesn't match the expected ATS domain (e.g., `icims.com`), raise an error immediately.
*   **Target:** M4 | **Effort:** Small

---

## 4. 🧠 LLM Enrichment & Strategic Intelligence
*The "Product Excellence" layer where data becomes competitive value.*

### LLM-01: Pay Value Hallucinations (🔴 CRITICAL)
*   **The Problem:** The AI sometimes sees "$1M budget" and thinks the job pays $1,000,000/hour. This pollutes our pay benchmarks with impossible outliers.
*   **The Solution:** Add **Business Rule Validation** to the Pydantic schema. Set hard bounds (e.g., Hourly: $10-$150) and a `check_pay_range` constraint ensuring `min <= max`.
*   **Target:** M4 | **Effort:** Small

### LLM-02: Signal Decay Model (🟠 HIGH)
*   **The Problem:** A brand relationship mentioned 6 months ago shouldn't carry the same weight as one mentioned yesterday. Currently, the system has no concept of "aging out" dormant signals.
*   **The Solution:** Implement a **Confidence Decay Algorithm**. Calculate a "Recency Score" for every brand relationship. Move brands from "Active" to "Dormant" automatically if no new evidence appears for 90 days.
*   **Target:** M6 | **Effort:** Large

### LLM-03: Multi-Source Triangulation (🟠 HIGH)
*   **The Problem:** Our database assumes a "Relationship" *is* a "Job Posting." When we add LinkedIn or Press Releases, they won't fit this restricted model.
*   **The Solution:** Refactor to an **`IntelGraph` architecture**. Postings, News, and Social changes become "Nodes" that feed a central "Relationship" entity with a weighted confidence score.
*   **Target:** M7 | **Effort:** Large

---

## 5. 🎨 Frontend & User Experience (UX)
*Ensuring the system is usable, trustworthy, and authoritative.*

### UX-01: Missing Evidence Trails (🔴 CRITICAL)
*   **The Problem:** An executive won't trust a chart saying "BDS is working with Samsung" if they can't see *why*. They need to see the proof.
*   **The Solution:** Implement **Contextual Provenance**. Every brand relationship in the UI must have an `EvidenceBadge` that links to the specific job posting, ideally scrolling the user directly to the text that triggered the match.
*   **Target:** M7 | **Effort:** Large

### UX-02: "Push to CRM" Integration (🔵 LOW)
*   **The Problem:** An opportunity identified in CompGraph requires manual copy-pasting into Salesforce/HubSpot to be acted upon.
*   **The Solution:** Add a **"Push to Pipeline" button**. Use a webhook to create a Lead/Opportunity in the CRM, pre-populating it with the LLM-generated dossier.
*   **Target:** M7 | **Effort:** Medium

---

## 6. 🔒 Security & 🚀 DevOps
*Operational safety and system reliability.*

### SEC-02: SQL Wildcard Injection (🔴 CRITICAL)
*   **The Problem:** During a recent code cleanup, the logic that sanitizes user-provided search terms was accidentally removed. A user searching for `%` could return the entire database or potentially disrupt the query.
*   **The Solution:** Restore the **`_escape_like()` helper** in the postings router to ensure special SQL characters are treated as literal text.
*   **Target:** M4 | **Effort:** Trivial

### OPS-02: Disaster Recovery (PITR) Drill (🟠 HIGH)
*   **The Problem:** We rely on Supabase backups, but we have never tested a "Point-in-Time Recovery." If a bad script wipes our append-only fact tables, we don't know how long it takes to get back online.
*   **The Solution:** Execute a **DB Recovery Drill**. Document the exact steps to restore to a specific minute on a separate branch.
*   **Target:** M6 | **Effort:** Medium

---

## 7. Project Manager Point of View

*Added 2026-02-24. Ground-truth verification against the codebase, severity re-calibration, and execution guidance.*

### Overall Assessment

This audit is solid work. It correctly identifies the structural gaps that separate CompGraph from a production-grade system. However, it was conducted against a snapshot that is now partially stale — several "CRITICAL" items have already been fixed, and the milestone references (M4/M5/M6) in `docs/phases.md` are themselves outdated (still says M3 in progress, references Streamlit). The actual state is **M6 complete, M7 in progress** with a live Next.js frontend on Vercel.

Below I classify each finding into one of three buckets:

- **RESOLVED** — already fixed in the codebase; remove from active tracking
- **AGREE** — real issue, accept the recommendation (possibly with re-prioritization)
- **DISAGREE / DEFER** — reject the recommendation or re-scope it

---

### Findings Already Resolved (Remove from Active Tracking)

These items are fixed. The audit was working from stale data.

| ID | Finding | Evidence |
|----|---------|----------|
| **SEC-02** | SQL Wildcard Injection | `_escape_like()` is present in `api/routes/postings.py:92`. Restored in PR #196 (Feb 24). |
| **DATA-01** | Enrichment Double-Counting | `latest_enrichment` CTE is implemented in both `pay_benchmarks.py` and `posting_lifecycle.py`. Fixed in the Feb 23 data quality session. |
| **SCRP-01** | Silent Scraper Failures | `check_baseline_anomaly()` exists in `scrapers/orchestrator.py:122`, called during scrape runs at line 452. Returns DEGRADED status on anomalous drops. |
| **QA-01** | Shallow Health Endpoint | `health.py` now includes `SELECT 1` DB ping (line 30) and APScheduler liveness check (line 44) with configurable timeouts. |
| **SEC-03** | Missing SSL in Alembic | `alembic/env.py:69` hardcodes `connect_args={"ssl": "require"}`. Already enforced. |
| **DATA-02** | Missing FK Indexes | Issue #45 is CLOSED. Models have composite indexes on all major FK columns (confirmed: `ix_posting_enrichment_brand_id`, `ix_posting_enrichment_retailer_id`, `ix_posting_enrichment_market_id`, `ix_velocity_date_company`, `ix_brand_timeline_company_brand`, etc.). |
| **DATA-03** | Brand Deduplication | `scripts/dedup_brands.py` exists and has been run in production. 3 merge pairs (Reliant/LG/Virgin) consolidated. |

**Action:** Mark these 7 items as CLOSED in `gap-analysis-consolidated.md` and `code-review-log.md`.

---

### Findings I Agree With (Accept & Prioritize)

#### Tier 1 — Do Before M7 Launch

| ID | Finding | PM Notes | Revised Target |
|----|---------|----------|---------------|
| **SEC-01** | Unauthenticated Pipeline Controls | This is the #1 priority. Anyone with the URL can trigger scrapes or stop the pipeline. Supabase Auth integration is already planned for M7 (Issue #59). Ship auth middleware before any stakeholder demo. | **M7 — first sprint** |
| **ARCH-02** | In-Memory Run Tracking | Real problem. Server restarts lose run state, UI shows stale data. Issue #156 tracks the DB migration. Should pair with auth work since both touch the orchestrator. | **M7 — first sprint** |
| **LLM-01** | Pay Value Hallucinations | **Partially addressed.** DB has `check_pay_min_positive`, `check_pay_max_positive`, and `check_pay_range` constraints. However, these only enforce `>= 0` and `min <= max` — they do NOT enforce upper bounds ($150/hr, $300K/yr) as the audit recommends. The Pydantic schema also lacks range validators. Worth adding the tighter bounds. | **M7 — quick win** |
| **ARCH-01** | Service Layer | Agree this is the right architectural direction. The `services/` directory exists but is empty (just `__init__.py`). However, I'd deprioritize this below auth and reliability — route-to-DB coupling is ugly but functional, and the API surface is small (< 15 endpoints). Refactor as routes grow. | **M7 — second sprint** |
| **UX-01** | Missing Evidence Trails | Agree this is critical for user trust. However, this is a UX *feature*, not a *bug*. It requires backend changes (brand_mentions API with provenance metadata) and frontend work (EvidenceBadge, SourcePostingLink). Correctly scoped as M7 Large. | **M7 — feature sprint** |

#### Tier 2 — Nice to Have for M7, Can Slip to M8

| ID | Finding | PM Notes | Revised Target |
|----|---------|----------|---------------|
| **SCRP-02** | Blind Redirect Following | Valid concern but low-probability failure mode. Our 4 ATS endpoints are stable. Add a `_validate_redirect()` but don't block M7 on it. | **M7 or M8** |
| **PERF-01** | N+1 API Fetching (postings detail) | Issue #18 tracks this. Not user-facing yet — the detail view isn't heavily used. Fix when it becomes a bottleneck. | **M7 or M8** |
| **PERF-02** | Sequential Aggregations | Correct that `asyncio.gather` would help, but the 7 agg jobs complete in < 30s total today. Premature optimization. Revisit if data volume grows 10x. | **M8** |
| **UX-02** | Missing ConfirmDialogs | Issue #184. Annoying but not dangerous — the pipeline has idempotent operations. Add before stakeholder access. | **M7** |
| **OPS-02** | Disaster Recovery Drill | Agree we need this, but it's an operational exercise, not a code change. Schedule it as a dedicated half-day, not a sprint task. | **M7 — operational** |

---

### Findings I Disagree With or Want to Re-Scope

| ID | Finding | PM Response |
|----|---------|-------------|
| **ARCH-03** | API Versioning (`/api/v1/`) | **Disagree for now.** We have exactly 1 consumer (the Next.js frontend) and 0 third-party integrations. API versioning adds complexity (double-registering routers, maintaining version shims) with zero current benefit. The audit's own rationale — "future mobile apps or third-party integrations" — is speculative. Revisit if/when we add a second consumer. |
| **ARCH-04** | Cross-Repo Schema Sync (pydantic-to-typescript) | **Disagree.** The frontend manually defines TypeScript types in `web/src/lib/types.ts`. This is intentional — the frontend types are *view models*, not 1:1 mirrors of DB models. Auto-generation would create coupling we don't want. The current approach (manually sync when API shapes change) works at our scale. |
| **LLM-02** | Signal Decay Model | **Defer to M8+.** This is a product feature, not a bug. Our brand timeline already shows temporal data — users can see recency visually. A formal decay algorithm adds complexity to the aggregation layer and needs product validation (what does "dormant" mean to Mosaic's sales team?). Don't engineer it without user feedback. |
| **LLM-03** | IntelGraph / Multi-Source Triangulation | **Defer indefinitely.** This is a fundamental schema redesign ("Postings become Nodes") for a use case (LinkedIn scraping, press releases) that doesn't exist yet and may never be prioritized. Classic YAGNI. If we add a second source, evaluate then. |
| **UX-02** | CRM Push Integration | **Defer to M8+.** Zero users have requested this. Build it when Mosaic asks for it, not before. |
| **UX-03** | TanStack Query / SWR | **Disagree with scope.** The audit frames `useEffect` polling as a major problem. It's not — the current polling works, and we added it intentionally with 3s intervals. TanStack Query is nice but it's a full state management migration. Don't rewrite working fetch logic for architectural purity. If specific pages have stale-state bugs, fix those pages. |
| **OPS-01** | Terraform/Ansible for IaC | **Defer to M8+.** We have 1 droplet, 1 firewall, and 1 Caddyfile. Terraform is a massive overhead for a single-server deployment. The bash scripts in `infra/` are battle-tested and working. Revisit only if we add a second environment (staging, production). |
| **QA-03** | FactoryBoy / MSW for test data | **Disagree on urgency.** Our test suite has 703 backend tests at 82% coverage and 164 frontend tests at 52% coverage. The fixtures work. FactoryBoy is a preference, not a requirement. Don't refactor test infrastructure that's passing. |
| **QA-05** | Visual Regression Testing (Playwright screenshots) | **Defer.** We don't have enough UI churn to justify screenshot testing infrastructure. Our design system is stabilizing, not actively breaking. |

---

### Items Correctly Scoped But Worth Noting

| ID | Notes |
|----|-------|
| **CG-QUAL-001** | Timezone-naive `datetime.now()` at `preflight.py:1005` — confirmed still present. Trivial fix, should ride along with next preflight PR. |
| **PERF-05** | `string_agg` aggregate ordering — the aggregation queries use raw SQL with `ORDER BY` inside CTEs (e.g., `ARRAY_AGG(DISTINCT brand_name ORDER BY brand_name)` in coverage_gaps). The `aggregate_order_by()` concern applies to SQLAlchemy ORM usage, but our aggregations are raw SQL. **Not actually a bug** — the `ORDER BY` clauses are correctly placed inside the aggregate functions in the raw SQL. |
| **OPS-05** | Duplicate dev dependency groups in pyproject.toml — Issue #187. Trivial cleanup, do whenever. |
| **LLM-04** | Eval N+1 queries — Issue #193. Real but only affects the eval leaderboard page, which is admin-only. Low urgency. |
| **LLM-05** | Batch enrichment counter increments — Issue #89. Correct analysis, minor perf win. Do when touching the enrichment orchestrator next. |

---

### Recommended M7 Sprint Sequence

Based on the above triage, here's the execution order I'd recommend:

1. **Auth & Security** (SEC-01 + ARCH-02): Supabase Auth middleware, admin RBAC, DB-backed run tracking. This unlocks stakeholder access.
2. **Data Quality Tightening** (LLM-01 partial): Add upper-bound pay validators to Pydantic schema. Quick win.
3. **Service Layer Foundation** (ARCH-01): Extract 2-3 key routes into services as a pattern. Don't boil the ocean.
4. **Evidence Trails** (UX-01): Backend provenance API + frontend EvidenceBadge. This is the feature that sells the product.
5. **Polish** (UX-02, CG-QUAL-001, OPS-05): ConfirmDialogs, timezone fix, dep cleanup.

### What's Missing From This Audit

The audit is thorough on *technical debt* but light on *product gaps*:

- **No mention of the Eval Tool** (Issue #128) — the single largest M7 deliverable and prerequisite for LLM provider migration. See `gap-analysis-consolidated.md` Section 10 for full decomposition. Target user is a **business admin with some technical knowledge** — the UX must simplify LLM jargon into business-relevant concepts (guided flows, human-friendly model labels, scenario templates). Uses **OpenRouter** (API credits available).
- **No mention of company expansion** — we have 4 competitors; Mosaic competes with 10+. Scraper expansion is a product priority.
- **No mention of export/reporting** — stakeholders will want to export data to Excel/PDF for leadership presentations.
- **No mention of Sentry integration** — we have Sentry configured but no systematic error alerting.

These product-level priorities should be weighed against the technical debt items when planning sprints.

### PM Corrections (updated 2026-02-24)

**ARCH-03 (API Versioning):** Reversed to ACCEPT — see `2026-02-24-engineering-disagreements.md` Section 6A. Prefix-only, no version negotiation.

**UX-03 (SWR):** Revised to PARTIAL ACCEPT — SWR for new M7 components and Settings page polling refactor. No blanket migration.

**Eval Tool user model:** Corrected from "engineers" to **business admin with some technical knowledge.** This validates the guided-flow UX, jargon simplification, and scenario template proposals from the engineering review. OpenRouter confirmed as the LLM provider for evaluations.

---

*— PM review complete. 7 of 13 "strategic roadmap" items already resolved. 5 accepted for M7. 2 re-scoped after engineering disagreement resolution. Milestone references in both audit docs need updating to reflect actual state (M6 complete, M7 in progress).*
