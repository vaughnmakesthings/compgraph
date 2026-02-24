# Pre-Release (Ship-Check)

Run full verification before deploy or merge — lint, typecheck, test (backend + frontend), build. Fails fast with clear output.

**Invocation:** User-only — run `/pre-release` before pushing, merging, or deploying.

## When to Use

- Before pushing a branch with code changes
- Before merging a PR (supplement to CI)
- Before manual deploy to dev/production
- After major refactors to confirm nothing is broken

## What It Runs

Runs in order; stops on first failure:

1. **Backend lint** — `uv run ruff check src/ tests/`
2. **Backend format check** — `uv run ruff format --check src/ tests/`
3. **Backend typecheck** — `uv run mypy src/compgraph/`
4. **Backend tests** — `uv run pytest -x -q -m "not integration" --tb=short`
5. **Frontend lint** — `cd web && npm run lint`
6. **Frontend typecheck** — `cd web && npm run typecheck`
7. **Frontend tests** — `cd web && npm test`
8. **Frontend build** — `cd web && npm run build`
9. **Playwright smoke** (optional) — `bash scripts/playwright-smoke.sh` — hits backend health + frontend; requires `npm install` in web/ first if @playwright/test not yet installed

## Usage

```
/pre-release
```

Or from terminal:

```bash
# Backend
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/compgraph/ && uv run pytest -x -q -m "not integration" --tb=short

# Frontend
cd web && npm run lint && npm run typecheck && npm test && npm run build
```

## Exit Codes

- `0` — All checks passed
- Non-zero — First failing step; fix and re-run

## Notes

- Integration tests (`-m integration`) are skipped — they require live DB
- Coverage thresholds are enforced by `npm test` and `pytest --cov` in CI
- For docs-only changes, backend/frontend steps may be skipped manually
