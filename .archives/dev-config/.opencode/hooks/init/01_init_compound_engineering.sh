#!/bin/bash
# Opencode Hook: Automatic Compound Engineering Environment Setup
# This hook runs at the start of each session to initialize the 
# TDD + Adversarial Review compound engineering environment

set -euo pipefail

# Configuration
LOG_FILE="${OPENCODE_LOG_DIR:-${PWD}/.opencode/logs}/hook_init.log"
LOG_DIR="${OPENCODE_LOG_DIR:-${PWD}/.opencode/logs}"

# Logging function
log() {
    local message="[opencode-compound-engineering-hook] $1"
    echo "$message"
    echo "$message" >> "$LOG_FILE"
}

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Initialize the compound engineering environment
log "Initializing compound engineering environment with TDD and Adversarial Review"

# Change to the project root if we're not already there
# This ensures we're working in the correct context
PROJECT_ROOT="${OPENCODE_PROJECT_ROOT:-${PWD}}"
cd "$PROJECT_ROOT"

# Initialize the workflow initializer
log "Starting workflow initialization..."
python3 -c "
import asyncio
import sys
import os
sys.path.insert(0, '${PROJECT_ROOT}/src')

from cohezion.compound.daemon.workflow_initializer import get_workflow_initializer

async def initialize():
    try:
        initializer = get_workflow_initializer()
        result = await initializer.initialize_session(
            session_id=os.environ.get('OPENCODE_SESSION_ID'),
            create_worktree=True,   # Always create isolated worktrees
            prepare_tdd=True,       # Prepare TDD environment
            prepare_review=True     # Prepare adversarial review environment
        )
        
        if result.get('success', False):
            print('SUCCESS: Compound engineering environment initialized')
            print(f'Session ID: {result.get(\"session_id\")}')
            print(f'Worktree: {result.get(\"worktree_path\")}')
            print(f'TDD Ready: {result.get(\"tdd_ready\")}')
            print(f'Review Ready: {result.get(\"review_ready\")}')
            return 0
        else:
            print('ERROR: Failed to initialize compound engineering environment')
            for error in result.get('errors', []):
                print(f'  - {error}')
            return 1
    except Exception as e:
        print(f'ERROR: Exception during initialization: {e}')
        return 1

exit_code = asyncio.run(initialize())
sys.exit(exit_code)
"

# Check if initialization was successful
if [ $? -ne 0 ]; then
    log "ERROR: Failed to initialize compound engineering environment"
    # Don't fail the hook - let the session continue but log the issue
else
    log "SUCCESS: Compound engineering environment initialized with TDD and Adversarial Review"
fi

log "Compound engineering hook completed"
