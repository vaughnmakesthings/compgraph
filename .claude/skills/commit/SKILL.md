---
name: commit
description: End-of-task ceremony — lint, test, diff review, commit, push
---

# Commit

Bundles end-of-task ceremony: lint, test, diff review, commit, push. Prevents the pattern of scattered git operations across a session.

## Input

Optional arguments:
- `--no-push` — commit only, skip push to origin
- Message text — used as commit message (otherwise auto-generated from diff)

## Steps

1. **Lint check** — fix before committing:
   ```bash
   uv run ruff check src/ tests/ --fix
   uv run ruff format src/ tests/
   ```

2. **Quick test run** — abort if tests fail:
   ```bash
   uv run pytest --no-cov -q --tb=short
   ```
   If tests fail, stop and report failures. Do not commit broken code.

3. **Diff review** — understand what's being committed:
   ```bash
   git status
   git diff --stat
   git diff
   ```
   Summarize changes in 2-3 bullet points for the user.

4. **Stage and commit**:
   - Stage relevant files by name (not `git add -A` — avoid secrets/binaries)
   - Generate a conventional commit message from the diff:
     - Format: `type: short description` (feat/fix/docs/refactor/test/chore)
     - Include body if changes span multiple concerns
   - Show proposed message to user for confirmation
   - Commit with the confirmed message

5. **Push** (unless `--no-push`):
   ```bash
   git push origin HEAD
   ```
   If on a feature branch with no upstream, use `git push -u origin HEAD`.

## Rules

- Never commit `.env`, credentials, or binary files
- Never use `--no-verify` unless the user explicitly requested it
- If ruff or pytest fail, fix the issues first — do not skip
- Always show the diff summary before committing — no silent commits
