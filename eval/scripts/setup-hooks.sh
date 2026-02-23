#!/usr/bin/env bash
# Install git hooks by symlinking from scripts/hooks/ to .git/hooks/
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="${PROJECT_DIR}/.git/hooks"
HOOKS_SRC="${SCRIPT_DIR}/hooks"

if [ ! -d "$HOOKS_SRC" ] || [ -z "$(ls -A "$HOOKS_SRC" 2>/dev/null)" ]; then
    echo "No hooks found in ${HOOKS_SRC}"
    exit 0
fi

for hook in "${HOOKS_SRC}/"*; do
    name=$(basename "$hook")
    target="${HOOKS_DIR}/${name}"

    if [ -f "$target" ] && [ ! -L "$target" ]; then
        echo "Backing up existing ${name} to ${name}.bak"
        mv "$target" "${target}.bak"
    fi

    ln -sf "$hook" "$target"
    echo "Installed: ${name}"
done

echo "Git hooks installed."
