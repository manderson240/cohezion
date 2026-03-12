---
title: "CI Pipeline debugging — cascading failures from dev deps and permissions"
date: "2026-03-05"
status: complete
tags: [experiment, ci-cd, debugging]
aspect: thinker
neural:
  activation: 0.287
  stage: embryo
  cluster: experiments
---

# CI Pipeline Debugging — Cascading Failures from Dev Deps and Permissions

## Hypothesis

CI pipeline failures were cascading from two independent root causes: (1) dev dependencies not being installed in the CI environment, and (2) GitHub Actions permissions insufficient for the required workflow steps.

## Method

Traced the failure chain from test execution errors backward through dependency installation logs and Actions permission grants. Identified that test frameworks required dev dependencies that weren't installed in the production CI profile.

## Results

Fixed by ensuring dev dependencies are installed in CI (adding `--dev` flag to install step) and granting necessary permissions in the workflow YAML. Both fixes were independently necessary — either alone was insufficient.

## Learnings

- CI environments must mirror the development dependency set when running tests
- GitHub Actions permissions are deny-by-default; each required scope must be explicitly granted
- Cascading failures mask the root cause — the first failure in the chain is rarely the one reported
- Related: [[2026-03-05-unblocking-pr-33-ci-fixes-for-branch-protection]]
