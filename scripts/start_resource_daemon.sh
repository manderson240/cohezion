#!/usr/bin/env bash
set -euo pipefail

# Check if daemon already running
if curl -sf http://localhost:8765/health >/dev/null 2>&1; then
    echo "Resource daemon already running at :8765"
    exit 0
fi

echo "Starting Cohezion resource daemon..."
cd "$(git rev-parse --show-toplevel)"
exec uv run python -m cohezion.platform.resource_manager
