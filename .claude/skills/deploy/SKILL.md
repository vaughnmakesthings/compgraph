---
name: deploy
description: Deploy current main branch to the Digital Ocean dev server
---

# Deploy to Dev Server

Deploys the current main branch to the Digital Ocean droplet via `infra/deploy.sh`.

## Input

- No arguments: code-only deploy (git pull + uv sync + restart)
- `--env-update`: also push fresh secrets from local 1Password

## Steps

1. **Pre-flight check**: Verify `origin/main` is up to date:
   ```bash
   git fetch origin
   git log --oneline origin/main -1
   ```

2. **Deploy**:
   ```bash
   bash infra/deploy.sh
   ```
   Or with secrets update:
   ```bash
   bash infra/deploy.sh --env-update
   ```

3. **Verify**: The deploy script runs a health check automatically against `https://dev.compgraph.io/health`.

4. **Report result**:
   - If health check returns 200: "Deployed successfully. Server healthy."
   - If health check fails: "Deploy completed but health check failed. Check logs:"
     ```bash
     ssh compgraph-do "journalctl -u compgraph -n 20 --no-pager"
     ```

5. **Post-deploy (optional)** — Run `/sentry-check` to surface any new unresolved critical issues in Sentry. If Sentry is configured, report findings to user.

## Rollback

If deployment fails, check recent logs and report to user. Do not attempt automatic rollback without user confirmation.

## Dashboard

Dashboard is available at `https://dashboard.dev.compgraph.io` — also restarted during deploy.
