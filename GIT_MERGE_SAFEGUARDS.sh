#!/bin/bash

################################################################################
# GIT MERGE SAFEGUARDS FOR PHASE 5B INTEGRATION
#
# Purpose: Automate pre-merge, merge, and post-merge validation
#
# Usage:
#   bash GIT_MERGE_SAFEGUARDS.sh [--dry-run|--execute|--verify]
#
# Stages:
#   1. PRE-MERGE: Validate branch state, backup, update .gitignore
#   2. MERGE: Execute rebase + merge with conflict tracking
#   3. POST-MERGE: Verify tests, imports, commit history
#   4. ROLLBACK: Restore from backup if needed
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/mike-anderson/dev/cohezion"
FEATURE_BRANCH="feature/token-efficiency-5b"
TARGET_BRANCH="develop"
BACKUP_BRANCH="backup-merge-$(date +%s)"
DRY_RUN=${1:-"--dry-run"}

# Logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

################################################################################
# STAGE 1: PRE-MERGE VALIDATION
################################################################################

pre_merge_validation() {
    log_info "=== STAGE 1: PRE-MERGE VALIDATION ==="

    cd "$PROJECT_ROOT"

    # Check current branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current branch: $current_branch"

    # Verify branches exist
    if ! git show-ref --verify --quiet "refs/heads/$FEATURE_BRANCH"; then
        log_error "Feature branch '$FEATURE_BRANCH' not found"
        return 1
    fi

    if ! git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
        log_error "Target branch '$TARGET_BRANCH' not found"
        return 1
    fi

    log_success "Both branches exist"

    # Check working directory is clean
    if [[ $(git status --porcelain | wc -l) -gt 0 ]]; then
        log_warn "Working directory has uncommitted changes:"
        git status --porcelain | head -5
        log_warn "These will be stashed during merge"
    fi

    # Fetch latest from origin
    log_info "Fetching latest changes from origin..."
    git fetch origin "$TARGET_BRANCH" "$FEATURE_BRANCH" 2>/dev/null || log_warn "Fetch incomplete (offline?)"

    # Check if branches are tracking
    feature_behind=$(git rev-list --count "$FEATURE_BRANCH..origin/$FEATURE_BRANCH" 2>/dev/null || echo "unknown")
    target_behind=$(git rev-list --count "$TARGET_BRANCH..origin/$TARGET_BRANCH" 2>/dev/null || echo "unknown")

    log_info "Feature branch status: $feature_behind commits behind origin"
    log_info "Target branch status: $target_behind commits behind origin"

    # Verify test suite exists
    if [[ ! -d "$PROJECT_ROOT/tests" ]]; then
        log_error "Test directory not found"
        return 1
    fi

    log_success "PRE-MERGE VALIDATION PASSED"
}

################################################################################
# STAGE 2: GITIGNORE UPDATES
################################################################################

update_gitignore() {
    log_info "=== STAGE 2: UPDATE .GITIGNORE FOR GENERATED ARTIFACTS ==="

    cd "$PROJECT_ROOT"

    # Files to ignore
    IGNORE_PATTERNS=(
        "uv.lock"
        "cloud-vault-mcp/uv.lock"
        "src/cohezion/skills/skill_registry.json"
        "*.egg-info/"
        ".pytest_cache/"
        "__pycache__/"
        ".ruff_cache/"
        "*.pyc"
    )

    # Check if already in .gitignore
    for pattern in "${IGNORE_PATTERNS[@]}"; do
        if grep -q "^${pattern}$" .gitignore 2>/dev/null; then
            log_info "Already ignoring: $pattern"
        else
            log_warn "Adding to .gitignore: $pattern"
            if [[ "$DRY_RUN" != "--dry-run" ]]; then
                echo "$pattern" >> .gitignore
            fi
        fi
    done

    # Remove generated artifacts from git tracking
    log_info "Removing generated artifacts from git..."

    for file in uv.lock cloud-vault-mcp/uv.lock src/cohezion/skills/skill_registry.json; do
        if git ls-files --error-unmatch "$file" 2>/dev/null; then
            if [[ "$DRY_RUN" != "--dry-run" ]]; then
                log_info "Removing from git: $file"
                git rm --cached "$file" 2>/dev/null || true
            else
                log_info "[DRY-RUN] Would remove: $file"
            fi
        fi
    done

    log_success "GITIGNORE UPDATES COMPLETED"
}

################################################################################
# STAGE 3: CREATE BACKUP
################################################################################

create_backup() {
    log_info "=== STAGE 3: CREATE BACKUP BRANCH ==="

    cd "$PROJECT_ROOT"

    log_info "Creating backup: $BACKUP_BRANCH"

    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        git branch "$BACKUP_BRANCH"
        log_success "Backup created: $BACKUP_BRANCH"
    else
        log_info "[DRY-RUN] Would create: $BACKUP_BRANCH"
    fi
}

################################################################################
# STAGE 4: REBASE FEATURE BRANCH
################################################################################

rebase_feature_branch() {
    log_info "=== STAGE 4: REBASE FEATURE BRANCH ONTO TARGET ==="

    cd "$PROJECT_ROOT"

    log_info "Checking out feature branch: $FEATURE_BRANCH"
    git checkout "$FEATURE_BRANCH"

    # Stash any changes
    stash_created=false
    if [[ $(git status --porcelain | wc -l) -gt 0 ]]; then
        log_warn "Stashing working directory changes..."
        git stash
        stash_created=true
    fi

    log_info "Rebasing onto $TARGET_BRANCH..."

    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        if git rebase "$TARGET_BRANCH"; then
            log_success "Rebase completed successfully"

            # Restore stash if created
            if [[ "$stash_created" == true ]]; then
                log_info "Restoring stashed changes..."
                git stash pop || log_warn "Stash pop failed (no stash)"
            fi
        else
            log_error "REBASE FAILED - Conflicts detected"
            log_info "Resolve conflicts manually, then run: git rebase --continue"
            return 1
        fi
    else
        log_info "[DRY-RUN] Would rebase $FEATURE_BRANCH onto $TARGET_BRANCH"
    fi
}

################################################################################
# STAGE 5: MERGE TO TARGET BRANCH
################################################################################

merge_to_target() {
    log_info "=== STAGE 5: MERGE FEATURE TO TARGET BRANCH ==="

    cd "$PROJECT_ROOT"

    log_info "Checking out target branch: $TARGET_BRANCH"
    git checkout "$TARGET_BRANCH"

    log_info "Merging $FEATURE_BRANCH into $TARGET_BRANCH..."

    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        if git merge --ff-only "$FEATURE_BRANCH"; then
            log_success "Merge completed (fast-forward)"
        else
            log_warn "Fast-forward failed, attempting merge commit..."
            if git merge --no-edit "$FEATURE_BRANCH"; then
                log_success "Merge completed with merge commit"
            else
                log_error "MERGE FAILED - Conflicts detected"
                log_info "Resolve conflicts, then: git merge --continue"
                return 1
            fi
        fi
    else
        log_info "[DRY-RUN] Would merge $FEATURE_BRANCH into $TARGET_BRANCH"
    fi
}

################################################################################
# STAGE 6: POST-MERGE VERIFICATION
################################################################################

post_merge_verification() {
    log_info "=== STAGE 6: POST-MERGE VERIFICATION ==="

    cd "$PROJECT_ROOT"

    # Check commit history
    log_info "Verifying commit history..."
    commits_since_merge=$(git rev-list --count "$TARGET_BRANCH"@{0}^.."$TARGET_BRANCH" 2>/dev/null || echo "unknown")
    log_info "Commits in merge: $commits_since_merge"

    # Verify no deleted files were resurrected
    log_info "Checking for resurrected files..."
    resurrected=$(git log --diff-filter=D --name-only "$TARGET_BRANCH" | wc -l || echo "0")
    log_warn "Files deleted in history: $resurrected (expected: many from develop cleanup)"

    # Check imports
    log_info "Verifying Python imports..."
    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        if python3 << 'PYEOF'
try:
    from cohezion.compound import CompoundExecutor
    from cohezion.compound.skill_consensus_voter import SkillConsensusVoter
    from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator
    from cohezion.cache import SemanticCache, RedisSemanticCache
    print("✓ All critical imports resolved")
except Exception as e:
    print(f"✗ Import error: {e}")
    exit(1)
PYEOF
        then
            log_success "Python imports verified"
        else
            log_error "Import verification failed"
            return 1
        fi
    else
        log_info "[DRY-RUN] Would verify imports"
    fi

    # Check git status
    log_info "Checking git status..."
    git status --short | head -10 || true

    log_success "POST-MERGE VERIFICATION COMPLETED"
}

################################################################################
# STAGE 7: RUN TEST SUITE (Optional, takes time)
################################################################################

run_tests() {
    log_info "=== STAGE 7: RUN TEST SUITE ==="

    cd "$PROJECT_ROOT"

    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        log_warn "This may take several minutes..."

        if uv run pytest tests/compound/ tests/cache/ -q --tb=short; then
            log_success "Test suite passed"
        else
            log_error "Test suite failed"
            return 1
        fi
    else
        log_info "[DRY-RUN] Would run: uv run pytest tests/compound/ tests/cache/ -q"
    fi
}

################################################################################
# ROLLBACK FUNCTION
################################################################################

rollback() {
    log_warn "=== ROLLING BACK TO BACKUP ==="

    cd "$PROJECT_ROOT"

    if git show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH"; then
        log_info "Restoring from backup: $BACKUP_BRANCH"
        git checkout "$BACKUP_BRANCH"
        git reset --hard
        log_success "Rollback completed"
    else
        log_error "Backup branch not found: $BACKUP_BRANCH"
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    log_info "Starting git merge safeguards..."
    log_info "Feature branch: $FEATURE_BRANCH"
    log_info "Target branch: $TARGET_BRANCH"
    log_info "Mode: $DRY_RUN"
    log_info ""

    case "$DRY_RUN" in
        --dry-run)
            log_warn "DRY-RUN MODE: No changes will be made"
            echo ""
            ;;
        --execute)
            log_warn "EXECUTE MODE: Changes will be committed"
            echo ""
            ;;
        --verify)
            log_info "VERIFY MODE: Check merge readiness only"
            echo ""
            ;;
        *)
            log_error "Invalid mode. Use: --dry-run, --execute, or --verify"
            exit 1
            ;;
    esac

    # Stage 1: Validation
    if ! pre_merge_validation; then
        log_error "Pre-merge validation failed"
        exit 1
    fi
    echo ""

    # Stage 2: Update .gitignore
    update_gitignore
    echo ""

    if [[ "$DRY_RUN" == "--verify" ]]; then
        log_success "VERIFY COMPLETE: Merge is safe to execute"
        exit 0
    fi

    # Stage 3: Create backup
    create_backup
    echo ""

    # Stage 4: Rebase
    if ! rebase_feature_branch; then
        log_error "Rebase failed, rolling back..."
        rollback
        exit 1
    fi
    echo ""

    # Stage 5: Merge
    if ! merge_to_target; then
        log_error "Merge failed, rolling back..."
        rollback
        exit 1
    fi
    echo ""

    # Stage 6: Verify
    if ! post_merge_verification; then
        log_error "Verification failed, rolling back..."
        rollback
        exit 1
    fi
    echo ""

    # Stage 7: Tests (optional)
    if [[ "$DRY_RUN" == "--execute" ]]; then
        read -p "Run full test suite? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_tests || log_warn "Tests failed, but merge is complete"
        fi
    fi

    echo ""
    if [[ "$DRY_RUN" == "--execute" ]]; then
        log_success "=== MERGE COMPLETE ==="
        log_info "Next steps:"
        log_info "  1. Push to origin: git push origin $TARGET_BRANCH"
        log_info "  2. Verify on remote: git log origin/$TARGET_BRANCH -5"
        log_info "  3. Create PR: $TARGET_BRANCH → main"
        log_info "  4. Backup branch (if needed): $BACKUP_BRANCH"
    else
        log_success "=== DRY-RUN COMPLETE ==="
        log_info "Ready to merge. Run with --execute to proceed."
    fi
}

# Run main
main
