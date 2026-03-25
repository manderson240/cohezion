#!/bin/bash
# Opencode Hook: Automatic Git Worktree Setup for Compound Engineering
# This hook runs at the start of each session to create an isolated worktree
# and initialize the TDD + Adversarial Review compound engineering environment

set -euo pipefail

# Configuration
WORKtrees_BASE_DIR="${OPENCODE_WORKTREES_DIR:-${PWD}/.opencode/worktrees}"
SESSION_ID="${OPENCODE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"
WORKTREE_NAME="session-${SESSION_ID}"
WORKTREE_PATH="${WORKtrees_BASE_DIR}/${WORKTREE_NAME}"
BRANCH_NAME="session/${SESSION_ID}"

# Logging function
log() {
    echo "[opencode-worktree-hook] $1"
}

# Error handling
handle_error() {
    log "ERROR: $1"
    exit 1
}

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    handle_error "Not in a git repository"
fi

# Get current branch and commit
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse HEAD)

log "Current branch: ${CURRENT_BRANCH} (${CURRENT_COMMIT:0:8})"

# Check if worktrees base directory exists, create if not
mkdir -p "${WORKtrees_BASE_DIR}"

# Check if we already have a worktree for this session
if [ -d "${WORKTREE_PATH}" ]; then
    log "Worktree already exists at ${WORKTREE_PATH}"
    # Check if it's valid
    if [ -d "${WORKTREE_PATH}/.git" ] || [ -f "${WORKTREE_PATH}/.git" ]; then
        log "Using existing worktree"
        cd "${WORKTREE_PATH}"
        # Export environment variables for downstream hooks
        export OPENCODE_WORKTREE_PATH="${WORKTREE_PATH}"
        export OPENCODE_SESSION_ID="${SESSION_ID}"
        export OPENCODE_WORKTREE_NAME="${WORKTREE_NAME}"
        exit 0
    else
        log "Existing worktree path is not a valid git worktree, removing..."
        rm -rf "${WORKTREE_PATH}"
    fi
fi

# Create new worktree from current commit
log "Creating new worktree: ${WORKTREE_NAME}"
log "From commit: ${CURRENT_COMMIT:0:8}"
log "Branch: ${BRANCH_NAME}"
log "Path: ${WORKTREE_PATH}"

# Create the worktree
if ! git worktree add -b "${BRANCH_NAME}" "${WORKTREE_PATH}" "${CURRENT_COMMIT}"; then
    handle_error "Failed to create git worktree"
fi

# Change to the worktree directory
cd "${WORKTREE_PATH}"

# Export environment variables for downstream hooks and processes
export OPENCODE_WORKTREE_PATH="${WORKTREE_PATH}"
export OPENCODE_SESSION_ID="${SESSION_ID}"
export OPENCODE_WORKTREE_NAME="${WORKTREE_NAME}"
export OPENCODE_GIT_WORKTREE="true"
export OPENCODE_ORIGINAL_BRANCH="${CURRENT_BRANCH}"
export OPENCODE_ORIGINAL_COMMIT="${CURRENT_COMMIT}"

log "Successfully initialized worktree session: ${SESSION_ID}"
log "Working in: ${WORKTREE_PATH}"
log "Branch: ${BRANCH_NAME}"
log "Isolated from: ${CURRENT_BRANCH}"

# Verify we're in the correct location
if [ "$(pwd)" != "${WORKTREE_PATH}" ]; then
    handle_error "Failed to change to worktree directory"
fi

# Verify this is a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    handle_error "Worktree directory is not a valid git repository"
fi

log "Worktree initialization complete"
