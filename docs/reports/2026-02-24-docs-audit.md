# Documentation Audit Report — 2026-02-24

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 23 |
| Plans | 12 |
| Reports | 6 (now 7 with this) |
| Memory files | 2 |
| Phantom refs | 0 |
| Unlisted refs | 0 |
| Agent mismatches | 0 |
| Skill mismatches | 3 |
| Stale docs | 3 |
| Content mismatches | 4 |
| Consistency checks passed | 4/7 |
| Auto-fixes proposed | 5 |

**Overall Health: YELLOW** (3 content mismatches, consistency 4/7)

---

## Phase 1 — Inventory

### Living Docs

| File | Exists | Last Commit | Lines |
|------|:------:|-------------|------:|
| CLAUDE.md | Y | 2026-02-24 | 444 |
| docs/context-packs.md | Y | 2026-02-24 | 498 |
| docs/changelog.md | Y | 2026-02-24 | 479 |
| docs/phases.md | Y | 2026-02-24 | 207 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-24 | 260 |
| docs/cheat-sheet.md | Y | 2026-02-24 | 194 |
| docs/ci.md | Y | 2026-02-24 | 108 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs

| File | Listed in Packs | Last Commit | Lines |
|------|:---:|-------------|------:|
| ai-generated-design-complaints.md | Y | 2026-02-20 | 115 |
| automation-setup.md | Y | 2026-02-24 | 58 |
| canadian-portals-research.md | Y | 2026-02-19 | 72 |
| fastapi-pagination-patterns.md | Y | 2026-02-21 | 1211 |
| icims-scraping.md | Y | 2026-02-12 | 346 |
| llm-eval-best-practices.md | Y | 2026-02-20 | 468 |
| llm-extraction-optimization.md | Y | 2026-02-12 | 212 |
| logo-dev-api.md | Y | 2026-02-23 | 234 |
| mcp-server-capabilities.md | Y | 2026-02-24 | 258 |
| metabase-oss-evaluation.md | Y | 2026-02-20 | 68 |
| multi-component-scraper-patterns.md | Y | 2026-02-16 | 101 |
| nextjs-15-vitest-testing-patterns.md | Y | 2026-02-20 | 269 |
| openrouter-model-candidates.md | Y | 2026-02-23 | 92 |
| operating-budget.md | Y | 2026-02-23 | 93 |
| osl-careers-research.md | Y | 2026-02-19 | 141 |
| silent-failure-audit.md | Y | 2026-02-16 | 179 |
| similar-projects-research.md | Y | 2026-02-12 | 202 |
| supabase-alembic-migrations.md | Y | 2026-02-12 | 189 |
| supabase-auth-fastapi.md | Y | 2026-02-21 | 879 |
| troc-ats-research.md | Y | 2026-02-15 | 60 |
| truncate-insert-patterns.md | Y | 2026-02-21 | 658 |
| vitest-infrastructure-best-practices.md | Y | 2026-02-20 | 106 |
| workday-cxs-api.md | Y | 2026-02-12 | 272 |

### Agents (disk vs CLAUDE.md)

12 agents on disk, 12 listed in CLAUDE.md. **All match.**

### Skills (disk vs CLAUDE.md)

21 skills on disk, 18 listed in CLAUDE.md.

| Skill | On Disk | In CLAUDE.md |
|-------|:-------:|:------------:|
| cleanup | Y | Y |
| commit | Y | Y |
| deploy | Y | Y |
| docs-audit | Y | Y |
| draft-pr | Y | Y |
| enrich-status | Y | Y |
| frontend-code-review | Y | **N** |
| frontend-design | Y | Y |
| gen-test | Y | Y |
| merge-guardian | Y | Y |
| migrate | Y | Y |
| parallel-pipeline | Y | Y |
| pr | Y | Y |
| pr-feedback-cycle | Y | Y |
| pre-release | Y | Y |
| research | Y | Y |
| sentry-check | Y | Y |
| sprint-plan | Y | Y |
| vercel-react-best-practices | Y | **N** |
| web-design-guidelines | Y | **N** |
| worktree | Y | Y |

**3 skills missing from CLAUDE.md:** `frontend-code-review`, `vercel-react-best-practices`, `web-design-guidelines`

### Counts

- Living docs: 12 | Reference docs: 23 | Plans: 12 | Reports: 7 | Memory files: 2
- Phantom refs: 0 | Unlisted refs: 0 | Agent mismatches: 0 | Skill mismatches: 3

---

## Phase 2 — Freshness & Accuracy

Latest `src/` commit: **2026-02-24**

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|:-----------:|--------|-------|
| CLAUDE.md | 2026-02-24 | 0 | CURRENT | |
| docs/context-packs.md | 2026-02-24 | 0 | CURRENT | |
| docs/changelog.md | 2026-02-24 | 0 | CURRENT | |
| docs/phases.md | 2026-02-24 | 0 | STALE-CONTENT | Test counts outdated (see below) |
| docs/design.md | 2026-02-15 | 9 | STABLE | Intentionally slow-changing |
| docs/failure-patterns.md | 2026-02-19 | 5 | CURRENT | |
| docs/workflow.md | 2026-02-24 | 0 | CURRENT | |
| docs/cheat-sheet.md | 2026-02-24 | 0 | CURRENT | |
| docs/ci.md | 2026-02-24 | 0 | STALE-CONTENT | Incorrect Vercel deploy claim |
| docs/secrets-reference.md | 2026-02-18 | 6 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 8 | STALE | Oldest living doc, but content static |
| docs/compgraph-product-spec.md | 2026-02-15 | 9 | STABLE | Intentionally slow-changing |

### Specific Discrepancies

1. **Backend test count:** pytest reports **703 collected**, phases.md says "703 tests" (**match**), but coverage is now **38.69%** — phases.md says "82% coverage" and "82.27% coverage". Coverage dropped significantly, likely due to new source code without corresponding test additions.

2. **Frontend test count:** Vitest reports **174 passing**, phases.md says "164 tests, 52.3% coverage". Frontend tests increased by 10 since the number was last recorded.

3. **MEMORY.md test counts:** Says "697 passing, 82.27% coverage" (backend) and "164 passing, 52.3% coverage" (frontend) — both stale.

4. **docs/ci.md Vercel claim:** Section "Frontend CD (Vercel via CD workflow)" claims Vercel deploys via `cd.yml` using `npx vercel deploy --prod`. The actual `cd.yml` has **zero Vercel references** — it only does SSH backend deployment. Vercel deploys via its own GitHub App integration automatically on push to main. The root CLAUDE.md correctly states "No manual deploy needed — Vercel handles build and CDN distribution."

---

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|:------:|---------|
| C1: Backend test count | MATCH | pytest=703, phases.md=703 |
| C2: Backend coverage | **MISMATCH** | pytest=38.69%, phases.md=82%, MEMORY.md=82.27% |
| C3: Frontend test count | **MISMATCH** | vitest=174, phases.md=164, MEMORY.md=164 |
| C4: Agent roster | MATCH | 12 on disk, 12 in CLAUDE.md |
| C5: Skill roster | **MISMATCH** | 21 on disk, 18 in CLAUDE.md (missing 3) |
| C6: Dev server IP | MATCH | 165.232.128.28 in CLAUDE.md and MEMORY.md |
| C7: Vercel deploy method | MATCH | CLAUDE.md correctly says GitHub App integration |

**Consistency score: 4/7 MATCH**

### Coverage Drop Investigation

The backend coverage dropped from 82% to 38.69%. This needs investigation — likely `--cov` scope changed or new uncovered modules were added. The `pyproject.toml` `[tool.coverage]` config should be checked.

---

## Phase 4 — Gap Analysis

### Current Milestone (M7) Coverage

- M7 implementation roadmap exists: `docs/plans/m7-implementation-roadmap.md`
- Gap analysis exists: `docs/gap-analysis-consolidated.md`
- Auth reference doc exists: `docs/references/supabase-auth-fastapi.md` (879 lines)
- Eval best practices exists: `docs/references/llm-eval-best-practices.md`
- Truncate-insert patterns exists: `docs/references/truncate-insert-patterns.md`

**No M7 gaps in reference documentation.**

### Missing from CLAUDE.md Skills

These 3 skills exist on disk but are not documented:

| Skill | Purpose (inferred) | Priority |
|-------|-------------------|----------|
| `/frontend-code-review` | Review frontend file changes | Medium |
| `/vercel-react-best-practices` | React/Next.js performance patterns | Low |
| `/web-design-guidelines` | Web interface guidelines compliance | Low |

### docs/ci.md Inaccuracy

The "Frontend CD" section (lines 69-79) incorrectly describes Vercel deployment as happening via `cd.yml` with `npx vercel deploy --prod` and GitHub secrets (`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`). In reality:
- Vercel deploys via its own GitHub App on push to main — no workflow file involved
- The duplicate Vercel deploy step was already removed from `cd.yml` in commit `a1b3bba` ("chore(ci): remove duplicate Vercel deploy from CD workflow")
- `docs/ci.md` was not updated to reflect this removal

---

## Auto-Fixes Proposed

5 fixes identified. Presenting for approval:

### Fix 1: Add 3 missing skills to CLAUDE.md

Add after the `/sentry-check` line (line 430):

```
- `/frontend-code-review` — review frontend files against checklist
- `/vercel-react-best-practices` — React/Next.js performance optimization guidelines
- `/web-design-guidelines` — Web Interface Guidelines compliance audit
```

### Fix 2: Update docs/ci.md Frontend CD section

Replace lines 69-79 (incorrect Vercel via CD workflow) with:

```markdown
### Frontend CD (Vercel GitHub App)

Vercel deploys the Next.js frontend automatically via its GitHub App integration:

1. Push to `main` → Vercel detects changes in `web/`
2. Vercel builds and deploys to its CDN edge network
3. API calls rewritten: `/api/*` → `https://dev.compgraph.io/api/*` (via `web/vercel.json`)

**No workflow file or GitHub secrets needed** — Vercel manages the integration directly.
**Env vars (Vercel dashboard):** `NEXT_PUBLIC_API_URL=https://dev.compgraph.io`
```

### Fix 3: Update phases.md frontend test count

Line 135: `164 tests, 52.3% coverage` → `174 tests`

### Fix 4: Update phases.md current state frontend test count

Line 45: `Frontend: 164 tests, 52% coverage` → `Frontend: 174 tests`

### Fix 5 (MANUAL — not auto-fixable): Investigate backend coverage drop

Backend coverage dropped from 82% → 38.69%. This likely indicates a `--cov` configuration change, not an actual quality regression. **Requires manual investigation** of `pyproject.toml` coverage settings and `pytest.ini` options.

---

## Recommended Actions (prioritized)

1. **Investigate backend coverage drop** — 82% → 38% is a red flag. Check `pyproject.toml [tool.coverage.run] source` and whether new modules are excluded.
2. **Fix docs/ci.md** Vercel section — currently documents a workflow that doesn't exist (Fix 2)
3. **Add 3 missing skills** to CLAUDE.md (Fix 1)
4. **Update test counts** in phases.md (Fixes 3-4)
5. **Update MEMORY.md** test counts manually (697→703 backend, 164→174 frontend, coverage TBD)

## Suggested Research

*None needed — M7 reference documentation is comprehensive.*
