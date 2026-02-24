## Gap ID
<!-- e.g., SEC-01, ARCH-02. Use "N/A" for non-gap-analysis work -->

## What Changed
<!-- Brief description of the change -->

## Why
<!-- Link to the gap analysis rationale or business reason -->

## Testing
- [ ] Unit tests pass (`uv run pytest -x -q --tb=short -m "not integration"`)
- [ ] Lint clean (`uv run ruff check src/ tests/ --fix && uv run ruff format src/ tests/`)
- [ ] Type check clean (`uv run mypy src/compgraph/`)
- [ ] Frontend checks (if applicable): lint, typecheck, test, build

## Migration Notes
<!-- List any Alembic migrations, new env vars, or infra changes. "None" if N/A -->

## Screenshots
<!-- For UX changes. Delete section if backend-only -->
