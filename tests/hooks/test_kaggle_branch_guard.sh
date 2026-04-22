#!/bin/sh
# Integration test for scripts/hooks/kaggle_branch_guard.sh.
#
# Runs the guard against synthetic git repos under a temp dir. Each test case
# builds a minimal repo, stages specific files, sets the branch, then invokes
# the guard and asserts the exit code + stderr.
#
# Usage (from repo root):
#   sh tests/hooks/test_kaggle_branch_guard.sh
#
# Exit 0 = all tests pass; exit 1 = at least one failure.

set -eu

GUARD="$(git rev-parse --show-toplevel)/scripts/hooks/kaggle_branch_guard.sh"
if [ ! -x "$GUARD" ]; then
    chmod +x "$GUARD"
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helper: set up a fresh repo with some staged files on a named branch
# ---------------------------------------------------------------------------
make_repo() {
    local name="$1"
    local branch="$2"
    shift 2
    local dir="$TMPDIR/$name"
    mkdir -p "$dir"
    cd "$dir"
    git init -q
    git checkout -q -b "$branch" 2>/dev/null || true
    git config user.email test@example.com
    git config user.name test
    # Seed an initial commit so HEAD resolves
    echo "seed" > .seed
    git add .seed
    git commit -q -m "seed"
    # Create + stage the requested files
    for f in "$@"; do
        mkdir -p "$(dirname "$f")"
        echo "content" > "$f"
        git add "$f"
    done
}

assert_exit() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [ "$expected" = "$actual" ]; then
        printf '  PASS %s (exit=%s)\n' "$name" "$actual"
        PASS=$((PASS + 1))
    else
        printf '  FAIL %s: expected exit=%s, got %s\n' "$name" "$expected" "$actual"
        FAIL=$((FAIL + 1))
    fi
}

run_guard() {
    # Runs the guard in the current cwd, returns its exit code via echoed "RC=<n>"
    rc=0
    "$GUARD" 2>/dev/null || rc=$?
    echo "$rc"
}

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

echo "[test-kaggle-branch-guard]"

# 1. On main/session-oom branch with Kaggle file staged → BLOCKED (exit 1)
make_repo t1 main src/cohezion/competition/neurogolf/solver.py
rc=$(run_guard)
assert_exit "t1: neurogolf file on main branch blocks" 1 "$rc"

# 2. On kaggle/agi-golf branch with the same file → ALLOWED (exit 0)
make_repo t2 kaggle/agi-golf src/cohezion/competition/neurogolf/solver.py
rc=$(run_guard)
assert_exit "t2: neurogolf file on kaggle/agi-golf allowed" 0 "$rc"

# 3. On main with non-Kaggle file → ALLOWED
make_repo t3 main src/cohezion/compound/executor.py
rc=$(run_guard)
assert_exit "t3: non-kaggle file on main allowed" 0 "$rc"

# 4. On main with arc_agi_3 file → BLOCKED
make_repo t4 main src/cohezion/competition/arc_agi_3/experiential_agent.py
rc=$(run_guard)
assert_exit "t4: arc_agi_3 on main blocks" 1 "$rc"

# 5. On main with nemotron filename pattern (even outside competition/) → BLOCKED
make_repo t5 main scripts/drive_nemotron_helper.py
rc=$(run_guard)
assert_exit "t5: nemotron filename pattern blocks on main" 1 "$rc"

# 6. On main with kaggle_submission filename pattern → BLOCKED
make_repo t6 main scripts/kaggle_submission_v2.py
rc=$(run_guard)
assert_exit "t6: kaggle_submission pattern blocks on main" 1 "$rc"

# 7. KAGGLE_GUARD_DISABLE=1 bypasses the guard
make_repo t7 main src/cohezion/competition/neurogolf/bypass_test.py
rc=0
KAGGLE_GUARD_DISABLE=1 "$GUARD" 2>/dev/null || rc=$?
assert_exit "t7: KAGGLE_GUARD_DISABLE=1 bypasses guard" 0 "$rc"

# 8. Empty staged set → ALLOWED (merge/amend case)
make_repo t8 main README.md
git reset -q HEAD README.md  # unstage
rc=$(run_guard)
assert_exit "t8: empty staged set allowed (merge case)" 0 "$rc"

# 9. Mixed commit: kaggle + non-kaggle → BLOCKED (any Kaggle file triggers)
make_repo t9 main src/cohezion/competition/neurogolf/x.py src/cohezion/compound/y.py
rc=$(run_guard)
assert_exit "t9: mixed kaggle+non-kaggle on main blocks" 1 "$rc"

# 10. kaggle/nemotron-june branch → ALLOWED
make_repo t10 kaggle/nemotron-june src/cohezion/competition/arc_prize_paper_track/score_draft.py
rc=$(run_guard)
assert_exit "t10: arc_prize_paper_track on kaggle/nemotron-june allowed" 0 "$rc"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
printf '[test-kaggle-branch-guard] %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
