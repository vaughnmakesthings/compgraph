---
name: sprint-plan
description: Analyze issues, build file-overlap matrix, and generate merge-wave plan for parallel development
---

# Sprint Plan

Accepts a list of GitHub issue numbers, analyzes each for file overlap, groups into parallel tracks vs sequential stacks, and outputs a merge-wave execution plan.

## Input

Issue numbers as arguments: `/sprint-plan 42 43 44 45`

If no issues provided, prompt the user for them.

## Phase 1: Issue Analysis

For each issue number:

1. Fetch the issue body:
   ```bash
   gh issue view <N> --json title,body,labels
   ```
2. Extract predicted file paths from:
   - Explicit file references in the issue body
   - Labels (e.g., `area:scraper` maps to `src/compgraph/scrapers/`)
   - Title keywords (e.g., "enrichment" maps to `src/compgraph/enrichment/`)
3. If file paths are ambiguous, use CodeSight or Grep to identify likely files.
4. Build a list per issue: `{ issue_number, title, predicted_files[], estimated_complexity }`

## Phase 2: File Overlap Matrix

Build a matrix showing which issues touch shared files:

```
         #42  #43  #44  #45
models.py  x    x         x
pass1.py   x
router.py       x    x
deps.py              x    x
```

Identify:
- **Independent issues**: no shared files with any other issue
- **Conflicting pairs**: issues that share 1+ files

## Phase 3: Merge Wave Assignment

Group issues into waves. Rules:

1. **Max 3 waves** per sprint
2. Issues within the same wave MUST NOT share files (can merge in any order)
3. Issues that share files go in sequential waves (earlier wave merges first)
4. Minimize total waves (pack independent issues into Wave 1 when possible)

Algorithm:
1. Sort issues by conflict count (most conflicts first)
2. Assign each to the earliest wave where it doesn't conflict with existing wave members
3. If an issue conflicts with issues in multiple waves, assign to the wave after the latest conflict

## Phase 4: Output

Display the plan as a table:

```
## Sprint Plan: 4 issues, 2 waves

### Wave 1 (parallel — merge in any order)
| Issue | Title | Branch | Shared Files | Worktree |
|-------|-------|--------|-------------|----------|
| #42 | Fix enrichment pass1 | fix/issue-42 | None in wave | `git worktree add ../wt-42 -b fix/issue-42` |
| #44 | Add lifecycle endpoint | feat/issue-44 | None in wave | `git worktree add ../wt-44 -b feat/issue-44` |

### Wave 2 (after Wave 1 merged)
| Issue | Title | Branch | Depends On | Worktree |
|-------|-------|--------|-----------|----------|
| #43 | Refactor router | refactor/issue-43 | #42 (models.py), #44 (router.py) | `git worktree add ../wt-43 -b refactor/issue-43` |
| #45 | Auth middleware | feat/issue-45 | #42 (models.py) | `git worktree add ../wt-45 -b feat/issue-45` |

### Execution Commands
Wave 1: `/worktree 42` and `/worktree 44` (parallel agents)
Wave 1 done: `/merge-guardian` each PR, then rebase Wave 2 branches
Wave 2: `/worktree 43` and `/worktree 45` (parallel agents)
```

## Phase 5: Draft PR Recommendations

For each wave:
- **Wave 1 issues**: Create as draft PRs (`/draft-pr create`). Convert to ready one at a time to avoid bot cascade.
- **Wave 2+ issues**: Keep as draft until Wave N-1 is fully merged and branches are rebased on main.

Recommend merge order within each wave if there's a preference (e.g., smaller PRs first to unblock faster).

## Guardrails

- NEVER merge issues from different waves simultaneously
- NEVER skip the rebase step between waves — stale branches cause merge conflicts
- If an issue touches `models.py` + requires migration, it must merge before any issue that also needs migrations (Alembic serial dependency)
- Warn if total estimated complexity exceeds 5 concurrent worktrees (resource constraint)
- If file prediction is uncertain, say so — don't guess silently
