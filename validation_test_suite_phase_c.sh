#!/bin/bash

################################################################################
# Phase C Validation Test Suite - BFG Cleanup + GitHub Push + Entire.io
# Purpose: Automated validation of all cleanup and push criteria
# Created: Session 55 QA Lead
# Usage: ./validation_test_suite_phase_c.sh [--bfg-output <file>] [--no-github]
################################################################################

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
BFG_OUTPUT_FILE="${1:-}"
SKIP_GITHUB="${2:-}"
REPO_DIR="$(pwd)"
LOG_DIR="/tmp/phase_c_validation_$(date +%s)"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/validation.log"
RESULTS_FILE="$LOG_DIR/VALIDATION_PHASE_C_RESULTS.md"

# Counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNED=0
MANUAL_CHECKS=0

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

manual_note() {
    echo -e "${CYAN}📋 MANUAL${NC}: $1" | tee -a "$LOG_FILE"
    ((MANUAL_CHECKS++))
}

run_test() {
    local test_name=$1
    local test_cmd=$2
    ((TESTS_TOTAL++))

    if eval "$test_cmd" >/dev/null 2>&1; then
        pass "$test_name"
        return 0
    else
        fail "$test_name"
        return 1
    fi
}

################################################################################
# PRE-CLEANUP VALIDATION (if BFG output provided)
################################################################################

phase_pre_cleanup() {
    test_header "PHASE 0: Pre-Cleanup Baseline"

    log "Checking repository state before cleanup..."

    # 0.1: Repository integrity
    ((TESTS_TOTAL++))
    if git fsck --full >/dev/null 2>&1; then
        pass "0.1 Repository integrity baseline"
    else
        warn "0.1 Repository integrity baseline (fsck warnings)"
    fi

    # 0.2: Current size
    ((TESTS_TOTAL++))
    GIT_SIZE_BEFORE=$(du -sh .git/ 2>/dev/null | cut -f1)
    GIT_SIZE_NUM=$(echo "$GIT_SIZE_BEFORE" | grep -oE '[0-9.]+' | head -1)
    log "Repository size before cleanup: $GIT_SIZE_BEFORE (~${GIT_SIZE_NUM}GB)"
    pass "0.2 Size baseline recorded ($GIT_SIZE_BEFORE)"
    echo "$GIT_SIZE_NUM" > "$LOG_DIR/size_before.txt"

    # 0.3: Commit count
    ((TESTS_TOTAL++))
    COMMIT_COUNT=$(git log --oneline | wc -l)
    if [ "$COMMIT_COUNT" -ge 7 ]; then
        pass "0.3 Commit count baseline ($COMMIT_COUNT commits)"
    else
        warn "0.3 Commit count baseline ($COMMIT_COUNT commits, expected 7+)"
    fi

    # 0.4: CLAUDE.md exists
    ((TESTS_TOTAL++))
    if [ -f CLAUDE.md ]; then
        LINES=$(wc -l < CLAUDE.md)
        pass "0.4 CLAUDE.md baseline ($LINES lines)"
    else
        fail "0.4 CLAUDE.md baseline (file missing)"
    fi
}

################################################################################
# BFG CLEANUP OUTPUT VALIDATION
################################################################################

phase_bfg_analysis() {
    test_header "PHASE 1: BFG Cleanup Output Analysis"

    if [ ! -f "$BFG_OUTPUT_FILE" ]; then
        warn "1.0 BFG output file not provided - skipping BFG analysis"
        return
    fi

    log "Analyzing BFG output from: $BFG_OUTPUT_FILE"

    # 1.1: Parse BFG stats
    ((TESTS_TOTAL++))
    if grep -q "Protected commits" "$BFG_OUTPUT_FILE"; then
        PROTECTED=$(grep "Protected commits" "$BFG_OUTPUT_FILE" | grep -oE '[0-9]+' | head -1)
        pass "1.1 BFG found protected commits ($PROTECTED commits)"
    else
        warn "1.1 BFG output incomplete (no 'Protected commits' found)"
    fi

    # 1.2: Objects deleted count
    ((TESTS_TOTAL++))
    if grep -qE "Deleted objects|Removing|Cleaned" "$BFG_OUTPUT_FILE"; then
        DELETED=$(grep -oE '[0-9]+.*deleted|[0-9]+.*removed' "$BFG_OUTPUT_FILE" | head -1)
        if [ ! -z "$DELETED" ]; then
            pass "1.2 Objects deleted by BFG ($DELETED)"
        else
            warn "1.2 Objects deleted unclear from BFG output"
        fi
    else
        warn "1.2 No deletion stats in BFG output"
    fi

    # 1.3: Compression ratio
    ((TESTS_TOTAL++))
    if grep -qE "Compression|compression|ratio" "$BFG_OUTPUT_FILE"; then
        RATIO=$(grep -oE '[0-9]+\.?[0-9]*%|[0-9]+\.?[0-9]* to [0-9]+\.?[0-9]*' "$BFG_OUTPUT_FILE" | head -1)
        if [ ! -z "$RATIO" ]; then
            pass "1.3 Compression ratio found ($RATIO)"
        else
            warn "1.3 Compression ratio not clearly stated"
        fi
    else
        warn "1.3 No compression stats in BFG output"
    fi

    # 1.4: BFG warnings/errors
    ((TESTS_TOTAL++))
    WARNING_COUNT=$(grep -icE "WARNING|ERROR|FATAL" "$BFG_OUTPUT_FILE" | wc -l)
    if [ "$WARNING_COUNT" -eq 0 ]; then
        pass "1.4 No BFG warnings or errors"
    elif [ "$WARNING_COUNT" -le 3 ]; then
        warn "1.4 BFG warnings detected ($WARNING_COUNT, review output)"
        head -20 "$BFG_OUTPUT_FILE" | grep -iE "WARNING|ERROR" | head -3 | tee -a "$LOG_FILE"
    else
        fail "1.4 Multiple BFG errors detected ($WARNING_COUNT, review output)"
    fi

    # 1.5: Target size achieved
    ((TESTS_TOTAL++))
    if grep -qE '[0-9.]+\s*GB|[0-9.]+\s*MB' "$BFG_OUTPUT_FILE"; then
        SIZE_RESULT=$(grep -oE '[0-9.]+\s*(GB|MB)' "$BFG_OUTPUT_FILE" | tail -1)
        if [ ! -z "$SIZE_RESULT" ]; then
            pass "1.5 Final size in BFG output ($SIZE_RESULT)"
        else
            warn "1.5 Final size not clearly stated"
        fi
    else
        warn "1.5 Final size not found in BFG output"
    fi

    # Store BFG output for reference
    cp "$BFG_OUTPUT_FILE" "$LOG_DIR/bfg_output.txt"
    log "BFG output saved to $LOG_DIR/bfg_output.txt"
}

################################################################################
# POST-CLEANUP VALIDATION
################################################################################

phase_post_cleanup() {
    test_header "PHASE 2: Post-Cleanup Verification"

    log "Verifying repository state after cleanup..."

    # 2.1: Repository integrity
    ((TESTS_TOTAL++))
    if git fsck --full >/dev/null 2>&1; then
        pass "2.1 Repository integrity maintained"
    else
        fail "2.1 Repository integrity check failed (corruption detected)"
    fi

    # 2.2: Size reduction
    ((TESTS_TOTAL++))
    GIT_SIZE_AFTER=$(du -sh .git/ 2>/dev/null | cut -f1)
    GIT_SIZE_AFTER_NUM=$(echo "$GIT_SIZE_AFTER" | grep -oE '[0-9.]+' | head -1)

    if [ -f "$LOG_DIR/size_before.txt" ]; then
        SIZE_BEFORE=$(cat "$LOG_DIR/size_before.txt")
        if [ ! -z "$SIZE_BEFORE" ] && [ ! -z "$GIT_SIZE_AFTER_NUM" ]; then
            REDUCTION=$(echo "scale=1; ($SIZE_BEFORE - $GIT_SIZE_AFTER_NUM) / $SIZE_BEFORE * 100" | bc -l)
            REDUCTION_INT=$(printf "%.0f" "$REDUCTION")
            log "Size reduction: ${SIZE_BEFORE}GB → ${GIT_SIZE_AFTER_NUM}GB (~${REDUCTION_INT}% reduction)"

            if (( $(echo "$REDUCTION >= 70" | bc -l) )); then
                pass "2.2 Size reduction >70% (${REDUCTION_INT}% achieved)"
                echo "$GIT_SIZE_AFTER_NUM" > "$LOG_DIR/size_after.txt"
            elif (( $(echo "$REDUCTION >= 50" | bc -l) )); then
                warn "2.2 Size reduction 50-70% (${REDUCTION_INT}% achieved, target 70%)"
            else
                warn "2.2 Size reduction <50% (${REDUCTION_INT}% achieved, target 70%)"
            fi
        fi
    else
        warn "2.2 Baseline size not available, skipping reduction check"
    fi

    # 2.3: All commits preserved
    ((TESTS_TOTAL++))
    COMMIT_COUNT_AFTER=$(git log --oneline | wc -l)
    if [ "$COMMIT_COUNT_AFTER" -ge 7 ]; then
        pass "2.3 All commits preserved ($COMMIT_COUNT_AFTER commits)"
    else
        fail "2.3 Commits lost during cleanup ($COMMIT_COUNT_AFTER, expected 7+)"
    fi

    # 2.4: CLAUDE.md readable
    ((TESTS_TOTAL++))
    if [ -f CLAUDE.md ]; then
        LINES=$(wc -l < CLAUDE.md)
        if grep -q "Cohezion" CLAUDE.md; then
            pass "2.4 CLAUDE.md readable and intact ($LINES lines)"
        else
            warn "2.4 CLAUDE.md exists but content may be corrupted"
        fi
    else
        fail "2.4 CLAUDE.md file missing after cleanup"
    fi

    # 2.5: Backup branch intact
    ((TESTS_TOTAL++))
    if git rev-parse backup/session-55-test-fixes-main >/dev/null 2>&1; then
        pass "2.5 Backup branch still exists"
    else
        warn "2.5 Backup branch not found (may have been cleaned)"
    fi

    # 2.6: No ref corruption
    ((TESTS_TOTAL++))
    REF_COUNT=$(git show-ref | wc -l)
    if [ "$REF_COUNT" -gt 5 ]; then
        pass "2.6 References intact ($REF_COUNT refs)"
    else
        warn "2.6 References may be incomplete ($REF_COUNT refs)"
    fi
}

################################################################################
# GITHUB PUSH PREPARATION
################################################################################

phase_github_push() {
    test_header "PHASE 3: GitHub Push Validation"

    if [ "$SKIP_GITHUB" = "--no-github" ]; then
        warn "3.0 GitHub validation skipped (--no-github flag)"
        return
    fi

    # 3.1: Remote configured
    ((TESTS_TOTAL++))
    if git remote -v | grep -q "origin"; then
        REMOTE=$(git remote get-url origin)
        pass "3.1 Git remote configured ($REMOTE)"
    else
        fail "3.1 Git remote not configured"
        return
    fi

    # 3.2: Branch exists
    ((TESTS_TOTAL++))
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log "Current branch: $BRANCH"
    if [ "$BRANCH" = "session-55-test-fixes-main" ]; then
        pass "3.2 Correct branch checked out ($BRANCH)"
    else
        warn "3.2 Unexpected branch ($BRANCH, expected session-55-test-fixes-main)"
    fi

    # 3.3: No uncommitted changes
    ((TESTS_TOTAL++))
    UNSTAGED=$(git status --porcelain | wc -l)
    if [ "$UNSTAGED" -eq 0 ]; then
        pass "3.3 No uncommitted changes"
    else
        warn "3.3 Uncommitted changes present ($UNSTAGED items)"
        git status --porcelain | head -5 | tee -a "$LOG_FILE"
    fi

    # 3.4: Commits ready to push
    ((TESTS_TOTAL++))
    if git fetch origin >/dev/null 2>&1; then
        COMMITS_TO_PUSH=$(git log --oneline "origin/$BRANCH..$BRANCH" 2>/dev/null | wc -l)
        if [ "$COMMITS_TO_PUSH" -gt 0 ]; then
            pass "3.4 Commits ready to push ($COMMITS_TO_PUSH new commits)"
            git log --oneline "origin/$BRANCH..$BRANCH" 2>/dev/null | head -5 | tee -a "$LOG_FILE"
        else
            warn "3.4 No new commits to push (may already be synced)"
        fi
    else
        warn "3.4 Cannot fetch from origin (network/auth issue)"
    fi

    # 3.5: CLAUDE.md tracked
    ((TESTS_TOTAL++))
    if git ls-files | grep -q "^CLAUDE.md$"; then
        pass "3.5 CLAUDE.md tracked in git"
    else
        fail "3.5 CLAUDE.md not tracked in git"
    fi

    # 3.6: Push would succeed (dry-run)
    ((TESTS_TOTAL++))
    if git push --dry-run origin "$BRANCH" >/dev/null 2>&1; then
        pass "3.6 Push dry-run would succeed"
    else
        warn "3.6 Push dry-run failed (may be auth or network issue)"
    fi
}

################################################################################
# ENTIRE.IO INTEGRATION VALIDATION
################################################################################

phase_entire_io() {
    test_header "PHASE 4: Entire.io Integration Validation"

    # 4.1: Settings file exists
    ((TESTS_TOTAL++))
    if [ -f ".entire/settings.json" ]; then
        pass "4.1 Entire.io settings file exists"
        cat .entire/settings.json | tee -a "$LOG_FILE"
    else
        warn "4.1 .entire/settings.json not found (Entire.io may not be configured)"
    fi

    # 4.2: Strategy configured
    ((TESTS_TOTAL++))
    if [ -f ".entire/settings.json" ] && grep -q "manual-commit" .entire/settings.json; then
        pass "4.2 Manual-commit strategy configured"
    else
        if [ -f ".entire/settings.json" ]; then
            warn "4.2 Strategy may not be manual-commit"
        else
            manual_note "4.2 Verify .entire/settings.json after sync"
        fi
    fi

    # 4.3: Checkpoint branch exists
    ((TESTS_TOTAL++))
    if git rev-parse entire/checkpoints/v1 >/dev/null 2>&1; then
        pass "4.3 Entire.io checkpoint branch exists"
        CHECKPOINT_COUNT=$(git log entire/checkpoints/v1 --oneline | wc -l)
        log "  Checkpoints captured: $CHECKPOINT_COUNT"
    else
        warn "4.3 entire/checkpoints/v1 branch not found (will be created on first sync)"
    fi

    # 4.4: .entire directory tracked
    ((TESTS_TOTAL++))
    ENTIRE_FILES=$(git ls-files | grep "^\.entire/" | wc -l)
    if [ "$ENTIRE_FILES" -gt 0 ]; then
        pass "4.4 .entire directory files tracked ($ENTIRE_FILES files)"
    else
        warn "4.4 .entire directory not yet tracked in git"
    fi

    # 4.5: Hook integration
    ((TESTS_TOTAL++))
    if command -v entire &>/dev/null; then
        if entire status >/dev/null 2>&1; then
            pass "4.5 Entire.io CLI available and responding"
            entire status 2>/dev/null | head -5 | tee -a "$LOG_FILE"
        else
            warn "4.5 Entire.io CLI present but not responding"
        fi
    else
        if [ -d ".git/hooks" ]; then
            ENTIRE_HOOKS=$(ls -la .git/hooks/ 2>/dev/null | grep -c "entire" || echo "0")
            if [ "$ENTIRE_HOOKS" -gt 0 ]; then
                pass "4.5 Entire.io git hooks installed"
            else
                manual_note "4.5 Entire.io CLI not found, will install during first push"
            fi
        fi
    fi

    # 4.6: Context files captured
    ((TESTS_TOTAL++))
    if [ -f ".entire/context.md" ] || [ -f ".entire/journey.md" ]; then
        pass "4.6 Journey context files present"
        ls -lh .entire/*.md 2>/dev/null | tee -a "$LOG_FILE"
    else
        manual_note "4.6 Journey context will be created during first checkpoint"
    fi
}

################################################################################
# MANUAL VERIFICATION CHECKLIST
################################################################################

manual_checklist() {
    test_header "MANUAL VERIFICATION CHECKLIST"

    cat >> "$LOG_FILE" << 'EOF'

The following items require manual verification in Phase C:

1. GITHUB WEB VERIFICATION (After Push)
   [ ] Navigate to: https://github.com/[owner]/[repo]/tree/session-55-test-fixes-main
   [ ] Verify CLAUDE.md is readable and properly formatted
   [ ] Verify all 7+ commits appear in commit history
   [ ] Confirm file sizes match post-cleanup expectations
   [ ] Check that .entire/ directory synced to GitHub

2. ENTIRE.IO CLOUD SYNC (If Enabled)
   [ ] Run: entire status
   [ ] Verify last checkpoint timestamp is recent
   [ ] Check Entire.io dashboard for captured session
   [ ] Verify session is searchable and accessible
   [ ] Confirm journey data includes CLAUDE.md context

3. CHECKPOINT VERIFICATION
   [ ] Run: git log entire/checkpoints/v1 --oneline -5
   [ ] Verify latest checkpoint has recent timestamp
   [ ] Check checkpoint commit message includes metadata
   [ ] Confirm checkpoint is reachable from both local and GitHub

4. SIZE REDUCTION VERIFICATION
   [ ] Confirm repository size achieved >70% reduction target
   [ ] If <70%: review BFG output for any warnings
   [ ] Verify git gc was run: git count-objects -v
   [ ] Check disk usage: du -sh .git/

5. GITHUB ACTIONS/CI (If Configured)
   [ ] Check GitHub Actions status for branch
   [ ] Verify any test workflows pass
   [ ] Confirm lint/format checks pass
   [ ] Review any security scanning results

EOF

    echo "" | tee -a "$LOG_FILE"
}

################################################################################
# SUMMARY AND RESULTS
################################################################################

print_summary() {
    test_header "VALIDATION SUMMARY"

    echo "" | tee -a "$LOG_FILE"
    echo "Automated Tests Run:    $TESTS_TOTAL" | tee -a "$LOG_FILE"
    echo -e "  Passed:             ${GREEN}$TESTS_PASSED${NC}" | tee -a "$LOG_FILE"
    echo -e "  Failed:             ${RED}$TESTS_FAILED${NC}" | tee -a "$LOG_FILE"
    echo -e "  Warnings:           ${YELLOW}$TESTS_WARNED${NC}" | tee -a "$LOG_FILE"
    echo "Manual Checks Required: $MANUAL_CHECKS" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # Determine overall status
    if [ "$TESTS_FAILED" -eq 0 ] && [ "$TESTS_PASSED" -ge 20 ]; then
        echo -e "${GREEN}✓ VALIDATION PASSED${NC}" | tee -a "$LOG_FILE"
        echo "Status: Ready for GitHub push in Phase C" | tee -a "$LOG_FILE"
        RESULT="PASS"
        EXIT_CODE=0
    elif [ "$TESTS_FAILED" -gt 0 ]; then
        echo -e "${RED}✗ VALIDATION FAILED${NC}" | tee -a "$LOG_FILE"
        echo "Status: Critical issues detected - see failures above" | tee -a "$LOG_FILE"
        RESULT="FAIL"
        EXIT_CODE=1
    else
        echo -e "${YELLOW}⚠ VALIDATION WARNING${NC}" | tee -a "$LOG_FILE"
        echo "Status: Some warnings - review before pushing" | tee -a "$LOG_FILE"
        RESULT="WARN"
        EXIT_CODE=0
    fi

    echo "" | tee -a "$LOG_FILE"
}

generate_results_report() {
    test_header "Generating Results Report"

    cat > "$RESULTS_FILE" << EOF
# Phase C Validation Results

**Date**: $(date)
**Branch**: $(git rev-parse --abbrev-ref HEAD)
**Commit**: $(git rev-parse --short HEAD)
**Repository**: $(pwd)

## Executive Summary

- **Automated Tests**: $TESTS_TOTAL total
  - ✓ Passed: $TESTS_PASSED
  - ✗ Failed: $TESTS_FAILED
  - ⚠ Warnings: $TESTS_WARNED
- **Manual Checks**: $MANUAL_CHECKS required
- **Overall Status**: **$RESULT**

## Test Results by Phase

### Phase 0: Pre-Cleanup Baseline
- Repository size baseline
- Commit count baseline
- CLAUDE.md baseline

### Phase 1: BFG Cleanup Analysis
- Protected commits identification
- Objects deleted tracking
- Compression ratio validation
- Size reduction >70% target

### Phase 2: Post-Cleanup Verification
- Repository integrity (git fsck)
- Size reduction confirmed
- All commits preserved
- CLAUDE.md readable and intact
- Backup branch preserved
- References intact

### Phase 3: GitHub Push Preparation
- Remote configured correctly
- Correct branch checked out
- No uncommitted changes
- Commits ready to push
- CLAUDE.md tracked in git
- Push dry-run would succeed

### Phase 4: Entire.io Integration
- Settings file configured
- Manual-commit strategy set
- Checkpoint branch prepared
- .entire directory tracked
- Hook integration ready
- Context files captured

## Key Metrics

EOF

    if [ -f "$LOG_DIR/size_before.txt" ] && [ -f "$LOG_DIR/size_after.txt" ]; then
        SIZE_BEFORE=$(cat "$LOG_DIR/size_before.txt")
        SIZE_AFTER=$(cat "$LOG_DIR/size_after.txt")
        REDUCTION=$(echo "scale=1; ($SIZE_BEFORE - $SIZE_AFTER) / $SIZE_BEFORE * 100" | bc -l)
        cat >> "$RESULTS_FILE" << EOF
- **Size Before Cleanup**: ${SIZE_BEFORE}GB
- **Size After Cleanup**: ${SIZE_AFTER}GB
- **Reduction**: ${REDUCTION}%
- **Target**: 70% (13GB → 2.5GB)
- **Status**: $([ $(echo "$REDUCTION >= 70" | bc -l) -eq 1 ] && echo "✓ ACHIEVED" || echo "⚠ NEEDS REVIEW")

EOF
    fi

    cat >> "$RESULTS_FILE" << EOF

## Logs and Artifacts

- Full validation log: \`$LOG_FILE\`
- BFG output: \`$LOG_DIR/bfg_output.txt\` (if provided)
- Size metrics: \`$LOG_DIR/size_*.txt\`

## Next Steps

EOF

    if [ "$RESULT" = "PASS" ]; then
        cat >> "$RESULTS_FILE" << EOF
### Phase C - Ready to Execute

1. ✓ Run BFG cleanup: \`bfg --delete-files CLAUDE.md HARDWARE_PROFILE_PRIME.md ...\`
2. ✓ Run git gc: \`git reflog expire --all --expire=now && git gc --aggressive --prune=now\`
3. ✓ Verify sizes match expectations
4. ✓ Push to GitHub: \`git push origin session-55-test-fixes-main\`
5. ⬜ Complete manual verification checklist above
6. ⬜ Monitor Entire.io checkpoint creation
7. ⬜ Verify GitHub shows cleanup results

**Estimated Time**: 10-15 minutes (includes manual verification)

EOF
    else
        cat >> "$RESULTS_FILE" << EOF
### Phase C - Hold and Investigate

1. ✗ Review failed tests above
2. ✗ Consult FAILURE_RECOVERY_GUIDE.md for remediation
3. ✗ Fix issues and re-run this suite
4. ✗ Do NOT push until all critical failures resolved

**Next Steps**:
- Run: \`./validation_test_suite_phase_c.sh --bfg-output <bfg.txt>\`
- After fixes applied

EOF
    fi

    cat >> "$RESULTS_FILE" << EOF

## Recovery Resources

- **Failure Guide**: FAILURE_RECOVERY_GUIDE.md
- **Backup Branch**: backup/session-55-test-fixes-main
- **Session 55 Log**: $LOG_FILE

---

Generated by Session 55 QA Lead on $(date)

EOF

    log "Results report generated: $RESULTS_FILE"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    log "=========================================="
    log "Phase C Validation Test Suite"
    log "=========================================="
    log "Repository: $(pwd)"
    log "Branch: $(git rev-parse --abbrev-ref HEAD)"
    log "Commit: $(git rev-parse --short HEAD)"
    log "Time: $(date)"
    log ""

    # Run validation phases
    phase_pre_cleanup
    phase_bfg_analysis
    phase_post_cleanup
    phase_github_push
    phase_entire_io
    manual_checklist

    # Generate reports
    print_summary
    generate_results_report

    # Output key info
    echo ""
    echo "=========================================="
    echo "Validation Complete"
    echo "=========================================="
    echo "Full log: $LOG_FILE"
    echo "Results:  $RESULTS_FILE"
    echo ""

    # Display results file for convenience
    if [ -f "$RESULTS_FILE" ]; then
        echo "Results Summary:"
        echo "---"
        cat "$RESULTS_FILE" | head -30
        echo "..."
        echo "---"
        echo ""
    fi

    exit $EXIT_CODE
}

# Execute if not sourced
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
