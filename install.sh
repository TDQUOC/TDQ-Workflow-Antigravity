#!/usr/bin/env bash
# TDQ-Workflow Antigravity User-Level One-Click Installer for macOS and Linux
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
    python3 "$DIR/install.py" "$@"
elif command -v python >/dev/null 2>&1; then
    python "$DIR/install.py" "$@"
else
    echo "Python 3 is required but was not found on PATH." >&2
    exit 1
fi
