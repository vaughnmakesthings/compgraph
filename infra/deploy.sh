#!/usr/bin/env bash
# deploy.sh — Deploy CompGraph to Digital Ocean droplet
# Usage: bash infra/deploy.sh [--env-update]
set -euo pipefail
trap 'rm -f /tmp/compgraph-env' EXIT

SSH_HOST="compgraph-do"
APP_DIR="/opt/compgraph"
HEALTH_URL="https://dev.compgraph.io/health"

ENV_UPDATE=false
for arg in "$@"; do
    case $arg in
        --env-update) ENV_UPDATE=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

echo "=== Deploying CompGraph to DO ==="

# ── 1. Push secrets (optional) ──
if [ "$ENV_UPDATE" = true ]; then
    echo "[1/5] Resolving and pushing secrets from 1Password..."
    # Copy local .env (already has resolved secrets) with DO-specific additions
    cp .env /tmp/compgraph-env
    echo "" >> /tmp/compgraph-env
    echo "SCHEDULER_ENABLED=true" >> /tmp/compgraph-env
    echo "DB_POOL_SIZE=3" >> /tmp/compgraph-env
    echo "DB_MAX_OVERFLOW=2" >> /tmp/compgraph-env
    scp /tmp/compgraph-env "$SSH_HOST:$APP_DIR/.env"
    ssh "$SSH_HOST" "chown compgraph:compgraph $APP_DIR/.env && chmod 600 $APP_DIR/.env"
    rm /tmp/compgraph-env
    echo "  Secrets pushed."
else
    echo "[1/5] Skipping secrets (use --env-update to push)."
fi

# ── 2. Pull latest code ──
echo "[2/5] Pulling latest code..."
ssh "$SSH_HOST" "cd $APP_DIR && git config --global safe.directory $APP_DIR && git pull"

# ── 3. Sync dependencies ──
echo "[3/5] Syncing dependencies..."
ssh "$SSH_HOST" "cd $APP_DIR && sudo -u compgraph uv sync"

# ── 4. Restart services ──
echo "[4/5] Restarting services..."
ssh "$SSH_HOST" "systemctl restart compgraph && systemctl reload caddy"

# ── 5. Health check ──
echo "[5/5] Waiting for startup..."
sleep 5

if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo ""
    echo "=== Deploy successful ==="
    curl -sf "$HEALTH_URL" | python3 -m json.tool
else
    echo ""
    echo "=== Health check failed ==="
    echo "Checking logs..."
    ssh "$SSH_HOST" "journalctl -u compgraph -n 20 --no-pager"
    exit 1
fi
