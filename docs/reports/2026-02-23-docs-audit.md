# Documentation Audit Report — 2026-02-23

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 22 |
| Phantom refs | 0 |
| Unlisted refs | 0 |
| Stale docs | 2 |
| Content mismatches | 3 |
| Consistency checks passed | 4/7 |
| Research gaps | 3 |
| Auto-fixes applied | 0 (pending user approval) |

**Overall Health: YELLOW**

Health criteria:
- GREEN: 0 phantom refs, 0 content mismatches, consistency >= 6/7
- YELLOW: 1-2 phantom refs OR 1-2 content mismatches OR consistency 4-5/7
- RED: 3+ phantom refs OR 3+ content mismatches OR consistency <= 3/7

Criteria: 0 phantom refs, 3 content mismatches (phases.md milestone, competitor-careers.md T-ROC, test counts), consistency 4/7.

---

## Phase 1 — Inventory

### Living Docs

| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-23 | 414 |
| docs/context-packs.md | Y | 2026-02-23 | 427 |
| docs/changelog.md | Y | 2026-02-23 | 423 |
| docs/phases.md | Y | 2026-02-23 | 376 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-21 | 218 |
| docs/cheat-sheet.md | Y | 2026-02-21 | 191 |
| docs/ci.md | Y | 2026-02-23 | 74 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs

| File | Listed in Packs | Last Commit | Lines |
|------|----------------|-------------|-------|
| docs/references/ai-generated-design-complaints.md | Y | 2026-02-20 | 115 |
| docs/references/canadian-portals-research.md | Y | 2026-02-19 | 72 |
| docs/references/fastapi-pagination-patterns.md | Y | 2026-02-21 | 1211 |
| docs/references/icims-scraping.md | Y | 2026-02-12 | 346 |
| docs/references/llm-eval-best-practices.md | Y | 2026-02-20 | 468 |
| docs/references/llm-extraction-optimization.md | Y | 2026-02-12 | 212 |
| docs/references/logo-dev-api.md | Y | 2026-02-23 | 234 |
| docs/references/mcp-server-capabilities.md | Y | 2026-02-23 | 202 |
| docs/references/metabase-oss-evaluation.md | Y | 2026-02-20 | 68 |
| docs/references/multi-component-scraper-patterns.md | Y | 2026-02-16 | 101 |
| docs/references/nextjs-15-vitest-testing-patterns.md | Y | 2026-02-20 | 269 |
| docs/references/openrouter-model-candidates.md | Y | 2026-02-23 | 92 |
| docs/references/operating-budget.md | Y | 2026-02-23 | 93 |
| docs/references/osl-careers-research.md | Y | 2026-02-19 | 141 |
| docs/references/silent-failure-audit.md | Y | 2026-02-16 | 179 |
| docs/references/similar-projects-research.md | Y | 2026-02-12 | 202 |
| docs/references/supabase-alembic-migrations.md | Y | 2026-02-12 | 189 |
| docs/references/supabase-auth-fastapi.md | Y | 2026-02-21 | 879 |
| docs/references/troc-ats-research.md | Y | 2026-02-15 | 60 |
| docs/references/truncate-insert-patterns.md | Y | 2026-02-21 | 658 |
| docs/references/vitest-infrastructure-best-practices.md | Y | 2026-02-20 | 106 |
| docs/references/workday-cxs-api.md | Y | 2026-02-12 | 272 |

### UI Specs (context-packs refs)

| File | Exists | Listed |
|------|--------|--------|
| docs/UI/compgraph-design-handoff/compgraph-handoff/specs/map-visualizations.md | Y | Y |
| docs/UI/compgraph-design-handoff/compgraph-handoff/specs/logo-dev-integration.md | Y | Y |

### Issues Found

- **Content mismatch**: `docs/phases.md` says "M3 ~95% complete", "Current State (2026-02-22)", "YOU ARE HERE (M3)". CLAUDE.md and MEMORY.md say M6 complete, Next.js live, Streamlit decommissioned.
- **Content gap**: `docs/competitor-careers.md` lists only 2020 Companies, BDS, MarketSource. Missing T-ROC (4th active scraper).
- **phases.md Future Constraints**: "Frontend framework (Next.js) | M7" and "Streamlit validates views cheaply" — Streamlit is decommissioned, Next.js is live.

### Counts

- Living docs: 12 | Reference docs: 22 | Plans: 22 | Reports: 6 | Memory files: 2
- Phantom refs: 0 | Unlisted refs: 0 | Agent mismatches: 0 | Skill mismatches: 0

### Agent Roster

| On disk | In CLAUDE.md |
|---------|--------------|
| 11 agents | 11 agents — MATCH |

### Skill Roster

| On disk | In CLAUDE.md |
|---------|--------------|
| 13 skills | 13 skills — MATCH |

---

## Phase 2 — Freshness & Accuracy

Latest src/ commit: 2026-02-23 19:59

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-23 | 0 | CURRENT | |
| docs/context-packs.md | 2026-02-23 | 0 | CURRENT | |
| docs/changelog.md | 2026-02-23 | 0 | CURRENT | |
| docs/phases.md | 2026-02-23 | 0 | STALE-CONTENT | Says M3 ~95%, should reflect M6 complete |
| docs/design.md | 2026-02-15 | 8 | STALE | Stable reference, OK |
| docs/failure-patterns.md | 2026-02-19 | 4 | CURRENT | |
| docs/workflow.md | 2026-02-21 | 2 | CURRENT | |
| docs/cheat-sheet.md | 2026-02-21 | 2 | CURRENT | |
| docs/ci.md | 2026-02-23 | 0 | CURRENT | |
| docs/secrets-reference.md | 2026-02-18 | 5 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 7 | STALE-CONTENT | Missing T-ROC |
| docs/compgraph-product-spec.md | 2026-02-15 | 8 | STABLE | Intentionally slow-changing |

### Specific Discrepancies

- **Milestone**: phases.md says M3 ~95%, "YOU ARE HERE (M3)". CLAUDE.md and MEMORY.md say M6 complete.
- **Test count**: pytest collects 699 tests (3 deselected). MEMORY.md says 697 backend + 164 frontend. CLAUDE.md does not cite test count.
- **competitor-careers.md**: Missing T-ROC section (4th active scraper).

---

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | MISMATCH | pytest=699 collected; MEMORY.md=697 backend + 164 frontend (different scopes) |
| C2: Milestone | MISMATCH | phases.md=M3 ~95%, CLAUDE.md=M6 complete, MEMORY.md=M1-M6 complete |
| C3: Scrapers | MATCH | 4 active (T-ROC, 2020 Companies, BDS, MarketSource) in CLAUDE, phases, MEMORY |
| C4: Agents | MATCH | 11 on disk, 11 in CLAUDE.md |
| C5: Skills | MATCH | 13 on disk, 13 in CLAUDE.md |
| C6: Dev server | MATCH | 165.232.128.28 consistent (CLAUDE, MEMORY, ci.md) |
| C7: Dropped competitors | MATCH | Acosta + Advantage dropped (phases.md PR #112, #115) |

**Consistency score: 4/7 MATCH**

---

## Phase 4 — Gap Analysis

### Current Milestone (M6) Coverage

- CLAUDE.md and MEMORY.md correctly state M6 complete.
- `docs/phases.md` has not been updated — still describes M3-era state, M4/M5/M6 as pending.
- M6 task tables in phases.md list many items as "Pending" that are done (Next.js frontend, DO dev, Streamlit decommissioned).

### Next Milestone (M7) Coverage

- M7 section in phases.md exists with task breakdown.
- Some M7 tasks are outdated: "Frontend stack finalization", "Rebuild Streamlit views" — Next.js is already live.
- Auth design: `docs/references/supabase-auth-fastapi.md` exists.
- No dedicated M7 transition checklist.

### Unlisted Reference Docs

All reference docs in `docs/references/` are listed in context-packs.md. No unlisted refs.

### CodeSight Status

- **Index**: Stale (last_indexed_at 2026-02-23T23:46, current commit differs)
- **Docs indexed**: Yes (961 files, 13,516 chunks)
- **Recommendation**: Run `index_codebase(project_path="...", project_name="compgraph")` per CLAUDE.md session-start rule

### Scaling Plan Integration

- `memory/scaling-plan.md` covers arq, LiteLLM, Batch API, Digital Ocean.
- `docs/phases.md` M6c (Scaling Prep) references these — alignment OK.
- M7 production deploy mentioned in both.

### Research Suggestions

- None critical. phases.md structural update is the main gap.

---

## Auto-Fixes Proposed

The following fixes are recommended. **Apply these N fixes? (y/n/select)**

1. **Add T-ROC to competitor-careers.md** — Add section with T-ROC careers URL (4th active scraper).
2. **Update phases.md Current State** — Change "M3 ~95% complete" to "M6 complete" and update date to 2026-02-23. Update Critical Path "YOU ARE HERE" to M7.
3. **Update phases.md Future Constraints** — Change "Frontend framework (Next.js) | M7" to reflect Next.js is live; remove "Streamlit validates views cheaply" (Streamlit decommissioned).

**Restrictions**: Per skill, we do NOT auto-modify `docs/design.md`, `docs/compgraph-product-spec.md`, or `memory/MEMORY.md`. MEMORY.md test count (697/164) is a different scope than pytest — no change needed.

---

## Recommended Actions (prioritized)

1. **Update docs/phases.md** — Align Current State, Critical Path, and Future Constraints with M6 completion (CLAUDE.md/MEMORY.md). This is the highest-impact fix.
2. **Add T-ROC to docs/competitor-careers.md** — Add T-ROC careers URL section.
3. **Reindex CodeSight** — Run `index_codebase` at session start per CLAUDE.md.
4. **Optional**: Update MEMORY.md test counts if backend/frontend split changes (697 + 164 = 861 total).

---

## Suggested Research

None required for current audit scope.
