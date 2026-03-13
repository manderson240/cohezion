#!/usr/bin/env bash
# Dreaming Engine Cron Wrapper
#
# Checks SurrealDB health, acquires a lockfile to prevent overlapping runs,
# then executes dreaming-engine.py with timestamped logging.
#
# Usage:
#   scripts/dreaming-cron.sh              # Full run (all 7 engines)
#   scripts/dreaming-cron.sh --quick      # Quick run (engines 1-4 only)
#
# Cron schedule:
#   --quick every 6h: 0 0,6,12,18 * * *
#   --full  daily:    30 2 * * *

set -euo pipefail

VAULT_DIR="/home/mike-anderson/vaults/cohezion-vault"
SCRIPT="${VAULT_DIR}/scripts/dreaming-engine.py"
LOG_FILE="${VAULT_DIR}/logs/dreaming-engine.log"
LOCK_FILE="/tmp/dreaming-engine.lock"
SURREAL_URL="http://localhost:8001/health"
MODE="${1:---full}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# ── Lockfile guard ───────────────────────────────────────────────────────────
cleanup() {
    rm -f "$LOCK_FILE"
}

if [ -f "$LOCK_FILE" ]; then
    pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        log "SKIP: Another dreaming-engine is running (PID $pid)"
        exit 0
    fi
    # Stale lock — previous run crashed
    log "WARN: Removing stale lockfile (PID $pid no longer running)"
    rm -f "$LOCK_FILE"
fi

echo $$ > "$LOCK_FILE"
trap cleanup EXIT

# ── SurrealDB health check ──────────────────────────────────────────────────
if ! curl -sf -o /dev/null -u root:root "$SURREAL_URL" --max-time 5; then
    log "ABORT: SurrealDB not responding at $SURREAL_URL"
    exit 1
fi

# ── Run the Dreaming Engine ─────────────────────────────────────────────────
log "START: dreaming-engine.py $MODE"

if [ "$MODE" = "--quick" ]; then
    python3 "$SCRIPT" --quick >> "$LOG_FILE" 2>&1
    exit_code=$?
else
    python3 "$SCRIPT" >> "$LOG_FILE" 2>&1
    exit_code=$?
fi

# ── Generate Graph Briefing ──────────────────────────────────────────────────
log "BRIEFING: Generating graph-briefing.md"
python3 "${VAULT_DIR}/scripts/graph_context.py" briefing > "${VAULT_DIR}/metabolism/graph-briefing.md" 2>> "$LOG_FILE" || log "WARN: briefing generation failed"

if [ $exit_code -eq 0 ]; then
    log "DONE: dreaming-engine.py $MODE completed successfully"
else
    log "FAIL: dreaming-engine.py $MODE exited with code $exit_code"
fi

# ── Log rotation (keep last 50KB) ───────────────────────────────────────────
if [ -f "$LOG_FILE" ]; then
    log_size=$(wc -c < "$LOG_FILE")
    if [ "$log_size" -gt 51200 ]; then
        tail -c 25600 "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        log "LOG: Rotated (was ${log_size} bytes)"
    fi
fi

exit $exit_code
