# Documentation Audit Report -- 2026-03-05

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 35 |
| Phantom refs | 0 |
| Unlisted refs | 0 |
| Stale docs | 8 |
| Content mismatches | 4 |
| Consistency checks passed | 4/7 |
| Research gaps | 2 |
| Auto-fixes applied | TBD |

**Overall Health: YELLOW**

Reason: 4 content mismatches (test counts, milestone dates, frontend tests), consistency 4/7.

## Phase 1 -- Inventory

### Living Docs
| File | Exists | Last Commit | Lines | Days Behind |
|------|--------|-------------|-------|-------------|
| CLAUDE.md | Y | 2026-02-25 | 473 | 8 |
| docs/context-packs.md | Y | 2026-02-24 | 524 | 9 |
| docs/changelog.md | Y | 2026-02-25 | 714 | 8 |
| docs/phases.md | Y | 2026-02-25 | 207 | 8 |
| docs/design.md | Y | 2026-02-15 | 368 | STABLE |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 | 14 |
| docs/workflow.md | Y | 2026-02-25 | 262 | 8 |
| docs/cheat-sheet.md | Y | 2026-02-24 | 194 | 9 |
| docs/ci.md | Y | 2026-02-24 | 107 | 9 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 | 15 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 | 17 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 | STABLE |

Latest src/ commit: 2026-03-05

### Reference Docs (35 files)
All 35 reference docs on disk are listed in context-packs.md. No phantom refs, no unlisted refs.

### Agent Roster
17 agents on disk, 17 listed in CLAUDE.md -- **MATCH**

### Skill Roster
31 skills on disk, 27 listed in CLAUDE.md -- **MISMATCH**

Missing from CLAUDE.md:
- `sentry-create-alert`
- `sentry-fix-issues`
- `sentry-pr-code-review`
- `sentry-setup-ai-monitoring`

(These are auto-installed Sentry plugin skills, not project-authored. May not need listing.)

### Counts
- Living docs: 12 | Reference docs: 35 | Plans: 15 | Reports: 8 (incl. this one)
- Phantom refs: 0 | Unlisted refs: 0 | Agent mismatches: 0 | Skill mismatches: 4

## Phase 2 -- Freshness & Accuracy

Latest src/ commit: **2026-03-05** (today -- 3 PRs merged this session)

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-25 | 8 | STALE-CONTENT | Test count, milestone state outdated |
| docs/context-packs.md | 2026-02-24 | 9 | STALE | Content likely still accurate |
| docs/changelog.md | 2026-02-25 | 8 | STALE | Missing Mar 1-5 entries |
| docs/phases.md | 2026-02-25 | 8 | STALE-CONTENT | Says 703 tests/82% cov, now 946/84% |
| docs/design.md | 2026-02-15 | 18 | STABLE | Intentionally slow-changing |
| docs/failure-patterns.md | 2026-02-19 | 14 | STALE | May need new patterns from recent work |
| docs/workflow.md | 2026-02-25 | 8 | STALE | Content likely still accurate |
| docs/cheat-sheet.md | 2026-02-24 | 9 | STALE | Content likely still accurate |
| docs/ci.md | 2026-02-24 | 9 | STALE | Content likely still accurate |
| docs/secrets-reference.md | 2026-02-18 | 15 | STALE | May need REDIS_URL addition |
| docs/competitor-careers.md | 2026-02-16 | 17 | STABLE | Competitor URLs rarely change |
| docs/compgraph-product-spec.md | 2026-02-15 | 18 | STABLE | Product spec, slow-changing |

### Specific Discrepancies
- **Backend test count**: pytest reports **946 collected**, MEMORY.md says 837, phases.md says 703
- **Backend coverage**: phases.md says 82%, MEMORY.md says 83.07%, actual likely ~84%
- **Frontend test count**: 266 tests (257 pass, 9 fail), MEMORY.md says 258 passing (15 files)
- **Frontend failures**: 9 tests failing (Market Overview page tests + Eval Runs page tests)
- **Phases.md date**: says "2026-02-24", should be updated to reflect Mar 5 state
- **Secrets reference**: missing `REDIS_URL` (added in PR #243)

## Phase 3 -- Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Backend test count | MISMATCH | pytest=946, MEMORY.md=837, phases.md=703 |
| C2: Milestone state | MATCH | All say M6 complete, M7 in progress |
| C3: Active scrapers | MATCH | 4 adapters (icims, workday + orchestrator/registry) consistent |
| C4: Agent roster | MATCH | 17 agents on disk = 17 in CLAUDE.md |
| C5: Skill roster | MISMATCH | 31 on disk, 27 in CLAUDE.md (4 Sentry plugin skills) |
| C6: Dev server address | MATCH | 165.232.128.28 consistent |
| C7: Frontend test count | MISMATCH | Actual=266 (9 fail), MEMORY.md=258 passing |

**Consistency score: 4/7 MATCH**

## Phase 4 -- Gap Analysis

### Current Milestone (M7) Coverage
- phases.md has M7 task breakdown with Sprint 1 and Sprint 2 items
- Auth chain marked complete in MEMORY.md
- Wave 1 just merged (PRs #242, #243, #244) -- changelog needs update

### Documentation Gaps
1. **secrets-reference.md** -- missing `REDIS_URL` (added in PR #243)
2. **changelog.md** -- no entries for Mar 1-5 work (PR #235 simplification, PRs #238-244)
3. **failure-patterns.md** -- 14 days stale, may need patterns from recent frontend filter work
4. **Frontend test failures** -- 9 tests failing in Market Overview + Eval pages (not a docs issue but flagged)

### Research Suggestions
- `/research supabase-auth session management patterns` -- M7 auth hardening
- `/research redis caching patterns for FastAPI` -- M7 Sprint 2 prep (Redis just provisioned)

## Auto-Fixes Recommended

1. Update MEMORY.md: backend test count 837 -> 946, frontend tests 258 -> 257 passing (266 total, 9 failing)
2. Update phases.md: Current State test count 703 -> 946, coverage 82% -> ~84%, frontend 174 -> 266
3. Update phases.md: date from 2026-02-24 to 2026-03-05
4. Add `REDIS_URL` to docs/secrets-reference.md
5. Update changelog.md with Mar 1-5 entries

## Recommended Actions (prioritized)
1. Fix 9 failing frontend tests (Market Overview + Eval pages) -- likely broken by recent merges
2. Update MEMORY.md test counts and milestone state
3. Update phases.md Current State section
4. Add changelog entries for Mar 1-5 work
5. Add REDIS_URL to secrets-reference.md
6. Consider whether Sentry plugin skills should be listed in CLAUDE.md (probably not -- they're auto-installed)
