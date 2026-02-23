# CI / CD — GitHub Actions

## Active Workflows

| Workflow | File | Trigger | What it does |
|----------|------|---------|-------------|
| **CI** | `ci.yml` | Push to main, PRs | Lint & Format (ruff), Type Check (mypy), Test (pytest + coverage), Security Scan (Snyk) |
| **CD** | `cd.yml` | CI passes on main (`workflow_run`) | Auto-deploys to DO dev server via SSH |

### CI (`ci.yml`)

Runs 4 parallel jobs on every push to `main` and every PR:

| Job | Command | Time |
|-----|---------|------|
| Lint & Format | `ruff check` + `ruff format --check` | ~15s |
| Type Check | `mypy src/compgraph/` | ~45s |
| Test | `pytest -x -q -m "not integration" --cov` | ~2m |
| Security Scan | Snyk severity-threshold=high | ~1m |

### CD (`cd.yml`)

Triggers automatically via `workflow_run` after CI succeeds on `main`:

1. Configures SSH with `DEPLOY_SSH_KEY` + `DEPLOY_SSH_KNOWN_HOSTS` secrets
2. SSHs to `165.232.128.28` (DO dev server)
3. Runs `infra/deploy-ci.sh` on the droplet:
   - `git pull origin main`
   - `uv sync` (dependency update)
   - `alembic upgrade head` (auto-migration via pooler URL)
   - `systemctl restart compgraph`
   - Health check with 6 retries (30s total)

**Concurrency control:** Only one deploy runs at a time. New merges cancel in-progress deploys.

**Secrets required:**
- `DEPLOY_SSH_KEY` — ED25519 private key for `root@165.232.128.28`
- `DEPLOY_SSH_KNOWN_HOSTS` — Server host key fingerprint

## Local Pre-Commit (via hooks)

Git hooks installed via `bash scripts/setup-hooks.sh`:

| Hook | What it runs |
|------|-------------|
| pre-commit | `ruff check --fix`, `ruff format`, `mypy` on staged Python files |
| pre-push | Full `pytest` suite (skipped for docs-only changes) |

PostToolUse hooks (Claude Code):
- `ruff format` on every Python file edit
- `pytest` on every Python file edit (informational, 15s timeout)

## Review Bots

4 review bots active on PRs — wait for all before merging:
- CodeRabbit
- Cursor Bugbot
- Cubic AI
- Copilot (GitHub)
