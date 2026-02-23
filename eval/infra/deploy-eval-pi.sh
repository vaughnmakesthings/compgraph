#!/usr/bin/env bash
set -euo pipefail

HOST="compgraph-dev"
APP_DIR="/opt/compgraph-eval"
FRONTEND_SERVICE="compgraph-eval"
API_SERVICE="compgraph-eval-api"

echo "==> Pulling latest code..."
ssh "$HOST" "cd $APP_DIR && git pull origin main"

echo "==> Installing Python dependencies..."
ssh "$HOST" "cd $APP_DIR && uv sync"

echo "==> Installing Node dependencies..."
ssh "$HOST" "cd $APP_DIR/web && npm ci"

echo "==> Building frontend..."
ssh "$HOST" "cd $APP_DIR/web && npm run build"

echo "==> Linking static assets..."
ssh "$HOST" "ln -sf $APP_DIR/web/public $APP_DIR/web/.next/standalone/public && mkdir -p $APP_DIR/web/.next/standalone/.next && ln -sf $APP_DIR/web/.next/static $APP_DIR/web/.next/standalone/.next/static"

echo "==> Fixing ownership..."
ssh "$HOST" "chown -R $FRONTEND_SERVICE:$FRONTEND_SERVICE $APP_DIR"

echo "==> Restarting services..."
ssh "$HOST" "systemctl restart $API_SERVICE && systemctl restart $FRONTEND_SERVICE"

echo "==> Health checks..."
sleep 3
API_STATUS=$(ssh "$HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/api/config/models")
WEB_STATUS=$(ssh "$HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")

if [ "$API_STATUS" = "200" ] && [ "$WEB_STATUS" = "200" ]; then
    echo "==> Deploy successful!"
    echo "    Frontend: http://192.168.1.69:3000"
    echo "    API:      http://192.168.1.69:8001 (localhost only)"
else
    echo "==> FAILED: API=$API_STATUS, Web=$WEB_STATUS"
    ssh "$HOST" "journalctl -u $API_SERVICE --no-pager -n 10; journalctl -u $FRONTEND_SERVICE --no-pager -n 10"
    exit 1
fi
