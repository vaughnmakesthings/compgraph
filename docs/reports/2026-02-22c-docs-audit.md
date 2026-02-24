# Documentation Audit Report — 2026-02-22 (c)

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | 19 |
| Phantom refs | 0 |
| Unlisted refs | 0 |
| Stale docs | 0 |
| Content mismatches | 2 |
| Consistency checks passed | 5/7 |
| Research gaps | 2 |
| Auto-fixes applied | TBD |

**Overall Health: YELLOW**

Criteria: 2 content mismatches (review bot list discrepancy, missing T-ROC from competitor-careers.md).

---

## Phase 1 — Inventory

### Living Docs

| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-22 | 402 |
| docs/context-packs.md | Y | 2026-02-21 | 422 |
| docs/changelog.md | Y | 2026-02-22 | 409 |
| docs/phases.md | Y | 2026-02-22 | 376 |
| docs/design.md | Y | 2026-02-15 | 368 |
| docs/failure-patterns.md | Y | 2026-02-19 | 375 |
| docs/workflow.md | Y | 2026-02-21 | 218 |
| docs/cheat-sheet.md | Y | 2026-02-21 | 191 |
| docs/ci.md | Y | 2026-02-21 | 59 |
| docs/secrets-reference.md | Y | 2026-02-18 | 49 |
| docs/competitor-careers.md | Y | 2026-02-16 | 16 |
| docs/compgraph-product-spec.md | Y | 2026-02-15 | 615 |

### Reference Docs

| File | Listed in Packs | Last Commit | Lines |
|------|----------------|-------------|-------|
| ai-generated-design-complaints.md | Y | 2026-02-20 | 115 |
| canadian-portals-research.md | Y | 2026-02-19 | 72 |
| fastapi-pagination-patterns.md | Y | 2026-02-21 | 1211 |
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
| supabase-auth-fastapi.md | Y | 2026-02-21 | 879 |
| troc-ats-research.md | Y | 2026-02-15 | 60 |
| truncate-insert-patterns.md | Y | 2026-02-21 | 658 |
| vitest-infrastructure-best-practices.md | Y | 2026-02-20 | 106 |
| workday-cxs-api.md | Y | 2026-02-12 | 272 |

### Issues Found

- **Content gap**: `docs/competitor-careers.md` lists only 3 competitors (2020 Companies, BDS, MarketSource). Missing T-ROC.
- **Review bot discrepancy**: CLAUDE.md lists "Gemini, Cursor, Copilot, Cubic" but `docs/ci.md` lists "CodeRabbit, Cursor Bugbot, Cubic AI, Copilot". PR #155 actual reviewers: gemini-code-assist, cursor, cubic-dev-ai. Both Gemini and CodeRabbit appear active — total may be 5 bots, not 4.

### Counts

- Living docs: 12 | Reference docs: 19 | Plans: 16 | Reports: 5 (pre-audit) | Memory files: 2
- Phantom refs: 0 | Unlisted refs: 0 | Agent mismatches: 0 | Skill mismatches: 0

---

## Phase 2 — Freshness & Accuracy

Latest src/ commit: 2026-02-22

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-22 | 0 | CURRENT | |
| docs/context-packs.md | 2026-02-21 | 1 | CURRENT | |
| docs/changelog.md | 2026-02-22 | 0 | CURRENT | |
| docs/phases.md | 2026-02-22 | 0 | CURRENT | |
| docs/design.md | 2026-02-15 | 7 | STABLE | Intentionally slow-changing |
| docs/failure-patterns.md | 2026-02-19 | 3 | CURRENT | |
| docs/workflow.md | 2026-02-21 | 1 | CURRENT | |
| docs/cheat-sheet.md | 2026-02-21 | 1 | CURRENT | |
| docs/ci.md | 2026-02-21 | 1 | STALE-CONTENT | Review bot list disagrees with CLAUDE.md |
| docs/secrets-reference.md | 2026-02-18 | 4 | CURRENT | |
| docs/competitor-careers.md | 2026-02-16 | 6 | STALE-CONTENT | Missing T-ROC URLs |
| docs/compgraph-product-spec.md | 2026-02-15 | 7 | STABLE | Intentionally slow-changing |

### State-Reference Checks

| Check | Source of Truth | Result |
|-------|----------------|--------|
| Test count | `pytest --collect-only` = 677 | MEMORY.md = 677 — MATCH |
| Milestone % | phases.md = ~95% | CLAUDE.md = ~95%, MEMORY.md = ~95% — MATCH |
| Active scrapers | `src/compgraph/scrapers/` = icims.py, workday.py (4 companies) | CLAUDE.md = 4, MEMORY.md = 4 — MATCH |
| Skill count | `.claude/skills/` = 13 | CLAUDE.md = 13 — MATCH |
| Agent count | `.claude/agents/` = 11 | CLAUDE.md = 11 — MATCH |
| CI workflows | `.github/workflows/` = ci.yml, cd.yml | docs/ci.md = ci.yml, cd.yml — MATCH |
| Review bots | PR #155 = gemini, cursor, cubic (+CodeRabbit in checks) | CLAUDE.md and ci.md disagree — MISMATCH |

### Specific Discrepancies

1. **Review bots**: CLAUDE.md says "Gemini, Cursor, Copilot, AND Cubic". ci.md says "CodeRabbit, Cursor Bugbot, Cubic AI, Copilot (GitHub)". PR #155 reviews show gemini-code-assist, cursor, cubic-dev-ai reviewed. CodeRabbit also runs as a check. Gemini appears to have replaced CodeRabbit in the review flow, but ci.md wasn't updated.
2. **competitor-careers.md**: Only lists 2020 Companies, BDS, and MarketSource. T-ROC (the 4th active scraper) is absent.

---

## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | MATCH | pytest=677, MEMORY.md=677 |
| C2: Milestone | MATCH | phases.md=~95%, CLAUDE.md=~95%, MEMORY.md=~95% |
| C3: Scrapers | MISMATCH | CLAUDE.md/MEMORY.md say 4 scrapers; competitor-careers.md only lists 3 (missing T-ROC) |
| C4: Agents | MATCH | 11 on disk = 11 in CLAUDE.md |
| C5: Skills | MATCH | 13 on disk = 13 in CLAUDE.md |
| C6: Dev server | MATCH | 165.232.128.28 consistent in CLAUDE.md, MEMORY.md, ci.md |
| C7: Review bots | MISMATCH | CLAUDE.md says Gemini; ci.md says CodeRabbit (both may be active — total is 5 not 4) |

**Consistency score: 5/7 MATCH**

---

## Phase 4 — Gap Analysis

### Current Milestone (M3) Gaps

- **#13 (data quality audit)** — open, no documented quality criteria or methodology reference doc
- **#14 (prompt tuning)** — open, no prompt tuning methodology reference doc
- **#29 (CI secrets)** — open, CI secrets (CODECOV_TOKEN, SNYK_TOKEN) not yet added

### Next Milestone (M4) Status

M4 reference docs are well-prepared:
- `docs/references/truncate-insert-patterns.md` (658 lines) — covers aggregation rebuild patterns
- `docs/references/fastapi-pagination-patterns.md` (1211 lines) — covers detail API pagination
- `docs/references/supabase-auth-fastapi.md` (879 lines) — covers auth (M4d)

M4 open issues (7):
- #70 — Handle multiple PostingEnrichment records per posting
- #148 — Coverage gaps SQL (CROSS JOIN + zip code handling)
- #150 — Daily velocity aggregation performance
- #151 — NULL country duplicate markets
- #152 — Posting lifecycle aggregation calculation
- #18 — Detail API endpoints
- #19/#20/#59 — Auth + alerts (deferred to M4d)

### MEMORY.md Cross-Check

- MEMORY.md mentions #149 for consolidation with #148, but #149 is not in open issues — likely already closed/consolidated. MEMORY.md should remove the #149 reference.

### Unlisted Reference Docs

None — all 19 reference docs on disk are listed in context-packs.md Tier 2 table.

### Research Suggestions

- `/research data-quality-audit-methodology` — define criteria for M3 issue #13 before starting the audit
- `/research alert-system-design-patterns` — M4 issue #20 has no reference doc beyond design.md §10

---

## Auto-Fixes Proposed

1. **Add T-ROC to competitor-careers.md** — the 4th active scraper is missing from the careers URL list
2. **Update ci.md review bots** — add Gemini Code Assist to the list (total: 5 bots, not 4)
3. **Update CLAUDE.md review bots** — update to list all 5 active bots (add CodeRabbit)

---

## Recommended Actions (prioritized)

1. **Fix review bot lists** in both CLAUDE.md and ci.md to list all 5 active bots consistently
2. **Add T-ROC careers URL** to docs/competitor-careers.md
3. **Remove #149 reference** from MEMORY.md (consolidated into #148)
4. **Create data quality audit criteria** doc before starting M3 issue #13

## Suggested Research

- `/research data-quality-audit-methodology` — define data quality criteria for issue #13
- `/research alert-system-design-patterns` — reference doc for M4 issue #20
