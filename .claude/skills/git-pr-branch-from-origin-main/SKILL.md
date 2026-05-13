---
name: git-pr-branch-from-origin-main
description: |
  Fix for PRs that show "CONFLICTING" on GitHub or carry 60+ unexpected commits
  because the branch was created from local main instead of origin/main. Use when:
  (1) a freshly-pushed PR shows CONFLICTING despite no code conflicts,
  (2) `git log origin/main..HEAD` shows far more commits than expected (60+),
  (3) cherry-picked commits include local-only "autoresearch" or experimental commits
  that were never pushed, (4) a branch created with `git checkout -b foo main` picks
  up local commits that aren't on GitHub's main.
author: Claude Code
version: 1.0.0
---

# Git: Base PR branches on origin/main, not local main

## Problem

A PR shows **CONFLICTING** on GitHub immediately after being pushed, even though the
branch had no conflicts when cherry-picked locally. Or `git log origin/main..HEAD`
shows 50-70 commits when only 1 was expected.

## Root Cause

Local `main` and `origin/main` can diverge significantly:

```
origin/main: A - B - C - D (4 commits)
local main:  A - B - C - D - E1 - E2 - ... - E62 (66 commits, 62 local-only)
```

When the local machine runs a long-lived autoresearch or autonomous loop, it commits
experimental results to local `main` without pushing. These never appear on GitHub.

```bash
git checkout -b fix/my-patch main   # ← takes ALL 66 commits as history
```

The branch now carries 62 commits unknown to GitHub. When pushed, GitHub sees a branch
62+ commits ahead of its `main` → marks the PR as CONFLICTING (merge divergence).

## Fix

**Always use `origin/main` explicitly when creating branches for PRs:**

```bash
# WRONG — picks up local-only commits
git checkout -b fix/my-patch main

# CORRECT — clean base from GitHub's main
git fetch origin
git checkout -b fix/my-patch origin/main
```

## Detection

Before pushing, verify only your intended commits are on the branch:

```bash
git log --oneline origin/main..HEAD   # should show exactly N commits (your work only)
```

If you see 10× more commits than expected, the branch is contaminated. Recover by
creating a fresh branch:

```bash
git cherry-pick <your-commit-sha>   # save your commit hash first
git checkout -b fix/my-patch-v2 origin/main
git cherry-pick <your-commit-sha>   # re-apply on the clean base
git push -u origin fix/my-patch-v2
```

## Why GitHub shows CONFLICTING

GitHub's "CONFLICTING" status means the PR branch cannot be auto-merged into base.
This happens when:
1. **Actual code conflicts** — same lines changed in both branches
2. **Branch divergence** — the merge base is too far back; GitHub can't calculate a
   clean merge diff

Case 2 (divergence) looks identical to case 1 in the GitHub UI. The diagnostic is
`git log origin/main..HEAD | wc -l` — if it's 10-100× higher than expected, it's
divergence, not a code conflict.

## Force-push recovery

If the PR is already open with the contaminated branch:

```bash
git fetch origin
git checkout fix/my-patch-contaminated
git reset --hard origin/main             # reset to GitHub's main
git cherry-pick <your-commit-sha>        # re-apply your work
git push --force-with-lease origin fix/my-patch-contaminated
```

Then re-check: `gh pr view <number> --json mergeable`

## Verification

```bash
git log --oneline origin/main..HEAD   # exactly your commits, nothing else
gh pr view <number> --json mergeable  # should show "MERGEABLE"
```
