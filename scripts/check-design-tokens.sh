#!/usr/bin/env bash
# Check for hardcoded hex colors in frontend source files.
# Warning only — exits 0 regardless. Integrated into pre-commit and CI.
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
WEB_SRC="$REPO_ROOT/web/src"

# Search for hex color patterns (#fff, #ffffff, #ffffffff) in .ts/.tsx files
# Exclude: globals.css (token definitions), chart-utils.ts (chart colors),
#          components/ui/ (shadcn/Tremor generated), test files
MATCHES=$(grep -rn --include='*.ts' --include='*.tsx' \
    -E '#[0-9A-Fa-f]{3,8}\b' "$WEB_SRC" \
    | grep -v '/globals\.css' \
    | grep -v '/chart-utils\.ts' \
    | grep -v '/components/ui/' \
    | grep -v '\.test\.' \
    | grep -v '/__tests__/' \
    || true)

if [ -n "$MATCHES" ]; then
    echo "[design-tokens] Warning: hardcoded hex colors found — prefer design tokens:"
    echo "$MATCHES"
    echo ""
    echo "Define colors in globals.css @theme and use Tailwind utility classes instead."
fi

exit 0
