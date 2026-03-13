---
title: "Corrupt Tree Object Dumps"
date: "2026-03-05"
tags: [git, corruption, forensics, preservation]
aspect: doer
neural:
  activation: 0.52
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

## badTree Objects (empty filename — from entire/ auto-commits)

These trees have a space-prefixed ` _bmad-output` directory name and a file named `!`.
Created by Claude Code's `entire/` auto-commit mechanism.

### 2d7a315eea35d3e01af10ad900a3382f1a729fb9
- Branch: entire/a1b6988-15500c (deleted, was auto-snapshot)
- Contains: ` _bmad-output` (space prefix), `!`, .agent, .antigravity, .archived, .autonomy, .chief, .claude, .cohezion, .entire, .gemini, .github, .opencode

### 3acb81109998acb8cd5e7c24e8c31774163965f7
- Same branch, similar content but different .entire tree

### 86c126347bb0bddea120e3f94dc13bbf73896293
- Similar pattern, no .autonomy or .entire, has .vscode

### a570bbd388301f833a7a6412778abb002a53a864
- Same as above

## duplicateEntries Objects (from submodule/directory conflict)

### 0c66a852348b02602ab3d6c3afc1338de3ff5086
- Branch: fix/bmad-memory-physics-restore (deleted, patches preserved)
- Path: research/challenges/
- Conflict: `anthropic_challenge_original` exists as BOTH:
  - `160000 commit 5452f74b...` (submodule reference)
  - `040000 tree 73706...` (regular directory)
- This is a known git corruption pattern from converting submodules to directories

### 44987e9eadaa0bfc44d1f439ca250ddd99498874
- Root tree of a commit on fix/bmad-memory-physics-restore
- Standard repo root structure

### Other duplicate entry trees (cfb75c09, 1063fc19, bbe50f2d, 53ec02f9, b22766fb, 8d9a2e30, aafddb8d)
- Likely same submodule/directory conflict pattern at different commits

## Resolution Path

Since main is CLEAN and all corrupt objects are in local-only branches:
1. Fresh clone from GitHub (gets clean pack files)
2. Re-create worktrees from clean clone
3. Apply stashed work via patches
4. Local-only branch content preserved in /tmp/branch-preservation/
