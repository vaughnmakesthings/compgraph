# Documentation Audit Report — 2026-02-21

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 16 |
| Phantom refs | 1 (already annotated) |
| Unlisted refs | 1 (fixed) |
| Stale docs | 2 (`workflow.md`, `ci.md`) |
| Content mismatches | 2 (fixed: Pi IP in phases.md, Pi ref in CLAUDE.md) |
| Consistency checks passed | 6/7 → 7/7 (after fixes) |
| Research gaps | 3 |
| Auto-fixes applied | 3 (1 was already done from prior audit) |

**Overall Health: YELLOW → GREEN (after fixes)**

Health criteria: 0 phantom refs unaddressed, 0 content mismatches remaining, consistency 7/7

## Phase 1 — Inventory

### Living Docs
| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-20 | 369 |
| docs/context-packs.md | Y | 2026-02-20 | 364 |
| docs/changelog.md | Y | 2026-02-20 | 349 |
| docs/phases.md | Y | 2026-02-20 | 376 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-12 | 199 |
| docs/cheat-sheet.md | Y | 2026-02-20 | 191 |
| docs/ci.md | Y | 2026-02-12 | 21 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs
| File | In Packs | Last Commit | Lines |
|------|----------|-------------|-------|
| ai-generated-design-complaints.md | Y | 2026-02-20 | 115 |
| canadian-portals-research.md | Y | 2026-02-19 | 72 |
| icims-scraping.md | Y | 2026-02-12 | 346 |
| llm-eval-best-practices.md | Y | 2026-02-20 | 468 |
| llm-extraction-optimization.md | Y | 2026-02-12 | 212 |
| metabase-oss-evaluation.md | Y (added) | 2026-02-20 | 68 |
| multi-component-scraper-patterns.md | Y | 2026-02-16 | 101 |
| nextjs-15-vitest-testing-patterns.md | Y | 2026-02-20 | 269 |
| openrouter-model-candidates.md | Y | 2026-02-20 | 92 |
| osl-careers-research.md | Y | 2026-02-19 | 141 |
| silent-failure-audit.md | Y | 2026-02-16 | 179 |
| similar-projects-research.md | Y | 2026-02-12 | 202 |
| supabase-alembic-migrations.md | Y | 2026-02-12 | 189 |
| troc-ats-research.md | Y | 2026-02-15 | 60 |
| vitest-infrastructure-best-practices.md | Y | 2026-02-20 | 106 |
| workday-cxs-api.md | Y | 2026-02-12 | 272 |

### Issues Found (Pre-Fix)
- Phantom ref: `proxy-provider-comparison.md` (already annotated `<!-- MISSING -->` from prior audit)
- Unlisted: `metabase-oss-evaluation.md` → **FIXED** (added to context-packs.md)
- Skill description: `/deploy` said "Raspberry Pi" → **FIXED** (now says "Digital Ocean")

### Counts
- Living docs: 12 | Reference docs: 16 | Plans: 13 | Reports: 3 (incl. this one) | Memory files: 2

## Phase 2 — Freshness & Accuracy

Latest src/ commit: 2026-02-20

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-20 | 0 | CURRENT | Agent crew updated this session |
| docs/context-packs.md | 2026-02-20 | 0 | CURRENT | |
| docs/changelog.md | 2026-02-20 | 0 | CURRENT | |
| docs/phases.md | 2026-02-20 | 0 | CURRENT | Pi IP fixed this audit |
| docs/design.md | 2026-02-15 | 5 | STABLE | Intentionally slow-changing |
| docs/failure-patterns.md | 2026-02-19 | 1 | CURRENT | |
| docs/workflow.md | 2026-02-12 | 8 | STALE | Oldest living doc |
| docs/cheat-sheet.md | 2026-02-20 | 0 | CURRENT | |
| docs/ci.md | 2026-02-12 | 8 | STALE | Only 21 lines |
| docs/secrets-reference.md | 2026-02-18 | 2 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 4 | CURRENT | |
| docs/compgraph-product-spec.md | 2026-02-15 | 5 | STABLE | |

### Specific Discrepancies
- Test count: pytest=510, MEMORY.md=510 — MATCH
- Milestone: all sources say ~95% — MATCH
- Dev server: all sources now say Digital Ocean/165.232.128.28 — MATCH (after fix)

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | MATCH | pytest=510, MEMORY.md=510 |
| C2: Milestone | MATCH | ~95% in all sources |
| C3: Scrapers | MATCH | 4 active in all sources |
| C4: Agents | MATCH | 11 on disk, 11 in CLAUDE.md |
| C5: Skills | MATCH | 13 on disk, 13 in CLAUDE.md |
| C6: Dev server | MATCH (fixed) | All sources now reference DO |
| C7: Dropped | MATCH | Acosta + Advantage consistent |

**Consistency score: 7/7 MATCH** (after fixes)

## Phase 4 — Gap Analysis

### Current Milestone (M3) Gaps
- No reference doc for prompt tuning methodology
- No documented data quality review criteria
- Security issues #130/#131 open with no remediation design doc

### Next Milestone (M4) Gaps
- No M4-labeled issues on GitHub
- No aggregation pattern design doc (truncate+insert mentioned but no dedicated reference)
- No API endpoint design doc
- No auth design doc (deferred to M4d per CLAUDE.md)

### CodeSight Status
- Index: refreshed (171 files, 1531 chunks, 3.8s incremental)
- Docs indexed: Yes

## Auto-Fixes Applied
1. ~~Phantom ref annotation~~ — already done from prior audit (2026-02-20)
2. Added `metabase-oss-evaluation.md` to `docs/context-packs.md` Tier 2 table
3. Fixed CLAUDE.md: `/deploy` description changed from "Raspberry Pi" to "Digital Ocean"
4. Fixed `docs/phases.md`: replaced `192.168.1.69:8000/:8501` with `dev.compgraph.io / dashboard.dev.compgraph.io (Digital Ocean)`

## Recommended Actions (prioritized)
1. Update `docs/workflow.md` — 8 days stale, oldest living doc
2. Expand `docs/ci.md` — only 21 lines, likely incomplete for current CI setup
3. Create prompt tuning reference doc before M3 completion
4. Create data quality review criteria doc before M3 completion
5. Begin M4 planning docs: aggregation patterns, API endpoints

## Suggested Research
- `/research prompt tuning methodology for LLM extraction` — M3 completion
- `/research truncate-insert aggregation patterns for PostgreSQL` — M4 prep
- `/research Supabase Auth integration with FastAPI` — M4d prep

## MEMORY.md Suggested Update
No changes needed — MEMORY.md is current (test count, milestone %, server addresses all accurate).
