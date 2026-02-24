# Parallel Development Playbook

How to run multiple Claude Code workstreams without the GitHub cascade: merge conflicts → rebase → force-push → re-trigger CI + 5 review bots → repeat.

---

## The Cascade Problem

When you parallelize naively, a single merge to `main` triggers a chain reaction:

```
PR-A merges to main
  → PR-B is now behind main → needs rebase
    → rebase = force-push
      → CI re-runs (~2 min)
      → CodeRabbit re-reviews
      → Gemini re-reviews
      → Cursor Bugbot re-reviews
      → Cubic re-reviews
      → Copilot re-reviews
        → bot comments may differ from first review
          → need to re-triage feedback
            → fix → push → CI + bots again...

Meanwhile PR-C and PR-D are also stale now.
```

With 5 review bots firing on every push, a 3-PR sprint can generate 30+ bot review cycles. Most of that is wasted work.

The solution is three layers: **prevent conflicts**, **reduce re-triggers**, and **cut CI waste**.

---

## Layer 1: Prevent Conflicts (File Overlap Mapping)

Most merge conflicts come from predictable hotspot files. Before starting a sprint, map which items touch which files and group accordingly.

### Sprint 1 Conflict Map

| File / Area | SEC-01 | ARCH-02 | LLM-01 | ARCH-03 | UX-02 |
|-------------|:------:|:-------:|:------:|:-------:|:-----:|
| `models.py` (migration) | ✦ auth_uid | ✦ heartbeat | | | |
| `api/main.py` | | | | ✦ prefix | |
| `api/deps.py` | ✦ auth middleware | | | | |
| `api/routes/*` | ✦ route guards | | | ✦ path changes | |
| `tests/test_api_*` | new auth tests | | | ✦ all /api/ paths | |
| `enrichment/schemas.py` | | | ✦ pay bounds | | |
| `orchestrator.py` | | ✦ state tracking | | | |
| `web/src/app/settings/` | | | | | ✦ dialogs |
| `web/src/lib/api-client.ts` | | | | ✦ base URL | |
| `web/vercel.json` | | | | ✦ rewrite | |

### Reading the Map

Items that share no ✦ rows can be **fully parallel** — different worktrees, simultaneous PRs, merge in any order.

Items that share ✦ rows must be **sequenced** — one merges first, the other branches from updated main. Or use stacked PRs (see below).

### Sprint 1 Parallel Groups

```
Group A (independent — no shared files):
├── LLM-01  (enrichment/schemas.py only)
├── UX-02   (web/src/app/settings/ only)
└── ARCH-02 (orchestrator.py + models.py migration)

Group B (shared API layer — must sequence):
├── ARCH-03 (API prefix — goes FIRST, touches tests broadly)
└── SEC-01  (auth — stacked on ARCH-03, shares routes + tests)
```

### Merge Order

```
Wave 1 (parallel, merge in any order):
  LLM-01 ─────→ merge
  UX-02 ──────→ merge
  ARCH-02 ────→ merge

Wave 2 (sequential):
  ARCH-03 ────→ merge → rebase SEC-01 → SEC-01 merge

Total: 3 parallel tracks, 1 sequential stack = 2 waves instead of 5 serial items
```

**Do this conflict mapping exercise for every sprint.** It takes 10 minutes and prevents hours of rebase pain.

---

## Layer 2: Stacked PRs for Sequential Items

When two items MUST be sequential because they touch the same files, use stacked PRs instead of waiting for the first to merge before starting the second.

### How Stacking Works

```
main ──────────────────────────────────────────→
  \
   └── fix/ARCH-03-api-prefix ────────────────→ PR #1 (base: main)
         \
          └── fix/SEC-01-auth ────────────────→ PR #2 (base: fix/ARCH-03-api-prefix)
```

PR #2 is based on PR #1's branch, not main. This means:
- You can start SEC-01 immediately after ARCH-03 is code-complete — no waiting for merge
- SEC-01's diff only shows its own changes, not ARCH-03's
- When ARCH-03 merges to main, SEC-01 only needs a small rebase

### Creating a Stacked PR

```bash
# Start with the base item
git checkout -b fix/ARCH-03-api-prefix
# ... implement ARCH-03 ...
git push -u origin fix/ARCH-03-api-prefix
gh pr create --title "[ARCH-03] API v1 prefix" --base main

# Stack the dependent item ON TOP of the base branch
git checkout -b fix/SEC-01-auth   # branches from ARCH-03, not main
# ... implement SEC-01 ...
git push -u origin fix/SEC-01-auth
gh pr create --title "[SEC-01] Supabase Auth RBAC" --base fix/ARCH-03-api-prefix
#                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                                                    PR targets the base branch, NOT main
```

### When the Base PR Merges

```bash
# ARCH-03 just merged to main. Update SEC-01:
git checkout fix/SEC-01-auth
git fetch origin

# Retarget PR to main (base branch was deleted on merge)
gh pr edit <SEC-01-PR-number> --base main

# Rebase onto updated main
git rebase origin/main
git push --force-with-lease
```

This rebase is usually clean because SEC-01 was already built on top of ARCH-03's changes.

### Stacking with Worktrees

```bash
# Worktree for the base item
git worktree add ../compgraph-arch03 -b fix/ARCH-03-api-prefix origin/main

# Worktree for the stacked item (based on the base branch)
git worktree add ../compgraph-sec01 -b fix/SEC-01-auth fix/ARCH-03-api-prefix
```

Now you can work on both in parallel directories. SEC-01's worktree has ARCH-03's changes as its starting point.

---

## Layer 3: Stop the Review Bot Storm

You have **5 review systems**: CodeRabbit, Gemini, Cursor Bugbot, Cubic, and Copilot. Every push triggers most of them. A rebase = force-push = a fresh wave of reviews.

### Fix 1: Use Draft PRs During Active Development

Draft PRs run CI but **skip most review bots**.

Your CodeRabbit config already has `drafts: false` — it won't review draft PRs. Gemini only triggers on `pull_request.opened`, not on subsequent pushes to drafts.

**Workflow:**
```bash
# Create as draft — gets CI feedback, no bot storm
gh pr create --draft --title "[ARCH-03] API v1 prefix"

# Iterate: push fixes, only CI runs, bots stay quiet
git push

# When ready for review: convert to ready
gh pr ready <number>
# NOW bots trigger — but only once
```

This alone can cut your bot review cycles by 60-70%.

### Fix 2: Configure CodeRabbit to Ignore Rebases

Add to your `.coderabbit.yaml`:

```yaml
reviews:
  auto_review:
    enabled: true
    drafts: false
    base_branches:
      - main
    ignore_title_keywords:
      - "WIP"
      - "DO NOT MERGE"
  path_filters:
    - "!docs/**"
    - "!*.md"
```

For pure rebases where you just want bots to stay quiet, comment on the PR:

```
@coderabbitai pause
```

Then when ready for final review:
```
@coderabbitai resume
@coderabbitai full review
```

### Fix 3: Reduce the Bot Count

Five review bots is excessive — especially when they contradict each other and you spend time arbitrating between them.

| Bot | Strength | Recommendation |
|-----|----------|----------------|
| CodeRabbit | Deep context, project-aware, configurable | ✅ Keep — best signal-to-noise |
| Gemini | Full codebase access via MCP, architecture-aware | ✅ Keep — good complement |
| Cursor Bugbot | Bug detection | ⚠️ Consider on-demand only |
| Cubic | General review | ⚠️ Consider on-demand only |
| Copilot | Most generic, least project-aware | ❌ Likely disable auto-review |

**You don't have to uninstall anything.** Disable auto-review and trigger manually when needed:

- **Copilot:** Repo Settings → Copilot → Code Review → disable auto-review
- **Cursor/Cubic:** Check their GitHub App settings for auto-review toggles
- **Gemini:** Already only triggers on `pull_request.opened`. To make it fully on-demand, change the dispatch trigger:

```yaml
# In gemini-dispatch.yml — change pull_request trigger to only fire on label:
on:
  pull_request:
    types:
      - 'labeled'    # instead of 'opened' — only reviews when you add a label
```

Then trigger Gemini manually by commenting `@gemini-cli /review` when you want it.

**Target state: 2 auto-reviewers (CodeRabbit + Gemini), rest on-demand.** This cuts your review wait from 5 parallel bot responses to 2, and eliminates cross-bot contradiction triage.

### Fix 4: Agent Reviews for Iteration, Bot Reviews for Final

During active development, use your Claude Code `code-reviewer` agent instead of pushing and waiting for bots:

```
Run the code-reviewer agent on the current branch changes.
Focus on: async patterns, append-only rules, plan alignment.
```

The agent runs locally, gives instant feedback, and doesn't pollute the PR with comment noise. Save bot reviews for the final pass before merge.

---

## Layer 4: Cut CI Waste with Path Filters

Your CI runs **all 6 jobs on every PR** regardless of what changed. A frontend-only PR runs pytest. A docs-only PR runs everything.

### Add Change Detection to ci.yml

Add a `changes` job that other jobs depend on:

```yaml
jobs:
  changes:
    name: Detect Changes
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      eval: ${{ steps.filter.outputs.eval }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'src/**'
              - 'tests/**'
              - 'pyproject.toml'
              - 'uv.lock'
              - 'alembic/**'
            frontend:
              - 'web/**'
            eval:
              - 'eval/**'
```

Then gate each job:

```yaml
  lint:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    # ... existing steps ...

  typecheck:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    # ... existing steps ...

  test:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    # ... existing steps ...

  security:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    # ... existing steps ...

  eval-python-test:
    needs: changes
    if: needs.changes.outputs.eval == 'true'
    # ... existing steps ...

  frontend-ci:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    # ... existing steps ...
```

### Impact

| PR Type | Before | After | Time Saved |
|---------|:------:|:-----:|:----------:|
| Backend-only | 6 jobs | 4 jobs | ~2 min |
| Frontend-only (UX-02) | 6 jobs | 1 job | ~3 min |
| Eval-only | 6 jobs | 1 job | ~3.5 min |
| Docs-only | 6 jobs | 0 jobs | ~4 min |
| Full-stack (SEC-01) | 6 jobs | 5-6 jobs | ~0 |

### Add CI Concurrency Cancellation

When you push commit B while commit A's CI is still running on the same PR, cancel A:

```yaml
# Add at the workflow level in ci.yml:
concurrency:
  group: ci-${{ github.event.pull_request.number || github.sha }}
  cancel-in-progress: true
```

You already have this on your CD workflow. Extend it to CI to stop testing stale code.

---

## Putting It All Together: The Parallel Sprint Routine

### Sprint Start (10 min)

1. Build the file overlap map for this sprint's items
2. Group into parallel tracks and sequential stacks
3. Define the merge wave order

### Daily Execution

```
Wave 1 — Parallel items (no shared files):

  Worktree A: LLM-01 ──→ /commit ──→ gh pr create --draft
  Worktree B: UX-02  ──→ /commit ──→ gh pr create --draft
  Worktree C: ARCH-02 ─→ /commit ──→ gh pr create --draft
                                      ↓
                              CI runs on all 3 (path-filtered)
                              Bots stay quiet (draft)
                                      ↓
                          Run code-reviewer agent locally on each
                          Fix issues, push
                                      ↓
                          gh pr ready on each → bots review once
                          Merge all (order doesn't matter)
                          /cleanup

Wave 2 — Sequential stack:

  git checkout main && git pull

  Worktree D: ARCH-03 ──→ /commit ──→ gh pr create --draft
  Worktree E: SEC-01 (stacked on ARCH-03) ──→ start work immediately
                                      ↓
                          ARCH-03: gh pr ready → review → merge
                                      ↓
                          SEC-01: retarget to main, rebase, gh pr ready → review → merge
                          /cleanup
```

### The Math

**Before (serial + 5 bots on every push):**
- 5 items × ~3 pushes × 5 bot reviews = **75 bot review cycles**
- 5 items × ~3 CI runs (all 6 jobs) = **15 full CI runs** (~30 min)
- Wall clock: **2-3 days of idle wait time** across the sprint

**After (parallel waves + draft PRs + path filters + 2 bots):**
- 5 items × 1 bot review each × 2 bots = **10 bot review cycles**
- 5 items × 1-2 CI runs (path-filtered) = **7-10 partial CI runs** (~10 min)
- Wall clock: **hours of wait time**, mostly overlapped with active work

---

## Quick Reference

| What | Command |
|------|---------|
| Create draft PR | `gh pr create --draft` |
| Convert to ready for review | `gh pr ready <number>` |
| Create stacked PR | `gh pr create --base <parent-branch>` |
| Retarget PR after parent merges | `gh pr edit <number> --base main` |
| Safe force-push after rebase | `git push --force-with-lease` |
| Pause CodeRabbit | Comment `@coderabbitai pause` on PR |
| Resume CodeRabbit | Comment `@coderabbitai full review` on PR |
| Trigger Gemini manually | Comment `@gemini-cli /review` on PR |
| Check all PR statuses | `gh pr status` |
| Rebase onto updated main | `git fetch origin && git rebase origin/main` |
