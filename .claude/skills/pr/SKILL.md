---
name: pr
description: Create a pull request with validation, CI awareness, and issue linking
---

# PR Creation

Creates a pull request with validation, CI awareness, and issue linking.

## Tool Preferences

**Use GitHub MCP tools** for PR creation:
- `mcp__github__create_pull_request` — create the PR with structured params

**Use `gh` CLI / git** for:
- Local pre-flight (pytest, ruff, git push)
- Branch detection and commit analysis

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
5. **Create PR** via MCP:
   ```
   mcp__github__create_pull_request(
     owner="vaughnmakesthings",
     repo="compgraph",
     head="<branch_name>",
     base="main",
     title="<concise title, under 70 chars>",
     draft=<true if --draft flag>,
     body="## Summary\n<bullet points from commit analysis>\n\n## Linked Issue\nCloses #<N>\n\n## Test Plan\n- [ ] All existing tests pass\n- [ ] New tests added for changed behavior\n- [ ] Manual verification steps\n\nGenerated with [Claude Code](https://claude.com/claude-code)"
   )
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
