# Deploy to Dev Server

Deploys the current main branch to the Raspberry Pi dev server at 192.168.1.69.

## Input

No arguments required. Deploys whatever is on `origin/main`.

## Steps

1. **Pre-flight check**: Verify we're on `main` or that `origin/main` is up to date:
   ```bash
   git fetch origin
   git log --oneline origin/main -1
   ```

2. **Deploy via SSH**:
   ```bash
   ssh compgraph-dev "cd /opt/compgraph && git pull && source /root/.local/bin/env && uv sync && systemctl restart compgraph"
   ```

3. **Wait for startup** (5 seconds):
   ```bash
   sleep 5
   ```

4. **Health check**:
   ```bash
   curl -sf http://192.168.1.69:8000/health
   ```

5. **Report result**:
   - If health check returns 200: "Deployed successfully. Server healthy."
   - If health check fails: "Deploy completed but health check failed. Check logs:"
     ```bash
     ssh compgraph-dev "journalctl -u compgraph -n 20 --no-pager"
     ```

## Rollback

If deployment fails, check recent logs and report to user. Do not attempt automatic rollback without user confirmation.
