---
title: Git Stash Branch Switch Hazard: Stashes Have No Branch Affinity
date: 2026-02-23
severity: MEDIUM
category: git
tags: [git, stash, branch-switching, workflow]
status: validated
---

# Lesson: Git Stash Branch Switch Hazard: Stashes Have No Branch Affinity

## Context

Git stash is global -- stashed changes from one branch are available when checking out another branch. Applying a stash on the wrong branch can silently apply code to an unintended branch.

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

## Validation

**Discovered**: Feb 2026 in multi-branch development sessions
**Status**: Validated
