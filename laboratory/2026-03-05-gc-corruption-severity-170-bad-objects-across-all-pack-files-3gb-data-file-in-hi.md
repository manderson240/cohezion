---
title: "GC corruption severity — 170+ bad objects across all pack files, 3GB data file in history"
date: "2026-03-05"
status: complete
tags: [experiment, git, debugging]
aspect: thinker
neural:
  activation: 0.287
  stage: embryo
  cluster: experiments
---

# GC Corruption Severity — 170+ Bad Objects, 3GB Data File

## Hypothesis

The severity of git GC corruption (170+ bad objects across all pack files) was amplified by a 3GB data file accidentally committed to the repository history, making standard `git gc` and `git repack` operations unreliable.

## Method

Ran `git fsck --full` to enumerate all bad objects. Traced the 3GB file through `git log --diff-filter=A --all -- '**/large-file*'` to identify when and where it was introduced. Assessed whether `git filter-branch` or BFG Repo-Cleaner could safely excise it.

## Results

Confirmed 170+ bad objects distributed across multiple pack files. The 3GB data file inflated clone times and GC operations. The corruption was too widespread for simple object replacement — required a clean re-clone strategy.

## Learnings

- Large binary files in git history are permanent unless actively removed with history rewriting tools
- Object corruption compounds: each bad object can prevent GC from processing the pack file containing it
- Prevention is cheaper than cure: `.gitignore` enforcement and pre-commit hooks are essential
- See [[lesson-13-8-6m-file-incident]] for the original incident
- Root cause analysis: [[2026-03-05-gc-corruption-root-cause-entire-auto-commits-and-submodule-conflicts]]
