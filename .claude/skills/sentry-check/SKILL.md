# Sentry Check

Check Sentry for unresolved critical issues before or after deploy. Uses Sentry MCP tools.

**Invocation:** Both — run `/sentry-check` to surface production errors.

## When to Use

- **Pre-deploy** — Before merging or deploying, check for unresolved critical bugs
- **Post-deploy** — After deploy, verify no new regressions appeared
- **Debugging** — When investigating production errors reported by users or Vercel logs

## Prerequisites

- Sentry MCP configured and authenticated (OAuth via Cursor Settings → MCP)
- CompGraph app instrumented with Sentry SDK (frontend and/or backend)
- Organization and project slugs known (run `find_organizations` and `find_projects` if unsure)

## Steps

1. **Find org/project** (if not cached):
   - `find_organizations()` → get `organizationSlug`
   - `find_projects(organizationSlug="...")` → get `projectSlugOrId` for CompGraph

2. **Search unresolved critical issues**:
   - `search_issues(organizationSlug="<org>", naturalLanguageQuery="unresolved critical bugs from last 7 days", limit=10)`

3. **Report**:
   - If empty: "No unresolved critical issues in Sentry."
   - If issues found: List each with title, status, link; recommend triage before deploy or investigate post-deploy.

## Integration Points

- **Deploy skill** — After step 4 (Verify), optionally run Sentry check to surface new errors
- **Merge-guardian** — Add to Merge Readiness Checklist: "Sentry: no unresolved critical issues"
- **Pre-release** — Optional step 9: run Sentry check before deploy

## Tool Reference

| Tool | Purpose |
|------|---------|
| `search_issues` | List issues (use naturalLanguageQuery for filters) |
| `search_events` | Count/aggregate events (e.g., "errors in last 24 hours") |
| `get_issue_details` | Full stack trace for a specific issue ID |

## Notes

- Sentry MCP requires OAuth — ensure you're authenticated in Cursor
- If Sentry is not yet instrumented in the app, this skill returns empty results
- Use with Vercel `get_runtime_logs` for full production debugging workflow
