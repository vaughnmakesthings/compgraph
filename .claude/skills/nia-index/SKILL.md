---
name: nia-index
description: Manage Nia's indexed knowledge base for CompGraph — check status, add sources, refresh, and audit coverage
---

# /nia-index

Manage Nia's indexed knowledge base. Ensures agents always have current, complete documentation context.

## Commands

### `/nia-index status`
List all indexed repos/docs and check freshness.

1. `list_repositories()` — get all indexed sources
2. For each source, `check_repository_status(name="<source>")` — check indexing state
3. Report in table format:

```
| Source | Type | Status | Last Indexed |
|--------|------|--------|--------------|
| fastapi | docs | ready | 2026-02-20 |
| apscheduler | repo | indexing | in progress |
```

4. Flag any sources that are >30 days stale or in error state.

### `/nia-index add <url-or-package>`
Index a new source.

1. Determine type:
   - GitHub URL → `index_repository(url="<url>")`
   - Documentation URL → `index_documentation(url="<url>")`
   - Package name → inform user that PyPI/NPM packages are pre-indexed (3K+) and searchable via `nia_package_search_hybrid` without manual indexing
2. Run the appropriate index command
3. Verify with `check_repository_status(name="<source>")`
4. Update `docs/references/nia-indexing-plan.md` with the new source

### `/nia-index refresh`
Re-index all sources from the indexing plan.

1. Read `docs/references/nia-indexing-plan.md` for the full source list
2. `list_repositories()` to see current state
3. Re-index any sources that are stale (>30 days) or missing
4. Report what was refreshed

### `/nia-index audit`
Compare what SHOULD be indexed vs what IS indexed.

1. Read `pyproject.toml` dependencies and `web/package.json` dependencies
2. Read `docs/references/nia-indexing-plan.md` for planned sources
3. `list_repositories()` for actual indexed sources
4. Report gaps:

```
## Nia Index Audit

### Indexed ✓
- fastapi docs, sqlalchemy docs, ...

### Missing (should be indexed)
- tremor docs — used in web/ but not indexed
- ...

### New dependencies (not in plan)
- <any new deps added since last audit>

### Recommended actions
- [ ] index_documentation(url="...")
- [ ] index_repository(url="...")
```

5. Update `docs/references/nia-indexing-plan.md` if gaps found

## Budget Awareness

- Pro tier: 50 indexing jobs/month
- Each `index_documentation` or `index_repository` call = 1 job
- Always report remaining budget after operations: "Used X of 50 monthly indexing jobs"
- Prefer re-indexing stale sources over adding new marginal ones

## Rules

- Always verify indexing completed before declaring success
- Update `docs/references/nia-indexing-plan.md` after any changes
- Don't index sources that are already available via pre-indexed packages (3K+ PyPI/NPM)
- Commit indexing plan changes: `git add docs/references/nia-indexing-plan.md && git commit -m "docs: update nia indexing plan"`
