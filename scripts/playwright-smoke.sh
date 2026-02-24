#!/usr/bin/env bash
# Playwright smoke test — hits key URLs and verifies they load.
# Requires: npx playwright (installed via @playwright/test or @playwright/mcp)
# Usage: bash scripts/playwright-smoke.sh [--install]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_DIR="$PROJECT_DIR/web"

# Optional: install Playwright browsers on first run
if [[ "${1:-}" == "--install" ]]; then
    cd "$WEB_DIR"
    npx playwright install chromium 2>/dev/null || true
    exit 0
fi

cd "$WEB_DIR"

# Check if @playwright/test is available
if ! npm ls @playwright/test >/dev/null 2>&1; then
    echo "Installing @playwright/test for smoke tests..."
    npm install -D @playwright/test
fi

# Create minimal smoke test if missing
SMOKE_SPEC="$WEB_DIR/tests/smoke.spec.ts"
if [[ ! -f "$SMOKE_SPEC" ]]; then
    mkdir -p "$(dirname "$SMOKE_SPEC")"
    cat > "$SMOKE_SPEC" << 'EOF'
import { test, expect } from '@playwright/test';

test.describe('Smoke', () => {
  test('backend health returns 200', async ({ request }) => {
    const base = process.env.NEXT_PUBLIC_API_URL || 'https://dev.compgraph.io';
    const res = await request.get(`${base}/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
  });

  test('frontend loads', async ({ page }) => {
    const url = process.env.SMOKE_FRONTEND_URL || 'https://compgraph.vercel.app';
    const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
    expect(res?.status()).toBe(200);
  });
});
EOF
    echo "Created $SMOKE_SPEC"
fi

# Run smoke tests (headless)
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-https://dev.compgraph.io}"
npx playwright test tests/smoke.spec.ts --project=chromium || {
    echo "Playwright smoke failed. Run: bash scripts/playwright-smoke.sh --install"
    exit 1
}
