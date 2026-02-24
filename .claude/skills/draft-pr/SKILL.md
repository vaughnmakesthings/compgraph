---
name: draft-pr
description: Manage draft PR lifecycle — create drafts, convert to ready, check status
---

# Draft PR

Manages draft PR lifecycle for parallel development. Three modes: create draft PRs (bots skip), convert to ready-for-review (bots trigger), and check status across open PRs.

## Input

Mode as first argument:
- `/draft-pr create` — create a draft PR from current branch
- `/draft-pr ready [N]` — mark PR #N as ready for review
- `/draft-pr status` — list all open PRs with draft/CI/bot status

If no mode provided, default to `status`.

---

## Mode: `create`

### Pre-flight

1. **Uncommitted changes**: `git status` — warn if dirty
2. **Tests**: `uv run pytest -x -q --no-cov` — must pass
3. **Lint**: `uv run ruff check src/ tests/` — must pass
4. **Branch divergence**: `git log main..HEAD --oneline` — must have commits

### Create

1. Push branch: `git push -u origin HEAD`
2. Create draft PR:
   ```bash
   gh pr create --draft \
     --title "<title>" \
     --body "$(cat <<'EOF'
   ## Summary
   <bullet points>

   ## Linked Issue
   Closes #<N>

   ## Test Plan
   - [ ] All existing tests pass
   - [ ] <specific test items>

   > Draft PR — bots will skip until marked ready.
   > Use `/draft-pr ready` when ready for review.

   Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```
3. Report:
   ```
   Draft PR created: <URL>

   Bot behavior:
   - CodeRabbit: SKIPPED (drafts: false in .coderabbit.yaml)
   - Gemini: SKIPPED (label-gated, no gemini-review label)
   - Cursor/Copilot/Cubic: may still review (not draft-aware)

   Next steps:
   - Continue pushing commits freely (no bot cascade)
   - When ready: `/draft-pr ready <N>`
   ```

---

## Mode: `ready [N]`

### Input

PR number as argument. If not provided, detect from current branch:
```bash
gh pr view --json number -q .number
```

### Pre-flight

1. **Tests**: `uv run pytest -x -q --no-cov` — must pass
2. **Lint**: `uv run ruff check src/ tests/` — must pass
3. **CI status**: `gh pr checks <N>` — must be green or pending (not failed)
4. **Up to date**: `git fetch origin main && git log HEAD..origin/main --oneline` — warn if behind main

### Convert

1. Mark ready: `gh pr ready <N>`
2. Add Gemini review label (if desired):
   ```bash
   gh pr edit <N> --add-label gemini-review
   ```
3. Report:
   ```
   PR #<N> marked ready for review.

   Expected bot timing:
   - CodeRabbit: ~1-2 min
   - Gemini: ~1-2 min (label added)
   - Cursor: 30s - 28 min (variable)
   - Cubic: 5-7 min
   - Copilot: 1-3 min (intermittent)

   Use `/pr-feedback-cycle <N>` to triage bot feedback.
   ```

---

## Mode: `status`

Query all open PRs:
```bash
gh pr list --json number,title,isDraft,headRefName,statusCheckRollup,labels
```

Display as table:

```
## Open PRs

| # | Title | Draft? | Branch | CI | Bots |
|---|-------|--------|--------|----|------|
| 42 | Fix enrichment | Yes | fix/issue-42 | passing | skipped |
| 43 | Add endpoint | No | feat/issue-43 | running | 3/5 reviewed |
| 44 | Auth middleware | Yes | feat/issue-44 | failing | skipped |
```

Bot count = number of distinct bot logins in PR reviews.

---

## Guardrails

- Never create a non-draft PR in this skill — use `/pr` for that
- Never force-push unless explicitly asked
- Never mark ready if tests are failing
- Always warn if the branch is behind main (suggest rebase first)
- For full PR lifecycle (non-draft), use `/pr` instead
