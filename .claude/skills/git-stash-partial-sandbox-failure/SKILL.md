---
name: git-stash-partial-sandbox-failure
description: |
  Fix for silent partial working-tree revert when `git stash` runs inside the
  Claude Code bwrap sandbox on a repo with read-only paths (e.g. .claude/).
  Symptoms: stash IS created (stash@{0} exists), but affected files silently
  revert to HEAD while others stay modified. `git stash pop` is then blocked by
  unrelated local changes in other files. Cascade: all tests that relied on the
  reverted files fail with symbol-not-found / attribute errors.
  Use when: (1) `git stash` exits non-zero citing "unable to unlink ... Read-only
  file system", (2) `git stash list` shows a new stash but `git status` shows
  partial revert, (3) tests fail on symbols you JUST added.
author: Claude Code
version: 1.0.0
---

# Git Stash Partial Failure in Claude Code Sandbox

## Problem

`git stash` fails mid-operation because `.claude/` (or another sandbox-denied
path) is bind-mounted read-only inside bwrap. The stash object IS written to the
object store, but the working tree is only partially reset — some modified files
revert to HEAD silently, others don't.

```
error: unable to unlink old '.claude/scheduled_tasks.lock': Read-only file system
```

`git stash pop` is then also blocked if any OTHER file has local changes that
conflict with what the stash would apply.

## Context / Trigger Conditions

- Claude Code running under bwrap sandbox (Linux)
- Repo contains paths in the sandbox's `denyWithinAllow` list (e.g. `.claude/`)
- You ran `git stash` to test a "before/after" state
- Stash list shows `stash@{0}` but tests fail on symbols you added this session

## Diagnosis

```bash
# 1. Confirm partial state: stash created but tree not clean
git stash list                # shows stash@{0}
git status                    # should be clean if stash worked; partial revert if not

# 2. Find which symbols are missing from reverted files
grep -n "def band_for_node\|VaultNeuronWriter\|CLRQualityGate" \
  src/cohezion/inference/task_classifier.py \
  src/cohezion/compound/autonomous_loop/coordinator.py \
  src/cohezion/compound/post_execution.py
# Missing symbols = file reverted to HEAD
```

## Solution

### Option A — Re-apply edits manually (safest)

1. Identify which files reverted using `grep` for added symbols (above)
2. Re-apply each edit with the Edit tool
3. Do NOT attempt `git stash pop` if unrelated files have local changes — it will conflict

### Option B — Drop the orphaned stash

```bash
git stash drop stash@{0}    # clear the partial stash once you've re-applied manually
```

### Option C — Avoid stash entirely for before/after testing

Use a temp branch instead:
```bash
git stash is BANNED for before/after state tests in the sandbox.
Instead: check current behavior directly, or create a test-only branch.
```

## Prevention

**Never use `git stash` for "undo" or "before/after" state inspection inside the sandbox.**

If you need to test what code looked like before your changes:
- `git show HEAD:path/to/file` — read the old version without touching working tree
- `git diff HEAD -- path/to/file` — see exactly what changed

The sandbox's read-only bind mounts make `git stash` unreliable. Prefer non-destructive inspection.

## Verification

After re-applying edits:
```bash
# Verify symbols are back
grep -c "def band_for_node" src/cohezion/inference/task_classifier.py   # expect 1
grep -c "VaultNeuronWriter" src/cohezion/compound/autonomous_loop/coordinator.py  # expect >= 1

# Run affected tests
uv run pytest tests/learning/ tests/compound/test_loop_coordinator.py -q
```
