---
name: pr
description: Create a pull request with validation, CI awareness, and issue linking
---

# PR Creation

Creates a pull request with validation, CI awareness, and issue linking.

## Input

Accepts an optional PR title. If not provided, derives from branch name and commit history.

Flags:
- `--draft` — create as a draft PR (bots skip drafts, use `/draft-pr ready` to convert later)

## Steps

1. **Pre-flight checks**:
   - `git status` — warn if uncommitted changes exist
   - `uv run pytest -x -q` — all tests must pass before PR creation
   - `uv run ruff check src/ tests/` — no lint errors
2. **Analyze changes**:
   - `git log main..HEAD --oneline` — summarize all commits since branching
   - `git diff main...HEAD --stat` — files changed summary
3. **Detect linked issue**: Parse branch name for issue number (e.g., `feat/issue-42` → #42)
4. **Push branch**: `git push -u origin HEAD`
5. **Create PR** with `gh pr create` (add `--draft` if flag was passed):
   - Title: concise, under 70 chars
   - Body format:
     ```
     ## Summary
     <bullet points from commit analysis>

     ## Linked Issue
     Closes #<N>

     ## Test Plan
     - [ ] All existing tests pass
     - [ ] New tests added for changed behavior
     - [ ] Manual verification steps

     Generated with [Claude Code](https://claude.com/claude-code)
     ```
6. **Report**:
   - **Standard PR**: PR URL + reminder to monitor CI checks
   - **Draft PR**: PR URL + note that bots will skip until marked ready. Suggest `/draft-pr ready <N>` when iteration is complete.

## Guardrails

- Never create a PR if tests are failing
- Never force-push unless explicitly asked
- Always link the issue if detectable from branch name
- If no commits exist beyond main, abort and explain
- For full draft PR lifecycle management (create/ready/status), use `/draft-pr`
