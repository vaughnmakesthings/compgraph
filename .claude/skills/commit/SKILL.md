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
   First, check if only non-code files changed (docs, config, markdown):
   ```bash
   git diff --name-only HEAD  # unstaged
   git diff --name-only --cached  # staged
   ```
   If ALL changed files match `\.(md|txt|rst|yaml|yml|json|toml)$`, skip tests:
   > "Docs-only changes, skipping tests."

   Otherwise, run tests:
   ```bash
   uv run pytest --no-cov -q --tb=short
   ```
   If tests fail, stop and report failures. Do not commit broken code.

3. **Doc-sync check** — only if `docs/references/` or `.claude/skills/` files appear in the diff:
   - If a **new file** was added to `docs/references/`: check `docs/context-packs.md` Tier 2 "External Research" table. If the file is not listed, warn: "New reference doc not indexed in context-packs.md — add a row before committing."
   - If a **new skill directory** was added to `.claude/skills/`: check `CLAUDE.md` Skills section and `docs/cheat-sheet.md` Custom Skills table. If missing from either, warn: "New skill not listed in CLAUDE.md or cheat-sheet.md — add entries before committing."
   - These are warnings, not blockers. Note them in the diff summary so the user can decide.

4. **Diff review** — understand what's being committed:
   ```bash
   git status
   git diff --stat
   git diff
   ```
   Summarize changes in 2-3 bullet points for the user.

5. **Stage and commit**:
   - Stage relevant files by name (not `git add -A` — avoid secrets/binaries)
   - Generate a conventional commit message from the diff:
     - Format: `type: short description` (feat/fix/docs/refactor/test/chore)
     - Include body if changes span multiple concerns
   - Show proposed message to user for confirmation
   - Commit with the confirmed message

6. **Push** (unless `--no-push`):
   ```bash
   git push origin HEAD
   ```
   If on a feature branch with no upstream, use `git push -u origin HEAD`.

## Cross-Repo Detection

When working in `compgraph-eval` (detected by `web/package.json` existing at repo root):

**Step 1 (lint)** — add frontend checks for staged `web/**/*.{ts,tsx}` files:
```bash
cd web && npm run lint && npm run typecheck
```

**Step 2 (test)** — add frontend tests for staged `web/**/*.{ts,tsx}` files:
```bash
cd web && npm test
```

Steps 1-2 from the main section (ruff, pytest) only run when Python files are staged — skip them for frontend-only changes.

## Rules

- Never commit `.env`, credentials, or binary files
- Never use `--no-verify` unless the user explicitly requested it
- If ruff or pytest fail, fix the issues first — do not skip
- If eslint, tsc, or vitest fail in compgraph-eval, fix before committing
- Always show the diff summary before committing — no silent commits
