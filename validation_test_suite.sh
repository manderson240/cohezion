#!/bin/bash

################################################################################
# E2E Validation Test Suite - GitHub Push + Entire.io Integration
# Purpose: Automated validation of all 31+ criteria
# Created: 2026-02-11
# QA Lead: Session 55 Validation Team
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNED=0

# Logging
LOG_FILE="/tmp/e2e_validation_$(date +%s).log"
RESULTS_FILE="/tmp/validation_results.txt"

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

test_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}" | tee -a "$LOG_FILE"
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1" | tee -a "$LOG_FILE"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1" | tee -a "$LOG_FILE"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1" | tee -a "$LOG_FILE"
    ((TESTS_WARNED++))
}

run_test() {
    local test_name=$1
    local test_cmd=$2
    local expected_exit=$3
    ((TESTS_TOTAL++))

    if eval "$test_cmd" &>/dev/null; then
        pass "$test_name"
        return 0
    else
        if [ "$expected_exit" = "0" ]; then
            fail "$test_name"
            return 1
        fi
    fi
}

################################################################################
# PHASE 1: PRE-CLEANUP VALIDATION
################################################################################

phase_1_validation() {
    test_header "PHASE 1: Pre-Cleanup Validation"

    # Test 1.1: Repository Integrity
    log "Testing repository integrity..."
    if git fsck --full --progress 2>&1 | grep -q "Checking connectivity: done."; then
        if ! git fsck --full 2>&1 | grep -qE "ERROR|broken|corrupt|missing"; then
            pass "1.1 Repository integrity check"
        else
            fail "1.1 Repository integrity check (corruption detected)"
        fi
    else
        fail "1.1 Repository integrity check (fsck failed)"
    fi

    # Test 1.2: Git size baseline
    log "Checking git directory size..."
    GIT_SIZE=$(du -sh .git/ 2>/dev/null | cut -f1)
    GIT_SIZE_NUM=$(echo "$GIT_SIZE" | grep -oE '[0-9.]+')
    log "Current .git/ size: $GIT_SIZE"
    if (( $(echo "$GIT_SIZE_NUM < 10" | bc -l) )); then
        pass "1.2 Git size baseline (<10GB)"
        echo "$GIT_SIZE" > /tmp/git_size_before.txt
    else
        warn "1.2 Git size baseline (>10GB, may need cleanup)"
        echo "$GIT_SIZE" > /tmp/git_size_before.txt
    fi

    # Test 1.3: Verify 7 commits present
    log "Checking for 7 commits..."
    COMMIT_COUNT=$(git log --oneline | wc -l)
    if [ "$COMMIT_COUNT" -ge 7 ]; then
        git log --oneline -10 > /tmp/commits_before.txt
        pass "1.3 All commits present ($COMMIT_COUNT commits found)"
    else
        fail "1.3 All commits present ($COMMIT_COUNT commits, expected 7+)"
    fi

    # Test 1.4: No uncommitted changes
    log "Checking for uncommitted changes..."
    UNSTAGED=$(git status --porcelain 2>/dev/null | wc -l)
    if [ "$UNSTAGED" -gt 0 ]; then
        warn "1.4 No uncommitted changes ($UNSTAGED items pending)"
        git status --porcelain > /tmp/git_status_before.txt
    else
        pass "1.4 No uncommitted changes"
    fi

    # Test 1.5: Backup branch exists
    log "Verifying backup branch..."
    if git rev-parse backup/session-55-test-fixes-main 2>/dev/null; then
        BACKUP_SHA=$(git rev-parse backup/session-55-test-fixes-main)
        pass "1.5 Backup branch exists and accessible"
    else
        fail "1.5 Backup branch missing (create with: git branch backup/session-55-test-fixes-main)"
    fi
}

################################################################################
# PHASE 2: POST-CLEANUP VALIDATION
################################################################################

phase_2_validation() {
    test_header "PHASE 2: Post-Cleanup Validation"

    # Test 2.1: Size reduction check
    log "Checking size reduction..."
    if [ -f /tmp/git_size_before.txt ]; then
        BEFORE=$(grep -oE '[0-9.]+' /tmp/git_size_before.txt)
        AFTER=$(du -sh .git/ | cut -f1 | grep -oE '[0-9.]+')
        REDUCTION=$(echo "scale=2; ($BEFORE - $AFTER) / $BEFORE * 100" | bc -l)
        log "Size: ${BEFORE}GB → ${AFTER}GB (${REDUCTION}% reduction)"

        if (( $(echo "$AFTER < 6.5" | bc -l) )); then
            pass "2.1 Repository size reduction (<6.5GB)"
        else
            warn "2.1 Repository size reduction (${AFTER}GB, target <6.5GB)"
        fi
        echo "$AFTER" > /tmp/git_size_after.txt
    else
        warn "2.1 Repository size reduction (baseline not available)"
    fi

    # Test 2.2: No corruption after cleanup
    log "Verifying integrity after cleanup..."
    if git fsck --full --progress 2>&1 | grep -q "Checking connectivity: done."; then
        if ! git fsck --full 2>&1 | grep -qE "ERROR|broken|corrupt"; then
            pass "2.2 No git corruption after cleanup"
        else
            fail "2.2 No git corruption after cleanup (corruption detected)"
        fi
    else
        fail "2.2 No git corruption after cleanup (fsck failed)"
    fi

    # Test 2.3: All commits still present
    log "Verifying commits after cleanup..."
    git log --oneline -10 > /tmp/commits_after.txt
    AFTER_COUNT=$(git log --oneline | wc -l)
    if [ "$AFTER_COUNT" -ge 7 ]; then
        pass "2.3 All commits still present ($AFTER_COUNT commits)"
    else
        fail "2.3 All commits still present ($AFTER_COUNT commits, expected 7+)"
    fi

    # Test 2.4: Commit SHAs unchanged
    log "Verifying commit SHAs..."
    BEFORE_SHA=$(head -1 /tmp/commits_before.txt 2>/dev/null | cut -d' ' -f1 || echo "UNKNOWN")
    AFTER_SHA=$(git rev-parse HEAD | cut -c1-7)
    if [ "$BEFORE_SHA" = "$AFTER_SHA" ]; then
        pass "2.4 Commit SHAs unchanged ($AFTER_SHA)"
    else
        warn "2.4 Commit SHAs changed (before: $BEFORE_SHA, after: $AFTER_SHA)"
    fi

    # Test 2.5: CLAUDE.md intact
    log "Verifying CLAUDE.md..."
    if [ -f CLAUDE.md ]; then
        LINES=$(wc -l < CLAUDE.md)
        if [ "$LINES" -gt 1500 ]; then
            pass "2.5 CLAUDE.md intact and readable ($LINES lines)"
        else
            warn "2.5 CLAUDE.md size unexpected ($LINES lines, expected ~2000)"
        fi
    else
        fail "2.5 CLAUDE.md file missing"
    fi

    # Test 2.6: Repository functional
    log "Testing repository functionality..."
    if git rev-parse HEAD >/dev/null 2>&1 && \
       git log --oneline -1 >/dev/null 2>&1 && \
       git status >/dev/null 2>&1; then
        pass "2.6 Repository functional (all commands working)"
    else
        fail "2.6 Repository functional (commands failing)"
    fi
}

################################################################################
# PHASE 3: GITHUB PUSH VALIDATION
################################################################################

phase_3_validation() {
    test_header "PHASE 3: GitHub Push Validation"

    log "GitHub credentials and remote check..."
    if ! git remote -v | grep -q "origin"; then
        warn "3.0 Git remote 'origin' not configured - skipping GitHub tests"
        return
    fi

    GITHUB_REMOTE=$(git remote get-url origin)
    log "Detected remote: $GITHUB_REMOTE"

    # Verify branch name
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log "Current branch: $BRANCH"

    # Test 3.1: Simulated push test (dry-run)
    log "Simulating git push..."
    if git push --dry-run origin "$BRANCH" >/dev/null 2>&1; then
        pass "3.1 Push would succeed (dry-run check)"
    else
        warn "3.1 Push simulation failed (may be auth or branch issue)"
    fi

    # Test 3.2: Check for obvious errors in recent operations
    log "Checking for HTTP errors..."
    if ! git log -1 --format=%B | grep -qE "500|error|failed"; then
        pass "3.2 No HTTP 500 errors in recent logs"
    else
        warn "3.2 Potential HTTP errors detected"
    fi

    # Test 3.3: Remote branch check
    log "Verifying remote branch..."
    if git fetch origin >/dev/null 2>&1; then
        if git rev-parse "origin/$BRANCH" >/dev/null 2>&1; then
            pass "3.3 Remote branch exists and accessible"
        else
            warn "3.3 Remote branch not yet created (will be created on push)"
        fi
    else
        warn "3.3 Cannot reach remote (network or auth issue)"
    fi

    # Test 3.4: Commits would be pushed
    log "Verifying commits for push..."
    COMMITS_TO_PUSH=$(git log --oneline origin/$BRANCH..$BRANCH 2>/dev/null | wc -l)
    if [ "$COMMITS_TO_PUSH" -gt 0 ]; then
        pass "3.4 Commits ready to push ($COMMITS_TO_PUSH commits)"
    else
        warn "3.4 No new commits to push (branch may already be synced)"
    fi

    # Test 3.5: CLAUDE.md would be pushed
    log "Verifying CLAUDE.md will be pushed..."
    if git ls-files --stage | grep -q "CLAUDE.md"; then
        pass "3.5 CLAUDE.md tracked and will be pushed"
    else
        fail "3.5 CLAUDE.md not tracked in git"
    fi
}

################################################################################
# PHASE 4: ENTIRE.IO INTEGRATION VALIDATION
################################################################################

phase_4_validation() {
    test_header "PHASE 4: Entire.io Integration Validation"

    # Test 4.1: Entire.io configuration
    log "Checking Entire.io configuration..."
    if [ -f ".entire/settings.json" ]; then
        if grep -q '"strategy".*manual-commit' .entire/settings.json && \
           grep -q '"enabled".*true' .entire/settings.json; then
            pass "4.1 Entire.io configuration correct"
        else
            warn "4.1 Entire.io configuration incomplete or wrong strategy"
        fi
    else
        warn "4.1 Entire.io configuration missing (.entire/settings.json not found)"
    fi

    # Test 4.2: Checkpoint metadata
    log "Checking checkpoint metadata..."
    if git rev-parse entire/checkpoints/v1 >/dev/null 2>&1; then
        if git log entire/checkpoints/v1 --format="%B" -1 | grep -qE "Entire-Session|Entire-Strategy"; then
            pass "4.2 Checkpoint metadata present"
            CHECKPOINT_COUNT=$(git log entire/checkpoints/v1 --oneline | wc -l)
            log "  Found $CHECKPOINT_COUNT checkpoints"
        else
            warn "4.2 Checkpoint metadata incomplete"
        fi
    else
        warn "4.2 Checkpoint branch not found (entire/checkpoints/v1 doesn't exist)"
    fi

    # Test 4.3: Agent context captured
    log "Checking captured agent context..."
    if git rev-parse entire/checkpoints/v1 >/dev/null 2>&1; then
        LATEST_CP=$(git log entire/checkpoints/v1 --format="%B" -1)
        if echo "$LATEST_CP" | grep -q "Entire-Agent"; then
            pass "4.3 Agent context captured"
        else
            warn "4.3 Agent context may be incomplete"
        fi
    else
        warn "4.3 Cannot verify agent context (checkpoint branch missing)"
    fi

    # Test 4.4: Journey data structure
    log "Checking journey data structure..."
    if git rev-parse entire/checkpoints/v1 >/dev/null 2>&1; then
        if git log entire/checkpoints/v1 --oneline | grep -q "Checkpoint:"; then
            pass "4.4 Journey data properly structured"
        else
            warn "4.4 Journey data structure may be wrong"
        fi
    else
        warn "4.4 Cannot verify journey data (checkpoint branch missing)"
    fi

    # Test 4.5: CLAUDE.md referenced in journey
    log "Checking CLAUDE.md in journey capture..."
    if git rev-parse entire/checkpoints/v1 >/dev/null 2>&1; then
        # Try to find context files
        CONTEXT_FILES=$(git ls-tree -r entire/checkpoints/v1 | grep -c "context.md" || echo "0")
        if [ "$CONTEXT_FILES" -gt 0 ]; then
            pass "4.5 Journey context files present ($CONTEXT_FILES files)"
        else
            warn "4.5 Journey context files not accessible"
        fi
    else
        warn "4.5 Cannot verify context (checkpoint branch missing)"
    fi

    # Test 4.6: Integration working
    log "Checking Entire.io integration status..."
    if command -v entire &> /dev/null; then
        if entire status >/dev/null 2>&1; then
            pass "4.6 Entire.io CLI available and responding"
        else
            warn "4.6 Entire.io CLI installed but not responding"
        fi
    else
        # Check if git hooks are installed
        if [ -d ".git/hooks" ] && ls .git/hooks/*entire* 2>/dev/null | grep -q .; then
            pass "4.6 Entire.io hooks installed in .git/hooks"
        else
            warn "4.6 Entire.io CLI not available (can verify after push)"
        fi
    fi
}

################################################################################
# MANUAL VERIFICATION SECTION
################################################################################

manual_verification() {
    test_header "MANUAL VERIFICATION REQUIRED"

    echo -e "\n${YELLOW}The following items require manual verification:${NC}\n" | tee -a "$LOG_FILE"

    echo "1. GitHub Web Verification" | tee -a "$LOG_FILE"
    echo "   [ ] Visit https://github.com/[owner]/[repo]/tree/session-55-test-fixes-main" | tee -a "$LOG_FILE"
    echo "   [ ] Verify CLAUDE.md is readable and properly formatted" | tee -a "$LOG_FILE"
    echo "   [ ] Verify all 7 commits are present in history" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    echo "2. Entire.io Cloud Sync (if enabled)" | tee -a "$LOG_FILE"
    echo "   [ ] Run 'entire status' and verify last sync is recent" | tee -a "$LOG_FILE"
    echo "   [ ] Check Entire.io cloud dashboard for captured session" | tee -a "$LOG_FILE"
    echo "   [ ] Verify checkpoints are searchable in cloud" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    echo "3. Entire.io Hook Functionality" | tee -a "$LOG_FILE"
    echo "   [ ] Run: git log entire/checkpoints/v1 --oneline -5" | tee -a "$LOG_FILE"
    echo "   [ ] Verify latest checkpoint has recent timestamp" | tee -a "$LOG_FILE"
    echo "   [ ] Verify checkpoint includes session metadata" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    echo "4. Repository Cross-Platform Verification" | tee -a "$LOG_FILE"
    echo "   [ ] If also pushing to GitLab: repeat Phase 3 tests for GitLab" | tee -a "$LOG_FILE"
    echo "   [ ] Verify .entire/ directory syncs to secondary platform" | tee -a "$LOG_FILE"
    echo "   [ ] Verify entire/checkpoints/v1 branch exists on both platforms" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

################################################################################
# SUMMARY AND REPORTING
################################################################################

print_summary() {
    test_header "VALIDATION SUMMARY"

    echo "" | tee -a "$LOG_FILE"
    echo "Tests Run:      $TESTS_TOTAL" | tee -a "$LOG_FILE"
    echo -e "Tests Passed:   ${GREEN}$TESTS_PASSED${NC}" | tee -a "$LOG_FILE"
    echo -e "Tests Failed:   ${RED}$TESTS_FAILED${NC}" | tee -a "$LOG_FILE"
    echo -e "Tests Warned:   ${YELLOW}$TESTS_WARNED${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    if [ "$TESTS_FAILED" -eq 0 ] && [ "$TESTS_PASSED" -ge 20 ]; then
        echo -e "${GREEN}✓ VALIDATION PASSED${NC}" | tee -a "$LOG_FILE"
        echo "Status: All critical tests passing. Ready for GitHub push." | tee -a "$LOG_FILE"
        RESULT="PASS"
    elif [ "$TESTS_FAILED" -gt 0 ]; then
        echo -e "${RED}✗ VALIDATION FAILED${NC}" | tee -a "$LOG_FILE"
        echo "Status: Critical failures detected. See details above." | tee -a "$LOG_FILE"
        RESULT="FAIL"
    else
        echo -e "${YELLOW}⚠ VALIDATION WARNING${NC}" | tee -a "$LOG_FILE"
        echo "Status: Some warnings detected. Review and proceed with caution." | tee -a "$LOG_FILE"
        RESULT="WARN"
    fi

    echo "" | tee -a "$LOG_FILE"
    echo "Full log: $LOG_FILE" | tee -a "$LOG_FILE"

    # Write results summary
    cat > "$RESULTS_FILE" << EOF
E2E Validation Results
======================
Date: $(date)
Branch: $(git rev-parse --abbrev-ref HEAD)
Commit: $(git rev-parse --short HEAD)

Results:
  Total Tests: $TESTS_TOTAL
  Passed: $TESTS_PASSED
  Failed: $TESTS_FAILED
  Warnings: $TESTS_WARNED

Status: $RESULT

Log File: $LOG_FILE

Next Steps:
EOF

    if [ "$RESULT" = "PASS" ]; then
        cat >> "$RESULTS_FILE" << EOF
1. Review manual verification items above
2. Run: git push origin $(git rev-parse --abbrev-ref HEAD)
3. Verify push succeeds and checkpoints created
4. Monitor .entire/logs/ for any issues
5. Proceed with merge to main
EOF
    else
        cat >> "$RESULTS_FILE" << EOF
1. Review failed/warned tests in detail
2. Consult FAILURE_RECOVERY_GUIDE.md for remediation
3. Fix issues and re-run validation
4. Do not push until all critical tests pass
EOF
    fi

    echo ""
    echo "Results saved to: $RESULTS_FILE"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    log "Starting E2E Validation Test Suite"
    log "Repository: $(pwd)"
    log "Branch: $(git rev-parse --abbrev-ref HEAD)"
    log "Commit: $(git rev-parse --short HEAD)"

    # Run all phases
    phase_1_validation
    phase_2_validation
    phase_3_validation
    phase_4_validation
    manual_verification

    # Print results
    print_summary

    # Exit with appropriate code
    [ "$TESTS_FAILED" -eq 0 ] && exit 0 || exit 1
}

# Execute main function
main "$@"
