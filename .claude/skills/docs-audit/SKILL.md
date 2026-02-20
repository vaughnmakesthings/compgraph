---
name: docs-audit
description: Validate documentation freshness, cross-doc consistency, and research gaps across the CompGraph doc ecosystem
---

# Documentation Audit

Systematic review of the CompGraph documentation ecosystem. Validates freshness, cross-doc consistency, token optimization, agent/skill discoverability, and identifies research gaps before upcoming milestones.

Runs as a linear orchestrator in the main session — no subagent delegation.

## Input

No required arguments.

Optional flags (passed as text after `/docs-audit`):
- `--report-only` — run all 4 phases but skip auto-fixes
- `--phase <N>` — run a single phase (1-4) and report

## Constants

```
LIVING_DOCS = [
  CLAUDE.md,
  docs/context-packs.md,
  docs/changelog.md,
  docs/phases.md,
  docs/design.md,
  docs/failure-patterns.md,
  docs/workflow.md,
  docs/cheat-sheet.md,
  docs/ci.md,
  docs/secrets-reference.md,
  docs/competitor-careers.md,
  docs/compgraph-product-spec.md
]
MEMORY_FILES = [
  ~/.claude/projects/-Users-vmud-Documents-dev-projects-compgraph/memory/MEMORY.md,
  ~/.claude/projects/-Users-vmud-Documents-dev-projects-compgraph/memory/scaling-plan.md
]
STALE_THRESHOLD_DAYS  = 7
MAX_AUTO_FIXES        = 10
REPORT_DIR            = docs/reports/
```

## Phase 1 — Inventory (~5 min)

Build a ground truth manifest of all documentation artifacts.

### Steps

1. **Living docs**: For each file in `LIVING_DOCS`, collect:
   - Exists on disk? (Glob tool)
   - Last commit date: `git log -1 --format=%ci -- <path>`
   - Line count: Read tool + count lines

2. **Reference docs**: List all files in `docs/references/`:
   ```bash
   git ls-files docs/references/
   ```
   For each: last commit date and line count.

3. **Context-packs cross-reference**: Read `docs/context-packs.md` and extract every file path referenced. Compare against files found in steps 1-2. Identify:
   - **Phantom refs**: paths listed in context-packs.md but missing from disk
   - **Unlisted refs**: files on disk in `docs/references/` not mentioned in context-packs.md

4. **Agent roster**: List `.claude/agents/*.md` on disk. Compare against the Agent Crew section in CLAUDE.md. Flag mismatches.

5. **Skill roster**: List `.claude/skills/*/SKILL.md` on disk. Compare against the Skills section in CLAUDE.md. Flag mismatches.

6. **Historical artifacts**: Count files in `docs/plans/` and `docs/reports/`.

7. **Memory files**: Read each file in `MEMORY_FILES` (use Read tool, not git — these may be outside the repo).

### Output

Print an inventory table:

```
## Phase 1 — Inventory

### Living Docs
| File | Exists | Last Commit | Lines |
|------|--------|-------------|-------|
| CLAUDE.md | Y | 2026-02-20 | 245 |
| ... | ... | ... | ... |

### Reference Docs
| File | Listed in Packs | Last Commit | Lines |
|------|----------------|-------------|-------|
| docs/references/icims-api.md | Y | 2026-02-15 | 120 |
| ... | ... | ... | ... |

### Issues Found
- Phantom ref: `docs/references/proxy-provider-comparison.md` (in context-packs.md, not on disk)
- Unlisted: `docs/references/osl-research.md` (on disk, not in context-packs.md)
- Agent mismatch: `enrichment-monitor` on disk but not in CLAUDE.md
- Skill mismatch: `docs-audit` on disk but not in CLAUDE.md

### Counts
- Living docs: 12 | Reference docs: N | Plans: N | Reports: N | Memory files: 2
- Phantom refs: N | Unlisted refs: N | Agent mismatches: N | Skill mismatches: N
```

## Phase 2 — Freshness & Accuracy (~8 min)

Assess whether each living doc reflects current reality.

### Steps

1. **Get latest code commit date**:
   ```bash
   git log -1 --format=%ci -- src/
   ```

2. **For each living doc**, compare its last commit date against `STALE_THRESHOLD_DAYS`:
   - If last commit is > 7 days behind the latest `src/` commit → flag as potentially stale

3. **State-reference checks** (validate specific claims in docs against reality):

   | Check | Source of Truth | Docs to Validate |
   |-------|----------------|-----------------|
   | Test count | `uv run pytest --collect-only -q 2>/dev/null \| tail -1` | CLAUDE.md, MEMORY.md |
   | Milestone % | `docs/phases.md` current state line | CLAUDE.md, MEMORY.md |
   | CI config | `.github/workflows/` files | `docs/ci.md` |
   | Active scrapers | `git ls-files src/compgraph/scrapers/ \| grep -v __pycache__` | CLAUDE.md, MEMORY.md |
   | Skill count | `ls .claude/skills/` | CLAUDE.md, `docs/cheat-sheet.md` |
   | Agent count | `ls .claude/agents/` | CLAUDE.md |

4. **Classify each doc**:
   - **CURRENT** — last commit within threshold, state-references accurate
   - **STALE** — last commit beyond threshold but content likely still accurate
   - **STALE-CONTENT** — contains outdated facts (wrong test count, wrong milestone %, etc.)
   - **BROKEN-REFS** — references files or sections that don't exist
   - **STABLE** — intentionally slow-changing (e.g., `docs/design.md`, `docs/compgraph-product-spec.md`)

### Output

```
## Phase 2 — Freshness & Accuracy

Latest src/ commit: 2026-02-20

| Doc | Last Commit | Days Behind | Status | Notes |
|-----|-------------|-------------|--------|-------|
| CLAUDE.md | 2026-02-20 | 0 | CURRENT | |
| docs/workflow.md | 2026-02-12 | 8 | STALE | Oldest living doc |
| docs/phases.md | 2026-02-18 | 2 | STALE-CONTENT | Says ~90%, should be ~95% |
| ... | ... | ... | ... | ... |

### Specific Discrepancies
- Test count: pytest reports 462, CLAUDE.md says 458, MEMORY.md says 458
- Milestone: phases.md says ~90%, CLAUDE.md says ~95%
```

## Phase 3 — Cross-Doc Consistency (~5 min)

Validate that shared facts agree across CLAUDE.md, phases.md, MEMORY.md, and context-packs.md.

### Checks

Run these 7 specific consistency checks:

| ID | Check | Files Compared | How to Verify |
|----|-------|---------------|---------------|
| C1 | Test count | CLAUDE.md, MEMORY.md vs `pytest --collect-only` | Extract number from docs, compare to pytest output |
| C2 | Milestone state | CLAUDE.md, MEMORY.md, phases.md | Extract M3 percentage from each, compare |
| C3 | Active scraper count | CLAUDE.md, MEMORY.md | Count scraper mentions, compare to `src/compgraph/scrapers/` adapters |
| C4 | Agent roster | CLAUDE.md vs `.claude/agents/` | List agents in both, diff |
| C5 | Skill roster | CLAUDE.md vs `.claude/skills/` | List skills in both, diff |
| C6 | Dev server address | CLAUDE.md, MEMORY.md | Extract IP addresses, compare |
| C7 | Dropped competitors | CLAUDE.md, MEMORY.md | Extract dropped company names, compare |

### Output

```
## Phase 3 — Cross-Doc Consistency

| Check | Status | Details |
|-------|--------|---------|
| C1: Test count | MISMATCH | pytest=462, CLAUDE.md=458, MEMORY.md=458 |
| C2: Milestone | MISMATCH | phases.md=~90%, CLAUDE.md=~95%, MEMORY.md=~95% |
| C3: Scrapers | MATCH | 4 active in all sources |
| C4: Agents | MISMATCH | disk has 9, CLAUDE.md lists 9, but names differ |
| C5: Skills | MISMATCH | disk has 12, CLAUDE.md lists 11 (missing docs-audit) |
| C6: Dev server | MATCH | 192.168.1.69 consistent |
| C7: Dropped | MATCH | Acosta + Advantage in both |

Consistency score: 4/7 MATCH
```

## Phase 4 — Gap Analysis (~5 min)

Identify missing documentation for current and upcoming work.

### Steps

1. **Current milestone (M3) coverage**: Check if `docs/phases.md` has detailed task status for M3. Check if remaining M3 items (data quality review, prompt tuning) have reference docs or design sections.

2. **Next milestone (M4) coverage**: Check `docs/phases.md` for M4 task breakdown. Look for:
   - Aggregation pattern design docs in `docs/references/` or `docs/design.md`
   - API endpoint design docs
   - Auth design docs
   - Any M4-related issues on GitHub: `gh issue list --label M4 --state open`

3. **Unlisted reference docs**: From Phase 1 inventory, list reference docs not in context-packs.md Tier 2 table. Recommend adding them with estimated token counts.

4. **CodeSight coverage**: Check if CodeSight indexes docs alongside code:
   ```
   get_indexing_status(project="compgraph")
   ```
   Verify `docs/` files appear in search results.

5. **Scaling plan integration**: Check if `memory/scaling-plan.md` topics (arq, LiteLLM, Batch API, Digital Ocean) have corresponding entries in `docs/phases.md` M6/M7.

### Output

```
## Phase 4 — Gap Analysis

### Current Milestone (M3) Gaps
- No reference doc for prompt tuning methodology
- Data quality review has no documented criteria

### Next Milestone (M4) Gaps
- No aggregation pattern design doc (truncate+insert mentioned in CLAUDE.md but no dedicated reference)
- No API endpoint design doc
- No auth design doc (deferred to M4d per CLAUDE.md)

### Unlisted Reference Docs
| File | Est. Tokens | Suggested Pack |
|------|-------------|---------------|
| docs/references/osl-research.md | ~800 | Tier 2 |
| ... | ... | ... |

### Research Suggestions
- `/research aggregation truncate-insert patterns for PostgreSQL` (M4 prep)
- `/research JWT auth patterns for FastAPI + Supabase` (M4d prep)

### CodeSight Status
- Index: current / stale
- Docs indexed: Y/N
```

## Auto-Fix Phase

After all 4 phases complete (skipped if `--report-only` was passed).

Up to `MAX_AUTO_FIXES` (10) structural/metadata fixes. **Always show the diff and get user confirmation before applying.**

### Fix Categories

| Category | What It Does | Example |
|----------|-------------|---------|
| 1. Phantom ref annotation | Add `<!-- MISSING -->` comment next to broken refs in context-packs.md | `proxy-provider-comparison.md <!-- MISSING -->` |
| 2. Add unlisted refs | Add unlisted reference docs to context-packs.md Tier 2 table | New row for `osl-research.md` |
| 3. Update date header | Update `phases.md` "Current State" date if stale | `(Feb 20, 2026)` |
| 4. Add missing skills | Add new skills to CLAUDE.md Skills section | `- /docs-audit — ...` |

### Flow

1. Collect all proposed fixes from Phases 1-4
2. If count > `MAX_AUTO_FIXES`, prioritize: Phantom refs > Unlisted refs > Date headers > Skill additions
3. Present fixes as a numbered list with file paths and diffs
4. Ask: "Apply these N fixes? (y/n/select)"
5. If `y` — apply all fixes using Edit tool
6. If `n` — skip, include in report as "recommended manual fixes"
7. If `select` — let user pick which fixes to apply

### Restrictions

- NEVER modify `src/`, `alembic/`, or `tests/` files
- NEVER update `memory/MEMORY.md` automatically — instead print the suggested edit as text for the user to review
- NEVER modify `docs/design.md` or `docs/compgraph-product-spec.md` (stable reference docs)
- NEVER change milestone percentages automatically — flag for manual update with suggested value

## Report Generation

After all phases (and optional auto-fixes), write a report file.

### File

`docs/reports/YYYY-MM-DD-docs-audit.md` (using today's date)

### Format

```markdown
# Documentation Audit Report — YYYY-MM-DD

## Summary

| Category | Count |
|----------|-------|
| Living docs | 12 |
| Reference docs | N |
| Phantom refs | N |
| Unlisted refs | N |
| Stale docs | N |
| Content mismatches | N |
| Consistency checks passed | N/7 |
| Research gaps | N |
| Auto-fixes applied | N |

**Overall Health: GREEN / YELLOW / RED**

Health criteria:
- GREEN: 0 phantom refs, 0 content mismatches, consistency >= 6/7
- YELLOW: 1-2 phantom refs OR 1-2 content mismatches OR consistency 4-5/7
- RED: 3+ phantom refs OR 3+ content mismatches OR consistency <= 3/7

## Phase 1 — Inventory
[paste Phase 1 output]

## Phase 2 — Freshness & Accuracy
[paste Phase 2 output]

## Phase 3 — Cross-Doc Consistency
[paste Phase 3 output]

## Phase 4 — Gap Analysis
[paste Phase 4 output]

## Auto-Fixes Applied
[list of fixes applied, or "Skipped (--report-only)" or "None needed"]

## Recommended Actions (prioritized)
1. [highest priority action]
2. [next action]
3. ...

## Suggested Research
- `/research <topic>` — <reason>
- ...
```

### After report

Suggest: "Run `/commit` to save the audit report, then address recommended actions."

## Guardrails

- **NEVER modify `src/`, `alembic/`, or test files** — this skill only touches docs and config
- **NEVER update `memory/MEMORY.md` automatically** — suggest edits as text output
- **NEVER create GitHub issues without explicit user confirmation**
- **NEVER invoke `/research` automatically** — suggest with exact invocation strings only
- **NEVER commit without showing full diff first** — suggest `/commit` after presenting changes
- **NEVER spiral into content editing** — identify issues, report them, and stop
- **NEVER modify stable reference docs** (`docs/design.md`, `docs/compgraph-product-spec.md`)
- **Phase time budget**: 15 min max per phase — if a phase exceeds this, cut scope and note what was skipped
- **Always write the report** even if zero issues are found (confirms the audit ran)
- **If CodeSight index is stale**, reindex before Phase 4 search (per CLAUDE.md mandatory rule)
- **Treat `pytest --collect-only` failure gracefully** — report "unable to collect" rather than blocking the audit
