#!/usr/bin/env bash
# PostToolUse hook: run ESLint and related Vitest tests when a .ts or .tsx file is edited.
# Triggered by Edit|Write on web/**/*.{ts,tsx}
# Exit 0 always (informational, never blocks).
set -euo pipefail

FILE_PATH=$(jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0

# Only web/ TypeScript files
[[ "$FILE_PATH" == *"/web/"* ]] || exit 0
[[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.tsx ]] || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}/web" || exit 0

# Run ESLint on the edited file
npm run lint -- --max-warnings 0 2>/dev/null | tail -15 || true

# Run related tests: map edited file to test file
RELPATH="${FILE_PATH#*web/}"
case "$RELPATH" in
  src/app/*/page.tsx) TEST_FILE="src/test/pages.test.tsx" ;;
  src/lib/api-client.ts) TEST_FILE="src/test/api-client.test.ts" ;;
  src/components/*) TEST_FILE="src/test/components.test.tsx" ;;
  *) exit 0 ;;
esac

[[ -f "$TEST_FILE" ]] && npm test -- --run "$TEST_FILE" 2>/dev/null | tail -12 || true
exit 0
