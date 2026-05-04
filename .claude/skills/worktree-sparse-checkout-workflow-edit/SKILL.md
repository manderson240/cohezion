---
name: worktree-sparse-checkout-workflow-edit
description: |
  Fix for "file not found" errors when trying to edit .github/workflows/ or other
  non-source directories in a git sparse checkout worktree. Use when: (1) ls shows
  .github directory missing but git ls-files .github/ returns files, (2) Read tool
  returns "file does not exist" for a file that git tracks, (3) a worktree was created
  with sparse checkout enabled covering only src/, tests/, docs/, scripts/, (4) you
  need to edit CI workflows, repo config, or other non-source files from a worktree.
author: Claude Code
version: 1.0.0
---

# Worktree Sparse Checkout: Adding .github/ for Workflow Editing

## Problem

A git worktree exists with sparse checkout enabled. Attempting to read or edit
`.github/workflows/*.yml` fails — the directory doesn't exist on the filesystem —
even though `git ls-files .github/` returns results.

```
ls .github/    →  "No such file or directory"
git ls-files .github/  →  .github/CODEOWNERS  .github/workflows/ci.yml ...
```

## Root Cause

Sparse checkout materializes only a subset of the repository on disk. Files exist
in the git index (tracked) but are not checked out to the filesystem. The sparse
checkout configuration controls which paths appear:

```bash
git sparse-checkout list
# config  docs  research  scripts  src  tests
# .github is NOT in this list → missing from filesystem
```

`git ls-files` queries the git index (always complete); `ls` queries the filesystem
(only sparse paths). They will disagree in sparse checkouts.

## Fix

Add the missing path to sparse checkout:

```bash
git sparse-checkout add .github
```

Verify it worked:
```bash
ls .github/workflows/   # should now show files
```

To see what's currently included:
```bash
git sparse-checkout list
```

To add multiple paths at once:
```bash
git sparse-checkout add .github Makefile pyproject.toml
```

## Scope Note

`git sparse-checkout add` is **additive** — it preserves existing paths and adds
new ones. It does NOT remove previously included paths.

## Checking Before Editing

When starting work in a worktree, quickly verify all the paths you'll need are
materialized:

```bash
# Check if critical dirs exist
ls .github/workflows/ src/ tests/ 2>&1 | grep "No such" && echo "SPARSE CHECKOUT ISSUE"
```

## Common Paths Often Missing from Source-Focused Worktrees

| Path | Contains |
|------|---------|
| `.github/` | CI workflows, issue templates, CODEOWNERS |
| `Makefile` | Build targets (may be in root, usually included) |
| `pyproject.toml` | Python project config (often included) |
| `docker/` | Docker config |
| `.agent/` | Agent/AI config files |

## Verification

After adding the path:
```bash
git sparse-checkout list   # confirms path is included
ls .github/workflows/      # confirms files are materialized
```
