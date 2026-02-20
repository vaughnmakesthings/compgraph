# Documentation Audit Report — 2026-02-20

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 10 |
| Phantom refs | 1 |
| Unlisted refs | 5 |
| Stale docs | 2 |
| Content mismatches | 2 |
| Consistency checks passed | 5/7 |
| Research gaps | 4 |
| Auto-fixes applied | 0 (--report-only) |

**Overall Health: YELLOW**

Criteria: 1 phantom ref + 2 content mismatches + consistency 5/7 = YELLOW

## Phase 1 — Inventory

### Living Docs
| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-20 | 280 |
| docs/context-packs.md | Y | 2026-02-20 | 354 |
| docs/changelog.md | Y | 2026-02-19 | 274 |
| docs/phases.md | Y | 2026-02-20 | 260 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-12 | 199 |
| docs/cheat-sheet.md | Y | 2026-02-15 | 184 |
| docs/ci.md | Y | 2026-02-12 | 21 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs
| File | Listed in Packs | Last Commit | Lines |
|------|:-:|-------------|-------|
| docs/references/canadian-portals-research.md | N | 2026-02-19 | 72 |
| docs/references/icims-scraping.md | Y | 2026-02-12 | 346 |
| docs/references/llm-extraction-optimization.md | Y | 2026-02-12 | 212 |
| docs/references/multi-component-scraper-patterns.md | N | 2026-02-16 | 101 |
| docs/references/osl-careers-research.md | N | 2026-02-19 | 141 |
| docs/references/silent-failure-audit.md | N | 2026-02-16 | 179 |
| docs/references/similar-projects-research.md | Y | 2026-02-12 | 202 |
| docs/references/supabase-alembic-migrations.md | Y | 2026-02-12 | 189 |
| docs/references/troc-ats-research.md | N | 2026-02-15 | 60 |
| docs/references/workday-cxs-api.md | Y | 2026-02-12 | 272 |

### Issues Found
- **Phantom ref:** `docs/references/proxy-provider-comparison.md` (in context-packs.md Tier 2, not on disk)
- **Unlisted:** `docs/references/canadian-portals-research.md`
- **Unlisted:** `docs/references/multi-component-scraper-patterns.md`
- **Unlisted:** `docs/references/osl-careers-research.md`
- **Unlisted:** `docs/references/silent-failure-audit.md`
- **Unlisted:** `docs/references/troc-ats-research.md`

### Roster Checks
- **Agents:** 9 on disk = 9 in CLAUDE.md — MATCH
- **Skills:** 12 on disk = 12 in CLAUDE.md — MATCH

### Counts
- Living docs: 12 | Reference docs: 10 | Plans: 13 | Reports: 1 | Memory files: 2
- Phantom refs: 1 | Unlisted refs: 5 | Agent mismatches: 0 | Skill mismatches: 0

## Phase 2 — Freshness & Accuracy

Latest `src/` commit: 2026-02-20

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|:-----------:|--------|-------|
| CLAUDE.md | 2026-02-20 | 0 | STALE-CONTENT | Test count not stated but MEMORY.md says 458 (actual: 508) |
| docs/context-packs.md | 2026-02-20 | 0 | BROKEN-REFS | Phantom ref: proxy-provider-comparison.md |
| docs/changelog.md | 2026-02-19 | 1 | CURRENT | |
| docs/phases.md | 2026-02-20 | 0 | STALE-CONTENT | States 458 tests (actual: 508) |
| docs/design.md | 2026-02-15 | 5 | STABLE | Intentionally slow-changing |
| docs/failure-patterns.md | 2026-02-19 | 1 | CURRENT | |
| docs/workflow.md | 2026-02-12 | 8 | STALE | Oldest living doc |
| docs/cheat-sheet.md | 2026-02-15 | 5 | STALE-CONTENT | Lists 5 of 12 skills |
| docs/ci.md | 2026-02-12 | 8 | STALE | Only 21 lines |
| docs/secrets-reference.md | 2026-02-18 | 2 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 4 | CURRENT | |
| docs/compgraph-product-spec.md | 2026-02-15 | 5 | STABLE | Intentionally slow-changing |

### Specific Discrepancies
- **Test count:** pytest reports 508 collected, phases.md and MEMORY.md say 458
- **Skill coverage in cheat-sheet.md:** Lists 5 of 12 skills (missing /pr, /deploy, /enrich-status, /migrate, /research, /pr-feedback-cycle, /docs-audit)

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | **MISMATCH** | pytest=508, phases.md=458, MEMORY.md=458 |
| C2: Milestone state | MATCH | phases.md=~95%, CLAUDE.md=~95%, MEMORY.md=~95% |
| C3: Active scrapers | MATCH | 4 active in all sources (iCIMS x2 + Workday x2) |
| C4: Agent roster | MATCH | 9 on disk = 9 in CLAUDE.md |
| C5: Skill roster | MATCH | 12 on disk = 12 in CLAUDE.md |
| C6: Dev server address | MATCH | 192.168.1.69 consistent |
| C7: Dropped competitors | **PARTIAL** | MEMORY.md: Acosta + Advantage dropped. CLAUDE.md: not mentioned |

**Consistency score: 5/7 MATCH**

## Phase 4 — Gap Analysis

### Current Milestone (M3) Gaps
- No reference doc for prompt tuning methodology
- No documented data quality review criteria

### Next Milestone (M4) Gaps
- No aggregation pattern design doc (truncate+insert mentioned but no dedicated reference)
- No API endpoint design doc
- No auth design doc (deferred to M4d)
- No GitHub issues labeled M4

### Unlisted Reference Docs
| File | Lines | Suggested Pack |
|------|-------|---------------|
| docs/references/canadian-portals-research.md | 72 | Tier 2 (Pack A) |
| docs/references/multi-component-scraper-patterns.md | 101 | Tier 2 (Pack A) |
| docs/references/osl-careers-research.md | 141 | Tier 2 (Pack A) |
| docs/references/silent-failure-audit.md | 179 | Tier 2 (Pack F) |
| docs/references/troc-ats-research.md | 60 | Tier 2 (Pack A) |

### Scaling Plan Integration
- phases.md M6: arq, LiteLLM, Batch API — MATCH with memory/scaling-plan.md
- phases.md M7: Digital Ocean deploy — MATCH

### CodeSight Status
- Index: current (reindexed during audit)
- Docs indexed: Yes (160 files, 1495 chunks)

## Auto-Fixes Applied

Skipped (`--report-only`)

## Recommended Actions (prioritized)

1. **Fix test count** in phases.md and MEMORY.md: 458 → 508
2. **Annotate or remove phantom ref** `proxy-provider-comparison.md` in context-packs.md
3. **Add 5 unlisted reference docs** to context-packs.md Tier 2 table
4. **Update cheat-sheet.md** to include all 12 skills
5. **Add dropped competitors** (Acosta, Advantage) to CLAUDE.md Architecture section
6. **Review workflow.md** (8 days stale, oldest living doc)
7. **Review ci.md** (8 days stale, only 21 lines — may be incomplete)

## Suggested Research

- `/research aggregation truncate-insert patterns for PostgreSQL` — M4 prep
- `/research FastAPI read-only API patterns with SQLAlchemy async` — M4 prep
- `/research JWT auth patterns for FastAPI + Supabase` — M4d prep
- `/research prompt tuning methodology for structured extraction` — M3 completion
