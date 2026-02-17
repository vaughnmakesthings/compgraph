---
name: parallel-pipeline
description: Decompose a GitHub issue into subtasks, dispatch parallel agents in worktrees, assemble result
---

# Parallel Agent Pipeline

Decomposes a GitHub issue into independent subtasks, dispatches parallel agents in isolated worktrees, and assembles the combined result.

## Input

Accepts a GitHub issue number or URL.

## Phase 1: Decomposition

1. **Read the issue**: `gh issue view <N> --json title,body,labels`
2. **Load context**: Read `CLAUDE.md` and the appropriate context pack from `docs/context-packs.md`
3. **Analyze for parallelism**: Identify subtasks that can be worked independently:
   - Different files/modules with no shared state
   - Independent test files
   - Separate API endpoints
   - Documentation vs code changes
4. **Present decomposition** to user:
   - List each subtask with: description, files affected, estimated complexity
   - Mark dependencies between subtasks (if any)
   - **Get user approval before proceeding**

## Phase 2: Dispatch

For each independent subtask:

1. **Create worktree**: `git worktree add ../compgraph-issue-<N>-task-<M> -b feat/issue-<N>-task-<M> origin/main`
2. **Spawn agent** using the Task tool with `run_in_background: true`:
   - Use `python-backend-developer` subagent for implementation tasks
   - Provide the subtask description, affected files, and CLAUDE.md conventions
   - Include: "Run `uv run pytest -x -q` after changes. Iterate until all tests pass. Max 5 retry cycles."
3. **Track progress**: Monitor each background agent's output file

## Phase 3: Assembly

Once all agents complete:

1. **Check results**: Read each agent's output — identify successes and failures
2. **Merge subtask branches** into a combined feature branch:
   ```bash
   git checkout -b feat/issue-<N>-combined origin/main
   git merge feat/issue-<N>-task-1
   git merge feat/issue-<N>-task-2
   # ... resolve conflicts if needed
   ```
3. **Run full test suite** on the combined branch: `uv run pytest -v`
4. **Report** to user:
   - Per-agent status (success/fail with summary)
   - Combined test results
   - Any merge conflicts that need manual resolution
   - Ready for PR creation? (suggest using `/pr` skill)

## Phase 4: Cleanup (on user request)

Remove all temporary worktrees and branches:
```bash
git worktree remove ../compgraph-issue-<N>-task-*
git branch -d feat/issue-<N>-task-*
```

## Guardrails

- Maximum 4 parallel agents (resource constraint)
- Each agent gets max 5 retry cycles against test suite
- If a subtask has dependencies on another, run them sequentially — don't parallelize
- Never force-merge — if conflicts arise, report them for user resolution
- Always run the FULL test suite on the combined branch before reporting success
- Use Python 3.13 for all worktree venvs
