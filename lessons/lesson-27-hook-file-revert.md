---
title: Hook File Revert: Failed Pre-Commit Hooks May Revert Staged Changes
date: 2026-02-23
severity: HIGH
category: git
tags: [pre-commit, hooks, git, staging, file-revert]
status: validated
---

# Lesson: Hook File Revert: Failed Pre-Commit Hooks May Revert Staged Changes

## Context

Pre-commit hooks that fail after partially modifying files can leave the working tree in an inconsistent state. Some hooks revert staged changes as a side effect of hook failure.

## Core Learning

**A failed pre-commit hook may revert your staged changes. Always check git diff --staged after a failed hook run.**

### Pattern
```bash
# After any hook failure
git status                    # Check overall state
git diff --staged             # Verify staged content still intact
git stash list                # Check if hook accidentally stashed
git reflog --all | head -5    # Check for any unexpected HEAD changes
```

## Recommendations

### Do
- Immediately run git diff --staged after any pre-commit hook failure
- Write hooks to be idempotent and non-destructive on failure

### Don't
- Assume hook failure means "nothing changed" in the repository
- Re-stage files without checking what was lost

## Related Concepts

- [[compound-engineering]] - Hook reliability is foundational to compound commit workflows

## Validation

**Discovered**: Feb 2026 in Cohezion development workflow
**Status**: Validated
