#!/usr/bin/env bash
# scripts/process-issue.sh — Headless pipeline for processing a single GitHub issue
# Usage: bash scripts/process-issue.sh <issue-number>
set -euo pipefail

ISSUE="${1:?Usage: process-issue.sh <issue-number>}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREE="${PROJECT_DIR}/../compgraph-issue-${ISSUE}"
LOG_DIR="/tmp/compgraph-pipeline"
RETRY_MAX=3

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
fail() { log "FATAL: $*"; exit 1; }

# Circuit breaker: track consecutive failures per phase
check_circuit() {
  local phase="$1" rf="/tmp/compgraph-cb-${ISSUE}-${phase}"
  local count
  count=$(cat "$rf" 2>/dev/null || echo 0)
  if [ "$count" -ge "$RETRY_MAX" ]; then
    rm -f "$rf"
    fail "Circuit breaker tripped for phase '${phase}' after ${RETRY_MAX} failures"
  fi
  echo $((count + 1)) > "$rf"
}

reset_circuit() {
  local phase="$1"
  rm -f "/tmp/compgraph-cb-${ISSUE}-${phase}"
}

cleanup_circuits() {
  rm -f /tmp/compgraph-cb-"${ISSUE}"-*
}
trap cleanup_circuits EXIT

log "=== Processing issue #${ISSUE} ==="

# Phase 1: Setup worktree
log "[1/3] Setting up worktree at ${WORKTREE}..."
check_circuit "setup"
claude -p "$(cat <<EOF
Set up a git worktree for GitHub issue #${ISSUE}:
1. git fetch origin
2. git worktree add ${WORKTREE} -b feat/issue-${ISSUE} origin/main
3. cd ${WORKTREE} && python3.13 -m venv .venv && source .venv/bin/activate && uv sync
4. uv run pytest -x -q --no-cov to verify baseline
Report: worktree path, Python version, test count.
EOF
)" \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  --output-format json > "${LOG_DIR}/setup-${ISSUE}.json" \
  || fail "Worktree setup failed"
reset_circuit "setup"
log "[1/3] Worktree ready."

# Phase 2: Implement
log "[2/3] Implementing changes..."
check_circuit "impl"
claude -p "$(cat <<EOF
You are working in ${WORKTREE} on GitHub issue #${ISSUE}.
1. Read the issue: gh issue view ${ISSUE} --json title,body,labels
2. Read CLAUDE.md for project conventions
3. Implement the required changes following all conventions (async, append-only, UUIDs, etc.)
4. After each file change, run: uv run pytest -x -q --no-cov
5. Iterate until ALL tests pass. Max 5 fix cycles — if still failing, stop and report what's broken.
6. Run: uv run ruff check src/ tests/ && uv run ruff format src/ tests/
Do NOT commit, push, or create a PR.
EOF
)" \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  --output-format json > "${LOG_DIR}/impl-${ISSUE}.json" \
  || fail "Implementation failed"
reset_circuit "impl"
log "[2/3] Implementation complete."

# Phase 3: Commit and PR
log "[3/3] Creating commit and draft PR..."
check_circuit "pr"
claude -p "$(cat <<EOF
You are in ${WORKTREE} on branch feat/issue-${ISSUE}.
1. git add the changed files (not .env, credentials, or .venv/)
2. Create a commit with a conventional message referencing #${ISSUE}
3. git push -u origin feat/issue-${ISSUE}
4. gh pr create --draft --title "<short title>" --body "Closes #${ISSUE}" --base main
Report: the PR URL.
EOF
)" \
  --allowedTools "Bash,Read,Glob,Grep" \
  --output-format json > "${LOG_DIR}/pr-${ISSUE}.json" \
  || fail "PR creation failed"
reset_circuit "pr"
log "[3/3] Draft PR created."

log "=== Pipeline complete for issue #${ISSUE} ==="
log "Logs: ${LOG_DIR}/*-${ISSUE}.json"
