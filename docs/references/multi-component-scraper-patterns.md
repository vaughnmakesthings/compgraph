# Multi-Component Scraper Patterns

Reference guide for implementing and debugging multi-source scraper systems. Based on real bugs from CompGraph's iCIMS and Workday adapters handling 4 competing companies with multiple portal URLs.

## 1. FK Cascade Patterns for Data Migrations

**Problem**: Silent data loss when cascading deletes propagate through fact tables.

**Checklist:**
- [ ] Trace FK dependency chains: `dimension_tables → fact_tables → snapshot/enrichment tables`
- [ ] Audit `ON DELETE CASCADE` vs `ON DELETE RESTRICT` for each FK
- [ ] When seeding dimension data (e.g., companies, brands), test that existing child rows survive
- [ ] Test **downgrade migrations** (not just upgrades) — verify rollbacks don't orphan data
- [ ] Document cascade impact in migration docstrings if a DELETE affects >1 child table
- [ ] If migrating a dimension table, use transaction isolation to prevent concurrent insert-then-delete races

**Real bug**: MarketSource company migration deleted 247 scrape_runs because the FK cascade wasn't explicitly checked in the downgrade path.

---

## 2. Partial Failure Semantics in Multi-Source Pipelines

**Problem**: Binary success/failure doesn't model N-of-M independent sources. Partial success treated as total failure causes cascading damage (false stale-posting deactivation, unneeded retries).

**Checklist:**
- [ ] **Never use** `success = len(errors) == 0` for multi-source pipelines
- [ ] Distinguish:
  - `warnings`: Some sources failed but data was captured from working sources → **don't retry, don't deactivate**
  - `errors`: Total failure (all sources failed or critical path blocked) → **retry eligible**
- [ ] Capture per-source status (`{company: "url": "status"}`) in scrape run metadata
- [ ] Stale posting deactivation must be **per-source** — only deactivate if that source hasn't reported in N days, not if aggregate run failed
- [ ] API consumers (`/api/scrape/runs`) must surface per-source status; partial success is actionable data, not a blocker
- [ ] **Design rule**: Warnings are acceptable completion states; errors are alert-worthy

**Real bug**: BDS multi-URL scrape had 1 of 2 portals fail. Pipeline marked run as failed, triggered stale deactivation for ALL BDS postings (including working portal's), triggered unnecessary retry loop.

---

## 3. Data Identity Disambiguation Across Sources

**Problem**: When multiple sources share a single table with non-global unique keys, ID collisions occur.

**Checklist:**
- [ ] For each source → fact table mapping, verify **uniqueness keys include source identity**
- [ ] Example iCIMS bug: `(company_id, external_job_id)` unique constraint fails when:
  - Company = BDS
  - Portal A (careers-bdssolutions.icims.com) posts job 47917
  - Portal B (careers-apolloretail.icims.com) posts job 47917 (same ID, different tenant)
  - Attempt to insert both → constraint violation on second insert
- [ ] **Fix**: Namespace external_job_id by source:
  - Scraper produces: `external_job_id = f"{portal_hostname}:{job_id}"`
  - Unique constraint becomes: `(company_id, external_job_id)` → globally unique
- [ ] **Backward compatibility**: Single-source companies (no multi-portal config) keep unprefixed IDs
- [ ] Test that multi-URL `search_urls` array in `scraper_config` doesn't create duplicate posting rows

**Real bug**: BDS iCIMS scraper with `search_urls: ["url1", "url2"]` created duplicate postings; second URL failed with unique constraint violation.

---

## 4. Error Boundary Design for N-Source Systems

**Problem**: One source's failure blocks all sources. Downstream consumers expect binary success but receive partial data.

**Checklist:**
- [ ] **Error isolation**: Each source (company adapter) runs in its own try-catch block
  - One failing adapter MUST NOT abort sibling adapters
  - Exceptions logged per-source; pipeline continues
- [ ] **Circuit breakers**: Per-source, not global
  - Track failure rate per company/URL pair
  - Disable that source's URL when threshold exceeded; leave others active
- [ ] **Downstream contract**: Orchestrator, API, and dashboard must handle partial results
  - Scrape run can have: some sources succeeded, some failed, some timed out
  - Status enum: `pending | in_progress | success | partial_success | failed`
  - Return `partial_success` if any source completed data
- [ ] **Logging**: Surface per-source status in structured logs and API responses
  - Include: company name, URL, row count, error (if failed)
  - Never collapse to aggregate "failures: 5" without per-source detail
- [ ] **Aggregation tables**: Rebuild from all available source data, even if one source is stale
  - Aggregation pipeline must validate source availability separately per query

**Real bug**: iCIMS multi-URL scrape reported failure at top level despite one portal succeeding, blocking aggregation and surfacing blank dashboard charts.

---

## Testing Checklist

- [ ] Multi-URL company: Create scraper_config with 2+ `search_urls`; verify both URLs produce postings with no constraint violations
- [ ] Partial failure: Mock 1 adapter exception; verify other adapters complete and pipeline status is `partial_success`
- [ ] Migration cascade: Write down>up migration pair; verify no data loss in rollback
- [ ] Identity uniqueness: Insert same external_job_id from different sources; verify constraint allows both (namespaced variant)
- [ ] Stale deactivation: Fail one source for N days; verify other sources' postings stay active

---

## Key Principles

1. **Source isolation**: Treat each source as an independent data producer with its own error domain
2. **Partial success is valid**: N-of-M sources succeeding is a success state, not a failure
3. **Namespace global IDs**: When merging multiple sources, prefix external IDs with source identity
4. **Trace FKs carefully**: Cascading deletes can be silent data loss; always test downgrade
5. **Surface per-source status**: APIs and dashboards must expose which sources are healthy, not just aggregate counts
