#!/usr/bin/env bash
# PostToolUse hook: when a plan or research document is written,
# remind Claude to save a summary to claude-mem and reindex CodeSight.
#
# Triggered by: Write on files matching docs/plans/, docs/references/, .claude/plans/
# Stdout is injected into Claude's context as a system reminder.
# Exit 0 always (informational, never blocks).

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only act on plan/research document paths
case "$FILE_PATH" in
  */docs/plans/*|*/docs/references/*|*/.claude/plans/*)
    ;;
  *)
    exit 0
    ;;
esac

# Only act on markdown files
[[ "$FILE_PATH" == *.md ]] || exit 0

RELPATH=${FILE_PATH#"$CLAUDE_PROJECT_DIR"/}

# Determine document type from path
if [[ "$FILE_PATH" == *"/docs/plans/"* ]] || [[ "$FILE_PATH" == *"/.claude/plans/"* ]]; then
  DOC_TYPE="plan"
elif [[ "$FILE_PATH" == *"/docs/references/"* ]]; then
  DOC_TYPE="research"
else
  DOC_TYPE="document"
fi

# Extract title from first heading, fallback to filename
TITLE=$(head -5 "$FILE_PATH" 2>/dev/null | grep -m1 '^#' | sed 's/^#\+ *//' || true)
[ -z "$TITLE" ] && TITLE=$(basename "$FILE_PATH")

cat <<EOF
New ${DOC_TYPE} document detected: ${RELPATH}
Title: ${TITLE}

ACTION REQUIRED — do both NOW before continuing other work:
1. save_memory: "New ${DOC_TYPE}: ${TITLE} (${RELPATH})" to project compgraph
2. index_codebase: project_path="${CLAUDE_PROJECT_DIR}", project_name="compgraph"
EOF

exit 0
