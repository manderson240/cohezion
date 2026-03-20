---
title: "Unblocking PR #33 — CI fixes for branch protection"
date: "2026-03-05"
status: complete
tags: [experiment, ci-cd, github]
aspect: thinker
neural:
  activation: 0.59
  stage: embryo
  synapse_in: 2
  synapse_out: 1
---

# Unblocking PR #33 — CI Fixes for Branch Protection

## Hypothesis

PR #33 was blocked by CI failures related to branch protection rules. The hypothesis was that the failures cascaded from dev dependency issues and permission misconfigurations rather than actual code problems.

## Method

Investigated CI pipeline logs, identified cascading failure chain from missing dev dependencies and incorrect GitHub Actions permissions. Applied targeted fixes to the workflow configuration.

## Results

PR unblocked after fixing dependency installation order and permissions. The cascading failure pattern was documented as a lesson.

## Results (Detailed)

The CI failure chain was traced to three issues in order of root cause:

1. **Dev dependency installation order** — `pytest` and `black` were installed after the test step, not before. The CI log showed a `ModuleNotFoundError` that looked like a code error but was actually a dependency absence.
2. **GitHub Actions permissions** — the workflow lacked `contents: read` and `checks: write` permissions, causing the check reporter to fail silently, which then caused the branch protection gate to remain unresolved.
3. **Branch protection rule strictness** — "Require status checks to pass before merging" was enabled with the old check name. After renaming the workflow job, the protected branch rule had no matching check and blocked indefinitely.

Fix applied: update `pyproject.toml` install step, add explicit permissions block to workflow YAML, update branch protection rule to match new check name.

## Learnings

- CI failures often cascade: the root cause is upstream of the reported error — always trace the full log from the beginning, not just the first visible error
- Branch protection + required checks creates a strict gate that amplifies CI issues; rename any workflow job only after updating the branch protection rule
- GitHub Actions permissions must be explicit when using `GITHUB_TOKEN` for check reporting
- **Investigation order**: (1) Read full log top to bottom, (2) Find the first non-green step, (3) Check that step's permissions and dependencies before looking at code

## Cohezion Relevance

This experiment surfaces a recurring failure mode in Cohezion CI pipelines: silent upstream failures that manifest as downstream errors. The [[lesson-03-critical]] principle — verify before proceeding — applies directly: checking that CI environment preconditions are met before treating a test failure as a code defect.

## Related

- [[2026-03-05-ci-pipeline-debugging-cascading-failures-from-dev-deps-and-permissions]] — detailed companion note on the cascading failure pattern
- [[lesson-03-critical]] — critical operations require explicit verification before proceeding
- [[lesson-04-surgery-lesson]] — surgical edits: fix only what's required to unblock
- [[compound-engineering]] — even CI debugging sessions produce reusable patterns if properly documented
