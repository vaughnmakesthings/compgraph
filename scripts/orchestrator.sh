#!/usr/bin/env bash
# orchestrator.sh — Self-healing orchestrator wrapper with circuit breakers
# Usage: ./scripts/orchestrator.sh <issue-number> [stage]
#
# Features:
#   - Preflight validation (API keys, env, MCP connections)
#   - Circuit breaker: 3 consecutive identical failures → halt that stage
#   - Orphan cleanup before starting
#   - Headless mode support via claude -p

set -euo pipefail

ISSUE="${1:?Usage: orchestrator.sh <issue-number> [stage]}"
STAGE="${2:-all}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/work/logs"
STATUS_DIR="${PROJECT_DIR}/work/status"
MAX_RETRIES=3
MAX_TURNS=50

mkdir -p "$LOG_DIR" "$STATUS_DIR"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[orchestrator]${NC} $*"; }
warn() { echo -e "${YELLOW}[orchestrator]${NC} $*"; }
err()  { echo -e "${RED}[orchestrator]${NC} $*" >&2; }

# ── Phase 1: Orphan Cleanup ──────────────────────────────────────────
cleanup_orphans() {
    log "Checking for orphaned processes..."

    # Kill stale claude processes from previous runs (but not the current shell)
    local stale_pids
    stale_pids=$(ps aux | grep "[c]laude.*orchestrator\|[c]laude.*-p" | grep -v $$ | awk '{print $2}' || true)
    if [ -n "$stale_pids" ]; then
        warn "Found stale processes: $stale_pids"
        echo "$stale_pids" | xargs kill 2>/dev/null || true
        log "Cleaned up stale processes"
    fi

    # Clean stale status files older than 2 hours
    find "$STATUS_DIR" -name "*.status" -mmin +120 -delete 2>/dev/null || true
    log "Orphan cleanup complete"
}

# ── Phase 2: Preflight Validation ────────────────────────────────────
preflight() {
    log "Running preflight checks..."
    local failures=0

    # Check .env exists
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        err "PREFLIGHT FAIL: .env file not found"
        ((failures++))
    fi

    # Check critical env vars (source safely)
    if [ -f "${PROJECT_DIR}/.env" ]; then
        # Validate DATABASE_URL is set
        if ! grep -q '^DATABASE_URL=' "${PROJECT_DIR}/.env"; then
            err "PREFLIGHT FAIL: DATABASE_URL not set in .env"
            ((failures++))
        fi

        # Validate ANTHROPIC_API_KEY format (sk-ant-*)
        local api_key
        api_key=$(grep '^ANTHROPIC_API_KEY=' "${PROJECT_DIR}/.env" | cut -d= -f2- || true)
        if [ -z "$api_key" ]; then
            err "PREFLIGHT FAIL: ANTHROPIC_API_KEY not set"
            ((failures++))
        elif [[ ! "$api_key" =~ ^sk-ant- ]]; then
            err "PREFLIGHT FAIL: ANTHROPIC_API_KEY has invalid format (expected sk-ant-*)"
            ((failures++))
        fi
    fi

    # Check uv is available
    if ! command -v uv &>/dev/null; then
        err "PREFLIGHT FAIL: uv not found in PATH"
        ((failures++))
    fi

    # Check Python version
    local py_version
    py_version=$(python3 --version 2>/dev/null | awk '{print $2}' || true)
    if [[ ! "$py_version" =~ ^3\.1[23] ]]; then
        warn "PREFLIGHT WARN: Python version is $py_version (expected 3.12 or 3.13)"
    fi

    # Check gh CLI authenticated
    if ! gh auth status &>/dev/null 2>&1; then
        err "PREFLIGHT FAIL: gh CLI not authenticated"
        ((failures++))
    fi

    if [ "$failures" -gt 0 ]; then
        err "Preflight failed with $failures error(s). Aborting."
        exit 1
    fi

    log "Preflight passed"
}

# ── Phase 3: Run Stage with Circuit Breaker ──────────────────────────
run_stage() {
    local stage_name="$1"
    local prompt="$2"
    local log_file="${LOG_DIR}/issue-${ISSUE}-${stage_name}.log"
    local status_file="${STATUS_DIR}/issue-${ISSUE}-${stage_name}.status"
    local retry_count=0
    local last_error=""

    log "Starting stage: ${stage_name}"
    echo "running" > "$status_file"

    while [ "$retry_count" -lt "$MAX_RETRIES" ]; do
        log "Attempt $((retry_count + 1))/${MAX_RETRIES} for stage ${stage_name}"

        # Run claude in headless mode
        local exit_code=0
        claude -p "$prompt" \
            --allowedTools "Edit,Read,Write,Bash,Grep,Glob,Task" \
            --max-turns "$MAX_TURNS" \
            2>&1 | tee "$log_file" || exit_code=$?

        if [ "$exit_code" -eq 0 ]; then
            log "Stage ${stage_name} completed successfully"
            echo "success" > "$status_file"
            return 0
        fi

        # Circuit breaker: check if same error repeated
        local current_error
        current_error=$(tail -5 "$log_file" | head -1)
        if [ "$current_error" = "$last_error" ] && [ -n "$last_error" ]; then
            ((retry_count++))
            warn "Same error repeated (${retry_count}/${MAX_RETRIES}): ${current_error}"
        else
            retry_count=1
            last_error="$current_error"
            warn "New error, resetting counter: ${current_error}"
        fi

        if [ "$retry_count" -ge "$MAX_RETRIES" ]; then
            err "CIRCUIT BREAKER: Stage ${stage_name} failed ${MAX_RETRIES} times with same error"
            echo "failed: ${last_error}" > "$status_file"
            return 1
        fi

        sleep 5
    done
}

# ── Phase 4: Execute ─────────────────────────────────────────────────
main() {
    log "Orchestrator starting for issue #${ISSUE}, stage: ${STAGE}"

    cleanup_orphans
    preflight

    # Check for duplicate runs
    local lock_file="${STATUS_DIR}/issue-${ISSUE}.lock"
    if [ -f "$lock_file" ]; then
        local lock_pid
        lock_pid=$(cat "$lock_file")
        if kill -0 "$lock_pid" 2>/dev/null; then
            err "Another orchestrator is already running for issue #${ISSUE} (PID: ${lock_pid})"
            exit 1
        else
            warn "Stale lock file found, removing"
            rm -f "$lock_file"
        fi
    fi
    echo $$ > "$lock_file"
    trap 'rm -f "$lock_file"' EXIT

    local plan_file="docs/plans/issue-${ISSUE}.md"

    if [ "$STAGE" = "all" ] || [ "$STAGE" = "plan" ]; then
        run_stage "plan" \
            "Read the GitHub issue #${ISSUE} using 'gh issue view ${ISSUE}'. Create an implementation plan at ${plan_file}. Follow the project conventions in CLAUDE.md. Load the appropriate context pack from docs/context-packs.md for the task type." \
            || { err "Planning stage failed. Check ${LOG_DIR}/issue-${ISSUE}-plan.log"; exit 1; }
    fi

    if [ "$STAGE" = "all" ] || [ "$STAGE" = "implement" ]; then
        run_stage "implement" \
            "Execute the implementation plan at ${plan_file} for issue #${ISSUE}. Write code following CLAUDE.md conventions. Run tests after changes. Do not commit yet." \
            || { err "Implementation stage failed. Check ${LOG_DIR}/issue-${ISSUE}-implement.log"; exit 1; }
    fi

    if [ "$STAGE" = "all" ] || [ "$STAGE" = "test" ]; then
        run_stage "test" \
            "Run the full test suite with 'uv run pytest -v'. Fix any failures related to issue #${ISSUE}. Ensure all tests pass before proceeding." \
            || { err "Test stage failed. Check ${LOG_DIR}/issue-${ISSUE}-test.log"; exit 1; }
    fi

    if [ "$STAGE" = "all" ] || [ "$STAGE" = "review" ]; then
        run_stage "review" \
            "Review the changes for issue #${ISSUE} against the plan at ${plan_file}. Check: async patterns, append-only compliance, test coverage, no security issues. Report findings." \
            || { err "Review stage failed. Check ${LOG_DIR}/issue-${ISSUE}-review.log"; exit 1; }
    fi

    log "Orchestrator complete for issue #${ISSUE}"
    log "Logs: ${LOG_DIR}/issue-${ISSUE}-*.log"
    log "Status: ${STATUS_DIR}/issue-${ISSUE}-*.status"
}

main "$@"
