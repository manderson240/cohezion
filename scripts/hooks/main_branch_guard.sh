#!/bin/sh
# Pre-commit guard — block direct commits to main/master.
#
# Context: commits to main skip all branch-based review gates, make
# rebasing harder for collaborators, and defeat the branch-protection
# model that allows per-feature worktree isolation. This is the
# complement to kaggle_branch_guard.sh — that guard keeps Kaggle work
# off main; this guard keeps ALL production code off main (use a
# feature branch, then squash-merge via cz worktree sync or PR).
#
# Bypass options:
#   MAIN_GUARD_DISABLE=1 git commit ...    explicit operator override
#
# Exit codes:
#   0 = allowed to commit
#   1 = blocked (message on stderr)

set -eu

# Operator override — use sparingly (documented bypasses only)
if [ "${MAIN_GUARD_DISABLE:-}" = "1" ]; then
    exit 0
fi

branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")
case "$branch" in
    main|master)
        printf '\n[main-branch-guard] BLOCKED: direct commit to "%s"\n' "$branch" >&2
        printf '\nFeature branches are required for all production code changes:\n' >&2
        printf '  git checkout -b feat/<description>\n' >&2
        printf '  git checkout -b fix/<description>\n' >&2
        printf '  git checkout -b refactor/<description>\n' >&2
        printf '\nFor the uncommitted adaptive-gate work (fleet.py + test):\n' >&2
        printf '  git checkout -b feat/adaptive-routing-gate\n' >&2
        printf '\nFor other uncommitted changes on main:\n' >&2
        printf '  git stash && git checkout -b feat/<name> && git stash pop\n' >&2
        printf '\nEscape hatch (operator override, use sparingly):\n' >&2
        printf '  MAIN_GUARD_DISABLE=1 git commit ...\n' >&2
        printf '\nSee ~/.claude/rules/git-operations.md for branch policy.\n' >&2
        exit 1
        ;;
esac
exit 0
