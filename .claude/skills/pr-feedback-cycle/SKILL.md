---
name: pr-feedback-cycle
description: Triage and resolve GitHub bot review comments on a PR — fetch, classify, fix/defer/reject, push, repeat
---

# PR Feedback Cycle

Automates triage and resolution of GitHub bot review comments on a PR. Fetches unresolved bot threads, classifies severity, fixes/defers/rejects each, pushes, waits for CI + bots to re-review, and repeats until clean or max cycles reached.

## Tool Preferences

**Use GitHub MCP tools** for structured data retrieval and writes:
- `mcp__github__pull_request_read` — PR details, reviews, review comments, status
- `mcp__github__issue_write` — create deferred issues
- `mcp__github__add_reply_to_pull_request_comment` — reply to review threads
- `mcp__github__pull_request_review_write` — submit reviews

**Use `gh` CLI** only for:
- `gh pr checks <N>` — CI status polling (MCP has no polling mechanism)
- `gh api graphql` — review thread resolution mutations (not in MCP)
- `gh pr view --json isDraft` — quick draft detection

## Input

Accepts an optional PR number (e.g., `/pr-feedback-cycle 86`). If not provided, detect from current branch:
```bash
gh pr view --json number -q .number
```

## Constants

```
BOT_LOGINS    = gemini-code-assist[bot], cursor[bot], copilot-pull-request-review[bot], cubic-dev-ai[bot]
BOT_API_NAMES = gemini-code-assist, cursor, copilot-pull-request-reviewer, cubic-dev-ai
(Note: GraphQL author.login omits [bot] suffix. Copilot uses "reviewer" not "review".)
(4 bots confirmed active Feb 2026. Copilot is intermittent — may not review every PR.)
MAX_CYCLES    = 5
CI_POLL       = 30s interval, 15 min timeout
```

### Bot Tiers

Bots are split into two tiers based on reliability and timing:

**Tier 1 — Blocking (wait up to 7 min):**
| Bot | Typical Delay | Notes |
|-----|---------------|-------|
| `gemini-code-assist[bot]` | < 1 min | Nearly instant after push |
| `cubic-dev-ai[bot]` | 5-7 min | Consistent |
| `coderabbitai[bot]` | 1-2 min | Reliable, high-quality summaries |

**Tier 2 — Async (non-blocking):**
| Bot | Typical Delay | Notes |
|-----|---------------|-------|
| `cursor[bot]` | 30s - 28 min | Highly variable — good bug detection but unreliable timing |
| `copilot-pull-request-review[bot]` | 1-3 min | Intermittent — may skip PRs entirely |

**Tier 1** bots are waited on before triage. **Tier 2** bots are included if they arrive during the Tier 1 wait, but the cycle does NOT block on them. Late Tier 2 feedback is caught post-merge by the `late-bot-review.yml` workflow, which auto-creates issues for unresolved comments on merged PRs.

**Implication:** Wait for all 3 Tier 1 bots OR 7 minutes (whichever comes first). Tier 2 feedback that arrives during the wait is triaged normally; feedback that arrives after merge is captured as issues.

## Draft Detection

Before entering the core loop, check if the PR is a draft:

```bash
gh pr view $PR_NUMBER --json isDraft -q .isDraft
```

If `true`:
- Display: "PR #$PR_NUMBER is a draft — review bots skip draft PRs."
- Recommend: "Use `/draft-pr ready $PR_NUMBER` to convert to ready-for-review, then re-run `/pr-feedback-cycle`."
- **Exit immediately.** Do not proceed to the core loop.

If `false`: continue to Core Loop.

---

## Core Loop

Track a `TRIAGED_THREAD_IDS` set across cycles to avoid re-processing.

### Step 0 — Wait for bot reviews (tiered)

**This step is mandatory before the first triage cycle.**

1. Poll CI status first:
   ```bash
   gh pr checks $PR_NUMBER
   ```
   Wait until CI passes (30s interval, 15 min timeout). If CI fails, stop and report.

2. Once CI passes, poll for bot reviews via MCP:
   ```
   mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=$PR_NUMBER, method="reviews")
   ```
   Extract reviewer logins from the response.

3. Compare detected bot logins against **Tier 1 bots** (gemini-code-assist, cubic-dev-ai, coderabbitai). Track which have posted.

4. Re-poll every 60 seconds until **all 3 Tier 1 bots** have posted OR **7 minutes** have elapsed since CI passed.

5. Also note any **Tier 2 bots** (cursor, copilot) that arrived during the wait — they'll be triaged too, but were not waited on.

6. Report status:
   ```
   Bot readiness (waited Xm Ys):
   Tier 1 (blocking):
     ✓ gemini-code-assist[bot] — detected
     ✓ cubic-dev-ai[bot] — detected
     ✓ coderabbitai[bot] — detected
   Tier 2 (async):
     ✓ cursor[bot] — detected (arrived during wait)
     ✗ copilot-pull-request-review[bot] — not detected (async — will be caught post-merge if needed)
   Proceeding with available reviews.
   ```

7. Proceed to Step 1 with all available reviews (Tier 1 + any Tier 2 that arrived). Missing Tier 2 bots are NOT an error — late feedback is caught by `late-bot-review.yml`.

**Skip Step 0** on cycle 2+ (re-triage after pushing fixes). For re-triage, use a simpler 2-minute wait after CI passes, since bots only need to re-analyze the diff delta.

### Step 1 — Fetch unresolved bot comments

Use MCP to get review comments:
```
mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=$PR_NUMBER, method="review_comments")
```

This returns structured review comment data. However, review **thread resolution status** (`isResolved`, `isOutdated`) is not available via MCP — use GraphQL for that:

```bash
gh api graphql -f query='
query($owner:String!,$repo:String!,$pr:Int!) {
  repository(owner:$owner,name:$repo) {
    pullRequest(number:$pr) {
      reviewThreads(first:100) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first:5) {
            nodes {
              author { login }
              body
              path
              line
              startLine
              url
            }
          }
        }
      }
    }
  }
}' -f owner=vaughnmakesthings -f repo=compgraph -F pr=$PR_NUMBER
```

Filter to threads that are:
- **Not resolved** (`isResolved: false`)
- **Not outdated** (`isOutdated: false`)
- **Authored by a bot** (first comment author login in `BOT_LOGINS`)
- **Not already triaged** (thread ID not in `TRIAGED_THREAD_IDS`)

If zero threads remain after filtering, skip to Step 7 (final report).

### Step 2 — Parse severity

Each bot uses a different format. Extract severity from the **first comment body** in each thread.

| Bot | High | Medium | Low |
|-----|------|--------|-----|
| `gemini-code-assist` | `![critical]` or `![high]` or `![security` in image alt text (`![alt](url)` format) | `![medium]` | `![low]` |
| `cursor` | `**Critical Severity**` or `**High Severity**` | `**Medium Severity**` | `**Low Severity**` |
| `copilot-pull-request-reviewer` | Body contains `critical` or `bug` keywords prominently | Default (no explicit severity) | `suggestion`, `nitpick`, `nit` keywords |
| `cubic-dev-ai` | Body starts with `P1:` | Body starts with `P2:` | Body starts with `P3:` or `P4:` |

**Gemini format note**: Gemini embeds severity as a markdown image: `![medium](https://www.gstatic.com/codereviewagent/medium-priority.svg)`. Extract the alt text between `![` and `]` — match against `critical`, `high`, `medium`, `low`, `security`. Do NOT search for `medium-priority` in the body text.

If severity cannot be determined, default to **Medium**.

### Step 3 — Triage decision

For each thread, classify as Accept, Defer, or Reject:

**Accept** (will fix now):
- High or security severity
- Bugs, logic errors, type errors, security vulnerabilities
- Missing error handling that could cause runtime failures
- Incorrect API usage or data corruption risks

**Defer** (create issue for later):
- Medium severity + refactoring, style, or performance suggestions
- Low severity + substantive improvement suggestion
- Test coverage improvements, documentation gaps, logging enhancements
- Any suggestion requiring architectural changes

**Reject** (dismiss with reason):
- Low severity style nitpicks that conflict with project conventions in CLAUDE.md
- Broad exception handling warnings in Streamlit code (known intentional pattern)
- Complaints about intentional project patterns: append-only model, `TYPE_CHECKING` imports, `begin_nested()` savepoints
- Outdated threads (code already changed)
- Duplicate of another thread already triaged

**Ambiguous → Defer.** Never silently skip a comment.

### Resolve thread (shared helper)

After **every** triage action (Accept, Defer, Reject), resolve the thread on GitHub via GraphQL (not available in MCP):

```bash
gh api graphql -f query='
mutation($threadId:ID!) {
  resolveReviewThread(input:{threadId:$threadId}) {
    thread { isResolved }
  }
}' -f threadId=$THREAD_ID
```

If resolution fails (permissions), log and continue — do not abort.

### Step 4 — Execute actions

Process in order: **all Accepts first**, then Defers, then Rejects. This ensures deferred issues reference post-fix code state.

#### Accept flow

For each accepted thread:

1. Read the affected file and surrounding context
2. Invoke `superpowers:systematic-debugging` for root cause analysis if the issue is non-trivial
3. Implement the fix
4. Run targeted tests:
   ```bash
   uv run pytest -x -q --no-cov -k "<relevant_test>"
   ```
5. Lint the changed files:
   ```bash
   uv run ruff check --fix <files> && uv run ruff format <files>
   ```
6. Verify `TYPE_CHECKING` imports survived ruff (known pitfall — check after formatting)
7. Stage and commit (one commit per fix, do NOT push yet):
   ```bash
   git add <specific files>
   git commit -m "fix: <description> (from <bot> review)"
   ```
8. Reply to the thread via MCP:
   ```
   mcp__github__add_reply_to_pull_request_comment(owner="vaughnmakesthings", repo="compgraph", pullNumber=$PR_NUMBER, commentId=$COMMENT_ID, body="Fixed in <short_hash> — <description of fix>")
   ```
9. **Resolve the thread** (see shared helper above — GraphQL)
10. Add thread ID to `TRIAGED_THREAD_IDS`

#### Defer flow

For each deferred thread:

1. Determine milestone from the file path:
   | Path prefix | Milestone |
   |-------------|-----------|
   | `src/compgraph/scrapers/` | `M3: Data Collection Period` (#3) |
   | `src/compgraph/enrichment/` | `M2: Enrichment Pipeline` (#2), or `M6: Tuning & Hardening` (#6) if M2 is closed |
   | `src/compgraph/api/` | `M4: Aggregation & API` (#4) |
   | `src/compgraph/dashboard/` | `M5: Prototype UI` (#5), or `M7: Production UI` (#7) if M5 is closed |
   | `alembic/` | `M1: Foundation` (#1) |
   | `tests/` | Match the milestone of the code under test |
   | Default | `M6: Tuning & Hardening` (#6) |

2. Create a GitHub issue via MCP:
   ```
   mcp__github__issue_write(owner="vaughnmakesthings", repo="compgraph", title="Review feedback: <short description>", body="<bot name> flagged <file>:<line> — <original comment summary>", milestone="<milestone name>")
   ```

3. Reply to the PR thread via MCP:
   ```
   mcp__github__add_reply_to_pull_request_comment(owner="vaughnmakesthings", repo="compgraph", pullNumber=$PR_NUMBER, commentId=$COMMENT_ID, body="Tracked as #<issue_number> (deferred to <milestone>)")
   ```

4. **Resolve the thread** (see shared helper above — GraphQL)
5. Add thread ID to `TRIAGED_THREAD_IDS`

#### Reject flow

For each rejected thread:

1. Reply with a 1-2 sentence reason via MCP:
   ```
   mcp__github__add_reply_to_pull_request_comment(owner="vaughnmakesthings", repo="compgraph", pullNumber=$PR_NUMBER, commentId=$COMMENT_ID, body="<rejection reason>")
   ```

2. **Resolve the thread** (see shared helper above — GraphQL)
3. Add thread ID to `TRIAGED_THREAD_IDS`

### Step 5 — Push and wait

Only execute this step if any Accepts were made (commits exist to push).

1. Run full test suite before pushing:
   ```bash
   uv run pytest -x -q --no-cov
   ```
   If tests fail, fix failures before pushing. Each fix attempt counts toward `MAX_CYCLES`.

2. Push:
   ```bash
   git push origin HEAD
   ```

3. Poll CI (CLI — MCP has no polling):
   ```bash
   gh pr checks $PR_NUMBER
   ```
   Every 30 seconds, timeout at 15 minutes. Report progress: "Waiting for CI... (3/5 checks complete)".

4. If CI fails, **stop the cycle and report**. Do not attempt to fix CI failures automatically — report what failed and exit.

5. **Wait for bots to re-analyze** after CI passes. Poll reviews via MCP:
   ```
   mcp__github__pull_request_read(owner="vaughnmakesthings", repo="compgraph", pullNumber=$PR_NUMBER, method="reviews")
   ```
   Check every 60 seconds for 3 minutes for new bot reviews posted after the push timestamp.

### Step 6 — Cycle detection

1. Re-fetch unresolved bot comments (same GraphQL query as Step 1)
2. Filter against `TRIAGED_THREAD_IDS`
3. If new comments found AND cycles < `MAX_CYCLES` → loop back to Step 2
4. If no new comments → proceed to Step 7
5. If cycles >= `MAX_CYCLES` → proceed to Step 7 with remaining threads listed

### Step 7 — Final report

Print a structured summary:

```
## PR Feedback Cycle Complete

**PR**: #<number> | **Cycles**: <N> | **Status**: <Clean / Remaining>

### Accepted (fixed)
| Thread | File | Fix | Commit |
|--------|------|-----|--------|
| <bot> | <file:line> | <description> | <short hash> |

### Deferred (issues created)
| Thread | File | Issue | Milestone |
|--------|------|-------|-----------|
| <bot> | <file:line> | #<N> | <milestone> |

### Rejected (dismissed)
| Thread | File | Reason |
|--------|------|--------|
| <bot> | <file:line> | <reason> |

### Remaining (if any)
| Thread | File | Severity |
|--------|------|----------|
| <bot> | <file:line> | <severity> |
```

If status is **Clean**, suggest: "Ready for `/merge-guardian` when you're satisfied with the changes."

## Guardrails

- **NEVER merge the PR** — merging is the job of `/merge-guardian`
- **NEVER dismiss** high-severity or security comments — always Accept or Defer
- **NEVER push** without local tests passing first
- **NEVER auto-fix** alembic migration files — always Defer migration changes
- **Maximum 5 cycles** — hard stop, report remaining threads
- **One commit per fix** — keeps history reviewable and revertable
- **Verify TYPE_CHECKING imports** survive ruff after each edit (known ruff pitfall)
- **Tier 1 bot readiness polling is mandatory** — Step 0 (7 min) on first cycle, 2 min on subsequent cycles. Never skip. Tier 2 bots are non-blocking.
- **If GraphQL fails** (thread resolution, reply), log the error and continue — do not abort the cycle
- **Ambiguous severity → Defer** — never silently skip a comment
