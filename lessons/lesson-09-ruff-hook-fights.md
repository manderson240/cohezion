---
title: Ruff Pre-Commit Hook Conflicts: Hook Order and Auto-Fix Staging
date: 2026-02-23
severity: MEDIUM
category: tooling
tags: [ruff, pre-commit, hooks, git, formatting]
status: validated
---

# Lesson: Ruff Pre-Commit Hook Conflicts: Hook Order and Auto-Fix Staging

## Context

When ruff is configured as a pre-commit hook with --fix, it modifies files during the commit process. If the hook modifies files but doesn't re-stage them, the commit captures the pre-fix version, causing a commit loop.

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

## Recommendations

### Do
- Use ruff-format hook after ruff fix hook to ensure re-staging
- Test pre-commit hooks in isolation before enabling in team repo

### Don't
- Add --exit-non-zero-on-fix without also re-staging
- Assume ruff and black can coexist without explicit configuration

## Related Concepts

- [[compound-engineering]] - Clean pre-commit hooks are foundational to compound dev workflows

## Validation

**Discovered**: Feb 2026 in Cohezion Python development
**Status**: Validated
