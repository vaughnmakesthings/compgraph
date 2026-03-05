# Documentation Audit Report — 2026-03-05 (v2)

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 35 |
| Phantom refs | 0 |
| Unlisted refs | 0 |
| Stale docs | 3 |
| Content mismatches | 1 |
| Consistency checks passed | 7/7 (after fixes) |
| Research gaps | 0 |
| Auto-fixes applied | 3 |

**Overall Health: YELLOW** (upgraded from previous audit; 1 remaining item: Pack S3 not committed)

## Phase 1 — Inventory

### Living Docs
| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-25 | 477 |
| docs/context-packs.md | Y | 2026-02-24 | 524 |
| docs/changelog.md | Y | 2026-03-05 | 744 |
| docs/phases.md | Y | 2026-03-05 | 207 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-25 | 262 |
| docs/cheat-sheet.md | Y | 2026-02-24 | 194 |
| docs/ci.md | Y | 2026-02-24 | 107 |
| docs/secrets-reference.md | Y | 2026-03-05 | 50 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs
35 files in `docs/references/` (excluding `.gitkeep`). All listed in context-packs.md.

### Agent & Skill Roster
- Agents: 17 on disk, 17 in CLAUDE.md — MATCH
- Skills: 31 on disk, 31 in CLAUDE.md — MATCH (after fix)

### Counts
- Living docs: 12 | Reference docs: 35 | Plans: 15 | Reports: 9
- Phantom refs: 0 | Unlisted refs: 0 | Agent mismatches: 0 | Skill mismatches: 0

## Phase 2 — Freshness & Accuracy

Latest src/ commit: **2026-03-05**

| Doc | Last Commit | Days Behind | Status |
|-----|-------------|-------------|--------|
| CLAUDE.md | Feb 25 | 8 | STALE-CONTENT (fixed: skills) |
| docs/context-packs.md | Feb 24 | 9 | STALE (Pack S3 not committed) |
| docs/changelog.md | Mar 5 | 0 | CURRENT |
| docs/phases.md | Mar 5 | 0 | CURRENT |
| docs/design.md | Feb 15 | 18 | STABLE |
| docs/failure-patterns.md | Feb 19 | 14 | STALE |
| docs/workflow.md | Feb 25 | 8 | STALE |
| docs/cheat-sheet.md | Feb 24 | 9 | STALE |
| docs/ci.md | Feb 24 | 9 | CURRENT |
| docs/secrets-reference.md | Mar 5 | 0 | CURRENT |
| docs/competitor-careers.md | Feb 16 | 17 | STABLE |
| docs/compgraph-product-spec.md | Feb 15 | 18 | STABLE |

### Discrepancies Found & Fixed
- MEMORY.md: frontend test count said "257 passing, 9 failing" — actual is 266 passing, 0 failing. **FIXED.**
- CLAUDE.md: missing 4 Sentry skills. **FIXED.**

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Backend test count | MATCH | pytest=946, CLAUDE.md=946, MEMORY.md=946 |
| C2: Milestone state | MATCH | M6 complete, M7 in progress |
| C3: Scrapers | MATCH | 4 active (iCIMS x2, Workday x2) |
| C4: Agents | MATCH | 17 on disk = 17 in CLAUDE.md |
| C5: Skills | MATCH | 31 on disk = 31 in CLAUDE.md (after fix) |
| C6: Dev server | MATCH | 165.232.128.28 |
| C7: Dropped competitors | MATCH | Acosta + Advantage |

**Consistency score: 7/7 MATCH**

## Phase 4 — Gap Analysis

### Sprint 3 Gaps
- Pack S3 (Sprint 3 context pack) was drafted in previous session but not committed to `docs/context-packs.md`
- Sprint 3 pre-gate (9 failing tests) is now resolved — all 266 frontend tests pass

### Stale But Non-Critical
- `docs/failure-patterns.md` (Feb 19) — no new failure patterns discovered; low priority
- `docs/workflow.md` (Feb 25) — workflow content still accurate
- `docs/cheat-sheet.md` (Feb 24) — commands unchanged

### Research Gaps
None — all Sprint 3 technologies indexed in Nia (heyapi, tanstack query, openapi-ts, FastAPI refreshed).

## Auto-Fixes Applied

1. **MEMORY.md**: Frontend test count "257 passing, 9 failing" → "266 passing, 0 failing"
2. **MEMORY.md**: Frontend failures line updated from active issue to "RESOLVED"
3. **CLAUDE.md**: Added 4 Sentry skills (`sentry-create-alert`, `sentry-fix-issues`, `sentry-pr-code-review`, `sentry-setup-ai-monitoring`)

## Recommended Actions (prioritized)

1. Commit Pack S3 to `docs/context-packs.md` (Sprint 3 context pack — currently only in session memory)
2. Commit the CLAUDE.md skills fix from this audit
3. Consider refreshing `docs/failure-patterns.md` if new patterns emerge during Sprint 3

## Comparison with Previous Audit (earlier today)

| Metric | Previous | Current |
|--------|----------|---------|
| Consistency score | 4/7 | 7/7 |
| Content mismatches | 4 | 0 (after fixes) |
| Stale docs | 8 | 3 |
| Auto-fixes needed | 5+ | 3 applied |

Previous audit findings (test counts, phases.md, secrets-reference, changelog) were addressed between audits.
