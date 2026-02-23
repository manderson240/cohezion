---
title: Pre-Commit Hooks Can Stage Additional Files: Understand Side Effects
date: 2026-02-23
severity: MEDIUM
category: git
tags: [pre-commit, git, hooks, staging, side-effects]
status: validated
---

# Lesson: Pre-Commit Hooks Can Stage Additional Files: Understand Side Effects

## Context

Some pre-commit hooks (ruff --fix, black, isort) modify files and re-stage them as part of hook execution. This means the commit content can differ from what was originally staged.

## Core Learning

**Pre-commit hooks that modify and re-stage files can commit unintended changes. Review staged content AFTER hooks run.**

### Pattern
```bash
# Check what hooks added to staging
git diff --staged                   # Before running pre-commit
pre-commit run --all-files
git diff --staged                   # After -- check for unexpected additions
git status                          # Confirm only intended files are staged
```

## Recommendations

### Do
- Review git diff --staged after hook execution before committing
- Configure hooks to modify files without auto-staging (safer)

### Don't
- Assume staged content after hooks matches staged content before hooks

## Related Concepts

- [[compound-engineering]] - Deterministic commits are prerequisite for compound git workflows

## Validation

**Discovered**: Feb 2026 in Cohezion development workflow
**Status**: Validated
