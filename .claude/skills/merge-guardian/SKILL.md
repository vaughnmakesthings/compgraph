---
name: merge-guardian
description: Review PR merge readiness — enforce all checks pass, then merge with cleanup
---

# Merge Guardian

Reviews a PR for merge readiness. Enforces that ALL checks pass before allowing merge. Handles post-merge cleanup.

## Tool Preferences

**Use GitHub MCP tools** for all structured data retrieval:
- `mcp__github__pull_request_read` — PR details, diff, status checks, files, reviews, comments
- `mcp__github__list_pull_requests` — list PRs by head/base branch
- `mcp__github__merge_pull_request` — squash merge
- `mcp__github__update_pull_request` — retarget base branch

**Use `gh` CLI** only for:
- `gh pr checks <N>` — polling CI status (MCP has no polling/wait mechanism)
- Post-merge git operations (checkout, branch delete, worktree remove)

## Input

Accepts a PR number or URL. If not provided, detect from current branch with `gh pr view --json number -q .number`.

## Review Phase

1. **Fetch PR details** via MCP:
   ```
   mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, method="details")
   ```
   Extract: title, body, headRefName, baseRefName, additions, deletions, changedFiles.

   Also fetch review status:
   ```
   mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, method="reviews")
   ```

   And CI status:
   ```
   mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, method="status")
   ```

2. **Stacked PR detection**:
   - Check `baseRefName` from PR details
   - If base branch is NOT `main`:
     - Warn: "Stacked PR detected — base branch is `<baseRefName>`, not `main`"
     - Check if the base branch has an open PR:
       ```
       mcp__github__list_pull_requests(owner="vaughnmakesthings", repo="compgraph", head="vaughnmakesthings:<baseRefName>", state="open")
       ```
     - If base branch PR is **still open**: abort with "Merge the base PR first (#<N>), then retarget this PR to main"
     - If base branch PR is **merged**: retarget via MCP:
       ```
       mcp__github__update_pull_request(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, base="main")
       ```
       Then suggest `git rebase main` locally.
   - If base branch IS `main`: continue normally

3. **Code review** against CLAUDE.md standards:
   - Append-only data model compliance (no UPDATE/DELETE on historical tables)
   - Async patterns (no sync DB calls)
   - UUID PKs on new tables
   - Timezone-aware timestamps
   - No secrets in code
4. **Run local test suite**: `uv run pytest -x -q`
5. **Lint check**: `uv run ruff check src/ tests/`

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
| Base branch is main (or parent merged) | |
| Sentry: no unresolved critical (optional) | Run `/sentry-check` if Sentry configured |

## Wait-and-Merge Mode

If user requests merge and checks are still running:

1. Poll `gh pr checks <N>` every 30 seconds (CLI — MCP has no polling)
2. Show progress: "Waiting for CI... (2/5 checks complete)"
3. **Timeout after 15 minutes** — report status and abort, do NOT merge
4. Only merge when EVERY check shows `pass` — never merge on `pending` or `queued`
5. Merge via MCP:
   ```
   mcp__github__merge_pull_request(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, merge_method="squash", commit_title="<PR title> (#<N>)")
   ```

## Post-Merge Cleanup

After successful merge:
1. `git checkout main && git pull`
2. Delete local feature branch: `git branch -d <branch>`
3. Remove worktree if one exists: `git worktree remove <path>` (with confirmation)
4. **Check for dependent PRs**:
   ```
   mcp__github__list_pull_requests(owner="vaughnmakesthings", repo="compgraph", base="<merged-branch>", state="open")
   ```
   - If other PRs target the just-merged branch, offer to retarget them to main:
     ```
     mcp__github__update_pull_request(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, base="main")
     ```
   - Suggest rebase for each: `git checkout <branch> && git rebase main`
5. Report: merged PR URL, closed issues, deleted branches, retargeted PRs

## Guardrails

- NEVER merge if ANY check is `pending`, `queued`, or `failure`
- NEVER force-merge or bypass required reviews
- NEVER delete branches that aren't fully merged
- NEVER merge a stacked PR whose base PR is still open
- If timeout reached, report what's still pending — don't merge
- Always confirm destructive cleanup actions with the user
