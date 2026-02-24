---
name: ci-debug
description: Debug GitHub Actions CI failures — fetch logs, identify failing step, correlate with local test results
---

# CI Debug

Fetches the latest failed GitHub Actions workflow run, identifies the failing step, and correlates with local test results to accelerate fix iteration.

## Tool Preferences

**Use GitHub MCP tools** for Actions data:
- `mcp__github__actions_list` — list workflow runs with status filter
- `mcp__github__actions_get` — get specific run details and jobs
- `mcp__github__get_job_logs` — fetch logs for a failed job

**Use `gh` CLI** only as fallback if MCP actions tools lack needed granularity.

## Input

- No arguments: debug the most recent failed CI run
- `<run_id>`: debug a specific workflow run by ID
- `<pr_number>`: debug the latest CI run for a specific PR

## Steps

### 1. Find the Failed Run

```
mcp__github__actions_list(owner="vaughnmakesthings", repo="compgraph", status="failure")
```

If debugging a specific PR, filter by branch name. Report: run ID, branch, trigger event, timestamp.

### 2. Identify Failing Job and Step

```
mcp__github__actions_get(owner="vaughnmakesthings", repo="compgraph", run_id=<run_id>)
```

Extract which job failed (lint, typecheck, test, build) and which step within it.

### 3. Fetch Failure Logs

```
mcp__github__get_job_logs(owner="vaughnmakesthings", repo="compgraph", job_id=<job_id>)
```

Extract the key error: compiler error, test failure, lint violation, or build error.

### 4. Correlate with Local State

Based on the failure type:

| CI Failure | Local Command | What to Check |
|------------|---------------|---------------|
| Backend lint | `uv run ruff check src/ tests/` | Same violations locally? |
| Backend typecheck | `uv run mypy src/compgraph/` | Type errors may differ if deps are stale — run `uv sync` first |
| Backend tests | `uv run pytest -x -q --tb=short` | Run the specific failing test: `uv run pytest <test_file>::<test_name> -v` |
| Frontend lint | `cd web && npm run lint` | ESLint errors |
| Frontend typecheck | `cd web && npm run typecheck` | TypeScript errors — may need `npm ci` if lockfile changed |
| Frontend tests | `cd web && npm test` | Run specific: `cd web && npx vitest run <test_file>` |
| Frontend build | `cd web && npm run build` | SSR errors, missing env vars, import issues |

### 5. Report

Present a summary:

```
## CI Failure Report

**Run:** #<id> on branch `<branch>` (<timestamp>)
**Failed job:** <job_name>
**Failed step:** <step_name>
**Error:** <key error message>

### Root Cause
<explanation>

### Fix
<specific fix with file/line references>

### Local Reproduction
<command to reproduce locally>
```

## CI Workflow Reference

CompGraph CI (`.github/workflows/ci.yml`) has change detection — only affected jobs run:

| Job | Triggers on | What it checks |
|-----|-------------|----------------|
| `changes` | All PRs | Detects which paths changed (backend/frontend/eval) |
| `lint` | Backend changes | `ruff check` + `ruff format --check` |
| `typecheck` | Backend changes | `mypy src/compgraph/` |
| `test` | Backend changes | `pytest` (unit only, no integration) |
| `frontend-lint` | Frontend changes | `npm run lint` (ESLint) |
| `frontend-typecheck` | Frontend changes | `npm run typecheck` |
| `frontend-test` | Frontend changes | `npm test` (Vitest) |
| `frontend-build` | Frontend changes | `npm run build` |

CD (`.github/workflows/cd.yml`) runs on push to `main` — deploys to DO droplet via `infra/deploy-ci.sh`.

## Common CI-Specific Failures

These fail in CI but not locally:

- **Missing env vars**: CI doesn't have `.env` — check if test depends on `settings` without mocking
- **Ubuntu vs macOS differences**: CI runs Ubuntu, you run macOS — path separators, case sensitivity
- **Stale lockfiles**: `uv.lock` or `package-lock.json` out of sync with pyproject.toml/package.json
- **Flaky tests**: Tests that depend on timing, network, or execution order — run with `pytest --count=3 -x` locally to reproduce
- **Node version mismatch**: CI uses Node 20 — check `node --version` locally
