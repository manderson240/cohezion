#!/bin/bash
# Cohezion - SurrealDB Launcher
# Ensures environment variables from .env (including subshells) are expanded correctly.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COHEZION_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$COHEZION_ROOT/.env" ]; then
    # We use a subshell to source and print to avoid polluting the current env
    # but we need the variables. 
    # Actually, just sourcing it here in bash works fine.
    set -a
    source "$COHEZION_ROOT/.env"
    set +a
fi

echo "🚀 Starting SurrealDB at $SURREAL_DATA_PATH on port $SURREAL_PORT"
exec "$SURREAL_BIN_PATH" start \
    --user "$SURREAL_USER" \
    --pass "$SURREAL_PASS" \
    --bind 0.0.0.0:"$SURREAL_PORT" \
    file://"$SURREAL_DATA_PATH"
