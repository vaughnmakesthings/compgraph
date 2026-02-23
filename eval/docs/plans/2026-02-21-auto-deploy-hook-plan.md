# Auto-Deploy on Merge to Main — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically deploy the CompGraph Eval dashboard to the Raspberry Pi whenever code is merged to main, using GitHub Actions + Tailscale SSH.

**Architecture:** GitHub Actions workflow triggers on push to main, joins the Tailscale network via ephemeral auth key, SSHs to the Pi, and runs the deploy steps (pull, build, restart, health check).

**Tech Stack:** GitHub Actions, `tailscale/github-action@v4`, SSH, systemd

---

### Task 1: Create the GitHub Actions Deploy Workflow

**Files:**
- Create: `.github/workflows/deploy-pi.yml`

**Step 1: Create the workflow file**

```yaml
name: Deploy to Pi

on:
  push:
    branches: [main]

concurrency:
  group: deploy-pi
  cancel-in-progress: false

jobs:
  deploy:
    name: Deploy to Raspberry Pi
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Setup Tailscale
        uses: tailscale/github-action@v4
        with:
          oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
          oauth-secret: ${{ secrets.TS_OAUTH_SECRET }}
          tags: tag:ci

      - name: Deploy via SSH
        env:
          PI_HOST: devserver
        run: |
          # Wait for Tailscale to be ready
          tailscale status

          # Deploy steps
          ssh -o StrictHostKeyChecking=no root@${PI_HOST} bash <<'DEPLOY'
          set -euo pipefail

          APP_DIR="/opt/compgraph-eval"
          SERVICE="compgraph-eval"

          echo "==> Pulling latest code..."
          cd "$APP_DIR" && git pull origin main

          echo "==> Installing dependencies..."
          cd "$APP_DIR/web" && npm ci

          echo "==> Building..."
          npm run build

          echo "==> Linking static assets..."
          ln -sf "$APP_DIR/web/public" "$APP_DIR/web/.next/standalone/public"
          mkdir -p "$APP_DIR/web/.next/standalone/.next"
          ln -sf "$APP_DIR/web/.next/static" "$APP_DIR/web/.next/standalone/.next/static"

          echo "==> Fixing ownership..."
          chown -R "$SERVICE:$SERVICE" "$APP_DIR"

          echo "==> Restarting service..."
          systemctl restart "$SERVICE"

          echo "==> Health check..."
          sleep 3
          STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000)
          if [ "$STATUS" = "200" ]; then
              echo "==> Deploy successful!"
          else
              echo "==> FAILED: Health check returned $STATUS"
              journalctl -u "$SERVICE" --no-pager -n 20
              exit 1
          fi
          DEPLOY

      - name: Report failure
        if: failure()
        run: echo "::error::Deployment to Pi failed. Check the deploy step logs above."
```

**Step 2: Verify YAML is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-pi.yml'))"`
Expected: No error (exits cleanly)

**Step 3: Commit**

```bash
git add .github/workflows/deploy-pi.yml
git commit -m "feat: add GitHub Actions auto-deploy to Pi via Tailscale"
```

---

### Task 2: Configure Tailscale OAuth and Pi SSH for GitHub Actions

This task requires manual steps in the Tailscale admin console and GitHub repo settings.

**Step 1: Create a Tailscale OAuth client**

1. Go to https://login.tailscale.com/admin/settings/oauth
2. Create a new OAuth client with:
   - Description: `compgraph-eval GitHub Actions deploy`
   - Scopes: Devices > Write (to create ephemeral nodes)
   - Tags: `tag:ci`
3. Copy the **Client ID** and **Client Secret**

**Step 2: Create the `tag:ci` ACL tag in Tailscale**

1. Go to https://login.tailscale.com/admin/acls
2. Add to the `tagOwners` section:
   ```json
   "tag:ci": ["autogroup:admin"]
   ```
3. Add an ACL rule allowing `tag:ci` to SSH to the Pi:
   ```json
   {"action": "accept", "src": ["tag:ci"], "dst": ["tag:server:22"]}
   ```
   (Adjust `dst` tag to match however the Pi is tagged, or use `"*:22"` for simplicity)

**Step 3: Enable Tailscale SSH on the Pi**

```bash
ssh compgraph-dev 'tailscale set --ssh'
```

Verify: `ssh compgraph-dev 'tailscale status --self'` should show SSH enabled.

**Step 4: Add GitHub repository secrets**

```bash
cd /Users/vmud/Documents/dev/projects/compgraph-eval
gh secret set TS_OAUTH_CLIENT_ID    # Paste the OAuth Client ID
gh secret set TS_OAUTH_SECRET       # Paste the OAuth Client Secret
```

Verify: `gh secret list` should show both secrets.

---

### Task 3: Push and Verify End-to-End

**Step 1: Push to main**

```bash
git push origin main
```

**Step 2: Watch the workflow run**

```bash
gh run watch
```

Or check: `gh run list --workflow=deploy-pi.yml`

Expected: Workflow triggers, Tailscale connects, SSH deploys successfully, health check passes.

**Step 3: If the workflow fails**

Check logs: `gh run view --log-failed`

Common issues:
- **Tailscale auth**: OAuth client ID/secret wrong → re-check secrets
- **SSH rejected**: Tailscale SSH not enabled on Pi → `ssh compgraph-dev 'tailscale set --ssh'`
- **ACL denied**: `tag:ci` can't reach Pi → update Tailscale ACLs
- **Build fails**: Code issue on main → fix and re-push

**Step 4: Verify the Pi is serving the latest build**

```bash
curl -s http://192.168.1.69:3000 | head -5
```
