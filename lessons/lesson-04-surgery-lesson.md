---
title: Surgical Code Changes: Modify Only What Is Required
date: 2026-02-23
severity: HIGH
category: coding
tags: [code-quality, minimal-changes, surgical-edits]
status: validated
---

# Lesson: Surgical Code Changes: Modify Only What Is Required

## Context

When fixing bugs or implementing features, the temptation is to improve surrounding code or clean up while in the area. This scope creep introduces unintended regressions and makes diffs harder to review.

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

## Validation

**Status**: Core Cohezion coding discipline
