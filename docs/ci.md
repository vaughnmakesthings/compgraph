# CI / CD — GitHub Actions

## Active Workflows

| Workflow | File | Trigger | What it does |
|----------|------|---------|-------------|
| **CI** | `ci.yml` | Push to main, PRs | Path-filtered: Lint & Format (ruff), Type Check (mypy), Test (pytest + coverage), Security Scan (Snyk), Eval Tests, Frontend CI (lint/typecheck/test/build) |
| **Backend CD** | `cd.yml` | CI passes on main (`workflow_run`) | Auto-deploys FastAPI to DO dev server via SSH |
| **Frontend CD** | `cd.yml` | CI passes on main (`workflow_run`) | Auto-deploys Next.js to Vercel via CLI |

### CI (`ci.yml`)

Runs **path-filtered** jobs on every push to `main` and every PR. A `changes` detection job determines which areas of the codebase were modified, and only relevant downstream jobs execute.

**Concurrency:** Pushing a new commit to a PR while CI is still running cancels the in-progress run. No wasted minutes on stale code.

#### Path Filter Groups

| Filter | Paths | Jobs Triggered |
|--------|-------|----------------|
| `backend` | `src/**`, `tests/**`, `pyproject.toml`, `uv.lock`, `alembic/**`, `scripts/**` | Lint, Type Check, Test, Security |
| `frontend` | `web/**` | Frontend CI |
| `eval` | `eval/**` | Eval Python Tests |
| *(none match)* | `docs/**`, `*.md`, config-only | No jobs run |

**Branch protection compatibility:** The three required status checks (Lint & Format, Type Check, Test) always run but exit early with a skip message when no backend changes are detected. This ensures they report a green status to GitHub even on frontend-only or docs-only PRs, preventing merge blocks. Non-required jobs (Security, Eval, Frontend CI) use standard `if:` conditions and skip entirely.

#### Jobs

| Job | Filter | Command | Time |
|-----|--------|---------|------|
| Detect Changes | *(always runs)* | `dorny/paths-filter@v3` | ~5s |
| Lint & Format | `backend` | `ruff check` + `ruff format --check` | ~15s |
| Type Check | `backend` | `mypy src/compgraph/` | ~45s |
| Test | `backend` | `pytest -x -q -m "not integration" --cov` | ~2m |
| Security Scan | `backend` | Snyk severity-threshold=high | ~1m |
| Eval Python Tests | `eval` | `pytest tests/ -q --tb=short` (in `eval/`) | ~30s |
| Frontend CI | `frontend` | `npm run lint && typecheck && test:coverage && build` (in `web/`) | ~2m |

#### CI Time by PR Type

| PR Type | Jobs Run | Approx. Time |
|---------|----------|:------------:|
| Backend-only | 4 (lint, type, test, security) | ~2 min |
| Frontend-only | 1 (frontend-ci) | ~2 min |
| Eval-only | 1 (eval-python-test) | ~30s |
| Docs-only | 0 (changes job only) | ~5s |
| Full-stack | 6 (all) | ~2 min (parallel) |

### Backend CD (`cd.yml`)

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

### Frontend CD (Vercel via CD workflow)

Vercel deploys the Next.js frontend via the CD workflow after CI passes on `main`:

1. CI succeeds on push to `main` → CD workflow triggers
2. `npx vercel deploy --prod` runs in `web/`
3. Built output deployed to Vercel's CDN edge network
4. API calls from the frontend are rewritten: `/api/*` → `https://dev.compgraph.io/api/*` (via `web/vercel.json`)

**Env vars (Vercel dashboard):** `NEXT_PUBLIC_API_URL=https://dev.compgraph.io`
**Secrets (GitHub):** `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

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

5 review systems active on PRs:
- CodeRabbit (auto-review, configurable via `.coderabbit.yaml`)
- Gemini (auto-review on PR open, on-demand via `@gemini-cli /review`)
- Cursor Bugbot
- Cubic AI
- Copilot (GitHub)

**Parallel development tip:** Use draft PRs (`gh pr create --draft`) during active iteration. CodeRabbit skips drafts (`drafts: false` in config). Convert to ready-for-review (`gh pr ready`) only when CI is green and you want bot feedback. This avoids re-triggering all bots on every push.
