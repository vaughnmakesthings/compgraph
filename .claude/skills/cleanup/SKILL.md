---
name: cleanup
description: Clean up merged branches and their associated worktrees
---

# Branch & Worktree Cleanup

Cleans up merged branches and their associated worktrees.

## Steps

1. **Fetch latest**: `git fetch origin --prune`
2. **Identify merged worktrees**:
   ```bash
   git worktree list
   ```
   For each worktree (excluding the main working directory):
   - Check if its branch has been merged to main: `git branch --merged main | grep <branch>`
   - Check if a PR exists and is merged: `gh pr list --head <branch> --state merged`
3. **Present cleanup plan** to the user:
   - Table showing: worktree path, branch name, merged status, PR status
   - Clearly mark which will be removed
   - **Ask for confirmation before proceeding**
4. **Execute cleanup** (only after user confirms):
   ```bash
   git worktree remove <path>
   git branch -d <branch>
   ```
5. **Clean gone branches** (remote-deleted but still local):
   ```bash
   git branch -v | grep '\[gone\]' | awk '{print $1}'
   ```
   Delete each with `git branch -d <branch>`
6. **Report**:
   - Worktrees removed
   - Branches deleted
   - Any branches that couldn't be deleted (not fully merged) — list for manual review

## Guardrails

- NEVER delete the main worktree or main branch
- NEVER use `git branch -D` (force delete) — only `-d` (safe delete)
- NEVER delete unmerged branches without explicit user confirmation
- Always show the plan and get confirmation before any destructive action
- If a worktree has uncommitted changes, warn and skip it
