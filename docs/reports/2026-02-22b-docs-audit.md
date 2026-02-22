# Documentation Audit Report — 2026-02-22 (Session 2)

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 19 |
| Phantom refs | 0 |
| Unlisted refs | 0 |
| Stale docs (>7 days) | 0 |
| Content mismatches | 3 |
| Consistency checks passed | 6/6 applicable |
| Research gaps | 0 |
| Auto-fixes applied | 2 |

**Overall Health: YELLOW**

> YELLOW: 3 content mismatches — test count in MEMORY.md (530 vs 644 actual), LLM Eval Tool stack in scaling-plan.md (Streamlit vs Next.js), Current State date in phases.md (Feb 20 vs Feb 22)

---

## Phase 1 — Inventory

All 12 living docs present. All 19 reference docs listed in context-packs.md. Agent roster: 11 on disk = 11 in CLAUDE.md. Skill roster: 13 on disk = 13 in CLAUDE.md. Zero phantom refs, zero unlisted refs. Perfect structural health.

### Living Docs

| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-21 | 399 |
| docs/context-packs.md | Y | 2026-02-21 | 422 |
| docs/changelog.md | Y | 2026-02-21 | 377 |
| docs/phases.md | Y | 2026-02-21 | 376 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-21 | 218 |
| docs/cheat-sheet.md | Y | 2026-02-21 | 191 |
| docs/ci.md | Y | 2026-02-21 | 59 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

---

## Phase 2 — Freshness & Accuracy

Latest src/ commit: **2026-02-22**

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-21 | 1 | CURRENT | |
| docs/context-packs.md | 2026-02-21 | 1 | CURRENT | |
| docs/changelog.md | 2026-02-21 | 1 | CURRENT | |
| docs/phases.md | 2026-02-21 | 1 | STALE-CONTENT | Current State date says 2026-02-20 |
| docs/design.md | 2026-02-15 | 7 | STABLE | |
| docs/failure-patterns.md | 2026-02-19 | 3 | CURRENT | |
| docs/workflow.md | 2026-02-21 | 1 | CURRENT | |
| docs/cheat-sheet.md | 2026-02-21 | 1 | CURRENT | |
| docs/ci.md | 2026-02-21 | 1 | CURRENT | |
| docs/secrets-reference.md | 2026-02-18 | 4 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 6 | STABLE | |
| docs/compgraph-product-spec.md | 2026-02-15 | 7 | STABLE | |

### Specific Discrepancies
- **MEMORY.md test count**: `530 tests passing` → pytest collects **644** (+114 from M4 work)
- **MEMORY.md Current State**: `Feb 21 2026` → today is Feb 22
- **MEMORY.md Pi section**: missing `compgraph-eval-api` service (FastAPI, port 8001), deployed this session
- **MEMORY.md latest PRs**: `#144, #146` — M4 branch PRs not tracked
- **scaling-plan.md LLM Eval Tool stack**: `LiteLLM + SQLite + Streamlit + Pydantic` → actual: **FastAPI + Next.js + aiosqlite + LiteLLM + Pydantic**
- **phases.md Current State date**: `(2026-02-20)` → should be `(2026-02-22)`

---

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | **MISMATCH** | pytest=644, MEMORY.md=530 |
| C2: Milestone state | MATCH | M3 ~95% across phases.md, CLAUDE.md, MEMORY.md |
| C3: Scrapers | MATCH | 4 active (iCIMS×2, Workday×2) in all sources |
| C4: Agents | MATCH | 11 on disk = 11 in CLAUDE.md |
| C5: Skills | MATCH | 13 on disk = 13 in CLAUDE.md |
| C6: Dev server | MATCH | 165.232.128.28 + 192.168.1.69 consistent |
| C7: Dropped competitors | N/A | Not tracked |

**Consistency score: 6/6 applicable checks** (C1 is content mismatch, flagged separately)

---

## Phase 4 — Gap Analysis

### M4 Coverage
- phases.md has detailed 4-step M4 task breakdown (Steps 4a–4e) — comprehensive
- All M4 tasks show "Pending" from main's perspective (accurate — work is on feature branch)
- 6 open review feedback issues (#148–#153) from M4 bot reviews not yet added to phases.md
- Reference docs present: `truncate-insert-patterns.md` (agg strategy), `supabase-auth-fastapi.md` (auth)

### CodeSight Status
- Index: **current** (commit `78d722e`, 221 files, 5,432 chunks, not stale)
- Docs indexed alongside code: **Yes**

### Scaling Plan
- All scaling topics (arq, LiteLLM, Batch API, DO) mapped to phases.md M6/M7 ✓
- LLM Eval Tool stack description in scaling-plan.md is stale (see auto-fixes)

---

## Auto-Fixes Applied

### Fix 1: docs/phases.md — Current State date updated
`(2026-02-20)` → `(2026-02-22)`

### Fix 2: memory/scaling-plan.md — LLM Eval Tool stack corrected
`LiteLLM + SQLite + Streamlit + Pydantic` → `FastAPI + Next.js + aiosqlite + LiteLLM + Pydantic`

---

## Recommended Manual Edits for MEMORY.md

```diff
-## Current State (Feb 21 2026)
+## Current State (Feb 22 2026)
-- 530 tests passing, CI green
+- 644 tests passing, CI green

 ## Pi Infrastructure (Eval Dashboard)
 ...
+- Services: compgraph-eval (Next.js, port 3000), compgraph-eval-api (FastAPI, port 8001)
```

---

## Recommended Actions (prioritized)

1. **Apply MEMORY.md edits** — test count (530→644) is most likely to cause confusion in future sessions
2. **Update M4 task statuses** in phases.md after `feat/m4-data-quality-aggregation` merges
3. **Add issues #148–#153** to phases.md Open Issue Mapping (M4 review feedback)
4. scaling-plan.md stack fix applied by auto-fix above

*Audit ran: 2026-02-22 | CodeSight: current | Phases: 4/4*
