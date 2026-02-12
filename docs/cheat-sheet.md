# CompGraph Developer Cheat Sheet

Quick reference for all commands, skills, and workflows.

---

## Daily Development Lifecycle

```
START → worktree → implement → test → commit → pr → merge → cleanup
```

| Step | Interactive (Claude Code) | Headless (terminal) |
|------|--------------------------|---------------------|
| **Start work** | `/worktree 42` | `./scripts/orchestrator.sh 42` |
| **Plan only** | `/worktree 42` then plan manually | `./scripts/orchestrator.sh 42 plan` |
| **Implement** | Write code with Claude | `./scripts/orchestrator.sh 42 implement` |
| **Test** | `uv run pytest` | `./scripts/orchestrator.sh 42 test` |
| **Commit** | `/commit` | `git commit` |
| **Open PR** | `/pr` | `gh pr create` |
| **Merge** | `/merge-guardian` | `gh pr merge <N> --squash` |
| **Cleanup** | `/cleanup` | `git worktree remove ../compgraph-issue-42` |

---

## Custom Skills (`.claude/skills/`)

| Skill | Command | When to use |
|-------|---------|-------------|
| **Worktree** | `/worktree <issue>` | Starting any new feature or bugfix |
| **PR** | `/pr` | Code is done, tests pass, ready for review |
| **Cleanup** | `/cleanup` | After PR is merged — removes stale worktrees + branches |
| **Merge Guardian** | `/merge-guardian` | PR is open, want to merge safely after CI passes |
| **Parallel Pipeline** | `/parallel-pipeline <issue>` | Large issue with independent subtasks |

## Plugin Skills (pre-installed)

| Skill | Command | When to use |
|-------|---------|-------------|
| **Commit** | `/commit` | Stage and commit with conventional message |
| **Commit + Push + PR** | `/commit-push-pr` | One-shot: commit, push, open PR |
| **Code Review** | `/code-review` | Review a PR (CodeRabbit or project reviewer) |
| **Brainstorm** | `/brainstorming` | Before creative work — explore requirements first |
| **Write Plan** | `/writing-plans` | Design implementation before coding |
| **Execute Plan** | `/executing-plans` | Run a written plan with review checkpoints |

---

## Shell Commands

### Project

```bash
uv sync                                          # Install/update dependencies
uv run compgraph                                 # Run dev server (0.0.0.0:8000)
uv run pytest                                    # Run all tests
uv run pytest -x -q                              # Run tests, stop on first failure
uv run pytest -k "test_name"                     # Run specific test
uv run ruff check src/ tests/                    # Lint check
uv run ruff format src/ tests/                   # Auto-format
```

### Database (requires Supabase connection)

```bash
uv run alembic upgrade head                      # Run all pending migrations
uv run alembic downgrade -1                      # Roll back one migration
uv run alembic revision --autogenerate -m "msg"  # Generate migration from models
uv run alembic history                           # Show migration history
```

### Git Worktrees

```bash
git worktree list                                # Show all worktrees
git worktree add ../compgraph-issue-42 -b feat/issue-42 origin/main
git worktree remove ../compgraph-issue-42        # Remove a worktree
```

### GitHub CLI

```bash
gh issue list                                    # List open issues
gh issue view 42                                 # View issue details
gh issue create -t "title" -b "body" -l scraper  # Create issue
gh pr list                                       # List open PRs
gh pr checks 42                                  # Check CI status on PR
gh pr merge 42 --squash --delete-branch          # Merge PR
```

### Orchestrator (headless)

```bash
./scripts/orchestrator.sh 42                     # Full pipeline (plan→implement→test→review)
./scripts/orchestrator.sh 42 plan                # Planning stage only
./scripts/orchestrator.sh 42 implement           # Implementation only
./scripts/orchestrator.sh 42 test                # Test stage only
./scripts/orchestrator.sh 42 review              # Review stage only
```

---

## GitHub Issue Organization

### Milestones (from `docs/phases.md`)

| Milestone | Phase | What |
|-----------|-------|------|
| M1 | Foundation | Schema, migrations, Supabase setup |
| M2 | Scrapers | 4 ATS adapters (iCIMS, Workday) |
| M3 | Enrichment | 2-pass LLM extraction pipeline |
| M4 | Aggregation | 4 materialized tables |
| M5 | API | FastAPI endpoints for dashboards |
| M6 | Alerts | Change detection + notifications |
| M7 | Hardening | Monitoring, error handling, docs |

### Labels

| Label | Color | Use for |
|-------|-------|---------|
| `scraper` | blue | ATS adapter work |
| `enrichment` | purple | LLM pipeline work |
| `aggregation` | green | Materialized table jobs |
| `api` | orange | FastAPI endpoints |
| `infra` | gray | DB, CI, deployment, config |
| `bug` | red | Defects |
| `research` | yellow | Investigation before implementation |

### Issue Template

```markdown
## Goal
What this achieves in one sentence.

## Context
- Phase: M2
- Context Pack: A (scraper adapter)
- Depends on: #41 (migrations)

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass

## Technical Notes
Relevant design decisions or references.
```

---

## Context Loading (for Claude sessions)

Always load the right context pack before starting work:

| Working on... | Tell Claude |
|---------------|-------------|
| Scraper adapter | "Load Pack A" |
| Enrichment pipeline | "Load Pack B" |
| Aggregation jobs | "Load Pack C" |
| API endpoints | "Load Pack D" |
| Database/migrations | "Load Pack E" |
| Debugging pipeline | "Load Pack F" |
| Pipeline orchestration | "Load Pack G" |
| Alert system | "Load Pack H" |

---

## Quick Decision Tree

```
New feature or bugfix?
  ├─ Small (< 1 hour) → work directly on a branch
  ├─ Medium (1-4 hours) → /worktree <issue>
  ├─ Large, can parallelize → /parallel-pipeline <issue>
  └─ Want full automation → ./scripts/orchestrator.sh <issue>

Ready to submit?
  ├─ Just commit → /commit
  ├─ Commit + PR → /pr
  └─ Commit + PR + merge → /pr then /merge-guardian

Done with a branch?
  └─ /cleanup
```
