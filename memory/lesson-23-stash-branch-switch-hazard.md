---
title: Git Stash Branch Switch Hazard: Stashes Have No Branch Affinity
date: 2026-02-23
severity: MEDIUM
category: git
cost_of_forgetting: "Code applied to wrong branch silently; debugging why feature code appeared on main"
tags: [git, stash, branch-switching, workflow]
status: validated
aspect: knower
neural:
  activation: 0.433
  stage: growing
  cluster: lessons
---

# Lesson: Git Stash Branch Switch Hazard: Stashes Have No Branch Affinity

## Context

During multi-branch Cohezion development sessions in February 2026, a developer stashed work-in-progress on a feature branch, switched to `main` to review something, and then ran `git stash pop` on `main` instead of switching back to the feature branch first. The stashed changes -- feature-specific code -- were silently applied to `main` and nearly committed to the wrong branch.

## Problem

Git stash is a global stack with no branch affinity:

1. **Global scope**: Stashes are stored at the repository level, not per-branch. `git stash list` shows the same stashes regardless of which branch is checked out.
2. **Silent application**: `git stash pop` applies the top stash to the current branch without warning that the stash was created on a different branch.
3. **Unnamed stashes**: Without explicit messages, stashes are identified only by `stash@{0}`, `stash@{1}`, etc. -- giving no indication of which branch they belong to.
4. **Accumulated stashes**: Over multiple branch switches, the stash stack accumulates entries from different branches, making it easy to pop the wrong one.

## Core Learning

**Git stash has no branch affinity. Always verify current branch before git stash pop.**

### Pattern
```bash
# Safe stash workflow
git stash push -m "feature-x: WIP before switch"
git checkout main
# ... do work on main ...
git checkout feature-x
git stash list                  # Verify which stash belongs here
git stash pop stash@{0}         # Explicit index
```

## Solution

The safe stash workflow includes three disciplines:

1. **Named stashes**: Always use `git stash push -m "branch-name: description"` so the stash message identifies its origin
2. **Branch verification**: Run `git branch --show-current` before `git stash pop` to confirm you are on the correct branch
3. **Explicit stash index**: Use `git stash pop stash@{N}` with an explicit index after reviewing `git stash list`, rather than defaulting to `stash@{0}`

## Prevention

- **Name every stash**: Include the branch name and a brief description in the stash message
- **Verify before popping**: `git branch --show-current` before `git stash pop` -- always
- **Review stash list**: `git stash list` before popping to see all stashes and their messages
- **Consider worktrees instead**: For multi-branch work, git worktrees (see [[lesson-git-worktrees-multi-session-isolation]]) avoid the stash problem entirely by maintaining separate working directories

## Cost of Forgetting

- **Feature code on wrong branch**: Stash applied to `main` instead of `feature-x`
- **Accidental commits**: If the wrong-branch application is not caught, it gets committed
- **Debugging confusion**: "Where did this code come from?" when reviewing commits

## Recommendations

### Do
- Always name stashes with branch and context
- Verify current branch with git branch --show-current before git stash pop
- Use git stash list to review all stashes before applying

### Don't
- Use git stash pop without checking current branch
- Leave stashes unnamed (impossible to identify later)

## Related Concepts

- [[compound-engineering]] - Clean branch management enables reliable compound workflows
- [[lesson-git-worktrees-multi-session-isolation]] - worktrees eliminate the stash hazard by providing separate working directories per branch
- [[lesson-03-critical]] - stash pop to wrong branch is a critical operation that should be verified before execution

## Validation

**Discovered**: Feb 2026 in multi-branch development sessions
**Status**: Validated -- named stashes and branch verification now standard
