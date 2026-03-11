---
title: Ruff Pre-Commit Hook Conflicts: Hook Order and Auto-Fix Staging
date: 2026-02-23
severity: MEDIUM
category: tooling
cost_of_forgetting: "Infinite commit loop -- pre-commit hook modifies files, commit captures old version, next commit retriggers fix"
tags: [ruff, pre-commit, hooks, git, formatting]
status: validated
aspect: knower
neural:
  activation: 0.468
  stage: growing
  cluster: lessons
---

# Lesson: Ruff Pre-Commit Hook Conflicts: Hook Order and Auto-Fix Staging

## Context

During Cohezion Python development in February 2026, a developer configured ruff as a pre-commit hook with the `--fix` flag to automatically fix linting issues on commit. The first commit attempt seemed to work, but subsequent commits entered an infinite loop: the hook modified files, the commit captured the pre-fix version, the next commit saw the modified files as new changes, the hook ran again, and so on.

## Problem

The root cause is a mismatch between hook execution and git staging:

1. Developer stages files with `git add`
2. Pre-commit hook runs ruff with `--fix`, which modifies the staged files on disk
3. Git commits the originally staged content (the snapshot from step 1), NOT the modified content from step 2
4. The on-disk files now differ from the committed version
5. Next `git status` shows the files as modified, triggering another commit cycle

This is a fundamental interaction between pre-commit hooks that modify files and git's staging model. The hook changes the working tree copy but not the staged copy.

Additionally, attempting to use both ruff and black simultaneously caused formatting conflicts where each tool would "fix" the other's output in an alternating loop.

## Core Learning

**Ruff with --fix in pre-commit hooks must be followed by git add of modified files, or the hook will fight itself in a loop.**

### Pattern
```yaml
# .pre-commit-config.yaml -- correct configuration
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format  # Run after ruff fix, re-stages implicitly
```

## Solution

The correct configuration chains two hooks: `ruff` (with `--fix`) runs first to fix linting issues, then `ruff-format` runs to format the code and implicitly re-stages the modified files. The pre-commit framework handles the re-staging when the hooks modify files in sequence.

Key insight: do not use `--exit-non-zero-on-fix` without also handling re-staging, as this causes the hook to fail even though the fix was applied.

## Prevention

- **Test hooks in isolation**: Run `pre-commit run --all-files` manually before enabling hooks for the team
- **Use ruff-format after ruff fix**: This is the canonical configuration that handles re-staging
- **Choose one formatter**: Do not run both ruff-format and black; they will conflict
- **Read pre-commit docs on file modification**: Understand how your pre-commit framework handles hooks that modify files

## Cost of Forgetting

- **Infinite commit loop**: Every commit triggers another round of modifications
- **Developer frustration**: "Git is broken" when the real issue is hook configuration
- **Wasted CI time**: If hooks are also in CI, the loop can exhaust CI resources

## Recommendations

### Do
- Use ruff-format hook after ruff fix hook to ensure re-staging
- Test pre-commit hooks in isolation before enabling in team repo

### Don't
- Add --exit-non-zero-on-fix without also re-staging
- Assume ruff and black can coexist without explicit configuration

## Related Concepts

- [[compound-engineering]] - Clean pre-commit hooks are foundational to compound dev workflows
- [[concept-automation]] - ruff hook with --fix must re-stage modified files or causes an automation loop
- [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]] - related: ruff auto-formatting changes file content between reads and edits
- [[lesson-16-pre-commit-hooks-stage-override]] - related: hooks can stage additional files as a side effect
- [[lesson-27-hook-file-revert]] - related: failed hooks may revert staged changes

## Validation

**Discovered**: Feb 2026 in Cohezion Python development
**Status**: Validated -- canonical ruff hook configuration now documented
