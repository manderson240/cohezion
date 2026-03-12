---
title: "GC corruption root cause — entire/ auto-commits and submodule conflicts"
date: "2026-03-05"
status: complete
tags: [experiment, git, debugging]
aspect: thinker
neural:
  activation: 0.287
  stage: embryo
  cluster: experiments
---

# GC Corruption Root Cause — entire/ Auto-Commits and Submodule Conflicts

## Hypothesis

Git GC corruption (170+ bad objects) was caused by automatic commits in the `entire/` directory conflicting with submodule state, creating unreachable objects that `git gc` couldn't properly handle.

## Method

Investigated pack file integrity with `git fsck`, traced bad objects to commits involving the `entire/` directory auto-commit pattern, and examined submodule configuration conflicts.

## Results

Confirmed root cause: auto-commits containing large files in `entire/` created orphaned pack file entries when submodule references became inconsistent. The 3GB data file in history compounded the corruption severity.

## Learnings

- Auto-commit patterns must exclude large binary files and submodule directories
- Git GC corruption from orphaned objects compounds over time — early detection is critical
- See [[lesson-13-8-6m-file-incident]] for the 8.6MB file incident that first revealed this pattern
- See [[lesson-14-cleanup-is-multi-pass]] for the multi-pass cleanup strategy
- Related severity assessment: [[2026-03-05-gc-corruption-severity-170-bad-objects-across-all-pack-files-3gb-data-file-in-hi]]
