---
name: git-status-snapshot-branch-mismatch
description: |
  Fix for trusting the session-start gitStatus over actual git state.
  Use when: (1) git push fails with "no upstream branch", (2) git commit
  lands on unexpected branch, (3) gitStatus shows branch X but git commands
  behave as if on branch Y. Root cause: gitStatus is a snapshot from session
  start — actual working directory may be a different worktree or branch.
---

# git Status Snapshot / Branch Mismatch

## Problem

The session-start `gitStatus` system reminder shows branch `feat/something`,
but `git push` fails with:

```
fatal: The current branch challenge-luma-cqq4mojz has no upstream branch.
```

Or commits appear on a different branch than expected.

## Root Cause

The `gitStatus` system reminder is a **snapshot taken at session start** and
never updates. If the working directory is a git worktree or the branch changed
after the snapshot was taken, the snapshot is stale.

The session reminder even says: _"Note that this status is a snapshot in time,
and will not update during the conversation."_

## Solution

**Always verify the actual branch before committing or pushing:**

```bash
# Step 1: Check actual branch (not the gitStatus snapshot)
git branch --show-current

# Step 2: Check remote tracking
git status  # shows "Your branch is ahead of 'origin/...' by N commits"
            # OR "no upstream" if push needs --set-upstream

# Step 3: Push accordingly
git push                              # if upstream already set
git push --set-upstream origin <branch>  # if no upstream
```

## When Gitignored Files Show as Modified

A related gotcha: files in `.gitignore` still show as `M` (modified) in
`git status --short` if they were previously force-added (`git add -f`).

```bash
# Before staging everything, check .gitignore patterns:
git check-ignore -v cache/swarm/  # confirms if path is ignored

# Never re-add gitignored files — skip them in git add commands
# The M marker means "tracked but gitignored content changed"
```

## Verification

```bash
git branch --show-current   # Actual current branch
git log --oneline -3        # Confirm commits landed on right branch
git status                  # Check upstream tracking status
```

## Example (this session)

Session gitStatus showed: `Current branch: feat/compound-elegant-simplification`

Actual branch (confirmed via `git branch --show-current`): `challenge-luma-cqq4mojz`

This was a worktree — the main repo was on the feat branch, but the active
worktree was on the challenge branch. The snapshot reflected the main repo's
state, not the worktree's.

Fix: `git push --set-upstream origin challenge-luma-cqq4mojz`

## References

- CLAUDE.md rules: `large-commit-protocol.md`
- `cz worktree status --json` — shows active worktree info when using cz CLI
