#!/usr/bin/env bash
# Cron-compatible wrapper for the Cohezion research pipeline
#
# Exit codes:
#   0 = success
#   1 = partial failure (some sources failed)
#   2 = total failure
#
# Usage:
#   research/run_research.sh              # Full run
#   research/run_research.sh --quick      # Quick mode
#   research/run_research.sh --dry-run    # Dry run (no files written)
#
# Cron example (daily at 6am):
#   0 6 * * * /home/mike-anderson/vaults/cohezion-vault/research/run_research.sh

set -euo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python3"
LOG_DIR="${RESEARCH_LOG_DIR:-$HOME/.pilot/logs}"
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/research-$TODAY.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting research pipeline run"
log "Vault: $VAULT_DIR"
log "Python: $PYTHON"

# Check venv exists
if [ ! -f "$PYTHON" ]; then
    log "ERROR: Python venv not found at $VENV"
    log "Run: python3 -m venv $VENV && $VENV/bin/pip install -r requirements.txt"
    exit 2
fi

# Check Ollama availability
OLLAMA_STATUS="available"
if ! curl -s --connect-timeout 3 http://localhost:11434/api/version >/dev/null 2>&1; then
    OLLAMA_STATUS="unavailable"
    log "WARNING: Ollama not available - falling back to keyword-only scoring"
fi

# Change to vault directory and set PYTHONPATH
cd "$VAULT_DIR"
export PYTHONPATH="$VAULT_DIR:${PYTHONPATH:-}"

# Build CLI arguments (global args before subcommand)
CLI_ARGS=("--config" "research/sources.yaml" "--vault" "." "run")
CLI_ARGS+=("$@")  # Pass through any extra args (--quick, --dry-run, etc.)

# Run the pipeline
log "Running: $PYTHON research/cli.py ${CLI_ARGS[*]}"
set +e
OUTPUT=$("$PYTHON" research/cli.py "${CLI_ARGS[@]}" 2>&1)
EXIT_CODE=$?
set -e

log "Pipeline output: $OUTPUT"

if [ $EXIT_CODE -eq 0 ]; then
    log "Pipeline completed successfully"
    # Parse output for summary
    NOTES=$(echo "$OUTPUT" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); print(d.get('inbox_notes_created', 'N/A'))" 2>/dev/null || echo "N/A")
    log "Inbox notes created: $NOTES"
    exit 0
elif [ $EXIT_CODE -eq 1 ]; then
    log "WARNING: Pipeline completed with partial failures"
    exit 1
else
    log "ERROR: Pipeline failed with exit code $EXIT_CODE"

    # Write failure note to inbox so user sees it in Obsidian
    FAILURE_NOTE="$VAULT_DIR/inbox/research-failure-$TODAY.md"
    cat > "$FAILURE_NOTE" << EOF
---
title: "Research Pipeline Failure: $TODAY"
date: $TODAY
status: new
triage_status: new
tags: [research, failure, automation]
---

## Pipeline Failure

The automated research pipeline failed on $TODAY.

**Exit code:** $EXIT_CODE
**Ollama status:** $OLLAMA_STATUS
**Log file:** $LOG_FILE

### Error Output
\`\`\`
$OUTPUT
\`\`\`

### Troubleshooting
1. Check log file: \`cat $LOG_FILE\`
2. Verify venv: \`$PYTHON --version\`
3. Test manually: \`$PYTHON research/cli.py run --quick --vault .\`
4. Check Ollama: \`curl http://localhost:11434/api/version\`
EOF

    log "Failure note written to $FAILURE_NOTE"
    exit 2
fi
