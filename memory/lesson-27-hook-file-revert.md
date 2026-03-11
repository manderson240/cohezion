---
title: Hook File Revert: Failed Pre-Commit Hooks May Revert Staged Changes
date: 2026-02-23
severity: HIGH
category: git
cost_of_forgetting: "Staged changes silently lost after hook failure; developer re-stages files without realizing content was reverted"
tags: [pre-commit, hooks, git, staging, file-revert]
status: validated
aspect: knower
neural:
  activation: 0.453
  stage: growing
  cluster: lessons
---

# Lesson: Hook File Revert: Failed Pre-Commit Hooks May Revert Staged Changes

## Context

During Cohezion development in February 2026, a developer ran `git commit` and the pre-commit hook failed (ruff found a linting error). After fixing the error and re-running `git commit`, the resulting commit was missing some of the originally staged changes. Investigation revealed that the failed hook had partially modified files, and the pre-commit framework's cleanup mechanism had reverted some staged changes as part of its failure recovery.

## Problem

Pre-commit hooks that modify files (ruff --fix, black, isort) interact with git's staging area in complex ways during failure:

1. **Partial modification**: The hook begins modifying files, then encounters an error and aborts. The working tree now contains partially-modified files.
2. **Cleanup revert**: Some pre-commit frameworks attempt to restore the working tree to its pre-hook state when a hook fails. This can revert not just the hook's changes but also the developer's staged changes if the framework cannot distinguish them.
3. **Silent loss**: The developer sees "hook failed" and focuses on fixing the hook error. They do not check whether their staged changes are still intact. After fixing the error and committing, the commit is missing content.

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

## Solution

After any pre-commit hook failure, a mandatory verification step checks the state of the staging area:

1. `git diff --staged` to verify all intended changes are still staged
2. `git status` to check for unexpected unstaged modifications
3. If changes are missing, recover from `git stash list` (some hooks stash changes) or `git reflog`

For hook authors: hooks should be idempotent and non-destructive on failure. If a hook fails, the working tree should be in the same state as before the hook ran.

## Prevention

- **Always verify staged content after hook failure**: `git diff --staged` is the essential post-failure check
- **Write idempotent hooks**: Hooks that fail should leave the working tree unchanged
- **Use `pre-commit run` manually first**: Run hooks before `git commit` to see their effects in isolation
- **Know your pre-commit framework's behavior**: Different frameworks handle failure cleanup differently

## Cost of Forgetting

- **Silently lost changes**: Staged content reverted without any warning
- **Incomplete commits**: Commits that are missing intended changes
- **Debugging overhead**: "Why isn't this code in the commit?" when the hook failure is the cause

## Recommendations

### Do
- Immediately run git diff --staged after any pre-commit hook failure
- Write hooks to be idempotent and non-destructive on failure

### Don't
- Assume hook failure means "nothing changed" in the repository
- Re-stage files without checking what was lost

## Related Concepts

- [[compound-engineering]] - Hook reliability is foundational to compound commit workflows
- [[lesson-09-ruff-hook-fights]] - ruff hook conflicts that can trigger the revert behavior
- [[lesson-16-pre-commit-hooks-stage-override]] - the opposite problem: hooks that ADD unintended content to staging
- [[concept-automation]] - hook failure recovery mechanisms can have destructive side effects

## Validation

**Discovered**: Feb 2026 in Cohezion development workflow
**Status**: Validated -- post-hook-failure verification now standard practice
