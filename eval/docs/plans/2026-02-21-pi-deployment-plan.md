# CompGraph Eval — Pi Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy the CompGraph Eval Next.js dashboard to the Raspberry Pi at 192.168.1.69, accessible on LAN at port 3000.

**Architecture:** Install Node.js 22 LTS on the Pi, clone the repo, enable Next.js standalone output, build on-device, run via systemd service. Deploy script for future updates.

**Tech Stack:** Next.js 16, Node.js 22 LTS, systemd, SSH (`compgraph-dev`)

---

### Task 1: Enable Next.js Standalone Output

**Files:**
- Modify: `web/next.config.ts`

**Step 1: Add `output: 'standalone'` to next.config.ts**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

**Step 2: Verify the build works locally**

Run: `cd /Users/vmud/Documents/dev/projects/compgraph-eval/web && npm run build`
Expected: Build succeeds, `.next/standalone/` directory is created

**Step 3: Commit**

```bash
git add web/next.config.ts
git commit -m "feat: enable Next.js standalone output for Pi deployment"
```

---

### Task 2: Install Node.js 22 LTS on Pi

**Step 1: Install NodeSource repo and Node.js**

```bash
ssh compgraph-dev 'curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs'
```

Expected: Node.js 22.x installed

**Step 2: Verify installation**

```bash
ssh compgraph-dev 'node --version && npm --version'
```

Expected: `v22.x.x` and `10.x.x`

---

### Task 3: Clone Repo and Initial Build on Pi

**Step 1: Clone the compgraph-eval repo**

```bash
ssh compgraph-dev 'git clone https://github.com/vaughnmakesthings/compgraph-eval.git /opt/compgraph-eval'
```

Expected: Repo cloned to `/opt/compgraph-eval/`

**Step 2: Install dependencies**

```bash
ssh compgraph-dev 'cd /opt/compgraph-eval/web && npm ci'
```

Expected: `node_modules/` created, no errors

**Step 3: Build the production app**

```bash
ssh compgraph-dev 'cd /opt/compgraph-eval/web && npm run build'
```

Expected: `.next/standalone/server.js` exists after build

**Step 4: Smoke test the standalone server**

```bash
ssh compgraph-dev 'cd /opt/compgraph-eval/web && node .next/standalone/server.js &'
# Wait 3 seconds, then curl
ssh compgraph-dev 'sleep 3 && curl -s -o /dev/null -w "%{http_code}" http://localhost:3000'
# Then kill the test server
ssh compgraph-dev 'pkill -f "node .next/standalone/server.js"'
```

Expected: HTTP 200

---

### Task 4: Create systemd Service

**Files:**
- Create: `infra/compgraph-eval.service`

**Step 1: Create the service user on Pi**

```bash
ssh compgraph-dev 'useradd --system --no-create-home --shell /usr/sbin/nologin compgraph-eval && chown -R compgraph-eval:compgraph-eval /opt/compgraph-eval'
```

**Step 2: Write the systemd unit file**

Create `infra/compgraph-eval.service`:

```ini
[Unit]
Description=CompGraph Eval Dashboard
After=network.target

[Service]
Type=simple
User=compgraph-eval
Group=compgraph-eval
WorkingDirectory=/opt/compgraph-eval/web
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=HOSTNAME=0.0.0.0
ExecStart=/usr/bin/node /opt/compgraph-eval/web/.next/standalone/server.js
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Step 3: Copy service file to Pi and enable**

```bash
scp infra/compgraph-eval.service compgraph-dev:/etc/systemd/system/
ssh compgraph-dev 'systemctl daemon-reload && systemctl enable --now compgraph-eval'
```

**Step 4: Verify service is running**

```bash
ssh compgraph-dev 'systemctl status compgraph-eval --no-pager'
```

Expected: `active (running)`

**Step 5: Verify LAN access**

```bash
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.69:3000
```

Expected: HTTP 200

**Step 6: Copy static assets for standalone mode**

Next.js standalone mode requires `public/` and `.next/static/` to be available alongside the standalone server. Symlink them:

```bash
ssh compgraph-dev 'ln -sf /opt/compgraph-eval/web/public /opt/compgraph-eval/web/.next/standalone/public && ln -sf /opt/compgraph-eval/web/.next/static /opt/compgraph-eval/web/.next/standalone/.next/static'
```

Then restart:

```bash
ssh compgraph-dev 'systemctl restart compgraph-eval'
```

**Step 7: Commit**

```bash
git add infra/compgraph-eval.service
git commit -m "feat: add systemd service for Pi deployment"
```

---

### Task 5: Create Deploy Script

**Files:**
- Create: `infra/deploy-eval-pi.sh`

**Step 1: Write the deploy script**

Create `infra/deploy-eval-pi.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST="compgraph-dev"
APP_DIR="/opt/compgraph-eval"
SERVICE="compgraph-eval"

echo "==> Pulling latest code..."
ssh "$HOST" "cd $APP_DIR && git pull origin main"

echo "==> Installing dependencies..."
ssh "$HOST" "cd $APP_DIR/web && npm ci"

echo "==> Building..."
ssh "$HOST" "cd $APP_DIR/web && npm run build"

echo "==> Linking static assets..."
ssh "$HOST" "ln -sf $APP_DIR/web/public $APP_DIR/web/.next/standalone/public && mkdir -p $APP_DIR/web/.next/standalone/.next && ln -sf $APP_DIR/web/.next/static $APP_DIR/web/.next/standalone/.next/static"

echo "==> Fixing ownership..."
ssh "$HOST" "chown -R $SERVICE:$SERVICE $APP_DIR"

echo "==> Restarting service..."
ssh "$HOST" "systemctl restart $SERVICE"

echo "==> Checking health..."
sleep 3
STATUS=$(ssh "$HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
if [ "$STATUS" = "200" ]; then
    echo "==> Deploy successful! http://192.168.1.69:3000"
else
    echo "==> WARNING: Health check returned $STATUS"
    ssh "$HOST" "journalctl -u $SERVICE --no-pager -n 20"
    exit 1
fi
```

**Step 2: Make executable**

```bash
chmod +x infra/deploy-eval-pi.sh
```

**Step 3: Commit**

```bash
git add infra/deploy-eval-pi.sh
git commit -m "feat: add Pi deploy script for eval dashboard"
```

---

### Task 6: Push and Verify End-to-End

**Step 1: Push all commits**

```bash
git push origin main
```

**Step 2: Run the deploy script to verify it works**

```bash
bash infra/deploy-eval-pi.sh
```

Expected: "Deploy successful! http://192.168.1.69:3000"

**Step 3: Open in browser**

Navigate to `http://192.168.1.69:3000` — the eval dashboard should load with all pages working.
