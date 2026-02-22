# Development Workflow

This document defines the development workflow for implementing features and fixes. It integrates the agent crew (project-level agents) with human review gates.

---

## Overview

```
Step  0: Context Loading .................. auto (every session)
Step  1: Research & Scope ................. autonomous
Step  2: Design / Plan Approval .......... GATE: human reviews plan
Step  3: Implementation (TDD) ............ autonomous (python-backend-developer)
Step  4: Lint / Type / Test .............. autonomous (ruff + pytest hooks)
Step  5: Code Review ..................... autonomous (code-reviewer agent)
Step  6: Test Audit ...................... autonomous (pytest-validator agent)
Step  7: Spec Alignment .................. autonomous (spec-reviewer agent)
Step  8: Create PR ....................... autonomous
Step  9: CI Testing ...................... GitHub Actions
Step 10: Human Review & Merge ........... GATE: human approves
Step 11: Auto-Deploy .................... CD workflow (automatic)
```

### Diagram

```
                          HUMAN GATES
                              |
  0 ─── 1 ─── 2 ──[APPROVE]─── 3 ─── 4 ─── 5 ─── 6 ─── 7 ─── 8
                                                                  |
                                                        9 ─── 10 ──[MERGE]─── 11 (auto-deploy)
```

---

## Step-by-Step

### Step 0: Context Loading

| Attribute | Value |
|-----------|-------|
| **Trigger** | Session start |
| **Mechanism** | Tiered context system (`docs/context-packs.md`) |
| **Gate** | None |

**How it works:**
- Tier 0: `CLAUDE.md` loaded automatically
- Read `docs/changelog.md` (latest entry) for continuity
- Tier 1: Load task-specific context pack for current work
- Tier 2: Reference docs on demand

---

### Step 1: Research & Scope

| Attribute | Value |
|-----------|-------|
| **Trigger** | New feature or issue |
| **Agent** | Main session or `Explore` subagent |
| **Gate** | None |

Understand the problem space. Read relevant code, check existing patterns, identify affected files. For specialist questions, use project agents (e.g., `database-optimizer` for indexing strategy).

---

### Step 2: Design / Plan Approval

| Attribute | Value |
|-----------|-------|
| **Trigger** | Research complete |
| **Agent** | Main session (EnterPlanMode) |
| **Gate** | **HUMAN APPROVAL** |

Write a plan covering: files to create/modify, approach, trade-offs. Present to user for approval before writing any code.

---

### Step 3: Implementation (TDD)

| Attribute | Value |
|-----------|-------|
| **Trigger** | Plan approved |
| **Agent** | `python-backend-developer` (project-level) |
| **Gate** | None |

Write tests first, then implementation. PostToolUse hooks auto-run ruff format and pytest on every Python file edit.

---

### Step 4: Lint / Type / Test

| Attribute | Value |
|-----------|-------|
| **Trigger** | Implementation complete |
| **Mechanism** | Automated via hooks + manual verification |
| **Gate** | All green to proceed |

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pytest
```

---

### Step 5: Code Review

| Attribute | Value |
|-----------|-------|
| **Trigger** | Step 4 passes |
| **Agent** | `code-reviewer` (project-level) |
| **Gate** | No critical issues |

Reviews: plan alignment, async patterns, append-only enforcement, error handling, test coverage.

---

### Step 6: Test Audit

| Attribute | Value |
|-----------|-------|
| **Trigger** | Code review passes |
| **Agent** | `pytest-validator` (project-level) |
| **Gate** | No hollow tests |

Audits: hollow assertions, TODO placeholders, insufficient coverage, missing edge cases, DB isolation.

---

### Step 7: Spec Alignment

| Attribute | Value |
|-----------|-------|
| **Trigger** | Test audit passes |
| **Agent** | `spec-reviewer` (project-level) |
| **Gate** | Goals met, no scope creep |

Validates implementation against `docs/compgraph-product-spec.md`. Flags unrelated features for removal.

---

### Step 8: Create PR

| Attribute | Value |
|-----------|-------|
| **Trigger** | All review gates pass |
| **Agent** | Main session |
| **Gate** | None |

Create PR with summary, test plan, and review gate results.

---

### Step 9: CI Testing

| Attribute | Value |
|-----------|-------|
| **Trigger** | PR created |
| **Mechanism** | GitHub Actions |
| **Gate** | CI green |

Runs: ruff lint + format, pytest, security scan (when configured).

---

### Step 10: Human Review & Merge

| Attribute | Value |
|-----------|-------|
| **Trigger** | CI green |
| **Agent** | None (human) |
| **Gate** | **HUMAN APPROVAL** |

Human reviews PR, approves, and merges.

---

### Step 11: Auto-Deploy

| Attribute | Value |
|-----------|-------|
| **Trigger** | Merge to main (CI passes) |
| **Mechanism** | GitHub Actions CD workflow (`cd.yml`) |
| **Gate** | Health check |

After merge, the CD workflow automatically:
1. SSHs to the DO dev server
2. Pulls latest main, syncs dependencies
3. Runs Alembic migrations
4. Restarts services
5. Verifies health endpoint

No manual action required. Monitor at: GitHub Actions → CD workflow runs.

---

## Agent Handoff Protocol

When delegating to a project-level agent:
1. Load the agent's recommended context pack from `docs/context-packs.md`
2. Include the latest `docs/changelog.md` entry
3. State the specific task clearly
4. Agent works autonomously, returns results

When querying a specialist project agent (e.g., `database-optimizer`, `python-pro`):
1. Formulate a specific question (not "help me build X")
2. Include relevant context pack reference
3. State project constraints (async, append-only, SQLAlchemy 2.0)

---

## Updating Context After Work

After completing significant work:
1. Update `docs/changelog.md` with a new session entry
2. Update `docs/phases.md` task status
3. If new failure modes discovered, add to `docs/failure-patterns.md`
4. If architecture changed, update relevant `docs/design.md` section
