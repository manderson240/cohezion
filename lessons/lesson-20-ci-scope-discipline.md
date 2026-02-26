---
title: CI Scope Discipline: Test What Changed and All Its Dependents
date: 2026-02-23
severity: HIGH
category: ci-cd
tags: [ci-cd, testing, scope, efficiency, discipline]
status: validated
---

# Lesson: CI Scope Discipline: Test What Changed and All Its Dependents

## Context

CI pipelines that run the entire test suite on every commit are slow. CI pipelines that run too few tests miss regressions. The discipline is running exactly the right scope.

## Core Learning

**Scope CI to changed modules and their direct dependents. Use import graph analysis to determine blast radius precisely.**

### Pattern
```bash
# Find changed files
CHANGED=$(git diff --name-only main...HEAD | grep ".py$")

# Find test files for changed modules
for file in $CHANGED; do
    module=$(echo $file | sed 's/.py//' | sed 's|/|.|g')
    grep -rl "import $module\|from $module" tests/ --include="*.py"
done | sort -u | xargs pytest
```

## Recommendations

### Do
- Run import-graph-scoped tests on every commit
- Run full test suite nightly (not on every commit)

### Don't
- Run full suite on every small commit (slow CI)
- Run only direct tests without checking dependents (missed regressions)

## Related Concepts

- [[compound-engineering]] - Scoped CI enables rapid compound iteration
- [[circleci-ai-cicd-validation]] - CircleCI Chunk automates exactly this discipline: uses dependency graph analysis to run only tests for changed modules and their dependents, implementing scope discipline at scale

## Validation

**Discovered**: Feb 2026 in Cohezion CI optimization
**Status**: Validated
