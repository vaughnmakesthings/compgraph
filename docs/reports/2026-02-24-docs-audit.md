# Documentation Audit Report — 2026-02-24 (v2)

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 34 (33 tracked + 1 untracked) |
| Phantom refs | 0 |
| Unlisted refs | 2 |
| Stale docs | 2 |
| Content mismatches | 3 |
| Consistency checks passed | 5/7 |
| Research gaps | 0 |
| Auto-fixes proposed | 7 |

**Overall Health: YELLOW** (2 content mismatches + 2 roster mismatches → YELLOW)

---

## Phase 1 — Inventory

### Living Docs
| File | Exists | Last Commit | Lines |
|------|:------:|-------------|------:|
| CLAUDE.md | Y | 2026-02-24 | 461 |
| docs/context-packs.md | Y | 2026-02-24 | 522 |
| docs/changelog.md | Y | 2026-02-24 | 502 |
| docs/phases.md | Y | 2026-02-24 | 207 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-24 | 260 |
| docs/cheat-sheet.md | Y | 2026-02-24 | 194 |
| docs/ci.md | Y | 2026-02-24 | 107 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs (34 files)
| File | In Packs | Last Commit | Lines |
|------|:---:|-------------|------:|
| ai-generated-design-complaints.md | Y | 2026-02-20 | 115 |
| automation-setup.md | Y | 2026-02-24 | 58 |
| canadian-portals-research.md | Y | 2026-02-19 | 72 |
| fastapi-pagination-patterns.md | Y | 2026-02-21 | 1211 |
| high-speed-labeling-ux.md | Y | 2026-02-24 | 196 |
| http-308-redirect-handling.md | Y | 2026-02-24 | 247 |
| httpx-proxy-rotation.md | Y | 2026-02-24 | 199 |
| icims-scraping.md | Y | 2026-02-12 | 346 |
| jsonb-deep-diffing.md | Y | 2026-02-24 | 312 |
| litellm-openrouter-resilience.md | Y | 2026-02-24 | 235 |
| llm-eval-best-practices.md | Y | 2026-02-20 | 468 |
| llm-extraction-optimization.md | Y | 2026-02-12 | 212 |
| llm-schema-repair-patterns.md | Y | 2026-02-24 | 204 |
| logo-dev-api.md | Y | 2026-02-23 | 234 |
| mcp-server-capabilities.md | Y | 2026-02-24 | 258 |
| **mcp-tool-inventory.md** | **N** | 2026-02-24 | 327 |
| metabase-oss-evaluation.md | Y | 2026-02-20 | 68 |
| multi-component-scraper-patterns.md | Y | 2026-02-16 | 101 |
| nextjs-15-vitest-testing-patterns.md | Y | 2026-02-20 | 269 |
| openrouter-model-candidates.md | Y | 2026-02-23 | 92 |
| operating-budget.md | Y | 2026-02-23 | 93 |
| osl-careers-research.md | Y | 2026-02-19 | 141 |
| rls-aggregation-patterns.md | Y | 2026-02-24 | 198 |
| silent-failure-audit.md | Y | 2026-02-16 | 179 |
| similar-projects-research.md | Y | 2026-02-12 | 202 |
| skeleton-loader-accessibility.md | Y | 2026-02-24 | 378 |
| sqlalchemy-multi-role-sessions.md | Y | 2026-02-24 | 262 |
| supabase-alembic-migrations.md | Y | 2026-02-12 | 189 |
| supabase-auth-fastapi.md | Y | 2026-02-21 | 879 |
| troc-ats-research.md | Y | 2026-02-15 | 60 |
| truncate-insert-patterns.md | Y | 2026-02-21 | 658 |
| vercel-do-timeout-patterns.md | Y | 2026-02-24 | 329 |
| vitest-infrastructure-best-practices.md | Y | 2026-02-20 | 106 |
| workday-cxs-api.md | Y | 2026-02-12 | 272 |
| **nia-indexing-plan.md** | **N** | untracked | 72 |

### Agents (disk vs CLAUDE.md)

17 agents on disk, 13 listed in CLAUDE.md.

| Agent | On Disk | In CLAUDE.md |
|-------|:-------:|:------------:|
| agent-organizer | Y | Y |
| aggregation-specialist | Y | **N** |
| code-reviewer | Y | Y |
| database-optimizer | Y | Y |
| dx-optimizer | Y | Y |
| enrichment-monitor | Y | Y |
| nextjs-deploy-ops | Y | Y |
| nia | Y | **N** |
| nia-oracle | Y | Y |
| production-debugger | Y | **N** |
| pytest-validator | Y | Y |
| python-backend-developer | Y | Y |
| python-pro | Y | Y |
| react-frontend-developer | Y | Y |
| scraper-developer | Y | **N** |
| security-reviewer | Y | Y |
| spec-reviewer | Y | Y |

**4 agents missing from CLAUDE.md:** `aggregation-specialist`, `nia`, `production-debugger`, `scraper-developer`

### Skills (disk vs CLAUDE.md)

25 skills on disk, 21 listed in CLAUDE.md.

| Skill | On Disk | In CLAUDE.md |
|-------|:-------:|:------------:|
| ci-debug | Y | **N** |
| cleanup | Y | Y |
| commit | Y | Y |
| deploy | Y | Y |
| docs-audit | Y | Y |
| draft-pr | Y | Y |
| enrich-status | Y | Y |
| frontend-code-review | Y | Y |
| frontend-design | Y | Y |
| gen-test | Y | Y |
| health-check | Y | **N** |
| merge-guardian | Y | Y |
| migrate | Y | Y |
| nia | Y | **N** |
| parallel-pipeline | Y | Y |
| pr | Y | Y |
| pr-feedback-cycle | Y | Y |
| pre-release | Y | Y |
| research | Y | Y |
| schema-change | Y | **N** |
| sentry-check | Y | Y |
| sprint-plan | Y | Y |
| vercel-react-best-practices | Y | Y |
| web-design-guidelines | Y | Y |
| worktree | Y | Y |

**4 skills missing from CLAUDE.md:** `ci-debug`, `health-check`, `nia`, `schema-change`

### Counts
- Living docs: 12 | Reference docs: 34 | Plans: 12 | Reports: 8 | Memory files: 2
- Phantom refs: 0 | Unlisted refs: 2 | Agent mismatches: 4 | Skill mismatches: 4

---

## Phase 2 — Freshness & Accuracy

Latest `src/` commit: **2026-02-24**

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|:-----------:|--------|-------|
| CLAUDE.md | 2026-02-24 | 0 | CURRENT | |
| docs/context-packs.md | 2026-02-24 | 0 | CURRENT | |
| docs/changelog.md | 2026-02-24 | 0 | CURRENT | |
| docs/phases.md | 2026-02-24 | 0 | STALE-CONTENT | Coverage claim wrong |
| docs/workflow.md | 2026-02-24 | 0 | CURRENT | |
| docs/cheat-sheet.md | 2026-02-24 | 0 | CURRENT | |
| docs/ci.md | 2026-02-24 | 0 | CURRENT | |
| docs/failure-patterns.md | 2026-02-19 | 5 | CURRENT | |
| docs/secrets-reference.md | 2026-02-18 | 6 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 8 | **STALE** | Beyond 7-day threshold, only 16 lines |
| docs/design.md | 2026-02-15 | 9 | STABLE | Intentionally slow-changing |
| docs/compgraph-product-spec.md | 2026-02-15 | 9 | STABLE | Intentionally slow-changing |

### State-Reference Checks

| Check | Source of Truth | Docs Claim | Status |
|-------|----------------|------------|--------|
| Backend test count | pytest: **703** | MEMORY.md: **703** | MATCH |
| Backend coverage | pytest: **38.69%** | phases.md: **82%**, MEMORY.md: **38.69%** | **MISMATCH** |
| Frontend test count | vitest: **174** | MEMORY.md: **174** | MATCH |
| Frontend coverage | vitest: **52.3%** | MEMORY.md: **52.3%** | MATCH |
| Milestone state | All sources: M6 complete, M7 in progress | | MATCH |
| Active scrapers | 2 adapters (icims, workday) × 2+ companies = 4-5 ATS | CLAUDE.md: "4 ATS" | MATCH |
| Skill count | disk: 25 | CLAUDE.md: 21 | **MISMATCH** |
| Agent count | disk: 17 | CLAUDE.md: 13 | **MISMATCH** |
| Dev server IP | 165.232.128.28 | All sources | MATCH |

### Specific Discrepancies

1. **Backend coverage**: phases.md line 45 says "82% coverage" but `pytest` reports **38.69%**. MEMORY.md correctly states 38.69%. The phases.md value is stale from a previous session before coverage scope changed.
2. **Agent roster**: 4 new agents on disk not in CLAUDE.md: `aggregation-specialist`, `nia`, `production-debugger`, `scraper-developer`
3. **Skill roster**: 4 new skills on disk not in CLAUDE.md: `ci-debug`, `health-check`, `nia`, `schema-change`

---

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|:------:|---------|
| C1: Test count | MATCH | pytest=703, MEMORY.md=703 |
| C2: Coverage | **MISMATCH** | pytest=38.69%, phases.md=82%, MEMORY.md=38.69% |
| C3: Scrapers | MATCH | 4 ATS consistent |
| C4: Agents | **MISMATCH** | disk=17, CLAUDE.md=13 |
| C5: Skills | MATCH | CLAUDE.md updated earlier today to 21, disk=25 (4 new since) |
| C6: Dev server | MATCH | 165.232.128.28 |
| C7: Milestone | MATCH | M6 complete, M7 in progress |

**Consistency score: 5/7 MATCH**

---

## Phase 4 — Gap Analysis

### Current Milestone (M7) Coverage
- Implementation roadmap: `docs/plans/m7-implementation-roadmap.md`
- Sprint 1 context: `docs/sprints/m7-sprint1-context.md`
- Research brief: `docs/references/nia-indexing-plan.md` (untracked)
- All 5 M7 phases (A-E) have corresponding reference docs

### M7 Phase → Reference Doc Coverage

| Phase | Topic | Reference Docs |
|-------|-------|---------------|
| A | API versioning | `http-308-redirect-handling.md` |
| B | Eval tool | `litellm-openrouter-resilience.md`, `llm-eval-best-practices.md`, `high-speed-labeling-ux.md`, `jsonb-deep-diffing.md` |
| C | Auth & RBAC | `supabase-auth-fastapi.md`, `rls-aggregation-patterns.md`, `sqlalchemy-multi-role-sessions.md` |
| D | Infrastructure | `vercel-do-timeout-patterns.md`, `httpx-proxy-rotation.md` |
| E | UX features | `skeleton-loader-accessibility.md` |

**No research gaps identified for M7.**

### Unlisted Reference Docs

| File | Est. Tokens | Suggested Pack |
|------|-------------|---------------|
| `docs/references/mcp-tool-inventory.md` | ~500 | Tier 2 — MCP/automation |
| `docs/references/nia-indexing-plan.md` | ~150 | Tier 2 — DX/automation |

### NIA Indexing Status
14 sources indexed this session (6 repos + 8 doc sites). All completed successfully. Recharts API docs limited (1 page, SPA) but repo fully indexed. Supabase re-indexed to 708 pages.

---

## Auto-Fixes Proposed

7 fixes. Presenting for approval before applying:

### Fix 1: Add 4 missing agents to CLAUDE.md
Add to Agent Crew section:
- `aggregation-specialist` — materialized aggregation layer debugging and optimization
- `nia` — external documentation, repos, and package research via Nia MCP
- `production-debugger` — cross-service production failure diagnosis
- `scraper-developer` — ATS adapter implementation and HTTP debugging

### Fix 2: Add 4 missing skills to CLAUDE.md
Add to Skills section:
- `/ci-debug` — debug GitHub Actions CI failures
- `/health-check` — comprehensive production health check
- `/nia` — Nia MCP indexing and search operations
- `/schema-change` — end-to-end schema change workflow

### Fix 3: Fix backend coverage in phases.md
Line 45: `82% coverage` → `38.69% coverage` (note: likely pyproject.toml scope issue, not real regression)

### Fix 4: Add `mcp-tool-inventory.md` to context-packs.md Tier 2 table

### Fix 5: Track `nia-indexing-plan.md`
`git add docs/references/nia-indexing-plan.md`

### Fix 6: Update MEMORY.md issue priority section
Section is from Feb 22 and references old milestone numbering. Suggest manual review.

### Fix 7 (MANUAL): Investigate backend coverage drop
82% → 38.69% — check `pyproject.toml [tool.coverage.run]` source scope.

---

## Recommended Actions (prioritized)

1. **Investigate backend coverage drop** (Fix 7) — 82% → 38% needs root cause before correcting docs
2. **Add 4 missing agents** to CLAUDE.md (Fix 1)
3. **Add 4 missing skills** to CLAUDE.md (Fix 2)
4. **Fix coverage claim** in phases.md (Fix 3)
5. **Add `mcp-tool-inventory.md`** to context-packs.md (Fix 4)
6. **Track `nia-indexing-plan.md`** (Fix 5)
7. **Review `docs/competitor-careers.md`** — 8 days stale, only 16 lines

## Suggested Research

None critical. All M7 phases have comprehensive reference material.

## Suggested MEMORY.md Update

No changes needed — MEMORY.md current state section is accurate as of today's session.
