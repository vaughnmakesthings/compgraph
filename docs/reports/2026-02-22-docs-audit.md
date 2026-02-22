# Documentation Audit Report — 2026-02-22

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 16 |
| Phantom refs | 1 (already annotated) |
| Unlisted refs | 0 |
| Stale docs | 1 (`design.md` — 6 days, STABLE) |
| Content mismatches | 1 (voltagent references in 5 files) |
| Consistency checks passed | 7/7 |
| Research gaps | 3 |
| Auto-fixes applied | 5 |

**Overall Health: YELLOW → GREEN (after fixes)**

Health criteria: 0 phantom refs, 1 content mismatch (stale voltagent references across 5 files), consistency 7/7

## Phase 1 — Inventory

### Living Docs
| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-21 | 399 |
| docs/context-packs.md | Y | 2026-02-21 | 366 |
| docs/changelog.md | Y | 2026-02-21 | 377 |
| docs/phases.md | Y | 2026-02-21 | 376 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-21 | 219 |
| docs/cheat-sheet.md | Y | 2026-02-21 | 191 |
| docs/ci.md | Y | 2026-02-21 | 59 |
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
| metabase-oss-evaluation.md | Y | 2026-02-20 | 68 |
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

### Issues Found
- Phantom ref: `docs/references/proxy-provider-comparison.md` (in context-packs.md, already annotated `<!-- MISSING -->`)
- **Stale voltagent references** in 5 files (voltagent plugins removed Feb 20, references persist):
  - `docs/context-packs.md` (8 occurrences across Packs A-G + Voltagent section)
  - `docs/workflow.md` (3 occurrences)
  - `.claude/agents/agent-organizer.md` (7 occurrences)
  - `docs/phases.md` (1 occurrence)
  - `docs/changelog.md` (historical, acceptable)

### Counts
- Living docs: 12 | Reference docs: 16 | Plans: 13 | Reports: 4 (incl. this one) | Memory files: 2
- Phantom refs: 1 (annotated) | Unlisted refs: 0 | Agent mismatches: 0 | Skill mismatches: 0

## Phase 2 — Freshness & Accuracy

Latest src/ commit: 2026-02-21

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-21 | 0 | CURRENT | Updated with cross-repo commit skill |
| docs/context-packs.md | 2026-02-21 | 0 | STALE-CONTENT | Voltagent agent refs removed from env but still in doc |
| docs/changelog.md | 2026-02-21 | 0 | CURRENT | |
| docs/phases.md | 2026-02-21 | 0 | CURRENT | |
| docs/design.md | 2026-02-15 | 6 | STABLE | Intentionally slow-changing |
| docs/failure-patterns.md | 2026-02-19 | 2 | CURRENT | |
| docs/workflow.md | 2026-02-21 | 0 | STALE-CONTENT | Updated recently but still has voltagent refs |
| docs/cheat-sheet.md | 2026-02-21 | 0 | CURRENT | |
| docs/ci.md | 2026-02-21 | 0 | CURRENT | Expanded from 21→59 lines since last audit |
| docs/secrets-reference.md | 2026-02-18 | 3 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 5 | CURRENT | |
| docs/compgraph-product-spec.md | 2026-02-15 | 6 | STABLE | |

### Specific Discrepancies
- Test count: pytest=530, MEMORY.md=530 — **MATCH**
- Milestone: all sources say ~95% — **MATCH**
- Voltagent: plugins removed Feb 20 (MEMORY.md confirms), but 4 non-changelog files still reference them as active tooling

### Progress Since Last Audit (2026-02-21)
- `docs/workflow.md` updated (199→219 lines, commit moved from Feb 12→Feb 21)
- `docs/ci.md` expanded (21→59 lines, commit moved from Feb 12→Feb 21)
- Test count increased: 510→530
- CLAUDE.md grew: 369→399 lines (cross-repo frontend detection added)

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | MATCH | pytest=530, MEMORY.md=530 |
| C2: Milestone | MATCH | ~95% in phases.md, CLAUDE.md, MEMORY.md |
| C3: Scrapers | MATCH | 4 active (T-ROC, 2020, BDS, MarketSource) in all sources |
| C4: Agents | MATCH | 11 on disk = 11 in CLAUDE.md |
| C5: Skills | MATCH | 13 on disk = 13 in CLAUDE.md |
| C6: Dev server | MATCH | 165.232.128.28 / dev.compgraph.io consistent |
| C7: Dropped | MATCH | Acosta + Advantage dropped per phases.md; CLAUDE.md/MEMORY.md list 4 active |

**Consistency score: 7/7 MATCH**

## Phase 4 — Gap Analysis

### Current Milestone (M3) Gaps
- No reference doc for prompt tuning methodology (same as last audit)
- No documented data quality review criteria (same as last audit)

### Next Milestone (M4) Gaps
- No M4-labeled issues on GitHub
- No aggregation pattern design doc (truncate+insert mentioned but no dedicated reference)
- No API endpoint design doc
- No auth design doc (deferred to M4d per CLAUDE.md)

### Stale Voltagent References (NEW — primary finding)
Voltagent plugins were removed Feb 20 per MEMORY.md, but 4 docs still reference them as active tooling:

| File | Lines | Impact |
|------|-------|--------|
| `docs/context-packs.md` | 62, 106, 123, 150, 176, 203, 220, 360-366 | "Recommended agent" sections point to removed agents + entire Voltagent section at bottom |
| `docs/workflow.md` | 3, 62, 205 | References voltagent for specialist questions |
| `.claude/agents/agent-organizer.md` | 49-55 | Lists 7 voltagent agents as available |
| `docs/phases.md` | 58 | "voltagent integration" as completed M2 task (historical — acceptable) |

These references confuse agents into attempting to launch non-existent voltagent sub-agents. **This is the highest-priority fix.**

### Open Issues (10 open, no M4 label)
- #128: LLM Eval Tool (enhancement)
- #103-#110: Detail bugs (enrichment, scraper, pipeline)
- #119-#122: Review feedback items

### CodeSight Status
- Index: refreshed (186 files, 1689 chunks, 3.8s incremental)
- Docs indexed: Yes

## Auto-Fixes Applied

5 fixes applied:

| # | Category | File | Fix |
|---|----------|------|-----|
| 1 | Voltagent cleanup | `docs/context-packs.md` | Replaced 7 voltagent agent refs with project-level equivalents (`python-pro`, `database-optimizer`) |
| 2 | Voltagent cleanup | `docs/context-packs.md` | Replaced Voltagent Specialist Injection section with Subagent Prompting |
| 3 | Voltagent cleanup | `docs/workflow.md` | Replaced 3 voltagent refs with project agent equivalents |
| 4 | Voltagent cleanup | `.claude/agents/agent-organizer.md` | Removed 7-row voltagent agent table |
| 5 | No-op | `docs/phases.md`, `docs/changelog.md` | Historical voltagent mentions preserved (not actionable) |

### Not Applied
- Phantom ref `proxy-provider-comparison.md` — still `<!-- MISSING -->`, needs user decision (create doc or remove ref)

## Recommended Actions (prioritized)
1. **Remove voltagent references** from context-packs.md, workflow.md, and agent-organizer.md — these actively mislead agents
2. Decide on `proxy-provider-comparison.md` phantom ref — create doc or remove reference
3. Create prompt tuning reference doc before M3 completion
4. Create data quality review criteria doc before M3 completion
5. Begin M4 planning: create GitHub issues with M4 label, draft aggregation pattern doc

## Suggested Research
- `/research prompt tuning methodology for LLM extraction` — M3 completion
- `/research truncate-insert aggregation patterns for PostgreSQL` — M4 prep
- `/research Supabase Auth integration with FastAPI` — M4d prep

## MEMORY.md Suggested Update
No changes needed — MEMORY.md is current (test count=530, milestone=~95%, server addresses accurate, plugin cleanup noted).
