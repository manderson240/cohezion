---
name: gh-pr-diff-large-pr
description: |
  Fix for "406 Not Acceptable" error from `gh pr diff` on large PRs.
  Use when: (1) `gh pr diff <number>` returns HTTP 406, (2) PR has
  300+ changed files, (3) need file-level diff data from a big PR.
---

# gh pr diff 406 Error on Large PRs

## Problem

`gh pr diff 123` fails with HTTP 406 when the PR has more than ~300 changed files. GitHub's diff API enforces this limit on large changesets.

## Solution

Use the paginated files endpoint instead of the diff endpoint:

```bash
# Instead of:
gh pr diff 123  # ← fails with 406 on 300+ file PRs

# Use:
gh api repos/OWNER/REPO/pulls/123/files --paginate --jq '.[].filename'

# With status filter (no != operator — use positive select):
gh api repos/OWNER/REPO/pulls/123/files --paginate \
  --jq '[.[] | select(.additions > 0)] | .[].filename'
```

## jq Gotchas

The `!=` operator in `--jq` expressions gets escaped by bash in some contexts. Prefer positive `select()` expressions:

```bash
# ❌ May fail: bash escapes != in some contexts
--jq '[.[] | select(.status != "removed")]'

# ✅ Safe: positive filter
--jq '[.[] | select(.additions > 0 or .changes > 0)]'

# ✅ Also safe: pipe to separate jq
gh api ... --paginate | jq '[.[] | select(.status != "removed")]'
```

## Get Full PR Details When diff Fails

```bash
# Count files
gh api repos/OWNER/REPO/pulls/123/files --paginate --jq 'length'

# Files over 500 lines added
gh api repos/OWNER/REPO/pulls/123/files --paginate \
  --jq '[.[] | select(.additions > 500)] | .[].filename'

# PR metadata (title, body, state)
gh pr view 123 --json title,body,state,additions,deletions
```

## Verification

```bash
# Confirm file count exceeds the 300-file limit
gh pr view 123 --json files --jq '.files | length'
# If this also errors, use:
gh api repos/OWNER/REPO/pulls/123 --jq '.changed_files'
```

## References

- Confirmed on PR #36 in manderson240/cohezion (1714 files, 56 commits)
- GitHub API limit: 300 files per diff request
