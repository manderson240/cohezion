---
title: "CI Pipeline debugging — cascading failures from dev deps and permissions"
date: "2026-03-05"
status: complete
tags: [experiment, ci-cd, debugging]
aspect: thinker
neural:
  activation: 0.6
  stage: embryo
  synapse_in: 1
  synapse_out: 1
---

# CI Pipeline Debugging — Cascading Failures from Dev Deps and Permissions

## Hypothesis

CI pipeline failures were cascading from two independent root causes: (1) dev dependencies not being installed in the CI environment, and (2) GitHub Actions permissions insufficient for the required workflow steps.

## Method

Traced the failure chain from test execution errors backward through dependency installation logs and Actions permission grants. Identified that test frameworks required dev dependencies that weren't installed in the production CI profile.

## Results

Fixed by ensuring dev dependencies are installed in CI (adding `--dev` flag to install step) and granting necessary permissions in the workflow YAML. Both fixes were independently necessary — either alone was insufficient.

## Results (Detailed)

### Cascading Failure Chain Diagram

```
Missing --dev flag
    → pytest not found
    → test step exits code 1
    → check reporter step skipped (depends on test step success)
    → GITHUB_TOKEN lacks checks:write scope
    → status check never posted
    → branch protection gate: "Required check not found"
    → PR remains blocked indefinitely
```

Each failure in the chain was reported as its own error in the GitHub Actions UI, making the root cause appear to be branch protection misconfiguration rather than a missing `--dev` flag. Standard debugging (looking at the last error first) would chase the wrong fix.

### Minimum Required Permissions Block

```yaml
permissions:
  contents: read
  checks: write        # Required for check reporters (pytest, coverage)
  pull-requests: write # Required for PR comments from actions
```

### Dev Dependency Installation Fix

```yaml
# Before (broke CI)
- run: pip install -e .

# After (fixed)
- run: pip install -e ".[dev]"   # installs pytest, black, ruff, mypy
```

## Learnings

- CI environments must mirror the development dependency set when running tests; use `pip install -e ".[dev]"` not `pip install -e .`
- GitHub Actions permissions are deny-by-default; each required scope must be explicitly granted in the workflow YAML
- Cascading failures mask the root cause — **always read the CI log from top to bottom**, not just the final error
- The failure chain is only visible when you observe which steps are skipped or fail implicitly
- Debug strategy: find the first non-green step and fix it before addressing downstream failures

## Cohezion Relevance

This experiment illustrates the [[lesson-03-critical]] principle in CI context: the reported error is rarely the actual cause. In the Cohezion project, where CI gates control vault-modifying deployments, a blocked CI pipeline is a blocked knowledge pipeline. The fix pattern (explicit permissions + dev deps) is now standard in all Cohezion GitHub Actions workflows.

## Related

- [[2026-03-05-unblocking-pr-33-ci-fixes-for-branch-protection]] — the PR context that triggered this investigation
- [[lesson-03-critical]] — critical operations require explicit verification before proceeding
- [[github-actions-as-autonomous-claude-code-scheduler]] — the autonomous scheduling pattern that must have correct permissions to function
