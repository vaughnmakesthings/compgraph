#!/usr/bin/env bash
# Install git hooks by symlinking from scripts/hooks/ to .git/hooks/
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="${PROJECT_DIR}/.git/hooks"

for hook in "${SCRIPT_DIR}/hooks/"*; do
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
