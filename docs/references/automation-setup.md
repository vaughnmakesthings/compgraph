# Claude Code & Cursor Automation Setup

Reference for MCP servers, hooks, skills, and agents added per automation recommender.

## MCP Servers (`.mcp.json`)

| Server | Purpose | Config |
|--------|---------|--------|
| **Playwright** | Browser automation, E2E test generation | `npx -y @playwright/mcp@latest` (stdio) |
| **Sentry** | Production error investigation | `https://mcp.sentry.dev/mcp` (HTTP/SSE) |

### Workflow Integration

- **Sentry:** `/sentry-check` skill; post-deploy step in deploy skill; merge-guardian checklist
- **Playwright:** `scripts/playwright-smoke.sh` and `npm run test:smoke` in web/; optional pre-release step 9; agents (react-frontend-developer, nextjs-deploy-ops) have Sentry + Playwright tools

### Sentry Setup (Cursor)

Sentry MCP uses OAuth. In Cursor:

1. **Settings → MCP** (or **Features → MCP**)
2. Add server: **Sentry**
3. Complete OAuth flow when prompted

For Claude Code: `claude mcp add --transport http sentry https://mcp.sentry.dev/mcp`

### Playwright Setup

Requires Node.js 18+. First run will install `@playwright/mcp`. No auth needed.

## Hooks (`.claude/settings.json`)

| Hook | Trigger | Action |
|------|---------|--------|
| **Frontend post-edit** | Edit/Write on `web/**/*.{ts,tsx}` | ESLint + related Vitest tests |

Script: `.claude/hooks/frontend-post-edit.sh`

Maps edited files to test files:
- `src/app/*/page.tsx` → `src/test/pages.test.tsx`
- `src/lib/api-client.ts` → `src/test/api-client.test.ts`
- `src/components/*` → `src/test/components.test.tsx`

## Skills (`.claude/skills/`)

| Skill | Invocation | Purpose |
|-------|------------|---------|
| **pre-release** | `/pre-release` | Full verification before deploy/merge |
| **gen-test** | `/gen-test <path>` | Generate Vitest tests for frontend |
| **sentry-check** | `/sentry-check` | Check Sentry for unresolved critical issues |

## Agents (`.claude/agents/`)

| Agent | Purpose |
|-------|---------|
| **security-reviewer** | Auth, RLS, input validation, injection risks |

Invoke before merging auth-related PRs (M4d) or when modifying RLS policies.
