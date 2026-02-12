# CI / GitHub Actions

> CI is not yet configured. This document tracks the planned pipeline.

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `ci.yml` | Push to main, PRs | ruff lint + format, pytest (skips if no `.py` changes) |
| `security.yml` | Push to main, PRs, weekly | Bandit security scan + pip-audit dependency check |

### Planned Additions

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `claude-code-review.yml` | PRs | AI code review via Claude Code Action |
| `post-merge.yml` | Push to main | Full test suite + security scan, auto-creates issue on failure |

### Local Pre-Commit (via hooks)

PostToolUse hooks handle:
- `ruff format` on every Python file edit
- `pytest` on every Python file edit (informational, 15s timeout)
