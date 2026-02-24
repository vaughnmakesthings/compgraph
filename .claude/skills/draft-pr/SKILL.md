---
name: draft-pr
description: Manage draft PR lifecycle — create drafts, convert to ready, check status
---

# Draft PR

Manages draft PR lifecycle for parallel development. Three modes: create draft PRs (bots skip), convert to ready-for-review (bots trigger), and check status across open PRs.

## Tool Preferences

**Use GitHub MCP tools** for all PR operations:
- `mcp__github__create_pull_request` — create draft PRs (with `draft=true`)
- `mcp__github__update_pull_request` — mark ready (`draft=false`), add labels
- `mcp__github__list_pull_requests` — list open PRs with status
- `mcp__github__pull_request_read` — get PR details, review status

**Use `gh` CLI / git** for:
- Local pre-flight (pytest, ruff, git push)
- `gh pr checks <N>` — CI status polling

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
2. Create draft PR via MCP:
   ```
   mcp__github__create_pull_request(
     owner="vaughnmakesthings",
     repo="compgraph",
     head="<branch_name>",
     base="main",
     title="<title>",
     draft=true,
     body="## Summary\n<bullet points>\n\n## Linked Issue\nCloses #<N>\n\n## Test Plan\n- [ ] All existing tests pass\n- [ ] <specific test items>\n\n> Draft PR — bots will skip until marked ready.\n> Use `/draft-pr ready` when ready for review.\n\nGenerated with [Claude Code](https://claude.com/claude-code)"
   )
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

1. Mark ready via MCP:
   ```
   mcp__github__update_pull_request(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, draft=false)
   ```
2. Add Gemini review label (if desired):
   ```
   mcp__github__update_pull_request(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, labels=["gemini-review"])
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

Query all open PRs via MCP:
```
mcp__github__list_pull_requests(owner="vaughnmakesthings", repo="compgraph", state="open")
```

For each PR, also fetch review status:
```
mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=<N>, method="reviews")
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
