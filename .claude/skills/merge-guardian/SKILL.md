---
name: merge-guardian
description: Review PR merge readiness — enforce all checks pass, then merge with cleanup
---

# Merge Guardian

Reviews a PR for merge readiness. Enforces that ALL checks pass before allowing merge. Handles post-merge cleanup.

## Input

Accepts a PR number or URL. If not provided, detect from current branch with `gh pr view --json number -q .number`.

## Review Phase

1. **Fetch PR details**:
   ```bash
   gh pr view <N> --json title,body,headRefName,baseRefName,additions,deletions,changedFiles,reviews,statusCheckRollup
   ```
2. **Code review** against CLAUDE.md standards:
   - Append-only data model compliance (no UPDATE/DELETE on historical tables)
   - Async patterns (no sync DB calls)
   - UUID PKs on new tables
   - Timezone-aware timestamps
   - No secrets in code
3. **Run local test suite**: `uv run pytest -x -q`
4. **Lint check**: `uv run ruff check src/ tests/`

## Merge Readiness Checklist

Display a table with each gate's status:

| Gate | Status |
|------|--------|
| All CI checks passed | |
| Local tests pass | |
| Lint clean | |
| PR linked to issue | |
| No merge conflicts | |
| Code review: append-only | |
| Code review: async patterns | |
| Code review: no secrets | |

## Wait-and-Merge Mode

If user requests merge and checks are still running:

1. Poll `gh pr checks <N>` every 30 seconds
2. Show progress: "Waiting for CI... (2/5 checks complete)"
3. **Timeout after 15 minutes** — report status and abort, do NOT merge
4. Only merge when EVERY check shows `pass` — never merge on `pending` or `queued`
5. Merge with: `gh pr merge <N> --squash --delete-branch`

## Post-Merge Cleanup

After successful merge:
1. `git checkout main && git pull`
2. Delete local feature branch: `git branch -d <branch>`
3. Remove worktree if one exists: `git worktree remove <path>` (with confirmation)
4. Report: merged PR URL, closed issues, deleted branches

## Guardrails

- NEVER merge if ANY check is `pending`, `queued`, or `failure`
- NEVER force-merge or bypass required reviews
- NEVER delete branches that aren't fully merged
- If timeout reached, report what's still pending — don't merge
- Always confirm destructive cleanup actions with the user
