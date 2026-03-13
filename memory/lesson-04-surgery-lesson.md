---
title: Surgical Code Changes: Modify Only What Is Required
date: 2026-02-23
severity: HIGH
category: coding
cost_of_forgetting: "Unintended regressions from scope creep; larger diffs that are harder to review and debug"
tags: [code-quality, minimal-changes, surgical-edits]
status: validated
aspect: knower
neural:
  activation: 0.71
  stage: growing
  synapse_in: 9
  synapse_out: 4
---

# Lesson: Surgical Code Changes: Modify Only What Is Required

## Context

During Cohezion development sessions, a recurring pattern emerged where agents (and developers) would fix a bug in a function and then "improve" surrounding code while they were in the file. These adjacent improvements -- variable renames, whitespace changes, import reordering, logic simplification -- were not part of the original task and were not covered by the task's test suite. Multiple regression incidents were traced back to these well-intentioned side-changes.

## Problem

Scope creep during implementation creates three categories of risk:

1. **Untested changes**: The task's tests verify the fix, not the surrounding cleanup. A renamed variable might break a consumer that is not tested by the current suite.
2. **Harder reviews**: A diff with 5 lines of fix and 50 lines of cleanup is harder to review than a 5-line diff. The reviewer cannot easily distinguish intentional changes from incidental ones.
3. **Regression attribution**: When a regression is discovered, the large diff makes it harder to identify which change caused the problem. Was it the fix or the cleanup?

In one specific incident, a bug fix to a session management function included a "cleanup" of the return type annotation. This change propagated to 3 consuming modules that had type-checking errors, requiring a second fix session.

## Core Learning

**Make the smallest possible change that satisfies the requirement. Resist all scope creep during implementation.**

### Why This Matters
- Each additional change is an additional failure vector
- Larger diffs are harder to review and reason about
- Cleanup changes are untested by the task's test suite

### Pattern
```
1. Read ONLY the code needed for the fix
2. Identify the minimal change set
3. Make exactly those changes
4. Verify the specific fix with tests
5. Stop -- don't clean up, don't improve
```

## Solution

The discipline is now to treat improvements as separate work items:

1. **Fix the bug**: Make the minimum change. Verify with tests.
2. **File improvements separately**: If you notice something worth improving, create a task for it -- do not do it now.
3. **Review diffs before committing**: Run `git diff` and verify that every changed line is part of the task. If any line is not, revert it.

This keeps diffs small, reviewable, and attributable.

## Prevention

- **Define scope before coding**: Know exactly which files and functions need to change before opening any file
- **Review your own diff**: Before committing, read `git diff` and ask "is every line necessary for this task?"
- **File improvements as tasks**: Use task management to capture improvement ideas without acting on them now
- **One commit, one purpose**: Every commit should be describable in a single sentence

## Cost of Forgetting

- **Invisible regressions**: Side-changes break consumers that are not tested by the current task
- **Review difficulty**: Reviewers cannot distinguish fix from cleanup in large diffs
- **Regression attribution failure**: When something breaks, large diffs make root cause analysis harder
- **Compound risk**: In multi-session workflows, each broad change compounds the risk of unintended interactions

## Recommendations

### Do
- Define the fix scope before touching any code
- Make one change, verify it, then stop
- File improvements as separate tasks for later

### Don't
- "Improve while I'm here" -- creates invisible regressions
- Refactor surrounding code as part of a bug fix
- Touch files not required for the change

## Related Concepts

- [[compound-engineering]] - Surgical changes compound cleanly; broad changes create chaos
- [[concept-modularity]] - surgical changes respect module boundaries and don't expand scope unnecessarily
- [[lesson-08-import-graph]] - understanding the import graph helps define the true blast radius of any change
- [[adversarial-review]] - adversarial review of diffs catches unintentional scope creep

## Validation

**Discovered**: Feb 2026 across multiple regression incidents caused by scope creep
**Status**: Core Cohezion coding discipline -- now encoded in coding standards
