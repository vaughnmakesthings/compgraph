#!/usr/bin/env bash
# scripts/dev.sh — Start both API and web servers for development
set -e

# Register trap before starting background processes to avoid cleanup race
trap 'kill $API_PID $WEB_PID 2>/dev/null' EXIT

echo "Starting eval API on :8001..."
uv run uvicorn eval.api:app --port 8001 --reload &
API_PID=$!

echo "Starting Next.js on :3000..."
cd web && npm run dev &
WEB_PID=$!

wait
