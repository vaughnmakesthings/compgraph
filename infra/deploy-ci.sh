#!/usr/bin/env bash
# deploy-ci.sh — CI/CD deploy script for GitHub Actions
# Runs on the droplet after SSH connection is established.
# Usage: bash /opt/compgraph/infra/deploy-ci.sh
set -euo pipefail

APP_DIR="/opt/compgraph"
HEALTH_URL="https://dev.compgraph.io/health"

cd "$APP_DIR"

echo "=== CD Deploy: $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

# ── 0. Pre-deploy: wait for active pipeline to finish ──
PIPELINE_WAIT_MAX=600  # 10 minutes max wait
PIPELINE_WAIT_INTERVAL=15
PIPELINE_WAITED=0

echo "[0/5] Checking for active pipeline..."
while [ $PIPELINE_WAITED -lt $PIPELINE_WAIT_MAX ]; do
    HEALTH_JSON=$(curl -sf "$HEALTH_URL" || echo '{}')
    PIPELINE_STATUS=$(echo "$HEALTH_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('checks',{}).get('pipeline','unknown'))" || echo "unknown")

    if [ "$PIPELINE_STATUS" = "idle" ]; then
        echo "  Pipeline is idle. Proceeding with deploy."
        break
    fi

    if [ "$PIPELINE_STATUS" = "unknown" ]; then
        echo "  WARNING: Pipeline status unknown (health endpoint may be down). Proceeding with deploy."
        break
    fi

    echo "  Pipeline is $PIPELINE_STATUS. Waiting ${PIPELINE_WAIT_INTERVAL}s... (${PIPELINE_WAITED}/${PIPELINE_WAIT_MAX}s)"
    sleep $PIPELINE_WAIT_INTERVAL
    PIPELINE_WAITED=$((PIPELINE_WAITED + PIPELINE_WAIT_INTERVAL))
done

if [ $PIPELINE_WAITED -ge $PIPELINE_WAIT_MAX ]; then
    echo "  WARNING: Pipeline still active after ${PIPELINE_WAIT_MAX}s. Deploying anyway."
fi

# ── 1. Pull latest code ──
echo "[1/5] Pulling latest code..."
git config --global safe.directory "$APP_DIR"
# Reset any tracked files modified on the server (uv.lock platform markers,
# migrations applied locally, etc.) to prevent merge conflicts on pull.
git checkout -- . 2>/dev/null || true
git pull origin main

# ── 2. Sync dependencies ──
echo "[2/5] Syncing dependencies..."
# Force Python 3.12 — server has 3.12 system-wide; .python-version may
# request 3.13+ which uv would install to root's cache (inaccessible to
# the compgraph service user).
sudo -u compgraph uv sync --python 3.12

# ── 3. Run Alembic migrations ──
echo "[3/5] Running migrations..."
# Build pooler URL from .env — avoids IPv6 direct connection issues
DB_PASSWORD=$(sudo grep '^DATABASE_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2-)
ENCODED_PW=$(DB_PASSWORD="$DB_PASSWORD" python3 -c "import os; from urllib.parse import quote_plus; print(quote_plus(os.environ['DB_PASSWORD']))")
SUPABASE_REF="tkvxyxwfosworwqxesnz"
export ALEMBIC_DATABASE_URL="postgresql+asyncpg://postgres.${SUPABASE_REF}:${ENCODED_PW}@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

CURRENT=$(sudo -u compgraph env ALEMBIC_DATABASE_URL="$ALEMBIC_DATABASE_URL" "$APP_DIR/.venv/bin/alembic" current 2>&1 | tail -1 | awk '{print $1}')
HEAD=$(sudo -u compgraph env ALEMBIC_DATABASE_URL="$ALEMBIC_DATABASE_URL" "$APP_DIR/.venv/bin/alembic" heads 2>&1 | tail -1 | awk '{print $1}')

if [ "$CURRENT" = "$HEAD" ]; then
    echo "  Database already at head ($HEAD). Skipping."
else
    echo "  Migrating: $CURRENT -> $HEAD"
    sudo -u compgraph env ALEMBIC_DATABASE_URL="$ALEMBIC_DATABASE_URL" "$APP_DIR/.venv/bin/alembic" upgrade head
    echo "  Migration complete."
fi

# ── 4. Restart services ──
echo "[4/5] Restarting services..."
systemctl restart compgraph
systemctl reload caddy

# ── 5. Health check ──
echo "[5/5] Waiting for startup..."
sleep 2

ATTEMPTS=0
MAX_ATTEMPTS=6
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo ""
        echo "=== Deploy successful ==="
        curl -sf "$HEALTH_URL"
        echo ""
        exit 0
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    echo "  Health check attempt $ATTEMPTS/$MAX_ATTEMPTS failed, retrying in 3s..."
    sleep 3
done

echo ""
echo "=== Health check failed after $MAX_ATTEMPTS attempts ==="
journalctl -u compgraph -n 30 --no-pager
exit 1
