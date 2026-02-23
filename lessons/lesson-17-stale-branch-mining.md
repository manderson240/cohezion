---
title: Stale Branch Mining: Old Branches Contain Valuable Abandoned Work
date: 2026-02-23
severity: MEDIUM
category: git
tags: [git, branches, knowledge-recovery, archaeology]
status: validated
---

# Lesson: Stale Branch Mining: Old Branches Contain Valuable Abandoned Work

## Context

Feature branches and session branches that were never merged often contain valuable work: failed experiments with informative error traces, partial implementations with working sub-components, and design explorations.

## Core Learning

**Before starting new work, mine stale branches for prior art. Check for abandoned implementations that can be resurrected.**

### Pattern
```bash
# List stale branches sorted by last commit
git for-each-ref --sort=-committerdate refs/heads/ \
  --format='%(refname:short) %(committerdate:relative)'

# Diff to extract code
git diff main...feature/old-attempt -- src/relevant_module.py

# Cherry-pick valuable commits
git cherry-pick abc1234
```

## Recommendations

### Do
- Run stale branch audit at the start of new feature work
- Extract passing tests from abandoned branches even if implementation was abandoned

### Don't
- Delete stale branches without reviewing them first

## Related Concepts

- [[compound-engineering]] - Prior work compounds forward, even failed attempts

## Validation

**Discovered**: Feb 2026 during repository archaeology
**Status**: Validated -- recovered usable code from multiple stale branches
