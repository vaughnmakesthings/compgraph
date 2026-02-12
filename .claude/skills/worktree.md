# Worktree Setup

Sets up an isolated git worktree for a GitHub issue with venv, dependencies, and test baseline.

## Input

Accepts a GitHub issue number or URL. If not provided, ask the user.

## Steps

1. **Fetch latest**: `git fetch origin`
2. **Parse issue**: Extract the issue number. Read the issue title with `gh issue view <N> --json title -q .title`
3. **Create branch name**: `feat/issue-<N>` (slugified from title if short enough, otherwise just the number)
4. **Create worktree**: `git worktree add ../compgraph-issue-<N> -b feat/issue-<N> origin/main`
5. **Set up venv** (in the new worktree directory):
   ```bash
   cd ../compgraph-issue-<N>
   python3.13 -m venv .venv
   source .venv/bin/activate
   uv sync
   ```
6. **Verify baseline**: `uv run pytest -x -q` — capture the test count and any failures
7. **Report** to the user:
   - Worktree path
   - Branch name
   - Python version confirmed
   - Test baseline (count + pass/fail)
   - Next steps: "cd ../compgraph-issue-<N> to start working"

## Guardrails

- Use Python 3.13, NOT 3.14
- If the branch already exists, ask user before overwriting
- If worktree directory already exists, report it and ask user how to proceed
- Never create a worktree from a dirty working tree without warning
