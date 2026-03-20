---
title: "GC corruption root cause — entire/ auto-commits and submodule conflicts"
date: "2026-03-05"
status: complete
tags: [experiment, git, debugging]
aspect: thinker
neural:
  activation: 0.62
  stage: growing
  synapse_in: 2
  synapse_out: 3
---

# GC Corruption Root Cause — entire/ Auto-Commits and Submodule Conflicts

## Hypothesis

Git GC corruption (170+ bad objects) was caused by automatic commits in the `entire/` directory conflicting with submodule state, creating unreachable objects that `git gc` couldn't properly handle.

## Method

Investigated pack file integrity with `git fsck`, traced bad objects to commits involving the `entire/` directory auto-commit pattern, and examined submodule configuration conflicts.

## Results

Confirmed root cause: auto-commits containing large files in `entire/` created orphaned pack file entries when submodule references became inconsistent. The 3GB data file in history compounded the corruption severity.

## Detailed Root Cause Chain

The GC corruption traced through four linked events:

1. **Auto-commit script** included the `entire/` directory, which contained Entire.io checkpoint exports as large binary blobs (~500MB each).
2. **Submodule reference conflict**: the `entire/` directory was also registered as a git submodule in `.gitmodules`. Auto-committing its contents directly (not via submodule ref) created ambiguous object references.
3. **Pack file fragmentation**: `git gc --auto` ran during one of these auto-commits and partially compacted the pack files, leaving 170 orphaned objects that pointed to now-unreachable tree entries.
4. **3GB data file**: a historical commit had included a raw SurrealDB export (`vault.db` at 3.1GB). This file was removed from HEAD but remained in pack history, consuming space and making `git fsck` extremely slow (30+ minutes).

### Diagnosis Commands That Worked

```bash
# Find all bad objects
git fsck --full --no-progress 2>&1 | grep "^error" | wc -l  # → 170

# Trace a bad object to its commit
git log --all --find-object=<bad-sha> --oneline

# Identify the large file in history
git rev-list --all --objects | sort -k 2 | git cat-file --batch-check | sort -k3 -rn | head -5
```

## Learnings

- Auto-commit patterns must exclude large binary files and submodule directories — add explicit `git add --pathspec-from-file=<allowlist>` instead of `git add .`
- Git GC corruption from orphaned objects compounds over time — run `git fsck` weekly on repos with auto-commit patterns
- Submodule directories must never be committed directly as working-tree files; the `.gitmodules` presence makes git treat mixed-mode commits as invalid
- A single large file in git history (even if deleted from HEAD) causes persistent `git fsck` slowness — use `git filter-repo` or BFG to excise it from all pack files

## Related

- [[2026-03-05-gc-corruption-severity-170-bad-objects-across-all-pack-files-3gb-data-file-in-hi]] — the severity assessment note
- [[lesson-13-8-6m-file-incident]] — the 8.6MB file incident that first revealed this pattern
- [[lesson-14-cleanup-is-multi-pass]] — multi-pass cleanup strategy for git history corruption
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] — mandatory knowledge capture before running destructive git commands like `filter-repo`
