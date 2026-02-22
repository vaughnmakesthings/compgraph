#!/usr/bin/env bash
# deploy-ci.sh — CI/CD deploy script for GitHub Actions
# Runs on the droplet after SSH connection is established.
# Usage: bash /opt/compgraph/infra/deploy-ci.sh
set -euo pipefail

APP_DIR="/opt/compgraph"
HEALTH_URL="https://dev.compgraph.io/health"

cd "$APP_DIR"

echo "=== CD Deploy: $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

# ── 1. Pull latest code ──
echo "[1/5] Pulling latest code..."
git config --global safe.directory "$APP_DIR"
git pull origin main

# ── 2. Sync dependencies ──
echo "[2/5] Syncing dependencies..."
sudo -u compgraph uv sync

# ── 3. Run Alembic migrations ──
echo "[3/5] Running migrations..."
# Build pooler URL from .env — avoids IPv6 direct connection issues
DB_PASSWORD=$(sudo grep '^DATABASE_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2-)
ENCODED_PW=$(python3 -c "from urllib.parse import quote_plus; print(quote_plus('$DB_PASSWORD'))")
SUPABASE_REF="tkvxyxwfosworwqxesnz"
export ALEMBIC_DATABASE_URL="postgresql+asyncpg://postgres.${SUPABASE_REF}:${ENCODED_PW}@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

ALEMBIC="sudo -u compgraph env ALEMBIC_DATABASE_URL=$ALEMBIC_DATABASE_URL $APP_DIR/.venv/bin/alembic"

CURRENT=$($ALEMBIC current 2>&1 | tail -1)
HEAD=$($ALEMBIC heads 2>&1 | tail -1 | awk '{print $1}')

if [ "$CURRENT" = "$HEAD" ]; then
    echo "  Database already at head ($HEAD). Skipping."
else
    echo "  Migrating: $CURRENT -> $HEAD"
    $ALEMBIC upgrade head
    echo "  Migration complete."
fi

# ── 4. Restart services ──
echo "[4/5] Restarting services..."
systemctl restart compgraph compgraph-dashboard
systemctl reload caddy

# ── 5. Health check ──
echo "[5/5] Waiting for startup..."
sleep 5

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
    echo "  Health check attempt $ATTEMPTS/$MAX_ATTEMPTS failed, retrying in 5s..."
    sleep 5
done

echo ""
echo "=== Health check failed after $MAX_ATTEMPTS attempts ==="
journalctl -u compgraph -n 30 --no-pager
exit 1
