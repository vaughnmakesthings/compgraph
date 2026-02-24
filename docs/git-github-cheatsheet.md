# Git & GitHub Cheat Sheet for Claude Code Development

Tailored to CompGraph's stack: Claude Code agents, worktrees, 6-job CI (~2 min), 4 review bots, auto-deploy CD.

---

## The Core Problem: You're Serialized

Your current workflow is serial — you work on one thing, push, wait for CI (~2 min), wait for 4 review bots (~3-5 min), address feedback, push again, wait again. A single item can eat 30+ minutes of wall clock time where you're blocked.

**The fix is parallelism.** Worktrees let you work on item B while item A is in CI/review. The rest of this doc teaches you when and how.

---

## When to Branch

| Situation | Action |
|-----------|--------|
| Starting any gap analysis item | New branch from `main` |
| Fixing a bug you found mid-sprint | New branch from `main` (don't pollute current branch) |
| Trying an experimental approach | New branch from current branch (rebase onto main if it works) |
| Docs-only change (CLAUDE.md, changelog, plans) | Branch from `main`, but can use `--no-verify` on push |
| One-line config fix | Branch from `main` — still use a PR, never commit directly to `main` |

**Rule: every PR = one concern.** If you're touching auth middleware AND fixing a pay validation bug, those are two branches and two PRs. Smaller PRs merge faster, review cleaner, and are easier to revert.

---

## Branch Naming

```
{type}/{gap-id}-{short-slug}
```

| Type | When |
|------|------|
| `fix/` | Gap analysis items, bug fixes |
| `feat/` | New features, new pages, new endpoints |
| `chore/` | Docs, config, dependency updates, cleanup |
| `refactor/` | Code restructuring with no behavior change |

Examples:
```
fix/SEC-01-supabase-auth-middleware
fix/LLM-01-pay-bounds
feat/eval-tool-phase1-runner
chore/update-phases-md-m7
refactor/ARCH-01-service-layer
```

---

## Worktrees vs. Branches: When to Use Which

### Plain Branch (Same Directory)
Use when you're working on **one thing at a time** and don't need to context-switch.

```bash
git checkout -b fix/LLM-01-pay-bounds
# ... work, commit, push, PR ...
git checkout main && git pull
git checkout -b fix/UX-02-confirm-dialogs
```

**Downside:** Switching branches means rebuilding `.venv`, reloading node_modules (if deps changed), and losing any running dev server state.

### Worktree (Parallel Directory)
Use when you want to **work on item B while item A is in CI/review**.

```bash
# Item A: push PR, CI starts running
git push -u origin HEAD
gh pr create ...

# Item B: spin up worktree, start working immediately
/worktree 42   # Claude Code skill — sets up venv, deps, test baseline

# You now have:
# /compgraph/              ← main (or item A's branch)
# /compgraph-issue-42/     ← item B, fully independent
```

**When worktrees pay off:**

| Scenario | Worth it? |
|----------|-----------|
| Sprint with 3+ items to ship this week | ✅ Yes — pipeline them |
| Quick one-file fix (LLM-01 pay bounds) | ❌ No — faster to just branch |
| Frontend + backend changes for same feature | ❌ No — keep in one branch |
| Two unrelated items that can merge independently | ✅ Yes — parallel PRs |
| Investigating a bug while a feature PR is in review | ✅ Yes — don't block yourself |

**Worktree lifecycle:**
```
Create worktree → Work → PR → CI passes → Merge → Cleanup
                                                      ↓
                                             /cleanup skill
```

### The Parallel Sprint Pattern

This is the workflow that eliminates most of your wait time:

```
Morning:
  1. Start item A in main worktree
  2. Finish, push PR ──────────────────── CI running (~2 min)
  3. /worktree for item B                  │
  4. Start item B ────────────────────── Review bots arrive (~5 min)
  5. Check item A reviews                  │
  6. Address feedback on A, push ────── CI re-runs
  7. Continue item B                       │
  8. Item A merges ✅                      │
  9. Finish item B, push PR               │
  10. /worktree for item C...             │
```

Instead of: A(work) → A(wait) → A(fix) → A(wait) → A(merge) → B(work) → ...
You get: A(work) → A+B(parallel) → A(merge)+B(work) → B+C(parallel) → ...

---

## The Commit Checklist

Your `/commit` skill already handles this, but here's the mental model:

### Before Every Commit
```bash
# Python changes
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run mypy src/compgraph/
uv run pytest -x -q --tb=short -m "not integration" --no-cov  # --no-cov is faster

# Frontend changes
cd web && npm run lint && npm run typecheck && npm test && npm run build

# Docs-only changes
# Skip all of the above — your /commit skill detects this automatically
```

### Commit Message Format
```
type(scope): short description

Longer explanation if needed.

Closes #42
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
Scope: `web`, `api`, `enrichment`, `scraping`, `eval`, `infra`, `db`

Good: `fix(enrichment): add Pydantic upper bounds for pay extraction`
Bad: `update schemas` / `fix stuff` / `WIP`

### When to Commit

| Pattern | Frequency |
|---------|-----------|
| Working on a feature | Commit at each logical checkpoint (model done, route done, tests done) |
| Exploring / prototyping | Don't commit until approach is validated |
| Fixing review feedback | One commit per round of feedback, then squash on merge |
| End of work session | Always commit WIP to your branch (but don't push broken code) |

---

## The Push Decision

| Question | Push? |
|----------|-------|
| Tests pass locally? | ✅ Push |
| Tests fail but you want CI feedback? | ❌ Fix locally first — CI is slower than local |
| Docs-only change? | ✅ Push (can use `--no-verify` to skip pre-push hooks) |
| WIP that compiles but isn't complete? | Push to your branch, but do NOT open a PR yet |
| You're in a worktree and want to "save" progress? | ✅ Push to your branch — it's isolated |

**Never push to `main` directly.** Your CD pipeline auto-deploys on merge to main. A broken push = a broken deploy.

---

## The PR Lifecycle

### Creating a PR

Use the `/pr` skill. It handles preflight, push, and `gh pr create` with issue linking.

**Timing:** Create the PR as soon as the branch is push-ready. Don't wait for "perfect" — the review bots will find issues. Your job is to get CI green and the logic correct.

### What Happens After You Push a PR

```
Push ──→ CI starts (6 parallel jobs, ~2 min)
    ──→ CodeRabbit review (~1-3 min)
    ──→ Cursor Bugbot review (~2-5 min)
    ──→ Cubic AI review (~2-5 min)
    ──→ Copilot review (~1-3 min)
```

**This is your parallelism window.** After pushing, immediately switch to another task.

### Monitoring PR Status

```bash
gh pr checks <number>        # CI job status
gh pr view <number>          # PR details + review status
gh pr status                 # All your open PRs at a glance
```

Or use the `/merge-guardian` skill which checks CI + all 4 bots before merge.

### Addressing Review Feedback

Use `/pr-feedback-cycle` skill. It reads bot comments, triages them (fix / defer to issue / reject with rationale), implements fixes, and pushes.

**Key rule from your CLAUDE.md:** Never leave unactioned review feedback before merge. Every comment gets one of: fix, defer to issue, or explicit rejection.

### Merging

Your CLAUDE.md says: **NEVER merge without explicit user approval.**

Merge checklist:
- [ ] All CI checks green (`gh pr checks <number>`)
- [ ] All 4 review bots have responded
- [ ] No unactioned feedback
- [ ] You've reviewed the diff for critical/high severity items
- [ ] Squash merge (keeps main history clean)

```bash
gh pr merge <number> --squash --delete-branch
```

After merge:
```bash
git checkout main && git pull origin main
# Rebase any open feature branches:
git checkout fix/next-item && git rebase main
```

---

## Reducing CI Wait Time

Your CI runs 6 jobs in parallel. The bottleneck is the **slowest job** (~2 min for pytest or frontend build). Here's how to minimize round-trips:

### 1. Catch Everything Locally First

Every CI failure you catch locally saves a 2-minute round-trip plus bot re-review time.

```bash
# The "local CI" command — run this before every push
uv run ruff check src/ tests/ --fix && \
uv run ruff format src/ tests/ && \
uv run mypy src/compgraph/ && \
uv run pytest -x -q --tb=short -m "not integration" --no-cov
```

Your `/commit` skill does this, but if you're pushing without `/commit`, run it manually.

For frontend:
```bash
cd web && npm run lint && npm run typecheck && npm test && npm run build
```

### 2. Use `--no-cov` Locally

Coverage collection adds ~15-30% to pytest runtime. CI collects coverage — you don't need to locally. Always use `--no-cov` for local test runs unless you're specifically checking coverage.

### 3. Run Only Affected Tests During Development

While iterating on a specific module, run targeted tests:
```bash
uv run pytest tests/test_enrichment.py -x -q --no-cov          # Single file
uv run pytest -k "test_pay_validation" -x -q --no-cov          # Single test
uv run pytest tests/test_enrichment.py tests/test_schemas.py    # Multiple files
```

Run the full suite only before committing. This is the biggest time saver — running 703 tests after every file save is wasteful.

### 4. Don't Push Hoping CI Will Catch Issues

Your CLAUDE.md already says this. Reinforcing: a local test run takes ~30s. A CI round-trip takes ~2 min + re-triggering bot reviews. Always validate locally.

### 5. Batch Review Feedback

When review bots leave 5 comments, don't push after fixing each one. Fix all 5, run local checks, push once. One CI run instead of five.

### 6. Draft PRs for Early CI Feedback

If you're unsure whether a change will pass CI (e.g., complex migration, new dependency), use a draft PR:
```bash
gh pr create --draft
```
This runs CI without triggering the full review bot gauntlet. Convert to ready-for-review when CI is green:
```bash
gh pr ready <number>
```

---

## GitHub Issues: Quick Reference

### Creating Issues
```bash
gh issue create --title "[SEC-01] Supabase Auth RBAC" \
  --body "..." \
  --label "severity: critical,security,effort: medium" \
  --milestone "M7 Sprint 1 — Foundation"
```

### Linking PRs to Issues
In PR body: `Closes #42` — auto-closes the issue when PR merges.
In PR body: `Part of #42` — links without auto-closing (for subtasks).

### Querying Issues
```bash
gh issue list --milestone "M7 Sprint 1 — Foundation"  # Sprint scope
gh issue list --label "blocked"                        # What's stuck
gh issue list --label "quick-win"                      # Low-hanging fruit
gh issue list --assignee @me --state open              # Your plate
```

### Moving Issues on the Project Board
```bash
# Via GitHub UI (Projects v2) or:
gh project item-edit --id <item-id> --field-id <field-id> --single-select-option-id <option-id>
# (Project board is easier to manage in the UI for drag-and-drop)
```

---

## Common Scenarios

### "I pushed a PR but CI failed on something I didn't touch"

Likely a flaky test or dependency issue. Check the specific failure:
```bash
gh pr checks <number>        # Which job failed?
gh run view <run-id> --log   # Full log for the failed job
```
If it's not your code, re-run the job:
```bash
gh run rerun <run-id> --failed
```

### "I need to rebase my branch because main moved"

```bash
git fetch origin
git rebase origin/main
# If conflicts: resolve, then git rebase --continue
git push --force-with-lease   # Safe force-push for rebased branches
```

**Use `--force-with-lease`, never `--force`.** It prevents overwriting someone else's push (even though you're solo, it's a good habit).

### "My worktree is stale and tests fail on baseline"

```bash
cd ../compgraph-issue-42
git fetch origin
git rebase origin/main
uv sync                      # Pick up any new deps
uv run pytest -x -q --no-cov # Verify baseline
```

### "I want to abandon a branch and start over"

```bash
# If in a worktree:
cd /Users/vmud/Documents/dev/projects/compgraph   # Back to main
git worktree remove ../compgraph-issue-42
git branch -d fix/issue-42-whatever

# If just a branch:
git checkout main
git branch -d fix/bad-approach       # -d = safe delete (only if merged)
git branch -D fix/bad-approach       # -D = force delete (unmerged, you're sure)
```

### "Review bots disagree with each other"

This happens. Your priority order for resolving conflicts:
1. Your own judgment (you know the codebase best)
2. CodeRabbit (most context-aware)
3. Cursor Bugbot / Cubic (good at catching real bugs)
4. Copilot (most generic, least project-aware)

If a bot suggestion is wrong, reject it with a comment explaining why. Your CLAUDE.md rule: never leave unactioned feedback.

### "I need to cherry-pick a fix from one branch into another"

```bash
git cherry-pick <commit-hash>
```
Use sparingly. If two branches need the same fix, it's usually better to merge the fix to main first, then rebase both branches.

---

## Workflow Cheat Codes (Your Existing Skills)

| What you want | Skill | What it does |
|---------------|-------|-------------|
| Set up isolated workspace for an issue | `/worktree 42` | Worktree + venv + deps + test baseline |
| Lint → test → commit → push | `/commit` | Full pre-commit ceremony |
| Create PR with preflight | `/pr` | Tests → push → gh pr create → issue link |
| Check if PR is safe to merge | `/merge-guardian` | CI + all 4 bots + feedback check |
| Handle review bot feedback | `/pr-feedback-cycle` | Triage → fix → push |
| Clean up merged worktrees | `/cleanup` | Remove worktrees + delete merged branches |
| Run full check suite before deploy | `/pre-release` | Lint + typecheck + test + build |

---

## Daily Rhythm

```
Start of day:
  git checkout main && git pull
  Check: gh pr status              ← any PRs ready to merge?
  Check: gh issue list --label blocked ← anything unblocked?

Working on items:
  Pick item → /worktree (if parallel) or branch (if solo)
  Implement → /commit → /pr
  Switch to next item while CI runs

End of day:
  Merge anything that's green
  /cleanup for merged branches/worktrees
  Update changelog if significant progress
```
