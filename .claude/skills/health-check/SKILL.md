---
name: health-check
description: Comprehensive production health check across all CompGraph services — API, database, enrichment, Vercel deployments, and Sentry errors
---

# Production Health Check

Runs a full diagnostic sweep across all CompGraph production services and produces a summary report. Combines checks that would otherwise require running `/enrich-status`, `/sentry-check`, and manual curl commands separately.

## Input

- No arguments: full health check (all services)
- `--quick`: API + DB connectivity only (skip Sentry and enrichment detail)

## Steps

### 1. API Health (Backend — Digital Ocean)

```bash
curl -sf -w "\nHTTP %{http_code} in %{time_total}s" https://dev.compgraph.io/health
```

- ✅ HTTP 200 + response body → record latency
- ❌ Non-200 or timeout → check service status:
  ```bash
  ssh compgraph-do "systemctl status compgraph --no-pager"
  ```
  If service is down, report and suggest `/deploy`. Stop further checks that depend on the API.

### 2. Frontend Health (Vercel)

Use Vercel MCP tools:

1. `list_deployments(projectId="prj_8IH6w1sFBAbXQhkmr1paJE3Nfrpr", teamId="team_rjCtHfOfITLEggddrnr4bhsI", limit=1)` → get latest deployment
2. Report: deployment state (READY/ERROR/BUILDING), commit SHA, timestamp
3. If state is ERROR → `get_deployment_build_logs` for the failed deployment and report the error

Also check the production URL responds:
```bash
curl -sf -o /dev/null -w "HTTP %{http_code} in %{time_total}s" https://compgraph.app/
```

### 3. Database Connectivity (Supabase)

Use Supabase MCP:

```sql
-- via execute_sql
SELECT
  now() AS server_time,
  count(*) AS table_count
FROM information_schema.tables
WHERE table_schema = 'public';
```

- ✅ Returns result → DB reachable
- ❌ Timeout or error → report connection failure

### 4. Enrichment Pipeline Status

Use Supabase MCP:

```sql
-- via execute_sql
SELECT
  (SELECT count(*) FROM postings WHERE is_active = true) AS active_postings,
  (SELECT count(*) FROM posting_enrichments WHERE pass_number = 1 AND created_at > now() - interval '24 hours') AS pass1_last_24h,
  (SELECT count(*) FROM posting_enrichments WHERE pass_number = 2 AND created_at > now() - interval '24 hours') AS pass2_last_24h,
  (SELECT system_state FROM pipeline_runs ORDER BY started_at DESC LIMIT 1) AS latest_pipeline_state,
  (SELECT started_at FROM pipeline_runs ORDER BY started_at DESC LIMIT 1) AS latest_pipeline_started
```

Also check via API if available:
```bash
curl -sf https://dev.compgraph.io/api/enrich/status
```

Report: active postings, enrichment throughput (last 24h), pipeline state, any errors.

### 5. Sentry — Unresolved Errors

Use Sentry MCP:

1. `find_organizations()` → get org slug (cache after first call)
2. `find_projects(organizationSlug="...")` → get project slug
3. `search_issues(organizationSlug="<org>", naturalLanguageQuery="unresolved issues from last 24 hours", limit=5)`
4. `search_events(organizationSlug="<org>", projectSlugOrId="<project>", naturalLanguageQuery="error count last 24 hours")`

Report: count of unresolved issues, top 3 by frequency, error trend (up/down/stable).

### 6. Vercel Runtime Errors (last 4h)

Use Vercel MCP:

1. `get_runtime_logs(projectId="prj_8IH6w1sFBAbXQhkmr1paJE3Nfrpr", teamId="team_rjCtHfOfITLEggddrnr4bhsI", level="error")` → recent production errors

Report: count of runtime errors, top error messages if any.

---

## Output Format

Present results as a status dashboard:

```
## CompGraph Health Report — [timestamp]

| Service            | Status | Details                          |
|--------------------|--------|----------------------------------|
| API (DO)           | ✅/❌  | 200 OK, 145ms                    |
| Frontend (Vercel)  | ✅/❌  | READY, deployed 2h ago (abc123)  |
| Database (Supabase)| ✅/❌  | Connected, 25 tables             |
| Enrichment         | ✅/⚠️/❌ | 1,204 pass1 / 892 pass2 (24h) |
| Sentry             | ✅/⚠️  | 3 unresolved issues              |
| Vercel Runtime     | ✅/⚠️  | 0 errors (last 4h)              |

### Issues Requiring Attention
- [list any ❌ or ⚠️ items with details]

### Recommendations
- [suggested actions if any issues found]
```

Use ✅ for healthy, ⚠️ for degraded (working but with warnings), ❌ for down/failing.

## `--quick` Mode

Only runs Steps 1-3 (API, Frontend, Database). Skip enrichment detail, Sentry, and Vercel runtime logs. Use when you just need a connectivity sanity check.

## When to Use

- **Start of work session** — quick situational awareness
- **Post-deploy** — verify everything came up healthy after `/deploy`
- **Before a demo** — confirm all services are operational
- **Investigating slowness** — check which layer is degraded
- **Morning check-in** — run at start of day to catch overnight issues
