---
title: Pre-Commit Hooks Can Stage Additional Files: Understand Side Effects
date: 2026-02-23
severity: MEDIUM
category: git
cost_of_forgetting: "Unintended changes committed silently; commit content differs from what was reviewed"
tags: [pre-commit, git, hooks, staging, side-effects]
status: validated
aspect: knower
neural:
  activation: 0.445
  stage: growing
  cluster: lessons
---

# Lesson: Pre-Commit Hooks Can Stage Additional Files: Understand Side Effects

## Context

During Cohezion development workflow in February 2026, a commit was made that included formatting changes to files the developer had not intentionally modified. The pre-commit hooks (ruff with `--fix`, isort) modified and re-staged files as part of hook execution. The developer reviewed their changes before committing, but the commit included additional modifications added by the hooks after the review.

## Problem

Pre-commit hooks that modify files create a gap between "what you reviewed" and "what gets committed":

1. Developer stages specific files and reviews `git diff --staged`
2. Developer runs `git commit`
3. Pre-commit hooks run: ruff fixes imports, isort reorders them, black reformats
4. Modified files are re-staged by the hook framework
5. The commit captures the hook-modified version, which may differ from what was reviewed

This is especially problematic when hooks touch files that were not in the original staging. For example, isort may rewrite imports in a file the developer did not change, and the hook framework stages that file too.

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

## Solution

The review workflow was updated to include a post-hook verification step:

1. Stage intended files with `git add`
2. Run `pre-commit run` manually (not as part of `git commit`)
3. Review `git diff --staged` AFTER hooks run to see the final commit content
4. Only then run `git commit`

This ensures the developer sees and approves exactly what will be committed, including hook modifications.

## Prevention

- **Run hooks manually before committing**: `pre-commit run` lets you see hook effects before the commit
- **Review staged content after hooks**: Always check `git diff --staged` after hooks run, not just before
- **Configure hooks conservatively**: Prefer hooks that check-only (exit non-zero) over hooks that auto-fix and re-stage
- **Understand each hook's behavior**: Know which hooks modify files and which only report issues

## Cost of Forgetting

- **Unintended changes committed**: Files modified by hooks that the developer did not review
- **Broken reviewer trust**: PR reviewers see changes the author did not intentionally make
- **Debugging confusion**: "I didn't change that file" when investigating a regression

## Recommendations

### Do
- Review git diff --staged after hook execution before committing
- Configure hooks to modify files without auto-staging (safer)

### Don't
- Assume staged content after hooks matches staged content before hooks

## Related Concepts

- [[compound-engineering]] - Deterministic commits are prerequisite for compound git workflows
- [[concept-automation]] - pre-commit hooks that modify and re-stage files are a key automation side-effect
- [[lesson-09-ruff-hook-fights]] - ruff hook configuration that causes commit loops when re-staging is not handled
- [[lesson-27-hook-file-revert]] - the opposite problem: failed hooks that revert staged changes

## Validation

**Discovered**: Feb 2026 in Cohezion development workflow
**Status**: Validated -- post-hook review now part of commit workflow
