---
title: CI Scope Discipline: Test What Changed and All Its Dependents
date: 2026-02-23
severity: HIGH
category: ci-cd
cost_of_forgetting: "Either slow CI (run everything) or missed regressions (run too little) -- both erode development velocity"
tags: [ci-cd, testing, scope, efficiency, discipline]
status: validated
aspect: knower
neural:
  activation: 0.72
  stage: growing
  synapse_in: 10
  synapse_out: 5
---

# Lesson: CI Scope Discipline: Test What Changed and All Its Dependents

## Context

During Cohezion CI optimization in February 2026, the CI pipeline ran the entire test suite on every commit. With 200+ tests and growing, CI feedback time was climbing toward 5+ minutes per commit. The team considered running only tests in changed files, but this approach missed regressions in dependent modules. The challenge was finding the precise middle ground: run enough tests to catch regressions, but not so many that CI becomes a bottleneck.

## Problem

Two extremes, both harmful:

1. **Run everything**: Every commit triggers all 200+ tests. Safe but slow. Developers start ignoring CI feedback because it takes too long. Small fixup commits become expensive.
2. **Run too little**: Only tests in changed files are run. Fast but dangerous. A change in `src/auth.py` that breaks `tests/test_api.py` (which imports auth) is missed because `test_api.py` was not changed.

The missed-regression failure is worse because it creates false confidence: CI passes, the code is merged, and the regression is discovered later -- often by a different developer working on an unrelated change.

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

## Solution

The CI pipeline now uses a two-tier approach:

1. **On every commit**: Run import-graph-scoped tests. The script identifies changed files, maps them to their importers (using `grep` or import graph analysis), and runs only the relevant tests. This typically runs 10-30% of the test suite.
2. **Nightly**: Run the full test suite as a safety net. This catches any regressions missed by import-graph scoping (e.g., dynamic imports, runtime dependencies).

This reduced average CI feedback time from 5+ minutes to under 90 seconds per commit, while maintaining regression detection at the same level as full-suite runs.

## Prevention

- **Map the import graph before enabling scoped CI**: Understand the dependency structure before relying on it
- **Include transitive dependents**: If A imports B and B imports C, changing C should test A too
- **Nightly full-suite as safety net**: Scoped CI is an optimization, not a replacement for comprehensive testing
- **Monitor regression escape rate**: Track how often the nightly run catches issues that scoped CI missed

## Cost of Forgetting

- **5+ minute CI feedback** if running everything -- developers stop waiting and merge without CI
- **Missed regressions** if running too little -- bugs merge silently and surface later
- **Developer frustration** from either slow or unreliable CI

## Recommendations

### Do
- Run import-graph-scoped tests on every commit
- Run full test suite nightly (not on every commit)

### Don't
- Run full suite on every small commit (slow CI)
- Run only direct tests without checking dependents (missed regressions)

## Related Concepts

- [[compound-engineering]] - Scoped CI enables rapid compound iteration
- [[circleci-ai-cicd-validation]] - CircleCI Chunk automates exactly this discipline: uses dependency graph analysis to run only tests for changed modules and their dependents
- [[lesson-08-import-graph]] - Import graph analysis is the prerequisite for accurate CI scoping
- [[lesson-10-gitlab-ci-runner]] - CI environments are clean rooms; scoped CI reduces the test surface in these constrained environments
- [[concept-testing]] - CI scope discipline is a test strategy decision: precision over coverage

## Validation

**Discovered**: Feb 2026 in Cohezion CI optimization
**Impact**: CI feedback from 5+ min to under 90 sec per commit
**Status**: Validated
