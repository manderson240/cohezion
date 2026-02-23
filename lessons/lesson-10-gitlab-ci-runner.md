---
title: GitLab CI Runner: Local Pass Does Not Guarantee CI Pass
date: 2026-02-23
severity: HIGH
category: ci-cd
tags: [ci-cd, gitlab, testing, environment-parity]
status: validated
---

# Lesson: GitLab CI Runner: Local Pass Does Not Guarantee CI Pass

## Context

GitLab CI runners run in clean Docker environments without local caches, credentials, or development dependencies. Tests that pass locally with cached virtualenvs or .env files fail silently in CI.

## Core Learning

**Treat CI as a hostile clean-room environment. Every dependency must be declared; no local state can be assumed.**

### Pattern
```yaml
# .gitlab-ci.yml -- explicitly install everything
test:
  script:
    - pip install -e ".[dev]"
    - cp .env.example .env
    - pytest tests/ -v
  services:
    - surrealdb/surrealdb:latest
```

## Recommendations

### Do
- Run tests in a clean Docker container locally before pushing
- Use .env.example with dummy values for CI
- Declare ALL test dependencies in pyproject.toml [dev] extras

### Don't
- Rely on locally cached virtualenvs being available in CI
- Use local .env secrets in CI (use CI/CD variables)

## Related Concepts

- [[compound-engineering]] - CI parity enables reliable compound deployment pipelines

## Validation

**Status**: Validated in Cohezion CI/CD pipeline
