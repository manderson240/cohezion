---
title: "GC Corruption Investigation & Resolution"
date: "2026-03-05"
tags: [git, corruption, gc, investigation]
aspect: doer
neural:
  activation: 0.51
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

## Problem

`git gc` fails with `fatal: empty filename in tree entry` and `fatal: failed to run repack`.
Auto-gc is blocked by gc.log file.

## Findings

13 corrupt tree objects found via `git fsck --full`:

### badTree (empty filename) — 4 trees
All on `entire/a1b6988-15500c` (auto-generated worktree snapshot from current session).
- 2d7a315eea35d3e01af10ad900a3382f1a729fb9
- 3acb81109998acb8cd5e7c24e8c31774163965f7
- 86c126347bb0bddea120e3f94dc13bbf73896293
- a570bbd388301f833a7a6412778abb002a53a864

### duplicateEntries — 9 trees
On `fix/bmad-memory-physics-restore` (disconnected history, track-c lineage):
- 0c66a852348b02602ab3d6c3afc1338de3ff5086
- 1063fc198a78c3e4fd817179e08dcb7efd1e6ac4
- 44987e9eadaa0bfc44d1f439ca250ddd99498874
- cfb75c09891bc3f40009c88ff5ded927ad2fdf1f

5 remaining are dangling (unreachable from any branch).

## Key Fact: main is CLEAN
`main` has zero corrupt objects. The corruption is entirely on local-only non-essential branches.

## Preservation Before Fix
- `fix/bmad-memory-physics-restore` unique commits (3) saved as patches to `/tmp/branch-preservation/bmad-memory-physics/`
- Patches contain: BMAD memory physics docs, BMAD slash commands restore, Strix Halo vLLM integration
- `entire/a1b6988-15500c` content is already in the merged PR #33

## Resolution
Delete the two local-only corrupt branch refs so `git gc` can run successfully.
The branches are NOT on remote. Content is preserved via patches and PR #33.
